#!/usr/bin/env python3
"""Read-only LuminaOS guest validation for a built 1.1 ISO.

Run inside the live or installed guest:
    python3 tools/validate-guest.py

It checks the local API, expected files, and key configuration. It does not
modify settings, install packages, run a VM, or access the internet.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:7700"
FILES = {
    "Lumina shell": "/usr/bin/lumina-shell",
    "App host": "/usr/bin/lumina-app",
    "Installer helper": "/usr/bin/lumina-install",
    "Installer launcher": "/usr/share/applications/lumina-install.desktop",
    "Desktop installer shortcut": "/etc/skel/Desktop/Install LuminaOS.desktop",
    "Setup app": "/usr/share/lumina/ui/apps/setup.html",
    "Compatibility app": "/usr/share/lumina/ui/apps/compat.html",
    "Universal terminal": "/usr/bin/lumina-terminal",
    "Kali Terminal launcher": "/usr/share/applications/lumina-kali-terminal.desktop",
    "Kali session profile": "/etc/lumina/kali-profile.sh",
    "Kali tools CLI": "/usr/local/bin/kali-tools",
    "Android nested-Wayland launcher": "/usr/libexec/lumina/lumina-android",
    "Universal MIME associations": "/usr/share/mime/packages/lumina-os-mime.xml",
    "Wine Windows runtime": "/usr/bin/wine",
    "Files app": "/usr/share/lumina/ui/apps/files.html",
    "Accessibility page": "/usr/share/lumina/ui/apps/settings.html",
    "Command palette overlay": "/usr/share/lumina/ui/overlay.html",
    "GRUB theme": "/boot/grub/themes/lumina/theme.txt",
    "Recovery hook": "/etc/grub.d/45_lumina_recovery",
    "Keyboard shortcuts": "/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml",
}
SETTING_KEYS = [
    "theme", "accent", "wallpaper", "reduceMotion", "transparency", "dockMagnify",
    "perfShadows", "performancePreset", "uiScale", "highContrast", "strongFocus",
    "screenReader",
    "focus", "focusUntil", "quietStart", "quietEnd", "notificationRules", "widgets",
]


def api(path):
    with urllib.request.urlopen(BASE + path, timeout=8) as response:
        return json.load(response)


def main():
    global BASE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE, help="Local Lumina API origin")
    parser.add_argument("--session", choices=("auto", "live", "installed"), default="auto",
                        help="Expected guest session type. Default: detect from /api/sys")
    args = parser.parse_args()
    if not args.base.startswith("http://127.0.0.1:") and not args.base.startswith("http://localhost:"):
        parser.error("Only a loopback Lumina API origin is allowed")
    BASE = args.base.rstrip("/")

    results = []
    def check(name, ok, detail=""):
        results.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    try:
        settings = api("/api/settings")
        sysinfo = api("/api/sys")
        first_run = api("/api/first-run/status")
        boot_checks = api("/api/system/check")
        compat = api("/api/compat")
        a11y = api("/api/a11y")
        bluetooth = api("/api/bt")
        terminal = api("/api/terminal/status")
        apps = api("/api/apps")
        zones = api("/api/timezones")
        notifications = api("/api/notifications")
    except Exception as e:
        print(json.dumps({"ok": False, "error": "Local API unavailable: " + str(e),
                          "checks": results}, indent=2))
        return 1

    check("Local API", True, "127.0.0.1:7700 responding")
    missing = [k for k in SETTING_KEYS if k not in settings]
    check("Settings schema", not missing, "missing: " + ", ".join(missing) if missing else "all keys present")
    check("Performance preset", settings.get("performancePreset") in ("custom", "balanced", "low-power"),
          settings.get("performancePreset"))
    check("Accessibility scale", 80 <= int(settings.get("uiScale") or 100) <= 150, settings.get("uiScale"))
    check("System information", bool(sysinfo.get("user") and sysinfo.get("os")), sysinfo.get("os", ""))
    check("First-run API", "live" in first_run and "complete" in first_run,
          "live=%s complete=%s" % (first_run.get("live"), first_run.get("complete")))
    is_live = bool(sysinfo.get("live")) if args.session == "auto" else args.session == "live"
    check("Session mode", True, "live session" if is_live else "installed")
    installed_checks = boot_checks.get("checks", [])
    if is_live:
        check("Installed-boot checks", True, "not applicable during live-session evaluation")
    else:
        check("System checks", bool(boot_checks.get("ok")),
              "%s/%s checks OK" % (sum(1 for c in installed_checks if c.get("ok")), len(installed_checks)))
    check("Windows and Android compatibility API", all(k in compat for k in ("wine", "flatpak", "waydroid", "weston", "binder")), str(compat)[:160])
    check("Accessibility state", all(k in a11y for k in ("screenReader", "installed", "atspi")), a11y.get("installed", "unknown"))
    check("Bluetooth state", all(k in bluetooth for k in ("available", "powered", "devices")), "adapter available" if bluetooth.get("available") else "no adapter (valid on VM)")
    check("Terminal status", bool(terminal.get("ok") and terminal.get("installed")), terminal.get("installed", []))
    check("App catalogue", len(apps) > 0, "%s apps" % len(apps))
    check("Time zones", len(zones.get("zones") or []) > 0, str(zones.get("current", "")))
    check("Notification centre", isinstance(notifications, list), "%s notifications" % len(notifications))

    for name, path in FILES.items():
        check(name, os.path.exists(path), path)

    if is_live:
        check("Installed GRUB recovery", True, "not applicable during live-session evaluation")
    else:
        try:
            grub = open("/boot/grub/grub.cfg", encoding="utf-8", errors="ignore").read().lower()
            check("GRUB safe graphics entry", "safe graphics" in grub, "/boot/grub/grub.cfg")
        except Exception as e:
            check("GRUB safe graphics entry", False, str(e))
    try:
        shortcuts = open(FILES["Keyboard shortcuts"], encoding="utf-8", errors="ignore").read()
        check("Command palette shortcut", "lumina-ctl command" in shortcuts and "&lt;Primary&gt;k" in shortcuts,
              "Ctrl+K")
    except Exception as e:
        check("Command palette shortcut", False, str(e))

    ok = all(c["ok"] for c in results)
    print(json.dumps({"ok": ok, "summary": "%s/%s checks passed" % (
        sum(1 for c in results if c["ok"]), len(results)), "checks": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
