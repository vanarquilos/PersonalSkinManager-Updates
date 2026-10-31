# PSM v1.0.5 local-only FROZEN APP parity QA. Not a redistributable installer.
# Never launches League, copies into Program Files, signs DLLs or publishes.
# Builds ONLY in a linked test worktree, leaving the original app untouched.
param(
    [Parameter(Mandatory = $true)][string]$ModToolsFile,
    [Parameter(Mandatory = $true)][string]$UnsignedLtkDir,
    [Parameter(Mandatory = $true)][string]$CslolDir,
    [string]$GameDir = "C:\Riot Games\League of Legends\Game"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
function Check-Exit([string]$Label) {
    if ($LASTEXITCODE -ne 0) { throw "$Label failed ($LASTEXITCODE)." }
}
function SHA256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
if ($env:OS -ne "Windows_NT") { throw "Windows host required." }
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath (Join-Path $Root ".git") -PathType Leaf)) {
    throw "Safety stop: use only the separate LINKED GIT WORKTREE. Do not run in the original repo."
}
Set-Location -LiteralPath $Root
$Branch = (& git branch --show-current).Trim()
Check-Exit "Git branch"
if ($Branch -ne "release/v105-public-installer-staging" -and
    -not $Branch.StartsWith("qa/v105-frozen-dllsearch-")) {
    throw "Run from release staging or a qa/v105-frozen-dllsearch-* linked worktree, not $Branch"
}
$Dirty = @(& git status --porcelain --untracked-files=no)
Check-Exit "Git status"
if ($Dirty.Count -gt 0) { throw "Tracked working files changed; aborting." }
$Head = (& git rev-parse HEAD).Trim()
Check-Exit "Git HEAD"
$Expected = [ordered]@{
    "mod-tools.exe" = "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44"
    "cslol-dll.dll" = "4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90"
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$Inputs = [ordered]@{
    "mod-tools.exe" = $ModToolsFile
    "cslol-dll.dll" = (Join-Path $CslolDir "cslol-dll.dll")
    "ltk_patcher_host.exe" = (Join-Path $UnsignedLtkDir "ltk_patcher_host.exe")
    "ltk_patcher_dll.dll" = (Join-Path $UnsignedLtkDir "ltk_patcher_dll.dll")
}
$Tools = Join-Path $Root "injection\tools"
$Dist = Join-Path $Root "dist\PersonalSkinManager"
$App = Join-Path $Dist "PersonalSkinManager.exe"
$RecordDir = Join-Path $Root "installer\candidates\v1.0.5"
$RecordPath = Join-Path $RecordDir "frozen-parity-private-qa.json"
$PublicInstaller = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
foreach ($Path in @($Dist, $RecordPath, $PublicInstaller)) {
    if (Test-Path -LiteralPath $Path) {
        throw "Nonempty or existing build output present: $Path. Use a fresh linked test worktree."
    }
}
$LocalModtools = Join-Path $Tools "mod-tools.exe"
if (Test-Path -LiteralPath $LocalModtools) {
    throw "Local mod-tools.exe exists in this worktree; refusing to overwrite."
}
foreach ($Name in $Inputs.Keys) {
    if (-not (Test-Path -LiteralPath $Inputs[$Name] -PathType Leaf)) {
        throw "Required local QA file missing: $Name"
    }
    $Hash = SHA256 $Inputs[$Name]
    if ($Hash -ne $Expected[$Name]) {
        throw "Local QA input fingerprint mismatch for $Name. No files changed."
    }
}
# Fail before writing anything: this historical unsigned candidate has an
# old DLL cutoff and must not be rebuilt as a current League gameplay test.
& python (Join-Path $Root "scripts\verify_v105_game_ltk_cutoff.py") `
    --game-dir $GameDir --ltk-dir $UnsignedLtkDir
Check-Exit "League-vs-LTK cutoff preflight"
$Running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends",
        "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Running.Count -gt 0) { throw "Close PSM, League gameplay and LTK host before freezing." }
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 or newer is required."
}
Write-Host "1/4 - Validate source packaging contracts" -ForegroundColor Cyan
& python -m unittest tests.test_v105_frozen_parity_private_qa_contract tests.test_v105_frozen_external_dll_search tests.test_release_packaging tests.test_ltk_qa_runtime_selector
Check-Exit "Focused regression tests"
Write-Host "2/4 - Stage mod-tools only in this isolated worktree" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $Tools -Force | Out-Null
Copy-Item -LiteralPath $ModToolsFile -Destination $LocalModtools
if ((SHA256 $LocalModtools) -ne $Expected["mod-tools.exe"]) {
    throw "Staged mod-tools SHA-256 verification failed."
}
$OldLtk = [Environment]::GetEnvironmentVariable("PSM_RELEASE_LTK_DIR")
$OldCslol = [Environment]::GetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR")
Write-Host "3/4 - PyInstaller FROZEN BUILD ONLY; do not create installer" -ForegroundColor Cyan
try {
    $env:PSM_RELEASE_LTK_DIR = (Resolve-Path -LiteralPath $UnsignedLtkDir).Path
    $env:PSM_RELEASE_CSLOL_DIR = (Resolve-Path -LiteralPath $CslolDir).Path
    & python (Join-Path $Root "scripts\build_pyinstaller.py")
    Check-Exit "PyInstaller frozen build"
} finally {
    [Environment]::SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $OldLtk)
    [Environment]::SetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", $OldCslol)
}
if (-not (Test-Path -LiteralPath $App -PathType Leaf)) {
    throw "Frozen application executable missing. No installer is approved."
}
Write-Host "4/4 - Validate exact frozen runtime identities" -ForegroundColor Cyan
$Packaged = [ordered]@{}
foreach ($Name in $Expected.Keys) {
    $Matches = @(Get-ChildItem -LiteralPath $Dist -File -Recurse -Filter $Name)
    if ($Matches.Count -ne 1) {
        throw "Expected exactly one packaged $Name but found $($Matches.Count)."
    }
    $File = $Matches[0]
    $Hash = SHA256 $File.FullName
    if ($Hash -ne $Expected[$Name]) {
        throw "Frozen $Name SHA-256 does not match reviewed local QA source."
    }
    $Packaged[$Name] = [ordered]@{
        sha256 = $Hash
        relative_location = $File.FullName.Substring($Dist.Length + 1).Replace("\", "/")
        bytes = [long]$File.Length
    }
}
if (Test-Path -LiteralPath $PublicInstaller) {
    throw "Unexpected public installer produced; stop and inspect manually."
}
New-Item -ItemType Directory -Path $RecordDir -Force | Out-Null
$Report = [ordered]@{
    version = "1.0.5"
    purpose = "LOCAL PRIVATE FROZEN PARITY TEST ONLY"
    source_commit = $Head
    unsigned_source_skin_rendering = "UNVERIFIED_ON_CURRENT_LEAGUE"
    frozen_app_visible_skin = "NOT TESTED"
    installed_candidate_visible_skin = "NOT TESTED"
    contains_third_party_signed_cslol = $true
    public_redistribution_approved = $false
    exe_sha256 = SHA256 $App
    files = $Packaged
}
$Report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $RecordPath -Encoding UTF8
Write-Host "LOCAL-ONLY frozen PSM application verified: $App" -ForegroundColor Green
Write-Host ("Frozen EXE SHA-256: " + $Report.exe_sha256)
Write-Host "All four components present with exact expected SHA-256 values."
Write-Warning "Do NOT upload/share this frozen folder: it contains third-party-signed CSLOL and is NOT approved for public redistribution."
Write-Warning "Not installed and not launched automatically. Keep the working PSM installation untouched."
Write-Host "Record a permitted visible-skin outcome only after testing the frozen app separately."
