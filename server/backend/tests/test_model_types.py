import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models  # noqa: F401 - register every ORM model before creating tables
from database import Base
from models.campaign import Campaign
from models.plugin import Plugin


class DatabaseTypeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)

    def test_json_columns_round_trip_native_values(self):
        campaign = Campaign(
            id="campaign",
            name="Campaign",
            target_url="https://example.com",
            plugin_ids=["plugin"],
            module_ids=["module"],
            selkies_config={"video_quality": "high"},
            advanced_options={"protocol": "selkies"},
        )
        plugin = Plugin(
            id="plugin",
            name="Plugin",
            files=[{"name": "manifest.json", "content": "{}"}],
        )

        with self.Session() as db:
            db.add_all([campaign, plugin])
            db.commit()
            db.expire_all()

            persisted_campaign = db.get(Campaign, "campaign")
            persisted_plugin = db.get(Plugin, "plugin")

            self.assertEqual(persisted_campaign.plugin_ids, ["plugin"])
            self.assertEqual(
                persisted_campaign.selkies_config,
                {"video_quality": "high"},
            )
            self.assertEqual(
                persisted_plugin.files[0]["name"],
                "manifest.json",
            )

    def test_timestamps_round_trip_as_aware_utc(self):
        campaign = Campaign(
            id="campaign",
            name="Campaign",
            target_url="https://example.com",
        )

        with self.Session() as db:
            db.add(campaign)
            db.commit()
            db.expire_all()

            persisted = db.get(Campaign, "campaign")
            self.assertIsNotNone(persisted.created_at.tzinfo)
            self.assertEqual(
                persisted.created_at.utcoffset(),
                timezone.utc.utcoffset(persisted.created_at),
            )

    def test_naive_timestamps_are_rejected(self):
        campaign = Campaign(
            id="campaign",
            name="Campaign",
            target_url="https://example.com",
            started_at=datetime.now(),
        )

        with self.Session() as db:
            db.add(campaign)
            with self.assertRaises(StatementError):
                db.commit()


if __name__ == "__main__":
    unittest.main()
