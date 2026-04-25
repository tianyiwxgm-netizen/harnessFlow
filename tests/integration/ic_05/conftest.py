"""IC-05 集成测试 fixtures · 真实 Delegator + ResourceLimiter + 假 SDK adapter.

铁律:
    - 真实 import L1-05 subagent 模块 (delegator/limiter/schemas)
    - SDK adapter 是边界 · 用 fake 不调真 anthropic API
    - event_bus 用 in-memory 假实现 (验证 emit_safe 调用)
    - tests/shared 共用 fixtures (project_id / tmp_root)
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from app.skill_dispatch.subagent.claude_sdk_client import (
    ClaudeSDKClient,
    SpawnFailedError,
    SubagentTimeoutError,
)
from app.skill_dispatch.subagent.delegator import Delegator
from app.skill_dispatch.subagent.resource_limiter import ResourceLimiter


class FakeBus:
    """In-memory event bus · append_event 收 (project_id, l1, event_type, payload)."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def append_event(
        self, *, project_id: str, l1: str, event_type: str, payload: dict[str, Any],
    ) -> None:
        self.events.append({
            "project_id": project_id,
            "l1": l1,
            "event_type": event_type,
            "payload": dict(payload),
        })

    def by_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e["event_type"] == event_type]


class FakeAdapter:
    """SDK adapter 替身 · 控制 spawn / await_result 行为.

    可注入:
        spawn_factory: Callable[[role], str] · 默认返 "sub-{n}".
        spawn_fail_first_n: 前 N 次 spawn 抛 SpawnFailedError (重试覆盖).
        result_factory: Callable[[session_id], dict] · 默认 {"artifacts": []}.
        result_timeout: bool · True 则 await_result 抛 SubagentTimeoutError.
    """

    def __init__(self) -> None:
        self.spawn_calls: list[dict[str, Any]] = []
        self.spawn_factory: Callable[[str], str] | None = None
        self.spawn_fail_first_n: int = 0
        self._spawn_attempts: int = 0
        self.result_factory: Callable[[str], dict[str, Any]] | None = None
        self.result_timeout: bool = False
        self.result_exception: Exception | None = None
        self.terminate_calls: list[tuple[str, bool]] = []

    async def spawn_session(
        self,
        *,
        role: str,
        allowed_tools: list[str],
        context: dict[str, Any],
        timeout_s: int,
    ) -> str:
        self.spawn_calls.append({
            "role": role,
            "allowed_tools": list(allowed_tools),
            "context": dict(context),
            "timeout_s": timeout_s,
        })
        self._spawn_attempts += 1
        if self._spawn_attempts <= self.spawn_fail_first_n:
            raise SpawnFailedError(
                f"E_SUB_SPAWN_FAILED: attempt={self._spawn_attempts}",
            )
        if self.spawn_factory is not None:
            return self.spawn_factory(role)
        return f"sub-{self._spawn_attempts}"

    async def await_result(self, session_id: str, timeout_s: float) -> dict[str, Any]:
        if self.result_timeout:
            raise SubagentTimeoutError("E_SUB_TIMEOUT: forced")
        if self.result_exception is not None:
            raise self.result_exception
        if self.result_factory is not None:
            return self.result_factory(session_id)
        return {"artifacts": [], "final_message": "ok"}

    async def terminate(self, session_id: str, *, force: bool = False) -> None:
        self.terminate_calls.append((session_id, force))


@pytest.fixture
def project_id() -> str:
    """IC-05 默认 pid · 与 ic-contracts.md PM-14 一致."""
    return "proj-ic05"


@pytest.fixture
def fake_bus() -> FakeBus:
    return FakeBus()


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def sdk_client(fake_adapter: FakeAdapter) -> ClaudeSDKClient:
    return ClaudeSDKClient(fake_adapter, sigterm_grace_s=0.01)


@pytest.fixture
def limiter() -> ResourceLimiter:
    """IC-05 默认 capacity · 3 + 10 = 13 槽."""
    return ResourceLimiter(max_concurrent=3, max_queue=10)


@pytest.fixture
def delegator(
    sdk_client: ClaudeSDKClient,
    limiter: ResourceLimiter,
    fake_bus: FakeBus,
) -> Delegator:
    return Delegator(sdk_client=sdk_client, limiter=limiter, event_bus=fake_bus)


@pytest.fixture
def task_brief() -> str:
    """50+ 字 · 满足 schema 校验."""
    return (
        "Please research the literature on async subagent dispatch patterns "
        "and produce a brief comparison; coverage at least 5 references."
    )


@pytest.fixture
def make_request(project_id: str, task_brief: str):
    """工厂 · 一行造合法 IC-05 DelegationRequest."""
    from app.skill_dispatch.subagent.schemas import DelegationRequest

    def _make(
        *,
        delegation_id: str = "del-ic05-default",
        role: str = "researcher",
        caller_l1: str = "L1-04",
        timeout_s: int = 60,
        ctx_extra: dict[str, Any] | None = None,
        allowed_tools: list[str] | None = None,
        pid_override: str | None = None,
    ) -> DelegationRequest:
        ctx: dict[str, Any] = {"project_id": pid_override or project_id}
        if ctx_extra:
            ctx.update(ctx_extra)
        return DelegationRequest(
            delegation_id=delegation_id,
            project_id=pid_override or project_id,
            role=role,
            task_brief=task_brief,
            context_copy=ctx,
            caller_l1=caller_l1,
            allowed_tools=allowed_tools or ["Read", "Glob", "Grep", "Bash"],
            timeout_s=timeout_s,
        )

    return _make


def run_async(coro: Any) -> Any:
    """同步壳 · 跑 asyncio coroutine 到完成."""
    return asyncio.run(coro)
