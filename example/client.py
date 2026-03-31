from __future__ import annotations

from opentool_python.opentool_client import FunctionCall, HostType, OpenToolClient

TOOL_PORT = 17002
TOOL_API_KEY = "6621c8a3-2110-4e6a-9d62-70ccd467e789"


def main() -> None:
    client = OpenToolClient(
        tool_host=HostType.LOCALHOST,
        tool_port=TOOL_PORT,
        tool_api_key=TOOL_API_KEY,
    )

    version = client.version()
    print(version.to_json())

    tool_return = client.call(FunctionCall(id="callId-0", name="count", arguments={}))
    print(tool_return.to_json())

    client.stream_call(
        FunctionCall(id="callId-1", name="sequentiallyRead", arguments={}),
        lambda event, result: print(event, result.to_json()),
    )

    open_tool = client.load()
    print(open_tool.to_json() if open_tool else None)

    status = client.stop()
    print(status.to_json() if status else None)


if __name__ == "__main__":
    main()
