"""L1-04 · L2-06 · orchestrator · S5 TDDExe Verifier 编排主入口.

**唯一入口**：`await orchestrate_s5(trace, deps) -> VerifiedResult`

**编排 7 步**（L2-06 §6.1 主算法 · 精简成 WP06 可落地版）：

1. `adapt_from_s4(trace)` → `VerificationRequest`（PM-14 + 字段校验）
2. `dispatch_with_retry(request, delegator)` → `IC20DispatchResult`（IC-20 独立 session）
3. `wait_verifier_callback(session_id, timeout)` → raw verifier_output（含三段）
4. `check_signatures(request, observed_blueprint, observed_test_report)` → `SignatureCheckResult`
5. `compute_dod_verdict(dod_evaluation)` → `VerifierVerdict` (PASS / FAIL_L3 等)
6. `downgrade_verdict(signatures, dod_verdict)` → 最终 verdict
7. 组装 `VerifiedResult`（含 three_segment_evidence）并返回

**三段证据链**（IC-20 §3.20.3）：
- `blueprint_alignment` · SignatureCheckResult.blueprint_detail
- `s4_diff_analysis`    · SignatureCheckResult.s4_diff_detail
- `dod_evaluation`      · verifier 独立 session 回调的 DoD 求值结果

**降级策略**（L2-06 §1.5 决策 D1）：
- IC-20 派发 3 次失败 → verdict=FAIL_L4 + BLOCK 升级（由 caller 层级处理）
- verifier 超时         → verdict=FAIL_L4（本模块捕获 TimeoutError 并降级）
- 硬红线 session prefix → SessionPrefixViolationError 直接 up（caller 走 BLOCK）
- 双签失败              → verdict 降级到 FAIL_L1/L2（见 signature_checker.downgrade_verdict）

**PM-03**（独立 session 硬约束）：
- session_id 前缀校验在 ic_20_dispatcher 层做
- verifier_output schema 校验在本模块 `_parse_verifier_output` 做
- 不允许主 session 降级自跑（L2-06 §6.9 E29 硬红线）

**依赖注入**（WP06 集成点）：
- `delegator`     · L1-05 delegate_verifier（main-2 WP · 本 WP 用 mock stub）
- `callback_waiter` · 等 verifier 回调的函数（支持 poll/push 两种实现）
- `audit_emitter` · 可选 · IC-09 event bus adapter
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.quality_loop.verifier.ic_20_dispatcher import (
    AuditEmitter,
    DelegateVerifierProtocol,
    DelegationFailureError,
    SessionPrefixViolationError,
    dispatch_with_retry,
)
from app.quality_loop.verifier.schemas import (
    IC20DispatchResult,
    SignatureCheckResult,
    VerificationRequest,
    VerifiedResult,
    VerifierError,
    VerifierVerdict,
)
from app.quality_loop.verifier.signature_checker import (
    check_signatures,
    downgrade_verdict,
)
from app.quality_loop.verifier.trace_adapter import (
    ExecutionTraceLike,
    adapt_from_s4,
)

# ==============================================================================
# 错误
# ==============================================================================


class OrchestratorError(VerifierError):
    """orchestrator 运行期错误基类."""


class CallbackTimeoutError(OrchestratorError):
    """verifier 30 min / 超时未回调 (L2-06 §3.5 E18 callback_timeout)."""


class CallbackSchemaError(OrchestratorError):
    """verifier 回调 payload schema 违反 (L2-06 §3.5 E19)."""


# ==============================================================================
# Callback waiter Protocol
# ==============================================================================


@runtime_checkable
class CallbackWaiterProtocol(Protocol):
    """等 verifier 独立 session 回调的接口.

    **实现方式**（由 caller 注入）：
    - 事件总线订阅模式：监听 L1-09 事件 verifier_verdict · 命中 delegation_id 就返回
    - 文件 watcher 模式：轮询 `verifier_reports/<sid>.json` 就绪
    - mock 测试模式：直接 in-memory dict 返回

    **约定**：
    - 接受 (delegation_id, session_id, timeout_s) · 返 raw output dict
    - 超时 → raise TimeoutError
    - schema 违反（缺必要字段） → caller 层 _parse_verifier_output 处理
    """

    async def wait(
        self,
        *,
        delegation_id: str,
        verifier_session_id: str,
        timeout_s: int,
    ) -> dict[str, Any]: ...


# ==============================================================================
# 依赖容器
# ==============================================================================


@dataclass
class VerifierDeps:
    """orchestrate_s5 依赖注入 bundle.

    Attributes:
        delegator: L1-05 IC-20 delegate_verifier（必填）
        callback_waiter: 等 verifier 回调（必填）
        audit_emitter: 可选 · IC-09 event bus
        sleep: 可注入 sleep 函数（用于测试免 delay · 默认 asyncio.sleep）
        coverage_tolerance: 双签 coverage 容忍（默认 0.05）
    """

    delegator: DelegateVerifierProtocol
    callback_waiter: CallbackWaiterProtocol
    audit_emitter: AuditEmitter | None = None
    sleep: Callable[[float], Awaitable[None]] | None = None
    coverage_tolerance: float = 0.05


# ==============================================================================
# 主入口
# ==============================================================================


async def orchestrate_s5(
    trace: ExecutionTraceLike,
    deps: VerifierDeps,
    *,
    max_retries: int = 3,
    delegation_id: str | None = None,
) -> VerifiedResult:
    """S5 Verifier 编排主入口.

    Args:
        trace: L2-05 S4 ExecutionTrace（WP05 产 · 本 WP 用 MockExecutionTrace）
        deps: 依赖注入 bundle（delegator + waiter + audit）
        max_retries: IC-20 重试次数硬锁 ≤ 3
        delegation_id: 幂等 key · 外部指定复用历史

    Returns:
        VerifiedResult · 含 verdict + signatures + dod_evaluation + three_segment_evidence

    Raises:
        TraceAdapterError: trace 字段缺失
        DelegationFailureError: 3 次重试仍失败（caller 层走 BLOCK）
        SessionPrefixViolationError: 硬红线（caller 层走 BLOCK）
        CallbackSchemaError: verifier 回调格式错（非 TimeoutError · caller 层决策）
    """
    start_ms = _now_ms()

    # Step 1: adapt trace → request
    request = adapt_from_s4(trace, delegation_id=delegation_id)

    await _emit(deps.audit_emitter, "L1-04:verifier_orchestrate_started", {
        "project_id": request.project_id,
        "delegation_id": request.delegation_id,
        "wp_id": request.wp_id,
    })

    # Step 2: IC-20 dispatch with retry
    try:
        dispatch_result: IC20DispatchResult = await dispatch_with_retry(
            request,
            deps.delegator,
            max_retries=max_retries,
            audit_emitter=deps.audit_emitter,
            sleep=deps.sleep,
        )
    except (DelegationFailureError, SessionPrefixViolationError):
        # 硬红线 · 传 up · caller 走 BLOCK
        raise

    # Step 3: wait verifier callback（捕获超时 → FAIL_L4）
    try:
        raw_output = await deps.callback_waiter.wait(
            delegation_id=request.delegation_id,
            verifier_session_id=dispatch_result.verifier_session_id or "",
            timeout_s=request.timeout_s,
        )
    except TimeoutError as e:
        await _emit(deps.audit_emitter, "L1-04:verifier_timeout", {
            "project_id": request.project_id,
            "delegation_id": request.delegation_id,
            "timeout_s": request.timeout_s,
        })
        # 超时 → verdict=FAIL_L4 · 返回可用结果（不抛异常 · 便于上层路由）
        return _build_timeout_result(
            request=request,
            dispatch_result=dispatch_result,
            duration_ms=_now_ms() - start_ms,
            timeout_detail=str(e) or f"callback timeout after {request.timeout_s}s",
        )

    # Step 4: parse verifier_output（schema 硬校验）
    parsed = _parse_verifier_output(raw_output)

    # Step 5: 双签校验
    signatures: SignatureCheckResult = check_signatures(
        request,
        parsed.observed_blueprint,
        parsed.observed_test_report,
        coverage_tolerance=deps.coverage_tolerance,
    )

    # Step 6: DoD verdict（由 verifier 独立 session 算出 · 默认 PASS/FAIL_L3）
    dod_verdict = _compute_dod_verdict(parsed.dod_evaluation)

    # Step 7: 组合降级
    final_verdict = downgrade_verdict(signatures, dod_verdict)

    three_segment_evidence = {
        "blueprint_alignment": signatures.blueprint_detail,
        "s4_diff_analysis": signatures.s4_diff_detail,
        "dod_evaluation": parsed.dod_evaluation,
    }

    result = VerifiedResult(
        project_id=request.project_id,
        delegation_id=request.delegation_id,
        wp_id=request.wp_id,
        verdict=final_verdict,
        signatures=signatures,
        dod_evaluation=dict(parsed.dod_evaluation),
        three_segment_evidence=three_segment_evidence,
        verifier_session_id=dispatch_result.verifier_session_id,
        duration_ms=_now_ms() - start_ms,
        verifier_report_id=parsed.report_id,
    )

    await _emit(deps.audit_emitter, "L1-04:verifier_report_issued", {
        "project_id": request.project_id,
        "delegation_id": request.delegation_id,
        "verdict": final_verdict.value,
        "duration_ms": result.duration_ms,
    })

    return result


# ==============================================================================
# 辅助：verifier 回调解析
# ==============================================================================


@dataclass(frozen=True)
class _ParsedVerifierOutput:
    observed_blueprint: dict[str, Any]
    observed_test_report: dict[str, Any]
    dod_evaluation: dict[str, Any]
    report_id: str | None


def _parse_verifier_output(raw: dict[str, Any]) -> _ParsedVerifierOutput:
    """校验并提取 verifier 回调 payload 的三段.

    **必需字段**（verifier 独立 session 回调约定）：
    - `blueprint_alignment` (dict) · verifier 看到的 blueprint
    - `s4_diff_analysis` 或 `test_report` (dict) · verifier 独立跑的 test 结果
    - `dod_evaluation` (dict) · DoD 表达式求值结果（含 `verdict` 字段）

    **失败处理**：缺必要字段或 schema 违反 → raise CallbackSchemaError。
    """
    if not isinstance(raw, dict):
        raise CallbackSchemaError(
            f"E19_callback_schema_violation: expected dict, got {type(raw).__name__}",
        )

    # blueprint_alignment 必有
    bp = raw.get("blueprint_alignment")
    if not isinstance(bp, dict):
        # 兼容 verifier 汇报时可能叫 observed_blueprint
        bp = raw.get("observed_blueprint")
    if not isinstance(bp, dict):
        raise CallbackSchemaError(
            "E19_callback_schema_violation: missing blueprint_alignment/observed_blueprint",
        )

    # s4_diff / test_report
    tr = raw.get("s4_diff_analysis")
    if not isinstance(tr, dict):
        tr = raw.get("test_report")
    if not isinstance(tr, dict):
        # 也许 verifier 说它没跑 · 归空 dict（双签会认为两侧都空 → OK）
        tr = {}

    # dod_evaluation
    dod = raw.get("dod_evaluation")
    if not isinstance(dod, dict):
        raise CallbackSchemaError(
            "E19_callback_schema_violation: missing dod_evaluation",
        )

    return _ParsedVerifierOutput(
        observed_blueprint=bp,
        observed_test_report=tr,
        dod_evaluation=dod,
        report_id=raw.get("verifier_report_id"),
    )


def _compute_dod_verdict(dod_evaluation: dict[str, Any]) -> VerifierVerdict:
    """根据 verifier 返回的 dod_evaluation 判 verdict.

    **规则**：
    - `dod_evaluation.verdict == "PASS"` or `all_pass == True` → PASS
    - 否则 → FAIL_L3（质量 gate 未过阈值）

    此函数只负责 **DoD 本身**的 verdict · 双签降级由 downgrade_verdict 负责。
    """
    explicit = dod_evaluation.get("verdict")
    if isinstance(explicit, str):
        upper = explicit.upper()
        if upper == "PASS":
            return VerifierVerdict.PASS
        # 如果 verifier 已经说 FAIL_L3/L4 等 · 尊重
        try:
            return VerifierVerdict(upper)
        except ValueError:
            return VerifierVerdict.FAIL_L3

    if dod_evaluation.get("all_pass") is True:
        return VerifierVerdict.PASS

    return VerifierVerdict.FAIL_L3


def _build_timeout_result(
    *,
    request: VerificationRequest,
    dispatch_result: IC20DispatchResult,
    duration_ms: int,
    timeout_detail: str,
) -> VerifiedResult:
    """verifier 超时 → verdict=FAIL_L4（BLOCK 级 · 上游 L2-07 路由）.

    **理由**（IC-20 §3.20.4 E_VER_TIMEOUT）：超时触发 FAIL_L4 + partial evidence + 告警升级。
    双签因无实际回调无法校验 · 两签均标 ok=False · 详情里说明原因。
    """
    signatures = SignatureCheckResult(
        blueprint_alignment_ok=False,
        s4_diff_analysis_ok=False,
        blueprint_detail={"ok": False, "reason": "verifier_timeout", "detail": timeout_detail},
        s4_diff_detail={"ok": False, "reason": "verifier_timeout", "detail": timeout_detail},
    )
    three_segment_evidence = {
        "blueprint_alignment": signatures.blueprint_detail,
        "s4_diff_analysis": signatures.s4_diff_detail,
        "dod_evaluation": {"status": "skipped_due_to_timeout", "reason": timeout_detail},
    }
    return VerifiedResult(
        project_id=request.project_id,
        delegation_id=request.delegation_id,
        wp_id=request.wp_id,
        verdict=VerifierVerdict.FAIL_L4,
        signatures=signatures,
        dod_evaluation={},
        three_segment_evidence=three_segment_evidence,
        verifier_session_id=dispatch_result.verifier_session_id,
        duration_ms=duration_ms,
        verifier_report_id=None,
    )


# ==============================================================================
# 辅助：通用
# ==============================================================================


def _now_ms() -> int:
    import time
    return int(time.time() * 1000)


async def _emit(emitter: AuditEmitter | None, event_type: str, payload: dict[str, Any]) -> None:
    if emitter is None:
        return
    try:
        r = emitter(event_type, payload)
        if asyncio.iscoroutine(r):
            await r
    except Exception:  # noqa: BLE001
        pass
