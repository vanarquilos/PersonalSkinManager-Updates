# Personal Skin Manager

Personal Skin Manager (PSM) is an open-source Windows skin-management application for League of Legends, derived from the open-source **Rose** project by Alban and Florent.

**Current stable release:** `v1.0.1`  
**Platform:** Windows 10/11 x64  
**Language:** Python  
**License:** MIT for the PSM/Rose-derived source, with separate terms for third-party components

[Download v1.0.1](https://github.com/vanarquilos/PersonalSkinManager-Updates/releases/tag/v1.0.1) · [Source](https://github.com/vanarquilos/PersonalSkinManager-Updates) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

> This repository is the canonical public source, release, update-channel, diagnostics, and documentation repository for Personal Skin Manager.

## What PSM does

PSM preserves the working skin-management foundations inherited from Rose while removing services that are not part of the PSM maintenance model.

Supported project areas include:

- League/LCU integration
- skins and chromas
- compatible custom mods
- supported forms and variants
- Pengu Loader integration
- CSLOL/mod tooling
- game monitoring and process coordination
- local bridge/content synchronization
- game-hash/data checks
- local settings and logs
- the existing content-injection pipeline

## Current release

### Personal Skin Manager v1.0.1

Installer:

```text
PersonalSkinManager_Setup.exe
```

SHA-256:

```text
3CF2E47BAEAC15376F759C0F7CA0C21C0011B36577E004B582105AD1779641BB
```

The installer is published through the official GitHub Release:

[Personal Skin Manager v1.0.1](https://github.com/vanarquilos/PersonalSkinManager-Updates/releases/tag/v1.0.1)

PSM does not mirror or distribute `cslol-dll.dll`.

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

stable/
  manifest.json

releases/
  v1.0.0/
  v1.0.1/

tools/
  diagnostics/
```

`stable/manifest.json` is a compatibility-critical path used by supported installed PSM builds and should not be moved or renamed casually.

## Project status

The current stable application baseline is **v1.0.1**.

Completed release work includes:

- sanitization of inherited analytics/community/update plumbing that is not used by PSM
- dependency and provenance review
- V1 application identity and UI finalization
- runtime and functional regression QA
- build, installer, updater, and uninstall hardening
- signed stable-channel updater bootstrap
- SHA-256 installer verification
- Ed25519 manifest verification
- publication of the sanitized application source

The historical `v1.0.1` release predates source integration into this repository. Its existing release/tag are intentionally retained for provenance and compatibility rather than rewritten.

## Removed from the Rose baseline

PSM removes services that are not required by the project:

- Rose analytics and heartbeat reporting
- the inherited Rose application self-updater
- Party Mode and its relay/network service
- Rose Discord/community callbacks
- Rose Ko-fi/community UI in the locally built loader

Compatibility-oriented internal identifiers are retained where changing them would create unnecessary regression risk.

## Application identity

- Product: **Personal Skin Manager**
- Stable version: **1.0.1**
- Executable: `PersonalSkinManager.exe`
- PyInstaller spec: `PersonalSkinManager.spec`
- Installer: `PersonalSkinManager_Setup.exe`
- Update channel: `stable`

## Compatibility data directory

PSM intentionally retains:

```text
%LOCALAPPDATA%\Rose
```

Some inherited local components and compatibility paths depend on that location. The path is an implementation detail and does not represent the visible application identity.

## Building

Requirements:

- Windows 10/11 x64
- Python 3.11 or newer
- packages from `requirements.txt`
- Visual Studio Build Tools with the required .NET desktop build components
- Inno Setup for installer creation

Build the application:

```powershell
python .\scripts\build_pyinstaller.py
```

Expected output:

```text
dist\PersonalSkinManager\PersonalSkinManager.exe
```

Build the complete application/installer pipeline:

```powershell
python .\scripts\build_all.py
```

Expected installer:

```text
installer\PersonalSkinManager_Setup.exe
```

Do not use the legacy `Rose.spec`; the maintained spec is `PersonalSkinManager.spec`.

## Stable update architecture

Application updates and League game-data freshness are separate concerns.

PSM's stable application updater:

1. fetches `stable/manifest.json` over HTTPS
2. verifies the manifest's Ed25519 signature
3. validates manifest schema/version information
4. verifies installer SHA-256 and exact size
5. defers installation while League is running
6. installs only a verified PSM release

The private Ed25519 signing key is maintained outside source control. Only the public verification key belongs in source.

Existing v1.0.1 clients use the stable manifest in this repository. Release engineering must preserve the manifest path and published release asset URLs when backward compatibility depends on them.

Game hash synchronization is handled separately from application releases; ordinary League data changes do not automatically require a new PSM application version.

## External CSLOL DLL

`cslol-dll.dll` is **not part of this repository and is not distributed by PSM**.

The DLL is governed by the League Toolkit **CSLOL DLL License Addendum (Distribution & Use Policy)**, which applies independently of the broader CSLOL project's license. PSM does not grant redistribution rights for that component.

Do not commit, bundle, mirror, or attach `cslol-dll.dll` to PSM source or release artifacts unless the distributor independently satisfies the upstream license terms.

## Security and compatibility boundary

This project does not add or improve:

- anti-cheat bypass or evasion
- stealth or process concealment
- driver-based circumvention
- security-control disabling
- tampering with protections in third-party runtime components

Compatibility work should remain focused on application correctness, content/data compatibility, provenance, verification, reproducible builds, and supported runtime behavior.

See [`SECURITY.md`](SECURITY.md) for reporting guidance.

## Public source checks

Pull requests and pushes to `main` run lightweight public-source checks that:

- compile Python source
- reject tracked private/signing material
- reject tracked local-only `cslol-dll.dll`
- reject generated top-level build output
- validate the stable manifest structure

These checks are source-hygiene gates, not a substitute for Windows runtime or gameplay QA.

## Diagnostics

Read-only public diagnostics live under:

```text
tools/diagnostics/
```

Diagnostic reports can contain local filesystem paths and package hashes. Review generated reports before posting them publicly.

## Licensing and attribution

PSM is derived from:

- **Rose** by Alban and Florent
- **Pengu Loader**
- third-party CSLOL/mod tooling used by the inherited runtime

The original Rose MIT `LICENSE` is retained. Third-party components keep their own licenses and are **not relicensed by the root PSM MIT license**.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for component-level attribution and licensing notes.

## Contributing

Contributions are welcome when they stay within the project's compatibility, provenance, and security boundaries.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

## Development model

The maintainer's historical/internal development repository remains private. Public development and contributions should use this repository as the maintained public source.

Release engineering must preserve:

- the `stable/manifest.json` compatibility path
- existing published release/tag provenance
- signing-key secrecy
- third-party licensing boundaries
- exclusion of local-only QA files and `cslol-dll.dll`

## Riot Games notice

League of Legends and related Riot Games properties belong to Riot Games and/or their respective rights holders.

Personal Skin Manager is an independent community project and is not affiliated with, sponsored by, or endorsed by Riot Games.
