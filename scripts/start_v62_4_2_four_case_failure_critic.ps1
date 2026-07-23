param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$StrategyFactoryEvidenceRoot = "D:\Codex-Workspace\AlphaPilot-Acceptance-Handoff-V62.4.1-FINAL3-20260723-191612\05_strategy_factory",
    [string]$FormalResultRoot = "D:\Codex-Workspace\AlphaPilot-Acceptance-Handoff-V62.4.1-FINAL3-20260723-191612\05_strategy_factory\v62_4_1_formal\formal_results\v36_tsmom_formal_v35_tsmom_crypto_adaptation_f9927348723c6029\v35_tsmom_crypto_adaptation",
    [string]$StrategyFactoryDatabase = "D:\Codex-Workspace\AlphaPilot-Control-Console\data\strategy_factory\strategy_factory.sqlite",
    [string]$ValidationRoot = "D:\Codex-Workspace\validation",
    [string]$PythonPath = "D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Read-SecretText {
    param([Parameter(Mandatory = $true)][string]$Prompt)

    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Protect-DiagnosticText {
    param(
        [AllowEmptyString()][string]$Text,
        [AllowEmptyString()][string[]]$Secrets
    )

    $protected = [string]$Text
    foreach ($secret in $Secrets) {
        if (-not [string]::IsNullOrWhiteSpace($secret)) {
            $protected = $protected.Replace($secret, "[REDACTED]")
        }
    }
    return $protected
}

function Invoke-FourCaseFailureCritic {
    param(
        [Parameter(Mandatory = $true)][string]$OutputRoot,
        [Parameter(Mandatory = $true)][string]$DeepSeekKey,
        [Parameter(Mandatory = $true)][string]$GeminiKey
    )

    $arguments = @(
        "-m",
        "alphapilot_control_console.v62_4_2_failure_critic",
        "--repository-root", $RepositoryRoot,
        "--strategy-factory-evidence-root", $StrategyFactoryEvidenceRoot,
        "--formal-result-root", $FormalResultRoot,
        "--strategy-factory-database", $StrategyFactoryDatabase,
        "--output-root", $OutputRoot
    )
    $quotedArguments = @($arguments | ForEach-Object {
        '"{0}"' -f ([string]$_).Replace('"', '\"')
    })
    $processInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $processInfo.FileName = $PythonPath
    $processInfo.Arguments = $quotedArguments -join " "
    $processInfo.WorkingDirectory = $RepositoryRoot
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true

    $credentialNamesToRemove = @(
        "OPENAI_API_KEY",
        "OKX_API_KEY", "OKX_SECRET_KEY", "OKX_API_SECRET", "OKX_PASSPHRASE",
        "OKX_DEMO_API_KEY", "OKX_DEMO_SECRET_KEY", "OKX_DEMO_API_SECRET",
        "OKX_DEMO_PASSPHRASE", "OKX_LIVE_API_KEY", "OKX_LIVE_SECRET_KEY",
        "OKX_LIVE_API_SECRET", "OKX_LIVE_PASSPHRASE",
        "EXCHANGE_API_KEY", "EXCHANGE_API_SECRET", "EXCHANGE_PASSPHRASE"
    )
    foreach ($name in $credentialNamesToRemove) {
        [void]$processInfo.EnvironmentVariables.Remove($name)
    }
    $processInfo.EnvironmentVariables["DEEPSEEK_API_KEY"] = $DeepSeekKey
    $processInfo.EnvironmentVariables["GEMINI_API_KEY"] = $GeminiKey

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $processInfo
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(1200000)) {
        try { $process.Kill() } catch { }
        $process.WaitForExit()
        return [pscustomobject]@{
            ExitCode = 124
            Stdout = $stdoutTask.Result
            Stderr = "four-case failure critic exceeded the bounded timeout"
        }
    }
    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Stdout = $stdoutTask.Result
        Stderr = $stderrTask.Result
    }
}

foreach ($path in @(
    $PythonPath,
    (Join-Path $StrategyFactoryEvidenceRoot "pilot_failure_attribution.json"),
    $FormalResultRoot,
    $StrategyFactoryDatabase
)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required V62.4.2 input was not found: $path"
    }
}
New-Item -ItemType Directory -Path $ValidationRoot -Force | Out-Null

$deepseekKey = $null
$geminiKey = $null
try {
    Clear-Host
    Write-Host "AlphaPilot V62.4.2 Four-Case Dual-Model Failure Critic" -ForegroundColor Cyan
    Write-Host "Reads only three development failures, one formal failure, and negative research memory." -ForegroundColor Yellow
    Write-Host "Provider credentials are injected only into the isolated AI Worker; exchange credentials are removed." -ForegroundColor Yellow
    Write-Host "This run cannot approve a Release, ARM, create orders, or enable Live or Withdraw." -ForegroundColor Yellow
    Write-Host ""

    $deepseekKey = Read-SecretText -Prompt "Enter DEEPSEEK_API_KEY (input is hidden)"
    $geminiKey = Read-SecretText -Prompt "Enter GEMINI_API_KEY (input is hidden)"
    if ([string]::IsNullOrWhiteSpace($deepseekKey) -or [string]::IsNullOrWhiteSpace($geminiKey)) {
        throw "Both Provider credentials are required."
    }

    $confirmation = Read-Host "Type RUN_V62_4_2_FAILURE_CRITIC to authorize eight read-only external reviews"
    if ($confirmation -cne "RUN_V62_4_2_FAILURE_CRITIC") {
        Write-Host "External calls were not authorized. Exiting safely." -ForegroundColor Yellow
        return
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $outputRoot = Join-Path $ValidationRoot "v62-4-2-four-case-failure-critic-$timestamp"
    Write-Host ""
    Write-Host "Running independent DeepSeek and Gemini reviews for four cases..." -ForegroundColor Cyan
    $result = Invoke-FourCaseFailureCritic `
        -OutputRoot $outputRoot `
        -DeepSeekKey $deepseekKey `
        -GeminiKey $geminiKey
    $safeStdout = Protect-DiagnosticText -Text $result.Stdout -Secrets @($deepseekKey, $geminiKey)
    $safeStderr = Protect-DiagnosticText -Text $result.Stderr -Secrets @($deepseekKey, $geminiKey)
    if ($result.ExitCode -ne 0) {
        Write-Host "The four-case review did not complete. Redacted error:" -ForegroundColor Red
        Write-Host $safeStderr -ForegroundColor Red
        throw "V62.4.2 four-case Failure Critic failed."
    }

    $summary = $safeStdout | ConvertFrom-Json
    Write-Host ""
    Write-Host "Four-case review completed: $($summary.status)" -ForegroundColor Green
    Write-Host "Accepted cases: $($summary.acceptedCaseCount)/$($summary.caseCount)" -ForegroundColor Cyan
    Write-Host "Critical disagreement cases: $($summary.criticalDisagreementCaseCount)" -ForegroundColor Cyan
    Write-Host "Evidence directory: $outputRoot" -ForegroundColor Cyan
    Write-Host "Execution authorized: false; Demo/Live ARM: false; orders: 0." -ForegroundColor Yellow
}
finally {
    $env:DEEPSEEK_API_KEY = $null
    $env:GEMINI_API_KEY = $null
    $deepseekKey = $null
    $geminiKey = $null
    [GC]::Collect()
    Write-Host ""
    Write-Host "Provider credentials have been cleared from this process." -ForegroundColor Cyan
    Read-Host "Press Enter to close"
}
