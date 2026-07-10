param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8766,
  [switch]$Mobile,
  [switch]$EnableOrder,
  [switch]$EnableAutomation,
  [switch]$EnableCancel,
  [switch]$Smoke
)

$ErrorActionPreference = "Stop"

function ConvertTo-PlainText {
  param([Security.SecureString]$SecureValue)
  if ($null -eq $SecureValue) {
    return ""
  }
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  } finally {
    if ($bstr -ne [IntPtr]::Zero) {
      [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
  }
}

function Read-SecretText {
  param([string]$Prompt)
  $secure = Read-Host -Prompt $Prompt -AsSecureString
  return ConvertTo-PlainText -SecureValue $secure
}

$python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = $repoRoot.Path

if ($Mobile) {
  $HostName = "0.0.0.0"
}

if ($Smoke) {
  & $python -m alphapilot_control_console.http_app --smoke
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "AlphaPilot OKX Demo Console Launcher" -ForegroundColor Cyan
Write-Host "Only OKX Demo Trading credentials should be used. Never paste live API keys here." -ForegroundColor Yellow
Write-Host "Keys are injected into this PowerShell process environment only and are not written to files." -ForegroundColor Yellow
Write-Host "Account site: Global (https://openapi.okx.com). Every private request uses x-simulated-trading: 1." -ForegroundColor Yellow
Write-Host ""

$apiKey = Read-SecretText "OKX Demo API Key"
$secretKey = Read-SecretText "OKX Demo Secret Key"
$passphrase = Read-SecretText "OKX Demo Passphrase"

if ([string]::IsNullOrWhiteSpace($apiKey) -or [string]::IsNullOrWhiteSpace($secretKey) -or [string]::IsNullOrWhiteSpace($passphrase)) {
  throw "OKX Demo API key, secret key, and passphrase are required for Demo mode."
}

$env:ALPHAPILOT_OKX_DEMO_ENABLED = "1"
$env:ALPHAPILOT_OKX_SITE = "global"
$env:ALPHAPILOT_OKX_DEMO_API_KEY = $apiKey
$env:ALPHAPILOT_OKX_DEMO_SECRET_KEY = $secretKey
$env:ALPHAPILOT_OKX_DEMO_PASSPHRASE = $passphrase
$env:ALPHAPILOT_OKX_DEMO_ORDER_ENABLED = if ($EnableOrder) { "1" } else { "0" }
$env:ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED = if ($EnableAutomation) { "1" } else { "0" }
$env:ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED = if ($EnableCancel) { "1" } else { "0" }

try {
  Write-Host ""
  Write-Host "Starting AlphaPilot Control Console with OKX Demo environment variables." -ForegroundColor Green
  Write-Host "URL: http://127.0.0.1:$Port/" -ForegroundColor Green
  if ($Mobile) {
    Write-Host "Mobile mode is enabled. Use the LAN URL shown in the console." -ForegroundColor Green
  }
  if (-not $EnableOrder) {
    Write-Host "Demo order smoke gate is OFF. Add -EnableOrder only for a connectivity smoke order." -ForegroundColor Yellow
  } else {
    Write-Host "Demo order smoke gate is ON. Smoke orders never count as strategy evidence or create a Demo Release." -ForegroundColor Yellow
  }
  if (-not $EnableCancel) {
    Write-Host "Demo cancel gate is OFF. Add -EnableCancel only for manual emergency cancel rehearsal." -ForegroundColor Yellow
  }
  if ($EnableAutomation -and -not $EnableOrder) {
    throw "-EnableAutomation requires -EnableOrder. Automatic Demo execution never bypasses the order gate."
  }
  if ($EnableAutomation) {
    Write-Host "Formal Demo automation gate is ON. Only immutable eligible Demo Releases can run; no release means no strategy order." -ForegroundColor Yellow
  }
  & $python -m alphapilot_control_console.http_app --host $HostName --port $Port
  exit $LASTEXITCODE
} finally {
  Remove-Item Env:\ALPHAPILOT_OKX_DEMO_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_SITE -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_DEMO_API_KEY -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_DEMO_SECRET_KEY -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_DEMO_PASSPHRASE -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_DEMO_ORDER_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED -ErrorAction SilentlyContinue
  Remove-Item Env:\ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED -ErrorAction SilentlyContinue
}
