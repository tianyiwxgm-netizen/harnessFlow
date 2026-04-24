"""Soft-drift schemas TC。"""
from __future__ import annotations

import pytest

from app.supervisor.soft_drift.schemas import (
    Tick,
    TrapMatch,
    TrapPatternId,
    WindowStats,
)


class TestTrapPatternId:
    def test_eight_patterns(self) -> None:
        vals = {p.value for p in TrapPatternId}
        assert vals == {f"SDP-0{i}" for i in range(1, 9)}


class TestTick:
    def test_pid_required(self) -> None:
        with pytest.raises(Exception):
            Tick(tick_seq=1, project_id="", captured_at_ms=0)

    def test_frozen(self) -> None:
        t = Tick(tick_seq=1, project_id="proj-a", captured_at_ms=0)
        with pytest.raises(Exception):
            t.tick_seq = 99  # type: ignore[misc]


class TestTrapMatch:
    def test_pid_required(self) -> None:
        with pytest.raises(ValueError, match="E_SDP_NO_PROJECT_ID"):
            TrapMatch(
                project_id="  ",
                pattern_id=TrapPatternId.SDP_01_GATE_OVERRUN,
                reason="test",
                evidence_tick_seqs=(1,),
                first_tick_seq=1,
                last_tick_seq=1,
                match_id="m-1",
            )

    def test_evidence_tick_seqs_non_empty(self) -> None:
        with pytest.raises(Exception):
            TrapMatch(
                project_id="proj-a",
                pattern_id=TrapPatternId.SDP_01_GATE_OVERRUN,
                reason="test",
                evidence_tick_seqs=(),  # empty
                first_tick_seq=1,
                last_tick_seq=1,
                match_id="m-1",
            )

    def test_default_severity_warn(self) -> None:
        m = TrapMatch(
            project_id="proj-a",
            pattern_id=TrapPatternId.SDP_02_WP_LOOP,
            reason="test",
            evidence_tick_seqs=(1,),
            first_tick_seq=1,
            last_tick_seq=1,
            match_id="m-1",
        )
        assert m.severity == "WARN"


class TestWindowStats:
    def test_defaults(self) -> None:
        ws = WindowStats(project_id="proj-a", tick_count=0)
        assert ws.window_size == 60
        assert ws.gate_tolerated_count == 0
