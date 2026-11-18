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

### Notifications
- Action buttons.
- Snooze for 15 minutes.
- Quiet hours, including overnight schedules.
- Per-app Normal / Silent / Off rules.

### Compatibility
- New Compatibility Wizard.
- Wine setup and configuration.
- Flatpak/Store entry point.
- Waydroid status and live-session guard.

## Known limitations

- No ISO or guest validation is included in this source-only package.
- Performance improvements are implemented but not numerically measured in a guest.
- Android support remains experimental and unavailable in the live session.
- Windows application compatibility remains app-dependent.
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
