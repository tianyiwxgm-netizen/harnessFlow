"""L2-01 · PanicHandler · IC-17 user_panic → PAUSED ≤ 100ms。

对齐 3-1 tech §3.3 on_user_panic:
- 触发源: L1-09 事件总线订阅 user_panic 事件(L1-10 UI 发)
- SLO: ≤ 100ms state=PAUSED · 测 panic_latency_ms
- 幂等: 已 PAUSED 收 panic · 返回 ALREADY_PAUSED 错误(静默 · debug log)
- 只影响当前 session · 不跨 project

PanicSignal schema(WP04 简化版 · 只用 §3.3 核心字段):
- panic_id, project_id, user_id, ts (必填)
- scope: tick | session (default tick)
- reason: string | null

与 HaltEnforcer 协同:
- panic 调 enforcer.mark_panic() → state=PAUSED
- 不影响 HALTED 状态(HALTED 不可被降级)
- loop 主循环每 iter 先 assert_can_dispatch() 判 PAUSED + HALTED 都拒
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_PANIC_ALREADY_PAUSED,
    E_TICK_PANIC_NO_USER_ID,
    PANIC_SLO_MS,
    TickError,
)


class PanicSignal(BaseModel):
    """IC-17 user_panic envelope (WP04 · §3.3)。

    字段级约束对齐 tech §3.3:
    - panic_id: panic-{uuid} 格式
    - project_id: pid-... 格式
    - user_id: 必填 (不能"无主"panic)
    - scope: tick | session (default tick)
    """

    model_config = {"frozen": True}

    panic_id: str = Field(..., pattern=r"^panic-[A-Za-z0-9_-]{3,}$")
    project_id: str = Field(..., pattern=r"^pid-[A-Za-z0-9_-]{3,}$")
    user_id: str = Field(..., min_length=1)
    reason: str | None = None
    ts: str = Field(..., min_length=10)
    scope: Literal["tick", "session"] = "tick"


class PanicResult(BaseModel):
    """panic 返回结果(对 §3.3 出参)。"""

    model_config = {"frozen": True}

    paused: bool
    panic_latency_ms: int = Field(..., ge=0)
    slo_violated: bool
    panic_id: str
    scope: Literal["tick", "session"]


@dataclass
class PanicHandler:
    """IC-17 panic 处理器 · mark_panic + latency 测量。

    用法:
        handler = PanicHandler(project_id="pid-x", halt_enforcer=he)
        result = handler.handle(signal)  # sync · 无 await · ≤ 1us 翻态 · 内存操作

    - project_id:    PM-14 根字段 · cross-project panic 拒
    - halt_enforcer: 底层态机驱动(mark_panic / clear_panic)
    - slo_ms:        panic latency 硬上限 (default 100)
    """

    project_id: str
    halt_enforcer: HaltEnforcer
    slo_ms: int = PANIC_SLO_MS

    _panic_history: list[dict[str, Any]] = field(default_factory=list, init=False)
    _active_panic_id: str | None = field(default=None, init=False)
    _active_user_id: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id required (PM-14)")
        if self.slo_ms <= 0:
            raise ValueError(f"slo_ms must be positive · got {self.slo_ms}")

    def handle(self, signal: PanicSignal) -> PanicResult:
        """处理 panic 信号 · 返回 PanicResult。

        错误路径(§3.3.1):
        - E_TICK_CROSS_PROJECT:   signal.project_id ≠ bound project_id → 抛
        - E_TICK_PANIC_NO_USER_ID: schema 已强制(min_length=1) · 这里兜底
        - E_TICK_PANIC_ALREADY_PAUSED: 已 PAUSED · 抛(静默路径 caller 接)
        - E_TICK_PANIC_SLO_VIOLATION: latency > slo · PanicResult.slo_violated=true

        成功路径:
        - enforcer.mark_panic() · state → PAUSED
        - 返回 PanicResult(paused=true, latency_ms, slo_violated)
        """
        from app.main_loop.tick_scheduler.schemas import E_TICK_CROSS_PROJECT

        start_ns = time.perf_counter_ns()

        # PM-14 cross-project 拒
        if signal.project_id != self.project_id:
            raise TickError(
                error_code=E_TICK_CROSS_PROJECT,
                message=(
                    f"cross-project panic forbidden · "
                    f"bound={self.project_id!r} signal={signal.project_id!r}"
                ),
                project_id=signal.project_id,
            )

        if not signal.user_id:
            # 兜底 · schema 已强制
            raise TickError(
                error_code=E_TICK_PANIC_NO_USER_ID,
                message="user_id required",
                project_id=signal.project_id,
            )

        # 幂等 · 已 PAUSED 再 panic → ALREADY_PAUSED
        if self.halt_enforcer.as_tick_state().value == "PAUSED":
            raise TickError(
                error_code=E_TICK_PANIC_ALREADY_PAUSED,
                message="already paused · panic ignored",
                project_id=signal.project_id,
                context={"panic_id": signal.panic_id},
            )

        # HALTED 期间收 panic · 仍记 history 但不改 state (HALTED 不被降级)
        # 不抛错 · 因为 HALTED 是 panic 的超集 · 静默记录
        was_halted = self.halt_enforcer.is_halted()

        # 核心: 翻态 · 纯内存操作
        self.halt_enforcer.mark_panic()

        end_ns = time.perf_counter_ns()
        latency_ms = (end_ns - start_ns) // 1_000_000
        slo_violated = latency_ms > self.slo_ms

        # 不抛 SLO 违反 · 记 history 供审计 (与 HRL-05 一致 · paused=true 是硬保证)
        self._panic_history.append(
            {
                "panic_id": signal.panic_id,
                "user_id": signal.user_id,
                "reason": signal.reason,
                "scope": signal.scope,
                "was_halted": was_halted,
                "latency_ms": int(latency_ms),
                "slo_violated": slo_violated,
                "ts_ns": end_ns,
            }
        )
        self._active_panic_id = signal.panic_id
        self._active_user_id = signal.user_id

        return PanicResult(
            paused=True,
            panic_latency_ms=int(latency_ms),
            slo_violated=slo_violated,
            panic_id=signal.panic_id,
            scope=signal.scope,
        )

    def resume(self) -> None:
        """user 端 resume(IC-17 user_intervene · authorize) · clear_panic。"""
        self.halt_enforcer.clear_panic()
        self._active_panic_id = None
        self._active_user_id = None

    @property
    def panic_history(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._panic_history)

    @property
    def active_panic_id(self) -> str | None:
        return self._active_panic_id

    @property
    def active_user_id(self) -> str | None:
        return self._active_user_id


__all__ = ["PanicHandler", "PanicResult", "PanicSignal"]
