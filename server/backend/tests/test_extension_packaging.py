import ast
import configparser
import json
from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CAMPAIGNS_ROUTE = PROJECT_ROOT / "server/backend/routes/campaign_lifecycle.py"
EXTENSIONS_ROOT = (
    PROJECT_ROOT / "bitm-images/common/firefox/bad_firefox_extensions"
)
STARTUP_SCRIPTS = (
    PROJECT_ROOT / "bitm-images/vnc/scripts/startVNC.sh",
    PROJECT_ROOT / "bitm-images/selkies/scripts/startSelkies.sh",
)
SELKIES_DOCKERFILES = (
    PROJECT_ROOT / "bitm-images/selkies/Dockerfile",
)
PACKAGE_PATTERN = re.compile(
    r"^cd /bitm/app/bad_firefox_extensions/([^/]+)/ && zip ",
    re.MULTILINE,
)


def declared_builtin_extensions() -> set[str]:
    tree = ast.parse(CAMPAIGNS_ROUTE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "extensions"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, ast.List) and all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in node.value.elts
        ):
            return {item.value for item in node.value.elts}
    raise AssertionError("Campaign built-in extension list was not found")


class ExtensionPackagingTests(unittest.TestCase):
    def test_vnc_and_selkies_package_every_declared_builtin(self):
        declared = declared_builtin_extensions()
        self.assertIn("disable-shortcuts", declared)
        self.assertNotIn("iban-module", declared)

        for script in STARTUP_SCRIPTS:
            content = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertEqual(set(PACKAGE_PATTERN.findall(content)), declared)
                self.assertNotIn("iban-module.xpi", content)
                self.assertIn('[[ -f "$EXTENSION_PATH" ]]', content)

    def test_declared_builtins_have_valid_source_manifests(self):
        extension_ids = set()
        for extension in declared_builtin_extensions():
            with self.subTest(extension=extension):
                manifest_path = EXTENSIONS_ROOT / extension / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                extension_id = manifest["browser_specific_settings"]["gecko"]["id"]
                self.assertNotIn(extension_id, extension_ids)
                extension_ids.add(extension_id)
                self.assertTrue(
                    manifest.get("background") or manifest.get("content_scripts")
                )

    def test_persistence_preserves_cookies_and_legacy_iban_is_absent(self):
        persistence = EXTENSIONS_ROOT / "persistence"
        manifest = json.loads(
            (persistence / "manifest.json").read_text(encoding="utf-8")
        )
        background = (persistence / "background.js").read_text(encoding="utf-8")

        self.assertNotIn("cookies", manifest.get("permissions", []))
        self.assertNotIn("cookies.remove", background)
        self.assertFalse((EXTENSIONS_ROOT / "iban-module").exists())

    def test_form_collector_only_accepts_trusted_user_submissions(self):
        extension = EXTENSIONS_ROOT / "form-interceptor"
        manifest = json.loads(
            (extension / "manifest.json").read_text(encoding="utf-8")
        )
        background = (extension / "background.js").read_text(encoding="utf-8")
        content = (extension / "content.js").read_text(encoding="utf-8")

        self.assertNotIn("webRequest", manifest.get("permissions", []))
        self.assertIn("content.js", json.dumps(manifest.get("content_scripts", [])))
        self.assertNotIn("onBeforeRequest", background)
        self.assertIn("event.isTrusted", content)
        self.assertIn("navigator.userActivation", content)
        self.assertIn("addEventListener('submit'", content)

    def test_cookie_collector_uses_only_in_memory_deduplication(self):
        extension = EXTENSIONS_ROOT / "cookie-hijacking"
        manifest = json.loads(
            (extension / "manifest.json").read_text(encoding="utf-8")
        )
        background = (extension / "background.js").read_text(encoding="utf-8")

        self.assertNotIn("storage", manifest.get("permissions", []))
        self.assertNotIn("browser.storage.local", background)
        self.assertIn("cookie.value || ''", background)
        self.assertIn("pendingCookies", background)

    def test_vnc_python_runtime_is_available_before_user_switch(self):
        dockerfile = (
            PROJECT_ROOT / "bitm-images/vnc/Dockerfile"
        ).read_text(encoding="utf-8")

        install = dockerfile.index("RUN python3 -m pip install")
        user_switch = dockerfile.index("USER bitm")
        self.assertLess(install, user_switch)
        self.assertIn("supervisor pynput websocket_server", dockerfile)
        self.assertNotIn("ENV PATH=/home/bitm/.local/bin", dockerfile)

    def test_vnc_supervisor_drops_each_desktop_process_to_bitm(self):
        config_path = PROJECT_ROOT / "bitm-images/vnc/conf/supervisord.conf"
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")

        self.assertEqual(parser["supervisord"].get("user"), "root")
        self.assertEqual(parser["supervisord"].get("logfile"), "/dev/null")
        environment = parser["supervisord"].get("environment", "")
        self.assertIn('HOME="/home/bitm"', environment)
        self.assertIn('XDG_CACHE_HOME="/home/bitm/.cache"', environment)
        programs = [
            section
            for section in parser.sections()
            if section.startswith("program:")
        ]
        self.assertTrue(programs)
        for section in programs:
            with self.subTest(section=section):
                self.assertEqual(parser[section].get("user"), "bitm")

    def test_vnc_storage_is_writable_by_the_desktop_user(self):
        startup = (
            PROJECT_ROOT / "bitm-images/vnc/scripts/startVNC.sh"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "install -d -o bitm -g bitm -m 0755 /storage",
            startup,
        )
        self.assertIn("chown bitm:bitm /storage/keylogs.txt", startup)
        self.assertIn("chmod 0644 /storage/keylogs.txt", startup)

    def test_vnc_all_modes_use_the_campaign_configured_firefox_profile(self):
        startup = (
            PROJECT_ROOT / "bitm-images/vnc/scripts/startFirefox.sh"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "--profile /bitm/.mozilla/firefox/bitm-profile",
            startup,
        )
        self.assertNotIn("/bitm/.mozilla/firefox/default", startup)

    def test_active_images_package_and_select_environment_policies(self):
        dockerfiles = (
            PROJECT_ROOT / "bitm-images/vnc/Dockerfile",
            *SELKIES_DOCKERFILES,
        )
        for dockerfile in dockerfiles:
            content = dockerfile.read_text(encoding="utf-8")
            with self.subTest(dockerfile=dockerfile.name):
                self.assertIn(
                    "COPY common/firefox/policies.json "
                    "/etc/firefox/policies/policies.json.prod",
                    content,
                )
                self.assertIn(
                    "COPY common/firefox/policies.json.dev "
                    "/etc/firefox/policies/policies.json.dev",
                    content,
                )

        for script in STARTUP_SCRIPTS:
            content = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertIn('if [ "${MODE:-}" = "default" ]', content)
                self.assertIn('POLICIES_SOURCE="${POLICIES_FILE}.dev"', content)
                self.assertIn('POLICIES_SOURCE="${POLICIES_FILE}.prod"', content)
                self.assertIn('cp "$POLICIES_SOURCE" "$POLICIES_FILE"', content)


if __name__ == "__main__":
    unittest.main()
