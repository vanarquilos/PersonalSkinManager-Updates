from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class UpdatePackage:
    type: str
    url: str
    sha256: str
    size: int
    filename: str


@dataclass(frozen=True)
class UpdateManifest:
    schema: int
    channel: str
    version: str
    minimum_version: str
    published_at: str
    release_notes: str
    package: UpdatePackage
    signature: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateManifest":
        required = {
            "schema", "channel", "version", "minimum_version",
            "published_at", "release_notes", "package", "signature",
        }
        missing = required.difference(data)
        if missing:
            raise ManifestError(f"Manifest missing field(s): {', '.join(sorted(missing))}")
        if data["schema"] != 1:
            raise ManifestError("Unsupported manifest schema")

        version = str(data["version"])
        minimum_version = str(data["minimum_version"])
        if not SEMVER_RE.fullmatch(version) or not SEMVER_RE.fullmatch(minimum_version):
            raise ManifestError("Manifest versions must use x.y.z semantic versions")

        package_data = data["package"]
        if not isinstance(package_data, dict):
            raise ManifestError("package must be an object")
        package_required = {"type", "url", "sha256", "size", "filename"}
        missing_package = package_required.difference(package_data)
        if missing_package:
            raise ManifestError(
                f"Package missing field(s): {', '.join(sorted(missing_package))}"
            )

        package = UpdatePackage(
            type=str(package_data["type"]),
            url=str(package_data["url"]),
            sha256=str(package_data["sha256"]).lower(),
            size=int(package_data["size"]),
            filename=str(package_data["filename"]),
        )

        if package.type != "inno":
            raise ManifestError("Only Inno Setup update packages are supported")
        if not re.fullmatch(r"[0-9a-f]{64}", package.sha256):
            raise ManifestError("Package SHA-256 is invalid")
        if package.size <= 0:
            raise ManifestError("Package size must be positive")
        if package.filename != "PersonalSkinManager_Setup.exe":
            raise ManifestError("Unexpected update package filename")

        return cls(
            schema=1,
            channel=str(data["channel"]),
            version=version,
            minimum_version=minimum_version,
            published_at=str(data["published_at"]),
            release_notes=str(data["release_notes"]),
            package=package,
            signature=str(data["signature"]),
        )


def canonical_signed_bytes(raw: dict[str, Any]) -> bytes:
    payload = dict(raw)
    payload.pop("signature", None)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def parse_semver(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value)
    if not match:
        raise ManifestError(f"Invalid semantic version: {value}")
    return tuple(int(x) for x in match.groups())
