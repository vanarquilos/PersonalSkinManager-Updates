# PSM 1.0.5 — no-install source/frozen runtime parity investigation

**Status: code-only QA prepared, gameplay not proven.** The maintainer does not need to install another LTK Manager or replace the working PSM installation to continue investigating the source-versus-PyInstaller discrepancy.

## Preferred definitive A/B: same reviewed ORIGINAL signed source pair in private frozen QA

The previous `scripts/build_v105_frozen_parity_private_qa.ps1` used **unsigned v1.28.1** host/DLL hashes that failed during gameplay, so it could not establish parity against the original signed source. A new script `scripts/build_v105_signed_source_parity_private_qa.ps1` uses the original source host/DLL hashes, unchanged original CSLOL input, and original mod-tools version. It builds ONLY a local frozen QA folder and confirms exact SHA-256 matches for all four packaged components. **No new official manager installation and no binary download.**

Copy/run the complete block in Windows PowerShell with PSM and League closed. It creates a unique NEW linked worktree; the working original checkout is untouched:

```powershell
$ErrorActionPreference = "Stop"
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Branch = "qa/v105-signed-parity-$Stamp"
$QA = "C:\Users\Van Arquilos\Desktop\PSM-v105-Signed-Parity-$Stamp"

git -C $Original fetch origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git -C $Original worktree add -b $Branch $QA origin/release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "QA worktree creation failed" }

powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File (Join-Path $QA "scripts\build_v105_signed_source_parity_private_qa.ps1") -OriginalSourceRepo $Original
if ($LASTEXITCODE -ne 0) { throw "Source-parity QA frozen build failed" }
Write-Host "Private EXE: $(Join-Path $QA 'dist\PersonalSkinManager\PersonalSkinManager.exe')"
```

Next, conduct a permitted Practice Tool test in the frozen QA build and inspect `scripts/inspect_v105_hook_failure_details.ps1`. Compare with a current Python source run **using the same exact pair**.

- Source renders, identical frozen doesn't: investigate PyInstaller DLL search, process elevation, host launch context, environment, game-suspension timing, and sidecar file placement.
- Both source and identical frozen fail: latest League build/upstream patcher compatibility problem, not demonstrated PyInstaller regression. Do not bypass security checks.
- Both render: private runtime parity passes, but public redistribution and clean-install/Swiftplay verification remain separate release gates.

**Never publish this private EXE/folder:** it contains upstream/third-party signed binaries and carries `public_distribution_approved=false`. A local hash match is not permission to distribute it. Keep draft PR #18 unmerged.

## What we know

- A previous Python-source workflow reportedly rendered a cosmetic. Exact active LTK host/DLL identity during that historical run was **not independently recorded**; source UAC relaunch could have dropped an unsigned QA override.
- Full frozen PSM QA on 2026-10-30 at 23:13:28 successfully observed LCU/WebSocket connection, gameflow, skin injection trigger, pre-armed scanner and overlay preparation, but failed at `SetWindowsHookEx` (three `0x00000000` log records). No DLL overlay initialization, host attachment or WAD redirection was recorded.
- Historical source-host SHA-256: `23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1`; source LTK DLL: `6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74`.
- Previously failed frozen QA unsigned-host SHA-256: `5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9`; DLL: `B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29`.
- These were **not matching file pairs**. A successful Python-source test does not validate a frozen EXE built with a different patcher.
- PSM v1.0.5 staging now defaults to the Rose-style **user-supplied runtime** model. A newly frozen app intentionally ships **without** the LTK host/DLL until a reviewed matching pair is explicitly provisioned. This is not a skin-ready standalone installer.

## Implemented without changing the desktop

- Corrected outdated regression assertions that required `LTK_PATCHER_FLAGS = 4`: `tests/test_release_packaging.py` and `tests/test_v105_frozen_external_dll_search.py` now align with upstream enforcement defaults (`flags=0`).
- Added `scripts/check_v105_source_frozen_pair_parity.ps1`, a **read-only** comparison of the four local runtime inputs in source and an existing frozen QA folder. It prints only component names and whether each file is IDENTICAL/DIFFERENT/SOURCE_ONLY/FROZEN_ONLY/ABSENT_BOTH. It does not run League, copy DLLs, install LTK or mutate PSM.
- Added contract test `tests.test_v105_source_frozen_pair_parity_contract`.
- Added `.github/workflows/windows-v105-parity.yml` to run Windows Python regressions and MSVC compilation/export checking of the inert, **PSM-owned** CSLOL loader stub on GitHub's Windows runner. Its workflow is code-only: no League process, no third-party LTK input, no uploaded executable release. **Workflow results are not confirmed.**

## Read-only comparison with the existing directories (optional)

No installation and no new download are needed. Use the existing source checkout and frozen QA executable:

```powershell
$Staging = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
$Source = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Frozen = "C:\Users\Van Arquilos\Desktop\PSM-v105-Frozen-Fix-20261030-222824\dist\PersonalSkinManager\PersonalSkinManager.exe"
git -C $Staging pull --ff-only origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Staging update failed" }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned `
  -File (Join-Path $Staging "scripts\check_v105_source_frozen_pair_parity.ps1") `
  -SourceRepo $Source -FrozenExe $Frozen
```

Interpretation: if the source and frozen LTK host or DLL are DIFFERENT, the earlier packaging comparison was not apples-to-apples. If both are SOURCE_ONLY, the Rose-style build needs a separately provisioned user-owned runtime; this does not mean the PyInstaller packaging itself failed. If both are IDENTICAL, inspect process elevation and host initialization next. A file-level match **does not** establish skin rendering, anti-cheat compatibility, redistribution rights or a successful public installer.

## No-install next gates

1. Observe the GitHub Windows regression and MSVC results; repair any code/test failure without modifying the original local PSM build.
2. Compare the original source pair with a previously frozen build using the read-only test above *only if and when the maintainer wants to provide that evidence*. Do not ask for new LTK installation.
3. If actual signed source runtime is necessary for a one-time controlled PRIVATE frozen parity build, reuse the already-local reviewed host/DLL for that QA only; do not distribute vendor-signed patcher bytes in a public installer.
4. Public release remains blocked until a matching supported runtime demonstrably renders skins in an installed, clean Windows environment and applicable distribution conditions are satisfied.

**Release decision: NO-GO for a 'fully working' v1.0.5.** A code-only CI pass or exact hash match is not sufficient to assert that a League skin rendered.
