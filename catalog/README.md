# PSM Community Catalog

This directory defines the metadata format for Rose-style one-click community
mods. PSM downloads only the package selected by the user, verifies its SHA-256,
caches it under `%LOCALAPPDATA%\\Rose\\catalog\\packages`, then imports it
through the existing mod-storage pipeline.

The catalog is for community/custom content that can be handled by the current
supported patcher. It is not a switch for weakening or bypassing LTK's current
verification.

## Entry format

```json
{
  "id": "creator-mod-slug",
  "championId": 523,
  "name": "Display name",
  "author": "Creator",
  "description": "Short description",
  "previewUrl": "https://...",
  "packageUrl": "https://.../mod.fantome",
  "sha256": "64 lowercase hex characters",
  "targetSkinIds": [523000],
  "version": "1",
  "enabled": true
}
```

`targetSkinIds` controls which skin context shows the mod in the existing
Custom Wheel. The first implementation intentionally starts with an empty
catalog so packages can be curated and hash-pinned before being surfaced to
users.
