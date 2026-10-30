# PSM v1.0.5: Rose-style private QA frozen app, user-provided LTK.
# Bundles PSM's inert CSLOL loader stub and mod-tools but never LTK.
# Strictly local. Does not create an installer or publish files.
param([Parameter(Mandatory=$true)][string]$ModToolsFile)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
function Check([string]$Name) {
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with $LASTEXITCODE" }
}
function Sha([string]$Name) {
    return (Get-FileHash -LiteralPath $Name -Algorithm SHA256).Hash.ToUpperInvariant()
}
if ($env:OS -ne "Windows_NT") { throw "Windows-only build." }
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath (Join-Path $Root ".git") -PathType Leaf)) {
    throw "Use a fresh linked Git worktree; original PSM checkout is protected."
}
Push-Location -LiteralPath $Root
try {
    $Branch = (& git branch --show-current).Trim()
    Check "Git branch"
    if (-not $Branch.StartsWith("qa/v105-rose-")) {
        throw "Branch must start with qa/v105-rose-"
    }
    $Dirty = @(& git status --porcelain --untracked-files=no)
    Check "Git status"
    if ($Dirty.Count -gt 0) { throw "Tracked worktree is dirty; abort." }
    $Commit = (& git rev-parse HEAD).Trim()
    Check "Git commit"
    $Tools = Join-Path $Root "injection\tools"
    $Dist = Join-Path $Root "dist\PersonalSkinManager"
    $Exe = Join-Path $Dist "PersonalSkinManager.exe"
    $Parent = Join-Path $Root "installer\candidates\v1.0.5"
    $StubDir = Join-Path $Parent "psm-inert-stub"
    $Result = Join-Path $Parent "rose-style-frozen-private-qa.json"
    $Public = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
    $ModDest = Join-Path $Tools "mod-tools.exe"
    foreach ($Item in @($Dist, $StubDir, $Result, $Public, $ModDest)) {
        if (Test-Path -LiteralPath $Item) { throw "Existing output: $Item. Start a new linked worktree." }
    }
    if (-not (Test-Path -LiteralPath $ModToolsFile -PathType Leaf) -or
        (Sha $ModToolsFile) -ne "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44") {
        throw "mod-tools.exe fingerprint mismatch."
    }
    $Running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -in @("PersonalSkinManager","League of Legends",
            "League of Legends (TM) Client","ltk_patcher_host")
    })
    if ($Running.Count -gt 0) { throw "Close PSM, LTK host and League gameplay." }
    & python -m unittest tests.test_v105_user_ltk_provisioning tests.test_v105_rose_style_build_contract tests.test_v105_current_ltk_private_manifest tests.test_v105_current_ltk_build_contract tests.test_ltk_host_protocol tests.test_release_packaging
    Check "Rose-style regression tests"
    New-Item -ItemType Directory -Path $Tools -Force | Out-Null
    Copy-Item -LiteralPath $ModToolsFile -Destination $ModDest
    if ((Sha $ModDest) -ne (Sha $ModToolsFile)) { throw "Staged mod-tools mismatch." }
    New-Item -ItemType Directory -Path $StubDir -Force | Out-Null
    $OldStub = [Environment]::GetEnvironmentVariable("PSM_LOCAL_STUB_OUTPUT_DIR", "Process")
    try {
        $env:PSM_LOCAL_STUB_OUTPUT_DIR = $StubDir
        & python (Join-Path $Root "scripts\build_psm_cslol_stub.py")
        Check "PSM CSLOL stub compilation"
    }
    finally {
        [Environment]::SetEnvironmentVariable("PSM_LOCAL_STUB_OUTPUT_DIR", $OldStub, "Process")
    }
    $StubManifest = Join-Path $StubDir "psm-cslol-stub-manifest.json"
    $StubInfo = Get-Content -LiteralPath $StubManifest -Raw | ConvertFrom-Json
    if ($StubInfo.purpose -ne "PSM_V105_INERT_CSLOL_STUB" -or
        $StubInfo.public_distribution_approved -ne $false -or
        (Sha (Join-Path $StubDir "cslol-dll.dll")) -ne $StubInfo.built_sha256) {
        throw "Stub manifest verification failed."
    }
    $OldLtk = [Environment]::GetEnvironmentVariable("PSM_RELEASE_LTK_DIR", "Process")
    $OldCslol = [Environment]::GetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", "Process")
    try {
        [Environment]::SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $null, "Process")
        $env:PSM_RELEASE_CSLOL_DIR = $StubDir
        & python (Join-Path $Root "scripts\build_pyinstaller.py")
        Check "PyInstaller build"
    }
    finally {
        [Environment]::SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $OldLtk, "Process")
        [Environment]::SetEnvironmentVariable("PSM_RELEASE_CSLOL_DIR", $OldCslol, "Process")
    }
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Frozen PSM executable missing." }
    foreach ($Name in @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")) {
        $Packaged = @(Get-ChildItem -LiteralPath $Dist -Recurse -File -Filter $Name)
        if ($Packaged.Count -ne 0) {
            throw "Rose-style package unexpectedly includes user-supplied $Name"
        }
    }
    foreach ($Name in @("mod-tools.exe", "cslol-dll.dll")) {
        $Packaged = @(Get-ChildItem -LiteralPath $Dist -Recurse -File -Filter $Name)
        $Expected = if ($Name -eq "mod-tools.exe") { Sha $ModToolsFile } else { Sha (Join-Path $StubDir $Name) }
        if ($Packaged.Count -ne 1 -or (Sha $Packaged[0].FullName) -ne $Expected) {
            throw "Frozen $Name identity mismatch."
        }
    }
    if (Test-Path -LiteralPath $Public) { throw "Public installer output not permitted." }
    $Record = [ordered]@{
        version = "1.0.5"
        purpose = "ROSE_STYLE_USER_SUPPLIED_LTK_PRIVATE_QA"
        commit = $Commit
        user_provided_ltk_bundled = $false
        cslol_source = "PSM_OWNED_INERT_STUB"
        cslol_stub_sha256 = Sha (Join-Path $StubDir "cslol-dll.dll")
        exe_sha256 = Sha $Exe
        gameplay_skin_rendering = "NOT_TESTED"
        public_distribution_approved = $false
    }
    $Record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Result -Encoding UTF8
    Write-Host "ROSE-STYLE PRIVATE PSM QA BUILD VERIFIED" -ForegroundColor Green
    Write-Host ("Frozen EXE SHA-256: " + $Record.exe_sha256)
    Write-Warning "No LTK host/DLL was bundled. Provision a verified user-supplied pair separately."
    Write-Warning "This build is NOT approved for public distribution or claimed to render skins."
}
finally {
    Pop-Location
}
