"""LRU cache keyed by (lang, file_hash) · in-memory · pid-isolated via keyed cache namespace."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


class LRUCache:
    def __init__(self, max_size: int = 128) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self._max = max_size
        self._data: OrderedDict[tuple[str, str, str], Any] = OrderedDict()
        # keys are (pid, lang, file_hash) · PM-14 enforces pid isolation

    def get(self, pid: str, lang: str, file_hash: str) -> Any | None:
        key = (pid, lang, file_hash)
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, pid: str, lang: str, file_hash: str, value: Any) -> None:
        key = (pid, lang, file_hash)
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._max:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
