from __future__ import annotations

import json
from pathlib import Path

from .model.opentool import OpenTool
from .model.schema import SchemasSingleton


class OpenToolJsonLoader:
    def __init__(self) -> None:
        self.schemas_json: dict[str, object] | None = None

    def load(self, json_string: str) -> OpenTool:
        opentool_map = json.loads(json_string)
        self.schemas_json = opentool_map.get("schemas")
        if isinstance(self.schemas_json, dict):
            SchemasSingleton.init_instance(self.schemas_json)
        return OpenTool.from_json(opentool_map)

    def load_from_file(self, json_path: str) -> OpenTool:
        return self.load(Path(json_path).read_text(encoding="utf-8"))
