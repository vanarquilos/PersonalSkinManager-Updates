#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Manager
Handles CSLOL tools detection and validation
"""

from pathlib import Path
from typing import Dict

from utils.core.logging import get_logger

log = get_logger()


class ToolsManager:
    """Manages CSLOL tools detection and validation"""

    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir

    def check_tools_available(self) -> bool:
        """Check whether overlay-builder and at least one patcher backend exist."""
        modtools = self.tools_dir / "mod-tools.exe"
        legacy_dll = self.tools_dir / "cslol-dll.dll"
        ltk_host = self.tools_dir / "ltk_patcher_host.exe"
        ltk_dll = self.tools_dir / "ltk_patcher_dll.dll"

        missing = []
        if not modtools.is_file():
            missing.append("mod-tools.exe")

        has_ltk_pair = ltk_host.is_file() and ltk_dll.is_file()
        has_legacy = legacy_dll.is_file()
        if not has_ltk_pair and not has_legacy:
            missing.append("LTK patcher pair or cslol-dll.dll")

        if missing:
            log.warning(f"Missing runtime injection dependencies: {missing}")
            log.warning(f"Expected runtime tools directory: {self.tools_dir}")
            if not modtools.is_file():
                log.warning(
                    "Development source checkout does not contain mod-tools.exe; "
                    "copy the trusted runtime binary from your installed PSM build "
                    "into injection/tools/ before live injection QA."
                )
            if not has_ltk_pair:
                log.warning(
                    "Patch 26.19 compatibility backend is unavailable: "
                    "ltk_patcher_host.exe + ltk_patcher_dll.dll were not found."
                )
            return False

        if has_ltk_pair:
            log.info("[INJECT] LTK patcher-host backend available")
        else:
            log.warning(
                "[INJECT] Only the legacy CSLOL runtime is available; "
                "current League compatibility may be limited."
            )
        return True

    def detect_tools(self) -> Dict[str, Path]:
        """Detect overlay builder and patcher runtime files."""
        tools = {
            "modtools": self.tools_dir / "mod-tools.exe",
            "ltk_host": self.tools_dir / "ltk_patcher_host.exe",
            "ltk_dll": self.tools_dir / "ltk_patcher_dll.dll",
            "legacy_dll": self.tools_dir / "cslol-dll.dll",
        }
        if not tools["modtools"].exists():
            log.error(f"[INJECTOR] Missing tool: {tools['modtools']}")
        return tools
