# LuminaOS Terminal - open a real Linux terminal of the LuminaOS VM on Windows
# Double-click "LuminaOS Terminal.cmd", or run:
#   powershell -ExecutionPolicy Bypass -File ".\LuminaOS Terminal.ps1"
# Options: -User furqan -Port 2223 -VM LuminaOS -Gui   (use -Gui to also open the desktop window)
param(
  [string]$VM = "LuminaOS",
  [string]$User = "furqan",
  [int]$Port = 2223,
  [switch]$Gui
)
$ErrorActionPreference = "Stop"
$VBox = Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"
if (-not (Test-Path $VBox)) {
  $cmd = Get-Command VBoxManage.exe -ErrorAction SilentlyContinue
  if ($cmd) { $VBox = $cmd.Source } else { Write-Host "ERROR: VirtualBox not installed." -ForegroundColor Red; exit 1 }
}

# ---- VM must exist ------------------------------------------------------
& $VBox showvminfo $VM --machinereadable *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: VM '$VM' not found. Run 'Run LuminaOS in VirtualBox.cmd' once first." -ForegroundColor Red; exit 1 }

# ---- make sure the VM is running (start headless if needed) -------------
$state = (& $VBox showvminfo $VM --machinereadable | Select-String '^VMState=').ToString().Split('"')[1]
if ($state -ne "running") {
  Write-Host "Starting LuminaOS VM (headless)..." -ForegroundColor Cyan
  & $VBox startvm $VM --type headless | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: could not start the VM." -ForegroundColor Red; exit 1 }
} elseif ($Gui) {
  # already running with GUI elsewhere; nothing to do
}
Write-Host "VM is running." -ForegroundColor Green

# ---- ensure the NAT port-forward rule for SSH ---------------------------
& $VBox controlvm $VM natpf1 delete ssh *> $null
& $VBox controlvm $VM natpf1 "ssh,tcp,127.0.0.1,$Port,,22" *> $null
if ($LASTEXITCODE -ne 0) {
  & $VBox modifyvm $VM --natpf1 delete ssh *> $null 2>&1
  & $VBox modifyvm $VM --natpf1 "ssh,tcp,127.0.0.1,$Port,,22" *> $null
}

# ---- wait briefly for sshd in the guest ---------------------------------
Write-Host "Connecting to Linux (user $User, port $Port)..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(15)
$ok = $false
while ((Get-Date) -lt $deadline) {
  $probe = & ssh -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o LogLevel=ERROR -p $Port "$User@127.0.0.1" "exit" 2>&1
  if ($LASTEXITCODE -ne 255 -or "$probe" -notmatch "refused|timed out|aborted") { $ok = $true; break }
  Start-Sleep -Seconds 2
}
if (-not $ok) {
  Write-Host ""
  Write-Host "SSH is not reachable inside LuminaOS yet." -ForegroundColor Yellow
  Write-Host "One-time setup - in the LuminaOS VM, open a Terminal (Ctrl+Alt+T) and run:" -ForegroundColor Yellow
  Write-Host '  curl -s 10.0.2.2:8000/lumina-ssh.sh | sh' -ForegroundColor White
  Write-Host "(needs the helper web server running on this PC:  python -m http.server 8000 --bind 127.0.0.1 --directory `"$env:TEMP\opencode\www`")" -ForegroundColor DarkGray
  exit 2
}

# ---- interactive SSH session --------------------------------------------
& ssh -t -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -p $Port "$User@127.0.0.1"
if ($LASTEXITCODE -ne 0) { Write-Host ""; Write-Host "ssh session ended with code $LASTEXITCODE" -ForegroundColor DarkGray }
