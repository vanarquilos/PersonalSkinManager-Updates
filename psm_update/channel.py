# PSM update-channel configuration.
# Deliberately disabled until the developer configures a manifest URL and
# generates the Ed25519 signing key. Never put the private key in this repo.

UPDATE_CHANNEL = "stable"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/vanarquilos/PersonalSkinManager-Updates/main/stable/manifest.json"
UPDATE_PUBLIC_KEY_B64 = "u5QzWedmJsTzTFWQx2Os9DrOlagA3aQeyz0rSO2IqXY="

AUTO_CHECK = True
AUTO_DOWNLOAD = True
AUTO_INSTALL_WHEN_SAFE = True

CHECK_TIMEOUT_S = 12
DOWNLOAD_TIMEOUT_S = 60
MAX_MANIFEST_BYTES = 128 * 1024
MAX_PACKAGE_BYTES = 512 * 1024 * 1024
