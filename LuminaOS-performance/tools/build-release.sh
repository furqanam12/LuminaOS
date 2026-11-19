#!/usr/bin/env bash
# Build and verify a LuminaOS 1.1 release ISO on a suitable Linux host.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(sed -n 's/^VERSION="\([^"]*\)".*/\1/p' build.sh | head -1)"
ISO="$ROOT/LuminaOS-${VERSION}-amd64.iso"
SUM="$ISO.sha256"
MANIFEST="$ROOT/release/build-manifest.json"
NEEDED=(sudo python3 node debootstrap mksquashfs xorriso grub-mkrescue grub-mkfont rsvg-convert convert)

echo "==> LuminaOS release build wrapper"
echo "Source: $ROOT"
echo "Version: $VERSION"

if [ "$(uname -s)" != "Linux" ]; then
  echo "ERROR: build.sh requires a Linux host or WSL 2." >&2
  exit 1
fi

missing=()
for tool in "${NEEDED[@]}"; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "ERROR: missing tools: ${missing[*]}" >&2
  echo "On Debian/Ubuntu:" >&2
  echo "  sudo apt-get update" >&2
  echo "  sudo apt-get install -y debootstrap squashfs-tools xorriso grub-pc-bin \\" >&2
  echo "    grub-efi-amd64-bin grub-common mtools dosfstools debian-archive-keyring \\" >&2
  echo "    librsvg2-bin imagemagick dpkg-dev rsync python3-pil fonts-inter nodejs" >&2
  exit 1
fi

available=$(df -PB1 "$ROOT" | tail -1 | awk '{print $4}')
required=$((8 * 1024 * 1024 * 1024))
if [ "$available" -lt "$required" ]; then
  echo "ERROR: at least 8 GiB free is required on $ROOT; found $((available / 1024 / 1024 / 1024)) GiB." >&2
  exit 1
fi

echo "==> Running local validation suites"
python3 tools/test-features.py
python3 tools/test-installer.py
python3 tools/test-performance.py
python3 tools/test-release.py
node tools/test-performance.js

echo "==> Building ISO"
if [ "$(id -u)" -eq 0 ]; then bash build.sh; else sudo bash build.sh; fi

echo "==> Verifying checksum"
[ -f "$ISO" ] || { echo "ERROR: ISO not found: $ISO" >&2; exit 1; }
[ -f "$SUM" ] || { echo "ERROR: checksum file not found: $SUM" >&2; exit 1; }
sha256sum -c "$SUM"

python3 - "$ISO" "$SUM" "$VERSION" "$MANIFEST" <<'PY'
import datetime
import hashlib
import json
import os
import pathlib
import sys

iso, checksum, version, manifest = map(pathlib.Path, sys.argv[1:5])
sha = hashlib.sha256()
with iso.open("rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        sha.update(block)
data = {
    "product": "LuminaOS",
    "version": str(version),
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "iso": str(iso),
    "iso_bytes": iso.stat().st_size,
    "iso_sha256": sha.hexdigest(),
    "checksum_file": str(checksum),
    "source_tests": {
        "test-features.py": "pass",
        "test-installer.py": "pass",
        "test-performance.py": "pass",
        "test-performance.js": "pass",
    },
    "guest_validation": "pending",
}
manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("Wrote " + str(manifest))
PY

echo "==> Build complete"
echo "ISO: $ISO"
echo "Checksum file: $SUM"
echo "Manifest: $MANIFEST"
echo "Next: boot the ISO and run release/RELEASE_CHECKLIST.md."
