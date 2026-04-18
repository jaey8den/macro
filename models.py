from dataclasses import dataclass, field
import uuid


@dataclass
class MacroKey:
    type: str = "key"       # "key" | "click"
    action: str = "press"   # "press" | "release"
    key: str = ""           # keyboard key string
    button: str = ""        # mouse button: "left", "right", "middle", "x1", "x2"
    x: int = 0              # screen x for click actions
    y: int = 0              # screen y for click actions
    delay_after: float = 0.02  # seconds to wait after this action

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "action": self.action,
            "key": self.key,
            "button": self.button,
            "x": self.x,
            "y": self.y,
            "delay_after": self.delay_after,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MacroKey":
        return cls(
            type=d.get("type", "key"),
            action=d.get("action", "press"),
            key=d.get("key", ""),
            button=d.get("button", ""),
            x=int(d.get("x", 0)),
            y=int(d.get("y", 0)),
            delay_after=float(d.get("delay_after", 0.02)),
        )


@dataclass
class Macro:
    name: str
    hotkey: str = ""
    loop: bool = False
    keys: list[MacroKey] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hotkey": self.hotkey,
            "loop": self.loop,
            "keys": [k.to_dict() for k in self.keys],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Macro":
        return cls(
            id=d["id"],
            name=d["name"],
            hotkey=d.get("hotkey", ""),
            loop=bool(d.get("loop", False)),
            keys=[MacroKey.from_dict(k) for k in d.get("keys", [])],
        )
