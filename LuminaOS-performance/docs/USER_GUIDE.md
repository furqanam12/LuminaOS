# LuminaOS User Guide

## 1. Before you begin

LuminaOS can be run live from an ISO or installed on a virtual disk. For normal daily use, install it to a VirtualBox disk and install Guest Additions.

**Recommended VirtualBox resources**

| Resource | Minimum | Recommended |
|---|---:|---:|
| Memory | 4 GB | 8 GB |
| Virtual CPUs | 2 | 4 |
| Dynamically allocated VDI disk | 20 GB | 40 GB or more |
| Video memory | 128 MB | 256 MB |
| Graphics controller | VBoxVGA | VBoxVGA with 3D acceleration |

For exact VM creation steps, see [Share LuminaOS with a friend](SHARE_WITH_FRIEND.md).

### Live session versus installed mode

- **Live session**: evaluate the desktop without changing the virtual disk. Some features, especially Android images and full first-run setup, require installation.
- **Installed mode**: persistent applications, settings, accounts, updates and compatibility runtimes. Use your account password for administrator prompts.

## 2. Desktop tour

| Area | What you can do |
|---|---|
| **Top bar** | See time, system status, network and sound controls |
| **Dock** | Launch pinned applications, switch running apps and manage windows |
| **Start / overlay** | Find applications, settings, commands and files |
| **Launchpad** | Browse installed apps in a grid |
| **Control Centre** | Change common connectivity and appearance settings |
| **Notification Centre** | Read alerts and use actions such as snooze |
| **Task View** | Review windows and switch workspaces |
| **Desktop** | Open user files, folders and desktop launchers |

### Common keyboard shortcuts

| Shortcut | Action |
|---|---|
| **Super** | Open Start |
| **Super + A** | Control Centre |
| **Super + E** | File Explorer |
| **Super + L** | Lock screen |
| **Ctrl + K** | Command palette |
| **Ctrl + T** | New Files tab |
| **Ctrl + L** | Files address entry |
| **F2** | Rename selected file |
| **Tab / Shift + Tab** | Move between controls |
| **Enter / Space** | Activate a focused control |
| **Escape** | Close a menu or overlay |

## 3. Built-in applications

### File Explorer

Use Files to browse your home folder, mounted devices and shared locations. It supports:

- Grid/list views, search, sort, tabs and split view
- Create, rename, copy, move and delete operations
- Undo/redo for common operations and conflict handling
- ZIP/TAR extraction, ZIP creation, file permissions and Trash restore
- Recent files, Quick Access and a detailed status bar
- **Open in Terminal** and **Open in Kali Terminal** in the current directory

For package files, use the format-specific procedure in the [Compatibility guide](COMPATIBILITY_GUIDE.md).

### Lumina Store

Install or remove catalogued applications, inspect package downloads, install supported local package files and apply updates. The **Library** shows running jobs and their result.

> A Windows `.exe` launch is labelled **Launched**, not Installed. An Android APK installation is only marked complete after the runtime returns success.

### Settings

Major sections include:

- **System and display**: host information, theme, brightness preferences, night light and output resolution
- **Sound**: volume, mute and system sounds
- **Notifications**: focus mode, quiet hours and per-application rules
- **Bluetooth & devices**: adapter power, scanning, pairing, connection and removal; pointer speed
- **Network**: adapters, Wi-Fi connections and advanced settings
- **Personalisation**: theme, accent, wallpaper, dock and effects
- **Power & performance**: lock, sleep, restart, shutdown and performance presets
- **Printers**: add CUPS printers and choose a default printer
- **Accessibility**: interface scale, contrast, focus outlines, animation and screen reader
- **Clipboard**: history management
- **Time & language**: time zone and 24-hour clock
- **Backup & restore**: export/import settings and update preferences

### Task Manager and utilities

- **Task Manager**: processes, resource use and performance history
- **Notepad**: tabs, find/replace, editing and file status
- **Calculator**: standard operations and history
- **Photos**: image browsing and viewing
- **Snipping Tool**: screenshots with capture options
- **About**: version and device details
- **Compatibility Wizard**: environment checks and runtime setup

## 4. Accounts and passwords

To create an account, go to **Settings → User accounts** and enter a unique username, password and confirmation.

- Use lowercase usernames beginning with a letter or underscore.
- Passwords must be at least four characters; use a strong, unique password in practice.
- Account creation assigns a login shell and home directory.
- Do not delete your active account. Keep a working administrator account.

Changing your password requires your current password. Never send credentials or API tokens in screenshots or support messages.

## 5. Accessibility

The following settings are available:

- Interface scale from **80% to 150%**
- High-contrast palettes and stronger focus indicators
- Reduced animation and solid/transparency preferences
- Orca screen-reader integration through AT-SPI

For Orca, open **Settings → Accessibility → Screen reader**. The page reports whether it is installed and switches the toolkit accessibility bridge and autostart entry. If your screen reader does not announce an app, check the troubleshooting guide and the AT-SPI bus log; do not install packages without understanding the proposed change.

## 6. Devices, network and printing

### Bluetooth

An adapter is required. On VirtualBox, pass through a USB Bluetooth adapter if necessary. Then:

1. Turn on Bluetooth power.
2. Put the peripheral into pairing mode.
3. Select **Scan for devices**.
4. Choose **Pair**, **Connect** or **Remove** as appropriate.

Pairing may require a confirmation PIN on both devices. Pairing audio hardware is not guaranteed on a VM without working pass-through support.

### Wi-Fi and wired networking

The Network page reads NetworkManager state. Choose a visible network and supply the security key if required. Wired connections normally work automatically in NAT mode.

### Printers

The default CUPS packages are included in the image. To add a printer:

1. Connect the printer or verify that its network address is reachable.
2. Open **Settings → Printers**.
3. Give it a simple name using letters, numbers, `.`, `_` or `-`, and enter the correct device URI, for example `socket://192.168.1.50:9100`.
4. Select **Add printer**.
5. Optionally choose **Set as default**.

CUPS model drivers may still be necessary for specialised features such as duplexing or manufacturer-specific finishing options.

## 7. Windows and Android applications

These require separate runtimes. They are not native ELF Linux programs.

- For `.exe`, `.msi` and `.bat`, use **Compatibility Wizard → Windows programs**.
- For `.apk`, use **Compatibility Wizard → Android** on an installed system, prepare the image and open the nested Android window.

The exact preparation, constraints and error messages are in the [Compatibility guide](COMPATIBILITY_GUIDE.md). Read the important notes before installing third-party executables.

## 8. Power and updates

**Power** offers lock, sleep, restart and shutdown commands. Restart and shutdown ask for confirmation, but closing applications can still lose unsaved work.

Before updating:

1. Save documents and close running installers.
2. Confirm internet access and sufficient disk space.
3. Check updates from Settings or Store.
4. Wait for jobs to finish; do not power off during package configuration.

The live guest should never be rebooted by an automated test without your consent.

## 9. Everyday safety checklist

- Only run Windows, Android and Linux packages from sources you trust.
- Do not execute random terminal commands from untrusted websites.
- Back up files before changing partitions or performing an installation.
- Keep at least one tested, bootable copy of your working ISO.
- Install updates deliberately, not in the middle of another installer.
- Restore demo settings after testing if you share an existing VM.

## 10. Getting help

Use [Troubleshooting](../TROUBLESHOOTING.md) for boot, display, API, Store and runtime failures. For VM-first guidance and checksum verification, see [Build and deployment](BUILD_AND_DEPLOY.md).
