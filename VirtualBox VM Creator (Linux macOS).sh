#!/usr/bin/env bash
# LuminaOS - create a ready-to-boot VirtualBox VM on Linux or macOS (Intel)
# Usage:  ./VirtualBox\ VM\ Creator\ \(Linux\ macOS\).sh ~/Downloads/LuminaOS-1.0-amd64.iso
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: $0 <path-to-LuminaOS-iso>   (env: NAME, MEM, CPUS, DISK_GB)"
  exit 1
fi
ISO="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
NAME="${NAME:-LuminaOS}"; MEM="${MEM:-4096}"; CPUS="${CPUS:-2}"; DISK_GB="${DISK_GB:-30}"
command -v VBoxManage >/dev/null || { echo "VBoxManage not found - install VirtualBox first"; exit 1; }
[ -f "$ISO" ] || { echo "ISO not found: $ISO"; exit 1; }

if VBoxManage showvminfo "$NAME" --machinereadable >/dev/null 2>&1; then
  echo "A VM named '$NAME' already exists. Open it from VirtualBox, or pick another name (NAME=... $0 ...)"; exit 1
fi

VBoxManage createvm --name "$NAME" --ostype Debian_64 --register
CFG=$(VBoxManage showvminfo "$NAME" --machinereadable | sed -n 's/^CfgFile="\(.*\)"/\1/p')
DISK="$(dirname "$CFG")/$NAME.vdi"

VBoxManage modifyvm "$NAME" --memory "$MEM" --cpus "$CPUS" --vram 128 --accelerate3d off \
  --graphicscontroller vmsvga --firmware efi --rtc-use-utc on \
  --nic1 nat --audio-enabled on --audio-out on --mouse usbtablet --usb-xhci on \
  --clipboard-mode bidirectional --drag-and-drop bidirectional \
  --natpf1 "ssh,tcp,127.0.0.1,2223,,22" \
  --boot1 dvd --boot2 disk --boot3 none --boot4 none
VBoxManage createmedium disk --filename "$DISK" --size $((DISK_GB*1024)) --format VDI
VBoxManage storagectl "$NAME" --name SATA --add sata --controller IntelAhci --portcount 2 --bootable on
VBoxManage storageattach "$NAME" --storagectl SATA --port 0 --device 0 --type hdd --medium "$DISK" --nonrotational on
VBoxManage storageattach "$NAME" --storagectl SATA --port 1 --device 0 --type dvddrive --medium "$ISO"
echo "VM '$NAME' created - starting..."
VBoxManage startvm "$NAME" --type gui
echo
echo "Tip: after installing LuminaOS, open its Linux terminal from Windows/Linux/macOS with:"
echo "  ssh -p 2223 <user>@127.0.0.1"
