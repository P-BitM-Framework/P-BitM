from __future__ import annotations

import io
import os
import secrets
import shutil
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Callable, Iterable

from utils.export_files import ExportLimitError


MAX_ARCHIVE_MEMBERS = 100_000
TAR_STREAM_OVERHEAD_BYTES = 64 * 1024 * 1024

ArchiveMemberFilter = Callable[[str], bool]
ArchiveMemberTransform = Callable[[str, BinaryIO, BinaryIO], None]


class _BoundedIteratorReader(io.RawIOBase):
    """Expose Docker's chunk iterator as a bounded, sequential binary stream."""

    def __init__(self, chunks: Iterable[bytes], max_bytes: int) -> None:
        super().__init__()
        self._chunks = iter(chunks)
        self._pending = memoryview(b"")
        self._max_bytes = max_bytes
        self._bytes_received = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        target = memoryview(buffer).cast("B")
        written = 0

        while written < len(target):
            if not self._pending:
                try:
                    chunk = next(self._chunks)
                except StopIteration:
                    break
                if not isinstance(chunk, (bytes, bytearray, memoryview)):
                    raise ExportLimitError("Docker returned an invalid archive stream")
                self._bytes_received += len(chunk)
                if self._bytes_received > self._max_bytes:
                    raise ExportLimitError(
                        "Firefox archive stream exceeds the maximum allowed size"
                    )
                self._pending = memoryview(chunk)

            copied = min(len(target) - written, len(self._pending))
            target[written:written + copied] = self._pending[:copied]
            self._pending = self._pending[copied:]
            written += copied

        return written

    def close(self) -> None:
        close = getattr(self._chunks, "close", None)
        if callable(close):
            close()
        super().close()


def _safe_archive_name(name: str) -> str:
    if (
        not name
        or "\\" in name
        or "\0" in name
        or any(ord(character) < 32 for character in name)
    ):
        raise ExportLimitError("Firefox archive contains an invalid path")

    normalized = name.removeprefix("./").rstrip("/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ExportLimitError("Firefox archive contains an unsafe path")
    return path.as_posix()


def read_single_file_from_tar(
    stream: Iterable[bytes],
    *,
    max_file_bytes: int,
) -> bytes:
    """Read one regular file from a bounded Docker archive stream."""
    if max_file_bytes <= 0:
        raise ValueError("max_file_bytes must be positive")

    archive_limit = max_file_bytes + TAR_STREAM_OVERHEAD_BYTES
    raw_reader = _BoundedIteratorReader(stream, archive_limit)
    buffered_reader = io.BufferedReader(raw_reader, buffer_size=1024 * 1024)
    member_count = 0
    file_count = 0
    contents: bytes | None = None
    try:
        with tarfile.open(fileobj=buffered_reader, mode="r|*") as tar_archive:
            for member in tar_archive:
                member_count += 1
                if member_count > MAX_ARCHIVE_MEMBERS:
                    raise ExportLimitError("Docker archive contains too many entries")
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ExportLimitError("Docker archive contains a non-regular file")

                _safe_archive_name(member.name)
                file_count += 1
                if file_count > 1:
                    raise ExportLimitError("Docker archive contains multiple files")
                if member.size > max_file_bytes:
                    raise ExportLimitError(
                        "Docker archive file exceeds the allowed size"
                    )

                source = tar_archive.extractfile(member)
                if source is None:
                    raise ExportLimitError("Docker archive contains an unreadable file")
                with source:
                    contents = source.read(max_file_bytes + 1)
                if len(contents) != member.size or len(contents) > max_file_bytes:
                    raise ExportLimitError(
                        "Docker archive file could not be read safely"
                    )

        if file_count != 1 or contents is None:
            raise ExportLimitError("Docker archive does not contain one regular file")
        return contents
    except (tarfile.TarError, OSError) as exc:
        raise ExportLimitError("Docker archive could not be read") from exc
    finally:
        buffered_reader.close()


def convert_tar_to_zip(
    stream: Iterable[bytes],
    destination: Path,
    *,
    max_uncompressed_bytes: int,
    member_filter: ArchiveMemberFilter | None = None,
    member_transform: ArchiveMemberTransform | None = None,
) -> int:
    """
    Convert a Docker tar stream to a ZIP without buffering either archive in RAM.

    The ZIP is written atomically and the returned size is the compressed file
    size used by the surrounding export budget.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_name(
        f".{destination.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    )
    archive_limit = max_uncompressed_bytes + TAR_STREAM_OVERHEAD_BYTES
    total_uncompressed = 0
    member_count = 0

    raw_reader = _BoundedIteratorReader(stream, archive_limit)
    buffered_reader = io.BufferedReader(raw_reader, buffer_size=1024 * 1024)
    try:
        with tarfile.open(fileobj=buffered_reader, mode="r|*") as tar_archive:
            with zipfile.ZipFile(
                temporary_destination,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True,
            ) as zip_archive:
                for member in tar_archive:
                    member_count += 1
                    if member_count > MAX_ARCHIVE_MEMBERS:
                        raise ExportLimitError(
                            "Firefox archive contains too many entries"
                        )
                    if member.isdir():
                        continue
                    if not member.isfile():
                        # A live Firefox profile contains transient lock
                        # symlinks. Never dereference archive links or special
                        # entries; omit them because they are not profile data
                        # and ZIP has no safe portable representation for them.
                        continue

                    total_uncompressed += member.size
                    if total_uncompressed > max_uncompressed_bytes:
                        raise ExportLimitError(
                            "Firefox profile exceeds the maximum export size"
                        )

                    archive_name = _safe_archive_name(member.name)
                    if (
                        member_filter is not None
                        and not member_filter(archive_name)
                    ):
                        continue

                    source = tar_archive.extractfile(member)
                    if source is None:
                        raise ExportLimitError(
                            "Firefox archive contains an unreadable file"
                        )
                    with source, zip_archive.open(archive_name, mode="w") as target:
                        if member_transform is None:
                            shutil.copyfileobj(source, target, length=1024 * 1024)
                        else:
                            member_transform(archive_name, source, target)

        temporary_destination.replace(destination)
        return destination.stat().st_size
    except (tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
        raise ExportLimitError("Firefox archive could not be converted") from exc
    finally:
        buffered_reader.close()
        temporary_destination.unlink(missing_ok=True)
