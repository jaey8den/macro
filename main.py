import os
import threading
import tkinter as tk
from pathlib import Path

from hotkeys import HotkeyManager
from models import Macro
from player import MacroPlayer
from store import MacroStore
from tray import TrayIcon
from ui_editor import EditorDialog
from ui_main import MainWindow


class App:
    def __init__(self):
        os.chdir(Path(__file__).parent)

        self._root = tk.Tk()
        self._root.withdraw()

        self._store = MacroStore()
        self._store.load()

        self._hotkey_manager = HotkeyManager()
        self._players: dict[str, MacroPlayer] = {}
        self._players_lock = threading.Lock()

        self._main_window = MainWindow(
            root=self._root,
            macros_getter=self._store.all,
            on_new=self._open_new_editor,
            on_edit=self._open_edit_editor,
            on_delete=self._delete_macro,
        )

        self._tray = TrayIcon(
            on_show=self._toggle_window,
            on_quit=self.quit,
        )

    def run(self) -> None:
        self._tray.start()
        self._hotkey_manager.start()
        self._hotkey_manager.rebuild(self._store.all(), self._on_trigger)
        self._main_window.refresh_list()
        # Show window on first launch
        self._root.after(100, self._main_window.show)
        self._root.mainloop()

    # --- Window visibility ---

    def _toggle_window(self) -> None:
        if self._root.state() == "withdrawn":
            self._root.after(0, self._main_window.show)
        else:
            self._root.after(0, self._main_window.hide)

    def show_window(self) -> None:
        self._root.after(0, self._main_window.show)

    # --- Macro trigger (called from hotkey listener thread) ---

    def _on_trigger(self, macro_id: str) -> None:
        macro = self._store.get(macro_id)
        if not macro:
            return

        with self._players_lock:
            if macro.loop:
                if macro_id in self._players and self._players[macro_id].is_running:
                    self._players[macro_id].stop()
                    del self._players[macro_id]
                    self._root.after(0, lambda: self._main_window.set_status(f"Stopped: {macro.name}"))
                    return
            else:
                if macro_id in self._players and self._players[macro_id].is_running:
                    return  # one-shot: ignore if already running

            def on_done(mid=macro_id, mname=macro.name):
                with self._players_lock:
                    self._players.pop(mid, None)
                self._root.after(0, lambda: self._main_window.set_status(f"Done: {mname}"))

            player = MacroPlayer(macro, on_done=on_done)
            self._players[macro_id] = player

        player.start()
        self._root.after(0, lambda: self._main_window.set_status(
            f"{'Looping' if macro.loop else 'Playing'}: {macro.name}"
        ))

    # --- Editor ---

    def _open_new_editor(self) -> None:
        EditorDialog(
            parent=self._root,
            macro=None,
            all_macros=self._store.all(),
            hotkey_manager=self._hotkey_manager,
            on_saved=self._on_macro_saved,
        ).show()

    def _open_edit_editor(self, macro: Macro) -> None:
        EditorDialog(
            parent=self._root,
            macro=macro,
            all_macros=self._store.all(),
            hotkey_manager=self._hotkey_manager,
            on_saved=self._on_macro_saved,
        ).show()

    def _on_macro_saved(self, macro: Macro) -> None:
        # Unregister old hotkey if editing an existing macro
        existing = self._store.get(macro.id)
        if existing and existing.hotkey and existing.hotkey != macro.hotkey:
            self._hotkey_manager.unregister(existing.hotkey)

        self._store.upsert(macro)
        self._hotkey_manager.rebuild(self._store.all(), self._on_trigger)
        self._main_window.refresh_list()
        self._main_window.set_status(f"Saved: {macro.name}")

    def _delete_macro(self, macro: Macro) -> None:
        # Stop any active playback
        with self._players_lock:
            player = self._players.pop(macro.id, None)
        if player:
            player.stop()

        if macro.hotkey:
            self._hotkey_manager.unregister(macro.hotkey)
        self._store.delete(macro.id)
        self._main_window.refresh_list()
        self._main_window.set_status(f"Deleted: {macro.name}")

    # --- Quit ---

    def quit(self) -> None:
        with self._players_lock:
            players = list(self._players.values())
            self._players.clear()
        for p in players:
            p.stop()
        self._hotkey_manager.stop()
        self._tray.stop()
        self._root.after(0, self._root.destroy)


if __name__ == "__main__":
    App().run()
