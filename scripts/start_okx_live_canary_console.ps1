param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8766,
  [switch]$Mobile,
  [switch]$EnableReadOnly,
  [switch]$EnableCanary,
  [switch]$EnableOrder,
  [switch]$EnableAutomation,
  [switch]$Smoke
)

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

$python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path -LiteralPath $python)) { $python = "python" }
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = $repoRoot.Path
if ($Mobile) { $HostName = "0.0.0.0" }
if ($Smoke) {
  & $python -m alphapilot_control_console.http_app --smoke
  exit $LASTEXITCODE
}
if (($EnableCanary -or $EnableOrder) -and -not $EnableReadOnly) {
  throw "-EnableCanary and -EnableOrder require -EnableReadOnly."
}
if ($EnableOrder -and -not $EnableCanary) {
  throw "-EnableOrder requires -EnableCanary."
}
if ($EnableAutomation -and -not $EnableOrder) {
  throw "-EnableAutomation requires -EnableOrder."
}

Write-Host "AlphaPilot OKX Live Canary Launcher" -ForegroundColor Cyan
Write-Host "Use a dedicated OKX Live Read+Trade key with Withdraw disabled." -ForegroundColor Yellow
Write-Host "Credentials remain in this process only and are never written to files." -ForegroundColor Yellow
Write-Host "All Live gates are OFF unless their switches are provided." -ForegroundColor Yellow

$apiKey = ""
$secretKey = ""
$passphrase = ""
if ($EnableReadOnly) {
  $apiKey = Read-SecretText "OKX Live API Key"
  $secretKey = Read-SecretText "OKX Live Secret Key"
  $passphrase = Read-SecretText "OKX Live Passphrase"
  if ([string]::IsNullOrWhiteSpace($apiKey) -or [string]::IsNullOrWhiteSpace($secretKey) -or [string]::IsNullOrWhiteSpace($passphrase)) {
    throw "All three OKX Live runtime credentials are required."
  }
}
if ($EnableCanary -or $EnableOrder -or $EnableAutomation) {
  $confirmation = Read-Host "Type ENABLE_OKX_LIVE_CANARY_PROCESS to open process gates"
  if ($confirmation -cne "ENABLE_OKX_LIVE_CANARY_PROCESS") {
    throw "Exact Live Canary process confirmation is required."
  }
}

$env:ALPHAPILOT_OKX_SITE = "global"
$env:ALPHAPILOT_OKX_LIVE_ENABLED = if ($EnableReadOnly) { "1" } else { "0" }
$env:ALPHAPILOT_OKX_LIVE_READ_ENABLED = if ($EnableReadOnly) { "1" } else { "0" }
$env:ALPHAPILOT_OKX_LIVE_CANARY_ENABLED = if ($EnableCanary) { "1" } else { "0" }
$env:ALPHAPILOT_OKX_LIVE_ORDER_ENABLED = if ($EnableOrder) { "1" } else { "0" }
$env:ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED = if ($EnableAutomation) { "1" } else { "0" }
$env:ALPHAPILOT_OKX_LIVE_API_KEY = $apiKey
$env:ALPHAPILOT_OKX_LIVE_SECRET_KEY = $secretKey
$env:ALPHAPILOT_OKX_LIVE_PASSPHRASE = $passphrase

try {
  Write-Host "Starting at http://127.0.0.1:$Port/" -ForegroundColor Green
  Write-Host "Read=$EnableReadOnly Canary=$EnableCanary Order=$EnableOrder Automation=$EnableAutomation" -ForegroundColor Yellow
  Write-Host "A matching LiveRelease, RiskProfile, reconciliation, and UI ARM confirmation are still required." -ForegroundColor Yellow
  & $python -m alphapilot_control_console.http_app --host $HostName --port $Port
  exit $LASTEXITCODE
} finally {
  Remove-Item Env:\ALPHAPILOT_OKX_SITE -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_READ_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_CANARY_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_ORDER_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_API_KEY -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_SECRET_KEY -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_LIVE_PASSPHRASE -ErrorAction SilentlyContinue
}
