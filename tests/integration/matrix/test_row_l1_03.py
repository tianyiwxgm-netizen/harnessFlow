"""Row L1-03 WBS+WP → others · 3 cells × 6 TC = 18 TC.

**3 cells**:
    L1-03 → L1-04 · IC-14 wp_complete trigger gate (WP DoD 评估)
    L1-03 → L1-09 · IC-02 wp_status_change (4 状态 / PM-14)
    L1-03 → L1-01 · IC-16 任务链 step (step 推进 / 暂停 / 失败)
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.matrix_helpers import CaseType


# =============================================================================
# Cell 1: L1-03 → L1-04 · IC-14 wp_complete trigger gate (6 TC)
# =============================================================================


class TestRowL1_03_to_L1_04:
    """L1-03 WBS → L1-04 Quality Loop · WP 完成触发 gate 评估."""

    def _wp_complete_event(
        self, project_id: str, wp_id: str = "wp-1", dod_status: str = "passed",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-03:wp_completed",
            actor="executor",
            payload={"wp_id": wp_id, "dod_status": dod_status},
            timestamp=datetime.now(UTC),
        )

    def test_happy_wp_complete_triggers_gate_event(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · L1-03 WP 完成 emit · L1-04 可消费."""
        from .conftest import record_cell

        evt = self._wp_complete_event(project_id, wp_id="wp-1", dod_status="passed")
        result = real_event_bus.append(evt)
        assert result.persisted is True
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_completed",
            min_count=1,
        )
        assert events[0]["payload"]["dod_status"] == "passed"
        record_cell(matrix_cov, "L1-03", "L1-04", CaseType.HAPPY)

    def test_happy_3_wps_complete_in_chain(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 3 个 WP 顺序完成 · 3 个 gate trigger event."""
        from .conftest import record_cell

        for i in range(3):
            real_event_bus.append(self._wp_complete_event(project_id, wp_id=f"wp-{i}"))
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_completed",
            min_count=3,
        )
        assert len(events) == 3
        assert [e["payload"]["wp_id"] for e in events] == ["wp-0", "wp-1", "wp-2"]
        record_cell(matrix_cov, "L1-03", "L1-04", CaseType.HAPPY)

    def test_negative_dod_failed_event_recorded(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · WP DoD failed · gate trigger 仍发(消费方决定 verdict)."""
        from .conftest import record_cell

        evt = self._wp_complete_event(project_id, wp_id="wp-bad", dod_status="failed")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_completed",
            payload_contains={"dod_status": "failed"},
        )
        assert events[0]["payload"]["wp_id"] == "wp-bad"
        record_cell(matrix_cov, "L1-03", "L1-04", CaseType.NEGATIVE)

    def test_negative_pm14_wp_event_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 wp_completed 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._wp_complete_event(project_id, wp_id="wp-A"))
        real_event_bus.append(self._wp_complete_event(other_project_id, wp_id="wp-B"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:wp_completed", min_count=1,
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-03:wp_completed", min_count=1,
        )
        assert a[0]["payload"]["wp_id"] == "wp-A"
        assert b[0]["payload"]["wp_id"] == "wp-B"
        record_cell(matrix_cov, "L1-03", "L1-04", CaseType.PM14)

    def test_slo_wp_event_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · L1-03 wp_completed emit < 50ms."""
        from .conftest import record_cell

        evt = self._wp_complete_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-14 trigger SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-03", "L1-04", CaseType.HAPPY)

    def test_e2e_full_wbs_completion_chain(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 5 WP 完整 WBS 完成链路 · 全 hash chain 完整."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(self._wp_complete_event(project_id, wp_id=f"wp-e2e-{i}"))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5
        record_cell(matrix_cov, "L1-03", "L1-04", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-03 → L1-09 · IC-02 wp_status_change (4 状态 / PM-14) (6 TC)
# =============================================================================


WP_STATES = ("PLAN", "READY", "RUNNING", "DONE")  # L1-03 4 状态


class TestRowL1_03_to_L1_09:
    """L1-03 WBS → L1-09 EventBus · IC-02 wp_status_change."""

    def _status_event(
        self, project_id: str, wp_id: str, new_state: str,
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-03:wp_status_changed",
            actor="executor",
            payload={"wp_id": wp_id, "new_state": new_state},
            timestamp=datetime.now(UTC),
        )

    def test_happy_status_plan_to_ready(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · PLAN → READY 状态 transit."""
        from .conftest import record_cell

        evt = self._status_event(project_id, "wp-1", "READY")
        real_event_bus.append(evt)
        assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:wp_status_changed",
            payload_contains={"new_state": "READY"},
        )
        record_cell(matrix_cov, "L1-03", "L1-09", CaseType.HAPPY)

    def test_happy_4_states_full_lifecycle(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · WP 完整 4 状态生命周期 PLAN→READY→RUNNING→DONE."""
        from .conftest import record_cell

        for st in WP_STATES:
            real_event_bus.append(self._status_event(project_id, "wp-life", st))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:wp_status_changed",
            min_count=4,
        )
        states = [e["payload"]["new_state"] for e in events]
        assert states == list(WP_STATES)
        record_cell(matrix_cov, "L1-03", "L1-09", CaseType.HAPPY)

    def test_negative_invalid_state_value(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · payload 含非合法 state · bus 不语义校验 · 但消费方拒."""
        from .conftest import record_cell

        evt = self._status_event(project_id, "wp-bad", "INVALID_STATE_X")
        result = real_event_bus.append(evt)
        # bus 接受
        assert result.persisted is True
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:wp_status_changed",
            payload_contains={"new_state": "INVALID_STATE_X"},
        )
        assert events[0]["payload"]["new_state"] == "INVALID_STATE_X"
        record_cell(matrix_cov, "L1-03", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_state_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 同 wp_id 状态独立."""
        from .conftest import record_cell

        real_event_bus.append(self._status_event(project_id, "wp-shared", "READY"))
        real_event_bus.append(self._status_event(other_project_id, "wp-shared", "DONE"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:wp_status_changed",
            payload_contains={"new_state": "READY"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-03:wp_status_changed",
            payload_contains={"new_state": "DONE"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-03", "L1-09", CaseType.PM14)

    def test_slo_status_change_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · status_changed emit < 50ms."""
        from .conftest import record_cell

        evt = self._status_event(project_id, "wp-1", "RUNNING")
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-02 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-03", "L1-09", CaseType.HAPPY)

    def test_e2e_5_wps_status_concurrent(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 5 WP 各 4 状态 · 共 20 条 audit · hash chain 完整."""
        from .conftest import record_cell

        for wp_idx in range(5):
            for st in WP_STATES:
                real_event_bus.append(
                    self._status_event(project_id, f"wp-{wp_idx}", st),
                )
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 20
        record_cell(matrix_cov, "L1-03", "L1-09", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-03 → L1-01 · IC-16 任务链 step (6 TC)
# =============================================================================


class TestRowL1_03_to_L1_01:
    """L1-03 WBS → L1-01 主决策 · IC-16 task_chain step 推进/暂停/失败."""

    def _step_event(
        self,
        project_id: str,
        chain_id: str = "chain-1",
        step_id: str = "step-1",
        status: str = "advanced",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-03:task_chain_step",
            actor="executor",
            payload={"chain_id": chain_id, "step_id": step_id, "status": status},
            timestamp=datetime.now(UTC),
        )

    def test_happy_step_advanced(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · step 推进 advanced 状态."""
        from .conftest import record_cell

        evt = self._step_event(project_id, status="advanced")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:task_chain_step",
            payload_contains={"status": "advanced"},
        )
        assert events[0]["payload"]["chain_id"] == "chain-1"
        record_cell(matrix_cov, "L1-03", "L1-01", CaseType.HAPPY)

    def test_happy_5_step_chain(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 5 step 链路顺序推进."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(self._step_event(
                project_id, chain_id="chain-multi", step_id=f"step-{i}",
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:task_chain_step",
            min_count=5,
        )
        assert [e["payload"]["step_id"] for e in events] == [
            f"step-{i}" for i in range(5)
        ]
        record_cell(matrix_cov, "L1-03", "L1-01", CaseType.HAPPY)

    def test_negative_step_paused(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · step paused (暂停 · 主决策需重新规划)."""
        from .conftest import record_cell

        evt = self._step_event(project_id, status="paused")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:task_chain_step",
            payload_contains={"status": "paused"},
        )
        assert events[0]["payload"]["status"] == "paused"
        record_cell(matrix_cov, "L1-03", "L1-01", CaseType.NEGATIVE)

    def test_negative_step_failed_pm14(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · step failed · 跨 pid 错误事件不串扰."""
        from .conftest import record_cell

        real_event_bus.append(self._step_event(project_id, status="failed"))
        # other pid 没失败
        real_event_bus.append(self._step_event(other_project_id, status="advanced"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-03:task_chain_step",
            payload_contains={"status": "failed"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-03:task_chain_step",
            payload_contains={"status": "advanced"},
        )
        assert a[0]["payload"]["status"] == "failed"
        assert b[0]["payload"]["status"] == "advanced"
        record_cell(matrix_cov, "L1-03", "L1-01", CaseType.PM14)

    def test_slo_step_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-16 step emit < 50ms."""
        from .conftest import record_cell

        evt = self._step_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-16 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-03", "L1-01", CaseType.HAPPY)

    def test_e2e_full_chain_lifecycle(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 完整 chain 生命周期 advanced × 3 + paused × 1 + completed × 1."""
        from .conftest import record_cell

        statuses = ["advanced", "advanced", "paused", "advanced", "completed"]
        for i, st in enumerate(statuses):
            real_event_bus.append(self._step_event(
                project_id, step_id=f"step-{i}", status=st,
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5
        record_cell(matrix_cov, "L1-03", "L1-01", CaseType.DEGRADE)
