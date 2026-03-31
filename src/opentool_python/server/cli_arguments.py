from __future__ import annotations

import argparse
from typing import Any

from ..dto import (
    CLI_ARGUMENT_APIKEYS,
    CLI_ARGUMENT_HOST,
    CLI_ARGUMENT_PORT,
    CLI_ARGUMENT_TAG,
)


class CliArguments:
    def __init__(self, args: list[str]) -> None:
        self._args = args
        self._parser = argparse.ArgumentParser(add_help=False)
        self._parser.add_argument(f"--{CLI_ARGUMENT_TAG}")
        self._parser.add_argument(f"--{CLI_ARGUMENT_HOST}")
        self._parser.add_argument(f"--{CLI_ARGUMENT_PORT}")
        self._parser.add_argument(f"--{CLI_ARGUMENT_APIKEYS}", action="append")

    def add_custom_option(self, name: str, **kwargs: Any) -> "CliArguments":
        argument_name = f"--{name}"
        self._parser.add_argument(argument_name, **kwargs)
        return self

    def add_custom_multi_option(self, name: str, **kwargs: Any) -> "CliArguments":
        argument_name = f"--{name}"
        if "action" not in kwargs:
            kwargs["action"] = "append"
        self._parser.add_argument(argument_name, **kwargs)
        return self

    def parse(self) -> dict[str, Any]:
        namespace, _ = self._parser.parse_known_args(self._args)
        data: dict[str, Any] = {}
        for key, value in vars(namespace).items():
            if value is not None:
                data[key] = value
        return data
