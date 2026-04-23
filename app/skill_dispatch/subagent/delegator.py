"""L2-04 Delegator · IC-05 / IC-12 / IC-20 路由 · 降级链.

IC-05 delegate_subagent (通用):
  - make_child_context → PM-03/14 隔离
  - 取 slot → spawn (retry 1) → 同步返 DispatchAck
  - 异步背景 task: await_result → emit subagent_final_report (via IC-09)

IC-12 delegate_codebase_onboarding (特化):
  - 额外校验 repo_path 存在 + 大小 < 100 万行 (粗估)
  - 走同样 spawn flow

IC-20 delegate_verifier (PM-03 硬约束):
  - allowed_tools 严格 ≤ {Read, Glob, Grep, Bash} (已由 schema 校验)
  - context 必是新 COW 副本 · 不复用主 session

降级链 (BF-E-09):
  Level 1: spawn retry 1 次 (ClaudeSDKClient 层)
  Level 2: retry fail → 返 DispatchAck(dispatched=False) + 发 subagent_spawn_failed
  Level 3: （留给调用方决定是否 inline 或 hard_halt · 不由 Delegator 代决）

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md
  - docs/superpowers/plans/Dev-γ-impl.md §6 Task 04.5
"""
from __future__ import annotations

import asyncio
import pathlib
from typing import Any

from .claude_sdk_client import ClaudeSDKClient, SpawnFailedError, SubagentTimeoutError
from .context_scope import make_child_context
from .resource_limiter import ResourceLimiter, SessionLimitError
from .schemas import (
    CodebaseOnboardingRequest,
    DelegationRequest,
    DispatchAck,
    VerifierRequest,
)


class OnboardingRepoError(ValueError):
    """E_OB_REPO_PATH_INVALID / E_OB_REPO_TOO_LARGE."""


class Delegator:
    """IC-05/12/20 入口 · 同步返回 DispatchAck · 异步发 final_report."""

    def __init__(
        self,
        *,
        sdk_client: ClaudeSDKClient,
        limiter: ResourceLimiter,
        event_bus: Any,
    ) -> None:
        self._client = sdk_client
        self._limiter = limiter
        self._bus = event_bus

    # ------------------------------------------------------------------ IC-05
    async def delegate_subagent(self, request: DelegationRequest) -> DispatchAck:
        """通用 IC-05 · schema 已校验 task_brief 长度 / role / PM-14."""
        return await self._dispatch_common(
            delegation_id=request.delegation_id,
            project_id=request.project_id,
            role=request.role,
            context_copy=dict(request.context_copy),
            allowed_tools=list(request.allowed_tools),
            timeout_s=request.timeout_s,
            task_brief=request.task_brief,
        )

    # ------------------------------------------------------------------ IC-12
    async def delegate_codebase_onboarding(
        self, request: CodebaseOnboardingRequest
    ) -> DispatchAck:
        """IC-12 · repo_path 校验 + 大小 check."""
        p = pathlib.Path(request.repo_path)
        if not p.exists() or not p.is_dir():
            raise OnboardingRepoError(
                f"E_OB_REPO_PATH_INVALID: {request.repo_path}"
            )
        # 大小粗估：> 100 万行拒绝（用文件数粗代）
        # 计细致行数耗时 · 这里先限制文件数 ≤ 10000（proxy for 100 万行）
        files = 0
        for _ in p.rglob("*"):
            files += 1
            if files > 10_000:
                raise OnboardingRepoError("E_OB_REPO_TOO_LARGE: > 10000 files")
        return await self._dispatch_common(
            delegation_id=request.delegation_id,
            project_id=request.project_id,
            role="codebase_onboarding",
            context_copy={"project_id": request.project_id, "repo_path": request.repo_path},
            allowed_tools=["Read", "Glob", "Grep", "Bash"],
            timeout_s=request.timeout_s,
            task_brief=f"onboarding repo {request.repo_path}",
        )

    # ------------------------------------------------------------------ IC-20
    async def delegate_verifier(self, request: VerifierRequest) -> DispatchAck:
        """IC-20 · 严格 allowed_tools 已由 schema 校验 · PM-03 独立 session."""
        return await self._dispatch_common(
            delegation_id=request.delegation_id,
            project_id=request.project_id,
            role="verifier",
            context_copy={
                "project_id": request.project_id,
                "wp_id": request.wp_id,
                "dod_exprs": request.acceptance_criteria,
            },
            allowed_tools=list(request.allowed_tools),
            timeout_s=request.timeout_s,
            task_brief=f"verify wp={request.wp_id}",
        )

    # ------------------------------------------------------------------ common
    async def _dispatch_common(
        self,
        *,
        delegation_id: str,
        project_id: str,
        role: str,
        context_copy: dict[str, Any],
        allowed_tools: list[str],
        timeout_s: int,
        task_brief: str,
    ) -> DispatchAck:
        # PM-03/14 隔离
        child_ctx, _checksum = make_child_context(
            context_copy, child_project_id=project_id,
        )
        # 非阻塞 reserve slot · 覆盖整个 session 生命周期
        reserved = await self._limiter.try_reserve()
        if not reserved:
            self._emit_safe(
                project_id=project_id,
                event_type="subagent_session_limit",
                payload={"delegation_id": delegation_id, "role": role},
            )
            return DispatchAck(
                delegation_id=delegation_id,
                dispatched=False,
                subagent_session_id=None,
            )
        # spawn (内含 retry 1 次)
        try:
            sid = await self._client.spawn(
                role=role,
                allowed_tools=allowed_tools,
                context=dict(child_ctx),
                timeout_s=timeout_s,
            )
        except SpawnFailedError:
            await self._limiter.release_reservation()
            self._emit_safe(
                project_id=project_id,
                event_type="subagent_spawn_failed",
                payload={"delegation_id": delegation_id, "role": role},
            )
            return DispatchAck(
                delegation_id=delegation_id,
                dispatched=False,
                subagent_session_id=None,
            )
        # spawn OK · emit · 启动背景 task 跑完 release slot
        self._emit_safe(
            project_id=project_id,
            event_type="subagent_spawned",
            payload={
                "delegation_id": delegation_id,
                "subagent_session_id": sid,
                "role": role,
            },
        )
        asyncio.create_task(
            self._run_and_report(
                delegation_id=delegation_id,
                project_id=project_id,
                session_id=sid,
                timeout_s=timeout_s,
            )
        )
        return DispatchAck(
            delegation_id=delegation_id,
            dispatched=True,
            subagent_session_id=sid,
        )

    async def _run_and_report(
        self,
        *,
        delegation_id: str,
        project_id: str,
        session_id: str,
        timeout_s: int,
    ) -> None:
        """背景执行 · 等 final_result · 发 subagent_final_report (IC-09) · 释放 slot."""
        try:
            try:
                result = await self._client.await_result(
                    session_id=session_id, timeout_s=float(timeout_s),
                )
                status = "success"
                artifacts = result.get("artifacts", [])
                final_message = result.get("final_message")
            except SubagentTimeoutError:
                status = "timeout"
                artifacts = []
                final_message = "E_SUB_TIMEOUT"
            except Exception as e:
                status = "failed"
                artifacts = []
                final_message = f"E_SUB_TOOL_ERROR: {type(e).__name__}"
            self._emit_safe(
                project_id=project_id,
                event_type="subagent_final_report",
                payload={
                    "delegation_id": delegation_id,
                    "subagent_session_id": session_id,
                    "status": status,
                    "artifacts": artifacts,
                    "final_message": final_message,
                },
            )
        finally:
            await self._limiter.release_reservation()

    def _emit_safe(self, *, project_id: str, event_type: str, payload: dict) -> None:
        try:
            self._bus.append_event(
                project_id=project_id,
                l1="L1-05",
                event_type=event_type,
                payload=payload,
            )
        except Exception:
            pass
