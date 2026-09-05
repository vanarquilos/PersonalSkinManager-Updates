from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from config import APP_VERSION
from utils.core.paths import get_user_data_dir
from utils.core.logging import get_named_logger

from .channel import (
    UPDATE_CHANNEL,
    UPDATE_MANIFEST_URL,
    UPDATE_PUBLIC_KEY_B64,
    AUTO_CHECK,
    AUTO_DOWNLOAD,
    AUTO_INSTALL_WHEN_SAFE,
)
from .client import download_verified_package, fetch_manifest
from .crypto import verify_manifest_signature
from .install import league_is_running, schedule_verified_installer
from .manifest import UpdateManifest, parse_semver

log = get_named_logger("psm_update", prefix="psm_update")


class UpdateResult(str, Enum):
    DISABLED = "disabled"
    UP_TO_DATE = "up_to_date"
    DEFERRED = "deferred"
    SCHEDULED = "scheduled"
    FAILED = "failed"


@dataclass
class PendingUpdate:
    manifest: UpdateManifest
    installer_path: Path


class PSMUpdateService:
    def __init__(self) -> None:
        self.root = get_user_data_dir() / "updates"
        self.staging = self.root / "staging"
        self.pending_path = self.root / "pending.json"

    @property
    def configured(self) -> bool:
        return bool(UPDATE_MANIFEST_URL and UPDATE_PUBLIC_KEY_B64)

    def _load_pending(self) -> PendingUpdate | None:
        if not self.pending_path.exists():
            return None
        try:
            data = json.loads(self.pending_path.read_text(encoding="utf-8"))
            raw_manifest = data["manifest"]
            verify_manifest_signature(raw_manifest, UPDATE_PUBLIC_KEY_B64)
            manifest = UpdateManifest.from_dict(raw_manifest)
            installer = Path(data["installer_path"])
            if not installer.exists():
                self.pending_path.unlink(missing_ok=True)
                return None
            return PendingUpdate(manifest=manifest, installer_path=installer)
        except Exception as exc:
            log.warning("Discarding invalid pending update: %s", exc)
            self.pending_path.unlink(missing_ok=True)
            return None

    def _save_pending(self, raw_manifest: dict, installer_path: Path) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.pending_path.write_text(
            json.dumps(
                {"manifest": raw_manifest, "installer_path": str(installer_path)},
                indent=2,
            ),
            encoding="utf-8",
        )

    def _clear_pending(self) -> None:
        self.pending_path.unlink(missing_ok=True)

    def run_startup_update(
        self,
        status_callback=None,
        progress_callback=None,
        dev_mode: bool = False,
    ) -> UpdateResult:
        if dev_mode or not AUTO_CHECK:
            return UpdateResult.DISABLED
        if not self.configured:
            log.info("PSM update channel is not configured; skipping.")
            return UpdateResult.DISABLED

        pending = self._load_pending()
        if pending:
            if parse_semver(pending.manifest.version) <= parse_semver(APP_VERSION):
                self._clear_pending()
            elif league_is_running():
                if status_callback:
                    status_callback("Verified update ready; waiting for League to close.")
                return UpdateResult.DEFERRED
            elif AUTO_INSTALL_WHEN_SAFE:
                if status_callback:
                    status_callback(
                        f"Installing Personal Skin Manager {pending.manifest.version}..."
                    )
                schedule_verified_installer(
                    pending.installer_path, APP_VERSION, pending.manifest.version
                )
                self._clear_pending()
                return UpdateResult.SCHEDULED

        try:
            if status_callback:
                status_callback("Checking Personal Skin Manager updates...")

            raw = fetch_manifest(UPDATE_MANIFEST_URL)
            verify_manifest_signature(raw, UPDATE_PUBLIC_KEY_B64)
            manifest = UpdateManifest.from_dict(raw)

            if manifest.channel != UPDATE_CHANNEL:
                raise ValueError(
                    f"Update channel mismatch: expected {UPDATE_CHANNEL}, got {manifest.channel}"
                )

            current = parse_semver(APP_VERSION)
            remote = parse_semver(manifest.version)
            minimum = parse_semver(manifest.minimum_version)

            if current < minimum:
                raise ValueError(
                    f"Update requires Personal Skin Manager {manifest.minimum_version} or newer"
                )
            if remote <= current:
                return UpdateResult.UP_TO_DATE
            if not AUTO_DOWNLOAD:
                return UpdateResult.DEFERRED

            if status_callback:
                status_callback(f"Downloading Personal Skin Manager {manifest.version}...")

            installer_path = self.staging / manifest.version / manifest.package.filename
            installer = download_verified_package(
                manifest, installer_path, progress_callback=progress_callback
            )
            self._save_pending(raw, installer)

            if league_is_running() or not AUTO_INSTALL_WHEN_SAFE:
                if status_callback:
                    status_callback(
                        "Update verified and saved. Installation deferred until League is closed."
                    )
                return UpdateResult.DEFERRED

            if status_callback:
                status_callback(f"Installing Personal Skin Manager {manifest.version}...")
            schedule_verified_installer(installer, APP_VERSION, manifest.version)
            self._clear_pending()
            return UpdateResult.SCHEDULED

        except Exception as exc:
            log.warning("PSM update check failed safely: %s", exc)
            if status_callback:
                status_callback("Application update check unavailable; continuing startup.")
            return UpdateResult.FAILED
