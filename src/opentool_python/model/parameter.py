from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import Schema


@dataclass
class Parameter:
    name: str
    schema: Schema
    required: bool
    description: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Parameter":
        return cls(
            name=str(data["name"]),
            schema=Schema.from_json(data["schema"]),
            required=bool(data["required"]),
            description=data.get("description"),
        )

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "schema": self.schema.to_json(),
            "required": self.required,
        }
        if self.description is not None:
            payload["description"] = self.description
        return payload
