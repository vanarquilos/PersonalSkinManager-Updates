# Personal Skin Manager 1.0.5 — current LTK runtime integration

**State (2026-10-30): source implementation staged, static inspection complete, Windows tests and gameplay pending. Public installer remains NO-GO.**

## Upstream facts verified from LeagueToolkit v1.31.1

- [LTK Manager v1.31.1](https://github.com/LeagueToolkit/ltk-manager/releases/tag/v1.31.1) was released 2026-10-28.
- [Source host protocol](https://github.com/LeagueToolkit/ltk-manager/blob/v1.31.1/crates/ltk-manager-runtime/src/patcher/host/protocol.rs) retains `config loglevel`, `config flags`, `config prefix` and `start scan`. [Host process tests](https://github.com/LeagueToolkit/ltk-manager/blob/v1.31.1/crates/ltk-manager-runtime/src/patcher/host/process.rs) assert `config flags 0`.
- [Bundled host protocol](https://github.com/LeagueToolkit/ltk-manager/blob/v1.31.1/src-tauri/src/patcher/delivery.rs) is `3`. The **manager release version is not the patcher DLL version**. Patcher builds now ship independently and are verified against signed delivery manifests.
- [ADR-0067](https://github.com/LeagueToolkit/ltk-manager/blob/v1.31.1/docs/adr/0067-a-delivered-patcher-dll-runs-only-unelevated.md): elevated LTK hosts use the bundled host/DLL from an administrator-only installation; delivered DLLs in user-writable AppData are only selected for unelevated sessions. PSM currently requests elevation, so this QA path uses an official **bundled** pair, not a delivered AppData pair.
- [LTK Patcher License](https://github.com/LeagueToolkit/ltk-manager/blob/main/LTK-PATCHER-LICENSE.md): upstream code-signed patcher binaries may not be redistributed by PSM under the upstream signature without explicit written permission. [CSLOL DLL License Addendum](https://github.com/LeagueToolkit/cslol-manager/blob/master/LICENSE-CSLOL.md) adds separate publisher-owned code-signing, trusted timestamp, and prohibited-content enforcement requirements.

## Implemented in the v1.0.5 staging branch

1. `injection/tools/patcher.py` accepts the optional `PSM_LTK_QA_MANIFEST` with `PSM_LTK_QA_RUNTIME_DIR`. The manifest pins schema 1, private-only purpose, bundled origin, protocol 3, exact host/DLL SHA-256, and refuses public distribution. Missing, changed, symlinked, malformed or incorrectly pinned files fail closed. Existing known v1.28.1 private QA selector remains backward compatible.
2. `injection/overlay/ltk_host.py` now uses `config flags 0` for all v1.0.5 staging paths. **Never** send bit `4` (`OPT_OUT_AH_V1`), which disables upstream skinhack enforcement.
3. `scripts/prepare_v105_current_ltk_private_qa.ps1` independently compares a local upstream-bundled candidate with two expected digests, verifies Valid Authenticode signatures, and records a small **local private QA** JSON manifest outside the vendor file directory. It does not copy or edit DLLs.
4. `scripts/build_v105_current_ltk_frozen_private_qa.ps1` makes a frozen QA folder in a **brand-new linked worktree** on a `qa/v105-current-ltk-*` branch. It refuses previous outputs, the failed old pair, hash mismatches and existing processes. It checks the four frozen inputs afterward and writes a manifest with `public_distribution_approved=false`. It creates **no installer**.
5. Tests: `tests.test_v105_current_ltk_private_manifest` and `tests.test_v105_current_ltk_build_contract`, as well as the updated host-protocol tests. These run on the user's Windows Python environment.

## Required local inputs

Choose a **verified, unmodified official LTK Manager v1.31.1 bundled** host/DLL pair (not a patcher delivery cache folder). Both files must be together in one directory. Keep that source directory unchanged. Do not assume the latest manager version implies the latest delivered patcher DLL; verify the exact bytes selected.

The operator must supply the two independently established expected SHA-256 values. Do not fill them from an untrusted download or assume historic hashes. Check upstream publisher Authenticode signatures and official release origin. If these cannot be established, do not generate a QA package.

### Prepare private QA manifest (Windows PowerShell)

```powershell
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Stage = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
$UpstreamBundled = "C:\REPLACE-WITH-VERIFIED-OFFICIAL-LTK-BUNDLED-DIRECTORY"
$HostHash = "REPLACE_WITH_INDEPENDENTLY_VERIFIED_64_HEX_HOST_SHA256"
$DllHash = "REPLACE_WITH_INDEPENDENTLY_VERIFIED_64_HEX_DLL_SHA256"
$Manifest = Join-Path $env:USERPROFILE "Desktop\PSM-v105-current-ltk-private-qa.json"
git -C $Stage pull --ff-only origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git update failed" }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned `
  -File (Join-Path $Stage "scripts\prepare_v105_current_ltk_private_qa.ps1") `
  -LtkDir $UpstreamBundled -ExpectedHostSha256 $HostHash -ExpectedDllSha256 $DllHash `
  -OutputManifest $Manifest -SourceManagerRelease v1.31.1
if ($LASTEXITCODE -ne 0) { throw "Current LTK provenance preparation failed" }
```

### Frozen private QA build without changing the installed app

Run with **PSM and League closed**. A new linked worktree is mandatory:

```powershell
$Name = "qa/v105-current-ltk-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$New = "C:\Users\Van Arquilos\Desktop\PSM-v105-Current-LTK-QA-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
git -C $Original fetch origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $Original worktree add -b $Name $New origin/release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Worktree setup failed" }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned `
  -File (Join-Path $New "scripts\build_v105_current_ltk_frozen_private_qa.ps1") `
  -ModToolsFile (Join-Path $Original "injection\tools\mod-tools.exe") `
  -LtkDir $UpstreamBundled -QaManifest $Manifest -CslolDir (Join-Path $Original "injection\tools")
if ($LASTEXITCODE -ne 0) { throw "QA frozen build failed" }
```

The frozen exe remains private because the build includes upstream-signed LTK and separately third-party-signed CSLOL binaries. **Do not upload/share the EXE or folder**, nor run the public builder on these QA inputs. The source code changes, tests and documentation can be reviewed publicly without bundling binaries.

### Windows QA outcome gate

In an elevated test shell, launch the exact new frozen PSM executable with `--dev --debug --logs`, setting `PSM_LTK_QA_RUNTIME_DIR` and `PSM_LTK_QA_MANIFEST` for that child process from the audited source inputs. Verify a single PSM process, test a permitted custom cosmetic through Practice Tool, and run `scripts/inspect_v105_hook_failure_details.ps1 -SinceLocal $TestStart`. Capture LCU/WebSocket, skin trigger, scanner, hook, attachment, WAD and visible rendering results. The source/publisher identity check is not a gameplay compatibility claim.

**Release blockers:** valid current runtime in a real match, official host-protocol compatibility in PSM, clean installed QA, publisher code-signing authorization for the LTK pair, distributor-owned CA signing and timestamp for CSLOL, and permitted-content filtering. Keep the release PR in draft until these checks pass. No security controls may be disabled to make QA succeed.
