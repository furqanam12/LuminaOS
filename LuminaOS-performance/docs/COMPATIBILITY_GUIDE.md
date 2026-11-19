# Compatibility Guide

This guide explains how LuminaOS opens non-native program formats and the practical limits of each runtime.

> **Important:** LuminaOS uses compatibility layers and containers; it does not become Windows, Android or macOS. Per-application testing is essential. Always obtain software from a trusted source.

## 1. Format dispatch at a glance

| File format | Runtime or handler | What the UI reports |
|---|---|---|
| `.exe` | Wine | **Launched** |
| `.msi` | Wine `msiexec` | Installer launched; finish it inside Wine |
| `.bat` | Wine `cmd` | Windows command process launched |
| `.deb` | `lumina-pkg` / APT | Installation job |
| `.flatpakref`, `.flatpak` | Flatpak / Flathub | Installation job |
| `.AppImage` | Direct executable / FUSE | Launch or installation job, depending on entry point |
| `.rpm` | Alien, then package manager | Conversion/install job |
| `.snap` | Snap daemon | Installation job |
| `.apk` | Waydroid | User-runtime installation job |
| `.dmg`, `.pkg` | Compatibility / archive tools | Inspection or native alternatives |

**Never treat these formats as interchangeable archives.** Windows and APK files are deliberately kept out of the privileged Debian package installer.

## 2. Windows programs through Wine

The image prepares i386 package support and installs Wine32, Wine64 and Winetricks. Compatibility still depends on the Windows program.

### First-time setup

1. Open **Compatibility Wizard → Windows**.
2. Review the Wine and Wine-prefix checks.
3. Choose **Set up Wine** to initialise the prefix.
4. If a program needs additional runtimes, use **Winetricks** selectively.
5. Open the installer or executable from Files or Store.

Wine's first launch may take time while it creates the Windows environment. Do not repeatedly start installers if the first one is still configuring.

### Supported launch paths

- **Portable `.exe`**: starts through Wine. This is a launch, not a system installation.
- **MSI `.msi`**: LuminaOS converts the local filename to a Windows-compatible path and passes it to `wine msiexec /i`. Complete the vendor installer normally.
- **Batch file `.bat`**: opens with `wine cmd /c`.
- **Application not yet available**: LuminaOS opens the Compatibility Wizard rather than silently doing nothing.

### Practical Windows limitations

The following often need application-specific work or cannot be supported by Wine:

- Kernel drivers, protected storage drivers and low-level antivirus software
- Applications using unsupported activation, DRM or anti-cheat systems
- Programs requiring unavailable hardware dongles
- Some .NET, DirectX, Visual C++ or font dependencies
- Installers that need OS-specific reboot and service behavior
- ARM-only Windows executables on an x86-64 VM

**Recommended testing order:** a portable application first, then a small MSI, then your actual required application. Keep a copy of the original installer and save its exact version.

### Safe Winetricks use

Winetricks downloads and installs Windows components into the user's Wine prefix. Review every component; version mismatches can make an otherwise working application fail. Prefer a dedicated prefix for incompatible applications. Do not run unknown DLLs with root privileges.

### Bottles and Proton

Bottles and Steam/Proton are optional compatibility managers. They can simplify per-app environments, but they do not make every Windows game or app compatible. Size, GPU performance and anti-cheat restrictions still apply.

## 3. Android applications through Waydroid

Android requires **Waydroid, Weston, binder kernel support and an initialized container**. LuminaOS currently uses an X11 desktop, so Android runs inside a **nested Weston Wayland window**.

### Supported target

The automated setup path targets **Debian 13 (trixie)** and configures:

- The signed Debian `trixie-backports` source
- `waydroid` and `weston`
- The Waydroid container service
- On first use, a system image selected by the Waydroid initialization command

On unsupported distributions the helper stops with a clear message; it does not execute an unverified third-party installer as root.

### Setup and first launch

1. Use an **installed LuminaOS system**, not the live session.
2. Open **Compatibility Wizard → Android**.
3. Start **Set up Android support** and install the offered Waydroid package.
4. Click **Open Android**.
5. Allow the administrator prompts required for container/image setup.
6. Wait for the first image download and session startup. This can take several minutes and needs reliable internet access.
7. Install an APK through Files or Store and inspect the running job for its real result.

### APK installation behavior

The Store opens `lumina-android install /path/to/application.apk` as a user-runtime background job. Only an exit status of **zero** marks the job **Installed**. First-start, image, session, permission and package errors remain visible in the job log.

Do not judge an install by whether a window merely opened. Check the Android app list after the job succeeds.

### Important APK limitations

- **ARM-only APKs are not supported natively by an x86-64 VM.** They require a separately validated translation layer. LuminaOS does not silently claim to install such a layer.
- Android-x86-compatible APKs provide the best starting point.
- Applications requiring Google certification, SafetyNet/Play Integrity, GPS, telephony, NFC, camera or physical sensors may not work.
- Google-enabled images require the vendor download and potentially Google account verification/regional terms.
- Heavy games may be limited by virtual GPU performance and available memory.
- Waydroid does not make every Play Store application available or compatible.

## 4. Kali Linux Security Suite

LuminaOS provides a dedicated Kali-themed terminal and a security-tool manager. Most standard tools are installed from Debian; the optional Kali repository is explicitly configured only when requested.

### Open the terminal

- Open **Kali Terminal** from the application menu, or
- Run `lumina-terminal --kali`, or
- Use **Open in Kali Terminal** from the Files context menu.

The terminal sources `/etc/lumina/kali-profile.sh`, with a user-profile fallback. Standard terminal commands still work. Existing `x-terminal-emulator` alternatives remain attached to a real emulator, not a recursive wrapper.

### The `kali-tools` command

```sh
kali-tools list       # report installed security tools
kali-tools top10      # install the standard tool set
kali-tools web        # Burp Suite, SQLMap and Nikto, where available
kali-tools password   # Hashcat, Hydra and Medusa, where available
kali-tools msf        # Metasploit through the validated Lumina helper
```

### Metasploit and the optional Kali repository

1. Click **Configure Kali Repositories** in Compatibility Wizard.
2. Allow the key download and signature-checked source configuration.
3. Then select **Install Metasploit**.

Repository setup uses HTTPS, a scoped keyring and a low APT pin-priority. If key or repository signature verification fails, the source is removed and setup fails closed.

**Warning:** Kali is a rolling distribution. Mixing dependencies with Debian can introduce conflicts even with pinning. APT preview is essential for large Metasploit/security-tool installations. Do not approve an unreviewed full-system upgrade merely to make a package install succeed.

Security tools are dual-use software. Only scan systems and networks you own or have explicit authorization to test.

## 5. Linux desktop packages

- **Debian `.deb`**: installed through APT so dependencies can be resolved.
- **Flatpak**: Flathub and Sandbox configuration may be required.
- **AppImage**: launchable directly when the correct FUSE components and execute bit are present; a separate install action can place a trusted image in a system location.
- **RPM**: converted through Alien; distribution-specific scripts or dependencies may not translate perfectly.
- **Snap**: requires snapd and the system service/socket.

These package managers can modify your system and typically need an administrator prompt. Read the package source, dependencies and planned removals before continuing.

## 6. macOS files (optional)

DMG and PKG files can be inspected or extracted with the supported tools. Darling provides limited command-line translation where available. **Full graphical macOS application compatibility is not provided.** For daily work, select a maintained native Linux alternative when available.

## 7. What to include in a compatibility report

- File extension, package/application name and exact version
- Where the file came from and its checksum, if published
- Installed/runtime versions (Wine, Waydroid, Weston, Flatpak, etc.)
- Whether it works on the live session or installed system
- Full job log or error text; never just “it doesn't work”
- VM resource allocation and kernel/container support for Android

Use `tools/validate-guest.py` for runtime/file presence checks. That script does **not** install packages or change settings.
