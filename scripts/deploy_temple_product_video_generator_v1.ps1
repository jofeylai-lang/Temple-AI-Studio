param(
  [string]$ProjectRoot = "D:\AI\Jofey AI Studio",
  [string]$ProductionRoot = "D:\AI\Temple Product Video Generator",
  [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
  Write-Host "Deploy Temple Product Video Generator V1 production installation."
  Write-Host "Usage: powershell -ExecutionPolicy Bypass -File .\scripts\deploy_temple_product_video_generator_v1.ps1"
  Write-Host "Optional: -ProjectRoot <path> -ProductionRoot <path>"
  exit 0
}

$appName = "temple-product-video-generator"
$appSource = Join-Path $ProjectRoot "apps\$appName"
$releaseZip = Join-Path $appSource "release\TempleProductVideoGenerator-1.0.0.zip"
$productionApp = Join-Path $ProductionRoot "app"
$productionData = Join-Path $ProductionRoot "data"
$backupRoot = Join-Path $ProductionRoot "deployment-backups"
$tempRoot = Join-Path $env:TEMP ("temple-product-video-generator-deploy-" + [guid]::NewGuid().ToString("N"))

function Resolve-SafePath {
  param([string]$Path)
  return [System.IO.Path]::GetFullPath($Path)
}

function Assert-UnderRoot {
  param([string]$Root, [string]$Target)
  $resolvedRoot = Resolve-SafePath $Root
  $resolvedTarget = Resolve-SafePath $Target
  if (-not $resolvedTarget.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to modify outside production root: $resolvedTarget"
  }
}

if (-not (Test-Path -LiteralPath $releaseZip)) {
  throw "Release package not found: $releaseZip"
}

New-Item -ItemType Directory -Force -Path $ProductionRoot, $productionData, $backupRoot, $tempRoot | Out-Null

if (Test-Path -LiteralPath $productionApp) {
  Assert-UnderRoot -Root $ProductionRoot -Target $productionApp
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $appBackup = Join-Path $backupRoot "app-before-deploy-$timestamp"
  Move-Item -LiteralPath $productionApp -Destination $appBackup
  Write-Host "Backed up existing app folder: $appBackup"
}

Expand-Archive -LiteralPath $releaseZip -DestinationPath $tempRoot -Force

$wrappedRoot = Get-ChildItem -LiteralPath $tempRoot -Directory | Where-Object { $_.Name -eq "TempleProductVideoGenerator-1.0.0" } | Select-Object -First 1
if ($wrappedRoot) {
  Move-Item -LiteralPath $wrappedRoot.FullName -Destination $productionApp
} elseif (Test-Path -LiteralPath (Join-Path $tempRoot "server.py")) {
  New-Item -ItemType Directory -Force -Path $productionApp | Out-Null
  Copy-Item -Path (Join-Path $tempRoot "*") -Destination $productionApp -Recurse -Force
} else {
  throw "Release archive did not contain a recognizable app structure."
}

$launcher = Join-Path $ProductionRoot "start.bat"
@"
@echo off
setlocal
set "TPVG_HOME=%~dp0"
set "TPVG_DATA_DIR=%TPVG_HOME%data"
cd /d "%TPVG_HOME%app"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":4173" ^| findstr "LISTENING"') do set "TPVG_PID=%%a"
if defined TPVG_PID (
  echo Temple Product Video Generator V1 is already running.
  start "" "http://127.0.0.1:4173"
  exit /b 0
)
start "" "http://127.0.0.1:4173"
python server.py
"@ | Set-Content -LiteralPath $launcher -Encoding ASCII

Copy-Item -LiteralPath (Join-Path $appSource "README.md") -Destination (Join-Path $ProductionRoot "README.md") -Force

Write-Host "Production app deployed: $productionApp"
Write-Host "Production data preserved: $productionData"
Write-Host "Launcher: $launcher"
