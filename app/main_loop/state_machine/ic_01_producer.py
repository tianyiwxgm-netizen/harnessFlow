"""L2-03 · IC-01 Producer · 发 state_transition_request 给 L1-02 Stage Gate。

对齐 ic-contracts.md §3.1 IC-01:
  - 必填 9 字段: transition_id / project_id / from / to / reason /
                trigger_tick / evidence_refs / ts / gate_id(optional)
  - 返回 dict (ok: bool, ...) · 透明转 TransitionResult

本 Producer 是 L1-01 → L1-02 出向桥;运行时依赖 Dev-δ
`app.project_lifecycle.stage_gate` 已 merged · 在 main 上可直接 import
StageGateController.request_state_transition 的 Protocol。

注意:
  - 生产实现由外部 inject StageGate 实例 (rx_target);本模块只负责拼字段 +
    格式校验 + 透传;**不在此做 7→9 enum 映射** (本 WP 保持 7-enum 单一来源)。
  - transition_id / ts / trigger_tick 由 caller 或 Producer 默认生成。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from app.main_loop.state_machine.schemas import (
    E_TRANS_NO_EVIDENCE,
    E_TRANS_NO_PROJECT_ID,
    E_TRANS_REASON_TOO_SHORT,
    MIN_REASON_LENGTH,
    State,
    StateMachineError,
)
from app.main_loop.state_machine.orchestrator import generate_transition_id


class StageGateTarget(Protocol):
    """L1-02 StageGateController 的 Protocol (ic-contracts §3.1.2 对齐)。

    真实实现: `app.project_lifecycle.stage_gate.controller.StageGateController`
    (已 Dev-δ merged)。运行时只需具备 `request_state_transition(**kwargs)`
    方法即可 duck-type 对接。
    """

    def request_state_transition(
        self,
        *,
        transition_id: str,
        project_id: str,
        from_state: str,
        to_state: str,
        reason: str,
        trigger_tick: str,
        evidence_refs: tuple[str, ...],
        ts: str,
        gate_id: str,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class IC01Envelope:
    """IC-01 出向载荷 value object (审计 + 重放用)。"""

    transition_id: str
    project_id: str
    from_state: State
    to_state: State
    reason: str
    trigger_tick: str
    evidence_refs: tuple[str, ...]
    ts: str
    gate_id: str | None = None


class IC01Producer:
    """L1-01 → L1-02 IC-01 出向桥。

    用法:
        producer = IC01Producer(target=stage_gate_controller)
        env, reply = producer.emit(
            project_id="pid-...",
            from_state="PLANNING",
            to_state="TDD_PLANNING",
            reason="...≥20 字",
            trigger_tick="tick-...",
            evidence_refs=("gate-xxx",),
            gate_id="gate-xxx",
        )
    """

    def __init__(
        self,
        *,
        target: StageGateTarget,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._target = target
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or generate_transition_id

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def emit(
        self,
        *,
        project_id: str,
        from_state: State,
        to_state: State,
        reason: str,
        trigger_tick: str,
        evidence_refs: tuple[str, ...],
        gate_id: str | None = None,
        transition_id: str | None = None,
        ts: str | None = None,
    ) -> tuple[IC01Envelope, dict[str, Any]]:
        """拼 IC-01 信封 + 调 target · 返回 (envelope, stage_gate_reply)。

        硬约束与 orchestrator 对齐:
          - project_id 非空 → E_TRANS_NO_PROJECT_ID
          - reason ≥ 20 字 → E_TRANS_REASON_TOO_SHORT
          - evidence_refs ≥ 1 → E_TRANS_NO_EVIDENCE
        其余字段 (state enum / transition_id 格式) 由下游 receiver (我们自己的
        orchestrator 或 Dev-δ StageGate) 再校一次 (纵深防御)。
        """
        if not project_id:
            raise StateMachineError(
                error_code=E_TRANS_NO_PROJECT_ID,
                message="project_id empty",
            )
        if not reason or len(reason) < MIN_REASON_LENGTH:
            raise StateMachineError(
                error_code=E_TRANS_REASON_TOO_SHORT,
                message=(
                    f"reason length {len(reason or '')} < "
                    f"{MIN_REASON_LENGTH}"
                ),
                project_id=project_id,
            )
        if not evidence_refs or len(evidence_refs) < 1:
            raise StateMachineError(
                error_code=E_TRANS_NO_EVIDENCE,
                message="evidence_refs minItems=1 violated",
                project_id=project_id,
            )

        tid = transition_id or self._id_factory()
        apply_ts = ts or self._iso_now()

        env = IC01Envelope(
            transition_id=tid,
            project_id=project_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            trigger_tick=trigger_tick,
            evidence_refs=tuple(evidence_refs),
            ts=apply_ts,
            gate_id=gate_id,
        )

        # 调 L1-02 · gate_id 空则透传空串 (Dev-δ controller 签名要求非 None)
        reply = self._target.request_state_transition(
            transition_id=env.transition_id,
            project_id=env.project_id,
            from_state=env.from_state,
            to_state=env.to_state,
            reason=env.reason,
            trigger_tick=env.trigger_tick,
            evidence_refs=env.evidence_refs,
            ts=env.ts,
            gate_id=env.gate_id or "",
        )
        return env, reply

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _iso_now(self) -> str:
        return (
            self._clock()
            .astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
