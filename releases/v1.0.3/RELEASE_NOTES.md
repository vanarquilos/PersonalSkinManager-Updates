# Personal Skin Manager v1.0.3

**Compatibility + Swiftplay Reliability Hotfix**

PSM v1.0.3 resolves the October 4 runtime cutoff regression and completes the Swiftplay reliability work introduced after v1.0.2. The release keeps the existing PSM workflow intact while making runtime validation and Swiftplay injection more resilient.

## Highlights

- Restores normal skin injection on the current supported League build.
- Fixes the incorrect calendar-based LTK cutoff check.
- Adds League-build-aware runtime validation.
- Hardens Swiftplay queue 480 skin tracking and injection timing.
- Adds Swiftplay recovery fallbacks across Matchmaking, ChampSelect, GameStart, and InProgress.
- Keeps Swiftplay injection alive through reconnects.
- Fixes the Swiftplay lobby banner so it follows the skin selected in the carousel.
- Preserves the all-in-one installer workflow with no manual runtime DLL setup.

## Runtime compatibility

PSM previously treated the LTK runtime cutoff as a normal date expiration. Once the wall clock passed the embedded cutoff, PSM could reject a runtime that was still compatible with the installed League build.

v1.0.3 now compares the installed League executable's PE build timestamp against the LTK DLL's supported build cutoff.

This means:

- a compatible League build is not rejected simply because the calendar date passed;
- a League build newer than the runtime cutoff is still rejected correctly;
- unknown or unreadable build timestamps are not falsely blocked before the runtime can report its own status.

Injection readiness reporting was also corrected so PSM no longer reports the injection system as ready after runtime validation has failed.

## Swiftplay

Swiftplay queue 480 now has a more resilient end-to-end path.

### Fixed

- Fixed a race where Matchmaking could begin before the selected skin reached PSM.
- Failed early preparation attempts no longer permanently mark Swiftplay injection as already triggered.
- Preparation retries while matchmaking is still searching.
- Overlay state is re-armed correctly when re-queueing.
- Added independent recovery points at ChampSelect, GameStart, and InProgress.
- Duplicate phase/WebSocket triggers are guarded so they do not race an active overlay worker.
- Prepared mods are retained when an overlay attempt fails so a later fallback can retry.
- Swiftplay now uses the same reconnect-aware game-lifetime stop behavior as the regular injection path.
- The selected Swiftplay champion slot/banner now visually follows the active carousel skin, including unowned/custom-selected skins supported by PSM.

## QA completed

Live QA confirmed:

- normal Practice Tool injection works;
- selected skins load correctly in-game;
- Swiftplay queue 480 injection works;
- Swiftplay skin selection can be changed in the lobby;
- the selected Swiftplay slot/banner follows the chosen carousel skin;
- reconnect-aware lifecycle behavior remains intact.

Regression coverage was added for:

- League builds before/after the LTK cutoff;
- unknown/invalid League build timestamps;
- Swiftplay late skin tracking;
- retryable matchmaking preparation;
- reconnect-aware game lifetime;
- active overlay-worker race protection;
- Swiftplay selected-banner synchronization.

## Installer

**File**

`PersonalSkinManager_Setup.exe`

**Size**

`28,162,646 bytes`

**SHA-256**

`4E1FB68959577213D773C98A8803850122848A838E0983B1397B5B6A1208C7FB`

PSM v1.0.3 remains an all-in-one installer. Existing PSM user data and downloaded content under `%LOCALAPPDATA%\Rose` are preserved by the installer/uninstaller design.

## Update channel

GitHub Releases is the canonical public distribution source for v1.0.3.

The signed in-app updater is a separate channel and may remain on an earlier published manifest until a new manifest is signed. This does not affect manual installation of the v1.0.3 GitHub Release.

## Project

PSM is derived from the open-source Rose project by Alban and Florent and preserves upstream and third-party attribution.

Website: `https://psm.vanarquilos.dev`

Source: `https://github.com/vanarquilos/PersonalSkinManager-Updates`
