import sys
import pystray
from PIL import Image
from pathlib import Path


def _find_icon():
    """Search for icon.png in several likely locations."""
    candidates = [
        # Relative to this source file (running from source)
        Path(__file__).parent.parent / "assets" / "icon.png",
        # Relative to the exe (cx_Freeze bundled)
        Path(sys.executable).parent / "assets" / "icon.png",
        # Current working directory
        Path.cwd() / "assets" / "icon.png",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


class TrayIcon:
    def __init__(self, on_quit_callback):
        self._on_quit = on_quit_callback
        self._icon = None

    def start(self):
        icon_path = _find_icon()
        if icon_path:
            image = Image.open(icon_path)
        else:
            image = self._create_default_icon()

        menu = pystray.Menu(
            pystray.MenuItem("Push-to-Talk Active", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon(
            name="PTT",
            icon=image,
            title="Push-to-Talk Voice-to-Text",
            menu=menu,
        )
        self._icon.run()

    def stop(self):
        if self._icon:
            self._icon.stop()

    def _quit(self, icon, item):
        self._on_quit()
        self.stop()

    @staticmethod
    def _create_default_icon():
        """Blue fallback icon matching the app theme."""
        img = Image.new("RGB", (32, 32), color=(126, 184, 224))
        return img
