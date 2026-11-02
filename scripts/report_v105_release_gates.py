#!/usr/bin/env python3
"""Read-only PSM v1.0.5 release-candidate preflight.

Does not run a game, provision files, change a git checkout, or certify skins.
A compatible LTK runtime, Windows build, CI, legal review and visually
observed in-game rendering are separate release approval requirements.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from injection.tools.patcher import (  # noqa: E402
    LTK_PATCHER_HOST, LTK_PATCHER_DLL, read_game_build, read_dll_eol,
)

SHA = "sha256"
REPORT = Path("installer/candidates/v1.0.5/rose-style-frozen-private-qa.json")
EXE = Path("dist/PersonalSkinManager/PersonalSkinManager.exe")


def hash_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest().upper()


def time_utc(timestamp: int | None) -> str | None:
    return (datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
            if timestamp is not None else None)


def inspect(qa_root: Path, league_dir: Path, ltk_dir: Path | None = None) -> dict:
    checks: dict[str, dict] = {}
    report_path = qa_root / REPORT
    exe = qa_root / EXE
    manifest = None
    try:
        if report_path.is_file() and report_path.stat().st_size <= 16_384:
            manifest = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError):
        pass

    manifest_ok = (
        isinstance(manifest, dict)
        and manifest.get("version") == "1.0.5"
        and manifest.get("purpose") == "ROSE_STYLE_USER_SUPPLIED_LTK_PRIVATE_QA"
        and manifest.get("user_provided_ltk_bundled") is False
        and manifest.get("cslol_source") == "PSM_OWNED_INERT_STUB"
        and manifest.get("gameplay_skin_rendering") == "NOT_TESTED"
        and manifest.get("public_distribution_approved") is False
    )
    checks["private_qa_manifest"] = {
        "passed": manifest_ok,
        "detail": "Valid private-QA identity and explicit no-release status"
        if manifest_ok else "Private-QA report missing or does not match the contract",
    }
    exe_ok = False
    try:
        exe_ok = (
            exe.is_file() and not exe.is_symlink()
            and manifest_ok
            and hash_file(exe) == str(manifest.get("exe_sha256", "")).upper()
        )
    except OSError:
        exe_ok = False
    checks["frozen_executable"] = {
        "passed": exe_ok,
        "detail": "Executable exists and matches the private QA manifest hash"
        if exe_ok else "EXE missing, unhashed, or mismatched",
    }
    game = read_game_build(league_dir)
    if game is None:
        game = read_game_build(league_dir / "Game")
    checks["league_game_build"] = {
        "passed": game is not None,
        "timestamp_utc": time_utc(game),
    }

    cutoff = None
    host_sha = None
    dll_sha = None
    pair_present = False
    if ltk_dir is not None:
        host, dll = ltk_dir / LTK_PATCHER_HOST, ltk_dir / LTK_PATCHER_DLL
        try:
            pair_present = (host.is_file() and dll.is_file()
                            and not host.is_symlink() and not dll.is_symlink())
            if pair_present:
                host_sha, dll_sha = hash_file(host), hash_file(dll)
                cutoff = read_dll_eol(dll)
        except (OSError, ValueError):
            pair_present = False
    checks["ltk_host_and_dll"] = {
        "passed": pair_present,
        "host_sha256": host_sha,
        "dll_sha256": dll_sha,
        "detail": "Local candidate present; authenticity NOT certified"
        if pair_present else "No complete local LTK pair supplied",
    }
    compatible_cutoff = (
        pair_present and game is not None and cutoff is not None and game <= cutoff
    )
    checks["ltk_game_build_cutoff"] = {
        "passed": bool(compatible_cutoff),
        "dll_cutoff_utc": time_utc(cutoff),
        "detail": "Build cutoff not exceeded; gameplay still unverified"
        if compatible_cutoff else "No verified supported DLL cutoff for this League build",
    }

    # These gates require evidence from other environments and cannot be
    # inferred from source code, a SHA-256 match, or the tool's own output.
    for key, reason in (
        ("windows_native_tests", "Run actual Windows MSVC, PyInstaller and unit tests"),
        ("github_actions_ci", "Require successful executed GitHub Actions jobs"),
        ("official_ltk_provenance", "Require vendor-signed manifest/source verification"),
        ("visible_skin_in_game", "Observe an allowed Practice Tool game with a custom skin"),
        ("install_upgrade_uninstall", "Test clean install/upgrade/uninstall on Windows"),
        ("redistribution_review", "Review third-party license/signature terms"),
    ):
        checks[key] = {"passed": False, "detail": f"REQUIRES INDEPENDENT EVIDENCE: {reason}"}

    # A source or local machine may be build-ready even while the public
    # release remains blocked; never silently promote a release from this audit.
    return {
        "version": "1.0.5",
        "purpose": "READ_ONLY_RELEASE_CANDIDATE_AUDIT",
        "private_build_verified": bool(manifest_ok and exe_ok),
        "runtime_cutoff_eligible": bool(compatible_cutoff),
        "public_release": "NO_GO",
        "checks": checks,
        "notice": (
            "This is not permission to run, publish or redistribute patched "
            "game binaries. Only external source, vendor and gameplay evidence "
            "can close the remaining release gates."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-root", required=True, type=Path)
    parser.add_argument("--league-dir", required=True, type=Path)
    parser.add_argument("--ltk-dir", type=Path)
    parser.add_argument(
        "--report-only", action="store_true",
        help="Print the release audit without failing the shell on NO_GO.",
    )
    args = parser.parse_args()
    report = inspect(args.qa_root, args.league_dir, args.ltk_dir)
    print(json.dumps(report, indent=2))
    # Fail-closed default: a build script invoking this without --report-only
    # cannot accidentally treat a private QA audit as public release approval.
    return 0 if args.report_only or report["public_release"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
