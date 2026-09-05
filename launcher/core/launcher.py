"""
Native Win32 startup dialog used to prepare Personal Skin Manager before launching.

This replaces the former PyQt-based launcher with a lightweight Steam-style
progress window that:
    1. Verifies local skin/game data.
    2. Synchronizes required skin content when needed.

Once all checks succeed, the dialog closes automatically and the main
application continues bootstrapping.
"""

from __future__ import annotations

import sys
import threading
import time

from utils.core.logging import get_logger, get_named_logger
from utils.system.win32_base import (
    WM_CLOSE,
    SW_SHOWNORMAL,
    user32,
)

from ..ui.update_dialog import UpdateDialog
from ..sequences.hash_check_sequence import HashCheckSequence
from ..sequences.skin_sync_sequence import SkinSyncSequence
from psm_update import PSMUpdateService, UpdateResult

log = get_logger()
updater_log = get_named_logger("updater", prefix="log_updater")

MB_ICONERROR = 0x00000010
MB_OK = 0x00000000
MB_TOPMOST = 0x00040000


def _show_error(message: str) -> None:
    """Show error dialog to user"""
    try:
        user32.MessageBoxW(
            None,
            message,
            "Personal Skin Manager - Launcher",
            MB_OK | MB_ICONERROR | MB_TOPMOST,
        )
        updater_log.error(f"Error dialog shown to user: {message}")
    except Exception:
        print(f"[Launcher] ERROR: {message}")
        updater_log.exception("Failed to show error dialog", exc_info=True)




def _perform_psm_application_update(dialog: UpdateDialog, dev_mode: bool = False) -> bool:
    # Returns True only when a verified installer has been scheduled.
    if dev_mode:
        updater_log.info("PSM application update check skipped in dev mode.")
        return False

    service = PSMUpdateService()

    def status(message: str) -> None:
        dialog.set_detail("Application update")
        dialog.set_status(message)
        dialog.pump_messages()
        updater_log.info("PSM update: %s", message)

    def progress(downloaded: int, total: int) -> None:
        dialog.update_transfer_progress(downloaded, total)
        dialog.pump_messages()

    result = service.run_startup_update(
        status_callback=status,
        progress_callback=progress,
        dev_mode=dev_mode,
    )

    if result == UpdateResult.SCHEDULED:
        dialog.set_detail("Verified update ready")
        dialog.set_status("Restarting to install Personal Skin Manager update...")
        dialog.set_progress(100)
        dialog.pump_messages()
        time.sleep(0.8)
        updater_log.info("Verified PSM update scheduled; exiting current process.")
        return True

    if result == UpdateResult.DEFERRED:
        updater_log.info("Verified PSM update deferred until League is closed.")
    elif result == UpdateResult.FAILED:
        updater_log.warning("PSM update check failed safely; startup continues.")
    return False


def run_launcher(dev_mode: bool = False, test_download_fail: bool = False) -> None:
    """Display the Win32 update dialog and perform startup checks.

    Args:
        dev_mode: If True, skip hash checks (for development)
        test_download_fail: If True, force skin download to fail (for testing)
    """
    if sys.platform != "win32":
        log.debug("Win32 launcher skipped on non-Windows platform.")
        return

    updater_log.info("Launcher sequence starting.")
    dialog = UpdateDialog()
    try:
        dialog.show_window(SW_SHOWNORMAL)
        dialog.pump_messages()
        updater_log.info("Update dialog displayed.")

        result: dict[str, Exception] = {}
        done_event = threading.Event()

        def worker():
            try:
                if _perform_psm_application_update(dialog, dev_mode=dev_mode):
                    os._exit(0)

                hash_sequence = HashCheckSequence()
                hash_sequence.perform_hash_check(dialog, dev_mode=dev_mode)
                
                skin_sequence = SkinSyncSequence()
                skin_sequence.perform_skin_sync(dialog, test_fail=test_download_fail)

                dialog.set_detail("All checks complete.")
                dialog.set_status("Launching Personal Skin Manager…")
                dialog.set_progress(100)
                dialog.pump_messages()
                time.sleep(0.4)
                updater_log.info("Launcher sequence completed successfully.")
            except SystemExit:
                updater_log.info("Launcher sequence exiting due to SystemExit (expected for update restart).")
                raise
            except Exception as exc:  # noqa: BLE001
                result["error"] = exc
                log.error(f"Launcher error: {exc}", exc_info=True)
                _show_error(f"Failed to prepare Personal Skin Manager:\n\n{exc}")
                updater_log.exception("Launcher sequence crashed", exc_info=True)
            finally:
                dialog.allow_close()
                if dialog.hwnd:
                    user32.PostMessageW(dialog.hwnd, WM_CLOSE, 0, 0)
                done_event.set()

        worker_thread = threading.Thread(target=worker, name="LauncherWorker", daemon=True)
        worker_thread.start()

        while not done_event.is_set():
            if not dialog.pump_messages(block=True):
                break

        worker_thread.join()

        if "error" in result:
            raise result["error"]
    finally:
        dialog.destroy_window()
        updater_log.info("Update dialog resources released.")
