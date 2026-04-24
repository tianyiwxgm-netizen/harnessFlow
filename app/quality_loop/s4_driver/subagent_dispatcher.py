"""L1-04 · L2-05 · S4 Driver · SubagentDispatcher（§2.6.4 · §6.9）.

**职责**：对 L1-05 invoke_skill 做 WP05 scope 封装：
  - mock 模式（本 WP 默认）· 直接返预定义 outcome 序列
  - real 模式（留 hook · main-2 接 Dev-γ 真实 invoke_skill）
  - 错误码按 §11 · SKILL_NOT_FOUND / SKILL_TIMEOUT / SKILL_BUDGET_EXHAUSTED
  - 返 SubagentInvokeResult · 错误包装（不抛 · 返 status=fail 让 driver 决策）

**为何不直接抛**（§3.4 输出契约）：
  orchestrator 通过 status 字段做 "success/partial/fail" 分支 ·
  否则每个 except 都得重复写 selfrepair_triggered 分支。

**mock 配置**：
  - `stub_plan: tuple[SubagentInvokeResult, ...]` · 按序弹出 · 耗尽后抛 INTERNAL_ASSERT
  - `fail_after_n: int` · 前 n 次 success · 之后全 fail（模拟 flaky skill）
  - `timeout_after_n: int` · 第 n 次触发 SKILL_TIMEOUT
"""

from __future__ import annotations

import itertools
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Callable, Protocol

from app.quality_loop.s4_driver.schemas import (
    INTERNAL_ASSERT,
    SKILL_BUDGET_EXHAUSTED,
    SKILL_INVOKE_FAIL,
    SKILL_NOT_FOUND,
    SKILL_TIMEOUT,
    DriverError,
    SubagentInvokeResult,
)


# ---------------------------------------------------------------------------
# 协议（真实 main-2 接 Dev-γ 需要实现这个）
# ---------------------------------------------------------------------------


class SkillBridge(Protocol):
    """L1-05 真实 invoke_skill 协议 · main-2 注入实现。"""

    def call(
        self,
        *,
        intent: str,
        context: dict,
        timeout_ms: int,
        budget_ms: int,
        budget_tokens: int,
    ) -> SubagentInvokeResult: ...


# ---------------------------------------------------------------------------
# Mock 实现（WP05 默认）
# ---------------------------------------------------------------------------


@dataclass
class MockSkillBridge:
    """WP05 默认 mock · 按 stub_plan 或规则返。

    **优先级**：
      1. 若 `stub_plan` 非空 · 逐一弹
      2. 否则按 `fail_after_n` / `timeout_after_n` 规则
      3. 默认 success

    **state**：`_count` 是已调用次数（observer 用）。
    """

    stub_plan: list[SubagentInvokeResult] = field(default_factory=list)
    fail_after_n: int | None = None
    timeout_after_n: int | None = None
    not_found_after_n: int | None = None
    budget_exhausted_after_n: int | None = None
    default_duration_ms: int = 100
    _count: int = 0

    def call(
        self,
        *,
        intent: str,
        context: dict,
        timeout_ms: int = 60_000,
        budget_ms: int = 60_000,
        budget_tokens: int = 30_000,
    ) -> SubagentInvokeResult:
        """Mock 调用 · 按 stub_plan / 规则 / 默认 返。"""
        self._count += 1
        n = self._count

        # 1) stub_plan 优先（逐一弹）
        if self.stub_plan:
            return self.stub_plan.pop(0)

        invoke_id = f"iv-{uuid.uuid4().hex[:12]}"

        # 2) 规则分支（按严重性从高到低）
        if self.not_found_after_n is not None and n >= self.not_found_after_n:
            return SubagentInvokeResult(
                invoke_id=invoke_id,
                skill_intent=intent,
                status="fail",
                error_code=SKILL_NOT_FOUND,
                error_message=f"skill intent {intent!r} not registered",
            )
        if self.timeout_after_n is not None and n >= self.timeout_after_n:
            return SubagentInvokeResult(
                invoke_id=invoke_id,
                skill_intent=intent,
                status="fail",
                duration_ms=timeout_ms,
                error_code=SKILL_TIMEOUT,
                error_message=f"skill {intent!r} timed out after {timeout_ms}ms",
            )
        if (
            self.budget_exhausted_after_n is not None
            and n >= self.budget_exhausted_after_n
        ):
            return SubagentInvokeResult(
                invoke_id=invoke_id,
                skill_intent=intent,
                status="fail",
                token_cost=budget_tokens,
                error_code=SKILL_BUDGET_EXHAUSTED,
                error_message=f"skill {intent!r} exhausted budget_tokens={budget_tokens}",
            )
        if self.fail_after_n is not None and n >= self.fail_after_n:
            return SubagentInvokeResult(
                invoke_id=invoke_id,
                skill_intent=intent,
                status="fail",
                duration_ms=self.default_duration_ms,
                error_code=SKILL_INVOKE_FAIL,
                error_message=f"skill {intent!r} returned failure",
            )

        # 3) 默认 success
        return SubagentInvokeResult(
            invoke_id=invoke_id,
            skill_intent=intent,
            status="success",
            duration_ms=self.default_duration_ms,
            token_cost=1000,
            output_summary=f"mock[{intent}] ok",
            artifacts_written=tuple(),
        )


# ---------------------------------------------------------------------------
# Dispatcher（§2.6.4 SkillInvoker）
# ---------------------------------------------------------------------------


class SubagentDispatcher:
    """§2.6.4 SkillInvoker · WP05 mock+real hook 双入口。

    - 构造注入 `bridge`（MockSkillBridge 默认 / 真实 L1-05 bridge）
    - `invoke(intent, context)` · 薄封装 · bridge.call → SubagentInvokeResult
    - 记录累计 `invoke_count` 供 driver 观测 · 不负责 retry（retry 在 driver 层）
    """

    def __init__(
        self,
        *,
        bridge: SkillBridge | None = None,
        default_timeout_ms: int = 60_000,
        default_budget_ms: int = 60_000,
        default_budget_tokens: int = 30_000,
    ) -> None:
        self._bridge = bridge or MockSkillBridge()
        self._default_timeout_ms = default_timeout_ms
        self._default_budget_ms = default_budget_ms
        self._default_budget_tokens = default_budget_tokens
        self.invoke_count = 0

    @property
    def bridge(self) -> SkillBridge:
        return self._bridge

    def invoke(
        self,
        *,
        intent: str,
        context: dict | None = None,
        timeout_ms: int | None = None,
        budget_ms: int | None = None,
        budget_tokens: int | None = None,
    ) -> SubagentInvokeResult:
        """§6.9 · 调 bridge.call · 返 SubagentInvokeResult（不抛 · 错误码走 status=fail）。

        **为何不抛异常**：
          - 3-1 §3.4 输出契约要求 status 字段可枚举
          - 让 driver 单点 switch（success → 继续 / fail → self-repair）
        """
        if not intent or not isinstance(intent, str):
            raise DriverError(
                INTERNAL_ASSERT,
                message="SubagentDispatcher.invoke requires non-empty str intent",
            )

        self.invoke_count += 1
        return self._bridge.call(
            intent=intent,
            context=context or {},
            timeout_ms=timeout_ms if timeout_ms is not None else self._default_timeout_ms,
            budget_ms=budget_ms if budget_ms is not None else self._default_budget_ms,
            budget_tokens=(
                budget_tokens if budget_tokens is not None else self._default_budget_tokens
            ),
        )


__all__ = [
    "SkillBridge",
    "MockSkillBridge",
    "SubagentDispatcher",
]
