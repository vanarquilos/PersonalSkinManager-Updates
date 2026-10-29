# Publish ONLY after installed unsigned-binary candidate passes real gameplay QA.
# Usage: -Publish -ConfirmedCleanInstall -ConfirmedPackagedPracticeTool
#        -ConfirmedPackagedSwiftplay -ConfirmedSecondMatch
param(
    [switch]$Publish,
    [switch]$ConfirmedCleanInstall,
    [switch]$ConfirmedPackagedPracticeTool,
    [switch]$ConfirmedPackagedSwiftplay,
    [switch]$ConfirmedSecondMatch
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (-not ($Publish -and $ConfirmedCleanInstall -and $ConfirmedPackagedPracticeTool -and
           $ConfirmedPackagedSwiftplay -and $ConfirmedSecondMatch)) {
    throw "Require -Publish and all four truthful, explicit INSTALLED-PACKAGE QA confirmations."
}
if ($env:OS -ne "Windows_NT") { throw "Windows required." }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dir = Join-Path $Root "installer\candidates\v1.0.5"
$AuditFile = Join-Path $Dir "release-candidate-audit.json"
$Candidate = Join-Path $Dir "PersonalSkinManager_Setup_v1.0.5-RC.exe"
$PublishedDir = Join-Path $Dir "publish"
$Published = Join-Path $PublishedDir "PersonalSkinManager_Setup.exe"
$NotesFile = Join-Path $Root "releases\v1.0.5\GITHUB_PRERELEASE_NOTES.md"
$NotesOut = Join-Path $Dir "published-release-notes.md"
$LegacyState = Join-Path $Root "injection\tools\_v105_rose_legacy_local_state.json"
$Repository = "vanarquilos/PersonalSkinManager-Updates"
$Tag = "v1.0.5"

foreach ($Cmd in @("git", "gh")) {
    if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) {
        throw "$Cmd is unavailable. Install GitHub CLI and authenticate with gh auth login."
    }
}
# Publishing uses the already-built, SHA-256-checked distribution candidate.
# Leave the maintainer's working source-test runtime untouched.
if (Test-Path -LiteralPath $LegacyState -PathType Leaf) {
    Write-Host "Private LTK v1.28.1 pair remains selected for source use; publishing only the separately verified RC." -ForegroundColor Cyan
}
foreach ($Path in @($AuditFile, $Candidate, $NotesFile)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required release file missing: $Path"
    }
}
Set-Location -LiteralPath $Root
$Branch = (& git branch --show-current).Trim()
if ($Branch -ne "fix/v1.0.5-pre-release-hardening") { throw "Wrong release branch." }
$Head = (& git rev-parse HEAD).Trim()
$Dirty = @(& git status --porcelain --untracked-files=no)
if ($Dirty.Count -gt 0) { throw "Tracked Git changes must be committed." }

$Audit = Get-Content -LiteralPath $AuditFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Audit.version -ne "1.0.5" -or
    $Audit.channel -ne "RELEASE CANDIDATE - NOT PUBLISHED" -or
    $Audit.source_commit -ne $Head -or
    $Audit.official_vendor_signatures_removed -ne $true) {
    throw "Release candidate provenance mismatch. Rebuild and retest the candidate."
}
# Hard stop for the exact known-bad unsigned LTK pair: this installed
# candidate produced SetWindowsHookEx failed during the 2026-10-29 game test.
# CLI confirmation flags cannot override a known failed runtime fingerprint.
$KnownBadHost = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
$KnownBadDll = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
if ([string]$Audit.unsigned_bundled_sha256."ltk_patcher_host.exe" -eq $KnownBadHost -and
    [string]$Audit.unsigned_bundled_sha256."ltk_patcher_dll.dll" -eq $KnownBadDll) {
    throw "Known failing unsigned LTK pair (SetWindowsHookEx). v1.0.5 cannot be published with this installer. Preserve the working tester and obtain a compatible distributable runtime."
}
$Hash = (Get-FileHash -LiteralPath $Candidate -Algorithm SHA256).Hash
$Size = (Get-Item -LiteralPath $Candidate).Length
if ($Hash -ne [string]$Audit.sha256 -or $Size -ne [int64]$Audit.size_bytes) {
    throw "Installer hash or byte size differs from the reviewed candidate."
}
& gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw "GitHub CLI authentication failed." }
& gh release view $Tag --repo $Repository *> $null
if ($LASTEXITCODE -eq 0) { throw "The v1.0.5 release already exists; refusing to overwrite." }

New-Item -ItemType Directory -Path $PublishedDir -Force | Out-Null
Copy-Item -LiteralPath $Candidate -Destination $Published -Force
if ((Get-FileHash -LiteralPath $Published -Algorithm SHA256).Hash -ne $Hash) {
    throw "Published-asset copy SHA-256 mismatch."
}

$Notes = Get-Content -LiteralPath $NotesFile -Raw -Encoding UTF8
$Notes += [Environment]::NewLine + "Installer SHA-256: " + $Hash
$Notes += [Environment]::NewLine + "Installer size (bytes): " + $Size
$Notes += [Environment]::NewLine + "Source commit: " + $Head
$Notes | Set-Content -LiteralPath $NotesOut -Encoding UTF8

Write-Host "Publishing PRE-RELEASE $Tag from source $Head" -ForegroundColor Cyan
Write-Host "Installer SHA-256: $Hash"
& gh release create $Tag $Published --repo $Repository --target $Head --prerelease --title "Personal Skin Manager v1.0.5 (Pre-release)" --notes-file $NotesOut
if ($LASTEXITCODE -ne 0) {
    throw "GitHub release creation failed. Stable update manifest was NOT changed."
}
Write-Host "GitHub v1.0.5 pre-release published. Stable update manifest is unchanged." -ForegroundColor Green
