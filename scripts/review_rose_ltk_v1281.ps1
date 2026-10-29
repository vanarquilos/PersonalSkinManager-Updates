# PSM v1.0.5 - Rose community legacy runtime research, isolated review ONLY.
# This does not install, run, stage or replace the active patcher host/DLL.
# Usage: powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\review_rose_ltk_v1281.ps1
param(
    [string]$LeagueGameDir = "C:\Riot Games\League of Legends\Game"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CandidateDir = Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
$PinnedCommit = "9f06802de5d83d6dde3ff1644a1c56049fadf9bb"
$Files = @(
    @{ Name = "ltk_patcher_host.exe"; Size = 1238272; Blob = "b2fc81c6de7bf5b40b81daaf8987706308ed5b33" },
    @{ Name = "ltk_patcher_dll.dll"; Size = 764160; Blob = "0cd0f58530906c3792e3189ea8af1a8f8bc6f264" }
)

if ($env:OS -ne "Windows_NT") {
    throw "This review script requires Windows."
}
foreach ($Command in @("git", "python")) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "$Command is not available on PATH."
    }
}
if (-not (Test-Path -LiteralPath $LeagueGameDir -PathType Container)) {
    throw "League game directory not found: $LeagueGameDir. Use -LeagueGameDir."
}
if (Test-Path -LiteralPath (Join-Path $CandidateDir "ltk_patcher_host.exe") -PathType Container) {
    throw "Unexpected directory at host file path."
}

New-Item -ItemType Directory -Path $CandidateDir -Force | Out-Null
Write-Host "Rose legacy v1.28.1 review - ISOLATED FILES ONLY" -ForegroundColor Cyan
Write-Host "Official upstream commit: $PinnedCommit"
Write-Host "No active PSM binaries will be changed or executed." -ForegroundColor Yellow

foreach ($Item in $Files) {
    $Target = Join-Path $CandidateDir $Item.Name
    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) {
        $Url = "https://raw.githubusercontent.com/LeagueToolkit/ltk-manager/$PinnedCommit/src-tauri/resources/$($Item.Name)"
        $Temp = $Target + ".download"
        try {
            Invoke-WebRequest -Uri $Url -OutFile $Temp -UseBasicParsing -ErrorAction Stop
            if ((Get-Item -LiteralPath $Temp).Length -ne [int64]$Item.Size) {
                throw "Unexpected download size for $($Item.Name)"
            }
            $Hash = (& git hash-object -- $Temp)
            if ($LASTEXITCODE -ne 0 -or $Hash.Trim().ToLowerInvariant() -ne $Item.Blob) {
                throw "Pinned upstream Git object mismatch for $($Item.Name)"
            }
            Move-Item -LiteralPath $Temp -Destination $Target -Force
        }
        finally {
            if (Test-Path -LiteralPath $Temp -PathType Leaf) {
                Remove-Item -LiteralPath $Temp -Force -ErrorAction SilentlyContinue
            }
        }
    }
    $FinalHash = (& git hash-object -- $Target)
    if ($LASTEXITCODE -ne 0 -or $FinalHash.Trim().ToLowerInvariant() -ne $Item.Blob) {
        throw "Candidate file differs from upstream tag: $($Item.Name)"
    }
    Write-Host "Verified official $($Item.Name)"
}

Write-Host "Running read-only build compatibility check..." -ForegroundColor Cyan
& python (Join-Path $Root "scripts\audit_ltk_v1281_compatibility.py") --candidate-dir $CandidateDir --game-dir $LeagueGameDir
if ($LASTEXITCODE -ne 0) {
    throw "The historical runtime failed the identity or game-build audit. No runtime was activated."
}
Write-Warning "Audit passed only for file identity and PE build cutoff. This is NOT a supported third-party host integration or proof of skin rendering."
Write-Host "Legacy binaries remain isolated: $CandidateDir"
