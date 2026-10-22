# Personal Skin Manager

Personal Skin Manager (PSM) is an open-source Windows skin-management application for League of Legends, derived from the open-source **Rose** project by Alban and Florent.

**Latest public pre-release:** `v1.0.4` (community testing)  
**Previous stable release:** `v1.0.3`  
**Next proposed version:** `v1.0.5` (League 26.21 compatibility audit; NOT release-ready)  
**Signed in-app update channel:** `v1.0.1` (manifest update deferred)  
**Platform:** Windows 10/11 x64  
**Website:** https://psm.vanarquilos.dev

[Website](https://psm.vanarquilos.dev) · [v1.0.4 community-test release](https://github.com/vanarquilos/PersonalSkinManager-Updates/releases/tag/v1.0.4) · [Previous v1.0.3](https://github.com/vanarquilos/PersonalSkinManager-Updates/releases/tag/v1.0.3) · [Source](https://github.com/vanarquilos/PersonalSkinManager-Updates) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

> This repository is the canonical public source, release, update-channel, diagnostics, and documentation repository for Personal Skin Manager.

## What PSM does

PSM preserves the working skin-management foundations inherited from Rose while maintaining its own compatibility, UI, installer, updater, and diagnostics.

Project areas include:

- League/LCU integration
- owned League skin/chroma selection
- compatible custom mods
- supported forms and variants
- Pengu Loader integration
- overlay creation and runtime patching
- game monitoring and process coordination
- local settings, cache, and logs

## Requirements

For normal users:

- Windows 10/11 x64
- League of Legends installed
- Administrator permission for the installer

PSM v1.0.2 and later are designed as **all-in-one installers**. Users should not need to copy DLLs or manually configure runtime files after installation.

## v1.0.5 preparation (unreleased)

League 26.21 introduces upstream LTK overlay/material-format changes. PSM v1.0.5 work is being reviewed separately from v1.0.4; no v1.0.5 installer is available yet.

The candidate branch fixes LCU reconnect PUT retries and a vanished-game-process race, with new regression tests. App and installer metadata are set to **v1.0.5**, but this does not mean an installer has been published. The bundled LTK patcher/host and mod tooling cannot be verified from this public repository because those binaries are not tracked.

**New 26.21 runtime candidate (private local QA only):** The older bundled LTK DLL expired October 4, 2026, before the October 16 League PE build. The upstream LTK v1.30.1 tag includes a host/DLL pair whose DLL cutoff is October 28, 2026, newer than that game build. Its host/DLL identity is pinned in `scripts/stage_ltk_v105_test.ps1`. This clears the known cutoff, but **does not prove host-protocol or in-game overlay compatibility**.

With PSM and League closed, stage the official pair for **your own Windows test only**:

```powershell
git fetch origin
git switch fix/v1.0.5-pre-release-hardening
git pull --ff-only origin fix/v1.0.5-pre-release-hardening
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\stage_ltk_v105_test.ps1
```

The staging script verifies exact upstream Git blob identities and file sizes, audits the game-build/DLL cutoff, backs up the old host/DLL, and stages the pair locally. If your game is installed elsewhere, pass `-LeagueGameDir "D:\Riot Games\League of Legends\Game"`.

**Do not publish a PSM installer containing the official signed patcher binaries.** League Toolkit's [separate patcher license](licenses/LTK-PATCHER-LICENSE.md) requires removing its official signatures on copies distributed in other tools, unless explicit permission is granted. For a public release, review the license, remove the official signatures using a trusted release-signing workflow, and verify the final artifact again.

To prepare a **local-only Windows test installer** from this branch:

```powershell
git fetch origin
git switch fix/v1.0.5-pre-release-hardening
git pull --ff-only origin fix/v1.0.5-pre-release-hardening
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\prepare_v1_0_5_test.ps1
```

If League is installed elsewhere, pass `-LeagueGameDir "D:\Riot Games\League of Legends\Game"` with your actual League Game folder. After all preflight checks and the build pass, the candidate is created at `installer/candidates/v1.0.5/PersonalSkinManager_Setup_v1.0.5-TEST.exe` alongside its SHA-256 and runtime audit. No public release or signed update manifest is changed.

**Before building:** ensure all three trusted local runtime files are present and have compatibility/provenance verified. The script refuses missing or detectably expired runtime files but cannot prove material-hash/host protocol compatibility.

**Release gate:** verify licensed/trusted compatible runtime binaries, in-game Practice Tool and Swiftplay tests, installer integrity, and a working feedback channel. See [the v1.0.5 release checklist](releases/v1.0.5/PRE_RELEASE_CHECKLIST.md).

## v1.0.4 (public community-test pre-release)

v1.0.4 carries the current scanner-timing compatibility work needed after v1.0.3.

Highlights:

- starts the LTK scanner when the loadout countdown begins instead of at the last injection moment
- reuses the pre-armed scanner for the selected skin overlay
- cleans up unused/dead scanner sessions safely between games
- preserves the overlay directory while clearing its contents so the scanner keeps a valid configured path
- retains League-build-aware runtime cutoff validation rather than bypassing an unsupported LTK runtime
- adds focused regression coverage for the timing and cleanup lifecycle

The v1.0.4 installer is published as a public GitHub pre-release. The maintainer verified normal skin injection and Swiftplay lobby skin selection. Swiftplay **in-game** injection has not yet been verified on v1.0.4; report problems through the official website feedback section. v1.0.3 remains available as the previous release.

See [CHANGELOG.md](CHANGELOG.md) and [releases/v1.0.4/RELEASE_NOTES.md](releases/v1.0.4/RELEASE_NOTES.md).

## v1.0.3

v1.0.3 is a focused compatibility hotfix for the October 4 runtime cutoff regression.

Highlights:

- validates LTK compatibility against the installed League build instead of the current calendar date
- restores injection when the bundled runtime still supports the installed League build
- prevents false "injection system ready" reporting when runtime validation fails
- hardens Swiftplay queue 480 against late skin-tracking and phase timing races
- adds retryable ChampSelect, GameStart, and InProgress Swiftplay fallbacks
- keeps Swiftplay injection alive through reconnects using the regular per-game runtime lifecycle
- adds regression coverage for LTK build-cutoff and Swiftplay timing behavior

See [CHANGELOG.md](CHANGELOG.md) and [releases/v1.0.3/RELEASE_NOTES.md](releases/v1.0.3/RELEASE_NOTES.md).

## v1.0.2

v1.0.2 introduced the all-in-one runtime path, current WAD handling, improved injection timing, cleanup, diagnostics, and Settings UI updates.

See [releases/v1.0.2/RELEASE_NOTES.md](releases/v1.0.2/RELEASE_NOTES.md).

## Repository layout

```text
main.py
config.py
PersonalSkinManager.spec

assets/
injection/
launcher/
lcu/
main/
pengu/
psm_update/
scripts/
state/
threads/
ui/
utils/
vendor/
licenses/

stable/
  manifest.json
```

`stable/manifest.json` is compatibility-critical for installed PSM clients.

## Application identity

- Product: **Personal Skin Manager**
- Latest public pre-release: **1.0.4** (community testing)
- Previous stable release: **1.0.3**
- Executable: `PersonalSkinManager.exe`
- Installer: `PersonalSkinManager_Setup.exe`
- Update channel: `stable`

The signed in-app update channel remains on v1.0.1 because the existing signing-key password is unavailable. Public GitHub releases are handled separately; do not replace the embedded signing key casually because older installed clients trust the existing public key.

## Antivirus detections and release verification

Some antivirus products may flag packaged PSM builds heuristically. PSM is a self-contained Windows application that bundles runtime components and coordinates with League processes for its supported skin workflow, which can resemble behavior that generic heuristic scanners treat cautiously.

A detection should be investigated rather than automatically dismissed or treated as proof of malware. Users should **not disable antivirus protection just to run PSM**.

For the official v1.0.4 community-test installer, verify all of the following before running it:

- download only from the canonical GitHub Release linked by this repository or the official website;
- installer filename: `PersonalSkinManager_Setup.exe`;
- exact size: `28,165,060 bytes`;
- SHA-256: `C31EAE458757C2EF9B3ADE8DDDCB6C791F785CBAEEA34C781622768AD407E7EA`;
- review the public source and release notes when additional assurance is needed.

If a scanner reports a suspected false positive, compare the scanner's file hash with the published release hash first. A different SHA-256 means it is not the exact published v1.0.4 installer. Confirmed false-positive detections should be submitted to the antivirus vendor for review rather than worked around by weakening endpoint security.

## Compatibility data directory

PSM intentionally retains:

```text
%LOCALAPPDATA%\Rose
```

Some inherited local components and compatibility paths depend on that location. It is an implementation detail and does not represent the visible product identity.

## Building

Requirements:

- Windows 10/11 x64
- Python 3.11 or newer
- packages from `requirements.txt`
- Visual Studio Build Tools with the required .NET desktop components
- Inno Setup
- trusted local copies of:
  - `injection/tools/mod-tools.exe`
  - `injection/tools/ltk_patcher_host.exe`
  - `injection/tools/ltk_patcher_dll.dll`

Those runtime binaries are intentionally excluded from ordinary source history. The release build verifies that all three are present and bundles them into the installer.

Build the full application and installer:

```powershell
python .\scripts\build_all.py
```

Expected installer:

```text
installer\PersonalSkinManager_Setup.exe
```

## Stable update architecture

PSM's stable updater:

1. fetches `stable/manifest.json` over HTTPS
2. verifies the Ed25519 manifest signature
3. validates version/package metadata
4. verifies installer SHA-256 and exact size
5. defers installation while League is running
6. installs only a verified release

The private Ed25519 signing key remains outside source control. Only the public verification key belongs in the repository.

The signed stable manifest remains intentionally deferred until the existing signing key can be used again or a deliberate key-rotation/bootstrap plan is implemented.

## Security and compatibility boundary

This project does not add or improve:

- anti-cheat bypass or evasion
- stealth or process concealment
- driver-based circumvention
- security-control disabling
- tampering with third-party enforcement controls

PSM does not patch or replace League Toolkit's verification code. v1.0.2+ uses the upstream Rose-compatible patcher-host mode required for Rose-style carrier overlays, while PSM's signed update/package verification remains enforced.

See [SECURITY.md](SECURITY.md).

## Third-party components

PSM is derived from or integrates with:

- **Rose** by Alban and Florent
- **Pengu Loader**
- **League Toolkit / CSLOL tooling**

Third-party components retain their own licenses and are not relicensed by PSM's root MIT license.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the `licenses/` directory.

## Public source checks

The repository keeps a manual `Public source checks` GitHub Actions workflow for release sanity checks. It validates:

- Python compilation
- release-source tests
- tracked-secret/local-file hygiene
- generated-output boundaries
- stable manifest structure

PSM development remains local-first; the workflow does not run automatically on every push or pull request. Windows runtime and installer QA are still required before publication.

## Riot Games notice

League of Legends and related Riot Games properties belong to Riot Games and/or their respective rights holders.

Personal Skin Manager is an independent community project and is not affiliated with, sponsored by, or endorsed by Riot Games.
