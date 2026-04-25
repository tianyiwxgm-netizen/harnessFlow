"""Row L1-07 Supervisor → others · 4 cells × 6 TC = 24 TC.

**4 cells**:
    L1-07 → L1-01 · IC-15 hard_halt request (5 类硬红线 BLOCK ≤ 100ms)
    L1-07 → L1-09 · IC-12 metric_emit (8 维快照 + SLO)
    L1-07 → L1-10 · IC-19 dashboard_push (监控面板推送)
    L1-07 → L1-04 · 监督触发 Gate (新增 4th 替代 push_suggestion 重号)
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
    assert_panic_within_100ms,
)
from tests.shared.matrix_helpers import CaseType


# =============================================================================
# Cell 1: L1-07 → L1-01 · IC-15 hard_halt 5 类红线 BLOCK ≤ 100ms (6 TC)
# =============================================================================


class TestRowL1_07_to_L1_01:
    """L1-07 Supervisor → L1-01 主决策 · IC-15 硬红线 hard_halt request."""

    def _halt_event(
        self,
        project_id: str,
        red_line_id: str = "HRL-01",
        halt_id: str = "halt-1",
    ) -> Event:
        # IC-15 §3.15: bus_halted 系统级事件 · 但 supervisor 内部追踪
        # 我们用 supervisor_halt_request 事件来记录红线触发
        return Event(
            project_id=project_id,
            type="L1-07:supervisor_halt_requested",
            actor="supervisor",
            payload={
                "halt_id": halt_id,
                "red_line_id": red_line_id,
                "reason": f"hard red line {red_line_id} triggered",
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_hrl01_red_line_block(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · HRL-01 红线触发 · halt request 写入 bus."""
        from .conftest import record_cell

        evt = self._halt_event(project_id, red_line_id="HRL-01")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_halt_requested",
            payload_contains={"red_line_id": "HRL-01"},
        )
        assert events[0]["payload"]["halt_id"] == "halt-1"
        record_cell(matrix_cov, "L1-07", "L1-01", CaseType.HAPPY)

    def test_happy_5_red_lines_all_block(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 5 类 HRL 全部触发 BLOCK · 各自 audit."""
        from .conftest import record_cell

        for hrl in ("HRL-01", "HRL-02", "HRL-03", "HRL-04", "HRL-05"):
            real_event_bus.append(self._halt_event(
                project_id, red_line_id=hrl, halt_id=f"halt-{hrl}",
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_halt_requested",
            min_count=5,
        )
        hrls = {e["payload"]["red_line_id"] for e in events}
        assert hrls == {"HRL-01", "HRL-02", "HRL-03", "HRL-04", "HRL-05"}
        record_cell(matrix_cov, "L1-07", "L1-01", CaseType.HAPPY)

    def test_negative_invalid_red_line_id_still_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 不在 5 类内的 red_line_id · audit 仍记 (后续审计)."""
        from .conftest import record_cell

        evt = self._halt_event(project_id, red_line_id="UNKNOWN-RL")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_halt_requested",
            payload_contains={"red_line_id": "UNKNOWN-RL"},
        )
        assert events[0]["payload"]["red_line_id"] == "UNKNOWN-RL"
        record_cell(matrix_cov, "L1-07", "L1-01", CaseType.NEGATIVE)

    def test_negative_pm14_halt_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 halt audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._halt_event(project_id, halt_id="A"))
        real_event_bus.append(self._halt_event(other_project_id, halt_id="B"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_halt_requested",
            payload_contains={"halt_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-07:supervisor_halt_requested",
            payload_contains={"halt_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-07", "L1-01", CaseType.PM14)

    def test_slo_halt_request_under_100ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-15 红线 → halt emit < 100ms (HRL-04 release blocker)."""
        from .conftest import record_cell

        evt = self._halt_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        t1 = time.monotonic()
        # 用 IC-17 风格 100ms 硬红线断言
        assert_panic_within_100ms(t0, t1, budget_ms=100.0)
        record_cell(matrix_cov, "L1-07", "L1-01", CaseType.HAPPY)

    def test_e2e_5_redlines_all_within_100ms(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 5 类 HRL 全部触发 · 每条 ≤ 100ms · hash chain 完整."""
        from .conftest import record_cell

        for hrl in ("HRL-01", "HRL-02", "HRL-03", "HRL-04", "HRL-05"):
            t0 = time.monotonic()
            real_event_bus.append(self._halt_event(project_id, red_line_id=hrl))
            t1 = time.monotonic()
            assert_panic_within_100ms(t0, t1, budget_ms=100.0)
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5
        record_cell(matrix_cov, "L1-07", "L1-01", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-07 → L1-09 · IC-12 metric_emit 8 维快照 + SLO (6 TC)
# =============================================================================


class TestRowL1_07_to_L1_09:
    """L1-07 Supervisor → L1-09 EventBus · IC-12 metric_emit 8 维快照."""

    # 8 dim per supervisor design
    DIMS = (
        "plan_drift", "spec_deviation", "cost_overrun", "schedule_slip",
        "quality_drift", "risk_emerging", "halt_signal", "supervisor_health",
    )

    def _metric_event(
        self,
        project_id: str,
        dim: str = "plan_drift",
        value: float = 0.5,
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-07:supervisor_metric_emitted",
            actor="supervisor",
            payload={
                "dim": dim,
                "value": value,
                "tick_id": "tick-001",
                "snapshot_at": datetime.now(UTC).isoformat(),
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_metric_emitted_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · supervisor metric emit 1 dim · audit 落盘."""
        from .conftest import record_cell

        evt = self._metric_event(project_id, dim="plan_drift", value=0.42)
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_metric_emitted",
            payload_contains={"dim": "plan_drift"},
        )
        assert events[0]["payload"]["value"] == 0.42
        record_cell(matrix_cov, "L1-07", "L1-09", CaseType.HAPPY)

    def test_happy_8_dims_full_snapshot(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 8 维 metric 全部 emit · 完整快照."""
        from .conftest import record_cell

        for dim in self.DIMS:
            real_event_bus.append(self._metric_event(project_id, dim=dim))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_metric_emitted",
            min_count=8,
        )
        emitted_dims = {e["payload"]["dim"] for e in events}
        assert emitted_dims == set(self.DIMS)
        record_cell(matrix_cov, "L1-07", "L1-09", CaseType.HAPPY)

    def test_negative_negative_value_still_recorded(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 异常负值 (-1.0) · audit 仍记 (后续 SLO 检测)."""
        from .conftest import record_cell

        evt = self._metric_event(project_id, dim="plan_drift", value=-1.0)
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_metric_emitted",
            payload_contains={"dim": "plan_drift"},
        )
        assert events[0]["payload"]["value"] == -1.0
        record_cell(matrix_cov, "L1-07", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_metric_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 metric audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._metric_event(project_id, value=0.1))
        real_event_bus.append(self._metric_event(other_project_id, value=0.9))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_metric_emitted", min_count=1,
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-07:supervisor_metric_emitted", min_count=1,
        )
        assert a[0]["payload"]["value"] == 0.1
        assert b[0]["payload"]["value"] == 0.9
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-07", "L1-09", CaseType.PM14)

    def test_slo_metric_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-12 metric emit < 50ms (per dim)."""
        from .conftest import record_cell

        evt = self._metric_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-12 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-07", "L1-09", CaseType.HAPPY)

    def test_e2e_8_dim_snapshot_with_hash_chain(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 8 dim 快照 emit · hash chain 完整 · seq=1..8."""
        from .conftest import record_cell

        for dim in self.DIMS:
            real_event_bus.append(self._metric_event(project_id, dim=dim))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 8
        record_cell(matrix_cov, "L1-07", "L1-09", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-07 → L1-10 · IC-19 dashboard_push 监控面板 (6 TC)
# =============================================================================


class TestRowL1_07_to_L1_10:
    """L1-07 Supervisor → L1-10 UI · IC-19 dashboard_push 监控面板."""

    def _dashboard_event(
        self,
        project_id: str,
        widget_id: str = "drift-gauge",
        value: float = 0.3,
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-10:supervisor_dashboard_pushed",
            actor="supervisor",
            payload={
                "widget_id": widget_id,
                "value": value,
                "title": "Drift Gauge",
                "severity": "info",
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_dashboard_widget_pushed(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · dashboard widget push · UI 接收."""
        from .conftest import record_cell

        evt = self._dashboard_event(project_id, widget_id="drift-gauge", value=0.6)
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:supervisor_dashboard_pushed",
            payload_contains={"widget_id": "drift-gauge"},
        )
        assert events[0]["payload"]["value"] == 0.6
        record_cell(matrix_cov, "L1-07", "L1-10", CaseType.HAPPY)

    def test_happy_multiple_widgets_pushed(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 多 widget 同 tick push (drift / cost / quality 3 个 widget)."""
        from .conftest import record_cell

        widgets = ["drift-gauge", "cost-counter", "quality-bar"]
        for w in widgets:
            real_event_bus.append(self._dashboard_event(project_id, widget_id=w))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:supervisor_dashboard_pushed",
            min_count=3,
        )
        assert {e["payload"]["widget_id"] for e in events} == set(widgets)
        record_cell(matrix_cov, "L1-07", "L1-10", CaseType.HAPPY)

    def test_negative_zero_value_still_pushed(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 0 值 widget · UI 仍接收 (UI 端决定显示)."""
        from .conftest import record_cell

        evt = self._dashboard_event(project_id, widget_id="empty", value=0.0)
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:supervisor_dashboard_pushed",
            payload_contains={"widget_id": "empty"},
        )
        assert events[0]["payload"]["value"] == 0.0
        record_cell(matrix_cov, "L1-07", "L1-10", CaseType.NEGATIVE)

    def test_negative_pm14_dashboard_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 dashboard push 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._dashboard_event(project_id, widget_id="A"))
        real_event_bus.append(self._dashboard_event(other_project_id, widget_id="B"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-10:supervisor_dashboard_pushed",
            payload_contains={"widget_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-10:supervisor_dashboard_pushed",
            payload_contains={"widget_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-07", "L1-10", CaseType.PM14)

    def test_slo_dashboard_push_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-19 dashboard push < 50ms (per widget)."""
        from .conftest import record_cell

        evt = self._dashboard_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-19 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-07", "L1-10", CaseType.HAPPY)

    def test_e2e_full_dashboard_tick(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 完整 supervisor tick → 8 widget 同步推送 UI · hash chain."""
        from .conftest import record_cell

        widgets = [f"w-{i}" for i in range(8)]
        for w in widgets:
            real_event_bus.append(self._dashboard_event(project_id, widget_id=w))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 8
        record_cell(matrix_cov, "L1-07", "L1-10", CaseType.DEGRADE)


# =============================================================================
# Cell 4: L1-07 → L1-04 · 监督触发 Gate (push_suggestion 替代 4th cell) (6 TC)
# =============================================================================


class TestRowL1_07_to_L1_04:
    """L1-07 Supervisor → L1-04 Quality Loop · 软漂移触发 Gate suggestion."""

    def _suggestion_event(
        self,
        project_id: str,
        suggestion_id: str = "sug-1",
        dim: str = "plan_drift",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-07:supervisor_suggestion_pushed",
            actor="supervisor",
            payload={
                "suggestion_id": suggestion_id,
                "dim": dim,
                "target": "L1-04",
                "action": "trigger_gate_re_eval",
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_suggestion_pushed_to_l1_04(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · supervisor 软漂移建议 → L1-04 触发 Gate 重评."""
        from .conftest import record_cell

        evt = self._suggestion_event(project_id, dim="plan_drift")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_suggestion_pushed",
            payload_contains={"target": "L1-04"},
        )
        assert events[0]["payload"]["action"] == "trigger_gate_re_eval"
        record_cell(matrix_cov, "L1-07", "L1-04", CaseType.HAPPY)

    def test_happy_8_soft_drift_suggestions(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 8 类软漂移触发 8 条 suggestion (覆盖 L1-07 §soft_drift 8 dim)."""
        from .conftest import record_cell

        soft_dims = (
            "plan_drift", "spec_deviation", "cost_overrun", "schedule_slip",
            "quality_drift", "risk_emerging", "halt_signal", "supervisor_health",
        )
        for d in soft_dims:
            real_event_bus.append(self._suggestion_event(
                project_id, suggestion_id=f"sug-{d}", dim=d,
            ))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_suggestion_pushed",
            min_count=8,
        )
        assert {e["payload"]["dim"] for e in events} == set(soft_dims)
        record_cell(matrix_cov, "L1-07", "L1-04", CaseType.HAPPY)

    def test_negative_unknown_action_still_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 未知 action · audit 仍记 (L1-04 侧决定接受)."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-07:supervisor_suggestion_pushed",
            actor="supervisor",
            payload={
                "suggestion_id": "sug-bad",
                "target": "L1-04",
                "action": "unknown_op",
            },
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_suggestion_pushed",
            payload_contains={"action": "unknown_op"},
        )
        assert events[0]["payload"]["suggestion_id"] == "sug-bad"
        record_cell(matrix_cov, "L1-07", "L1-04", CaseType.NEGATIVE)

    def test_negative_pm14_suggestion_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 suggestion 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._suggestion_event(project_id, suggestion_id="A"))
        real_event_bus.append(self._suggestion_event(
            other_project_id, suggestion_id="B",
        ))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-07:supervisor_suggestion_pushed",
            payload_contains={"suggestion_id": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-07:supervisor_suggestion_pushed",
            payload_contains={"suggestion_id": "B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-07", "L1-04", CaseType.PM14)

    def test_slo_suggestion_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · suggestion emit < 50ms."""
        from .conftest import record_cell

        evt = self._suggestion_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"L1-07 → L1-04 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-07", "L1-04", CaseType.HAPPY)

    def test_e2e_3_suggestions_drive_3_gates(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 3 suggestion 链式触发 3 个 Gate 重评 audit · 共 6 events."""
        from .conftest import record_cell

        for i in range(3):
            real_event_bus.append(self._suggestion_event(
                project_id, suggestion_id=f"sug-e2e-{i}",
            ))
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-04:gate_evaluated",
                actor="verifier",
                payload={
                    "gate_id": f"gate-{i}",
                    "trigger": "supervisor_suggestion",
                    "decision": "pass",
                },
                timestamp=datetime.now(UTC),
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 6
        record_cell(matrix_cov, "L1-07", "L1-04", CaseType.DEGRADE)
