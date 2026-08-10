import io
import json
import os
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from utils.plugin_files import (
    MAX_PLUGIN_FILE_BYTES,
    PluginFileValidationError,
    normalize_plugin_file_path,
    read_plugin_archive,
    resolve_plugin_destination,
    validate_plugin_files,
)


class PluginPathTests(unittest.TestCase):
    def test_nested_relative_path_is_allowed(self):
        self.assertEqual(
            normalize_plugin_file_path("icons/toolbar/icon.svg"),
            "icons/toolbar/icon.svg",
        )

    def test_unsafe_paths_are_rejected(self):
        unsafe_paths = [
            "",
            ".",
            "..",
            "../manifest.json",
            "icons/../../manifest.json",
            "/etc/passwd",
            "C:/Windows/file.txt",
            r"icons\icon.svg",
            "icons//icon.svg",
            "icons/./icon.svg",
            "icons/",
            " padded.js",
            "padded.js ",
            "bad\x00name.js",
        ]

        for path in unsafe_paths:
            with self.subTest(path=path):
                with self.assertRaises(PluginFileValidationError):
                    normalize_plugin_file_path(path)

    def test_duplicate_paths_are_rejected(self):
        with self.assertRaises(PluginFileValidationError):
            validate_plugin_files(
                [
                    {"name": "manifest.json", "content": "{}"},
                    {"name": "manifest.json", "content": "{}"},
                ]
            )

    def test_large_file_is_rejected(self):
        with self.assertRaises(PluginFileValidationError):
            validate_plugin_files(
                [
                    {
                        "name": "background.js",
                        "content": "a" * (MAX_PLUGIN_FILE_BYTES + 1),
                    }
                ]
            )

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as base_dir, tempfile.TemporaryDirectory() as outside:
            base = Path(base_dir)
            os.symlink(outside, base / "icons")

            with self.assertRaises(PluginFileValidationError):
                resolve_plugin_destination(base, "icons/icon.svg")


class PluginArchiveTests(unittest.TestCase):
    def _archive(self, entries):
        buffer = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, content, external_attr in entries:
                    if external_attr is None:
                        archive.writestr(name, content)
                    else:
                        info = zipfile.ZipInfo(name)
                        info.external_attr = external_attr
                        archive.writestr(info, content)
        buffer.seek(0)
        return zipfile.ZipFile(buffer, "r")

    def test_valid_archive_with_nested_file(self):
        archive = self._archive(
            [
                (
                    "plugin.json",
                    json.dumps({"name": "Test", "description": "Description"}),
                    None,
                ),
                ("files/manifest.json", "{}", None),
                ("files/icons/icon.svg", "<svg></svg>", None),
            ]
        )
        with archive:
            metadata, files = read_plugin_archive(archive)

        self.assertEqual(metadata["name"], "Test")
        self.assertEqual(
            [file["name"] for file in files],
            ["manifest.json", "icons/icon.svg"],
        )

    def test_archive_traversal_is_rejected(self):
        archive = self._archive(
            [
                ("plugin.json", '{"name":"Test"}', None),
                ("files/../../escape.js", "bad", None),
            ]
        )
        with archive, self.assertRaises(PluginFileValidationError):
            read_plugin_archive(archive)

    def test_archive_directory_traversal_is_rejected(self):
        archive = self._archive(
            [
                ("plugin.json", '{"name":"Test"}', None),
                ("files/../../", b"", None),
            ]
        )
        with archive, self.assertRaises(PluginFileValidationError):
            read_plugin_archive(archive)

    def test_duplicate_entries_are_rejected(self):
        archive = self._archive(
            [
                ("plugin.json", '{"name":"Test"}', None),
                ("files/background.js", "one", None),
                ("files/background.js", "two", None),
            ]
        )
        with archive, self.assertRaises(PluginFileValidationError):
            read_plugin_archive(archive)

    def test_symlink_entry_is_rejected(self):
        symlink_mode = (0o120777 << 16)
        archive = self._archive(
            [
                ("plugin.json", '{"name":"Test"}', None),
                ("files/link", "../../escape", symlink_mode),
            ]
        )
        with archive, self.assertRaises(PluginFileValidationError):
            read_plugin_archive(archive)

    def test_unexpected_root_file_is_rejected(self):
        archive = self._archive(
            [
                ("plugin.json", '{"name":"Test"}', None),
                ("escape.js", "bad", None),
            ]
        )
        with archive, self.assertRaises(PluginFileValidationError):
            read_plugin_archive(archive)

    def test_non_utf8_file_is_rejected(self):
        archive = self._archive(
            [
                ("plugin.json", '{"name":"Test"}', None),
                ("files/image.bin", b"\xff\xfe", None),
            ]
        )
        with archive, self.assertRaises(PluginFileValidationError):
            read_plugin_archive(archive)


if __name__ == "__main__":
    unittest.main()
