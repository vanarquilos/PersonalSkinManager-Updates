# Personal Skin Manager v1.0.4

**League Compatibility Update — Community Testing**

PSM v1.0.4 carries the current scanner-timing and overlay-cleanup fixes needed after v1.0.3.

## What changed

- The LTK scanner now starts when the loadout countdown begins instead of waiting until the final skin-injection trigger.
- The actual injection reuses that pre-armed scanner once the overlay is ready.
- Dead pre-armed scanner sessions are replaced before the next game.
- Unused scanners are stopped when a countdown ends without an injection, when default skin is selected, or when injection setup fails.
- Overlay cleanup now keeps the overlay directory itself in place while clearing its contents, preventing the already-configured scanner from losing its prefix path.

## Compatibility basis

This ports the relevant current Rose fixes:

- `0cf810ee4731b45e6917dfa66fa7b620c280f181` — start the LTK patcher with the loadout countdown
- `5bf9169837d7d04c4c7fced99dde293110f142ff` — keep the overlay folder while cleaning it

The v1.0.3 build-aware LTK cutoff validation remains in place. PSM still refuses a runtime that does not support the installed League build; this release does not bypass that compatibility boundary.

## Regression coverage

Added tests for:

- scanner pre-arm at countdown start
- scanner reuse during actual injection
- dead-session replacement
- unused-session cleanup
- overlay-directory preservation during pre/post-game cleanup

The new checks are included in both the manual public-source workflow and the Windows live-QA script.

## Published pre-release / community-testing status

v1.0.4 was published on October 19, 2026 as an openly labeled public GitHub pre-release for community testing. Maintainer-reported checks at the time of release preparation:

- Normal skin injection: working in a live test.
- Swiftplay lobby skin selection: working in a live test.
- Swiftplay in-game skin injection: **not verified** on v1.0.4.
- Automated regression tests: included in source and must pass during the release build.
- Compatibility with every League build, queue, and PC configuration is not guaranteed.

Please report issues through https://psm.vanarquilos.dev (Feedback / Support) with the mode, selected skin, PSM version, and what happened. Do not share passwords or session tokens.

The installer was built from v1.0.4 source and trusted local runtime files. The published GitHub Release asset was verified against the checksum and size below.

## Verified installer artifact

- Filename: `PersonalSkinManager_Setup.exe`
- Size: **28,165,060 bytes**
- SHA-256: `C31EAE458757C2EF9B3ADE8DDDCB6C791F785CBAEEA34C781622768AD407E7EA`
- Source commit: `d9022c756348d5a649eb6a21d66798db65810688`
- [Official v1.0.4 GitHub Release](https://github.com/vanarquilos/PersonalSkinManager-Updates/releases/tag/v1.0.4)

This is a pre-release; Swiftplay in-game injection is unverified and compatibility is not guaranteed across configurations.

## Distribution

GitHub Releases remains the canonical public distribution channel.

The signed in-app updater is a separate channel and may continue to lag while the existing signing-key issue remains unresolved.
