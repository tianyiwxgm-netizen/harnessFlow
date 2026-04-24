"""L1-01 L2-02 Decision Engine · 数据契约.

对齐:
    - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md
      §3.1.1 decision_type × decision_params 表
      §7.2 DecisionRecord(本模块 ChosenAction 是其 WP03 精简投影)
    - WP03 范围 `decide(candidates, ctx) -> ChosenAction`

不可变约定:@dataclass(frozen=True)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# =========================================================
# decision_type 白名单(对齐 L2-02 §3.1.1 12 类)
# WP03 只实现 skill-class 决策;kb_read/kb_write 归 IC-06/07。
# =========================================================

DECISION_TYPES: frozenset[str] = frozenset({
    "invoke_skill",
    "use_tool",
    "delegate_subagent",
    "kb_read",
    "kb_write",
    "process_content",
    "request_user",
    "state_transition",
    "start_chain",
    "warn_response",
    "fill_discipline_gap",
    "no_op",
})


# =========================================================
# Candidate · 上游(Supervisor 或 规则引擎)传入候选
# =========================================================


@dataclass(frozen=True)
class Candidate:
    """候选决策项。

    Attributes:
        decision_type: §3.1.1 12 类之一。
        decision_params: 按 decision_type 形状(dict);本模块不 strict 校验各 type
                         的 params 子字段(留给 L2-03/L2-04 入口校验)。
        base_score: 规则引擎打分 ∈ [0.0, 1.0]。
        guard_expr: AST 白名单守卫表达式;True 才可选;空串 = 不守卫。
        reason: 候选生成理由 ≥ 10 字(决策 reason 拼接用)。
        kb_tags: 可选 KB tag 列表 · 参与 kb_booster 匹配。
    """
    decision_type: str
    decision_params: dict[str, Any] = field(default_factory=dict)
    base_score: float = 0.5
    guard_expr: str = ""
    reason: str = ""
    kb_tags: tuple[str, ...] = ()


# =========================================================
# HistoryEntry · 过往 ChosenAction 的回放形式(history_weighter 用)
# =========================================================


@dataclass(frozen=True)
class HistoryEntry:
    """历史决策条目(用于计算 history weight)。

    Attributes:
        decision_type: 同 Candidate。
        outcome: "success" | "fail" | "skip" | "unknown"。
        tick_delta: 相对当前 tick 的距离(越近权重越大)。
        params_fingerprint: 参数指纹(str),用于同类但不同 params 的区分。
    """
    decision_type: str
    outcome: str = "unknown"
    tick_delta: int = 1
    params_fingerprint: str = ""


# =========================================================
# KBSnippet · KBReadService 返回的条目精简投影(kb_booster 用)
# =========================================================


@dataclass(frozen=True)
class KBSnippet:
    """KB 读出片段。

    Attributes:
        kind: pattern / trap / recipe / tool_combo / anti_pattern / ...
        tags: 可匹配 Candidate.kb_tags 的标签;交集权重。
        rerank_score: 来自 KBReader 的 rerank_score ∈ [0.0, 1.0]。
        observed_count: 被观察次数(fallback 权重因子)。
    """
    kind: str = "pattern"
    tags: tuple[str, ...] = ()
    rerank_score: float = 0.0
    observed_count: int = 1


# =========================================================
# DecisionContext · decide() 入参上下文(L2-02 TickContext 的 WP03 精简投影)
# =========================================================


@dataclass(frozen=True)
class DecisionContext:
    """决策上下文。

    Attributes:
        project_id: PM-14 根字段 · 不能为空(Falsy → E_CTX_NO_PROJECT_ID)。
        tick_id: 用于审计 / 幂等。
        state: S0_init … S6_wrap。
        history: 过往 ChosenAction 列表(降序按时间)。
        kb_enabled: 是否启用 KB boost;False = 强制降级无 KB 模式。
        kb_snippets: 已由 KBReader 读出的条目(decide() 内部调用 kb_booster 匹配)。
        guard_vars: AST guard_expr 可读的变量命名空间(仅 Literal 值 · 不含函数)。
        fallback_candidate: 所有候选被否后的兜底(默认 no_op)。
    """
    project_id: str
    tick_id: str = ""
    state: str = "S0_init"
    history: tuple[HistoryEntry, ...] = ()
    kb_enabled: bool = True
    kb_snippets: tuple[KBSnippet, ...] = ()
    guard_vars: dict[str, Any] = field(default_factory=dict)
    fallback_candidate: Candidate | None = None


# =========================================================
# ChosenAction · decide() 出参(L2-02 DecisionRecord 的 WP03 精简投影)
# =========================================================


@dataclass(frozen=True)
class ChosenAction:
    """选定的决策。

    Attributes:
        decision_type: 12 类白名单之一。
        decision_params: 从 Candidate 透传。
        final_score: base_score + kb_boost + history_weight。
        kb_boost: 本次决策的 KB 加权(可能为 0;kb_enabled=False 时必为 0)。
        history_weight: 历史加权(连续成功正向 / 连续失败负向)。
        base_score: 源 Candidate 的 base_score(审计回放用)。
        reason: ≥ 20 字;拼接 Candidate.reason + 评分细节。
        kb_degraded: 是否启用了无 KB 模式(降级标记)。
        alternatives: top-3 候选(按 final_score 降序;不含被选中者);审计用。
    """
    decision_type: str
    decision_params: dict[str, Any]
    final_score: float
    kb_boost: float
    history_weight: float
    base_score: float
    reason: str
    kb_degraded: bool = False
    alternatives: tuple[tuple[str, float], ...] = ()


__all__ = [
    "DECISION_TYPES",
    "Candidate",
    "ChosenAction",
    "DecisionContext",
    "HistoryEntry",
    "KBSnippet",
]
