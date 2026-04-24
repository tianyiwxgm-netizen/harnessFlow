"""L2-05 · Soft-drift 模式识别器 · schemas · 8 类 trap + 60 tick 滑窗。

Brief §5 简化版 8 种模式：
- SDP-01 gate_overrun · Gate 过度让步（≥ 3 次 TOLERATED）
- SDP-02 wp_loop · WP 循环反复（fail_count ≥ 3）
- SDP-03 skill_fallback · Skill fallback 过度
- SDP-04 kb_miss · KB 命中率骤降（< 30%）
- SDP-05 audit_tail · Audit 写入 P95 > 20ms
- SDP-06 ui_panic · UI panic 频发（24h ≥ 3）
- SDP-07 verifier_reject · Verifier 连续拒绝（≥ 3）
- SDP-08 state_reverse · 状态机逆转回撤

匹配 → IC-13 push_suggestion level=WARN。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TrapPatternId(str, Enum):
    """8 类 trap 编号。"""

    SDP_01_GATE_OVERRUN = "SDP-01"
    SDP_02_WP_LOOP = "SDP-02"
    SDP_03_SKILL_FALLBACK = "SDP-03"
    SDP_04_KB_MISS = "SDP-04"
    SDP_05_AUDIT_TAIL = "SDP-05"
    SDP_06_UI_PANIC = "SDP-06"
    SDP_07_VERIFIER_REJECT = "SDP-07"
    SDP_08_STATE_REVERSE = "SDP-08"


class Tick(BaseModel):
    """单 tick 的滑窗输入 · 8 维指标子集 + tick_seq。

    window_stats.py 以 Tick 聚合 · matcher 对 Tick 序列模式匹配。
    """

    model_config = {"frozen": True}

    tick_seq: int = Field(..., ge=0)
    project_id: str = Field(..., min_length=1)
    captured_at_ms: int = Field(..., ge=0)
    # 关注指标（任何 None 表示本 tick 该维缺）
    gate_verdict: str | None = None       # "PASS" / "TOLERATED" / "FAIL"
    wp_state: str | None = None            # "RETRY_1" / "RETRY_3" / "ESCALATED" / "DONE"
    wp_fail_count: int | None = None
    skill_fallback_count: int | None = None  # 本 tick 内 fallback 次数
    kb_hit_rate: float | None = None         # 0.0-1.0
    audit_p95_ms: int | None = None
    ui_panic_count: int | None = None
    verifier_verdict: str | None = None      # "PASS" / "REJECT"
    state_seq: str | None = None             # 状态机当前 label（用于检测逆转）


class TrapMatch(BaseModel):
    """命中 · matcher 输出。"""

    model_config = {"frozen": True}

    project_id: str = Field(..., min_length=1)
    pattern_id: TrapPatternId
    reason: str = Field(..., min_length=1)
    evidence_tick_seqs: tuple[int, ...] = Field(..., min_length=1)
    first_tick_seq: int
    last_tick_seq: int
    severity: str = "WARN"  # 固定 WARN（SDP 不升级 CRITICAL · 硬升级归 L2-06）
    match_id: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_SDP_NO_PROJECT_ID")
        return v


class WindowStats(BaseModel):
    """60-tick 滑窗聚合统计。"""

    model_config = {"frozen": True}

    project_id: str
    window_size: int = 60
    tick_count: int = Field(..., ge=0)
    first_tick_seq: int | None = None
    last_tick_seq: int | None = None
    # 各类聚合 · pattern matcher 用
    gate_tolerated_count: int = 0
    wp_fail_max: int = 0
    skill_fallback_total: int = 0
    kb_hit_rate_avg: float | None = None
    audit_p95_max: int = 0
    ui_panic_total: int = 0
    verifier_reject_streak: int = 0  # 最新连续 reject 次数
    state_reverse_count: int = 0
