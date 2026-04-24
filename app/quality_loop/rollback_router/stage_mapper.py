"""`StageMapper` · severity + verdict + level_count → `RouteDecision`。

**常规映射**（对齐 Dev-ζ `rollback_pusher._LEGAL_MAPPING`）：

| verdict   | target_stage (常规) | new_wp_state       |
|:----------|:--------------------|:-------------------|
| FAIL_L1   | S3                  | retry_s3           |
| FAIL_L2   | S4                  | retry_s4           |
| FAIL_L3   | S5                  | retry_s5           |
| FAIL_L4   | UPGRADE_TO_L1_01    | upgraded_to_l1_01  |

**升级逻辑**：当 `level_count >= 3` · 任何 verdict 强制 override →
`UPGRADE_TO_L1_01` · 并标 `escalated=True`（供 executor / 审计识别）。

**硬约束**：阈值常量 `ESCALATION_THRESHOLD = 3` · 不从 config 读 · 防绕过
BF-E-10 死循环保护（对齐 3-1 L2-07 §6.7）。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    NewWpState,
    RollbackVerdict,
    RouteDecision,
    TargetStage,
)

# 硬常量 · 同级连续失败 ≥ 3 升级
ESCALATION_THRESHOLD: int = 3

# 常规 verdict → (target_stage, new_wp_state) 映射（Dev-ζ 合法集）
_NORMAL_MAPPING: dict[FailVerdict, tuple[TargetStage, NewWpState]] = {
    FailVerdict.FAIL_L1: (TargetStage.S3, NewWpState.RETRY_S3),
    FailVerdict.FAIL_L2: (TargetStage.S4, NewWpState.RETRY_S4),
    FailVerdict.FAIL_L3: (TargetStage.S5, NewWpState.RETRY_S5),
    FailVerdict.FAIL_L4: (
        TargetStage.UPGRADE_TO_L1_01, NewWpState.UPGRADED_TO_L1_01,
    ),
}

# 升级路径（≥ 3 次 · 任何 verdict 强制 override）
_ESCALATED_TARGET: tuple[TargetStage, NewWpState] = (
    TargetStage.UPGRADE_TO_L1_01, NewWpState.UPGRADED_TO_L1_01,
)


@dataclass(frozen=True)
class StageMapper:
    """纯决策函数的类包装 · severity+verdict → RouteDecision。

    无状态 · frozen · 可放心跨 route 共享。
    """

    def decide(self, *, rv: RollbackVerdict, route_id: str) -> RouteDecision:
        """接受分类后的 `RollbackVerdict` + `route_id`，产 `RouteDecision`。

        逻辑：
        1. level_count >= 3 → 升级路径（UPGRADE_TO_L1_01 · escalated=True）
        2. FAIL_L4 本身即升级语义 · `escalated=False`（非 "同级 >= 3" 触发）
        3. 其他 · 按 _NORMAL_MAPPING 常规映射 · `escalated=False`
        """
        # 升级路径优先：连续 >= 3 次同级失败 · 不论 verdict · 统一 UPGRADE
        if rv.level_count >= ESCALATION_THRESHOLD:
            target, new_state = _ESCALATED_TARGET
            return RouteDecision(
                target_stage=target,
                new_wp_state=new_state,
                severity=rv.severity,
                escalated=True,
                route_id=route_id,
                wp_id=rv.wp_id,
                project_id=rv.project_id,
                level_count=rv.level_count,
            )

        # 常规路径
        target, new_state = _NORMAL_MAPPING[rv.verdict]
        return RouteDecision(
            target_stage=target,
            new_wp_state=new_state,
            severity=rv.severity,
            escalated=False,  # FAIL_L4 首次 · 非 "同级 >= 3" · 不标 escalated
            route_id=route_id,
            wp_id=rv.wp_id,
            project_id=rv.project_id,
            level_count=rv.level_count,
        )
