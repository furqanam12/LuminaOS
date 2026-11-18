# WSL2 on E: — build workflow

This workflow keeps WSL build data on `E:`, which has about 29 GB free. It does **not** unregister or delete an existing Ubuntu distro. It exports a copy into a new distro named `LuminaBuild`, imported from `E:`.

## Files

| File | Purpose |
|---|---|
| `prepare-wsl2.ps1` | Installs/imports a build distro onto `E:` and warns before stopping WSL |
| `wsl-build.sh` | Runs inside WSL: installs dependencies, stages source, tests, builds ISO, copies artifacts to `E:` |
| `build-in-wsl.ps1` | Windows wrapper that invokes `wsl-build.sh` in `LuminaBuild` |
| `vm-acceptance.ps1` | Creates/starts a VirtualBox VM from the built ISO if VirtualBox is installed |

## Step 1 — prepare WSL2

Open **PowerShell as Administrator** if WSL is not installed yet:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
cd "C:\Users\Muhammad Furqan Amin\Downloads\New folder\LuminaOS-performance"
.\release\wsl2\prepare-wsl2.ps1
```

If WSL is not installed, install Ubuntu first:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart Windows when prompted, then rerun `prepare-wsl2.ps1`.

The script:

- Creates `E:\LuminaOS-WSL`.
- Exports an existing Ubuntu/Debian distro to an archive on `E:`.
- Imports it as `LuminaBuild` with its filesystem on `E:`.
- Leaves the original distro installed.
- Calls `wsl --shutdown` only after a warning, because a clean export requires it.

## Step 2 — build the ISO

```powershell
cd "C:\Users\Muhammad Furqan Amin\Downloads\New folder\LuminaOS-performance"
.\release\wsl2\build-in-wsl.ps1
```

The wrapper runs:

- dependency installation inside WSL,
- a timestamped source staging copy inside the WSL ext4 filesystem,
- all four local test suites,
- `tools/build-release.sh`,
- artifact copy-back to `E:\LuminaOS-Artifacts`.

Expected outputs:

```text
E:\LuminaOS-Artifacts\LuminaOS-1.1-amd64.iso
E:\LuminaOS-Artifacts\LuminaOS-1.1-amd64.iso.sha256
E:\LuminaOS-Artifacts\build-manifest.json
```

## Step 3 — VirtualBox acceptance

Install VirtualBox 7.x if needed. Then:

```powershell
.\release\wsl2\vm-acceptance.ps1
```

The script refuses to overwrite an existing VM with the same name. Use `-VMName` to choose a different name.

Inside the first booted session, run:

```powershell
# Copy the validator into the guest, then inside the guest shell:
python3 tools/validate-guest.py
```

If copying files into the guest is inconvenient, manually check the items in `release/RELEASE_CHECKLIST.md`.

## Troubleshooting

- **“WSL not found”**: install WSL2, reboot, then rerun.
- **“No source distro found”**: run `wsl --install -d Ubuntu-24.04`, reboot, then rerun.
- **“LuminaBuild already exists”**: that is fine; skip step 1 and run `build-in-wsl.ps1`.
- **“VBoxManage not found”**: install VirtualBox 7.x or add its directory to `PATH`.
- **Build fails on free space**: check both `E:` and the WSL VHDX size; the build needs at least 8 GB inside the ext4 filesystem.
