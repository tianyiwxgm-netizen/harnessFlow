"""`VerdictClassifier` · verdict → 4 级 severity 映射。

对齐 task spec §职责 的 4 级回退：
- L1 `INFO_SUGG` ← 本 IC-14 消费端**不产**（不走 IC-14 · 仅枚举保留）
- L2 `WARN`     ← `FAIL_L1` · stage 内 retry 当前 WP
- L3 `FAIL`     ← `FAIL_L2` / `FAIL_L3` · 中度回退（回退到上一 stage）
- L4 `CRITICAL` ← `FAIL_L4` · 深度回退（回 S1/S2 · 重新 Planning）

**对齐 3-1 L2-07 §6.3**：严格按 Dev-ζ `FailVerdict` 4 值枚举分级。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    RollbackSeverity,
    RollbackVerdict,
)

# 严格映射表（常量 · 不从 config 读）· 严禁漂移
_VERDICT_TO_SEVERITY: dict[FailVerdict, RollbackSeverity] = {
    FailVerdict.FAIL_L1: RollbackSeverity.WARN,      # L2
    FailVerdict.FAIL_L2: RollbackSeverity.FAIL,      # L3
    FailVerdict.FAIL_L3: RollbackSeverity.FAIL,      # L3
    FailVerdict.FAIL_L4: RollbackSeverity.CRITICAL,  # L4
}


def classify_verdict(verdict: FailVerdict) -> RollbackSeverity:
    """纯函数 · verdict → severity 查表。

    Raises:
        KeyError: 理论不会发生（Dev-ζ enum 4 值全覆盖 · 此检测守护未来漂移）
    """
    return _VERDICT_TO_SEVERITY[verdict]


@dataclass(frozen=True)
class VerdictClassifier:
    """类包装 · 接受 `PushRollbackRouteCommand` 字段 → 产 `RollbackVerdict`。

    frozen 保证无状态（分类器本身是纯函数）· 便于依赖注入 + 测试。
    """

    def classify(
        self,
        *,
        verdict: FailVerdict,
        wp_id: str,
        project_id: str,
        level_count: int,
    ) -> RollbackVerdict:
        """包装成内部 `RollbackVerdict`（Pydantic frozen model）。

        wp_id / project_id / level_count 由上游 IC-14 消费入口透传。
        """
        severity = classify_verdict(verdict)
        return RollbackVerdict(
            verdict=verdict,
            severity=severity,
            wp_id=wp_id,
            project_id=project_id,
            level_count=level_count,
        )
