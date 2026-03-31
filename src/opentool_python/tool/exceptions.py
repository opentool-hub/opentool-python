from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class FunctionNotSupportedException(Exception):
    function_name: str
    code: int = 405

    @property
    def message(self) -> str:
        return f"Function Not Supported: {self.function_name}"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}

    def __str__(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)


@dataclass
class InvalidArgumentsException(Exception):
    arguments: dict[str, Any] | None
    code: int = 400

    @property
    def message(self) -> str:
        return f"Invalid Arguments: {json.dumps(self.arguments, ensure_ascii=False)}"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}

    def __str__(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)


@dataclass
class ToolBreakException(Exception):
    message: str | None
    code: int = 500

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}

    def __str__(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)


@dataclass
class JsonParserException(Exception):
    code: int = 404
    message: str = "Json Parser NOT implement"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}

    def __str__(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)
