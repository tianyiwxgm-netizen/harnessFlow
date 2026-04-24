"""Soft-drift window_stats.TickWindow TC。"""
from __future__ import annotations

import pytest

from app.supervisor.soft_drift.schemas import Tick
from app.supervisor.soft_drift.window_stats import TickWindow


def _tick(
    seq: int,
    *,
    project_id: str = "proj-a",
    gate: str | None = None,
    wp_fail: int | None = None,
    sk_fb: int | None = None,
    kb: float | None = None,
    audit: int | None = None,
    ui: int | None = None,
    verifier: str | None = None,
    state: str | None = None,
) -> Tick:
    return Tick(
        tick_seq=seq,
        project_id=project_id,
        captured_at_ms=seq * 30000,
        gate_verdict=gate,
        wp_fail_count=wp_fail,
        skill_fallback_count=sk_fb,
        kb_hit_rate=kb,
        audit_p95_ms=audit,
        ui_panic_count=ui,
        verifier_verdict=verifier,
        state_seq=state,
    )


class TestTickWindow:
    def test_empty_window(self) -> None:
        w = TickWindow(project_id="proj-a")
        stats = w.aggregate()
        assert stats.tick_count == 0

    def test_push_single(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, gate="PASS"))
        assert w.size == 1

    def test_max_window_size(self) -> None:
        w = TickWindow(project_id="proj-a", window_size=5)
        for i in range(10):
            w.push(_tick(i, gate="PASS"))
        assert w.size == 5
        stats = w.aggregate()
        assert stats.first_tick_seq == 5
        assert stats.last_tick_seq == 9

    def test_cross_pid_rejected(self) -> None:
        w = TickWindow(project_id="proj-a")
        with pytest.raises(ValueError, match="E_SDP_CROSS_PROJECT"):
            w.push(_tick(1, project_id="proj-b"))

    def test_gate_tolerated_count(self) -> None:
        w = TickWindow(project_id="proj-a")
        for i in range(5):
            w.push(_tick(i, gate="TOLERATED" if i % 2 == 0 else "PASS"))
        stats = w.aggregate()
        assert stats.gate_tolerated_count == 3

    def test_wp_fail_max(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, wp_fail=1))
        w.push(_tick(2, wp_fail=3))
        w.push(_tick(3, wp_fail=2))
        stats = w.aggregate()
        assert stats.wp_fail_max == 3

    def test_skill_fallback_total(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, sk_fb=2))
        w.push(_tick(2, sk_fb=3))
        w.push(_tick(3, sk_fb=1))
        stats = w.aggregate()
        assert stats.skill_fallback_total == 6

    def test_kb_hit_rate_avg(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, kb=0.5))
        w.push(_tick(2, kb=0.7))
        w.push(_tick(3, kb=0.3))
        stats = w.aggregate()
        assert stats.kb_hit_rate_avg == pytest.approx(0.5)

    def test_kb_hit_rate_none_skipped(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, kb=None))
        w.push(_tick(2, kb=0.4))
        stats = w.aggregate()
        assert stats.kb_hit_rate_avg == pytest.approx(0.4)

    def test_audit_p95_max(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, audit=10))
        w.push(_tick(2, audit=50))
        w.push(_tick(3, audit=20))
        stats = w.aggregate()
        assert stats.audit_p95_max == 50

    def test_ui_panic_total(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, ui=1))
        w.push(_tick(2, ui=2))
        stats = w.aggregate()
        assert stats.ui_panic_total == 3

    def test_verifier_reject_streak_simple(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, verifier="REJECT"))
        w.push(_tick(2, verifier="REJECT"))
        w.push(_tick(3, verifier="REJECT"))
        stats = w.aggregate()
        assert stats.verifier_reject_streak == 3

    def test_verifier_reject_streak_broken_by_pass(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, verifier="REJECT"))
        w.push(_tick(2, verifier="PASS"))
        w.push(_tick(3, verifier="REJECT"))
        w.push(_tick(4, verifier="REJECT"))
        stats = w.aggregate()
        # 从最新往前数 · 遇到 PASS 即断 · streak=2
        assert stats.verifier_reject_streak == 2

    def test_state_reverse_count(self) -> None:
        w = TickWindow(project_id="proj-a")
        w.push(_tick(1, state="S1"))
        w.push(_tick(2, state="S3"))
        w.push(_tick(3, state="S2"))  # 逆序 1
        w.push(_tick(4, state="S4"))
        w.push(_tick(5, state="S3"))  # 逆序 2
        stats = w.aggregate()
        assert stats.state_reverse_count == 2
