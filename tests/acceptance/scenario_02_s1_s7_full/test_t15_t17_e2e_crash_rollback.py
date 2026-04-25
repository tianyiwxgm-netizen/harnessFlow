"""scenario_02 · T15-T17 · 完整 e2e + 中途崩溃恢复 + 跨阶段回滚.

T15 · 完整 7 阶段 e2e 一气呵成 · 全程 < 5min · 总 IC ≥ 28 events
T16 · 中途崩溃恢复 (S3 后崩溃 → checkpoint snapshot → recover → 续走)
T17 · 跨阶段回滚 (S3 通过后 reject 回 S2 · re_open_count 增)
"""
from __future__ import annotations

import time

from app.l1_09.checkpoint import RecoveryAttempt, SnapshotJob
from app.l1_09.event_bus.core import EventBus
from app.project_lifecycle.stage_gate import StageGateController
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)


async def test_t15_full_e2e_seven_stages(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T15 · S1→S7 完整 e2e 一气呵成 · 单 TC 跑全 7 阶段.

    Then:
        - 5 次 IC-01 transition (S1/S2/S3/S5/S7)
        - 总 IC-09 events ≥ 20 (每 transition 至少 4 events)
        - hash chain 跨 5 transitions 完整
        - 全程 < 5s (mock 模式 · 不跑真 LLM)
    """
    async with gwt("T15 · 完整 7 阶段 e2e · S1→S7 一气呵成"):
        gwt.given(f"干净 project={project_id} · INITIALIZED")
        before = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert before == 0
        assert l1_01_spy.calls == []

        gwt.when("依次跑 S1 → S2 → S3 → (S4 progress) → S5 → (S6 progress) → S7")
        t0 = time.monotonic()

        # S1 → INITIALIZED → PLANNING
        d1, _ = advance_stage("S1", current_state="INITIALIZED")
        assert d1.decision == "pass"

        # S2 → PLANNING → TDD_PLANNING
        d2, _ = advance_stage("S2", current_state="PLANNING")
        assert d2.decision == "pass"

        # S3 → TDD_PLANNING → EXECUTING
        d3, _ = advance_stage("S3", current_state="TDD_PLANNING")
        assert d3.decision == "pass"

        # S4 stage_progress · 直接落 IC-09(无 IC-01)
        from app.l1_09.event_bus.schemas import Event
        from datetime import UTC, datetime

        real_event_bus.append(Event(
            project_id=project_id,
            type="L1-02:stage_progress",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"stage": "S4", "signal": "all_wp_complete"},
        ))

        # S5 → EXECUTING → CLOSING
        d5, _ = advance_stage("S5", current_state="EXECUTING")
        assert d5.decision == "pass"

        # S6 stage_progress
        real_event_bus.append(Event(
            project_id=project_id,
            type="L1-02:stage_progress",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"stage": "S6", "signal": "deploy_runbook_ready"},
        ))

        # S7 → CLOSING → CLOSED
        d7, _ = advance_stage("S7", current_state="CLOSING")
        assert d7.decision == "pass"
        elapsed = time.monotonic() - t0

        gwt.then("5 次 IC-01 transition · 全 spy 调用")
        assert len(l1_01_spy.calls) == 5
        # 检查 IC-01 路径完整 (各阶段 to_state)
        transition_path = [c["to_state"] for c in l1_01_spy.calls]
        assert transition_path == ["PLANNING", "TDD_PLANNING", "EXECUTING", "CLOSING", "CLOSED"]

        gwt.then("总 IC-09 events ≥ 20 (5 transition × 4 events) + 2 stage_progress")
        n_events = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n_events >= 22, f"7 stage e2e 至少 22 events · 实际={n_events}"

        gwt.then("全程 < 5s (mock 模式)")
        assert elapsed < 5.0, f"7 stage e2e 耗时 {elapsed:.2f}s 超 5s"

        gwt.then("hash chain 跨全 5 transitions 完整")
        # 已在上面 assert_ic_09_hash_chain_intact 校验


async def test_t16_mid_stage_crash_recovery(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    snapshot_job: SnapshotJob,
    recovery_attempt: RecoveryAttempt,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T16 · 中途 S3 后崩溃 · checkpoint snapshot · recover · 验证状态可读.

    模拟过程:
        1. 跑完 S1+S2+S3
        2. 触发 SnapshotJob.take_snapshot(pid)
        3. 模拟崩溃(只销毁内存对象 · 落盘 events.jsonl + checkpoints/ 仍在)
        4. 用新 RecoveryAttempt + 同 bus_root 调 recover_from_checkpoint
        5. 验证 recovered_state 可读 + hash chain 仍完整
    """
    async with gwt("T16 · S3 后崩溃 → snapshot → recover · 状态完整"):
        gwt.given("跑到 S3 完成")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")

        # 记录 pre-crash state
        events_before = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert events_before > 10
        ic01_before = len(l1_01_spy.calls)
        assert ic01_before == 3

        gwt.when("触发 SnapshotJob.take_snapshot 落 checkpoint")
        snap = snapshot_job.take_snapshot(project_id)
        assert snap.last_event_sequence == events_before
        assert snap.checkpoint_id

        gwt.and_("模拟崩溃 · 仅销毁内存对象 · 物理盘不动")
        # 销毁 stage_gate / spy 内存(模拟进程重启 · 物理 events + ckpt 仍在)
        del stage_gate

        gwt.when("用新 RecoveryAttempt 重建状态")
        recovered = recovery_attempt.recover_from_checkpoint(project_id)

        gwt.then("recovered_state 可读 · last_event_sequence 一致")
        assert recovered.project_id == project_id
        assert recovered.checkpoint_id_used == snap.checkpoint_id
        assert recovered.last_event_sequence_replayed == events_before
        assert recovered.hash_chain_valid is True

        gwt.then("hash chain 跨 crash 仍完整")
        events_after = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert events_after == events_before  # 未丢失


async def test_t17_cross_stage_rollback(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T17 · 跨阶段回滚 · S3 gate 通过后 user reject → re_open S2 · re_open_count 增."""
    async with gwt("T17 · 跨阶段回滚 · S3 gate 通过后 reject → re_open"):
        gwt.given("已通过 S1 + S2 · 处 TDD_PLANNING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")

        gwt.when("S3 gate 评估 pass · 但 user reject(发现质量风险)")
        from app.project_lifecycle.stage_gate import EvidenceBundle
        ev_s3 = EvidenceBundle(
            project_id=project_id,
            stage="S3",
            request_id="req-s3-rollback",
            signals=("tdd_blueprint_ready",),
            caller_l2="L2-02",
        )
        dec_s3 = stage_gate.request_gate_decision(ev_s3, current_state="TDD_PLANNING")
        assert dec_s3.decision == "pass"

        # user reject · 触发 rollback
        result = stage_gate.receive_user_decision(
            gate_id=dec_s3.gate_id,
            user_decision="reject",
            change_requests=("blueprint missing API contract for L1-04",),
        )

        gwt.then("user_decision=reject · re_open_count=1")
        assert result["user_decision"] == "reject"
        assert result["re_open_count"] == 1

        gwt.then("IC-01 不再 advance (gate 被 reject 后无 transition 发起)")
        # S1+S2 共 2 IC-01 · S3 reject 不调
        assert len(l1_01_spy.calls) == 2

        gwt.then("IC-09 落 gate_rolled_back · payload 含 change_requests")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_rolled_back",
            payload_contains={"gate_id": dec_s3.gate_id, "re_open_count": 1},
        )
        assert events
        assert "blueprint missing API contract for L1-04" in events[0]["payload"]["change_requests"]

        gwt.then("第二次 reject · re_open_count=2 (验证累计)")
        # 重新评估 + 再 reject
        ev_s3_v2 = EvidenceBundle(
            project_id=project_id,
            stage="S3",
            request_id="req-s3-rollback-v2",
            signals=("tdd_blueprint_ready",),
            caller_l2="L2-02",
        )
        dec_s3_v2 = stage_gate.request_gate_decision(ev_s3_v2, current_state="TDD_PLANNING")
        result_v2 = stage_gate.receive_user_decision(
            gate_id=dec_s3_v2.gate_id,
            user_decision="reject",
            change_requests=("still missing details",),
        )
        assert result_v2["re_open_count"] == 2
