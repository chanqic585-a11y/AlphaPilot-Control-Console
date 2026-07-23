param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$FormalResultRoot = "D:\Codex-Workspace\worktrees\alphapilot-v62-4-1-blocker-closeout\quant\reports\formal_validation\v62_4_1_tsmom_formal_results\v36_tsmom_formal_v35_tsmom_crypto_adaptation_f9927348723c6029\v35_tsmom_crypto_adaptation",
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

function Invoke-FailureCritic {
    param(
        [Parameter(Mandatory = $true)][string]$OutputRoot,
        [Parameter(Mandatory = $true)][string]$DeepSeekKey,
        [Parameter(Mandatory = $true)][string]$GeminiKey
    )

    $arguments = @(
        "-m",
        "alphapilot_control_console.v62_4_1_failure_critic_acceptance",
        "--repository-root", $RepositoryRoot,
        "--formal-result-root", $FormalResultRoot,
        "--strategy-factory-database", $StrategyFactoryDatabase,
        "--output-root", $OutputRoot,
        "--candidate-id", "v35_tsmom_crypto_adaptation"
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
    if (-not $process.WaitForExit(420000)) {
        try {
            $process.Kill()
        }
        catch {
        }
        $process.WaitForExit()
        return [pscustomobject]@{
            ExitCode = 124
            Stdout = $stdoutTask.Result
            Stderr = "failure critic acceptance exceeded the bounded timeout"
        }
    }
    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Stdout = $stdoutTask.Result
        Stderr = $stderrTask.Result
    }
}

if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "AlphaPilot Python was not found: $PythonPath"
}
if (-not (Test-Path -LiteralPath $FormalResultRoot -PathType Container)) {
    throw "Formal result root was not found: $FormalResultRoot"
}
if (-not (Test-Path -LiteralPath $StrategyFactoryDatabase -PathType Leaf)) {
    throw "Strategy Factory database was not found: $StrategyFactoryDatabase"
}
New-Item -ItemType Directory -Path $ValidationRoot -Force | Out-Null

$deepseekKey = $null
$geminiKey = $null
try {
    Clear-Host
    Write-Host "AlphaPilot V62.4.1 双模型失败归因独立验收" -ForegroundColor Cyan
    Write-Host "只读取冻结 Formal 失败结果和历史失败研究记忆。" -ForegroundColor Yellow
    Write-Host "凭据仅注入当前 PowerShell 子进程；AI Worker 不继承任何交易所凭据。" -ForegroundColor Yellow
    Write-Host "不会批准 Release、不会 ARM、不会创建订单，也不会启用 Live 或 Withdraw。" -ForegroundColor Yellow
    Write-Host ""

    $deepseekKey = Read-SecretText -Prompt "请输入 DEEPSEEK_API_KEY（输入不会显示）"
    $geminiKey = Read-SecretText -Prompt "请输入 GEMINI_API_KEY（输入不会显示）"
    if ([string]::IsNullOrWhiteSpace($deepseekKey) -or [string]::IsNullOrWhiteSpace($geminiKey)) {
        throw "两项 Provider 凭据都必须输入。"
    }

    $confirmation = Read-Host "确认执行两次只读外部审查请输入 RUN_FAILURE_CRITIC_ACCEPTANCE"
    if ($confirmation -cne "RUN_FAILURE_CRITIC_ACCEPTANCE") {
        Write-Host "未授权外部调用，已安全退出。" -ForegroundColor Yellow
        return
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $outputRoot = Join-Path $ValidationRoot "v62-4-1-failure-critic-$timestamp"
    Write-Host ""
    Write-Host "正在执行 DeepSeek 与 Gemini 独立失败归因审查..." -ForegroundColor Cyan
    $result = Invoke-FailureCritic `
        -OutputRoot $outputRoot `
        -DeepSeekKey $deepseekKey `
        -GeminiKey $geminiKey
    $safeStdout = Protect-DiagnosticText -Text $result.Stdout -Secrets @($deepseekKey, $geminiKey)
    $safeStderr = Protect-DiagnosticText -Text $result.Stderr -Secrets @($deepseekKey, $geminiKey)

    if ($result.ExitCode -ne 0) {
        Write-Host "独立验收未完成。脱敏错误如下：" -ForegroundColor Red
        Write-Host $safeStderr -ForegroundColor Red
        throw "V62.4.1 failure critic acceptance failed."
    }

    $summary = $safeStdout | ConvertFrom-Json
    Write-Host ""
    Write-Host "独立验收已完成：$($summary.status)" -ForegroundColor Green
    Write-Host "报告 Hash：$($summary.reportHash)" -ForegroundColor Cyan
    Write-Host "证据目录：$outputRoot" -ForegroundColor Cyan
    Write-Host "执行授权：false；Demo/Live ARM：false；订单：0。" -ForegroundColor Yellow
}
finally {
    $env:DEEPSEEK_API_KEY = $null
    $env:GEMINI_API_KEY = $null
    $deepseekKey = $null
    $geminiKey = $null
    [GC]::Collect()
    Write-Host ""
    Write-Host "当前进程中的 Provider 凭据已清除。" -ForegroundColor Cyan
    Read-Host "按 Enter 关闭窗口"
}
