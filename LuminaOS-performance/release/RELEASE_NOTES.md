# LuminaOS 1.1 “Aurora Update 1” — release notes

LuminaOS 1.1 is an update to the 1.0 Aurora release. It keeps the same design language and system architecture while adding performance controls, a cleaner installer experience, first-run setup, accessibility options, productivity improvements and compatibility tooling.

## Highlights

### Performance
- Balanced and VM / low-power presets.
- Reduced motion, transparency, dock magnification and shadow control.
- Shared CPU-time sampling and one-second statistics cache.
- Less idle work in desktop icons, dock, top bar and Task Manager.
- Read-only benchmark tool for before/after comparison.

### Installer and first run
- Branded `lumina-install` launcher and correctly named desktop shortcut.
- Generic Calamares launchers hidden from the application list.
- Installed systems open a guided setup wizard once.
- Installed GRUB safe-graphics recovery entry.
- `.desktop` files in the Desktop folder display their real name and icon.

### Accessibility
- Interface scale from 80% to 150% for built-in application windows.
- High-contrast dark and light palettes.
- Strong keyboard focus indicator.
- Keyboard activation for common clickable controls.
- Orca screen-reader integration with AT-SPI, autostart and a Settings toggle.
- Settings → Accessibility page.

### Command palette
- Ctrl+K opens a searchable palette for apps, settings and actions.
- Keyboard navigation with arrows, Enter and Escape.

### File Explorer
- Undo / redo for common operations.
- Split view with independent navigation and drag-and-drop.
- Keep both / Replace / Skip conflict handling.
- ZIP/TAR extraction, ZIP creation and permissions editing.
- Ctrl+L address editing and Trash restore support.
- Loading skeleton while the first folder listing is fetched.

### Notifications
- Action buttons.
- Snooze for 15 minutes.
- Quiet hours, including overnight schedules.
- Per-app Normal / Silent / Off rules.

### Devices and printing
- Bluetooth adapter power, scanning, pairing, connecting and device removal.
- Printer management with validated add and set-default actions.

### Security and reliability
- Rotating API audit log (1 MiB) so unattended desktops cannot grow it without bound.
- Token protection extended to the new printer, Bluetooth and accessibility actions.

## Compatibility and distribution
- Package-file handling for Windows executables and installers, Linux packages, and Android APKs; each is dispatched to the correct runtime instead of a generic installer.
- Compatibility wizard with Windows (Wine), Kali Linux, Flatpak, AppImage, macOS, and Android tabs.
- Kali Linux Security Suite with dedicated Kali terminal, kali-tools CLI, pinned repos, and one-click tool installers.
- lumina-terminal as default x-terminal-emulator with robust multi-terminal fallback.
- File associations for Windows, Android, macOS and AppImage packages.

## Known limitations

- No ISO or guest validation is included in this source-only package.
- Performance improvements are implemented but not numerically measured in a guest.
- Android support is experimental: on Debian 13 the backports Waydroid package and a nested Weston Wayland window are used. It requires binder support, an initialized image and an installed system. ARM-only APKs need a separate translation layer and are not guaranteed to work.
- Windows application compatibility remains app-dependent.
- Bluetooth and Orca screen-reader behavior could not be validated in the installed 1.0 guest (no Bluetooth adapter; Orca not installed).
- Compositing is intentionally kept enabled; disabling it caused black areas in VirtualBox on 1.0.

## Build

```bash
sudo bash build.sh
```

Output:

```text
LuminaOS-1.1-amd64.iso
LuminaOS-1.1-amd64.iso.sha256
```

See `release/BUILD_AND_ACCEPTANCE.md` for the full workflow.

## Upgrade note

This is not an in-place upgrade package. Build the ISO, boot it, and perform a clean installation or validate manually before replacing production media.
