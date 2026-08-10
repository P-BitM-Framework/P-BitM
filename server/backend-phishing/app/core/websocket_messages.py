"""Validation and rate limits for messages sent by public WebSocket clients."""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ClientMessageError(ValueError):
    """Raised when a structured client message violates its contract."""


class StrictMessageModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RTCSessionDescription(StrictMessageModel):
    type: Literal["offer"]
    sdp: str = Field(min_length=1, max_length=64 * 1024)


class RTCIceCandidate(StrictMessageModel):
    candidate: str = Field(min_length=1, max_length=8 * 1024)
    sdpMid: str | None = Field(default=None, max_length=256)
    sdpMLineIndex: int | None = Field(default=None, ge=0, le=65_535)
    usernameFragment: str | None = Field(default=None, max_length=256)


class WebRTCOfferMessage(StrictMessageModel):
    type: Literal["webrtc-offer"]
    session_id: str = Field(
        min_length=20,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    offer: RTCSessionDescription


class WebRTCCandidateMessage(StrictMessageModel):
    type: Literal["webrtc-candidate"]
    session_id: str = Field(
        min_length=20,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    candidate: RTCIceCandidate


class WebcamErrorMessage(StrictMessageModel):
    type: Literal["webcam-error"]
    session_id: str = Field(
        min_length=20,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    code: Literal[
        "permission-denied",
        "device-unavailable",
        "capture-failed",
        "signaling-failed",
    ]


@dataclass(frozen=True)
class MessageDecision:
    allowed: bool
    reason: str | None = None


class WebSocketMessageLimiter:
    """Per-connection sliding-window and byte-size limiter."""

    def __init__(
        self,
        *,
        max_message_bytes: int,
        window_seconds: int,
        max_messages: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if min(max_message_bytes, window_seconds, max_messages) <= 0:
            raise ValueError("WebSocket message limits must be positive")
        self.max_message_bytes = max_message_bytes
        self.window_seconds = window_seconds
        self.max_messages = max_messages
        self._clock = clock
        self._messages: deque[float] = deque()

    def check(self, message: str) -> MessageDecision:
        if len(message.encode("utf-8")) > self.max_message_bytes:
            return MessageDecision(False, "message_too_large")

        now = self._clock()
        cutoff = now - self.window_seconds
        while self._messages and self._messages[0] <= cutoff:
            self._messages.popleft()
        if len(self._messages) >= self.max_messages:
            return MessageDecision(False, "message_rate_limit")
        self._messages.append(now)
        return MessageDecision(True)


def parse_structured_client_message(message: str) -> dict | None:
    """Validate recognized JSON messages; return None for ordinary text."""
    if not message.startswith("{"):
        return None
    try:
        data = json.loads(message)
    except json.JSONDecodeError as exc:
        raise ClientMessageError("Malformed JSON message") from exc
    if not isinstance(data, dict):
        raise ClientMessageError("JSON message must be an object")

    message_type = data.get("type")
    model_type = {
        "webrtc-offer": WebRTCOfferMessage,
        "webrtc-candidate": WebRTCCandidateMessage,
        "webcam-error": WebcamErrorMessage,
    }.get(message_type)
    if model_type is None:
        raise ClientMessageError("Unsupported JSON message type")
    try:
        return model_type.model_validate(data).model_dump()
    except ValidationError as exc:
        raise ClientMessageError("Invalid structured message") from exc


def parse_collected_info(message: str) -> dict | None:
    prefix = "[COLLECTED INFO]"
    if not message.startswith(prefix):
        return None
    try:
        data = json.loads(message[len(prefix):].strip())
    except json.JSONDecodeError as exc:
        raise ClientMessageError("Malformed collected-info JSON") from exc
    if not isinstance(data, dict):
        raise ClientMessageError("Collected info must be a JSON object")
    return data
