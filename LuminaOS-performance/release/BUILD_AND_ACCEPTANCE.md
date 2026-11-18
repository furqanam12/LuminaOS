# Build and acceptance guide

This guide describes the cleanest way to build and validate LuminaOS 1.1.

## Recommended Windows/WSL2 route

If you are preparing the build from Windows, use the dedicated workflow in `release/wsl2/README.md`. It imports a build copy of WSL Ubuntu onto the `E:` drive, stages the source inside the WSL ext4 filesystem, builds the ISO, and copies artifacts to `E:\LuminaOS-Artifacts`.

Quick sequence:

```powershell
cd "C:\Users\Muhammad Furqan Amin\Downloads\New folder\LuminaOS-performance"
.\release\wsl2\prepare-wsl2.ps1
.\release\wsl2\build-in-wsl.ps1
.\release\wsl2\vm-acceptance.ps1
```

## Host requirements

- Debian or Ubuntu x86-64, or WSL 2 with a real Linux filesystem.
- `sudo` access.
- At least **8 GiB free** on the build filesystem. About 12 GiB is comfortable.
- Internet access for `debootstrap` and package installation.
- VirtualBox 7.x or QEMU for guest validation.

The Windows host used to prepare this release kit had only about **7 GiB free** on `C:` and no detected `VBoxManage`, so no ISO was built there.

## Clean build

```bash
cd /path/to/LuminaOS-performance
python3 tools/test-features.py
python3 tools/test-installer.py
python3 tools/test-performance.py
node tools/test-performance.js
sudo bash build.sh
```

Recommended wrapper:

```bash
chmod +x tools/build-release.sh
./tools/build-release.sh
```

The wrapper checks dependencies and disk space, runs the local suites, starts the build, verifies the ISO checksum, and writes `release/build-manifest.json`.

## Outputs

- `LuminaOS-1.1-amd64.iso`
- `LuminaOS-1.1-amd64.iso.sha256`

Verify manually:

```bash
sha256sum -c LuminaOS-1.1-amd64.iso.sha256
```

## VirtualBox VM

Use the supplied creator:

```bash
cd virtualbox
./create-luminaos-vm.sh ../LuminaOS-1.1-amd64.iso
```

Or on Windows:

```powershell
.\create-luminaos-vm.ps1 -Iso "C:\path\to\LuminaOS-1.1-amd64.iso"
```

Recommended VM profile:

- Debian 64-bit
- 2 CPUs
- 4 GB RAM
- VMSVGA, 128 MB video memory, 3D off
- EFI
- 30 GB dynamic disk
- NAT
- USB tablet
- Host audio enabled

## Guest validation

Inside the installed guest:

```bash
python3 tools/validate-guest.py
```

The script is read-only, checks the local API and expected system files, prints JSON, and exits non-zero if any required check fails. It supports `--json` for machine-readable output only.

For performance comparison:

```bash
python3 tools/benchmark-performance.py --label balanced --seconds 60
# switch to VM / low-power and sign out/in
python3 tools/benchmark-performance.py --label low-power --seconds 60
```

Record both JSON outputs in the release record. Do not publish a performance percentage unless the benchmark was actually run on the target VM.

## Manual acceptance

Work through `release/RELEASE_CHECKLIST.md` and `release/QA_MATRIX.md`. Any **[GUEST]** item not executed must remain unchecked in the final record.
