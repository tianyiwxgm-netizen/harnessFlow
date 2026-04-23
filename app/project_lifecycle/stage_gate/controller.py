"""L2-01 StageGateController · IC-01 唯一发起方 · 对齐 tech §3 + §6。

核心职责：
  1. request_gate_decision(evidence) → pass / reject / need_input
  2. receive_user_decision(gate_id, decision) · 处理 IC-17 用户决定
  3. authorize_transition(from, to, gate_id) · IC-01 唯一发起方（只内部可调）
  4. rollback_gate(gate_id) · Re-open + re_open_count
  5. query_gate_state()

硬约束：
  - GATE_AUTO_TIMEOUT_ENABLED=true · 启动 crash（tech §10）
  - authorize_transition 只能本实例内部调 · 外部 caller != 'L2-01' 拒（PM-14 越权）
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Protocol

from app.project_lifecycle.stage_gate.errors import (
    E_GATE_EVIDENCE_MISSING,
    E_HISTORY_QUOTA_EXCEEDED,
    E_PM14_OWNERSHIP_VIOLATION,
    E_TRANSITION_FORBIDDEN,
    StageGateError,
    StartupConfigError,
)
from app.project_lifecycle.stage_gate.ic_16_stub import (
    UIBridge,
    build_push_stage_gate_card_command,
)
from app.project_lifecycle.stage_gate.schemas import (
    Decision,
    EvidenceBundle,
    GateDecision,
    GateStateSnapshot,
    ProjectState,
    RollbackResult,
    Stage,
    TransitionResult,
    UserDecision,
)
from app.project_lifecycle.stage_gate.state_machine import validate_transition


_STAGE_TRANSITION_MAP: dict[Stage, tuple[ProjectState, ProjectState]] = {
    "S1": ("INITIALIZED", "PLANNING"),
    "S2": ("PLANNING", "TDD_PLANNING"),
    "S3": ("TDD_PLANNING", "EXECUTING"),
    "S5": ("EXECUTING", "CLOSING"),
    "S7": ("CLOSING", "CLOSED"),
}

_REQUIRED_SIGNALS_BY_STAGE: dict[Stage, tuple[str, ...]] = {
    "S1": ("charter_ready", "stakeholders_ready", "goal_anchor_hash_locked"),
    "S2": ("4_pieces_ready", "9_plans_ready", "togaf_ready", "wbs_ready"),
    "S3": ("tdd_blueprint_ready",),
    "S5": ("s5_pass",),
    "S7": ("delivery_bundled", "retro_ready", "archive_written"),
}


class EventSink(Protocol):
    def append_event(
        self, *, project_id: str, event_type: str, payload: dict[str, Any],
    ) -> None: ...


class L1_01_StateMachine(Protocol):
    """L1-01 L2-03 主状态机 · authorize_transition 最终调它。

    入参对齐 ic-contracts.md §3.1.2（state_transition_request）:
      required: [transition_id, project_id, from, to, reason, trigger_tick,
                 evidence_refs, ts]
      optional: gate_id
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
    ) -> dict[str, Any]: ...


_MAX_RE_OPEN = 10
_MAX_GATE_HISTORY = 200


class StageGateController:
    """L2-01 · 3 元决策 + 状态机授权 + re-open。

    启动配置校验：若环境变量或 config 显式 enable GATE_AUTO_TIMEOUT · 直接 raise StartupConfigError。
    """

    def __init__(
        self,
        *,
        event_bus: EventSink,
        l1_01_state_machine: L1_01_StateMachine,
        config: dict[str, Any] | None = None,
        ui_bridge: UIBridge | None = None,
    ) -> None:
        config = config or {}
        # 硬约束：GATE_AUTO_TIMEOUT_ENABLED=true 启动 crash
        if config.get("GATE_AUTO_TIMEOUT_ENABLED", False) is True:
            raise StartupConfigError(
                "GATE_AUTO_TIMEOUT_ENABLED=true is forbidden (Gate 必须用户硬门 · 禁自动放行)"
            )
        # env 变量也拉
        if os.environ.get("HARNESSFLOW_GATE_AUTO_TIMEOUT_ENABLED", "").lower() == "true":
            raise StartupConfigError(
                "env HARNESSFLOW_GATE_AUTO_TIMEOUT_ENABLED=true is forbidden"
            )

        self._event_bus = event_bus
        self._l1_01 = l1_01_state_machine
        self._ui_bridge = ui_bridge  # IC-16 · Dev-θ L1-10 真实 UI 接入前可为 None
        self._gate_history: dict[str, GateStateSnapshot] = {}
        self._re_open_counts: dict[tuple[str, Stage], int] = {}
        self._decisions_by_request: dict[str, GateDecision] = {}  # 幂等

    # ---- public API 1/5 ----

    def request_gate_decision(
        self,
        evidence: EvidenceBundle,
        *,
        current_state: ProjectState = "INITIALIZED",
    ) -> GateDecision:
        # 幂等
        if evidence.request_id in self._decisions_by_request:
            return self._decisions_by_request[evidence.request_id]

        missing = self._compute_missing_signals(evidence)
        if missing:
            dec = GateDecision(
                gate_id=self._mint_gate_id(evidence.project_id, evidence.stage),
                project_id=evidence.project_id,
                stage=evidence.stage,
                decision="need_input",
                reason=f"missing signals: {missing}",
                missing_signals=missing,
            )
        else:
            from_state, to_state = _STAGE_TRANSITION_MAP.get(
                evidence.stage, (current_state, current_state),
            )
            dec = GateDecision(
                gate_id=self._mint_gate_id(evidence.project_id, evidence.stage),
                project_id=evidence.project_id,
                stage=evidence.stage,
                decision="pass",
                reason=f"all {len(evidence.signals)} signals present",
                from_state=from_state,
                to_state=to_state,
            )

        # 记录 gate 状态
        self._gate_history[dec.gate_id] = GateStateSnapshot(
            gate_id=dec.gate_id,
            project_id=dec.project_id,
            stage=dec.stage,
            state="OPEN" if dec.decision == "pass" else "WAITING",
            created_at_ns=time.time_ns(),
        )
        self._decisions_by_request[evidence.request_id] = dec

        # IC-09 审计
        self._event_bus.append_event(
            project_id=evidence.project_id,
            event_type="gate_decision_computed",
            payload={
                "gate_id": dec.gate_id,
                "stage": evidence.stage,
                "decision": dec.decision,
                "missing_signals": list(dec.missing_signals),
            },
        )

        # IC-16 § 3.16 · Gate pass 后推 UI 卡片
        if dec.decision == "pass":
            self._push_gate_card(
                gate_id=dec.gate_id,
                project_id=dec.project_id,
                stage_name=dec.stage,
                trim_level=self._trim_level_from(evidence),
            )

        self._enforce_history_quota()
        return dec

    # ---- public API 2/5 ----

    def authorize_transition(
        self,
        *,
        project_id: str,
        from_state: ProjectState,
        to_state: ProjectState,
        gate_id: str,
        reason: str,
        caller: str = "L2-01",  # PM-14 硬锁 · 只内部调
        trigger_tick: str | None = None,
        evidence_refs: tuple[str, ...] | None = None,
    ) -> TransitionResult:
        """IC-01 §3.1.2 · 发送 state_transition_request。

        ic-contracts.md §3.1.2 必填字段：
          - transition_id: 本方法生成 trans-{uuid} · 幂等键
          - project_id / from / to / reason / gate_id（optional）
          - trigger_tick: 若调用方未传 · 从 gate_id 派生
          - evidence_refs: minItems=1 · 若未传 · 默认 (gate_id,)
          - ts: ISO-8601 utc · 本方法自动生成
        """
        if caller != "L2-01":
            raise StageGateError(
                error_code=E_PM14_OWNERSHIP_VIOLATION,
                message=f"only L2-01 may authorize_transition · caller={caller!r}",
                caller_l2=caller,
                project_id=project_id,
            )
        if not reason or len(reason) < 20:
            raise StageGateError(
                error_code=E_TRANSITION_FORBIDDEN,
                message=f"reason too short (< 20 chars): {reason!r}",
                project_id=project_id,
            )
        # §3.1.2 evidence_refs minItems=1 · 默认填 (gate_id,)
        if evidence_refs is None:
            evidence_refs = (gate_id,)
        if not evidence_refs or len(evidence_refs) < 1:
            raise StageGateError(
                error_code=E_TRANSITION_FORBIDDEN,
                message="evidence_refs minItems=1 violated (§3.1.2)",
                project_id=project_id,
            )
        validate_transition(from_state, to_state, project_id=project_id)

        # §3.1.2 必填字段生成
        transition_id = f"trans-{uuid.uuid4()}"
        ts = (
            datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
        # trigger_tick 若未传 · 从 gate_id 派生保证追溯链非空
        if trigger_tick is None:
            trigger_tick = f"tick-{gate_id}"

        # 发 IC-01 · §3.1.2 9 字段完整
        ic01_result = self._l1_01.request_state_transition(
            transition_id=transition_id,
            project_id=project_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            trigger_tick=trigger_tick,
            evidence_refs=tuple(evidence_refs),
            ts=ts,
            gate_id=gate_id,
        )
        ok = bool(ic01_result.get("ok", True))

        # IC-09 审计
        self._event_bus.append_event(
            project_id=project_id,
            event_type="state_transition_authorized",
            payload={
                "from": from_state, "to": to_state,
                "gate_id": gate_id, "ok": ok,
            },
        )
        return TransitionResult(
            project_id=project_id,
            from_state=from_state,
            to_state=to_state,
            gate_id=gate_id,
            success=ok,
            emitted_ic01=True,
            reason=reason,
        )

    # ---- public API 3/5 ----

    def receive_user_decision(
        self,
        *,
        gate_id: str,
        user_decision: UserDecision,
        change_requests: tuple[str, ...] = (),
        reason: str = "",
    ) -> dict[str, Any]:
        if gate_id not in self._gate_history:
            raise StageGateError(
                error_code=E_GATE_EVIDENCE_MISSING,
                message=f"gate {gate_id!r} not in history",
            )
        snap = self._gate_history[gate_id]
        pid = snap.project_id

        if user_decision == "approve":
            # 触发 authorize_transition
            from_state, to_state = _STAGE_TRANSITION_MAP.get(
                snap.stage, ("INITIALIZED", "PLANNING"),
            )
            transition_reason = reason or f"user approved S{snap.stage[1:]} gate {gate_id}"
            result = self.authorize_transition(
                project_id=pid,
                from_state=from_state,
                to_state=to_state,
                gate_id=gate_id,
                reason=transition_reason,
                caller="L2-01",
            )
            self._gate_history[gate_id] = replace(
                snap, state="CLOSED", last_decision_at_ns=time.time_ns(),
            )
            self._event_bus.append_event(
                project_id=pid, event_type="gate_closed",
                payload={"gate_id": gate_id, "user_decision": "approve"},
            )
            return {"user_decision": "approve", "transition_success": result.success}

        if user_decision == "reject":
            rollback = self.rollback_gate(gate_id, change_requests=change_requests)
            return {
                "user_decision": "reject",
                "re_open_count": rollback.new_re_open_count,
                "change_requests": list(change_requests),
            }

        # request_change · ANALYZING
        self._gate_history[gate_id] = replace(snap, state="ANALYZING")
        self._event_bus.append_event(
            project_id=pid, event_type="gate_analyzing",
            payload={"gate_id": gate_id, "change_requests": list(change_requests)},
        )
        return {"user_decision": "request_change", "state": "ANALYZING"}

    # ---- public API 4/5 ----

    def rollback_gate(
        self,
        gate_id: str,
        *,
        change_requests: tuple[str, ...] = (),
    ) -> RollbackResult:
        if gate_id not in self._gate_history:
            raise StageGateError(
                error_code=E_GATE_EVIDENCE_MISSING,
                message=f"gate {gate_id!r} not found",
            )
        snap = self._gate_history[gate_id]
        key = (snap.project_id, snap.stage)
        current = self._re_open_counts.get(key, 0)
        new_count = current + 1
        if new_count > _MAX_RE_OPEN:
            raise StageGateError(
                error_code=E_HISTORY_QUOTA_EXCEEDED,
                message=f"re_open_count={new_count} > MAX_RE_OPEN={_MAX_RE_OPEN}",
                project_id=snap.project_id,
            )
        self._re_open_counts[key] = new_count
        self._gate_history[gate_id] = replace(
            snap, state="REROUTING", last_decision_at_ns=time.time_ns(),
        )
        self._event_bus.append_event(
            project_id=snap.project_id, event_type="gate_rolled_back",
            payload={
                "gate_id": gate_id,
                "re_open_count": new_count,
                "change_requests": list(change_requests),
            },
        )
        return RollbackResult(
            project_id=snap.project_id,
            gate_id=gate_id,
            new_re_open_count=new_count,
            change_requests=change_requests,
        )

    # ---- public API 5/5 ----

    def query_gate_state(self, gate_id: str) -> GateStateSnapshot | None:
        return self._gate_history.get(gate_id)

    def query_gates_by_project(self, project_id: str) -> list[GateStateSnapshot]:
        return [s for s in self._gate_history.values() if s.project_id == project_id]

    # ---- internals ----

    def _compute_missing_signals(self, evidence: EvidenceBundle) -> tuple[str, ...]:
        required = set(_REQUIRED_SIGNALS_BY_STAGE.get(evidence.stage, ()))
        return tuple(sorted(required - set(evidence.signals)))

    @staticmethod
    def _trim_level_from(evidence: EvidenceBundle) -> str:
        """EvidenceBundle.trim_level (full|minimal|custom) → §3.16 enum (minimal|standard|full)。"""
        mapping = {"full": "full", "minimal": "minimal", "custom": "standard"}
        return mapping.get(evidence.trim_level, "standard")

    def _push_gate_card(
        self,
        *,
        gate_id: str,
        project_id: str,
        stage_name: str,
        trim_level: str,
    ) -> None:
        """IC-16 § 3.16 · Gate pass 后推 UI 卡片。

        - ui_bridge 注入（Dev-θ L1-10 真实 UI 可用）→ delegate
        - 未注入 → 降级为 IC-09 事件 ic_16_push_stage_gate_card（审计可追溯）
        """
        command = build_push_stage_gate_card_command(
            gate_id=gate_id,
            project_id=project_id,
            stage_name=stage_name,
            trim_level=trim_level,
        )
        if self._ui_bridge is not None:
            self._ui_bridge.push_stage_gate_card_to_ui(command=command)
        # 无论 ui_bridge 是否存在 · 审计事件都发（§3.16.7 IC-09 审计路径）
        self._event_bus.append_event(
            project_id=project_id,
            event_type="ic_16_push_stage_gate_card",
            payload=command,
        )

    @staticmethod
    def _mint_gate_id(project_id: str, stage: Stage) -> str:
        return f"gate-{project_id[:8]}-{stage}-{uuid.uuid4().hex[:8]}"

    def _enforce_history_quota(self) -> None:
        if len(self._gate_history) > _MAX_GATE_HISTORY:
            # 淘汰最老 · 按 created_at 排序
            sorted_by_age = sorted(
                self._gate_history.values(),
                key=lambda s: s.created_at_ns,
            )
            while len(self._gate_history) > _MAX_GATE_HISTORY and sorted_by_age:
                oldest = sorted_by_age.pop(0)
                self._gate_history.pop(oldest.gate_id, None)
