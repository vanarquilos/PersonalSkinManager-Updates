# PSM supported modskin backend — v1.0.5 decision

**Decision date:** 2026-10-29. **Status:** Back-end dependency blocked; PSM v1.0.5 remains draft.

## Confirmed behavior

- PSM's last local game log built an Aphelios Fantome overlay successfully, rebased its game WAD header (1/1), and initialized/attached the LTK DLL, but served **zero observed WAD redirections**.
- The sanitized diagnostic identified an **LTK host-verification refusal** in that same session.
- A [LeagueToolkit contributor](https://github.com/LeagueToolkit/ltk-manager/issues/923) confirmed on 2026-10-22 that the DLL verification is intentionally designed to block third-party hosts.
- [Rose issue #401](https://github.com/Alban1911/Rose/issues/401) has no released integrated fix; user comments suggest older DLLs as a workaround, **not** a supported new API.
- LTK's [ecosystem integration documentation](https://github.com/LeagueToolkit/wiki/blob/1964862c571555cca6662575cafe6bd58ae6bf8a/src/content/docs/developers/ecosystem-integration.mdx) describes `.fantome` and `.modpkg` interoperability, but explicitly says a public mod-management/overlay API and replacement LTK modtools CLI are not yet available.
- LTK's `ltk://install` documented deep-link accepts **HTTPS package URLs**, not a local file path, and is a user-facing *install* workflow. It does not grant PSM permission or a mechanism to start a patcher session.

## October 29: Rose community v1.28.1 compatibility workaround

Rose has **not** published a code fix for the vendor host-verification refusal. In [Rose issue #401](https://github.com/Alban1911/Rose/issues/401), several users report restoring skins by reverting their LTK patcher host/DLL to *official* LTK Manager v1.28.1, before the intentional third-party-host check. This is an unofficial community workaround, **not a vendor-authorized integration** and **not a PSM release solution**.

- Official historical tag: [v1.28.1](https://github.com/LeagueToolkit/ltk-manager/releases/tag/v1.28.1), commit `9f06802de5d83d6dde3ff1644a1c56049fadf9bb`.
- Host Git blob `b2fc81c6de7bf5b40b81daaf8987706308ed5b33`, 1,238,272 bytes; DLL Git blob `0cd0f58530906c3792e3189ea8af1a8f8bc6f264`, 764,160 bytes. Confirmed against the official tag tree.
- Community reports an October 18, 2026 07:00 UTC **game executable build** cutoff. Last PSM League executable was built October 16 22:15 UTC, but a newer League update would invalidate that comparison.
- The older pair predates the [LTK v1.29.1 material-format parser fix](https://github.com/LeagueToolkit/ltk-manager/releases/tag/v1.29.1) for League 26.21 and may fail on some champion WADs.
- Added `scripts/audit_ltk_v1281_compatibility.py` as a **read-only identity and build-cutoff check** for separately obtained official binaries. It will not install, start, copy, replace, or alter the runtime, and it does not assert that PSM is authorized as a patcher host.
- Added `scripts/review_rose_ltk_v1281.ps1`: opt-in isolated **download and identity audit** from the pinned official tag. Saves the files solely under the ignored `installer/candidates/v1.0.5/audit-only-ltk-v1.28.1` folder, verifies each Git blob, then invokes the read-only cutoff audit. It neither launches the patcher nor replaces files in `injection/tools`; passing it is **not** a license or compatibility verdict.

To run the new isolated review on Windows:

```powershell
Set-Location -LiteralPath "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
git pull --ff-only origin fix/v1.0.5-pre-release-hardening
python -m unittest tests.test_ltk_v1281_compatibility_audit tests.test_rose_legacy_review_contract
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\review_rose_ltk_v1281.ps1"
```

If the League Game folder is elsewhere, pass `-LeagueGameDir` explicitly. Keep downloaded candidate files in the isolated audit-only directory. **Do not use those binaries in PSM or distribute them merely because the identity and cutoff checks pass.**
- No automatic downgrade, binary patches, host impersonation, verification bypass, or redistribution is implemented.

## Opt-in local compatibility test using Rose-reported historical files

The `scripts/use_rose_legacy_runtime_local.ps1` helper now supports an **explicit private source-only** test. It does not patch or spoof the DLL. After the separate `review_rose_ltk_v1281.ps1` downloads the original pinned v1.28.1 pair, it validates identity and the current game build, backs up the active PSM host/DLL to an ignored installer-candidate directory, records the restore manifest **before** replacing them locally, and selects those unmodified historical files in `injection/tools`. This is reversible with `-Action Restore`.

The private test is NOT a vendor-supported API. This approach uses an older build before later third-party host checks and before the 26.21 material-parser fixes, so individual champions may still fail. It must **never** be packaged or published as a PSM release. The local installer-build script and v1.30.1 staging script refuse to proceed while this historical test state is active.

From an up-to-date local Windows checkout, with PSM and League fully closed:

```powershell
Set-Location -LiteralPath "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
git switch fix/v1.0.5-pre-release-hardening
git pull --ff-only origin fix/v1.0.5-pre-release-hardening
python -m unittest tests.test_ltk_v1281_compatibility_audit tests.test_rose_legacy_review_contract tests.test_rose_legacy_local_runtime_contract tests.test_ltk_host_protocol
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\review_rose_ltk_v1281.ps1"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\use_rose_legacy_runtime_local.ps1" -Action Activate
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\run_live_qa.ps1"
```

**After testing and closing League/PSM**, generate the sanitized report and restore:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\diagnose_no_skin_v105.ps1"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\use_rose_legacy_runtime_local.ps1" -Action Restore
```

Use `-LeagueGameDir "<actual Game folder>"` on **both** review and activation if League is installed elsewhere. Keep unmodified binaries private, retain build provenance, do not attempt to bypass game security or vendor verification in newer DLLs, and do not claim skin success without actual in-game rendering.

## Technical decision

Do **not** fake/impersonate the official host, patch the DLL, force-disable verification, or substitute old binaries to evade the host policy. Do not advertise 'skin applied' unless gameplay and WAD redirection are confirmed. Keep a clear hard failure in PSM on host verification refusal.

### Supported integration paths

1. **Local-first file handoff (available conceptually):** PSM continues producing or retaining standard `.fantome` files and may offer **Export package for LTK Manager**. The user imports the file through the official manager UI; PSM does not claim to run the overlay or control the manager. No network upload required. Scope: package and metadata handling only.
2. **Official hosted download handoff (optional):** Where the mod author publishes an authorized, publicly reachable HTTPS package URL, a *user-initiated* `ltk://install` link may ask LTK Manager to import it. Do not use this for user-private local files, invent public uploads, or claim it applies a skin automatically.
3. **Future authorized managed backend:** Only after LeagueToolkit publishes and documents a third-party-compatible API/CLI or grants the required explicit authorization, implement it behind an injected `ModskinBackend` interface, with capability discovery, version negotiation, error classification, and no raw secret/token logging.

### Proposed PSM boundary (not yet implemented)

- `PackageRepository`: resolve/download (when separately authorized), validate and export immutable package files.
- `ModskinBackend`: `capabilities()`, `prepare(package)`, `start_session(context)`, `stop_session()`, `status()`.
- `OfficialManagerHandoff`: user-initiated package export and optional documented deep-link; reports `handed_off`, **never** `injected` or `applied`.
- `AuthorizedRuntimeBackend`: not enabled until a legitimate API and production compatibility exist.
- Existing legacy LTK host adapter: **private diagnostics only** while the verification refusal persists; fail closed, no automatic runtime downgrade.
- `RenderVerdict`: `not_started`, `preparing`, `handoff_only`, `backend_rejected`, `unverified`, `confirmed`. `confirmed` requires real-game evidence, not only an attached DLL.

### Release gates

- [ ] Confirm vendor-approved API/CLI or decide to ship handoff-only mode with precise user messaging.
- [ ] Implement any new backend/handoff behavior as opt-in, testable, local-first functionality; do not silently send packages online.
- [ ] Validate package provenance and structure, and preserve user files on failure.
- [ ] Run focused Windows regression tests.
- [ ] For automatic injection claim: verify skin rendering in Practice Tool and Swiftplay on a supported backend, including reconnect/next game.
- [ ] Finish code signing/redistribution review, installer QA and stable manifest audit.

**Release policy:** Do not merge PR #15 or publish a v1.0.5 installer as working modskin until a supported back-end and all required QA gates pass.
