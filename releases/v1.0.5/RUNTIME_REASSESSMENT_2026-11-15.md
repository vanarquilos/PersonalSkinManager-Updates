# PSM v1.0.5 runtime feasibility reassessment — 2026-11-15

**Outcome: upstream has moved forward, but PSM's direct-host architecture is not proven compatible and a release is still NO-GO.**

## Public evidence

1. [LeagueToolkit issue #976](https://github.com/LeagueToolkit/ltk-manager/issues/976), the exact 16.21.834.2754 / October 30 game timestamp incompatibility, **closed November 3, 2026**. Closure alone does not authenticate a particular DLL for the installed/current League build.
2. [Official LeagueToolkit releases](https://github.com/LeagueToolkit/ltk-manager/releases) list **LTK Manager 1.33.0, released November 4, 2026**. The patcher DLL is delivered separately; manager version is not the patcher digest or current build support.
3. [Alban1911/Rose README](https://github.com/Alban1911/Rose/blob/main/README.md), section `LTK Manager Requirement`, states Rose **requires an LTK Manager installation** and drives it through a bridge; users need not open the manager manually. This supersedes our older assumption that the present Rose release is standalone and can operate solely by copying host/DLL files. Rose's current `injection/overlay/ltf_session.py` uses its `LtkBridge` path.
4. [LeagueToolkit issue #923](https://github.com/LeagueToolkit/ltk-manager/issues/923) contains a LeagueToolkit contributor's explicit statement that patcher host verification is intended to **block third-party apps from directly using its DLL**. Do not attempt to disable, spoof or bypass verification; the old PSM `injection/overlay/ltk_host.py` direct-host route cannot be considered release ready just because the patcher cutoff becomes valid.
5. [LeagueToolkit issue #1082](https://github.com/LeagueToolkit/ltk-manager/issues/1082), opened November 14 and still open on November 15, reports a `429 rate_limited` error retrieving the patcher DLL even with LTK Manager 1.33.0. This is one affected user's report, not proof that the delivery service fails for every user. Treat delivery failures separately from game-build cutoff or PSM application errors.

## Engineering decision

Do **not** claim PSM v1.0.5 is fixed by provisioning an official updated host/DLL pair without testing accepted host verification and visible in-game rendering. The current explicit PSM user preference is **no separate LTK Manager installation**. That requirement conflicts with Alban1911/Rose's **current** runtime dependency.

Two legitimate options:

- **Option A — manager-backed integration:** if the user agrees to a one-time official LTK Manager installation and the integration method is permitted, redesign PSM to orchestrate the manager via documented/authorized interfaces, not by bypassing host verification. PSM remains the daily UI and user need not manually open the manager. Current source lacks that integration; it needs design, code, Windows QA and approval.
- **Option B — strictly standalone:** retain PSM-only UI and installation but wait for explicit upstream support/permission for a third-party patcher SDK/runtime, or use another independently supported and authorized rendering approach. Do not claim official LeagueToolkit's current patcher is standalone third-party software.

## Safe local next check

Check the **current** installed League executable version/date, the presence of an official delivered host/DLL cache, and diagnostics from an **official** LTK Manager if one is installed. Use the existing read-only script `scripts/audit_official_ltk_delivery_cache_v105.py` from a synchronized QA worktree. It does not contact the delivery service or read tokens. If a current DLL exists, verify its digest, cutoff and provenance, but do not start raw host testing as a bypass of upstream enforcement.

If official LTK Manager itself reports `429 rate_limited`, direct remediation belongs to upstream delivery service; don't repeatedly hammer the endpoint, copy service tokens or invent a direct download URL. Check upstream issue #1082 and official manager diagnostics.

## v1.0.5 release status

Build/installer source fixes remain on `rebuild/v1.0.5-rose-compatible` / PR #19. As of November 15, 2026, there is **no locally verified private Windows build**, no confirmed current DLL that accepts PSM's host, no accepted manager-backed integration, and no visible skin rendering. Keep the PR draft. Neither a closed upstream issue nor a version bump satisfies the release gates in `FINALIZATION_GATE_2026-11-02.md`.
