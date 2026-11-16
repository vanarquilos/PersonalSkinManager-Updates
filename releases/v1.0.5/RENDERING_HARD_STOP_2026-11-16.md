# PSM v1.0.5 — rendering status and pre-injection safety (2026-11-16)

**Status: NOT RENDERING / NO-GO.** Do not publish or describe this as a skin-rendering fix.

## What source review established

The frozen private QA EXE at commit c1d694f matches its manifest and
has no LTK host/DLL. It packages a 2 KiB inert CSLOL compatibility stub,
which is not a skin renderer. The user's Python regression set passed
31/31 tests, and official LTK Manager 1.33.0 is installed and detected.
None of those observations proves successful in-game cosmetics.

The current PSM injector still uses direct `ltk_patcher_host.exe`. Recent
LTK patcher host verification intentionally rejects third-party direct
hosts (LeagueToolkit/ltk-manager issue #923). LTK's documented external
deep links import mods but do not provide session control to start/stop
patchers or select a skin. Alban1911/Rose's current embedded bridge is
its internal implementation, not a supported PSM SDK.

The private PSM branch must **not** copy identity-spoofing mechanics,
strip upstream verification, alter Riot/Vanguard controls, or turn
enforcement-off flags on. An updated LTK Manager is not a replacement
for an authorized PSM rendering backend.

## Actual source change in this PR

`SkinInjector.inject_skin` now refuses unavailable runtime BEFORE it
resolves a skin archive, cleans mod storage, unpacks assets, starts an
overlay or triggers the patcher. If a game was suspended by the caller,
it asks the existing manager to resume. It records an actionable
`INJECTION_RUNTIME_UNAVAILABLE` issue and never returns a fake success.
Three offline regression tests cover no side effects, missing readiness
state and resume exceptions.

The legacy LTK host session now also refuses to return success on a clean
process exit or manual stop unless **all three** of these observations were
recorded: game attachment, DLL overlay initialization and at least one
modded WAD redirection. This corrects the former false-positive outcome
when a host exited with zero attachment. Five offline regression tests
cover both the evidence verdict and complete session return codes.
A session without observable redirection is unverified; this is not proof
that an unobserved rendering attempt necessarily failed visually.

These safeguards address a real error path, but **they do not render
skins**.

## Requirements before PSM skin rendering can be marked complete

1. Obtain a supported, authorized runtime integration with actual
   selection, patcher start/stop, health and cleanup operations. A bare
   install link or passing a DLL EOL test is insufficient.
2. Verify selected PSM skin assets can be accepted by that renderer on
   the installed League 16.22 build. LTK content rules may reject
   unowned official Riot skins even if custom mods work.
3. Confirm a skin selected in the PSM interface visibly renders in a
   permitted Practice Tool match with matching logs and WAD redirects.
4. Test early start, reconnect, cancellation, exceptions, state restore,
   clean Windows install/upgrade, and repeat across at least two games.
5. Document licensing, patcher provenance and release gates; retain
   the old public v1.0.4 release and protected rollback until then.

**Do not start any new v1.0.5 public installer build from this patch.**
