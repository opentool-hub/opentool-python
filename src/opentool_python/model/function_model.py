from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .parameter import Parameter
from .return_model import Return
from .schema import SchemaResolver


@dataclass
class FunctionModel:
    name: str
    description: str
    parameters: list[Parameter]
    return_: Return | None = None
    stream: dict[str, Return] | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any], *, schema_resolver: SchemaResolver | None = None) -> "FunctionModel":
        parameters = data["parameters"]
        if not isinstance(parameters, list) or any(not isinstance(item, dict) for item in parameters):
            raise ValueError("parameters: expected an array of objects")

        raw_return = data.get("return")
        if raw_return is not None and not isinstance(raw_return, dict):
            raise ValueError("return: expected an object")

        raw_stream = data.get("stream")
        stream: dict[str, Return] | None = None
        if raw_stream is not None:
            if not isinstance(raw_stream, dict) or any(not isinstance(item, dict) for item in raw_stream.values()):
                raise ValueError("stream: expected a map of return objects")
            stream = {
                name: Return.from_json(value, schema_resolver=schema_resolver)
                for name, value in raw_stream.items()
            }

        return cls(
            name=str(data["name"]),
            description=str(data["description"]),
            parameters=[
                Parameter.from_json(item, schema_resolver=schema_resolver)
                for item in parameters
            ],
            return_=(
                Return.from_json(raw_return, schema_resolver=schema_resolver)
                if raw_return is not None else None
            ),
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
