"""L2-03 TimeoutManager · skill 调用的超时控制 · ±100ms 精度 · hard-cap 300s.

设计:
  - 使用 ThreadPoolExecutor (max_workers=1) + future.result(timeout) 模式
  - 超过 timeout_ms → SkillTimeout · caller（Executor）据此走 fallback 路径
  - 原始异常（skill 主动 raise）透传
  - hard-cap 自动 clamp 到 HARD_CAP_MS（防 caller 误传巨值）

注意事项:
  - 慢线程无法被中断（Python threading 限制）· 超时后主线程返回 · 慢线程后台跑完
  - 所以本 module 提供 persistent executor shared across calls (避免 ctx-mgr wait)

错误码: E_SKILL_INVOCATION_TIMEOUT

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §5 Task 03.3
"""
from __future__ import annotations

import atexit
import concurrent.futures
from collections.abc import Callable
from typing import Any, TypeVar

HARD_CAP_MS: int = 300_000   # 5min


class SkillTimeout(TimeoutError):
    """E_SKILL_INVOCATION_TIMEOUT."""


T = TypeVar("T")


# Module-level persistent executor · 避免每次调用创建/销毁线程池
_executor: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(
    max_workers=8,
    thread_name_prefix="skill-invoke",
)


def _shutdown() -> None:   # pragma: no cover
    try:
        _executor.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass


atexit.register(_shutdown)


def run_with_timeout(
    fn: Callable[..., T],
    *args: Any,
    timeout_ms: int,
    **kwargs: Any,
) -> T:
    """运行 fn(*args, **kwargs) · 最多等 min(timeout_ms, HARD_CAP_MS).

    超时 → SkillTimeout
    fn raise → 原 exception 透传
    """
    effective_ms = min(timeout_ms, HARD_CAP_MS)
    timeout_s = effective_ms / 1000.0
    fut = _executor.submit(fn, *args, **kwargs)
    try:
        return fut.result(timeout=timeout_s)
    except concurrent.futures.TimeoutError as e:
        raise SkillTimeout(
            f"E_SKILL_INVOCATION_TIMEOUT: exceeded {effective_ms}ms"
        ) from e
