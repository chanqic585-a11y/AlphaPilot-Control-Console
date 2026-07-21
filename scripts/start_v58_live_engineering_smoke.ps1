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
    $statusPath = Join-Path $repoRoot "reports\v54_v60\v58_live_engineering_smoke\live_engineering_smoke_status.json"
    $safeBlockerCode = "unclassified_preflight_failure"
    $safeInstrumentId = ""
    if (Test-Path -LiteralPath $statusPath) {
      try {
        $statusPayload = Get-Content -LiteralPath $statusPath -Encoding UTF8 -Raw | ConvertFrom-Json
        if (-not [string]::IsNullOrWhiteSpace([string]$statusPayload.safeBlockerCode)) {
          $safeBlockerCode = [string]$statusPayload.safeBlockerCode
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$statusPayload.safeInstrumentId)) {
          $safeInstrumentId = [string]$statusPayload.safeInstrumentId
        }
      } catch {
        $safeBlockerCode = "status_artifact_unreadable"
      }
    }
    $nextAction = switch ($safeBlockerCode) {
      "account_instruments_unavailable" { "Verify this is a Global OKX Live Read+Trade key, its IP allowlist, and API permissions." }
      "account_config_unavailable" { "Verify the Live API key, site, IP allowlist, and Read permission." }
      "account_config_invalid" { "Review the OKX account configuration response before retrying." }
      "unsupported_position_mode" { "Use OKX net mode or long/short mode for this bounded smoke." }
      "available_usdt_unavailable" { "Verify the Live trading account exposes an available USDT balance." }
      "insufficient_available_usdt" { "Keep at least 10 USDT available in the Live trading account." }
      "positions_unavailable" { "Verify the key can read Live swap positions." }
      "nonzero_initial_positions" { "Close all Live swap positions before retrying the zero-state smoke." }
      "open_orders_unavailable" { "Verify the key can read Live pending orders." }
      "nonzero_initial_open_orders" { "Cancel all Live pending swap orders before retrying." }
      "leverage_unavailable" { "Verify the key can read leverage for the selected USDT swap." }
      "isolated_leverage_not_1x" {
        if ([string]::IsNullOrWhiteSpace($safeInstrumentId)) {
          "Preconfigure the selected USDT swap to 1x isolated leverage, then retry."
        } else {
          "Preconfigure $safeInstrumentId to 1x isolated leverage, then retry."
        }
      }
      "public_instruments_unavailable" { "Check network access to OKX public instrument metadata." }
      "public_tickers_unavailable" { "Check network access to OKX public ticker data." }
      "no_eligible_bounded_instrument" { "No major contract fits the frozen 10 USDT cap; a larger cap requires a new approval." }
      default { "Review the redacted status artifact before retrying." }
    }
    Write-Host "Preflight blocker: $safeBlockerCode" -ForegroundColor Red
    if (-not [string]::IsNullOrWhiteSpace($safeInstrumentId)) {
      Write-Host "Selected instrument: $safeInstrumentId" -ForegroundColor Cyan
    }
    Write-Host "Next action: $nextAction" -ForegroundColor Yellow
    throw "V58 Live engineering smoke did not complete before order submission."
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
