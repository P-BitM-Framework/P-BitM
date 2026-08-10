import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


KEYLOGGER_PATH = (
    Path(__file__).resolve().parents[1]
    / "bitm-images"
    / "common"
    / "keylogger"
    / "keylogger.py"
)
SPEC = importlib.util.spec_from_file_location("bitm_keylogger", KEYLOGGER_PATH)
keylogger = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = keylogger
SPEC.loader.exec_module(keylogger)


class FakeSyncWorker:
    def __init__(self):
        self.payloads = []

    def submit(self, payload):
        self.payloads.append(payload)


class FakeKeyEnum:
    space = object()
    enter = object()
    tab = object()
    backspace = object()


class FakeKey:
    def __init__(self, *, char=None, name=None):
        self.char = char
        self.name = name


class KeyloggerTests(unittest.TestCase):
    def test_buffer_restore_preserves_order(self):
        buffer = keylogger.KeyBuffer(timestamp_seconds=60)
        buffer.append("first")
        drained = buffer.drain()
        buffer.append("second")
        buffer.restore(drained)

        self.assertEqual(buffer.drain(), "firstsecond")

    def test_key_conversion_does_not_stop_on_escape(self):
        self.assertEqual(
            keylogger.key_to_text(FakeKey(char="è"), FakeKeyEnum),
            "è",
        )
        self.assertEqual(
            keylogger.key_to_text(FakeKeyEnum.backspace, FakeKeyEnum),
            "[BACKSPACE]",
        )
        self.assertEqual(
            keylogger.key_to_text(FakeKey(name="esc"), FakeKeyEnum),
            "[ESC]",
        )

    def test_modifier_and_control_keys_are_ignored(self):
        for name in ("alt", "alt_l", "shift", "shift_r", "ctrl", "cmd"):
            with self.subTest(name=name):
                self.assertEqual(
                    keylogger.key_to_text(FakeKey(name=name), FakeKeyEnum),
                    "",
                )
        self.assertEqual(
            keylogger.key_to_text(FakeKey(char="\x01"), FakeKeyEnum),
            "",
        )

    def test_remote_metadata_url_is_rejected(self):
        environment = {
            "CAMPAIGN_ID": "campaign_1",
            "VICTIM_ID": "victim_1",
            "CAMPAIGN_API_URL": "https://example.com",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(RuntimeError):
                keylogger.load_config()

    def test_flush_writes_utf8_and_submits_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            sync_worker = FakeSyncWorker()
            config = keylogger.Config(
                storage_path=Path(temporary_directory),
                campaign_api_url="http://127.0.0.1:8080",
                campaign_id="campaign_1",
                victim_id="victim_1",
                flush_seconds=5,
                timestamp_seconds=60,
                max_file_bytes=1024,
            )
            recorder = keylogger.KeylogRecorder(config, sync_worker)
            recorder.initialize()
            recorder.record("città")

            self.assertTrue(recorder.flush())
            self.assertIn("città", config.log_file.read_text(encoding="utf-8"))
            self.assertEqual(
                sync_worker.payloads[-1]["file_path"],
                "keylogs.txt",
            )
            self.assertEqual(config.log_file.stat().st_mode & 0o777, 0o644)

    def test_current_file_stays_bounded_and_previous_file_is_retained(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            sync_worker = FakeSyncWorker()
            config = keylogger.Config(
                storage_path=Path(temporary_directory),
                campaign_api_url="http://127.0.0.1:8080",
                campaign_id="campaign_1",
                victim_id="victim_1",
                flush_seconds=5,
                timestamp_seconds=60,
                max_file_bytes=96,
            )
            recorder = keylogger.KeylogRecorder(config, sync_worker)
            recorder.initialize()
            recorder.record("à" * 60)
            recorder.flush()

            self.assertLessEqual(config.log_file.stat().st_size, 96)
            self.assertTrue(config.archive_file.is_file())


if __name__ == "__main__":
    unittest.main()
