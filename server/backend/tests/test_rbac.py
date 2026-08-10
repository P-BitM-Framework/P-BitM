import unittest
from types import SimpleNamespace

from utils.permissions import can_access_campaign, can_manage_resources


def user(user_id: str, role: str):
    return SimpleNamespace(
        id=user_id,
        role=role,
        is_admin=lambda: role == "admin",
    )


class CampaignAccessTests(unittest.TestCase):
    def test_admin_can_access_another_users_campaign(self):
        campaign = SimpleNamespace(created_by="owner")
        self.assertTrue(can_access_campaign(user("admin", "admin"), campaign))

    def test_operator_can_only_access_owned_campaign(self):
        owned = SimpleNamespace(created_by="operator")
        foreign = SimpleNamespace(created_by="someone-else")

        self.assertTrue(can_access_campaign(user("operator", "operator"), owned))
        self.assertFalse(can_access_campaign(user("operator", "operator"), foreign))

    def test_removed_viewer_role_cannot_read_campaigns(self):
        owned = SimpleNamespace(created_by="viewer")
        foreign = SimpleNamespace(created_by="someone-else")

        self.assertFalse(can_access_campaign(user("viewer", "viewer"), owned))
        self.assertFalse(can_access_campaign(user("viewer", "viewer"), foreign))


class RolePolicyTests(unittest.TestCase):
    def test_admin_and_operator_can_mutate_resources(self):
        self.assertTrue(can_manage_resources(user("admin", "admin")))
        self.assertTrue(can_manage_resources(user("operator", "operator")))

    def test_removed_viewer_role_cannot_mutate_resources(self):
        self.assertFalse(can_manage_resources(user("viewer", "viewer")))


if __name__ == "__main__":
    unittest.main()
