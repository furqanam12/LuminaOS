#!/usr/bin/env bash
# Runs inside the LuminaBuild WSL distro.
# Usage: wsl-build.sh /mnt/c/.../LuminaOS-performance /mnt/e/LuminaOS-Artifacts
set -euo pipefail

SRC="${1:?Windows source path in /mnt/... form required}"
ART="${2:?Windows artifact path in /mnt/... form required}"
[ -d "$SRC" ] || { echo "ERROR: source not found: $SRC" >&2; exit 1; }
mkdir -p "$ART"

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi
$SUDO apt-get update -qq
$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin grub-common \
  mtools dosfstools debian-archive-keyring librsvg2-bin imagemagick dpkg-dev \
  rsync python3 python3-pil fonts-inter nodejs sudo ca-certificates locales >/dev/null

STAMP="$(date -u +%Y%m%d-%H%M%S)"
STAGE="$HOME/LuminaOS/builds/LuminaOS-performance-$STAMP"
mkdir -p "$(dirname "$STAGE")"
echo "==> Staging source into $STAGE"
cp -a "$SRC/." "$STAGE/"
cd "$STAGE"

chmod +x tools/build-release.sh tools/validate-guest.py 2>/dev/null || true
echo "==> Running source validation"
python3 tools/test-release.py
python3 tools/test-features.py
python3 tools/test-installer.py
python3 tools/test-performance.py
node tools/test-performance.js

echo "==> Building ISO"
./tools/build-release.sh

ISO="$STAGE/LuminaOS-1.1-amd64.iso"
[ -f "$ISO" ] || { echo "ERROR: ISO not created" >&2; exit 1; }
echo "==> Copying artifacts to $ART"
cp -a "$ISO" "$ART/"
cp -a "$ISO.sha256" "$ART/" 2>/dev/null || true
[ -f release/build-manifest.json ] && cp -a release/build-manifest.json "$ART/" || true

cat > "$ART/wsl-build-status.txt" <<EOF
build_time_utc=$STAMP
source=$SRC
stage=$STAGE
iso=$(basename "$ISO")
iso_sha256=$(sha256sum "$ISO" | awk '{print $1}')
guest_validation=pending
EOF

echo "==> Done"
echo "Artifacts: $ART"
echo "Next: run vm-acceptance.ps1 on Windows, or boot the ISO manually."
