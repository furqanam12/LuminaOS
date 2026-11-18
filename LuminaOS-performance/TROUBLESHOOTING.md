# LuminaOS Troubleshooting

Common issues and how to fix them.

## Boot & Installation

### Black screen after GRUB
**Cause:** Graphics driver issue in the live session.
**Fix:** At the GRUB menu, choose **"Start LuminaOS (safe graphics)"** which adds `nomodeset`. If the installed system has this problem, edit `/etc/default/grub.d/lumina.cfg` and add `nomodeset` to `GRUB_CMDLINE_LINUX_DEFAULT`, then run `update-grub`.

### QEMU shows black screen with `-vga vmware`
**Cause:** The vmwgfx driver doesn't support the resolution used by LuminaOS.
**Fix:** Use `-vga std` or virtio instead of `-vga vmware`. VirtualBox VMSVGA works fine.

### Installer shows generic Calamares launchers
**Cause:** This was fixed in the current source. If you see old launchers, rebuild from the latest `src/` tree or use the branded **"Install LuminaOS"** desktop shortcut.

## Live Session

### Wi-Fi not working
**Cause:** NetworkManager may not have started, or firmware is missing.
**Fix:** Check `nmcli networking` output. Ensure `firmware-linux` and `firmware-iwlwifi` are installed (they are in the base package list). Try `sudo systemctl restart NetworkManager`.

### SSH not reachable from host
**Cause:** The NAT port-forward rule hasn't been created, or sshd isn't running in the guest.
**Fix:** Run `LuminaOS Terminal.cmd` from Windows — it sets up the port forward automatically. If that fails, inside the VM run:
```
curl -s 10.0.2.2:8000/lumina-ssh.sh | sh
```
(You need `python -m http.server 8000` serving `$env:TEMP\\opencode\\www` on the host.)

## Shell & UI

### Glass/transparency is slow or CPU-bound
**Cause:** WebKit hardware acceleration is forcing GPU compositing on a VM without 3D.
**Fix:** The shell now auto-detects VirtualBox/VMware/QEMU and sets `LUMINA_GPU=never`. To override, run:
```
LUMINA_GPU=always lumina-shell
```
or set `LUMINA_GPU=never` to force software rendering everywhere.

### Animations feel sluggish
**Cause:** `reduceMotion` is off on slower hardware.
**Fix:** Open Settings → Personalisation → Effects and turn off **"Animation effects"**, or set `reduceMotion: true` in `~/.config/lumina/settings.json`.

### Settings changes don't persist
**Cause:** The settings file (`~/.config/lumina/settings.json`) may not be writable, or the shell crashed before writing.
**Fix:** Check `~/.cache/lumina-shell.log` for errors. Ensure `~/.config/lumina/` exists and is writable.

## API

### `401 authentication required` from the API
**Cause:** A mutating POST was made without a valid `X-Lumina-Token`.
**Fix:** The JS client (`lumina.js`) handles this automatically — it fetches a token from `/api/auth/token` and retries. If calling the API manually, first GET `/api/auth/token`, then send `X-Lumina-Token` on subsequent POSTs.

### API endpoint returns 500
**Cause:** A subprocess call failed (e.g. `nmcli`, `xrandr`, `systemctl` not available).
**Fix:** Check `~/.cache/lumina-shell.log` for the Python traceback. Ensure the required tool is installed (`nmcli`, `xrandr`, `maim`, `xclip`, etc. are in `packages.list`).

## Store & Updates

### "No internet connection" when installing from Store
**Cause:** Network is down or `nmcli networking` is disabled.
**Fix:** Check connectivity with `nmcli networking`. If offline, connect to Wi-Fi from Settings → Network first.

### Waydroid / Android setup fails
**Cause:** The installer script download failed or the kernel lacks binder support.
**Fix:** `lumina-pkg` now downloads the installer to a temp file before executing (no `curl | bash`). Check `/tmp` for the downloaded script if it fails. Binder support requires a kernel with `CONFIG_ANDROID_BINDERFS`.

## Building

### `build.sh` fails at debootstrap
**Cause:** Missing build dependencies or no network access to Debian mirrors.
**Fix:** Install the host tools listed in `build.sh` (`debootstrap`, `squashfs-tools`, `xorriso`, `grub-pc-bin`, etc.) and ensure you can reach `deb.debian.org`.

### ISO is too large (784 MB)
**Cause:** Firefox ESR and many packages are included.
**Fix:** Remove optional packages from `packages.list` (e.g. `firefox-esr`) and rebuild.

## Logs

| Log | Location |
|-----|----------|
| Shell output | `~/.cache/lumina-shell.log` |
| API errors | Printed to shell stdout (captured in shell log) |
| App errors | Printed per-app to `~/.cache/` (per-app log) |
| Store job logs | `~/.cache/lumina/job-*.log` |

Still stuck? Open an issue with your `REPORT.md` version, hardware details (VM or bare metal), and relevant log excerpts.