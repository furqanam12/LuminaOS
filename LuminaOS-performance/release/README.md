# LuminaOS 1.1 release kit

This directory contains the release-readiness material for LuminaOS 1.1 “Aurora Update 1”.

| File | Purpose |
|---|---|
| `RELEASE_NOTES.md` | User-facing summary of changes and known limitations |
| `RELEASE_CHECKLIST.md` | Go/no-go checklist, including guest-only acceptance items |
| `QA_MATRIX.md` | Test-case matrix with current source/guest status |
| `BUILD_AND_ACCEPTANCE.md` | Linux build, checksum, VM and in-guest validation commands |
| `RELEASE_STATUS.md` | Current release status and environment blockers |
| `ARTIFACT_MANIFEST.md` | Expected build artifacts and recorded source-package checksums |
| `SIGNOFF_TEMPLATE.md` | Final release approval record |

## Current status

Source implementation and automated validation are complete. The ISO build and all guest acceptance items are pending because the preparation host did not have enough free workspace disk space or a detected VirtualBox installation.

Do not mark the release complete until `RELEASE_CHECKLIST.md` is finished and `SIGNOFF_TEMPLATE.md` is approved.
