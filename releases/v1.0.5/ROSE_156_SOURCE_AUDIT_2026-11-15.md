# PSM 1.0.5: source comparison with Alban1911/Rose 1.5.6
**Audit date:** 2026-11-15 (Asia/Manila)
**Repositories:** https://github.com/Alban1911/Rose (`main`) and https://github.com/vanarquilos/PersonalSkinManager-Updates (`rebuild/v1.0.5-rose-compatible`)
**Release decision:** **NO-GO for a working modskin release.** Source diagnostics and release QA can be corrected independently of the injection backend; actual rendering is unverified.

## What changed upstream (source-confirmed)

Rose's current README and its November 5 release 1.5.0 state that its old direct patcher was replaced with **installed LTK Manager as the skin engine**. As of the November 9 release 1.5.6, the key implementation remains:

- `injection/tools/tools_manager.py`: recognizes `ltk-manager.exe`, resolves configured `ltkManagerPath`, running manager path or known Program Files / Local AppData locations; validates its own `ltk_launcher.exe` and `LeagueToolFlop.dll` instead of the raw LTK patcher host/DLL.
- `injection/overlay/ltf_session.py`: manages an LTK Manager session via a local bridge, waits for readiness and restores state after a game. User-open manager sessions are not silently terminated, and unready/missing manager states are reported distinctly.
- `injection/tools/bridge.py`: connects to a Rose-supplied native bridge loaded into LTK Manager, not an official public LTK Manager SDK. Its commands and authentication are internal to that bridge. This is **not** evidence that PSM has authorized access to the manager's private API.
- `injection/overlay/overlay_manager.py`: stages mods during champion-select countdown, verifies patcher readiness, handles reconnect windows, and restores/cleans up mod library switches. A skin choice after the late cutoff is not applied retrospectively.
- `injection/overlay/ltk_data.py`: reads LTK Manager's library/log state and treats incidents separately from raw host attachment.
- `injection/overlay/ltf_report.py`: classifies delivery refusal/rate limits, offline delivery, administrator/elevation context, incompatible patcher, host verification, WAD refusal, missing launcher, stale bridge, timing/late join, health-check, incident and host-crash cases; avoids calling attachment successful skin rendering.
- `injection/tests/test_ltf_session.py`: covers manager ownership, user mods, imports, failures, cleanup, retries, staging, host verification, and no false-success cases.
- Rose v1.5.5 (November 8) introduced health/repair checks for custom mod imports and reports when LTK rejects a mod using another official skin as its base; v1.5.6 (November 9) improved mod library reuse/migration. It does not mean every unowned Riot cosmetic is supported.

**Important trust boundary:** Rose's `native/ltf/VENDORED.md` documents native LTF code that loads a DLL into an LTK Manager process and adjusts the manager's recorded parent to satisfy upstream host-verification checks. LTK's issue #923 reports the latter verification was intended to restrict third-party use. We must not silently copy or deploy such verification-bypass mechanics into PSM. This audit describes the behavior; it does **not** implement it.

## PSM current behavior (source-confirmed)

| System | Rose main | PSM v1.0.5 rebuild | Finding |
| --- | --- | --- | --- |
| Skin backend | LTK Manager + Rose LTF bridge | Direct `ltk_patcher_host.exe` via `injection/overlay/ltk_host.py` | **Architecturally different**; swapping DLLs is insufficient |
| Patch delivery | Manager's authenticated official delivery | Manual, user-provided host/DLL | Source of vendor patcher updates remains external |
| Program discovery | LTK Manager path config/running/install | Direct local DLL path | PSM cannot detect or use current manager-backed Rose engine |
| Process privilege | Manager normally unelevated | PSM spec/startup and new auto-start set to standard user | Corrected in rebuild, Windows execution still unverified |
| Host verification | Manager session has own vendor checks | Direct third-party host may be rejected | **Cannot claim compatibility from cutoff or SHA alone** |
| Mods | Manager library with import/health and cleanup | PSM mod-tools overlay builder and local storage | Incompatible library management contracts |
| Timing | LTK Manager prewarmed, countdown staging, reconnect/hold guard | Direct scanner early + local game monitoring | Cannot carry over Rose timing code alone |
| Errors | Dedicated LTF/manager status classification | Original PSM reporter filtered important codes | **Fixed in rebuild** |
| Official-skin substitutes | Modern health and integrity restrictions enforced | Historical PSM tests still expect some unowned-skin carrier behavior | **Feature compatibility requires separate review** |
| Tests | Extensive bridge/session/cleanup cases | Direct LTK host protocol, PyInstaller and source-contract tests | Real Windows + approved in-game QA pending |

## Defects fixed in this pass

1. `utils/core/issue_reporter.py` now records `LTK_HOST_VERIFICATION_FAILED`, `LTK_ADMIN_CONTEXT`, `LTK_NO_WAD_REDIRECTION`, `LTK_PATCHER_CUTOFF_UNKNOWN`, `LEAGUE_BUILD_UNREADABLE`, and `LEAGUE_DIR_NOT_FOUND`. Previously, `report_issue` silently dropped these failures from Troubleshooting.
2. `injection/tools/tools_manager.py` no longer calls a DLL with an unknown embedded cutoff or an unreadable League executable build **ready**. It fails closed with an actionable diagnostic. When a timestamp check succeeds, it explicitly says that vendor host authorization and visible skin rendering remain **unverified**.
3. `injection/overlay/ltk_host.py` correctly attributes a rejected overlay to **PSM**, not Rose.
4. `utils/integration/ltk_onboarding.py` and `releases/v1.0.5/USER_LTK_SETUP.md` no longer claim the current Rose workflow is a copy-based user-supplied patcher setup. The import script remains for **private QA**, not a guaranteed repair or public-release installation procedure.
5. LTK and League timestamp diagnostics are labeled **UTC**, avoiding local-time ambiguity at the patch boundary.
6. Regression tests: `tests/test_v105_rose_runtime_diagnostics.py`, updated `tests/test_runtime_failure_reporting.py` and `tests/test_v105_ltk_expiry_troubleshooting.py`. They are included in the Windows CI workflow and the private Rose-style build script.

These changes **do not** create a current LTK Manager bridge or a working skin renderer. The native loader, backend, and game session behavior have NOT been ported.

## Architecture decision before v1.0.5 is considered skin-ready

**Route A — current Rose-like runtime:** Requires installed official LTK Manager. PSM can remain the primary user interface only if a documented, authorized manager-control interface is available and is implemented with proper consent, permissions, ownership, library sync and return codes. Rose's proprietary-integration-specific launcher and host-verification manipulation must not be treated as such an API. A one-time install contradicts the prior PSM *no LTK Manager installation* requirement unless the product owner revises that requirement.

**Route B — strictly independent PSM:** Keep PSM's no-manager-install requirement; obtain a different authorized runtime or explicit upstream supported third-party interface. No existing local PSM LTK host/DLL pair supports this as an independently verified current game backend. Rebuilding a PSM-owned inert `cslol-dll.dll` cannot inject skins; it only enables `mod-tools mkoverlay`.

**Route C — release non-skin features only:** Do not call this the completed skin manager or silently ship a broken skin button. Explicitly disable/label unverified skin application and publish only after deciding whether this reduced scope warrants a separate version. Do not promote 1.0.5 as skin-ready.

## Further technical gates

- A candidate that passes a DLL cutoff and SHA-256 check still needs a legitimate vendor execution path and acceptance by host verification.
- Official manager patcher delivery can fail independently; LTK issue #1082 (November 14) reports `429 rate_limited` for some users, not necessarily everyone.
- Complete real Windows MSVC/PyInstaller/installer QA, user-data upgrade/uninstall safety, successful GitHub Actions jobs, and permitted in-game tests. Current CI's minimal Ubuntu echo runner also fails **before any step**, which cannot be fixed by changing PSM tests.
- Review the separate licenses before shipping: Rose's top-level MIT license permits reuse with notice; the LTF native source's provenance/permissions and LeagueToolkit's separate Patcher License still require independent review. The LTK license permits certain third-party use but imposes signature/distribution requirements; legal permission does not imply a current patcher will accept a third-party process.

**Stop condition:** No bypass of upstream signature verification, no spoofed host identities, no game security disable flags, no public installer marked working without visible in-game rendering.
