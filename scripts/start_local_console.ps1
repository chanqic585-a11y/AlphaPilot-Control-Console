[CmdletBinding()]
param(
    [string]$RepositoryPath = "",
    [string]$PythonPath = "",
    [string]$ConsoleUrl = "http://127.0.0.1:8766/",
    [ValidateRange(10, 300)]
    [int]$StartupTimeoutSeconds = 120,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepositoryPath)) {
    $RepositoryPath = Split-Path -Parent $PSScriptRoot
}

function Get-ConsoleHealth {
    param([int]$TimeoutSeconds = 3)

    try {
        return Invoke-RestMethod -UseBasicParsing -Uri ($ConsoleUrl + "api/health") -TimeoutSec $TimeoutSeconds
    }
    catch {
        return $null
    }
}

function Open-ConsoleBrowser {
    if ($NoBrowser) {
        return
    }

    try {
        Start-Process -FilePath "explorer.exe" -ArgumentList $ConsoleUrl -ErrorAction Stop
    }
    catch {
        Start-Process -FilePath $ConsoleUrl
    }
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $PythonPath = Join-Path $RepositoryPath ".venv\Scripts\python.exe"
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "AlphaPilot console Python was not found: $PythonPath. Run scripts\setup_console_runtime.ps1 first."
}

& $PythonPath -c "import websocket; assert websocket.__version__ == '1.8.0'" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Pinned websocket-client 1.8.0 is unavailable. Run scripts\setup_console_runtime.ps1 first."
}

$existingHealth = Get-ConsoleHealth
if ($null -ne $existingHealth -and $existingHealth.ok -eq $true) {
    Write-Host "[AlphaPilot] Control Console is already running; reusing the healthy process."
    Open-ConsoleBrowser
    exit 0
}

$consoleUri = [Uri]$ConsoleUrl
$listener = Get-NetTCPConnection -State Listen -LocalPort $consoleUri.Port -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($null -ne $listener) {
    $listenerProcessId = [int]$listener.OwningProcess
    $listenerProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$listenerProcessId"
    $isAlphaPilotConsole = $null -ne $listenerProcess -and
        $listenerProcess.Name -like "python*" -and
        $listenerProcess.CommandLine -like "*alphapilot_control_console.http_app*"

    if (-not $isAlphaPilotConsole) {
        throw "Another process owns port $($consoleUri.Port); refusing to stop it."
    }

    Write-Host "[AlphaPilot] Replacing an unhealthy verified AlphaPilot listener."
    Stop-Process -Id $listenerProcessId -Force

    $releaseDeadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        Start-Sleep -Milliseconds 250
        $listener = Get-NetTCPConnection -State Listen -LocalPort $consoleUri.Port -ErrorAction SilentlyContinue |
            Select-Object -First 1
    } while ($null -ne $listener -and [DateTime]::UtcNow -lt $releaseDeadline)

    if ($null -ne $listener) {
        throw "AlphaPilot port $($consoleUri.Port) did not become available."
    }
}

Write-Host "[AlphaPilot] Starting local Control Console..."
Write-Host "[AlphaPilot] Repository: $RepositoryPath"

$server = Start-Process -FilePath $PythonPath `
    -ArgumentList "-m", "alphapilot_control_console.http_app" `
    -WorkingDirectory $RepositoryPath `
    -WindowStyle Hidden `
    -PassThru

$deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
$health = $null
while ([DateTime]::UtcNow -lt $deadline) {
    if ($server.HasExited) {
        throw "Control Console process exited before becoming healthy (exit code $($server.ExitCode))."
    }

    $health = Get-ConsoleHealth
    if ($null -ne $health -and $health.ok -eq $true) {
        break
    }

    Start-Sleep -Milliseconds 500
}

if ($null -eq $health -or $health.ok -ne $true) {
    throw "Control Console did not become healthy within $StartupTimeoutSeconds seconds."
}

$version = if ($health.version) { $health.version } elseif ($health.controlConsoleVersion) { $health.controlConsoleVersion } else { "unknown version" }
Write-Host "[AlphaPilot] Control Console is running: $version"
Open-ConsoleBrowser
