import tempfile
import unittest
from pathlib import Path

from utils.artifact_files import (
    normalize_artifact_path,
    read_file_tail_bounded,
    resolve_artifact_file,
    safe_campaign_directory_name,
)


class ArtifactPathTests(unittest.TestCase):
    def test_campaign_name_cannot_create_nested_storage(self):
        directory = safe_campaign_directory_name("../../outside/name", "abc_123")
        self.assertEqual(directory, "outside-name-abc_123")
        self.assertNotIn("/", directory)

    def test_invalid_campaign_id_is_rejected(self):
        with self.assertRaises(ValueError):
            safe_campaign_directory_name("name", "../id")

    def test_normal_nested_artifact_path_is_allowed(self):
        self.assertEqual(
            normalize_artifact_path("screenshots/capture.png"),
            "screenshots/capture.png",
        )

    def test_traversal_and_absolute_paths_are_rejected(self):
        for candidate in (
            "../secret",
            "screenshots/../../secret",
            "/etc/passwd",
            r"screenshots\capture.png",
            "screenshots//capture.png",
        ):
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    normalize_artifact_path(candidate)

    def test_resolver_rejects_symlink_outside_victim_storage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            victim_root = base / "victim"
            victim_root.mkdir()
            outside = base / "outside.txt"
            outside.write_text("secret")
            (victim_root / "escape.txt").symlink_to(outside)

            with self.assertRaises(ValueError):
                resolve_artifact_file(victim_root, "escape.txt")

    def test_resolver_accepts_existing_regular_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            victim_root = Path(temporary_directory) / "victim"
            artifact = victim_root / "screenshots" / "capture.png"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"png")

            self.assertEqual(
                resolve_artifact_file(victim_root, "screenshots/capture.png"),
                artifact.resolve(),
            )

    def test_bounded_reader_returns_only_the_file_tail(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifact = Path(temporary_directory) / "keylogs.txt"
            artifact.write_bytes(b"0123456789")

            content, original_size = read_file_tail_bounded(artifact, 4)

            self.assertEqual(content, b"6789")
            self.assertEqual(original_size, 10)


if __name__ == "__main__":
    unittest.main()
