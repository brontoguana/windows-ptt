import tkinter as tk
import ctypes

from ptt.config import (
    OVERLAY_WIDTH,
    OVERLAY_HEIGHT,
    OVERLAY_BG,
    OVERLAY_FG,
    OVERLAY_FG_DIM,
    OVERLAY_FONT,
    OVERLAY_OPACITY,
    OVERLAY_POSITION,
)

# Win32 constants
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
HWND_TOPMOST = -1

user32 = ctypes.windll.user32

class Overlay:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._window = None
        self._text_widget = None
        self._status_label = None
        self._is_visible = False
        self._create_window()

    def _create_window(self):
        self._window = tk.Toplevel(self._root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.attributes("-alpha", OVERLAY_OPACITY)
        self._window.configure(bg=OVERLAY_BG)

        screen_w = self._window.winfo_screenwidth()
        screen_h = self._window.winfo_screenheight()
        if OVERLAY_POSITION == "bottom_right":
            x = screen_w - OVERLAY_WIDTH - 20
            y = screen_h - OVERLAY_HEIGHT - 60
        elif OVERLAY_POSITION == "top_right":
            x = screen_w - OVERLAY_WIDTH - 20
            y = 20
        else:
            x = (screen_w - OVERLAY_WIDTH) // 2
            y = (screen_h - OVERLAY_HEIGHT) // 2

        self._window.geometry(f"{OVERLAY_WIDTH}x{OVERLAY_HEIGHT}+{x}+{y}")

        # Status bar at top (recording indicator + ESC hint)
        self._status_label = tk.Label(
            self._window,
            text="  Recording...  (hit ESC to cancel)",
            font=(OVERLAY_FONT[0], 9),
            fg=OVERLAY_FG_DIM,
            bg=OVERLAY_BG,
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=8, pady=(8, 0))

        # Separator line between status and text
        separator = tk.Frame(self._window, bg=OVERLAY_FG_DIM, height=1)
        separator.pack(fill="x", padx=12, pady=(6, 0))

        # Scrolling text area for live transcription
        self._text_widget = tk.Text(
            self._window,
            font=OVERLAY_FONT,
            fg=OVERLAY_FG,
            bg=OVERLAY_BG,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=6,
            cursor="arrow",       # Don't show text cursor
            state="disabled",     # Read-only
        )
        self._text_widget.pack(fill="both", expand=True, padx=4, pady=(4, 8))

        self._window.withdraw()
        self._window.after(10, self._apply_noactivate_style)

    def _apply_noactivate_style(self):
        hwnd = user32.GetParent(self._window.winfo_id())
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

    def show(self):
        if not self._is_visible:
            self._status_label.config(text="  Recording...  (hit ESC to cancel)")
            self._text_widget.config(state="normal")
            self._text_widget.delete("1.0", "end")
            self._text_widget.config(state="disabled")
            self._window.deiconify()
            self._is_visible = True
            hwnd = user32.GetParent(self._window.winfo_id())
            user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )

    def hide(self):
        if self._is_visible:
            self._window.withdraw()
            self._is_visible = False

    def set_status(self, text: str):
        self._status_label.config(text=text)

    def set_transcription(self, text: str):
        self._text_widget.config(state="normal")
        self._text_widget.delete("1.0", "end")
        if text:
            self._text_widget.insert("1.0", text)
        self._text_widget.see("end")  # Auto-scroll to bottom
        self._text_widget.config(state="disabled")

    def destroy(self):
        if self._window:
            self._window.destroy()
