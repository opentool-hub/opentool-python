from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ServerConfig:
    url: str
    description: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ServerConfig":
        return cls(url=str(data["url"]), description=data.get("description"))

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": self.url}
        if self.description is not None:
            payload["description"] = self.description
        return payload
