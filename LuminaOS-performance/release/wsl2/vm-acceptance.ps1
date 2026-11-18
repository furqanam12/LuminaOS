# Create and start a VirtualBox acceptance VM for the built ISO
param(
  [string]$Iso = "E:\LuminaOS-Artifacts\LuminaOS-1.1-amd64.iso",
  [string]$VMName = "LuminaOS-1.1-Acceptance",
  [string]$Source = "C:\Users\Muhammad Furqan Amin\Downloads\New folder\LuminaOS-performance"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Iso)) { throw "ISO not found: $Iso" }

$VBox = Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"
if (-not (Test-Path $VBox)) {
  $cmd = Get-Command VBoxManage.exe -ErrorAction SilentlyContinue
  if ($cmd) { $VBox = $cmd.Source } else { throw "VirtualBox not found. Install VirtualBox 7.x first." }
}

$existing = & $VBox list vms | Where-Object { $_ -match '"' + [regex]::Escape($VMName) + '"' }
if ($existing) { throw "VM '$VMName' already exists. Use -VMName with a different value." }

$creator = Join-Path $Source "virtualbox\create-luminaos-vm.ps1"
if (-not (Test-Path $creator)) { throw "VM creator script not found: $creator" }

Write-Host "Creating VM '$VMName' from $Iso" -ForegroundColor Cyan
& $creator -Iso $Iso -Name $VMName -MemoryMB 4096 -Cpus 2 -DiskGB 30
if ($LASTEXITCODE -ne 0) { throw "VM creation failed." }

Write-Host @'

VM started. Complete these checks manually:
  1. GRUB menu -> Start LuminaOS, then safe graphics.
  2. Live desktop -> installer shortcut and Welcome button.
  3. Install to disk, reboot without ISO.
  4. First-run setup opens once and completes.
  5. Settings -> Accessibility, Performance, Notifications, Accounts.
  6. Ctrl+K command palette.
  7. File Explorer undo/redo, split view, archives, permissions.
  8. Compatibility wizard.
  9. Run tools/validate-guest.py inside the guest if available.

Record results in release/RELEASE_CHECKLIST.md and release/SIGNOFF_TEMPLATE.md.
'@ -ForegroundColor Green
