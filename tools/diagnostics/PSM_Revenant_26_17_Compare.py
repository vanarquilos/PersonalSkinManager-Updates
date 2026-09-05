#!/usr/bin/env python3
"""
PSM Revenant Reign Viego — current League baseline comparator.

READ-ONLY:
- Does not modify League, PSM, Fantome files, registry, or processes.
- Reads WAD headers only; it does not inject, patch, suspend, or alter the game.
- Writes one TXT report to the Desktop.

Usage:
    python .\PSM_Revenant_26_17_Compare.py

Optional if auto-detection misses League:
    python .\PSM_Revenant_26_17_Compare.py --game-dir "C:\Riot Games\League of Legends\Game"
"""
from __future__ import annotations

import argparse
import configparser
import os
import re
import struct
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

USER = Path(os.environ.get("USERPROFILE", str(Path.home())))
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", USER / "AppData" / "Local"))
PROGRAMDATA = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))

FANTOME = LOCALAPPDATA / "Rose" / "skins" / "234" / "234043" / "234043.fantome"
OUT = USER / "Desktop" / "PSM_Revenant_26_17_Compare.txt"

TARGETS = {
    0xF0371E1AA2B8983F: "assets/sounds/wwise2016/sfx/shared/misc_gameplay_killstreak_sfx_audio.bnk",
    0x704B0292633A00A7: "gameplay.bin",
    0xF221D11BC2E0CAE6: "gameplay.viegoskin43viewcontroller.bin",
    0x26162BD67C7EB042: "data/characters/viego/animations/skin0.bin",
    0x50AA7AC5B646F513: "data/characters/viego/animations/skin43.bin",
    0x4EDF655BF6F3D880: "data/characters/viego/skins/skin0.bin",
    0x12BCB8373C9B2D16: "data/characters/viego/skins/skin43.bin",
}


def fmt_checksum(v: int) -> str:
    return f"{v:016x}"


def parse_v3_entries_from_bytes(data: bytes) -> List[dict]:
    if len(data) < 272 or data[:2] != b"RW" or data[2] != 3:
        return []
    count = struct.unpack_from("<I", data, 268)[0]
    table_end = 272 + count * 32
    if table_end > len(data):
        return []
    out = []
    off = 272
    for _ in range(count):
        path_hash, data_off, csz, usz = struct.unpack_from("<QIII", data, off)
        type_sub = data[off + 20]
        dtype = type_sub & 0x0F
        subchunks = type_sub >> 4
        duplicate = data[off + 21]
        first_subchunk = struct.unpack_from("<H", data, off + 22)[0]
        checksum = struct.unpack_from("<Q", data, off + 24)[0]
        out.append(
            {
                "path_hash": path_hash,
                "data_offset": data_off,
                "compressed_size": csz,
                "uncompressed_size": usz,
                "type": dtype,
                "subchunks": subchunks,
                "duplicate": duplicate,
                "first_subchunk": first_subchunk,
                "checksum": checksum,
            }
        )
        off += 32
    return out


def read_v3_entry_table(path: Path) -> Tuple[Optional[Tuple[int, int]], List[dict]]:
    try:
        with path.open("rb") as f:
            head = f.read(272)
            if len(head) < 272 or head[:2] != b"RW":
                return None, []
            major, minor = head[2], head[3]
            if major != 3:
                return (major, minor), []
            count = struct.unpack_from("<I", head, 268)[0]
            if count > 5_000_000:
                return (major, minor), []
            table = f.read(count * 32)
            if len(table) != count * 32:
                return (major, minor), []
            data = head + table
            return (major, minor), parse_v3_entries_from_bytes(data)
    except (OSError, struct.error):
        return None, []


def detect_from_riot_metadata() -> Optional[Path]:
    candidates = [
        PROGRAMDATA
        / "Riot Games"
        / "Metadata"
        / "league_of_legends.live"
        / "league_of_legends.live.product_settings.yaml",
        PROGRAMDATA
        / "Riot Games"
        / "Metadata"
        / "league_of_legends.live"
        / "league_of_legends.live.product_settings.json",
    ]
    for meta in candidates:
        if not meta.exists():
            continue
        try:
            text = meta.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        keys = (
            "product_install_full_path",
            "product_install_root",
            "product_install_path",
        )
        for key in keys:
            patterns = [
                rf'{re.escape(key)}\s*:\s*"([^"]+)"',
                rf"{re.escape(key)}\s*:\s*'([^']+)'",
                rf'{re.escape(key)}"\s*:\s*"([^"]+)"',
                rf"{re.escape(key)}\s*:\s*([^\r\n]+)",
            ]
            for pat in patterns:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if not m:
                    continue
                raw = m.group(1).strip().strip('"').strip("'")
                raw = raw.replace("\\\\", "\\")
                base = Path(raw)
                probes = [base, base / "Game", base / "League of Legends" / "Game"]
                for p in probes:
                    if p.exists() and p.is_dir():
                        if p.name.lower() == "game" or (p / "DATA").exists():
                            return p
    return None


def detect_from_psm_config() -> Optional[Path]:
    cfg = LOCALAPPDATA / "Rose" / "config.ini"
    if not cfg.exists():
        return None
    cp = configparser.ConfigParser()
    try:
        cp.read(cfg, encoding="utf-8")
    except Exception:
        return None
    candidate_keys = {
        "game_dir",
        "game_path",
        "league_path",
        "league_dir",
        "league_game_dir",
        "lol_path",
        "install_path",
    }
    for section in cp.sections():
        for key, val in cp.items(section):
            if key.lower() not in candidate_keys:
                continue
            base = Path(os.path.expandvars(val.strip().strip('"')))
            for p in (base, base / "Game"):
                if p.exists() and p.is_dir():
                    if p.name.lower() == "game" or (p / "DATA").exists():
                        return p
    return None


def detect_common_paths() -> Optional[Path]:
    drives = [f"{c}:\\" for c in "CDEFGHIJKLMNOPQRSTUVWXYZ"]
    rels = [
        Path("Riot Games") / "League of Legends" / "Game",
        Path("Games") / "Riot Games" / "League of Legends" / "Game",
        Path("Program Files") / "Riot Games" / "League of Legends" / "Game",
    ]
    for d in drives:
        root = Path(d)
        if not root.exists():
            continue
        for rel in rels:
            p = root / rel
            if p.exists() and p.is_dir():
                return p
    return None


def detect_game_dir(arg: Optional[str]) -> Tuple[Optional[Path], str]:
    if arg:
        p = Path(os.path.expandvars(arg)).expanduser()
        if p.exists():
            return p, "--game-dir"
    for fn, label in (
        (detect_from_riot_metadata, "Riot metadata"),
        (detect_from_psm_config, "PSM config"),
        (detect_common_paths, "common install path"),
    ):
        p = fn()
        if p:
            return p, label
    return None, "not found"


def load_custom_entries() -> Tuple[Dict[int, dict], List[str]]:
    found: Dict[int, dict] = {}
    notes: List[str] = []
    if not FANTOME.exists():
        notes.append(f"Fantome missing: {FANTOME}")
        return found, notes

    try:
        with zipfile.ZipFile(FANTOME, "r") as z:
            for member in (
                "WAD/Common.wad.client",
                "WAD/UI.wad.client",
                "WAD/Viego.wad.client",
            ):
                try:
                    data = z.read(member)
                except KeyError:
                    notes.append(f"Missing member: {member}")
                    continue
                if data[:2] != b"RW":
                    notes.append(f"{member}: not a WAD")
                    continue
                version = (data[2], data[3])
                if version[0] != 3:
                    notes.append(
                        f"{member}: unsupported WAD {version[0]}.{version[1]} for this comparator"
                    )
                    continue
                entries = parse_v3_entries_from_bytes(data)
                notes.append(f"{member}: WAD {version[0]}.{version[1]}, {len(entries)} entries")
                for e in entries:
                    if e["path_hash"] in TARGETS:
                        item = dict(e)
                        item["wad"] = member
                        found[e["path_hash"]] = item
    except (OSError, zipfile.BadZipFile) as exc:
        notes.append(f"Fantome read error: {type(exc).__name__}: {exc}")
    return found, notes


def scan_game_wads(game_dir: Path) -> Tuple[Dict[int, List[dict]], int, List[str]]:
    found: Dict[int, List[dict]] = {h: [] for h in TARGETS}
    errors: List[str] = []
    count = 0
    try:
        wad_paths = list(game_dir.rglob("*.wad.client"))
    except OSError as exc:
        return found, 0, [f"WAD enumeration failed: {exc}"]

    for wad in wad_paths:
        count += 1
        version, entries = read_v3_entry_table(wad)
        if version is None or version[0] != 3:
            continue
        for e in entries:
            h = e["path_hash"]
            if h in TARGETS:
                item = dict(e)
                try:
                    item["wad"] = str(wad.relative_to(game_dir))
                except ValueError:
                    item["wad"] = str(wad)
                found[h].append(item)
    return found, count, errors


def describe_entry(prefix: str, e: dict) -> List[str]:
    return [
        f"{prefix} WAD: {e.get('wad')}",
        f"{prefix} compressed: {e['compressed_size']}",
        f"{prefix} uncompressed: {e['uncompressed_size']}",
        f"{prefix} type: {e['type']}",
        f"{prefix} checksum: {fmt_checksum(e['checksum'])}",
        f"{prefix} duplicate: {e['duplicate']}",
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", default=None)
    args = ap.parse_args()

    lines: List[str] = [
        "Personal Skin Manager — Revenant Reign Viego current-League comparator",
        "READ-ONLY: no League/PSM/process modification is performed.",
        "",
        f"Fantome: {FANTOME}",
        f"Fantome exists: {FANTOME.exists()}",
        "",
    ]

    custom, custom_notes = load_custom_entries()
    lines.append("=== CUSTOM 234043 PACKAGE ===")
    lines.extend(custom_notes)
    lines.append(f"Resolved target entries in package: {len(custom)} / {len(TARGETS)}")
    lines.append("")

    game_dir, detection = detect_game_dir(args.game_dir)
    lines.append("=== LEAGUE INSTALL ===")
    lines.append(f"Detection: {detection}")
    lines.append(f"Game directory: {game_dir if game_dir else 'NOT FOUND'}")
    lines.append("")

    if not game_dir:
        lines += [
            "STOP: League Game directory was not auto-detected.",
            "Re-run with:",
            r'python .\PSM_Revenant_26_17_Compare.py --game-dir "C:\Riot Games\League of Legends\Game"',
            "",
        ]
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("[WARN] League Game directory not found.")
        print(f"[OK] Report: {OUT}")
        return 2

    game, wad_count, scan_errors = scan_game_wads(game_dir)
    lines.append("=== GAME WAD SCAN ===")
    lines.append(f"WAD files scanned: {wad_count}")
    for err in scan_errors:
        lines.append(f"ERROR: {err}")
    lines.append("")

    lines.append("=== TARGET COMPARISON ===")
    for h, name in TARGETS.items():
        lines.append(f"[{h:016x}] {name}")
        ce = custom.get(h)
        ges = game.get(h, [])
        lines.append(f"Custom present: {'YES' if ce else 'NO'}")
        if ce:
            lines.extend(describe_entry("  Custom", ce))
        lines.append(f"Current League matches: {len(ges)}")
        for idx, ge in enumerate(ges, 1):
            lines.extend(describe_entry(f"  League #{idx}", ge))
        if ce and ges:
            same_checksum = any(ce["checksum"] == ge["checksum"] for ge in ges)
            same_uncompressed = any(
                ce["uncompressed_size"] == ge["uncompressed_size"] for ge in ges
            )
            lines.append(f"  Any identical entry checksum: {'YES' if same_checksum else 'NO'}")
            lines.append(
                f"  Any identical uncompressed size: {'YES' if same_uncompressed else 'NO'}"
            )
        lines.append("")

    missing = [name for h, name in TARGETS.items() if not game.get(h)]
    lines.append("=== SUMMARY ===")
    lines.append(f"Targets found in current League: {len(TARGETS) - len(missing)} / {len(TARGETS)}")
    if missing:
        lines.append("Targets not found:")
        for name in missing:
            lines.append(f"  - {name}")
    else:
        lines.append("All seven target paths were found in the current League installation.")
    lines.append("")
    lines.append("Interpretation note:")
    lines.append("A different checksum is expected for files intentionally modified by the skin.")
    lines.append("This report is for establishing the exact current-game baseline, not for declaring")
    lines.append("a modified entry bad solely because its checksum differs.")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] League Game: {game_dir}")
    print(f"[OK] WAD files scanned: {wad_count}")
    print(f"[OK] Report written to: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
