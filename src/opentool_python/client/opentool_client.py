from __future__ import annotations

import json
import socket
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Any
from urllib import error, parse, request

from ..dto import (
    DEFAULT_PREFIX,
    JsonRPCHttpRequestBody,
    JsonRPCHttpResponseBody,
    StatusInfo,
    Version,
)
from ..llm.model import FunctionCall, ToolReturn
from ..model.opentool import OpenTool
from ..tool.model import EventType
from .exceptions import (
    OpenToolServerCallException,
    OpenToolServerNoAccessException,
    OpenToolServerUnauthorizedException,
)


class Client(ABC):
    @abstractmethod
    def version(self) -> Version:
        raise NotImplementedError

    @abstractmethod
    def call(self, function_call: FunctionCall) -> ToolReturn:
        raise NotImplementedError

    @abstractmethod
    def stream_call(
        self,
        function_call: FunctionCall,
        on_stream: Callable[[str, ToolReturn], None],
    ) -> None:
        raise NotImplementedError

    def load(self) -> OpenTool | None:
        return None

    @abstractmethod
    def stop(self) -> StatusInfo | None:
        raise NotImplementedError


class OpenToolClient(Client):
    def __init__(
        self,
        *,
        tool_host: str,
        tool_port: int,
        tool_api_key: str | None = None,
        is_ssl: bool = False,
    ) -> None:
        self.is_ssl = is_ssl
        self.host = tool_host
        self.port = tool_port
        self.prefix = DEFAULT_PREFIX
        self.tool_api_key = tool_api_key
        protocol = "https" if self.is_ssl else "http"
        self.base_url = f"{protocol}://{self.host}:{self.port}{self.prefix}"

    def version(self) -> Version:
        data = self._request_json("GET", "/version")
        return Version.from_json(data)

    def call(self, function_call: FunctionCall) -> ToolReturn:
        result = self._call_json_rpc_http(
            function_call.id,
            function_call.name,
            function_call.arguments,
        )
        return ToolReturn(id=function_call.id, result=result)

    def _call_json_rpc_http(
        self,
        request_id: str,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        body = JsonRPCHttpRequestBody(id=request_id, method=method, params=params)
        data = self._request_json("POST", "/call", body.to_json())
        response_body = JsonRPCHttpResponseBody.from_json(data)
        if response_body.error is not None:
            raise OpenToolServerCallException(response_body.error.message)
        return response_body.result

    def stream_call(
        self,
        function_call: FunctionCall,
        on_stream: Callable[[str, ToolReturn], None],
    ) -> None:
        body = JsonRPCHttpRequestBody(
            id=function_call.id,
            method=function_call.name,
            params=function_call.arguments,
        )

        on_stream(
            EventType.START,
            ToolReturn(id=function_call.id, result={EventType.START: function_call.name}),
        )

        for event_name, event_data in self._stream_call_json_rpc_http(body.to_json()):
            if event_name in (EventType.DATA, EventType.ERROR):
                response_body = JsonRPCHttpResponseBody.from_json(event_data)
                if response_body.error is not None:
                    raise OpenToolServerCallException(response_body.error.message)
                on_stream(event_name, ToolReturn(id=function_call.id, result=response_body.result))

        on_stream(
            EventType.DONE,
            ToolReturn(id=function_call.id, result={EventType.DONE: function_call.name}),
        )

    def _stream_call_json_rpc_http(
        self, payload: dict[str, Any]
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        url = f"{self.base_url}/streamCall"
        request_data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self.tool_api_key:
            headers["Authorization"] = f"Bearer {self.tool_api_key}"

        req = request.Request(url=url, method="POST", data=request_data, headers=headers)
        try:
            with request.urlopen(req, timeout=60) as response:
                if response.status == 401:
                    raise OpenToolServerUnauthorizedException()
                buffer: list[str] = []
                for raw_line in response:
                    line = raw_line.decode("utf-8").rstrip("\n")
                    if line == "":
                        event_name, event_data = _parse_sse_block(buffer)
                        buffer = []
                        if event_name is not None and event_data is not None:
                            yield event_name, event_data
                        continue
                    buffer.append(line)
                if buffer:
                    event_name, event_data = _parse_sse_block(buffer)
                    if event_name is not None and event_data is not None:
                        yield event_name, event_data
        except error.HTTPError as exc:
            if exc.code == 401:
                raise OpenToolServerUnauthorizedException() from exc
            message = exc.read().decode("utf-8", errors="ignore")
            raise OpenToolServerCallException(f"HTTP {exc.code} {message}") from exc
        except (socket.timeout, error.URLError) as exc:
            raise OpenToolServerNoAccessException() from exc

    def load(self) -> OpenTool | None:
        try:
            data = self._request_json("GET", "/load")
            return OpenTool.from_json(data)
        except Exception:
            return None

    def stop(self) -> StatusInfo | None:
        try:
            data = self._request_json("POST", "/stop")
            return StatusInfo.from_json(data)
        except Exception:
            return None

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = parse.urljoin(f"{self.base_url}/", path.lstrip("/"))
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.tool_api_key:
            headers["Authorization"] = f"Bearer {self.tool_api_key}"

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = request.Request(url=url, method=method, data=data, headers=headers)

        try:
            with request.urlopen(req, timeout=20) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except error.HTTPError as exc:
            if exc.code == 401:
                raise OpenToolServerUnauthorizedException() from exc
            message = exc.read().decode("utf-8", errors="ignore")
            raise OpenToolServerCallException(f"HTTP {exc.code} {message}") from exc
        except (socket.timeout, error.URLError) as exc:
            raise OpenToolServerNoAccessException() from exc


def _parse_sse_block(lines: list[str]) -> tuple[str | None, dict[str, Any] | None]:
    event_name: str | None = None
    data_payload: str | None = None

    for line in lines:
        if line.startswith("event:"):
            event_name = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_payload = line[len("data:") :].strip()

    if event_name is None or data_payload is None:
        return None, None

    try:
        return event_name, json.loads(data_payload)
    except json.JSONDecodeError:
        return event_name, {"raw": data_payload}
