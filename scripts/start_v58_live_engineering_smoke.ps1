$ErrorActionPreference = "Stop"

function ConvertTo-PlainText {
  param([Security.SecureString]$SecureValue)
  if ($null -eq $SecureValue) { return "" }
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally {
    if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  }
}

function Read-SecretText {
  param([string]$Prompt)
  return ConvertTo-PlainText -SecureValue (Read-Host -Prompt $Prompt -AsSecureString)
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = "D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  $python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
}
if (-not (Test-Path -LiteralPath $python)) { throw "AlphaPilot Python runtime is unavailable." }

Write-Host "AlphaPilot V58 OKX Live Engineering Smoke" -ForegroundColor Cyan
Write-Host "Use only the dedicated OKX Live Read+Trade key. Withdraw must remain disabled." -ForegroundColor Yellow
Write-Host "This approved one-shot smoke is capped at 10 USDT, 1x isolated, and must cancel to zero state." -ForegroundColor Yellow
Write-Host "Credentials stay in this PowerShell process and are cleared when the script exits." -ForegroundColor Yellow
Write-Host "The running OKX Demo console will not be restarted." -ForegroundColor Green

$apiKey = Read-SecretText "OKX Live API Key"
$secretKey = Read-SecretText "OKX Live Secret Key"
$passphrase = Read-SecretText "OKX Live Passphrase"
if (
  [string]::IsNullOrWhiteSpace($apiKey) -or
  [string]::IsNullOrWhiteSpace($secretKey) -or
  [string]::IsNullOrWhiteSpace($passphrase)
) {
  throw "All three OKX Live runtime credentials are required."
}

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $repoRoot
$env:ALPHAPILOT_OKX_SITE = "global"
$env:ALPHAPILOT_OKX_LIVE_API_KEY = $apiKey
$env:ALPHAPILOT_OKX_LIVE_SECRET_KEY = $secretKey
$env:ALPHAPILOT_OKX_LIVE_PASSPHRASE = $passphrase

try {
  Write-Host "Credentials received. Running the single approved V58 smoke now..." -ForegroundColor Green
  & $python (Join-Path $repoRoot "scripts/run_v58_live_engineering_smoke.py")
  if ($LASTEXITCODE -ne 0) {
    throw "V58 Live engineering smoke did not complete. Review the redacted status artifact."
  }
  Write-Host "V58 smoke completed and reconciled to zero state." -ForegroundColor Green
} finally {
  $apiKey = ""
  $secretKey = ""
  $passphrase = ""
  if ($null -eq $previousPythonPath) {
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
  } else {
    $env:PYTHONPATH = $previousPythonPath
  }
  Remove-Item Env:\ALPHAPILOT_OKX_SITE -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_API_KEY -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_SECRET_KEY -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_PASSPHRASE -ErrorAction SilentlyContinue
}
