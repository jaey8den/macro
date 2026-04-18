import json
import os
import threading
from pathlib import Path

from models import Macro

MACROS_FILE = Path("macros.json")


class MacroStore:
    def __init__(self, path: Path = MACROS_FILE):
        self._path = path
        self._macros: dict[str, Macro] = {}
        self._lock = threading.Lock()

    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            with self._lock:
                self._macros = {
                    m["id"]: Macro.from_dict(m)
                    for m in data.get("macros", [])
                }
        except (json.JSONDecodeError, KeyError, ValueError):
            self._macros = {}

    def save(self) -> None:
        with self._lock:
            data = {"version": 1, "macros": [m.to_dict() for m in self._macros.values()]}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    def all(self) -> list[Macro]:
        with self._lock:
            return list(self._macros.values())

    def get(self, macro_id: str) -> Macro | None:
        with self._lock:
            return self._macros.get(macro_id)

    def upsert(self, macro: Macro) -> None:
        with self._lock:
            self._macros[macro.id] = macro
        self.save()

    def delete(self, macro_id: str) -> None:
        with self._lock:
            self._macros.pop(macro_id, None)
        self.save()
