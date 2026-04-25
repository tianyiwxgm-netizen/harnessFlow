"""Scenario 03 · T9-T10 · audit 链完整 + cross-attempt evidence 关联.

T9: 多 rollback 后 hash chain 完整 · seq 单调递增
T10: cross-attempt evidence 关联 · attempt-1 → attempt-2 evidence 链路可追溯
"""
from __future__ import annotations

from app.l1_09.event_bus.core import EventBus
from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.supervisor.event_sender.schemas import FailVerdict, TargetStage
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


async def test_t9_audit_chain_intact_after_multi_rollback(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    ic14_consumer: IC14Consumer,
    make_route_cmd,
    gwt: GWT,
) -> None:
    """T9 · 5 次连续 rollback · hash chain 完整 · 单调递增."""
    async with gwt("T9 · 5 次连续 rollback · hash chain 完整"):
        gwt.given("audit 干净")
        assert assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id) == 0

        gwt.when("跑 5 次 rollback (不同 wp · 不同 verdict)")
        cases = [
            ("route-t9-a", "wp-a", FailVerdict.FAIL_L1, TargetStage.S3),
            ("route-t9-b", "wp-b", FailVerdict.FAIL_L2, TargetStage.S4),
            ("route-t9-c", "wp-c", FailVerdict.FAIL_L3, TargetStage.S5),
            ("route-t9-d", "wp-d", FailVerdict.FAIL_L1, TargetStage.S3),
            (
                "route-t9-e",
                "wp-e",
                FailVerdict.FAIL_L4,
                TargetStage.UPGRADE_TO_L1_01,
            ),
        ]
        for route_id, wp_id, verdict, target in cases:
            cmd = make_route_cmd(
                route_id=route_id,
                wp_id=wp_id,
                verdict=verdict,
                target_stage=target,
            )
            ack = await ic14_consumer.consume(cmd)
            assert ack.applied is True

        gwt.then("hash chain 完整 · 5 条 rollback_executed seq=1..5")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5

        gwt.then("5 条事件 type 全为 L1-04:rollback_executed · seq 单调")
        events = list_events(
            event_bus_root,
            project_id,
            type_exact="L1-04:rollback_executed",
        )
        assert len(events) == 5
        seqs = [e["sequence"] for e in events]
        assert seqs == sorted(seqs), f"seq 非单调 · {seqs}"


async def test_t10_cross_attempt_evidence_linkage(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    ic14_consumer: IC14Consumer,
    make_route_cmd,
    gwt: GWT,
) -> None:
    """T10 · cross-attempt evidence 关联 · attempt-1 → attempt-2 可追溯."""
    async with gwt("T10 · cross-attempt evidence 关联"):
        gwt.given("wp-x 三次 attempt · 共用 wp_id · 不同 route_id + verifier_report_id")
        attempts = [
            ("route-t10-a1", "vr-attempt-1", 1),
            ("route-t10-a2", "vr-attempt-2", 2),
            ("route-t10-a3", "vr-attempt-3", 3),
        ]

        gwt.when("依次跑 3 次 attempt · level_count 1→2→3 (升级触发)")
        for route_id, vr_id, lc in attempts:
            cmd = make_route_cmd(
                route_id=route_id,
                wp_id="wp-x",
                verdict=FailVerdict.FAIL_L1,
                target_stage=TargetStage.S3,
                level_count=lc,
                verifier_report_id=vr_id,
            )
            ack = await ic14_consumer.consume(cmd)
            assert ack.applied is True
            # level_count >= 3 → 升级路径
            if lc >= 3:
                assert ack.escalated is True
                assert ack.new_wp_state.value == "upgraded_to_l1_01"

        gwt.then("3 条 rollback_executed · 全 wp_id=wp-x · level_count 单调")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:rollback_executed",
            payload_contains={"wp_id": "wp-x"},
            min_count=3,
        )
        assert len(events) == 3
        lcs = [e["payload"]["level_count"] for e in events]
        assert lcs == [1, 2, 3], f"level_count 非单调 · {lcs}"

        gwt.then("最后 1 条 escalated=True · 升级触发 audit 关联")
        assert events[-1]["payload"]["escalated"] is True
        assert events[-1]["payload"]["new_wp_state"] == "upgraded_to_l1_01"

        gwt.then("L1-04:rollback_escalated 附加事件落 · 升级路径硬约束")
        esc_events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:rollback_escalated",
            payload_contains={"wp_id": "wp-x", "level_count": 3},
        )
        assert len(esc_events) == 1
