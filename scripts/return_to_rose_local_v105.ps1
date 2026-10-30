# Local-only rollback to the source-tested Rose-style LTK v1.28.1 pair.
# This does not rebuild, sign, install, publish or alter the game.
# Preserves the working signed source pair when already active.
param(
    [ValidateSet("Prepare", "Status", "Run")]
    [string]$Action = "Prepare",
    [string]$LeagueGameDir = "C:\Riot Games\League of Legends\Game",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Legacy = Join-Path $Root "scripts\use_rose_legacy_runtime_local.ps1"
$LiveQA = Join-Path $Root "scripts\run_live_qa.ps1"
$Source = Join-Path $Root "injection\tools"
$Pinned = Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
$RestoreState = Join-Path $Source "_v105_rose_legacy_local_state.json"
$Expected = [ordered]@{
    "ltk_patcher_host.exe" = "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1"
    "ltk_patcher_dll.dll" = "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74"
}

if ($env:OS -ne "Windows_NT") { throw "This local rollback requires Windows." }
Set-Location -LiteralPath $Root

$CurrentBranch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not inspect the current Git branch." }
if ($CurrentBranch -ne "fix/v1.0.5-rose-local-rollback") {
    throw "Use the isolated fix/v1.0.5-rose-local-rollback branch. The production branch is unchanged."
}
if (-not (Test-Path -LiteralPath $Legacy -PathType Leaf) -or
    -not (Test-Path -LiteralPath $LiveQA -PathType Leaf)) {
    throw "Existing legacy runtime or source test script is unavailable."
}

function Get-PairStatus([string]$Folder) {
    $Match = $true
    foreach ($Name in $Expected.Keys) {
        $Path = Join-Path $Folder $Name
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            Write-Warning "Missing original Rose-style runtime input: $Name"
            $Match = $false
            continue
        }
        $Hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
        $Signature = [string](Get-AuthenticodeSignature -LiteralPath $Path).Status
        if ($Hash -ne $Expected[$Name] -or $Signature -ne "Valid") {
            Write-Warning "$Name is not the reviewed original signed v1.28.1 file."
            $Match = $false
        }
        else {
            Write-Host "MATCH: $Name original signed LTK v1.28.1." -ForegroundColor Green
        }
    }
    return $Match
}

Write-Host "=== PSM v1.0.5 - Rose local-only rollback ===" -ForegroundColor Cyan
Write-Host "Pinned source A/B rollback commit: 79150ea9fafd99f4665d2d196435301b12345205"
Write-Warning "PRIVATE LOCAL SOURCE QA ONLY. Do not distribute upstream-signed LTK binaries."
Write-Warning "This does not replace the Program Files installation or publish v1.0.5."

$SignedAlready = Get-PairStatus $Source
if ($Action -eq "Status") {
    if ($SignedAlready) {
        Write-Host "Original signed LTK pair is already active; no rollback needed." -ForegroundColor Green
        exit 0
    }
    Write-Warning "The active source pair differs. Prepare can activate a backed-up historical pair."
    exit 2
}

# Avoid changing a runtime while it or League gameplay may still be using it.
$Active = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @(
        "PersonalSkinManager", "ltk_patcher_host",
        "League of Legends", "League of Legends (TM) Client"
    )
})
if ($Active.Count -gt 0) {
    throw "Close installed/source PSM, League gameplay, and LTK host before local rollback or QA."
}
if (-not (Get-PairStatus $Pinned)) {
    throw "The isolated official v1.28.1 reference is missing or differs. No files were changed."
}

if ($SignedAlready) {
    Write-Host "Already at the original working signed source runtime; keeping files unchanged." -ForegroundColor Green
}
else {
    if (Test-Path -LiteralPath $RestoreState -PathType Leaf) {
        throw "A prior rollback manifest exists but the active pair differs. Inspect it; never overwrite the recorded backup."
    }
    Write-Host "Activating the reviewed Rose-style local runtime with automatic backup..." -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $Legacy -Action Activate -LeagueGameDir $LeagueGameDir
    if ($LASTEXITCODE -ne 0) {
        throw "Legacy activation refused. Existing files and backup must be inspected."
    }
}
if (-not (Get-PairStatus $Source)) {
    throw "Post-rollback source runtime verification failed; do not start the app."
}

Write-Host "Local Rose-style source runtime ready. No installer build or release performed." -ForegroundColor Green
if ($Action -eq "Run") {
    Write-Host "Starting the live Python source tester (not installed PSM)." -ForegroundColor Cyan
    if ($SkipTests) {
        & powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $LiveQA -SkipTests
    }
    else {
        & powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $LiveQA
    }
    if ($LASTEXITCODE -ne 0) { throw "Source QA exited with a failure." }
}
else {
    Write-Host "When ready, run this script with -Action Run; use Practice Tool for a non-default skin."
}
