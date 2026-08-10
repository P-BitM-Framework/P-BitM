import io
import tempfile
import unittest
from pathlib import Path

from fastapi import UploadFile

from core.uploads import (
    UploadValidationError,
    read_upload_limited,
    resolve_local_file,
    validate_transfer_filename,
)


class CampaignUploadValidationTests(unittest.IsolatedAsyncioTestCase):
    def test_rejects_websocket_message_delimiter(self):
        with self.assertRaises(UploadValidationError):
            validate_transfer_filename("invoice|payload.pdf")

    def test_rejects_relative_path(self):
        with self.assertRaises(UploadValidationError):
            validate_transfer_filename("../invoice.pdf")

    async def test_reads_only_up_to_the_configured_limit(self):
        upload = UploadFile(
            filename="invoice.pdf",
            file=io.BytesIO(b"1234"),
        )

        with self.assertRaises(UploadValidationError):
            await read_upload_limited(upload, 3)

    def test_resolves_collected_file_inside_storage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            artifact = root / "invoice.pdf"
            artifact.write_bytes(b"original")

            self.assertEqual(
                resolve_local_file(root, "invoice.pdf"),
                artifact.resolve(),
            )

    def test_rejects_collected_file_symlink(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target.pdf"
            target.write_bytes(b"original")
            link = root / "invoice.pdf"
            link.symlink_to(target)

            with self.assertRaises(UploadValidationError):
                resolve_local_file(root, "invoice.pdf")
