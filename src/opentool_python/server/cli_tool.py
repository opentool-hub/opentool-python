from __future__ import annotations

from typing import Any

from ..tool.tool import Tool


class CliTool(Tool):
    def init_args(self, args: dict[str, Any] | None) -> dict[str, Any] | None:
        return args
