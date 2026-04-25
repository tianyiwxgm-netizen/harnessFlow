"""Row L1-09 Resilience/Audit → others · 3 cells × 6 TC = 18 TC.

**3 cells**:
    L1-09 → L1-01 · IC-17 panic 100ms 全停 3 路径 (panic + resume)
    L1-09 → L1-04 · IC-18 audit_query · hash-chain verify
    L1-09 → L1-07 · IC-09 → supervisor 反馈 (audit 反向触发 supervisor)

注: brief 提到 "resume" 单独 cell · 但 EXPECTED_CELLS 只列 3 cells · 把
    panic + resume 合到 cell 1 (panic_request 含 panic / resume / pause 3 路径).
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.audit import Anchor, AnchorType, AuditQuery, QueryFilter
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    assert_panic_within_100ms,
)
from tests.shared.matrix_helpers import CaseType


# =============================================================================
# Cell 1: L1-09 → L1-01 · IC-17 panic 100ms 3 路径 (panic + resume) (6 TC)
# =============================================================================


class TestRowL1_09_to_L1_01:
    """L1-09 Resilience → L1-01 主决策 · IC-17 panic + resume 全链."""

    def _panic_event(
        self,
        project_id: str,
        reason: str = "bus_fsync_failed",
        panic_id: str = "panic-1",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-09:panic_emitted",
            actor="recoverer",
            payload={"panic_id": panic_id, "reason": reason, "scope": "tick"},
            timestamp=datetime.now(UTC),
        )

    def _resume_event(
        self,
        project_id: str,
        panic_id: str = "panic-1",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-09:resume_completed",
            actor="recoverer",
            payload={"panic_id": panic_id, "new_state": "RUNNING"},
            timestamp=datetime.now(UTC),
        )

    def test_happy_panic_bus_fsync_failed(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · panic 路径 1 · bus_fsync_failed 触发."""
        from .conftest import record_cell

        evt = self._panic_event(project_id, reason="bus_fsync_failed: ENOSPC")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-09:panic_emitted",
            payload_contains={"panic_id": "panic-1"},
        )
        assert "bus_fsync_failed" in events[0]["payload"]["reason"]
        record_cell(matrix_cov, "L1-09", "L1-01", CaseType.HAPPY)

    def test_happy_3_panic_paths_all_emitted(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 3 panic 触发路径 · bus_fsync / hash_chain / bus_write."""
        from .conftest import record_cell

        reasons = (
            "bus_fsync_failed: events.jsonl ENOSPC",
            "hash_chain_broken: prev_hash mismatch at seq=42",
            "bus_write_failed: append_atomic POSIX EIO",
        )
        for i, r in enumerate(reasons):
            real_event_bus.append(self._panic_event(
                project_id, reason=r, panic_id=f"panic-{i}",
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-09:panic_emitted", min_count=3,
        )
        emitted_reasons = [e["payload"]["reason"] for e in events]
        for r in reasons:
            assert any(r in er for er in emitted_reasons)
        record_cell(matrix_cov, "L1-09", "L1-01", CaseType.HAPPY)

    def test_negative_panic_already_paused_audit(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 重复 panic (already_paused) · audit 仍记 + error_code."""
        from .conftest import record_cell

        # 第一次 panic
        real_event_bus.append(self._panic_event(project_id, panic_id="p-1"))
        # 第二次 panic 被拒 · 但还是记 audit
        evt = Event(
            project_id=project_id,
            type="L1-09:panic_rejected",
            actor="recoverer",
            payload={"panic_id": "p-2", "error_code": "E_TICK_PANIC_ALREADY_PAUSED"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-09:panic_rejected",
            payload_contains={"error_code": "E_TICK_PANIC_ALREADY_PAUSED"},
        )
        assert events[0]["payload"]["panic_id"] == "p-2"
        record_cell(matrix_cov, "L1-09", "L1-01", CaseType.NEGATIVE)

    def test_negative_pm14_panic_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 panic audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._panic_event(project_id, panic_id="A"))
        real_event_bus.append(self._panic_event(other_project_id, panic_id="B"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-09:panic_emitted",
            payload_contains={"panic_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-09:panic_emitted",
            payload_contains={"panic_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-09", "L1-01", CaseType.PM14)

    def test_slo_panic_within_100ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-17 panic emit ≤ 100ms (HRL-04 release blocker)."""
        from .conftest import record_cell

        evt = self._panic_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        t1 = time.monotonic()
        assert_panic_within_100ms(t0, t1, budget_ms=100.0)
        record_cell(matrix_cov, "L1-09", "L1-01", CaseType.HAPPY)

    def test_e2e_panic_then_resume_chain(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · panic + resume 完整链 · 重启恢复 · hash chain 完整."""
        from .conftest import record_cell

        # 完整 panic → resume 链路 (3 panic + 3 resume)
        for i in range(3):
            real_event_bus.append(self._panic_event(
                project_id, panic_id=f"p-e2e-{i}",
                reason=f"reason-{i}",
            ))
            real_event_bus.append(self._resume_event(
                project_id, panic_id=f"p-e2e-{i}",
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 6
        record_cell(matrix_cov, "L1-09", "L1-01", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-09 → L1-04 · IC-18 audit_query hash-chain verify (6 TC)
# =============================================================================


class TestRowL1_09_to_L1_04:
    """L1-09 AuditQuery → L1-04 Quality Loop · IC-18 query_audit_trail."""

    def test_happy_query_returns_all_events(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · IC-18 query 返全部 events (供 Gate 决策)."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier",
                payload={"gate_id": f"g-{i}", "decision": "pass"},
                timestamp=datetime.now(UTC),
            ))
        aq = AuditQuery(root=event_bus_root)
        anchor = Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id,
            project_id=project_id,
        )
        trail = aq.query_audit_trail(anchor)
        assert trail.project_id == project_id
        assert trail.event_layer.count == 5
        record_cell(matrix_cov, "L1-09", "L1-04", CaseType.HAPPY)

    def test_happy_query_filter_by_event_type(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · IC-18 query 按 event_type 过滤."""
        from .conftest import record_cell

        for i in range(3):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier",
                payload={"gate_id": f"g-{i}"},
                timestamp=datetime.now(UTC),
            ))
        for i in range(2):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:rollback_pushed",
                actor="verifier",
                payload={"rollback_id": f"r-{i}"},
                timestamp=datetime.now(UTC),
            ))
        aq = AuditQuery(root=event_bus_root)
        anchor = Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id, project_id=project_id,
        )
        trail = aq.query_audit_trail(
            anchor, QueryFilter(event_type="L1-04:rollback_pushed"),
        )
        assert trail.event_layer.count == 2
        record_cell(matrix_cov, "L1-09", "L1-04", CaseType.HAPPY)

    def test_negative_query_empty_pid_raises(
        self, project_id: str, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 未注册的 pid 分片查询 · raise BusProjectNotRegistered."""
        from app.l1_09.event_bus.schemas import BusProjectNotRegistered

        from .conftest import record_cell

        # 不写任何 event · 直接查
        aq = AuditQuery(root=event_bus_root)
        anchor = Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id, project_id=project_id,
        )
        with pytest.raises(BusProjectNotRegistered):
            aq.query_audit_trail(anchor)
        record_cell(matrix_cov, "L1-09", "L1-04", CaseType.NEGATIVE)

    def test_negative_pm14_query_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 audit_query 分片隔离."""
        from .conftest import record_cell

        # pid_A 写 3 条 · pid_B 写 2 条
        for i in range(3):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier", payload={"i": i},
                timestamp=datetime.now(UTC),
            ))
        for i in range(2):
            real_event_bus.append(Event(
                project_id=other_project_id,
                type="L1-04:gate_evaluated",
                actor="verifier", payload={"i": i},
                timestamp=datetime.now(UTC),
            ))
        aq = AuditQuery(root=event_bus_root)
        # 各 pid 各自查
        ta = aq.query_audit_trail(Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id, project_id=project_id,
        ))
        tb = aq.query_audit_trail(Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=other_project_id, project_id=other_project_id,
        ))
        assert ta.event_layer.count == 3
        assert tb.event_layer.count == 2
        record_cell(matrix_cov, "L1-09", "L1-04", CaseType.PM14)

    def test_slo_query_under_500ms(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """SLO · IC-18 query P95 ≤ 500ms (§3.18)."""
        from .conftest import record_cell

        for i in range(20):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier", payload={"i": i},
                timestamp=datetime.now(UTC),
            ))
        aq = AuditQuery(root=event_bus_root)
        anchor = Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id, project_id=project_id,
        )
        t0 = time.monotonic()
        trail = aq.query_audit_trail(anchor)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 500, f"IC-18 SLO {elapsed_ms:.2f}ms"
        assert trail.event_layer.count == 20
        record_cell(matrix_cov, "L1-09", "L1-04", CaseType.HAPPY)

    def test_e2e_hash_chain_verify_no_gap(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · hash chain 跨 10 events 完整 · 无 gap."""
        from .conftest import record_cell

        for i in range(10):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier", payload={"step": i},
                timestamp=datetime.now(UTC),
            ))
        # 物理校验 hash chain 连续
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 10
        # AuditQuery 也能查到全部
        aq = AuditQuery(root=event_bus_root)
        trail = aq.query_audit_trail(Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id, project_id=project_id,
        ))
        assert trail.event_layer.count == 10
        record_cell(matrix_cov, "L1-09", "L1-04", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-09 → L1-07 · IC-09 → supervisor 反馈 (6 TC)
# =============================================================================


class TestRowL1_09_to_L1_07:
    """L1-09 EventBus → L1-07 Supervisor · 反向触发 supervisor sense."""

    def _audit_to_sup_event(
        self,
        project_id: str,
        event_id: str = "audit-1",
        signal_kind: str = "anomaly",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-07:supervisor_sense_emitted",
            actor="supervisor",
            payload={
                "source_event_id": event_id,
                "dim": "audit_anomaly",
                "signal": signal_kind,
                "source": "L1-09",
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_audit_anomaly_triggers_sense(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · L1-09 audit 异常 → supervisor sense emit."""
        from .conftest import record_cell

        evt = self._audit_to_sup_event(project_id, signal_kind="hash_gap")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_sense_emitted",
            payload_contains={"source": "L1-09"},
        )
        assert events[0]["payload"]["signal"] == "hash_gap"
        record_cell(matrix_cov, "L1-09", "L1-07", CaseType.HAPPY)

    def test_happy_3_anomaly_kinds_all_sense(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 3 类 audit 异常各自触发 supervisor sense."""
        from .conftest import record_cell

        for kind in ("hash_gap", "fsync_slow", "panic_burst"):
            real_event_bus.append(self._audit_to_sup_event(
                project_id, signal_kind=kind,
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_sense_emitted",
            min_count=3,
        )
        signals = {e["payload"]["signal"] for e in events}
        assert signals == {"hash_gap", "fsync_slow", "panic_burst"}
        record_cell(matrix_cov, "L1-09", "L1-07", CaseType.HAPPY)

    def test_negative_no_anomaly_no_sense(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 正常 audit · 不触发 supervisor sense (空)."""
        from .conftest import record_cell

        # 写正常 audit · 不触发 sense
        real_event_bus.append(Event(
            project_id=project_id,
            type="L1-04:gate_evaluated",
            actor="verifier", payload={"normal": True},
            timestamp=datetime.now(UTC),
        ))
        # 不应有 supervisor_sense_emitted
        from tests.shared.ic_assertions import list_events
        sense_events = list_events(
            event_bus_root, project_id,
            type_exact="L1-07:supervisor_sense_emitted",
        )
        assert sense_events == []
        record_cell(matrix_cov, "L1-09", "L1-07", CaseType.NEGATIVE)

    def test_negative_pm14_sense_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 supervisor sense 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._audit_to_sup_event(project_id, event_id="A"))
        real_event_bus.append(self._audit_to_sup_event(
            other_project_id, event_id="B",
        ))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_sense_emitted",
            payload_contains={"source_event_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-07:supervisor_sense_emitted",
            payload_contains={"source_event_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-09", "L1-07", CaseType.PM14)

    def test_slo_sense_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · L1-09 → supervisor sense emit < 50ms."""
        from .conftest import record_cell

        evt = self._audit_to_sup_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"L1-09 → L1-07 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-09", "L1-07", CaseType.HAPPY)

    def test_e2e_audit_burst_triggers_5_sense(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 5 个 audit 异常事件 → 5 supervisor sense · hash chain."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(self._audit_to_sup_event(
                project_id, event_id=f"a-{i}", signal_kind=f"sig-{i}",
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5
        record_cell(matrix_cov, "L1-09", "L1-07", CaseType.DEGRADE)
