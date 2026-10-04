# Changelog

## [1.0.3] - 2026-10-05

### Fixed

#### Runtime compatibility
- Fixed the October 4 runtime cutoff regression that could cause selected skins to fall back to the default skin.
- Replaced wall-clock LTK expiration validation with installed-League-build validation.
- PSM now compares the League executable PE build timestamp against the LTK DLL build cutoff.
- Fixed injection readiness reporting so PSM no longer reports the injection system as ready after runtime validation has failed.

#### Swiftplay
- Fixed a Swiftplay queue 480 timing race where Matchmaking could begin before the selected skin reached PSM.
- Failed early Swiftplay preparation attempts now remain retryable instead of permanently marking injection as triggered.
- Swiftplay preparation now retries while matchmaking is searching.
- Swiftplay overlay state now re-arms correctly for re-queues and subsequent games.
- Added independent Swiftplay fallback handling at ChampSelect, GameStart, and InProgress.
- Added WebSocket/phase coordination so duplicate fallback triggers do not race an active overlay worker.
- Prepared Swiftplay mods are restored after failed overlay attempts so later fallback phases can retry.
- Swiftplay now uses the same reconnect-aware per-game stop lifecycle as the regular injection path.
- Fixed the Swiftplay selected-slot banner so unowned/custom-selected skins visually follow the active carousel choice.

### Changed
- Runtime validation now follows the League build semantics used by the current compatible Rose/LTK path.
- Swiftplay injection lifecycle is aligned more closely with the regular PSM overlay lifecycle while retaining its dedicated lobby-pick tracking flow.
- Public release documentation now reflects GitHub Releases as the canonical v1.0.3 distribution source while the signed in-app updater remains a separate channel.

### QA
- Live Practice Tool QA passed with working in-game skin injection.
- Live Swiftplay queue 480 QA passed.
- Swiftplay lobby skin changing passed.
- Swiftplay selected-slot/banner synchronization passed.
- Added regression coverage for League-build-aware LTK cutoff behavior.
- Added regression coverage for invalid/unknown League build timestamps.
- Added regression coverage for Swiftplay late-tracking retries.
- Added regression coverage for reconnect-aware game lifetime.
- Added regression coverage for active overlay-worker race protection.
- Added regression coverage for Swiftplay selected-banner synchronization.

### Release artifact
- Installer: `PersonalSkinManager_Setup.exe`
- Size: `28,162,646 bytes`
- SHA-256: `4E1FB68959577213D773C98A8803850122848A838E0983B1397B5B6A1208C7FB`

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
