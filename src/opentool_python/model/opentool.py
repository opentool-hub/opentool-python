from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .function_model import FunctionModel
from .info import Info
from .schema import Schema
from .server import ServerConfig


@dataclass
class OpenTool:
    opentool: str
    info: Info
    functions: list[FunctionModel]
    server: ServerConfig | None = None
    schemas: dict[str, Schema] | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "OpenTool":
        raw_schemas = data.get("schemas")
        schemas: dict[str, Schema] | None = None
        if isinstance(raw_schemas, dict):
            schemas = {
                name: Schema.from_json(schema)
                for name, schema in raw_schemas.items()
                if isinstance(schema, dict)
            }

        return cls(
            opentool=str(data["opentool"]),
            info=Info.from_json(data["info"]),
            server=ServerConfig.from_json(data["server"]) if isinstance(data.get("server"), dict) else None,
            functions=[
                FunctionModel.from_json(item)
                for item in data.get("functions", [])
                if isinstance(item, dict)
            ],
            schemas=schemas,
        )

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "opentool": self.opentool,
            "info": self.info.to_json(),
            "functions": [function.to_json() for function in self.functions],
        }
        if self.server is not None:
            payload["server"] = self.server.to_json()
        if self.schemas is not None:
            payload["schemas"] = {
                name: schema.to_json() for name, schema in self.schemas.items()
            }
        return payload
