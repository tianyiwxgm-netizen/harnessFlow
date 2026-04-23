"""L1-02 / L1-03 / L1-04 数据源 stub · 供 L2-01 采集器测试注入。

生产替代：真实 IC-L1-02 read_lifecycle_state + read_stage_artifacts、
          IC-L1-03 read_wbs_snapshot、IC-L1-04 read_self_repair_stats + read_rollback_counter。
每个 stub 用 bool 开关模拟 timeout / unavailable · 供错误码分支测试。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class L102Stub:
    """IC-L1-02 · phase + stage artifacts。"""

    phase: str = "S3"
    artifacts_completeness_pct: float = 75.0
    artifacts_missing: list[str] = field(default_factory=list)
    _timeout: bool = False
    _unavailable: bool = False

    async def read_lifecycle_state(self, project_id: str) -> dict[str, Any]:
        if self._unavailable:
            raise RuntimeError("IC-L1-02 unavailable")
        if self._timeout:
            raise TimeoutError("IC-L1-02 timeout")
        return {"phase": self.phase}

    async def read_stage_artifacts(self, project_id: str) -> dict[str, Any]:
        if self._unavailable:
            raise RuntimeError("IC-L1-02 unavailable")
        if self._timeout:
            raise TimeoutError("IC-L1-02 timeout")
        return {
            "completeness_pct": self.artifacts_completeness_pct,
            "missing": list(self.artifacts_missing),
        }


@dataclass
class L103Stub:
    """IC-L1-03 · WBS snapshot。"""

    total: int = 10
    completed: int = 3
    in_progress: int = 2
    blocked: int = 0
    _timeout: bool = False
    _unavailable: bool = False

    async def read_wbs_snapshot(self, project_id: str) -> dict[str, Any]:
        if self._unavailable:
            raise RuntimeError("IC-L1-03 unavailable")
        if self._timeout:
            raise TimeoutError("IC-L1-03 timeout")
        return {
            "total": self.total,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "blocked": self.blocked,
            "completion_pct": round(
                100.0 * self.completed / max(1, self.total), 2
            ),
        }


@dataclass
class L104Stub:
    """IC-L1-04 · self-repair rate + rollback counter。"""

    attempts: int = 5
    successes: int = 4
    failures: int = 1
    rollback_count: int = 0
    rollback_reasons: dict[str, int] = field(default_factory=dict)
    _timeout: bool = False
    _unavailable: bool = False

    async def read_self_repair_stats(self, project_id: str) -> dict[str, Any]:
        if self._unavailable:
            raise RuntimeError("IC-L1-04 unavailable")
        if self._timeout:
            raise TimeoutError("IC-L1-04 timeout")
        rate = 0.0 if self.attempts == 0 else round(self.successes / self.attempts, 4)
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "rate": rate,
        }

    async def read_rollback_counter(self, project_id: str) -> dict[str, Any]:
        if self._unavailable:
            raise RuntimeError("IC-L1-04 unavailable")
        if self._timeout:
            raise TimeoutError("IC-L1-04 timeout")
        return {"count": self.rollback_count, "by_reason": dict(self.rollback_reasons)}
