# PSM v1.0.5 — temporary Rose-style local rollback

**Status:** private source QA only. No public v1.0.5 installer, signature modification, new vendor integration, or game-security changes are approved by this rollback.

## Why this branch exists

The installed v1.0.5 candidate has repeatedly shown default skins and/or failed to detect League, even though earlier original signed and isolated unsigned LTK source tests rendered non-default skins. The current candidate's packaging and LCU/WebSocket changes are unverified in-game. We need a known working **source** baseline before another release attempt.

This branch was forked from `79150ea9fafd99f4665d2d196435301b12345205` (the original signed/unsigned source A/B workflow that the maintainer subsequently reported was working). The separate development branch `fix/v1.0.5-pre-release-hardening` is preserved, not reset or rewritten.

## Exact local recovery procedure

Close installed/source PersonalSkinManager, League gameplay and the LTK host. First check for uncommitted work; do not force checkout, reset or stash automatically.

```powershell
Set-Location -LiteralPath "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
if (@(git status --porcelain --untracked-files=no).Count -gt 0) { throw "Commit or preserve tracked changes before switching branches." }
git fetch origin fix/v1.0.5-rose-local-rollback
if ($LASTEXITCODE -ne 0) { throw "Fetch failed." }
git switch --track origin/fix/v1.0.5-rose-local-rollback
if ($LASTEXITCODE -ne 0) { throw "Branch switch failed." }
python -m unittest tests.test_v105_rose_local_return_contract tests.test_rose_legacy_local_runtime_contract
if ($LASTEXITCODE -ne 0) { throw "Rollback safeguard tests failed." }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\return_to_rose_local_v105.ps1" -Action Prepare
```

If the original signed v1.28.1 host/DLL pair is already active, **Prepare is a no-op** and checks the hashes/signatures. If it differs, the wrapper checks the isolated official pair and calls the existing `use_rose_legacy_runtime_local.ps1 -Action Activate`, which creates a separate verified backup and records restore metadata *before* changing the active local host/DLL. It never rewrites, signs or patches the files. If a prior restore manifest exists with unexpected contents, it fails rather than overwriting the backup.

To start a private source QA session:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\return_to_rose_local_v105.ps1" -Action Run
```

This invokes `run_live_qa.ps1` and `python main.py --dev --debug --logs`, *not* the installed EXE. Open League normally and use Practice Tool to verify a **non-default skin is visible in-game**, not just overlay-ready status.

## How to return to development

Close the source tester and League gameplay first. Switching branches changes source code only. To return to the current development branch:

```powershell
git switch fix/v1.0.5-pre-release-hardening
```

Do **not** automatically run `use_rose_legacy_runtime_local.ps1 -Action Restore`. That command specifically restores the runtime pair backed up before a past activation, and could replace a functioning v1.28.1 source tester. Use it only when intentionally restoring a known previous pair after reviewing its stored backup checksums.

## Safety, compatibility and distribution

The historical official v1.28.1 host/DLL predates newer League 26.21 parser changes. Successful hashes and build timestamps do not guarantee that current gameplay will work. No anti-cheat evasion or Windows hook-integrity bypass is part of this procedure.

The upstream-signed binaries remain strictly a **local test input**, not a distributable PSM package. v1.0.5 publication is blocked until a separate, license-compliant installed build passes League detection, Pengu initialization, and visible skin rendering in Practice Tool and multiple matches. The published v1.0.4 stable release is unchanged.
