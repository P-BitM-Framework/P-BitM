"""Shared dependencies and helpers for the campaign route modules."""

from __future__ import annotations

import os
import asyncio
import uuid
import json
import logging
import base64
import re
import secrets
import tempfile
import shutil
from fastapi import APIRouter, HTTPException, Depends, Request, status, Query, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from models.landing_page import LandingPage
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timezone, timedelta
from typing import Optional
import docker
import httpx
from pathlib import Path
from urllib.parse import urlparse
from starlette.background import BackgroundTask

from database import get_db
from models import Campaign, Victim, User, VictimEvent, DataCollection, CampaignStatus
from models.victim_event import EventType
from models.victim import VictimStatus
from models.target import Target
from models.target_list import TargetList
from models.email_template import EmailTemplate
from models.sending_profile import SMTPProfile
from models.module import Module
from models.plugin import Plugin
from routes.auth import (
    get_current_user_from_session,
    require_campaign_read_access,
    require_campaign_write_access,
    require_operator,
    verify_campaign_internal_key,
    verify_internal_key_or_campaign_reader,
)
from utils.docker import (
    CampaignRuntimeStateError,
    copy_file_to_container,
    get_docker_client,
    remove_related_containers,
    set_campaign_runtime_paused,
)
from utils.campaign import dump_firefox_data, get_selkies_env, create_campaign_victims
from utils.network import find_free_port, valid_url
from utils.client_ip import normalize_ip_address
from utils.storage import setup_campaign_storage, get_host_campaign_storage_path
from utils.artifact_files import (
    normalize_artifact_path,
    read_file_tail_bounded,
    resolve_artifact_file,
    safe_campaign_directory_name,
)
from utils.landing_page import process_landing_page
from utils.internal_auth import derive_campaign_api_key
from utils.public_routes import build_public_access_url, derive_entry_path
from utils.campaign_networks import (
    connect_container_to_campaign_network,
    remove_campaign_egress_network,
    remove_campaign_network,
)
from utils.egress_proxy import create_campaign_egress_proxy
from utils.plugin_files import (
    PluginFileValidationError,
    resolve_plugin_destination,
    validate_plugin_files,
)
from utils.export_files import (
    ExportLimitError,
    configured_export_limit,
    copy_tree_bounded,
)
from utils.uploads import (
    UploadValidationError,
    configured_upload_limit,
    read_upload_limited,
    validate_transfer_filename,
)
from utils.request_models import (
    CampaignCreateRequest,
    CampaignModuleRequest,
    CollectedInfoRequest,
    CommandRequest,
    DataCollectionRequest,
    EventCreateRequest,
    ModuleExecutionRequest,
    VictimContainerRequest,
    VictimCreateRequest,
    VictimStatusRequest,
)
from utils.runtime_diagnostics import RuntimeStartupError
from utils.victim_containers import (
    GlobalCapacityError,
    capture_victim_screenshot as capture_admin_owned_victim_screenshot,
    create_victim_container as create_admin_owned_victim_container,
    destroy_victim_container as destroy_admin_owned_victim_container,
    dump_victim_container as dump_admin_owned_victim_container,
)

logger = logging.getLogger(__name__)
# Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "server_bitm-network")
CAMPAIGN_IMAGE = os.getenv("CAMPAIGN_IMAGE", "p-bitm:latest")
STORAGE_PATH = os.getenv("STORAGE_PATH", "/storage")
MODE = "default" if ENVIRONMENT == "development" else "kiosk"
MAX_WEBCAM_PROXY_BODY_BYTES = 256 * 1024
MAX_WEBCAM_PROXY_RESPONSE_BYTES = 2 * 1024 * 1024
WEBCAM_PROXY_METHODS = {
    "request-offer": "POST",
    "send-answer": "POST",
    "ice-candidate": "POST",
    "ice-candidates": "GET",
    "stop": "POST",
    "status": "GET",
}
WEBCAM_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
INTERACTIVE_IP_METADATA_KEY = "interactive_ip_address"


def _apply_interactive_client_metadata(
    victim: Victim,
    event_type: EventType,
    payload: dict,
) -> None:
    if event_type != EventType.VICTIM_CONNECTED:
        return

    client_ip = normalize_ip_address(payload.get("ip_address"))
    if not client_ip:
        return

    metadata = dict(victim.extra_metadata or {})
    metadata[INTERACTIVE_IP_METADATA_KEY] = client_ip
    victim.extra_metadata = metadata
    victim.ip_address = client_ip

    user_agent = payload.get("user_agent")
    if isinstance(user_agent, str) and user_agent:
        victim.user_agent = user_agent[:1024]


def _merge_collected_metadata(victim: Victim, collected: dict) -> None:
    metadata = dict(collected)
    interactive_ip = (victim.extra_metadata or {}).get(
        INTERACTIVE_IP_METADATA_KEY
    )
    if interactive_ip:
        metadata[INTERACTIVE_IP_METADATA_KEY] = interactive_ip
    victim.extra_metadata = metadata


def _serialize_screenshot(
    screenshot: DataCollection,
    campaign_id: str,
    victim_id: str,
) -> dict:
    metadata = screenshot.extra_metadata or {}
    return {
        "id": screenshot.id,
        "name": os.path.basename(screenshot.file_path),
        "file_path": screenshot.file_path,
        "size_bytes": screenshot.file_size_bytes or 0,
        "size_mb": round(
            (screenshot.file_size_bytes or 0) / (1024 * 1024),
            2,
        ),
        "collected_at": screenshot.collected_at,
        "resolution": metadata.get("resolution"),
        "download_url": (
            f"/api/campaigns/{campaign_id}/victims/{victim_id}"
            f"/files/{screenshot.file_path}"
        ),
    }


PUBLIC_HOST_LABEL = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def campaign_internal_headers(campaign_id: str) -> dict[str, str]:
    return {
        "X-Internal-API-Key": derive_campaign_api_key(
            INTERNAL_API_KEY,
            campaign_id,
        )
    }


def normalize_public_domain(value: str | None) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise HTTPException(400, "public_domain must be a hostname")

    candidate = value.strip()
    if not candidate:
        return ""

    if "://" in candidate:
        parsed = urlparse(candidate)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise HTTPException(400, "public_domain must contain only a hostname")
        try:
            if parsed.port is not None:
                raise HTTPException(400, "public_domain must not include a port")
        except ValueError as exc:
            raise HTTPException(400, "public_domain contains an invalid port") from exc
        candidate = parsed.hostname
    else:
        candidate = candidate.rstrip("/")
        if any(character in candidate for character in "/?#@:"):
            raise HTTPException(400, "public_domain must contain only a hostname")

    candidate = candidate.rstrip(".").lower()
    try:
        candidate = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise HTTPException(400, "public_domain is not a valid hostname") from exc

    if (
        not candidate
        or len(candidate) > 253
        or any(
            not PUBLIC_HOST_LABEL.fullmatch(label)
            for label in candidate.split(".")
        )
    ):
        raise HTTPException(400, "public_domain is not a valid hostname")

    return candidate


def build_campaign_public_url(campaign_id: str, public_domain: str | None = None) -> str:
    if ENVIRONMENT != "production":
        ip = os.environ.get("IP", "127.0.0.1")
        return f"https://{ip}/{campaign_id}/"

    domain = normalize_public_domain(public_domain)
    if not domain:
        raise HTTPException(400, "public_domain required in production")

    return f"https://{domain}/"


def parse_schedule_datetime(value: object, field_name: str) -> datetime | None:
    """Parse an explicit timezone-aware ISO-8601 campaign timestamp."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise HTTPException(400, f"{field_name} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            400,
            f"Invalid {field_name} format. Use ISO 8601 format.",
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(
            400,
            f"{field_name} must include a timezone offset",
        )
    return parsed.astimezone(timezone.utc)


def resolve_campaign_schedule(
    data: dict,
    campaign_type: str,
    now: datetime,
) -> tuple[datetime | None, datetime | None, CampaignStatus]:
    """Validate launch_type and return one unambiguous campaign schedule."""
    launch_type = data.get("launch_type", "immediate")
    raw_start = data.get("scheduled_date")
    raw_end = data.get("scheduled_date_end")

    if campaign_type == "standalone":
        if launch_type != "immediate" or raw_start or raw_end:
            raise HTTPException(
                400,
                "Standalone campaigns must launch immediately",
            )
        return None, None, CampaignStatus.active

    if launch_type == "immediate":
        if raw_start or raw_end:
            raise HTTPException(
                400,
                "Immediate campaigns must not include scheduled dates",
            )
        return None, None, CampaignStatus.active

    scheduled_start = parse_schedule_datetime(
        raw_start,
        "scheduled_date",
    )
    scheduled_end = parse_schedule_datetime(
        raw_end,
        "scheduled_date_end",
    )
    if scheduled_start is None or scheduled_end is None:
        raise HTTPException(
            400,
            "Scheduled campaigns require both start and end dates",
        )
    if scheduled_start <= now:
        raise HTTPException(400, "scheduled_date must be in the future")
    if scheduled_end <= scheduled_start:
        raise HTTPException(
            400,
            "scheduled_date_end must be later than scheduled_date",
        )
    return scheduled_start, scheduled_end, CampaignStatus.scheduled


def remove_campaign_runtime(container_name: str, campaign_id: str) -> None:
    """Remove campaign workloads first, then their isolated network."""
    remove_related_containers(container_name, campaign_id)
    remove_campaign_egress_network(campaign_id)
    remove_campaign_network(campaign_id)
