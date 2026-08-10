import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from utils.campaign import create_campaign_victims, get_selkies_env


class CampaignVictimCreationTests(unittest.TestCase):
    def test_distributes_send_times_across_the_full_schedule(self):
        start = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
        end = start + timedelta(minutes=20)
        targets = [
            SimpleNamespace(
                email=f"target-{index}@example.test",
                first_name="Target",
                last_name=str(index),
            )
            for index in range(3)
        ]
        db = MagicMock()

        created = create_campaign_victims(
            db,
            "campaign",
            targets,
            scheduled_date=start,
            scheduled_date_end=end,
        )

        self.assertEqual(created, 3)
        scheduled_times = [
            call.args[0].scheduled_send_at
            for call in db.add.call_args_list
        ]
        self.assertEqual(
            scheduled_times,
            [
                start,
                start + timedelta(minutes=6, seconds=40),
                start + timedelta(minutes=13, seconds=20),
            ],
        )
        self.assertTrue(all(send_time < end for send_time in scheduled_times))
        db.commit.assert_not_called()

    def test_empty_target_sequence_does_not_commit(self):
        db = MagicMock()

        created = create_campaign_victims(db, "campaign", [])

        self.assertEqual(created, 0)
        db.add.assert_not_called()
        db.commit.assert_not_called()


class SelkiesEnvironmentTests(unittest.TestCase):
    def test_maps_dashboard_quality_presets_to_environment(self):
        result = get_selkies_env(
            {
                "selkies": {
                    "use_streaming_mode": True,
                    "use_paint_over_quality": False,
                    "video_quality": "high",
                    "framerate": "low",
                    "compression_level": "medium",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "SELKIES_ENABLE_STREAMING": "true",
                "SELKIES_ENABLE_PAINTOVER": "false",
                "SELKIES_H264_CRF": "20",
                "SELKIES_H264_PAINTOVER_CRF": "15",
                "SELKIES_FRAMERATE": "30",
            },
        )


if __name__ == "__main__":
    unittest.main()
