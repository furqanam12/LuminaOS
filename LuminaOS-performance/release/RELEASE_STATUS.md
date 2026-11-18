# LuminaOS 1.1 release status

**Status:** source complete; ISO and guest validation pending.

## Completed

- Performance implementation: 1.1 patch.
- Installer and first-run implementation.
- Accessibility and command palette implementation.
- Files, notification and compatibility implementation.
- Version set to **1.1** in `build.sh`.
- VM creator examples updated to `LuminaOS-1.1-amd64.iso`.
- Release notes, QA matrix, build guide, checklist and sign-off template written.
- Automated source validation:
  - `tools/test-features.py`: 10/10 passed.
  - `tools/test-installer.py`: 8/8 passed.
  - `tools/test-performance.py`: 46/46 passed.
  - `tools/test-performance.js`: 25/25 passed.

## Not completed

- No ISO was built.
- No checksum for a 1.1 ISO exists yet.
- No virtual machine was booted.
- No live-session, installer, installed-boot or feature acceptance test was run in a guest.
- No performance percentages are claimed.

## Host assessment

The Windows preparation host reported approximately **7 GB free** on the workspace drive (`C:`). The build script requires at least **8 GB**, and roughly 12 GB is recommended. `VBoxManage` was not detected. The WSL status check was blocked by the local command-safety policy.

## WSL2 workflow

A non-destructive WSL2-on-E: workflow has been added under `release/wsl2/`. It exports a copy of an existing WSL distro to `E:\LuminaOS-WSL`, imports it as `LuminaBuild`, stages the source inside the WSL ext4 filesystem, builds the ISO, and copies artifacts to `E:\LuminaOS-Artifacts`. It does not unregister the original distro.

## Required next action

Move or copy the source to a Linux filesystem with at least 8 GB free, then run:

```bash
chmod +x tools/build-release.sh tools/validate-guest.py
./tools/build-release.sh
```

After the ISO is built, boot it using the commands in `release/BUILD_AND_ACCEPTANCE.md`, run `tools/validate-guest.py` inside the guest, and complete `release/RELEASE_CHECKLIST.md`.
