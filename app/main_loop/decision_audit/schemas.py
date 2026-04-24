"""L2-05 数据契约 · 对齐 3-1 §3 字段级 + §7 AuditEntry 结构.

关键 schema:
    - `AuditCommand` · record_audit() 入参(4 种 source_ic 多态)
    - `AuditEntry` · 内部聚合根 · buffer / index 存储单位 · 落盘后 immutable
    - `AuditResult` · record_audit() 出参 · {audit_id, buffered, buffer_remaining, event_id}
    - `FlushResult` · flush_buffer() 出参
    - `ReplayResult` · replay_from_jsonl() 出参
    - `HashTip` · get_hash_tip() 出参
    - `QueryResult` · query_by_* 出参
    - `DecisionRecord` · L2-02 decision_made 的 payload 结构
    - `ActionChosen` · L2-04 任务链 action_chosen 的 payload
    - `IcDispatched` · L2-04 dispatch 出 IC 的 payload

TDD 铁律的字段以此处 schema 为准(不用 TDD doc 里示例 schema 的字面逐字 · 以结构对齐).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


# =========================================================
# source_ic 白名单 · §2.4 VO
# =========================================================

SOURCE_IC_LITERALS = ("IC-L2-05", "IC-L2-06", "IC-L2-07", "IC-L2-09")
SourceIC = Literal["IC-L2-05", "IC-L2-06", "IC-L2-07", "IC-L2-09"]


# =========================================================
# action × source_ic → event_type 白名单
# §7.2 11 个 L1-01:* event_type · 对齐 architecture.md §2.5
# =========================================================

# (source_ic, action) → event_type(以 "L1-01:" 前缀)
EVENT_TYPE_MAP: dict[tuple[str, str], str] = {
    # IC-L2-05 通用
    ("IC-L2-05", "tick_scheduled"): "L1-01:tick_scheduled",
    ("IC-L2-05", "tick_completed"): "L1-01:tick_completed",
    ("IC-L2-05", "tick_timeout"): "L1-01:tick_timeout",
    ("IC-L2-05", "idle_spin"): "L1-01:idle_spin",
    ("IC-L2-05", "panic_intercepted"): "L1-01:panic_intercepted",
    ("IC-L2-05", "hard_halt_received"): "L1-01:hard_halt",
    ("IC-L2-05", "supervisor_info"): "L1-01:supervisor_info",
    ("IC-L2-05", "decision_made"): "L1-01:decision_made",
    ("IC-L2-05", "action_chosen"): "L1-01:action_chosen",
    ("IC-L2-05", "ic_dispatched"): "L1-01:ic_dispatched",
    # IC-L2-06 state
    ("IC-L2-06", "state_transitioned"): "L1-01:state_transition",
    # IC-L2-07 chain
    ("IC-L2-07", "chain_step_completed"): "L1-01:chain_step_completed",
    # IC-L2-09 warn response
    ("IC-L2-09", "warn_response"): "L1-01:warn_response",
    # meta events(本 L2 自身元事件)
    ("IC-L2-05", "audit_rejected"): "L1-01:audit_rejected",
    ("IC-L2-05", "stale_buffer"): "L1-01:stale_buffer",
    ("IC-L2-05", "buffer_overflow"): "L1-01:buffer_overflow",
}


def resolve_event_type(source_ic: str, action: str) -> Optional[str]:
    """查白名单 · 返 event_type 或 None(unknown)."""
    return EVENT_TYPE_MAP.get((source_ic, action))


# =========================================================
# 核心 payload shape
# =========================================================


@dataclass(frozen=True)
class DecisionRecord:
    """L2-02 decision_made payload · 注入 IC-09 payload 的核心."""
    decision_id: str
    decision_type: str  # invoke_skill / dispatch_subagent / write_kb / halt / ...
    reason: str
    evidence: list[str] = field(default_factory=list)
    chosen_action: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ActionChosen:
    """L2-04 action_chosen payload."""
    action_type: str
    target_l1: str
    target_l2: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IcDispatched:
    """L2-04 ic_dispatched payload · IC-01/02/03/04/05/06 等."""
    ic_name: str  # IC-01 / IC-02 / ...
    direction: str  # send / recv
    target_l1: str
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None


# =========================================================
# record_audit() 入参
# =========================================================


@dataclass
class AuditCommand:
    """record_audit() 入参 · §3.1 · 4 种 source_ic 多态."""

    source_ic: str  # 一般是 SourceIC · but str 方便 TDD make_audit_cmd 传任意字符串
    actor: dict[str, Any]  # {"l1": "L1-01", "l2": "L2-01/02/..."}
    action: str
    project_id: Optional[str]
    reason: str
    evidence: list[str] = field(default_factory=list)
    linked_tick: Optional[str] = None
    linked_decision: Optional[str] = None
    linked_chain: Optional[str] = None
    linked_warn: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)
    ts: str = "1970-01-01T00:00:00Z"
    idempotency_key: Optional[str] = None


# =========================================================
# 内部聚合根(§2.2)· buffer / index 存储
# =========================================================


@dataclass
class AuditEntry:
    """I-05/06/07/08 invariants · buffer/index 存储单位.

    Note: 一旦 flush 到 IC-09 · 此 entry 应 frozen(buffer 阶段可追加 linked_*).
    测试断言会读 `.action / .linked_tick / .source_ic / .payload / .audit_id / .event_type` · 故非 frozen.
    hash / sequence / prev_hash 在 flush 时由 HashChainCalculator 填入.
    """

    audit_id: str
    source_ic: str
    actor: dict[str, Any]
    action: str
    event_type: str  # L1-01:xxx
    project_id: str
    reason: str
    evidence: list[str]
    payload: dict[str, Any]
    ts: str
    idempotency_key: Optional[str] = None
    linked_tick: Optional[str] = None
    linked_decision: Optional[str] = None
    linked_chain: Optional[str] = None
    linked_warn: Optional[str] = None
    # hash chain meta(flush 后填充)
    prev_hash: Optional[str] = None
    hash: Optional[str] = None
    sequence: Optional[int] = None
    event_id: Optional[str] = None
    # 本 L2 元字段(非落盘)
    error_code: Optional[str] = None  # 审计违规 / overflow 等元事件携带
    level: Optional[str] = None  # INFO / WARN / ERROR


# =========================================================
# 出参
# =========================================================


@dataclass(frozen=True)
class AuditResult:
    """record_audit() 出参 · §3.1."""

    audit_id: str
    buffered: bool
    buffer_remaining: int
    event_id: Optional[str] = None


@dataclass(frozen=True)
class FlushResult:
    """flush_buffer() 出参 · §3.4."""

    flushed_count: int
    last_event_id: Optional[str]
    last_hash: str  # "0"*64 (空) 或 sha256-hex
    duration_ms: int = 0


@dataclass(frozen=True)
class ReplayResult:
    """replay_from_jsonl() 出参 · §3.5."""

    replayed_count: int
    latest_hash: str
    files_scanned: int
    hash_chain_valid: bool
    first_broken_at: Optional[str] = None
    duration_ms: int = 0
    partial: bool = False


@dataclass(frozen=True)
class HashTip:
    """get_hash_tip() 出参 · §3.6."""

    hash: str  # genesis = "0"*64
    sequence: int = 0


@dataclass
class QueryResult:
    """query_by_tick / by_chain 出参 · §3.2 / §3.3."""

    entries: list[AuditEntry]
    source: str  # buffer | index | jsonl_scan | mixed | not_found
    count: int = 0
    query_duration_ms: int = 0
    partial: bool = False

    def __post_init__(self) -> None:
        # 自动计算 count(若未显式传)
        if self.count == 0 and self.entries:
            self.count = len(self.entries)


__all__ = [
    "SOURCE_IC_LITERALS",
    "SourceIC",
    "EVENT_TYPE_MAP",
    "resolve_event_type",
    "DecisionRecord",
    "ActionChosen",
    "IcDispatched",
    "AuditCommand",
    "AuditEntry",
    "AuditResult",
    "FlushResult",
    "ReplayResult",
    "HashTip",
    "QueryResult",
]
