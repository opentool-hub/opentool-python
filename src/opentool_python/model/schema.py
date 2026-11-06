from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, unquote

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012


SchemaValue = dict[str, Any] | bool
SchemaReferenceResolver = Callable[[str], SchemaValue | None]
_LOCAL_PREFIX = "https://opentool.invalid/schemas/"


class SchemaType:
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


@dataclass
class SchemaValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.valid


class SchemaResolver:
    def __init__(
        self,
        definitions: dict[str, SchemaValue] | None = None,
        reference_resolver: SchemaReferenceResolver | None = None,
    ) -> None:
        self._definitions = deepcopy(definitions) if definitions is not None else {}

        def retrieve(uri: str) -> Resource:
            value = reference_resolver(uri) if reference_resolver is not None else None
            if value is None:
                raise NoSuchResource(ref=uri)
            return self._resource(value)

        self.registry = Registry(retrieve=retrieve).with_resources(
            (_LOCAL_PREFIX + quote(name, safe=""), self._resource(value))
            for name, value in self._definitions.items()
        )

    def resolve_all(self) -> dict[str, Schema]:
        return {name: Schema.from_json(value, resolver=self) for name, value in self._definitions.items()}

    def _resource(self, value: SchemaValue) -> Resource:
        if not isinstance(value, (dict, bool)):
            raise ValueError("Expected a JSON Schema object or boolean")
        return Resource.from_contents(self.normalize(value), default_specification=DRAFT202012)

    def keyword_view(self, value: dict[str, Any]) -> dict[str, Any]:
        chain = [value]
        seen = set()
        while isinstance(ref := value.get("$ref"), str) and ref.startswith("#/schemas/"):
            token = ref[len("#/schemas/"):]
            if "/" in token or ref in seen:
                break
            seen.add(ref)
            name = unquote(token).replace("~1", "/").replace("~0", "~")
            target = self._definitions.get(name)
            if not isinstance(target, dict):
                break
            chain.append(target)
            value = target
        view: dict[str, Any] = {}
        for node in reversed(chain):
            view.update(node)
        return view

    def normalize(self, value: SchemaValue) -> SchemaValue:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        # Only visit schema positions, leaving literal values in enum, const and annotations intact.
        for key in ("$ref", "$dynamicRef", "$recursiveRef"):
            ref = value.get(key)
            if isinstance(ref, str) and ref.startswith("#/schemas/"):
                token, separator, rest = ref[len("#/schemas/"):].partition("/")
                name = unquote(token).replace("~1", "/").replace("~0", "~")
                if name not in self._definitions:
                    raise ValueError(f"Unknown OpenTool schema reference: {ref}")
                normalized[key] = _LOCAL_PREFIX + quote(name, safe="") + (f"#/{rest}" if separator else "")
        for key in ("$defs", "definitions", "properties", "patternProperties", "dependentSchemas", "dependencies"):
            if isinstance(value.get(key), dict):
                normalized[key] = {name: self.normalize(node) for name, node in value[key].items()}
        for key in ("allOf", "anyOf", "oneOf", "prefixItems", "items"):
            if isinstance(value.get(key), list):
                normalized[key] = [self.normalize(node) for node in value[key]]
        for key in (
            "additionalProperties", "unevaluatedProperties", "items", "additionalItems",
            "unevaluatedItems", "contains", "propertyNames", "not", "if", "then", "else", "contentSchema",
        ):
            if isinstance(value.get(key), (dict, bool)):
                normalized[key] = self.normalize(value[key])
        return normalized


class SchemasSingleton:
    """Legacy registry for standalone Schema.from_json callers."""

    _resolver = SchemaResolver()
    _schemas: dict[str, Schema] = {}

    @classmethod
    def init_instance(cls, schemas_json: dict[str, SchemaValue]) -> None:
        resolver = SchemaResolver(schemas_json)
        schemas = resolver.resolve_all()
        cls._resolver = resolver
        cls._schemas = schemas

    @classmethod
    def get_instance(cls) -> dict[str, Schema]:
        return dict(cls._schemas)


class Schema:
    def __init__(
        self,
        type: str | list[str],
        description: str | None = None,
        properties: dict[str, Schema] | None = None,
        items: Schema | None = None,
        enum_: list[Any] | None = None,
        required: list[str] | None = None,
        **keywords: Any,
    ) -> None:
        value = {"type": type, **keywords}
        if description is not None:
            value["description"] = description
        if properties is not None:
            value["properties"] = {key: schema.to_json() for key, schema in properties.items()}
        if items is not None:
            value["items"] = items.to_json()
        if enum_ is not None:
            value["enum"] = enum_
        if required is not None:
            value["required"] = required
        self._initialize(value, SchemaResolver())

    @classmethod
    def from_json(cls, data: SchemaValue, *, resolver: SchemaResolver | None = None) -> Schema:
        schema = cls.__new__(cls)
        schema._initialize(data, resolver if resolver is not None else SchemasSingleton._resolver)
        return schema

    def _initialize(self, data: SchemaValue, resolver: SchemaResolver) -> None:
        if not isinstance(data, (dict, bool)):
            raise ValueError("Expected a JSON Schema object or boolean")
        self._json = deepcopy(data)
        self._resolver = resolver
        normalized = resolver.normalize(self._json)
        validator_class = validator_for(normalized, default=Draft202012Validator)
        validator_class.check_schema(normalized)
        self._validator = validator_class(normalized, registry=resolver.registry)
        self._format_validator = self._validator.evolve(format_checker=validator_class.FORMAT_CHECKER or FormatChecker())

    @property
    def is_boolean_schema(self) -> bool:
        return isinstance(self._json, bool)

    @property
    def raw_schema(self) -> SchemaValue:
        return self.to_json()

    def __getitem__(self, keyword: str) -> Any:
        if not isinstance(self._json, dict):
            return None
        if keyword in self._json:
            return deepcopy(self._json[keyword])
        return deepcopy(self._resolver.keyword_view(self._json).get(keyword))

    @property
    def has_type(self) -> bool:
        return self["type"] is not None

    @property
    def type(self) -> str:
        value = self["type"]
        if isinstance(value, list):
            return value[0] if value else ""
        return value if isinstance(value, str) else ""

    @property
    def type_union(self) -> list[str] | None:
        value = self["type"]
        return value if isinstance(value, list) else None

    @property
    def description(self) -> str | None:
        return self["description"]

    @property
    def enum_(self) -> list[Any] | None:
        return self["enum"]

    @property
    def required(self) -> list[str] | None:
        return self["required"]

    @property
    def properties(self) -> dict[str, Schema] | None:
        properties = self["properties"]
        if properties is None:
            return None
        return {key: self._child(node) for key, node in properties.items()}

    @property
    def items(self) -> Schema | list[Schema] | None:
        items = self["items"]
        if isinstance(items, list):
            return [self._child(node) for node in items]
        return self._child(items) if items is not None else None

    def _child(self, node: SchemaValue) -> Schema:
        child = self.__class__.__new__(self.__class__)
        child._json = node
        child._resolver = self._resolver
        normalized = self._resolver.normalize(node)
        child._validator = self._validator.evolve(schema=normalized)
        child._format_validator = self._format_validator.evolve(schema=normalized)
        return child

    def to_json(self) -> SchemaValue:
        return deepcopy(self._json)

    def validate(self, instance: Any, *, validate_formats: bool = False) -> SchemaValidationResult:
        validator = self._format_validator if validate_formats else self._validator
        errors = [f"{error.json_path}: {error.message}" for error in validator.iter_errors(instance)]
        return SchemaValidationResult(valid=not errors, errors=errors)

    def is_valid(self, instance: Any, *, validate_formats: bool = False) -> bool:
        validator = self._format_validator if validate_formats else self._validator
        return validator.is_valid(instance)
