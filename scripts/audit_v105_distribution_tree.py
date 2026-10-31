#!/usr/bin/env python3
"""Audit the built v1.0.5 distribution tree before Inno Setup runs.

Only the public certifi CA trust store is exempted from the PEM block.
Never allow credential files, signing material, or private PSM runtime state.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


PRIVATE_STATE = re.compile(r"^_v105_.*\.json$", re.IGNORECASE)
BLOCKED_EXTENSIONS = {".pem", ".pfx", ".p12", ".key", ".jks", ".keystore"}
CA_BUNDLE_PATHS = {"_internal/certifi/cacert.pem", "certifi/cacert.pem"}
PEM_HEADER = re.compile(rb"-----BEGIN ([A-Za-z0-9 ]+)-----")


def is_public_certifi_bundle(relative: str, path: Path) -> bool:
    if relative.casefold() not in CA_BUNDLE_PATHS:
        return False
    try:
        data = path.read_bytes()
    except OSError:
        return False
    headers = PEM_HEADER.findall(data)
    # A CA bundle should contain only public X.509 certificates. A private
    # key, signing request, or other PEM object is never approved here.
    return bool(headers) and set(headers) == {b"CERTIFICATE"}


def inspect_distribution(root: Path) -> tuple[list[str], list[str]]:
    root = root.resolve(strict=True)
    blocked = []
    allowed = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        # Fail closed on a symlink escaping the distribution directory.
        if not path.resolve().is_relative_to(root):
            blocked.append(relative + " (outside distribution)")
            continue
        name = path.name
        if PRIVATE_STATE.fullmatch(name):
            blocked.append(relative)
        elif path.suffix.casefold() in BLOCKED_EXTENSIONS:
            if path.suffix.casefold() == ".pem" and is_public_certifi_bundle(relative, path):
                allowed.append(relative)
            else:
                blocked.append(relative)
    return sorted(blocked), sorted(allowed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, required=True)
    args = parser.parse_args()
    try:
        blocked, allowed = inspect_distribution(args.dist)
    except OSError as exc:
        print(f"[ERROR] Distribution audit could not inspect output: {exc}")
        return 1
    for relative in allowed:
        print(f"[OK] Public CA trust bundle allowed: {relative}")
    if blocked:
        print("[ERROR] The distribution contains prohibited runtime state or signing material:")
        for relative in blocked:
            # Print only distribution-relative names, never file contents.
            print(f"  - {relative}")
        print("[ERROR] No release candidate is approved. Review and exclude these inputs from packaging.")
        return 1
    print("[OK] Distribution tree contains no prohibited private state or signing material.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
