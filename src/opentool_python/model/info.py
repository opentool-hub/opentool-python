from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Info:
    title: str
    version: str
    description: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Info":
        return cls(
            title=str(data["title"]),
            version=str(data["version"]),
            description=data.get("description"),
        )

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": self.title, "version": self.version}
        if self.description is not None:
            payload["description"] = self.description
        return payload
