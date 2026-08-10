"""Safe paths for campaign storage and victim artifacts."""

import os
from pathlib import Path, PurePosixPath
import re


MAX_ARTIFACT_PATH_LENGTH = 512
MAX_ARTIFACT_SEGMENTS = 16
MAX_ARTIFACT_SEGMENT_LENGTH = 128


def safe_campaign_directory_name(campaign_name: str, campaign_id: str) -> str:
    if not campaign_id or not re.fullmatch(r"[A-Za-z0-9_-]+", campaign_id):
        raise ValueError("Invalid campaign ID")

    clean_name = re.sub(r"[^A-Za-z0-9._-]+", "-", (campaign_name or "").strip())
    clean_name = clean_name.strip(".-")[:80]
    if not clean_name:
        clean_name = "campaign"
    return f"{clean_name}-{campaign_id}"


def normalize_artifact_path(file_path: str) -> str:
    if not isinstance(file_path, str):
        raise ValueError("Artifact path must be a string")
    if not file_path or len(file_path) > MAX_ARTIFACT_PATH_LENGTH:
        raise ValueError("Invalid artifact path length")
    if "\\" in file_path or "\x00" in file_path:
        raise ValueError("Invalid artifact path")
    if any(ord(character) < 32 for character in file_path):
        raise ValueError("Invalid artifact path")

    path = PurePosixPath(file_path)
    if path.is_absolute():
        raise ValueError("Artifact path must be relative")

    parts = path.parts
    if (
        not parts
        or len(parts) > MAX_ARTIFACT_SEGMENTS
        or any(part in {"", ".", ".."} for part in parts)
        or any(len(part) > MAX_ARTIFACT_SEGMENT_LENGTH for part in parts)
    ):
        raise ValueError("Invalid artifact path")

    normalized = path.as_posix()
    if normalized != file_path:
        raise ValueError("Artifact path must be normalized")
    return normalized


def resolve_artifact_file(victim_root: Path, file_path: str) -> Path:
    normalized = normalize_artifact_path(file_path)

    try:
        resolved_root = victim_root.resolve(strict=True)
        resolved_file = (resolved_root / normalized).resolve(strict=True)
        resolved_file.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise ValueError("Artifact file is outside victim storage or does not exist") from exc

    if not resolved_file.is_file():
        raise ValueError("Artifact path is not a file")
    return resolved_file


def read_file_tail_bounded(path: Path, max_bytes: int) -> tuple[bytes, int]:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero")

    file_stat = path.stat()
    start_offset = max(0, file_stat.st_size - max_bytes)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(path, flags)
    try:
        opened_stat = os.fstat(descriptor)
        if (
            opened_stat.st_dev != file_stat.st_dev
            or opened_stat.st_ino != file_stat.st_ino
        ):
            raise ValueError("Artifact changed while being read")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            stream.seek(start_offset)
            return stream.read(max_bytes), file_stat.st_size
    finally:
        if descriptor >= 0:
            os.close(descriptor)
