import threading
from typing import Callable

import pystray
from PIL import Image, ImageDraw


def _make_icon_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    # Draw a simple keyboard-like rectangle
    draw.rounded_rectangle([6, 18, 58, 46], radius=5, fill=(70, 130, 180))
    # Three small key squares
    for x in (14, 28, 42):
        draw.rounded_rectangle([x, 24, x + 8, 32], radius=2, fill=(220, 220, 220))
    draw.rounded_rectangle([14, 36, 50, 42], radius=2, fill=(220, 220, 220))
    return img


class TrayIcon:
    def __init__(self, on_show: Callable, on_quit: Callable):
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon: pystray.Icon | None = None

    def start(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Show / Hide", self._on_show, default=True),
            pystray.MenuItem("Quit", self._on_quit),
        )
        self._icon = pystray.Icon(
            "MacroApp",
            icon=_make_icon_image(),
            title="Macro App",
            menu=menu,
        )
        t = threading.Thread(target=self._icon.run, daemon=True)
        t.start()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
