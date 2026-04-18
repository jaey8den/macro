import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from models import Macro


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        macros_getter: Callable[[], list[Macro]],
        on_new: Callable,
        on_edit: Callable[[Macro], None],
        on_delete: Callable[[Macro], None],
    ):
        self._root = root
        self._macros_getter = macros_getter
        self._on_new = on_new
        self._on_edit = on_edit
        self._on_delete = on_delete

        self._root.title("Macro App")
        self._root.minsize(500, 300)
        self._root.protocol("WM_DELETE_WINDOW", self.hide)
        self._root.bind("<Unmap>", self._on_unmap)

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self._root, padding=4)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="New", command=self._new).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit", command=self._edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=2)

        frame = ttk.Frame(self._root, padding=4)
        frame.pack(fill=tk.BOTH, expand=True)

        cols = ("name", "hotkey", "loop", "keys")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        self._tree.heading("name", text="Name")
        self._tree.heading("hotkey", text="Hotkey")
        self._tree.heading("loop", text="Loop")
        self._tree.heading("keys", text="Keys")
        self._tree.column("name", width=160)
        self._tree.column("hotkey", width=160)
        self._tree.column("loop", width=50, anchor=tk.CENTER)
        self._tree.column("keys", width=50, anchor=tk.CENTER)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.bind("<Double-1>", lambda _e: self._edit())

        status = ttk.Frame(self._root, padding=(4, 2))
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(status, textvariable=self._status_var, anchor=tk.W).pack(fill=tk.X)

    def show(self) -> None:
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def hide(self) -> None:
        self._root.withdraw()

    def _on_unmap(self, event) -> None:
        if event.widget is self._root:
            self._root.after(10, self._check_minimized)

    def _check_minimized(self) -> None:
        if self._root.state() == "iconic":
            self._root.withdraw()

    def refresh_list(self) -> None:
        self._root.after(0, self._do_refresh)

    def _do_refresh(self) -> None:
        selected = self._selected_macro_id()
        for item in self._tree.get_children():
            self._tree.delete(item)
        for macro in self._macros_getter():
            loop_str = "yes" if macro.loop else "no"
            iid = self._tree.insert(
                "", tk.END,
                iid=macro.id,
                values=(macro.name, macro.hotkey, loop_str, len(macro.keys)),
            )
        if selected:
            try:
                self._tree.selection_set(selected)
            except tk.TclError:
                pass

    def _selected_macro(self) -> Macro | None:
        sel = self._tree.selection()
        if not sel:
            return None
        macro_id = sel[0]
        for macro in self._macros_getter():
            if macro.id == macro_id:
                return macro
        return None

    def _selected_macro_id(self) -> str | None:
        sel = self._tree.selection()
        return sel[0] if sel else None

    def set_status(self, msg: str) -> None:
        self._root.after(0, lambda: self._status_var.set(msg))

    def _new(self) -> None:
        self._on_new()

    def _edit(self) -> None:
        macro = self._selected_macro()
        if not macro:
            messagebox.showinfo("Select a macro", "Please select a macro to edit.", parent=self._root)
            return
        self._on_edit(macro)

    def _delete(self) -> None:
        macro = self._selected_macro()
        if not macro:
            messagebox.showinfo("Select a macro", "Please select a macro to delete.", parent=self._root)
            return
        if messagebox.askyesno("Delete", f"Delete macro '{macro.name}'?", parent=self._root):
            self._on_delete(macro)
