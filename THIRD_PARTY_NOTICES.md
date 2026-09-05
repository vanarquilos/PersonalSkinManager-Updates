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

Upstream:

`https://github.com/LeagueToolkit/cslol-manager`

The broader `LeagueToolkit/cslol-manager` project is published under **GPL-3.0**. Its source refers to the CSLOL tooling executable `cslol-tools/mod-tools.exe`.

PSM contains/uses inherited CSLOL/mod-tooling integration, including a prebuilt `injection/tools/mod-tools.exe`. Treat that binary and related upstream CSLOL components as third-party material governed by their applicable upstream terms; the PSM root MIT license does not relicense them.

### cslol-dll.dll

`cslol-dll.dll` is **not committed to, bundled with, or distributed by PSM**.

League Toolkit publishes a separate **CSLOL DLL License Addendum (Distribution & Use Policy)**. The addendum states that it solely governs `cslol-dll.dll` and derivative binaries and controls over a project-wide license when the two conflict.

Among other conditions, the addendum imposes distribution, signing, enforcement, and anti-tampering requirements. Anyone considering distribution of that DLL must read and independently comply with the current upstream addendum.

PSM's source references a local runtime path for the DLL because a separately supplied local dependency may be present. That reference is not a grant of redistribution rights.

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
