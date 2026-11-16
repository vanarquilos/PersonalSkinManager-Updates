# PSM v1.0.5 — official LTK Manager custom-mod handoff (private QA)

**Status: source-only development, NOT a working PSM skin renderer and NOT an approved release.**

PSM currently has no supported mechanism to control LTK Manager's patcher
sessions. Direct use of the vendor's modern patcher DLL is restricted by
host-verification checks. This change does not bypass those restrictions.

## What IS supported

Official LTK Manager v1.33.0 accepts an existing local .fantome or .modpkg
file as a command-line argument and opens its native import UI. See upstream:

- https://github.com/LeagueToolkit/ltk-manager/blob/main/src-tauri/src/deep_link/files.rs
- https://github.com/LeagueToolkit/ltk-manager/blob/main/docs/adr/0060-mod-file-types-are-registered-per-user-by-the-app.md

The private PSM handoff sends an explicit user-approved local file to the
installed manager, without shell interpolation, DLL copying,
unsigned binaries, game hooking or background automation. The manager alone
decides whether a mod is valid, whether to import it, and when a user enables
it and starts the patcher.

**This is NOT automatic PSM skin selection.** There is no published external
LTK Manager control route to select a mod and start a patcher session.
Upstream ltk:// actions permit install/install-list/settings, not patcher
control. A successful handoff means only that the request was made, never
that the mod imported or rendered.

## Local PowerShell usage

Run from a NEW isolated QA checkout containing this branch, not the protected
fix/v1.0.5-rose-local-rollback original checkout:

    python -B -m unittest -v tests.test_v105_ltk_manager_handoff
    python -B scripts/ltk_manager_handoff_v105.py --status

After locally confirming the exact archive and approving an external action:

    python -B scripts/ltk_manager_handoff_v105.py --import-custom-mod "C:\Path\YourOwnCustomMod.fantome" --confirm

For the standard official Manager UI only:

    python -B scripts/ltk_manager_handoff_v105.py --open-manager --confirm

If LTK Manager is installed elsewhere, specify an existing manager exe with
--manager-exe "C:\Path\ltk-manager.exe". The filename and existence are
checked; **this helper does not authenticate the publisher or certificate**.
Prefer the official installed location and verify its provenance independently.

The CLI never starts the patcher, injects into a process, selects paid/locked
Riot cosmetics, changes vendor security settings, or copies LTK files.

## Remaining gates

1. Verify the official manager can import and apply a permitted independent
   custom cosmetic mod on the actual installed League build.
2. Obtain a documented and approved third-party session-control interface
   (or an independently supported rendering engine) before implementing
   automatic PSM champion/skin selection.
3. Implement per-game mod ownership, prewarming, state restore, handling of
   disabled/removed mods, reconnect and honest success/error reporting.
4. Run Windows native tests, full installed QA, gameplay checks, content-policy
   review and release-signature review independently.
5. Leave public v1.0.4, the signed stable updater manifest and the existing
   private rollback completely untouched until all gates pass.
