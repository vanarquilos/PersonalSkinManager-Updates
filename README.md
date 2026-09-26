# Personal Skin Manager

Personal Skin Manager (PSM) is an open-source Windows skin-management application for League of Legends, derived from the open-source **Rose** project by Alban and Florent.

**Current stable release:** `v1.0.1`  
**Release candidate:** `v1.0.2`  
**Platform:** Windows 10/11 x64  
**Website:** https://psm.vanarquilos.dev

[Website](https://psm.vanarquilos.dev) · [Stable release](https://github.com/vanarquilos/PersonalSkinManager-Updates/releases/tag/v1.0.1) · [Source](https://github.com/vanarquilos/PersonalSkinManager-Updates) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

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

PSM v1.0.2 is designed as an **all-in-one installer**. Users should not need to copy DLLs or manually configure runtime files after installation.

## v1.0.2

v1.0.2 is a League compatibility release focused on restoring a stable supported runtime path after the September 2026 game update.

Highlights:

- updated runtime compatibility
- current WAD handling
- improved startup/injection timing
- improved cleanup and diagnostics
- cleaner Settings UI with section icons and visual hierarchy
- bundled runtime dependencies for a simpler installation

See [CHANGELOG.md](CHANGELOG.md) and [releases/v1.0.2/RELEASE_NOTES.md](releases/v1.0.2/RELEASE_NOTES.md).

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
- Release candidate: **1.0.2**
- Executable: `PersonalSkinManager.exe`
- Installer: `PersonalSkinManager_Setup.exe`
- Update channel: `stable`

The stable channel remains on v1.0.1 until the v1.0.2 installer is built, verified, published, and the signed manifest is updated.

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

The signed stable manifest must not be changed until the final v1.0.2 installer exists and its hash/size are known.

## Security and compatibility boundary

This project does not add or improve:

- anti-cheat bypass or evasion
- stealth or process concealment
- driver-based circumvention
- security-control disabling
- tampering with third-party enforcement controls

PSM does not patch or replace League Toolkit's verification code. v1.0.2 uses the upstream Rose-compatible patcher-host mode required for Rose-style carrier overlays, while PSM's signed update/package verification remains enforced.

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
