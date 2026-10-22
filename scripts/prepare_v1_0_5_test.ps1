# Builds a LOCAL ONLY v1.0.5 test installer; never publishes a GitHub release.
# Example: powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\prepare_v1_0_5_test.ps1
# Alternative League path: -LeagueGameDir "D:\Riot Games\League of Legends\Game"
param([string]$LeagueGameDir = "C:\Riot Games\League of Legends\Game")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Check-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed (exit code $LASTEXITCODE). No test installer approved."
    }
}

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Root
$ExpectedBranch = "fix/v1.0.5-pre-release-hardening"
$Installer = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
$OutDir = Join-Path $Root "installer\candidates\v1.0.5"
$TestInstaller = Join-Path $OutDir "PersonalSkinManager_Setup_v1.0.5-TEST.exe"
$ReportDir = Join-Path $OutDir "reports"

if ($env:OS -ne "Windows_NT") { throw "Requires Windows." }
foreach ($Cmd in @("git", "python")) {
    if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) { throw "$Cmd missing from PATH." }
}
if (-not (Test-Path -LiteralPath $LeagueGameDir -PathType Container)) {
    throw "League Game directory not found. Supply -LeagueGameDir with the correct directory: $LeagueGameDir"
}

$Branch = (& git branch --show-current).Trim()
Check-Exit "git branch"
if ($Branch -ne $ExpectedBranch) { throw "Switch to $ExpectedBranch first (currently: $Branch)." }
$Changes = & git status --porcelain --untracked-files=no
Check-Exit "git status"
if ($Changes) { throw "Tracked local source changes exist; commit or stash them first." }
$Head = (& git rev-parse HEAD).Trim()
Check-Exit "git commit lookup"

$Config = Get-Content -LiteralPath (Join-Path $Root "config.py") -Raw
$Iss = Get-Content -LiteralPath (Join-Path $Root "installer.iss") -Raw -Encoding UTF8
if ($Config -notmatch 'APP_VERSION\s*=\s*"1\.0\.5"' -or
    $Iss -notmatch '#define MyAppVersion "1\.0\.5"' -or
    $Iss -notmatch '#define MyAppVersionInfo "1\.0\.5\.0"') {
    throw "v1.0.5 app/installer versions do not match."
}

New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
Write-Host "PSM v1.0.5 LOCAL TEST BUILD (nothing will be published)" -ForegroundColor Cyan
Write-Host "Source commit: $Head"

$Tests = @(
    "tests.test_release_packaging",
    "tests.test_release_skin_routing",
    "tests.test_psm_ui_polish_release",
    "tests.test_patch_2619_wad_headers",
    "tests.test_ltk_host_protocol",
    "tests.test_ltk_countdown_prearm",
    "tests.test_overlay_cleanup",
    "tests.test_patcher_eol",
    "tests.test_swiftplay_runtime",
    "tests.test_lcu_put_reconnect",
    "tests.test_game_monitor_vanishing_process",
    "tests.test_runtime_failure_reporting"
)

Write-Host "1/4: Source regression tests" -ForegroundColor Cyan
& python -m unittest @Tests
Check-Exit "Source regression tests"

Write-Host "2/4: Audit trusted local runtime" -ForegroundColor Cyan
$Audit = Join-Path $ReportDir "runtime-audit.json"
& python (Join-Path $Root "scripts\audit_runtime_v105.py") --game-dir $LeagueGameDir |
    Out-File -LiteralPath $Audit -Encoding utf8
Check-Exit "Runtime inspection"

# Archive previous local installer and remove its former output path so
# a failed build cannot mistake v1.0.4 for the new installer.
if (Test-Path -LiteralPath $Installer -PathType Leaf) {
    $OldHash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash
    $BackupDir = Join-Path $Root "installer\backup"
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    $Backup = Join-Path $BackupDir "PersonalSkinManager_previous_$OldHash.exe"
    if (-not (Test-Path -LiteralPath $Backup -PathType Leaf)) {
        Copy-Item -LiteralPath $Installer -Destination $Backup -Force
    }
    Remove-Item -LiteralPath $Installer -Force
}

Write-Host "3/4: Build new installer" -ForegroundColor Cyan
$Started = Get-Date
& python (Join-Path $Root "scripts\build_all.py")
Check-Exit "Windows installer build"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
    throw "New installer output not found."
}
$Built = Get-Item -LiteralPath $Installer
if ($Built.LastWriteTime -lt $Started.AddSeconds(-3) -or $Built.Length -lt 1000000) {
    throw "Installer appears stale or unexpectedly small."
}
$Hash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToUpperInvariant()
$Size = [int64]$Built.Length
Copy-Item -LiteralPath $Installer -Destination $TestInstaller -Force
if ((Get-FileHash -LiteralPath $TestInstaller -Algorithm SHA256).Hash.ToUpperInvariant() -ne $Hash) {
    throw "Copied candidate checksum mismatch."
}

Write-Host "4/4: Candidate provenance" -ForegroundColor Cyan
$Manifest = [ordered]@{
    app = "Personal Skin Manager"
    version = "1.0.5"
    channel = "LOCAL TEST ONLY - NOT PUBLISHED"
    source_commit = $Head
    built_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    league_game_directory = $LeagueGameDir
    installer_name = (Split-Path -Leaf $TestInstaller)
    installer_size_bytes = $Size
    installer_sha256 = $Hash
    runtime_audit = "reports/runtime-audit.json"
    practice_tool_test = "NOT YET VERIFIED"
    swiftplay_gameplay_test = "NOT YET VERIFIED"
}
$Manifest | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $OutDir "candidate-manifest.json") -Encoding UTF8

Write-Host ""
Write-Host "LOCAL TEST INSTALLER READY" -ForegroundColor Green
Write-Host $TestInstaller
Write-Host "Size: $Size bytes"
Write-Host "SHA-256: $Hash"
Write-Host "No GitHub release, tag or signed update manifest was changed."
