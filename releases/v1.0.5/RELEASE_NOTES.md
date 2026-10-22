# Personal Skin Manager v1.0.5 — Test Candidate

**Status: unreleased / Windows testing required.** Do not upload this text as an official stable release until the release checklist is satisfied.

## What changed since v1.0.4

- Corrected League Client PUT retries after a client restart: the retry now targets the refreshed connection URL and port.
- Fixed game-monitor handling when a League process exits between discovery and suspension; the monitor continues watching for the actual game.
- Added regression tests for these two failure modes and included them in the existing source-test and live-QA commands.
- Added a read-only audit of the trusted local runtime files (file size, SHA-256), installed League build timestamp, and detectable LTK DLL cutoff.
- Added a local-only Windows installer build workflow that names the candidate `PersonalSkinManager_Setup_v1.0.5-TEST.exe`, preserves the previous local installer in a backup folder, and records the new build's exact SHA-256, size and source commit.

## Source hardening after failed Windows test

- Fixed PSM diagnostics dropping the `LTK_PATCHER_EOL`, `LTK_PATCHER_MISSING`, and `INJECTION_RUNTIME_UNAVAILABLE` error codes.
- Injection failures now identify an unsupported LTK runtime without misleadingly reporting a missing League game directory.
- The local test build audit now rejects the exact LTK host/DLL pair previously observed in the failed v1.0.5 League 26.21 test, preventing accidental repackaging of that failing combination.
- Added runtime failure-reporting and build-audit regression tests.

**Not yet fixed:** Applying skins on League 26.21 still requires legitimate, protocol-compatible LTK runtime binaries that have not been supplied or verified. No security or overlay compatibility checks were bypassed.

## Compatibility with patch 26.21

League 26.21 changed skin/material data formats. LTK upstream published fixes in v1.29.1 and v1.30.1 and evolved host protocol support. **Those LTK Manager releases are not drop-in PSM runtime binaries.** The PSM source repository does not include the local third-party runtime trio, and we have not established that the files on the Windows build machine support these changes.

Do not weaken overlay verification or force an unsupported patcher to run. Identify a legitimate compatible host/DLL pair, check licenses, and verify it with Practice Tool before publishing a release.

## Windows tester instructions

1. Fetch the GitHub branch `fix/v1.0.5-pre-release-hardening`.
2. Confirm the trusted runtime files already exist in `injection/tools/`; do not manually swap in unrelated LTK Manager installers.
3. Run `scripts/prepare_v1_0_5_test.ps1` and check the local runtime report.
4. Install the locally produced **TEST** installer on the tester's own Windows PC only.
5. Check PSM version 1.0.5; start with Practice Tool, then Swiftplay in-game selection, then reconnect/second match, and validate error cleanup.
6. Keep the test report and PSM logs. Sanitize personal paths, account/session tokens and any League authentication credentials before sharing.

See [PRE_RELEASE_CHECKLIST.md](PRE_RELEASE_CHECKLIST.md) for exact release gates.

## Distribution boundary

- **Current public build:** v1.0.4 community pre-release (untouched).
- **v1.0.5:** local test candidate only.
- **In-app stable updater:** remains separately signed and should not be modified without access to its existing signing keys.
- **Feedback:** use GitHub Issues if the PSM website is unavailable.

The final installer size, SHA-256, tested commit and known issues must be recorded after an actual Windows build, not copied from v1.0.4.
