# PSM v1.0.5 - opt-in local Rose-community legacy runtime compatibility test.
# ORIGINAL official v1.28.1 binaries only. No DLL modification or impersonation.
# Private source QA only; public installer distribution is not permitted here.
# Before Activate: run scripts/review_rose_ltk_v1281.ps1 and close League/PSM.
# Restore: powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\use_rose_legacy_runtime_local.ps1 -Action Restore
param(
    [ValidateSet("Activate", "Restore")]
    [string]$Action = "Activate",
    [string]$LeagueGameDir = "C:\Riot Games\League of Legends\Game"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Tools = Join-Path $Root "injection\tools"
$Candidate = Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
$StatePath = Join-Path $Tools "_v105_rose_legacy_local_state.json"
$OriginPath = Join-Path $Tools "_v105_runtime_origin.json"
$Pair = @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")

if ($env:OS -ne "Windows_NT") { throw "Windows required." }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python unavailable." }
$Active = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @(
        "PersonalSkinManager", "League of Legends",
        "League of Legends (TM) Client", "ltk_patcher_host"
    )
})
if ($Active.Count -gt 0) {
    throw "Close PSM, League gameplay, and the patcher host before changing local test inputs."
}

function Verify-ExistingPair([string]$Directory) {
    foreach ($Name in $Pair) {
        if (-not (Test-Path -LiteralPath (Join-Path $Directory $Name) -PathType Leaf)) {
            throw "Required runtime is missing: $Name"
        }
    }
}

if ($Action -eq "Restore") {
    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
        throw "No recorded legacy runtime session exists. No files changed."
    }
    $State = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($State.purpose -ne "PRIVATE_SOURCE_QA_ONLY" -or
        -not $State.backup_folder -or
        -not (Test-Path -LiteralPath $State.backup_folder -PathType Container)) {
        throw "Invalid local restore manifest. No files changed."
    }
    $Backup = [string]$State.backup_folder
    Verify-ExistingPair $Backup
    foreach ($Name in $Pair) {
        $Expected = [string]$State.original_sha256.$Name
        if (-not $Expected -or
            (Get-FileHash -LiteralPath (Join-Path $Backup $Name) -Algorithm SHA256).Hash -ne $Expected) {
            throw "Backup checksum mismatch: $Name. No files changed."
        }
    }
    foreach ($Name in $Pair) {
        Copy-Item -LiteralPath (Join-Path $Backup $Name) -Destination (Join-Path $Tools $Name) -Force
    }
    foreach ($Name in $Pair) {
        $Expected = [string]$State.original_sha256.$Name
        if ((Get-FileHash -LiteralPath (Join-Path $Tools $Name) -Algorithm SHA256).Hash -ne $Expected) {
            throw "Restored file checksum mismatch: $Name"
        }
    }
    $PreviousOrigin = Join-Path $Backup "_v105_runtime_origin.json"
    if (Test-Path -LiteralPath $PreviousOrigin -PathType Leaf) {
        Copy-Item -LiteralPath $PreviousOrigin -Destination $OriginPath -Force
    }
    elseif (Test-Path -LiteralPath $OriginPath -PathType Leaf) {
        Remove-Item -LiteralPath $OriginPath -Force
    }
    Remove-Item -LiteralPath $StatePath -Force
    Write-Host "Restored the original local LTK host/DLL pair." -ForegroundColor Green
    exit 0
}

if (Test-Path -LiteralPath $StatePath -PathType Leaf) {
    throw "Legacy runtime already activated. Run -Action Restore first."
}
Verify-ExistingPair $Tools
Verify-ExistingPair $Candidate
if (-not (Test-Path -LiteralPath $LeagueGameDir -PathType Container)) {
    throw "League Game directory not found; supply -LeagueGameDir."
}

Write-Warning "This selects the original historical LTK v1.28.1 pair for a PRIVATE LOCAL test."
Write-Warning "Its original release predates League 26.21 material-parser fixes."
Write-Warning "This is NOT a vendor-supported third-party integration; no installer may be released using this test state."

# Fail closed: first verify the official identity and installed League build.
& python (Join-Path $Root "scripts\audit_ltk_v1281_compatibility.py") --candidate-dir $Candidate --game-dir $LeagueGameDir
if ($LASTEXITCODE -ne 0) {
    throw "Official identity/game build audit failed. Active files were not changed."
}

$Backup = Join-Path $Root ("installer\candidates\v1.0.5\runtime-backup-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Backup -Force | Out-Null
$Hashes = @{}
foreach ($Name in $Pair) {
    $Source = Join-Path $Tools $Name
    $Hashes[$Name] = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
    Copy-Item -LiteralPath $Source -Destination (Join-Path $Backup $Name)
}
if (Test-Path -LiteralPath $OriginPath -PathType Leaf) {
    Copy-Item -LiteralPath $OriginPath -Destination (Join-Path $Backup "_v105_runtime_origin.json")
}

try {
    foreach ($Name in $Pair) {
        Copy-Item -LiteralPath (Join-Path $Candidate $Name) -Destination (Join-Path $Tools $Name) -Force
        if ((Get-FileHash -LiteralPath (Join-Path $Tools $Name) -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath (Join-Path $Candidate $Name) -Algorithm SHA256).Hash) {
            throw "Local copy checksum mismatch for $Name"
        }
    }
    $State = [ordered]@{
        purpose = "PRIVATE_SOURCE_QA_ONLY"
        source = "LeagueToolkit/ltk-manager"
        source_tag = "v1.28.1"
        source_commit = "9f06802de5d83d6dde3ff1644a1c56049fadf9bb"
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        backup_folder = $Backup
        original_sha256 = $Hashes
    }
    $State | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
    $Origin = [ordered]@{
        purpose = "LOCAL QA ONLY - NOT FOR DISTRIBUTION"
        source = "LeagueToolkit/ltk-manager"
        source_tag = "v1.28.1"
        source_commit = "9f06802de5d83d6dde3ff1644a1c56049fadf9bb"
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        backup_folder = $Backup
    }
    $Origin | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $OriginPath -Encoding UTF8
}
catch {
    foreach ($Name in $Pair) {
        if (Test-Path -LiteralPath (Join-Path $Backup $Name) -PathType Leaf) {
            Copy-Item -LiteralPath (Join-Path $Backup $Name) -Destination (Join-Path $Tools $Name) -Force
        }
    }
    $OldOrigin = Join-Path $Backup "_v105_runtime_origin.json"
    if (Test-Path -LiteralPath $OldOrigin -PathType Leaf) {
        Copy-Item -LiteralPath $OldOrigin -Destination $OriginPath -Force
    }
    elseif (Test-Path -LiteralPath $OriginPath -PathType Leaf) {
        Remove-Item -LiteralPath $OriginPath -Force
    }
    if (Test-Path -LiteralPath $StatePath -PathType Leaf) {
        Remove-Item -LiteralPath $StatePath -Force
    }
    throw
}
Write-Host "Official historical LTK host/DLL selected for LOCAL SOURCE QA." -ForegroundColor Green
Write-Host "Backup retained under: $Backup"
Write-Host "Run scripts/run_live_qa.ps1 for source-only Practice Tool testing."
Write-Host "Restore afterward using -Action Restore. Do not build or publish an installer."
