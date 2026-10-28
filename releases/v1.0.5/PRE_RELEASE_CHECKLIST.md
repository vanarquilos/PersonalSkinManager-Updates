# Personal Skin Manager v1.0.5 — release readiness checklist

**Prepared:** 2026-10-22. **Updated:** 2026-10-29. **Status: PRIVATE SOURCE-QA CANDIDATE, NOT RELEASE-READY.** The current public installer remains v1.0.4 (community-test pre-release). A local v1.0.5 TEST installer was built on 2026-10-27 but did not render the selected skin; it is not approved for distribution. Current debugging proceeds from Python source without rebuilding.

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
