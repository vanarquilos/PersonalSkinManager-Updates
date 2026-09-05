# Personal Skin Manager — Updates

Public release infrastructure and compatibility tooling for **Personal Skin Manager (PSM)**.

This repository is intentionally separate from the application source repository. It contains the stable signed update channel, published release artifacts/history, and small public diagnostics that are safe to share.

## Repository layout

```text
stable/
  manifest.json

releases/
  v1.0.0/
  v1.0.1/

tools/
  diagnostics/
    README.md
    PSM_Revenant_234043_Audit.py
    PSM_Revenant_26_17_Compare.py
```

## Stable update channel

`stable/manifest.json` is the machine-readable update manifest consumed by supported PSM builds. PSM verifies the manifest with its embedded Ed25519 public key and verifies the installer package by SHA-256 and exact size before use.

The **private Ed25519 signing key is never stored in this repository**. It is maintained separately by the project maintainer.

Release installers should be distributed through GitHub Release assets. Historical files under `releases/` are retained for provenance and compatibility with the existing release history.

## Diagnostics

Public read-only compatibility tools live under [`tools/diagnostics`](tools/diagnostics/README.md).

Diagnostic reports can contain local filesystem paths and package hashes. Review generated reports before posting them publicly.

## Deliberately not included

This repository does not publish:

- private update-signing keys or passwords
- local PSM configuration, caches, logs, or user data
- `cslol-dll.dll`
- local QA-only binaries
- Riot Games assets extracted from a user's installation

`cslol-dll.dll` is subject to the League Toolkit CSLOL DLL License Addendum and is not distributed by PSM.

## Open-source scope

Original documentation and diagnostic tooling in this repository are released under the root [`LICENSE`](LICENSE).

Published/historical application installers can contain third-party components with their own license terms. The root MIT license does **not** relicense those components. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Source and attribution

Personal Skin Manager is derived from the open-source **Rose** project by Alban and Florent. The application source retains its upstream license and third-party notices.

League of Legends and related Riot Games properties belong to Riot Games and/or their respective rights holders. Personal Skin Manager is not affiliated with or endorsed by Riot Games.
