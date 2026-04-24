"""L1-01 L2-06 · Supervisor 建议接收器 · **唯一 supervisor 入口网关**。

architecture.md §3.3 "单一 supervisor 接入点" · 3 条 IC 全部从这里进：
- IC-13 push_suggestion  → `consume_suggestion(signal) → SuggestionAck`
- IC-14 push_rollback_route → `consume_rollback(signal) → RollbackAck`
- IC-15 request_hard_halt → `consume_halt(signal) → HaltAck`（Sync ≤ 100ms · HRL-05）

**组装策略**：
- 3 个 consumer 各自独立组装 · receiver 只做 thin dispatch
- `session_pid` + `event_bus` 由 receiver 统一注入 3 个 consumer
- `halt_target` / `rollback_downstream` 由外部传入（DI · 便于测试 + 灵活替换）

WP06 范围 = 最小网关 · 满足 "3 个 consume 方法 + 统一注入"。
后续 WP 扩展：AdviceQueue aggregate / watchdog / clear_block / 4 级 counter。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.main_loop.supervisor_receiver.ic_13_consumer import (
    EventBusProtocol,
    IC13Consumer,
)
from app.main_loop.supervisor_receiver.ic_14_consumer import (
    IC14Consumer as Receiver_IC14Consumer,
)
from app.main_loop.supervisor_receiver.ic_14_consumer import (
    QualityLoopRollbackTarget,
)
from app.main_loop.supervisor_receiver.ic_15_consumer import (
    HaltTargetProtocol,
    IC15Consumer,
)
from app.main_loop.supervisor_receiver.schemas import (
    HaltAck,
    HaltSignal,
    RollbackAck,
    RollbackInbox,
    SuggestionAck,
    SuggestionInbox,
)


@dataclass
class SupervisorReceiver:
    """L1-01 L2-06 唯一 supervisor 网关 · 3 个 IC consume 入口。

    构造参数：
    - `session_pid`: 本 session 绑定的 project_id · PM-14 统一注入
    - `event_bus`: L1-09 IC-09 审计端点 · 统一注入
    - `halt_target`: L2-01 halt 目标（IC-15 消费必需）
    - `rollback_downstream`: main-1 merged `quality_loop.rollback_router.IC14Consumer` 实例
    - `halt_slo_ms`: IC-15 SLO · 默认 100 · 生产环境不得调高（HRL-05）

    内部 consumer 在 `__post_init__` 组装完成 · 对外仅 3 个 consume 方法。
    """

    session_pid: str
    event_bus: EventBusProtocol
    halt_target: HaltTargetProtocol
    rollback_downstream: QualityLoopRollbackTarget
    halt_slo_ms: int = 100

    _ic13: IC13Consumer = field(init=False)
    _ic14: Receiver_IC14Consumer = field(init=False)
    _ic15: IC15Consumer = field(init=False)

    def __post_init__(self) -> None:
        if not self.session_pid or not self.session_pid.strip():
            raise ValueError("E_SUP_NO_PROJECT_ID: session_pid 必带（PM-14）")
        self._ic13 = IC13Consumer(
            session_pid=self.session_pid, event_bus=self.event_bus
        )
        self._ic14 = Receiver_IC14Consumer(
            session_pid=self.session_pid,
            downstream=self.rollback_downstream,
            event_bus=self.event_bus,
        )
        self._ic15 = IC15Consumer(
            session_pid=self.session_pid,
            halt_target=self.halt_target,
            event_bus=self.event_bus,
            slo_ms=self.halt_slo_ms,
        )

    # --- 对外 3 个 consume 方法 ---

    async def consume_suggestion(self, signal: SuggestionInbox) -> SuggestionAck:
        """IC-13 push_suggestion 消费入口 · 分级入 INFO/SUGG/WARN 队列。"""
        return await self._ic13.consume(signal)

    async def consume_rollback(self, signal: RollbackInbox) -> RollbackAck:
        """IC-14 push_rollback_route 消费入口 · 转发 main-1 merged IC14Consumer。"""
        return await self._ic14.consume(signal)

    async def consume_halt(self, signal: HaltSignal) -> HaltAck:
        """IC-15 request_hard_halt 消费入口 · **Sync ≤ 100ms · HRL-05 铁律**。"""
        return await self._ic15.consume(signal)

    # --- 观测 / 调试辅助（供 L2-02 pull + L1-07 健康监测） ---

    def queue_depth(self, level: Any) -> int:
        """返回指定 level（AdviceLevel）queue 深度。"""
        return self._ic13.queue_depth(level)

    def counter_snapshot(self) -> dict[str, int]:
        """3 级 suggestion counter 快照（单调递增）。"""
        return self._ic13.counter_snapshot()

    def is_halted(self, red_line_id: str) -> bool:
        """某 red_line_id 是否已触发 halt。"""
        return self._ic15.is_halted(red_line_id)

    def is_rollback_forwarded(self, route_id: str) -> bool:
        """某 route_id 是否已通过 receiver 转发到 quality_loop。"""
        return self._ic14.is_forwarded(route_id)
