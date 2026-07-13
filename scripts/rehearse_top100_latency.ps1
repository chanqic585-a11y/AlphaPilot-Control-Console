param(
  [int]$Iterations = 20,
  [int]$ReleaseCount = 10
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$report = Join-Path $repoRoot "data\ops\v13_27_9_top100_latency_rehearsal.json"

if (-not (Test-Path -LiteralPath $python)) {
  throw "AlphaPilot console .venv is missing. Run scripts\setup_console_runtime.ps1 first."
}

& $python -m alphapilot_control_console.top100_latency_rehearsal --iterations $Iterations --release-count $ReleaseCount --report $report
if ($LASTEXITCODE -ne 0) {
  throw "Top100 no-order latency rehearsal failed."
}

Write-Host "No-order rehearsal report: $report" -ForegroundColor Green
