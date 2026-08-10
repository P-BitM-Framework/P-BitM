"""Pure authorization policy helpers."""


VALID_USER_ROLES = frozenset({"admin", "operator"})
MANAGER_ROLES = VALID_USER_ROLES


def can_manage_resources(user) -> bool:
    return user.role in MANAGER_ROLES


def can_access_campaign(user, campaign) -> bool:
    """Admins can access every campaign; operators only their own."""
    if user.role not in VALID_USER_ROLES:
        return False
    return user.is_admin() or campaign.created_by == user.id
