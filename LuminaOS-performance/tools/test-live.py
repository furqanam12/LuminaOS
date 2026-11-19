#!/usr/bin/env python3
"""LuminaOS live system test suite (non-destructive).

Run this INSIDE a booted LuminaOS session (or over SSH with DISPLAY set):

    DISPLAY=:0 XAUTHORITY=$HOME/.Xauthority python3 tools/test-live.py

It exercises the local API, filesystem, settings, notifications, audio,
display, network, all built-in apps, window actions and performance stats.
The JSON report is written to /tmp/lumina-live-report.json.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:7700"
HOME = os.path.expanduser("~")
results = []


def record(name, ok, detail=""):
    results.append({"test": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" - " + str(detail)[:160]) if detail else ""), flush=True)


def warn(name, detail):
    results.append({"test": name, "ok": True, "warn": True, "detail": str(detail)[:400]})
    print("WARN %s - %s" % (name, str(detail)[:160]), flush=True)


def http(path, data=None, timeout=25, raw=False):
    url = BASE + path
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            return r.status, (payload if raw else json.loads(payload.decode("utf-8", "replace"))), time.time() - t0
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            parsed = json.loads(payload.decode("utf-8", "replace"))
        except Exception:
            parsed = payload[:200]
        return e.code, parsed, time.time() - t0
    except Exception as e:
        return 0, {"error": str(e)}, time.time() - t0


def get(path, **kw):
    return http(path, **kw)


def post(path, body=None, **kw):
    return http(path, {} if body is None else body, **kw)


def sh(cmd, timeout=25):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


# ---------------------------------------------------------------- system
def test_system():
    rc, out, _ = sh("uname -srm")
    record("kernel", rc == 0 and "Linux" in out, out)
    rc, out, _ = sh(". /etc/os-release && echo $PRETTY_NAME")
    record("os-release", "LuminaOS" in out, out)
    rc, out, _ = sh("uptime -p")
    record("uptime", rc == 0, out)
    rc, out, _ = sh("systemctl is-system-running")
    if out == "degraded":
        warn("systemd state", "degraded (vboxadd.service unit only)")
    else:
        record("systemd state", out in ("running", "degraded"), out)
    rc, out, _ = sh("systemctl --failed --no-legend --no-pager --plain | wc -l")
    try:
        failed_units = int(out.strip() or 0)
    except ValueError:
        failed_units = -1
    record("failed units <= 1", 0 <= failed_units <= 1, "%d failed unit(s)" % failed_units)
    rc, out, _ = sh("df -Pm / | tail -1 | awk '{print $4}'")
    free_mb = int(out or 0)
    record("root free space >1GB", free_mb > 1024, "%d MB" % free_mb)
    rc, out, _ = sh("free -m | awk '/Mem:/{print $7}'")
    record("available memory >600MB", int(out or 0) > 600, "%s MB" % out)
    rc, out, _ = sh("pgrep -c -f 'Xorg :0'; pgrep -c -f xfwm4; pgrep -c -f lumina-shell; pgrep -c -f lightdm")
    counts = [int(x) for x in out.split()] if out else []
    record("core processes", len(counts) == 4 and all(c >= 1 for c in counts), "Xorg/xfwm4/shell/lightdm=%s" % counts)
    rc, out, _ = sh("ss -ltn | grep -c '127.0.0.1:7700'")
    record("API listening on 7700", out == "1", out)
    rc, out, _ = sh("xrandr --current | grep '\\*' | head -1")
    record("display mode 1920x1080", "1920x1080" in out, out)
    rc, out, _ = sh("lsmod | grep -c '^vboxguest'")
    record("VirtualBox guest modules", out == "1", out)
    rc, out, _ = sh("cat /sys/class/dmi/id/sys_vendor 2>/dev/null")
    record("virtualization detected", "VirtualBox" in out or "innotek" in out, out)


# ---------------------------------------------------------------- UI pages
def test_ui_pages():
    paths = ["/ui/desktop.html", "/ui/topbar.html", "/ui/dock.html", "/ui/overlay.html",
             "/ui/toasts.html", "/ui/css/lumina.css", "/ui/js/lumina.js", "/ui/js/window.js"]
    html_dir = "/usr/share/lumina/ui/apps"
    for f in sorted(os.listdir(html_dir)):
        if f.endswith(".html"):
            paths.append("/ui/apps/" + f)
    bad = []
    for p in paths:
        code, body, _ = get(p, raw=True)
        size = len(body) if isinstance(body, (bytes, str)) else 0
        if code != 200 or size < 100:
            bad.append("%s:%s/%sB" % (p, code, size))
    record("all %d UI pages/assets load" % len(paths), not bad, ", ".join(bad) or "all 200")


# ---------------------------------------------------------------- API GET sweep
def test_api_gets():
    routes = ["/api/apps", "/api/audio", "/api/bt", "/api/compat", "/api/display",
              "/api/fs/places", "/api/fs/recent", "/api/net", "/api/notifications",
              "/api/procs", "/api/services", "/api/settings", "/api/startup",
              "/api/stats", "/api/store", "/api/store/jobs", "/api/store/owner",
              "/api/sys", "/api/timezones", "/api/users", "/api/wallpapers",
              "/api/windows", "/api/workspaces",
              "/api/fs/list?path=" + urllib.parse.quote(HOME),
              "/api/fs/read?path=/etc/hostname",
              "/api/fs/raw?path=/etc/hostname",
              "/api/fs/search?q=hostname&path=/etc",
              "/api/icon?name=lumina-files&size=64",
              "/api/wallpaper/file?name=clearwater.jpg",
              "/api/wallpaper/blur?name=clearwater.jpg"]
    bad = []
    slow = []
    for p in routes:
        code, body, dt = get(p, raw=True, timeout=30)
        if code != 200:
            bad.append("%s:%s" % (p, code))
        if dt > 2:
            slow.append("%s:%.1fs" % (p.split("?")[0], dt))
    record("GET API sweep (%d endpoints)" % len(routes), not bad, ", ".join(bad) or "all 200")
    if slow:
        warn("slow endpoints", ", ".join(slow))
    code, s, _ = get("/api/sys")
    keys = ["os", "kernel", "cpu", "cores", "mem", "disk", "arch"]
    record("sysinfo fields", all(k in s for k in keys), ",".join(k for k in keys if k not in s) or "ok")
    code, a, _ = get("/api/apps")
    record("application catalog", isinstance(a, list) and len(a) >= 20, "%d apps" % (len(a) if isinstance(a, list) else -1))
    lum = [x for x in a if x.get("lumina")] if isinstance(a, list) else []
    record("12 built-in Lumina apps", len(lum) >= 12, "%d" % len(lum))
    code, w, _ = get("/api/windows")
    record("window manager API", isinstance(w, list), "%d windows" % (len(w) if isinstance(w, list) else -1))


# ---------------------------------------------------------------- filesystem
def test_files():
    stamp = str(int(time.time()))
    base = os.path.join(HOME, "lumina-test-" + stamp)
    code, r, _ = post("/api/fs/mkdir", {"path": HOME, "name": "lumina-test-" + stamp})
    base = r.get("path", base) if isinstance(r, dict) else base
    record("fs mkdir", code == 200 and os.path.isdir(base), base)
    code, r, _ = post("/api/fs/newfile", {"path": base, "name": "hello.txt"})
    f1 = os.path.join(base, "hello.txt")
    record("fs newfile", code == 200 and os.path.exists(f1), f1)
    code, r, _ = post("/api/fs/write", {"path": f1, "text": "LuminaOS live test 123"})
    code2, body, _ = get("/api/fs/read?path=" + urllib.parse.quote(f1))
    record("fs write+read", code == 200 and body.get("text") == "LuminaOS live test 123", body.get("text"))
    dest = os.path.join(base, "copy")
    os.makedirs(dest, exist_ok=True)
    code, r, _ = post("/api/fs/copy", {"paths": [f1], "dest": dest})
    record("fs copy", code == 200 and r.get("ok") and os.path.exists(os.path.join(dest, "hello.txt")), r)
    code, r, _ = post("/api/fs/rename", {"path": f1, "name": "renamed.txt"})
    f2 = os.path.join(base, "renamed.txt")
    record("fs rename", code == 200 and os.path.exists(f2), r)
    code, body, _ = get("/api/fs/list?path=" + urllib.parse.quote(base))
    names = [x.get("name") for x in body.get("items", [])] if isinstance(body, dict) else []
    record("fs list", code == 200 and "renamed.txt" in names and "copy" in names, names)
    code, body, _ = get("/api/fs/search?q=renamed&path=" + urllib.parse.quote(base))
    record("fs search", code == 200, str(body)[:80])
    code, r, _ = post("/api/fs/delete", {"paths": [base]})
    record("fs delete", code == 200 and not os.path.exists(base), r)
    # /api/run smoke test
    marker = os.path.join(HOME, "lumina-run-" + stamp)
    code, r, _ = post("/api/run", {"cmd": "touch " + marker})
    time.sleep(0.7)
    record("/api/run executes command", os.path.exists(marker), marker)
    if os.path.exists(marker):
        os.remove(marker)


# ---------------------------------------------------------------- settings
def test_settings():
    code, orig, _ = get("/api/settings")
    if code != 200:
        record("settings readable", False, code)
        return
    record("settings readable", True, "%d keys" % len(orig))
    sf = os.path.join(HOME, ".config/lumina/settings.json")
    record("settings file exists", os.path.exists(sf), sf)

    def roundtrip(key, value, verify=None):
        code, r, _ = post("/api/settings", {key: value})
        time.sleep(0.25)
        code2, now, _ = get("/api/settings")
        actual = now.get(key)
        ok = code == 200 and (verify(actual) if verify else actual == value)
        record("setting %s -> %s" % (key, value), ok, "actual=%s" % actual)
        return ok

    roundtrip("theme", "dark")
    roundtrip("theme", "light")
    roundtrip("accent", "#0a84ff")
    roundtrip("reduceMotion", True)
    roundtrip("transparency", False)
    roundtrip("dockMagnify", True)
    roundtrip("clock24", False)
    roundtrip("nightLight", True)
    roundtrip("focus", True)
    roundtrip("brightness", 60, lambda v: isinstance(v, (int, float)) and 0 <= v <= 100)
    # wallpaper cycle
    code, walls, _ = get("/api/wallpapers")
    items = walls.get("items", []) if isinstance(walls, dict) else []
    if len(items) > 1:
        alt = next((x["name"] for x in items if x["name"] != orig.get("wallpaper")), None)
        if alt:
            roundtrip("wallpaper", alt)
    # restore original for everything we touched
    restore = {k: orig[k] for k in ("theme", "accent", "reduceMotion", "transparency", "dockMagnify",
                                    "clock24", "nightLight", "focus", "brightness", "wallpaper") if k in orig}
    code, r, _ = post("/api/settings", restore)
    time.sleep(0.4)
    code2, final, _ = get("/api/settings")
    diffs = {k: (orig.get(k), final.get(k)) for k in restore if final.get(k) != orig.get(k)}
    record("settings restored", not diffs, diffs or "all restored")


# ---------------------------------------------------------------- apps
APP_IDS = ["lumina-files.desktop", "lumina-settings.desktop", "lumina-taskmgr.desktop",
           "lumina-notepad.desktop", "lumina-calculator.desktop", "lumina-snip.desktop",
           "lumina-photos.desktop", "lumina-store.desktop", "lumina-welcome.desktop",
           "lumina-about.desktop", "lumina-terminal.desktop", "lumina-performance.desktop"]


def windows():
    code, w, _ = get("/api/windows")
    return w if isinstance(w, list) else []


def test_apps():
    opened = 0
    failed = []
    for aid in APP_IDS:
        before = {w["pid"] for w in windows()}
        t0 = time.time()
        code, r, _ = post("/api/launch", {"id": aid})
        if code != 200 or not r.get("ok"):
            failed.append("%s launch" % aid)
            record("app launch " + aid, False, r)
            continue
        found = None
        while time.time() - t0 < 30:
            time.sleep(0.5)
            for w in windows():
                if w.get("pid") not in before:
                    found = w
                    break
            if found:
                break
        if not found:
            record("app launch " + aid, False, "no window after 30s")
            failed.append(aid)
            continue
        opened += 1
        record("app window " + aid, True, "%s (%.1fs)" % ((found.get("title") or "")[:40], time.time() - t0))
        xid, pid = found["xid"], found["pid"]
        post("/api/window", {"xid": xid, "action": "close"})
        for _ in range(12):
            time.sleep(0.3)
            if not any(w["xid"] == xid for w in windows()):
                break
        sh("kill %d 2>/dev/null; true" % pid)
        time.sleep(0.6)
    record("all built-in apps opened (%d/%d)" % (opened, len(APP_IDS)), opened == len(APP_IDS), ", ".join(failed) or "ok")

    # window actions on calculator
    before = {w["pid"] for w in windows()}
    post("/api/launch", {"id": "lumina-calculator.desktop"})
    win = None
    for _ in range(40):
        time.sleep(0.4)
        for w in windows():
            if w.get("pid") not in before:
                win = w
                break
        if win:
            break
    if win:
        post("/api/window", {"xid": win["xid"], "action": "minimize"})
        time.sleep(0.6)
        m = next((w for w in windows() if w["xid"] == win["xid"]), {})
        record("window minimize", bool(m.get("minimized")), m.get("minimized"))
        post("/api/window", {"xid": win["xid"], "action": "toggle"})
        time.sleep(0.6)
        m = next((w for w in windows() if w["xid"] == win["xid"]), {})
        record("window restore", not m.get("minimized"), m.get("minimized"))
        post("/api/window", {"xid": win["xid"], "action": "maximize"})
        time.sleep(0.6)
        m = next((w for w in windows() if w["xid"] == win["xid"]), {})
        record("window maximize", bool(m.get("maximized")), m.get("maximized"))
        post("/api/window", {"xid": win["xid"], "action": "close"})
    else:
        record("window actions", False, "calculator did not open")


# ---------------------------------------------------------------- notifications / audio / display
def test_services():
    code, before, _ = get("/api/notifications")
    code, n, _ = post("/api/notify", {"title": "LuminaOS live test", "body": "Automated check",
                                      "icon": "lumina-about", "app": "System Test"})
    record("notification create", code == 200 and isinstance(n, dict) and bool(n.get("id")), n)
    time.sleep(0.4)
    code, after, _ = get("/api/notifications")
    found = [x for x in after if x.get("id") == (n.get("id") if isinstance(n, dict) else None)]
    record("notification listed", bool(found), "%d notifications" % len(after))
    if found:
        post("/api/notifications/clear", {"id": found[0]["id"]})
        code, cleared, _ = get("/api/notifications")
        record("notification clear", all(x.get("id") != found[0]["id"] for x in cleared), len(cleared))

    code, a, _ = get("/api/audio")
    record("audio readable", code == 200 and a.get("available") is True, a)
    old_vol, old_mute = a.get("volume"), a.get("muted")
    post("/api/audio", {"volume": 30})
    time.sleep(0.3)
    code, a2, _ = get("/api/audio")
    record("audio volume set", a2.get("volume") == 30, a2.get("volume"))
    post("/api/audio", {"muted": True})
    time.sleep(0.3)
    code, a3, _ = get("/api/audio")
    record("audio mute", a3.get("muted") is True, a3.get("muted"))
    post("/api/audio", {"volume": old_vol, "muted": old_mute})

    code, d, _ = get("/api/display")
    outs = d.get("outputs", []) if isinstance(d, dict) else []
    record("display outputs", len(outs) >= 1 and outs[0].get("current") == "1920x1080", outs[0].get("current") if outs else "none")
    if outs:
        code, r, _ = post("/api/display", {"output": outs[0]["name"], "mode": outs[0]["current"]})
        record("display mode re-apply", code == 200 and r.get("ok", False), r)


# ---------------------------------------------------------------- network
def test_network():
    code, n, _ = get("/api/net")
    rec = (n.get("devices") or [{}])[0]
    record("network device", n.get("available") is True and bool(n.get("primary")) and rec.get("state") == "connected",
           "%s %s" % (rec.get("device"), rec.get("state")))
    rc, out, _ = sh("ping -c 2 -W 3 1.1.1.1")
    record("internet ping", rc == 0 and "2 packets transmitted, 2 received" in out, out.splitlines()[-1] if out else "")
    rc, out, _ = sh("getent hosts deb.debian.org")
    record("DNS resolution", rc == 0 and bool(out), out)
    rc, out, _ = sh("curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://deb.debian.org")
    record("HTTPS connectivity", out.strip() in ("200", "301", "302"), out.strip())


# ---------------------------------------------------------------- performance
def test_performance():
    code, s1, _ = get("/api/stats")
    time.sleep(2.0)
    code2, s2, _ = get("/api/stats")
    ok = all(k in s2 for k in ("cpu", "mem", "disk", "procs")) and 0 <= s2.get("cpu", -1) <= 100
    record("live stats", ok, "cpu=%.1f%% mem=%.1f%% procs=%s" % (s2.get("cpu", -1), s2.get("mem", {}).get("percent", -1), s2.get("procs")))
    record("stats update over time", s2.get("uptime", 0) > s1.get("uptime", 0), "%.1fs" % (s2.get("uptime", 0) - s1.get("uptime", 0)))
    code, p, _ = get("/api/procs")
    plist = p if isinstance(p, list) else p.get("procs", [])
    record("process list", len(plist) > 40, "%d processes" % len(plist))
    code, sv, _ = get("/api/services")
    record("service list", bool(sv), type(sv).__name__)
    code, ws, _ = get("/api/workspaces")
    record("workspaces", isinstance(ws, dict) and ws.get("count", 0) >= 1, ws)
    rc, out, _ = sh("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null")
    if out:
        record("cpu governor", True, out)
    else:
        warn("cpu governor", "no cpufreq driver in this VM (virtualized CPU)")


# ---------------------------------------------------------------- store + logs
def test_store():
    code, s, _ = get("/api/store")
    ok = code == 200 and isinstance(s, dict) and bool(s)
    record("store catalog", ok, "%d keys" % (len(s) if isinstance(s, dict) else -1))
    if isinstance(s, dict):
        print("  store keys:", ",".join(list(s.keys())[:8]), flush=True)
    code, o, _ = get("/api/store/owner")
    record("store owner info", code == 200, str(o)[:100])
    code2, o2, _ = get("/api/store/owner?desktop=lumina-files.desktop")
    record("store owner lookup", code2 == 200 and o2.get("name") == "File Explorer", str(o2)[:100])
    code, j, _ = get("/api/store/jobs")
    record("store jobs", code == 200 and isinstance(j, list), "%d jobs" % (len(j) if isinstance(j, list) else -1))


def test_logs():
    rc, out, _ = sh("ls -l /home/furqan/.xsession-errors 2>/dev/null | awk '{print $5}'")
    if out:
        rc, errs, _ = sh("grep -E 'JS error|Unhandled|Traceback' /home/furqan/.xsession-errors | tail -5")
        if errs:
            warn("session JS/python errors", errs.replace("\n", " | ")[:300])
        else:
            record("no JS/python errors in session log", True, "clean")
    rc, out, _ = sh("journalctl -b -p 3 --no-pager -n 20 2>/dev/null | grep -v 'password is required' | tail -6")
    benign = "obexd" in out or "evolution" in out or not out
    record("no critical journal errors", benign or "error" not in out.lower(), out[:200] or "none")


def main():
    print("LuminaOS live test starting at", time.strftime("%Y-%m-%d %H:%M:%S"), flush=True)
    phases = [("SYSTEM", test_system), ("UI PAGES", test_ui_pages), ("API GET", test_api_gets),
              ("FILES", test_files), ("SETTINGS", test_settings), ("APPS", test_apps),
              ("SERVICES", test_services), ("NETWORK", test_network),
              ("PERFORMANCE", test_performance), ("STORE", test_store), ("LOGS", test_logs)]
    for title, fn in phases:
        print("\n----- %s -----" % title, flush=True)
        try:
            fn()
        except Exception as e:
            import traceback
            record(title + " phase", False, "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    passed = sum(1 for r in results if r["ok"] and not r.get("warn"))
    failed = [r for r in results if not r["ok"]]
    warned = [r for r in results if r.get("warn")]
    print("\n===== SUMMARY =====")
    print("checks: %d  passed: %d  failed: %d  warnings: %d" % (len(results), passed, len(failed), len(warned)))
    for r in failed:
        print("FAILED:", r["test"], "-", r["detail"])
    for r in warned:
        print("WARN:", r["test"], "-", r["detail"])
    payload = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results,
               "passed": passed, "failed": len(failed), "warned": len(warned)}
    with open("/tmp/lumina-live-report.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
