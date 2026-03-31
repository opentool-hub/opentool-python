from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .parameter import Parameter
from .return_model import Return


@dataclass
class FunctionModel:
    name: str
    description: str
    parameters: list[Parameter]
    return_: Return | None = None
    stream: dict[str, Return] | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "FunctionModel":
        raw_stream = data.get("stream")
        stream: dict[str, Return] | None = None
        if isinstance(raw_stream, dict):
            stream = {
                name: Return.from_json(value)
                for name, value in raw_stream.items()
                if isinstance(value, dict)
            }

        return cls(
            name=str(data["name"]),
            description=str(data["description"]),
            parameters=[
                Parameter.from_json(item)
                for item in data.get("parameters", [])
                if isinstance(item, dict)
            ],
            return_=Return.from_json(data["return"]) if isinstance(data.get("return"), dict) else None,
            stream=stream,
        )

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "parameters": [parameter.to_json() for parameter in self.parameters],
        }
        if self.return_ is not None:
            payload["return"] = self.return_.to_json()
        if self.stream is not None:
            payload["stream"] = {
                event_name: return_model.to_json()
                for event_name, return_model in self.stream.items()
            }
        return payload
