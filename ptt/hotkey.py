import time
from pynput import keyboard

from ptt.config import DOUBLE_TAP_WINDOW_S

_PTT_KEYS = {keyboard.Key.insert, keyboard.Key.ctrl_r}


class HotkeyListener:
    def __init__(self, on_start_callback, on_stop_callback, on_cancel_callback):
        self._on_start_cb = on_start_callback
        self._on_stop_cb = on_stop_callback
        self._on_cancel_cb = on_cancel_callback
        self._listener = None

        self._recording = False
        self._key_held = False          # True while a PTT key is physically down
        self._last_tap_time = 0.0       # monotonic time of last completed tap
        self._ignore_next_release = False

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_press(self, key):
        if key in _PTT_KEYS:
            if self._key_held:
                return  # Ignore key-repeat
            self._key_held = True

            if self._recording:
                # Single tap to stop recording
                self._recording = False
                self._ignore_next_release = True
                self._on_stop_cb()
            else:
                # Check for double-tap
                now = time.monotonic()
                if now - self._last_tap_time <= DOUBLE_TAP_WINDOW_S:
                    # Double-tap detected — start recording
                    self._recording = True
                    self._last_tap_time = 0.0
                    self._ignore_next_release = True
                    self._on_start_cb()

        elif key == keyboard.Key.esc and self._recording:
            self._recording = False
            self._on_cancel_cb()

    def _on_release(self, key):
        if key in _PTT_KEYS and self._key_held:
            self._key_held = False
            if self._ignore_next_release:
                self._ignore_next_release = False
            else:
                # Record this tap time for double-tap detection
                self._last_tap_time = time.monotonic()
