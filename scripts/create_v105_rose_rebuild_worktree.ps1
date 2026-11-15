# PSM v1.0.5 Rose-style rebuild bootstrap.
# Creates NEW isolated linked worktree; never checkout, reset, restore
# or change the user's current rollback branch.
param(
    [string]$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates",
    [switch]$PrepareOnly
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
function CheckExit([string]$Stage) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Stage failed (exit $LASTEXITCODE). Existing source checkout was not changed."
    }
}
if ($env:OS -ne "Windows_NT") { throw "Windows required." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git not found." }
if (-not (Test-Path -LiteralPath $Original -PathType Container)) {
    throw "Original PSM checkout not found: $Original"
}
$Original = (Resolve-Path -LiteralPath $Original).Path
$Current = (& git -C $Original branch --show-current).Trim()
CheckExit "Read original checkout branch"
Write-Host ("Preserving original branch: " + $Current) -ForegroundColor Cyan
$TargetRef = "rebuild/v1.0.5-rose-compatible"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$QaBranch = "qa/v105-rose-$Stamp"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Qa = Join-Path $Desktop "PSM-v105-Rose-Rebuild-$Stamp"
if (Test-Path -LiteralPath $Qa) {
    throw "Refusing to reuse an existing QA directory: $Qa"
}
# Git fetch updates Git metadata only; no checkout of existing source files.
& git -C $Original fetch origin ("+refs/heads/" + $TargetRef + ":refs/remotes/origin/" + $TargetRef)
CheckExit "Fetch Rose-style PSM rebuild branch"
& git -C $Original worktree add -b $QaBranch $Qa ("origin/" + $TargetRef)
CheckExit "Create isolated QA worktree"
$CreatedBranch = (& git -C $Qa branch --show-current).Trim()
CheckExit "Confirm QA branch"
if ($CreatedBranch -ne $QaBranch) { throw "Unexpected QA branch after creation." }
Write-Host ("QA worktree created: " + $Qa) -ForegroundColor Green
Write-Host ("Original branch remains: " + $Current) -ForegroundColor Green
if ($PrepareOnly) {
    Write-Host "Private build skipped. No installer, binaries or user data modified."
    exit 0
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ required. QA worktree remains at $Qa."
}
$ModTools = Join-Path $Original "injection\tools\mod-tools.exe"
if (-not (Test-Path -LiteralPath $ModTools -PathType Leaf)) {
    throw "Original reviewed mod-tools.exe not found. QA worktree remains at $Qa."
}
# Inert PSM-owned CSLOL stub, no bundled LTK; private QA only.
& powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File (Join-Path $Qa "scripts\build_v105_rose_style_frozen_private_qa.ps1") -ModToolsFile $ModTools
CheckExit "Rose-style v1.0.5 PRIVATE QA frozen build"
Write-Host ("Private PSM EXE: " + (Join-Path $Qa "dist\PersonalSkinManager\PersonalSkinManager.exe")) -ForegroundColor Green
Write-Warning "NOT a release. This build does NOT bundle LTK; game rendering is unverified."
Write-Host "No checkout change, software installation, or publication was performed."
