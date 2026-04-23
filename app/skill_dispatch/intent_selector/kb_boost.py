"""L2-02 KB boost · 调 IC-06 kb_read · 150ms 超时 · 降级返 {}.

旁路语义:
  KB 命中只是"推一把"· 超时/失败不应阻 rank · fetch() 永不 raise
  （除 PM-14 约束 · 空 project_id 是调用方 bug · 该 raise ValueError）.

实现要点（bug 修复记录）:
  不使用 ThreadPoolExecutor context manager · 因为 __exit__ 会 shutdown(wait=True)
  导致即使 fut.result() 已 timeout · 进程仍会等慢 KB 线程跑完才返回.
  改为 class 级 persistent executor + cancel_futures 上的 timeout.

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md §6 signal[5]
  - docs/superpowers/plans/Dev-γ-impl.md §4 Task 02.4
"""
from __future__ import annotations

import atexit
import concurrent.futures
from typing import Any


class KBBooster:
    """KB 旁路 · 调 IC-06 · 超时硬降级.

    每实例持有自己的 ThreadPoolExecutor · 避免 ctx-manager 等待慢线程.
    （慢 KB 线程会在后台跑完 · 但主线程已返回空 dict 给 rank）.

    Example:
        booster = KBBooster(kb=ic06_reader, timeout_ms=150)
        hits = booster.fetch(project_id="p1", capability="write_test")
        # → {"skill_id_a": 0.9, "skill_id_b": 0.7}
    """

    def __init__(self, kb: Any, timeout_ms: int = 150) -> None:
        self._kb = kb
        self._timeout_s = timeout_ms / 1000.0
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="kb-boost"
        )
        atexit.register(self._shutdown_quietly)

    def _shutdown_quietly(self) -> None:
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

    def close(self) -> None:
        self._shutdown_quietly()

    def __del__(self) -> None:   # pragma: no cover
        self._shutdown_quietly()

    def fetch(self, *, project_id: str, capability: str) -> dict[str, float]:
        if not project_id:
            raise ValueError("KBBooster.fetch: project_id required (PM-14)")
        fut = self._executor.submit(self._kb.kb_read, project_id, capability)
        try:
            recipes = fut.result(timeout=self._timeout_s)
        except concurrent.futures.TimeoutError:
            # E_INTENT_KB_TIMEOUT · 降级返空 · 不阻 rank
            # 慢线程会后台跑完 · 但主线程立即继续
            return {}
        except Exception:
            # KB 读失败任何其他异常一律降级（旁路不可阻挡主链）
            return {}
        out: dict[str, float] = {}
        for r in recipes or []:
            try:
                out[r.skill_id] = float(r.success_rate)
            except (AttributeError, TypeError, ValueError):
                continue
        return out
