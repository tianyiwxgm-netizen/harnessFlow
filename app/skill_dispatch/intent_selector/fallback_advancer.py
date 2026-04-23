"""L2-02 FallbackAdvancer · 把 Chain.advance() 包装上 IC-09 事件落盘.

职责:
  - advance(chain, pid, reason) → new Chain · 成功时 emit `capability_fallback_advanced`
  - chain 耗尽 → raise ChainExhaustedError · 并 emit `capability_exhausted`
    （调用方 L2-03 invoker 据此决定是否触发 IC-15 hard_halt）

PM-14:
  - project_id 必填 · 写 IC-09 事件需要它.

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md
  - docs/superpowers/plans/Dev-γ-impl.md §4 Task 02.5
"""
from __future__ import annotations

from typing import Any

from .schemas import Chain, ChainExhaustedError


class FallbackAdvancer:
    """包装 Chain.advance 的审计层 · emit IC-09 · raise 耗尽异常."""

    def __init__(self, event_bus: Any) -> None:
        self._bus = event_bus

    def advance(self, chain: Chain, *, project_id: str, reason: str) -> Chain:
        if not project_id:
            raise ValueError("FallbackAdvancer.advance: project_id required (PM-14)")
        try:
            new_chain = chain.advance(reason)
        except ChainExhaustedError:
            # 先发 IC-09 再 re-raise · 让 caller 决定 IC-15 路径
            try:
                self._bus.append_event(
                    project_id=project_id,
                    l1="L1-05",
                    event_type="capability_exhausted",
                    payload={"capability": chain.capability, "reason": reason},
                )
            except Exception:
                # 审计失败不得吞掉原异常 · 静默继续
                pass
            raise
        try:
            self._bus.append_event(
                project_id=project_id,
                l1="L1-05",
                event_type="capability_fallback_advanced",
                payload={
                    "capability": chain.capability,
                    "reason": reason,
                    "new_primary": new_chain.primary.skill.skill_id,
                    "remaining_fallbacks": len(new_chain.fallbacks),
                },
            )
        except Exception:
            pass
        return new_chain
