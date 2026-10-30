# Personal Skin Manager v1.0.5 — Release Notes

> **PREPARED, NOT PUBLISHED.** Publish this text only when an installer built from the reviewed source, compliant with every bundled third-party runtime license, has passed its own Windows gameplay QA and the asset SHA-256 is recorded.

This update focuses on skin-selection reliability and compatibility with League of Legends client transitions. It preserves the Personal Skin Manager interface and the tested Rose-style runtime workflow.

## What's new

- Improved retry behavior when the local League Client API restarts or changes connection port.
- Improved game-process monitoring when a process exits between detection and suspension.
- Retained the early LTK scanner start and overlay-directory lifecycle fixes from v1.0.4.
- Improved handling and diagnostics for skin-selection transitions, including Swiftplay.
- Added clearer local diagnostics for patcher/runtime errors and overlay preparation, without treating overlay creation alone as proof of skin rendering.
- Improved packed WAD/Fantome inspection and troubleshooting tools for private compatibility testing.

## Working baseline

The maintainer reports that the **combined v1.0.5 private installer**, built from the source branch `fix/v1.0.5-rose-local-rollback`, detects League and successfully renders selected non-default skins on their Windows installation. This was reported on **October 30, 2026**.

That installer is a **private, upstream-signed LTK test build**. It is **not itself approved for redistribution**. The packaged build that is ultimately published may differ because the LTK Patcher License requires removal of LeagueToolkit's upstream signatures unless the distributor has written authorization. Any altered/distributable build needs its own independent installed gameplay QA. Do not claim that the private build's success verifies the as-yet-unbuilt public artifact.

## Compatibility and limitations

- Compatibility depends on the League game patch and on the LTK host/DLL and CSLOL `mod-tools.exe` companion DLLs shipped with the exact tested installer.
- A selected skin shown in the UI does **not** guarantee an in-game skin change. Test in Practice Tool before joining an ordinary game.
- Game updates can introduce incompatibilities, including changes to WAD or material formats.
- League Client integration and visual in-game rendering are separate checks.
- The project is independent of Riot Games and LeagueToolkit; neither endorses this software.
- Keep the previously published v1.0.4 installer available until v1.0.5's public artifact passes its own tests.

## Reporting a problem

Please include the PSM version, League patch, game mode, the stage that failed (client detection / mod-tools overlay / LTK host / game rendering), and a sanitized troubleshooting report. Never share League Client lockfile passwords, local authentication tokens, or private signing files.

Feedback: https://github.com/vanarquilos/PersonalSkinManager-Updates/issues

## Open-source and third-party license notices

- Rose original project attribution and license are retained.
- Pengu Loader and CSLOL components retain their own applicable upstream licensing.
- LTK patcher host/DLL: see `licenses/LTK-PATCHER-LICENSE.md`. LeagueToolkit's original signatures must not be redistributed inside PSM unless separately authorized in writing. Otherwise, use separately staged unsigned copies and independently verify the exact installed artifact.
- The PSM root license does not relicense bundled third-party runtimes.

## Release integrity

The exact **public installer SHA-256, byte count, reviewed source commit, verified bundled-file hashes, final QA result, and release artifact filename** are intentionally omitted until a compliant candidate exists and those values have been independently measured. Do not copy the hash of a private signed installer or older release.

The current stable updater manifest is not changed by these release notes.
