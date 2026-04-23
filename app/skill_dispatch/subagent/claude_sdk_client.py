"""L2-04 ClaudeSDKClient · Claude Agent SDK 封装 · adapter pattern.

分层:
  SDKAdapter (protocol)          — 抽象接口 · spawn/await_result/terminate
    ├── AnthropicSDKAdapter      — 真实 Claude Agent SDK 适配 (TODO · 装 anthropic 后实现)
    └── (测试用 fake adapter)    — tests/skill_dispatch/test_l2_04 里实现

ClaudeSDKClient (本模块)
  - spawn(role, allowed_tools, context, timeout_s) → session_id
    - 失败 retry 1 次 · 二次失败 → E_SUB_SPAWN_FAILED
  - await_result(session_id, timeout_s) → dict
    - 超时 → SIGTERM → grace (sigterm_grace_s) → SIGKILL · 最终 raise SubagentTimeoutError
  - kill(session_id) → None · 幂等

错误码:
  E_SUB_SPAWN_FAILED / E_SUB_TIMEOUT / E_SUB_TOOL_ERROR

TODO:SDK-INTEGRATION — Task 04.4+ 接入真实 anthropic SDK:
  安装: pip install -e ".[sdk]"  (已在 pyproject.toml 里)
  实现: subclass SDKAdapter + import anthropic.Client(...).sessions().create(...)

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §6 Task 04.4
"""
from __future__ import annotations

import asyncio
from typing import Any, Protocol


class SpawnFailedError(RuntimeError):
    """E_SUB_SPAWN_FAILED."""


class SubagentTimeoutError(TimeoutError):
    """E_SUB_TIMEOUT."""


class SDKAdapter(Protocol):
    """SDK 适配器协议 · 真实/假实现都必须满足."""

    async def spawn_session(
        self,
        *,
        role: str,
        allowed_tools: list[str],
        context: dict[str, Any],
        timeout_s: int,
    ) -> str:
        """启动一个子 Agent session · 返 session_id."""
        ...

    async def await_result(self, session_id: str, timeout_s: float) -> dict[str, Any]:
        """等待结果 · 超时 raise asyncio.TimeoutError."""
        ...

    async def terminate(self, session_id: str, *, force: bool = False) -> None:
        """向子 Agent 发 SIGTERM (force=False) 或 SIGKILL (force=True)."""
        ...


class ClaudeSDKClient:
    """子 Agent 生命周期的单 session 管理器 · adapter 可插拔."""

    MAX_SPAWN_ATTEMPTS = 2  # 1 initial + 1 retry

    def __init__(
        self,
        adapter: SDKAdapter,
        *,
        sigterm_grace_s: float = 5.0,
    ) -> None:
        self._adapter = adapter
        self._sigterm_grace_s = sigterm_grace_s
        self._active: set[str] = set()

    async def spawn(
        self,
        *,
        role: str,
        allowed_tools: list[str],
        context: dict[str, Any],
        timeout_s: int,
    ) -> str:
        """Spawn 子 Agent · 失败 retry 1 次 · 二次失败 raise SpawnFailedError."""
        last_err: BaseException | None = None
        for attempt in range(1, self.MAX_SPAWN_ATTEMPTS + 1):
            try:
                sid = await self._adapter.spawn_session(
                    role=role,
                    allowed_tools=allowed_tools,
                    context=context,
                    timeout_s=timeout_s,
                )
                self._active.add(sid)
                return sid
            except Exception as exc:
                last_err = exc
                continue
        raise SpawnFailedError(
            f"E_SUB_SPAWN_FAILED after {self.MAX_SPAWN_ATTEMPTS} attempts: {last_err}"
        ) from last_err

    async def await_result(
        self,
        *,
        session_id: str,
        timeout_s: float,
    ) -> dict[str, Any]:
        """等结果 · 超时走 SIGTERM→grace→SIGKILL · 最终 raise SubagentTimeoutError."""
        try:
            return await asyncio.wait_for(
                self._adapter.await_result(session_id, timeout_s),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError as e:
            # 先 SIGTERM
            try:
                await self._adapter.terminate(session_id, force=False)
            except Exception:
                pass
            # grace 等
            await asyncio.sleep(self._sigterm_grace_s)
            # SIGKILL 确保清理
            try:
                await self._adapter.terminate(session_id, force=True)
            except Exception:
                pass
            self._active.discard(session_id)
            raise SubagentTimeoutError(
                f"E_SUB_TIMEOUT: session {session_id} exceeded {timeout_s}s"
            ) from e

    async def kill(self, *, session_id: str) -> None:
        """幂等 kill · SIGTERM + grace + SIGKILL."""
        try:
            await self._adapter.terminate(session_id, force=False)
        except Exception:
            pass
        await asyncio.sleep(self._sigterm_grace_s)
        try:
            await self._adapter.terminate(session_id, force=True)
        except Exception:
            pass
        self._active.discard(session_id)
