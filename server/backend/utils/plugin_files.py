"""Validation and safe filesystem handling for editable browser-extension files."""

from __future__ import annotations

import json
import stat
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


MAX_PLUGIN_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_PLUGIN_FILES = 128
MAX_PLUGIN_FILE_BYTES = 2 * 1024 * 1024
MAX_PLUGIN_TOTAL_BYTES = 10 * 1024 * 1024
MAX_PLUGIN_METADATA_BYTES = 64 * 1024
MAX_PLUGIN_PATH_LENGTH = 240
MAX_PLUGIN_PATH_SEGMENT_LENGTH = 128
MAX_PLUGIN_ARCHIVE_MEMBERS = 512
MAX_PLUGIN_NAME_LENGTH = 120
MAX_PLUGIN_DESCRIPTION_LENGTH = 4_000


class PluginFileValidationError(ValueError):
    """Raised when a plugin file collection or archive is unsafe."""


def normalize_plugin_file_path(name: str) -> str:
    if not isinstance(name, str):
        raise PluginFileValidationError("Plugin file name must be a string")

    normalized = unicodedata.normalize("NFC", name)
    if not normalized or normalized != normalized.strip():
        raise PluginFileValidationError("Plugin file path is empty or padded")
    if len(normalized) > MAX_PLUGIN_PATH_LENGTH:
        raise PluginFileValidationError("Plugin file path is too long")
    if len(normalized.encode("utf-8")) > 1_024:
        raise PluginFileValidationError("Plugin file path is too long")
    if "\\" in normalized or "\x00" in normalized:
        raise PluginFileValidationError("Plugin file path contains invalid characters")
    if any(ord(character) < 32 for character in normalized):
        raise PluginFileValidationError("Plugin file path contains control characters")
    if normalized.startswith("/") or normalized.endswith("/") or "//" in normalized:
        raise PluginFileValidationError("Plugin file path must be a relative file path")

    raw_parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise PluginFileValidationError("Plugin file path contains unsafe segments")
    if any(len(part) > MAX_PLUGIN_PATH_SEGMENT_LENGTH for part in raw_parts):
        raise PluginFileValidationError("Plugin file path segment is too long")
    if any(len(part.encode("utf-8")) > 255 for part in raw_parts):
        raise PluginFileValidationError("Plugin file path segment is too long")
    if len(raw_parts[0]) >= 2 and raw_parts[0][1] == ":":
        raise PluginFileValidationError("Windows drive paths are not allowed")

    path = PurePosixPath(normalized)
    if path.is_absolute() or str(path) != normalized:
        raise PluginFileValidationError("Plugin file path is not canonical")

    return normalized


def validate_plugin_files(files: Any) -> list[dict[str, str]]:
    if not isinstance(files, list):
        raise PluginFileValidationError("Plugin files must be a list")
    if len(files) > MAX_PLUGIN_FILES:
        raise PluginFileValidationError(
            f"A plugin can contain at most {MAX_PLUGIN_FILES} files"
        )

    validated: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    total_size = 0

    for item in files:
        if not isinstance(item, dict):
            raise PluginFileValidationError("Each plugin file must be an object")

        name = normalize_plugin_file_path(item.get("name"))
        content = item.get("content")
        if not isinstance(content, str):
            raise PluginFileValidationError(
                f"Plugin file '{name}' content must be UTF-8 text"
            )
        if name in seen_paths:
            raise PluginFileValidationError(f"Duplicate plugin file path: {name}")

        content_size = len(content.encode("utf-8"))
        if content_size > MAX_PLUGIN_FILE_BYTES:
            raise PluginFileValidationError(
                f"Plugin file '{name}' exceeds the per-file size limit"
            )
        total_size += content_size
        if total_size > MAX_PLUGIN_TOTAL_BYTES:
            raise PluginFileValidationError("Plugin files exceed the total size limit")

        seen_paths.add(name)
        validated.append({"name": name, "content": content})

    return validated


def resolve_plugin_destination(plugin_dir: Path, name: str) -> Path:
    normalized = normalize_plugin_file_path(name)
    base = plugin_dir.resolve()
    destination = base.joinpath(*PurePosixPath(normalized).parts)
    resolved_destination = destination.resolve(strict=False)

    try:
        resolved_destination.relative_to(base)
    except ValueError as exc:
        raise PluginFileValidationError(
            "Plugin file path escapes its storage directory"
        ) from exc

    return resolved_destination


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def _validate_plugin_metadata(metadata: Any) -> dict[str, str]:
    if not isinstance(metadata, dict):
        raise PluginFileValidationError("plugin.json must contain a JSON object")

    name = metadata.get("name", "Imported Plugin")
    description = metadata.get("description", "")
    if not isinstance(name, str) or not name.strip():
        raise PluginFileValidationError("Plugin name must be a non-empty string")
    if len(name) > MAX_PLUGIN_NAME_LENGTH:
        raise PluginFileValidationError("Plugin name is too long")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise PluginFileValidationError("Plugin description must be a string")
    if len(description) > MAX_PLUGIN_DESCRIPTION_LENGTH:
        raise PluginFileValidationError("Plugin description is too long")

    return {"name": name.strip(), "description": description}


def read_plugin_archive(archive: zipfile.ZipFile) -> tuple[dict[str, str], list[dict[str, str]]]:
    infos = archive.infolist()
    if len(infos) > MAX_PLUGIN_ARCHIVE_MEMBERS:
        raise PluginFileValidationError("Plugin archive contains too many entries")

    member_names: set[str] = set()
    file_entries: list[zipfile.ZipInfo] = []
    metadata_info: zipfile.ZipInfo | None = None
    total_uncompressed_size = 0

    for info in infos:
        if info.filename in member_names:
            raise PluginFileValidationError(
                f"Duplicate ZIP entry: {info.filename}"
            )
        member_names.add(info.filename)

        if info.flag_bits & 0x1:
            raise PluginFileValidationError("Encrypted ZIP entries are not supported")
        if _is_symlink(info):
            raise PluginFileValidationError("ZIP symlinks are not allowed")
        if info.is_dir():
            directory_name = info.filename.rstrip("/")
            if directory_name == "files":
                continue
            if not directory_name.startswith("files/"):
                raise PluginFileValidationError(
                    f"Unexpected directory in plugin archive: {info.filename}"
                )
            normalize_plugin_file_path(directory_name[len("files/") :])
            continue

        if info.filename == "plugin.json":
            metadata_info = info
            continue

        if not info.filename.startswith("files/"):
            raise PluginFileValidationError(
                f"Unexpected file in plugin archive: {info.filename}"
            )

        relative_name = info.filename[len("files/") :]
        normalize_plugin_file_path(relative_name)
        if info.file_size > MAX_PLUGIN_FILE_BYTES:
            raise PluginFileValidationError(
                f"Plugin file '{relative_name}' exceeds the per-file size limit"
            )

        total_uncompressed_size += info.file_size
        if total_uncompressed_size > MAX_PLUGIN_TOTAL_BYTES:
            raise PluginFileValidationError(
                "Plugin archive exceeds the uncompressed size limit"
            )
        file_entries.append(info)

    if metadata_info is None:
        raise PluginFileValidationError("Plugin archive is missing plugin.json")
    if metadata_info.file_size > MAX_PLUGIN_METADATA_BYTES:
        raise PluginFileValidationError("plugin.json exceeds the size limit")
    if len(file_entries) > MAX_PLUGIN_FILES:
        raise PluginFileValidationError(
            f"A plugin can contain at most {MAX_PLUGIN_FILES} files"
        )

    try:
        metadata = json.loads(archive.read(metadata_info).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PluginFileValidationError("plugin.json is not valid UTF-8 JSON") from exc

    files: list[dict[str, str]] = []
    for info in file_entries:
        relative_name = info.filename[len("files/") :]
        try:
            content = archive.read(info).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PluginFileValidationError(
                f"Plugin file '{relative_name}' is not UTF-8 text"
            ) from exc
        files.append({"name": relative_name, "content": content})

    return _validate_plugin_metadata(metadata), validate_plugin_files(files)
