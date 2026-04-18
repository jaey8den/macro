import threading
import time
from typing import Callable

from pynput import keyboard, mouse

from models import Macro, MacroKey


def parse_key(key_str: str) -> keyboard.Key | keyboard.KeyCode:
    if key_str.startswith("Key."):
        attr = key_str[4:]
        try:
            return keyboard.Key[attr]
        except KeyError:
            pass
    if key_str.startswith("<") and key_str.endswith(">"):
        try:
            return keyboard.KeyCode(vk=int(key_str[1:-1]))
        except ValueError:
            pass
    if len(key_str) == 1:
        return keyboard.KeyCode.from_char(key_str)
    return keyboard.KeyCode.from_char(key_str)


def _parse_mouse_button(button_str: str) -> mouse.Button:
    return getattr(mouse.Button, button_str, mouse.Button.left)


class MacroPlayer:
    def __init__(self, macro: Macro, on_done: Callable[[], None] | None = None):
        self._macro = macro
        self._on_done = on_done
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._kb = keyboard.Controller()
        self._mouse = mouse.Controller()
        # Track what's currently held for cleanup on stop
        self._held_keys: list[keyboard.Key | keyboard.KeyCode] = []
        self._held_buttons: list[mouse.Button] = []

    def start(self) -> None:
        self._stop_event.clear()
        self._held_keys.clear()
        self._held_buttons.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _do_action(self, mk: MacroKey) -> None:
        if mk.type == "click":
            btn = _parse_mouse_button(mk.button)
            if mk.action == "press":
                self._mouse.position = (mk.x, mk.y)
                self._mouse.press(btn)
                self._held_buttons.append(btn)
            else:
                self._mouse.release(btn)
                if btn in self._held_buttons:
                    self._held_buttons.remove(btn)
        else:
            key = parse_key(mk.key)
            if mk.action == "press":
                self._kb.press(key)
                self._held_keys.append(key)
            else:
                self._kb.release(key)
                # Remove last matching entry (handles repeated presses)
                for i in reversed(range(len(self._held_keys))):
                    if str(self._held_keys[i]) == str(key):
                        self._held_keys.pop(i)
                        break

    def _release_all_held(self) -> None:
        for key in reversed(self._held_keys):
            try:
                self._kb.release(key)
            except Exception:
                pass
        for btn in reversed(self._held_buttons):
            try:
                self._mouse.release(btn)
            except Exception:
                pass
        self._held_keys.clear()
        self._held_buttons.clear()

    def _play_once(self) -> bool:
        """Play the sequence once. Returns False if interrupted."""
        for mk in self._macro.keys:
            if self._stop_event.is_set():
                return False
            try:
                self._do_action(mk)
            except Exception:
                pass
            if mk.delay_after > 0:
                if self._stop_event.wait(timeout=mk.delay_after):
                    return False
        return True

    def _run(self) -> None:
        try:
            if self._macro.loop:
                while not self._stop_event.is_set():
                    if not self._play_once():
                        break
            else:
                self._play_once()
        finally:
            self._release_all_held()
            if self._on_done and not self._stop_event.is_set():
                self._on_done()
