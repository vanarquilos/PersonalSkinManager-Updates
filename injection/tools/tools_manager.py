#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Manager
Validates the overlay builder and current LTK runtime.
"""

from datetime import datetime
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
        # The caller must not report another generic injection error when
        # this manager already recorded the actionable root cause.
        self.last_failure_code: Optional[str] = None

    def check_tools_available(self, game_dir: Optional[Path] = None) -> bool:
        """Require complete runtime, reject unsupported builds, report root cause."""
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
        missing = list(patcher.missing)
        missing.extend(name for name, path in required.items() if not path.is_file() and name not in missing)

        if missing:
            self.last_failure_code = "LTK_PATCHER_MISSING"
            log.error(f"[INJECT] Missing required runtime files: {missing}")
            log.error(f"[INJECT] Expected runtime tools directory: {self.tools_dir}")
            report_issue(
                "LTK_PATCHER_MISSING",
                "error",
                "PSM cannot apply skins: its required runtime files are missing.",
                hint=(
                    "Provide a verified official LTK host/DLL pair using the optional "
                    "local provisioning workflow; avoid unofficial downloads."
                ),
                dedupe_window_s=120.0,
            )
            return False

        if patcher.expired_for(game_dir):
            self.last_failure_code = "LTK_PATCHER_EOL"
            # Remove the previous generic secondary error before recording
            # one actionable expired-runtime message for this new attempt.
            clear_issue("INJECTION_RUNTIME_UNAVAILABLE")
            # Migrate only the previous bundled-runtime wording; preserve
            # deduplication for the current active expired-patcher message.
            clear_issue("LTK_PATCHER_EOL", legacy_only=True)
            # Align with Rose's patcher EOL interpretation: this is the
            # COMPATIBILITY boundary enforced by the DLL, not a packaging
            # warning or a condition that can be solved by retrying injection.
            eol_text = datetime.fromtimestamp(patcher.eol).strftime("%Y-%m-%d")
            game_stamp = read_game_build(game_dir) if game_dir is not None else None
            game_text = (
                datetime.fromtimestamp(game_stamp).strftime("%Y-%m-%d")
                if game_stamp is not None else "unknown"
            )
            log.error(
                "[INJECT] Patcher too old for this League executable "
                "(LTK DLL cutoff %s; League PE build %s)",
                eol_text,
                game_text,
            )
            report_issue(
                "LTK_PATCHER_EOL",
                "error",
                "LTK patcher outdated: this League build is newer than the selected DLL.",
                details={
                    "ltk_dll_cutoff": eol_text,
                    "league_pe_build": game_text,
                },
                hint=(
                    f"LTK supports game builds through {eol_text}; your League "
                    f"executable was built {game_text}. Replace BOTH LTK host "
                    "and DLL with a trusted, compatible pair, then restart PSM. "
                    "Do not reuse the expired pair or bypass compatibility checks."
                ),
                dedupe_window_s=120.0,
            )
            return False

        # On a verified newer runtime, clear obsolete EOL and generic
        # troubleshooting entries from earlier sessions. This does not prove
        # a custom skin will render in-game.
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
