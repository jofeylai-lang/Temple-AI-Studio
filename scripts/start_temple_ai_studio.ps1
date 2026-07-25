param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
  [string]$DataRoot = "D:\AI\Temple AI Studio Production Data",
  [int]$TempleOsPort = 8766,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$DataRoot = [System.IO.Path]::GetFullPath($DataRoot)
$runtimeRoot = Join-Path $DataRoot "runtime"
$logRoot = Join-Path $DataRoot "logs\launcher"
$appData = Join-Path $DataRoot "applications\temple-product-video-generator"
$osData = Join-Path $DataRoot "temple-os"
$appServer = Join-Path $ProjectRoot "apps\temple-product-video-generator\server.py"
$osCli = Join-Path $ProjectRoot "scripts\temple_os_cli.py"

if (-not (Test-Path -LiteralPath $appServer) -or -not (Test-Path -LiteralPath $osCli)) {
  throw "Temple AI Studio program files are incomplete: $ProjectRoot"
}

New-Item -ItemType Directory -Force -Path $DataRoot, $runtimeRoot, $logRoot, $appData, $osData | Out-Null

$pathValue = [System.Environment]::GetEnvironmentVariable("Path", "Process")
$pathKeys = [System.Environment]::GetEnvironmentVariables(
  [System.EnvironmentVariableTarget]::Process
).Keys | Where-Object {
  ([string]$_).Equals("PATH", [System.StringComparison]::OrdinalIgnoreCase)
}
foreach ($key in @($pathKeys)) {
  [System.Environment]::SetEnvironmentVariable(
    [string]$key,
    $null,
    [System.EnvironmentVariableTarget]::Process
  )
}
[System.Environment]::SetEnvironmentVariable(
  "Path",
  $pathValue,
  [System.EnvironmentVariableTarget]::Process
)

$python = (Get-Command python -ErrorAction Stop).Source
$env:TEMPLE_PRODUCTION_DATA_ROOT = $DataRoot
$env:TPVG_DATA_DIR = $appData
$env:TPVG_PORT = "4173"

function Test-LocalPort {
  param([int]$Port)
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
    $connected = $result.AsyncWaitHandle.WaitOne(500) -and $client.Connected
    $client.Close()
    return $connected
  } catch {
    return $false
  }
}

function Start-TempleProcess {
  param(
    [string]$Name,
    [string]$Arguments,
    [string]$WorkingDirectory,
    [int]$Port
  )
  if (Test-LocalPort -Port $Port) {
    Write-Host "$Name is already running."
    return
  }
  $stdout = Join-Path $logRoot "$Name-stdout.log"
  $stderr = Join-Path $logRoot "$Name-stderr.log"
  $process = Start-Process `
    -FilePath $python `
    -ArgumentList $Arguments `
    -WorkingDirectory $WorkingDirectory `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru
  Set-Content -LiteralPath (Join-Path $runtimeRoot "$Name.pid") -Value $process.Id -Encoding ASCII
  Write-Host "$Name started with PID $($process.Id)."
}

$osArguments = "`"$osCli`" --root `"$osData`" serve --host 127.0.0.1 --port $TempleOsPort"
$appArguments = "`"$appServer`""
Start-TempleProcess -Name "temple-os" -Arguments $osArguments -WorkingDirectory $ProjectRoot -Port $TempleOsPort
Start-TempleProcess -Name "product-video-generator" -Arguments $appArguments -WorkingDirectory (Split-Path -Parent $appServer) -Port 4173

$appReady = $false
$osReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
  $appReady = Test-LocalPort -Port 4173
  $osReady = Test-LocalPort -Port $TempleOsPort
  if ($appReady -and $osReady) {
    break
  }
  Start-Sleep -Seconds 1
}
if (-not $appReady -or -not $osReady) {
  throw "Temple AI Studio services did not start within 30 seconds. See $logRoot"
}

if (-not $NoBrowser) {
  Start-Process "http://127.0.0.1:4173"
}
Write-Host "Temple AI Studio is ready: http://127.0.0.1:4173"
