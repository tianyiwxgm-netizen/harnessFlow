"""L2-03 RetryPolicy · idempotent skill 最多 retry 1 次 · 指数退避.

规则:
  - is_idempotent=False → 0 retry · 直接 fallback_advance
  - is_idempotent=True · attempt ≥ MAX_ATTEMPTS → 耗尽 · fallback_advance
  - 只 retry "transient" 类: SkillTimeout / ConnectionError / OSError
  - ValueError / TypeError / pydantic.ValidationError → caller bug · 不 retry

错误码: E_SKILL_INVOCATION_RETRY_EXHAUSTED

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §5 Task 03.4
"""
from __future__ import annotations

from .timeout_manager import SkillTimeout

# 初始 attempt=1 · 成功或耗尽在此 · 允许最多一次 retry 故 MAX=2.
MAX_ATTEMPTS: int = 2

# 可 retry 的异常类（transient failure）.
_TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SkillTimeout,
    ConnectionError,
    OSError,     # 含 BrokenPipeError 等
)


def should_retry(exc: BaseException, *, attempt: int, is_idempotent: bool) -> bool:
    """判断当前失败的 skill 调用是否可以再试一次.

    Args:
        exc: 刚刚失败时抛出的异常
        attempt: 当前这次已是第几次尝试 (1-based)
        is_idempotent: skill 是否声明 idempotent (SkillSpec 或 registry 元数据)

    Returns:
        True 可以再试一次 (attempt 应 +1 后重跑) · False 放弃 · caller 走 fallback_advance
    """
    if not is_idempotent:
        return False
    if attempt >= MAX_ATTEMPTS:
        return False
    if isinstance(exc, _TRANSIENT_EXCEPTIONS):
        return True
    return False


def backoff_ms(attempt: int) -> int:
    """指数退避: 100ms · 200ms · 400ms · ..."""
    if attempt < 1:
        return 100
    return 100 * (2 ** (attempt - 1))
