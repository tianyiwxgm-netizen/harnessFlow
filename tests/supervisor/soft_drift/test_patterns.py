"""Soft-drift 8 patterns TC · 每 pattern 1 正 + 1 反。"""
from __future__ import annotations

from app.supervisor.soft_drift.patterns.sdp_01_gate_overrun import (
    GateOverrunPattern,
)
from app.supervisor.soft_drift.patterns.sdp_02_wp_loop import WpLoopPattern
from app.supervisor.soft_drift.patterns.sdp_03_skill_fallback import (
    SkillFallbackPattern,
)
from app.supervisor.soft_drift.patterns.sdp_04_kb_miss import KbMissPattern
from app.supervisor.soft_drift.patterns.sdp_05_audit_tail import AuditTailPattern
from app.supervisor.soft_drift.patterns.sdp_06_ui_panic import UiPanicPattern
from app.supervisor.soft_drift.patterns.sdp_07_verifier_reject import (
    VerifierRejectPattern,
)
from app.supervisor.soft_drift.patterns.sdp_08_state_reverse import (
    StateReversePattern,
)
from app.supervisor.soft_drift.schemas import Tick, TrapPatternId
from app.supervisor.soft_drift.window_stats import TickWindow


def _fill_window(project_id: str, ticks: list[Tick]) -> TickWindow:
    w = TickWindow(project_id=project_id)
    for t in ticks:
        w.push(t)
    return w


def _t(
    seq: int,
    *,
    project_id: str = "proj-a",
    **kwargs,
) -> Tick:
    return Tick(
        tick_seq=seq,
        project_id=project_id,
        captured_at_ms=seq * 1000,
        **kwargs,
    )


# ==================== SDP-01 ====================


class TestSdp01GateOverrun:
    def test_no_hit_below_threshold(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, gate_verdict="TOLERATED"),
                _t(2, gate_verdict="PASS"),
                _t(3, gate_verdict="TOLERATED"),
            ],
        )
        m = GateOverrunPattern().check(w, w.aggregate())
        assert m is None

    def test_hits_three_tolerated(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, gate_verdict="TOLERATED"),
                _t(2, gate_verdict="TOLERATED"),
                _t(3, gate_verdict="TOLERATED"),
            ],
        )
        m = GateOverrunPattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_01_GATE_OVERRUN


# ==================== SDP-02 ====================


class TestSdp02WpLoop:
    def test_no_hit_fail_2(self) -> None:
        w = _fill_window(
            "proj-a",
            [_t(1, wp_fail_count=2), _t(2, wp_fail_count=2)],
        )
        assert WpLoopPattern().check(w, w.aggregate()) is None

    def test_hits_fail_3(self) -> None:
        w = _fill_window("proj-a", [_t(1, wp_fail_count=3)])
        m = WpLoopPattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_02_WP_LOOP


# ==================== SDP-03 ====================


class TestSdp03SkillFallback:
    def test_no_hit_below_5(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, skill_fallback_count=1),
                _t(2, skill_fallback_count=2),
            ],
        )
        assert SkillFallbackPattern().check(w, w.aggregate()) is None

    def test_hits_above_5(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, skill_fallback_count=3),
                _t(2, skill_fallback_count=3),
            ],
        )
        m = SkillFallbackPattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_03_SKILL_FALLBACK


# ==================== SDP-04 ====================


class TestSdp04KbMiss:
    def test_no_hit_above_30pct(self) -> None:
        w = _fill_window(
            "proj-a",
            [_t(1, kb_hit_rate=0.5), _t(2, kb_hit_rate=0.4)],
        )
        assert KbMissPattern().check(w, w.aggregate()) is None

    def test_hits_below_30pct(self) -> None:
        w = _fill_window(
            "proj-a",
            [_t(1, kb_hit_rate=0.2), _t(2, kb_hit_rate=0.25)],
        )
        m = KbMissPattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_04_KB_MISS

    def test_no_rate_data_no_hit(self) -> None:
        # 无 kb_hit_rate 数据 · 不命中（保守）
        w = _fill_window("proj-a", [_t(1), _t(2)])
        m = KbMissPattern().check(w, w.aggregate())
        assert m is None


# ==================== SDP-05 ====================


class TestSdp05AuditTail:
    def test_no_hit_below_20ms(self) -> None:
        w = _fill_window(
            "proj-a",
            [_t(1, audit_p95_ms=10), _t(2, audit_p95_ms=15)],
        )
        assert AuditTailPattern().check(w, w.aggregate()) is None

    def test_hits_above_20ms(self) -> None:
        w = _fill_window(
            "proj-a",
            [_t(1, audit_p95_ms=50)],
        )
        m = AuditTailPattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_05_AUDIT_TAIL


# ==================== SDP-06 ====================


class TestSdp06UiPanic:
    def test_no_hit_below_3(self) -> None:
        w = _fill_window(
            "proj-a",
            [_t(1, ui_panic_count=1), _t(2, ui_panic_count=1)],
        )
        assert UiPanicPattern().check(w, w.aggregate()) is None

    def test_hits_3(self) -> None:
        w = _fill_window(
            "proj-a",
            [_t(1, ui_panic_count=2), _t(2, ui_panic_count=1)],
        )
        m = UiPanicPattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_06_UI_PANIC


# ==================== SDP-07 ====================


class TestSdp07VerifierReject:
    def test_no_hit_streak_2(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, verifier_verdict="REJECT"),
                _t(2, verifier_verdict="REJECT"),
            ],
        )
        assert VerifierRejectPattern().check(w, w.aggregate()) is None

    def test_hits_streak_3(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, verifier_verdict="REJECT"),
                _t(2, verifier_verdict="REJECT"),
                _t(3, verifier_verdict="REJECT"),
            ],
        )
        m = VerifierRejectPattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_07_VERIFIER_REJECT


# ==================== SDP-08 ====================


class TestSdp08StateReverse:
    def test_no_hit_one_reverse(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, state_seq="S1"),
                _t(2, state_seq="S3"),
                _t(3, state_seq="S2"),  # 1 次 reverse
            ],
        )
        assert StateReversePattern().check(w, w.aggregate()) is None

    def test_hits_two_reverses(self) -> None:
        w = _fill_window(
            "proj-a",
            [
                _t(1, state_seq="S1"),
                _t(2, state_seq="S3"),
                _t(3, state_seq="S2"),  # reverse 1
                _t(4, state_seq="S4"),
                _t(5, state_seq="S3"),  # reverse 2
            ],
        )
        m = StateReversePattern().check(w, w.aggregate())
        assert m is not None
        assert m.pattern_id is TrapPatternId.SDP_08_STATE_REVERSE
