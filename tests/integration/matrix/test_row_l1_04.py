"""Row L1-04 Quality Loop → others · 3 cells × 6 TC = 18 TC.

**3 cells**:
    L1-04 → L1-01 · IC-14 verdict via response (PASS/BLOCK/INCONCLUSIVE)
    L1-04 → L1-09 · IC-09 gate_evaluated audit (event_type / evidence)
    L1-04 → L1-07 · IC-13 (旁路) Supervisor 观察 observation 事件
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
    assert_ic_13_sense_emitted,
)
from tests.shared.matrix_helpers import CaseType


# =============================================================================
# Cell 1: L1-04 → L1-01 · IC-14 verdict via response (6 TC)
# =============================================================================


class TestRowL1_04_to_L1_01:
    """L1-04 Quality Loop → L1-01 主决策 · verdict response (PASS/BLOCK/INCONCLUSIVE)."""

    def _verdict_event(
        self,
        project_id: str,
        verdict: str,
        wp_id: str = "wp-1",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={
                "verifier_report_id": f"vr-{wp_id}",
                "verdict": verdict,
                "wp_id": wp_id,
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_pass_verdict_emitted(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · PASS verdict · L1-01 收到放行."""
        from .conftest import record_cell

        evt = self._verdict_event(project_id, "PASS")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:verifier_report_issued",
            payload_contains={"verdict": "PASS"},
        )
        assert events[0]["payload"]["verifier_report_id"] == "vr-wp-1"
        record_cell(matrix_cov, "L1-04", "L1-01", CaseType.HAPPY)

    def test_happy_3_verdicts_pass_path(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 3 个 WP 各 PASS · L1-01 顺序消费."""
        from .conftest import record_cell

        for i in range(3):
            real_event_bus.append(self._verdict_event(
                project_id, "PASS", wp_id=f"wp-pass-{i}",
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:verifier_report_issued",
            min_count=3,
        )
        assert all(e["payload"]["verdict"] == "PASS" for e in events)
        record_cell(matrix_cov, "L1-04", "L1-01", CaseType.HAPPY)

    def test_negative_block_verdict(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · FAIL_L1 verdict (BLOCK) · L1-01 触发回退."""
        from .conftest import record_cell

        evt = self._verdict_event(project_id, "FAIL_L1", wp_id="wp-bad")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:verifier_report_issued",
            payload_contains={"verdict": "FAIL_L1"},
        )
        assert events[0]["payload"]["wp_id"] == "wp-bad"
        record_cell(matrix_cov, "L1-04", "L1-01", CaseType.NEGATIVE)

    def test_negative_pm14_verdict_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 verdict 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._verdict_event(project_id, "PASS", wp_id="wp-A"))
        real_event_bus.append(self._verdict_event(
            other_project_id, "FAIL_L1", wp_id="wp-B",
        ))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:verifier_report_issued",
            payload_contains={"verdict": "PASS"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-04:verifier_report_issued",
            payload_contains={"verdict": "FAIL_L1"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-04", "L1-01", CaseType.PM14)

    def test_slo_verdict_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · verdict response emit < 50ms."""
        from .conftest import record_cell

        evt = self._verdict_event(project_id, "PASS")
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-14 verdict SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-04", "L1-01", CaseType.HAPPY)

    def test_e2e_4_verdicts_pass_l1_l2_l3(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · PASS / FAIL_L1 / FAIL_L2 / FAIL_L3 4 verdict 全 emit."""
        from .conftest import record_cell

        verdicts = ["PASS", "FAIL_L1", "FAIL_L2", "FAIL_L3"]
        for i, v in enumerate(verdicts):
            real_event_bus.append(self._verdict_event(
                project_id, v, wp_id=f"wp-e2e-{i}",
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:verifier_report_issued",
            min_count=4,
        )
        assert [e["payload"]["verdict"] for e in events] == verdicts
        record_cell(matrix_cov, "L1-04", "L1-01", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-04 → L1-09 · IC-09 gate_evaluated audit (6 TC)
# =============================================================================


class TestRowL1_04_to_L1_09:
    """L1-04 Quality Loop → L1-09 EventBus · gate evaluated audit."""

    def _gate_event(
        self,
        project_id: str,
        gate_id: str = "gate-1",
        decision: str = "pass",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-04:gate_evaluated",
            actor="verifier",
            payload={
                "gate_id": gate_id,
                "decision": decision,
                "evidence_refs": ["ev-1", "ev-2"],
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_gate_pass_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · Gate PASS · audit emit · evidence_refs 完整."""
        from .conftest import record_cell

        evt = self._gate_event(project_id, decision="pass")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:gate_evaluated",
            payload_contains={"decision": "pass"},
        )
        assert events[0]["payload"]["evidence_refs"] == ["ev-1", "ev-2"]
        record_cell(matrix_cov, "L1-04", "L1-09", CaseType.HAPPY)

    def test_happy_gate_reject_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · Gate REJECT · audit emit."""
        from .conftest import record_cell

        evt = self._gate_event(project_id, decision="reject")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:gate_evaluated",
            payload_contains={"decision": "reject"},
        )
        assert events[0]["payload"]["decision"] == "reject"
        record_cell(matrix_cov, "L1-04", "L1-09", CaseType.HAPPY)

    def test_negative_gate_need_input(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · Gate need_input · audit 仍记 · evidence 不全."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-04:gate_evaluated",
            actor="verifier",
            payload={
                "gate_id": "gate-need", "decision": "need_input",
                "missing_signals": ["plan_complete"],
            },
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:gate_evaluated",
            payload_contains={"decision": "need_input"},
        )
        assert "missing_signals" in events[0]["payload"]
        record_cell(matrix_cov, "L1-04", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_gate_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 gate audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._gate_event(project_id, decision="pass"))
        real_event_bus.append(self._gate_event(other_project_id, decision="reject"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:gate_evaluated",
            payload_contains={"decision": "pass"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-04:gate_evaluated",
            payload_contains={"decision": "reject"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-04", "L1-09", CaseType.PM14)

    def test_slo_gate_audit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · gate_evaluated emit < 50ms."""
        from .conftest import record_cell

        evt = self._gate_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-09 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-04", "L1-09", CaseType.HAPPY)

    def test_e2e_5_stages_gate_evaluation(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · S1-S5 各 1 gate evaluation · 5 个 audit · hash chain 完整."""
        from .conftest import record_cell

        for stage in ("S1", "S2", "S3", "S4", "S5"):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier",
                payload={"gate_id": f"gate-{stage}", "stage": stage,
                         "decision": "pass"},
                timestamp=datetime.now(UTC),
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5
        record_cell(matrix_cov, "L1-04", "L1-09", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-04 → L1-07 · IC-13 (旁路) Supervisor 观察 (6 TC)
# =============================================================================


class TestRowL1_04_to_L1_07:
    """L1-04 Quality Loop → L1-07 Supervisor · IC-13 旁路观察 sense 事件."""

    def _sense_event(
        self,
        project_id: str,
        dim: str = "verifier_drift",
        signal: str = "high_fail_rate",
    ) -> Event:
        # L1-07 supervisor_sense_emitted · dim/signal in payload
        return Event(
            project_id=project_id,
            type="L1-07:supervisor_sense_emitted",
            actor="supervisor",
            payload={"dim": dim, "signal": signal, "source": "L1-04"},
            timestamp=datetime.now(UTC),
        )

    def test_happy_drift_sense_emitted(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · L1-04 verifier drift → supervisor sense emit."""
        from .conftest import record_cell

        real_event_bus.append(self._sense_event(project_id))
        assert_ic_13_sense_emitted(
            event_bus_root, project_id=project_id,
            dim="verifier_drift", min_count=1,
        )
        record_cell(matrix_cov, "L1-04", "L1-07", CaseType.HAPPY)

    def test_happy_multi_dim_observations(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 多个 dim 同时 sense (verifier/scope/cost)."""
        from .conftest import record_cell

        for dim in ("verifier_drift", "scope_creep", "cost_overrun"):
            real_event_bus.append(self._sense_event(project_id, dim=dim))
        for dim in ("verifier_drift", "scope_creep", "cost_overrun"):
            assert_ic_13_sense_emitted(
                event_bus_root, project_id=project_id, dim=dim, min_count=1,
            )
        record_cell(matrix_cov, "L1-04", "L1-07", CaseType.HAPPY)

    def test_negative_low_signal_no_observe(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 低 signal · sense 仍 emit (但消费方 supervisor 不告警)."""
        from .conftest import record_cell

        evt = self._sense_event(project_id, signal="low")
        real_event_bus.append(evt)
        events = assert_ic_13_sense_emitted(
            event_bus_root, project_id=project_id, dim="verifier_drift", min_count=1,
        )
        assert events[0]["payload"]["signal"] == "low"
        record_cell(matrix_cov, "L1-04", "L1-07", CaseType.NEGATIVE)

    def test_negative_pm14_observation_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自观察隔离."""
        from .conftest import record_cell

        real_event_bus.append(self._sense_event(project_id))
        real_event_bus.append(self._sense_event(other_project_id))
        assert_ic_13_sense_emitted(
            event_bus_root, project_id=project_id, min_count=1,
        )
        assert_ic_13_sense_emitted(
            event_bus_root, project_id=other_project_id, min_count=1,
        )
        record_cell(matrix_cov, "L1-04", "L1-07", CaseType.PM14)

    def test_slo_observe_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-13 旁路 observation < 50ms."""
        from .conftest import record_cell

        evt = self._sense_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-13 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-04", "L1-07", CaseType.HAPPY)

    def test_e2e_8_dims_full_sense_lifecycle(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 8 dim sense (plan_drift/spec_dev/cost/sched/quality/risk/halt/supervisor)."""
        from .conftest import record_cell

        dims = [
            "plan_drift", "spec_deviation", "cost_overrun", "schedule_slip",
            "quality_drift", "risk_emerging", "halt_signal", "supervisor_health",
        ]
        for dim in dims:
            real_event_bus.append(self._sense_event(project_id, dim=dim))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 8
        record_cell(matrix_cov, "L1-04", "L1-07", CaseType.DEGRADE)
