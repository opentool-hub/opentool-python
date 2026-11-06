from __future__ import annotations

import json
from pathlib import Path

from .model.opentool import OpenTool
from .model.schema import SchemaReferenceResolver


class OpenToolJsonLoader:
    def __init__(self, *, schema_reference_resolver: SchemaReferenceResolver | None = None) -> None:
        self.schema_reference_resolver = schema_reference_resolver
        self.schemas_json: dict[str, object] | None = None

    def load(self, json_string: str) -> OpenTool:
        opentool_map = json.loads(json_string)
        self.schemas_json = opentool_map.get("schemas")
        return OpenTool.from_json(
            opentool_map, schema_reference_resolver=self.schema_reference_resolver
        )

    def load_from_file(self, json_path: str) -> OpenTool:
        return self.load(Path(json_path).read_text(encoding="utf-8"))
