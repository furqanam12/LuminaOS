# Artifact manifest

## Source packages

| Artifact | Files | Size | SHA-256 |
|---|---:|---:|---|
| `LuminaOS-Performance-Patch-1.1.zip` | 128 | 44,371,050 | `edfd3e17bbce31db17004997707ebe5e54308c72014db81157725b94751423d8` |
| `LuminaOS-Installer-FirstRun-Patch.zip` | 135 | 44,381,211 | `a5ef33e9f0772ef841703add41db034f7472115920f78c331d90bb8c16fa32f9` |
| `LuminaOS-Features-1.4-1.5-Patch.zip` | 138 | 44,393,458 | `3be3efd05bffb290a3442531b6308c636ad2c83d91ea32673f9b470ee72acf44` |

These are previous cumulative source snapshots. The final combined release package supersedes them for build purposes. The checksum of the current combined release kit is recorded in the external `LuminaOS-1.1-Release-Kit.zip.sha256` file beside the archive.

## Expected build artifacts

These do **not** exist yet. They are created by `tools/build-release.sh` or `build.sh` on a suitable Linux host.

| Artifact | Expected name | Status |
|---|---|---|
| ISO | `LuminaOS-1.1-amd64.iso` | Pending |
| ISO checksum | `LuminaOS-1.1-amd64.iso.sha256` | Pending |
| Build manifest | `release/build-manifest.json` | Pending |
| Guest validation output | `release/guest-validation.json` | Pending |
| Balanced benchmark | `release/benchmark-balanced.json` | Pending |
| Low-power benchmark | `release/benchmark-low-power.json` | Pending |
| Completed sign-off | `release/SIGNOFF.md` | Pending |

## Release documentation

- `release/README.md`
- `release/RELEASE_NOTES.md`
- `release/RELEASE_CHECKLIST.md`
- `release/QA_MATRIX.md`
- `release/BUILD_AND_ACCEPTANCE.md`
- `release/RELEASE_STATUS.md`
- `release/SIGNOFF_TEMPLATE.md`
- `release/wsl2/README.md`
- `release/wsl2/prepare-wsl2.ps1`
- `release/wsl2/wsl-build.sh`
- `release/wsl2/build-in-wsl.ps1`
- `release/wsl2/vm-acceptance.ps1`

## Verification commands

On Linux:

```bash
sha256sum -c LuminaOS-1.1-amd64.iso.sha256
python3 tools/validate-guest.py > release/guest-validation.json
```

On Windows, PowerShell can compute a source-package checksum:

```powershell
Get-FileHash .\LuminaOS-1.1-Release-Kit.zip -Algorithm SHA256
```
