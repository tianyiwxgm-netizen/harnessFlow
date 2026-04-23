"""L2-03 Audit · IC-09 两次写 + params_hash SHA-256 + 敏感字段脱敏.

两次写模型:
  - audit_start: invocation_id / capability / skill_id / caller_l1 / attempt / params_hash / started_at_ts_ns
  - audit_finish: invocation_id / success / duration_ms / fallback_used / result_summary

敏感字段脱敏:
  - 字段名匹配 *_token / *_key / *password* / *secret* / *credential* 的值替换为 "<REDACTED>"
  - 脱敏在 hash 之前做 · 保证 hash 不携带明文信息 · 且 hash 稳定（不同明文 · 同字段名 · 同 hash）

IC-09 失败降级:
  - append_event 抛异常 · 用 try/except 吞掉（best-effort）
  - 错误码: E_SKILL_INVOCATION_AUDIT_SEED_FAILED · 但不让主链 crash

错误码:
  E_SKILL_INVOCATION_AUDIT_SEED_FAILED (仅日志 · 不 raise)

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md §7
  - docs/superpowers/plans/Dev-γ-impl.md §5 Task 03.5
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

_SENSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r".*_token$", re.IGNORECASE),
    re.compile(r".*_key$", re.IGNORECASE),
    re.compile(r".*password.*", re.IGNORECASE),
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*credential.*", re.IGNORECASE),
)

_REDACTED = "<REDACTED>"


def _is_sensitive_key(k: str) -> bool:
    return any(p.match(k) for p in _SENSITIVE_PATTERNS)


def _desensitize(obj: Any) -> Any:
    """递归替换敏感字段的值 · 保留 key · 不动非 dict 叶子."""
    if isinstance(obj, dict):
        return {
            k: (_REDACTED if _is_sensitive_key(k) else _desensitize(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_desensitize(x) for x in obj]
    return obj


def params_hash(params: dict[str, Any]) -> str:
    """SHA-256(canonical_json(_desensitize(params))) · 64-char hex."""
    desensitized = _desensitize(params)
    canonical = json.dumps(desensitized, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Auditor:
    """L2-03 审计器 · 两次 IC-09 写 · best-effort · 失败不阻主链."""

    def __init__(self, event_bus: Any) -> None:
        self._bus = event_bus

    def audit_start(
        self,
        *,
        project_id: str,
        invocation_id: str,
        capability: str,
        skill_id: str,
        caller_l1: str,
        attempt: int,
        params: dict[str, Any],
    ) -> str:
        """始 · 写 skill_invocation_started 事件 · 返 params_hash 供 Signature 落盘用."""
        ph = params_hash(params)
        try:
            self._bus.append_event(
                project_id=project_id,
                l1="L1-05",
                event_type="skill_invocation_started",
                payload={
                    "invocation_id": invocation_id,
                    "capability": capability,
                    "skill_id": skill_id,
                    "caller_l1": caller_l1,
                    "attempt": attempt,
                    "params_hash": ph,
                    "started_at_ts_ns": time.time_ns(),
                },
            )
        except Exception:
            pass   # E_SKILL_INVOCATION_AUDIT_SEED_FAILED · 不阻主链
        return ph

    def audit_finish(
        self,
        *,
        project_id: str,
        invocation_id: str,
        success: bool,
        duration_ms: int,
        fallback_used: bool,
        result_summary: str | None = None,
    ) -> None:
        """终 · 写 skill_invocation_finished 事件 · 失败不 raise."""
        try:
            self._bus.append_event(
                project_id=project_id,
                l1="L1-05",
                event_type="skill_invocation_finished",
                payload={
                    "invocation_id": invocation_id,
                    "success": success,
                    "duration_ms": duration_ms,
                    "fallback_used": fallback_used,
                    "result_summary": result_summary,
                },
            )
        except Exception:
            pass
