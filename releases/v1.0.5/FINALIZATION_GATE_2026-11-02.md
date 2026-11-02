# PSM v1.0.5 — Release candidate finalization gate
**Reviewed:** 2026-11-02 (Asia/Manila)
**Branch:** `rebuild/v1.0.5-rose-compatible`
**PR:** https://github.com/vanarquilos/PersonalSkinManager-Updates/pull/19
**Decision:** **NO-GO for public release**; source-side private QA is ready for Windows execution.

## Frozen scope

- Rebuild remains standalone Personal Skin Manager, with Alban1911/Rose-style mod overlay creation using reviewed `mod-tools.exe`.
- The PSM-authored `cslol-dll.dll` **inert export stub** supports the overlay builder. It is not the game hook; it does not render skins.
- The official LeagueToolkit patcher host/DLL must be obtained separately from an authorized source, verified, locally provisioned, and not redistributed with an upstream publisher signature.
- Strict source/version controls, no runtime EOL edits, no safety-disable flags, and no interference with Riot/Vanguard protections.
- Source and frozen EXE launch at **normal user** integrity; installation/provisioning may require admin, but the installer must never automatically run the PSM app elevated.
- The current source branch includes the MSVC vcvars64.bat quoted-path fix, SHA-pinned private worktree builder, original rollback protection and conservative uninstall.
- Public manifest or stable update promotion remains disabled; do not merge PR #19 to public/stable without all gates.

## Exact release gates

| Gate | Requirement | Current result |
| --- | --- | --- |
| G1 Version/packaging | PSM and Inno both 1.0.5, deterministic private build manifest and frozen EXE SHA-256 | Implemented, Windows execution not confirmed |
| G2 MSVC | Compile inert stub and verify eight real PE exports in Windows x64 | Source fix committed; actual run not confirmed |
| G3 Private EXE | PyInstaller output has exactly one reviewed mod-tools and one PSM-owned inert stub, and **zero** bundled LTK host/DLL | Build script implements checks; actual output not confirmed |
| G4 Current vendor runtime | Matched official LTK host and DLL, verifiable provenance, protocol, acceptable embedded cutoff relative to installed League | **BLOCKED** |
| G5 In-game function | In a permitted Practice Tool game, selected custom skin visibly renders and log confirms overlay/WAD redirection | **NOT TESTED on compatible runtime** |
| G6 Windows install/upgrade | Clean install, source/frozen paths, standard-user startup, legacy scheduled-task review, preserving user-supplied data on upgrade/uninstall | Pending |
| G7 CI | GitHub Actions source tests and Windows MSVC ABI jobs execute and pass (not zero-step failure) | **BLOCKED: runners fail before setup** |
| G8 Legal/security | Review actual patcher license, provenance/Authenticode, notices and distribution rights; do not ship vendor signature without permission | Pending |

All gates are required for a public skin-ready v1.0.5. Passing the cutoff in G4 does **not** prove the vendor's host verification accepts PSM or that skins render (G5). Source-only readiness is not feature completion.

## Latest vendor status

- Official LeagueToolkit manager release **v1.32.2 (Nov 1, 2026)**. Its 1.32.1 notes say the patcher DLL is now downloaded rather than bundled; this is not confirmation of a patcher compatible with the user's League executable. Source: https://github.com/LeagueToolkit/ltk-manager/releases
- The matching League hotfix issue **#976** remains **open on November 2**, with no verified compatibility resolution: https://github.com/LeagueToolkit/ltk-manager/issues/976
- The user's League executable had PE build `2026-10-30T19:07:32Z`. Seven previously inventoried local LTK pairs expire before that build.
- Upstream's official delivery service requires an authenticated/attested client and minisign-verified manifest. Do not scrape tokens, mimic manager identity, invent signed links or bypass cutoff logic.

## The next Windows QA session

Original rollback checkout: `C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates`, branch `fix/v1.0.5-rose-local-rollback`. Do not checkout/reset this directory.

Existing isolated attempted build: `C:\Users\Van Arquilos\Desktop\PSM-v105-Rose-Rebuild-20261031-132306`.

1. Close PSM, League gameplay and LTK host. With Windows PowerShell, fetch only the rebuild branch into `origin/rebuild/v1.0.5-rose-compatible`.
2. Run `scripts/finish_v105_rose_private_qa.ps1` copied from that remote branch to `%TEMP%`. It verifies the isolated worktree is clean, validates the mod-tools SHA, resumes the **exact** previously failed empty-stub state, runs tests and builds the frozen EXE. It **refuses** ambiguous partial output instead of deleting files.
3. If the original failed worktree is not safely resumable, create a **new** linked `qa/v105-rose-*` worktree via `scripts/create_v105_rose_rebuild_worktree.ps1` and build there, retaining the original and the failed QA directory.
4. Run the read-only release report (exit code 0 only with `--report-only`):
   ```powershell
   python scripts/report_v105_release_gates.py --qa-root "." --league-dir "C:\Riot Games\League of Legends" --report-only
   ```
   To inspect a user-supplied **candidate** DLL pair, add `--ltk-dir "D:\YourOfficialLTKPair"`; a good timestamp alone is not permission to release.
5. Independently confirm official vendor provenance and actual visible Practice Tool rendering. Record the exact game build, patcher DLL SHA-256/verified manifest, PSM EXE SHA-256, test timestamp, logs, skin selected and tester observation in the private QA report. Do not include account secrets, install tokens or private payment data.
6. After all gates pass, compile the **private** Inno installer for clean Windows install/upgrade/uninstall tests. Only then consider a public release after license review.

## GitHub Actions blockage

Current Actions jobs, including a minimal Ubuntu `echo` step, show failure with `steps=null` before any runner step executes. It is not evidence of failing PSM tests. Inspect the run banner and GitHub billing, spending limits and repository Actions permissions/runner availability. A run that fails before job setup is **not a pass** and is **not fixable by deleting PSM tests**.

## Engineering stop condition

If a new official delivered DLL still refuses the League build or rejects PSM's host/protocol, stop the release; do not strip signatures, alter game-build cutoff checks, request disabled enforcement or silently fall back to expired native CSLOL injection.

**Public v1.0.5 becomes GO only after all eight gates have documented passing evidence.**
