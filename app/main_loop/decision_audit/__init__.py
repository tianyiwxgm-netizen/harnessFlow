"""L1-01 · L2-05 决策审计记录器 · main-2 WP01 · PM-08 单一事实源.

职责(Goal §4.1 硬约束):
    - 每 tick 决策必发 IC-09(decision_made / action_chosen / ic_dispatched · 含 reason + evidence)
    - **可追溯率 100% 硬约束** · 未审计的决策 raise
    - 调 Dev-α(l1_09.event_bus)真实 IC-09

对外:
    - `DecisionAuditRecorder` · 对 L2-01/02/03/04/06 暴露 6 方法(record_audit / query_by_tick /
      query_by_decision / query_by_chain / flush_buffer / replay_from_jsonl / get_hash_tip).
    - `TraceabilityGuard` · 未审计决策触发 raise(release blocker).
    - `EventBusAdapter` · 将 L2-05 的审计入口适配到 Dev-α IC-09 · 唯一落盘出口.
"""
from app.main_loop.decision_audit.schemas import (
    ActionChosen,
    AuditCommand,
    AuditEntry,
    AuditResult,
    DecisionRecord,
    FlushResult,
    HashTip,
    IcDispatched,
    QueryResult,
    ReplayResult,
)
from app.main_loop.decision_audit.errors import (
    AuditError,
    E_AUDIT_BUFFER_OVERFLOW,
    E_AUDIT_CROSS_PROJECT,
    E_AUDIT_EVENT_TYPE_UNKNOWN,
    E_AUDIT_FLUSH_CONCURRENT,
    E_AUDIT_HALT_ON_FAIL,
    E_AUDIT_HASH_BROKEN,
    E_AUDIT_NO_PROJECT_ID,
    E_AUDIT_NO_REASON,
    E_AUDIT_QUERY_MISS,
    E_AUDIT_QUERY_TIMEOUT,
    E_AUDIT_REPLAY_TIMEOUT,
    E_AUDIT_STALE_BUFFER,
    E_AUDIT_UNAUDITED_DECISION,
    E_AUDIT_WRITE_FAIL,
)
from app.main_loop.decision_audit.recorder import DecisionAuditRecorder
from app.main_loop.decision_audit.traceability_guard import TraceabilityGuard

__all__ = [
    # schemas
    "ActionChosen",
    "AuditCommand",
    "AuditEntry",
    "AuditResult",
    "DecisionRecord",
    "FlushResult",
    "HashTip",
    "IcDispatched",
    "QueryResult",
    "ReplayResult",
    # errors
    "AuditError",
    "E_AUDIT_BUFFER_OVERFLOW",
    "E_AUDIT_CROSS_PROJECT",
    "E_AUDIT_EVENT_TYPE_UNKNOWN",
    "E_AUDIT_FLUSH_CONCURRENT",
    "E_AUDIT_HALT_ON_FAIL",
    "E_AUDIT_HASH_BROKEN",
    "E_AUDIT_NO_PROJECT_ID",
    "E_AUDIT_NO_REASON",
    "E_AUDIT_QUERY_MISS",
    "E_AUDIT_QUERY_TIMEOUT",
    "E_AUDIT_REPLAY_TIMEOUT",
    "E_AUDIT_STALE_BUFFER",
    "E_AUDIT_UNAUDITED_DECISION",
    "E_AUDIT_WRITE_FAIL",
    # core
    "DecisionAuditRecorder",
    "TraceabilityGuard",
]
