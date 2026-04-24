"""TraceabilityGuard 单元测试 · 100% 可追溯硬约束.

Goal §4.1 · 未审计的决策 · 必 raise E_AUDIT_UNAUDITED_DECISION(release blocker).
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_audit import (
    AuditError,
    E_AUDIT_UNAUDITED_DECISION,
    TraceabilityGuard,
)
from app.main_loop.decision_audit.traceability_guard import TraceabilityReport


class TestTraceabilityGuard:
    """TraceabilityGuard 单元测试."""

    def test_TC_L101_L205_G01_empty_guard_reports_100_coverage(self) -> None:
        """TC-G01 · 空 guard · coverage=1.0(分母 0)· is_full_coverage=True."""
        g = TraceabilityGuard()
        rep = g.report()
        assert rep.total_decisions == 0
        assert rep.audited_decisions == 0
        assert rep.coverage == 1.0
        assert rep.is_full_coverage is True

    def test_TC_L101_L205_G02_register_then_audit_gives_full_coverage(self) -> None:
        """TC-G02 · 登记 3 个 · audit 3 个 · coverage=100%."""
        g = TraceabilityGuard()
        for i in range(3):
            g.register_decision(f"dec-{i}", project_id="pid-A")
        for i in range(3):
            g.mark_audited(f"dec-{i}")
        rep = g.report()
        assert rep.total_decisions == 3
        assert rep.audited_decisions == 3
        assert rep.coverage == 1.0
        assert rep.unaudited_decision_ids == []

    def test_TC_L101_L205_G03_unaudited_decision_reports_partial_coverage(self) -> None:
        """TC-G03 · 登记 3 个 · audit 2 个 · coverage=2/3."""
        g = TraceabilityGuard()
        for i in range(3):
            g.register_decision(f"dec-{i}", project_id="pid-A")
        g.mark_audited("dec-0")
        g.mark_audited("dec-1")
        rep = g.report()
        assert rep.total_decisions == 3
        assert rep.audited_decisions == 2
        assert abs(rep.coverage - 2 / 3) < 1e-9
        assert "dec-2" in rep.unaudited_decision_ids
        assert rep.is_full_coverage is False

    def test_TC_L101_L205_G04_verify_all_audited_raises_on_partial(self) -> None:
        """TC-G04 · 未满 100% · verify_all_audited 必 raise E_AUDIT_UNAUDITED_DECISION."""
        g = TraceabilityGuard()
        g.register_decision("dec-pending", project_id="pid-A", tick_id="tick-1")
        with pytest.raises(AuditError) as exc:
            g.verify_all_audited()
        assert exc.value.error_code == E_AUDIT_UNAUDITED_DECISION
        assert exc.value.level == "CRITICAL"
        assert "dec-pending" in exc.value.extra.get("unaudited", [])

    def test_TC_L101_L205_G05_verify_all_audited_passes_on_full(self) -> None:
        """TC-G05 · 100% · verify_all_audited 不 raise."""
        g = TraceabilityGuard()
        g.register_decision("dec-ok", project_id="pid-A")
        g.mark_audited("dec-ok")
        g.verify_all_audited()  # 不 raise 即通过

    def test_TC_L101_L205_G06_idempotent_register(self) -> None:
        """TC-G06 · 同 decision_id 重复 register · 幂等."""
        g = TraceabilityGuard()
        g.register_decision("dec-1", project_id="pid-A")
        g.register_decision("dec-1", project_id="pid-A")
        g.register_decision("dec-1", project_id="pid-A")
        assert len(g) == 1

    def test_TC_L101_L205_G07_mark_audited_before_register_auto_registers(self) -> None:
        """TC-G07 · mark_audited 先于 register · 自动登记 · is_audited=True."""
        g = TraceabilityGuard()
        g.mark_audited("dec-orphan")
        assert g.is_audited("dec-orphan") is True
        assert g.has_decision("dec-orphan") is True
        rep = g.report()
        assert rep.audited_decisions == 1

    def test_TC_L101_L205_G08_reset_clears_state(self) -> None:
        """TC-G08 · reset · 清空台账."""
        g = TraceabilityGuard()
        g.register_decision("dec-1", project_id="pid-A")
        g.register_decision("dec-2", project_id="pid-A")
        assert len(g) == 2
        g.reset()
        assert len(g) == 0
        assert g.report().coverage == 1.0

    def test_TC_L101_L205_G09_concurrent_register_audit_thread_safe(self) -> None:
        """TC-G09 · 10 线程并发 register+audit · 最终一致."""
        import threading

        g = TraceabilityGuard()

        def worker(base: int) -> None:
            for i in range(20):
                did = f"dec-{base}-{i}"
                g.register_decision(did, project_id="pid-A")
                g.mark_audited(did)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=5)
        rep = g.report()
        assert rep.total_decisions == 200
        assert rep.audited_decisions == 200
        assert rep.is_full_coverage

    def test_TC_L101_L205_G10_recorder_registers_decision_on_record_audit(
        self,
        sut,
        mock_project_id,
        make_audit_cmd,
    ) -> None:
        """TC-G10 · Recorder 自动登记 · record_audit(decision_made) → traceability.has_decision."""
        dec_id = "dec-g10"
        cmd = make_audit_cmd(
            source_ic="IC-L2-05", action="decision_made",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_decision=dec_id,
            reason="TC-G10 decision_made 自动登记 traceability",
            evidence=["evt-1"], payload={"decision_type": "invoke_skill"},
        )
        sut.record_audit(cmd)
        assert sut.traceability.has_decision(dec_id) is True
        assert sut.traceability.is_audited(dec_id) is True
        rep = sut.traceability.report()
        assert rep.audited_decisions >= 1
        assert rep.is_full_coverage is True

    def test_TC_L101_L205_G11_recorder_unaudited_decision_raises_on_verify(
        self,
        sut,
    ) -> None:
        """TC-G11 · Recorder 通过 register_decision 注入未 audited decision · verify 必 raise."""
        sut.traceability.register_decision("dec-unaudited", project_id="pid-G11")
        with pytest.raises(AuditError) as exc:
            sut.traceability.verify_all_audited()
        assert exc.value.error_code == E_AUDIT_UNAUDITED_DECISION

    def test_TC_L101_L205_G12_report_has_coverage_property(self) -> None:
        """TC-G12 · TraceabilityReport.coverage 属性检查."""
        rep = TraceabilityReport(total_decisions=10, audited_decisions=7)
        assert abs(rep.coverage - 0.7) < 1e-9
        assert rep.is_full_coverage is False
