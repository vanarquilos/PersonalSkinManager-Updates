# Public Repository and Release Model

This repository is the canonical public repository for **Personal Skin Manager**.

It contains:

- sanitized application source
- public project documentation
- the stable signed update manifest
- published release history
- public read-only diagnostics

The maintainer's historical/internal development repository remains private.

## Compatibility-critical paths

Already-installed PSM clients depend on the stable update channel in this repository.

Do not casually move or rename:

```text
stable/manifest.json
```

Do not rewrite or force-move already-published release tags merely to change repository organization.

The historical v1.0.1 GitHub Release and installer remain valid provenance. Future releases should tag the canonical application source in this repository.

## Publication boundary

Never publish:

- private Ed25519 signing keys or signing passwords
- `cslol-dll.dll`
- local user configuration/cache/log files
- `%LOCALAPPDATA%\Rose` user data
- generated `dist/`, `build/`, or installer working output
- local diagnostic TXT reports
- temporary backups/recovery folders
- credentials, tokens, or machine-specific secrets
- Riot Games assets extracted from a user's installation

## Release model

For future application versions:

1. update and verify source in this repository
2. run targeted tests and a clean application build
3. create the installer without local-only QA DLLs
4. verify installer SHA-256 and exact size
5. publish the installer as a GitHub Release asset
6. sign the stable manifest with the private Ed25519 key stored outside the repository
7. update `stable/manifest.json`
8. verify the updater against the published manifest
9. tag the verified canonical source commit

Avoid committing new installer binaries into ordinary Git history. Existing historical files under `releases/` are retained for provenance and should not be rewritten without a specific migration reason.

## Public contribution model

Public contributors should branch from the maintained public source in this repository.

The private historical development repository is not required to build, inspect, or contribute to the public project.