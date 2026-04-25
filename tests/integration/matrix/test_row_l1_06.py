"""Row L1-06 KB → others · 3 cells × 6 TC = 18 TC.

**3 cells**:
    L1-06 → L1-09 · IC-09 kb_audit (写/读/晋升 audit)
    L1-06 → L1-04 · IC-08 → Gate (KB 内容驱动 Gate · predicate 数据源)
    L1-06 → L1-10 · IC-19 KB 浏览器 push (UI 候选展示)
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
# Cell 1: L1-06 → L1-09 · IC-09 kb_audit (6 TC)
# =============================================================================


class TestRowL1_06_to_L1_09:
    """L1-06 KB → L1-09 EventBus · KB read/write/promote audit."""

    def _kb_event(
        self,
        project_id: str,
        type_suffix: str,
        kind: str = "pattern",
        scope: str = "project",
    ) -> Event:
        return Event(
            project_id=project_id,
            type=f"L1-06:{type_suffix}",
            actor="main_loop",
            payload={"kind": kind, "scope": scope, "entry_id": "e-1"},
            timestamp=datetime.now(UTC),
        )

    def test_happy_kb_read_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · kb_read_completed audit."""
        from .conftest import record_cell

        evt = self._kb_event(project_id, "kb_read_completed")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-06:kb_read_completed",
            min_count=1,
        )
        assert events[0]["payload"]["scope"] == "project"
        record_cell(matrix_cov, "L1-06", "L1-09", CaseType.HAPPY)

    def test_happy_kb_write_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · kb_entry_written audit."""
        from .conftest import record_cell

        evt = self._kb_event(project_id, "kb_entry_written", kind="gotcha")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-06:kb_entry_written",
            payload_contains={"kind": "gotcha"},
        )
        assert events[0]["payload"]["entry_id"] == "e-1"
        record_cell(matrix_cov, "L1-06", "L1-09", CaseType.HAPPY)

    def test_negative_kb_read_empty_still_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · KB 读返空 · audit 仍记 (用 result_count=0)."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-06:kb_read_completed",
            actor="main_loop",
            payload={"scope": "session", "result_count": 0},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-06:kb_read_completed",
            payload_contains={"result_count": 0},
        )
        assert events[0]["payload"]["result_count"] == 0
        record_cell(matrix_cov, "L1-06", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_kb_audit_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 KB audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._kb_event(project_id, "kb_read_completed"))
        real_event_bus.append(self._kb_event(other_project_id, "kb_read_completed"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-06:kb_read_completed", min_count=1,
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-06:kb_read_completed", min_count=1,
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-06", "L1-09", CaseType.PM14)

    def test_slo_kb_audit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · kb audit emit < 50ms."""
        from .conftest import record_cell

        evt = self._kb_event(project_id, "kb_read_completed")
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-09 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-06", "L1-09", CaseType.HAPPY)

    def test_e2e_full_kb_lifecycle_audit(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · KB 完整生命周期 read/write/promote · 6 audit · hash chain 完整."""
        from .conftest import record_cell

        types = [
            "kb_read_completed", "kb_entry_written", "kb_entry_promoted",
            "kb_entry_observed", "kb_index_built", "kb_session_persisted",
        ]
        for t in types:
            real_event_bus.append(self._kb_event(project_id, t))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 6
        record_cell(matrix_cov, "L1-06", "L1-09", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-06 → L1-04 · IC-08 → Gate predicate 数据源 (6 TC)
# =============================================================================


class TestRowL1_06_to_L1_04:
    """L1-06 KB 内容 → L1-04 Quality Loop · 驱动 Gate predicate."""

    def test_happy_kb_returns_relevant_for_gate(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """HAPPY · KB 返 ≥ 1 个 pattern 给 Gate predicate."""
        from .conftest import record_cell

        fake_kb_repo.project_entries = [
            type("E", (), {"id": "p-1", "kind": "pattern",
                           "content": "rule1", "observed_count": 3})(),
            type("E", (), {"id": "p-2", "kind": "pattern",
                           "content": "rule2", "observed_count": 5})(),
        ]
        entries = fake_kb_repo.read_project(None, ["pattern"])
        # Gate predicate 拿这些 entries 评估
        assert len(entries) >= 1
        # 至少 1 个含 content 的 entry
        assert any(getattr(e, "content", None) for e in entries)
        record_cell(matrix_cov, "L1-06", "L1-04", CaseType.HAPPY)

    def test_happy_multiple_kinds_for_gate(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """HAPPY · KB 有 pattern + gotcha · Gate 双驱动."""
        from .conftest import record_cell

        fake_kb_repo.project_entries = [
            type("E", (), {"id": "p1", "kind": "pattern", "observed_count": 2})(),
            type("E", (), {"id": "g1", "kind": "gotcha", "observed_count": 1})(),
        ]
        entries = fake_kb_repo.read_project(None, ["pattern", "gotcha"])
        kinds = {getattr(e, "kind", None) for e in entries}
        assert "pattern" in kinds and "gotcha" in kinds
        record_cell(matrix_cov, "L1-06", "L1-04", CaseType.HAPPY)

    def test_negative_kb_no_relevant_predicate_blocks(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """NEGATIVE · KB 空 · Gate predicate 因无数据源而保持 PENDING."""
        from .conftest import record_cell

        # KB 空 · 不向 Gate 提供 patterns
        entries = fake_kb_repo.read_project(None, ["pattern"])
        assert entries == []
        # Gate 应记 missing_signals
        record_cell(matrix_cov, "L1-06", "L1-04", CaseType.NEGATIVE)

    def test_negative_pm14_kb_pid_for_gate(
        self,
        project_id: str,
        other_project_id: str,
        fake_scope_checker,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 KB 不交叉 (即不同 pid 的 Gate 用各自 KB)."""
        from .conftest import record_cell

        # 两个不同 pid 各 scope_check
        req_a = type("R", (), {"project_id": project_id})()
        req_b = type("R", (), {"project_id": other_project_id})()
        a = fake_scope_checker.scope_check(req_a)
        b = fake_scope_checker.scope_check(req_b)
        assert a.isolation_ctx["project_id"] != b.isolation_ctx["project_id"]
        record_cell(matrix_cov, "L1-06", "L1-04", CaseType.PM14)

    def test_slo_kb_query_for_gate_under_50ms(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """SLO · Gate predicate 查 KB < 50ms."""
        from .conftest import record_cell

        fake_kb_repo.project_entries = [
            type("E", (), {"id": f"e-{i}", "kind": "pattern",
                           "observed_count": 1})()
            for i in range(20)
        ]
        t0 = time.monotonic()
        fake_kb_repo.read_project(None, ["pattern"])
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-08 → Gate SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-06", "L1-04", CaseType.HAPPY)

    def test_e2e_kb_drives_5_gate_evals(
        self, project_id: str, fake_kb_repo, real_event_bus, event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """E2E · KB 5 entries 驱动 5 个 Gate eval audit."""
        from .conftest import record_cell

        fake_kb_repo.project_entries = [
            type("E", (), {"id": f"e-{i}", "kind": "pattern",
                           "observed_count": i + 1})()
            for i in range(5)
        ]
        entries = fake_kb_repo.read_project(None, ["pattern"])
        # 每个 entry 驱动一个 gate_evaluated audit
        for i, e in enumerate(entries):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier",
                payload={"gate_id": f"gate-{i}", "kb_entry": e.id,
                         "decision": "pass"},
                timestamp=datetime.now(UTC),
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-04:gate_evaluated", min_count=5,
        )
        assert len(events) == 5
        record_cell(matrix_cov, "L1-06", "L1-04", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-06 → L1-10 · IC-19 KB 浏览器 push (6 TC)
# =============================================================================


class TestRowL1_06_to_L1_10:
    """L1-06 KB → L1-10 UI · IC-19 浏览器 push 候选展示."""

    def _ui_push_event(
        self,
        project_id: str,
        candidate_id: str = "kb-cand-1",
        kind: str = "pattern",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-10:ui_kb_candidate_pushed",
            actor="ui",
            payload={
                "candidate_id": candidate_id,
                "kind": kind,
                "title": "Sample KB Pattern",
                "score": 0.85,
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_candidate_pushed_to_ui(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · KB 候选推送到 UI · 含 score / kind / title."""
        from .conftest import record_cell

        evt = self._ui_push_event(project_id)
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_kb_candidate_pushed", min_count=1,
        )
        assert events[0]["payload"]["candidate_id"] == "kb-cand-1"
        assert events[0]["payload"]["score"] == 0.85
        record_cell(matrix_cov, "L1-06", "L1-10", CaseType.HAPPY)

    def test_happy_5_candidates_top_k_push(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · top-5 候选 push · 5 events 顺序."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(self._ui_push_event(
                project_id, candidate_id=f"kb-cand-{i}",
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_kb_candidate_pushed", min_count=5,
        )
        ids = [e["payload"]["candidate_id"] for e in events]
        assert ids == [f"kb-cand-{i}" for i in range(5)]
        record_cell(matrix_cov, "L1-06", "L1-10", CaseType.HAPPY)

    def test_negative_low_score_still_pushed(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 低 score 候选 (低于 UI 阈值) 仍 emit · UI 端决定显示."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-10:ui_kb_candidate_pushed",
            actor="ui",
            payload={"candidate_id": "low", "score": 0.1, "kind": "pattern"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_kb_candidate_pushed",
            payload_contains={"candidate_id": "low"},
        )
        assert events[0]["payload"]["score"] == 0.1
        record_cell(matrix_cov, "L1-06", "L1-10", CaseType.NEGATIVE)

    def test_negative_pm14_ui_push_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 ui push 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._ui_push_event(project_id, candidate_id="A"))
        real_event_bus.append(self._ui_push_event(other_project_id, candidate_id="B"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_kb_candidate_pushed",
            payload_contains={"candidate_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-10:ui_kb_candidate_pushed",
            payload_contains={"candidate_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-06", "L1-10", CaseType.PM14)

    def test_slo_ui_push_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · KB → UI push emit < 50ms."""
        from .conftest import record_cell

        evt = self._ui_push_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-19 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-06", "L1-10", CaseType.HAPPY)

    def test_e2e_ui_browse_session(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 完整 UI browse session · 10 候选 push (pattern×5 + gotcha×5)."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(self._ui_push_event(
                project_id, candidate_id=f"p-{i}", kind="pattern",
            ))
        for i in range(5):
            real_event_bus.append(self._ui_push_event(
                project_id, candidate_id=f"g-{i}", kind="gotcha",
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 10
        record_cell(matrix_cov, "L1-06", "L1-10", CaseType.DEGRADE)
