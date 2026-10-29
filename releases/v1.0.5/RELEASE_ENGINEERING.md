# PSM v1.0.5 — Windows pre-release publishing procedure

**Current state:** Source release engineering implemented. The maintainer reports a working legacy-patcher source run, but no installer made from unsigned LTK binaries has been tested or published.

## Requirements

- Windows build machine, Python 3.11+, Git, PyInstaller dependencies, Inno Setup 6.
- Microsoft Windows SDK **SignTool** available on PATH or in the Windows Kits x64 directory. Microsoft documents `signtool remove /s <file>` for complete embedded signature removal.
- GitHub CLI `gh` logged in with release-creation permission, for the final **optional** publish step.
- Audited original LTK Manager **v1.28.1** host/DLL files isolated under `installer/candidates/v1.0.5/audit-only-ltk-v1.28.1`. Obtain them through `scripts/review_rose_ltk_v1281.ps1`; do not commit to Git.
- Reviewed local `injection/tools/mod-tools.exe`; the project build pipeline expects it.

## 1. Preserve or reactivate the working local source runtime

**Do not run `-Action Restore` merely to build a candidate.** That command intentionally reinstalls the earlier host/DLL pair, which previously failed in PSM. The local historical LTK v1.28.1 pair can remain selected while the release process stages **different copies** for distribution.

For the working source-only setup, close PSM and League first, then:

```powershell
Set-Location -LiteralPath "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
git switch fix/v1.0.5-pre-release-hardening
git pull --ff-only origin fix/v1.0.5-pre-release-hardening
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\use_rose_legacy_runtime_local.ps1" -Action Status
```

If the Status command reports `DIFFERENT` for either file, reactivate the pinned original pair (with League and PSM closed):

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\use_rose_legacy_runtime_local.ps1" -Action Activate
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\use_rose_legacy_runtime_local.ps1" -Action Status
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\run_live_qa.ps1" -SkipTests
```

This launches the Python source app against the original tested LTK files. **An already-installed `PersonalSkinManager.exe` includes its own bundled runtime** and is not fixed by changing the source directory. The installed release-candidate version must be tested independently.

## 2. Build the **separate unsigned** release candidate

```powershell
git switch fix/v1.0.5-pre-release-hardening
git pull --ff-only origin fix/v1.0.5-pre-release-hardening
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\build_v105_distribution_candidate.ps1"
```

The builder checks tests and original binary identity; copies the official host/DLL; removes the original LeagueToolkit Authenticode signatures from **isolated copies only**; validates these copies; packages them using `PSM_RELEASE_LTK_DIR`; checks the bundled copies by SHA-256 and signature status; and records an installer hash.

Expected output: `installer/candidates/v1.0.5/PersonalSkinManager_Setup_v1.0.5-RC.exe`, alongside `release-candidate-audit.json`.

The builder **preserves the active working source runtime** and does not publish, modify the signed upstream originals, override game security, or change `stable/manifest.json`. If the build stops, fix the reported failure; do not fall back to distributing the upstream-signed originals.

## 3. Test the **actual installed RC**, not the source checkout

Verify on Windows:
- Clean install / uninstall and reinstall without missing runtime binaries.
- Practice Tool: selected non-default skin renders visibly in game, no new host verification failure.
- Swiftplay: selected skin renders in the actual match (not merely in the lobby).
- Second consecutive match and reconnect; check champion changes and no hanging/resume bug.
- Diagnostics after gameplay and the installer asset SHA-256. Keep any logs sanitized.

The working signed *source* setup is useful evidence but does **not** establish success of the *unsigned distributable* runtime. If the signature-removed host/DLL pair fails in game, do not publish. Record the blocker and revert to source QA.

## 4. Publish the GitHub **pre-release** only after all QA is confirmed

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\publish_v105_prerelease.ps1" `
    -Publish `
    -ConfirmedCleanInstall `
    -ConfirmedPackagedPracticeTool `
    -ConfirmedPackagedSwiftplay `
    -ConfirmedSecondMatch
```

These flags are explicit statements of completed real tests, **not a way to skip them**. The publishing script rejects a missing candidate, a mismatched installer hash/byte size or source commit, an existing GitHub v1.0.5 release, or missing GitHub CLI authentication. It leaves an active local source-test runtime untouched. It creates a GitHub **pre-release** using the verified installer with the established `PersonalSkinManager_Setup.exe` asset name.

Existing v1.0.4 files and the `stable/manifest.json` signed updater remain unchanged. Any future stable-channel promotion must use the separate signed-manifest workflow, not a plaintext edit.

## Source references

- [LTK Patcher License](https://github.com/LeagueToolkit/ltk-manager/blob/main/LTK-PATCHER-LICENSE.md)
- [Microsoft SignTool remove command](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool)
- [Release-candidate checklist](PRE_RELEASE_CHECKLIST.md)
- [Proposed public pre-release notes](GITHUB_PRERELEASE_NOTES.md)
