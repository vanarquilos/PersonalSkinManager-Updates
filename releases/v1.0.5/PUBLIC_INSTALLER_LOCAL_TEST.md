# PSM v1.0.5 — Public installer path, local Windows testing only

**Status: staging implementation available for Windows QA, but no tested public installer exists yet.** This work does not alter the working private QA installer, original source host/DLL, public v1.0.4 release, or stable signed updater.

## What changed in this staging branch

1. The PyInstaller spec explicitly bundles all four co-dependent runtime files: `mod-tools.exe`, `cslol-dll.dll`, `ltk_patcher_host.exe`, and `ltk_patcher_dll.dll`. The earlier spec enumerated only three.
2. `PSM_RELEASE_LTK_DIR` selects isolated LTK host/DLL files. `PSM_RELEASE_CSLOL_DIR` independently selects an isolated CSLOL companion, avoiding silent bundling of a private original.
3. `scripts/preflight_v105_public_candidate.ps1` prints a **read-only** staged-file and signature audit, known-bad-runtime check, and manual license gate.
4. `scripts/build_v105_public_path_local_test.ps1` builds only in a **fresh linked Git worktree** and insists on audited inputs. It does **not** create a public release or attest to licensing, content enforcement, or gameplay success.
5. All the added Python contract checks are source-level, not substitute Windows/gameplay tests.

## Public distribution constraints

- The official LTK patcher host/DLL must have League Toolkit's signatures removed from copies used in a third-party installer, unless written permission says otherwise. A PSM-owned signature is optional under that patcher license, and may merit compatibility testing; it is not guaranteed to solve the earlier hook failure.
- The **CSLOL DLL Addendum v1.1** is separate. It requires a publicly trusted CA-issued distributor signing certificate, trusted timestamp, published publisher certificate identity/fingerprint and DLL SHA-256, and functional launcher-level blocking of prohibited content. An unsigned or upstream-signed CSLOL copy **cannot** be approved for public redistribution by this build workflow.
- PSM's existing unowned-skin carrier flow requires a separate content policy review. Keeping source behavior unchanged for test purposes is not a licensing approval.
- `Get-AuthenticodeSignature` reporting `Valid` alone does not prove the issuing CA meets all upstream requirements; trusted publisher identity/chain must be reviewed before publication.
- Preserve the original working signed private QA installer and original LTK binaries; do not upload or overwrite them.

## October 30 preflight evidence and corrected certificate gate

The maintainer's installed-preparation preflight passed 8/8 packaging contract tests and found all four components. Observed values:

| Component | SHA-256 | Signature |
| --- | --- | --- |
| `mod-tools.exe` | `25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44` | Valid |
| `cslol-dll.dll` | `4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90` | Valid; third-party certificate |
| `ltk_patcher_host.exe` | `5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9` | NotSigned; previously failed hook |
| `ltk_patcher_dll.dll` | `B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29` | NotSigned; previously failed hook |

The CSLOL certificate was observed with subject `CN=Daniel Langov, O=Daniel Langov, L=Burgas, S=Burgas, C=BG`, public certificate SHA-256 `1F51EA1346FF54970541227A4A88E9B4B11FB9A0ADB6B17040DC5DB84E905CE9`, and a timestamp. **This is not a PSM publisher-issued signing identity.** The initial builder only detected signers mentioning "League Toolkit" and could have mistaken this `Valid` third-party signature for PSM-owned signing authority.

The corrected local-only builder rejects this exact CSLOL DLL/certificate pair and requires `-ExpectedDistributorCertSha256`, an independently verified **PSM-owned CA-issued signing certificate SHA-256**. A matching fingerprint is necessary, **not** sufficient: verify its public CA trust chain, responsible distributor identity, timestamp, notices, and prohibited-content enforcement separately. The two original upstream-signed LTK fingerprints are also now expressly rejected, as well as the known failed unsigned pair.

**Do not** set the expected distributor certificate hash to the Daniel Langov certificate fingerprint to force a pass. A code-signing certificate isn't a payment/subscription feature, but acquiring a publicly trusted publisher signing certificate generally involves identity verification and possible cost. Free, public software is compatible with a third-party code-signing requirement, though the project cannot claim a fully no-cost *build process* without an alternative rights agreement or authorized backend.

### Before a new builder run

Run the existing source-only signed/unsigned A/B helper from the working original checkout. It validates the working source host/DLL hashes before opening a local QA session and does not replace them. This test is needed because the staged unsigned host/DLL exactly match a known failing installed candidate. If unsigned source fails too, no new installer should be built from those bytes. If unsigned source works, compare installed-only process context and sanitized current-session logs. Either way, do not reproduce the failed public-path candidate.

## October 30 unsigned-source QA result and installed-binary parity follow-up

The maintainer subsequently confirmed **visible non-default skin rendering from the isolated unsigned LTK source tester**, which uses the exact SHA-256-identified unsigned v1.28.1 host and DLL above. This **supersedes the hypothesis that the unsigned pair is universally nonfunctional**. It does not erase the earlier installed candidate's failed hook or prove that a newly packaged installer works.

The previous unsigned-installed failure and working unsigned-source result can coexist. Investigate runtime layout, bundled-component identity and launch context. The historical hash guard in the public-path builder remains a conservative **installed-artifact failure gate**, not proof those bytes fail everywhere.

**Read-only next test:** inspect the currently installed PSM without modifying binaries:

```powershell
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Repo = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File (Join-Path $Repo "scripts\inspect_v105_installed_parity.ps1") -SourceToolsDir (Join-Path $Original "injection\tools") -UnsignedLtkDir (Join-Path $Original "installer\candidates\v1.0.5\release-unsigned-ltk") -InstalledDir "C:\Program Files\Personal Skin Manager" -InstalledIdentity Unknown
```

Set `-InstalledIdentity HistoricalUnsignedFailed` **only if that exact failed installation is still present and independently identified**. If it was replaced by the working private version, leave identity `Unknown` or use `WorkingPrivate`; current fingerprints cannot prove anything about the old failed installation.

The parity report prints hashes, signature status, relative layouts, missing/duplicate components and newest shared-log age only. It does not start League, read raw confidential logs, run patcher binaries or write files. For installed-only failure, examine new-session evidence and Windows launch context without disabling integrity checks.

## October 30 installed binary findings and isolated frozen QA

The latest maintainer Windows parity run passed 18/18 source-level contract tests and found:

- `mod-tools.exe`: source and installed SHA-256 identical (`25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44`)
- `ltk_patcher_host.exe` and `ltk_patcher_dll.dll`: installed copies match the **working source-tested unsigned** QA pair byte-for-byte; they live at `_internal/injection/tools`
- `cslol-dll.dll`: **present in source, missing from installed**
- Installed PSM EXE SHA-256: `ACA442296881CDDA5B94633EE25EBB11F122B627FAF41CAA19ADC0FC8C88A12E` (installer/build provenance unknown)
- Shared Rose log age: 11 minutes; cannot attribute it to an installed process without stronger session identity

The absence of `cslol-dll.dll` is a **confirmed package completeness defect** that the new PyInstaller spec has already addressed. Do not claim it caused the earlier `SetWindowsHookEx` failure: the current LTK `ToolsManager` requires `mod-tools.exe` and the LTK host/DLL, not the CSLOL DLL. This leaves the frozen-versus-source launch context unresolved.

### Local-only intermediate test: PyInstaller freeze without Inno Setup

The next diagnostic artifact is **not** the public installer. It is a frozen PSM directory produced only in the already created **linked test worktree**, using the exact locally reviewed source-tested unsigned LTK pair and existing third-party-signed CSLOL solely for private, on-device debugging. The script does not run the app, install anything into Program Files, register an updater, publish artifacts, sign DLLs, or overwrite the original source runtime.

```powershell
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Test = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
git -C $Test pull --ff-only origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git update failed" }
Set-Location -LiteralPath $Test
python -m unittest tests.test_v105_frozen_parity_private_qa_contract
if ($LASTEXITCODE -ne 0) { throw "Frozen QA contract test failed" }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\build_v105_frozen_parity_private_qa.ps1" 
  -ModToolsFile (Join-Path $Original "injection\tools\mod-tools.exe") 
  -UnsignedLtkDir (Join-Path $Original "installer\candidates\v1.0.5\release-unsigned-ltk") 
  -CslolDir (Join-Path $Original "injection\tools")
```

The script hashes and verifies all four source files **before** any worktree changes, runs targeted source unit tests, builds only PyInstaller (not Inno Setup), then verifies exactly one packaged copy of each binary and saves `installer/candidates/v1.0.5/frozen-parity-private-qa.json` inside the test worktree. The output is `dist/PersonalSkinManager/PersonalSkinManager.exe` **in the worktree only**. An existing `dist` directory or installer makes the script refuse to run rather than overwrite it.

**Strictly local QA:** the generated folder contains a third-party-signed CSLOL DLL. Do **not** upload the frozen folder or EXE, share it with anyone, or use it as a public v1.0.5 release. The public builder's distributor-signing and content restrictions are unchanged.

Once package integrity is verified, determine whether the frozen EXE itself can perform authorized cosmetic rendering without reinstalling the application. Run only one PSM process at a time and avoid uninstalling or reconfiguring the working version, since Pengu Loader and startup state can be shared between PSM instances. If frozen QA works but installed QA fails, focus on Inno/installation context; if frozen QA fails, focus on PyInstaller/resource paths and launched process environment. A successful freeze alone is **not** a gameplay pass.

## October 30 frozen-build verification (maintainer Windows result)

The maintainer ran `build_v105_frozen_parity_private_qa.ps1` in the linked staging worktree. PyInstaller reported build success and the script independently verified all four bundled runtime files against the expected exact SHA-256 values. The frozen application has **not yet been launched/gameplay-tested**. Output details:

- Executable: `dist/PersonalSkinManager/PersonalSkinManager.exe` relative to the disposable test worktree
- Frozen EXE SHA-256: `A7FD93BB20AFAAB387F1529386658DCE05F2A9FEA1E6AB69C6264BAE11D418C3`
- Reporter: four package files verified; `cslol-dll.dll` is present in frozen output, unlike the previously inspected installation
- Next gate: run *this exact EXE* on the Windows test machine, confirm UI starts, check the permissible transformed custom cosmetic actually displays in Practice Tool, and confirm no current-session hook failure; then terminate cleanly and inspect latest sanitized log
- Do not start the existing installed application concurrently. Frozen and installed PSM may share `%LOCALAPPDATA%\Rose`, Pengu Loader activation and other operating-system state. Avoid uninstalling or reconfiguring the working copy. Back up relevant user state before a live test if preservation is essential.
- The frozen QA artifact still includes third-party-signed CSLOL. It is **not** legal-release approved: neither the EXE nor the folder may be uploaded or shared. Publisher CA signing and prohibited-content launcher enforcement remain unresolved.

Interpretation: if this frozen EXE renders a cosmetic visibly in gameplay, the PyInstaller side of the source-to-package gap is likely closed and Inno/installed runtime context becomes the priority. A successful frozen build alone does not prove runtime functionality.

## Frozen EXE does not render: isolated external-process DLL search correction

The first frozen EXE (SHA-256 `A7FD93BB20AFAAB387F1529386658DCE05F2A9FEA1E6AB69C6264BAE11D418C3`) **launched but did not render the selected skin** in the maintainer's local test. This is a failed frozen gameplay QA result, even though all four binary hashes matched their source counterparts.

One **unconfirmed hypothesis** is that the PyInstaller bootloader's Windows `SetDllDirectoryW` configuration is inherited by subprocesses. Official PyInstaller guidance documents this issue when launching external executables from frozen applications: https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html .

The staging branch now uses a narrowly scoped, serialized external-process launcher. During creation of `ltk_patcher_host.exe` and the three `mod-tools.exe` subprocess call sites it temporarily restores standard Windows DLL search behavior and immediately restores PyInstaller's original path. It never changes, signs, replaces or patches the runtime binaries or any Riot/League files. Patch flags and game integrity checks are unchanged. Tests simulate frozen Windows subprocess success/failure and verify restoration of the search path.

### Fresh linked worktree for the second frozen QA build

Because the first linked worktree contains a verified previous build, **do not overwrite it**. The frozen QA builder permits a dedicated `qa/v105-frozen-dllsearch-*` branch in a fresh linked worktree. Obtain the newest staging changes and create an isolated test checkout:

```powershell
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$New = "C:\Users\Van Arquilos\Desktop\PSM-v105-Frozen-DLLSearch-QA"
$Branch = "qa/v105-frozen-dllsearch-rc1"
if (Test-Path -LiteralPath $New) { throw "Test folder exists; do not overwrite it" }
git -C $Original fetch origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git -C $Original worktree add -b $Branch $New origin/release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Cannot create fresh linked worktree" }
Set-Location -LiteralPath $New
python -m unittest tests.test_v105_frozen_external_dll_search tests.test_v105_frozen_parity_private_qa_contract
if ($LASTEXITCODE -ne 0) { throw "Focused tests failed" }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\build_v105_frozen_parity_private_qa.ps1" 
  -ModToolsFile (Join-Path $Original "injection\tools\mod-tools.exe") 
  -UnsignedLtkDir (Join-Path $Original "installer\candidates\v1.0.5\release-unsigned-ltk") 
  -CslolDir (Join-Path $Original "injection\tools")
if ($LASTEXITCODE -ne 0) { throw "Frozen QA rebuild failed" }
```

Before starting this exact EXE, close all other PSM/League/gameplay processes and record `$TestStart = Get-Date` in PowerShell. Execute only the local `dist/PersonalSkinManager/PersonalSkinManager.exe`, test visible permitted custom-cosmetic rendering, then close it. Afterward run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\inspect_v105_frozen_session_logs.ps1" -SinceLocal $TestStart
```

The logs report sanitized event categories only. Shared `%LOCALAPPDATA%\Rose` logs do not conclusively prove process origin, so the gameplay observation and EXE SHA are separately required.

If the second frozen build still fails, use the categorized log evidence to determine whether LTK process startup, hook initialization, overlay creation, WAD redirection, game version, LCU connection or a missing skin selection is the true blocker. Do not bypass signature, LTK host-integrity, anti-cheat or content protections.

**PUBLIC RELEASE REMAINS NO-GO:** The local frozen QA package contains the existing third-party-signed CSLOL DLL and unreviewed launcher content restrictions. Neither existing nor rebuilt frozen QA files may be published or shared.

## October 30 frozen DLL-search patch still fails: isolate launcher versus frozen behavior

The second maintainer-built frozen QA application also **did not render a skin**. Sanitized post-test report since `2026-10-30 22:31:48` showed: LTK startup 2, hook failure 4, overlay ready 4, and no reported host attachment, WAD verification, or redirection. The DLL-search inheritance patch was therefore **not a demonstrated functional fix**.

Important new A/B distinction: the successful source command is `python main.py --dev --debug --logs`, while the two unsuccessful frozen EXEs were launched without `--dev`. In `main/__init__.py`, `--dev` **skips PSM's native launcher**, including its update/hash/skin-sync stage; both paths still call the main application. This could affect launch timing or contents, but is **not** yet an established cause of the hook error.

**Do not rebuild now.** First run the new read-only `scripts/inspect_v105_hook_failure_details.ps1` on the latest failure with `-SinceLocal ([datetime]'2026-10-30 22:31:48')` to extract numeric `SetWindowsHookEx` codes and timestamp-filtered counters without outputting paths, raw logs or mod names.

Then, with all PSM instances closed, run the **exact existing second frozen EXE** in local QA using `--dev --debug --logs`, matching the successful source arguments. Record a fresh `$TestStart = Get-Date` immediately before launch. This must remain local-only; `--dev` skips application launch checks and **must not become the public default**. Test visible non-default custom cosmetic; close app; run `inspect_v105_hook_failure_details.ps1 -SinceLocal $TestStart`.

Decision: If frozen `--dev` works, investigate launcher-related initialization/update/hash sync order without weakening validation. If frozen `--dev` fails, inspect the exact hook error code and compare executable parent/permissions with Python source, subject to vendor integrity requirements. Do not bypass game, OS or vendor hook verification to make the result pass.

## October 30 22:50 frozen --dev test: hook failure persists

The maintainer retried the second frozen QA executable in `--dev --debug --logs` mode and confirmed no visible skin. Timestamp-filtered sanitized log report from 22:50:18: 4 hook-failure matches, 3 numeric `SetWindowsHookEx failed: 0x00000000` entries (22:52:07), 1 uncoded summary failure, 4 overlay-preparation matches, 0 verified DLL initialization, 0 WAD redirections, 0 attached-host matches and 0 launcher-stage matches.

**Conclusion:** skipping the launcher is not a fix; DLL-search restoration alone is not a fix. Do not rebuild the same configuration or interpret 0x00000000 as meaningful Windows `GetLastError`. LeagueToolkit issue #302 shows this hook error also appeared upstream in July 2026 during a Vanguard compatibility regression, but current source success prevents assigning that historical cause to this environment without more evidence.

**Next controlled A/B (same EXE, no rebuild):** Keep the exact frozen QA EXE and its mod-tools component, but set the existing hash-pinned `PSM_LTK_QA_RUNTIME_DIR` process environment override to the original staged unsigned LTK directory already proven to render under Python. Run from an already **elevated PowerShell** so PSM does not relaunch through UAC and discard the environment override. Verify the LTK pair's expected SHA-256, close all PSM and League processes, set process-local override, launch frozen EXE with `--dev --debug --logs`, and immediately restore the PowerShell environment variable after process creation (the child inherits its value). Do not modify or replace the signed source copy. The launcher must not activate an application updater.

If frozen EXE with external source-staged LTK pair renders, the remaining suspect is runtime location or adjacent DLL resolution in `_internal/injection/tools`. If it still fails, compare parent process elevation/environment and application-specific launch context with Python. Neither result justifies bypassing kernel, game or vendor integrity verification.

## October 30 23:00 external unsigned LTK directory QA: no injection evidence

The maintainer launched the same frozen QA EXE from an elevated PowerShell session, using a process-local `PSM_LTK_QA_RUNTIME_DIR` override pointing at the hash-verified unsigned source-tested pair. Report start: `2026-10-30 23:00:02`; one shared Rose log was modified but the old diagnostic showed **zero** hook failures, host verification errors, LTK initialization, WAD redirection, host attachment, overlay preparation, and launcher activity.

**Do not mark this as a pass.** No record shows a completed Practice Tool match, active skin selection, or even that the frozen PSM reached its injection trigger during this test. The absence of hook errors is uninterpretable without positive logged runtime activity. The tool cannot attribute shared Rose logs conclusively to this frozen process.

`scripts/inspect_v105_hook_failure_details.ps1` is now extended to report timestamped lines and high-level application startup, WebSocket/LCU connection, gameflow/loadout and selected-skin injection triggers in addition to LTK/hook events. Its regression tests include the zero-activity case. Re-run it with `-SinceLocal ([datetime]'2026-10-30 23:00:02')` after pulling updated staging branch. This reads the existing logs without another game test.

Before the next gameplay test, compare the actual running `Win32_Process.ExecutablePath` with the intended QA EXE *as a boolean only*; do not publish paths, raw process command lines, tokens or shared user logs. If no candidate app is running or no gameflow was recorded, reproduce a full authorized Practice Tool test with the same locally reviewed executable, selecting a non-default permitted cosmetic. If app, client and trigger activity appear but LTK is absent, investigate trigger-to-start transitions. No rebuild, publication, Windows hook changes, signature bypass or game integrity weakening should follow from zero evidence.

## October 30 23:00 source-location override: frozen executable confirmed, injection not observed

Follow-up verified **6/6 diagnostic contract tests** and one running `PersonalSkinManager.exe` process matching the exact frozen QA EXE path; no other PSM process was running. The shared log contains 64 timestamped lines between 23:00:03 and 23:03:54, including app init (4), generic ready (2), and LCU/client mentions (2), but **zero gameflow/loadout, selected-skin injection, scanner startup, hook failure, WAD redirection or attachment**. Therefore the external unsigned LTK directory test **does not yet demonstrate a runtime pass or failure**. The process ran; no game-session injection was recorded.

The updated diagnostic separates exact WebSocket-connected readiness from generic `System ready`/`LCU client initialized` markers. Pull staging before rechecking the same session; do not mistake generic LCU activity for a connected client.

Next required user-visible test (no rebuild, no parallel PSM): with the **same frozen QA process that inherited the unsigned LTK-directory override**, record a fresh `$TestStart = Get-Date`, open League Practice Tool from the client, choose a permitted non-default cosmetic using PSM and actually enter the game. Run the sanitized hook-details script against that timestamp. If client connection/skin selection remains absent after a match, diagnose LCU/Pengu startup; if scanner starts and hook fails, resume hook-context analysis with the selected LTK directory and process identity. Do not modify vendor DLLs or bypass game integrity checks.

## First: inspect the current Windows inputs

On the working repository checkout of this staging branch (or a linked worktree with this branch), run:

```powershell
python -m unittest tests.test_v105_public_installer_staging_contract
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\preflight_v105_public_candidate.ps1" `
  -LtkDir "C:\path\to\separately-staged-LTK" `
  -CslolDir "C:\path\to\distributor-signed-CSLOL" `
  -ExpectedDistributorCertSha256 "64_CHARACTER_PSM_PUBLISHER_CERTIFICATE_SHA256" `
  -ModToolsFile "C:\path\to\working-original-repo\injection\tools\mod-tools.exe"
```

The preflight neither signs nor modifies files. A linked worktree normally does not contain the original untracked runtime files, so pass `-ModToolsFile` pointing to the existing audited source `mod-tools.exe` rather than copying it into the worktree. The preflight prints the public CSLOL certificate subject and SHA-256 fingerprint, but a `Valid` signature does not prove the certificate belongs to the PSM distributor. If it flags the historically failed installed hashes, **do not assume the unsigned source is broken**: the maintainer has confirmed visible skin rendering in source QA. Compare installed paths and binaries using `scripts/inspect_v105_installed_parity.ps1`; do not recreate the same installed release candidate without an explained change.

## Only once compliant, compatible inputs are available: make an isolated test installer

The project already contains the working private source checkout. Do not branch-switch it or run a build against it. Use a **fresh linked worktree**:

```powershell
$SourceRepo = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$BuildRepo = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
if (Test-Path -LiteralPath $BuildRepo) { throw "Build worktree exists; do not overwrite" }
git -C $SourceRepo fetch origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git -C $SourceRepo show-ref --quiet --verify refs/heads/release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) {
    git -C $SourceRepo branch release/v105-public-installer-staging origin/release/v105-public-installer-staging
    if ($LASTEXITCODE -ne 0) { throw "Cannot create local release staging branch" }
}
git -C $SourceRepo worktree add $BuildRepo release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Cannot create isolated build worktree" }
```

In the **fresh linked worktree**, with PSM/League/gameplay and patcher closed:

```powershell
Set-Location -LiteralPath "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\build_v105_public_path_local_test.ps1" `
  -ModToolsFile (Join-Path $Original "injection\tools\mod-tools.exe") `
  -LtkDir "C:\path\to\separately-staged-LTK" `
  -CslolDir "C:\path\to\distributor-signed-CSLOL" `
  -ExpectedDistributorCertSha256 "64_CHARACTER_PSM_PUBLISHER_CERTIFICATE_SHA256"
```

The builder rejects missing inputs, the known failed LTK pair, unsigned/non-timestamped CSLOL and upstream-signed patcher/CSLOL, plus reused worktree outputs. It tests source packaging, builds PyInstaller/Inno only in the linked worktree, checks all four bundled-file SHA-256 values, and records a local provenance manifest. The output is:

`installer/candidates/v1.0.5/PersonalSkinManager_v1.0.5_PUBLIC-PATH-LOCAL-TEST.exe`

**Local test only. Do not upload.** A successful build proves packaging, not in-game compatibility, publisher CA validation, or content restrictions.

## Installed candidate QA

Test the **exact** installer digest, never a renamed/rebuilt alternative:

- Clean install into a separate test environment; verify all four runtime files, LCU/WebSocket, Pengu activation and absence of fresh runtime errors.
- With authorized cosmetic content, verify visible skin rendering in Practice Tool; overlay-ready or DLL attach alone is not sufficient.
- Verify actual skin rendering in Swiftplay, reconnect, and a consecutive second match.
- Re-run runtime fingerprint checks and compare new-session game logs. Do not treat stale `%LOCALAPPDATA%\Rose` diagnostics as current proof.
- Clean uninstall/reinstall and re-hash the installer. Investigate any antivirus flag rather than disabling protections.

## Publication gate (later, separate action)

Do not run `publish_v105_prerelease.ps1` as a substitute for compliance review; the existing legacy publisher does **not** validate the new CSLOL addendum end-to-end or the new public-path manifest. We must first record successful *installed* QA, verified public CA certificate/CSLOL DLL hash and timestamp, effective prohibited-content blocking, upstream notices, approved release notes, and explicit owner approval. Keep the signed stable updater manifest unchanged.
