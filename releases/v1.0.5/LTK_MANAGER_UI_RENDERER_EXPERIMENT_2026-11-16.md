# PSM v1.0.5 — Experimental LTK Manager UI rendering session

## Scope

This is a **real manager-backed session starter**, not an LTK DLL injector.
It uses Windows accessibility to operate the **official LTK Manager 1.33**
profile selector and **Start** button, and can stop the patcher and restore
the previously active profile.

It does **not yet** wire into PSM's automatic champion-select events,
provision skins, or prove that a selected skin appears in-game. It is a
private source-level experiment, not a publishable v1.0.5 renderer.

Why this approach? LTK Manager's documented public deep links do not
expose external patcher control. The app itself exposes a named profile
switcher and a Start/Stop control. Its own source defines Ctrl+2 for the
library and Ctrl+P as a patcher toggle. We use the buttons rather than
blindly toggling Ctrl+P so we do not stop an existing user patcher.

Sources:
- https://github.com/LeagueToolkit/ltk-manager/blob/main/src/modules/library/components/ProfileSelector/index.tsx
- https://github.com/LeagueToolkit/ltk-manager/blob/main/src/modules/keys/utils/commands/app.ts
- https://github.com/LeagueToolkit/ltk-manager/blob/main/src/modules/library/api/useLibraryHotkeys.ts
- https://github.com/LeagueToolkit/ltk-manager/blob/main/docs/ux/LIBRARY.md

## What this does

1. Locate official LTK Manager exe under Program Files or LocalAppData.
2. Read-only inspect the active profile and its enabled-mod IDs in the
   official v2 library index (no direct JSON edits).
3. Select the requested named profile through accessible UI controls.
4. Verify that LTK saved the new active profile.
5. Click official **Start**, wait for official **Stop** to become visible.
6. On cleanup, click **Stop**, verify **Start**, then restore the user's
   previous active profile. Never terminate a user-owned Manager instance.

No signatures are removed. No native bridge is injected, no process parent
is forged and no host verification or Riot integrity control is modified.

## Prerequisites

LTK Manager 1.33.0 must be installed. The user must create a profile with
**at least one enabled mod that LTK itself accepts**. Unsupported official
skin substitutions can be rejected by LTK's content checks. PSM's older
official/locked-skin catalog does not automatically translate into accepted
LTK mod packages.

Requires a Python environment with PSM dependencies and optional
pywinauto installed. This module intentionally does not add the optional
dependency to PSM's production PyInstaller build.

LTK Manager must be running as a normal desktop application, using the
classic Start/Stop patcher flow; its Modern Play mode may launch League
unexpectedly and is not supported by this experiment.

## Private Windows source-level run

From the isolated QA worktree, not the protected rollback:

    python -B -m pip install pywinauto==0.6.9
    python -B -m unittest -v tests.test_v105_ltk_manager_ui_renderer
    python -B scripts/ltk_manager_renderer_v105.py --inspect

Then, ONLY if an actual accepted mod has been enabled in a named profile:

    python -B scripts/ltk_manager_renderer_v105.py --profile "YOUR EXACT PROFILE NAME" --run

This script actually selects the LTK profile and clicks Start. It stays
open until Ctrl+C, then requests patcher stop and profile restoration.
If UI element accessibility differs on the user's machine, it fails
rather than clicking guessed screen coordinates.

**You cannot infer in-game rendering from a Start/Stop UI response**.
Observe the skin in a Practice Tool game, inspect LTK diagnostics, and
confirm the vendor has not blocked the selected content.

A separate explicit JSON mapping can associate PSM skin keys to profiles:

    {
      "skin_266001": "PSM skin_266001"
    }

Pass it with:

    python -B scripts/ltk_manager_renderer_v105.py --skin-key skin_266001 --mapping "C:\Path\psm-ltk-mapping.json" --run

The script only reads this file; it never modifies LTK's library index.

## Remaining work before release

- Verify the accessible controls and that profile switching and patcher
  startup work on an actual LTK Manager 1.33.0 installation.
- Integrate profile selection and session lifecycle into PSM champion
  select; prearm during countdown rather than at the final 300 ms.
- Handle reconnects, phase changes and failures without leaving the
  patcher running or changing user profiles.
- Determine a legitimate way to prepare the exact PSM skin under LTK's
  content and mod-health rules. Current PSM official/locked skin routing
  cannot be called working with this bridge.
- Verify in-game rendering. No public v1.0.5 release before then.

Original rollback b06fa4b, draft PRs 19-21, the stable updater and public
v1.0.4 remain untouched.
