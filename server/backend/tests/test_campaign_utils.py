import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from utils.campaign import (
    FIREFOX_POLICY_PATH,
    create_campaign_victims,
    dump_firefox_data,
    get_selkies_env,
)


def _docker_archive(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, payload in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    return buffer.getvalue()


def _extension_xpi(extension_id: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "manifest_version": 2,
                    "name": "Test extension",
                    "version": "1.0",
                    "browser_specific_settings": {
                        "gecko": {"id": extension_id},
                    },
                }
            ),
        )
    return buffer.getvalue()


class CampaignVictimCreationTests(unittest.TestCase):
    def test_distributes_send_times_across_the_full_schedule(self):
        start = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
        end = start + timedelta(minutes=20)
        targets = [
            SimpleNamespace(
                email=f"target-{index}@example.test",
                first_name="Target",
                last_name=str(index),
            )
            for index in range(3)
        ]
        db = MagicMock()

        created = create_campaign_victims(
            db,
            "campaign",
            targets,
            scheduled_date=start,
            scheduled_date_end=end,
        )

        self.assertEqual(created, 3)
        scheduled_times = [
            call.args[0].scheduled_send_at
            for call in db.add.call_args_list
        ]
        self.assertEqual(
            scheduled_times,
            [
                start,
                start + timedelta(minutes=6, seconds=40),
                start + timedelta(minutes=13, seconds=20),
            ],
        )
        self.assertTrue(all(send_time < end for send_time in scheduled_times))
        db.commit.assert_not_called()

    def test_empty_target_sequence_does_not_commit(self):
        db = MagicMock()

        created = create_campaign_victims(db, "campaign", [])

        self.assertEqual(created, 0)
        db.add.assert_not_called()
        db.commit.assert_not_called()


class SelkiesEnvironmentTests(unittest.TestCase):
    def test_maps_dashboard_quality_presets_to_environment(self):
        result = get_selkies_env(
            {
                "selkies": {
                    "use_streaming_mode": True,
                    "use_paint_over_quality": False,
                    "video_quality": "high",
                    "framerate": "low",
                    "compression_level": "medium",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "SELKIES_ENABLE_STREAMING": "true",
                "SELKIES_ENABLE_PAINTOVER": "false",
                "SELKIES_H264_CRF": "20",
                "SELKIES_H264_PAINTOVER_CRF": "15",
                "SELKIES_FRAMERATE": "30",
            },
        )


class FirefoxProfileDumpTests(unittest.IsolatedAsyncioTestCase):
    @patch(
        "utils.campaign._pbitm_developer_extension_ids",
        return_value=frozenset(),
    )
    @patch("utils.campaign.convert_tar_to_zip", return_value=123)
    @patch("utils.campaign.get_container")
    async def test_selects_the_profile_path_for_each_protocol(
        self,
        get_container,
        convert_archive,
        developer_extension_ids,
    ):
        container = MagicMock()
        container.exec_run.return_value.exit_code = 0
        container.get_archive.return_value = (iter([b"archive"]), {})
        get_container.return_value = container

        for protocol, expected_path in (
            ("selkies", "/config/.mozilla/firefox/bitm-profile"),
            ("vnc", "/bitm/.mozilla/firefox/bitm-profile"),
        ):
            with self.subTest(protocol=protocol):
                result = await dump_firefox_data(
                    "victim-container",
                    MagicMock(),
                    protocol=protocol,
                )

                self.assertEqual(result, 123)
                container.exec_run.assert_called_with(
                    f"test -d {expected_path}",
                    stdout=False,
                    stderr=False,
                )
                container.get_archive.assert_called_with(expected_path)
                developer_extension_ids.assert_called_once_with(container)
                container.reset_mock()
                convert_archive.reset_mock()
                developer_extension_ids.reset_mock()

    @patch(
        "utils.campaign._pbitm_developer_extension_ids",
        return_value=frozenset(),
    )
    @patch("utils.campaign.get_container")
    async def test_exports_browser_state_without_runtime_configuration(
        self,
        get_container,
        _developer_extension_ids,
    ):
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
            members = {
                "bitm-profile/user.js": (
                    b'user_pref("browser.startup.homepage", "https://example.test");\n'
                    b'user_pref("network.proxy.type", 1);\n'
                ),
                "bitm-profile/prefs.js": (
                    b'user_pref("network.proxy.type", 1);\n'
                    b'user_pref("browser.zoom.siteSpecific", false);\n'
                ),
                "bitm-profile/chrome/userChrome.css": (
                    b"#PanelUI-button { display: none; }\n"
                ),
                "bitm-profile/sessionstore.jsonlz4": b"session-data",
                "bitm-profile/cookies.sqlite": b"cookie-data",
                "bitm-profile/places.sqlite": b"history-data",
            }
            for name, payload in members.items():
                member = tarfile.TarInfo(name)
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))

        container = MagicMock()
        container.exec_run.return_value.exit_code = 0
        container.get_archive.return_value = (iter([tar_buffer.getvalue()]), {})
        get_container.return_value = container

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "profile.zip"

            await dump_firefox_data(
                "victim-container",
                destination,
                protocol="vnc",
            )

            with zipfile.ZipFile(destination) as archive:
                self.assertNotIn("bitm-profile/user.js", archive.namelist())
                self.assertNotIn("bitm-profile/prefs.js", archive.namelist())
                self.assertNotIn(
                    "bitm-profile/chrome/userChrome.css",
                    archive.namelist(),
                )
                self.assertEqual(
                    archive.read("bitm-profile/sessionstore.jsonlz4"),
                    b"session-data",
                )
                self.assertEqual(
                    archive.read("bitm-profile/cookies.sqlite"),
                    b"cookie-data",
                )
                self.assertEqual(
                    archive.read("bitm-profile/places.sqlite"),
                    b"history-data",
                )

    @patch("utils.campaign.get_container")
    async def test_removes_only_pbitm_developer_extensions(self, get_container):
        developer_extension_id = "developer@bitm.test"
        legitimate_extension_id = "legitimate@example.test"
        developer_extension_path = (
            "/bitm/app/bad_firefox_extensions/developer-extension.xpi"
        )
        profile_directory = "/bitm/.mozilla/firefox/bitm-profile"
        developer_extension_xpi = (
            "bitm-profile/extensions/developer@bitm.test.xpi"
        )
        legitimate_extension_xpi = (
            "bitm-profile/extensions/legitimate@example.test.xpi"
        )
        developer_extension_data = (
            "bitm-profile/browser-extension-data/developer@bitm.test/data.json"
        )
        legitimate_extension_data = (
            "bitm-profile/browser-extension-data/legitimate@example.test/data.json"
        )
        developer_extension_store = (
            "bitm-profile/extension-store/developer@bitm.test/data.json"
        )
        legitimate_extension_store = (
            "bitm-profile/extension-store/legitimate@example.test/data.json"
        )
        policy = {
            "policies": {
                "Extensions": {
                    "Install": [
                        developer_extension_path,
                        "https://example.test/legitimate-extension.xpi",
                    ],
                },
            },
        }
        profile_archive = _docker_archive(
            {
                "bitm-profile/user.js": b'user_pref("network.proxy.type", 1);\n',
                "bitm-profile/prefs.js": b'user_pref("network.proxy.type", 1);\n',
                developer_extension_xpi: b"developer",
                legitimate_extension_xpi: b"legitimate",
                developer_extension_data: b"developer-data",
                legitimate_extension_data: b"legitimate-data",
                developer_extension_store: b"developer-store",
                legitimate_extension_store: b"legitimate-store",
                "bitm-profile/addonStartup.json.lz4": b"stale-startup-cache",
                "bitm-profile/extensions.ini": b"stale-ini-cache",
                "bitm-profile/extensions.sqlite": b"stale-sqlite-cache",
                "bitm-profile/extensions.json": json.dumps(
                    {
                        "addons": [
                            {"id": developer_extension_id, "name": "P-BitM"},
                            {
                                "id": legitimate_extension_id,
                                "name": "Legitimate",
                            },
                        ],
                        "schemaVersion": 35,
                    }
                ).encode(),
                "bitm-profile/extension-preferences.json": json.dumps(
                    {
                        developer_extension_id: {"enabled": True},
                        legitimate_extension_id: {"enabled": True},
                    }
                ).encode(),
                "bitm-profile/cookies.sqlite": b"cookies",
                "bitm-profile/places.sqlite": b"history",
                "bitm-profile/sessionstore.jsonlz4": b"session",
            }
        )
        archives = {
            FIREFOX_POLICY_PATH: _docker_archive(
                {"policies.json": json.dumps(policy).encode()}
            ),
            developer_extension_path: _docker_archive(
                {"developer-extension.xpi": _extension_xpi(developer_extension_id)}
            ),
            profile_directory: profile_archive,
        }

        container = MagicMock()
        container.exec_run.return_value.exit_code = 0
        container.get_archive.side_effect = lambda path: (iter([archives[path]]), {})
        get_container.return_value = container

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "profile.zip"

            await dump_firefox_data(
                "victim-container",
                destination,
                protocol="vnc",
            )

            with zipfile.ZipFile(destination) as archive:
                names = set(archive.namelist())
                self.assertNotIn(developer_extension_xpi, names)
                self.assertNotIn(developer_extension_data, names)
                self.assertNotIn(developer_extension_store, names)
                self.assertNotIn("bitm-profile/addonStartup.json.lz4", names)
                self.assertNotIn("bitm-profile/extensions.ini", names)
                self.assertNotIn("bitm-profile/extensions.sqlite", names)
                self.assertIn(legitimate_extension_xpi, names)
                self.assertIn(legitimate_extension_data, names)
                self.assertIn(legitimate_extension_store, names)
                self.assertEqual(archive.read(legitimate_extension_xpi), b"legitimate")
                self.assertEqual(
                    archive.read(legitimate_extension_data),
                    b"legitimate-data",
                )
                self.assertEqual(
                    archive.read("bitm-profile/cookies.sqlite"),
                    b"cookies",
                )
                self.assertEqual(
                    archive.read("bitm-profile/places.sqlite"),
                    b"history",
                )
                self.assertEqual(
                    archive.read("bitm-profile/sessionstore.jsonlz4"),
                    b"session",
                )

                extension_metadata = json.loads(
                    archive.read("bitm-profile/extensions.json")
                )
                self.assertEqual(
                    extension_metadata["addons"],
                    [{"id": legitimate_extension_id, "name": "Legitimate"}],
                )
                extension_preferences = json.loads(
                    archive.read("bitm-profile/extension-preferences.json")
                )
                self.assertEqual(
                    extension_preferences,
                    {legitimate_extension_id: {"enabled": True}},
                )

        self.assertEqual(
            [call.args[0] for call in container.get_archive.call_args_list],
            [
                FIREFOX_POLICY_PATH,
                developer_extension_path,
                profile_directory,
            ],
        )


if __name__ == "__main__":
    unittest.main()
