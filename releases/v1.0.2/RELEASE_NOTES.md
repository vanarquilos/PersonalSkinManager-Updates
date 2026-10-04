# Personal Skin Manager v1.0.2

## League Compatibility Update

PSM v1.0.2 updates the runtime used by Personal Skin Manager for the current League version.

### Fixed
- Improved supported skin/mod runtime compatibility.
- Fixed injection timing issues.
- Fixed Reconnect and game-repair problems tied to the previous runtime.
- Improved overlay handling and cleanup.

### Improved
- Updated the runtime used by PSM.
- Refreshed the Settings UI with cleaner icons and layout.
- All required runtime components are included in the installer, so no manual DLL setup is needed.

### QA
Final live Practice Tool QA confirmed the Rose-compatible runtime path end to end: pre-launch scanning, game hold/resume, overlay build, current WAD-header rebase, LTK DLL attachment, overlay verification, WAD redirection, in-game skin application, and clean teardown. The final packaged v1.0.2 installer still requires a clean-install verification before publication.

Existing PSM user data and downloaded content are preserved when updating from v1.0.1.

Thanks to everyone who reported the issue and waited while the compatibility update was investigated and tested.
