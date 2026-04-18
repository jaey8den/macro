import threading
from typing import Callable

from pynput import keyboard, mouse

from models import Macro


def _is_mouse_hotkey(hotkey: str) -> bool:
    return hotkey.startswith("mouse:")


class HotkeyManager:
    def __init__(self):
        self._kb_hotkeys: dict[str, Callable] = {}    # "<ctrl>+<shift>+m" -> cb
        self._mouse_hotkeys: dict[str, Callable] = {}  # "mouse:x1" -> cb
        self._kb_listener: keyboard.GlobalHotKeys | None = None
        self._ms_listener: mouse.Listener | None = None
        self._lock = threading.Lock()
        self._paused = False

    def start(self) -> None:
        self._restart_listeners()

    def stop(self) -> None:
        with self._lock:
            self._stop_listeners_locked()

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            self._stop_listeners_locked()

    def resume(self) -> None:
        with self._lock:
            self._paused = False
        self._restart_listeners()

    def unregister(self, hotkey: str) -> None:
        with self._lock:
            if _is_mouse_hotkey(hotkey):
                self._mouse_hotkeys.pop(hotkey, None)
            else:
                self._kb_hotkeys.pop(hotkey, None)
        self._restart_listeners()

    def rebuild(self, macros: list[Macro], trigger_fn: Callable[[str], None]) -> None:
        with self._lock:
            self._kb_hotkeys = {}
            self._mouse_hotkeys = {}
            for macro in macros:
                if not macro.hotkey:
                    continue
                macro_id = macro.id
                cb = lambda mid=macro_id: trigger_fn(mid)
                if _is_mouse_hotkey(macro.hotkey):
                    self._mouse_hotkeys[macro.hotkey] = cb
                else:
                    self._kb_hotkeys[macro.hotkey] = cb
        self._restart_listeners()

    # --- Internal ---

    def _stop_listeners_locked(self) -> None:
        """Must be called with self._lock held."""
        if self._kb_listener:
            old = self._kb_listener
            self._kb_listener = None
            threading.Thread(target=old.stop, daemon=True).start()
        if self._ms_listener:
            old = self._ms_listener
            self._ms_listener = None
            threading.Thread(target=old.stop, daemon=True).start()

    def _restart_listeners(self) -> None:
        with self._lock:
            if self._paused:
                return
            self._stop_listeners_locked()

            if self._kb_hotkeys:
                try:
                    listener = keyboard.GlobalHotKeys(dict(self._kb_hotkeys))
                    listener.daemon = True
                    listener.start()
                    self._kb_listener = listener
                except Exception:
                    pass

            if self._mouse_hotkeys:
                try:
                    listener = mouse.Listener(on_click=self._on_mouse_click)
                    listener.daemon = True
                    listener.start()
                    self._ms_listener = listener
                except Exception:
                    pass

    def _on_mouse_click(self, x, y, button, pressed: bool) -> None:
        if not pressed:
            return
        key = f"mouse:{button.name}"
        # Read without lock — listener is stopped before _mouse_hotkeys is mutated
        cb = self._mouse_hotkeys.get(key)
        if cb:
            cb()
