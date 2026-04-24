"""L2-03 schemas TC。"""
from __future__ import annotations

import pytest

from app.supervisor.red_line import (
    DetectionResult,
    Evidence,
    RedLineHit,
    RedLineId,
    RedLineSeverity,
)


class TestRedLineId:
    def test_five_ids(self) -> None:
        vals = {r.value for r in RedLineId}
        assert vals == {"HRL-01", "HRL-02", "HRL-03", "HRL-04", "HRL-05"}


class TestEvidence:
    def test_requires_observation_refs(self) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError
            Evidence(
                observation_refs=(),
                detector_name="x",
                detected_at_ms=0,
            )

    def test_valid(self) -> None:
        e = Evidence(
            observation_refs=("ev-1",),
            detector_name="pm14_violator",
            detected_at_ms=1000,
        )
        assert e.observation_refs == ("ev-1",)


class TestRedLineHit:
    def test_pid_required(self) -> None:
        with pytest.raises(ValueError, match="E_REDLINE_NO_PROJECT_ID"):
            RedLineHit(
                red_line_id=RedLineId.HRL_01_PM14_VIOLATION,
                project_id="   ",
                severity=RedLineSeverity.CRITICAL,
                evidence=Evidence(
                    observation_refs=("ev-1",),
                    detector_name="x",
                    detected_at_ms=0,
                ),
                reason="test",
                hit_id="hit-1",
            )

    def test_frozen(self) -> None:
        h = RedLineHit(
            red_line_id=RedLineId.HRL_02_AUDIT_BROKEN,
            project_id="proj-a",
            severity=RedLineSeverity.HIGH,
            evidence=Evidence(
                observation_refs=("ev-1",),
                detector_name="x",
                detected_at_ms=0,
            ),
            reason="test",
            hit_id="hit-1",
        )
        with pytest.raises(Exception):
            h.reason = "mutated"  # type: ignore[misc]


class TestDetectionResult:
    def test_latency_us_non_neg(self) -> None:
        with pytest.raises(Exception):  # ge=0 validator
            DetectionResult(
                detector_name="x",
                red_line_id=RedLineId.HRL_03_TRACEABILITY,
                hit=None,
                latency_us=-1,
            )
