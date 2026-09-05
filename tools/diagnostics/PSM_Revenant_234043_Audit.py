#!/usr/bin/env python3
"""
Personal Skin Manager — Revenant Reign Viego 234043 Fantome audit.

READ-ONLY:
- Does not modify or extract the Fantome.
- Does not modify League, PSM, the registry, or any process.
- Writes one TXT report to the Desktop.

The script checks the current Revenant Reign package and, when present, a
previously created backup copy. It validates the Fantome/ZIP structure, CRCs,
member inventory, relevant metadata names, and SHA-256 hashes.
"""
from __future__ import annotations

import hashlib
import os
import zipfile
from collections import Counter
from pathlib import Path

USER = Path(os.environ.get("USERPROFILE", str(Path.home())))
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", USER / "AppData" / "Local"))

CURRENT = LOCALAPPDATA / "Rose" / "skins" / "234" / "234043" / "234043.fantome"
BACKUP = USER / "Desktop" / "PSM_Revenant_Reign_Backup" / "234043" / "234043.fantome"
OUT = USER / "Desktop" / "PSM_Revenant_234043_Audit.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def audit(label: str, path: Path) -> list[str]:
    lines = [f"=== {label} ===", f"Path: {path}"]
    if not path.exists():
        return lines + ["Exists: NO", ""]

    stat = path.stat()
    lines += [
        "Exists: YES",
        f"Size: {stat.st_size} bytes",
        f"SHA256: {sha256(path)}",
    ]

    with path.open("rb") as handle:
        lines.append(f"First 8 bytes: {handle.read(8).hex(' ').upper()}")

    if not zipfile.is_zipfile(path):
        return lines + ["ZIP/Fantome structure: NOT a valid ZIP container", ""]

    lines.append("ZIP/Fantome structure: valid ZIP container")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]

        lines.append(f"Members: {len(infos)}")
        bad = archive.testzip()
        lines.append(f"CRC test: {'PASS' if bad is None else 'FAIL at ' + bad}")

        duplicates = [name for name, count in Counter(names).items() if count > 1]
        lines.append(f"Duplicate member names: {len(duplicates)}")

        extensions = Counter((Path(name).suffix.lower() or "<none>") for name in names)
        lines.append("Top extensions:")
        for extension, count in extensions.most_common(20):
            lines.append(f"  {extension}: {count}")

        relevant = [
            name
            for name in names
            if any(
                key in name.lower()
                for key in ("viego", "skin43", "234043", "swordswap", "sword_swap")
            )
        ]
        lines.append(f"Viego/Revenant-relevant member names: {len(relevant)}")
        for name in relevant[:250]:
            lines.append(f"  {name}")

        metadata = [
            info
            for info in infos
            if info.file_size <= 2_000_000
            and info.filename.lower().endswith((".json", ".txt", ".meta", ".cfg", ".ini"))
        ]
        lines.append(f"Small metadata/text candidates: {len(metadata)}")
        for info in metadata[:40]:
            lines.append(f"  {info.filename} ({info.file_size} bytes)")
            try:
                text = archive.read(info).decode("utf-8", errors="replace")
                preview = " ".join(text.split())
                if len(preview) > 400:
                    preview = preview[:400] + "..."
                if preview:
                    lines.append("    preview: " + preview)
            except Exception as exc:
                lines.append(f"    read error: {type(exc).__name__}: {exc}")

    return lines + [""]


def inventory() -> list[str]:
    root = LOCALAPPDATA / "Rose" / "skins" / "234"
    lines = ["=== VIEGO PACKAGE INVENTORY ===", f"Root: {root}"]

    if not root.exists():
        return lines + ["Viego root not found.", ""]

    files = sorted(root.rglob("*.fantome"))
    lines.append(f"Fantome files found: {len(files)}")
    for file in files:
        try:
            lines.append(
                f"{file.relative_to(root)} | {file.stat().st_size} bytes | {sha256(file)}"
            )
        except Exception as exc:
            lines.append(f"{file} | ERROR {type(exc).__name__}: {exc}")

    return lines + [""]


def main() -> int:
    lines = [
        "Personal Skin Manager - Revenant Reign Viego 234043 Audit",
        "READ-ONLY: this script does not modify or extract any files.",
        "",
    ]
    lines += audit("CURRENT 234043", CURRENT)
    lines += audit("BACKUP 234043", BACKUP)
    lines += ["=== CURRENT vs BACKUP ==="]

    if CURRENT.exists() and BACKUP.exists():
        lines += [
            f"Same SHA256: {'YES' if sha256(CURRENT) == sha256(BACKUP) else 'NO'}",
            f"Current SHA256: {sha256(CURRENT)}",
            f"Backup SHA256: {sha256(BACKUP)}",
            "",
        ]
    else:
        lines += ["Comparison unavailable because one file is missing.", ""]

    lines += inventory()

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Audit written to: {OUT}")
    if CURRENT.exists():
        print(f"[INFO] Current SHA256: {sha256(CURRENT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
