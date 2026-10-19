# Publish Personal Skin Manager v1.0.4 as a community-testing pre-release.
# Requires a Windows development checkout with the trusted local runtime trio.
# Does not disable antivirus, bypass LTK compatibility checks, or reuse an old installer.

param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-LastExit([string] $Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed (exit code $LASTEXITCODE). Nothing further will be published."
    }
}

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Root

$Repo = "vanarquilos/PersonalSkinManager-Updates"
$Tag = "v1.0.4"
$Installer = Join-Path $Root "installer\PersonalSkinManager_Setup.exe"
$NotesFile = Join-Path $Root "installer\PSM-v1.0.4-community-release-notes.md"
$OldHash = "4E1FB68959577213D773C98A8803850122848A838E0983B1397B5B6A1208C7FB"

Write-Host ""
Write-Host "=== PSM v1.0.4 | Community-Test Release ===" -ForegroundColor Cyan
Write-Host "Checkout: $Root"
Write-Host "Release type: public pre-release (Swiftplay gameplay not yet verified)"
Write-Host ""

if ($env:OS -ne "Windows_NT") {
    throw "The PSM Windows installer must be built on Windows."
}

foreach ($ToolName in @("git", "python", "gh")) {
    if (-not (Get-Command $ToolName -ErrorAction SilentlyContinue)) {
        if ($ToolName -eq "gh") {
            throw "GitHub CLI is missing. Install it with: winget install --id GitHub.cli -e"
        }
        throw "$ToolName is not installed or is not on PATH."
    }
}

& gh auth status --hostname github.com
Assert-LastExit "GitHub CLI authentication (run: gh auth login)"

$Branch = (& git branch --show-current).Trim()
Assert-LastExit "Read Git branch"
if ($Branch -ne "main") {
    throw "Checkout the main branch first; current branch is '$Branch'."
}

$TrackedChanges = (& git status --porcelain --untracked-files=no)
Assert-LastExit "Inspect working tree"
if ($TrackedChanges) {
    throw "Tracked local changes found. Commit or stash them before publishing; this script will not overwrite your work."
}

& git fetch origin main
Assert-LastExit "Fetch main"
& git pull --ff-only origin main
Assert-LastExit "Update main"

$ActualAppVersion = (Get-Content -LiteralPath (Join-Path $Root "config.py") -Raw)
$ActualInstallerVersion = (Get-Content -LiteralPath (Join-Path $Root "installer.iss") -Raw)
if ($ActualAppVersion -notmatch 'APP_VERSION\s*=\s*"1\.0\.4"' -or
    $ActualInstallerVersion -notmatch '#define MyAppVersion "1\.0\.4"') {
    throw "Source/installer version is not exactly 1.0.4."
}

# Refuse to replace an existing public release or Git tag.
$ExistingTag = (& git ls-remote --tags origin "refs/tags/$Tag")
Assert-LastExit "Inspect remote release tag"
if ($ExistingTag) {
    throw "The $Tag tag already exists. Review the existing release instead of overwriting it."
}

$RuntimeNames = @(
    "injection\tools\mod-tools.exe",
    "injection\tools\ltk_patcher_host.exe",
    "injection\tools\ltk_patcher_dll.dll"
)
foreach ($Relative in $RuntimeNames) {
    $InputFile = Join-Path $Root $Relative
    if (-not (Test-Path -LiteralPath $InputFile -PathType Leaf)) {
        throw "Missing trusted local runtime file: $InputFile"
    }
}
Write-Host "Required local runtime files found." -ForegroundColor Green

Write-Host ""
Write-Host "Running automated source tests (not a substitute for Swiftplay gameplay QA)..." -ForegroundColor Cyan
& python -m unittest tests.test_release_packaging tests.test_release_skin_routing tests.test_psm_ui_polish_release tests.test_patch_2619_wad_headers tests.test_ltk_host_protocol tests.test_ltk_countdown_prearm tests.test_overlay_cleanup
Assert-LastExit "PSM source regression tests"

# Archive any previous installer so we cannot accidentally publish v1.0.3
# under the v1.0.4 tag if the new build fails.
if (Test-Path -LiteralPath $Installer -PathType Leaf) {
    $PreviousHash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash
    $ArchiveDir = Join-Path $Root "installer\archive"
    New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
    $ArchivePath = Join-Path $ArchiveDir "PersonalSkinManager_Setup-$PreviousHash.exe"
    if (Test-Path -LiteralPath $ArchivePath -PathType Leaf) {
        Remove-Item -LiteralPath $Installer -Force
    } else {
        Move-Item -LiteralPath $Installer -Destination $ArchivePath
    }
    Write-Host "Archived previous installer: $ArchivePath"
}

Write-Host ""
Write-Host "Building PSM v1.0.4 and the Windows installer..." -ForegroundColor Cyan
$BuildStarted = Get-Date
& python (Join-Path $Root "scripts\build_all.py")
Assert-LastExit "Complete v1.0.4 Windows build"

if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
    throw "No installer was produced: $Installer"
}

$Built = Get-Item -LiteralPath $Installer
if ($Built.LastWriteTime -lt $BuildStarted.AddSeconds(-2)) {
    throw "The installer does not appear to be from this build. Refusing to publish."
}
if ($Built.Length -lt 1000000) {
    throw "The installer is unexpectedly small ($($Built.Length) bytes). Refusing to publish."
}

$Hash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToUpperInvariant()
if ($Hash -eq $OldHash) {
    throw "Built installer SHA-256 matches the old v1.0.3 installer. Refusing to relabel it."
}
$Size = [int64] $Built.Length

# Build release notes from the verified artifact, not a guessed checksum.
$Notes = @'
# Personal Skin Manager v1.0.4

## League compatibility update (community testing)

This is a public **pre-release** for community testing. It addresses an LTK scanner timing problem that could leave the selected skin unapplied when League starts.

### Changes

- Starts the scanner earlier during the loadout countdown.
- Reuses the running scanner for the skin overlay.
- Cleans up unused and stopped scanner sessions between games.
- Preserves the overlay directory when clearing its contents.
- Keeps the existing League-build compatibility check; unsupported runtimes are not bypassed.

### Test status

- Normal skin injection: working in maintainer's live test.
- Swiftplay lobby skin selection: working in maintainer's live test.
- **Swiftplay in-game injection: not yet verified on v1.0.4.**
- Automated source regression tests: passed during this Windows build.
- Compatibility across all game patches and PCs is not guaranteed.

Please report issues through https://psm.vanarquilos.dev (Feedback / Support). Include PSM v1.0.4, game mode, the skin selected, and the problem. Do not include passwords or session tokens.

### Installer verification

- Filename: PersonalSkinManager_Setup.exe
- File size: {{SIZE}} bytes
- SHA-256: {{SHA256}}

Download only from the official GitHub Release. Do not disable antivirus protection to run the installer.

Based on the open-source Rose project by Alban and Florent. GitHub Releases is separate from PSM's signed in-app updater, which may remain on an older version.
'@
$Notes = $Notes.Replace("{{SIZE}}", "$Size").Replace("{{SHA256}}", $Hash)
Set-Content -LiteralPath $NotesFile -Value $Notes -Encoding UTF8

$Commit = (& git rev-parse HEAD).Trim()
Assert-LastExit "Read release source commit"

Write-Host ""
Write-Host "Publishing GitHub PRE-RELEASE..." -ForegroundColor Cyan
Write-Host "Source commit: $Commit"
Write-Host "Installer: $Installer"
Write-Host "Size: $Size bytes"
Write-Host "SHA-256: $Hash"

& gh release create $Tag $Installer --repo $Repo --target $Commit --title "PSM v1.0.4 - Community Test" --notes-file $NotesFile --prerelease
Assert-LastExit "GitHub release creation"

$ReleaseJson = & gh api "repos/$Repo/releases/tags/$Tag"
Assert-LastExit "Verify published release"
$Release = ($ReleaseJson | ConvertFrom-Json)

if (-not $Release.prerelease) {
    throw "Release exists, but GitHub did not mark it as a pre-release."
}

$Asset = @($Release.assets | Where-Object { $_.name -eq "PersonalSkinManager_Setup.exe" }) | Select-Object -First 1
if (-not $Asset) {
    throw "Release was created, but the installer asset is missing."
}
if ([int64]$Asset.size -ne $Size) {
    throw "Published installer size differs from the local build."
}
if ($Asset.digest -and $Asset.digest.ToLowerInvariant() -ne ("sha256:" + $Hash.ToLowerInvariant())) {
    throw "Published installer digest does not match the local build."
}

Write-Host ""
Write-Host "PUBLISHED: PSM v1.0.4 community-test pre-release" -ForegroundColor Green
Write-Host "Release: $($Release.html_url)"
Write-Host "Installer SHA-256: $Hash"
Write-Host "Installer size: $Size bytes"
Write-Host ""
Write-Host "Swiftplay gameplay is intentionally disclosed as unverified."
Write-Host "The signed in-app updater has not been changed."
