#!/usr/bin/env python3
"""Build an inert PSM-owned cslol-dll.dll compatibility module for mkoverlay.

This does not rebuild LeagueToolkit's CSLOL DLL. It has no injection functions;
it is only an import table stand-in for mod-tools.exe's mkoverlay subcommand.
Build only into an explicitly supplied, empty output directory.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native/cslol_stub/psm_cslol_stub.c"


def locate_vcvars() -> Path | None:
    candidate = (
        Path(os.environ.get("ProgramFiles(x86)", ""))
        / "Microsoft Visual Studio/Installer/vswhere.exe"
    )
    if not candidate.is_file():
        return None
    proc = subprocess.run(
        [
            str(candidate), "-latest", "-products", "*",
            "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property", "installationPath"
        ],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        path = Path(line.strip()) / "VC/Auxiliary/Build/vcvars64.bat"
        if path.is_file():
            return path
    return None


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest().upper()


def main() -> int:
    if os.name != "nt":
        raise RuntimeError("MSVC Windows x64 host required.")
    target = os.environ.get("PSM_LOCAL_STUB_OUTPUT_DIR")
    if not target:
        raise RuntimeError("PSM_LOCAL_STUB_OUTPUT_DIR must be set explicitly.")
    output_dir = Path(target).resolve(strict=True)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise RuntimeError("Select an already-existing EMPTY isolated output directory.")
    vcvars = locate_vcvars()
    if vcvars is None:
        raise RuntimeError("Visual Studio 2022 MSVC x64 build tools were not found.")
    if not SOURCE.is_file():
        raise RuntimeError("PSM stand-in source missing.")
    output = output_dir / "cslol-dll.dll"
    with tempfile.TemporaryDirectory() as temp:
        implib = Path(temp) / "cslol-dll.lib"
        statement = (
            f'call "{vcvars}" >nul && '
            f'cl /nologo /LD /O1 /GS- /TC "{SOURCE}" '
            f'/link /NOENTRY /NODEFAULTLIB '
            f'/OUT:"{output}" /IMPLIB:"{implib}"'
        )
        result = subprocess.run(["cmd", "/d", "/c", statement], cwd=temp, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"MSVC stub build failed ({result.returncode}).")
        # Prove the compiled DLL exports what the actual upstream import-table
        # consumer expects. Do not assume source-level declarations are enough.
        export_cmd = (
            f'call "{vcvars}" >nul && '
            f'dumpbin /nologo /exports "{output}"'
        )
        exported = subprocess.run(
            ["cmd", "/d", "/c", export_cmd],
            cwd=temp, capture_output=True, text=True, errors="replace",
            check=False,
        )
        if exported.returncode != 0:
            raise RuntimeError("MSVC dumpbin export validation did not run.")
        expected_exports = {
            "cslol_find", "cslol_hook", "cslol_init", "cslol_log_pull",
            "cslol_msg_hookproc", "cslol_set_config", "cslol_set_flags",
            "cslol_set_log_level",
        }
        import re
        matched = set(re.findall(
            r"^\\s*\\d+\\s+[0-9A-Fa-f]+\\s+[0-9A-Fa-f]+\\s+"
            r"(cslol_[a-z_]+)\\s*$",
            exported.stdout, flags=re.MULTILINE,
        ))
        if matched != expected_exports:
            raise RuntimeError(
                "PSM stub ABI mismatch: missing="
                + ",".join(sorted(expected_exports - matched))
                + "; unexpected=" + ",".join(sorted(matched - expected_exports))
            )
    if not output.is_file():
        raise RuntimeError("Expected cslol-dll.dll was not created.")
    # No third-party CSLOL binary is copied or embedded; a signature check
    # is not a substitute for the independent PSM stub source build.
    manifest = {
        "schema": 1,
        "purpose": "PSM_V105_INERT_CSLOL_STUB",
        "source_sha256": sha256(SOURCE),
        "built_sha256": sha256(output),
        "public_distribution_approved": False,
    }
    (output_dir / "psm-cslol-stub-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("PSM-owned inert CSLOL import stub built in isolated directory.")
    print("SHA-256:", manifest["built_sha256"])
    print("No official CSLOL binary was packaged or modified.")
    print("Public installer remains blocked pending real runtime/rights review.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError) as exc:
        print("[ERROR]", exc, file=sys.stderr)
        raise SystemExit(1)
