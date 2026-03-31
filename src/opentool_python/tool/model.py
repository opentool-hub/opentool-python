from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class EventType:
    START = "start"
    DATA = "data"
    ERROR = "error"
    DONE = "done"


@dataclass
class Event:
    name: str
    data: dict[str, Any]

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Event":
        return cls(name=str(payload["name"]), data=payload.get("data") or {})

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "data": self.data}
