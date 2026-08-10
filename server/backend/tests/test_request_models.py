import unittest
from datetime import timezone

from pydantic import ValidationError

from utils.request_models import (
    CampaignCreateRequest,
    CommandRequest,
    DataCollectionRequest,
    EventCreateRequest,
    TrackingEventRequest,
    VictimStatusRequest,
)


def valid_campaign_payload():
    return {
        "name": "Awareness campaign",
        "description": "",
        "url": "https://example.com",
        "public_domain": "training.example.com",
        "campaign_type": "standalone",
        "smtp_profile_id": None,
        "email_template_id": None,
        "landing_page_id": "landing01",
        "target_list_id": "targets01",
        "plugin_ids": [],
        "module_ids": [],
        "launch_type": "immediate",
        "scheduled_date": None,
        "scheduled_date_end": None,
        "advanced_options": {
            "protocol": "selkies",
            "selkies": {
                "use_streaming_mode": True,
                "use_paint_over_quality": True,
                "video_quality": "medium",
                "framerate": "medium",
                "compression_level": "medium",
            },
        },
    }


class CampaignRequestValidationTests(unittest.TestCase):
    def test_accepts_the_frontend_campaign_contract(self):
        request = CampaignCreateRequest.model_validate(valid_campaign_payload())

        self.assertEqual(request.name, "Awareness campaign")
        self.assertEqual(request.advanced_options.protocol, "selkies")

    def test_rejects_unknown_fields(self):
        payload = valid_campaign_payload()
        payload["unexpected"] = "value"

        with self.assertRaises(ValidationError):
            CampaignCreateRequest.model_validate(payload)

    def test_rejects_duplicate_plugin_identifiers(self):
        payload = valid_campaign_payload()
        payload["plugin_ids"] = ["plugin01", "plugin01"]

        with self.assertRaises(ValidationError):
            CampaignCreateRequest.model_validate(payload)

    def test_accepts_optional_tracking_parameter(self):
        payload = valid_campaign_payload()
        payload["advanced_options"]["tracking_parameter"] = "state"

        request = CampaignCreateRequest.model_validate(payload)

        self.assertEqual(
            request.advanced_options.tracking_parameter,
            "state",
        )

    def test_rejects_unsafe_tracking_parameter(self):
        for value in ("1state", "state.value", "state/value", "state value"):
            with self.subTest(value=value):
                payload = valid_campaign_payload()
                payload["advanced_options"]["tracking_parameter"] = value
                with self.assertRaises(ValidationError):
                    CampaignCreateRequest.model_validate(payload)

    def test_rejects_unsafe_target_urls_on_create(self):
        unsafe_urls = (
            "javascript:alert(1)",
            "https://example.com/$(whoami)",
            "https://example.com/`whoami`",
            "https://example.com/${PATH}",
            "https://user:password@example.com/",
            "https://example.com\\@attacker.test/",
            "https://example.com:invalid/",
            "https://example.com/path with spaces",
        )

        for value in unsafe_urls:
            with self.subTest(value=value):
                payload = valid_campaign_payload()
                payload["url"] = value
                with self.assertRaises(ValidationError):
                    CampaignCreateRequest.model_validate(payload)

    def test_accepts_url_query_metacharacters_as_data(self):
        payload = valid_campaign_payload()
        payload["url"] = "https://example.com/path?a=1&b=x|y;c=z"

        request = CampaignCreateRequest.model_validate(payload)

        self.assertEqual(request.url, payload["url"])

class CallbackRequestValidationTests(unittest.TestCase):
    def test_accepts_gateway_disconnect_status(self):
        request = VictimStatusRequest(status="disconnected")

        self.assertEqual(request.status, "disconnected")

    def test_rejects_artifact_traversal(self):
        with self.assertRaises(ValidationError):
            DataCollectionRequest(
                data_type="screenshot",
                file_path="../outside.png",
            )

    def test_module_data_requires_a_module_identifier(self):
        with self.assertRaises(ValidationError):
            DataCollectionRequest(
                data_type="module_data",
                file_path=None,
            )

    def test_rejects_unknown_event_fields(self):
        with self.assertRaises(ValidationError):
            EventCreateRequest(
                event_type="navigation",
                payload={},
                unexpected=True,
            )

    def test_accepts_json_event_contract(self):
        request = EventCreateRequest.model_validate(
            {
                "event_type": "navigation",
                "timestamp": "2026-07-26T08:15:30Z",
                "payload": {},
            }
        )

        self.assertEqual(request.event_type.value, "navigation")
        self.assertEqual(request.timestamp.tzinfo, timezone.utc)

    def test_accepts_bulk_cookie_payload(self):
        request = EventCreateRequest.model_validate(
            {
                "event_type": "cookie_captured",
                "timestamp": "2026-07-26T08:15:30+00:00",
                "payload": {"cookies": []},
            }
        )

        self.assertEqual(request.event_type.value, "cookie_captured")

    def test_accepts_json_data_collection_timestamp(self):
        request = DataCollectionRequest.model_validate(
            {
                "data_type": "screenshot",
                "file_path": "screenshots/capture.png",
                "collected_at": "2026-07-26T08:15:30Z",
            }
        )

        self.assertEqual(request.collected_at.tzinfo, timezone.utc)

    def test_rejects_naive_json_timestamp(self):
        with self.assertRaises(ValidationError):
            EventCreateRequest.model_validate(
                {
                    "event_type": "navigation",
                    "timestamp": "2026-07-26T08:15:30",
                    "payload": {},
                }
            )

    def test_rejects_oversized_metadata(self):
        with self.assertRaises(ValidationError):
            TrackingEventRequest(
                tracking_id="tracking",
                campaign_id="campaign",
                submitted_data={"value": "x" * (256 * 1024)},
            )

    def test_rejects_oversized_commands(self):
        with self.assertRaises(ValidationError):
            CommandRequest(command="x" * (1024 * 1024 + 1))
