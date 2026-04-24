"""L2-03 · cursor-based 分页 · 大结果（> 10000 条）拆页."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    items: list
    next_cursor: int | None
    total: int


def paginate(items: Iterable, *, cursor: int = 0, page_size: int = 100) -> Page:
    all_items = list(items)
    total = len(all_items)
    end = cursor + page_size
    chunk = all_items[cursor:end]
    next_cursor = end if end < total else None
    return Page(items=chunk, next_cursor=next_cursor, total=total)


__all__ = ["Page", "paginate"]
