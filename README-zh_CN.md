# OpenTool Python SDK

[English](README.md) | 中文

OpenTool Python SDK 提供在 Python 中托管或调用 OpenTool 兼容 Tool 的核心能力：HTTP/JSON-RPC 服务端运行时、支持普通调用 + SSE 流式调用的客户端，以及 JSON 规范加载器。该项目的目标是与 [opentool-dart](https://github.com/opentool-hub/opentool-dart) 对齐，便于多语言 SDK 保持一致行为。

## 库入口

- `opentool_python.opentool_server` - 服务端运行时、CLI 参数工具与 Tool 基类。
- `opentool_python.opentool_client` - HTTP/JSON-RPC 客户端，以及 DTO/LLM 数据结构。
- `opentool_python.opentool_schema` - OpenTool JSON 规范模型与加载器。

## 特性

- `OpenToolServer` 基于你的 `Tool` 实现挂载 `/opentool` JSON-RPC 接口，可选启用 Bearer API Key 鉴权。
- `OpenToolClient` 支持版本查询、同步 `call`、SSE `stream_call`、`load` 与远程 `stop`。
- `OpenToolJsonLoader` 支持解析 OpenTool JSON 规范并处理 `$ref` 引用。
- `example/server.py` 与 `example/client.py` 提供了 CRUD + 流式调用的端到端示例。

## 环境要求

- Python `>=3.10`
- 安装 SDK 时会安装 Schema 校验依赖 `jsonschema` 和 `referencing`。

## 安装

从 PyPI 安装：

```sh
python -m pip install opentool-python
```

本地开发建议使用可编辑安装：

```sh
pip install -e .
```

也可以在其他项目中通过源码路径安装：

```sh
pip install /absolute/path/to/opentool-python
```

## 快速开始

### 实现一个 Tool

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

### 启动服务端

```sh
PYTHONPATH=src python example/server.py
```

`CliArguments` 会把内置参数和自定义参数传给 `CliTool.init_args`，适合在服务真正对外前完成初始化。

### 在 Python 中调用 Tool

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

## CLI 与 HTTP 参考

- 默认路径前缀：`/opentool`
- 接口列表：
  - `GET /version`
  - `POST /call`
  - `POST /streamCall`
  - `GET /load` 在工具没有元数据时返回 HTTP 404，错误码为 `TOOL_NOT_FOUND`。
  - `POST /stop`
- 内置 CLI 参数（`CliArguments`）：
  - `--opentoolServerTag`
  - `--opentoolServerHost`
  - `--opentoolServerPort`
  - 可重复的 `--opentoolServerApiKeys`
- 流式协议为 SSE，事件名包括 `start`、`data`、`error`、`done`。

## JSON 规范加载器

- 仅需要规范模型/解析时可直接使用 `opentool_python.opentool_schema`。
- `OpenToolJsonLoader().load_from_file(path)` 会从文件加载并解析 `#/schemas/*` 的 `$ref`。
- `OpenToolJsonLoader().load(json_string)` 支持从字符串解析。
- 规范定义见：[OpenTool Spec](https://github.com/opentool-hub/opentool-spec)。

Schema 默认采用 JSON Schema Draft 2020-12，也可通过 `$schema` 选择已支持的版本。`Schema.to_json()` 返回字典或布尔值，并保留引用、注解和扩展关键字。`#/schemas/...` 引用在各自的 OpenTool 文档内解析，文件和 HTTP 加载采用同一规则。

用 `schema.validate(value)` 获取校验结果及错误，或用 `schema.is_valid(value)` 判断是否有效。传入 `validate_formats=True` 可启用格式校验。需要解析外部 Schema 时，向 `OpenTool.from_json`、`OpenToolJsonLoader` 或 `OpenToolClient` 传入同步的 `schema_reference_resolver` 回调。回调接收资源 URI，返回字典、布尔值或表示资源不存在的 `None`。

## 示例与开发

- 示例文件：
  - `example/server.py`
  - `example/client.py`
  - `example/mock_tool.json`
- 常用本地命令：

```sh
python -m compileall src example
PYTHONPATH=src python example/server.py
PYTHONPATH=src python example/client.py
```

## 兼容性说明

当前 Python SDK 是对齐 `opentool-dart` 的基线版本，重点保证 API 形态与协议行为兼容。
