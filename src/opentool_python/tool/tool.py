from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from ..model.opentool import OpenTool


class Tool(ABC):
    def init(self) -> None:
        return None

    @abstractmethod
    def call(self, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
        raise NotImplementedError

    def stream_call(
        self,
        name: str,
        arguments: dict[str, Any] | None,
        on_event: Callable[[str, dict[str, Any]], None],
    ) -> None:
        return None

    def load(self) -> OpenTool | None:
        return None

    def dispose(self) -> None:
        return None
