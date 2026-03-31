from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FunctionCall:
    id: str
    name: str
    arguments: dict[str, Any]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "FunctionCall":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            arguments=data.get("arguments") or {},
        )

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}


@dataclass
class ToolReturn:
    id: str
    result: dict[str, Any]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ToolReturn":
        return cls(id=str(data["id"]), result=data.get("result") or {})

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "result": self.result}
