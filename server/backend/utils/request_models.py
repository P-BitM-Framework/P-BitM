from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    field_validator,
    model_validator,
)

from models.victim_event import EventType
from utils.artifact_files import normalize_artifact_path
from utils.network import valid_url


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


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SelkiesOptions(StrictRequestModel):
    use_streaming_mode: bool = True
    use_paint_over_quality: bool = True
    video_quality: Literal["low", "medium", "high"] = "medium"
    framerate: Literal["low", "medium", "high"] = "medium"
    compression_level: Literal["low", "medium", "high"] = "medium"


class CampaignAdvancedOptions(StrictRequestModel):
    protocol: Literal["selkies", "vnc"] = "selkies"
    selkies: SelkiesOptions = Field(default_factory=SelkiesOptions)
    tracking_parameter: str | None = Field(
        default=None,
        max_length=32,
        pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,31}$",
    )

    @field_validator("tracking_parameter")
    @classmethod
    def normalize_tracking_parameter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CampaignCreateRequest(StrictRequestModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    url: str = Field(min_length=1, max_length=2048)
    public_domain: str | None = Field(default=None, max_length=253)
    campaign_type: Literal["full", "standalone"] = "full"
    smtp_profile_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    email_template_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    landing_page_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    target_list_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    plugin_ids: list[
        str
    ] = Field(default_factory=list, max_length=128)
    module_ids: list[
        str
    ] = Field(default_factory=list, max_length=128)
    launch_type: Literal["immediate", "scheduled"] = "immediate"
    scheduled_date: str | None = Field(default=None, max_length=64)
    scheduled_date_end: str | None = Field(default=None, max_length=64)
    advanced_options: CampaignAdvancedOptions = Field(
        default_factory=CampaignAdvancedOptions
    )

    @field_validator("name", "description", "url", "public_domain")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def validate_target_url(cls, value: str) -> str:
        if not valid_url(value):
            raise ValueError("url must be a safe HTTP or HTTPS URL")
        return value

    @field_validator("plugin_ids", "module_ids")
    @classmethod
    def validate_identifier_list(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Duplicate identifiers are not allowed")
        for value in values:
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 128
                or not all(character.isalnum() or character in "_-" for character in value)
            ):
                raise ValueError("Invalid identifier")
        return values


class VictimContainerRequest(StrictRequestModel):
    user_agent: str = Field(default="unknown", max_length=1024)
    theme: Literal["light", "dark", "unknown"] = "light"


class VictimCreateRequest(StrictRequestModel):
    id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    victim_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    ip_address: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=1024)


class VictimStatusRequest(StrictRequestModel):
    status: Literal["active", "inactive", "disconnected"]
    last_seen: str | None = Field(default=None, max_length=64)


class CollectedInfoRequest(RootModel[dict[str, Any]]):
    @field_validator("root")
    @classmethod
    def validate_root(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_size(value, MAX_METADATA_BYTES, "collected_info")


class EventCreateRequest(StrictRequestModel):
    event_type: EventType
    timestamp: datetime | None = None
    url: str | None = Field(default=None, max_length=2048)
    hostname: str | None = Field(default=None, max_length=253)
    title: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=4096)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type", mode="before")
    @classmethod
    def parse_event_type(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                return EventType(value)
            except ValueError:
                return value
        return value

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        return value

    @field_validator("timestamp")
    @classmethod
    def require_timestamp_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("timestamp must include a timezone")
        return value

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_size(value, MAX_METADATA_BYTES, "payload")


class DataCollectionRequest(StrictRequestModel):
    data_type: str = Field(
        min_length=1,
        max_length=64,
        pattern=DATA_TYPE_PATTERN,
    )
    file_path: str | None = Field(default=None, max_length=512)
    module_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    file_size_bytes: int = Field(default=0, ge=0, le=512 * 1024 * 1024)
    collected_at: datetime | None = None
    extra_metadata: dict[str, Any] | None = None

    @field_validator("collected_at", mode="before")
    @classmethod
    def parse_collected_at(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        return value

    @field_validator("collected_at")
    @classmethod
    def require_collection_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("collected_at must include a timezone")
        return value

    @field_validator("extra_metadata")
    @classmethod
    def validate_metadata(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if value is not None:
            ensure_json_size(value, MAX_METADATA_BYTES, "extra_metadata")
        return value

    @model_validator(mode="after")
    def validate_file_contract(self):
        if self.file_path is not None:
            self.file_path = normalize_artifact_path(self.file_path)
        elif self.data_type != "module_data":
            raise ValueError("file_path is required for this data type")
        if self.data_type == "module_data" and not self.module_id:
            raise ValueError("module_id is required for module_data")
        return self


class CommandRequest(StrictRequestModel):
    command: str = Field(min_length=1, max_length=MAX_OPERATION_PAYLOAD_BYTES)


class CampaignModuleRequest(StrictRequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    category: str = Field(default="Custom", min_length=1, max_length=80)
    icon: str | None = Field(default=None, max_length=1024 * 1024)
    inputs: list[Any] = Field(default_factory=list, max_length=64)
    payload: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_OPERATION_PAYLOAD_BYTES,
    )
    payload_js: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_OPERATION_PAYLOAD_BYTES,
    )
    link: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_aliases(self):
        if not (self.name or self.title):
            raise ValueError("name is required")
        if not (self.payload or self.payload_js):
            raise ValueError("payload is required")
        ensure_json_size(self.inputs, MAX_METADATA_BYTES, "inputs")
        return self


class ModuleExecutionRequest(StrictRequestModel):
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


class TrackingEventRequest(StrictRequestModel):
    tracking_id: str = Field(min_length=1, max_length=128)
    campaign_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=IDENTIFIER_PATTERN,
    )
    ip_address: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=1024)
    submitted_data: dict[str, Any] | None = None

    @field_validator("submitted_data")
    @classmethod
    def validate_submitted_data(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if value is not None:
            ensure_json_size(value, MAX_METADATA_BYTES, "submitted_data")
        return value
