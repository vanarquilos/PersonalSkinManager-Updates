# Changelog

## [1.0.3] - 2026-10-05

### Fixed
- Fixed the October 4 runtime cutoff regression that caused selected skins to fall back to the default skin.
- Changed LTK compatibility validation to compare the installed League executable build timestamp against the DLL build cutoff instead of comparing the cutoff against the current wall clock.
- Fixed injection readiness reporting so PSM no longer reports the injection system as ready when runtime validation fails.
- Fixed a Swiftplay timing race where Matchmaking could fire before the selected skin reached PSM and permanently suppress the later valid selection.
- Swiftplay now retries preparation while searching, re-arms on re-queue, and has ChampSelect, GameStart, and InProgress overlay fallbacks.
- Swiftplay now uses the same reconnect-aware game-lifetime stop semantics as the regular injection path.
- Fixed the Swiftplay selected-slot banner so changing to an unowned/custom skin visually follows the active carousel pick instead of keeping the owned/default splash.

### QA
- Live Practice Tool QA confirmed the hotfix restores in-game skin injection on the current League build.
- Added regression coverage for League-build-aware LTK cutoff handling.
- Added code-level regression coverage for Swiftplay late-tracking retries, reconnect-aware lifecycle, and selected-banner synchronization.
- Live Swiftplay QA confirmed queue-480 modskin injection works; the remaining banner mismatch found during that test was fixed afterward.

## [1.0.2] - 2026-09-26

### Fixed
- Restored compatibility with the current League version for supported runtime flows.
- Fixed injection timing and lifecycle reliability.
- Fixed Reconnect and game-repair issues tied to the retired runtime path.
- Improved overlay cleanup and error handling.

### Changed
- Updated PSM to the current supported runtime path.
- Added current WAD compatibility handling.
- Bundled required runtime components in the installer.
- Refreshed the Settings UI with cleaner section icons and visual hierarchy.

## [1.0.1]
- Signed stable updater bootstrap and previous stable release baseline.
