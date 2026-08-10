import io
import os
import struct
import tarfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("INTERNAL_API_KEY", "i" * 32)

from utils.victim_containers import (
    VICTIM_CLIPBOARD_ENV,
    _wait_for_victim_service,
    capture_victim_screenshot,
)


class FakeContainer:
    def __init__(self, exit_codes, status="running"):
        self.exit_codes = iter(exit_codes)
        self.status = status
        self.attempts = 0

    def reload(self):
        return None

    def exec_run(self, command):
        self.attempts += 1
        exit_code = next(self.exit_codes)
        return SimpleNamespace(exit_code=exit_code, output=b"not ready")


class VictimReadinessTests(unittest.TestCase):
    def test_victim_clipboard_is_enabled_in_both_directions(self):
        self.assertEqual(
            VICTIM_CLIPBOARD_ENV,
            {
                "SELKIES_CLIPBOARD_ENABLED": "true",
                "SELKIES_CLIPBOARD_IN_ENABLED": "true",
                "SELKIES_CLIPBOARD_OUT_ENABLED": "true",
            },
        )

    def test_waits_until_http_endpoint_is_ready(self):
        container = FakeContainer([7, 7, 0])

        _wait_for_victim_service(
            container,
            8443,
            timeout_seconds=1,
            poll_seconds=0,
        )

        self.assertEqual(container.attempts, 3)

    def test_fails_immediately_when_container_stops(self):
        container = FakeContainer([], status="exited")

        with self.assertRaisesRegex(
            RuntimeError,
            "stopped during startup",
        ):
            _wait_for_victim_service(
                container,
                8443,
                timeout_seconds=1,
                poll_seconds=0,
            )


class VictimScreenshotTests(unittest.TestCase):
    @staticmethod
    def _png(width=1920, height=1080):
        return (
            b"\x89PNG\r\n\x1a\n"
            + b"\x00\x00\x00\rIHDR"
            + struct.pack(">II", width, height)
            + b"\x08\x06\x00\x00\x00"
        )

    @staticmethod
    def _archive(filename, content):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            member = tarfile.TarInfo(filename)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        return stream.getvalue()

    def test_captures_scoped_selkies_desktop(self):
        content = self._png()
        container = MagicMock()
        container.labels = {
            "bitm.campaign.id": "campaign",
            "bitm.victim.id": "victim",
            "bitm.role": "victim",
        }
        container.status = "running"
        container.exec_run.side_effect = [
            SimpleNamespace(exit_code=0, output=b""),
            SimpleNamespace(exit_code=0, output=b""),
        ]
        container.get_archive.return_value = (
            [self._archive("capture.png", content)],
            {"size": len(content)},
        )
        client = MagicMock()
        client.containers.get.return_value = container
        campaign = SimpleNamespace(
            id="campaign",
            container_name="p-bitm-campaign",
            protocol="selkies",
        )

        with patch(
            "utils.victim_containers.get_docker_client",
            return_value=client,
        ):
            screenshot = capture_victim_screenshot(campaign, "victim")

        self.assertEqual(screenshot.content, content)
        self.assertEqual((screenshot.width, screenshot.height), (1920, 1080))
        capture_call = container.exec_run.call_args_list[0]
        self.assertEqual(capture_call.kwargs["user"], "abc")
        self.assertEqual(
            capture_call.kwargs["environment"],
            {"DISPLAY": ":1"},
        )

    def test_rejects_container_outside_victim_scope(self):
        container = MagicMock()
        container.labels = {
            "bitm.campaign.id": "another-campaign",
            "bitm.victim.id": "victim",
            "bitm.role": "victim",
        }
        client = MagicMock()
        client.containers.get.return_value = container
        campaign = SimpleNamespace(
            id="campaign",
            container_name="p-bitm-campaign",
            protocol="selkies",
        )

        with patch(
            "utils.victim_containers.get_docker_client",
            return_value=client,
        ):
            with self.assertRaisesRegex(RuntimeError, "outside victim scope"):
                capture_victim_screenshot(campaign, "victim")


if __name__ == "__main__":
    unittest.main()
