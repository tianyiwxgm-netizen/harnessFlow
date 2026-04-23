"""L2-05 · 失败回退协调器。

职责：
- 维护 FailureCounter（每 wp_id 5 态机）
- 连续 3 次失败触发升级（IC-14 push_rollback_route 或 IC-15 request_hard_halt）
- 生成 RollbackAdvice（3 个选项：SPLIT_WP / MODIFY_WBS / MODIFY_AC）
- 标记 stuck（调 manager.mark_stuck · L2-02 IC-L2-06）
- 消费死锁信号（L2-03 dispatcher 发现 deadlock 时调 on_deadlock_notified）
"""

from app.l1_03.rollback.coordinator import RollbackCoordinator
from app.l1_03.rollback.escalator import Escalator, RollbackRoute
from app.l1_03.rollback.failure_counter import (
    FailureCounter,
    FailureCounterState,
)
from app.l1_03.rollback.schemas import (
    AdviceOption,
    FailureCounterSnapshot,
    RollbackAdvice,
)

__all__ = [
    "AdviceOption",
    "RollbackAdvice",
    "FailureCounterSnapshot",
    "FailureCounterState",
    "FailureCounter",
    "Escalator",
    "RollbackRoute",
    "RollbackCoordinator",
]
