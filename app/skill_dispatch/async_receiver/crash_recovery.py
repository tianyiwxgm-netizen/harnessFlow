"""L2-05 崩溃恢复 · pending.jsonl append-only + TimeoutWatcher asyncio tick.

PendingStore:
  - enroll(entry): append-only 写 jsonl · 幂等（同 result_id 不重复）
  - finalize(result_id, status): 从内存清 (compaction 走 cron · 非本 module)
  - replay(): 启动时读 jsonl 重建 _cache · 容错 malformed 行
  - timed_out(now_ns): 返 deadline 已过的 entries

TimeoutWatcher:
  - start(): asyncio task · 每 tick_s 扫一次 timed_out · 调 handler · finalize(timeout)
  - stop(): cancel + await

SLO: 1000 entries replay ≤ 5s

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-05-异步结果回收器.md
  - docs/superpowers/plans/Dev-γ-impl.md §7 Task 05.4
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import time
from collections.abc import Callable

from .schemas import PendingEntry


class PendingStore:
    """Crash-safe pending entry table · jsonl + in-memory cache."""

    def __init__(self, project_root: pathlib.Path) -> None:
        self.path = (
            pathlib.Path(project_root) / "skills" / "registry-cache" / "pending.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, PendingEntry] = {}

    def enroll(self, entry: PendingEntry) -> None:
        if entry.result_id in self._cache:
            return   # 幂等
        self._cache[entry.result_id] = entry
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
            f.flush()

    def finalize(self, result_id: str, status: str) -> None:
        self._cache.pop(result_id, None)

    def replay(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = PendingEntry(**json.loads(line))
                self._cache[rec.result_id] = rec
            except Exception:
                # malformed line · 跳过
                continue

    def timed_out(self, now_ns: int | None = None) -> list[PendingEntry]:
        now = now_ns if now_ns is not None else time.time_ns()
        return [e for e in self._cache.values() if e.deadline_ts_ns < now]


class TimeoutWatcher:
    """asyncio 背景 task · 扫 timed_out entries · 调用 handler."""

    def __init__(self, store: PendingStore, tick_s: float = 60.0) -> None:
        self._store = store
        self._tick_s = tick_s
        self._task: asyncio.Task[None] | None = None
        self._handler: Callable[[PendingEntry], None] = lambda _entry: None

    def set_handler(self, handler: Callable[[PendingEntry], None]) -> None:
        self._handler = handler

    async def start(self) -> None:
        async def loop() -> None:
            while True:
                try:
                    for entry in self._store.timed_out():
                        try:
                            self._handler(entry)
                        except Exception:
                            pass
                        self._store.finalize(entry.result_id, "timeout")
                except Exception:
                    pass
                await asyncio.sleep(self._tick_s)

        self._task = asyncio.create_task(loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
