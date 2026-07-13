param(
  [string]$PythonPath = (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvRoot = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$requirements = Join-Path $repoRoot "requirements.txt"

if (-not (Test-Path -LiteralPath $PythonPath)) {
  throw "Bundled Python was not found at $PythonPath. Pass -PythonPath with a verified Python 3 executable."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
  Write-Host "Creating AlphaPilot console virtual environment..." -ForegroundColor Cyan
  & $PythonPath -m venv $venvRoot
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create .venv."
  }
}

Write-Host "Installing pinned console runtime dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install --requirement $requirements --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
  throw "Failed to install console runtime dependencies."
}

& $venvPython -c "import websocket; print('websocket-client ' + websocket.__version__)"
if ($LASTEXITCODE -ne 0) {
  throw "websocket-client verification failed."
}

Write-Host "AlphaPilot console runtime is ready: $venvPython" -ForegroundColor Green
