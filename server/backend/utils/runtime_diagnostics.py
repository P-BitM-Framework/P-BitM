"""Bounded, sanitized diagnostics for app-owned Docker workloads."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import docker


logger = logging.getLogger(__name__)

MAX_DIAGNOSTIC_BYTES = 8 * 1024
_SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    (?P<key>
        authorization|api[_-]?key|cookie|master[_-]?token|
        session[_-]?token|bootstrap[_-]?token|password|secret
    )
    (?P<separator>['"]?\s*[:=]\s*['"]?)
    (?P<value>[^,'"\s}\]]+)
    """
)


def sanitize_runtime_text(value: str) -> str:
    """Remove credential-like assignments from diagnostic output."""
    return _SECRET_ASSIGNMENT.sub(
        lambda match: (
            f"{match.group('key')}{match.group('separator')}[REDACTED]"
        ),
        value,
    )


def classify_startup_failure(logs: str, exit_code: int | None) -> str:
    lowered = logs.lower()
    if "s6-overlay-suexec" in lowered and "pid 1" in lowered:
        return "S6_INIT_NOT_PID1"
    if "address already in use" in lowered:
        return "PORT_ALREADY_IN_USE"
    if "no space left on device" in lowered:
        return "STORAGE_FULL"
    if "out of memory" in lowered or exit_code == 137:
        return "OUT_OF_MEMORY"
    if "permission denied" in lowered:
        return "PERMISSION_DENIED"
    return "CONTAINER_START_FAILED"


@dataclass(frozen=True)
class RuntimeDiagnostic:
    error_code: str
    status: str
    exit_code: int | None
    logs: str

    def summary(self) -> str:
        fields = [
            f"code={self.error_code}",
            f"status={self.status}",
        ]
        if self.exit_code is not None:
            fields.append(f"exit_code={self.exit_code}")
        if self.logs:
            fields.append(f"logs={self.logs}")
        return "; ".join(fields)


class RuntimeStartupError(RuntimeError):
    def __init__(self, workload: str, diagnostic: RuntimeDiagnostic):
        self.workload = workload
        self.diagnostic = diagnostic
        super().__init__(
            f"{workload} runtime startup failed: {diagnostic.summary()}"
        )


def inspect_container_failure(container) -> RuntimeDiagnostic:
    """Collect diagnostics before a failed container is removed."""
    status = "unknown"
    exit_code: int | None = None
    logs = ""
    try:
        container.reload()
        status = container.status or "unknown"
        state = container.attrs.get("State") or {}
        raw_exit_code = state.get("ExitCode")
        if isinstance(raw_exit_code, int):
            exit_code = raw_exit_code
    except docker.errors.NotFound:
        status = "removed"
        logger.debug(
            "Container %s disappeared while collecting failure diagnostics",
            getattr(container, "name", "?"),
        )
    except docker.errors.DockerException as exc:
        status = "unavailable"
        logger.debug(
            "Could not reload container %s while collecting diagnostics: %s",
            getattr(container, "name", "?"),
            exc,
        )

    try:
        raw_logs = container.logs(
            stdout=True,
            stderr=True,
            tail=120,
        )
        if isinstance(raw_logs, bytes):
            raw_logs = raw_logs.decode("utf-8", errors="replace")
        logs = sanitize_runtime_text(str(raw_logs))[-MAX_DIAGNOSTIC_BYTES:]
    except docker.errors.DockerException as exc:
        logs = ""
        logger.debug(
            "Could not fetch logs from container %s while diagnosing its "
            "failure: %s",
            getattr(container, "name", "?"),
            exc,
        )

    return RuntimeDiagnostic(
        error_code=classify_startup_failure(logs, exit_code),
        status=status,
        exit_code=exit_code,
        logs=logs,
    )
