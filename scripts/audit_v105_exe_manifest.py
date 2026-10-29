#!/usr/bin/env python3
"""Fail closed unless a frozen PSM executable requests normal user launch."""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def execution_levels(document: bytes) -> list[str]:
    text = None
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le"):
        try:
            candidate = document.decode(encoding)
            ET.fromstring(candidate)
            text = candidate
            break
        except (UnicodeError, ET.ParseError):
            continue
    if text is None:
        raise ValueError("Could not decode or parse executable manifest")
    root = ET.fromstring(text)
    return [
        str(element.attrib.get("level", ""))
        for element in root.iter()
        if element.tag.split("}")[-1] == "requestedExecutionLevel"
    ]


def read_embedded_manifests(executable: Path) -> list[bytes]:
    try:
        import pefile
    except ImportError as exc:
        raise RuntimeError("PE manifest auditing requires PyInstaller's pefile dependency") from exc

    pe = pefile.PE(str(executable), fast_load=False)
    try:
        resources = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
        if resources is None:
            return []
        result = []
        for resource_type in resources.entries:
            if resource_type.id != 24:
                continue
            for entry in resource_type.directory.entries:
                for language in entry.directory.entries:
                    node = language.data.struct
                    result.append(pe.get_data(node.OffsetToData, node.Size))
        return result
    finally:
        pe.close()


def verify_as_invoker(executable: Path) -> None:
    if not executable.is_file():
        raise FileNotFoundError(executable)
    manifests = read_embedded_manifests(executable)
    if len(manifests) != 1:
        raise ValueError(f"Expected exactly one executable manifest; found {len(manifests)}")
    levels = execution_levels(manifests[0])
    if levels != ["asInvoker"]:
        raise ValueError(f"Packaged PSM must request asInvoker, found {levels!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=Path)
    args = parser.parse_args()
    try:
        verify_as_invoker(args.exe)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"[ERROR] v1.0.5 packaged launch profile NOT APPROVED: {exc}")
        return 1
    print("[OK] Embedded PSM EXE manifest requests asInvoker (normal user launch).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
