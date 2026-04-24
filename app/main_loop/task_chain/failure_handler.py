"""L1-01 L2-04 · Failure Handler · BF-E-* backward fail 分类.

对齐:
    - L2-04 §11.1 错误分类
    - BF-E-* 前缀 · 下游 L1 失败反向传回本 L2 后的统一错误码
    - 捕获 dev-δ/ε/γ 抛出的异常 → 映射到 BF-E-* 便于 L2-05 审计分类

设计:
    - 捕获 downstream exception · 无差别 classify_exception() → BackwardFailCode
    - 保留 original exception 在 TaskChainError.cause · 审计可追溯
"""
from __future__ import annotations

import asyncio
from enum import StrEnum


class BackwardFailCode(StrEnum):
    """BF-E-* 错误码 · 下游 L1 失败反向传回本 L2 的分类.

    前缀约定:
        BF-E- = Backward Fail from downstream L1 (被动失败)

    分类:
        - DOWNSTREAM_RAISE:     下游 L1 抛一般异常 (ValueError / TypeError 等).
        - DOWNSTREAM_TIMEOUT:   下游 L1 超时 (asyncio.TimeoutError / TimeoutError).
        - DOWNSTREAM_CANCELLED: 下游 L1 被取消 (asyncio.CancelledError).
        - IC_CONTRACT_VIOLATION: IC payload 合法但 reply 字段缺失 / 非法.
        - UNKNOWN:              兜底 · 未分类的 BaseException.
    """

    DOWNSTREAM_RAISE = "BF-E-DOWNSTREAM_RAISE"
    DOWNSTREAM_TIMEOUT = "BF-E-DOWNSTREAM_TIMEOUT"
    DOWNSTREAM_CANCELLED = "BF-E-DOWNSTREAM_CANCELLED"
    IC_CONTRACT_VIOLATION = "BF-E-IC_CONTRACT_VIOLATION"
    UNKNOWN = "BF-E-UNKNOWN"


BF_ERROR_CODES: frozenset[BackwardFailCode] = frozenset(BackwardFailCode)


class TaskChainError(Exception):
    """本 L2 抛出的运行时异常 · 携带 BF-E-* 分类 + 原始异常链.

    使用方式:
        try:
            await downstream_l1.do_thing()
        except Exception as exc:
            raise TaskChainError.from_cause(exc, project_id=..., task_id=...) from exc
    """

    def __init__(
        self,
        *,
        code: BackwardFailCode,
        message: str,
        project_id: str | None = None,
        task_id: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.project_id = project_id
        self.task_id = task_id
        self.cause = cause

    @classmethod
    def from_cause(
        cls,
        exc: BaseException,
        *,
        project_id: str | None = None,
        task_id: str | None = None,
        override_code: BackwardFailCode | None = None,
    ) -> TaskChainError:
        """从下游异常构造 TaskChainError · 自动 classify.

        Args:
            exc: 下游抛出的原始异常.
            project_id / task_id: 审计字段.
            override_code: 强制指定 BF-E-* (如 IC_CONTRACT_VIOLATION).
        """
        code = override_code or classify_exception(exc)
        return cls(
            code=code,
            message=f"{type(exc).__name__}: {exc!s}",
            project_id=project_id,
            task_id=task_id,
            cause=exc,
        )


def classify_exception(exc: BaseException) -> BackwardFailCode:
    """将下游异常分类到 BF-E-* 错误码.

    规则:
        - asyncio.CancelledError → DOWNSTREAM_CANCELLED
        - asyncio.TimeoutError / TimeoutError → DOWNSTREAM_TIMEOUT
        - 其他 Exception / BaseException → DOWNSTREAM_RAISE
        - 若 exc 是 TaskChainError 自身 → 透传 exc.code (不再分类 · 避免双重包装)

    注意:
        本函数不区分 dev-δ/ε/γ/β 的具体错误码 (由 L2-05 审计层进一步归因);
        此处做粗分 5 类 · 足够 router 判断是否 retry / rollback.
    """
    if isinstance(exc, TaskChainError):
        return exc.code
    if isinstance(exc, asyncio.CancelledError):
        return BackwardFailCode.DOWNSTREAM_CANCELLED
    # asyncio.TimeoutError 在 3.11 是 TimeoutError 的别名 · 统一判断
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return BackwardFailCode.DOWNSTREAM_TIMEOUT
    if isinstance(exc, Exception):
        return BackwardFailCode.DOWNSTREAM_RAISE
    return BackwardFailCode.UNKNOWN


__all__ = [
    "BF_ERROR_CODES",
    "BackwardFailCode",
    "TaskChainError",
    "classify_exception",
]
