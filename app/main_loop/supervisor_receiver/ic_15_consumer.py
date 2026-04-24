"""`IC15Consumer` · IC-15 request_hard_halt 消费端 · **Sync ≤ 100ms · HRL-05 铁律**。

**硬约束**（主会话仲裁 2026-04-23-Dev-ζ §C-2 + arch §3.5 D-05）：
- halt 端到端（receiver.consume → halt_target.halt 完成 → ack 返回）≤ 100ms
- P99 由 pytest-benchmark 强校验 · 违反视为 release blocker
- 硬编码 `require_user_authorization=true`（schema 已保证）· 只能 IC-17 user_intervene(authorize) 清除

端到端链路（对齐 3-1 L2-06 §3.2 broadcast_block）：

1. PM-14 校验（跨 pid 拒绝 · 安全第一不降级）
2. 证据校验：observation_refs ≥ 1 + confirmation_count ≥ 2（schema 已强制 · 此处快速路径）
3. 幂等 by `red_line_id`（同 red_line_id 已 active · 返回 cached ack）
4. 调 `halt_target.halt()` 阻塞执行（L2-01 / L1-01 tick 调度器）
5. 测 latency_ms · > 100 · 标 slo_violated=true · emit HRL-05 审计
6. IC-09 审计 `L1-01:hard_halted`
7. 组装 `HaltAck` 返回

**独立性**：
- 不改 Dev-ζ `halt_requester.py`（producer）
- consume 的是 `HaltSignal`（receiver envelope · wrap `RequestHardHaltCommand`）
- 使用 `time.perf_counter_ns()` 精度 ≥ 微秒 · 100ms 判定可靠
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.main_loop.supervisor_receiver.schemas import (
    HaltAck,
    HaltSignal,
    HaltState,
)
from app.supervisor.event_sender.schemas import (
    HardHaltState,
)

# 硬约束：100ms P99 · HRL-05
HALT_SLO_MS: int = 100


class HaltTargetProtocol(Protocol):
    """L2-01 tick 调度器协议（L1-01 halt 入口）。"""

    async def halt(self, halt_id: str, red_line_id: str) -> HardHaltState:
        """阻塞执行 halt · 返回 state_before。"""
        ...

    @property
    def current_state(self) -> HardHaltState: ...


class EventBusProtocol(Protocol):
    async def append_event(
        self,
        *,
        project_id: str,
        type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str: ...


@dataclass
class IC15Consumer:
    """IC-15 消费端主类 · Sync ≤ 100ms 硬约束。

    - `session_pid`: PM-14 · 跨 pid 拒绝
    - `halt_target`: L2-01 halt 目标
    - `event_bus`: L1-09 IC-09 审计
    - `slo_ms`: 默认 100 · HRL-05 不应被调高（仅测试时可调低验证 slo_violated 路径）
    """

    session_pid: str
    halt_target: HaltTargetProtocol
    event_bus: EventBusProtocol
    slo_ms: int = HALT_SLO_MS

    # 幂等 by red_line_id（同 red_line_id 重复命中返回首次 ack）
    _idem_cache: dict[str, HaltAck] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.session_pid or not self.session_pid.strip():
            raise ValueError("E_HALT_NO_PROJECT_ID: session_pid 必带（PM-14）")
        if self.slo_ms <= 0:
            raise ValueError("slo_ms must be positive")

    async def consume(self, signal: HaltSignal) -> HaltAck:
        """阻塞式消费 IC-15 · 返回 HaltAck（含 latency_ms · slo_violated 标志）。"""
        cmd = signal.command

        # Step 1: PM-14 · 跨 pid 拒绝（安全第一 · 不降级）
        if cmd.project_id != self.session_pid:
            raise ValueError(
                f"E_HALT_NO_PROJECT_ID: cross-project halt forbidden "
                f"{cmd.project_id} != {self.session_pid}"
            )

        # Step 2: 证据 schema 已保证（confirmation_count ≥ 2 · observation_refs ≥ 1）
        #         require_user_authorization=true 已在 schema validator 强制

        # Step 3: 幂等 by red_line_id
        cached = self._idem_cache.get(cmd.red_line_id)
        if cached is not None:
            # 仍返回 cached · idempotent_hit=true
            return HaltAck(
                halt_id=cached.halt_id,
                halted=cached.halted,
                latency_ms=cached.latency_ms,
                state_before=cached.state_before,
                state_after=cached.state_after,
                slo_violated=cached.slo_violated,
                idempotent_hit=True,
            )

        # Step 4: 执行 halt · 测时延（perf_counter_ns 精度足够）
        state_before_halt: HardHaltState = self.halt_target.current_state
        start_ns = time.perf_counter_ns()
        before_reported = await self.halt_target.halt(
            halt_id=cmd.halt_id, red_line_id=cmd.red_line_id
        )
        end_ns = time.perf_counter_ns()
        latency_ms = max(0, (end_ns - start_ns) // 1_000_000)

        # 采用 halt_target 返回的 state_before（更权威 · 避免 current_state race）
        state_before = before_reported if before_reported is not None else state_before_halt

        slo_violated = latency_ms > self.slo_ms

        # Step 5: IC-09 审计 · hard_halted
        await self.event_bus.append_event(
            project_id=self.session_pid,
            type="L1-01:hard_halted",
            payload={
                "halt_id": cmd.halt_id,
                "red_line_id": cmd.red_line_id,
                "state_before": state_before.value,
                "state_after": HardHaltState.HALTED.value,
                "latency_ms": int(latency_ms),
                "slo_violated": slo_violated,
                "confirmation_count": cmd.evidence.confirmation_count,
                "require_user_authorization": cmd.require_user_authorization,
            },
            evidence_refs=tuple(cmd.evidence.observation_refs),
        )

        # Step 6: SLO 违反 · HRL-05 告警（release blocker 证据）
        if slo_violated:
            await self.event_bus.append_event(
                project_id=self.session_pid,
                type="L1-07:halt_slo_violated",
                payload={
                    "halt_id": cmd.halt_id,
                    "red_line_id": cmd.red_line_id,
                    "latency_ms": int(latency_ms),
                    "slo_target_ms": self.slo_ms,
                    "error_code": "E_HALT_SLO_VIOLATION",
                    "release_blocker": "HRL-05",
                },
                evidence_refs=tuple(cmd.evidence.observation_refs),
            )

        # Step 7: 组装 ack · 缓存（idempotent_hit 在 cached 分支单独置 true）
        ack = HaltAck(
            halt_id=cmd.halt_id,
            halted=True,
            latency_ms=int(latency_ms),
            state_before=_to_receiver_state(state_before),
            state_after=HaltState.HALTED,
            slo_violated=slo_violated,
            idempotent_hit=False,
        )
        self._idem_cache[cmd.red_line_id] = ack
        return ack

    # --- 辅助 ---

    def is_halted(self, red_line_id: str) -> bool:
        """判断某 red_line_id 是否已触发 halt（幂等命中检测）。"""
        return red_line_id in self._idem_cache


def _to_receiver_state(state: HardHaltState) -> HaltState:
    """Dev-ζ `HardHaltState` → receiver `HaltState`（两 enum value 一致 · 1:1 映射）。"""
    return HaltState(state.value)
