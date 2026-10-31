# Local-only frozen PSM QA with a separately audited CURRENT LTK pair.
# This DOES NOT create an installer, strip signatures, disable checks or publish.
# It also cannot prove runtime/gameplay compatibility; a real match is required.
param(
    [Parameter(Mandatory = $true)][string]$ModToolsFile,
    [Parameter(Mandatory = $true)][string]$LtkDir,
    [Parameter(Mandatory = $true)][string]$QaManifest,
    [Parameter(Mandatory = $true)][string]$CslolDir,
    [string]$GameDir = "C:\Riot Games\League of Legends\Game"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
function Sha([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
function Check([string]$Task) {
    if ($LASTEXITCODE -ne 0) { throw "$Task failed ($LASTEXITCODE)." }
}
if ($env:OS -ne "Windows_NT") { throw "Windows required." }
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath (Join-Path $Root ".git") -PathType Leaf)) {
    throw "Use a NEW linked test worktree; original repo and existing QA outputs are protected."
}
Set-Location -LiteralPath $Root
$Branch = (& git branch --show-current).Trim()
Check "Git branch"
if (-not $Branch.StartsWith("qa/v105-current-ltk-")) {
    throw "Branch must start with qa/v105-current-ltk-."
}
$Dirty = @(& git status --porcelain --untracked-files=no)
Check "Git status"
if ($Dirty.Count -gt 0) { throw "Tracked files changed; abort." }
$Commit = (& git rev-parse HEAD).Trim()
Check "Git commit"
$Dir = (Resolve-Path -LiteralPath $LtkDir).Path
$ManifestPath = (Resolve-Path -LiteralPath $QaManifest).Path
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($Manifest.schema -ne 1 -or
    $Manifest.purpose -ne "PSM_V105_PRIVATE_QA_ONLY" -or
    $Manifest.runtime_origin -ne "official-bundled" -or
    $Manifest.host_protocol -ne 3 -or
    $Manifest.public_distribution_approved -ne $false) {
    throw "Current LTK QA manifest gate failed."
}
$Pair = @{
    "ltk_patcher_host.exe" = [string]$Manifest.files_sha256.'ltk_patcher_host.exe'
    "ltk_patcher_dll.dll" = [string]$Manifest.files_sha256.'ltk_patcher_dll.dll'
}
foreach ($Name in $Pair.Keys) {
    if ($Pair[$Name] -notmatch '^[A-Fa-f0-9]{64}$') { throw "Bad manifest SHA-256 for $Name" }
    $File = Join-Path $Dir $Name
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { throw "Missing $Name" }
    if ((Sha $File) -ne $Pair[$Name].ToUpperInvariant()) { throw "LTK fingerprint mismatch: $Name" }
    $Signature = Get-AuthenticodeSignature -LiteralPath $File
    if ($Signature.Status -ne "Valid" -or $null -eq $Signature.SignerCertificate) {
        throw "Only verified signed upstream binaries are accepted for this PRIVATE integration QA."
    }
}
# A manifest with exact SHA-256 and valid Authenticode still cannot
# authorize an already-expired patcher for this League executable.
& python (Join-Path $Root "scripts\verify_v105_game_ltk_cutoff.py") `
    --game-dir $GameDir --ltk-dir $Dir
Check "League-vs-LTK cutoff preflight"
$OldBadHost = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
$OldBadDll = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
if ($Pair["ltk_patcher_host.exe"] -eq $OldBadHost -and
    $Pair["ltk_patcher_dll.dll"] -eq $OldBadDll) {
    throw "The previously failing v1.28.1 pair is not a current runtime candidate."
}
$Files = [ordered]@{
    "mod-tools.exe" = $ModToolsFile
    "cslol-dll.dll" = Join-Path $CslolDir "cslol-dll.dll"
    "ltk_patcher_host.exe" = Join-Path $Dir "ltk_patcher_host.exe"
    "ltk_patcher_dll.dll" = Join-Path $Dir "ltk_patcher_dll.dll"
}
$Hashes = [ordered]@{}
foreach ($Name in $Files.Keys) {
    if (-not (Test-Path -LiteralPath $Files[$Name] -PathType Leaf)) { throw "Missing $Name" }
    $Hashes[$Name] = Sha $Files[$Name]
}
$ExpectedModTools = "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44"
$LocalOnlyCslol = "4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90"
if ($Hashes["mod-tools.exe"] -ne $ExpectedModTools -or
    $Hashes["cslol-dll.dll"] -ne $LocalOnlyCslol) {
    throw "Unknown mod-tools or private-only CSLOL input; no frozen package built."
}
$Tools = Join-Path $Root "injection\tools"
$Dist = Join-Path $Root "dist\PersonalSkinManager"
$App = Join-Path $Dist "PersonalSkinManager.exe"
$Report = Join-Path $Root "installer\candidates\v1.0.5\current-ltk-frozen-private-qa.json"
$Public = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
$Dest = Join-Path $Tools "mod-tools.exe"
foreach ($Path in @($Dist, $App, $Report, $Public, $Dest)) {
    if (Test-Path -LiteralPath $Path) { throw "Existing build output found. Use a new linked QA worktree." }
}
$Busy = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends",
        "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Busy.Count -gt 0) { throw "Close all PSM, League gameplay and LTK host processes." }
& python -m unittest tests.test_v105_current_ltk_private_manifest tests.test_v105_current_ltk_build_contract tests.test_release_packaging tests.test_ltk_qa_runtime_selector tests.test_ltk_host_protocol
Check "Private QA runtime integration regression tests"
New-Item -ItemType Directory -Path $Tools -Force | Out-Null
Copy-Item -LiteralPath $ModToolsFile -Destination $Dest
if ((Sha $Dest) -ne $ExpectedModTools) { throw "Staged mod-tools hash mismatch" }
$OldLtk = [Environment]::GetEnvironmentVariable("PSM_RELEASE_LTK_DIR", "Process")
$OldCslol = [Environment]::GetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", "Process")
try {
    $env:PSM_RELEASE_LTK_DIR = $Dir
    $env:PSM_RELEASE_CSLOL_DIR = (Resolve-Path -LiteralPath $CslolDir).Path
    & python (Join-Path $Root "scripts\build_pyinstaller.py")
    Check "Frozen PyInstaller build"
}
finally {
    [Environment]::SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $OldLtk, "Process")
    [Environment]::SetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", $OldCslol, "Process")
}
if (-not (Test-Path -LiteralPath $App -PathType Leaf)) { throw "Frozen executable missing." }
foreach ($Name in $Files.Keys) {
    $Matches = @(Get-ChildItem -LiteralPath $Dist -Recurse -File -Filter $Name)
    if ($Matches.Count -ne 1 -or (Sha $Matches[0].FullName) -ne $Hashes[$Name]) {
        throw "Unexpected frozen runtime component: $Name"
    }
}
if (Test-Path -LiteralPath $Public) { throw "Unexpected installer; stop." }
$Parent = Split-Path -Path $Report -Parent
if (-not (Test-Path -LiteralPath $Parent)) { New-Item -ItemType Directory -Path $Parent -Force | Out-Null }
$Record = [ordered]@{
    version = "1.0.5"
    channel = "CURRENT LTK PRIVATE FROZEN QA ONLY"
    source_commit = $Commit
    source_manager_release_metadata = $Manifest.source_manager_release
    host_protocol = $Manifest.host_protocol
    actual_patcher_build_version = "UNVERIFIED"
    runtime_components_sha256 = $Hashes
    frozen_exe_sha256 = Sha $App
    private_qa_skin_rendering = "NOT TESTED"
    contains_upstream_signed_runtime = $true
    contains_third_party_signed_cslol = $true
    public_distribution_approved = $false
}
$Record | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $Report -Encoding UTF8
Write-Host "CURRENT LTK FROZEN PRIVATE QA BUILD COMPLETE" -ForegroundColor Green
Write-Host ("EXE SHA-256: " + $Record.frozen_exe_sha256)
Write-Warning "Not a public installer. No gameplay/compatibility or legal redistribution approval; do NOT upload the frozen folder."
