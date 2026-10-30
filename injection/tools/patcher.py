#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTK patcher runtime inspection.

The LTK DLL's embedded end-of-life value is compared against the League
game executable's PE build timestamp, not the current wall clock. A DLL can
therefore remain valid after its calendar EOL until League itself updates.
"""

import struct
import os
import json
import re
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

LTK_PATCHER_HOST = "ltk_patcher_host.exe"
LTK_PATCHER_DLL = "ltk_patcher_dll.dll"

GAME_EXECUTABLE_NAMES = (
    "League of Legends.exe",
    "League of Legends (TM) Client.exe",
)

# Explicit local QA override to compare unchanged official v1.28.1 and
# separately signature-removed files WITHOUT modifying source injection/tools.
# The QA selector is intentionally pinned to the reviewed v1.28.1 build.
LTK_QA_RUNTIME_DIR_ENV = "PSM_LTK_QA_RUNTIME_DIR"
LTK_QA_MANIFEST_ENV = "PSM_LTK_QA_MANIFEST"
LTK_CURRENT_HOST_PROTOCOL = 3  # LTK Manager v1.31.1 bundled host protocol; verify candidate API separately
LTK_QA_ORIGINAL_SHA256 = {
    LTK_PATCHER_HOST: "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1",
    LTK_PATCHER_DLL: "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74",
}
LTK_QA_UNSIGNED_SHA256 = {
    LTK_PATCHER_HOST: "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9",
    LTK_PATCHER_DLL: "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29",
}


def _hash_file(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as data:
        for block in iter(lambda: data.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest().upper()


def _verify_local_qa_manifest(selected: Path, manifest_path: Path) -> list[str]:
    """Hash-pin a separately reviewed local LTK host/DLL pair for PSM QA.

    The manifest is a maintainer-controlled, local-only INPUT, not proof of
    publisher authenticity or a live protocol compatibility test. No downloads,
    signature stripping, anti-cheat overrides or runtime file writes occur.
    """
    if not manifest_path.is_absolute() or not manifest_path.is_file():
        return ["local LTK QA manifest missing or non-absolute"]
    try:
        if manifest_path.stat().st_size > 16_384:
            return ["local LTK QA manifest oversized"]
        info = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError, OSError):
        return ["local LTK QA manifest unreadable or invalid"]
    if not isinstance(info, dict):
        return ["local LTK QA manifest must be a JSON object"]
    required = {
        "schema": 1,
        "purpose": "PSM_V105_PRIVATE_QA_ONLY",
        "host_protocol": LTK_CURRENT_HOST_PROTOCOL,
        "public_distribution_approved": False,
    }
    if any(type(info.get(key)) is not type(value) or info[key] != value
           for key, value in required.items()):
        return ["local LTK QA manifest schema, purpose, protocol or distribution gate invalid"]
    if not isinstance(info.get("source_manager_release"), str) or not re.fullmatch(
        r"v\d+\.\d+\.\d+", info["source_manager_release"]
    ):
        return ["local LTK QA manifest manager release label invalid"]
    # The manager release is provenance metadata; it is NOT the delivered
    # patcher build version and cannot establish host/DLL compatibility.
    expected = info.get("files_sha256")
    if not isinstance(expected, dict) or set(expected) != {LTK_PATCHER_HOST, LTK_PATCHER_DLL}:
        return ["local LTK QA manifest must pin exactly one host and DLL"]
    for name in (LTK_PATCHER_HOST, LTK_PATCHER_DLL):
        digest = expected[name]
        if not isinstance(digest, str) or re.fullmatch(r"[A-Fa-f0-9]{64}", digest) is None:
            return ["local LTK QA manifest SHA-256 format invalid"]
        candidate = selected / name
        if not candidate.is_file() or candidate.is_symlink():
            return ["local LTK QA file missing or symlink rejected"]
        try:
            if _hash_file(candidate) != digest.upper():
                return ["local LTK QA component fingerprint mismatch"]
        except OSError:
            return ["local LTK QA component unreadable"]
    return []


def _resolve_qa_runtime(tools_dir: Path) -> tuple[Path, list[str]]:
    supplied = os.environ.get(LTK_QA_RUNTIME_DIR_ENV)
    if not supplied:
        if os.environ.get(LTK_QA_MANIFEST_ENV):
            return tools_dir, ["local LTK QA manifest requires a runtime directory"]
        return tools_dir, []
    selected = Path(supplied)
    if not selected.is_absolute() or not selected.is_dir():
        return selected, ["invalid local QA runtime directory"]
    manifest = os.environ.get(LTK_QA_MANIFEST_ENV)
    if manifest:
        return selected, _verify_local_qa_manifest(selected, Path(manifest))
    paths = {name: selected / name for name in (LTK_PATCHER_HOST, LTK_PATCHER_DLL)}
    if any(not path.is_file() for path in paths.values()):
        return selected, ["incomplete local QA runtime"]
    try:
        hashes = {name: _hash_file(path) for name, path in paths.items()}
    except OSError:
        return selected, ["unreadable local QA runtime"]
    if hashes not in (LTK_QA_ORIGINAL_SHA256, LTK_QA_UNSIGNED_SHA256):
        return selected, ["local QA runtime does not match the reviewed pair"]
    return selected, []


_EOL_MESSAGE = b"end of life reached, please update: "
_EOL_SEARCH_WINDOW = 0x100


@dataclass
class LtkPatcherStatus:
    host: Path
    dll: Path
    missing: list
    eol: Optional[int]

    def expired_for(self, game_dir: Optional[Path]) -> bool:
        """Return True only when the installed League build is newer than the DLL cutoff.

        If the game build cannot be read, do not reject the DLL pre-emptively.
        The patcher itself will still report an unsupported build when it runs.
        """
        if self.eol is None or game_dir is None:
            return False

        build = read_game_build(game_dir)
        return build is not None and build > self.eol


def check_ltk_patcher(tools_dir: Path) -> LtkPatcherStatus:
    """Report required LTK files and the DLL's embedded build cutoff."""
    selected_dir, qa_errors = _resolve_qa_runtime(tools_dir)
    host = selected_dir / LTK_PATCHER_HOST
    dll = selected_dir / LTK_PATCHER_DLL
    missing = qa_errors or [p.name for p in (host, dll) if not p.is_file()]
    eol = read_dll_eol(dll) if dll.is_file() else None
    return LtkPatcherStatus(host=host, dll=dll, missing=missing, eol=eol)


def read_dll_eol(dll_path: Path) -> Optional[int]:
    """Return the LTK DLL's embedded game-build cutoff timestamp."""
    try:
        data = dll_path.read_bytes()
        sections = _parse_sections(data)
    except (OSError, ValueError, struct.error):
        return None

    msg_offset = data.find(_EOL_MESSAGE)
    if msg_offset < 0:
        return None

    msg_rva = _offset_to_rva(sections, msg_offset)
    text = next((s for s in sections if s[0] == b".text"), None)
    if msg_rva is None or text is None:
        return None

    _, text_rva, text_size, text_raw = text
    code = data[text_raw:text_raw + text_size]

    for i in range(len(code) - 7):
        if (
            code[i] not in (0x48, 0x4C)
            or code[i + 1] != 0x8D
            or (code[i + 2] & 0xC7) != 0x05
        ):
            continue

        disp = struct.unpack_from("<i", code, i + 3)[0]
        if not 0 <= msg_rva - (text_rva + i + 7 + disp) <= 16:
            continue

        eol = _find_eol_compare(code, i)
        if eol is not None:
            return eol

    return None


def read_game_build(game_dir: Path) -> Optional[int]:
    """Read League's PE TimeDateStamp, which is what the LTK DLL validates."""
    for name in GAME_EXECUTABLE_NAMES:
        try:
            with open(Path(game_dir) / name, "rb") as f:
                header = f.read(0x1000)
        except OSError:
            continue

        try:
            pe = struct.unpack_from("<I", header, 0x3C)[0]
            if header[:2] == b"MZ" and header[pe:pe + 4] == b"PE\0\0":
                return struct.unpack_from("<I", header, pe + 8)[0]
        except struct.error:
            pass

    return None


def _find_eol_compare(code: bytes, lea_index: int) -> Optional[int]:
    start = max(0, lea_index - _EOL_SEARCH_WINDOW)
    for j in range(lea_index - 11, start - 1, -1):
        if (
            code[j] == 0x3D
            and code[j + 5] == 0x0F
            and code[j + 6] == 0x86
        ):
            return struct.unpack_from("<I", code, j + 1)[0]
    return None


def _parse_sections(data: bytes):
    if data[:2] != b"MZ":
        raise ValueError("not a PE file")

    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE file")

    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + opt_size

    sections = []
    for k in range(count):
        entry = table + k * 40
        name = data[entry:entry + 8].rstrip(b"\0")
        rva, raw_size, raw_offset = struct.unpack_from("<III", data, entry + 12)
        sections.append((name, rva, raw_size, raw_offset))
    return sections


def _offset_to_rva(sections, offset: int) -> Optional[int]:
    for _, rva, raw_size, raw_offset in sections:
        if raw_offset <= offset < raw_offset + raw_size:
            return offset - raw_offset + rva
    return None
