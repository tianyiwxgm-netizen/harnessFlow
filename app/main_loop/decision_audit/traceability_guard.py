"""100% 可追溯硬约束 · Goal §4.1 铁律.

核心职责:任何"决策"必须有对应的 audit entry, 否则 raise `E_AUDIT_UNAUDITED_DECISION`
(release blocker · 不可降级).

使用:
    guard = TraceabilityGuard()
    guard.register_decision("dec-123", project_id="pid-xxx")  # L2-02 决策开始
    # ... L2-02 调用 record_audit(decision_made, linked_decision="dec-123")
    guard.mark_audited("dec-123")  # record_audit 成功后标记
    guard.verify_all_audited()  # 无未审计决策 · 否则 raise E_AUDIT_UNAUDITED_DECISION
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from app.main_loop.decision_audit.errors import (
    E_AUDIT_UNAUDITED_DECISION,
    AuditError,
    make_audit_error,
)


@dataclass
class _DecisionRecord:
    decision_id: str
    project_id: str
    tick_id: Optional[str] = None
    reason: Optional[str] = None
    registered_ts: float = 0.0
    audited: bool = False


@dataclass
class TraceabilityReport:
    """可追溯率报告."""

    total_decisions: int = 0
    audited_decisions: int = 0
    unaudited_decision_ids: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        """审计率 · [0.0, 1.0]."""
        if self.total_decisions == 0:
            return 1.0
        return self.audited_decisions / self.total_decisions

    @property
    def is_full_coverage(self) -> bool:
        """100% 硬约束 · Goal §4.1."""
        return self.coverage >= 1.0


class TraceabilityGuard:
    """100% 可追溯守护 · L1-01 决策的"审计台账"."""

    def __init__(self) -> None:
        self._decisions: dict[str, _DecisionRecord] = {}
        self._lock = threading.RLock()

    def register_decision(
        self,
        decision_id: str,
        *,
        project_id: str,
        tick_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """L2-02 决策开始时登记 · 幂等(同 decision_id 重复登记忽略)."""
        with self._lock:
            if decision_id in self._decisions:
                return
            import time
            self._decisions[decision_id] = _DecisionRecord(
                decision_id=decision_id,
                project_id=project_id,
                tick_id=tick_id,
                reason=reason,
                registered_ts=time.monotonic(),
                audited=False,
            )

    def mark_audited(self, decision_id: str) -> None:
        """record_audit 成功后标记 · 幂等."""
        with self._lock:
            rec = self._decisions.get(decision_id)
            if rec is None:
                # 允许"先 audit 后 register"逆序 · 自动登记
                import time
                self._decisions[decision_id] = _DecisionRecord(
                    decision_id=decision_id,
                    project_id="__unknown__",
                    registered_ts=time.monotonic(),
                    audited=True,
                )
            else:
                rec.audited = True

    def is_audited(self, decision_id: str) -> bool:
        with self._lock:
            rec = self._decisions.get(decision_id)
            return rec is not None and rec.audited

    def has_decision(self, decision_id: str) -> bool:
        with self._lock:
            return decision_id in self._decisions

    def report(self) -> TraceabilityReport:
        """生成当前可追溯率报告."""
        with self._lock:
            total = len(self._decisions)
            audited = sum(1 for r in self._decisions.values() if r.audited)
            unaudited = [d for d, r in self._decisions.items() if not r.audited]
            return TraceabilityReport(
                total_decisions=total,
                audited_decisions=audited,
                unaudited_decision_ids=unaudited,
            )

    def verify_all_audited(self) -> None:
        """100% 硬约束 · 有任何未审计的决策 → raise E_AUDIT_UNAUDITED_DECISION.

        调用时机:tick 结束 / session 结束 / CI 集成测试收尾 · 由 L2-01 驱动.
        """
        rep = self.report()
        if not rep.is_full_coverage:
            raise make_audit_error(
                E_AUDIT_UNAUDITED_DECISION,
                f"可追溯率 {rep.coverage:.2%} < 100% · "
                f"未审计 decisions={rep.unaudited_decision_ids} · "
                f"release blocker(Goal §4.1)",
                unaudited=rep.unaudited_decision_ids,
                coverage=rep.coverage,
            )

    def reset(self) -> None:
        """测试钩子 · 清空台账."""
        with self._lock:
            self._decisions.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._decisions)


__all__ = ["TraceabilityGuard", "TraceabilityReport"]
