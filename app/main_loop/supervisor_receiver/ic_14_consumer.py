"""`IC14Consumer`（receiver 侧）· IC-14 push_rollback_route 消费端。

**语义**：supervisor_receiver 对 IC-14 的最小职责是
"转发给 main-1 merged 的 `app.quality_loop.rollback_router.IC14Consumer`"。

为什么 L2-06 再套一层 thin wrapper（而不是 L1-07 直接调 quality_loop consumer）：
- 按 architecture §3.3 "单一 supervisor 接入点" · 所有 L1-07 出来的 IC 都必须走 L2-06
- L2-06 额外做：
  1. PM-14 校验（跨 pid 拒绝 · 在 quality_loop consumer 之前过滤）
  2. 包装 envelope `RollbackInbox`（records received_at_ms · 后续 queue snapshot / latency 度量用）
  3. 组装 `RollbackAck`（增补 `forwarded` / `idempotent_hit` · 便于 L2-02 pull 观测）
  4. IC-09 审计 `L1-01:rollback_route_received`

**独立性**：
- 不改 main-1 merged `quality_loop.rollback_router.IC14Consumer`
- 不改 Dev-ζ `rollback_pusher.py`
- 本类只做转发 + ack 增补

WP06 范围 = 最小转发 + 幂等观测 + 审计 · 完整 watchdog/queue snapshot 留给后续 WP。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.main_loop.supervisor_receiver.schemas import (
    RollbackAck,
    RollbackInbox,
)
from app.supervisor.event_sender.schemas import (
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
)


class QualityLoopRollbackTarget(Protocol):
    """main-1 merged `quality_loop.rollback_router.IC14Consumer` 协议。"""

    async def consume(
        self, command: PushRollbackRouteCommand
    ) -> PushRollbackRouteAck: ...

    def is_processed(self, route_id: str) -> bool: ...


class EventBusProtocol(Protocol):
    """L1-09 IC-09 append_event 协议。"""

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str: ...


@dataclass
class IC14Consumer:
    """receiver 侧 IC-14 thin wrapper · 转发 main-1 merged IC14Consumer。

    - `session_pid`: 本 session 绑定的 project_id · PM-14 跨 pid 拒绝
    - `downstream`: main-1 `quality_loop.rollback_router.IC14Consumer` 实例
    - `event_bus`: L1-09 IC-09 审计
    """

    session_pid: str
    downstream: QualityLoopRollbackTarget
    event_bus: EventBusProtocol

    # 本层 ack 缓存（用于观测 `idempotent_hit` · downstream 自己也有幂等缓存）
    _seen_route_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.session_pid or not self.session_pid.strip():
            raise ValueError("E_ROUTE_NO_PROJECT_ID: session_pid 必带（PM-14）")

    async def consume(self, inbox: RollbackInbox) -> RollbackAck:
        """转发 inbox.command → downstream · 组装 RollbackAck · emit 审计。"""
        cmd: PushRollbackRouteCommand = inbox.command

        # Step 1: PM-14 · 跨 pid 拒绝（在 downstream 之前过滤 · 保持 receiver 独立守护）
        if cmd.project_id != self.session_pid:
            raise ValueError(
                f"E_ROUTE_CROSS_PROJECT: {cmd.project_id} != {self.session_pid}"
            )

        # Step 2: 检测 receiver 层是否重复（downstream 自己的幂等为准）
        idem_hit = cmd.route_id in self._seen_route_ids

        # Step 3: 调 downstream（downstream 自带幂等缓存 · 重复推返回 cached ack）
        try:
            downstream_ack: PushRollbackRouteAck = await self.downstream.consume(cmd)
            forwarded = True
        except Exception as exc:
            # downstream 抛异常 · receiver 层记审计 · 向上抛（L1-07 能感知）
            await self.event_bus.append_event(
                project_id=self.session_pid,
                type="L1-01:rollback_route_failed",
                payload={
                    "route_id": cmd.route_id,
                    "wp_id": cmd.wp_id,
                    "error": str(exc),
                },
                evidence_refs=(cmd.evidence.verifier_report_id,),
            )
            raise

        # Step 4: IC-09 审计 · rollback_route_received
        await self.event_bus.append_event(
            project_id=self.session_pid,
            type="L1-01:rollback_route_received",
            payload={
                "route_id": cmd.route_id,
                "wp_id": cmd.wp_id,
                "verdict": cmd.verdict.value,
                "target_stage": cmd.target_stage.value,
                "new_wp_state": downstream_ack.new_wp_state.value,
                "escalated": downstream_ack.escalated,
                "idempotent_hit": idem_hit,
                "received_at_ms": inbox.received_at_ms,
            },
            evidence_refs=(cmd.evidence.verifier_report_id,),
        )

        # Step 5: 记录见过 · 用于本层 idempotent_hit 观测
        self._seen_route_ids.add(cmd.route_id)

        # Step 6: 组装 receiver 侧 ack（比 downstream ack 多 `forwarded` / `idempotent_hit`）
        return RollbackAck(
            route_id=cmd.route_id,
            forwarded=forwarded,
            idempotent_hit=idem_hit,
            target_new_state=downstream_ack.new_wp_state.value,
        )

    # --- 辅助 ---

    def is_forwarded(self, route_id: str) -> bool:
        """判断 receiver 是否转发过某 route_id。"""
        return route_id in self._seen_route_ids
