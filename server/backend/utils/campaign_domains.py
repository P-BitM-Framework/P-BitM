"""Public-domain ownership rules shared by campaign lifecycle services."""

from datetime import datetime, time, timezone

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from models import Campaign, CampaignStatus


DOMAIN_OWNER_STATUSES = (
    CampaignStatus.active,
    CampaignStatus.paused,
)


def find_public_domain_conflict(
    db: Session,
    public_url: str,
    *,
    scheduled_start: datetime | None = None,
    scheduled_end: datetime | None = None,
    exclude_campaign_id: str | None = None,
) -> Campaign | None:
    """Return a campaign that owns or overlaps a reservation for the domain."""
    if (scheduled_start is None) != (scheduled_end is None):
        raise ValueError("Both scheduled_start and scheduled_end are required")

    conflicting_status = Campaign.status.in_(DOMAIN_OWNER_STATUSES)
    if scheduled_start is not None and scheduled_end is not None:
        candidate_first_day = datetime.combine(
            scheduled_start.astimezone(timezone.utc).date(),
            time.min,
            tzinfo=timezone.utc,
        )
        candidate_last_day = datetime.combine(
            scheduled_end.astimezone(timezone.utc).date(),
            time.max,
            tzinfo=timezone.utc,
        )
        conflicting_status = or_(
            conflicting_status,
            and_(
                Campaign.status == CampaignStatus.scheduled,
                Campaign.scheduled_start <= candidate_last_day,
                Campaign.scheduled_end >= candidate_first_day,
            ),
        )

    query = db.query(Campaign).filter(
        func.lower(Campaign.public_url) == public_url.lower(),
        Campaign.deleted_at == None,
        conflicting_status,
    )
    if exclude_campaign_id is not None:
        query = query.filter(Campaign.id != exclude_campaign_id)
    return query.first()
