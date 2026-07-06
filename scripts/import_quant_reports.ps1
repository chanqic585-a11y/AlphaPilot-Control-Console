$ErrorActionPreference = "Stop"

$python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$env:PYTHONPATH = (Resolve-Path ".").Path
& $python -m alphapilot_control_console.importer
