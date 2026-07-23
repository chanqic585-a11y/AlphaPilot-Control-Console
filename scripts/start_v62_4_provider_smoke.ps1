param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$DataRoot = "D:\Codex-Workspace\validation\v62-4-provider-smoke",
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

function Invoke-CapturedPython {
    param(
        [Parameter(Mandatory = $true)][string]$Module,
        [Parameter(Mandatory = $true)][string[]]$ModuleArguments,
        [Parameter(Mandatory = $true)][hashtable]$Environment,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $quoted = @($ModuleArguments | ForEach-Object {
        '"{0}"' -f ([string]$_).Replace('"', '\"')
    })
    $processInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $processInfo.FileName = $PythonPath
    $processInfo.Arguments = "-m $Module " + ($quoted -join " ")
    $processInfo.WorkingDirectory = $RepositoryRoot
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true

    $exchangeCredentialNames = @(
        "OKX_API_KEY", "OKX_SECRET_KEY", "OKX_API_SECRET", "OKX_PASSPHRASE",
        "OKX_DEMO_API_KEY", "OKX_DEMO_SECRET_KEY", "OKX_DEMO_API_SECRET",
        "OKX_DEMO_PASSPHRASE", "OKX_LIVE_API_KEY", "OKX_LIVE_SECRET_KEY",
        "OKX_LIVE_API_SECRET", "OKX_LIVE_PASSPHRASE"
    )
    foreach ($name in $exchangeCredentialNames) {
        [void]$processInfo.EnvironmentVariables.Remove($name)
    }
    foreach ($name in $Environment.Keys) {
        $processInfo.EnvironmentVariables[[string]$name] = [string]$Environment[$name]
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $processInfo
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        try { $process.Kill() } catch { }
        $process.WaitForExit()
        return [pscustomobject]@{
            ExitCode = 124
            Stdout = $stdoutTask.Result
            Stderr = "provider smoke exceeded the bounded timeout"
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
New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null

$deepseekKey = $null
$geminiKey = $null
try {
    Clear-Host
    Write-Host "AlphaPilot V62.4 DeepSeek + Gemini 安全配置" -ForegroundColor Cyan
    Write-Host "凭据仅注入当前 PowerShell 子进程，不写入配置、日志、SQLite 或网页。" -ForegroundColor Yellow
    Write-Host "请勿在 Codex 对话中粘贴任何 Key。" -ForegroundColor Yellow
    Write-Host ""

    $deepseekKey = Read-SecretText -Prompt "请输入 DEEPSEEK_API_KEY（输入不会显示）"
    $geminiKey = Read-SecretText -Prompt "请输入 GEMINI_API_KEY（输入不会显示）"
    if ([string]::IsNullOrWhiteSpace($deepseekKey) -or [string]::IsNullOrWhiteSpace($geminiKey)) {
        throw "两项 Provider 凭据都必须输入。"
    }

    $providerEnvironment = @{
        DEEPSEEK_API_KEY = $deepseekKey
        GEMINI_API_KEY = $geminiKey
    }
    $readinessArguments = @{
        Module = "alphapilot_control_console.ai_orchestration.provider_readiness"
        ModuleArguments = @("--repository-root", $RepositoryRoot)
        Environment = $providerEnvironment
        TimeoutSeconds = 30
    }
    $readiness = Invoke-CapturedPython @readinessArguments
    $readinessText = Protect-DiagnosticText -Text $readiness.Stdout -Secrets @($deepseekKey, $geminiKey)
    if ($readiness.ExitCode -ne 0) {
        $readinessError = Protect-DiagnosticText -Text $readiness.Stderr -Secrets @($deepseekKey, $geminiKey)
        throw "Readiness 失败：$readinessError"
    }
    $readinessReport = $readinessText | ConvertFrom-Json
    if ($readinessReport.status -ne "provider_credentials_ready") {
        throw "Readiness 未通过：$($readinessReport.status)"
    }

    Write-Host ""
    Write-Host "Readiness 已通过：provider_credentials_ready" -ForegroundColor Green
    Write-Host "固定脱敏输入 Hash：$($readinessReport.providerSmokeInputHash)" -ForegroundColor Cyan
    Write-Host "最多 3 次只读外部调用；每次最多 512 输出 Token、0.05 USD。" -ForegroundColor Yellow
    $confirmation = Read-Host "确认执行请输入 RUN_PROVIDER_SMOKE；其他输入将安全退出"
    if ($confirmation -cne "RUN_PROVIDER_SMOKE") {
        Write-Host "未授权外部调用，已安全退出。" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "正在依次执行 DeepSeek-only、Gemini-only、双模型独立审查..." -ForegroundColor Cyan
    $smokeArguments = @{
        Module = "alphapilot_control_console.ai_orchestration.provider_smoke"
        ModuleArguments = @(
            "--repository-root", $RepositoryRoot,
            "--data-root", $DataRoot
        )
        Environment = $providerEnvironment
        TimeoutSeconds = 330
    }
    $smoke = Invoke-CapturedPython @smokeArguments

    $safeStdout = Protect-DiagnosticText -Text $smoke.Stdout -Secrets @($deepseekKey, $geminiKey)
    $safeStderr = Protect-DiagnosticText -Text $smoke.Stderr -Secrets @($deepseekKey, $geminiKey)
    $statusPath = Join-Path $DataRoot "last_provider_smoke_status.json"
    $diagnosticPath = Join-Path $DataRoot "last_provider_smoke_diagnostic.txt"
    if (-not [string]::IsNullOrWhiteSpace($safeStdout)) {
        [IO.File]::WriteAllText($statusPath, $safeStdout.Trim() + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    }
    $diagnostic = @(
        "exitCode=$($smoke.ExitCode)",
        "stdout:",
        $safeStdout.Trim(),
        "stderr:",
        $safeStderr.Trim()
    ) -join [Environment]::NewLine
    [IO.File]::WriteAllText($diagnosticPath, $diagnostic + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))

    try {
        $report = $safeStdout | ConvertFrom-Json
        Write-Host ""
        Write-Host "Provider Smoke：$($report.status)" -ForegroundColor $(if ($report.status -eq "provider_smoke_passed") { "Green" } else { "Red" })
        foreach ($check in @($report.checks)) {
            $detail = if ($check.errorType) { " · $($check.errorType): $($check.errorMessage)" } else { "" }
            Write-Host "- $($check.taskType)：$($check.status)$detail"
        }
        if ($report.failureStage) {
            Write-Host "- $($report.failureStage)：$($report.errorType): $($report.errorMessage)" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "Provider Smoke 未返回可解析 JSON；完整脱敏诊断已保存。" -ForegroundColor Red
    }
    Write-Host "脱敏状态：$statusPath" -ForegroundColor Cyan
    Write-Host "脱敏诊断：$diagnosticPath" -ForegroundColor Cyan
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
