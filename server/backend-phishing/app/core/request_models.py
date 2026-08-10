from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.favicon import (
    MAX_FAVICON_CHARACTERS,
    validate_favicon_data_uri,
    validate_favicon_url,
)


IDENTIFIER_PATTERN = r"^[A-Za-z0-9_-]+$"
DATA_TYPE_PATTERN = r"^[a-z][a-z0-9_-]*$"
MAX_METADATA_BYTES = 256 * 1024
MAX_OPERATION_PAYLOAD_BYTES = 1024 * 1024


def ensure_json_size(value: Any, max_bytes: int, field_name: str) -> Any:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain JSON-compatible data") from exc
    if len(encoded) > max_bytes:
        raise ValueError(f"{field_name} exceeds {max_bytes} bytes")
    return value


def normalize_artifact_path(value: str) -> str:
    if (
        not value
        or len(value) > 512
        or "\\" in value
        or "\0" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("Invalid artifact path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or len(path.parts) > 16
        or any(
            part in {"", ".", ".."} or len(part) > 128
            for part in path.parts
        )
        or path.as_posix() != value
    ):
        raise ValueError("Invalid artifact path")
    return value


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CommandRequest(StrictRequestModel):
    command: str = Field(min_length=1, max_length=MAX_OPERATION_PAYLOAD_BYTES)


class SiteInfoRequest(StrictRequestModel):
    title: str = Field(default="", max_length=256)
    favicon: str = Field(default="", max_length=MAX_FAVICON_CHARACTERS)

    @field_validator("favicon")
    @classmethod
    def validate_favicon(cls, value: str) -> str:
        if not value or value.lower().startswith("data:"):
            return validate_favicon_data_uri(value)
        return validate_favicon_url(value)


class VictimDataRequest(StrictRequestModel):
    data_type: str = Field(
        min_length=1,
        max_length=64,
        pattern=DATA_TYPE_PATTERN,
    )
    file_path: str = Field(min_length=1, max_length=512)
    module_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    file_size_bytes: int = Field(default=0, ge=0, le=512 * 1024 * 1024)
    metadata: dict[str, Any] | None = None
    extra_metadata: dict[str, Any] | None = None

    @field_validator("file_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_artifact_path(value)

    @model_validator(mode="after")
    def validate_metadata(self):
        if self.metadata is not None and self.extra_metadata is not None:
            raise ValueError("Use only one metadata field")
        metadata = (
            self.extra_metadata
            if self.extra_metadata is not None
            else self.metadata or {}
        )
        ensure_json_size(metadata, MAX_METADATA_BYTES, "metadata")
        return self

    def normalized_metadata(self) -> dict[str, Any]:
        return (
            self.extra_metadata
            if self.extra_metadata is not None
            else self.metadata or {}
        )


class ModuleDataRequest(StrictRequestModel):
    data_type: Literal["module_data"]
    module_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    file_path: None = None

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_size(value, MAX_METADATA_BYTES, "metadata")


class EventProxyRequest(StrictRequestModel):
    event_type: Literal[
        "email_sent",
        "email_opened",
        "email_link_clicked",
        "email_bounced",
        "email_marked_spam",
        "victim_connected",
        "victim_disconnected",
        "navigation",
        "form_submission",
        "cookie_captured",
        "file_downloaded",
        "file_uploaded",
        "screenshot",
        "keylog",
        "copy_paste",
        "developer_tools_opened",
    ]
    timestamp: str | None = Field(default=None, max_length=64)
    url: str | None = Field(default=None, max_length=2048)
    hostname: str | None = Field(default=None, max_length=253)
    title: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=4096)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_size(value, MAX_METADATA_BYTES, "payload")


class ExecuteModuleRequest(StrictRequestModel):
    module_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def validate_params(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 64:
            raise ValueError("Too many module parameters")
        return ensure_json_size(value, MAX_METADATA_BYTES, "params")
