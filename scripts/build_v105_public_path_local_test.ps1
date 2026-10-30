# PSM v1.0.5 - local-only public-path installer QA builder.
# Must run in a separate linked Git worktree. Never publishes or changes the
# maintainer's working private build, and never signs or edits vendor binaries.
param(
    [Parameter(Mandatory = $true)][string]$ModToolsFile,
    [Parameter(Mandatory = $true)][string]$LtkDir,
    [Parameter(Mandatory = $true)][string]$CslolDir
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Check-Exit([string]$Task) {
    if ($LASTEXITCODE -ne 0) { throw "$Task failed ($LASTEXITCODE); no installer approved." }
}
function File-Sha([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$GitMarker = Join-Path $Root ".git"
# A linked worktree has a .git FILE. Ordinary clones have a .git DIRECTORY.
if (-not (Test-Path -LiteralPath $GitMarker -PathType Leaf)) {
    throw "Safety stop: run only from a fresh LINKED GIT WORKTREE; do not run against the original working repository."
}
if ($env:OS -ne "Windows_NT") { throw "Windows build host required." }
$ExpectedBranch = "release/v105-public-installer-staging"
Set-Location -LiteralPath $Root
$Branch = (& git branch --show-current).Trim()
Check-Exit "Git branch lookup"
if ($Branch -ne $ExpectedBranch) { throw "Wrong branch: $Branch" }
$Dirty = @(& git status --porcelain --untracked-files=no)
Check-Exit "Git status"
if ($Dirty.Count -ne 0) { throw "Tracked source files modified. Preserve them before building." }
$Head = (& git rev-parse HEAD).Trim()
Check-Exit "Git commit lookup"
$Dest = Join-Path $Root "injection\tools"
$InnoResult = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
$Dist = Join-Path $Root "dist\PersonalSkinManager"
$OutDir = Join-Path $Root "installer\candidates\v1.0.5"
$Candidate = Join-Path $OutDir "PersonalSkinManager_v1.0.5_PUBLIC-PATH-LOCAL-TEST.exe"
$Manifest = Join-Path $OutDir "public-path-local-test-manifest.json"
$LTKNames = @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")
$KnownBad = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$Inputs = [ordered]@{
    "mod-tools.exe" = $ModToolsFile
    "cslol-dll.dll" = (Join-Path $CslolDir "cslol-dll.dll")
    "ltk_patcher_host.exe" = (Join-Path $LtkDir "ltk_patcher_host.exe")
    "ltk_patcher_dll.dll" = (Join-Path $LtkDir "ltk_patcher_dll.dll")
}
foreach ($Path in @($InnoResult, $Candidate, $Manifest, $Dist)) {
    if (Test-Path -LiteralPath $Path) { throw "Refusing to replace existing build output; use a fresh worktree." }
}
foreach ($Name in $Inputs.Keys) {
    if (-not (Test-Path -LiteralPath $Inputs[$Name] -PathType Leaf)) {
        throw "Missing approved input: $Name. No files were changed."
    }
}
$CSLOL = Get-AuthenticodeSignature -LiteralPath $Inputs["cslol-dll.dll"]
if ($CSLOL.Status -ne "Valid" -or $null -eq $CSLOL.SignerCertificate -or
    $null -eq $CSLOL.TimeStamperCertificate) {
    throw "CSLOL requires a distributor-owned publicly trusted signature and timestamp. Do not package the unsigned or original vendor DLL."
}
if ($CSLOL.SignerCertificate.Subject -match "(?i)league\s*toolkit") {
    throw "Original upstream CSLOL signature cannot be republished in this third-party installer."
}
$Hashes = [ordered]@{}
foreach ($Name in $Inputs.Keys) { $Hashes[$Name] = File-Sha $Inputs[$Name] }
if ($Hashes["ltk_patcher_host.exe"] -eq $KnownBad["ltk_patcher_host.exe"] -and
    $Hashes["ltk_patcher_dll.dll"] -eq $KnownBad["ltk_patcher_dll.dll"]) {
    throw "Known failing unsigned LTK pair: SetWindowsHookEx failed. Do not rebuild identical binaries."
}
foreach ($Name in $LTKNames) {
    $Sig = Get-AuthenticodeSignature -LiteralPath $Inputs[$Name]
    if ($Sig.Status -notin @("NotSigned", "Valid")) {
        throw "LTK patcher file has an invalid Authenticode status: $Name"
    }
    if ($null -ne $Sig.SignerCertificate -and
        $Sig.SignerCertificate.Subject -match "(?i)league\s*toolkit") {
        throw "LTK original vendor signature still present on $Name; written permission is required to redistribute it."
    }
}
$Running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends",
        "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Running.Count -gt 0) { throw "Close PSM, game and LTK host for a reproducible build." }
foreach ($Cmd in @("python", "git")) {
    if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) { throw "$Cmd not found." }
}
# Tests precede any local build-file changes.
& python -m unittest tests.test_v105_public_installer_staging_contract tests.test_release_packaging tests.test_v105_distribution_contract
Check-Exit "Source packaging regression tests"

# This worktree is intentionally disposable; its own injection/tools is the
# only destination modified here. Never touch original source runtime paths.
New-Item -ItemType Directory -Path $Dest -Force | Out-Null
$LocalModTools = Join-Path $Dest "mod-tools.exe"
if (Test-Path -LiteralPath $LocalModTools -PathType Leaf) {
    throw "Refusing to overwrite mod-tools.exe in this worktree."
}
Copy-Item -LiteralPath $ModToolsFile -Destination $LocalModTools
if ((File-Sha $LocalModTools) -ne $Hashes["mod-tools.exe"]) {
    throw "Local mod-tools copy differs from audited input."
}
$PriorLTK = [Environment]::GetEnvironmentVariable("PSM_RELEASE_LTK_DIR")
$PriorCSLOL = [Environment]::GetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR")
try {
    $env:PSM_RELEASE_LTK_DIR = (Resolve-Path -LiteralPath $LtkDir).Path
    $env:PSM_RELEASE_CSLOL_DIR = (Resolve-Path -LiteralPath $CslolDir).Path
    & python (Join-Path $Root "scripts\build_all.py")
    Check-Exit "PyInstaller and Inno Setup build"
} finally {
    [Environment]::SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $PriorLTK)
    [Environment]::SetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", $PriorCSLOL)
}
if (-not (Test-Path -LiteralPath $InnoResult -PathType Leaf)) {
    throw "New Inno installer not found."
}
foreach ($Name in $Inputs.Keys) {
    $Copies = @(Get-ChildItem -LiteralPath $Dist -Recurse -File -Filter $Name)
    if ($Copies.Count -ne 1) { throw "Expected one packaged $Name, found $($Copies.Count)." }
    if ((File-Sha $Copies[0].FullName) -ne $Hashes[$Name]) {
        throw "Packaged $Name differs from audited input."
    }
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
Copy-Item -LiteralPath $InnoResult -Destination $Candidate
if ((File-Sha $Candidate) -ne (File-Sha $InnoResult)) {
    throw "Installer copy digest mismatch."
}
$Record = [ordered]@{
    version = "1.0.5"
    channel = "LOCAL WINDOWS TEST ONLY - NOT PUBLICATION APPROVED"
    source_commit = $Head
    package_filename = (Split-Path -Leaf $Candidate)
    package_sha256 = (File-Sha $Candidate)
    package_size_bytes = (Get-Item -LiteralPath $Candidate).Length
    components_sha256 = $Hashes
    cslol_publisher_subject = [string]$CSLOL.SignerCertificate.Subject
    cslol_certificate_thumbprint = [string]$CSLOL.SignerCertificate.Thumbprint
    cslol_timestamp_present = $true
    provenance_and_code_signing_review = "PENDING"
    license_content_enforcement_review = "PENDING"
    practice_tool_visible_skin_test = "PENDING"
    swiftplay_visible_skin_test = "PENDING"
    second_match_and_reconnect = "PENDING"
    clean_install_uninstall = "PENDING"
    public_distribution_approved = $false
}
$Record | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $Manifest -Encoding UTF8
Write-Host "LOCAL TEST INSTALLER CREATED (not public distribution approved)" -ForegroundColor Green
Write-Host $Candidate
Write-Host ("SHA-256: " + $Record.package_sha256)
Write-Host "All 4 packaged runtime inputs match their audited local staging hashes."
Write-Warning "Publisher certificate trust, content enforcement, runtime compatibility and full installed-game QA still require independent review. DO NOT PUBLISH."
