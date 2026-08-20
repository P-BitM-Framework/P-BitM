from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import secrets
import uuid

from models.victim import VictimStatus, Victim
from utils.docker import get_container
from utils.export_files import configured_export_limit
from utils.files import convert_tar_to_zip
from sqlalchemy.orm import Session

APP_DIR = "/bitm/app"
FIREFOX_PROFILE_DIRS = {
    "selkies": "/config/.mozilla/firefox/bitm-profile",
    "vnc": "/bitm/.mozilla/firefox/bitm-profile",
}

logger = logging.getLogger(__name__)

SELKIES_QUALITY_MAP = {
    "video_quality": {
        "low": {
            "h264_paintover_crf": 25,
        },
        "medium": {
            "h264_paintover_crf": 20,
        },
        "high": {
            "h264_paintover_crf": 15,
        }
    },
    "framerate": {
        "low": 30,
        "medium": 60,
        "high": 120
    },
    "compression_level": {
        "low": 25,    # More compressed
        "medium": 20, # Balanced
        "high": 15    # Less compressed (better quality)
    }
}

def get_selkies_env(config: dict) -> dict:
    """Convert dashboard quality presets to Selkies environment variables."""
    selkies = config.get("selkies", {})
    quality = selkies.get("video_quality", "medium")
    quality_settings = SELKIES_QUALITY_MAP["video_quality"][quality]
    framerate_value = SELKIES_QUALITY_MAP["framerate"][
        selkies.get("framerate", "medium")
    ]
    compression = SELKIES_QUALITY_MAP["compression_level"][
        selkies.get("compression_level", "medium")
    ]

    return {
        "SELKIES_ENABLE_STREAMING": (
            "true" if selkies.get("use_streaming_mode") else "false"
        ),
        "SELKIES_ENABLE_PAINTOVER": (
            "true" if selkies.get("use_paint_over_quality") else "false"
        ),
        "SELKIES_H264_CRF": str(compression),
        "SELKIES_H264_PAINTOVER_CRF": str(
            quality_settings["h264_paintover_crf"]
        ),
        "SELKIES_FRAMERATE": str(framerate_value),
    }

async def dump_firefox_data(
    container_name: str,
    destination: Path,
    *,
    protocol: str,
    max_bytes: int | None = None,
) -> int | None:
    """Write a bounded Firefox profile ZIP and return its compressed size."""
    container = get_container(container_name)
    try:
        firefox_profile_dir = FIREFOX_PROFILE_DIRS[protocol]
    except KeyError as exc:
        raise ValueError(f"Unsupported victim protocol: {protocol}") from exc
    exec_result = container.exec_run(
        f"test -d {firefox_profile_dir}",
        stdout=False,
        stderr=False,
    )
    if exec_result.exit_code != 0:
        raise Exception("Firefox profile directory not found")
    stream, _stat = container.get_archive(firefox_profile_dir)
    return convert_tar_to_zip(
        stream,
        destination,
        max_uncompressed_bytes=max_bytes or configured_export_limit(),
    )


def create_campaign_victims(
    db: Session,
    campaign_id: str,
    targets: Sequence,
    scheduled_date: datetime | None = None,
    scheduled_date_end: datetime | None = None,
    company: str | None = None,
) -> int:
    """Add scheduled victims to the caller-owned database transaction."""
    total_targets = len(targets)
    if total_targets == 0:
        return 0

    start_time = scheduled_date or datetime.now(timezone.utc)
    interval_seconds = 0.0
    if scheduled_date_end and total_targets > 1:
        duration_seconds = (scheduled_date_end - start_time).total_seconds()
        if duration_seconds > 0:
            # scheduled_end closes the email-delivery window; it is not the
            # campaign lifetime. The final recipient is scheduled strictly
            # before the boundary so all sends fit inside the selected window.
            interval_seconds = duration_seconds / total_targets

    for index, target in enumerate(targets):
        if interval_seconds > 0:
            offset_seconds = int(index * interval_seconds)
            scheduled_send = start_time + timedelta(seconds=offset_seconds)
        else:
            scheduled_send = start_time

        victim = Victim(
            id=str(uuid.uuid4())[:8],
            campaign_id=campaign_id,
            email=target.email,
            first_name=target.first_name,
            last_name=target.last_name,
            company=company,
            tracking_id=secrets.token_urlsafe(16),
            status=VictimStatus.pending,
            scheduled_send_at=scheduled_send,
            created_at=datetime.now(timezone.utc),
        )
        db.add(victim)

    return total_targets
