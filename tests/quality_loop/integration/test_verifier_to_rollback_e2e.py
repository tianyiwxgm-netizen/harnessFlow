"""WP08 · e2e · 场景 4 · Verifier FAIL_L1-L4 → RollbackRouter.ic_14_consumer → L2 stage rollback.

覆盖 WP06 (L2-06 Verifier) → Dev-ζ IC-14 → WP07 (L2-07 RollbackRouter) 全链。

**验证点**:
- VerifierVerdict.FAIL_L1/L2/L3/L4 → Dev-ζ PushRollbackRouteCommand 合法映射
- RollbackRouter.IC14Consumer 消费 · classify + map + execute
- state_transition mock(L1-02)· event_bus mock(L1-09)· L2 边界真实
- 同级 ≥ 3 升级全链路

**铁律**:
- WP06 产 VerifiedResult 手工构造(模拟 verifier 真实返值结构)
- WP07 真实 import(IC14Consumer + VerdictClassifier + StageMapper + RollbackExecutor)
- 仅 mock L1-02 state_transition + L1-09 event_bus(非 L2 间)
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    RouteEvidence,
    RollbackSeverity,
    TargetStage,
)
from app.quality_loop.verifier.schemas import (
    SignatureCheckResult,
    VerifiedResult,
    VerifierVerdict,
)


# =============================================================================
# Helpers · VerifierVerdict → IC-14 PushRollbackRouteCommand
# =============================================================================


# Dev-ζ 合法映射(与 rollback_pusher._LEGAL_MAPPING 对齐)
_VERDICT_TO_STAGE: dict[VerifierVerdict, TargetStage] = {
    VerifierVerdict.FAIL_L1: TargetStage.S3,
    VerifierVerdict.FAIL_L2: TargetStage.S4,
    VerifierVerdict.FAIL_L3: TargetStage.S5,
    VerifierVerdict.FAIL_L4: TargetStage.UPGRADE_TO_L1_01,
}


def _verdict_to_fail_verdict(v: VerifierVerdict) -> FailVerdict:
    """VerifierVerdict(WP06) → FailVerdict(Dev-ζ / WP07)."""
    assert v != VerifierVerdict.PASS, "PASS 不走 IC-14 rollback"
    return FailVerdict(v.value)


def _build_rollback_command_from_verified_result(
    vr: VerifiedResult,
    *,
    level_count: int = 1,
    route_id: str | None = None,
) -> PushRollbackRouteCommand:
    """把 WP06 VerifiedResult → Dev-ζ IC-14 command(模拟 supervisor 转译)."""
    fv = _verdict_to_fail_verdict(vr.verdict)
    target = _VERDICT_TO_STAGE[vr.verdict]
    rid = route_id or f"route-{vr.delegation_id}"
    return PushRollbackRouteCommand(
        route_id=rid,
        project_id=vr.project_id,
        wp_id=vr.wp_id,
        verdict=fv,
        target_stage=target,
        level_count=level_count,
        evidence=RouteEvidence(
            verifier_report_id=vr.verifier_report_id or f"vr-{vr.delegation_id}",
        ),
        ts="2026-04-23T10:00:00Z",
    )


def _make_verified_result(
    *, project_id: str, wp_id: str, verdict: VerifierVerdict,
    delegation_id: str = "ver-e2e",
) -> VerifiedResult:
    """构造 VerifiedResult(仅为 e2e 桥接 · 真实 orchestrate_s5 流程已在场景 3 覆盖)。"""
    sig_ok = verdict == VerifierVerdict.PASS
    return VerifiedResult(
        project_id=project_id,
        delegation_id=delegation_id,
        wp_id=wp_id,
        verdict=verdict,
        signatures=SignatureCheckResult(
            blueprint_alignment_ok=sig_ok or verdict != VerifierVerdict.FAIL_L2,
            s4_diff_analysis_ok=sig_ok or verdict != VerifierVerdict.FAIL_L1,
            blueprint_detail={"ok": sig_ok},
            s4_diff_detail={"ok": sig_ok},
        ),
        dod_evaluation={"verdict": verdict.value},
        three_segment_evidence={
            "blueprint_alignment": {"ok": True},
            "s4_diff_analysis": {"ok": True},
            "dod_evaluation": {"verdict": verdict.value},
        },
        verifier_session_id="sub-e2e",
        duration_ms=1234,
        verifier_report_id=f"vr-{delegation_id}",
    )


# =============================================================================
# Mock L1-02 state_transition + L1-09 event_bus
# =============================================================================


class RecordingStateTransition:
    """L1-02 IC-01 state_transition 端点 mock · 记录每次调用。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def state_transition(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"transitioned": True, "new_state": kwargs.get("new_wp_state")}


class RecordingEventBus:
    """L1-09 append_event mock · 记录所有审计事件。"""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def append_event(
        self, *, project_id: str, type: str, payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str:
        self.events.append({
            "project_id": project_id, "type": type,
            "payload": payload, "evidence_refs": evidence_refs,
        })
        return f"ev-{len(self.events)}"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pid() -> str:
    return "proj-wp08-verifier-rollback"


@pytest.fixture
def consumer_bundle(pid: str):
    """IC14Consumer + recorded stateTransition/eventBus · 三件套复用。"""
    st = RecordingStateTransition()
    bus = RecordingEventBus()
    c = IC14Consumer(session_pid=pid, state_transition=st, event_bus=bus)
    return c, st, bus


# =============================================================================
# 场景 4.1 · FAIL_L1 → WARN → S3 retry(stage 内 retry)
# =============================================================================


class TestVerifierFailL1ToRollbackWarn:
    """VerifierVerdict.FAIL_L1 → FAIL_L1 → S3 retry_s3 · severity=WARN."""

    @pytest.mark.asyncio
    async def test_TC_E2E_VER_RB_01_fail_l1_to_retry_s3(
        self, consumer_bundle, pid: str,
    ) -> None:
        """TC-E2E-VER-RB-01 · FAIL_L1 → IC-14 → retry_s3 · severity=WARN · 不升级."""
        consumer, st, bus = consumer_bundle
        vr = _make_verified_result(
            project_id=pid, wp_id="wp-l1-01", verdict=VerifierVerdict.FAIL_L1,
            delegation_id="ver-l1-01",
        )
        cmd = _build_rollback_command_from_verified_result(vr, level_count=1)
        ack: PushRollbackRouteAck = await consumer.consume(cmd)

        assert ack.applied is True
        assert ack.new_wp_state.value == "retry_s3"
        assert ack.escalated is False
        # L1-02 state_transition 调 1 次
        assert len(st.calls) == 1
        assert st.calls[0]["new_wp_state"] == "retry_s3"
        assert st.calls[0]["target_stage"] == TargetStage.S3.value
        assert st.calls[0]["severity"] == RollbackSeverity.WARN.value
        # 审计事件含 rollback_executed(未 escalated · 无 rollback_escalated)
        types = [e["type"] for e in bus.events]
        assert "L1-04:rollback_executed" in types
        assert "L1-04:rollback_escalated" not in types


# =============================================================================
# 场景 4.2 · FAIL_L2 → FAIL → S4 / FAIL_L3 → FAIL → S5
# =============================================================================


class TestVerifierFailL2L3ToStageRetry:
    """中度失败的两个 verdict · FAIL_L2→S4 · FAIL_L3→S5."""

    @pytest.mark.asyncio
    async def test_TC_E2E_VER_RB_02_fail_l2_to_retry_s4(
        self, consumer_bundle, pid: str,
    ) -> None:
        """TC-E2E-VER-RB-02 · FAIL_L2(蓝图不齐) → retry_s4 · severity=FAIL."""
        consumer, st, bus = consumer_bundle
        vr = _make_verified_result(
            project_id=pid, wp_id="wp-l2-02", verdict=VerifierVerdict.FAIL_L2,
            delegation_id="ver-l2-02",
        )
        cmd = _build_rollback_command_from_verified_result(vr, level_count=1)
        ack = await consumer.consume(cmd)
        assert ack.new_wp_state.value == "retry_s4"
        assert ack.escalated is False
        assert st.calls[0]["severity"] == RollbackSeverity.FAIL.value

    @pytest.mark.asyncio
    async def test_TC_E2E_VER_RB_03_fail_l3_to_retry_s5(
        self, consumer_bundle, pid: str,
    ) -> None:
        """TC-E2E-VER-RB-03 · FAIL_L3(DoD 未过) → retry_s5 · severity=FAIL."""
        consumer, st, bus = consumer_bundle
        vr = _make_verified_result(
            project_id=pid, wp_id="wp-l3-03", verdict=VerifierVerdict.FAIL_L3,
            delegation_id="ver-l3-03",
        )
        cmd = _build_rollback_command_from_verified_result(vr, level_count=1)
        ack = await consumer.consume(cmd)
        assert ack.new_wp_state.value == "retry_s5"
        assert st.calls[0]["target_stage"] == TargetStage.S5.value


# =============================================================================
# 场景 4.3 · FAIL_L4 → CRITICAL → UPGRADE_TO_L1_01
# =============================================================================


class TestVerifierFailL4ToUpgrade:
    """深度失败 · FAIL_L4 → UPGRADE_TO_L1_01 · severity=CRITICAL."""

    @pytest.mark.asyncio
    async def test_TC_E2E_VER_RB_04_fail_l4_to_upgrade(
        self, consumer_bundle, pid: str,
    ) -> None:
        """TC-E2E-VER-RB-04 · FAIL_L4(超时/委托失败) → UPGRADE_TO_L1_01 · CRITICAL.

        注意: FAIL_L4 首次不 escalated(非 '同级 ≥ 3' 触发)· 但 state=UPGRADE_TO_L1_01。
        """
        consumer, st, bus = consumer_bundle
        vr = _make_verified_result(
            project_id=pid, wp_id="wp-l4-04", verdict=VerifierVerdict.FAIL_L4,
            delegation_id="ver-l4-04",
        )
        cmd = _build_rollback_command_from_verified_result(vr, level_count=1)
        ack = await consumer.consume(cmd)
        assert ack.new_wp_state.value == "upgraded_to_l1_01"
        # FAIL_L4 首次 · escalated=False(同级连续 ≥ 3 才为 True)
        assert ack.escalated is False
        assert st.calls[0]["target_stage"] == TargetStage.UPGRADE_TO_L1_01.value
        assert st.calls[0]["severity"] == RollbackSeverity.CRITICAL.value


# =============================================================================
# 场景 4.4 · 同级 ≥ 3 → escalated upgrade
# =============================================================================


class TestVerifierSameLevel3Escalation:
    """同 (wp, verdict) 连续 3 次失败 · 即使是 FAIL_L1 也强制升级。"""

    @pytest.mark.asyncio
    async def test_TC_E2E_VER_RB_05_fail_l1_level3_escalated_upgrade(
        self, consumer_bundle, pid: str,
    ) -> None:
        """TC-E2E-VER-RB-05 · FAIL_L1 连 3 次(level_count=3)→ UPGRADE_TO_L1_01 · escalated=True.

        验证 stage_mapper.ESCALATION_THRESHOLD=3 硬常量 · 对任何 verdict 生效。
        """
        consumer, st, bus = consumer_bundle
        vr = _make_verified_result(
            project_id=pid, wp_id="wp-esc-05", verdict=VerifierVerdict.FAIL_L1,
            delegation_id="ver-esc-05",
        )
        cmd = _build_rollback_command_from_verified_result(vr, level_count=3)
        ack = await consumer.consume(cmd)
        assert ack.new_wp_state.value == "upgraded_to_l1_01"
        assert ack.escalated is True
        # escalated · 应有 rollback_escalated 审计事件
        types = [e["type"] for e in bus.events]
        assert "L1-04:rollback_escalated" in types


# =============================================================================
# 场景 4.5 · 幂等 · 同 route_id 重复消费 → 单次执行
# =============================================================================


class TestVerifierRollbackIdempotency:
    """Dev-ζ 幂等 key = route_id · 重复消费返 cached ack."""

    @pytest.mark.asyncio
    async def test_TC_E2E_VER_RB_06_idempotent_by_route_id(
        self, consumer_bundle, pid: str,
    ) -> None:
        """TC-E2E-VER-RB-06 · 同 route_id 二次消费 · state_transition 只调 1 次."""
        consumer, st, bus = consumer_bundle
        vr = _make_verified_result(
            project_id=pid, wp_id="wp-idem-06", verdict=VerifierVerdict.FAIL_L2,
            delegation_id="ver-idem-06",
        )
        cmd = _build_rollback_command_from_verified_result(vr, level_count=1)
        ack1 = await consumer.consume(cmd)
        ack2 = await consumer.consume(cmd)
        # 两次返相同 ack 对象(cached)
        assert ack1 == ack2
        # state_transition 只调 1 次
        assert len(st.calls) == 1
        # is_processed 断言
        assert consumer.is_processed(cmd.route_id) is True
