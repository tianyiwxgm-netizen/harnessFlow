"""IC-06 kb_read mock — 波4 替换为 Dev-β L1-06 L2-02 真实 KB.

TODO:MOCK-REPLACE-FROM-DEV-β — β WP03 交付后删除本 mock · 改为
`from app.l1_06.l2_02.kb_reader import KBReader` 或对齐的真实接口。

字段级契约参考 docs/3-1-Solution-Technical/integration/ic-contracts.md §3.6 IC-06。
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class KBRecipe:
    """KB 中单条 Recipe（Dev-β schema 一致字段）."""

    capability: str
    skill_id: str
    success_rate: float          # 0..1
    last_seen_ts: int            # unix seconds


class IC06KBMock:
    """空 KB · 返空列表 · 支持注入 slow-read 模拟超时."""

    def __init__(
        self,
        recipes: list[KBRecipe] | None = None,
        read_latency_ms: int = 0,
    ) -> None:
        self._recipes = recipes or []
        self._latency_ms = read_latency_ms

    def kb_read(self, project_id: str, capability: str) -> list[KBRecipe]:
        if not project_id:
            raise ValueError("IC-06: project_id required (PM-14)")
        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)
        return [r for r in self._recipes if r.capability == capability]
