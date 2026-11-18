# Build LuminaOS 1.1 inside the WSL distro and copy artifacts to E:
param(
  [string]$DistroName = "LuminaBuild",
  [string]$Source = "C:\Users\Muhammad Furqan Amin\Downloads\New folder\LuminaOS-performance",
  [string]$Artifacts = "E:\LuminaOS-Artifacts"
)
$ErrorActionPreference = "Stop"
$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if (-not $wsl) { throw "WSL not found." }
if (-not (Test-Path $Source)) { throw "Source not found: $Source" }

$list = @(wsl.exe --list --quiet | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ })
if ($list -notcontains $DistroName) { throw "Distro '$DistroName' not found. Run prepare-wsl2.ps1 first." }

function Convert-ToWslPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $full = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
  if ($full -match '^([A-Za-z]):\\(.*)$') {
    return "/mnt/$($Matches[1].ToLower())/$($Matches[2].Replace('\','/'))"
  }
  throw "Unsupported path: $Path"
}

# Artifacts directory may not exist yet, so convert it as a string.
function Convert-NewWslPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $full = [System.IO.Path]::GetFullPath($Path)
  if ($full -match '^([A-Za-z]):\\(.*)$') {
    return "/mnt/$($Matches[1].ToLower())/$($Matches[2].Replace('\','/'))"
  }
  throw "Unsupported path: $Path"
}

$sourceWsl = Convert-ToWslPath $Source
$artifactsWsl = Convert-NewWslPath $Artifacts
$scriptWsl = Convert-ToWslPath (Join-Path $PSScriptRoot "wsl-build.sh")

New-Item -ItemType Directory -Force -Path $Artifacts | Out-Null
Write-Host "Building in WSL distro '$DistroName' ..." -ForegroundColor Cyan
wsl.exe -d $DistroName --exec bash $scriptWsl $sourceWsl $artifactsWsl
if ($LASTEXITCODE -ne 0) { throw "WSL build failed with exit code $LASTEXITCODE." }
Write-Host "Artifacts are in $Artifacts" -ForegroundColor Green
