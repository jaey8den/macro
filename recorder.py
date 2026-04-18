import threading
import time
from typing import Callable

from pynput import keyboard, mouse

from models import MacroKey


def _normalize_key(key) -> str:
    if isinstance(key, keyboard.Key):
        return f"Key.{key.name}"
    if isinstance(key, keyboard.KeyCode):
        if key.char is not None:
            return key.char
        if key.vk is not None:
            return f"<{key.vk}>"
    return str(key)


class KeyRecorder:
    def __init__(self):
        self._kb_listener: keyboard.Listener | None = None
        self._ms_listener: mouse.Listener | None = None
        self._sequence: list[MacroKey] = []
        self._last_action_time: float = 0.0
        self._lock = threading.Lock()
        self._on_update: Callable[[list[MacroKey]], None] | None = None

    def start(self, on_update: Callable[[list[MacroKey]], None]) -> None:
        self._on_update = on_update
        self._sequence = []
        self._last_action_time = time.monotonic()

        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._ms_listener = mouse.Listener(
            on_click=self._on_mouse_click,
        )
        self._kb_listener.start()
        self._ms_listener.start()

    def stop(self) -> list[MacroKey]:
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None
        if self._ms_listener:
            self._ms_listener.stop()
            self._ms_listener = None
        with self._lock:
            return list(self._sequence)

    def _append(self, entry: MacroKey) -> list[MacroKey]:
        """Finalize delay_after of previous entry, append new one, return snapshot."""
        now = time.monotonic()
        if self._sequence:
            self._sequence[-1].delay_after = round(max(0.0, now - self._last_action_time), 4)
        self._last_action_time = now
        self._sequence.append(entry)
        return list(self._sequence)

    def _on_key_press(self, key) -> None:
        key_str = _normalize_key(key)
        with self._lock:
            snapshot = self._append(MacroKey(type="key", action="press", key=key_str, delay_after=0.0))
        if self._on_update:
            self._on_update(snapshot)

    def _on_key_release(self, key) -> None:
        key_str = _normalize_key(key)
        with self._lock:
            snapshot = self._append(MacroKey(type="key", action="release", key=key_str, delay_after=0.0))
        if self._on_update:
            self._on_update(snapshot)

    def _on_mouse_click(self, x: int, y: int, button, pressed: bool) -> None:
        btn_str = button.name  # "left", "right", "middle", "x1", "x2"
        action = "press" if pressed else "release"
        with self._lock:
            snapshot = self._append(MacroKey(
                type="click", action=action,
                button=btn_str, x=x, y=y,
                delay_after=0.0,
            ))
        if self._on_update:
            self._on_update(snapshot)
