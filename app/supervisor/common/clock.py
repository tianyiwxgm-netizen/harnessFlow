"""可注入时钟。RealClock 走 time.monotonic · FrozenClock 供测试按步长 advance。

采集器用 monotonic 计算 latency_ms（抗墙钟跳变）· now_iso 仅做事件落盘 readability。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


class Clock(Protocol):
    """两方法接口 · 任何实现注入到 collector 即可替换。"""

    def now_iso(self) -> str: ...

    def monotonic_ms(self) -> int: ...


class RealClock:
    """生产实现。墙钟 UTC + monotonic 基准。"""

    def now_iso(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def monotonic_ms(self) -> int:
        return int(time.monotonic() * 1000)


@dataclass
class FrozenClock:
    """测试时钟。advance(ms) 手动推进 · now_iso 保持给定字符串。"""

    _now_iso: str = "2026-04-23T00:00:00Z"
    _monotonic: int = 0

    def now_iso(self) -> str:
        return self._now_iso

    def monotonic_ms(self) -> int:
        return self._monotonic

    def advance(self, ms: int) -> None:
        self._monotonic += ms
