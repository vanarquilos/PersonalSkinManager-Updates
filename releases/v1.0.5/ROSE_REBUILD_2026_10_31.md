# Personal Skin Manager v1.0.5 — Rose-compatible rebuild

**Status:** new development branch, NOT A PUBLIC RELEASE; actual skin rendering NOT VERIFIED.

## Source and branch ownership

- New GitHub branch: `rebuild/v1.0.5-rose-compatible`.
- Based on the existing PSM Rose-style v1.0.5 staging work, not on an unreviewed DLL bundle.
- Maintainer's local rollback checkout `fix/v1.0.5-rose-local-rollback` stays untouched.
- Every local private build occurs in a fresh linked `qa/v105-rose-*` worktree. No `git checkout`, force reset, branch switch, cleanup or vendor binary replacement is required in the existing checkout.
- This is a PSM implementation informed by Alban1911/Rose's public source, not a redistribution of Rose's private assets or upstream LeagueToolkit signed patcher.

## The actual Rose-style architecture

1. League client and game lifecycle monitoring remain in the PSM source.
2. `mod-tools.exe mkoverlay` produces an overlay from selected local mods; the PSM-owned inert `cslol-dll.dll` stand-in permits this overlay build without redistributing a third-party signed CSLOL DLL. The stand-in has no injection or skin-rendering functionality.
3. The independently supplied official LTK pair `ltk_patcher_host.exe` and `ltk_patcher_dll.dll` serves the overlay. **Neither file is included in the default frozen application or installer.**
4. A PSM user-owned local manifest pins both SHA-256 hashes, host protocol 3, and a non-distribution status. `scripts/import_user_ltk_v105.ps1` performs an explicit signed-file import into a user-owned installation.
5. The DLL's embedded end-of-life cutoff is compared against the installed League executable PE build. The supported runtime and successful visible in-game rendering must both be established separately. Do not bypass game/patcher security checks.

This matches Rose's documented user-supplied host/DLL model. **Copying Rose's source cannot generate a newer official signed LTK DLL.**

## Known incompatible game/runtime

On October 31, 2026, the maintainer's read-only inventory found seven local LTK directories, all expired for League built **October 30, 2026 19:07:32 UTC**. The latest local LTK DLL cutoff was **October 28, 2026 23:06:41 UTC**. None of those seven pairs is a supported v1.0.5 release candidate.

No cached official LTK Manager installation was found in the probed locations. This is not permission to download unknown binaries, strip signatures, edit expiry values or disable security controls. A newer official-compatible pair must be obtained through a supported LeagueToolkit channel before claiming skin rendering.

## Current official upstream version and license (checked November 1, 2026)

Official LeagueToolkit release history now lists **LTK Manager v1.32.0 (October 30, 2026)**. Earlier v1.31.1 references are superseded. The LTK patcher delivery service can provide independently updated host/DLL bytes; the manager version alone does not establish the selected patcher's build cutoff or current League compatibility. Upstream: https://github.com/LeagueToolkit/ltk-manager/releases

Upstream's LTK Patcher License permits reuse and redistribution under specific conditions, including that official LeagueToolkit code-signing signatures may **not** be distributed under someone else's product without explicit permission. PSM's selected model therefore keeps the official signed host/DLL **user supplied**, avoids modifying vendor signatures, and does not bundle upstream-signed binaries. This is a release-distribution decision, not a claim that all forms of reuse are prohibited. Read the exact terms at https://github.com/LeagueToolkit/ltk-manager/blob/main/LTK-PATCHER-LICENSE.md.

## Installer rebuild fixes

- Inno source still excludes `ltk_patcher_host.exe`, `ltk_patcher_dll.dll` and `ltk-user-local.json` from its payload.
- **Removed the destructive broad uninstall actions** that deleted `{app}\_internal`, `{app}\injection\mods`, or the entire `{app}` tree. Uninstaller-managed PSM binaries are removed by Inno's own tracked-file log; user-provided patcher files and untracked data are not deliberately wiped.
- Removed the cross-product uninstall commands that deleted the standalone `Rose` scheduled task or ran a separate Rose Pengu Loader uninstaller. PSM only deletes its own scheduled task.
- Tests: `tests.test_v105_rose_rebuild_installer_safety`.

## How to create the new isolated private PSM build

**No branch switch and no LTK Manager installation required** to prepare/test the PSM-owned binary itself. Close PSM and League before building.

From the existing local checkout:

```powershell
$Repo = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Ref = "rebuild/v1.0.5-rose-compatible"
git -C $Repo fetch origin ("+refs/heads/" + $Ref + ":refs/remotes/origin/" + $Ref)
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
$Bootstrap = Join-Path ([Environment]::GetFolderPath("Desktop")) "psm-v105-rose-bootstrap.ps1"
git -C $Repo show ("origin/" + $Ref + ":scripts/create_v105_rose_rebuild_worktree.ps1") |
  Set-Content -LiteralPath $Bootstrap -Encoding ascii
if ($LASTEXITCODE -ne 0) { throw "Could not retrieve the bootstrap script" }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $Bootstrap -Original $Repo
if ($LASTEXITCODE -ne 0) { throw "Private Rose-style QA build failed" }
```

The bootstrap creates a unique `PSM-v105-Rose-Rebuild-*` worktree and builds the frozen app with the reviewed local mod-tools and a newly compiled inert PSM-owned CSLOL stub. It **does not ship or install LTK**, publish a release or replace the original source/tester. Requires Python 3.11+, MSVC x64 tools and the project's existing build dependencies on Windows. Use `-PrepareOnly` to skip the build if these are unavailable.

## MSVC quoted-path failure and safe in-place retry (2026-10-31)

A first private rebuild reached the inert CSLOL stub compilation but failed with:

```text
'"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"' is not recognized ...
[ERROR] MSVC stub build failed (1)
```

Cause: the original Python builder passed a compound `call "C:\Program Files ...\vcvars64.bat" >nul && cl ...` string directly through `cmd.exe /c`. Quotation was stripped/misparsed before MSVC was configured. The user already has a `vcvars64.bat` path that `vswhere` discovered; this **does not prove Build Tools are missing**.

Fix: `scripts/build_psm_cslol_stub.py` now writes a temporary `build_stub.cmd` and invokes it by its short basename as `cmd.exe /d /c build_stub.cmd` from its own working directory. Inside the batch, `call "path with spaces\vcvars64.bat" >nul` works with normal batch semantics; `cl` and `dumpbin` share the vcvars environment. Failed compilation now reports compiler stdout/stderr. Regression: `tests.test_v105_msvc_space_path_contract`, plus revised `tests.test_v105_rose_style_build_contract` expectations.

The private builder now has a strictly controlled `-ResumeFailedStubBuild` option. It refuses all unexpected/missing state: it must be a clean tracked `qa/v105-rose-*` linked worktree, have the reviewed SHA-pinned mod-tools binary, an existing **empty** inert stub directory, no frozen app, no finished QA manifest and no installer. It does not delete or overwrite any existing output.

The original unsuccessful QA directory can be retried *without* making another QA worktree. From PowerShell:

```powershell
$ErrorActionPreference = "Stop"
$QA = "C:\Users\Van Arquilos\Desktop\PSM-v105-Rose-Rebuild-20261031-132306"
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Ref = "rebuild/v1.0.5-rose-compatible"

if (-not (Test-Path -LiteralPath $QA -PathType Container)) { throw "QA folder missing" }
$Branch = (git -C $QA branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or -not $Branch.StartsWith("qa/v105-rose-")) {
    throw "Not an isolated PSM Rose QA worktree; original left untouched"
}
$Dirty = @(git -C $QA status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $Dirty.Count -gt 0) {
    throw "Tracked QA worktree changed. Will not overwrite"
}
git -C $QA fetch origin ("+refs/heads/" + $Ref + ":refs/remotes/origin/" + $Ref)
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $QA merge --ff-only ("origin/" + $Ref)
if ($LASTEXITCODE -ne 0) { throw "Fast-forward merge failed" }

Push-Location $QA
try {
    python -m unittest -v tests.test_v105_msvc_space_path_contract tests.test_v105_rose_style_build_contract
    if ($LASTEXITCODE -ne 0) { throw "Source contract tests failed" }
} finally { Pop-Location }

powershell.exe -NoProfile -ExecutionPolicy RemoteSigned `
    -File (Join-Path $QA "scripts\build_v105_rose_style_frozen_private_qa.ps1") `
    -ModToolsFile (Join-Path $Original "injection\tools\mod-tools.exe") `
    -ResumeFailedStubBuild

if ($LASTEXITCODE -ne 0) { throw "Resumed private QA build failed" }
Write-Host "Private QA output: $(Join-Path $QA 'dist\PersonalSkinManager\PersonalSkinManager.exe')"
```

No source checkout reset, installer, network LTK download, vendor binary replacement, or game process execution. **A successful inert-stub build only establishes compatibility with the mod-tools loader; skins cannot render until an official current LTK host/DLL pair has been supplied and tested.** The GitHub Windows CI check still reports failure without usable job logs; do not claim remote validation passed.

## One-command completion entry point (November 1, 2026)

The repo now has `scripts/finish_v105_rose_private_qa.ps1`, which validates and
fast-forwards **only** the existing linked QA worktree, runs focused regression
tests, resumes the original failed stub compilation, verifies the final EXE
hash and QA manifest, and keeps the original rollback checkout intact. The
script refuses to touch an unexpected checkout, a changed mod-tools binary,
nonempty stub output, partial frozen outputs or a dirty tracked worktree.
It does not install LTK Manager or publish a release.

Because the user's main checkout stays on its rollback branch, fetch the
new script from its isolated rebuild branch into a temporary file and run it:

```powershell
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Ref = "rebuild/v1.0.5-rose-compatible"
$TempScript = Join-Path $env:TEMP "finish-psm-v105-rose-qa.ps1"

git -C $Repo fetch origin ("+refs/heads/" + $Ref + ":refs/remotes/origin/" + $Ref)
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }

$ScriptText = @(git -C $Repo show ("origin/" + $Ref + ":scripts/finish_v105_rose_private_qa.ps1"))
if ($LASTEXITCODE -ne 0 -or $ScriptText.Count -eq 0) {
    throw "Cannot retrieve QA completion script"
}
$ScriptText | Set-Content -LiteralPath $TempScript -Encoding Ascii

powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $TempScript
if ($LASTEXITCODE -ne 0) { throw "Isolated PSM private build failed" }
```

This completes only **source/private frozen packaging** if Windows build
dependencies and all earlier QA invariants pass. The build produces **no**
working LTK host/DLL and does not establish visible skin rendering.

## November 1: official delivery compatibility and CI runner diagnosis

### LTK delivery is authenticated, not a public file mirror

LeagueToolkit's current `crates/ltk-manager-runtime/src/patcher/delivery/mod.rs`
requires a release-build attestation for a network sync, verifies a minisign
manifest, downloads `ltk_patcher_dll.dll` into
`<manager data dir>/patcher/<lowercase dll SHA256>/`, and copies the official
host into the same directory when selecting a session. Its October 31 ADR-0074
explicitly requires the delivered DLL and a **normal user integrity** process.
An unofficial standalone downloader impersonating or replaying an upstream
attestation is **not** part of PSM.

Our user-provided LTK model remains compatible with that layout: once the
real official Manager has staged a verified matching host/DLL pair, it may
be inspected and deliberately imported through the existing
`scripts/import_user_ltk_v105.ps1` script after independently checking
SHA-256, Authenticode and the current League build. PSM does not distribute
vendor signatures or tamper with game integrity controls.

New `scripts/audit_official_ltk_delivery_cache_v105.py` is READ-ONLY. Its
default roots are `%APPDATA%/dev.leaguetoolkit.manager/patcher` and
`%LOCALAPPDATA%/dev.leaguetoolkit.manager/patcher`. For a custom LTK Manager
mod storage directory, specify `--data-dir "D:\\YourLTKStorage"`.
It inventories immediate SHA-256-named folders only, verifies that a staged
DLL's SHA matches its directory, confirms a host file is beside the DLL,
and compares its embedded cutoff with the League executable's PE timestamp.
**It never reads the delivery.json token, impersonates a manager, downloads
a DLL, runs external binaries or declares a skin working.** Source test:
`tests.test_v105_official_ltk_cache_inventory`.

```powershell
$QA = "C:\Users\Van Arquilos\Desktop\PSM-v105-Rose-Rebuild-20261031-132306"
Set-Location -LiteralPath $QA
python scripts/audit_official_ltk_delivery_cache_v105.py --league-dir "C:\Riot Games\League of Legends"
```

A cache containing no candidate is **not** a PSM packaging bug. The user
must obtain a legitimate delivered patcher through LeagueToolkit's supported
manager process. The manager release version alone cannot guarantee a newer
DLL for the current game build. User can keep PSM installed independently.

### Remove the real privilege mismatch

Before this change the PSM PyInstaller spec set `uac_admin=True`, and source
`main/core/initialization.py` called `ensure_admin_rights()`. Even with
`LTK_ELEVATE_INJECTOR=False`, starting the LTK child from an elevated PSM
parent inherits high integrity, contradicting upstream ADR-0074. The rebuild
now sets `uac_admin=False`, avoids forcing source startup elevation,
refuses elevated LTK child startup with a clear diagnostic, and creates
new auto-start tasks with `/RL LIMITED` instead of `HIGHEST`.
The changed binary must still be validated on actual Windows and existing
legacy high-integrity scheduled tasks must be reviewed manually.
Contract: `tests.test_v105_ltk_unelevated_contract`.

### Why GitHub Windows CI reports failure without logs

GitHub run `41266285801` contained three failures with **no job steps**,
including a minimal Ubuntu echo job that imports no PSM code, Python or MSVC.
Another earlier Windows-only run behaved identically even when rerun.
This isolates the red state to **GitHub Actions job provisioning or
account/repository configuration**, not an observed PSM unit-test assertion.
The exact provider-side cause remains unknown. On GitHub, inspect the
Actions run's summary/annotations and repository
`Settings > Actions > General`, plus any Actions billing/usage restriction.
If those show no actionable error, raise GitHub Support with run/job IDs.
Do not change working PSM production code to suppress or fake these CI checks.

Manual source checks remain possible locally using
`python -m unittest`; no CI success or public release can be claimed
until GitHub runners become available. Even a full source/CI pass does not
replace in-game Practice Tool verification and current authorized LTK DLL.

## Verification gates

- Windows source contract tests pass, including proper installer ownership, branch preservation and SHA/protocol/cutoff checks.
- MSVC compiles the inert stub and `dumpbin` verifies all eight expected exports.
- A private PyInstaller freeze contains exactly one PSM-owned inert stub and one approved mod-tools, **zero** LTK patcher host/DLL binaries, and a manifest recording `gameplay_skin_rendering=NOT_TESTED`.
- Once an official compatible user-provided LTK pair exists, validate Authenticode/signatures and SHA-256s, compare DLL cutoff against installed League, then run permitted Practice Tool/Swiftplay QA.
- Do not publish an installer or mark the build skin-ready without visible in-game rendering and successful clean install/uninstall/upgrade testing.

CI workflow: `.github/workflows/v105-rose-rebuild-validation.yml`. These are code and ABI gates only, not an anti-cheat compatibility test.
