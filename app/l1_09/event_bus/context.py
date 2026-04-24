"""L2-01 · correlation_id / trace_id / span_id contextvars · 对齐 3-1 §3.5.

所有 5 条 L2-01 API 共享以下 header 层元字段（thread-local）：

- **correlation_id**：一次 tick 的全链路追踪 id · L1-01 创建（格式 `cor_<20 hex>`）
- **trace_id**：OTEL trace · 可选透传
- **span_id**：OTEL span · 可选

使用：
    with request_context(correlation_id="cor_abc...", trace_id="..."):
        bus.append(event)  # append 内部自动读取 context 填入 event body

若未显式 set · 首次 append 自动生成 correlation_id（确保每条事件都可追溯）.
"""
from __future__ import annotations

import contextvars
import secrets
from collections.abc import Generator
from contextlib import contextmanager

# 全链路追踪 id（L1-01 创建 · 跨 L1 透传）
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "harness_correlation_id", default=None
)
# OTEL trace id（可选）
_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "harness_trace_id", default=None
)
# OTEL span id（可选）
_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "harness_span_id", default=None
)


def _is_valid_correlation_id(value: str) -> bool:
    """格式：`cor_` + 20 lowercase hex."""
    return (
        isinstance(value, str)
        and value.startswith("cor_")
        and len(value) == 24
        and all(c in "0123456789abcdef" for c in value[4:])
    )


def new_correlation_id() -> str:
    """生成合法格式 correlation_id · `cor_` + 20 hex."""
    return f"cor_{secrets.token_hex(10)}"


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def get_trace_id() -> str | None:
    return _trace_id.get()


def get_span_id() -> str | None:
    return _span_id.get()


def set_correlation_id(value: str | None) -> contextvars.Token:
    if value is not None and not _is_valid_correlation_id(value):
        raise ValueError(
            f"correlation_id must match 'cor_' + 20 hex (got {value!r})"
        )
    return _correlation_id.set(value)


def set_trace_id(value: str | None) -> contextvars.Token:
    return _trace_id.set(value)


def set_span_id(value: str | None) -> contextvars.Token:
    return _span_id.set(value)


@contextmanager
def request_context(
    *,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    auto_generate_correlation: bool = True,
) -> Generator[dict, None, None]:
    """调用方 bracket · 自动 set 三个元字段 · 退出恢复.

    若 correlation_id is None 且 auto_generate=True · 自动生成新 id.
    yields dict(correlation_id, trace_id, span_id) · 当前上下文值.

    E-1 修复：nested-safe · 用 Token.reset(token) 正确恢复每 ContextVar 的前值.
    原实现无条件 `set(None)` 会擦外层值（嵌套场景破 L1-01 主循环 tick-level 追溯）.
    """
    if correlation_id is None and auto_generate_correlation:
        correlation_id = new_correlation_id()
    # E-1: 配对 (ContextVar, Token) · 退出时 ContextVar.reset(Token) 恢复前值
    reset_pairs: list[tuple[contextvars.ContextVar, contextvars.Token]] = []
    if correlation_id is not None:
        reset_pairs.append((_correlation_id, set_correlation_id(correlation_id)))
    if trace_id is not None:
        reset_pairs.append((_trace_id, set_trace_id(trace_id)))
    if span_id is not None:
        reset_pairs.append((_span_id, set_span_id(span_id)))
    try:
        yield {
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "span_id": span_id,
        }
    finally:
        # reverse 恢复（LIFO · 与 set 顺序相反）· 保持 ContextVar 原值
        for var, tok in reversed(reset_pairs):
            var.reset(tok)


__all__ = [
    "request_context",
    "new_correlation_id",
    "get_correlation_id",
    "get_trace_id",
    "get_span_id",
    "set_correlation_id",
    "set_trace_id",
    "set_span_id",
]
