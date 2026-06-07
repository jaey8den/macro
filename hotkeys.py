import re
import threading
from typing import Callable

from pynput import keyboard, mouse

from models import Macro


def _is_mouse_hotkey(hotkey: str) -> bool:
    return hotkey.startswith("mouse:")


_MOD_KEY_TO_STR = {
    keyboard.Key.ctrl_l:  "<ctrl>",   keyboard.Key.ctrl_r:  "<ctrl>",   keyboard.Key.ctrl:  "<ctrl>",
    keyboard.Key.shift_l: "<shift>",  keyboard.Key.shift_r: "<shift>",  keyboard.Key.shift: "<shift>",
    keyboard.Key.alt_l:   "<alt>",    keyboard.Key.alt_r:   "<alt>",    keyboard.Key.alt:   "<alt>",
    keyboard.Key.alt_gr:  "<alt_gr>",
    keyboard.Key.cmd_l:   "<cmd>",    keyboard.Key.cmd_r:   "<cmd>",    keyboard.Key.cmd:   "<cmd>",
}


def _is_vk_hotkey(hotkey: str) -> bool:
    return bool(re.search(r'<\d+>$', hotkey))


def _parse_vk_hotkey(hotkey: str):
    parts = hotkey.split("+")
    m = re.fullmatch(r'<(\d+)>', parts[-1])
    if not m:
        return None
    return (frozenset(parts[:-1]), int(m.group(1)))


class HotkeyManager:
    def __init__(self):
        self._kb_hotkeys: dict[str, Callable] = {}    # "<ctrl>+<shift>+m" -> cb
        self._vk_hotkeys: dict[tuple, Callable] = {}  # (frozenset_mods, vk_int) -> cb
        self._mouse_hotkeys: dict[str, Callable] = {}  # "mouse:x1" -> cb
        self._kb_listener: keyboard.GlobalHotKeys | None = None
        self._vk_listener: keyboard.Listener | None = None
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
            elif _is_vk_hotkey(hotkey):
                parsed = _parse_vk_hotkey(hotkey)
                if parsed:
                    self._vk_hotkeys.pop(parsed, None)
            else:
                self._kb_hotkeys.pop(hotkey, None)
        self._restart_listeners()

    def rebuild(self, macros: list[Macro], trigger_fn: Callable[[str], None]) -> None:
        with self._lock:
            self._kb_hotkeys = {}
            self._vk_hotkeys = {}
            self._mouse_hotkeys = {}
            for macro in macros:
                if not macro.hotkey:
                    continue
                macro_id = macro.id
                cb = lambda mid=macro_id: trigger_fn(mid)
                if _is_mouse_hotkey(macro.hotkey):
                    self._mouse_hotkeys[macro.hotkey] = cb
                elif _is_vk_hotkey(macro.hotkey):
                    parsed = _parse_vk_hotkey(macro.hotkey)
                    if parsed:
                        self._vk_hotkeys[parsed] = cb
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
        if self._vk_listener:
            old = self._vk_listener
            self._vk_listener = None
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

            if self._vk_hotkeys:
                vk_snapshot = dict(self._vk_hotkeys)
                held_mods: set[str] = set()

                def on_vk_press(key, _vk=vk_snapshot, _mods=held_mods):
                    mod = _MOD_KEY_TO_STR.get(key)
                    if mod:
                        _mods.add(mod)
                    elif isinstance(key, keyboard.KeyCode) and key.vk is not None:
                        cb = _vk.get((frozenset(_mods), key.vk))
                        if cb:
                            cb()

                def on_vk_release(key, _mods=held_mods):
                    mod = _MOD_KEY_TO_STR.get(key)
                    if mod:
                        _mods.discard(mod)

                listener = keyboard.Listener(on_press=on_vk_press, on_release=on_vk_release)
                listener.daemon = True
                listener.start()
                self._vk_listener = listener

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
