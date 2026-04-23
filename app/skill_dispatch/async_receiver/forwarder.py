"""L2-05 → L1-04 DoD 网关转发 · 不自判 verdict · 只 route + IC-14 prev_hash.

设计:
  - forward(pid, capability, result_id, artifact, prev_hash) → Verdict
  - 先 emit IC-09 `dod_gate_forward` 事件 · 携带 prev_hash (IC-14 一致性链)
  - 再调 L1-04 dod_gate_check 同步求值 · 10s 超时
  - 超时 → DoDGateTimeout + emit `dod_gate_timeout`

错误码: E_COLLECT_DOD_GATE_TIMEOUT

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-05-异步结果回收器.md
  - docs/superpowers/plans/Dev-γ-impl.md §7 Task 05.3
"""
from __future__ import annotations

import concurrent.futures
from typing import Any

from .schemas import Verdict


class DoDGateTimeout(TimeoutError):
    """E_COLLECT_DOD_GATE_TIMEOUT."""


class DoDForwarder:
    """转发 L2-05 校验结果给 L1-04 DoD evaluator · 不代为判定."""

    def __init__(self, dod_gate: Any, event_bus: Any, timeout_s: float = 10.0) -> None:
        self._gate = dod_gate
        self._bus = event_bus
        self._timeout_s = timeout_s

    def forward(
        self,
        *,
        project_id: str,
        capability: str,
        result_id: str,
        artifact: dict[str, Any],
        prev_hash: str,
    ) -> Verdict:
        # IC-14 事件：L2-05 侧发起 · 携带 prev_hash 保持一致性链
        self._safe_emit(
            project_id=project_id,
            event_type="dod_gate_forward",
            payload={
                "result_id": result_id,
                "capability": capability,
                "prev_hash": prev_hash,
            },
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(
                self._gate.dod_gate_check,
                project_id, capability, result_id, artifact,
            )
            try:
                verdict_obj = fut.result(timeout=self._timeout_s)
            except concurrent.futures.TimeoutError as e:
                self._safe_emit(
                    project_id=project_id,
                    event_type="dod_gate_timeout",
                    payload={"result_id": result_id, "capability": capability},
                )
                raise DoDGateTimeout(
                    f"E_COLLECT_DOD_GATE_TIMEOUT: {result_id} capability={capability}"
                ) from e
        return verdict_obj.verdict

    def _safe_emit(self, *, project_id: str, event_type: str, payload: dict) -> None:
        try:
            self._bus.append_event(
                project_id=project_id,
                l1="L1-05",
                event_type=event_type,
                payload=payload,
            )
        except Exception:
            pass
