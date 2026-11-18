# LuminaOS - create a ready-to-boot VirtualBox VM on Windows
# Usage (PowerShell):  .\VirtualBox VM Creator (Windows).ps1 -Iso "C:\Users\you\Downloads\LuminaOS-1.0-amd64.iso"
param(
  [Parameter(Mandatory=$true)][string]$Iso,
  [string]$Name   = "LuminaOS",
  [int]$MemoryMB  = 4096,
  [int]$Cpus      = 2,
  [int]$DiskGB    = 30
)
$ErrorActionPreference = "Stop"
$VBox = Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"
if (-not (Test-Path $VBox)) { throw "VirtualBox not found. Install it from https://www.virtualbox.org/wiki/Downloads" }
if (-not (Test-Path $Iso))  { throw "ISO not found: $Iso" }
$Iso = (Resolve-Path $Iso).Path

& $VBox showvminfo $Name --machinereadable *> $null
if ($LASTEXITCODE -eq 0) { throw "A VM named '$Name' already exists. Open it from VirtualBox, or pick another name with -Name." }

& $VBox createvm --name $Name --ostype Debian_64 --register
$Cfg = (& $VBox showvminfo $Name --machinereadable | Select-String '^CfgFile=').ToString()
$VmDir = Split-Path $Cfg.Substring($Cfg.IndexOf('=') + 1).Trim('"')
$Disk  = Join-Path $VmDir "$Name.vdi"

& $VBox modifyvm $Name --memory $MemoryMB --cpus $Cpus --vram 128 --accelerate3d off `
  --graphicscontroller vmsvga --firmware efi --rtc-use-utc on `
  --nic1 nat --audio-enabled on --audio-out on --mouse usbtablet --usb-xhci on `
  --clipboard-mode bidirectional --drag-and-drop bidirectional `
  --natpf1 "ssh,tcp,127.0.0.1,2223,,22" `
  --boot1 dvd --boot2 disk --boot3 none --boot4 none

& $VBox createmedium disk --filename $Disk --size ($DiskGB * 1024) --format VDI
& $VBox storagectl $Name --name "SATA" --add sata --controller IntelAhci --portcount 2 --bootable on
& $VBox storageattach $Name --storagectl "SATA" --port 0 --device 0 --type hdd --medium $Disk --nonrotational on
& $VBox storageattach $Name --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium $Iso

Write-Host "`nVM '$Name' created. Starting it now..." -ForegroundColor Green
& $VBox startvm $Name --type gui
Write-Host "`nTip: after installing LuminaOS, open its Linux terminal from Windows with 'LuminaOS Terminal.cmd' (SSH on port 2223)." -ForegroundColor Cyan
