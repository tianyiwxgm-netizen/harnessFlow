"""L2-04 · WP 完成度追踪器。

职责：
- 订阅 IC-09 事件总线（L1-04 广播的 wp_done / wp_failed）
- 申请状态跃迁（调 manager.transition_state RUNNING→DONE/FAILED）
- 4 项聚合指标：completion_rate / remaining_effort / done_wps / running_wps
- 失败时通过 Protocol 转发给 L2-05（WP05 实现）
- 发 L1-03:progress_metrics_updated 事件到 IC-09
"""

from app.l1_03.progress.burndown import compute_burndown
from app.l1_03.progress.event_subscriber import (
    ProgressEventSubscriber,
    WPCompletionEvent,
    WPFailureEvent,
)
from app.l1_03.progress.schemas import BurndownPoint, ProgressSnapshot
from app.l1_03.progress.tracker import (
    ProgressTracker,
    RollbackCoordinatorProtocol,
)

__all__ = [
    "ProgressSnapshot",
    "BurndownPoint",
    "compute_burndown",
    "ProgressEventSubscriber",
    "WPCompletionEvent",
    "WPFailureEvent",
    "ProgressTracker",
    "RollbackCoordinatorProtocol",
]
