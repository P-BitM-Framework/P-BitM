"""Validated runtime identity passed to dynamically created containers."""

import os


MAX_RUNTIME_ID = 2_147_483_647


def _runtime_id(variable: str) -> str:
    value = os.getenv(variable, "1000")
    if not value.isdecimal():
        raise RuntimeError(f"{variable} must be a positive integer")
    parsed = int(value, 10)
    if parsed <= 0 or parsed > MAX_RUNTIME_ID:
        raise RuntimeError(
            f"{variable} must be between 1 and {MAX_RUNTIME_ID}"
        )
    return str(parsed)


def runtime_identity_environment(*, linuxserver: bool = False) -> dict[str, str]:
    """Return the selected IDs, including LinuxServer's conventional names."""
    uid = _runtime_id("PBITM_UID")
    gid = _runtime_id("PBITM_GID")
    environment = {"PBITM_UID": uid, "PBITM_GID": gid}
    if linuxserver:
        environment.update({"PUID": uid, "PGID": gid})
    return environment
