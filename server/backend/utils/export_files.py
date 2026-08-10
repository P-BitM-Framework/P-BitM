from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path


DEFAULT_EXPORT_LIMIT_BYTES = 512 * 1024 * 1024


class ExportLimitError(ValueError):
    pass


def configured_export_limit() -> int:
    raw_value = os.getenv("MAX_EXPORT_BYTES")
    if raw_value is None:
        return DEFAULT_EXPORT_LIMIT_BYTES
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("MAX_EXPORT_BYTES must be an integer") from exc
    if value <= 0:
        raise RuntimeError("MAX_EXPORT_BYTES must be greater than zero")
    return value


def copy_tree_bounded(
    source: Path,
    destination: Path,
    *,
    max_bytes: int,
    initial_bytes: int = 0,
) -> int:
    if source.is_symlink():
        raise ExportLimitError("Export source is not a regular directory")
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ExportLimitError("Export source is not a regular directory")

    total_bytes = initial_bytes
    destination.mkdir(parents=True, exist_ok=True)

    for root, directories, filenames in os.walk(source, followlinks=False):
        root_path = Path(root)
        relative_root = root_path.relative_to(source)

        for directory_name in directories:
            directory_path = root_path / directory_name
            if directory_path.is_symlink():
                raise ExportLimitError("Symbolic links are not allowed in exports")
            (destination / relative_root / directory_name).mkdir(
                parents=True,
                exist_ok=True,
            )

        for filename in filenames:
            source_file = root_path / filename
            file_stat = source_file.lstat()
            if not stat.S_ISREG(file_stat.st_mode):
                raise ExportLimitError("Only regular files can be exported")

            total_bytes += file_stat.st_size
            if total_bytes > max_bytes:
                raise ExportLimitError("Export exceeds the maximum allowed size")

            destination_file = destination / relative_root / filename
            destination_file.parent.mkdir(parents=True, exist_ok=True)

            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(source_file, flags)
            try:
                opened_stat = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(opened_stat.st_mode)
                    or opened_stat.st_dev != file_stat.st_dev
                    or opened_stat.st_ino != file_stat.st_ino
                ):
                    raise ExportLimitError("Export source changed while being read")
                with os.fdopen(descriptor, "rb") as source_stream:
                    descriptor = -1
                    with destination_file.open("wb") as destination_stream:
                        shutil.copyfileobj(source_stream, destination_stream)
            finally:
                if descriptor >= 0:
                    os.close(descriptor)

    return total_bytes
