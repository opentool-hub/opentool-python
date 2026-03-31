from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SchemaType:
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"
    ARRAY = "array"
    OBJECT = "object"


class SchemasSingleton:
    _schemas: dict[str, "Schema"] = {}

    @classmethod
    def init_instance(cls, schemas_json: dict[str, Any]) -> None:
        cls._schemas = {}
        for schema_name, schema_map in schemas_json.items():
            if isinstance(schema_map, dict) and "$ref" not in schema_map:
                cls._schemas[schema_name] = Schema.from_json(schema_map)

    @classmethod
    def get_instance(cls) -> dict[str, "Schema"]:
        return cls._schemas


@dataclass
class Schema:
    type: str
    description: str | None = None
    properties: dict[str, "Schema"] | None = None
    items: "Schema" | None = None
    enum_: list[Any] | None = None
    required: list[str] | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Schema":
        ref = data.get("$ref")
        if isinstance(ref, str):
            schema = cls._from_ref(ref)
            schema._validate_enum_consistency()
            return schema

        properties: dict[str, Schema] | None = None
        raw_properties = data.get("properties")
        if isinstance(raw_properties, dict):
            properties = {
                k: cls.from_json(v)
                for k, v in raw_properties.items()
                if isinstance(v, dict)
            }

        items: Schema | None = None
        raw_items = data.get("items")
        if isinstance(raw_items, dict):
            items = cls.from_json(raw_items)

        schema = cls(
            type=str(data["type"]),
            description=data.get("description"),
            properties=properties,
            items=items,
            enum_=data.get("enum"),
            required=data.get("required"),
        )
        schema._validate_enum_consistency()
        return schema

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type}
        if self.description is not None:
            payload["description"] = self.description
        if self.properties is not None:
            payload["properties"] = {
                key: schema.to_json() for key, schema in self.properties.items()
            }
        if self.items is not None:
            payload["items"] = self.items.to_json()
        if self.enum_ is not None:
            payload["enum"] = self.enum_
        if self.required is not None:
            payload["required"] = self.required
        return payload

    @staticmethod
    def _from_ref(ref: str) -> "Schema":
        parts = ref.split("/")
        if len(parts) == 3 and parts[0] == "#" and parts[1] == "schemas":
            ref_name = parts[2]
            schema = SchemasSingleton.get_instance().get(ref_name)
            if schema is None:
                raise ValueError(f"#ref not found: {ref}")
            return schema
        raise ValueError(f"#ref format exception: {ref}")

    def _validate_enum_consistency(self) -> None:
        if not self.enum_:
            return
        for index, value in enumerate(self.enum_):
            if not self._is_value_consistent_with_type(value):
                raise ValueError(
                    f'Enum value at index {index} ("{value}") '
                    f'does not match schema type "{self.type}".'
                )

    def _is_value_consistent_with_type(self, value: Any) -> bool:
        if self.type == "string":
            return isinstance(value, str) or value is None
        if self.type == "integer":
            return (isinstance(value, int) and not isinstance(value, bool)) or value is None
        if self.type == "number":
            return (
                (isinstance(value, (int, float)) and not isinstance(value, bool))
                or value is None
            )
        if self.type == "boolean":
            return isinstance(value, bool) or value is None
        if self.type == "null":
            return value is None
        return True
