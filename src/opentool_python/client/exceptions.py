from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ResponseNullException(Exception):
    code: int
    message: str = "Response is null"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


@dataclass
class ErrorNullException(Exception):
    code: int
    message: str = "Error is null"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


@dataclass
class OpenToolServerUnauthorizedException(Exception):
    code: int = 401
    message: str = "Please check API Key is VALID or NOT"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


@dataclass
class OpenToolServerNoAccessException(Exception):
    code: int = 404
    message: str = "Please check OpenTool Server is RUNNING or NOT"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


@dataclass
class OpenToolServerCallException(Exception):
    message: str

    def to_json(self) -> dict[str, Any]:
        return {"message": self.message}
