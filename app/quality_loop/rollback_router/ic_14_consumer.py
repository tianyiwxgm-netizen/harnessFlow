"""`IC14Consumer` · IC-14 消费入口 · 订阅 L1-07 → L2-07。

端到端链路（对齐 3-1 L2-07 §6.2 主算法的 Dev-ζ 对齐版）：

1. 幂等检查（by `route_id`）· 已处理过直接返回 cached ack
2. PM-14 校验（跨 project_id 拒绝 · 对齐 Dev-ζ `E_ROUTE_CROSS_PROJECT`）
3. `verdict_classifier`：verdict → severity + wrap `RollbackVerdict`
4. `stage_mapper`：`RollbackVerdict` → `RouteDecision`
5. 合法性交叉校验：`(verdict, decision.target_stage)` 必须在 Dev-ζ
   `_LEGAL_MAPPING` 合法集中 · 否则 `E_ROUTE_VERDICT_TARGET_MISMATCH`
6. `executor`：调 L1-02 state_transition（mock Dev-δ）· emit IC-09 审计
7. 组装 `PushRollbackRouteAck` · 写幂等缓存 · 返回

**独立性**：不改 Dev-ζ producer（`rollback_pusher.py`）· 只消费 · 保持 WP 独立。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.quality_loop.rollback_router.executor import (
    EventBusProtocol,
    RollbackExecutor,
    StateTransitionTarget,
)
from app.quality_loop.rollback_router.schemas import (
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    RouteDecision,
)
from app.quality_loop.rollback_router.stage_mapper import StageMapper
from app.quality_loop.rollback_router.verdict_classifier import VerdictClassifier
from app.supervisor.event_sender.rollback_pusher import _LEGAL_MAPPING


@dataclass
class IC14Consumer:
    """IC-14 消费端主类 · 组装 classifier + mapper + executor。

    - `session_pid`: 本 session 绑定的 project_id · PM-14 跨 pid 拒绝
    - `state_transition`: L1-02 IC-01 端点（mock Dev-δ）
    - `event_bus`: L1-09 IC-09 审计
    - `_idem_cache`: 幂等缓存 by route_id
    """

    session_pid: str
    state_transition: StateTransitionTarget
    event_bus: EventBusProtocol
    classifier: VerdictClassifier = field(default_factory=VerdictClassifier)
    mapper: StageMapper = field(default_factory=StageMapper)
    _executor: RollbackExecutor = field(init=False)
    _idem_cache: dict[str, PushRollbackRouteAck] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.session_pid or not self.session_pid.strip():
            raise ValueError("E_ROUTE_NO_PROJECT_ID: session_pid 必带（PM-14）")
        self._executor = RollbackExecutor(
            state_transition=self.state_transition,
            event_bus=self.event_bus,
            session_pid=self.session_pid,
        )

    async def consume(
        self, command: PushRollbackRouteCommand,
    ) -> PushRollbackRouteAck:
        """端到端消费一次 IC-14 command · 返回 ack（幂等）。"""
        # Step 1: 幂等检查
        cached = self._idem_cache.get(command.route_id)
        if cached is not None:
            return cached

        # Step 2: PM-14 校验
        if command.project_id != self.session_pid:
            raise ValueError(
                f"E_ROUTE_CROSS_PROJECT: {command.project_id} != {self.session_pid}"
            )

        # Step 3: 分类 verdict → severity + wrap
        rv = self.classifier.classify(
            verdict=command.verdict,
            wp_id=command.wp_id,
            project_id=command.project_id,
            level_count=command.level_count,
        )

        # Step 4: 映射 → RouteDecision
        decision: RouteDecision = self.mapper.decide(
            rv=rv, route_id=command.route_id,
        )

        # Step 5: 合法性交叉校验（对齐 Dev-ζ _LEGAL_MAPPING）
        # Dev-ζ 在 producer 侧校验 (command.verdict, command.target_stage)
        # 我们在 consumer 侧再校验一次 (command.verdict, decision.target_stage)：
        # 防止 mapper 未来调整漂移 · 守护 producer-consumer 双签的合法集。
        if (command.verdict, command.target_stage) not in _LEGAL_MAPPING:
            raise ValueError(
                f"E_ROUTE_VERDICT_TARGET_MISMATCH: "
                f"{command.verdict.value}→{command.target_stage.value}"
            )

        # Step 6: 执行
        await self._executor.execute(decision)

        # Step 7: 组装 ack + 写幂等缓存
        ack = PushRollbackRouteAck(
            route_id=command.route_id,
            applied=True,
            new_wp_state=decision.new_wp_state,
            escalated=decision.escalated,
            ts=command.ts,
        )
        self._idem_cache[command.route_id] = ack
        return ack

    # --- 审计 / 调试辅助 ---

    def is_processed(self, route_id: str) -> bool:
        """判断某 route_id 是否已被消费过（幂等命中检测）。"""
        return route_id in self._idem_cache

    def snapshot_cache(self) -> dict[str, Any]:
        """导出幂等缓存快照（供审计）。"""
        return {rid: ack.model_dump() for rid, ack in self._idem_cache.items()}
