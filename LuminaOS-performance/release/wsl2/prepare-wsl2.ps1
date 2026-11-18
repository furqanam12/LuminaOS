# Prepare a WSL2 build distro on E:
# Non-destructive: does not unregister an existing distro.
param(
  [string]$DistroName = "LuminaBuild",
  [string]$Root = "E:\LuminaOS-WSL",
  [string]$SourceDistro = ""
)
$ErrorActionPreference = "Stop"
$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if (-not $wsl) { throw "WSL not found. Run: wsl --install -d Ubuntu-24.04" }

$exports = Join-Path $Root "exports"
$distroDir = Join-Path $Root $DistroName
New-Item -ItemType Directory -Force -Path $exports, (Split-Path $distroDir -Parent) | Out-Null

$drives = Get-PSDrive -PSProvider FileSystem | Where-Object Name -eq ($Root.Substring(0,1))
if ($drives.Free -lt 20GB) { throw "Less than 20 GB free on $($Root.Substring(0,1)):. Free space before continuing." }

$list = @(wsl.exe --list --quiet | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ })
if ($list -contains $DistroName) {
  Write-Host "Distro '$DistroName' already exists. Reusing it." -ForegroundColor Green
  wsl.exe -d $DistroName --exec bash -lc 'echo WSL build distro is available'
  if ($LASTEXITCODE -ne 0) { throw "Existing distro could not be started." }
  exit 0
}

if (-not $SourceDistro) {
  $SourceDistro = $list | Where-Object { $_ -match 'Ubuntu|Debian' } | Select-Object -First 1
}
if (-not $SourceDistro) {
  throw "No source distro found. Run: wsl --install -d Ubuntu-24.04 ; reboot ; rerun this script."
}
if ($list -notcontains $SourceDistro) { throw "Source distro '$SourceDistro' is not installed." }

Write-Warning "WSL will be shut down briefly so '$SourceDistro' can be exported. Save any WSL work first."
Read-Host "Press Enter to continue, or Ctrl+C to cancel" | Out-Null
wsl.exe --shutdown
Start-Sleep -Seconds 2

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tar = Join-Path $exports "$SourceDistro-$stamp.tar"
Write-Host "Exporting '$SourceDistro' to $tar ..." -ForegroundColor Cyan
wsl.exe --export $SourceDistro $tar
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $tar)) { throw "WSL export failed." }

Write-Host "Importing as '$DistroName' on $distroDir ..." -ForegroundColor Cyan
wsl.exe --import $DistroName $distroDir $tar --version 2
if ($LASTEXITCODE -ne 0) { throw "WSL import failed." }

wsl.exe -d $DistroName --exec bash -lc 'apt-get update -qq && apt-get install -y -qq sudo locales >/dev/null'
Write-Host "Done. Use build-in-wsl.ps1 next." -ForegroundColor Green
