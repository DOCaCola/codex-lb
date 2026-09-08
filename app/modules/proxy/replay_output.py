"""Bounded per-attempt output reconstruction for stateless continuation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.core.types import JsonValue


@dataclass
class ReplayOutputCollector:
    max_items: int = 256
    max_bytes: int = 8 * 1024 * 1024
    _items: dict[int, tuple[JsonValue, int]] = field(default_factory=dict)
    _bytes: int = 0
    _tainted: bool = False

    def clear(self) -> None:
        self._items.clear()
        self._bytes = 0
        self._tainted = False

    def retain(self, payload: dict[str, JsonValue]) -> None:
        if self._tainted:
            return
        index = payload.get("output_index")
        item = payload.get("item")
        if type(index) is not int or index < 0 or not isinstance(item, dict) or not isinstance(item.get("type"), str):
            self.clear()
            self._tainted = True
            return
        size = len(json.dumps(item, separators=(",", ":")).encode())
        previous = self._items.pop(index, None)
        self._bytes += size - (previous[1] if previous else 0)
        if len(self._items) >= self.max_items or self._bytes > self.max_bytes:
            self.clear()
            self._tainted = True
            return
        self._items[index] = (item, size)

    def finish(self, terminal_output: JsonValue) -> list[JsonValue] | None:
        try:
            if isinstance(terminal_output, list) and terminal_output:
                return terminal_output
            if self._tainted:
                return None
            return [item for _, (item, _) in sorted(self._items.items())]
        finally:
            self.clear()
