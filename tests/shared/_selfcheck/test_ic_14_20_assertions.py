"""Smoke: IC-14 / IC-20 断言功能(基于 Dev-ζ 真实 schema)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)
from tests.shared.ic_assertions import assert_ic_14_pushed, assert_ic_20_dispatched


def _mk_push(pid: str, wp_id: str, verdict: FailVerdict, target: TargetStage) -> PushRollbackRouteCommand:
    return PushRollbackRouteCommand(
        route_id=f"route-{wp_id}",
        project_id=pid,
        wp_id=wp_id,
        verdict=verdict,
        target_stage=target,
        level_count=1,
        evidence=RouteEvidence(
            verifier_report_id="vr-1",
            decision_id="dec-1",
        ),
        ts="2026-04-24T10:00:00Z",
    )


def test_assert_ic_14_pushed_success() -> None:
    recorded = [_mk_push("proj-x", "wp-1", FailVerdict.FAIL_L1, TargetStage.S3)]
    matched = assert_ic_14_pushed(
        recorded, project_id="proj-x", wp_id="wp-1", verdict="FAIL_L1", target_stage="S3",
    )
    assert len(matched) == 1


def test_assert_ic_14_pushed_fail_wrong_verdict() -> None:
    recorded = [_mk_push("proj-x", "wp-1", FailVerdict.FAIL_L1, TargetStage.S3)]
    with pytest.raises(AssertionError, match="IC-14 rollback push 断言失败"):
        assert_ic_14_pushed(
            recorded, project_id="proj-x", wp_id="wp-1", verdict="FAIL_L2",
        )


@dataclass
class _FakeIC20Cmd:
    project_id: str
    wp_id: str
    delegation_id: str


def test_assert_ic_20_dispatched_success() -> None:
    calls = [_FakeIC20Cmd("proj-x", "wp-1", "del-1")]
    matched = assert_ic_20_dispatched(calls, project_id="proj-x", wp_id="wp-1")
    assert len(matched) == 1


def test_assert_ic_20_dispatched_fail_wrong_wp() -> None:
    calls = [_FakeIC20Cmd("proj-x", "wp-1", "del-1")]
    with pytest.raises(AssertionError, match="IC-20 delegate_verifier 断言失败"):
        assert_ic_20_dispatched(calls, project_id="proj-x", wp_id="wp-99")
