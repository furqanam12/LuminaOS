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

    def test_no_unreachable_post_routes(self):
        """Every POST route must be reachable: no return before later handlers."""
        tree = ast.parse(API.read_text(encoding="utf-8"), filename=str(API))
        route = next(n for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef) and n.name == "route_post")

        def dead_lines(body):
            dead, terminated = [], False
            for st in body:
                if terminated:
                    dead.append(st.lineno)
                if isinstance(st, (ast.Return, ast.Raise)):
                    terminated = True
                for field in ("body", "orelse", "finalbody"):
                    dead.extend(dead_lines(getattr(st, field, []) or []))
                for handler in getattr(st, "handlers", []) or []:
                    dead.extend(dead_lines(handler.body))
            return dead

        self.assertEqual(dead_lines(route.body), [],
                         "unreachable statements after a return in route_post")

    def test_power_profile_presets_are_canonical(self):
        api = API.read_text(encoding="utf-8")
        self.assertIn('"powersaver": "low-power"', api)
        self.assertIn('{"performancePreset": target}', api)
        self.assertNotIn("L.setSettings", api)
        settings = self.read("src/ui/apps/settings.html")
        self.assertEqual(settings.count("async power(pg)"), 1)
        self.assertIn("opt('low-power','Power Saver')", settings)
        self.assertIn("$('#prof').value", settings)

    def test_store_owner_rejects_empty_desktop(self):
        """An empty desktop name must not try to open the applications directory."""
        api = API.read_text(encoding="utf-8")
        self.assertIn('d = os.path.basename(q.get("desktop", "").strip())', api)
        self.assertIn('if not d.endswith(".desktop"):', api)
        self.assertIn("if os.path.isfile(f):", api)

    def test_printer_default_endpoint(self):
        """Printers can be made default without the old placeholder message."""
        api = API.read_text(encoding="utf-8")
        self.assertIn('if p == "/api/printers/default":', api)
        self.assertIn('["lpadmin", "-d", name]', api)
        self.assertIn('re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", name)', api)
        packages = self.read("packages.list").splitlines()
        self.assertIn("cups", packages)
        self.assertIn("cups-client", packages)
        settings = self.read("src/ui/apps/settings.html")
        self.assertIn("'/api/printers/default'", settings)
        self.assertNotIn("API endpoint pending", settings)

    def test_bluetooth_management_endpoints(self):
        """Bluetooth scanning and pairing are real API actions, not a static card."""
        api = API.read_text(encoding="utf-8")
        for route in ("/api/bt/scan", "/api/bt/pair", "/api/bt/connect", "/api/bt/remove", "/api/bt/power"):
            self.assertIn('"%s"' % route, api)
        self.assertIn("BT_MAC_RE", api)
        self.assertIn("bluetoothctl", api)
        settings = self.read("src/ui/apps/settings.html")
        self.assertIn("'/api/bt/scan'", settings)
        self.assertIn("data-bt=\"pair\"", settings)
        self.assertIn("Scan for devices", settings)
        self.assertIn("bluez", self.read("packages.list").splitlines())

    def test_screen_reader_support(self):
        """Orca/AT-SPI is packaged and can be toggled from Settings."""
        api = API.read_text(encoding="utf-8")
        self.assertIn('"screenReader": False', api)
        self.assertIn("def a11y_set", api)
        self.assertIn("orca", api)
        packages = self.read("packages.list")
        self.assertIn("at-spi2-core", packages)
        self.assertIn("orca", packages)
        settings = self.read("src/ui/apps/settings.html")
        self.assertIn("'/api/a11y'", settings)
        self.assertIn("Screen reader", settings)

    def test_audit_log_rotation(self):
        """Audit logs must rotate rather than grow without bound."""
        api = API.read_text(encoding="utf-8")
        self.assertIn("AUDIT_MAX_BYTES", api)
        self.assertIn('AUDIT_FILE + ".1"', api)

    def test_files_loading_skeleton(self):
        """Files shows a loading state before the first asynchronous listing."""
        files = self.read("src/ui/apps/files.html")
        self.assertIn('<div class="spinner" style="margin:0 auto 10px"></div>Loading', files)

    def test_ui_api_routes_exist(self):
        """Every literal L.get/L.post URL used by the UI must have an API route."""
        api = API.read_text(encoding="utf-8")
        lines = api.splitlines()
        get_at = next(i for i, line in enumerate(lines) if line.strip().startswith("def route_get"))
        post_at = next(i for i, line in enumerate(lines) if line.strip().startswith("def route_post"))
        end_at = next((i for i, line in enumerate(lines[post_at + 1:], post_at + 1)
                       if line.startswith("class ") or line.startswith("def ")), len(lines))
        get_src, post_src = "\n".join(lines[get_at:post_at]), "\n".join(lines[post_at:end_at])

        def routes(src):
            return (set(re.findall(r'p\s*==\s*"([^"]+)"', src)),
                    set(re.findall(r'p\.startswith\(\s*"([^"]+)"', src)))

        get_exact, get_prefix = routes(get_src)
        post_exact, post_prefix = routes(post_src)
        missing = []
        for path in (ROOT / "src/ui").rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"L\.(get|post)\(\s*['\"]([^'\"]+)", text):
                method, url = m.group(1), m.group(2)
                if not url.startswith("/api/") or "${" in url:
                    continue
                url = url.split("?")[0]
                exact, prefix = (get_exact, get_prefix) if method == "get" else (post_exact, post_prefix)
                if url.endswith("/"):
                    # Dynamic prefix such as '/api/bt/' + action must match a real route.
                    found = any(r.startswith(url) for r in exact | prefix)
                else:
                    found = url in exact or any(url.startswith(p) for p in prefix)
                if not found:
                    missing.append("%s %s (%s)" % (method.upper(), url, path.name))
        self.assertEqual(missing, [], "UI calls without an API route: " + ", ".join(missing))

    def test_windows_store_files_use_wine_not_privileged_package_helper(self):
        api = API.read_text(encoding="utf-8")
        self.assertIn('file.lower().endswith((".exe", ".msi", ".bat", ".apk"))', api)
        self.assertLess(api.index('file.lower().endswith((".exe", ".msi", ".bat", ".apk"))'),
                        api.index('steps.append(["install-file", file])'))
        self.assertIn('argv = ["wine", "msiexec", "/i", wpath]', api)
        self.assertIn('["wine", "cmd", "/c", wpath]', api)
        store = self.read("src/ui/apps/store.html")
        self.assertIn("|apk", store)
        helper = self.read("src/libexec/lumina-pkg")
        self.assertNotIn("*.exe)", helper)

    def test_android_nested_wayland_runtime(self):
        api = API.read_text(encoding="utf-8")
        self.assertIn("def launch_android", api)
        self.assertIn('"/usr/libexec/lumina/lumina-android"', api)
        self.assertIn("not available in the live session", api)
        self.assertIn('helper, "install", path', api)
        self.assertIn('"weston": bool(shutil.which("weston"))', api)
        helper = self.read("src/libexec/lumina-pkg")
        self.assertIn("-t trixie-backports waydroid weston", helper)
        runtime = self.read("src/libexec/lumina-android")
        self.assertIn("--backend=x11-backend.so", runtime)
        self.assertIn("waydroid app install", runtime)
        self.assertIn("ARM-only apps are not supported", runtime)

    def test_inline_javascript_syntax(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required for inline JavaScript validation")
        for rel in ("src/ui/overlay.html", "src/ui/apps/settings.html", "src/ui/apps/files.html",
                    "src/ui/apps/compat.html", "src/ui/js/lumina.js"):
            path = ROOT / rel
            blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", path.read_text(encoding="utf-8")) if path.suffix == ".html" else [path.read_text(encoding="utf-8")]
            self.assertTrue(blocks, rel)
            for block in blocks:
                result = subprocess.run([node, "--check"], input=block, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, rel + ": " + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
