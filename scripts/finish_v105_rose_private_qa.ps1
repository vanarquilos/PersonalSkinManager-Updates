# PSM v1.0.5 private Rose-style QA completion.
# No local rollback checkout switch/reset; no LTK Manager download or install.
param(
    [string]$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates",
    [string]$Qa = "C:\Users\Van Arquilos\Desktop\PSM-v105-Rose-Rebuild-20261031-132306"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
function Check([string]$Name) {
    if ($LASTEXITCODE -ne 0) { throw "$Name failed (exit $LASTEXITCODE)" }
}
function Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
$Ref = "rebuild/v1.0.5-rose-compatible"
if ($env:OS -ne "Windows_NT") { throw "Windows-only QA" }
if (-not (Test-Path -LiteralPath $Original -PathType Container) -or -not (Test-Path -LiteralPath $Qa -PathType Container)) {
    throw "Original checkout or private QA folder not found."
}
$Original = (Resolve-Path -LiteralPath $Original).Path
$Qa = (Resolve-Path -LiteralPath $Qa).Path
$OriginalBranch = (& git -C $Original branch --show-current).Trim()
Check "Original checkout branch"
$QaBranch = (& git -C $Qa branch --show-current).Trim()
Check "QA checkout branch"
if (-not $QaBranch.StartsWith("qa/v105-rose-") -or
    $Qa.Equals($Original, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to modify an unexpected or original checkout."
}
$Dirty = @(& git -C $Qa status --porcelain --untracked-files=no)
Check "QA tracked status"
if ($Dirty.Count -gt 0) { throw "Tracked QA changes detected. Refusing merge." }
$SourceMod = Join-Path $Original "injection\tools\mod-tools.exe"
$StagedMod = Join-Path $Qa "injection\tools\mod-tools.exe"
$StubDir = Join-Path $Qa "installer\candidates\v1.0.5\psm-inert-stub"
$Report = Join-Path $Qa "installer\candidates\v1.0.5\rose-style-frozen-private-qa.json"
$Exe = Join-Path $Qa "dist\PersonalSkinManager\PersonalSkinManager.exe"
$ModPin = "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44"
if (-not (Test-Path -LiteralPath $SourceMod -PathType Leaf) -or (Hash $SourceMod) -ne $ModPin) {
    throw "Original reviewed mod-tools.exe missing or fingerprint mismatch."
}
Write-Host ("Original branch preserved: " + $OriginalBranch) -ForegroundColor Cyan
Write-Host ("Isolated QA branch: " + $QaBranch) -ForegroundColor Cyan
if (Test-Path -LiteralPath $Report -PathType Leaf) {
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Report exists but EXE missing." }
    $Data = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
    if ($Data.public_distribution_approved -ne $false -or
        $Data.gameplay_skin_rendering -ne "NOT_TESTED" -or
        $Data.exe_sha256 -ne (Hash $Exe)) {
        throw "Previously produced QA report inconsistent."
    }
    Write-Host ("Existing verified private EXE: " + $Exe) -ForegroundColor Green
    Write-Warning "No actual skin rendering verified and no public release approved."
    exit 0
}
if (Test-Path -LiteralPath (Join-Path $Qa "dist")) {
    throw "Partial dist exists without QA report: manual review required; no overwrite."
}
if (-not (Test-Path -LiteralPath $StagedMod -PathType Leaf) -or (Hash $StagedMod) -ne $ModPin) {
    throw "Staged mod-tools file missing or modified."
}
if (-not (Test-Path -LiteralPath $StubDir -PathType Container) -or
    @(Get-ChildItem -LiteralPath $StubDir -Force).Count -ne 0) {
    throw "Expected empty failed-stub output directory not found."
}
& git -C $Qa fetch origin ("+refs/heads/" + $Ref + ":refs/remotes/origin/" + $Ref)
Check "Fetch Rose rebuild branch"
& git -C $Qa merge --ff-only ("origin/" + $Ref)
Check "Fast-forward QA worktree"
Push-Location -LiteralPath $Qa
try {
    & python -m unittest -v tests.test_v105_msvc_space_path_contract tests.test_v105_rose_style_build_contract tests.test_v105_rose_rebuild_installer_safety tests.test_v105_rose_rebuild_worktree_contract tests.test_v105_no_false_release_ready
    Check "Source and build contract tests"
}
finally { Pop-Location }
& powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File (Join-Path $Qa "scripts\build_v105_rose_style_frozen_private_qa.ps1") -ModToolsFile $SourceMod -ResumeFailedStubBuild
Check "Private frozen build"
if (-not (Test-Path -LiteralPath $Exe -PathType Leaf) -or
    -not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "Missing private QA completion outputs."
}
$Data = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
if ($Data.public_distribution_approved -ne $false -or
    $Data.gameplay_skin_rendering -ne "NOT_TESTED" -or
    $Data.exe_sha256 -ne (Hash $Exe)) {
    throw "Final private QA manifest failed validation."
}
Write-Host ("PRIVATE EXE BUILT: " + $Exe) -ForegroundColor Green
Write-Host ("SHA-256: " + (Hash $Exe))
Write-Warning "No official LTK pair bundled. Game rendering and public release remain unverified."
