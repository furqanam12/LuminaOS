# Architecture Guide

LuminaOS is a custom desktop built on a Debian 13 base. Its user interface is hosted by GTK/WebKitGTK windows, communicates through a local API, and delegates privileged work to focused package/container helpers.

## 1. Component map

| Component | Role |
|---|---|
| `src/bin/lumina-session` | Starts and restarts the desktop session; owns session-level startup wiring. |
| `src/bin/lumina-shell` | Hosts desktop, top bar, dock, toast and overlay surfaces on xfwm4 |
| `src/bin/lumina-app` | Creates managed windows for built-in applications; handles window geometry, actions and snapping |
| `src/bin/lumina-terminal` | Selects a concrete emulator, forwards commands safely and loads Kali profiles when requested |
| `src/lib/lumina/api.py` | Loopback HTTP + JSON + Server-Sent Events hub, file/device actions and local job notifications |
| `src/libexec/lumina-pkg` | Deliberately privileged package, update and optional repository operations |
| `src/libexec/lumina-android` | User-session Waydroid setup, nested Weston startup and APK installation |
| `src/libexec/kali-tools` | CLI security-tool reporting and installation routing |
| `src/data/store.json` | Store applications, package ecosystems and categories |
| `system/` | Live-session, GRUB, Calamares and installed-system configuration overlay |
| `build.sh` | Debian bootstrap, package installation, asset generation and hybrid ISO creation |

The UI under `src/ui/` contains the shell pages and built-in app surfaces. `src/ui/js/lumina.js` supplies the shared JavaScript client and actions.

## 2. Desktop rendering model

`lumina-shell` hosts separate WebKitGTK windows for desktop components. It uses WNCK and monitoring/layout information to position workspaces, top bar, dock and overlays.

`lumina-app` hosts higher-level application windows and supports:

- Per-application default dimensions and single-instance controls
- Client-side title bars with native window actions
- Snap layouts, resize areas and transparent rounding/shadows
- Loading the app's HTML from the local server with serialized launch arguments
- Message passing between web content and native GTK window management

The shell currently targets X11 with **xfwm4 compositing enabled**. This is deliberate for VM rendering stability. Android adds a nested Wayland compositor instead of silently replacing the whole desktop session.

On virtual machines, `lumina-session` and the window hosts set `WEBKIT_DISABLE_DMABUF_RENDERER=1` and `WEBKIT_DISABLE_COMPOSITING_MODE=1` before WebKit initialises. WebKitGTK 2.54's DMA-BUF path fails on VirtualBox/VMware/QEMU guests without usable 3D acceleration and can paint every shell window black. The software path is fast enough for this 2D desktop and keeps the glass styling intact. Set `LUMINA_WEBKIT_DMABUF=1` in `~/.config/lumina/env` to opt back into accelerated rendering on real GPU hardware.

## 3. Local API and event flow

The API listens on **`127.0.0.1:7700`** by default and does not require exposure to the LAN or internet.

| Mechanism | Purpose |
|---|---|
| GET routes | System information, settings, devices, files, Store and readiness checks |
| POST routes | Settings, mutation, jobs and launch/runtime actions |
| Server-Sent Events | Settings changes, UI commands, app notifications and Store job updates |
| Shared `Lumina` client | Shared HTTP, application, menu, dialog and settings operations |

Mutating routes require `X-Lumina-Token`, generated per boot and stored at `~/.cache/lumina/api-token` with owner-only permissions. Rate limiting and the audit log support basic local-host hardening; the audit log rotates at 1 MiB.

**Trust boundary:** the loopback API is not intended to be a network service. Do not bind it publicly, proxy it into the internet or publish its token.

## 4. Application installation and job state

The privileged helper runs through sudo for pre-authorized actions or pkexec for a user-mediated prompt. Package names, printer names and Bluetooth addresses are validated before command execution.

The Store distinguishes these jobs:

- **System packages** — privileged APT, Flatpak or file-install actions; progress is streamed through the helper output.
- **Windows launches** — direct Wine execution, represented as *Launched*, not an installed package.
- **APK jobs** — asynchronous user-runtime invocations; success is marked only after process exit zero.

Process-spawn failures are captured in the job rather than leaving a stuck “running” job. Empty or unsupported parameters are not silently forwarded to arbitrary commands.

## 5. Compatibility runtime separation

### Wine

`open_path()` selects specific Windows command forms. MSI and batch filenames are converted using `winepath` and sent to `msiexec` and `cmd` respectively. The file is not reclassified as a Debian package.

### Wayland and Android

`lumina-android` follows a readiness sequence:

1. Reject the live session and missing runtime tools.
2. Use an existing Wayland socket when available; otherwise start nested Weston on X11.
3. Initialize the Android image only if missing, using a privileged prompt.
4. Start the Waydroid container.
5. Wait for the Android session before installing an APK or reporting readiness.

This separation means the UI cannot honestly claim that the first button click installed the APK.

### Kali

Dedicated terminal launchers use argv arrays for profile paths and concrete emulator choice. They never invoke themselves through the `x-terminal-emulator` alternative. The package helper validates Kali's archive key, limits its trust to a signed-by keyring and removes the source if verification fails.

## 6. Settings and user data

Per-user configuration normally lives below:

```text
~/.config/lumina/
~/.cache/lumina/
```

Defaults cover appearance, performance, accessibility and notifications. Settings updates are applied consistently through the API/client and propagated to interested shell surfaces.

Processes use `start_new_session=True` for detached application launches, and file-opening helpers use safe path checks rather than shell interpolation. The `cwd` for terminal actions is validated and falls back to the user's home directory.

## 7. Performance design

- Shared CPU-time sampling and cached statistics reduce repeated system reads.
- Idle work is bounded in desktop, dock, top bar and Task Manager timers.
- Reduced-motion, transparency, dock magnification and shadow preferences are exposed in Settings.
- Balanced, custom and powersaver/low-power profiles coordinate the preferences.
- UI visibility changes and failed pollers release monitoring locks and resume appropriately.

**Performance claims require live measurement.** Host-source tests do not prove guest boot time, frame rate or memory percentages. Before/after comparisons in a guest should use the benchmark tool and an unchanged workload.

## 8. Build architecture

The release wrapper `tools/build-release.sh` checks the Linux host, tool availability and free space, runs source suites, invokes `build.sh`, and verifies the output SHA256.

The GitHub **build-iso** workflow runs this process on Ubuntu 24.04 when manually dispatched and uploads:

- `LuminaOS-1.1-amd64.iso`
- `LuminaOS-1.1-amd64.iso.sha256`
- `release/build-manifest.json`

Build output is an artifact for testing/distribution. Successful build plus matching checksum still requires guest boot/installer/installed-boot acceptance before a production sign-off.

## 9. Verification layers

| Layer | Purpose |
|---|---|
| Static/source tests | API routes, settings, installer files, package prerequisites, shell/JS syntax |
| Performance tests | Shared sampling, caching and UI monitoring behavior |
| Release checks | Documentation/read-only validator/WSL workflow safety/checksum manifest format |
| Live API suite | Non-destructive desktop and app checks in a booted guest |
| Guest validator | Expected files, Wine/compatibility endpoints, terminal/Kali support and accessibility state |
| VirtualBox acceptance | Actual live boot, installer, installed boot and user-facing checks |

Use `tools/test-live.py` for broad non-destructive interaction testing and `tools/validate-guest.py` for read-only built-image validation. Neither replaces a careful manual review of destructive operations such as repartitioning.

## 10. Extension guidelines

1. Reuse `Lumina` client APIs instead of duplicating HTTP and token handling.
2. Validate all user/package/device identifiers on the server.
3. Prefer user-session actions; require privilege only when unavoidable.
4. Never report completion before the actual operation exits successfully.
5. Keep unrelated user work out of a feature commit.
6. Add focused regression tests and update release counts/QA documentation together.

See [Contributing](../CONTRIBUTING.md) and the [API reference](../API.md) for implementation details.
