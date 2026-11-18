#!/usr/bin/env python3
"""Isolated performance regressions; run with Python, without GTK, pwd or psutil."""
import ast
import collections
import concurrent.futures
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from html.parser import HTMLParser
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "src/lib/lumina/api.py"
TREE = ast.parse(API.read_text(encoding="utf-8"), filename=str(API))
FUNCTIONS = {
    "performance_patch", "read_json", "write_json", "get_settings", "set_settings",
    "cpu_load", "stats", "apply_window_shadows",
}
GLOBALS = {
    "DEFAULTS", "PERFORMANCE_PRESETS", "PERFORMANCE_KEYS", "_settings_lock",
    "_shadow_lock", "_stats_lock", "_stats_cache", "_stats_time", "_cpu_previous", "_prev_io",
}
SELECTED = [n for n in TREE.body if
            isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS or
            isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in GLOBALS for t in n.targets)]
CPU = collections.namedtuple("CPU", "user nice system idle iowait irq softirq steal guest guest_nice", defaults=[0] * 10)
SOURCE_LINES = {n.name: n.lineno for n in TREE.body if isinstance(n, ast.FunctionDef)}


def location(name):
    return "src/lib/lumina/api.py:%s" % SOURCE_LINES[name]


def load_api(settings_file, psutil=None):
    namespace = {
        "__name__": "isolated_lumina_api", "json": json, "os": os,
        "threading": threading, "shutil": shutil, "time": time,
        "psutil": psutil or Mock(), "SETTINGS_FILE": str(settings_file),
        "HUB": types.SimpleNamespace(emit=Mock()), "apply_native_theme": Mock(), "sh": Mock(),
    }
    exec(compile(ast.Module(body=SELECTED, type_ignores=[]), str(API), "exec"), namespace)
    if not FUNCTIONS.issubset(namespace) or not GLOBALS.issubset(namespace):
        raise AssertionError("Isolated AST loader is missing required source nodes")
    return namespace


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lumina-performance-")
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "settings.json"
        self.api = load_api(self.file)
        self.write = Mock(wraps=self.api["write_json"])
        self.api["write_json"] = self.write

    def settings(self, patch_value):
        return self.api["set_settings"](patch_value)

    def assertNoEffects(self):
        self.write.assert_not_called()
        self.api["HUB"].emit.assert_not_called()
        self.api["apply_native_theme"].assert_not_called()

    def test_balanced_and_low_power_expand_authoritatively(self):
        """performance_patch: both presets override conflicting boolean effects."""
        expected = {
            "balanced": dict(reduceMotion=False, transparency=True, dockMagnify=True, perfShadows=True),
            "low-power": dict(reduceMotion=True, transparency=False, dockMagnify=False, perfShadows=False),
        }
        for preset, effects in expected.items():
            with self.subTest(preset=preset):
                request = {"performancePreset": preset, **{k: not v for k, v in effects.items()}}
                before = dict(request)
                result = self.settings(request)
                self.assertEqual(request, before)
                self.assertEqual(result["performancePreset"], preset)
                self.assertEqual({k: result[k] for k in effects}, effects)
                self.assertEqual(result["wallpaper"], self.api["DEFAULTS"]["wallpaper"])
                self.assertEqual(self.api["HUB"].emit.call_args.args, ("settings", result))
        self.assertEqual(self.write.call_count, 2)

    def test_custom_preserves_current_effects(self):
        """set_settings: custom is a label, not a third expanding preset."""
        low = self.settings({"performancePreset": "low-power"})
        custom = self.settings({"performancePreset": "custom", "accent": "#123456"})
        for key in self.api["PERFORMANCE_KEYS"]:
            self.assertEqual(custom[key], low[key])
        self.assertEqual(custom["accent"], "#123456")
        self.assertEqual(custom["performancePreset"], "custom")
        custom = self.settings({"performancePreset": "custom", "dockMagnify": True})
        self.assertTrue(custom["dockMagnify"])
        self.assertFalse(custom["transparency"])

    def test_manual_effect_resets_only_on_actual_change(self):
        """performance_patch: unchanged effects and unrelated changes retain preset."""
        for key in sorted(self.api["PERFORMANCE_KEYS"]):
            with self.subTest(effect=key):
                current = self.settings({"performancePreset": "low-power"})
                self.assertEqual(self.settings({key: current[key]})["performancePreset"], "low-power")
                changed = self.settings({key: not current[key]})
                self.assertEqual(changed["performancePreset"], "custom")
                self.assertEqual(changed[key], not current[key])
        self.settings({"performancePreset": "balanced"})
        self.assertEqual(self.settings({"clock24": False})["performancePreset"], "balanced")

    def test_invalid_presets_reject_without_side_effects(self):
        """performance_patch: invalid objects, preset names and types are rejected."""
        for value in ("turbo", "", None, False, 1, [], {}):
            with self.subTest(preset=value), self.assertRaises(ValueError):
                self.settings({"performancePreset": value})
        for value in (None, [], "low-power", True):
            with self.subTest(request=value), self.assertRaises(ValueError):
                self.settings(value)
        self.assertNoEffects()
        self.assertFalse(self.file.exists())

    def test_nonboolean_effects_reject_even_with_expanding_preset(self):
        """performance_patch: bool validation must not silently coerce JSON values."""
        for key in sorted(self.api["PERFORMANCE_KEYS"]):
            for value in (0, 1, "false", None, [], {}):
                for preset in (None, "balanced", "low-power"):
                    request = {key: value}
                    if preset:
                        request["performancePreset"] = preset
                    with self.subTest(effect=key, value=value, preset=preset), self.assertRaises(ValueError):
                        self.settings(request)
        self.assertNoEffects()

    def test_default_no_op_does_not_create_file_write_emit_or_apply(self):
        """set_settings: defaults and empty patches do not cause work."""
        for request in ({}, {"performancePreset": "custom"}, {"perfShadows": True},
                        {"transparency": True, "reduceMotion": False}):
            self.assertEqual(self.settings(request), self.api["get_settings"]())
        self.assertNoEffects()
        self.assertFalse(self.file.exists())

    def test_saved_preset_no_op_does_not_touch_file(self):
        """set_settings: repeated preset and unchanged effects avoid disk and events."""
        saved = self.settings({"performancePreset": "low-power"})
        content, mtime = self.file.read_bytes(), self.file.stat().st_mtime_ns
        self.write.reset_mock()
        self.api["HUB"].emit.reset_mock()
        self.api["apply_native_theme"].reset_mock()
        for request in ({}, {"performancePreset": "low-power"}, {"reduceMotion": True},
                        {"dockMagnify": False, "perfShadows": False}):
            self.assertEqual(self.settings(request), saved)
        self.assertNoEffects()
        self.assertEqual(self.file.read_bytes(), content)
        self.assertEqual(self.file.stat().st_mtime_ns, mtime)

    def test_saved_settings_reload_and_restart_semantics(self):
        """get_settings: a fresh namespace restores persisted effects and label."""
        self.settings({"performancePreset": "low-power", "wallpaper": "saved.jpg"})
        saved = self.settings({"transparency": True})
        restarted = load_api(self.file)
        self.assertEqual(restarted["get_settings"](), saved)
        self.assertEqual(saved["performancePreset"], "custom")
        restarted["set_settings"]({"performancePreset": "balanced"})
        final = load_api(self.file)["get_settings"]()
        self.assertEqual(final["performancePreset"], "balanced")
        self.assertEqual(final["wallpaper"], "saved.jpg")
        self.assertTrue(all(final[k] == v for k, v in restarted["PERFORMANCE_PRESETS"]["balanced"].items()))
        self.assertFalse(Path(str(self.file) + ".tmp").exists())

    def test_saved_label_does_not_reexpand_effects_on_restart(self):
        """get_settings: startup loads saved values, not an implicit preset request."""
        self.api["write_json"](str(self.file), {"performancePreset": "balanced", "perfShadows": False})
        restarted = load_api(self.file)
        self.assertFalse(restarted["get_settings"]()["perfShadows"])
        self.assertEqual(restarted["get_settings"]()["performancePreset"], "balanced")

    def test_json_atomic_replace_and_malformed_fallback(self):
        """read_json/write_json: round-trip and corrupt/missing-file defaults."""
        default = {"sentinel": True}
        self.assertIs(self.api["read_json"](str(self.file), default), default)
        self.api["write_json"](str(self.file), {"widgets": True})
        self.assertEqual(self.api["read_json"](str(self.file), {}), {"widgets": True})
        self.file.write_text("{broken", encoding="utf-8")
        self.assertIs(self.api["read_json"](str(self.file), default), default)

    def test_shadow_application_only_updates_shadow_properties(self):
        """apply_window_shadows: never disable compositing or change theme."""
        for enabled in (False, True):
            self.settings({"perfShadows": enabled})
            self.api["sh"].reset_mock()
            with patch.object(shutil, "which", return_value="mock-xfconf-query"):
                self.api["apply_window_shadows"]()
            commands = [call.args[0] for call in self.api["sh"].call_args_list]
            self.assertEqual(len(commands), 3)
            self.assertEqual({c[c.index("-p") + 1] for c in commands}, {
                "/general/show_frame_shadow", "/general/show_popup_shadow", "/general/show_dock_shadow",
            })
            for command in commands:
                self.assertEqual(command[:4], ["xfconf-query", "-c", "xfwm4", "-p"])
                self.assertEqual(command[-5:], ["-n", "-t", "bool", "-s", str(enabled).lower()])
                self.assertNotIn("use_compositing", " ".join(command))
        self.api["sh"].reset_mock()
        with patch.object(shutil, "which", return_value=None):
            self.api["apply_window_shadows"]()
        self.api["sh"].assert_not_called()

    def test_native_effect_change_invokes_actual_shadow_function(self):
        """apply_native_theme: shadow-only patch executes only shadow commands."""
        node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "apply_native_theme")
        original = self.api["apply_native_theme"]
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(API), "exec"), self.api)
        with patch.object(shutil, "which", return_value="mock-xfconf-query"):
            self.settings({"perfShadows": False})
        self.assertEqual(self.api["sh"].call_count, 3)
        self.assertTrue(all("shadow" in c.args[0][4] for c in self.api["sh"].call_args_list))
        self.api["apply_native_theme"] = original

    def test_shell_startup_explicitly_applies_saved_shadows(self):
        """src/bin/lumina-shell:176 apply_initial runs saved perfShadows on startup."""
        shell_file = ROOT / "src/bin/lumina-shell"
        tree = ast.parse(shell_file.read_text(encoding="utf-8"), filename=str(shell_file))
        shell = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Shell")
        initial = next(n for n in shell.body if isinstance(n, ast.FunctionDef) and n.name == "apply_initial")
        namespace = {"api": types.SimpleNamespace(get_settings=self.api["get_settings"],
                                                  apply_native_theme=Mock(), apply_brightness=Mock()),
                     "threading": threading}
        exec(compile(ast.Module(body=[initial], type_ignores=[]), str(shell_file), "exec"), namespace)
        for enabled in (False, True):
            self.settings({"perfShadows": enabled})
            namespace["apply_initial"](object())
            settings, changed = namespace["api"].apply_native_theme.call_args.args
            self.assertEqual(changed, {"theme": settings["theme"], "perfShadows": enabled})
        startup = next(n for n in shell.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                            and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"
                            and n.func.attr == "apply_initial" for n in ast.walk(startup)))


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lumina-stats-")
        self.addCleanup(self.temp.cleanup)
        self.ps = Mock()
        self.ps.cpu_times.side_effect = lambda percpu=False: self.cores if percpu else self.cpu
        self.ps.disk_io_counters.side_effect = lambda: self.io
        self.ps.net_io_counters.side_effect = lambda: self.net
        self.ps.virtual_memory.return_value = types.SimpleNamespace(total=1000, available=400, percent=60)
        self.ps.swap_memory.return_value = types.SimpleNamespace(total=200, used=20)
        self.ps.pids.return_value = [101, 102]
        self.ps.boot_time.return_value = 10
        self.ps.cpu_freq.return_value = types.SimpleNamespace(current=2400)
        self.cpu = CPU(user=10, system=10, idle=80)
        self.cores = [self.cpu, self.cpu]
        self.io = types.SimpleNamespace(read_bytes=100, write_bytes=200)
        self.net = types.SimpleNamespace(bytes_recv=300, bytes_sent=400)
        self.now = 100.0
        self.api = load_api(Path(self.temp.name) / "settings.json", self.ps)
        self.addCleanup(patch.stopall)
        patch.object(time, "monotonic", side_effect=lambda: self.now).start()
        patch.object(shutil, "disk_usage", return_value=types.SimpleNamespace(total=10000, used=4000)).start()

    def advance(self, dt=1):
        self.now += dt
        self.cpu = self.cpu._replace(user=self.cpu.user + 30, idle=self.cpu.idle + 70)
        self.cores = [self.cpu, self.cpu]

    def threaded_sample(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: (threading.current_thread(), self.api["stats"]())).result(timeout=5)

    def test_first_sample_zero_and_shared_cpu_deltas_across_request_threads(self):
        """stats: first sample is zero, later request threads share CPU baseline."""
        first_thread, first = self.threaded_sample()
        self.assertEqual(first["cpu"], 0)
        self.assertEqual(first["percpu"], [0, 0])
        for key in ("diskRead", "diskWrite", "netRecv", "netSent"):
            self.assertEqual(first[key], 0)
        self.advance()
        second_thread, second = self.threaded_sample()
        self.assertIsNot(first_thread, second_thread)
        self.assertEqual(second["cpu"], 30)
        self.assertEqual(second["percpu"], [30, 30])
        self.advance()
        _, third = self.threaded_sample()
        self.assertEqual(third["cpu"], 30)
        self.ps.cpu_percent.assert_not_called()

    def test_thread_safe_shared_sample_once_per_second(self):
        """stats: simultaneous consumers sample exactly once per one-second bucket."""
        def burst():
            barrier = threading.Barrier(16)
            def request(_):
                barrier.wait(timeout=5)
                return self.api["stats"]()
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                return list(executor.map(request, range(16)))
        first = burst()
        self.assertTrue(all(x is first[0] for x in first))
        self.assertEqual(self.ps.cpu_times.call_count, 2)
        self.assertEqual(self.ps.disk_io_counters.call_count, 1)
        self.advance(.999)
        self.assertIs(self.api["stats"](), first[0])
        self.assertEqual(self.ps.cpu_times.call_count, 2)
        self.now = 101.0
        second = burst()
        self.assertTrue(all(x is second[0] for x in second))
        self.assertIsNot(first[0], second[0])
        for method in (self.ps.disk_io_counters, self.ps.net_io_counters, self.ps.virtual_memory,
                       self.ps.swap_memory, self.ps.pids, self.ps.cpu_freq):
            self.assertEqual(method.call_count, 2)
        self.assertEqual(self.ps.cpu_times.call_count, 4)

    def test_cpu_guest_exclusion_iowait_and_reset(self):
        """cpu_load: exclude guest fields from totals and treat iowait as idle."""
        load = self.api["cpu_load"]
        baseline = CPU()
        current = CPU(user=20, nice=10, system=10, idle=40, iowait=20, guest=500, guest_nice=700)
        self.assertEqual(load(baseline, current), 40)
        self.assertEqual(load(baseline, current._replace(guest=0, guest_nice=0)), 40)
        self.assertEqual(load(baseline, CPU(iowait=100)), 0)
        self.assertEqual(load(baseline, CPU(steal=100)), 100)
        self.assertEqual(load(None, current), 0)
        self.assertEqual(load(current, baseline), 0)
        self.assertEqual(load(current, current), 0)

    def test_disk_network_deltas_reset_missing_and_recovery(self):
        """stats: I/O deltas normalize elapsed time and never become negative."""
        self.api["stats"]()
        self.advance(2)
        self.io = types.SimpleNamespace(read_bytes=300, write_bytes=600)
        self.net = types.SimpleNamespace(bytes_recv=900, bytes_sent=1200)
        sample = self.api["stats"]()
        self.assertEqual([sample[k] for k in ("diskRead", "diskWrite", "netRecv", "netSent")], [100, 200, 300, 400])
        self.advance()
        self.io = types.SimpleNamespace(read_bytes=1, write_bytes=2)
        self.net = types.SimpleNamespace(bytes_recv=3, bytes_sent=4)
        sample = self.api["stats"]()
        self.assertTrue(all(sample[k] == 0 for k in ("diskRead", "diskWrite", "netRecv", "netSent")))
        for io_missing, net_missing in ((True, False), (False, True), (True, True), (False, False)):
            self.advance()
            self.io = None if io_missing else types.SimpleNamespace(read_bytes=20, write_bytes=30)
            self.net = None if net_missing else types.SimpleNamespace(bytes_recv=40, bytes_sent=50)
            sample = self.api["stats"]()
            self.assertTrue(all(sample[k] >= 0 for k in ("diskRead", "diskWrite", "netRecv", "netSent")))
            if io_missing:
                self.assertEqual((sample["diskRead"], sample["diskWrite"]), (0, 0))
            if net_missing:
                self.assertEqual((sample["netRecv"], sample["netSent"]), (0, 0))

    def test_new_cpu_core_first_delta_zero_and_missing_frequency(self):
        """stats: CPU hot-add and unavailable cpu_freq preserve valid samples."""
        self.api["stats"]()
        self.advance()
        self.cores.append(CPU(user=900, idle=100))
        self.ps.cpu_freq.return_value = None
        sample = self.api["stats"]()
        self.assertEqual(sample["percpu"], [30, 30, 0])
        self.assertEqual(sample["freq"], 0)


class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attrs = dict(attrs)
            script_type = attrs.get("type", "").lower()
            executable = script_type in ("", "module", "text/javascript", "application/javascript")
            self.current = [self.getpos()[0], [], executable and "src" not in attrs, script_type]

    def handle_data(self, data):
        if self.current:
            self.current[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current:
            line, chunks, executable, script_type = self.current
            if executable:
                self.scripts.append((line, "".join(chunks), script_type))
            self.current = None


class SyntaxTests(unittest.TestCase):
    pass


def install_syntax_tests():
    files = set(ROOT.glob("src/**/*.py")) | set(ROOT.glob("tools/*.py"))
    for script in (ROOT / "src/bin").iterdir():
        if script.is_file() and re.match(br"^#![^\n]*python", script.read_bytes()):
            files.add(script)
    for index, file in enumerate(sorted(files)):
        def check(self, file=file):
            compile(file.read_bytes(), str(file), "exec")
        check.__doc__ = str(file.relative_to(ROOT)) + ":1 Python syntax compilation (no bytecode writes)"
        setattr(SyntaxTests, "test_python_%03d" % index, check)
    node = shutil.which("node")
    index = 0
    for file in sorted((ROOT / "src/ui").rglob("*.html")):
        parser = ScriptParser()
        parser.feed(file.read_text(encoding="utf-8"))
        if not parser.scripts:
            def check_empty(self, file=file):
                parser = ScriptParser()
                parser.feed(file.read_text(encoding="utf-8"))
                self.assertEqual(parser.scripts, [])
            check_empty.__doc__ = str(file.relative_to(ROOT)) + ":1 no inline executable JS"
            setattr(SyntaxTests, "test_html_%03d" % index, check_empty)
            index += 1
        for line, code, script_type in parser.scripts:
            def check(self, file=file, line=line, code=code, script_type=script_type):
                self.assertIsNotNone(node, "node is required for UI syntax validation")
                command = [node, "--check"]
                if script_type == "module":
                    command.append("--input-type=module")
                command.append("-")
                result = subprocess.run(command, input="\n" * (line - 1) + code,
                                        capture_output=True, text=True, encoding="utf-8", timeout=15)
                self.assertEqual(result.returncode, 0, "%s:%s\n%s" % (file.relative_to(ROOT), line, result.stderr))
            check.__doc__ = "%s:%s inline JS node --check stdin" % (file.relative_to(ROOT), line)
            setattr(SyntaxTests, "test_inline_js_%03d" % index, check)
            index += 1
    for index, file in enumerate(sorted((ROOT / "src/ui").rglob("*.js"))):
        def check(self, file=file):
            self.assertIsNotNone(node, "node is required for UI syntax validation")
            result = subprocess.run([node, "--check", "-"], input=file.read_text(encoding="utf-8"),
                                    capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(result.returncode, 0, "%s:1\n%s" % (file.relative_to(ROOT), result.stderr))
        check.__doc__ = str(file.relative_to(ROOT)) + ":1 external JS node --check stdin"
        setattr(SyntaxTests, "test_external_js_%03d" % index, check)


class Result(unittest.TextTestResult):
    def getDescription(self, test):
        method = getattr(type(test), test._testMethodName)
        test_line = inspect.getsourcelines(method)[1]
        description = test.shortDescription() or ""
        match = re.match(r"(\w+):", description)
        if match and match[1] in SOURCE_LINES:
            description = location(match[1]) + " " + description
        return "%s [tools/test-performance.py:%s] %s" % (test._testMethodName, test_line, description)


if __name__ == "__main__":
    install_syntax_tests()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    failures = len(result.failures) + len(result.errors)
    print("Python SUMMARY: %s tests, %s passed, %s failures/errors" %
          (result.testsRun, result.testsRun - failures, failures))
    sys.exit(0 if result.wasSuccessful() else 1)
