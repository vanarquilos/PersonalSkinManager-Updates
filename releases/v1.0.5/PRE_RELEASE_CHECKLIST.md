# Personal Skin Manager v1.0.5 — release readiness checklist

**Prepared:** 2026-10-22. **Status: NOT RELEASE-READY.** The current public installer remains v1.0.4 (community-test pre-release). No 1.0.5 installer has been built or verified.

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
