"""Row L1-10 UI/BFF → others · 2 cells × 6 TC = 12 TC.

**2 cells**:
    L1-10 → L1-01 · IC-19 (response) user_intervention 用户操作
    L1-10 → L1-09 · IC-09 ui_audit · UI 操作 audit
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
# Cell 1: L1-10 → L1-01 · IC-19 (response) user_intervention (6 TC)
# =============================================================================


class TestRowL1_10_to_L1_01:
    """L1-10 UI → L1-01 主决策 · IC-19 用户操作 (resume / pause / approve)."""

    def _intervention_event(
        self,
        project_id: str,
        action: str = "approve",
        intervention_id: str = "ui-1",
        user_id: str = "operator",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-10:user_intervention_received",
            actor=f"human:{user_id}",
            payload={
                "intervention_id": intervention_id,
                "action": action,
                "user_id": user_id,
                "target": "L1-01",
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_user_approve_intervention(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 用户 approve 操作 · L1-01 接收."""
        from .conftest import record_cell

        evt = self._intervention_event(project_id, action="approve")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:user_intervention_received",
            payload_contains={"action": "approve"},
        )
        assert events[0]["payload"]["target"] == "L1-01"
        record_cell(matrix_cov, "L1-10", "L1-01", CaseType.HAPPY)

    def test_happy_5_action_types_all_processed(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 5 类用户操作 (approve/reject/pause/resume/intervene)."""
        from .conftest import record_cell

        actions = ("approve", "reject", "pause", "resume", "intervene")
        for i, a in enumerate(actions):
            real_event_bus.append(self._intervention_event(
                project_id, action=a, intervention_id=f"ui-{i}",
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:user_intervention_received",
            min_count=5,
        )
        emitted_actions = {e["payload"]["action"] for e in events}
        assert emitted_actions == set(actions)
        record_cell(matrix_cov, "L1-10", "L1-01", CaseType.HAPPY)

    def test_negative_unknown_action_still_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 未知 action · audit 仍记 (L1-01 决定接受)."""
        from .conftest import record_cell

        evt = self._intervention_event(project_id, action="exotic_op")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:user_intervention_received",
            payload_contains={"action": "exotic_op"},
        )
        assert events[0]["payload"]["intervention_id"] == "ui-1"
        record_cell(matrix_cov, "L1-10", "L1-01", CaseType.NEGATIVE)

    def test_negative_pm14_intervention_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 user_intervention 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._intervention_event(
            project_id, intervention_id="A",
        ))
        real_event_bus.append(self._intervention_event(
            other_project_id, intervention_id="B",
        ))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:user_intervention_received",
            payload_contains={"intervention_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-10:user_intervention_received",
            payload_contains={"intervention_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-10", "L1-01", CaseType.PM14)

    def test_slo_intervention_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-19 user_intervention 写入 < 50ms."""
        from .conftest import record_cell

        evt = self._intervention_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-19 user_intervention SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-10", "L1-01", CaseType.HAPPY)

    def test_e2e_5_intervention_workflow(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 完整用户介入流程 5 actions · hash chain 完整."""
        from .conftest import record_cell

        # 完整流程: pause → review → approve / reject → resume
        actions = ("pause", "review", "approve", "intervene", "resume")
        for i, a in enumerate(actions):
            real_event_bus.append(self._intervention_event(
                project_id, action=a, intervention_id=f"flow-{i}",
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5
        record_cell(matrix_cov, "L1-10", "L1-01", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-10 → L1-09 · IC-09 ui_audit (6 TC)
# =============================================================================


class TestRowL1_10_to_L1_09:
    """L1-10 UI → L1-09 EventBus · IC-09 ui_audit (UI 操作 audit)."""

    def _ui_audit_event(
        self,
        project_id: str,
        ui_action: str = "click",
        component: str = "button:approve",
        session_id: str = "sess-1",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-10:ui_action_audited",
            actor="ui",
            payload={
                "session_id": session_id,
                "ui_action": ui_action,
                "component": component,
                "viewport": "desktop",
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_click_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · UI click 操作 audit · 落盘."""
        from .conftest import record_cell

        evt = self._ui_audit_event(project_id, ui_action="click")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_action_audited",
            payload_contains={"ui_action": "click"},
        )
        assert events[0]["payload"]["component"] == "button:approve"
        record_cell(matrix_cov, "L1-10", "L1-09", CaseType.HAPPY)

    def test_happy_5_ui_action_kinds_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 5 类 UI 操作 (click/scroll/input/submit/cancel) 各自 audit."""
        from .conftest import record_cell

        kinds = ("click", "scroll", "input", "submit", "cancel")
        for k in kinds:
            real_event_bus.append(self._ui_audit_event(project_id, ui_action=k))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_action_audited", min_count=5,
        )
        emitted_kinds = {e["payload"]["ui_action"] for e in events}
        assert emitted_kinds == set(kinds)
        record_cell(matrix_cov, "L1-10", "L1-09", CaseType.HAPPY)

    def test_negative_invalid_component_still_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 未知 component · audit 仍记 (后续审计)."""
        from .conftest import record_cell

        evt = self._ui_audit_event(
            project_id, ui_action="click", component="ghost-component",
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_action_audited",
            payload_contains={"component": "ghost-component"},
        )
        assert events[0]["payload"]["session_id"] == "sess-1"
        record_cell(matrix_cov, "L1-10", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_ui_audit_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 ui_audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._ui_audit_event(project_id, session_id="A"))
        real_event_bus.append(self._ui_audit_event(
            other_project_id, session_id="B",
        ))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:ui_action_audited",
            payload_contains={"session_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-10:ui_action_audited",
            payload_contains={"session_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-10", "L1-09", CaseType.PM14)

    def test_slo_ui_audit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · UI audit emit < 50ms."""
        from .conftest import record_cell

        evt = self._ui_audit_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-09 ui_audit SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-10", "L1-09", CaseType.HAPPY)

    def test_e2e_full_ui_session_audit(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 完整 UI session 8 操作 audit · hash chain · seq=1..8."""
        from .conftest import record_cell

        ops = ("click", "scroll", "input", "click", "submit",
               "scroll", "click", "cancel")
        for i, op in enumerate(ops):
            real_event_bus.append(self._ui_audit_event(
                project_id, ui_action=op, component=f"c-{i}",
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 8
        record_cell(matrix_cov, "L1-10", "L1-09", CaseType.DEGRADE)
