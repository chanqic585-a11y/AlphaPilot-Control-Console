param(
  [int]$ExpectedCount = 10
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
  throw "AlphaPilot console .venv is missing. Run scripts\setup_console_runtime.ps1 first."
}

Write-Host "Activating rollback-safe immutable Top100 Demo successors..." -ForegroundColor Cyan
& $python -m alphapilot_control_console.demo_release_successor_cli --expected-count $ExpectedCount
if ($LASTEXITCODE -ne 0) {
  throw "Top100 Demo successor activation failed. Existing releases remain unchanged or were rolled back."
}
