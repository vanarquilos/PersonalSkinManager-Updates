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

Earlier PSM installers aimed to be all-in-one, but **v1.0.5 is NOT a working all-in-one skin installer**. Its direct LTK host/DLL backend is not verified against recent vendor host checks, and no v1.0.5 release has been published.

## v1.0.5 preparation (unreleased, November 15 audit)

**Release status: NO-GO.** The v1.0.5 source/installer work is maintained in the draft
[PR #19](https://github.com/vanarquilos/PersonalSkinManager-Updates/pull/19)
(`rebuild/v1.0.5-rose-compatible`). No public installer is available or approved.

**Important architecture change:** Alban1911/Rose **v1.5.0 and later** apply
mods through an installed LTK Manager, and Rose v1.5.6 continues that design.
Our current PSM v1.0.5 still uses a direct LTK host/DLL. LTK's newer official
patcher checks host identity and can refuse that third-party direct mode.
A copied DLL, matching hash or non-expired cutoff does not prove it can
apply skins. PSM's inert CSLOL stub only supports local overlay creation;
it does not render skins.

The v1.0.5 rebuild currently includes:
- A safer private QA worktree build, MSVC path quoting fix and non-elevated PSM startup.
- Non-destructive installer/uninstaller handling; **no bundled LTK vendor binaries**.
- Better error reporting for host-verification refusal, administrative context,
  missing WAD redirection, unreadable game builds and unknown DLL cutoffs.
- Explicitly fail-closed skin-readiness checks; no claim of in-game rendering.
- Independent LTK licensing/third-party authorization review remains a release gate.

Read the source comparison at
[`releases/v1.0.5/ROSE_156_SOURCE_AUDIT_2026-11-15.md`](releases/v1.0.5/ROSE_156_SOURCE_AUDIT_2026-11-15.md).
The approved release criteria are at
[`releases/v1.0.5/FINALIZATION_GATE_2026-11-02.md`](releases/v1.0.5/FINALIZATION_GATE_2026-11-02.md).

**Do not run legacy `stage_ltk_v105_test.ps1` scripts as a compatibility fix
or switch away from the maintainer's rollback checkout.** The historical
October v1.30.x DLLs predate newer League builds and do not solve current
host verification. The private build scripts on the rebuild branch use
isolated linked Git worktrees and deliberately cannot publish a skin-ready
installer.

The remaining functional choice is between (1) an authorized LTK
Manager-backed integration (requiring an official manager installation)
and (2) a fully independent PSM backend with explicit support for
third-party use. Neither has passed actual Windows gameplay tests on
current League builds. We will not bypass vendor or game integrity checks
to force the direct-host route.

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
