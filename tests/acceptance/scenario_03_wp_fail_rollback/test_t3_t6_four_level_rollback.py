"""Scenario 03 · T3-T6 · 4 级回退路径 · 重试 / 细化 / 重设计 / 升级.

T3 · FAIL_L1 → S3 retry (stage 内重试 = 重试)
T4 · FAIL_L2 → S4 refine (回退到 S4 = 细化)
T5 · FAIL_L3 → S5 redesign (回退到 S5 = 重设计)
T6 · FAIL_L4 → UPGRADE_TO_L1_01 (升级 L1-01 = 升级)
"""
from __future__ import annotations

import pytest

from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.supervisor.event_sender.schemas import FailVerdict, TargetStage
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_emitted


# 4 级映射 (verdict, target_stage, expected_new_state, severity)
ROLLBACK_LEVELS = [
    ("T3", FailVerdict.FAIL_L1, TargetStage.S3, "retry_s3", "WARN", "重试"),
    ("T4", FailVerdict.FAIL_L2, TargetStage.S4, "retry_s4", "FAIL", "细化"),
    ("T5", FailVerdict.FAIL_L3, TargetStage.S5, "retry_s5", "FAIL", "重设计"),
    (
        "T6",
        FailVerdict.FAIL_L4,
        TargetStage.UPGRADE_TO_L1_01,
        "upgraded_to_l1_01",
        "CRITICAL",
        "升级 L1-01",
    ),
]


@pytest.mark.parametrize(
    "tid,verdict,target,expected_state,expected_severity,desc",
    ROLLBACK_LEVELS,
)
async def test_t3_t6_four_level_rollback(
    project_id: str,
    real_event_bus,
    event_bus_root,
    ic14_consumer: IC14Consumer,
    make_route_cmd,
    gwt: GWT,
    tid: str,
    verdict: FailVerdict,
    target: TargetStage,
    expected_state: str,
    expected_severity: str,
    desc: str,
) -> None:
    """T3-T6 · 4 级回退完整链路 · IC-14 → IC-09 audit."""
    async with gwt(f"{tid} · {verdict.value} → {target.value} ({desc})"):
        gwt.given(f"WP fail · verdict={verdict.value} · level_count=1 (非升级触发)")
        cmd = make_route_cmd(
            route_id=f"route-{tid.lower()}-{verdict.value.lower()}",
            wp_id="wp-rollback-target",
            verdict=verdict,
            target_stage=target,
            level_count=1,
        )

        gwt.when("L2-07 IC14Consumer 消费 · 走完 classify→map→execute")
        ack = await ic14_consumer.consume(cmd)

        gwt.then(f"ack.new_wp_state={expected_state} · 4 级映射正确")
        assert ack.applied is True
        assert ack.new_wp_state.value == expected_state
        # FAIL_L4 自身就是升级 · 但 escalated=False (非 level≥3 触发)
        assert ack.escalated is False, (
            f"{tid} 非 level_count≥3 触发 · escalated 应=False"
        )

        gwt.then(f"IC-09 rollback_executed · severity={expected_severity}")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:rollback_executed",
            payload_contains={
                "wp_id": "wp-rollback-target",
                "severity": expected_severity,
                "target_stage": target.value,
                "new_wp_state": expected_state,
            },
        )
        assert len(events) == 1, f"{tid} · audit 缺失"
