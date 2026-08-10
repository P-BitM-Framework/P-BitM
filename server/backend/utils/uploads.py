from __future__ import annotations

import os
from pathlib import PurePath

from fastapi import UploadFile


DEFAULT_UPLOAD_LIMIT_BYTES = 10 * 1024 * 1024


class UploadValidationError(ValueError):
    pass


def configured_upload_limit(
    env_name: str = "MAX_UPLOAD_BYTES",
    default: int = DEFAULT_UPLOAD_LIMIT_BYTES,
) -> int:
    raw_value = os.getenv(env_name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{env_name} must be greater than zero")
    return value


def validate_transfer_filename(filename: str | None) -> str:
    if not filename:
        raise UploadValidationError("A filename is required")
    if len(filename.encode("utf-8")) > 255:
        raise UploadValidationError("Filename is too long")
    if filename in {".", ".."} or PurePath(filename).name != filename:
        raise UploadValidationError("Filename must not contain a path")
    if any(character in filename for character in ("/", "\\", "|", "\0")):
        raise UploadValidationError("Filename contains unsupported characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in filename):
        raise UploadValidationError("Filename contains control characters")
    return filename


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise UploadValidationError(
            f"File exceeds the maximum size of {max_bytes} bytes"
        )
    return content
