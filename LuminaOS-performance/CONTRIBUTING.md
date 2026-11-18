# Contributing to LuminaOS

Thank you for wanting to contribute to LuminaOS! This guide covers how to get started, the project structure, and the conventions we follow.

## Project Overview

LuminaOS is a desktop operating system built on Debian 13 (trixie) with a custom shell written in Python (GTK3 + WebKitGTK 4.1) and HTML/CSS/JS for the UI.

**Design languages:** Windows 11 layout, macOS motion, HarmonyOS softness.

```
GRUB ─► Plymouth ─► LightDM autologin ─► lumina-session
                                    │
                                    xfwm4 (window manager)
                                    lumina-shell (Python + GTK3 + WebKitGTK)
                                      ├─ desktop / topbar / dock / overlay
                                      ├─ API (HTTP + SSE on 127.0.0.1:7700)
                                      └─ lumina-app (per-app WebKit windows)
```

## Repository Layout

```
LuminaOS-performance/
├── build.sh                  # ISO builder (debootstrap chroot → squashfs → grub-mkrescue)
├── iso-grub.cfg              # GRUB menu entries
├── packages.list             # Extra Debian packages for the live system
├── REPORT.md                 # Project report
├── API.md                    # API reference (this repo)
├── CONTRIBUTING.md           # This file
├── src/
│   ├── bin/                  # Executable entry points
│   │   ├── lumina-shell      # Main shell (window manager + API server)
│   │   ├── lumina-app        # Per-app WebKitGTK host window
│   │   ├── lumina-session    # X session startup script
│   │   ├── lumina-install    # Installer launcher
│   │   └── lumina-ctl        # Send UI commands to the shell
│   ├── lib/lumina/
│   │   └── api.py            # HTTP + SSE API hub (60+ endpoints)
│   ├── libexec/
│   │   └── lumina-pkg        # Privileged package helper (apt/flatpak)
│   ├── ui/
│   │   ├── desktop.html      # Desktop window
│   │   ├── topbar.html       # Top bar
│   │   ├── dock.html         # Dock
│   │   ├── overlay.html      # Start / Control Centre / Launchpad / etc.
│   │   ├── toasts.html       # Toast notifications
│   │   ├── css/
│   │   │   ├── lumina.css    # Design system (colors, animations)
│   │   │   ├── overlay.css   # Overlay-specific styles
│   │   │   └── window.css    # App window chrome
│   │   ├── js/
│   │   │   ├── lumina.js     # Shared client library (API, settings, shortcuts)
│   │   │   └── window.js     # Per-app window chrome (captions, snap)
│   │   └── apps/
│   │       ├── files.html    # File Explorer
│   │       ├── settings.html # Settings app
│   │       ├── taskmgr.html  # Task Manager
│   │       ├── notepad.html  # Notepad
│   │       ├── calculator.html
│   │       ├── snip.html     # Snipping Tool
│   │       ├── store.html    # Lumina Store
│   │       ├── photos.html   # Photos
│   │       ├── welcome.html  # Welcome screen
│   │       ├── setup.html    # First-run setup
│   │       ├── about.html    # About
│   │       ├── compat.html   # Windows/Android compatibility
│   │       └── terminal.html
│   └── data/
│       ├── store.json        # Lumina Store catalog
│       └── applications/     # .desktop files for built-in apps
└── tools/
    ├── gen-icons.py          # Generate app icons from SVG
    ├── gen-xfwm.py           # Generate xfwm4 window theme
    └── gen-brand.sh          # Generate boot branding (GRUB, Plymouth)
```

## How to Contribute

### 1. Fork and Clone

There is no central git repository yet — the project ships as source tarballs. Copy the `src/` tree to your working directory and make changes there.

### 2. Make Changes

- **Python API changes:** Edit `src/lib/lumina/api.py`
- **Shell changes:** Edit `src/bin/lumina-shell`
- **App entry points:** Edit `src/bin/lumina-app`, `lumina-ctl`, etc.
- **UI changes:** Edit files under `src/ui/` (HTML, CSS, JS)
- **Package helper:** Edit `src/libexec/lumina-pkg`
- **Build changes:** Edit `build.sh`, `packages.list`, `iso-grub.cfg`

### 3. Conventions

- **Python:** Follow PEP 8. Use 4-space indentation. Wrap subprocess calls in try/except. Return `{"ok": True/False, ...}` dicts from API functions.
- **JavaScript:** Use the existing `Lumina` object pattern (`window.Lumina`). Keep functions small and focused. Use `L.get()` / `L.post()` for API calls.
- **CSS:** Use CSS custom properties (`--accent`, `--shadow`, etc.) from `lumina.css`. Follow the existing BEM-like naming (`.block__element--modifier`).
- **Shell scripts:** Use `set -e`. Validate all user input in `lumina-pkg` (package names are whitelisted).

### 4. Testing

- **Syntax check Python:** `python3 -m py_compile src/lib/lumina/api.py`
- **Syntax check JS:** Open the HTML file in a browser with developer tools
- **Shell:** `sh -n src/libexec/lumina-pkg`
- **Full test:** Build the ISO with `./build.sh` (requires Debian/Ubuntu, ~8 GB disk, sudo) and boot in VirtualBox

### 5. Submitting Changes

Since there is no central git host yet, share your changes as:
- A unified diff (`diff -u`)
- A patched source tree
- A description of what changed and why

## Areas That Need Help

- Unit tests for `api.py` (no test suite exists yet)
- Integration tests (automated VM boot + API checks)
- More Settings panels (Bluetooth pairing, Wi-Fi management, power profiles)
- Accessibility improvements (screen reader support, high-contrast mode)
- Performance tuning for older hardware
- Documentation improvements

## License

LuminaOS is original artwork and code. No third-party trademarks or code are used. The base Debian system remains under its own licenses. Wallpapers are CC BY-SA / CC BY licensed (see `REPORT.md` for credits).