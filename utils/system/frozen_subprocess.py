"""Start an independent Windows process without inheriting PyInstaller DLL paths.

PyInstaller's Windows bootloader calls SetDllDirectoryW(sys._MEIPASS). That
setting is inherited by child processes, potentially redirecting unrelated
vendor EXE dependencies into PSM's frozen Python runtime. Reset it only for
the short Popen call, then restore the original setting. No signature, process
token, or Windows/game security settings are modified.
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import threading

_spawn_lock = threading.RLock()


def popen_external(command, **kwargs):
    """Launch a reviewed independent EXE with the system DLL search order.

    Source Python uses its normal environment unchanged. For frozen Windows,
    preserve and restore the exact previous DLL directory, even if Popen fails.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return subprocess.Popen(command, **kwargs)

    if not getattr(sys, "_MEIPASS", None):
        raise RuntimeError("Frozen Windows app lacks its PyInstaller runtime directory")

    with _spawn_lock:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_dir = kernel32.GetDllDirectoryW
        get_dir.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
        get_dir.restype = ctypes.c_uint32
        set_dir = kernel32.SetDllDirectoryW
        set_dir.argtypes = [ctypes.c_wchar_p]
        set_dir.restype = ctypes.c_int

        size = get_dir(0, None)
        previous = None
        if size:
            # If the directory changed between calls, fail closed rather than
            # restore an incomplete path after launching an external program.
            buffer = ctypes.create_unicode_buffer(size)
            copied = get_dir(size, buffer)
            if copied == 0 or copied >= size:
                raise RuntimeError("Unable to read frozen DLL search directory")
            previous = buffer.value

        if not set_dir(None):
            raise OSError(ctypes.get_last_error(), "Could not reset Windows DLL directory")

        try:
            return subprocess.Popen(command, **kwargs)
        finally:
            if not set_dir(previous):
                raise OSError(
                    ctypes.get_last_error(),
                    "Could not restore PyInstaller DLL search directory",
                )
