param(
  [string]$DataRoot = "D:\AI\Temple AI Studio Production Data"
)

$ErrorActionPreference = "Stop"
$runtimeRoot = Join-Path ([System.IO.Path]::GetFullPath($DataRoot)) "runtime"

foreach ($name in @("product-video-generator", "temple-os")) {
  $pidPath = Join-Path $runtimeRoot "$name.pid"
  if (-not (Test-Path -LiteralPath $pidPath)) {
    Write-Host "$name has no running process record."
    continue
  }
  $processId = [int](Get-Content -LiteralPath $pidPath -Raw)
  $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $processId
    Write-Host "$name stopped."
  } else {
    Write-Host "$name was already stopped."
  }
  Remove-Item -LiteralPath $pidPath -Force
}
