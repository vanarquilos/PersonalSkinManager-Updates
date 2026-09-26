#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Manager
Validates the v1.0.2 overlay builder and current LTK runtime.
"""

from pathlib import Path
from typing import Dict
import time

from utils.core.logging import get_logger
from .patcher import (
    LTK_PATCHER_DLL,
    LTK_PATCHER_HOST,
    check_ltk_patcher,
)

log = get_logger()


class ToolsManager:
    """Manages required overlay-builder and runtime files."""

    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir

    def check_tools_available(self) -> bool:
        """Require the complete v1.0.2 runtime set."""
        modtools = self.tools_dir / "mod-tools.exe"
        patcher = check_ltk_patcher(self.tools_dir)
        ltk_host = patcher.host
        ltk_dll = patcher.dll

        required = {
            "mod-tools.exe": modtools,
            LTK_PATCHER_HOST: ltk_host,
            LTK_PATCHER_DLL: ltk_dll,
        }
        missing = [name for name, path in required.items() if not path.is_file()]

        if missing:
            log.error(f"[INJECT] Missing required v1.0.2 runtime files: {missing}")
            log.error(f"[INJECT] Expected runtime tools directory: {self.tools_dir}")
            return False

        if patcher.expired:
            eol_text = time.strftime("%Y-%m-%d %H:%M", time.localtime(patcher.eol))
            log.error(
                "[INJECT] Current LTK runtime reached end of life on %s",
                eol_text,
            )
            return False

        log.info("[INJECT] Current LTK patcher-host backend available")
        return True

    def detect_tools(self) -> Dict[str, Path]:
        """Return the v1.0.2 overlay builder and current LTK runtime paths."""
        tools = {
            "modtools": self.tools_dir / "mod-tools.exe",
            "ltk_host": self.tools_dir / LTK_PATCHER_HOST,
            "ltk_dll": self.tools_dir / LTK_PATCHER_DLL,
        }
        for name, path in tools.items():
            if not path.exists():
                log.error(f"[INJECTOR] Missing tool {name}: {path}")
        return tools
