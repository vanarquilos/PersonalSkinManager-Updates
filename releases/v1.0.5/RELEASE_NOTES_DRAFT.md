# Personal Skin Manager v1.0.5 — release notes (DRAFT)

**Release channel:** GitHub pre-release, pending packaged Windows gameplay and license checks.
**Status:** The maintainer reported a successful local source test on October 29, 2026, using original LTK v1.28.1 binaries. The distributable installer assembled with *unsigned* copies has **not yet been built or gameplay-tested**. Do not present this as a published release.

## Changes in v1.0.5

- Improved League client lifecycle and LCU reconnect handling to reduce lost skin selections between game phases.
- Continued monitoring when a game process exits before it can be suspended.
- Improved Swiftplay and champion-selection error reporting.
- Added a more resilient Fantome skin archive inspector for packed `WAD/<champion>.wad.client` mods.
- Added source diagnostics that distinguish overlay creation, DLL attachment, host verification rejection, and actual observed WAD redirections.
- Added a carefully scoped release-candidate build that packages independently staged LTK binaries after removing upstream Authenticode signatures.

## Compatibility

This candidate uses the original historical patcher host/DLL pair from **LeagueToolkit/ltk-manager v1.28.1**, selected because of community reports of skin rendering with Rose on League 26.21. It may not support every current League game build, champion, skin or material format. The historic pair predates upstream's League 26.21 material-hash parser fix. A matching game-build timestamp is necessary but not sufficient.

**Important:** PSM is independent software, not official LTK Manager, not endorsed by LeagueToolkit, and not endorsed by Riot Games. The modding/injection function is at the user's own risk and may be affected by future game updates or platform restrictions.

## Packaging and attribution

LTK patcher binaries are covered by the [LTK Patcher License](../../licenses/LTK-PATCHER-LICENSE.md). PSM must remove LeagueToolkit's official signing certificate from every separately bundled patcher host/DLL before distribution, unless written permission exists. The release candidate uses isolated, unsigned copies and retains source and license attribution. The installer, if signed, must use PSM's own identity.

## Before publishing

- [ ] Source regression tests pass on Windows.
- [ ] Release-candidate builder completes and produces a fresh installer and SHA-256.
- [ ] Verify no official upstream signature is embedded in the bundled LTK host/DLL.
- [ ] Install **the release-candidate installer**, not just the source checkout; visibly verify a non-default skin in Practice Tool.
- [ ] Verify Swiftplay in-game rendering, reconnects and a second match.
- [ ] Confirm uninstall/reinstall and no secret/runtime provenance leaks.
- [ ] Provide release asset size, SHA-256 and tested League game version.
- [ ] Publish as **pre-release** first and keep existing releases available.
- [ ] Do not change `stable/manifest.json` without the appropriate Ed25519 update-manifest signing process.

**Support and issues:** https://github.com/vanarquilos/PersonalSkinManager-Updates/issues
