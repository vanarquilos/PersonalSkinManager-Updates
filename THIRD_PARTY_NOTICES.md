# Third-Party Notices

Personal Skin Manager (PSM) is derived from and integrates with multiple upstream projects. This file records attribution and clarifies that the repository's root license does not relicense third-party components.

## Rose

Upstream:

`https://github.com/Alban1911/Rose`

PSM was derived from the Rose codebase by Alban and Florent. The original Rose MIT license is retained as the repository root `LICENSE`.

PSM's initial sanitization work used the pinned Rose baseline:

`59922fc0586d45b4c5da6250db73d3be675305c1`

Copyright and license notices inherited from Rose must be preserved where required.

## Pengu Loader

Upstream:

`https://github.com/PenguLoader/PenguLoader`

Vendored source is retained under:

`vendor/PenguLoader-1.1.6/`

The corresponding Pengu Loader license remains with the vendored source. PSM does not claim ownership of Pengu Loader or its third-party dependencies.

Prebuilt Pengu Loader runtime components present in the inherited project remain third-party components and are not relicensed by the PSM root MIT license.

## League Toolkit / CSLOL tooling

Upstream projects:

- `https://github.com/LeagueToolkit/cslol-manager`
- `https://github.com/LeagueToolkit/ltk-manager`

PSM v1.0.2 uses third-party League Toolkit components for overlay creation and the current runtime patcher. Release installers may include the applicable `mod-tools.exe`, `ltk_patcher_host.exe`, and `ltk_patcher_dll.dll` binaries so users do not need to install them manually.

These components remain governed by their upstream license terms. The PSM root MIT license does not relicense them. Release engineering must preserve attribution and provide clear access to the corresponding upstream source/license information.

The retired `cslol-dll.dll` runtime is not required by PSM v1.0.2 and is not part of the v1.0.2 installer.

## Python dependencies

Python dependencies are listed in `requirements.txt` and retain their own upstream licenses.

For example, the `cryptography` project is distributed under its applicable upstream dual-license terms. Refer to the installed dependency metadata/upstream project for the exact version-specific license.

## Plugins and inherited assets

Vendored plugins and inherited assets retain their original names, authorship, source references, and license notices where present.

Do not remove third-party notices merely to simplify branding. Internal compatibility identifiers may still contain the Rose name where changing them would introduce regression risk.

## Riot Games

League of Legends, Riot Games, and related names/assets are the property of Riot Games and/or their respective rights holders.

Personal Skin Manager is not affiliated with, sponsored by, or endorsed by Riot Games.

Nothing in the PSM license grants rights to Riot Games assets or other third-party intellectual property.
