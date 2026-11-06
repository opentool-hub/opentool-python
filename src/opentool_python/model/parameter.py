from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import Schema, SchemaResolver


@dataclass
class Parameter:
    name: str
    schema: Schema
    required: bool = False
    description: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any], *, schema_resolver: SchemaResolver | None = None) -> "Parameter":
        required = data.get("required")
        if required is not None and not isinstance(required, bool):
            raise ValueError("required: expected a boolean")
        return cls(
            name=str(data["name"]),
            schema=Schema.from_json(data["schema"], resolver=schema_resolver),
            required=required if required is not None else False,
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
