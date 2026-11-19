#!/usr/bin/env python3
"""Focused regression checks for the installer and first-run feature update."""
import ast
import configparser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import mock_open, patch

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "src/lib/lumina/api.py"
TREE = ast.parse(API.read_text(encoding="utf-8"), filename=str(API))
FUNCTIONS = {"session_user", "is_live_session", "first_run_status", "complete_first_run",
             "installed_boot_checks", "desktop_entry"}
SELECTED = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS]


def load_api(setup_done):
    fake_pwd = types.SimpleNamespace(getpwuid=lambda uid: types.SimpleNamespace(pw_name="lumina"))
    ns = {"os": os, "shutil": shutil, "configparser": configparser, "pwd": fake_pwd,
          "socket": __import__("socket"), "time": __import__("time"), "HOME": str(Path.home()),
          "SETUP_DONE": str(setup_done), "sh": lambda *a, **k: "UTC"}
    exec(compile(ast.Module(body=SELECTED, type_ignores=[]), str(API), "exec"), ns)
    return ns


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lumina-setup-")
        self.addCleanup(self.temp.cleanup)
        self.api = load_api(Path(self.temp.name) / "setup-complete")

    def test_desktop_entry_name_icon_and_exec(self):
        path = Path(self.temp.name) / "Install LuminaOS.desktop"
        path.write_text("[Desktop Entry]\nType=Application\nName=Install LuminaOS\nIcon=lumina-logo\nExec=lumina-install %f\n", encoding="utf-8")
        entry = self.api["desktop_entry"](str(path))
        self.assertEqual(entry, {"id": "Install LuminaOS.desktop", "name": "Install LuminaOS",
                                 "icon": "lumina-logo", "exec": "lumina-install"})

    def test_first_run_status_and_completion_marker(self):
        with patch("builtins.open", mock_open(read_data="luminaos\n")), patch("os.path.exists", return_value=False):
            status = self.api["first_run_status"]()
        self.assertEqual(status["live"], False)
        self.assertEqual(status["complete"], False)
        self.assertEqual(status["hostname"], "luminaos")
        self.assertEqual(status["timezone"], "UTC")
        self.assertTrue(self.api["complete_first_run"]()["ok"])
        self.assertTrue(Path(self.api["SETUP_DONE"]).exists())

    def test_installed_boot_checks_detect_good_and_missing_system(self):
        exists = lambda p: p != "/run/live/medium"
        with patch("os.path.exists", side_effect=exists), patch("os.path.isdir", return_value=True), \
             patch("os.access", return_value=True), patch("shutil.which", return_value="/usr/bin/calamares"), \
             patch("builtins.open", mock_open(read_data="menuentry 'LuminaOS (safe graphics)'")):
            result = self.api["installed_boot_checks"]()
        self.assertTrue(result["ok"], [c for c in result["checks"] if not c["ok"]])
        self.assertEqual(len(result["checks"]), 10)
        with patch("os.path.exists", return_value=False), patch("os.path.isdir", return_value=False), \
             patch("os.access", return_value=False), patch("shutil.which", return_value=None), \
             patch("builtins.open", side_effect=OSError("missing")):
            result = self.api["installed_boot_checks"]()
        self.assertFalse(result["ok"])
        self.assertTrue(any(c["name"] == "Safe-graphics recovery" and not c["ok"] for c in result["checks"]))


class SourceTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_installer_launcher_is_branded_and_hides_generic_entries(self):
        desktop = configparser.RawConfigParser(strict=False)
        desktop.read(ROOT / "src/data/applications/lumina-install.desktop", encoding="utf-8")
        entry = desktop["Desktop Entry"]
        self.assertEqual(entry["Name"], "Install LuminaOS")
        self.assertEqual(entry["Exec"], "lumina-install")
        self.assertEqual(entry["Icon"], "lumina-logo")
        build = self.read("build.sh")
        self.assertIn("lumina-session lumina-install", build)
        self.assertIn("/usr/share/applications/calamares*.desktop", build)
        self.assertIn("NoDisplay=true", build)
        self.assertIn("Install\\ LuminaOS.desktop", build)
        live = self.read("system/usr/lib/live/config/2000-lumina")
        self.assertIn("/home/lumina/Desktop/calamares*.desktop", live)
        self.assertIn("Install\\ LuminaOS.desktop", live)

    def test_first_run_wiring(self):
        session = self.read("src/bin/lumina-session")
        self.assertIn("/run/live/medium", session)
        self.assertIn("lumina-app welcome", session)
        self.assertIn("lumina-app setup", session)
        self.assertIn("setup-complete", session)
        app = self.read("src/bin/lumina-app")
        self.assertIn('"setup": (860, 640)', app)
        self.assertIn('"setup": "LuminaOS Setup"', app)
        self.assertIn('"snip", "setup", "compat"}', app)
        self.assertIn("welcome|setup|compat) exec lumina-app", self.read("src/bin/lumina-ctl"))
        api_source = API.read_text(encoding="utf-8")
        for endpoint in ("/api/first-run/status", "/api/first-run/complete", "/api/system/check"):
            self.assertIn(endpoint, api_source)
        setup = self.read("src/ui/apps/setup.html")
        for marker in ("Current password", "Device name", "Time zone", "Performance", "System check"):
            self.assertIn(marker, setup)
        self.assertIn("L.app('store', ['--essentials'])", setup)

    def test_installed_recovery_is_built_and_validated(self):
        grub = self.read("system/etc/grub.d/45_lumina_recovery")
        self.assertIn("menuentry 'LuminaOS (safe graphics)'", grub)
        self.assertIn("nomodeset", grub)
        self.assertIn("GRUB_DEVICE_UUID", grub)
        build = self.read("build.sh")
        self.assertIn("chmod 0755 /etc/grub.d/45_lumina_recovery", build)
        self.assertIn("update-grub", build)
        self.assertIn("safe graphics", self.read("iso-grub.cfg"))

    def test_runtime_packages_do_not_break_iso_install(self):
        build = self.read("build.sh")
        packages = [line.strip() for line in self.read("packages.list").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        # wine32 is an i386 package, so the architecture must be registered
        # before any apt operation inside the build chroot.
        self.assertIn("dpkg --add-architecture i386", build)
        self.assertLess(build.index("dpkg --add-architecture i386"),
                        build.index('chroot "$CH" apt-get update'))
        self.assertIn("wine32:i386", packages)
        self.assertIn("wine64", packages)
        # Waydroid is only in trixie-backports and needs Wayland; adding it to
        # the base package list would abort an otherwise healthy ISO build.
        self.assertNotIn("waydroid", packages)
        self.assertNotIn("lxctl", packages)
        helper = self.read("src/libexec/lumina-pkg")
        self.assertIn("trixie-backports", helper)
        self.assertIn("-t trixie-backports waydroid weston", helper)

    def test_kali_repository_setup_is_fail_closed(self):
        helper = self.read("src/libexec/lumina-pkg")
        self.assertIn("signed-by=/etc/apt/keyrings/kali-archive-keyring.gpg", helper)
        self.assertIn('https://http.kali.org/kali', helper)
        self.assertIn("Kali repository verification failed", helper)
        self.assertNotIn("archive-key.asc | gpg", helper)
        self.assertIn("Configure Kali Repositories first", helper)
        self.assertIn("kali-msf)", helper)

    def test_shell_syntax(self):
        scripts = [ROOT / "build.sh", ROOT / "src/bin/lumina-install", ROOT / "src/bin/lumina-ctl",
                   ROOT / "src/bin/lumina-session", ROOT / "system/usr/lib/live/config/2000-lumina",
                   ROOT / "system/etc/grub.d/45_lumina_recovery", ROOT / "src/libexec/lumina-pkg",
                   ROOT / "src/libexec/kali-tools", ROOT / "src/bin/lumina-terminal",
                   ROOT / "src/libexec/lumina-android", ROOT / "src/etc/lumina/kali-profile.sh"]
        for path in scripts:
            shell = "bash" if path.name in ("build.sh", "lumina-terminal", "lumina-android", "kali-tools", "kali-profile.sh") else "sh"
            result = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{path}: {result.stderr}")

    def test_inline_setup_javascript_syntax(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required for inline JavaScript validation")
        html = self.read("src/ui/apps/setup.html")
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", html)
        self.assertTrue(blocks)
        for block in blocks:
            result = subprocess.run([node, "--check"], input=block, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
