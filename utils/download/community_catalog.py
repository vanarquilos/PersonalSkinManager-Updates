#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Curated community-mod catalog for Rose-style one-click installs.

The catalog is metadata only. Packages are downloaded on demand, SHA-256
verified, cached under %LOCALAPPDATA%/Rose/catalog, and imported through the
existing ModStorageService. This service does not weaken LTK verification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
import re
import threading
import time
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse

import requests

from config import APP_USER_AGENT, SKIN_DOWNLOAD_STREAM_TIMEOUT_S
from injection.mods.storage import ModStorageService, SkinModEntry
from utils.core.junction import safe_remove_entry
from utils.core.logging import get_logger
from utils.core.paths import get_app_dir, get_user_data_dir

log = get_logger()

CATALOG_VERSION = 1
DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/vanarquilos/"
    "PersonalSkinManager-Updates/main/catalog/community-mods.json"
)
CATALOG_REFRESH_SECONDS = 15 * 60
MAX_PACKAGE_BYTES = 512 * 1024 * 1024


@dataclass(frozen=True)
class CommunityCatalogEntry:
    id: str
    champion_id: int
    name: str
    package_url: str
    sha256: str
    target_skin_ids: tuple[int, ...]
    description: Optional[str] = None
    preview_url: Optional[str] = None
    author: Optional[str] = None
    version: str = "1"

    @property
    def catalog_mod_id(self) -> str:
        return f"catalog:{self.id}"


class CommunityCatalogService:
    """Read the curated catalog and install a selected package on demand."""

    def __init__(
        self,
        mod_storage: Optional[ModStorageService] = None,
        catalog_url: str = DEFAULT_CATALOG_URL,
    ) -> None:
        self.mod_storage = mod_storage or ModStorageService()
        self.catalog_url = catalog_url
        self.root = get_user_data_dir() / "catalog"
        self.packages_dir = self.root / "packages"
        self.cached_manifest = self.root / "community-mods.json"
        self.local_override = self.root / "community-mods.local.json"
        self.installed_state_path = self.root / "installed.json"
        self.bundled_manifest = get_app_dir() / "catalog" / "community-mods.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._refresh_thread: Optional[threading.Thread] = None
        self._last_refresh_attempt = 0.0
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": APP_USER_AGENT})

    @staticmethod
    def _safe_https_url(value: object) -> Optional[str]:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = urlparse(raw)
        except Exception:
            return None
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return None

        host = parsed.hostname.strip().lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return None
        try:
            ip = ipaddress.ip_address(host)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                return None
        except ValueError:
            pass
        return raw

    @staticmethod
    def _normalize_sha256(value: object) -> Optional[str]:
        digest = str(value or "").strip().lower()
        if len(digest) != 64:
            return None
        try:
            int(digest, 16)
        except ValueError:
            return None
        return digest

    @classmethod
    def _parse_entry(cls, raw: object) -> Optional[CommunityCatalogEntry]:
        if not isinstance(raw, dict) or raw.get("enabled", True) is False:
            return None
        try:
            entry_id = str(raw["id"]).strip()
            champion_id = int(raw["championId"])
            name = str(raw["name"]).strip()
        except (KeyError, TypeError, ValueError):
            return None

        # IDs become cache filenames and protocol identifiers. Keep them
        # deliberately boring so catalog metadata can never create paths.
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", entry_id):
            return None

        package_url = cls._safe_https_url(raw.get("packageUrl"))
        digest = cls._normalize_sha256(raw.get("sha256"))
        if not entry_id or not name or champion_id <= 0 or not package_url or not digest:
            return None

        target_ids: set[int] = set()
        raw_targets = raw.get("targetSkinIds") or []
        if not isinstance(raw_targets, (list, tuple, set)):
            return None
        for value in raw_targets:
            try:
                skin_id = int(value)
            except (TypeError, ValueError):
                continue
            if skin_id > 0 and skin_id // 1000 == champion_id:
                target_ids.add(skin_id)
        if not target_ids:
            return None

        preview_url = cls._safe_https_url(raw.get("previewUrl"))
        return CommunityCatalogEntry(
            id=entry_id,
            champion_id=champion_id,
            name=name,
            package_url=package_url,
            sha256=digest,
            target_skin_ids=tuple(sorted(target_ids)),
            description=str(raw.get("description") or "").strip() or None,
            preview_url=preview_url,
            author=str(raw.get("author") or "").strip() or None,
            version=str(raw.get("version") or "1").strip() or "1",
        )

    def _read_manifest(self, path: Path) -> list[CommunityCatalogEntry]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(payload, dict) or int(payload.get("version") or 0) != CATALOG_VERSION:
            return []
        raw_entries = payload.get("entries") or []
        if not isinstance(raw_entries, list):
            return []
        entries: list[CommunityCatalogEntry] = []
        seen: set[str] = set()
        for raw in raw_entries:
            entry = self._parse_entry(raw)
            if entry is None or entry.id in seen:
                continue
            seen.add(entry.id)
            entries.append(entry)
        return entries

    def entries(self) -> list[CommunityCatalogEntry]:
        """Return local-override, cached, or bundled entries without blocking on network."""
        with self._lock:
            for path in (self.local_override, self.cached_manifest, self.bundled_manifest):
                entries = self._read_manifest(path)
                if entries:
                    return entries
            return []

    def refresh_async(self, force: bool = False) -> None:
        """Refresh catalog metadata in the background; packages remain on-demand."""
        now = time.monotonic()
        with self._lock:
            if self._refresh_thread and self._refresh_thread.is_alive():
                return
            if not force and (now - self._last_refresh_attempt) < CATALOG_REFRESH_SECONDS:
                return
            self._last_refresh_attempt = now
            self._refresh_thread = threading.Thread(
                target=self._refresh_worker,
                daemon=True,
                name="CommunityCatalogRefresh",
            )
            self._refresh_thread.start()

    def _refresh_worker(self) -> None:
        url = self._safe_https_url(self.catalog_url)
        if not url:
            return
        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or int(payload.get("version") or 0) != CATALOG_VERSION:
                raise ValueError("unsupported catalog version")
            raw_entries = payload.get("entries") or []
            if not isinstance(raw_entries, list):
                raise ValueError("catalog entries must be a list")
            valid_count = sum(1 for raw in raw_entries if self._parse_entry(raw) is not None)
            if raw_entries and valid_count == 0:
                raise ValueError("catalog contains no valid entries")
            temporary = self.cached_manifest.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.cached_manifest)
            log.info("[CATALOG] Refreshed community catalog (%d valid entries)", valid_count)
        except Exception as exc:
            log.debug("[CATALOG] Remote refresh unavailable: %s", exc)

    def find(self, entry_id: str) -> Optional[CommunityCatalogEntry]:
        requested = str(entry_id or "").strip()
        for entry in self.entries():
            if entry.id == requested:
                return entry
        return None

    def _load_installed_state(self) -> dict:
        try:
            payload = json.loads(self.installed_state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {"version": 1, "entries": {}}
        if not isinstance(payload, dict):
            return {"version": 1, "entries": {}}
        entries = payload.get("entries")
        if not isinstance(entries, dict):
            entries = {}
        return {"version": 1, "entries": entries}

    def _save_installed_state(self, payload: dict) -> None:
        temporary = self.installed_state_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.installed_state_path)

    def _installed_entry(self, entry: CommunityCatalogEntry) -> Optional[SkinModEntry]:
        state = self._load_installed_state()
        metadata = state.get("entries", {}).get(entry.id)
        if not isinstance(metadata, dict) or metadata.get("sha256") != entry.sha256:
            return None
        relative_path = str(metadata.get("relativePath") or "").replace("\\", "/").strip("/")
        if not relative_path:
            return None
        requested = relative_path.casefold()
        for candidate in self.mod_storage.list_mods_for_champion(entry.champion_id):
            try:
                rel = candidate.path.relative_to(self.mod_storage.mods_root).as_posix()
            except (ValueError, AttributeError):
                continue
            if rel.casefold() == requested:
                return candidate
        return None

    def list_for_skin(
        self,
        champion_id: int,
        compatible_skin_ids: Iterable[int],
    ) -> list[dict]:
        """Return catalog-only entries not already represented by installed storage."""
        try:
            champion_id = int(champion_id)
        except (TypeError, ValueError):
            return []
        compatible = {int(value) for value in compatible_skin_ids}
        payloads: list[dict] = []
        for entry in self.entries():
            targets = set(entry.target_skin_ids)
            if entry.champion_id != champion_id or not (targets & compatible):
                continue
            if self._installed_entry(entry) is not None:
                continue
            description = entry.description
            if entry.author:
                description = (
                    f"{description} · by {entry.author}" if description else f"by {entry.author}"
                )
            payloads.append(
                {
                    "modName": entry.name,
                    "skinId": min(targets & compatible),
                    "targetSkinIds": sorted(targets),
                    "availableForRequestedSkin": True,
                    "description": description,
                    "updatedAt": 0,
                    "relativePath": entry.catalog_mod_id,
                    "thumbnailRelativePath": None,
                    "thumbnailUrl": entry.preview_url,
                    "source": "catalog",
                    "catalogId": entry.id,
                    "installed": False,
                    "version": entry.version,
                }
            )
        return payloads

    def _download_package(self, entry: CommunityCatalogEntry) -> Path:
        suffix = Path(urlparse(entry.package_url).path).suffix.lower()
        if suffix not in {".fantome", ".zip"}:
            suffix = ".fantome"
        destination = self.packages_dir / f"{entry.id}-{entry.sha256[:12]}{suffix}"
        if destination.is_file():
            if self._sha256_file(destination) == entry.sha256:
                return destination
            destination.unlink(missing_ok=True)

        part = destination.with_suffix(destination.suffix + ".part")
        part.unlink(missing_ok=True)
        hasher = hashlib.sha256()
        downloaded = 0
        try:
            with self._session.get(
                entry.package_url,
                stream=True,
                timeout=SKIN_DOWNLOAD_STREAM_TIMEOUT_S,
            ) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if content_length and str(content_length).isdigit():
                    if int(content_length) > MAX_PACKAGE_BYTES:
                        raise ValueError("catalog package is larger than the safety limit")
                with part.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        if downloaded > MAX_PACKAGE_BYTES:
                            raise ValueError("catalog package exceeded the safety limit")
                        hasher.update(chunk)
                        handle.write(chunk)
            actual = hasher.hexdigest()
            if actual != entry.sha256:
                raise ValueError(
                    f"SHA-256 mismatch for {entry.id}: expected {entry.sha256}, got {actual}"
                )
            part.replace(destination)
            return destination
        except Exception:
            part.unlink(missing_ok=True)
            raise

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def ensure_installed(
        self,
        entry_id: str,
        champion_id: int,
        requested_skin_id: int,
    ) -> SkinModEntry:
        """Download, verify, cache, import, and return one catalog mod."""
        entry = self.find(entry_id)
        if entry is None:
            raise ValueError("Catalog entry is unavailable")
        champion_id = int(champion_id)
        requested_skin_id = int(requested_skin_id)
        if entry.champion_id != champion_id:
            raise ValueError("Catalog entry does not belong to this champion")
        if requested_skin_id not in set(entry.target_skin_ids):
            raise ValueError("Catalog entry is not compatible with this skin")

        existing = self._installed_entry(entry)
        if existing is not None:
            return existing

        package_path = self._download_package(entry)
        target_dir, _manifest_path, _mod_name = self.mod_storage.import_mod_file(
            champion_id,
            package_path,
            entry.target_skin_ids,
        )
        installed = next(
            (
                candidate
                for candidate in self.mod_storage.list_mods_for_champion(champion_id)
                if candidate.path == target_dir
            ),
            None,
        )
        if installed is None:
            raise RuntimeError("Catalog package imported but was not visible in mod storage")

        state = self._load_installed_state()
        entries = state.setdefault("entries", {})
        previous = entries.get(entry.id)
        entries[entry.id] = {
            "sha256": entry.sha256,
            "relativePath": installed.path.relative_to(self.mod_storage.mods_root).as_posix(),
            "version": entry.version,
            "installedAt": int(time.time()),
        }
        self._save_installed_state(state)

        # If this catalog entry replaced an older managed install, remove that
        # old catalog-owned directory only after the new import succeeded.
        if isinstance(previous, dict):
            old_relative = str(previous.get("relativePath") or "").replace("\\", "/").strip("/")
            new_relative = installed.path.relative_to(self.mod_storage.mods_root).as_posix()
            if old_relative and old_relative.casefold() != new_relative.casefold():
                try:
                    old_path = (self.mod_storage.mods_root / Path(old_relative)).resolve()
                    mods_root = self.mod_storage.mods_root.resolve()
                    old_path.relative_to(mods_root)
                    if old_path.exists() and old_path != mods_root:
                        safe_remove_entry(old_path)
                except (OSError, ValueError) as exc:
                    log.debug("[CATALOG] Ignored unsafe replaced-install path: %s", exc)
                except Exception as exc:
                    log.debug("[CATALOG] Could not remove replaced catalog install: %s", exc)

        log.info("[CATALOG] Installed %s for champion %s", entry.name, champion_id)
        return installed
