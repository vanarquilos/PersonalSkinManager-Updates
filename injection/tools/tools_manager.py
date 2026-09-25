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
        """Check if the runtime injection tool is present."""
        required_tools = [
            "mod-tools.exe",
            "cslol-dll.dll",
        ]
        missing_tools = []
        for tool in required_tools:
            if not (self.tools_dir / tool).exists():
                missing_tools.append(tool)

        if missing_tools:
            log.warning(f"Missing runtime injection dependencies: {missing_tools}")
            log.warning(f"Expected runtime tools directory: {self.tools_dir}")
            if "mod-tools.exe" in missing_tools:
                log.warning(
                    "Development source checkout does not contain mod-tools.exe; "
                    "copy the trusted runtime binary from your installed PSM build "
                    "into injection/tools/ before live injection QA."
                )
            return False

        return True

    def detect_tools(self) -> Dict[str, Path]:
        """Detect runtime injection tools."""
        tools = {
            "modtools": self.tools_dir / "mod-tools.exe",
        }
        for name, exe in tools.items():
            if not exe.exists():
                log.error(f"[INJECTOR] Missing tool: {exe}")
        return tools
