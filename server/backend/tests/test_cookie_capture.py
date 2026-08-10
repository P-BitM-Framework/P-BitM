import asyncio
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Campaign, CapturedCookie, Victim, VictimEvent
from models.victim_event import EventType
from routes.campaign_victims import create_event
from utils.cookie_capture import filter_new_cookie_payload
from utils.request_models import EventCreateRequest


class CookieCaptureDeduplicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.campaign = Campaign(
            id="campaign",
            name="Campaign",
            target_url="https://example.test",
        )
        self.victim = Victim(
            id="victim",
            campaign_id=self.campaign.id,
            email="victim@example.test",
            tracking_id="tracking",
            scheduled_send_at=datetime.now(timezone.utc),
        )
        self.db.add_all([self.campaign, self.victim])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @staticmethod
    def cookie(value: str, name: str = "session") -> dict:
        return {
            "storeId": "firefox-default",
            "domain": ".example.test",
            "path": "/",
            "name": name,
            "value": value,
            "secure": True,
        }

    def test_same_value_is_reserved_once_but_changed_value_is_new(self):
        first, first_duplicates = filter_new_cookie_payload(
            self.db, self.victim.id, self.cookie("first")
        )
        duplicate, duplicate_count = filter_new_cookie_payload(
            self.db, self.victim.id, self.cookie("first")
        )
        changed, changed_duplicates = filter_new_cookie_payload(
            self.db, self.victim.id, self.cookie("second")
        )

        self.assertIsNotNone(first)
        self.assertEqual(first_duplicates, 0)
        self.assertIsNone(duplicate)
        self.assertEqual(duplicate_count, 1)
        self.assertIsNotNone(changed)
        self.assertEqual(changed_duplicates, 0)

    def test_bulk_payload_keeps_only_new_cookie_values(self):
        filter_new_cookie_payload(
            self.db, self.victim.id, self.cookie("existing")
        )
        filtered, duplicate_count = filter_new_cookie_payload(
            self.db,
            self.victim.id,
            {
                "cookies": [
                    self.cookie("existing"),
                    self.cookie("new"),
                    self.cookie("new"),
                ],
                "count": 3,
            },
        )

        self.assertEqual(duplicate_count, 2)
        self.assertEqual(filtered["count"], 1)
        self.assertEqual(filtered["cookies"], [self.cookie("new")])

    def test_event_endpoint_does_not_insert_a_duplicate_event(self):
        request = EventCreateRequest(
            event_type=EventType.COOKIE_CAPTURED,
            payload=self.cookie("same"),
        )

        first = asyncio.run(
            create_event(
                self.campaign.id,
                self.victim.id,
                request,
                self.db,
                True,
            )
        )
        duplicate = asyncio.run(
            create_event(
                self.campaign.id,
                self.victim.id,
                request,
                self.db,
                True,
            )
        )

        self.assertIsNotNone(first["event_id"])
        self.assertTrue(duplicate["duplicate"])
        self.assertIsNone(duplicate["event_id"])
        self.assertEqual(
            self.db.query(VictimEvent)
            .filter(VictimEvent.event_type == EventType.COOKIE_CAPTURED)
            .count(),
            1,
        )
        self.assertEqual(self.db.query(CapturedCookie).count(), 1)
