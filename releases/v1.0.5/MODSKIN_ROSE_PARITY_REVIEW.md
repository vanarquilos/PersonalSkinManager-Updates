# PSM v1.0.5 — Modskin pipeline / Rose comparison

Reviewed: 2026-10-27 (Asia/Manila). This is a source-level parity review, **not a verified working in-game skin**.

## Checked sources

- [Rose main](https://github.com/Alban1911/Rose) (commit `12a0d46bfc63387a39479f395e2724b324d3d095`, 2026-10-22)
  - `injection/core/injector.py`
  - `injection/mods/mod_manager.py`
  - `injection/mods/zip_resolver.py`
  - `injection/overlay/overlay_manager.py`
  - `injection/game/game_monitor.py`
- [LeagueToolkit Manager v1.30.1](https://github.com/LeagueToolkit/ltk-manager/tree/044e6b5fc2dfe78d92dc5a5ada3e0f57f32860f6)
  - `crates/ltk-manager-runtime/src/patcher/host/protocol.rs`
  - `crates/ltk-manager-runtime/src/patcher/dll_lines.rs`
  - `docs/ux/LEAGUE_DIAGNOSTICS.md`
- [LTK Manager v1.30.5](https://github.com/LeagueToolkit/ltk-manager/releases/tag/v1.30.5) was published 2026-10-25; **not** staged or verified by PSM at this time.

## What matches Rose

1. Skin ZIP/Fantome resolution and safe extraction to a named mod folder.
2. `mod-tools.exe mkoverlay` with current game path, mod list, `--noTFT`, and `--ignoreConflict`.
3. LTK scan arming before League game launch and reuse across overlay building.
4. Overlay WAD v3 header rebase from the installed game's archive.
5. Directory-preserving overlay cleanup to avoid invalidating an LTK prefix.
6. Game phase callback allowing reconnects.

## Verified PSM divergence corrected

**Host lifetime on a client-phase end:** Rose's `_run_ltk_patcher` checks whether the actual League game process still exists when the stop callback fires. A client disconnect or early phase transition must not stop the overlay while League is still in-game. PSM previously stopped the host immediately. PSM now checks both `League of Legends.exe` and `League of Legends (TM) Client.exe`, and retains the host while either exists.

**False-positive success:** LeagueToolkit treats `status injected` / `init done` / `redirected wad:` as different evidence. PSM now reports a no-redirection warning and a nonzero skin-application result for an attached, initialized DLL that served no recorded modded WAD during a completed game session. It does not bypass verification or security.

**LTK diagnostic parity:** source `--debug` requests DLL debug logs, and the PSM report detects init, WAD redirection, rejection, and hook failures. Normal/release logging remains INFO.

## User's Windows evidence

- League executable timestamp: `2026-10-16T22:15:09Z`.
- Previous 2026-10-04 cutoff replaced locally with official pinned v1.30.1, cutoff `2026-10-28T23:06:41Z`. This is a **League executable build-timestamp boundary**, not automatic expiration on that calendar date: a later League build may fall outside this runtime.
- Host/DLL SHA256 match in source, built, and installed locations.
- Overlay WAD header rebase 1/1.
- Local DEBUG requested, DLL events observed: 20; last host state `waiting`; attached `True`; DLL overlay initialized.
- WAD redirection events: **0**; verified WAD verdict: unavailable.
- Skin archive file entries: 2, including 1 packed WAD.

These findings do not establish whether the generated WAD contains a modified payload, whether its path matches the game's requested WAD, or whether the host previously stopped prematurely.

## October 29: Aphelios archive inspection correction

Windows focused source tests passed. The selected archive is ZIP-compatible with two files, one packed `WAD/Aphelios.wad.client` of 11,990 bytes, and a valid RW WAD header. The first inspection script printed `recognized_game_relative_path: null` and `matching_game_wad_exists: false`, but these were **a false diagnostic caused by assuming Fantome WAD member names must already be full `DATA/...` paths**. This is not evidence the mod was rejected.

LeagueToolkit's [Fantome format reference](https://github.com/LeagueToolkit/wiki/blob/1964862c571555cca6662575cafe6bd58ae6bf8a/src/content/docs/reference/mod-packages/fantome.mdx) explicitly permits packed `.wad.client` directly under `WAD/`. Such archives store a mod layer's changed chunks and are resolved/rebased by the mod tools, so whole-file size and payload hashes are not valid evidence of mod application. The inspector now reports `package_wad_format: fantome_packed_wad`, `wad_alias`, and advisory filename-matched game archive candidates without mislabeling the format invalid. Added regression tests and fixed the non-fatal invalid-escape docstring warning. Re-run tests on Windows and inspect the new output; **in-game skin rendering is still unverified**.

## Safe remaining QA gates (no installer)

- [ ] Run Python host regression tests (including the added lifecycle and missing-redirection tests) on Windows.
- [ ] Run `python scripts/inspect_v105_skin_wad.py` to check current selected archive's WAD header, path and payload comparison without changing files.
- [ ] Launch PSM source via `scripts/run_live_qa.ps1`, then test ONE supported non-default skin in Practice Tool.
- [ ] Confirm whether the new host stays alive throughout League gameplay when the client phase ends.
- [ ] Confirm at least one `redirected wad:` record and actual visible skin rendering. **No counted redirect = not confirmed.**
- [ ] Once Practice Tool passes, test Swiftplay and reconnects on a subsequent valid runtime.
- [ ] Review any newer LTK host/DLL pair and the upcoming v1.30.1 cutoff before further builds; do not assume the newer LTK Manager UI installer is a compatible patcher.
- [ ] Verify release licensing, signatures and security and rerun build tests separately. Do not publish PSM v1.0.5 until gameplay, runtime and packaging checks pass.

## Safety boundary

No anti-cheat, integrity, WAD-signature, or runtime-cutoff bypass should be introduced. User's pinned official LTK pair is private test material only. Preserve the last published v1.0.4, PR draft, and v1.0.5 source-test workflow until release-ready.
