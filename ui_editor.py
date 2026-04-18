import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse

from hotkeys import HotkeyManager
from models import Macro, MacroKey
from recorder import KeyRecorder

# Arrow symbols shown in the action column
_DOWN = "\u2193"  # ↓
_UP   = "\u2191"  # ↑


def _format_kb_hotkey(keys_held: set, last_key) -> str:
    """Build a pynput GlobalHotKeys-compatible hotkey string from a key combo."""
    mod_map = {
        pynput_keyboard.Key.ctrl_l:  "<ctrl>",
        pynput_keyboard.Key.ctrl_r:  "<ctrl>",
        pynput_keyboard.Key.ctrl:    "<ctrl>",
        pynput_keyboard.Key.shift_l: "<shift>",
        pynput_keyboard.Key.shift_r: "<shift>",
        pynput_keyboard.Key.shift:   "<shift>",
        pynput_keyboard.Key.alt_l:   "<alt>",
        pynput_keyboard.Key.alt_r:   "<alt>",
        pynput_keyboard.Key.alt:     "<alt>",
        pynput_keyboard.Key.alt_gr:  "<alt_gr>",
        pynput_keyboard.Key.cmd:     "<cmd>",
        pynput_keyboard.Key.cmd_l:   "<cmd>",
        pynput_keyboard.Key.cmd_r:   "<cmd>",
    }
    parts: list[str] = []
    seen_mods: set[str] = set()
    for k in keys_held:
        mod = mod_map.get(k)
        if mod and mod not in seen_mods:
            parts.append(mod)
            seen_mods.add(mod)

    if isinstance(last_key, pynput_keyboard.Key):
        if last_key in mod_map:
            return ""  # modifier-only, not a valid hotkey
        parts.append(f"<{last_key.name}>")
    elif isinstance(last_key, pynput_keyboard.KeyCode) and last_key.char:
        parts.append(last_key.char)
    else:
        return ""

    return "+".join(parts)


class HotkeyCaptureDialog:
    """Captures either a keyboard combo or a mouse button as a hotkey."""

    def __init__(self, parent: tk.Tk | tk.Toplevel):
        self._parent = parent

    def capture(self) -> str:
        dlg = tk.Toplevel(self._parent)
        dlg.title("Capture Hotkey")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self._parent)

        ttk.Label(
            dlg,
            text="Press a key combo  —or—  click a mouse button\n(side buttons X1/X2 supported)",
            padding=16,
            justify=tk.CENTER,
        ).pack()
        result_var = tk.StringVar(value="Waiting...")
        ttk.Label(dlg, textvariable=result_var, font=("Consolas", 12), padding=(20, 0)).pack()
        ttk.Button(dlg, text="Cancel", command=dlg.destroy).pack(pady=10)

        dlg.update_idletasks()
        px = self._parent.winfo_rootx() + self._parent.winfo_width() // 2
        py = self._parent.winfo_rooty() + self._parent.winfo_height() // 2
        dlg.geometry(f"+{px - 150}+{py - 70}")

        result_holder: list[str] = []
        done = threading.Event()

        def finish(value: str) -> None:
            if done.is_set():
                return
            done.set()
            result_holder.append(value)
            result_var.set(value)
            dlg.after(300, dlg.destroy)

        # Keyboard capture
        keys_held: set = set()

        def on_kb_press(key):
            keys_held.add(key)

        def on_kb_release(key):
            combo = _format_kb_hotkey(keys_held, key)
            if combo:
                finish(combo)
            keys_held.discard(key)

        # Mouse capture — fire on button press (not release), so it feels responsive
        def on_mouse_click(x, y, button, pressed):
            if pressed:
                finish(f"mouse:{button.name}")

        kb_listener = pynput_keyboard.Listener(on_press=on_kb_press, on_release=on_kb_release)
        ms_listener = pynput_mouse.Listener(on_click=on_mouse_click)
        kb_listener.start()
        ms_listener.start()

        dlg.wait_window()

        kb_listener.stop()
        ms_listener.stop()

        return result_holder[0] if result_holder else ""


class EditorDialog:
    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        macro: Macro | None,
        all_macros: list[Macro],
        hotkey_manager: HotkeyManager,
        on_saved: Callable[[Macro], None],
    ):
        self._parent = parent
        self._macro = macro
        self._all_macros = all_macros
        self._hotkey_manager = hotkey_manager
        self._on_saved = on_saved
        self._recorder = KeyRecorder()
        self._recording = False
        self._cell_editor: tk.Entry | None = None

    def show(self) -> None:
        self._dlg = tk.Toplevel(self._parent)
        self._dlg.title("Edit Macro" if self._macro else "New Macro")
        self._dlg.grab_set()
        self._dlg.transient(self._parent)
        self._dlg.minsize(540, 440)
        self._dlg.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._build_ui()

        if self._macro:
            self._name_var.set(self._macro.name)
            self._hotkey_var.set(self._macro.hotkey)
            self._loop_var.set(self._macro.loop)
            self._populate_table(self._macro.keys)

        self._dlg.update_idletasks()
        px = self._parent.winfo_rootx() + self._parent.winfo_width() // 2
        py = self._parent.winfo_rooty() + self._parent.winfo_height() // 2
        w, h = 560, 480
        self._dlg.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")

        self._dlg.wait_window()

    def _build_ui(self) -> None:
        dlg = self._dlg

        # --- Top fields ---
        top = ttk.Frame(dlg, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._name_var = tk.StringVar()
        ttk.Entry(top, textvariable=self._name_var, width=30).grid(row=0, column=1, sticky=tk.EW, padx=4)

        ttk.Label(top, text="Hotkey:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._hotkey_var = tk.StringVar()
        hf = ttk.Frame(top)
        hf.grid(row=1, column=1, sticky=tk.EW, padx=4)
        ttk.Entry(hf, textvariable=self._hotkey_var, width=22).pack(side=tk.LEFT)
        ttk.Button(hf, text="Capture...", command=self._capture_hotkey).pack(side=tk.LEFT, padx=4)

        self._loop_var = tk.BooleanVar()
        ttk.Checkbutton(top, text="Loop (toggle on/off with hotkey)", variable=self._loop_var).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=2
        )
        top.columnconfigure(1, weight=1)

        # --- Sequence table ---
        seq_frame = ttk.LabelFrame(dlg, text="Action Sequence", padding=6)
        seq_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ("idx", "action", "delay")
        self._tree = ttk.Treeview(seq_frame, columns=cols, show="headings", height=10)
        self._tree.heading("idx",    text="#")
        self._tree.heading("action", text="Action")
        self._tree.heading("delay",  text="Delay After (s)")
        self._tree.column("idx",    width=30,  anchor=tk.CENTER)
        self._tree.column("action", width=240)
        self._tree.column("delay",  width=110, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(seq_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.bind("<Double-1>", self._on_double_click)

        # --- Row controls ---
        row_ctrl = ttk.Frame(dlg, padding=(8, 0))
        row_ctrl.pack(fill=tk.X)
        ttk.Button(row_ctrl, text="Delete Row", command=self._delete_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(row_ctrl, text="↑", width=3, command=self._move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(row_ctrl, text="↓", width=3, command=self._move_down).pack(side=tk.LEFT, padx=2)

        # --- Record controls ---
        rec_frame = ttk.Frame(dlg, padding=(8, 4))
        rec_frame.pack(fill=tk.X)
        self._rec_btn  = ttk.Button(rec_frame, text="\u23fa  Record", command=self._start_recording)
        self._stop_btn = ttk.Button(rec_frame, text="\u23f9  Stop",   command=self._stop_recording, state=tk.DISABLED)
        self._rec_btn.pack(side=tk.LEFT, padx=2)
        self._stop_btn.pack(side=tk.LEFT, padx=2)
        self._rec_status = tk.StringVar(value="")
        ttk.Label(rec_frame, textvariable=self._rec_status, foreground="red").pack(side=tk.LEFT, padx=8)

        # --- Bottom buttons ---
        btn_frame = ttk.Frame(dlg, padding=8)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="Save",   command=self._on_save).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)

    # --- Table helpers ---

    @staticmethod
    def _action_label(mk: MacroKey) -> str:
        arrow = _DOWN if mk.action == "press" else _UP
        if mk.type == "click":
            return f"{arrow} {mk.button}-click ({mk.x}, {mk.y})"
        return f"{arrow} {mk.key}"

    def _populate_table(self, keys: list[MacroKey]) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, mk in enumerate(keys, 1):
            self._tree.insert(
                "", tk.END,
                values=(i, self._action_label(mk), f"{mk.delay_after:.4f}"),
                tags=(mk.type, mk.action),
            )

    def _renumber(self) -> None:
        for i, item in enumerate(self._tree.get_children(), 1):
            vals = list(self._tree.item(item, "values"))
            vals[0] = i
            self._tree.item(item, values=vals)

    def _get_keys(self) -> list[MacroKey]:
        keys = []
        for item in self._tree.get_children():
            vals = self._tree.item(item, "values")
            tags = self._tree.item(item, "tags")
            try:
                label   = str(vals[1])
                delay   = float(vals[2])
                kind    = tags[0] if len(tags) > 0 else "key"    # "key" | "click"
                action  = tags[1] if len(tags) > 1 else "press"  # "press" | "release"
                # Strip leading arrow + space: "↓ a" -> "a", "↑ left-click (x, y)" -> "left-click (x, y)"
                raw = label[2:]
                if kind == "click":
                    # "left-click (100, 200)" -> button="left", x=100, y=200
                    btn_part, coord_part = raw.split("-click ")
                    btn = btn_part.strip()
                    coord_part = coord_part.strip("()")
                    cx, cy = (int(v.strip()) for v in coord_part.split(","))
                    keys.append(MacroKey(type="click", action=action, button=btn, x=cx, y=cy, delay_after=delay))
                else:
                    keys.append(MacroKey(type="key", action=action, key=raw, delay_after=delay))
            except (ValueError, IndexError):
                pass
        return keys

    def _delete_row(self) -> None:
        sel = self._tree.selection()
        if sel:
            self._tree.delete(sel[0])
            self._renumber()

    def _move_up(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        idx = self._tree.index(item)
        if idx > 0:
            self._tree.move(item, "", idx - 1)
            self._renumber()

    def _move_down(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        idx = self._tree.index(item)
        if idx < len(self._tree.get_children()) - 1:
            self._tree.move(item, "", idx + 1)
            self._renumber()

    # --- Inline cell edit (delay_after column only) ---

    def _on_double_click(self, event) -> None:
        region = self._tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self._tree.identify_column(event.x)
        col_idx = int(col[1:]) - 1
        # Only the delay column (index 2) is editable; index and action are not
        if col_idx != 2:
            return
        item = self._tree.identify_row(event.y)
        if not item:
            return
        self._start_cell_edit(item, col_idx)

    def _start_cell_edit(self, item: str, col_idx: int) -> None:
        if self._cell_editor:
            self._cell_editor.destroy()
            self._cell_editor = None

        col_id = f"#{col_idx + 1}"
        bbox = self._tree.bbox(item, col_id)
        if not bbox:
            return
        x, y, w, h = bbox

        current_val = self._tree.item(item, "values")[col_idx]
        var = tk.StringVar(value=str(current_val))
        entry = ttk.Entry(self._tree, textvariable=var)
        entry.place(x=x, y=y, width=w, height=h)
        entry.select_range(0, tk.END)
        entry.focus_set()
        self._cell_editor = entry

        def commit(_event=None):
            vals = list(self._tree.item(item, "values"))
            try:
                vals[col_idx] = f"{float(var.get()):.4f}"
            except ValueError:
                pass
            self._tree.item(item, values=vals)
            entry.destroy()
            self._cell_editor = None

        def cancel(_event=None):
            entry.destroy()
            self._cell_editor = None

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", commit)

    # --- Hotkey capture ---

    def _capture_hotkey(self) -> None:
        result = HotkeyCaptureDialog(self._dlg).capture()
        if result:
            self._hotkey_var.set(result)

    # --- Recording ---

    def _start_recording(self) -> None:
        self._recording = True
        self._rec_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self._rec_status.set("Recording... press keys/click mouse, then Stop")
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._hotkey_manager.pause()
        self._recorder.start(on_update=self._on_record_update)

    def _stop_recording(self) -> None:
        keys = self._recorder.stop()
        self._hotkey_manager.resume()
        self._recording = False
        self._rec_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        self._rec_status.set(f"Recorded {len(keys)} action(s)")
        self._populate_table(keys)

    def _on_record_update(self, keys: list[MacroKey]) -> None:
        self._dlg.after(0, lambda: self._populate_table(keys))

    # --- Save / Cancel ---

    def _on_save(self) -> None:
        name   = self._name_var.get().strip()
        hotkey = self._hotkey_var.get().strip()
        loop   = self._loop_var.get()
        keys   = self._get_keys()

        if not name:
            messagebox.showerror("Validation", "Macro name cannot be empty.", parent=self._dlg)
            return
        if not hotkey:
            messagebox.showerror("Validation", "Hotkey cannot be empty.", parent=self._dlg)
            return
        if not keys:
            messagebox.showerror("Validation", "Sequence cannot be empty.", parent=self._dlg)
            return

        current_id = self._macro.id if self._macro else None
        for m in self._all_macros:
            if m.hotkey == hotkey and m.id != current_id:
                messagebox.showerror(
                    "Hotkey conflict",
                    f"Hotkey '{hotkey}' is already used by macro '{m.name}'.",
                    parent=self._dlg,
                )
                return

        macro = Macro(
            id=self._macro.id if self._macro else __import__("uuid").uuid4().hex,
            name=name, hotkey=hotkey, loop=loop, keys=keys,
        )
        self._dlg.destroy()
        self._on_saved(macro)

    def _on_cancel(self) -> None:
        if self._recording:
            self._recorder.stop()
            self._hotkey_manager.resume()
        self._dlg.destroy()
