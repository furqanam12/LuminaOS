# LuminaOS - one-click launcher for the VirtualBox VM on Windows
# Double-click "Run LuminaOS in VirtualBox.cmd", or run:
#   powershell -ExecutionPolicy Bypass -File ".\Run LuminaOS in VirtualBox.ps1"
# Optional: -Iso <path> -MemoryMB 3072 -Cpus 2 -DiskGB 20 -BootFromDisk -BootIso
#   After LuminaOS is installed to the virtual disk, the VM boots from disk by
#   default. Pass -BootIso to boot the installer ISO again (live session).
param(
  [string]$Iso = (Join-Path $PSScriptRoot "LuminaOS-1.0-amd64.iso"),
  [string]$Name = "LuminaOS",
  [int]$MemoryMB = 2560,
  [int]$Cpus = 1,
  [int]$DiskGB = 20,
  [switch]$BootFromDisk,   # boot the installed system on the virtual hard disk
  [switch]$BootIso         # force-boot the installer ISO (live session)
)
$ErrorActionPreference = "Stop"

function Fail([string]$msg) {
  Write-Host ""
  Write-Host "ERROR: $msg" -ForegroundColor Red
  exit 1
}

# ---- locate VirtualBox -------------------------------------------------
$VBox = Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"
if (-not (Test-Path $VBox)) {
  $cmd = Get-Command VBoxManage.exe -ErrorAction SilentlyContinue
  if ($cmd) { $VBox = $cmd.Source }
  else { Fail "VirtualBox is not installed. Download it from https://www.virtualbox.org/wiki/Downloads" }
}

# ---- create the VM once, reuse it afterwards ---------------------------
& $VBox showvminfo $Name --machinereadable *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Creating VM '$Name'..." -ForegroundColor Cyan
  & $VBox createvm --name $Name --ostype Debian_64 --register | Out-Null
  if ($LASTEXITCODE -ne 0) { Fail "Could not create the VM '$Name'." }

  $cfg = (& $VBox showvminfo $Name --machinereadable | Select-String '^CfgFile=').ToString()
  $vmDir = Split-Path $cfg.Substring($cfg.IndexOf('=') + 1).Trim('"')
  $disk = Join-Path $vmDir "$Name.vdi"

  & $VBox modifyvm $Name --memory $MemoryMB --cpus $Cpus --vram 32 --accelerate3d off `
    --graphicscontroller vmsvga --firmware efi --rtc-use-utc on `
    --nic1 nat --audio-enabled on --audio-out on --mouse usbtablet --usb-xhci on `
    --clipboard-mode bidirectional --drag-and-drop bidirectional `
    --natpf1 "ssh,tcp,127.0.0.1,2223,,22" | Out-Null

  & $VBox createmedium disk --filename $disk --size ($DiskGB * 1024) --format VDI | Out-Null
  & $VBox storagectl $Name --name "SATA" --add sata --controller IntelAhci --portcount 2 --bootable on | Out-Null
  & $VBox storageattach $Name --storagectl "SATA" --port 0 --device 0 --type hdd --medium $disk --nonrotational on | Out-Null
}
else {
  $cfg = (& $VBox showvminfo $Name --machinereadable | Select-String '^CfgFile=').ToString()
  $vmDir = Split-Path $cfg.Substring($cfg.IndexOf('=') + 1).Trim('"')
}

# ---- decide what to boot ------------------------------------------------
# Once LuminaOS is installed on the virtual disk, keep booting from disk
# (remembered in a marker file) unless the user forces the ISO with -BootIso.
$diskFlag = Join-Path $vmDir "boot-from-disk.flag"
$installed = Test-Path $diskFlag
$bootDisk = $false
if ($BootIso) { $bootDisk = $false }
elseif ($BootFromDisk) { $bootDisk = $true; New-Item -ItemType File -Path $diskFlag -Force | Out-Null }
elseif ($installed) { $bootDisk = $true }

# ---- validate the ISO before touching the VM (only needed for DVD boot) --
if (-not $bootDisk) {
  if (-not (Test-Path $Iso)) { Fail "ISO not found: $Iso" }
  $Iso = (Resolve-Path $Iso).Path
  $fileLen = (Get-Item $Iso).Length
  if ($fileLen % 2048 -ne 0) {
    Fail ("ISO is incomplete: {0:N0} bytes is not a multiple of 2048, so the download/copy was cut off." -f $fileLen)
  }
  $pvd = New-Object byte[] 2048
  $fs = [System.IO.File]::OpenRead($Iso)
  try { $null = $fs.Read($pvd, 0, 2048) } finally { $fs.Close() }
  if ([System.Text.Encoding]::ASCII.GetString($pvd, 1, 5) -ne "CD001") {
    Fail "Not a valid ISO 9660 image: $Iso"
  }
  $expected = [BitConverter]::ToUInt32($pvd, 80) * 2048
  if ($expected -gt 0 -and $fileLen -ne $expected) {
    Fail ("ISO is incomplete: {0:N0} of {1:N0} bytes present ({2:P0} of the image). Re-download or re-copy the whole file." -f `
          $fileLen, $expected, ($fileLen / $expected))
  }
}

# ---- boot order and DVD drive -------------------------------------------
if ($bootDisk) {
  & $VBox modifyvm $Name --boot1 disk --boot2 dvd --boot3 none --boot4 none | Out-Null
} else {
  & $VBox modifyvm $Name --boot1 dvd --boot2 disk --boot3 none --boot4 none | Out-Null
  & $VBox storageattach $Name --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium $Iso | Out-Null
  if ($LASTEXITCODE -ne 0) { Fail "VirtualBox could not attach the ISO. Close any program using it and try again." }
}

# ---- start -------------------------------------------------------------
$state = (& $VBox showvminfo $Name --machinereadable | Select-String '^VMState=').ToString().Split('"')[1]
if ($state -eq "running") {
  Write-Host "LuminaOS is already running." -ForegroundColor Green
  exit 0
}
Write-Host "Starting '$Name'..." -ForegroundColor Green
& $VBox startvm $Name --type gui
if ($LASTEXITCODE -ne 0) { Fail "VirtualBox could not start the VM." }
