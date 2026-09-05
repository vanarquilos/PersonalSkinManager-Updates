from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .manifest import canonical_signed_bytes


class SignatureVerificationError(ValueError):
    pass


def verify_manifest_signature(raw_manifest: dict, public_key_b64: str) -> None:
    if not public_key_b64:
        raise SignatureVerificationError("Update public key is not configured")

    signature_b64 = raw_manifest.get("signature")
    if not isinstance(signature_b64, str) or not signature_b64:
        raise SignatureVerificationError("Manifest signature is missing")

    try:
        public_key_raw = base64.b64decode(public_key_b64, validate=True)
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise SignatureVerificationError("Invalid base64 key/signature") from exc

    if len(public_key_raw) != 32:
        raise SignatureVerificationError("Ed25519 public key must be 32 bytes")

    try:
        key = Ed25519PublicKey.from_public_bytes(public_key_raw)
        key.verify(signature, canonical_signed_bytes(raw_manifest))
    except InvalidSignature as exc:
        raise SignatureVerificationError("Manifest signature is invalid") from exc
    except Exception as exc:
        raise SignatureVerificationError(
            f"Manifest signature verification failed: {exc}"
        ) from exc
