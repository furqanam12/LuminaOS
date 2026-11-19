# Build and Deployment Guide

This is the release path for producing a LuminaOS image, verifying it and sharing it for VirtualBox evaluation.

## 1. Release inputs and outputs

**Required input:** the current LuminaOS source tree and a Linux build environment with administrator access.

**Outputs:**

```text
LuminaOS-1.1-amd64.iso
LuminaOS-1.1-amd64.iso.sha256
release/build-manifest.json
```

The checksum establishes file integrity against the published checksum. It is not a replacement for a digital release signature or a successful guest test.

## 2. Option A — GitHub Actions (recommended on Windows)

The repository includes two workflows:

- **host-tests** — source, installer, performance and release checks on relevant pushes.
- **build-iso** — manually dispatched Linux build with downloadable ISO artifacts.

### Dispatch the ISO build

From the repository root:

```sh
gh auth login
# If workflow files have not been pushed yet, request the workflow scope first:
gh auth refresh -h github.com -s workflow

gh workflow run build-iso.yml --ref main
gh run list --workflow build-iso.yml --limit 1
```

Alternatively, open **GitHub → Actions → build-iso → Run workflow**.

### Monitor progress

Copy the run ID from the output and use:

```sh
gh run watch <RUN_ID> --exit-status --interval 60
```

The workflow has a 120-minute timeout. It installs the Debian build dependencies, validates the source, runs the build, checks the checksum and uploads artifacts. An in-progress run is **not** evidence of a working ISO.

### Download the build

```sh
gh run download <RUN_ID> -n LuminaOS-1.1-amd64 -D artifacts
```

Inspect `artifacts/release/build-manifest.json`. It records source test outcomes, timestamps, ISO size, hash and guest-validation state.

### When a run fails

```sh
gh run view <RUN_ID> --log-failed
```

Do not distribute an ISO from a failed job. Correct the error, rerun the source checks and create a fresh artifact.

## 3. Option B — local Debian/Ubuntu build

Requirements:

- x86-64 Debian/Ubuntu Linux or WSL2
- Administrator access
- At least 8 GiB free disk; approximately 12 GiB or more is recommended
- Reliable network access
- Debian build utilities from `tools/build-release.sh`

From the `LuminaOS-performance` directory:

```sh
sudo bash tools/build-release.sh
```

The wrapper installs no guest packages for testing; it constructs a new environment from Debian repositories and the supplied package list. On its first run, the base bootstrap and package download can take considerable time.

The base ISO enables i386 before installing Wine32/Wine64. On Debian 13, Waydroid is **not** unconditionally included from the main repository; the Android helper configures signed trixie-backports on demand.

### WSL2 notes

The workflow under `release/wsl2/` provides a source-copy workflow on E:. It may stop WSL after confirmation for consistent export; it does not unregister the original distro. Follow [`release/wsl2/README.md`](../release/wsl2/README.md) rather than improvising an import over your working Linux installation.

## 4. Verify the artifact

### On Linux

Run beside the ISO and checksum file:

```sh
sha256sum -c LuminaOS-1.1-amd64.iso.sha256
```

### On Windows PowerShell

```powershell
$expected = (Get-Content .\LuminaOS-1.1-amd64.iso.sha256).Split()[0]
$actual = (Get-FileHash .\LuminaOS-1.1-amd64.iso -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) { throw "ISO checksum mismatch" }
Write-Host "ISO checksum verified: $actual"
```

A mismatch means the file should not be used. Re-download or rebuild it rather than trying to repair an unknown image.

## 5. VirtualBox deployment

Use VirtualBox 7.x or newer.

| Setting | Value |
|---|---|
| Guest type/version | Linux / Debian 64-bit |
| RAM | 4 GB minimum; 8 GB recommended |
| Processors | 2 minimum; 4 recommended |
| Disk | Dynamic VDI, 40 GB recommended |
| Display | VBoxVGA, 3D acceleration enabled |
| Audio | Intel HD Audio |
| Network | NAT for simple outbound connectivity |
| Optical drive | Verified LuminaOS ISO |

After installation is finished, remove the optical ISO and boot from the virtual disk. Install Guest Additions for improved integration where appropriate.

**Warning:** **Erase disk** inside the Calamares installer means the selected **virtual disk**. Double-check the target device before continuing.

For a companion checklist, use [Share LuminaOS with a friend](SHARE_WITH_FRIEND.md).

## 6. Guest acceptance

Build success is just one stage. Run the read-only guest validator in a booted installed guest:

```sh
python3 tools/validate-guest.py
```

It checks expected API fields, package/runtime presence, Wine, Kali terminal, accessibility and Bluetooth response shapes. It does not install packages or change settings.

For broader non-destructive app checks:

```sh
DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority" python3 tools/test-live.py
```

Run that command inside the graphical guest session (or through SSH with the correct display authority). Review its JSON report for failures and warnings. Restore demo settings, close test windows, clear test notifications and do not reset or power off another user's session without permission.

Also complete the relevant rows in:

- `release/QA_MATRIX.md`
- `release/RELEASE_CHECKLIST.md`
- `release/SIGNOFF_TEMPLATE.md`

Required coverage includes live boot, installation, installed boot, settings, apps, network, audio, display and compatibility runtime behavior.

## 7. Host test commands

From `LuminaOS-performance`:

```sh
python3 tools/test-features.py
python3 tools/test-installer.py
python3 tools/test-performance.py
node tools/test-performance.js
python3 tools/test-release.py
python3 -m py_compile src/lib/lumina/api.py tools/test-live.py
```

The exact currently recorded counts are in [`release/RELEASE_STATUS.md`](../release/RELEASE_STATUS.md) and [`release/QA_MATRIX.md`](../release/QA_MATRIX.md).

## 8. Package delivery checklist

Before sending the ISO to someone else:

- ISO was produced by a successful release workflow or Linux build.
- SHA256 verification passes on the destination computer.
- Guest acceptance is documented with any unresolved failures.
- No secret token, SSH private key, password or personal home-directory content is included.
- The recipient has the concise [SHARE_WITH_FRIEND.md](SHARE_WITH_FRIEND.md) guide.
- Windows and Android support is described honestly; ARM-only Android apps and app-specific Wine limitations are included.
- A clear build date and version are visible in the manifest.

## 9. Rollback and release hygiene

- Keep the last known working ISO and its checksum.
- Never overwrite your working VirtualBox VM disk while testing a new ISO; make a separate VM.
- Do not modify, restart or power off an existing guest merely to test a release.
- Keep generated ISOs, `work/` and environment-specific caches out of source commits.
- Store release evidence with the source revision that produced it.

Professional release sign-off means **repeatable build, verified artifacts and explicit guest evidence**, not merely “all apps are implemented.”
