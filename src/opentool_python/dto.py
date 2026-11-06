from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

JSONRPC_VERSION = "2.0"
LOAD_METADATA_NOT_FOUND_CODE = "TOOL_NOT_FOUND"
LOAD_METADATA_NOT_FOUND_MESSAGE = "Tool metadata not found"
DEFAULT_PREFIX = "/opentool"
DEFAULT_TOOL_TAG = "N/A"
DEFAULT_TOOL_HOST = "0.0.0.0"
DEFAULT_TOOL_PORT = 17001
CLI_ARGUMENT_TAG = "opentoolServerTag"
CLI_ARGUMENT_HOST = "opentoolServerHost"
CLI_ARGUMENT_PORT = "opentoolServerPort"
CLI_ARGUMENT_APIKEYS = "opentoolServerApiKeys"


class HostType:
    ANY = "0.0.0.0"
    LOCALHOST = "127.0.0.1"


@dataclass
class Version:
    version: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Version":
        return cls(version=str(data["version"]))

    def to_json(self) -> dict[str, Any]:
        return {"version": self.version}


@dataclass
class JsonRPCHttpRequestBody:
    method: str
    params: dict[str, Any] | None
    id: str
    jsonrpc: str = JSONRPC_VERSION

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "JsonRPCHttpRequestBody":
        method, request_id = data["method"], data["id"]
        params = data.get("params")
        version = data.get("jsonrpc", JSONRPC_VERSION)
        if not isinstance(method, str) or not isinstance(request_id, str):
            raise ValueError("method and id must be strings")
        if params is not None and not isinstance(params, dict):
            raise ValueError("params must be an object or null")
        if not isinstance(version, str):
            raise ValueError("jsonrpc must be a string")
        return cls(method=method, params=params, id=request_id, jsonrpc=version)

    def to_json(self) -> dict[str, Any]:
        return {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "id": self.id,
            **({"params": self.params} if self.params is not None else {}),
        }


@dataclass
class JsonRPCHttpResponseBodyError:
    code: int
    message: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "JsonRPCHttpResponseBodyError":
        return cls(code=int(data["code"]), message=str(data["message"]))

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


@dataclass
class JsonRPCHttpResponseBody:
    result: dict[str, Any] = field(default_factory=dict)
    id: str = ""
    error: JsonRPCHttpResponseBodyError | None = None
    jsonrpc: str = JSONRPC_VERSION

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "JsonRPCHttpResponseBody":
        error_data = data.get("error")
        error = (
            JsonRPCHttpResponseBodyError.from_json(error_data)
            if isinstance(error_data, dict)
            else None
        )
        return cls(
            result=data.get("result") or {},
            id=str(data.get("id", "")),
            error=error,
            jsonrpc=str(data.get("jsonrpc", JSONRPC_VERSION)),
        )

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "result": self.result,
            "id": self.id,
        }
        if self.error is not None:
            payload["error"] = self.error.to_json()
        return payload


class StatusType:
    STOPPED = "stopped"


@dataclass
class StatusInfo:
    status: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StatusInfo":
        return cls(status=str(data["status"]))

    def to_json(self) -> dict[str, Any]:
        return {"status": self.status}
