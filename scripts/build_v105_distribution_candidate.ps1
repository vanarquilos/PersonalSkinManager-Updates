# PSM v1.0.5: local release candidate ONLY. Never publishes.
# Original upstream binaries remain intact; remove signatures only from copies.
param([string]$LeagueGameDir = "C:\Riot Games\League of Legends\Game")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Check-Exit([string]$Task) {
    if ($LASTEXITCODE -ne 0) { throw "$Task failed ($LASTEXITCODE). No release approved." }
}

function Get-SignTool {
    $Tool = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
    if ($null -ne $Tool) { return $Tool.Source }
    $ProgramFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
    $Dir = Join-Path $ProgramFilesX86 "Windows Kits\10\bin"
    if (Test-Path -LiteralPath $Dir -PathType Container) {
        $Paths = @(Get-ChildItem -LiteralPath $Dir -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName "x64\signtool.exe" } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
        if ($Paths.Count -gt 0) { return $Paths[0] }
    }
    throw "Install Windows SDK SignTool to remove the upstream signatures from isolated copies."
}

if ($env:OS -ne "Windows_NT") { throw "This release builder requires Windows." }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutDir = Join-Path $Root "installer\candidates\v1.0.5"
$Official = Join-Path $OutDir "audit-only-ltk-v1.28.1"
$Unsigned = Join-Path $OutDir "release-unsigned-ltk"
$Installer = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
$Rc = Join-Path $OutDir "PersonalSkinManager_Setup_v1.0.5-RC.exe"
$Audit = Join-Path $OutDir "release-candidate-audit.json"
$Dist = Join-Path $Root "dist\PersonalSkinManager"
$LegacyActive = Join-Path $Root "injection\tools\_v105_rose_legacy_local_state.json"
$Pair = @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")

# Keep the working local v1.28.1 pair untouched. The build copies the
# pinned originals into an isolated unsigned distribution input directory.
# Having a private test-selection state is not itself a packaging failure.
if (Test-Path -LiteralPath $LegacyActive -PathType Leaf) {
    Write-Host "Private v1.28.1 local runtime is active; preserving it during RC packaging." -ForegroundColor Cyan
    foreach ($Name in $Pair) {
        $ActiveFile = Join-Path (Join-Path $Root "injection\tools") $Name
        $PinnedFile = Join-Path $Official $Name
        if (-not (Test-Path -LiteralPath $ActiveFile -PathType Leaf) -or
            -not (Test-Path -LiteralPath $PinnedFile -PathType Leaf) -or
            (Get-FileHash -LiteralPath $ActiveFile -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $PinnedFile -Algorithm SHA256).Hash) {
            throw "Private test state exists, but the active $Name differs from the pinned original. Refusing to proceed until reviewed."
        }
    }
}
foreach ($Command in @("git", "python")) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "$Command is missing from PATH."
    }
}
if (-not (Test-Path -LiteralPath $LeagueGameDir -PathType Container)) {
    throw "League Game directory not found: $LeagueGameDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $Root "injection\tools\mod-tools.exe") -PathType Leaf)) {
    throw "Required locally reviewed mod-tools.exe is missing."
}
$Processes = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends", "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Processes.Count -gt 0) {
    throw "Close PSM, League gameplay and the patcher before building the installer; files will not be changed."
}
Set-Location -LiteralPath $Root
$Branch = (& git branch --show-current).Trim()
Check-Exit "Git branch"
if ($Branch -ne "fix/v1.0.5-pre-release-hardening") {
    throw "Wrong branch: $Branch"
}
$Dirty = @(& git status --porcelain --untracked-files=no)
Check-Exit "Git worktree"
if ($Dirty.Count -gt 0) { throw "Commit tracked source changes first." }
$Head = (& git rev-parse HEAD).Trim()
Check-Exit "Git revision"

Write-Host "1/5: Run release source regression tests" -ForegroundColor Cyan
$Tests = @(
    "tests.test_release_packaging",
    "tests.test_release_skin_routing",
    "tests.test_psm_ui_polish_release",
    "tests.test_patch_2619_wad_headers",
    "tests.test_ltk_host_protocol",
    "tests.test_ltk_qa_runtime_selector",
    "tests.test_ltk_countdown_prearm",
    "tests.test_overlay_cleanup",
    "tests.test_runtime_failure_reporting",
    "tests.test_runtime_audit_v105",
    "tests.test_ltk_v1281_compatibility_audit",
    "tests.test_rose_legacy_review_contract",
    "tests.test_rose_legacy_local_runtime_contract",
    "tests.test_v105_distribution_contract",
    "tests.test_v105_distribution_tree_audit",
    "tests.test_v105_exe_manifest",
    "tests.test_v105_publish_contract",
    "tests.test_v105_diagnostic_contract",
    "tests.test_v105_skin_wad_inspection",
    "tests.test_swiftplay_runtime"
)
& python -m unittest @Tests
Check-Exit "Release regression tests"

Write-Host "2/5: Verify original official LTK binaries and current League build" -ForegroundColor Cyan
& python (Join-Path $Root "scripts\audit_ltk_v1281_compatibility.py") --candidate-dir $Official --game-dir $LeagueGameDir
Check-Exit "Historical runtime identity and cutoff audit"

Write-Host "3/5: Make license-compliant isolated copies" -ForegroundColor Cyan
$SignTool = Get-SignTool
New-Item -ItemType Directory -Path $Unsigned -Force | Out-Null
$SignedHashes = @{}
$UnsignedHashes = @{}
foreach ($Name in $Pair) {
    $Source = Join-Path $Official $Name
    $Target = Join-Path $Unsigned $Name
    $SignedHashes[$Name] = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
    Copy-Item -LiteralPath $Source -Destination $Target -Force
    if ((Get-AuthenticodeSignature -LiteralPath $Target).Status -ne "NotSigned") {
        & $SignTool remove /s $Target
        Check-Exit "Remove official signature from isolated $Name"
    }
    if ((Get-AuthenticodeSignature -LiteralPath $Target).Status -ne "NotSigned") {
        throw "Upstream signature remains on staged $Name"
    }
    $UnsignedHashes[$Name] = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
    Write-Host "Reviewed unsigned copy: $Name"
}

# The same unsigned pair succeeded in the October 30 isolated source QA,
# but the earlier elevated installed executable failed SetWindowsHookEx.
# Rebuilding is only permitted with a normal-user launch manifest and installer
# launch behavior. The previous elevated installer remains NOT APPROVED.
$SpecFile = Join-Path $Root "PersonalSkinManager.spec"
$InnoFile = Join-Path $Root "installer.iss"
$SpecText = Get-Content -LiteralPath $SpecFile -Raw -Encoding UTF8
$InnoText = Get-Content -LiteralPath $InnoFile -Raw -Encoding UTF8
if ($SpecText -notmatch 'uac_admin\s*=\s*False' -or
    $InnoText -notmatch 'Flags:\s*nowait\s+postinstall\s+skipifsilent\s+runasoriginaluser' -or
    $InnoText -match 'Verb:\s*runas') {
    throw "Packaging still forces elevation. Rebuild blocked until source-test-aligned asInvoker launch is configured."
}
if ($env:PSM_LTK_QA_RUNTIME_DIR) {
    throw "Private source QA runtime selector is set. Close that session before packaging."
}

Write-Host "4/5: Build standalone installer using ONLY the staged LTK copies" -ForegroundColor Cyan
$PriorOverride = [Environment]::GetEnvironmentVariable("PSM_RELEASE_LTK_DIR")
try {
    $env:PSM_RELEASE_LTK_DIR = $Unsigned
    $Started = Get-Date
    & python (Join-Path $Root "scripts\build_all.py")
    Check-Exit "Installer build"
    if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
        throw "Expected installer was not created."
    }
    $Built = Get-Item -LiteralPath $Installer
    if ($Built.Length -lt 1000000 -or $Built.LastWriteTime -lt $Started.AddSeconds(-3)) {
        throw "Installer output appears stale or too small."
    }
    # Verify the actual frozen EXE, not only the source spec.
    & python (Join-Path $Root "scripts\audit_v105_exe_manifest.py") --exe (Join-Path $Dist "PersonalSkinManager.exe")
    Check-Exit "Frozen EXE normal-user launch manifest audit"
    foreach ($Name in $Pair) {
        $Found = @(Get-ChildItem -LiteralPath $Dist -Recurse -File -Filter $Name)
        if ($Found.Count -ne 1) {
            throw "Expected exactly one packaged $Name, found $($Found.Count)."
        }
        if ((Get-FileHash -LiteralPath $Found[0].FullName -Algorithm SHA256).Hash -ne $UnsignedHashes[$Name]) {
            throw "Packaged $Name does not match the unsigned staged input."
        }
        if ((Get-AuthenticodeSignature -LiteralPath $Found[0].FullName).Status -ne "NotSigned") {
            throw "Packaged $Name still bears an upstream signature."
        }
    }
    # Independent second check after building the installer. Public certifi
    # CA trust stores are not private keys; everything else stays blocked.
    & python (Join-Path $Root "scripts\audit_v105_distribution_tree.py") --dist $Dist
    Check-Exit "Private runtime state or signing material was bundled."

    Copy-Item -LiteralPath $Installer -Destination $Rc -Force
    $Hash = (Get-FileHash -LiteralPath $Rc -Algorithm SHA256).Hash
    if ($Hash -ne (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash) {
        throw "Candidate installer checksum mismatch."
    }
    Write-Host "5/5: Record checksum and pending packaged-game QA" -ForegroundColor Cyan
    $Record = [ordered]@{
        version = "1.0.5"
        channel = "RELEASE CANDIDATE - NOT PUBLISHED"
        source_commit = $Head
        created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        ltk_source = "LeagueToolkit/ltk-manager v1.28.1"
        official_input_sha256 = $SignedHashes
        unsigned_bundled_sha256 = $UnsignedHashes
        official_vendor_signatures_removed = $true
        launch_profile = "asInvoker"
        source_unsigned_ab_result = "MAINTAINER_REPORTED_WORKING"
        installed_launch_context_qa = "PENDING"

        filename = (Split-Path -Leaf $Rc)
        sha256 = $Hash
        size_bytes = (Get-Item -LiteralPath $Rc).Length
        installed_test = "PENDING"
        practice_tool_packaged_skin_render = "PENDING"
        swiftplay_packaged_skin_render = "PENDING"
    }
    $Record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Audit -Encoding UTF8
    Write-Host "RC ready for local installation testing: $Rc" -ForegroundColor Green
    Write-Host "SHA-256: $Hash"
    Write-Warning "NOT PUBLISHED: verify skin rendering from this unsigned, installed candidate before release."
}
finally {
    [Environment]::SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $PriorOverride)
}
