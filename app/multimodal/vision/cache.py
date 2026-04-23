"""L2-03 vision cache · (pid, image_hash, task) → VisionResult · LRU."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from pathlib import Path
from typing import Any


def hash_image(path: Path) -> str:
    """Return sha256 hex of image bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VisionCache:
    def __init__(self, max_size: int = 256) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self._max = max_size
        self._data: OrderedDict[tuple[str, str, str], Any] = OrderedDict()

    def get(self, pid: str, image_hash: str, task: str) -> Any | None:
        key = (pid, image_hash, task)
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, pid: str, image_hash: str, task: str, value: Any) -> None:
        key = (pid, image_hash, task)
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._max:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
