import io
import os
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi import UploadFile

from utils.export_files import ExportLimitError, copy_tree_bounded
from utils.files import convert_tar_to_zip
from utils.uploads import (
    UploadValidationError,
    read_upload_limited,
    validate_transfer_filename,
)


class UploadValidationTests(unittest.IsolatedAsyncioTestCase):
    def test_accepts_a_plain_filename(self):
        self.assertEqual(
            validate_transfer_filename("report final.pdf"),
            "report final.pdf",
        )

    def test_rejects_paths_and_protocol_delimiters(self):
        for filename in (
            "../report.pdf",
            "folder/report.pdf",
            r"folder\report.pdf",
            "report|payload.pdf",
            "report\n.pdf",
        ):
            with self.subTest(filename=filename):
                with self.assertRaises(UploadValidationError):
                    validate_transfer_filename(filename)

    async def test_rejects_an_upload_over_the_limit(self):
        upload = UploadFile(
            filename="payload.bin",
            file=io.BytesIO(b"12345"),
        )

        with self.assertRaises(UploadValidationError):
            await read_upload_limited(upload, 4)


class BoundedExportTests(unittest.TestCase):
    def test_copies_regular_nested_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source"
            destination = root / "destination"
            (source / "nested").mkdir(parents=True)
            (source / "nested" / "artifact.txt").write_text(
                "artifact",
                encoding="utf-8",
            )

            copied_bytes = copy_tree_bounded(
                source,
                destination,
                max_bytes=100,
            )

            self.assertEqual(copied_bytes, len("artifact"))
            self.assertEqual(
                (destination / "nested" / "artifact.txt").read_text(
                    encoding="utf-8"
                ),
                "artifact",
            )

    def test_rejects_files_over_the_total_limit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source"
            source.mkdir()
            (source / "artifact.bin").write_bytes(b"12345")

            with self.assertRaises(ExportLimitError):
                copy_tree_bounded(
                    source,
                    root / "destination",
                    max_bytes=4,
                )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_rejects_symbolic_links(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source"
            source.mkdir()
            outside = root / "outside.txt"
            outside.write_text("secret", encoding="utf-8")
            (source / "artifact.txt").symlink_to(outside)

            with self.assertRaises(ExportLimitError):
                copy_tree_bounded(
                    source,
                    root / "destination",
                    max_bytes=100,
                )

    def test_streams_tar_members_to_a_zip_file(self):
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
            payload = b"firefox-profile"
            member = tarfile.TarInfo("bitm-profile/storage/default.txt")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))

        chunks = [
            tar_buffer.getvalue()[offset:offset + 17]
            for offset in range(0, len(tar_buffer.getvalue()), 17)
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "profile.zip"

            zip_size = convert_tar_to_zip(
                iter(chunks),
                destination,
                max_uncompressed_bytes=1024,
            )

            self.assertEqual(zip_size, destination.stat().st_size)
            with zipfile.ZipFile(destination) as archive:
                self.assertEqual(
                    archive.read("bitm-profile/storage/default.txt"),
                    payload,
                )

    def test_rejects_tar_content_over_the_uncompressed_limit(self):
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
            payload = b"12345"
            member = tarfile.TarInfo("bitm-profile/large.bin")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "profile.zip"

            with self.assertRaises(ExportLimitError):
                convert_tar_to_zip(
                    iter([tar_buffer.getvalue()]),
                    destination,
                    max_uncompressed_bytes=4,
                )
            self.assertFalse(destination.exists())

    def test_skips_live_firefox_lock_symlinks_without_dereferencing_them(self):
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
            lock = tarfile.TarInfo("bitm-profile/lock")
            lock.type = tarfile.SYMTYPE
            lock.linkname = "/outside/profile"
            archive.addfile(lock)

            payload = b"session-data"
            member = tarfile.TarInfo("bitm-profile/sessionstore.jsonlz4")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "profile.zip"

            convert_tar_to_zip(
                iter([tar_buffer.getvalue()]),
                destination,
                max_uncompressed_bytes=1024,
            )

            with zipfile.ZipFile(destination) as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["bitm-profile/sessionstore.jsonlz4"],
                )
                self.assertEqual(
                    archive.read("bitm-profile/sessionstore.jsonlz4"),
                    payload,
                )
