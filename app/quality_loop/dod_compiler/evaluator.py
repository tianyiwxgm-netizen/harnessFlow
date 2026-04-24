"""L1-04 · L2-02 · DoDEvaluator (run-time eval 唯一入口).

锚点:§3.2 eval_expression · §6.2 DoDEvaluator.eval.

MVP 简化:
    - 不做 signal.SIGALRM 超时 kill(在测试环境会打断 pytest),改用 wall-clock 估算 + raise.
    - 不做 subprocess 隔离.
    - 不做 resource.setrlimit.
    - 保留 pure function 契约:不写文件 · 不 emit 事件.
    - 保留 caller 白名单 + PM-14 + cache-hit 契约.

上层(L2-05 / L2-06) 若需要硬超时 · 可传 subprocess wrapper.
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.quality_loop.dod_compiler.compiler import DoDExpressionCompiler
from app.quality_loop.dod_compiler.errors import (
    CachePoisonError,
    CallerUnauthorizedError,
    CrossProjectError,
    DataSourceUnknownTypeError,
    DoDEvalError,
    EvalTimeoutError,
    IllegalFunctionError,
    IllegalNodeError,
    NoProjectIdError,
    SandboxEscapeDetectedError,
    WhitelistVersionMismatchError,
)
from app.quality_loop.dod_compiler.predicate_eval import (
    WHITELISTED_DATA_SOURCE_KEYS,
    WhitelistRegistry,
    safe_eval,
)
from app.quality_loop.dod_compiler.schemas import (
    EvalCaller,
    EvalCommand,
    EvalResult,
)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class DoDEvaluator:
    """运行期 eval 唯一入口(§3.2)."""

    def __init__(
        self,
        compiler: DoDExpressionCompiler,
        *,
        whitelist_registry: WhitelistRegistry | None = None,
        eval_timeout_ms: int = 500,
        max_concurrent: int = 50,
    ) -> None:
        self._compiler = compiler
        self._registry = whitelist_registry or compiler.registry
        self._timeout_ms = eval_timeout_ms
        self._sem = threading.BoundedSemaphore(max_concurrent)
        # 幂等 cache: (command_id, snapshot_hash) → EvalResult
        self._result_cache: dict[tuple[str, str], EvalResult] = {}
        self._cache_lock = threading.Lock()

    def eval_expression(self, cmd: EvalCommand) -> EvalResult:
        """eval 一条已编译的 DoDExpression."""
        # 1. 前置校验
        if not cmd.project_id:
            raise NoProjectIdError("project_id required")

        # caller 白名单 (pydantic enum 已限)
        if not isinstance(cmd.caller, EvalCaller):
            try:
                EvalCaller(cmd.caller)
            except ValueError as exc:
                raise CallerUnauthorizedError(f"caller not allowed: {cmd.caller!r}") from exc

        # 2. 取 expression(含 ast)
        pair = self._compiler._get_expression_by_id(cmd.expr_id)
        if pair is None:
            raise DoDEvalError(f"expr_id {cmd.expr_id!r} not found")
        expr, tree = pair

        # 3. PM-14 交叉防护
        if expr.project_id != cmd.project_id:
            raise CrossProjectError(
                f"expr.project_id={expr.project_id} vs req={cmd.project_id}"
            )

        # 4. 白名单版本一致性
        cur_version = self._registry.version
        if expr.whitelist_version != cur_version:
            raise WhitelistVersionMismatchError(
                f"expr.whitelist_version={expr.whitelist_version} vs current={cur_version}"
            )

        # 5. DataSource 白名单预检
        for k in cmd.data_sources_snapshot:
            if k not in WHITELISTED_DATA_SOURCE_KEYS:
                raise DataSourceUnknownTypeError(f"unknown data source: {k}")

        # 6. 幂等 cache 检查
        snapshot_hash = _snapshot_hash(cmd.data_sources_snapshot)
        cache_key = (cmd.command_id, snapshot_hash)
        with self._cache_lock:
            cached = self._result_cache.get(cache_key)
            if cached is not None:
                # 返回一个 cache_hit=True 的克隆
                return cached.model_copy(update={"cache_hit": True})

        # 7. 并发限流
        acquired = self._sem.acquire(timeout=(cmd.timeout_ms or self._timeout_ms) / 1000.0)
        if not acquired:
            raise DoDEvalError("concurrent eval cap reached")

        # 8. 执行
        t0 = time.perf_counter()
        try:
            # 软超时:限制 eval 运行时间(由谓词库快速返回 · predicate 不会长跑)
            budget_ms = min(cmd.timeout_ms or self._timeout_ms, self._timeout_ms)
            t_budget_end = t0 + (budget_ms / 1000.0)

            try:
                value, evidence = safe_eval(
                    tree,
                    dict(cmd.data_sources_snapshot),
                    registry=self._registry,
                )
            except (IllegalNodeError, IllegalFunctionError) as exc:
                raise CachePoisonError(f"runtime re-validate failed: {exc}") from exc
            except SandboxEscapeDetectedError:
                raise
            except DoDEvalError:
                raise
            except Exception as exc:  # pragma: no cover
                raise DoDEvalError(f"eval error: {exc}") from exc

            if time.perf_counter() > t_budget_end:
                raise EvalTimeoutError(f"eval exceeded {budget_ms}ms")

            duration_ms = int((time.perf_counter() - t0) * 1000)

            reason = self._format_reason(expr.expression_text, value, evidence)
            result = EvalResult.model_validate({
                "command_id": cmd.command_id,
                "eval_id": f"eval-{uuid.uuid4()}",
                "project_id": cmd.project_id,
                "expr_id": cmd.expr_id,
                "pass": bool(value),
                "reason": reason,
                "evidence_snapshot": evidence,
                "duration_ms": duration_ms,
                "whitelist_version": cur_version,
                "evaluated_at": _now_iso(),
                "caller": cmd.caller,
                "cache_hit": False,
            })
            with self._cache_lock:
                self._result_cache[cache_key] = result
            return result
        finally:
            self._sem.release()

    # -------- helpers --------

    def _format_reason(self, expression_text: str, value: Any, evidence: dict[str, Any]) -> str:
        if value:
            used = sorted(evidence.keys()) if evidence else ["<no-ds>"]
            return f"PASS · expr={expression_text!r} · evidence_keys={used}"
        # fail 模式给 diagnostic
        return f"FAIL · expr={expression_text!r} · value={value!r} · evidence={evidence!r}"

    def _debug_cache_size(self) -> int:
        with self._cache_lock:
            return len(self._result_cache)

    def clear_cache(self) -> None:
        """白名单变更时调用(§3.5.3)."""
        with self._cache_lock:
            self._result_cache.clear()


def _snapshot_hash(snapshot: dict[str, Any]) -> str:
    import hashlib
    import json
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["DoDEvaluator"]
