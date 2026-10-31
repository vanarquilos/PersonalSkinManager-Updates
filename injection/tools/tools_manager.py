#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Manager
Validates the overlay builder and current LTK runtime.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
import time

from utils.core.logging import get_logger
from utils.core.issue_reporter import clear_issue, report_issue
from .patcher import (
    LTK_PATCHER_DLL,
    LTK_PATCHER_HOST,
    check_ltk_patcher,
    read_game_build,
)

log = get_logger()


class ToolsManager:
    """Manages required overlay-builder and runtime files."""

    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir
        self.last_failure_code: Optional[str] = None

    def check_tools_available(self, game_dir: Optional[Path] = None) -> bool:
        """Require the runtime set and reject only unsupported League builds."""
        self.last_failure_code = None
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
            self.last_failure_code = "LTK_PATCHER_MISSING"
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
            self.last_failure_code = "LTK_PATCHER_EOL"
            # Replace old duplicated reports without discarding the current
            # issue's dedupe state on subsequent attempts.
            clear_issue("INJECTION_RUNTIME_UNAVAILABLE")
            clear_issue("LTK_PATCHER_EOL", legacy_only=True)
            eol_text = datetime.fromtimestamp(
                patcher.eol, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC")
            game_stamp = read_game_build(game_dir) if game_dir is not None else None
            game_text = (
                datetime.fromtimestamp(game_stamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                if game_stamp is not None else "unknown"
            )
            log.error(
                "[INJECT] Outdated LTK DLL (cutoff=%s; League build=%s)",
                eol_text, game_text,
            )
            report_issue(
                "LTK_PATCHER_EOL",
                "error",
                "LTK patcher outdated: its DLL does not support this League build.",
                hint=(
                    f"League executable: {game_text}; LTK cutoff: {eol_text}. "
                    "Obtain a newer official-compatible host and DLL pair. "
                    "Do not bypass patcher or game integrity controls."
                ),
                dedupe_window_s=120.0,
            )
            return False

        # Remove previous errors only after file/cutoff validation succeeds.
        # This is not proof that an in-game skin will render.
        clear_issue("LTK_PATCHER_EOL")
        clear_issue("INJECTION_RUNTIME_UNAVAILABLE")
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
