"""Resolve the unprivileged numeric identity used by P-BitM containers."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


DEFAULT_RUNTIME_UID = 1000
DEFAULT_RUNTIME_GID = 1000
MAX_RUNTIME_ID = 2_147_483_647


class RuntimeIdentityError(RuntimeError):
    """Raised when a safe non-root runtime identity cannot be selected."""


@dataclass(frozen=True)
class RuntimeIdentity:
    """Numeric identity and the host signal from which it was selected."""

    uid: int
    gid: int
    source: str

    def build_environment(self) -> dict[str, str]:
        return {
            "PBITM_UID": str(self.uid),
            "PBITM_GID": str(self.gid),
        }


def _positive_id(value: object, label: str) -> int:
    try:
        parsed = int(str(value), 10)
    except (TypeError, ValueError) as exc:
        raise RuntimeIdentityError(f"{label} must be a positive integer") from exc
    if parsed <= 0 or parsed > MAX_RUNTIME_ID:
        raise RuntimeIdentityError(
            f"{label} must be between 1 and {MAX_RUNTIME_ID}"
        )
    return parsed


def resolve_runtime_identity(
    project_root: Optional[Path] = None,
    *,
    system_name: Optional[str] = None,
    effective_uid: Optional[int] = None,
    effective_gid: Optional[int] = None,
    environment: Optional[Mapping[str, str]] = None,
) -> RuntimeIdentity:
    """Select the non-root UID/GID used for Linux bind-mounted storage.

    Docker Desktop mediates host mounts through its Linux VM, so macOS and
    other non-Linux hosts retain the image default. On Linux, a normal launch
    follows the current user; a sudo launch follows the original user; and a
    direct root launch uses a non-root repository owner or the safe default.
    """
    system_name = system_name or platform.system()
    if system_name != "Linux":
        return RuntimeIdentity(
            DEFAULT_RUNTIME_UID,
            DEFAULT_RUNTIME_GID,
            "container-default",
        )

    if effective_uid is None:
        effective_uid = getattr(os, "geteuid", lambda: DEFAULT_RUNTIME_UID)()
    if effective_gid is None:
        effective_gid = getattr(os, "getegid", lambda: DEFAULT_RUNTIME_GID)()

    if effective_uid != 0:
        return RuntimeIdentity(
            _positive_id(effective_uid, "current UID"),
            _positive_id(effective_gid, "current GID"),
            "current-user",
        )

    environment = os.environ if environment is None else environment
    sudo_uid = environment.get("SUDO_UID")
    sudo_gid = environment.get("SUDO_GID")
    if sudo_uid is not None or sudo_gid is not None:
        if sudo_uid is None or sudo_gid is None:
            raise RuntimeIdentityError(
                "SUDO_UID and SUDO_GID must either both be set or both be absent"
            )
        return RuntimeIdentity(
            _positive_id(sudo_uid, "SUDO_UID"),
            _positive_id(sudo_gid, "SUDO_GID"),
            "sudo-user",
        )

    root = (
        Path(project_root).resolve()
        if project_root is not None
        else Path(__file__).resolve().parent.parent
    )
    metadata = root.stat()
    owner_uid = getattr(metadata, "st_uid", 0)
    owner_gid = getattr(metadata, "st_gid", 0)
    if owner_uid > 0 and owner_gid > 0:
        return RuntimeIdentity(
            _positive_id(owner_uid, "repository owner UID"),
            _positive_id(owner_gid, "repository owner GID"),
            "repository-owner",
        )

    return RuntimeIdentity(
        DEFAULT_RUNTIME_UID,
        DEFAULT_RUNTIME_GID,
        "root-default",
    )


def runtime_subprocess_environment(
    identity: Optional[RuntimeIdentity] = None,
) -> dict[str, str]:
    """Return the current process environment plus Compose build identity."""
    selected = identity or resolve_runtime_identity()
    environment = os.environ.copy()
    environment.update(selected.build_environment())
    return environment
