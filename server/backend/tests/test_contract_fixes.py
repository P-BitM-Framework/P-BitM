import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Campaign, DataCollection, Victim, VictimEvent
from models.victim_event import EventType
from routes import campaigns as campaign_routes
from routes import campaign_actions, campaign_common, campaign_victims
from routes.email_templates import EmailTemplateCreate
from utils.request_models import CampaignModuleRequest
from utils.tracking import update_victim_clicked


class CampaignRouteContractTests(unittest.TestCase):
    def test_general_campaign_update_route_is_not_registered(self):
        methods_by_path = {
            route.path: route.methods
            for route in campaign_routes.router.routes
        }

        self.assertNotIn(
            "PUT",
            methods_by_path.get("/{campaign_id}", set()),
        )


class SerializationContractTests(unittest.TestCase):
    def test_invalid_collection_metadata_does_not_break_response(self):
        collection = DataCollection(
            id="collection",
            victim_id="victim",
            campaign_id="campaign",
            data_type="module_data",
            extra_metadata="{invalid",
        )

        result = collection.to_dict()

        self.assertEqual(result["metadata"], {})
        self.assertEqual(result["extra_metadata"], {})

    def test_invalid_event_payload_does_not_break_response(self):
        event = VictimEvent(
            id="event",
            victim_id="victim",
            campaign_id="campaign",
            event_type=EventType.FORM_SUBMISSION,
            payload="{invalid",
        )

        self.assertEqual(event.to_dict()["payload"], {})


class CampaignCollectedDataStatsTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.campaign = Campaign(
            id="campaign",
            name="Campaign",
            target_url="https://example.test",
            total_targets=3,
        )
        self.victims = [
            Victim(
                id=f"victim-{index}",
                campaign_id=self.campaign.id,
                email=f"victim-{index}@example.test",
                tracking_id=f"tracking-{index}",
                scheduled_send_at=datetime.now(timezone.utc),
            )
            for index in range(3)
        ]
        self.db.add_all([self.campaign, *self.victims])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_counts_distinct_victims_with_collected_information(self):
        self.db.add_all([
            DataCollection(
                victim_id=self.victims[0].id,
                campaign_id=self.campaign.id,
                data_type="module_data",
            ),
            VictimEvent(
                victim_id=self.victims[1].id,
                campaign_id=self.campaign.id,
                event_type=EventType.COOKIE_CAPTURED,
            ),
        ])
        self.victims[2].data_submitted_at = datetime.now(timezone.utc)
        self.db.commit()

        self.campaign.update_stats(self.db)

        self.assertEqual(self.campaign.to_dict()["data_collected"], 3)


class VictimNetworkMetadataTests(unittest.TestCase):
    def test_interactive_connection_replaces_tracking_proxy_ip(self):
        victim = SimpleNamespace(
            extra_metadata=None,
            ip_address="198.51.100.174",
            user_agent=None,
        )

        campaign_common._apply_interactive_client_metadata(
            victim,
            EventType.VICTIM_CONNECTED,
            {
                "ip_address": "203.0.113.42",
                "user_agent": "Victim browser",
            },
        )

        self.assertEqual(victim.ip_address, "203.0.113.42")
        self.assertEqual(
            victim.extra_metadata["interactive_ip_address"],
            "203.0.113.42",
        )
        self.assertEqual(victim.user_agent, "Victim browser")

    def test_later_tracking_click_does_not_replace_interactive_ip(self):
        victim = SimpleNamespace(
            email_link_clicked_at=datetime.now(timezone.utc),
            extra_metadata={"interactive_ip_address": "203.0.113.42"},
            ip_address="203.0.113.42",
            user_agent="Victim browser",
            browser=None,
            os=None,
            campaign=None,
        )
        db = MagicMock()

        update_victim_clicked(
            db,
            victim,
            ip_address="198.51.100.174",
            user_agent="Mail scanner",
        )

        self.assertEqual(victim.ip_address, "203.0.113.42")
        self.assertEqual(victim.user_agent, "Victim browser")
        db.commit.assert_called_once()

    def test_collected_browser_info_preserves_interactive_ip(self):
        victim = SimpleNamespace(
            extra_metadata={"interactive_ip_address": "203.0.113.42"},
        )

        campaign_common._merge_collected_metadata(
            victim,
            {"language": "it-IT"},
        )

        self.assertEqual(victim.extra_metadata["language"], "it-IT")
        self.assertEqual(
            victim.extra_metadata["interactive_ip_address"],
            "203.0.113.42",
        )


class EmailTemplateContractTests(unittest.TestCase):
    def test_create_schema_accepts_tags_and_attachments(self):
        schema = EmailTemplateCreate(
            name="Template",
            subject="Subject",
            html_content="<p>Hello</p>",
            tags=["awareness"],
            attachments=[{"filename": "notice.pdf", "path": "notice.pdf"}],
        )

        self.assertEqual(schema.tags, ["awareness"])
        self.assertEqual(schema.attachments[0]["filename"], "notice.pdf")


class CampaignModuleContractTests(unittest.TestCase):
    def test_dashboard_module_payload_matches_database_model(self):
        campaign = SimpleNamespace(
            id="campaign",
            name="Campaign",
            module_ids=[],
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = campaign

        with tempfile.TemporaryDirectory() as temporary_storage:
            with patch.object(campaign_actions, "STORAGE_PATH", temporary_storage):
                result = campaign_actions.create_campaign_module(
                    campaign_id=campaign.id,
                    data=CampaignModuleRequest(
                        name="Browser prompt",
                        description="Test module",
                        category="Custom",
                        inputs=[],
                        payload="<div>Prompt</div>",
                    ),
                    db=db,
                    current_user=SimpleNamespace(id="operator", username="operator"),
                )

            module_file = (
                Path(temporary_storage)
                / "campaigns"
                / "Campaign-campaign"
                / "modules"
                / f"{result['id']}.json"
            )
            self.assertTrue(module_file.is_file())

        created_module = db.add.call_args.args[0]
        self.assertEqual(created_module.name, "Browser prompt")
        self.assertEqual(created_module.payload, "<div>Prompt</div>")
        self.assertEqual(result["name"], "Browser prompt")


class CampaignDomainContractTests(unittest.TestCase):
    def test_public_domain_is_canonicalized(self):
        self.assertEqual(
            campaign_common.normalize_public_domain(
                "https://Login.Example.COM/"
            ),
            "login.example.com",
        )

    def test_public_domain_rejects_route_injection_and_url_components(self):
        invalid_values = (
            "example.com:8443",
            "example.com/path",
            "https://user@example.com/",
            "https://example.com/?redirect=other",
            "example.com`) || Host(`other.example.com",
        )

        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(HTTPException):
                campaign_common.normalize_public_domain(value)

    def test_production_public_url_uses_canonical_host(self):
        with patch.object(campaign_common, "ENVIRONMENT", "production"):
            self.assertEqual(
                campaign_common.build_campaign_public_url(
                    "campaign",
                    "HTTPS://Phish.Example/",
                ),
                "https://phish.example/",
            )


class CampaignScheduleContractTests(unittest.TestCase):
    def test_schedule_timestamp_is_normalized_to_utc(self):
        parsed = campaign_common.parse_schedule_datetime(
            "2026-07-25T20:00:00+02:00",
            "scheduled_date",
        )

        self.assertEqual(
            parsed,
            datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        )

    def test_schedule_timestamp_requires_explicit_timezone(self):
        with self.assertRaises(HTTPException):
            campaign_common.parse_schedule_datetime(
                "2026-07-25T20:00:00",
                "scheduled_date",
            )


class ManualScreenshotContractTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.campaign = Campaign(
            id="campaign",
            name="Campaign",
            target_url="https://example.test",
            protocol="selkies",
            container_name="p-bitm-campaign",
        )
        self.victim = Victim(
            id="victim",
            campaign_id=self.campaign.id,
            email="victim@example.test",
            tracking_id="tracking",
            scheduled_send_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self.db.add_all([self.campaign, self.victim])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_manual_capture_persists_file_metadata_and_event(self):
        captured = SimpleNamespace(
            content=b"\x89PNG\r\n\x1a\ncapture",
            width=1280,
            height=720,
        )

        with tempfile.TemporaryDirectory() as storage:
            with (
                patch.object(
                    campaign_victims,
                    "capture_admin_owned_victim_screenshot",
                    return_value=captured,
                ),
                patch.object(
                    campaign_victims,
                    "setup_campaign_storage",
                    return_value=Path(storage),
                ),
            ):
                result = asyncio.run(
                    campaign_victims.capture_screenshot(
                        campaign_id=self.campaign.id,
                        victim_id=self.victim.id,
                        db=self.db,
                        current_user=SimpleNamespace(id="operator", username="operator"),
                    )
                )

            screenshot = self.db.query(DataCollection).one()
            event = self.db.query(VictimEvent).one()
            destination = Path(storage) / self.victim.id / screenshot.file_path

            self.assertTrue(destination.is_file())
            self.assertEqual(destination.read_bytes(), captured.content)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            self.assertEqual(screenshot.extra_metadata["capture_mode"], "manual")
            self.assertEqual(screenshot.extra_metadata["resolution"], "1280x720")
            self.assertEqual(event.event_type, EventType.SCREENSHOT)
            self.assertEqual(result["screenshot"]["id"], screenshot.id)
            self.assertEqual(self.campaign.total_screenshots, 1)

    def test_manual_capture_rejects_offline_victim(self):
        self.victim.is_active = False
        self.db.commit()

        with patch.object(
            campaign_victims,
            "capture_admin_owned_victim_screenshot",
        ) as capture:
            with self.assertRaisesRegex(
                HTTPException,
                "Victim browser is not connected",
            ):
                asyncio.run(
                    campaign_victims.capture_screenshot(
                        campaign_id=self.campaign.id,
                        victim_id=self.victim.id,
                        db=self.db,
                        current_user=SimpleNamespace(id="operator", username="operator"),
                    )
                )

        capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
