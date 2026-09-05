#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CHANNEL = ROOT / "psm_update" / "channel.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-url", required=True)
    args = parser.parse_args()

    parsed = urlparse(args.manifest_url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise SystemExit("Manifest URL must use HTTPS")

    text = CHANNEL.read_text(encoding="utf-8")
    if not re.search(r'^UPDATE_MANIFEST_URL = ".*"$', text, flags=re.MULTILINE):
        raise SystemExit("Could not find UPDATE_MANIFEST_URL in channel.py")

    text = re.sub(
        r'^UPDATE_MANIFEST_URL = ".*"$',
        f'UPDATE_MANIFEST_URL = "{args.manifest_url}"',
        text,
        flags=re.MULTILINE,
    )
    CHANNEL.write_text(text, encoding="utf-8", newline="\n")
    print("[OK] Configured PSM stable update manifest URL:")
    print(args.manifest_url)


if __name__ == "__main__":
    main()
