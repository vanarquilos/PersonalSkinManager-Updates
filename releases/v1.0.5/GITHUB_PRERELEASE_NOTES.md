# Personal Skin Manager v1.0.5 — Pre-release

This update focuses on improving skin selection reliability, League Client reconnect behavior, and diagnosis of patcher/overlay errors.

### Improvements
- More reliable LCU connection and game-process lifecycle handling.
- Better behavior around Swiftplay and skin-selection transitions.
- Improved packed Fantome WAD inspection and reporting.
- Better error reporting for outdated patchers, verification refusal, overlay failures, and missing WAD redirection.
- Release packaging includes independently staged LTK patcher components with original upstream Authenticode signatures removed in accordance with the LTK Patcher License.

### Compatibility and known limitations
- Tested with the original historical LTK Manager v1.28.1 patcher host/DLL pair; newer League builds or some skins may be incompatible.
- A successfully loaded client skin selection does not guarantee the skin appears in-game. Test in Practice Tool first.
- This is a **pre-release** for public feedback; keep v1.0.4 available as a fallback.
- This project is not affiliated with Riot Games or LeagueToolkit. Modding is at your own risk.

### Reporting issues
Please provide your League patch, game mode, PSM version, whether a non-default skin rendered, and the sanitized diagnostic report. **Never share League Client authentication tokens.**

Feedback: https://github.com/vanarquilos/PersonalSkinManager-Updates/issues

### Third-party license
LTK patcher binaries retain their own license: https://github.com/LeagueToolkit/ltk-manager/blob/main/LTK-PATCHER-LICENSE.md

The updater's stable channel is unchanged by this pre-release.
