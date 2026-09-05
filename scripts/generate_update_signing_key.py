#!/usr/bin/env python3
# Generate the one-time Ed25519 PSM update signing key.
# The encrypted private key is stored outside the repository:
# %USERPROFILE%\.personal-skin-manager\signing\update_ed25519_private.pem

from __future__ import annotations

import base64
from getpass import getpass
from pathlib import Path
import re

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
CHANNEL = ROOT / "psm_update" / "channel.py"
KEY_DIR = Path.home() / ".personal-skin-manager" / "signing"
PRIVATE_KEY = KEY_DIR / "update_ed25519_private.pem"


def main() -> None:
    if PRIVATE_KEY.exists():
        raise SystemExit(
            f"Private update key already exists:\n{PRIVATE_KEY}\nRefusing to overwrite it."
        )

    text = CHANNEL.read_text(encoding="utf-8")
    match = re.search(r'^UPDATE_PUBLIC_KEY_B64 = "(.*)"$', text, flags=re.MULTILINE)
    if not match:
        raise SystemExit("Could not find UPDATE_PUBLIC_KEY_B64 in channel.py")
    if match.group(1):
        raise SystemExit("A public update key is already embedded; refusing to replace it.")

    password = getpass("Create password for the encrypted update-signing key: ")
    confirm = getpass("Confirm password: ")
    if not password:
        raise SystemExit("Signing-key password cannot be empty.")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    KEY_DIR.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_b64 = base64.b64encode(public_raw).decode("ascii")

    PRIVATE_KEY.write_bytes(private_pem)
    text = re.sub(
        r'^UPDATE_PUBLIC_KEY_B64 = ".*"$',
        f'UPDATE_PUBLIC_KEY_B64 = "{public_b64}"',
        text,
        flags=re.MULTILINE,
    )
    CHANNEL.write_text(text, encoding="utf-8", newline="\n")

    print("[OK] Generated encrypted Personal Skin Manager Ed25519 update key.")
    print(f"[PRIVATE] {PRIVATE_KEY}")
    print("[OK] Public verification key embedded in psm_update/channel.py")
    print("Back up the encrypted private PEM and its password separately.")
    print("Never commit or upload the private PEM.")


if __name__ == "__main__":
    main()
