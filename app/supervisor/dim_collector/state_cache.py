"""StateCache · Last-Known-Good per-project 单槽位 + TTL。

用途：
- tick 成功后 put snapshot · collector 作为 LKG
- on_demand cache-hit 命中 → 20ms SLO 返回
- fast collect 复用 6 维 cached state · 只刷 tool_calls + latency_slo

TTL：默认 60s（与 §B C/D-1 约束一致）· 超时 is_stale=True · 但不自动清理（collector 决策是否降级）
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.supervisor.common.clock import Clock
from app.supervisor.dim_collector.schemas import SupervisorSnapshot


@dataclass
class StateCache:
    clock: Clock
    ttl_ms: int = 60_000
    _store: dict[str, SupervisorSnapshot] = field(default_factory=dict)

    def get_latest(self, project_id: str) -> SupervisorSnapshot | None:
        return self._store.get(project_id)

    def put(self, snap: SupervisorSnapshot) -> None:
        self._store[snap.project_id] = snap

    def is_stale(self, project_id: str) -> bool:
        snap = self._store.get(project_id)
        if snap is None:
            return False
        age = self.clock.monotonic_ms() - snap.captured_at_ms
        return age > self.ttl_ms
