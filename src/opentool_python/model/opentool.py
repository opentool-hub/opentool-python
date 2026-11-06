from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .function_model import FunctionModel
from .info import Info
from .schema import Schema, SchemaReferenceResolver, SchemaResolver
from .server import ServerConfig


@dataclass
class OpenTool:
    opentool: str
    info: Info
    functions: list[FunctionModel]
    server: ServerConfig | None = None
    schemas: dict[str, Schema] | None = None

    @classmethod
    def from_json(
        cls,
        data: dict[str, Any],
        *,
        schema_reference_resolver: SchemaReferenceResolver | None = None,
    ) -> "OpenTool":
        raw_schemas = data.get("schemas")
        if raw_schemas is not None and not isinstance(raw_schemas, dict):
            raise ValueError("schemas: expected an object")
        schema_resolver = SchemaResolver(raw_schemas, schema_reference_resolver)
        schemas = schema_resolver.resolve_all() if raw_schemas is not None else None
        functions = data["functions"]
        if not isinstance(functions, list) or any(not isinstance(item, dict) for item in functions):
            raise ValueError("functions: expected an array of objects")

        return cls(
            opentool=str(data["opentool"]),
            info=Info.from_json(data["info"]),
            server=ServerConfig.from_json(data["server"]) if isinstance(data.get("server"), dict) else None,
            functions=[
                FunctionModel.from_json(item, schema_resolver=schema_resolver)
                for item in functions
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
