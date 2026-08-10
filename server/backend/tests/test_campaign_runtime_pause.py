import asyncio
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from models import Campaign, CampaignStatus, Victim
from routes.campaign_lifecycle import pause_campaign, resume_campaign, stop_campaign
from routes.campaign_victims import update_victim_status
from utils.request_models import VictimStatusRequest
from utils.docker import (
    CampaignRuntimeStateError,
    set_campaign_runtime_paused,
)


class FakeContainer:
    def __init__(self, identifier, name, labels, status, events):
        self.id = identifier
        self.name = name
        self.labels = labels
        self.status = status
        self.events = events
        self.pause_error = None
        self.unpause_error = None

    def reload(self):
        return None

    def pause(self):
        self.events.append(("pause", self.name))
        if self.pause_error:
            raise self.pause_error
        self.status = "paused"

    def unpause(self):
        self.events.append(("unpause", self.name))
        if self.unpause_error:
            raise self.unpause_error
        self.status = "running"

    def start(self):
        self.events.append(("start", self.name))
        self.status = "running"

    def stop(self, timeout=10):
        self.events.append(("stop", self.name))
        self.status = "exited"


class CampaignRuntimePauseTests(unittest.TestCase):
    def make_runtime(self, status="running"):
        events = []
        campaign = FakeContainer(
            "campaign",
            "p-bitm-campaign",
            {"bitm.campaign.id": "campaign", "bitm.type": "campaign"},
            status,
            events,
        )
        victim = FakeContainer(
            "victim",
            "p-bitm-campaign-victim",
            {"bitm.campaign.id": "campaign", "bitm.role": "victim"},
            status,
            events,
        )
        egress = FakeContainer(
            "egress",
            "p-bitm-egress-campaign",
            {
                "bitm.campaign.id": "campaign",
                "bitm.role": "campaign-egress-proxy",
            },
            status,
            events,
        )
        client = MagicMock()
        client.containers.get.return_value = campaign
        client.containers.list.return_value = [victim, egress, campaign]
        return client, campaign, victim, egress, events

    def test_pauses_gateway_before_related_workloads(self):
        client, campaign, victim, egress, events = self.make_runtime()

        with patch("utils.docker.get_docker_client", return_value=client):
            changed = set_campaign_runtime_paused(
                campaign.name,
                "campaign",
                True,
            )

        self.assertEqual(changed, 3)
        self.assertEqual(events[0], ("pause", campaign.name))
        self.assertEqual(
            {campaign.status, victim.status, egress.status},
            {"paused"},
        )

    def test_resumes_gateway_after_related_workloads(self):
        client, campaign, victim, egress, events = self.make_runtime("paused")

        with patch("utils.docker.get_docker_client", return_value=client):
            changed = set_campaign_runtime_paused(
                campaign.name,
                "campaign",
                False,
            )

        self.assertEqual(changed, 3)
        self.assertEqual(events[-1], ("unpause", campaign.name))
        self.assertEqual(
            {campaign.status, victim.status, egress.status},
            {"running"},
        )

    def test_rolls_back_partial_pause(self):
        client, campaign, victim, _egress, events = self.make_runtime()
        victim.pause_error = RuntimeError("pause failed")

        with (
            patch("utils.docker.get_docker_client", return_value=client),
            self.assertRaises(CampaignRuntimeStateError),
        ):
            set_campaign_runtime_paused(
                campaign.name,
                "campaign",
                True,
            )

        self.assertIn(("unpause", campaign.name), events)
        self.assertEqual(campaign.status, "running")

    def test_rejects_campaign_container_with_wrong_scope(self):
        client, campaign, *_ = self.make_runtime()
        campaign.labels["bitm.campaign.id"] = "different"

        with (
            patch("utils.docker.get_docker_client", return_value=client),
            self.assertRaises(CampaignRuntimeStateError),
        ):
            set_campaign_runtime_paused(
                campaign.name,
                "campaign",
                True,
            )


class CampaignPauseRouteTests(unittest.TestCase):
    def campaign(self, status):
        return SimpleNamespace(
            id="campaign",
            name="Test Campaign",
            container_name="p-bitm-campaign",
            status=status,
            container_status="running",
            scheduled_end=None,
            started_at=None,
        )

    def database(self, campaign):
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = campaign
        return db

    def actor(self):
        return SimpleNamespace(username="test-operator")

    def test_pause_changes_runtime_and_persisted_state(self):
        campaign = self.campaign(CampaignStatus.active)
        db = self.database(campaign)

        with patch(
            "routes.campaign_lifecycle.set_campaign_runtime_paused"
        ) as set_paused:
            result = asyncio.run(
                pause_campaign("campaign", db=db, current_user=self.actor())
            )

        set_paused.assert_called_once_with(
            campaign.container_name,
            campaign.id,
            True,
        )
        self.assertEqual(campaign.status, CampaignStatus.paused)
        self.assertEqual(campaign.container_status, "paused")
        self.assertEqual(result["status"], "paused")

    def test_failed_pause_restores_active_state(self):
        campaign = self.campaign(CampaignStatus.active)
        db = self.database(campaign)

        with (
            patch(
                "routes.campaign_lifecycle.set_campaign_runtime_paused",
                side_effect=CampaignRuntimeStateError("failed"),
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            asyncio.run(
                pause_campaign("campaign", db=db, current_user=self.actor())
            )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(campaign.status, CampaignStatus.active)
        self.assertEqual(campaign.container_status, "running")

    def test_resume_changes_runtime_and_persisted_state(self):
        campaign = self.campaign(CampaignStatus.paused)
        campaign.container_status = "paused"
        campaign.scheduled_end = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db = self.database(campaign)

        with patch(
            "routes.campaign_lifecycle.set_campaign_runtime_paused"
        ) as set_paused:
            result = asyncio.run(
                resume_campaign("campaign", db=db, current_user=self.actor())
            )

        set_paused.assert_called_once_with(
            campaign.container_name,
            campaign.id,
            False,
        )
        self.assertEqual(campaign.status, CampaignStatus.active)
        self.assertEqual(campaign.container_status, "running")
        self.assertIsNotNone(campaign.started_at)
        self.assertEqual(result["status"], "active")


class CampaignStopRouteTests(unittest.TestCase):
    def test_stop_marks_every_victim_offline(self):
        campaign = SimpleNamespace(
            id="campaign",
            name="Test Campaign",
            container_name="p-bitm-campaign",
            status=CampaignStatus.active,
            container_status="running",
            completed_at=None,
        )
        victims = [
            SimpleNamespace(is_active=True, container_status="running"),
            SimpleNamespace(is_active=False, container_status=None),
        ]
        campaign_query = MagicMock()
        campaign_query.filter.return_value.first.return_value = campaign
        victim_query = MagicMock()
        victim_query.filter.return_value.all.return_value = victims
        db = MagicMock()
        db.query.side_effect = lambda model: (
            campaign_query if model is Campaign else victim_query
        )

        with patch(
            "routes.campaign_lifecycle.remove_campaign_runtime"
        ) as remove_runtime:
            result = asyncio.run(
                stop_campaign(
                    campaign.id,
                    db=db,
                    current_user=SimpleNamespace(username="test-operator"),
                )
            )

        remove_runtime.assert_called_once_with(
            campaign.container_name,
            campaign.id,
        )
        self.assertEqual(campaign.status, CampaignStatus.completed)
        self.assertEqual(campaign.container_status, "stopped")
        self.assertTrue(all(not victim.is_active for victim in victims))
        self.assertTrue(all(
            victim.container_status == "stopped" for victim in victims
        ))
        db.commit.assert_called_once()
        self.assertTrue(result["success"])

    def test_late_heartbeat_cannot_reactivate_completed_campaign_victim(self):
        victim = SimpleNamespace(
            id="victim",
            campaign=SimpleNamespace(status=CampaignStatus.completed),
            is_active=True,
            first_seen=datetime.now(timezone.utc),
            last_seen=None,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = victim

        result = asyncio.run(
            update_victim_status(
                "campaign",
                victim.id,
                VictimStatusRequest(status="active"),
                db=db,
                _=True,
            )
        )

        self.assertFalse(victim.is_active)
        self.assertFalse(result["is_active"])
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
