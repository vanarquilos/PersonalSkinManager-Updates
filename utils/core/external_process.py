"""Launch external tools without inheriting PyInstaller's DLL search override.

PyInstaller changes the process-wide Windows DLL search directory while a
frozen program runs. External EXEs should use their own adjacent DLLs and
normal Windows search paths, not the Python bundle's library directory.
This helper restores the prior frozen directory immediately after Popen.

No security checks, game files, vendor binaries, or patcher flags are changed.
"""
from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
import threading

_DLL_LAUNCH_LOCK = threading.RLock()
_LOG = logging.getLogger(__name__)


def popen_external(*args, **kwargs) -> subprocess.Popen:
    """Spawn an external EXE with standard Windows DLL lookup when frozen.

    The DLL setting is process-global; serialize our subprocess launch sites
    and keep its temporary change confined to the Popen call. Child processes
    inherit the default DLL search setting on Windows.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return subprocess.Popen(*args, **kwargs)

    bundled_dir = getattr(sys, "_MEIPASS", None)
    if not bundled_dir:
        raise RuntimeError("Frozen Windows DLL directory unavailable")

    with _DLL_LAUNCH_LOCK:
        set_dll_directory = ctypes.windll.kernel32.SetDllDirectoryW
        if not set_dll_directory(None):
            raise OSError(ctypes.get_last_error(), "Cannot reset DLL search directory for external executable")
        try:
            return subprocess.Popen(*args, **kwargs)
        finally:
            if not set_dll_directory(str(bundled_dir)):
                _LOG.error("Could not restore frozen DLL search directory after external process launch")
