from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class ServerException(Exception):
    code: int
    message: str

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


@dataclass
class JsonParseException(ServerException):
    message: str = "Parse error"
    code: int = -32700

    def __str__(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)


@dataclass
class InvalidJsonPayloadException(ServerException):
    message: str = "Invalid JSON payload: expected object"
    code: int = -32700

    def __str__(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)
