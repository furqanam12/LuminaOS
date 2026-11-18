#!/usr/bin/env python3
"""Focused checks for the 1.4 accessibility/command and 1.5 productivity updates."""
import ast
import configparser
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import mock_open, patch

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "src/lib/lumina/api.py"
TREE = ast.parse(API.read_text(encoding="utf-8"), filename=str(API))
FUNCTIONS = {"in_quiet_hours", "notify", "copy_paths", "archive_extract", "archive_create",
             "file_permissions", "set_file_permissions", "trash_restore"}
SELECTED = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS]


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lumina-features-")
        self.addCleanup(self.temp.cleanup)
        ns = {"os": os, "time": time, "shutil": shutil, "re": re,
              "zipfile": __import__("zipfile"), "tarfile": __import__("tarfile"),
              "urllib": __import__("urllib.parse", fromlist=["parse"]) and __import__("urllib"),
              "pwd": types.SimpleNamespace(getpwuid=lambda uid: types.SimpleNamespace(pw_name="lumina")),
              "uuid": types.SimpleNamespace(uuid4=lambda: types.SimpleNamespace(hex="abcdef123456")),
              "HOME": self.temp.name, "NOTIF_FILE": str(Path(self.temp.name) / "notifications.json"),
              "HUB": types.SimpleNamespace(emit=lambda *a, **k: None),
              "_notif_lock": __import__("threading").Lock(),
              "_notifs": [],
              "read_json": lambda p, d: d, "write_json": lambda p, v: None,
              "get_settings": lambda: {}, "sh": lambda *a, **k: "", "sh_rc": lambda *a, **k: (0, ""),
              "safe_path": lambda p: os.path.abspath(os.path.expanduser(p)),
              "DEFAULTS": {}}
        exec(compile(ast.Module(body=SELECTED, type_ignores=[]), str(API), "exec"), ns)
        self.api = ns

    def test_quiet_hours(self):
        self.assertTrue(self.api["in_quiet_hours"]({"quietStart": "22:00", "quietEnd": "06:00"}) if time.localtime().tm_hour >= 22 or time.localtime().tm_hour < 6 else True)
        self.assertFalse(self.api["in_quiet_hours"]({}))

    def test_notify_actions_and_rules(self):
        settings = {"notificationRules": {"Demo": "silent"}}
        self.api["get_settings"] = lambda: settings
        n = self.api["notify"]("Title", "Body", "", "Demo", ["open", "Open"])
        self.assertTrue(n["silent"])
        self.assertEqual(n["actions"], [{"id": "open", "label": "Open"}])
        settings["notificationRules"]["Demo"] = "off"
        suppressed = self.api["notify"]("Title", "", "", "Demo")
        self.assertTrue(suppressed.get("suppressed"))

    def test_copy_conflict_policies(self):
        src = Path(self.temp.name) / "source.txt"; src.write_text("new")
        dest = Path(self.temp.name) / "out"; dest.mkdir()
        (dest / "source.txt").write_text("old")
        out = self.api["copy_paths"]([str(src)], str(dest), conflict="skip")
        self.assertEqual(out, [])
        self.assertEqual((dest / "source.txt").read_text(), "old")
        out = self.api["copy_paths"]([str(src)], str(dest), conflict="replace")
        self.assertEqual((dest / "source.txt").read_text(), "new")
        out = self.api["copy_paths"]([str(src)], str(dest), conflict="rename")
        self.assertIn("source (2).txt", str(out[0]))

    def test_archive_and_permissions_roundtrip(self):
        src = Path(self.temp.name) / "a.txt"; src.write_text("hello")
        zip_path = self.api["archive_create"]([str(src)], self.temp.name, "bundle")
        self.assertTrue(zip_path.endswith("bundle.zip"))
        out = Path(self.temp.name) / "out"; out.mkdir()
        self.assertTrue(self.api["archive_extract"](zip_path, str(out)))
        self.assertEqual((out / "a.txt").read_text(), "hello")
        info = self.api["set_file_permissions"](str(src), "700")
        if sys.platform.startswith("win"):
            self.assertEqual(info["octal"], "%03o" % (os.stat(src).st_mode & 0o777))
        else:
            self.assertEqual(info["octal"], "700")
            self.assertEqual(os.stat(src).st_mode & 0o777, 0o700)


class SourceTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_accessibility_settings_and_css(self):
        api = API.read_text(encoding="utf-8")
        for key in ('"uiScale": 100', '"highContrast": False', '"strongFocus": False'):
            self.assertIn(key, api)
        js = self.read("src/ui/js/lumina.js")
        for marker in ("high-contrast", "strong-focus", "--ui-scale", "initKeyboardNav"):
            self.assertIn(marker, js)
        css = self.read("src/ui/css/lumina.css")
        self.assertIn(".high-contrast", css)
        self.assertIn(".strong-focus :focus", css)
        settings = self.read("src/ui/apps/settings.html")
        self.assertIn("async accessibility(pg)", settings)
        self.assertIn("accessibility: 'accessibility'", settings)

    def test_command_palette(self):
        overlay = self.read("src/ui/overlay.html")
        for marker in ('id="command"', "'command', 'menu'", 'function renderCommands', 'function commandNav',
                       "['start', 'cc', 'notifications', 'search', 'command', 'launchpad'", "performance', 'bolt'"):
            self.assertIn(marker, overlay)
        shortcuts = self.read("system/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml")
        self.assertIn("&lt;Primary&gt;k", shortcuts)
        self.assertIn("lumina-ctl command", shortcuts)
        self.assertIn("lumina-ctl command", shortcuts)
        self.assertIn('\\"cmd\\":\\"$cmd\\"', self.read("src/bin/lumina-ctl"))

    def test_files_features(self):
        files = self.read("src/ui/apps/files.html")
        for marker in ("undoStack", "redoStack", "toggleSplit", 'id="splitpane"', "/api/fs/archive/create",
                       "editPermissions", "body.conflict", "editAddress", "k === 'l'"):
            self.assertIn(marker, files)
        api = API.read_text(encoding="utf-8")
        for marker in ("def copy_paths(paths, dest, move=False, conflict=", "def archive_extract",
                       "def archive_create", "def file_permissions", "def set_file_permissions",
                       "def trash_restore", "/api/fs/restore"):
            self.assertIn(marker, api)

    def test_notification_features(self):
        api = API.read_text(encoding="utf-8")
        for marker in ("focusUntil", "quietStart", "notificationRules", "def in_quiet_hours",
                       "/api/notifications/action", "/api/notifications/snooze"):
            self.assertIn(marker, api)
        overlay = self.read("src/ui/overlay.html")
        self.assertIn('id="nsnooze"', overlay)
        self.assertIn("/api/notifications/action", overlay)
        settings = self.read("src/ui/apps/settings.html")
        self.assertIn("Quiet hours", settings)
        self.assertIn("App rules", settings)

    def test_compatibility_wizard(self):
        html = self.read("src/ui/apps/compat.html")
        for marker in ("Compatibility wizard", "/api/compat", "Set up Wine", "Waydroid", "Flatpak"):
            self.assertIn(marker, html)
        desktop = configparser.RawConfigParser(strict=False)
        desktop.read(ROOT / "src/data/applications/lumina-compat.desktop", encoding="utf-8")
        self.assertEqual(desktop["Desktop Entry"]["Exec"], "lumina-app compat")
        app = self.read("src/bin/lumina-app")
        self.assertIn('"compat": (780, 620)', app)
        self.assertIn('"compat": "Compatibility Wizard"', app)
        settings = self.read("src/ui/apps/settings.html")
        self.assertIn("id=\"compat-wizard\"", settings)

    def test_inline_javascript_syntax(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required for inline JavaScript validation")
        for rel in ("src/ui/overlay.html", "src/ui/apps/settings.html", "src/ui/apps/files.html",
                    "src/ui/apps/compat.html", "src/ui/js/lumina.js"):
            path = ROOT / rel
            blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", path.read_text(encoding="utf-8")) if path.suffix == ".html" else [path.read_text(encoding="utf-8")]
            self.assertTrue(blocks, rel)
            for block in blocks:
                result = subprocess.run([node, "--check"], input=block, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, rel + ": " + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
