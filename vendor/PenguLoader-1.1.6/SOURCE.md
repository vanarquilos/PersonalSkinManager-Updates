# Pengu Loader source

This vendored source is based on the official Pengu Loader project:

- Repository: https://github.com/PenguLoader/PenguLoader
- Upstream tag: `v1.1.6`
- Upstream commit: `4d641f52bc5d70aac4c09dfa1fa7a043a9069aff`

Personal Skin Manager retains the loader for its existing League Client integration. PSM-specific changes are intentionally limited to compatibility and product integration, including:

- PSM/Rose-compatible local configuration paths where changing them would introduce regression risk
- CLI commands used by the Python integration, including status/path/restart/silent flows
- removal of inherited Rose application-update/community surfaces that are not part of PSM
- PSM-visible branding where appropriate

The loader is rebuilt from this vendored source by `scripts/build_pengu_loader.py` before the packaged PSM build. NuGet-generated runtime dependencies are therefore not required to be committed to the public source snapshot.

`Pengu Loader/core.dll` remains a separate upstream runtime component used by Pengu activation and is treated as third-party material under the applicable Pengu Loader terms. PSM's Python integration invokes the loader/runtime; it does not claim ownership of Pengu's activation implementation.

See the repository root `THIRD_PARTY_NOTICES.md` for attribution and third-party licensing scope.
