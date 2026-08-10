"""Fail-closed validation for secrets loaded into the admin backend."""

from __future__ import annotations

import os
from collections.abc import Mapping


PLACEHOLDER_MARKERS = (
    "change-me",
    "changeme",
    "replace-with",
    "example",
)


def validate_runtime_security(environment: Mapping[str, str] | None = None) -> None:
    values = os.environ if environment is None else environment
    errors: list[str] = []

    runtime_environment = values.get("ENVIRONMENT", "")
    if runtime_environment not in {"development", "production"}:
        errors.append("ENVIRONMENT must be development or production")

    for name, minimum_length in (
        ("INTERNAL_API_KEY", 32),
        ("DATA_ENCRYPTION_KEY", 32),
        ("ADMIN_PASSWORD", 16),
    ):
        value = values.get(name, "")
        lowered = value.lower()
        if len(value) < minimum_length:
            errors.append(f"{name} must contain at least {minimum_length} characters")
        elif any(marker in lowered for marker in PLACEHOLDER_MARKERS):
            errors.append(f"{name} still contains a placeholder value")

    if not values.get("ADMIN_USERNAME", "").strip():
        errors.append("ADMIN_USERNAME is required")

    if errors:
        raise RuntimeError("Unsafe runtime configuration: " + "; ".join(errors))
