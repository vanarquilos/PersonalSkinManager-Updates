## October 30, 11:07 PH — installed client running, live LCU REST succeeds; startup finalization

The user supplied a second read-only diagnostic generated **2026-10-30 11:07:53 +08:00**:
- League client processes: **8**; League game processes: **0** (no gameplay active).
- Installed PersonalSkinManager process active: **yes**.
- Standard League installation, game executable, and LCU lockfile: **present**.
- Live local LCU REST API returned **HTTP 200** using the existing local lockfile (no credentials exposed).
- The diagnostic's `PSM LCU discovery import: unavailable (ModuleNotFoundError)` occurred in **external Python diagnostic**, not inside the frozen PSM; direct-script execution did not reliably put the repository root on Python's import path.
- The most recent shared PSM log was **115 minutes old**. Earlier LCU/WebSocket/Pengu counts cannot be attributed to the new installed session. A process being active or having a shared log file with an older mtime does not establish a current WebSocket connection.

**Engineering finalization of this stage (source only, awaiting Windows QA):**
1. Standalone diagnostic now adds repository root to `sys.path`, reports the actual missing module name if imports still fail, and differentiates source-import availability from frozen-app status.
2. Diagnostic can probe an authenticated local LCU WebSocket handshake without sending game commands, and reports only handshake success/failure category, never tokens, passwords, account data or raw paths. LCU REST HTTP 200 remains separate evidence.
3. `main/__init__.py` no longer blocks its main UI indefinitely on `while not t_ws.connection.is_connected`. A daemon worker uses `main/core/client_startup_gate.py` to wait for the **actual** WebSocket before starting Pengu/injection setup, emitting a warning/diagnostic on prolonged waits; shutdown is respected, and an exited WebSocket worker is explicitly reported.
4. Added isolated unit tests for WebSocket readiness/delayed connection, shutdown, worker death, runtime gating and diagnostic imports; wired these to local release builder and CI source checks.
5. LTK source tester remains untouched, and previously failed installed/PyInstaller candidate is not approved. **No newly rebuilt v1.0.5 Windows package was tested or released** as part of these source changes.

**Final release gates:** Run updated source unit tests and diagnostic with the full League client active. A successful standalone WebSocket handshake does not prove PSM integration. Build a fresh asInvoker Windows RC only after tests pass; validate that exact installed candidate detects League, activates supported Pengu integration, renders a non-default skin in Practice Tool and Swiftplay, and works in a consecutive match. Keep v1.0.5 as draft until all are verified.

## October 30 10:45 PH — received live-client diagnostics

The user supplied `PSM-v1.0.5-league-connection.txt`, generated **2026-10-30 10:45:40 +08:00**. It reports **8 League client process instances**, zero game processes (expected if not in a match), **0 inaccessible client executable paths**, and **present** `LeagueClient.exe`, game EXE, and lockfile in a standard Riot installation directory. Thus a missing client installation or OS-denied process-path inspection is **not evidenced** by this report.

The newest shared PSM log was **93 minutes old**. Counts `LCU connected=6`, `WebSocket connected=4`, `WebSocket disconnected=2`, `Pengu initial status unknown=1`, and `Pengu activation failed=0` represent historical log text only; none can reliably establish the current installed-app connection state. The diagnostic did not prove PSM was running when executed, and it did not probe the live LCU endpoint.

Extended `scripts/diagnose_v105_league_connection.py` with read-only and sanitized:
- Is the **installed** PersonalSkinManager process running (count + executable identity only, no paths printed)?
- Was the newest shared PSM log modified after that installed process started?
- Can PSM's own Python lockfile finder import and locate its expected file?
- Is the local LCU `/lol-gameflow/v1/gameflow-phase` endpoint reachable using credentials read **locally** from the lockfile? Only HTTP status or sanitized exception class is printed, never authentication secrets, player identity, endpoints, or response body.
- Added unit fixtures and release/CI test wiring.

**Next:** Have user open and log into full League client, launch installed PSM, leave both running, and execute the updated diagnostic. Do not rebuild or alter Pengu/anti-cheat merely from a stale historical status marker. A failed LCU probe, absent PSM process, or live LCU success with Pengu failure require different follow-up fixes. Public release remains blocked.

## October 30 — installed candidate cannot detect League Client (open issue)

The maintainer reports that the newly installed candidate does not detect League. This is a **separate prerequisite failure from LTK skin overlay rendering** and needs isolated LCU/client startup QA. Existing installed EXE does not contain new source fixes.

Code inspection found three concrete weak points:
- `GameDetector` returned no League directories when `psutil` could not retrieve `LeagueClient.exe`'s executable path, unless a fully valid path pair was already saved.
- LCU lockfile discovery did not reuse PSM's previously saved client directory. This matters for custom-drive installations where process EXE inspection is denied.
- `_setup_pengu_and_injection()` previously ignored the boolean result from `pengu_loader.activate_on_start()`. Thus LCU connection could succeed while client integration fails with no explicit PSM issue.

Implemented a conservative on-disk fallback requiring **both** `LeagueClient.exe` and `Game/League of Legends.exe`, saved-client lockfile lookup without dumping credentials, and a PSM issue when Pengu cannot activate. These source changes are **not a verified repair** for the already installed candidate.

**Do not rebuild yet:** Open the actual League client via Riot, leave it open, and run `python scripts/diagnose_v105_league_connection.py` from the checked-out branch. Its report distinguishes missing process, inaccessible process EXE, absent lockfile, LCU WebSocket failure and Pengu activation issues. It contains no lockfile contents or authentication tokens. If the report shows League/LCU connected but Pengu failed, diagnose Pengu's installation permissions separately without disabling OS/game security. Only then build a newly reviewed RC; installation and gameplay tests remain pending.

## October 30 — investigate default skin in newly installed PSM

**Release remains blocked.** Signed and unsigned LTK pairs worked in source tests, but the installed application continues to show the default skin. A code review found `ensure_admin_rights()` in `main/core/initialization.py`, called by both source and packaged runs; therefore, the prior claim that the source tester necessarily ran without elevation was unsupported. The `asInvoker` packaged manifest also did not prevent this runtime relaunch. Implicit startup elevation has been removed in source, with a regression test and privilege-category log.

Next steps:
- [ ] Before building again, run the read-only `scripts/compare_v105_portable_and_installed.ps1` to prove the **actual** portable and installed EXE hashes and paired LTK files.
- [ ] Manually test the **existing frozen portable EXE** from `dist/PersonalSkinManager` with a non-default skin, note any UAC prompt, and collect the latest sanitized portable-session report.
- [ ] If portable works but installed fails, investigate install-directory resolution/permissions and leftover files; if both fail, investigate frozen startup and LTK lifecycle.
- [ ] Rebuild after a root-cause-supported change, rerun the source tester, and independently QA the installed candidate in Practice Tool, Swiftplay, and a second match.

**Do not remove/sign/replace the working LTK files or announce v1.0.5 as released before installed gameplay is verified.**

## October 30, 2026 — unsigned source passed; new asInvoker RC pending

- [x] Original signed source runtime: non-default skin rendered
- [x] Isolated original-signature-removed v1.28.1 host/DLL: maintainer reports non-default skin rendered **from source**
- [x] Identified prior installed EXE as requiring administrator elevation (`uac_admin=True`) and post-install `Verb: runas`, unlike the source session
- [x] Switched new packaged EXE to `asInvoker`, post-install run to original user and added a fail-closed compiled-manifest audit
- [x] Builder only packages staged unsigned copies and keeps developer's signed source files unchanged
- [ ] Build new asInvoker installer candidate on Windows, verify compiled EXE manifest, staged host/DLL hashes, installer SHA-256 and reviewed source commit
- [ ] **Install that new candidate**; confirm a non-default skin in Practice Tool, Swiftplay and a consecutive second match
- [ ] Record actual installed-gameplay results, then publish GitHub pre-release using explicit truthful QA flags

The old elevated installer and its documented `SetWindowsHookEx` failure remain **NO-GO**. Launch-context parity is a plausible fix, not yet proven. Do not release based solely on the source A/B pass.

## Final release decision — October 29, 2026

**NO-GO for the existing v1.0.5 unsigned installer.** Installed runtime fingerprints are host `5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9` and DLL `B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29`. In the October 29 installed game test, overlay construction succeeded, but the LTK host failed with `hook install failed` and `SetWindowsHookEx failed: 0x00000000` at 21:11:20; selected skin was not applied.

The original signed v1.28.1 source tester has separate hashes and was reported working. **Do not touch, restore, overwrite, or package that working local pair.** Removing a digital signature alters bytes; correlation is not yet proof that the signature removal caused the hook failure. The LeagueToolkit license prevents redistributing official upstream-signed binaries under PSM without permission.

- [x] Confirm installed/default-skin failure and isolate the hook-installation stage using sanitized log evidence
- [x] Record exact known-bad unsigned host/DLL fingerprints
- [x] Add a fail-closed publisher block for those fingerprints regardless of manually supplied QA flags
- [ ] Obtain a compatible, distributable runtime consistent with the upstream license and platform security
- [ ] Build a new release candidate using separate distribution copies, install it, and demonstrate non-default skin rendering in Practice Tool and Swiftplay, plus a second match
- [ ] Only then publish a pre-release and verify the GitHub asset hash

**Existing v1.0.4 GitHub releases and stable manifest stay unchanged.**

# Personal Skin Manager v1.0.5 — release readiness checklist

**Prepared:** 2026-10-22. **Updated:** 2026-10-29. **Status: RELEASE-CANDIDATE PREPARATION, NOT YET PUBLISHED.** The current public installer remains v1.0.4 (community-test pre-release). A local v1.0.5 TEST installer was built on 2026-10-27 but did not render the selected skin; it is not approved for distribution. Current debugging proceeds from Python source without rebuilding.

## Scope and evidence

- Riot shipped League patch **26.21** on 2026-10-21.
- LTK Manager **v1.29.1** (Oct 21) fixed "Invalid property kind 178" overlay verification for 8-byte `StaticMaterialDef.name` hashes.
- LTK Manager **v1.30.1** (Oct 22) fixed repair of older mods with the new hash type.
- Current LTK Manager source now records **bundled host protocol 3**; that is a protocol compatibility warning, **not proof** that PSM's local host/DLL pair needs replacing.
- PSM v1.0.4 includes the early scanner startup and overlay-directory preservation fixes, but its proprietary/third-party runtime trio is **untracked** and cannot be inspected from public GitHub.
- New PSM source fixes under review: LCU PUT retry uses the refreshed client port; game monitor continues after a vanished process.

## Failed local test — 2026-10-22

The maintainer ran the v1.0.5 candidate and reported: **no skin appeared in-game**. The 2026-10-22 diagnostic summary confirms **3 matches for unsupported/expired LTK runtime** and **0 recorded injection/attachment, overlay success, or material parsing errors**. The local mod-tools, host, and DLL hashes were collected. The exact installed League build and embedded DLL cutoff comparison is still needed; the root cause is strongly suspected but not conclusively established.

Top suspect: the locally bundled LTK patcher predates League 26.21's material-data format change. LTK Manager v1.29.1 corrected overlay verification failure (invalid property kind 178), followed by v1.30.1 mod repair fixes. These manager releases are **not** interchangeable with PSM's patcher host/DLL binaries.

Before any more gameplay attempts, from the candidate branch run `powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\diagnose_no_skin_v105.ps1` again. The updated script includes the League game-build timestamp and DLL cutoff timestamp **from the existing local runtime-audit.json**, while withholding local paths and raw logs. Compare the two timestamps before deciding whether the runtime is genuinely expired. The script does not change League, PSM, or antivirus settings.

Do **not** merge, publish, or bypass security/overlay validation until the no-skin failure is understood and retested.

## October 22 source hardening (after the diagnostic)

- The locally audited LTK host/DLL pair from the failed v1.0.5 test is now rejected **by the v1.0.5 candidate build audit**. This is a test-proven compatibility block, not a malware verdict or claim that those files fail on every game build.
- `ToolsManager` now records an actionable unsupported-runtime or missing-runtime issue instead of simply failing initialization silently.
- Injection attempts no longer describe every runtime failure as a missing League installation.
- Automated tests now cover diagnostic visibility and refusing the previously failed host/DLL pair.
- **The actual no-skin compatibility problem is not yet repaired.** The vendor-controlled, signed LTK patcher distribution currently requires an eligible official manager and a matching host protocol. PSM cannot assume those DLLs are publicly redistributable or compatible with its older host.
- Do not build or publish v1.0.5 until a legitimate, compatible runtime pair has been obtained, audited, and successfully tested. Do not bypass the build gate or patcher verification.

## Upstream LTK v1.30.1 candidate available for PRIVATE test

The LTK v1.30.1 Git tag points to commit `044e6b5fc2dfe78d92dc5a5ada3e0f57f32860f6`. Its bundled patcher DLL embeds **2026-10-28T23:06:41Z** as the cutoff, later than the maintainer's installed League executable timestamp **2026-10-16T22:15:09Z**. This is **cutoff compatibility only**, not proof of injection success.

- [x] Identified upstream source tag, commit, exact host/DLL Git blob IDs, and the separate LTK Patcher License.
- [x] Added `scripts/stage_ltk_v105_test.ps1`: download only from pinned official GitHub commit, verify each file size and Git blob ID, back up previous host/DLL, audit cutoff, swap both as a pair for **local private testing**.
- [x] On Windows stage the pinned runtime, record runtime audit, and build a **private TEST** candidate (2026-10-27); installation/build verification alone did not fix in-game skin rendering.
- [ ] In Practice Tool verify actual skin rendering on League 26.21, confirm no host protocol errors; then test Swiftplay gameplay and reconnect.
- [ ] For *any public redistribution*, remove League Toolkit's official code signatures from both binaries (or obtain written permission), optionally sign with PSM's own certificate, and repeat final integrity and Windows QA. Do NOT upload the signed official upstream binaries in a PSM installer.

The initial pair's 2026-10-04 cutoff was genuinely older than League's executable. The original block remains in place for that known-failing pair. The new upstream candidate does not bypass any checks.

## October 27-28: private Windows diagnostic status and source update

- [x] Maintainer staged pinned official v1.30.1 host/DLL locally; verified sizes, Git blobs and signatures. League PE build: 2026-10-16T22:15:09Z; DLL cutoff: 2026-10-28T23:06:41Z (**game-build timestamp comparison**, not wall-clock expiration).
- [x] Built local v1.0.5-TEST installer, and confirmed source/built/installed host and DLL SHA-256 matched. **No successful skin rendering** from installer or directly launched Python source.
- [x] Latest debug report: log level DEBUG, LTK DLL attached, overlay initialized, 20 DLL events, 1/1 WAD header rebased; **no WAD redirection observed**, verified-WAD verdict missing. Selected archive contains two files, one WAD. These findings are not proof of archive compatibility.
- [x] Compared `injection` implementation with Rose `main` at `12a0d46b`, particularly the client-phase/game-process host-lifetime guard; ported the guard to PSM. The host now remains active if the game process is still running after an early client-phase transition.
- [x] Changed PSM to report missing WAD redirection as **not confirmed skin application** instead of silently reporting success; this does not bypass integrity checks.
- [x] Added local-only LTK DEBUG logging, sanitized latest-session diagnostics, read-only WAD archive/payload comparison, and regression tests. Both local live-QA and manually dispatched source-check workflow include the new archive tests.
- [ ] Run the new tests on Windows, confirm the selected WAD path/payload, and verify **a real redirected WAD and visible non-default skin** in Practice Tool.
- [ ] Test Swiftplay, reconnects, runtime provenance/licensing, packaging and in-app update distribution separately.

October 29 archive result: maintainer's earlier source tests passed; selected Aphelios archive contained two files and a 11,990-byte packed `WAD/Aphelios.wad.client` with an RW header. This is a valid Fantome packed WAD path per upstream specification. The first inspector incorrectly expected a full `DATA/...` path and thus reported `null`/missing. The inspection code and tests now recognize packed Fantome aliases and avoid false game-WAD comparison verdicts; updated tests and game rendering have not yet been verified on Windows.

See `releases/v1.0.5/MODSKIN_ROSE_PARITY_REVIEW.md` for source comparison, evidence limits and acceptance criteria. The pull request stays **draft**; no stable manifest or public installer should be updated.

## October 29: Rose/LTK current status and host-verification refusal

- Rose official latest release: [v1.4.9](https://github.com/Alban1911/Rose/releases/tag/1.4.9), published 2026-10-16. Latest main commit: `12a0d46bfc63` (2026-10-22); no later public modskin fix was found as of this review.
- Rose [issue #401](https://github.com/Alban1911/Rose/issues/401) remains open for selected skins failing to appear in League 26.21. [Issue #404](https://github.com/Alban1911/Rose/issues/404) reported `host verification failed, refusing overlay [VRF00000008]` on League 26.21; its closed status is not evidence of a published runtime fix. [LTK issue #896](https://github.com/LeagueToolkit/ltk-manager/issues/896) reports attached DLL but zero redirections with another LTK version.
- [LTK issue #923](https://github.com/LeagueToolkit/ltk-manager/issues/923) explicitly confirms from a LeagueToolkit contributor on 2026-10-22 that the host-verification check is intended to block third-party apps from using the DLL. This is a fundamental third-party integration blocker, not a transient parsing issue; rolling back or patching verification is not an acceptable product release strategy.
- **New release precondition:** Obtain an officially supported/authorized integration or implement/evaluate a legitimately licensed independent backend, without evading integrity or Riot anti-cheat checks. Confirm all product distribution rights (including official signing conditions) in writing where needed.
- LTK Manager's latest release checked: [v1.31.1](https://github.com/LeagueToolkit/ltk-manager/releases/tag/v1.31.1), 2026-10-28. Its release notes do not confirm a fix for PSM's zero-redirection symptom, and its distribution is not automatically a compatible host/DLL pair for PSM.
- New user diagnostic generated 2026-10-29 07:28 +08:00: source DEBUG, game DLL attached, overlay initialized, 20 DLL events, WAD header rebase 1/1, 0 observed redirected WADs, no observed verified-WAD verdict; last state exited. The old report counted one `mkoverlay` error alongside completed overlay runs.
- PSM now reports a vendor `host verification failed, refusing overlay` verdict as a **terminal failure**, with sanitized issue text and no vendor proof/identifiers logged by that branch. No verification bypass was introduced.
- The latest diagnostic script has a narrower builder-error pattern and reports the **last selected-skin builder outcome**, so a previous failed attempt does not override a later successful one. Added offline tests for these reporting contracts to both source QA entry points.
- [ ] Re-run Windows Python tests and the read-only diagnostic on the existing October 29 log to distinguish `succeeded` / `failed` builder outcome from DLL redirection absence.
- [ ] Actual in-game WAD redirection and visible skin rendering remain **unverified/failed**. Do not release, merge, update stable manifest, or distribute official-signed LTK binaries.

## October 29, 07:48 Manila time — verified failure classification

Maintainer reran the **read-only diagnostic** against the same October 29 07:28 PSM log. Updated report confirms:
- Last selected-skin `mkoverlay` outcome: **succeeded**; rebased WAD headers **1/1**; selected Fantome archive contains **2 members**, including **1 packed WAD**.
- DLL attached, **20** DLL events, overlay initialized, host final state `exited`.
- `LTK host verification refused: 1`; verified-WAD verdict **not observed**; WAD redirections **0**. No expired-runtime, late-join, hook, or material-parser error recorded in this session.
- The previous 'overlay builder failed' classification was a false lead: the scanner counted an older/misclassified marker while the last skin build succeeded.
- This is **host verification refusal**, not evidence that Aphelios's packed Fantome format is invalid. Vendor verification is an intended third-party-host restriction per [LeagueToolkit issue #923](https://github.com/LeagueToolkit/ltk-manager/issues/923).
- **Blocker / next action:** obtain an **authorized/supported integration** or choose a lawful independent backend. No further installer or gameplay loops with the currently refused integration; no DLL patch, forced validation bypass, or unsupported downgrade. Obtain new evidence only when the backend is supported.
- Source changes already detect and report this failure; the report predates the latest source detection addition, so no claim is made that the runtime-side error dialog was tested on Windows.
- The PR stays draft and stable `v1.0.4` remains unchanged.

## October 29: Historical v1.28.1 compatibility evaluation (read-only)

Rose community members in [issue #401](https://github.com/Alban1911/Rose/issues/401) report that official LTK Manager v1.28.1 patcher host/DLL pairs worked for them. Rose itself did **not** commit a host-verification fix. That older pair predates the third-party-host restriction but also predates League 26.21's [material-format repair in v1.29.1](https://github.com/LeagueToolkit/ltk-manager/releases/tag/v1.29.1). Neither gameplay compatibility nor authorization follows from a successful prior report.

- [x] Pinned the official v1.28.1 tag's two original Git blobs and file sizes in a new **read-only** auditor `scripts/audit_ltk_v1281_compatibility.py`.
- [x] Added standalone offline tests for the Git object fingerprint, missing files, cutoff and identity mismatch.
- [x] Included those tests in the source QA and manual GitHub checks.
- [ ] On Windows, run the auditor only against separately obtained official binaries and the *current* League Game folder. This does **not** stage or execute the older files.
- [ ] Confirm upstream-approved integration, production game compatibility, licensing and actual visible skin rendering before authorizing a PSM public release.
- [ ] No automatic downgrade, legacy DLL redistribution, bypass of signature/host verification or stable-channel changes are authorized.

## October 29 evening: Rose-reported legacy runtime private source test

After verifying Rose's latest public main (October 22) and latest published release (1.4.9), there is still no new public code fix for the LTK host refusal. Users in Rose [#401](https://github.com/Alban1911/Rose/issues/401) reported working with the original official **LTK v1.28.1** pair, rather than patching the newer DLL.

**Local opt-in implementation committed:**
- `scripts/review_rose_ltk_v1281.ps1`: separately download and verify official historical files against pinned Git blob IDs, then audit the League executable build cutoff.
- `scripts/use_rose_legacy_runtime_local.ps1 -Action Activate`: after successful audit and while League/PSM are closed, make a backup of the existing LTK host/DLL and select the unmodified official historical pair **for private local source QA only**.
- `-Action Restore`: recover the original host/DLL from checksummed backups, with a rollback state file recorded before replacement.
- The existing `scripts/run_live_qa.ps1` warns when the historical pair is active. The installer builder and v1.30.1 stage helper **refuse to run while the legacy test is active**.
- Added offline static regression checks and source-QA wiring. Windows tests have **not** been executed yet.

**No public release approval:** The historical pair predates the League 26.21 material parsing fixes, is not a vendor-supported current integration, and may be incompatible with the game or individual skins. No binary is committed to the repository. Test only in Practice Tool using the source app, inspect the sanitized diagnostic, and restore the original pair afterward. No bypass of newer DLL verification, game security modifications, signed binary redistribution or v1.0.5 public package is part of this change.

## October 29 evening: maintainer source test succeeded; distributable installer pending

The maintainer reports that the legacy v1.28.1 source test is now **working**. This is user-reported gameplay feedback, not an uploaded rendered-skin screenshot, new WAD redirect report, or packaged installer QA record.

We are preparing a *separate* redistributable candidate:
- [x] PyInstaller spec accepts `PSM_RELEASE_LTK_DIR` for only the two patcher host/DLL inputs, keeping `mod-tools.exe` in the reviewed tools directory.
- [x] Added `scripts/build_v105_distribution_candidate.ps1` which audits the original pinned v1.28.1 files, copies them into an ignored staging directory, invokes Windows SDK `signtool remove /s` **on the copies only**, checks that their embedded Authenticode signatures are absent, and builds a local v1.0.5 RC installer.
- [x] The builder verifies that the *actual bundled* host and DLL match the unsigned staging files by SHA-256, checks that private state and signing materials are absent, and creates a release-candidate hash manifest.
- [x] Existing source and tests include release-specific packaging safeguards; `releases/v1.0.5/RELEASE_NOTES_DRAFT.md` contains notes for a future GitHub pre-release.
- [ ] Run Windows source tests and the new candidate builder. Windows SDK SignTool and Inno Setup are required.
- [ ] **Install and gameplay-test the unsigned-binary RC** in Practice Tool, Swiftplay and a second match. A working original signed local pair does not prove that its signature-removed distribution copy works.
- [ ] Confirm installer hash, license notices, version/channel copy, installation/uninstallation, and publish a `v1.0.5` GitHub **pre-release** only after QA.
- [ ] Keep existing GitHub releases and stable updater manifest unchanged until the release is approved.

## October 29 evening: correct regression from forced LTK runtime restore

The previous release workflow instructed the maintainer to use `-Action Restore` before packaging. That restores the pre-test host/DLL pair and can undo the Rose-reported v1.28.1 local working configuration. **This was a release-workflow error, not the disappearance of LTK itself.**

- [x] `scripts/use_rose_legacy_runtime_local.ps1 -Action Status` compares the current live source host/DLL to the pinned original v1.28.1 files by SHA-256, without changing files. `-Action Activate` is idempotent if the tested pair is already selected.
- [x] `scripts/run_live_qa.ps1` verifies that an active private v1.28.1 pair actually matches the pinned files instead of relying on the backup-state marker alone. It no longer urges automatic restore.
- [x] `scripts/build_v105_distribution_candidate.ps1` preserves a working source host/DLL while packaging independently staged unsigned **release-only** copies. It also checks an active test pair's identity before building and requires PSM/League to be closed.
- [x] `scripts/publish_v105_prerelease.ps1` no longer unnecessarily restores the active source runtime; it must still independently verify installed candidate QA and installer provenance.
- [ ] Rerun the source app explicitly after verifying or reactivating the pinned v1.28.1 pair. An existing installed PSM executable uses its **own bundled host/DLL**, not the source checkout's files.
- [ ] If the unsigned packaged RC fails while the original signed source pair works, treat this as a **distribution compatibility blocker**, not a justification to redistribute upstream-signed binaries contrary to the LTK Patcher License.

## P0: Block publishing until ALL are complete

- [ ] Identify the exact locally bundled `mod-tools.exe`, `ltk_patcher_host.exe`, and `ltk_patcher_dll.dll`. Record each filename, byte size, and SHA-256 using `python scripts/audit_runtime_v105.py --game-dir "C:\\Riot Games\\League of Legends\\Game"`. Supply an explicit, correct League Game folder if installed elsewhere.
- [ ] Obtain runtime files only through their legitimate supported distribution paths, verify redistribution terms and provenance, and test host/DLL compatibility. **Do not substitute the LTK Manager installer for its separate patcher binaries.**
- [ ] Verify the patcher's game-build cutoff and run a real **League 26.21** test. A passing cutoff alone cannot establish support for new material hashes.
- [ ] Verify overlay creation/validation for an existing supported skin, a changed skin, and an older compatible custom mod; confirm an unsupported/corrupt mod is rejected safely rather than silently reported as applied.
- [ ] Practice Tool: League launches without hanging, the selected skin renders correctly, no overlay verification failure, and the game resumes if injection fails. Test at least two consecutive games.
- [ ] Swiftplay: lobby selection, selected skin in-game, champion/skin changes, dodge/cancel, and a subsequent match all behave correctly. **Lobby-only verification is insufficient.**
- [ ] Test reconnect/League Client restart while PSM stays open. Confirm in-game and LCU reattachment paths do not leave a game suspended.
- [ ] Run full source tests including new LCU and monitor regression tests, plus the Windows live QA script. Record outcomes for the release.
- [ ] Fresh Windows install + uninstall + reinstall test, including all-in-one packaged tools and previous-version migration. No manual DLL copying should be required of end users.
- [ ] Build an installer from reviewed commit and approved local runtime, capture its SHA-256 and size, then compare the *uploaded* GitHub asset to the built file.
- [ ] Provide a working issue-reporting destination. If `psm.vanarquilos.dev` remains paused, use GitHub Issues as the explicit fallback until the website resumes.

## P1: Must be checked or clearly documented

- [ ] Confirm the local run passes repeated Practice Tool launches on a normal/non-admin user account where supported.
- [ ] Validate chroma/variant selection, owned/default skins, missing selection, and selected skin persistence when champion changes.
- [ ] Validate slow-PC timing: scanning starts before League launch; a failed or timed-out overlay does not create a stuck game process.
- [ ] Verify missing/outdated patcher shows a comprehensible error and does not say "ready" when injection cannot work.
- [ ] Verify crash/error logs include PSM version, League build, selected queue, runtime hashes/versions (if obtainable), stage, and error classification; **never include League authentication secrets**.
- [ ] Check startup, installer, loading and settings UX at 100% and 125–150% display scaling; no unrelated UI redesign in this hotfix.
- [ ] Update `README.md`, `SECURITY.md`, `CHANGELOG.md`, release notes, and website version/download copy only after final verification. Correct old v1.0.2 messages in build scripts.
- [ ] The signed in-app updater is still on **v1.0.1** because its signing-key access is unresolved. Keep it separate: do not silently overwrite/forge a signed manifest. Clearly link to the GitHub Release.
- [ ] Antivirus transparency: publish exact installer hash and instructions to report suspected false positives; do not ask users to disable endpoint protection.

## Deferred unless blocking a core flow

- New cosmetic features, new UI architecture, analytics, party features, large dependency upgrades.
- A generalized automatic LTK binary updater unless the upstream distribution contract, signature verification, fallback, and user consent are fully established.
- Replacing or bypassing security checks to force an unsupported overlay to run.

## Release decision / rollback

**GO** only when P0 is complete with tested Windows evidence. Keep v1.0.4 available until v1.0.5 is validated. If an upstream patcher regression cannot be resolved, publish no installer and inform community testers of the limitation. Do not increment public-release status solely because source tests pass.

**QA evidence to retain privately:** tested commit, Windows build, installed League version, runtime hashes, source-test result, Practice Tool outcome, Swiftplay gameplay outcome, installer hash and byte size, feedback URL, known issues.
