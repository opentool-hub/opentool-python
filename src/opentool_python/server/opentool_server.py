from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from ..dto import (
    CLI_ARGUMENT_APIKEYS,
    CLI_ARGUMENT_HOST,
    CLI_ARGUMENT_PORT,
    CLI_ARGUMENT_TAG,
    DEFAULT_PREFIX,
    DEFAULT_TOOL_HOST,
    DEFAULT_TOOL_PORT,
    DEFAULT_TOOL_TAG,
    JSONRPC_VERSION,
    JsonRPCHttpRequestBody,
    JsonRPCHttpResponseBody,
    JsonRPCHttpResponseBodyError,
    StatusInfo,
    StatusType,
    Version,
)
from ..tool.exceptions import JsonParserException
from ..tool.model import EventType
from .cli_arguments import CliArguments
from .cli_tool import CliTool
from .exceptions import InvalidJsonPayloadException, JsonParseException, ServerException


class Server(ABC):
    def __init__(self, cli_tool: CliTool) -> None:
        self.cli_tool = cli_tool

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError


class OpenToolServer(Server):
    def __init__(self, cli_tool: CliTool, cli_arguments: CliArguments | None = None) -> None:
        super().__init__(cli_tool=cli_tool)
        self.cli_arguments = cli_arguments
        self.version = DEFAULT_TOOL_TAG
        self.host = DEFAULT_TOOL_HOST
        self.port = DEFAULT_TOOL_PORT
        self.prefix = DEFAULT_PREFIX
        self.api_keys: list[str] = []
        self._server: ThreadingHTTPServer | None = None

    def init_cli(self) -> None:
        cli_args = self.cli_arguments.parse() if self.cli_arguments else {}
        cli_args = self.cli_tool.init_args(cli_args) or cli_args

        self.version = str(cli_args.get(CLI_ARGUMENT_TAG, DEFAULT_TOOL_TAG))
        self.host = str(cli_args.get(CLI_ARGUMENT_HOST, DEFAULT_TOOL_HOST))

        raw_port = cli_args.get(CLI_ARGUMENT_PORT)
        if raw_port is not None:
            self.port = int(raw_port)

        api_keys = cli_args.get(CLI_ARGUMENT_APIKEYS)
        self.api_keys = list(api_keys) if isinstance(api_keys, list) else []

    def start(self) -> None:
        self.init_cli()
        self.cli_tool.init()

        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args: Any) -> None:
                return None

            def do_GET(self) -> None:  # noqa: N802
                if not self._authorize():
                    return
                path = self._path_without_query()
                if path == f"{server.prefix}/version":
                    self._respond_json(HTTPStatus.OK, Version(version=server.version).to_json())
                    return
                if path == f"{server.prefix}/load":
                    try:
                        open_tool = server.cli_tool.load()
                        body = open_tool.to_json() if open_tool is not None else JsonParserException().to_json()
                        self._respond_json(HTTPStatus.OK, body)
                    except Exception as exc:
                        self._respond_json(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": str(exc)},
                        )
                    return
                self._respond_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

            def do_POST(self) -> None:  # noqa: N802
                if not self._authorize():
                    return
                path = self._path_without_query()
                if path == f"{server.prefix}/call":
                    self._handle_call()
                    return
                if path == f"{server.prefix}/streamCall":
                    self._handle_stream_call()
                    return
                if path == f"{server.prefix}/stop":
                    self._handle_stop()
                    return
                self._respond_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

            def _handle_call(self) -> None:
                payload_result = self._read_json_payload()
                if isinstance(payload_result, tuple):
                    self._respond_json(payload_result[0], payload_result[1])
                    return

                payload = payload_result
                try:
                    body = JsonRPCHttpRequestBody.from_json(payload)
                except Exception as exc:
                    self._respond_json(
                        HTTPStatus.BAD_REQUEST,
                        _json_parse_error_response(
                            JsonParseException(message=str(exc)),
                            id=str(payload.get("id", "")),
                        ),
                    )
                    return

                try:
                    result = server.cli_tool.call(body.method, body.params)
                    response_body = JsonRPCHttpResponseBody(result=result, id=body.id)
                    self._respond_json(HTTPStatus.OK, response_body.to_json())
                except Exception as exc:
                    response_body = JsonRPCHttpResponseBody(
                        result={},
                        id=body.id,
                        error=JsonRPCHttpResponseBodyError(code=500, message=str(exc)),
                    )
                    self._respond_json(HTTPStatus.OK, response_body.to_json())

            def _handle_stream_call(self) -> None:
                payload_result = self._read_json_payload()
                if isinstance(payload_result, tuple):
                    self._respond_json(payload_result[0], payload_result[1])
                    return

                payload = payload_result
                try:
                    body = JsonRPCHttpRequestBody.from_json(payload)
                except Exception as exc:
                    self._respond_json(
                        HTTPStatus.BAD_REQUEST,
                        _json_parse_error_response(JsonParseException(message=str(exc))),
                    )
                    return

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                self._push_data(EventType.START, json.dumps({EventType.START: body.method}))

                try:
                    def send_event(event: str, data: dict[str, Any]) -> None:
                        if event == EventType.DATA:
                            response_body = JsonRPCHttpResponseBody(result=data, id=body.id)
                            self._push_data(event, json.dumps(response_body.to_json()))
                        elif event == EventType.ERROR:
                            error = JsonRPCHttpResponseBodyError(
                                code=int(data.get("code", 500)),
                                message=str(data.get("message", data)),
                            )
                            response_body = JsonRPCHttpResponseBody(result={}, id=body.id, error=error)
                            self._push_data(event, json.dumps(response_body.to_json()))

                    server.cli_tool.stream_call(body.method, body.params, send_event)
                except Exception as exc:
                    self._push_data(
                        EventType.ERROR,
                        json.dumps({"code": 500, "message": str(exc), "id": body.id}),
                    )
                finally:
                    self._push_data(EventType.DONE, json.dumps({EventType.DONE: body.method}))

            def _handle_stop(self) -> None:
                try:
                    server.cli_tool.dispose()
                    self._respond_json(HTTPStatus.OK, StatusInfo(status=StatusType.STOPPED).to_json())

                    def shutdown_async() -> None:
                        server.stop()

                    threading.Thread(target=shutdown_async, daemon=True).start()
                except Exception as exc:
                    self._respond_json(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        {"error": str(exc)},
                    )

            def _read_json_payload(self) -> dict[str, Any] | tuple[int, dict[str, Any]]:
                content_type = self.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    return HTTPStatus.BAD_REQUEST, {"error": "Content-Type must be application/json"}

                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

                try:
                    payload = json.loads(body)
                except json.JSONDecodeError as exc:
                    return (
                        HTTPStatus.BAD_REQUEST,
                        _json_parse_error_response(JsonParseException(message=str(exc))),
                    )

                if not isinstance(payload, dict):
                    return (
                        HTTPStatus.BAD_REQUEST,
                        _json_parse_error_response(InvalidJsonPayloadException()),
                    )
                return payload

            def _path_without_query(self) -> str:
                return urlparse(self.path).path

            def _authorize(self) -> bool:
                if not server.api_keys:
                    return True
                authorization = self.headers.get("Authorization")
                token_prefix = "Bearer "
                if authorization is None or not authorization.startswith(token_prefix):
                    self._respond_text(HTTPStatus.UNAUTHORIZED, "Missing or malformed authorization header")
                    return False
                token = authorization[len(token_prefix) :]
                if token not in server.api_keys:
                    self._respond_text(HTTPStatus.UNAUTHORIZED, "Invalid authorization token")
                    return False
                return True

            def _respond_json(self, status: int, body: dict[str, Any]) -> None:
                payload = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _respond_text(self, status: int, body: str) -> None:
                payload = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _push_data(self, event_type: str, data_string: str) -> None:
                payload = f"event:{event_type}\\ndata:{data_string}\\n\\n".encode("utf-8")
                self.wfile.write(payload)
                self.wfile.flush()

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        print(f"Start Server: http://{self.host}:{self.port}{self.prefix}")
        self._server.serve_forever(poll_interval=0.1)

    def stop(self) -> None:
        server = self._server
        if server is None:
            return
        server.shutdown()
        server.server_close()
        self._server = None


def _json_parse_error_response(exception: ServerException, id: str | None = None) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "result": {},
        "error": exception.to_json(),
        "id": id,
    }
