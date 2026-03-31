from __future__ import annotations

from pathlib import Path

from opentool_python.json_loader import OpenToolJsonLoader
from opentool_python.opentool_server import (
    CLI_ARGUMENT_APIKEYS,
    CLI_ARGUMENT_HOST,
    CLI_ARGUMENT_PORT,
    CLI_ARGUMENT_TAG,
    CliArguments,
    CliTool,
    EventType,
    FunctionNotSupportedException,
    OpenTool,
    OpenToolServer,
    ToolBreakException,
)

from mock_util import MockUtil

TOOL_PORT = 17002
TOOL_API_KEYS = [
    "6621c8a3-2110-4e6a-9d62-70ccd467e789",
    "bb31b6a6-1fda-4214-8cd6-b1403842070c",
]


class MockTool(CliTool):
    def __init__(self) -> None:
        self.mock_util = MockUtil()

    def init_args(self, args):
        new_values = args.get("newValues") if isinstance(args, dict) else None
        if isinstance(new_values, list):
            for value in new_values:
                self.mock_util.create(str(value))
        return args

    def call(self, name, arguments):
        if name == "count":
            return {"count": self.mock_util.count()}
        if name == "create" and arguments:
            return {"id": self.mock_util.create(str(arguments["text"]))}
        if name == "read" and arguments:
            return {"text": self.mock_util.read(int(arguments["id"]))}
        if name == "update" and arguments:
            self.mock_util.update(int(arguments["id"]), str(arguments["text"]))
            return {"result": "Update successfully."}
        if name == "delete" and arguments:
            self.mock_util.delete(int(arguments["id"]))
            return {"result": "Delete successfully."}
        if name == "run":
            try:
                self.mock_util.run()
            except Exception as exc:
                raise ToolBreakException(str(exc)) from exc
            return {"result": "Run successfully."}
        return FunctionNotSupportedException(function_name=name).to_json()

    def stream_call(self, name, arguments, on_event):
        if name == "sequentiallyRead":
            self.mock_util.sequentially_read(
                lambda data: on_event(EventType.DATA, {"data": data})
            )
        else:
            on_event(
                EventType.ERROR,
                FunctionNotSupportedException(function_name=name).to_json(),
            )

    def load(self) -> OpenTool | None:
        json_path = Path(__file__).parent / "mock_tool.json"
        return OpenToolJsonLoader().load_from_file(str(json_path))


def main() -> None:
    cli_args = [
        "--newValues",
        "Foo",
        "--newValues",
        "bar",
        f"--{CLI_ARGUMENT_TAG}",
        "1.0.0",
        f"--{CLI_ARGUMENT_HOST}",
        "0.0.0.0",
        f"--{CLI_ARGUMENT_PORT}",
        str(TOOL_PORT),
        f"--{CLI_ARGUMENT_APIKEYS}",
        TOOL_API_KEYS[0],
        f"--{CLI_ARGUMENT_APIKEYS}",
        TOOL_API_KEYS[1],
    ]

    cli_arguments = CliArguments(cli_args).add_custom_multi_option(
        "newValues",
        help="Demo to customize args, will add new values. e.g. --newValues Foo --newValues Bar",
    )
    OpenToolServer(cli_tool=MockTool(), cli_arguments=cli_arguments).start()


if __name__ == "__main__":
    main()
