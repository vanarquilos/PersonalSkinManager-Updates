# Personal Skin Manager v1.0.3

## Runtime Compatibility Hotfix

PSM v1.0.3 fixes the October 4, 2026 runtime cutoff regression that could make a correctly selected skin load as the default skin in-game.

### Fixed
- Fixed LTK runtime compatibility validation using the current wall clock instead of the installed League build.
- PSM now compares the League executable's PE build timestamp against the LTK DLL's supported build cutoff.
- Fixed the injection system reporting itself as ready after runtime validation had already failed.

### What did not change
- Skin/chroma selection behavior is unchanged.
- The Rose-compatible pre-launch scanner lifecycle remains in place.
- Current WAD-header compatibility handling remains in place.
- The bundled LTK runtime pair is unchanged in this hotfix unless later QA proves a binary refresh is required.

### QA
Live Practice Tool QA on October 5 confirmed that the hotfix restores working in-game skin injection on the current installed League build.

Regression tests cover:
- League builds older than the LTK cutoff remain supported.
- League builds newer than the cutoff are rejected.
- Unknown/invalid game-build timestamps are not falsely rejected before the LTK host can report its own status.

### Updating
v1.0.3 is intended to replace v1.0.2 as the public compatibility build after installer QA is complete.

The signed in-app update manifest is a separate release-system concern and remains deferred until the existing signing key can be used again or a deliberate key-rotation/bootstrap strategy is implemented.

Existing PSM user data and downloaded content under `%LOCALAPPDATA%\Rose` are preserved by the installer/uninstaller design.
