param(
  [string]$BaseUrl = "http://127.0.0.1:8766"
)

$ErrorActionPreference = "Stop"

$base = $BaseUrl.TrimEnd("/")

function Read-JsonEndpoint {
  param([string]$Path)
  $response = Invoke-WebRequest -UseBasicParsing "$base$Path" -TimeoutSec 5
  if ($response.StatusCode -ne 200) {
    throw "$Path returned HTTP $($response.StatusCode)"
  }
  return $response.Content | ConvertFrom-Json
}

$health = Read-JsonEndpoint "/api/health"
$mobile = Read-JsonEndpoint "/api/mobile/status"
$connection = Read-JsonEndpoint "/api/mobile/connection-info"

if ($health.safetyBoundary.tradeApiAllowed -ne $false) {
  throw "Safety check failed: tradeApiAllowed must be false."
}
if ($mobile.safetyBoundary.orderCreationAllowed -ne $false) {
  throw "Safety check failed: orderCreationAllowed must be false."
}
if ($connection.safetyBoundary.automaticTradingAllowed -ne $false) {
  throw "Safety check failed: automaticTradingAllowed must be false."
}

[pscustomobject]@{
  ok = $true
  baseUrl = $base
  version = $health.version
  strategyCount = $mobile.strategyCount
  recommendedMobileUrl = $connection.recommendedMobileUrl
  serverLanVisible = $connection.serverLanVisible
  lanAddressCount = @($connection.lanAddresses).Count
  tradeApiAllowed = $health.safetyBoundary.tradeApiAllowed
  orderCreationAllowed = $mobile.safetyBoundary.orderCreationAllowed
  automaticTradingAllowed = $connection.safetyBoundary.automaticTradingAllowed
} | ConvertTo-Json -Depth 5
