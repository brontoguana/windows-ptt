import time
from pynput.keyboard import Key, Controller

from ptt.config import PASTE_DELAY_MS


class Paster:
    def __init__(self, tk_root):
        self._root = tk_root
        self._keyboard = Controller()

    def paste(self, text: str):
        if not text:
            return

        self._root.clipboard_clear()
        self._root.clipboard_append(text)
        self._root.update()

        time.sleep(PASTE_DELAY_MS / 1000.0)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press('v')
        self._keyboard.release('v')
        self._keyboard.release(Key.ctrl)
