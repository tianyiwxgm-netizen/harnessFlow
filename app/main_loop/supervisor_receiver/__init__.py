"""L1-01 L2-06 · Supervisor 建议接收器。

**唯一 supervisor 网关**（architecture.md §3.3 "单一 supervisor 接入点"），消费 Dev-ζ 的 3 条 IC：
- IC-13 push_suggestion → SuggestionInbox · 软决策候选（INFO/SUGG/WARN）
- IC-14 push_rollback_route → RollbackRouteInbox · 触发 main-1 L1-04 L2-07 rollback
- IC-15 request_hard_halt → HaltSignal · **Sync ≤ 100ms 硬约束**（HRL-05）

外部入口：`SupervisorReceiver`（`receiver.py`）。内部消费器：
- `ic_13_consumer.IC13Consumer` · 软建议队列
- `ic_14_consumer.IC14Consumer` · rollback 派发
- `ic_15_consumer.IC15Consumer` · halt 阻塞式 · 100ms bench
"""
from app.main_loop.supervisor_receiver.receiver import (
    SupervisorReceiver,
)
from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    HaltAck,
    HaltSignal,
    HaltState,
    RollbackAck,
    RollbackInbox,
    SuggestionAck,
    SuggestionInbox,
)

__all__ = [
    "AdviceLevel",
    "HaltAck",
    "HaltSignal",
    "HaltState",
    "RollbackAck",
    "RollbackInbox",
    "SuggestionAck",
    "SuggestionInbox",
    "SupervisorReceiver",
]
