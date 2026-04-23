"""IC-09 append_event mock — 波4 替换为 Dev-α L1-09 L2-05 真实事件总线.

TODO:MOCK-REPLACE-FROM-DEV-α — α WP04 交付后，删除本文件并 import
真实 `app.l1_09.event_bus.append_event`（契约一致）.

字段级契约参考 docs/3-1-Solution-Technical/integration/ic-contracts.md §3.9 IC-09。
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class IC09EventRecord:
    """IC-09 事件记录（与真实接口字段对齐 · 不可再加字段）."""

    event_id: str
    project_id: str
    l1: str                    # 发起方 L1
    event_type: str            # e.g. "skill_invocation_started"
    payload: dict[str, Any]
    ts_ns: int                 # time.time_ns()
    prev_hash: str             # IC-14 一致性链 · 前一条事件的 hash
    this_hash: str             # sha256(prev_hash + canonical(record))

    def canonical_bytes(self) -> bytes:
        body = {k: v for k, v in self.__dict__.items() if k != "this_hash"}
        return json.dumps(body, sort_keys=True, default=str).encode("utf-8")


class IC09EventBusMock:
    """内存版事件总线 · 全局锁 · hash chain · 单测可 flush/read.

    真实替换时保留 append_event / read_all 两个方法的签名不变（其余是 mock 私有）。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[IC09EventRecord] = []
        self._last_hash = "0" * 64   # genesis

    def append_event(
        self,
        *,
        project_id: str,
        l1: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> IC09EventRecord:
        if not project_id:
            raise ValueError("IC-09: project_id required (PM-14)")
        ts = time.time_ns()
        rec = IC09EventRecord(
            event_id=hashlib.sha256(f"{ts}-{event_type}".encode()).hexdigest()[:16],
            project_id=project_id,
            l1=l1,
            event_type=event_type,
            payload=payload,
            ts_ns=ts,
            prev_hash=self._last_hash,
            this_hash="",
        )
        rec.this_hash = hashlib.sha256(
            rec.prev_hash.encode() + rec.canonical_bytes()
        ).hexdigest()
        with self._lock:
            self._events.append(rec)
            self._last_hash = rec.this_hash
        return rec

    def read_all(self, project_id: str | None = None) -> list[IC09EventRecord]:
        if project_id is None:
            return list(self._events)
        return [e for e in self._events if e.project_id == project_id]

    def flush(self) -> None:
        with self._lock:
            self._events.clear()
            self._last_hash = "0" * 64


_default_bus: IC09EventBusMock | None = None


def get_default_bus() -> IC09EventBusMock:
    """进程级单例 mock · 仅测试用."""
    global _default_bus
    if _default_bus is None:
        _default_bus = IC09EventBusMock()
    return _default_bus
