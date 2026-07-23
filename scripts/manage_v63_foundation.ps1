param(
    [ValidateSet("Validate", "Start", "Stop", "Status", "Health", "Backup", "Restore")]
    [string]$Action = "Status",
    [string]$RepositoryRoot = "",
    [string]$PythonExecutable = "",
    [string]$StateRoot = "D:\Codex-Workspace\runtime\v63",
    [string]$RepositoryCommit = "",
    [string]$RepositoryTag = "v13.27.1.63-server-foundation-console",
    [string]$Roles = "all",
    [string]$StartupStatePath = "",
    [string]$SourceDatabase = "",
    [string]$DestinationDatabase = "",
    [string]$RestoreGuardPath = "",
    [double]$HeartbeatSeconds = 5,
    [double]$TimeoutSeconds = 30,
    [double]$MaximumAgeSeconds = 15
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $RepositoryRoot = Split-Path -Parent $scriptRoot
}
$RepositoryRoot = [System.IO.Path]::GetFullPath($RepositoryRoot)
$StateRoot = [System.IO.Path]::GetFullPath($StateRoot)

function Resolve-PythonExecutable {
    param([string]$Requested)
    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        $resolved = [System.IO.Path]::GetFullPath($Requested)
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw "Python executable not found: $resolved"
        }
        return $resolved
    }
    $candidates = @(
        (Join-Path $RepositoryRoot ".venv\Scripts\python.exe"),
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }
    throw "No supported AlphaPilot Python executable was found."
}

function Resolve-RepositoryCommit {
    if (-not [string]::IsNullOrWhiteSpace($RepositoryCommit)) {
        if ($RepositoryCommit -notmatch "^[0-9a-fA-F]{40}$") {
            throw "RepositoryCommit must be an exact 40-character Git SHA."
        }
        return $RepositoryCommit.ToLowerInvariant()
    }
    $gitCandidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:ALPHAPILOT_GIT)) {
        $gitCandidates += $env:ALPHAPILOT_GIT
    }
    $pathGit = Get-Command git -ErrorAction SilentlyContinue
    if ($null -ne $pathGit) {
        $gitCandidates += $pathGit.Source
    }
    $gitCandidates += (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe")
    foreach ($candidate in $gitCandidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        $value = (& $candidate -C $RepositoryRoot rev-parse HEAD 2>$null)
        if ($LASTEXITCODE -eq 0 -and "$value".Trim() -match "^[0-9a-fA-F]{40}$") {
            return "$value".Trim().ToLowerInvariant()
        }
    }
    throw "Unable to resolve the exact repository Commit."
}

function Write-Utf8JsonAtomic {
    param(
        [string]$Path,
        [object]$Value
    )
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = "$Path.tmp"
    $json = $Value | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText(
        $temporary,
        $json + [Environment]::NewLine,
        [System.Text.UTF8Encoding]::new($false)
    )
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function New-MaterializedManifest {
    $templatePath = Join-Path $RepositoryRoot "config\v63_server_foundation_manifest.template.json"
    if (-not (Test-Path -LiteralPath $templatePath -PathType Leaf)) {
        throw "V63 manifest template not found: $templatePath"
    }
    $manifest = Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $manifest.stateRoot = $StateRoot
    $manifest.repositoryCommit = Resolve-RepositoryCommit
    $manifest.repositoryTag = $RepositoryTag
    $manifestPath = Join-Path $StateRoot "config\v63_server_foundation_manifest.json"
    Write-Utf8JsonAtomic -Path $manifestPath -Value $manifest

    $mappingSource = Join-Path $RepositoryRoot "config\v63_server_directory_mapping.json"
    $mappingDestination = Join-Path $StateRoot "config\v63_server_directory_mapping.json"
    if (Test-Path -LiteralPath $mappingSource -PathType Leaf) {
        $mapping = Get-Content -LiteralPath $mappingSource -Raw -Encoding UTF8 | ConvertFrom-Json
        $mapping.localRepositoryRoot = $RepositoryRoot
        $mapping.localRuntimeRoot = $StateRoot
        Write-Utf8JsonAtomic -Path $mappingDestination -Value $mapping
    }
    return $manifestPath
}

$PythonExecutable = Resolve-PythonExecutable -Requested $PythonExecutable
$env:PYTHONPATH = $RepositoryRoot
$materializedManifest = Join-Path $StateRoot "config\v63_server_foundation_manifest.json"

if ($Action -in @("Validate", "Start") -or -not (Test-Path -LiteralPath $materializedManifest -PathType Leaf)) {
    $materializedManifest = New-MaterializedManifest
}

if ([string]::IsNullOrWhiteSpace($StartupStatePath)) {
    $StartupStatePath = Join-Path $RepositoryRoot "config\v63_startup_state.shadow_no_order.json"
}

$common = @(
    "--manifest", $materializedManifest,
    "--python-executable", $PythonExecutable,
    "--repository-root", $RepositoryRoot,
    "--roles", $Roles
)

switch ($Action) {
    "Validate" {
        & $PythonExecutable -m alphapilot_control_console.server_foundation.cli validate --manifest $materializedManifest
    }
    "Start" {
        & $PythonExecutable -m alphapilot_control_console.server_foundation.cli start @common `
            --startup-state $StartupStatePath `
            --heartbeat-seconds $HeartbeatSeconds `
            --timeout-seconds $TimeoutSeconds
    }
    "Stop" {
        & $PythonExecutable -m alphapilot_control_console.server_foundation.cli stop @common `
            --timeout-seconds $TimeoutSeconds
    }
    "Status" {
        & $PythonExecutable -m alphapilot_control_console.server_foundation.cli status @common `
            --maximum-age-seconds $MaximumAgeSeconds
    }
    "Health" {
        & $PythonExecutable -m alphapilot_control_console.server_foundation.cli health @common `
            --maximum-age-seconds $MaximumAgeSeconds
    }
    "Backup" {
        if ([string]::IsNullOrWhiteSpace($SourceDatabase)) {
            $SourceDatabase = Join-Path $StateRoot "foundation_leases.sqlite"
        }
        if ([string]::IsNullOrWhiteSpace($DestinationDatabase)) {
            $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
            $DestinationDatabase = Join-Path $StateRoot "backups\foundation_leases-$stamp.sqlite"
        }
        $receipt = "$DestinationDatabase.receipt.json"
        & $PythonExecutable -m alphapilot_control_console.server_foundation.cli backup `
            --source $SourceDatabase `
            --destination $DestinationDatabase `
            --receipt $receipt
    }
    "Restore" {
        if ([string]::IsNullOrWhiteSpace($SourceDatabase) -or
            [string]::IsNullOrWhiteSpace($DestinationDatabase) -or
            [string]::IsNullOrWhiteSpace($RestoreGuardPath)) {
            throw "Restore requires SourceDatabase, DestinationDatabase, and RestoreGuardPath."
        }
        $receipt = "$DestinationDatabase.restore-receipt.json"
        & $PythonExecutable -m alphapilot_control_console.server_foundation.cli restore `
            --source $SourceDatabase `
            --destination $DestinationDatabase `
            --guard $RestoreGuardPath `
            --receipt $receipt
    }
}

exit $LASTEXITCODE
