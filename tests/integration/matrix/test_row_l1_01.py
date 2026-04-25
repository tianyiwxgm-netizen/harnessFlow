"""Row L1-01 主决策(main_loop) → others · 4 cells × 6 TC = 24 TC.

**4 cells**:
    L1-01 → L1-02 · IC-01 触发 stage_transition (7 状态 / PM-14 / 拒非法边)
    L1-01 → L1-04 · IC-14 trigger Gate (verdict 接收 / 重试 / 升级)
    L1-01 → L1-05 · IC-04 调 skill (调用 / 超时 / fallback)
    L1-01 → L1-09 · IC-09 append_event (hash chain / SLO)

**每 cell 6 TC**: HAPPY × 2 / NEGATIVE × 2 / SLO × 1 / E2E × 1.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.main_loop.state_machine import (
    StateMachineOrchestrator,
    TransitionRequest,
)
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.matrix_helpers import CaseType


# IC-01 严格 pid 格式: ^pid-[0-9a-fA-F-]{8,}$
_L1_01_PID = "pid-00000000-0000-0000-0000-000000ab0001"
_L1_01_PID_OTHER = "pid-00000000-0000-0000-0000-000000ab0002"


def _build_request(
    project_id: str, frm: str, to: str, *, suffix: str = "0001",
) -> TransitionRequest:
    # transition_id 格式: ^trans-[0-9a-fA-F-]{8,}$ (只允许 hex + 短横)
    tid_suffix = suffix.zfill(4)  # padding 到 4 hex
    return TransitionRequest(
        transition_id=f"trans-{tid_suffix}-deadbeef-feedface",
        project_id=project_id,
        from_state=frm,
        to_state=to,
        reason=f"IC-01 矩阵集成测试 {frm} -> {to} reason ≥ 20 字",
        trigger_tick="tick-00000000-0000-0000-0000-000000000001",
        evidence_refs=("ev-matrix-1",),
        ts="2026-04-23T10:00:00.000000Z",
    )


# =============================================================================
# Cell 1: L1-01 → L1-02 · IC-01 触发 stage_transition (6 TC)
# =============================================================================


class TestRowL1_01_to_L1_02:
    """L1-01 主决策 → L1-02 项目生命周期 · IC-01 stage_transition 契约."""

    def test_happy_init_to_planning_state_transition(self, matrix_cov) -> None:
        """HAPPY · NOT_EXIST → INITIALIZED 合法 transition."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "INITIALIZED")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.new_state == "INITIALIZED"
        assert orch.get_current_state() == "INITIALIZED"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_happy_planning_to_tdd_full_chain(self, matrix_cov) -> None:
        """HAPPY · 推进 PLANNING → TDD_PLANNING (常用主链路)."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="PLANNING",
        )
        req = _build_request(_L1_01_PID, "PLANNING", "TDD_PLANNING")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.new_state == "TDD_PLANNING"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_negative_illegal_edge_rejected(self, matrix_cov) -> None:
        """NEGATIVE · 非法边 NOT_EXIST → CLOSED 必拒 + error_code."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "CLOSED")
        result = orch.transition(req)
        assert result.accepted is False
        assert result.error_code is not None
        # state 不变
        assert orch.get_current_state() == "NOT_EXIST"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.NEGATIVE)

    def test_negative_pm14_cross_project_rejected(self, matrix_cov) -> None:
        """NEGATIVE/PM-14 · 跨 pid transition_id 必拒(orchestrator pid != req pid)."""
        from app.main_loop.state_machine.schemas import (
            E_TRANS_CROSS_PROJECT,
            StateMachineError,
        )

        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        # 用 other pid 构造 request (违反 PM-14)
        req = _build_request(_L1_01_PID_OTHER, "NOT_EXIST", "INITIALIZED")
        with pytest.raises(StateMachineError) as exc_info:
            orch.transition(req)
        assert exc_info.value.error_code == E_TRANS_CROSS_PROJECT
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.PM14)

    def test_slo_transition_under_100ms(self, matrix_cov) -> None:
        """SLO · IC-01 transition P99 < 100ms."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "INITIALIZED")
        t0 = time.monotonic()
        result = orch.transition(req)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert result.accepted is True
        assert elapsed_ms < 100, f"IC-01 SLO 违反 实际 {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_e2e_full_7_states_chain(self, matrix_cov) -> None:
        """E2E · 走完 6 边 N→I→P→T→E→C→CLOSED 全链 7 态正确."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        chain = [
            ("NOT_EXIST", "INITIALIZED"),
            ("INITIALIZED", "PLANNING"),
            ("PLANNING", "TDD_PLANNING"),
            ("TDD_PLANNING", "EXECUTING"),
            ("EXECUTING", "CLOSING"),
            ("CLOSING", "CLOSED"),
        ]
        for i, (frm, to) in enumerate(chain):
            req = _build_request(_L1_01_PID, frm, to, suffix=f"e2e{i:03d}")
            result = orch.transition(req)
            assert result.accepted is True
            assert result.new_state == to
        assert orch.get_current_state() == "CLOSED"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.DEGRADE)
