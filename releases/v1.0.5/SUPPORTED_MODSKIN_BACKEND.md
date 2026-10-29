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
- No automatic downgrade, binary patches, host impersonation, verification bypass, or redistribution is implemented.

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
