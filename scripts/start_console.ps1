param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8766,
  [switch]$Smoke
)

$ErrorActionPreference = "Stop"

$python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$env:PYTHONPATH = (Resolve-Path ".").Path

if ($Smoke) {
  & $python -m alphapilot_control_console.http_app --smoke
  exit $LASTEXITCODE
}

& $python -m alphapilot_control_console.http_app --host $HostName --port $Port
