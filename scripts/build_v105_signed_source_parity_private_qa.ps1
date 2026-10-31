# PSM 1.0.5 - signed-source parity PRIVATE frozen build.
# No installation, signature modification, or publication.
param(
    [Parameter(Mandatory=$true)][string]$OriginalSourceRepo,
    [string]$GameDir = "C:\Riot Games\League of Legends\Game"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
function Check([string]$Stage) {
    if ($LASTEXITCODE -ne 0) { throw "$Stage failed with code $LASTEXITCODE" }
}
function Sha([string]$File) {
    return (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToUpperInvariant()
}
if ($env:OS -ne "Windows_NT") { throw "Windows-only private QA." }
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Original = (Resolve-Path -LiteralPath $OriginalSourceRepo).Path
if ($Root.Equals($Original, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Do not run this builder in the ORIGINAL working source checkout."
}
if (-not (Test-Path -LiteralPath (Join-Path $Root ".git") -PathType Leaf)) {
    throw "Use only a newly created linked Git QA worktree."
}
Push-Location -LiteralPath $Root
try {
    $Branch = (& git branch --show-current).Trim()
    Check "Branch discovery"
    if (-not $Branch.StartsWith("qa/v105-signed-parity-")) {
        throw "Expected a qa/v105-signed-parity-* private branch."
    }
    $Dirty = @(& git status --porcelain --untracked-files=no)
    Check "Tracked status"
    if ($Dirty.Count -gt 0) { throw "Tracked changes found. Use clean QA worktree." }
    $Commit = (& git rev-parse HEAD).Trim()
    Check "Commit identity"
    $SourceTools = Join-Path $Original "injection\tools"
    $Tools = Join-Path $Root "injection\tools"
    $ModDest = Join-Path $Tools "mod-tools.exe"
    $Dist = Join-Path $Root "dist\PersonalSkinManager"
    $Exe = Join-Path $Dist "PersonalSkinManager.exe"
    $Report = Join-Path $Root "installer\candidates\v1.0.5\signed-source-parity-private-qa.json"
    $Public = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
    foreach ($Path in @($ModDest, $Dist, $Report, $Public)) {
        if (Test-Path -LiteralPath $Path) {
            throw "Existing destination found; use another QA worktree: $Path"
        }
    }
    $Expected = [ordered]@{
        "mod-tools.exe" = "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44"
        "cslol-dll.dll" = "4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90"
        "ltk_patcher_host.exe" = "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1"
        "ltk_patcher_dll.dll" = "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74"
    }
    foreach ($Name in $Expected.Keys) {
        $File = Join-Path $SourceTools $Name
        if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
            throw "Original source runtime missing: $Name"
        }
        if ((Sha $File) -ne $Expected[$Name]) {
            throw "Original source runtime differs from reviewed SHA-256: $Name"
        }
    }
    $Busy = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -in @("PersonalSkinManager", "ltk_patcher_host", "League of Legends", "League of Legends (TM) Client")
    })
    if ($Busy.Count -gt 0) { throw "Close PSM, LTK host and League gameplay first." }
    # Fail BEFORE copying, compiling or bundling an already-expired LTK DLL.
    # Hash matches alone cannot establish League build compatibility.
    & python (Join-Path $Root "scripts\verify_v105_game_ltk_cutoff.py") `
        --game-dir $GameDir --ltk-dir $SourceTools
    Check "League-vs-LTK cutoff preflight"

    Write-Host "1/4 - Run focused QA regression tests" -ForegroundColor Cyan
    & python -m unittest tests.test_v105_signed_source_parity_private_qa_contract tests.test_v105_frozen_external_dll_search tests.test_ltk_qa_runtime_selector tests.test_release_packaging
    Check "Private parity unit tests"

    Write-Host "2/4 - Copy only mod-tools to the separate QA worktree" -ForegroundColor Cyan
    New-Item -Path $Tools -ItemType Directory -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $SourceTools "mod-tools.exe") -Destination $ModDest
    if ((Sha $ModDest) -ne $Expected["mod-tools.exe"]) { throw "Staged mod-tools SHA-256 mismatch." }

    Write-Host "3/4 - Build PRIVATE frozen app from the original source runtime pair" -ForegroundColor Cyan
    $PreviousLtk = [Environment]::GetEnvironmentVariable("PSM_RELEASE_LTK_DIR", "Process")
    $PreviousCslol = [Environment]::GetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", "Process")
    try {
        $env:PSM_RELEASE_LTK_DIR = $SourceTools
        $env:PSM_RELEASE_CSLOL_DIR = $SourceTools
        & python (Join-Path $Root "scripts\build_pyinstaller.py")
        Check "PyInstaller private build"
    }
    finally {
        [Environment]::SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $PreviousLtk, "Process")
        [Environment]::SetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", $PreviousCslol, "Process")
    }
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Frozen EXE missing." }

    Write-Host "4/4 - Verify same original source binary bytes in frozen QA" -ForegroundColor Cyan
    $Inputs = [ordered]@{}
    foreach ($Name in $Expected.Keys) {
        $Matches = @(Get-ChildItem -LiteralPath $Dist -Recurse -File -Filter $Name)
        if ($Matches.Count -ne 1) { throw "Expected exactly one frozen $Name; found $($Matches.Count)" }
        $Hash = Sha $Matches[0].FullName
        if ($Hash -ne $Expected[$Name]) { throw "Frozen differs from original source: $Name" }
        $Inputs[$Name] = $Hash
    }
    if (Test-Path -LiteralPath $Public) { throw "Unexpected installer generated." }
    $Parent = Split-Path -Path $Report -Parent
    New-Item -Path $Parent -ItemType Directory -Force | Out-Null
    $Evidence = [ordered]@{
        version = "1.0.5"
        purpose = "SIGNED-SOURCE FROZEN PARITY QA ONLY - NO DISTRIBUTION"
        source_commit = $Commit
        all_four_source_and_frozen_files_sha256_match = $true
        source_skin_rendering = "UNVERIFIED_ON_CURRENT_LEAGUE"
        frozen_skin_rendering = "NOT TESTED"
        public_distribution_approved = $false
        includes_third_party_signed_binary = $true
        exe_sha256 = Sha $Exe
        runtime_sha256 = $Inputs
    }
    $Evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Report -Encoding UTF8
    Write-Host "SIGNED-SOURCE PARITY PRIVATE BUILD VERIFIED" -ForegroundColor Green
    Write-Host ("Frozen EXE: " + $Exe)
    Write-Warning "NOT an installer. Contains third-party signed binaries; do not publish/share."
    Write-Warning "Hash parity does not establish game hook compatibility or skin rendering."
}
finally {
    Pop-Location
}
