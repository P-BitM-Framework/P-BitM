import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli import commands
from cli.database import finalize_campaigns_for_shutdown
from cli.utils import cleanup_campaign_containers


class GlobalDownTests(unittest.TestCase):
    @patch("cli.commands.finalize_campaigns_for_shutdown", return_value=True)
    @patch("cli.commands.compose_down", return_value=True)
    @patch("cli.commands.cleanup_campaign_containers", return_value=True)
    @patch("cli.commands.compose_stop", return_value=True)
    def test_down_terminates_runtime_before_finalizing_database(
        self,
        compose_stop,
        cleanup_campaigns,
        compose_down,
        finalize_campaigns,
    ):
        calls = []
        compose_stop.side_effect = lambda: calls.append("stop") or True
        cleanup_campaigns.side_effect = lambda: calls.append("cleanup") or True
        compose_down.side_effect = lambda volumes=False: (
            calls.append(("down", volumes)) or True
        )
        finalize_campaigns.side_effect = lambda: calls.append("database") or True

        self.assertTrue(commands.cmd_down())
        self.assertEqual(
            calls,
            ["stop", "cleanup", ("down", False), "database"],
        )

    @patch("cli.commands.finalize_campaigns_for_shutdown")
    @patch("cli.commands.compose_down", return_value=True)
    @patch("cli.commands.cleanup_campaign_containers", return_value=False)
    @patch("cli.commands.compose_stop", return_value=True)
    def test_down_does_not_finalize_database_after_incomplete_cleanup(
        self,
        _compose_stop,
        cleanup_campaigns,
        compose_down,
        finalize_campaigns,
    ):
        self.assertFalse(commands.cmd_down())
        compose_down.assert_called_once_with(volumes=False)
        self.assertEqual(cleanup_campaigns.call_count, 2)
        finalize_campaigns.assert_not_called()

    @patch("cli.commands.finalize_campaigns_for_shutdown", return_value=True)
    @patch("cli.commands.compose_down", side_effect=[False, True])
    @patch("cli.commands.cleanup_campaign_containers", side_effect=[False, True])
    @patch("cli.commands.compose_stop", return_value=False)
    def test_down_retries_after_partial_teardown(
        self,
        _compose_stop,
        cleanup_campaigns,
        compose_down,
        finalize_campaigns,
    ):
        self.assertTrue(commands.cmd_down())
        self.assertEqual(cleanup_campaigns.call_count, 2)
        self.assertEqual(compose_down.call_count, 2)
        finalize_campaigns.assert_called_once_with()


class ShutdownDatabaseTests(unittest.TestCase):
    def test_only_resumable_campaigns_are_completed(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "p-bitm.db"
            connection = sqlite3.connect(database_path)
            connection.executescript(
                """
                CREATE TABLE campaigns (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    container_status TEXT,
                    completed_at TEXT
                );
                CREATE TABLE victims (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    is_active INTEGER,
                    container_status TEXT
                );
                """
            )
            connection.executemany(
                "INSERT INTO campaigns VALUES (?, ?, ?, ?)",
                [
                    ("active", "active", "running", None),
                    ("paused", "paused", "paused", None),
                    ("scheduled", "scheduled", "scheduled", None),
                    ("draft", "draft", None, None),
                    ("completed", "completed", "stopped", "earlier"),
                ],
            )
            connection.executemany(
                "INSERT INTO victims VALUES (?, ?, 1, 'running')",
                [("v-active", "active"), ("v-draft", "draft")],
            )
            connection.commit()
            connection.close()

            self.assertTrue(finalize_campaigns_for_shutdown(database_path))

            connection = sqlite3.connect(database_path)
            campaigns = dict(
                connection.execute("SELECT id, status FROM campaigns")
            )
            victims = {
                row[0]: (row[1], row[2])
                for row in connection.execute(
                    "SELECT id, is_active, container_status FROM victims"
                )
            }
            connection.close()

            self.assertEqual(campaigns["active"], "completed")
            self.assertEqual(campaigns["paused"], "completed")
            self.assertEqual(campaigns["scheduled"], "completed")
            self.assertEqual(campaigns["draft"], "draft")
            self.assertEqual(campaigns["completed"], "completed")
            self.assertEqual(victims["v-active"], (0, "stopped"))
            self.assertEqual(victims["v-draft"], (1, "running"))


class CampaignCleanupTests(unittest.TestCase):
    @patch("cli.utils.subprocess.run")
    def test_cleanup_removes_all_labeled_workloads_and_networks(self, run):
        def result_for(command, **_kwargs):
            if command[:3] == ["docker", "ps", "-aq"]:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="campaign\nvictim\negress\n",
                )
            if command[:4] == ["docker", "network", "ls", "-q"]:
                role_filter = command[5]
                network = (
                    "private-net\n"
                    if role_filter.endswith("campaign-private")
                    else "egress-net\n"
                )
                return subprocess.CompletedProcess(command, 0, stdout=network)
            return subprocess.CompletedProcess(command, 0, stdout="")

        run.side_effect = result_for

        self.assertTrue(cleanup_campaign_containers())
        commands_run = [call.args[0] for call in run.call_args_list]
        self.assertIn(["docker", "rm", "-f", "campaign"], commands_run)
        self.assertIn(["docker", "rm", "-f", "victim"], commands_run)
        self.assertIn(["docker", "rm", "-f", "egress"], commands_run)
        self.assertIn(
            ["docker", "network", "rm", "private-net"],
            commands_run,
        )
        self.assertIn(
            ["docker", "network", "rm", "egress-net"],
            commands_run,
        )


if __name__ == "__main__":
    unittest.main()
