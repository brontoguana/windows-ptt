import sys
import os
import ctypes
import ctypes.wintypes
import traceback
import logging
from pathlib import Path

# Set up file logging so crashes are visible even with base="gui" (no console)
_log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PTT"
_log_dir.mkdir(parents=True, exist_ok=True)
_log_file = _log_dir / "ptt.log"

logging.basicConfig(
    filename=str(_log_file),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
logging.info("PTT starting up")

# Win32 constants
MUTEX_NAME = "Global\\PTT_VoiceToText_SingleInstance"
EVENT_NAME = "Global\\PTT_VoiceToText_Shutdown"
ERROR_ALREADY_EXISTS = 183


def signal_existing_instance():
    """Signal the running instance to shut down via a named event."""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenEventW(0x2, False, EVENT_NAME)  # EVENT_MODIFY_STATE
    if handle:
        kernel32.SetEvent(handle)
        kernel32.CloseHandle(handle)
        # Give the old instance a moment to exit
        import time
        time.sleep(0.5)


def main():
    kernel32 = ctypes.windll.kernel32

    # Try to create a named mutex
    mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        # Another instance is running — tell it to quit, then take over
        print("Another instance detected, signalling it to exit...")
        kernel32.CloseHandle(mutex)
        signal_existing_instance()
        # Re-acquire the mutex now that the old instance should be gone
        mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)

    # Create the shutdown event that other instances can signal
    shutdown_event = kernel32.CreateEventW(None, True, False, EVENT_NAME)

    try:
        from ptt.app import App
        app = App(shutdown_event=shutdown_event)
        app.run()
    except Exception:
        logging.exception("Fatal error during startup or runtime")
        raise
    finally:
        kernel32.CloseHandle(shutdown_event)
        kernel32.ReleaseMutex(mutex)
        kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Unhandled exception in main()")
        # Show a visible error dialog so the user knows something went wrong
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"PTT failed to start. Check the log at:\n{_log_file}",
                "PTT Error",
                0x10,  # MB_ICONERROR
            )
        except Exception:
            pass
