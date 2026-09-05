from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

from .channel import (
    CHECK_TIMEOUT_S,
    DOWNLOAD_TIMEOUT_S,
    MAX_MANIFEST_BYTES,
    MAX_PACKAGE_BYTES,
)
from .manifest import ManifestError, UpdateManifest


class UpdateNetworkError(RuntimeError):
    pass


def require_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise UpdateNetworkError("Update URLs must use HTTPS")


def fetch_manifest(url: str) -> dict:
    require_https(url)
    try:
        response = requests.get(
            url,
            timeout=CHECK_TIMEOUT_S,
            allow_redirects=True,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise UpdateNetworkError(f"Manifest request failed: {exc}") from exc

    if response.url:
        require_https(response.url)
    if len(response.content) > MAX_MANIFEST_BYTES:
        raise UpdateNetworkError("Manifest is unexpectedly large")

    try:
        data = json.loads(response.content.decode("utf-8"))
    except Exception as exc:
        raise ManifestError("Manifest is not valid UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise ManifestError("Manifest root must be an object")
    return data


def download_verified_package(
    manifest: UpdateManifest,
    destination: Path,
    progress_callback=None,
) -> Path:
    require_https(manifest.package.url)
    if manifest.package.size > MAX_PACKAGE_BYTES:
        raise UpdateNetworkError("Update package exceeds configured size limit")

    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_suffix(destination.suffix + ".part")
    part.unlink(missing_ok=True)

    hasher = hashlib.sha256()
    downloaded = 0
    try:
        with requests.get(
            manifest.package.url,
            stream=True,
            timeout=DOWNLOAD_TIMEOUT_S,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()
            if response.url:
                require_https(response.url)
            with part.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > MAX_PACKAGE_BYTES:
                        raise UpdateNetworkError("Update package exceeded maximum size")
                    hasher.update(chunk)
                    fh.write(chunk)
                    if progress_callback:
                        progress_callback(downloaded, manifest.package.size)
    except Exception:
        part.unlink(missing_ok=True)
        raise

    if downloaded != manifest.package.size:
        part.unlink(missing_ok=True)
        raise UpdateNetworkError(
            f"Update size mismatch: expected {manifest.package.size}, got {downloaded}"
        )
    if hasher.hexdigest().lower() != manifest.package.sha256:
        part.unlink(missing_ok=True)
        raise UpdateNetworkError("Update package SHA-256 verification failed")

    part.replace(destination)
    return destination
