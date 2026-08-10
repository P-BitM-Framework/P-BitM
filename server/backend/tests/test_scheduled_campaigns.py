import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from models import CampaignStatus
from routes.campaign_common import resolve_campaign_schedule
from utils.docker import set_campaign_runtime_started

from tests.test_campaign_runtime_pause import FakeContainer


class CampaignScheduleValidationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

    def test_scheduled_launch_requires_a_future_bounded_window(self):
        start = self.now + timedelta(hours=1)
        end = start + timedelta(hours=2)

        result = resolve_campaign_schedule(
            {
                "launch_type": "scheduled",
                "scheduled_date": start.isoformat(),
                "scheduled_date_end": end.isoformat(),
            },
            "full",
            self.now,
        )

        self.assertEqual(result, (start, end, CampaignStatus.scheduled))

    def test_scheduled_launch_rejects_missing_or_past_dates(self):
        with self.assertRaises(HTTPException):
            resolve_campaign_schedule(
                {
                    "launch_type": "scheduled",
                    "scheduled_date": None,
                    "scheduled_date_end": None,
                },
                "full",
                self.now,
            )

        with self.assertRaises(HTTPException):
            resolve_campaign_schedule(
                {
                    "launch_type": "scheduled",
                    "scheduled_date": (
                        self.now - timedelta(minutes=1)
                    ).isoformat(),
                    "scheduled_date_end": (
                        self.now + timedelta(hours=1)
                    ).isoformat(),
                },
                "full",
                self.now,
            )

    def test_immediate_launch_rejects_scheduled_dates(self):
        with self.assertRaises(HTTPException):
            resolve_campaign_schedule(
                {
                    "launch_type": "immediate",
                    "scheduled_date": (
                        self.now + timedelta(hours=1)
                    ).isoformat(),
                    "scheduled_date_end": (
                        self.now + timedelta(hours=2)
                    ).isoformat(),
                },
                "full",
                self.now,
            )


class ScheduledRuntimeTests(unittest.TestCase):
    def make_runtime(self, status):
        events = []
        campaign = FakeContainer(
            "campaign",
            "p-bitm-campaign",
            {"bitm.campaign.id": "campaign", "bitm.type": "campaign"},
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
        client.containers.list.return_value = [campaign, egress]
        return client, campaign, egress, events

    def test_starts_gateway_after_supporting_sidecars(self):
        client, campaign, egress, events = self.make_runtime("created")

        with patch("utils.docker.get_docker_client", return_value=client):
            changed = set_campaign_runtime_started(
                campaign.name,
                "campaign",
                True,
            )

        self.assertEqual(changed, 2)
        self.assertEqual(events[0], ("start", egress.name))
        self.assertEqual(events[-1], ("start", campaign.name))

    def test_stops_gateway_before_supporting_sidecars(self):
        client, campaign, egress, events = self.make_runtime("running")

        with patch("utils.docker.get_docker_client", return_value=client):
            changed = set_campaign_runtime_started(
                campaign.name,
                "campaign",
                False,
            )

        self.assertEqual(changed, 2)
        self.assertEqual(events[0], ("stop", campaign.name))
        self.assertEqual(events[-1], ("stop", egress.name))


if __name__ == "__main__":
    unittest.main()
