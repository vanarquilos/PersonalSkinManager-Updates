#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Manager
Validates the v1.0.2 overlay builder and current LTK runtime.
"""

from pathlib import Path
from typing import Dict

from utils.core.logging import get_logger

log = get_logger()


class ToolsManager:
    """Manages required overlay-builder and runtime files."""

    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir

    def check_tools_available(self) -> bool:
        """Require the complete v1.0.2 runtime set."""
        modtools = self.tools_dir / "mod-tools.exe"
        ltk_host = self.tools_dir / "ltk_patcher_host.exe"
        ltk_dll = self.tools_dir / "ltk_patcher_dll.dll"

        required = {
            "mod-tools.exe": modtools,
            "ltk_patcher_host.exe": ltk_host,
            "ltk_patcher_dll.dll": ltk_dll,
        }
        missing = [name for name, path in required.items() if not path.is_file()]

        if missing:
            log.error(f"[INJECT] Missing required v1.0.2 runtime files: {missing}")
            log.error(f"[INJECT] Expected runtime tools directory: {self.tools_dir}")
            return False

        log.info("[INJECT] Current LTK patcher-host backend available")
        return True

    def detect_tools(self) -> Dict[str, Path]:
        """Return the v1.0.2 overlay builder and current LTK runtime paths."""
        tools = {
            "modtools": self.tools_dir / "mod-tools.exe",
            "ltk_host": self.tools_dir / "ltk_patcher_host.exe",
            "ltk_dll": self.tools_dir / "ltk_patcher_dll.dll",
        }
        for name, path in tools.items():
            if not path.exists():
                log.error(f"[INJECTOR] Missing tool {name}: {path}")
        return tools
