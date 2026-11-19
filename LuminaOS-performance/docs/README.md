# LuminaOS Documentation

**Edition:** LuminaOS 1.1 — Aurora Update 1  
**Documentation revision:** 1.0  
**Last reviewed:** 20 November 2026  
**Audience:** new users, VirtualBox testers, developers and release maintainers

Welcome to the official documentation set for LuminaOS. These guides describe the features implemented in the source tree, safe installation practices, compatibility boundaries and the release-verification process.

> **Read this first:** a source test is not the same as acceptance testing a booted ISO. For release readiness, always consult [`release/RELEASE_STATUS.md`](../release/RELEASE_STATUS.md), the checksum and the guest-validation results. Compatibility depends on the application, hardware and runtime; no operating system can guarantee every Windows, Android or macOS application.

## Start here

| Guide | Purpose |
|---|---|
| **[User guide](USER_GUIDE.md)** | Desktop, built-in apps, settings, files, keyboard shortcuts and daily use |
| **[Compatibility guide](COMPATIBILITY_GUIDE.md)** | Windows, Android, Kali and Linux package support with concrete setup steps |
| **[Build and deployment guide](BUILD_AND_DEPLOY.md)** | Reproducible ISO builds, artifact downloads, VirtualBox setup and guest acceptance |
| **[Architecture guide](ARCHITECTURE.md)** | Shell, API, window hosting, package helpers, security boundaries and testing |
| **[Share LuminaOS with a friend](SHARE_WITH_FRIEND.md)** | A concise companion checklist for sharing the ISO |
| **[API reference](../API.md)** | Complete local HTTP/SSE endpoint reference |
| **[Troubleshooting](../TROUBLESHOOTING.md)** | Boot, UI, device, package and compatibility fixes |
| **[Contributing](../CONTRIBUTING.md)** | Coding conventions, test commands and pull-request workflow |

## Downloadable documentation

The generated, professionally formatted versions are:

- `docs/index.html` — searchable on-screen manual with print layout
- `docs/LuminaOS-Documentation.pdf` — offline/shareable manual

Regenerate them after editing any Markdown file in this directory:

```sh
cd LuminaOS-performance
python3 tools/build-docs.py
```

If Google Chrome or Microsoft Edge is installed, the script also generates the PDF automatically. Otherwise the always-current Markdown and HTML documentation remain available. No third-party Python packages are needed.

## What LuminaOS provides

- A custom **Lumina Shell** with desktop, dock, top bar, Start/overlay surfaces, workspaces and notifications.
- Built-in **Files, Settings, Store, Task Manager, Notepad, Calculator, Photos, Snipping Tool, About, Setup and Compatibility Wizard** applications.
- A local, loopback-only desktop API using JSON and Server-Sent Events.
- Performance controls, accessibility options, window management and persistent per-user settings.
- Printer and Bluetooth management, CUPS integration, Orca/AT-SPI support and clipboard history.
- Route-specific runtimes for Windows programs, Android APKs and common Linux package formats.
- An automated host-test CI workflow and a manually dispatched GitHub Actions ISO build with checksum artifacts.

## Documentation conventions

- **Recommended**: a tested or safer option, not a mandatory requirement.
- **Warning**: an operation that may need administrator access, modify the host or lose unsaved work.
- **Note**: an important version, hardware or compatibility constraint.
- Commands beginning with `sudo` or `pkexec` modify the system; understand the action before approving a prompt.
- Absolute operating-system paths describe the **guest**, not the Windows host.

## Support and evidence

When asking for help, include:

1. LuminaOS version, host OS and VirtualBox version.
2. Live session or installed system.
3. Exact application/package name and format.
4. The complete error message, screenshots and logs where available.
5. Output from the relevant checklist in `docs/BUILD_AND_DEPLOY.md`.

Do not share your API token, password, private SSH key or other credentials in bug reports.

---

**Project:** https://github.com/furqanam12/LuminaOS  
**Release evidence:** [`release/QA_MATRIX.md`](../release/QA_MATRIX.md) · [`release/RELEASE_CHECKLIST.md`](../release/RELEASE_CHECKLIST.md)
