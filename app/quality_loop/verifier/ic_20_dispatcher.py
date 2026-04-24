"""L1-04 · L2-06 · ic_20_dispatcher · IC-20 delegate_verifier 生产端.

**职责**：把 VerificationRequest → IC20Command → 通过 L1-05 Delegator 派发 → 同步拿 IC20DispatchResult。

**并发协议**（Exe-plan §3 · WP06 与 main-2 并发）：
- L1-05 的 `delegate_verifier` 真实实现在 main-2 · 尚未合 main
- 本模块定义 `DelegateVerifierProtocol` 鸭子接口 · 供 mock stub 注入
- orchestrator 在集成层挂真实 L1-05 adapter / mock stub / 单元测试 fake

**3 次指数退避**（L2-06 §1.5 D3 · §6.4 · 硬锁 max_retries=3）：
- attempt=1 失败 → backoff=2s → attempt=2
- attempt=2 失败 → backoff=4s → attempt=3
- attempt=3 失败 → raise DelegationFailureError（外层 orchestrator 走 handle_delegation_failure_three_strikes）

**硬红线**：
- `max_retries` 参数硬锁 ≤ 3（L2-06 §6.4 `_assert_ max_retries <= 3`）
- verifier_session_id 前缀必须以 `sub-` 开头（PM-03 独立 session · L2-06 §6.7）
- 派发失败必升 BLOCK · 禁 fallback 主 session（L2-06 §6.9 E29 硬红线）

**错误码**（L2-06 §3.12）：
- E14 `ic_20_api_error` · L1-05 返 5xx
- E15 `ic_20_api_rate_limit` · 429 限流
- E16 `subagent_spawn_failure` · L1-05 起 session 失败
- E17 `session_id_prefix_violation` · session_id 以 `main.` 开头（硬红线）
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerificationRequest,
    VerifierError,
)

# ==============================================================================
# 错误
# ==============================================================================


class DispatcherError(VerifierError):
    """ic_20_dispatcher 统一错误基类."""


class DelegationFailureError(DispatcherError):
    """3 次重试后仍失败（触发 BLOCK 升级 · L2-06 §6.9 E30 `retry_count_exceeded`）.

    属性:
        retry_log · 每次失败的 attempt 记录
        last_error · 最后一次的底层错误
    """

    def __init__(
        self,
        *,
        retry_log: list[dict[str, Any]],
        last_error: Exception | None = None,
        max_retries: int = 3,
    ) -> None:
        msg = (
            f"E30_retry_count_exceeded: delegation failed after "
            f"{len(retry_log)} attempts (max={max_retries}); "
            f"last_error={last_error!r}"
        )
        super().__init__(msg)
        self.retry_log = retry_log
        self.last_error = last_error
        self.max_retries = max_retries


class SessionPrefixViolationError(DispatcherError):
    """硬红线 · verifier_session_id 非法前缀（不是 sub- 开头 或 是 main. 前缀）.

    对应 L2-06 §3.12 E17 session_id_prefix_violation（CRITICAL）。
    """


# ==============================================================================
# Delegator Protocol（本模块 mock · L1-05 真 · main-2 WP 产）
# ==============================================================================


@runtime_checkable
class DelegateVerifierProtocol(Protocol):
    """L1-05 delegate_verifier 接口 · 鸭子类型.

    真实实现（main-2 WP）应提供一个 awaitable `delegate_verifier(cmd)` 方法。
    本模块不强绑真实类型 · 测试层注入 fake / mock stub 即可。

    **约定**：
    - 接受 IC20Command · 返回 IC20DispatchResult
    - 网络/API 错误 → raise RuntimeError / TimeoutError / 特定 API error
    - session_id 由 L1-05 侧分配（本 WP 只做前缀校验）
    """

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult: ...


# ==============================================================================
# Audit hook（可选 · 供 event bus 注入）
# ==============================================================================

AuditEmitter = Callable[[str, dict[str, Any]], Awaitable[None] | None]


async def _call_emit(emitter: AuditEmitter | None, event_type: str, payload: dict[str, Any]) -> None:
    """调 audit emitter · 吞异常（审计故障不阻塞主路径）."""
    if emitter is None:
        return
    try:
        result = emitter(event_type, payload)
        if asyncio.iscoroutine(result):
            await result
    except Exception:  # noqa: BLE001
        pass  # 审计失败不阻塞


# ==============================================================================
# 转换 · VerificationRequest → IC20Command
# ==============================================================================


def build_ic_20_command(request: VerificationRequest) -> IC20Command:
    """把 VerificationRequest → IC20Command（§3.20.2 payload）.

    **纯函数**：同入参同出参 · 无副作用。
    """
    return IC20Command(
        delegation_id=request.delegation_id,
        project_id=request.project_id,
        wp_id=request.wp_id,
        blueprint_slice=dict(request.blueprint_slice),
        s4_snapshot=dict(request.s4_snapshot),
        acceptance_criteria=dict(request.acceptance_criteria),
        timeout_s=request.timeout_s,
        allowed_tools=("Read", "Glob", "Grep", "Bash"),
        ts=request.ts,
    )


# ==============================================================================
# Session prefix check
# ==============================================================================


def verify_session_prefix(
    verifier_session_id: str | None,
    main_session_id: str,
) -> None:
    """硬校验 verifier_session_id 合法前缀（L2-06 §6.7 硬约束 2）.

    **校验规则**：
    1. 非空
    2. 以 `sub-` 开头（IC-20 §3.20.3 `verifier_session_id: format "sub-{uuid-v7}"`）
    3. 绝不等于 main_session_id
    4. 绝不以 `main.` 前缀开头（防 L1-05 bug 退化到主 session）

    任一违反 → raise SessionPrefixViolationError（硬红线 · 不重试 · 直接 BLOCK）。
    """
    if not verifier_session_id:
        raise SessionPrefixViolationError(
            "E17_session_id_prefix_violation: verifier_session_id is empty",
        )
    if not verifier_session_id.startswith("sub-"):
        raise SessionPrefixViolationError(
            f"E17_session_id_prefix_violation: "
            f"expected 'sub-' prefix, got '{verifier_session_id[:10]}...'",
        )
    if verifier_session_id == main_session_id:
        raise SessionPrefixViolationError(
            "E20_session_id_prefix_mismatch: "
            "verifier_session_id equals main_session_id",
        )
    if verifier_session_id.startswith("main."):
        raise SessionPrefixViolationError(
            "E17_session_id_prefix_violation: "
            "verifier_session_id has 'main.' prefix (PM-03 violation)",
        )


# ==============================================================================
# Dispatcher with retry
# ==============================================================================


@dataclass
class _RetryConfig:
    """重试配置 · L2-06 §6.4 · max_retries 硬锁 ≤ 3."""

    max_retries: int = 3
    backoff_base_s: float = 2.0
    backoff_factor: float = 2.0

    def __post_init__(self) -> None:
        if self.max_retries > 3:
            raise ValueError(
                "max_delegation_retries hard-locked at 3 (L2-06 §6.4 · §1.5 D3)",
            )
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")


async def dispatch_with_retry(
    request: VerificationRequest,
    delegator: DelegateVerifierProtocol,
    *,
    max_retries: int = 3,
    backoff_base_s: float = 2.0,
    audit_emitter: AuditEmitter | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> IC20DispatchResult:
    """派发 IC-20 · 3 次指数退避 · 失败升 DelegationFailureError.

    Args:
        request: VerificationRequest
        delegator: L1-05 delegate_verifier 接口（mock / 真实）
        max_retries: 硬锁 ≤ 3（L2-06 §6.4）
        backoff_base_s: 初始退避秒数（2s / 4s / 8s）
        audit_emitter: 可选 IC-09 审计 emitter
        sleep: 可注入的 sleep 函数（测试时用 `async def no_sleep(s): pass`）

    Returns:
        IC20DispatchResult · dispatched=True + verifier_session_id 合法

    Raises:
        DelegationFailureError · 3 次重试后仍失败
        SessionPrefixViolationError · 硬红线（不重试 · 直接传 up）
    """
    cfg = _RetryConfig(max_retries=max_retries, backoff_base_s=backoff_base_s)
    sleep_fn = sleep if sleep is not None else asyncio.sleep
    retry_log: list[dict[str, Any]] = []
    last_error: Exception | None = None

    command = build_ic_20_command(request)

    for attempt in range(1, cfg.max_retries + 1):
        try:
            result = await delegator.delegate_verifier(command)
        except SessionPrefixViolationError:
            # 硬红线 · 不重试 · 直接传 up
            raise
        except Exception as e:  # noqa: BLE001
            last_error = e
            retry_log.append({
                "attempt": attempt,
                "outcome": _classify_error(e),
                "detail": str(e),
            })
            await _call_emit(audit_emitter, "L1-04:verifier_delegation_failed", {
                "project_id": request.project_id,
                "delegation_id": request.delegation_id,
                "attempt": attempt,
                "reason": _classify_error(e),
            })
            if attempt < cfg.max_retries:
                backoff = cfg.backoff_base_s * (cfg.backoff_factor ** (attempt - 1))
                await sleep_fn(backoff)
                continue
            # 最后一次 · 走到这里说明 3 次都失败 · raise
            raise DelegationFailureError(
                retry_log=retry_log,
                last_error=last_error,
                max_retries=cfg.max_retries,
            ) from e

        # 派发成功 · 校验 dispatched + session_id 前缀
        if not result.dispatched:
            last_error = RuntimeError(
                f"E16_subagent_spawn_failure: dispatched=False, delegation_id={request.delegation_id}",
            )
            retry_log.append({
                "attempt": attempt,
                "outcome": "subagent_spawn_failure",
                "detail": "dispatched=False in IC20DispatchResult",
            })
            await _call_emit(audit_emitter, "L1-04:verifier_delegation_failed", {
                "project_id": request.project_id,
                "delegation_id": request.delegation_id,
                "attempt": attempt,
                "reason": "subagent_spawn_failure",
            })
            if attempt < cfg.max_retries:
                backoff = cfg.backoff_base_s * (cfg.backoff_factor ** (attempt - 1))
                await sleep_fn(backoff)
                continue
            raise DelegationFailureError(
                retry_log=retry_log,
                last_error=last_error,
                max_retries=cfg.max_retries,
            )

        # 成功 · 校验 session_id 前缀（硬红线）
        verify_session_prefix(result.verifier_session_id, request.main_session_id)

        # 发成功审计
        await _call_emit(audit_emitter, "L1-04:verifier_delegation_dispatched", {
            "project_id": request.project_id,
            "delegation_id": request.delegation_id,
            "attempt": attempt,
            "verifier_session_id": result.verifier_session_id,
        })
        return result

    # 不可达 · 安全网
    raise DelegationFailureError(
        retry_log=retry_log,
        last_error=last_error,
        max_retries=cfg.max_retries,
    )


# ==============================================================================
# 辅助 · 错误分类
# ==============================================================================


def _classify_error(e: Exception) -> str:
    """把异常映射到 L2-06 §3.12 错误码分类（用于审计归因）."""
    msg = str(e).lower()
    name = type(e).__name__
    if "timeout" in name.lower() or "timeout" in msg:
        return "timeout"
    if "429" in msg or "rate" in msg or "limit" in msg:
        return "ic_20_api_rate_limit"  # E15
    if "500" in msg or "5xx" in msg or "server" in msg:
        return "ic_20_api_error"  # E14
    if "spawn" in msg or "start" in msg:
        return "subagent_spawn_failure"  # E16
    return "ic_20_api_error"  # default fallback (保守)
