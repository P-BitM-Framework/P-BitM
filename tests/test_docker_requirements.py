import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cli.doctor import CheckStatus, DoctorRunner
from cli.docker_ops import check_docker
from cli.utils import (
    build_docker_image,
    docker_buildkit_is_disabled,
    docker_engine_is_supported,
    get_docker_compose_command,
    get_docker_compose_version,
    parse_docker_engine_version,
)


class DockerVersionTests(unittest.TestCase):
    def test_parses_engine_major_and_minor_versions(self):
        self.assertEqual(parse_docker_engine_version("23.0.6"), (23, 0))
        self.assertEqual(parse_docker_engine_version(" 29.1.2"), (29, 1))
        self.assertIsNone(parse_docker_engine_version("unknown"))

    def test_requires_docker_engine_23_or_newer(self):
        self.assertFalse(docker_engine_is_supported("22.0.9"))
        self.assertTrue(docker_engine_is_supported("23.0.0"))
        self.assertTrue(docker_engine_is_supported("29.1.2"))

    @patch.dict("os.environ", {"DOCKER_BUILDKIT": "0"})
    def test_detects_an_explicitly_disabled_buildkit(self):
        self.assertTrue(docker_buildkit_is_disabled())


class DockerPluginTests(unittest.TestCase):
    @patch("cli.utils._docker_plugin_version")
    def test_compose_version_uses_only_the_cli_plugin(self, plugin_version):
        plugin_version.return_value = "Docker Compose version v2.40.0"

        self.assertEqual(
            get_docker_compose_version(),
            "Docker Compose version v2.40.0",
        )
        plugin_version.assert_called_once_with(
            ["docker", "compose", "version"]
        )

    @patch("cli.utils.error")
    @patch("cli.utils.get_docker_compose_version", return_value=None)
    def test_compose_command_does_not_fall_back_to_standalone(
        self, compose_version, report_error
    ):
        self.assertIsNone(get_docker_compose_command())
        compose_version.assert_called_once_with()
        report_error.assert_called_once()

    @patch("cli.utils.success")
    @patch("cli.utils.run_command", return_value=True)
    def test_custom_images_are_built_with_buildx_and_loaded_locally(
        self, run_command, report_success
    ):
        self.assertTrue(
            build_docker_image(
                "example:latest",
                "images/Dockerfile",
                "images",
            )
        )
        run_command.assert_called_once_with(
            [
                "docker",
                "buildx",
                "build",
                "--load",
                "-t",
                "example:latest",
                "-f",
                "images/Dockerfile",
                "images",
            ],
            quiet=False,
        )
        report_success.assert_called_once()


class DockerPreflightTests(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.client.ping.return_value = True
        self.client.version.return_value = {"Version": "29.1.2"}

    @patch("cli.docker_ops.get_docker_compose_version")
    @patch("cli.docker_ops.get_docker_buildx_version")
    @patch("cli.docker_ops.get_docker_client")
    def test_accepts_complete_modern_toolchain(
        self, get_client, buildx_version, compose_version
    ):
        get_client.return_value = self.client
        buildx_version.return_value = "github.com/docker/buildx v0.30.0"
        compose_version.return_value = "Docker Compose version v2.40.0"

        self.assertTrue(check_docker())

    @patch("cli.docker_ops.get_docker_compose_version")
    @patch("cli.docker_ops.get_docker_buildx_version", return_value=None)
    @patch("cli.docker_ops.get_docker_client")
    def test_rejects_a_missing_buildx_plugin(
        self, get_client, buildx_version, compose_version
    ):
        get_client.return_value = self.client

        self.assertFalse(check_docker())
        compose_version.assert_not_called()

    @patch("cli.docker_ops.get_docker_compose_version")
    @patch("cli.docker_ops.get_docker_buildx_version")
    @patch("cli.docker_ops.get_docker_client")
    def test_rejects_an_unsupported_engine_before_plugin_checks(
        self, get_client, buildx_version, compose_version
    ):
        self.client.version.return_value = {"Version": "22.0.9"}
        get_client.return_value = self.client

        self.assertFalse(check_docker())
        buildx_version.assert_not_called()
        compose_version.assert_not_called()

    @patch.dict("os.environ", {"DOCKER_BUILDKIT": "0"})
    @patch("cli.docker_ops.get_docker_compose_version")
    @patch("cli.docker_ops.get_docker_buildx_version")
    @patch("cli.docker_ops.get_docker_client")
    def test_rejects_an_explicitly_disabled_buildkit(
        self, get_client, buildx_version, compose_version
    ):
        get_client.return_value = self.client

        self.assertFalse(check_docker())
        buildx_version.assert_not_called()
        compose_version.assert_not_called()


class DoctorDockerRequirementTests(unittest.TestCase):
    @patch("cli.doctor.get_docker_compose_version", return_value=None)
    @patch(
        "cli.doctor.get_docker_buildx_version",
        return_value="github.com/docker/buildx v0.30.0",
    )
    @patch("cli.doctor.shutil.which", return_value="/usr/bin/tool")
    def test_doctor_reports_plugins_separately(
        self, which, buildx_version, compose_version
    ):
        runner = DoctorRunner(MagicMock(), project_root=Path.cwd())

        runner._check_host_tools()

        checks = {check.name: check for check in runner.checks}
        self.assertEqual(checks["Docker Buildx"].status, CheckStatus.PASS)
        self.assertEqual(
            checks["Docker Compose plugin"].status,
            CheckStatus.FAIL,
        )
        self.assertIsNone(runner.compose_command)

    @patch("cli.doctor.docker.from_env")
    def test_doctor_rejects_an_unsupported_engine(self, from_env):
        client = MagicMock()
        client.version.return_value = {"Version": "22.0.9"}
        from_env.return_value = client
        runner = DoctorRunner(MagicMock(), project_root=Path.cwd())

        runner._check_docker()

        self.assertEqual(runner.checks[0].status, CheckStatus.FAIL)
        self.assertIn("23.0", runner.checks[0].action)


if __name__ == "__main__":
    unittest.main()
