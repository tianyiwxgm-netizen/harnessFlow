"""L2-06 escalator · 死循环升级器 · 同级连 ≥ 3 failed 触发升级。

**主会话仲裁**：同级连 3 fail → ESCALATED · 实际动作走 IC-14 push_rollback_route
（升级到 UPGRADE_TO_L1-01 target_stage · 非 IC-13 L4）。

5 态机：ACTIVE → RETRY_1 → RETRY_2 → RETRY_3 → ESCALATED
- WP state DONE → counter reset · 回 ACTIVE
- dedup by wp_id · 同一 wp 一次升级只发 1 次 IC-14
  （参考 Dev-ε `RollbackCoordinator._escalated_wps`）
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class WpFailLevel(str, Enum):
    """升级层级。"""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"  # hard red-line / L1-01 升级


class EscalationState(str, Enum):
    """5 态机。"""

    ACTIVE = "ACTIVE"        # 初始 · 尚未失败
    RETRY_1 = "RETRY_1"      # 第 1 次失败后
    RETRY_2 = "RETRY_2"      # 第 2 次失败后
    RETRY_3 = "RETRY_3"      # 第 3 次失败后 · 下次 fail 升级
    ESCALATED = "ESCALATED"  # 已 ≥3 次 fail · 已升级（不重复发）


class WpFailEvent(BaseModel):
    """输入：一次 WP 失败事件。"""

    model_config = {"frozen": True}

    project_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)
    verdict_level: WpFailLevel
    verifier_report_id: str = Field(..., min_length=1)
    ts: str = Field(..., min_length=1)


class WpDoneEvent(BaseModel):
    """输入：一次 WP 成功完成事件 · 触发 counter reset。"""

    model_config = {"frozen": True}

    project_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)
    ts: str = Field(..., min_length=1)


class EscalationDecision(BaseModel):
    """EscalationLogic.decide 返回 · counter 推进结果 + 是否应升级。"""

    model_config = {"frozen": True}

    wp_id: str
    previous_state: EscalationState
    new_state: EscalationState
    should_escalate: bool
    fail_count: int
    dedup_hit: bool = False  # 同 wp 已升级过 · 本次被 dedup
