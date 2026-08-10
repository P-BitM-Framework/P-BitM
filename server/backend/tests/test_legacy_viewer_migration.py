import os
import unittest

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "A-secure-initial-password-123")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")

from database import Base, SessionLocal, engine, init_db
from models.campaign import Campaign, CampaignStatus
from models.user import User


class LegacyViewerMigrationTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        init_db()

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def test_deletes_viewer_and_reassigns_owned_campaigns(self):
        db = SessionLocal()
        try:
            legacy_viewer = User(
                id="viewer1",
                username="legacy-viewer",
                email="legacy-viewer@example.com",
                password="unused",
                role="viewer",
                is_active=True,
            )
            campaign = Campaign(
                id="campaign1",
                name="Legacy campaign",
                status=CampaignStatus.active,
                target_url="https://example.com",
                plugin_ids=[],
                module_ids=[],
                created_by=legacy_viewer.id,
            )
            db.add_all([legacy_viewer, campaign])
            db.commit()
        finally:
            db.close()

        init_db()

        db = SessionLocal()
        try:
            admin = db.query(User).filter(
                User.username == os.environ["ADMIN_USERNAME"]
            ).one()
            campaign = db.query(Campaign).filter(Campaign.id == "campaign1").one()

            self.assertEqual(
                db.query(User).filter(User.role == "viewer").count(),
                0,
            )
            self.assertEqual(campaign.created_by, admin.id)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
