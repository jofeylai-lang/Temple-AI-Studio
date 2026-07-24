param(
  [string]$InstallRoot = "D:\AI\Temple AI Studio",
  [string]$DataRoot = "D:\AI\Temple AI Studio Production Data"
)

$ErrorActionPreference = "Stop"
$sourceRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$installRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$dataRoot = [System.IO.Path]::GetFullPath($DataRoot)
$manifest = Join-Path $sourceRoot "RELEASE_MANIFEST.json"

if (-not (Test-Path -LiteralPath $manifest)) {
  throw "Installation is allowed only from a commercial-acceptance release."
}

$parent = Split-Path -Parent $installRoot
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$staging = Join-Path $parent ("Temple AI Studio.staging-" + [guid]::NewGuid().ToString("N"))
$backupRoot = Join-Path $parent "Temple AI Studio Deployment Backups"
New-Item -ItemType Directory -Force -Path $parent, $dataRoot, $backupRoot, $staging | Out-Null

Get-ChildItem -LiteralPath $sourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $staging -Recurse -Force
}

if (Test-Path -LiteralPath $installRoot) {
  $backup = Join-Path $backupRoot "before-$stamp"
  Move-Item -LiteralPath $installRoot -Destination $backup
  Write-Host "Previous program files were backed up: $backup"
}
Move-Item -LiteralPath $staging -Destination $installRoot

foreach ($relative in @(
  "applications\temple-product-video-generator",
  "backups",
  "emma",
  "evidence",
  "exports",
  "health",
  "knowledge",
  "logs",
  "models",
  "projects",
  "providers",
  "runtime",
  "temporary",
  "temple-os",
  "workflows"
)) {
  New-Item -ItemType Directory -Force -Path (Join-Path $dataRoot $relative) | Out-Null
}

$desktop = [Environment]::GetFolderPath("Desktop")
if ($desktop) {
  try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcutName = ([char]0x555F).ToString() + ([char]0x52D5).ToString() + " Temple AI Studio.lnk"
    $shortcut = $shell.CreateShortcut((Join-Path $desktop $shortcutName))
    $shortcut.TargetPath = Join-Path $installRoot "start_temple_ai_studio.bat"
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.Description = "Start Temple AI Studio"
    $shortcut.Save()
    Write-Host "Desktop shortcut created."
  } catch {
    Write-Warning "Desktop shortcut could not be created: $($_.Exception.Message)"
  }
}

Write-Host "Temple AI Studio installed: $installRoot"
Write-Host "User data: $dataRoot"
Write-Host "Launch: $(Join-Path $installRoot 'start_temple_ai_studio.bat')"
