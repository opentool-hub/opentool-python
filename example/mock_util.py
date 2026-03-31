from __future__ import annotations

import time


class MockUtil:
    def __init__(self) -> None:
        self.storage = ["Hello", "World"]

    def count(self) -> int:
        return len(self.storage)

    def create(self, text: str) -> int:
        self.storage.append(text)
        return len(self.storage) - 1

    def read(self, idx: int) -> str:
        return self.storage[idx]

    def sequentially_read(self, on_data) -> None:
        for data in self.storage:
            on_data(data)
            time.sleep(2)

    def update(self, idx: int, text: str) -> None:
        self.storage[idx] = text

    def delete(self, idx: int) -> None:
        self.storage.pop(idx)

    def run(self) -> None:
        raise RuntimeError("A fatal error to break this tool.")
