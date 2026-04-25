"""scenario_02 · S1→S7 完整 7 阶段端到端 · 共享 fixtures.

**真实组件**:
    - L1-09 EventBus(IC-09 唯一写入口) · 真 hash chain
    - L2-01 StageGateController(IC-01 唯一发起方) · 真 7 阶段 + 12 合法转换
    - L2-04 SnapshotJob / RecoveryAttempt(便于 e2e/T17 回放)
    - audit-ledger 落盘 events.jsonl + 校验 hash chain 完整

**注入**:
    - L1-01 state_machine 用 spy(记录 IC-01 调用 + 默认 ok=True)
    - 注入 EventBus 进 StageGateController.event_bus(append_event 适配 L1-09 真 schema)

**PID 约定**: pid=`proj-acceptance-02` · 全部 evidence + audit 落 projects/<pid>/
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.project_lifecycle.stage_gate import StageGateController
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    """scenario 02 默认 pid."""
    return "proj-acceptance-02"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 物理根 · 每 TC 独立."""
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · IC-09 唯一写入口 · hash chain."""
    return EventBus(event_bus_root)


# ============================================================================
# IC-09 适配器 · 把 L2-01 的 EventSink 协议 (append_event(project_id,event_type,payload))
# 桥接到真 L1-09 EventBus(append(Event)).
# ============================================================================


class _StageGateBusAdapter:
    """将 StageGateController 的 EventSink 协议 → L1-09 EventBus.append(Event)."""

    def __init__(self, real_bus: EventBus) -> None:
        self._bus = real_bus
        self.calls: list[dict[str, Any]] = []

    def append_event(
        self,
        *,
        project_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        # L2-01 的 event_type 是 free-form(如 'gate_decision_computed') ·
        # L1-09 要 L1-XX:event 前缀 · 加 L1-02: 表示 stage_gate 域
        full_type = f"L1-02:{event_type}" if ":" not in event_type else event_type
        evt = Event(
            project_id=project_id,
            type=full_type,
            actor="planner",  # L2-01 stage_gate 由 planner 角色驱动
            timestamp=datetime.now(UTC),
            payload=dict(payload),
        )
        self._bus.append(evt)
        self.calls.append({
            "project_id": project_id,
            "event_type": full_type,
            "payload": payload,
        })


@pytest.fixture
def stage_gate_bus(real_event_bus: EventBus) -> _StageGateBusAdapter:
    """L2-01 用的 EventSink 适配器 · 内部转发到真 L1-09."""
    return _StageGateBusAdapter(real_event_bus)


# ============================================================================
# L1-01 state_machine spy(记录 IC-01 transition_request)
# ============================================================================


class _L1_01_StateMachineSpy:
    """记录每次 request_state_transition 调用 · 默认 ok=True."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._ok = True

    def set_ok(self, ok: bool) -> None:
        self._ok = ok

    def request_state_transition(self, **kwargs) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"ok": self._ok, "ic_01_tx_id": f"tx-{len(self.calls)}"}


@pytest.fixture
def l1_01_spy() -> _L1_01_StateMachineSpy:
    """L1-01 IC-01 spy · 记录全部 state_transition."""
    return _L1_01_StateMachineSpy()


@pytest.fixture
def stage_gate(
    stage_gate_bus: _StageGateBusAdapter,
    l1_01_spy: _L1_01_StateMachineSpy,
) -> StageGateController:
    """真 StageGateController · IC-01 + IC-09 双轨."""
    return StageGateController(
        event_bus=stage_gate_bus,
        l1_01_state_machine=l1_01_spy,
    )


# ============================================================================
# 7 阶段 evidence 工厂 · 按 stage_gate.controller._REQUIRED_SIGNALS_BY_STAGE 配齐
# ============================================================================


_STAGE_SIGNALS: dict[str, tuple[str, ...]] = {
    "S1": ("charter_ready", "stakeholders_ready", "goal_anchor_hash_locked"),
    "S2": ("4_pieces_ready", "9_plans_ready", "togaf_ready", "wbs_ready"),
    "S3": ("tdd_blueprint_ready",),
    "S5": ("s5_pass",),
    "S7": ("delivery_bundled", "retro_ready", "archive_written"),
}


def make_evidence(
    project_id: str,
    stage: str,
    *,
    request_id: str | None = None,
    signals: tuple[str, ...] | None = None,
):
    """按 stage 构造 EvidenceBundle · 默认填全 required signals."""
    from app.project_lifecycle.stage_gate import EvidenceBundle

    if signals is None:
        signals = _STAGE_SIGNALS.get(stage, ())
    return EvidenceBundle(
        project_id=project_id,
        stage=stage,  # type: ignore[arg-type]
        request_id=request_id or f"req-{stage}-{id(signals)}",
        signals=signals,
        caller_l2="L2-02",
    )


@pytest.fixture
def evidence_factory(project_id: str):
    """工厂 · stage → EvidenceBundle · TC 内可配置 missing signals."""
    def _mk(stage: str, *, request_id: str | None = None, signals=None):
        return make_evidence(project_id, stage, request_id=request_id, signals=signals)
    return _mk


# ============================================================================
# 阶段切换助手 · 把 stage 推进 1 步(request_decision → user approve → IC-01)
# ============================================================================


@pytest.fixture
def advance_stage(stage_gate: StageGateController, project_id: str):
    """driver helper · 推进 1 阶段(等价 evidence pass + user approve).

    返回 (gate_id, transition_result).
    """
    def _advance(
        stage: str,
        *,
        current_state: str = "INITIALIZED",
        signals: tuple[str, ...] | None = None,
        request_id: str | None = None,
    ):
        from app.project_lifecycle.stage_gate.controller import _STAGE_TRANSITION_MAP

        ev = make_evidence(project_id, stage, request_id=request_id, signals=signals)
        dec = stage_gate.request_gate_decision(ev, current_state=current_state)  # type: ignore[arg-type]
        if dec.decision != "pass":
            return dec, None
        result = stage_gate.receive_user_decision(
            gate_id=dec.gate_id,
            user_decision="approve",
            reason=f"user approved {stage} gate after evidence review",
        )
        return dec, result

    return _advance


# ============================================================================
# L1-09 Snapshot/Recovery(便于 T16 中途崩溃恢复)
# ============================================================================


@pytest.fixture
def snapshot_job(real_event_bus: EventBus, event_bus_root: Path):
    """L1-09 SnapshotJob · 给 e2e/T16 用."""
    from app.l1_09.checkpoint import SnapshotJob

    # SnapshotJob 接 read_range · 真 EventBus 已实现
    return SnapshotJob(event_bus_root, event_bus=real_event_bus)


@pytest.fixture
def recovery_attempt(real_event_bus: EventBus, event_bus_root: Path):
    """L1-09 RecoveryAttempt · 给 T16/T17 中途崩溃 + 恢复用."""
    from app.l1_09.checkpoint import RecoveryAttempt

    return RecoveryAttempt(event_bus_root, event_bus=real_event_bus)
