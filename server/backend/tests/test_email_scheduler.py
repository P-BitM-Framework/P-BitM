import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from models import CampaignStatus
from services.email_sender import (
    activate_scheduled_campaigns,
    campaign_is_active,
    send_campaign_batch,
)
from utils.docker import CampaignRuntimeStateError


class QueryMustNotRun:
    def query(self, *args, **kwargs):
        raise AssertionError("standalone campaigns must not enter email delivery")


class EmailSchedulerTests(unittest.TestCase):
    def test_due_campaign_starts_runtime_before_delivery(self):
        campaign = SimpleNamespace(
            id="campaign",
            name="Scheduled campaign",
            container_name="p-bitm-campaign",
            status=CampaignStatus.scheduled,
            container_status="scheduled",
            started_at=None,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [campaign]
        now = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)

        with patch(
            "services.email_sender.set_campaign_runtime_started"
        ) as start_runtime:
            activated = activate_scheduled_campaigns(db, now)

        self.assertEqual(activated, 1)
        start_runtime.assert_called_once_with(
            campaign.container_name,
            campaign.id,
            True,
        )
        self.assertEqual(campaign.status, CampaignStatus.active)
        self.assertEqual(campaign.container_status, "running")
        self.assertEqual(campaign.started_at, now)

    def test_failed_scheduled_start_remains_retryable(self):
        campaign = SimpleNamespace(
            id="campaign",
            name="Scheduled campaign",
            container_name="p-bitm-campaign",
            status=CampaignStatus.scheduled,
            container_status="scheduled",
            started_at=None,
        )
        db = MagicMock()
        filtered = db.query.return_value.filter.return_value
        filtered.all.return_value = [campaign]
        filtered.first.return_value = campaign
        now = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)

        with patch(
            "services.email_sender.set_campaign_runtime_started",
            side_effect=CampaignRuntimeStateError("start failed"),
        ):
            activated = activate_scheduled_campaigns(db, now)

        self.assertEqual(activated, 0)
        self.assertEqual(campaign.status, CampaignStatus.scheduled)
        self.assertEqual(campaign.container_status, "start_failed")
        self.assertIsNone(campaign.started_at)

    def test_reads_current_campaign_status_before_delivery(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = (
            CampaignStatus.paused
        )

        self.assertFalse(campaign_is_active(db, "campaign"))

    def test_standalone_campaign_never_attempts_email_delivery(self):
        campaign = SimpleNamespace(campaign_type="standalone")

        send_campaign_batch(QueryMustNotRun(), campaign)

if __name__ == "__main__":
    unittest.main()
