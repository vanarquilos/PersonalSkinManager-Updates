#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from getpass import getpass
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization


def canonical_bytes(data: dict) -> bytes:
    payload = dict(data)
    payload.pop("signature", None)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--minimum-version", default="1.0.0")
    parser.add_argument("--package", required=True)
    parser.add_argument("--package-url", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--private-key",
        default=str(
            Path.home()
            / ".personal-skin-manager"
            / "signing"
            / "update_ed25519_private.pem"
        ),
    )
    parser.add_argument("--output", default="manifest.json")
    args = parser.parse_args()

    package = Path(args.package).resolve()
    private_key_path = Path(args.private_key).resolve()
    if not package.is_file():
        raise SystemExit(f"Package not found: {package}")
    if package.name != "PersonalSkinManager_Setup.exe":
        raise SystemExit("Package must be named PersonalSkinManager_Setup.exe")
    if not private_key_path.is_file():
        raise SystemExit(f"Private key not found: {private_key_path}")
    if not args.package_url.lower().startswith("https://"):
        raise SystemExit("Package URL must use HTTPS")

    password = os.environ.get("PSM_UPDATE_KEY_PASSWORD")
    if password is None:
        password = getpass("Update-signing key password: ")

    private_key = serialization.load_pem_private_key(
        private_key_path.read_bytes(),
        password=password.encode("utf-8"),
    )

    manifest = {
        "schema": 1,
        "channel": "stable",
        "version": args.version,
        "minimum_version": args.minimum_version,
        "published_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "release_notes": args.notes,
        "package": {
            "type": "inno",
            "url": args.package_url,
            "sha256": sha256_file(package),
            "size": package.stat().st_size,
            "filename": "PersonalSkinManager_Setup.exe",
        },
        "signature": "",
    }

    signature = private_key.sign(canonical_bytes(manifest))
    manifest["signature"] = base64.b64encode(signature).decode("ascii")
    output = Path(args.output).resolve()
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Signed manifest: {output}")
    print(f"[INFO] Package SHA-256: {manifest['package']['sha256']}")
    print(f"[INFO] Package size: {manifest['package']['size']}")


if __name__ == "__main__":
    main()
