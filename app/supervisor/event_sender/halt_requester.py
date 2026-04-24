"""IC-15 · HaltRequester · L1-07 → L1-01 · 阻塞式 · P99 ≤ 100ms 硬约束（HRL-05）。

**主会话仲裁**（2026-04-23 · §C-2）：
- IC-15 存在 · 必须实现（驳回 C-2 claim）
- 100ms 硬约束不可降级为 500ms
- `pytest-benchmark` 验证 P99 ≤ 100ms · 违反视为 release blocker

语义（§3.15）：
- 硬红线命中触发的硬暂停 · 阻塞式调用 · ≤100ms 内 L1-01 state=HALTED
- 必须用户 IC-17 authorize 才解 halt（require_user_authorization=true 硬编码）
- 与 IC-13 严格区分：IC-13 是建议（fire-and-forget）· IC-15 是命令（blocking）

幂等（§3.15.5）：
- key = red_line_id
- 同 red_line_id 重复命中只触发一次 halt · 返回首次 halt_id 的 ack

IC-09 审计：
- 成功：`L1-01:hard_halted`（halt_id, red_line_id, latency_ms, evidence）
- SLO 违反：`L1-07:halt_slo_violated`（HRL-05 告警 · release blocker 证据）
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    HardHaltState,
    RequestHardHaltAck,
    RequestHardHaltCommand,
)


class HardHaltTarget(Protocol):
    """L1-01 L2-06 Supervisor 接收 + L2-01 tick 调度协议。"""

    async def halt(self, halt_id: str, red_line_id: str) -> HardHaltState:
        """阻塞 halt tick · 返回 state_before。"""
        ...

    @property
    def current_state(self) -> HardHaltState: ...


@dataclass
class MockHardHaltTarget:
    """测试 target · 支持注入 slow_halt_ms（模拟 SLO 违反路径）。"""

    initial_state: HardHaltState = HardHaltState.RUNNING
    slow_halt_ms: int = 0
    _state: HardHaltState | None = None
    halt_call_count: int = 0
    halt_log: list[tuple[str, str]] = field(default_factory=list)

    @property
    def current_state(self) -> HardHaltState:
        if self._state is None:
            return self.initial_state
        return self._state

    async def halt(self, halt_id: str, red_line_id: str) -> HardHaltState:
        before = self.current_state
        self.halt_call_count += 1
        self.halt_log.append((halt_id, red_line_id))
        if self.slow_halt_ms > 0:
            # 同步阻塞 · 模拟 L1-01 tick abort 慢路径
            time.sleep(self.slow_halt_ms / 1000.0)
        self._state = HardHaltState.HALTED
        return before


@dataclass
class HaltRequester:
    """IC-15 request_hard_halt 实现 · 阻塞同步 · 100ms 硬约束。"""

    session_pid: str
    target: HardHaltTarget
    event_bus: EventBusStub

    # 幂等缓存 · key=red_line_id · val=首次 ack
    _idem_cache: dict[str, RequestHardHaltAck] = field(default_factory=dict)

    async def request_hard_halt(
        self, command: RequestHardHaltCommand
    ) -> RequestHardHaltAck:
        """阻塞式触发 L1-01 硬暂停 · 返回 halt_latency_ms ≤ 100ms（正常路径）。"""
        # 跨 project 拒绝（§3.15.4 E_HALT_NO_PROJECT_ID · 安全第一仍尝试 halt）
        # 主会话仲裁：硬红线最重 · pid 不一致时拒绝（不能跨 project 发 halt）
        if command.project_id != self.session_pid:
            raise ValueError(
                f"E_HALT_NO_PROJECT_ID: cross-project halt forbidden "
                f"{command.project_id} != {self.session_pid}"
            )

        # §3.15.5 幂等 by red_line_id
        cached = self._idem_cache.get(command.red_line_id)
        if cached is not None:
            # 仍返回 cached ack（halt_id 是首次那一条）
            return cached

        # 阻塞 · 测时延
        start_ns = time.perf_counter_ns()
        state_before = await self.target.halt(
            halt_id=command.halt_id, red_line_id=command.red_line_id
        )
        end_ns = time.perf_counter_ns()
        latency_ms = max(0, (end_ns - start_ns) // 1_000_000)

        # IC-09 审计（先 emit 获得 audit_entry_id）
        audit_entry_id = await self.event_bus.append_event(
            project_id=self.session_pid,
            type="L1-01:hard_halted",
            payload={
                "halt_id": command.halt_id,
                "red_line_id": command.red_line_id,
                "state_before": state_before.value,
                "state_after": HardHaltState.HALTED.value,
                "latency_ms": int(latency_ms),
                "require_user_authorization": command.require_user_authorization,
                "confirmation_count": command.evidence.confirmation_count,
            },
            evidence_refs=tuple(command.evidence.observation_refs),
        )

        ack = RequestHardHaltAck(
            halt_id=command.halt_id,
            halted=True,
            halt_latency_ms=int(latency_ms),
            state_before=state_before,
            state_after=HardHaltState.HALTED,
            audit_entry_id=audit_entry_id,
        )

        self._idem_cache[command.red_line_id] = ack

        # SLO 违反（HRL-05 告警 · release blocker 证据）
        if latency_ms > 100:
            await self.event_bus.append_event(
                project_id=self.session_pid,
                type="L1-07:halt_slo_violated",
                payload={
                    "halt_id": command.halt_id,
                    "red_line_id": command.red_line_id,
                    "latency_ms": int(latency_ms),
                    "slo_target_ms": 100,
                    "error_code": "E_HALT_SLO_VIOLATION",
                    "release_blocker": "HRL-05",
                },
                evidence_refs=tuple(command.evidence.observation_refs),
            )

        return ack


def _gen_audit_id() -> str:
    """本模块内部使用 · 未使用 event_bus.append 时的备用审计 id 生成。"""
    return f"audit-{uuid.uuid4().hex[:12]}"
