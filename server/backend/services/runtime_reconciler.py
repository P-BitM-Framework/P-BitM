"""Conservative reconciliation for app-owned Docker campaign resources."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from models import Campaign, CampaignStatus
from utils.campaign_networks import (
    CAMPAIGN_ID_PATTERN,
    remove_campaign_egress_network,
    remove_campaign_network,
)
from utils.docker import (
    get_docker_client,
    remove_related_containers,
    set_campaign_runtime_paused,
    set_campaign_runtime_started,
)


logger = logging.getLogger(__name__)
ORPHAN_GRACE = timedelta(
    minutes=int(os.getenv("RUNTIME_ORPHAN_GRACE_MINUTES", "30"))
)


def _created_at(resource) -> datetime | None:
    raw_value = resource.attrs.get("Created")
    if not isinstance(raw_value, str):
        return None
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _past_grace(resource, now: datetime) -> bool:
    created_at = _created_at(resource)
    if created_at is None:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return now - created_at >= ORPHAN_GRACE


def remove_campaign_runtime(container_name: str, campaign_id: str) -> None:
    """Remove all app-owned workloads and the private network for a campaign."""
    remove_related_containers(container_name, campaign_id)
    remove_campaign_egress_network(campaign_id)
    remove_campaign_network(campaign_id)


def reconcile_campaign_runtime() -> None:
    """
    Remove terminal runtimes and stale app-owned resources with no DB row.

    Unknown resources are never touched. Orphans receive a grace period so a
    campaign being provisioned cannot race the scheduled reconciler.
    """
    db = SessionLocal()
    try:
        campaigns = db.query(Campaign).all()
        known_campaign_ids = {campaign.id for campaign in campaigns}
        terminal_campaigns = [
            campaign
            for campaign in campaigns
            if (
                campaign.deleted_at is not None
                or campaign.status == CampaignStatus.completed
            )
            and campaign.container_status != "stopped"
        ]
    finally:
        db.close()

    for campaign in terminal_campaigns:
        if not campaign.container_name:
            continue
        try:
            remove_campaign_runtime(campaign.container_name, campaign.id)
            update_db = SessionLocal()
            try:
                persisted = update_db.query(Campaign).filter(
                    Campaign.id == campaign.id
                ).first()
                if persisted is not None:
                    persisted.container_status = "stopped"
                    update_db.commit()
            finally:
                update_db.close()
        except Exception:
            logger.exception(
                "Runtime reconciliation failed for terminal campaign %s",
                campaign.id,
            )

    paused_campaigns = [
        campaign
        for campaign in campaigns
        if (
            campaign.deleted_at is None
            and campaign.status == CampaignStatus.paused
            and campaign.container_name
        )
    ]
    for campaign in paused_campaigns:
        try:
            set_campaign_runtime_paused(
                campaign.container_name,
                campaign.id,
                True,
            )
            update_db = SessionLocal()
            try:
                persisted = update_db.query(Campaign).filter(
                    Campaign.id == campaign.id
                ).first()
                if (
                    persisted is not None
                    and persisted.status == CampaignStatus.paused
                ):
                    persisted.container_status = "paused"
                    update_db.commit()
            finally:
                update_db.close()
        except Exception:
            # Catch broadly, not just CampaignRuntimeStateError: a Docker
            # error class or a failed update_db.commit() above must not
            # abort reconciliation of the remaining campaigns in this pass.
            logger.exception(
                "Runtime reconciliation failed for paused campaign %s",
                campaign.id,
            )

    scheduled_campaigns = [
        campaign
        for campaign in campaigns
        if (
            campaign.deleted_at is None
            and campaign.status == CampaignStatus.scheduled
            and campaign.container_name
        )
    ]
    for campaign in scheduled_campaigns:
        try:
            set_campaign_runtime_started(
                campaign.container_name,
                campaign.id,
                False,
            )
            update_db = SessionLocal()
            try:
                persisted = update_db.query(Campaign).filter(
                    Campaign.id == campaign.id
                ).first()
                if (
                    persisted is not None
                    and persisted.status == CampaignStatus.scheduled
                    and persisted.container_status != "start_failed"
                ):
                    persisted.container_status = "scheduled"
                    update_db.commit()
            finally:
                update_db.close()
        except Exception:
            # Catch broadly, not just CampaignRuntimeStateError: a Docker
            # error class or a failed update_db.commit() above must not
            # abort reconciliation of the remaining campaigns in this pass.
            logger.exception(
                "Runtime reconciliation failed for scheduled campaign %s",
                campaign.id,
            )

    starting_campaigns = [
        campaign
        for campaign in campaigns
        if (
            campaign.deleted_at is None
            and campaign.status == CampaignStatus.active
            and campaign.container_status == "starting"
            and campaign.container_name
        )
    ]
    for campaign in starting_campaigns:
        try:
            set_campaign_runtime_started(
                campaign.container_name,
                campaign.id,
                True,
            )
            update_db = SessionLocal()
            try:
                persisted = update_db.query(Campaign).filter(
                    Campaign.id == campaign.id
                ).first()
                if (
                    persisted is not None
                    and persisted.status == CampaignStatus.active
                    and persisted.container_status == "starting"
                ):
                    persisted.container_status = "running"
                    update_db.commit()
            finally:
                update_db.close()
        except Exception:
            # Catch broadly, not just CampaignRuntimeStateError: a Docker
            # error class or a failed update_db.commit() above must not
            # abort reconciliation of the remaining campaigns in this pass.
            logger.exception(
                "Runtime reconciliation failed for starting campaign %s",
                campaign.id,
            )

    docker_client = get_docker_client()
    now = datetime.now(timezone.utc)
    orphan_groups: dict[str, list] = {}

    for container in docker_client.containers.list(
        all=True,
        filters={"label": "bitm.campaign.id"},
    ):
        labels = container.labels or {}
        campaign_id = labels.get("bitm.campaign.id", "")
        is_owned_workload = (
            labels.get("bitm.type") == "campaign"
            or labels.get("bitm.role") == "victim"
        )
        if (
            is_owned_workload
            and CAMPAIGN_ID_PATTERN.fullmatch(campaign_id)
            and campaign_id not in known_campaign_ids
        ):
            orphan_groups.setdefault(campaign_id, []).append(container)

    for campaign_id, containers in orphan_groups.items():
        if not containers or not all(
            _past_grace(container, now) for container in containers
        ):
            continue
        campaign_container = next(
            (
                container
                for container in containers
                if (container.labels or {}).get("bitm.type") == "campaign"
            ),
            containers[0],
        )
        try:
            remove_campaign_runtime(campaign_container.name, campaign_id)
            logger.warning("Removed stale orphan runtime %s", campaign_id)
        except Exception:
            logger.exception(
                "Failed to remove stale orphan runtime %s",
                campaign_id,
            )

    for network in docker_client.networks.list(
        filters={"label": "bitm.role=campaign-private"}
    ):
        labels = network.attrs.get("Labels") or {}
        campaign_id = labels.get("bitm.campaign.id", "")
        if (
            not CAMPAIGN_ID_PATTERN.fullmatch(campaign_id)
            or campaign_id in known_campaign_ids
            or not _past_grace(network, now)
        ):
            continue
        try:
            remove_campaign_network(campaign_id)
            logger.warning("Removed stale orphan network %s", network.name)
        except Exception:
            logger.exception(
                "Failed to remove stale orphan network %s",
                network.name,
            )

    for network in docker_client.networks.list(
        filters={"label": "bitm.role=campaign-egress"}
    ):
        labels = network.attrs.get("Labels") or {}
        campaign_id = labels.get("bitm.campaign.id", "")
        if (
            not CAMPAIGN_ID_PATTERN.fullmatch(campaign_id)
            or campaign_id in known_campaign_ids
            or not _past_grace(network, now)
        ):
            continue
        try:
            remove_campaign_egress_network(campaign_id)
            logger.warning("Removed stale egress network %s", network.name)
        except Exception:
            logger.exception(
                "Failed to remove stale egress network %s",
                network.name,
            )
