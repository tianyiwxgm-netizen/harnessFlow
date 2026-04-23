"""L2-03 ContextInjector · 白名单注入 · 防上游 context 字段泄漏到 skill 或子 Agent.

白名单（仅 5 个字段允许透传）:
  project_id / wp_id / loop_session_id / decision_id / correlation_id

为何只注入白名单:
  - 防 token/secret 等上游敏感字段被 skill 读取（E09 防御）
  - 防 task_board 等"主 session 独占"状态泄漏到子 Agent（PM-03）
  - 强制 PM-14 · 缺 project_id 立即拒绝

错误码: E_SKILL_INVOCATION_CONTEXT_INJECTION_FAILED

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §5 Task 03.2
"""
from __future__ import annotations

from typing import Any

ALLOWED_CONTEXT_KEYS: frozenset[str] = frozenset(
    {
        "project_id",       # PM-14 主键
        "wp_id",            # WP 追溯
        "loop_session_id",  # L1-01 决策循环 session
        "decision_id",      # L1-01 单次决策 ID
        "correlation_id",   # 跨 L1 审计链关联
    }
)


class ContextInjectionError(ValueError):
    """E_SKILL_INVOCATION_CONTEXT_INJECTION_FAILED."""


def inject(upstream_ctx: dict[str, Any]) -> dict[str, Any]:
    """按白名单过滤 upstream context · 返新 dict · 永不 in-place.

    PM-14 校验: project_id 必须存在且非空.
    """
    pid = upstream_ctx.get("project_id")
    if not pid:
        raise ContextInjectionError(
            "E_SKILL_INVOCATION_CONTEXT_INJECTION_FAILED: project_id missing or empty (PM-14)"
        )
    return {k: v for k, v in upstream_ctx.items() if k in ALLOWED_CONTEXT_KEYS}
