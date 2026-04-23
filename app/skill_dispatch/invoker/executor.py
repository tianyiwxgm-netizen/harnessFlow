"""L2-03 SkillExecutor · IC-04 invoke_skill 主入口 · 6 阶段流水编排.

6 阶段:
  1. IntentSelector.select(request) → Chain (primary + fallbacks)
     - CapabilityNotFoundError → 返 success=false · code=E_SKILL_NO_CAPABILITY
  2. inject(request.context) → safe_ctx (白名单)
  3. audit_start() → params_hash (IC-09 两次写之一)
  4. run_with_timeout(skill_runner, skill, params, safe_ctx, timeout_ms=per_call)
  5. retry / fallback:
     - should_retry(exc, attempt, is_idempotent) True → sleep(backoff) + retry
     - False → advancer.advance(chain, reason)
     - ChainExhaustedError → 返 success=false · code=E_SKILL_ALL_FALLBACK_FAIL
  6. audit_finish() · ledger.record() (IC-L2-07 caller='L2-02')

SLO:
  dispatch 延迟 (含 skill 本身执行) · 10 候选 ≤ 200ms (test_dispatch_latency_under_200ms_slo)

错误码:
  E_SKILL_NO_CAPABILITY / E_SKILL_ALL_FALLBACK_FAIL / (底层 TIMEOUT / RETRY_EXHAUSTED 映射到 trace)

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md §6
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.4 IC-04
  - docs/superpowers/plans/Dev-γ-impl.md §5 Task 03.6
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ..intent_selector import IntentSelector
from ..intent_selector.schemas import (
    ChainExhaustedError,
    Constraints,
    IntentRequest,
)
from ..registry.ledger import LedgerWriter
from ..registry.query_api import CapabilityNotFoundError
from ..registry.schemas import SkillSpec
from . import retry_policy
from .audit import Auditor
from .context_injector import inject
from .retry_policy import backoff_ms, should_retry
from .schemas import InvocationRequest, InvocationResponse
from .timeout_manager import run_with_timeout

# skill_runner signature: (skill, params, ctx) -> dict
SkillRunnerFn = Callable[[SkillSpec, dict[str, Any], dict[str, Any]], dict[str, Any]]


def _is_idempotent(_skill: SkillSpec) -> bool:
    """默认所有 skill idempotent · 未来 SkillSpec 扩展字段后可读 skill.idempotent.

    PRD 里 retry 只对 idempotent 有意义 · 我们这里用 True 作默认 · skill 作者若需要禁
    retry · 后续引入 SkillSpec.idempotent=False 字段（本次 scope 外）.
    """
    return True


class SkillExecutor:
    """IC-04 invoke_skill 主入口 · 绑定 selector + audit + ledger + skill_runner."""

    def __init__(
        self,
        *,
        selector: IntentSelector,
        event_bus: Any,
        ledger: LedgerWriter,
        skill_runner: SkillRunnerFn,
    ) -> None:
        self.selector = selector
        self.auditor = Auditor(event_bus=event_bus)
        self.ledger = ledger
        self.skill_runner = skill_runner
        self.advancer = selector.advancer

    def invoke(self, request: InvocationRequest) -> InvocationResponse:
        wall_start_ns = time.perf_counter_ns()

        # ---- Phase 1: select chain ----
        try:
            chain = self.selector.select(
                IntentRequest(
                    project_id=request.project_id,
                    capability=request.capability,
                    constraints=Constraints(),   # 调用方暂不透传 · 后续按需扩展
                    context=request.context,
                )
            )
        except CapabilityNotFoundError as e:
            return InvocationResponse(
                invocation_id=request.invocation_id,
                success=False,
                skill_id="E_SKILL_NO_CAPABILITY",
                duration_ms=int((time.perf_counter_ns() - wall_start_ns) / 1_000_000),
                fallback_used=False,
                error={"code": "E_SKILL_NO_CAPABILITY", "detail": str(e)},
            )

        fallback_trace: list[dict[str, Any]] = []

        # ---- Phase 2-6: walk chain with retry + fallback ----
        current = chain
        while True:
            skill = current.primary.skill
            attempt = 1
            last_exc: BaseException | None = None

            while True:   # retry loop (bounded by MAX_ATTEMPTS)
                safe_ctx = inject(request.context)
                self.auditor.audit_start(
                    project_id=request.project_id,
                    invocation_id=request.invocation_id,
                    capability=request.capability,
                    skill_id=skill.skill_id,
                    caller_l1=request.caller_l1,
                    attempt=attempt,
                    params=request.params,
                )
                try:
                    # timeout 取 min(request.timeout_ms, skill.timeout_s*1000)
                    per_call_ms = min(request.timeout_ms, skill.timeout_s * 1000)
                    result = run_with_timeout(
                        self.skill_runner, skill, request.params, safe_ctx,
                        timeout_ms=per_call_ms,
                    )
                except Exception as exc:
                    last_exc = exc
                    duration_ms = int(
                        (time.perf_counter_ns() - wall_start_ns) / 1_000_000
                    )
                    self.auditor.audit_finish(
                        project_id=request.project_id,
                        invocation_id=request.invocation_id,
                        success=False,
                        duration_ms=duration_ms,
                        fallback_used=(skill.skill_id != chain.primary.skill.skill_id),
                        result_summary=f"attempt {attempt} failed: {type(exc).__name__}",
                    )
                    self._ledger_record_safely(
                        request, skill, success=False,
                        reason=type(exc).__name__,
                    )
                    if should_retry(
                        exc, attempt=attempt, is_idempotent=_is_idempotent(skill),
                    ):
                        time.sleep(backoff_ms(attempt) / 1000.0)
                        attempt += 1
                        continue   # retry loop
                    break   # out of retry loop · go fallback
                else:
                    # success
                    duration_ms = int(
                        (time.perf_counter_ns() - wall_start_ns) / 1_000_000
                    )
                    self.auditor.audit_finish(
                        project_id=request.project_id,
                        invocation_id=request.invocation_id,
                        success=True,
                        duration_ms=duration_ms,
                        fallback_used=(skill.skill_id != chain.primary.skill.skill_id),
                        result_summary="ok",
                    )
                    self._ledger_record_safely(
                        request, skill, success=True, reason=None,
                    )
                    return InvocationResponse(
                        invocation_id=request.invocation_id,
                        success=True,
                        skill_id=skill.skill_id,
                        duration_ms=duration_ms,
                        fallback_used=(skill.skill_id != chain.primary.skill.skill_id),
                        result=result,
                        fallback_trace=fallback_trace,
                    )

            # retry loop exited with failure · push trace + advance
            fallback_trace.append(
                {
                    "skill_id": skill.skill_id,
                    "attempt": attempt,
                    "reason": type(last_exc).__name__ if last_exc else "unknown",
                }
            )
            if not request.allow_fallback:
                duration_ms = int(
                    (time.perf_counter_ns() - wall_start_ns) / 1_000_000
                )
                return InvocationResponse(
                    invocation_id=request.invocation_id,
                    success=False,
                    skill_id=skill.skill_id,
                    duration_ms=duration_ms,
                    fallback_used=False,
                    error={
                        "code": "E_SKILL_INVOCATION_FAILED",
                        "detail": str(last_exc)[:200] if last_exc else "unknown",
                    },
                    fallback_trace=fallback_trace,
                )
            try:
                current = self.advancer.advance(
                    current, project_id=request.project_id,
                    reason=type(last_exc).__name__ if last_exc else "unknown",
                )
            except ChainExhaustedError:
                duration_ms = int(
                    (time.perf_counter_ns() - wall_start_ns) / 1_000_000
                )
                return InvocationResponse(
                    invocation_id=request.invocation_id,
                    success=False,
                    skill_id=skill.skill_id,
                    duration_ms=duration_ms,
                    fallback_used=True,
                    error={
                        "code": "E_SKILL_ALL_FALLBACK_FAIL",
                        "last_error": str(last_exc)[:200] if last_exc else "unknown",
                    },
                    fallback_trace=fallback_trace,
                )

    def _ledger_record_safely(
        self,
        request: InvocationRequest,
        skill: SkillSpec,
        *,
        success: bool,
        reason: str | None,
    ) -> None:
        """账本写入 best-effort · 失败不阻主链 (IC-L2-07 caller='L2-02')."""
        try:
            self.ledger.record(
                project_id=request.project_id,
                capability=request.capability,
                skill_id=skill.skill_id,
                success=success,
                failure_reason=reason,
                caller=self.ledger.ALLOWED_CALLER,
            )
        except Exception:
            pass


# Re-export commonly-needed symbols for convenience.
__all__ = ["SkillExecutor", "SkillRunnerFn", "retry_policy"]
