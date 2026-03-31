# OpenTool SDK for Python

English | [中文](README-zh_CN.md)

OpenTool SDK for Python provides the core building blocks to host or consume OpenTool-compatible tools in Python: an HTTP/JSON-RPC server runtime, an HTTP client with unary + SSE streaming calls, and a JSON schema loader. This project is designed to align with `../opentool-dart` so multi-language SDK behavior stays consistent.

## Library Entrypoints

- `opentool_python.opentool_server` - server runtime, CLI argument helper, and Tool base class.
- `opentool_python.opentool_client` - HTTP/JSON-RPC client plus DTO/LLM models.
- `opentool_python.opentool_schema` - JSON specification models and loader.

## Features

- `OpenToolServer` mounts `/opentool` JSON-RPC endpoints backed by your `Tool` implementation, with optional Bearer API-key auth.
- `OpenToolClient` supports version lookup, unary `call`, SSE `stream_call`, metadata `load`, and remote `stop`.
- `OpenToolJsonLoader` parses OpenTool JSON specs and resolves `$ref` schema references.
- End-to-end examples in `example/server.py` and `example/client.py` demonstrate CRUD + streaming usage.

## Requirements

- Python `>=3.10`
- No required runtime dependencies (current implementation uses Python stdlib only).

## Installation

Install as editable package in local development:

```sh
pip install -e .
```

Or install with source path from another project:

```sh
pip install /absolute/path/to/opentool-python
```

## Quick Start

### Implement a Tool

```python
from pathlib import Path
from opentool_python.json_loader import OpenToolJsonLoader
from opentool_python.opentool_server import (
    CliTool,
    EventType,
    FunctionNotSupportedException,
    OpenTool,
)


class MockTool(CliTool):
    def call(self, name, arguments):
        if name == "count":
            return {"count": 1}
        return FunctionNotSupportedException(function_name=name).to_json()

    def stream_call(self, name, arguments, on_event):
        if name == "sequentiallyRead":
            on_event(EventType.DATA, {"data": "Hello"})
        else:
            on_event(
                EventType.ERROR,
                FunctionNotSupportedException(function_name=name).to_json(),
            )

    def load(self) -> OpenTool | None:
        return OpenToolJsonLoader().load_from_file(
            str(Path("example/mock_tool.json"))
        )
```

### Launch the server

```sh
PYTHONPATH=src python example/server.py
```

`CliArguments` can pass built-in and custom CLI switches into your `CliTool.init_args`, so you can preload state before handlers accept requests.

### Call the tool from Python

```python
from opentool_python.opentool_client import FunctionCall, HostType, OpenToolClient

client = OpenToolClient(
    tool_host=HostType.LOCALHOST,
    tool_port=17002,
    tool_api_key="your-key",
)

print(client.version().to_json())
print(client.call(FunctionCall(id="call-0", name="count", arguments={})).to_json())

client.stream_call(
    FunctionCall(id="call-1", name="sequentiallyRead", arguments={}),
    lambda event, tool_return: print(event, tool_return.result),
)

print(client.load().to_json())
print(client.stop().to_json())
```

## CLI and HTTP Reference

- Base path defaults to `/opentool`.
- Endpoints:
  - `GET /version`
  - `POST /call`
  - `POST /streamCall`
  - `GET /load`
  - `POST /stop`
- Built-in CLI flags (via `CliArguments`):
  - `--opentoolServerTag`
  - `--opentoolServerHost`
  - `--opentoolServerPort`
  - repeatable `--opentoolServerApiKeys`
- Streaming protocol is Server-Sent Events with event names `start`, `data`, `error`, and `done`.

## JSON Specification Loader

- Import `opentool_python.opentool_schema` if you only need spec models and parsing.
- `OpenToolJsonLoader().load_from_file(path)` loads local files and resolves `$ref` entries under `#/schemas/*`.
- `OpenToolJsonLoader().load(json_string)` loads from raw JSON strings.
- Specification reference: [OpenTool Spec](https://github.com/opentool-hub/opentool-spec).

## Examples and Development

- Example files:
  - `example/server.py`
  - `example/client.py`
  - `example/mock_tool.json`
- Common local workflow:

```sh
python -m compileall src example
PYTHONPATH=src python example/server.py
PYTHONPATH=src python example/client.py
```

## Compatibility Note

This Python SDK is currently a baseline implementation focused on API shape and protocol compatibility with `opentool-dart`.
