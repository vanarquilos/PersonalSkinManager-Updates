#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTK patcher runtime inspection.

Generic runtime compatibility helper aligned with Rose 1.3.x:
- validates the host/DLL pair;
- reads the LTK DLL's built-in end-of-life timestamp when available;
- lets PSM fail early when the bundled/current runtime is stale.

No champion, skin, chroma, or mod IDs are handled here.
"""

import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

LTK_PATCHER_HOST = "ltk_patcher_host.exe"
LTK_PATCHER_DLL = "ltk_patcher_dll.dll"

_EOL_MESSAGE = b"end of life reached, please update: "
_EOL_SEARCH_WINDOW = 0x100


@dataclass
class LtkPatcherStatus:
    host: Path
    dll: Path
    missing: list
    eol: Optional[int]

    @property
    def expired(self) -> bool:
        return self.eol is not None and time.time() > self.eol


def check_ltk_patcher(tools_dir: Path) -> LtkPatcherStatus:
    host = tools_dir / LTK_PATCHER_HOST
    dll = tools_dir / LTK_PATCHER_DLL
    missing = [p.name for p in (host, dll) if not p.is_file()]
    eol = read_dll_eol(dll) if dll.is_file() else None
    return LtkPatcherStatus(host=host, dll=dll, missing=missing, eol=eol)


def read_dll_eol(dll_path: Path) -> Optional[int]:
    """Return the LTK DLL EOL timestamp when its current binary layout is recognized."""
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
        # lea r64, [rip + disp32]
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
