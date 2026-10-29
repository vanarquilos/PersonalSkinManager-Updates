#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Manager
Validates the overlay builder and current LTK runtime.
"""

from pathlib import Path
from typing import Dict, Optional
import time

from utils.core.logging import get_logger
from utils.core.issue_reporter import report_issue
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

    def check_tools_available(self, game_dir: Optional[Path] = None) -> bool:
        """Require the runtime set and reject only unsupported League builds."""
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
            log.error(f"[INJECT] Missing required runtime files: {missing}")
            log.error(f"[INJECT] Expected runtime tools directory: {self.tools_dir}")
            report_issue(
                "LTK_PATCHER_MISSING",
                "error",
                "PSM cannot apply skins: its required runtime files are missing.",
                hint="Use a complete, trusted PSM installer; do not download random DLLs.",
                dedupe_window_s=120.0,
            )
            return False

        if patcher.expired_for(game_dir):
            eol_text = time.strftime("%Y-%m-%d %H:%M", time.localtime(patcher.eol))
            log.error(
                "[INJECT] Current LTK runtime does not support this League build "
                "(build cutoff %s)",
                eol_text,
            )
            report_issue(
                "LTK_PATCHER_EOL",
                "error",
                "PSM cannot apply skins: the bundled LTK runtime does not support this League build.",
                hint=(
                    "A compatible and trusted LTK runtime is required. "
                    "Do not bypass the cutoff or disable game security checks."
                ),
                dedupe_window_s=120.0,
            )
            return False

        # This check establishes file presence and that no known cutoff was
        # exceeded. It CANNOT prove overlay/material compatibility.
        log.info("[INJECT] Runtime files present; no known League-build cutoff exceeded")
        return True

    def detect_tools(self) -> Dict[str, Path]:
        """Return overlay builder and current LTK runtime paths."""
        patcher = check_ltk_patcher(self.tools_dir)
        tools = {
            "modtools": self.tools_dir / "mod-tools.exe",
            "ltk_host": patcher.host,
            "ltk_dll": patcher.dll,
        }
        for name, path in tools.items():
            if not path.exists():
                log.error(f"[INJECTOR] Missing tool {name}: {path}")
        return tools
