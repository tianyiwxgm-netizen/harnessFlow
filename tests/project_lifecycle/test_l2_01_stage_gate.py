"""L2-01 StageGateController 测试 · 对齐 3-2 TDD md §2/§3。

TC 精选：
  - TC-001/002 request_gate_decision pass
  - TC-003 need_input 缺信号
  - TC-006 authorize_transition PLANNING→TDD_PLANNING
  - TC-007 reason < 20 字 拒
  - TC-008/009 receive_user_decision approve / reject
  - TC-011 rollback_gate
  - TC-013 query_gate_state
  - TC-016 合法转换（state_machine.validate）
  - TC-102 TRANSITION_FORBIDDEN
  - TC-106 PM14_OWNERSHIP_VIOLATION
  - TC-113 GATE_AUTO_TIMEOUT 启动拒绝
  - IC: TC-401 IC-01 唯一发起 · TC-403 IC-09 事件 · TC-405 IC-17 user_intervene
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.stage_gate import (
    ALLOWED_TRANSITIONS,
    EvidenceBundle,
    StageGateController,
    StageGateError,
    StartupConfigError,
    is_allowed,
    validate_transition,
)
from app.project_lifecycle.stage_gate.errors import (
    E_PM14_OWNERSHIP_VIOLATION,
    E_TRANSITION_FORBIDDEN,
)


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def l1_01() -> MagicMock:
    m = MagicMock()
    m.request_state_transition.return_value = {"ok": True, "ic_01_tx_id": "tx-1"}
    return m


@pytest.fixture
def sut(event_bus, l1_01) -> StageGateController:
    return StageGateController(event_bus=event_bus, l1_01_state_machine=l1_01)


def _evidence_full(stage: str = "S2", signals=None) -> EvidenceBundle:
    if signals is None:
        signals = {
            "S1": ("charter_ready", "stakeholders_ready", "goal_anchor_hash_locked"),
            "S2": ("4_pieces_ready", "9_plans_ready", "togaf_ready", "wbs_ready"),
            "S3": ("tdd_blueprint_ready",),
        }.get(stage, ())
    return EvidenceBundle(
        project_id="p_test00000000-1234-5678-9abc-def012345678",
        stage=stage, request_id=f"req-{stage}-1",
        signals=signals, caller_l2="L2-02",
    )


class TestL2_01_StateMachine:

    def test_TC_L102_L201_016_validate_legal_transitions(self) -> None:
        """12 合法边全部 is_allowed=True。"""
        for f, t in ALLOWED_TRANSITIONS:
            assert is_allowed(f, t), f"{f}→{t} should be allowed"

    def test_TC_L102_L201_102_transition_forbidden(self) -> None:
        """非法转换拒绝 · E_TRANSITION_FORBIDDEN。"""
        with pytest.raises(StageGateError) as exc:
            validate_transition("INITIALIZED", "CLOSED")
        assert exc.value.error_code == E_TRANSITION_FORBIDDEN


class TestL2_01_RequestGateDecision:

    def test_TC_L102_L201_001_s1_gate_pass(self, sut: StageGateController) -> None:
        ev = _evidence_full("S1")
        dec = sut.request_gate_decision(ev, current_state="INITIALIZED")
        assert dec.decision == "pass"
        assert dec.from_state == "INITIALIZED"
        assert dec.to_state == "PLANNING"

    def test_TC_L102_L201_002_s2_gate_pass_full_evidence(self, sut: StageGateController) -> None:
        dec = sut.request_gate_decision(_evidence_full("S2"))
        assert dec.decision == "pass"
        assert dec.to_state == "TDD_PLANNING"

    def test_TC_L102_L201_003_need_input_missing_togaf(self, sut: StageGateController) -> None:
        """S2 signals 缺 togaf_ready · decision=need_input · missing_signals 含 togaf_ready。"""
        ev = _evidence_full("S2", signals=("4_pieces_ready", "9_plans_ready", "wbs_ready"))
        dec = sut.request_gate_decision(ev)
        assert dec.decision == "need_input"
        assert "togaf_ready" in dec.missing_signals

    def test_TC_L102_L201_004_same_request_id_idempotent(self, sut: StageGateController) -> None:
        """同 request_id 两次调用返同 decision。"""
        ev = _evidence_full("S2")
        d1 = sut.request_gate_decision(ev)
        d2 = sut.request_gate_decision(ev)
        assert d1.gate_id == d2.gate_id
        assert d1.decision == d2.decision


class TestL2_01_AuthorizeTransition:

    def test_TC_L102_L201_006_planning_to_tdd_planning(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        result = sut.authorize_transition(
            project_id="p_abc00000-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="gate-s2-1",
            reason="S2 Gate approved · all evidence ready · moving to TDD",
        )
        assert result.success is True
        assert result.emitted_ic01 is True
        l1_01.request_state_transition.assert_called_once()

    def test_TC_L102_L201_007_reason_too_short_rejected(self, sut: StageGateController) -> None:
        with pytest.raises(StageGateError) as exc:
            sut.authorize_transition(
                project_id="p_x00000000-1234-5678-9abc-def012345678",
                from_state="PLANNING", to_state="TDD_PLANNING",
                gate_id="g1", reason="ok",
            )
        assert exc.value.error_code == E_TRANSITION_FORBIDDEN

    def test_TC_L102_L201_106_non_L2_01_caller_rejected(
        self, sut: StageGateController,
    ) -> None:
        """PM-14 越权 · 非 L2-01 caller 拒 · E_PM14_OWNERSHIP_VIOLATION。"""
        for bad_caller in ("L2-02", "L2-07", "L1-05", "external"):
            with pytest.raises(StageGateError) as exc:
                sut.authorize_transition(
                    project_id="p_y00000000-1234-5678-9abc-def012345678",
                    from_state="PLANNING", to_state="TDD_PLANNING",
                    gate_id="g-yy", reason="authorize from external caller test",
                    caller=bad_caller,
                )
            assert exc.value.error_code == E_PM14_OWNERSHIP_VIOLATION


class TestL2_01_UserDecisionAndRollback:

    def test_TC_L102_L201_008_receive_user_approve_triggers_transition(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        dec = sut.request_gate_decision(_evidence_full("S2"))
        result = sut.receive_user_decision(
            gate_id=dec.gate_id, user_decision="approve",
            reason="user approved S2 gate after review of 4 pieces and TOGAF",
        )
        assert result["user_decision"] == "approve"
        assert result["transition_success"] is True
        # IC-01 发了
        l1_01.request_state_transition.assert_called_once()

    def test_TC_L102_L201_009_receive_user_reject_triggers_rollback(
        self, sut: StageGateController,
    ) -> None:
        dec = sut.request_gate_decision(_evidence_full("S2"))
        result = sut.receive_user_decision(
            gate_id=dec.gate_id, user_decision="reject",
            change_requests=("improve AC",),
        )
        assert result["user_decision"] == "reject"
        assert result["re_open_count"] == 1

    def test_TC_L102_L201_011_rollback_gate_re_open_count(
        self, sut: StageGateController,
    ) -> None:
        dec = sut.request_gate_decision(_evidence_full("S2"))
        r1 = sut.rollback_gate(dec.gate_id, change_requests=("x",))
        r2 = sut.rollback_gate(dec.gate_id, change_requests=("y",))
        assert r1.new_re_open_count == 1
        assert r2.new_re_open_count == 2

    def test_TC_L102_L201_013_query_gate_state(
        self, sut: StageGateController,
    ) -> None:
        dec = sut.request_gate_decision(_evidence_full("S2"))
        snap = sut.query_gate_state(dec.gate_id)
        assert snap is not None
        assert snap.gate_id == dec.gate_id
        assert snap.stage == "S2"


class TestL2_01_StartupConfig:

    def test_TC_L102_L201_113_gate_auto_timeout_enabled_crashes(
        self, event_bus, l1_01,
    ) -> None:
        """启动 config 置 GATE_AUTO_TIMEOUT_ENABLED=true · 必 crash（tech §10）。"""
        with pytest.raises(StartupConfigError):
            StageGateController(
                event_bus=event_bus, l1_01_state_machine=l1_01,
                config={"GATE_AUTO_TIMEOUT_ENABLED": True},
            )


class TestL2_01_IcContracts:

    def test_TC_L102_L201_401_ic_01_sole_authorization_path(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        """唯一 IC-01 发起方 · 每次 authorize_transition 调 l1_01.request_state_transition 一次。"""
        sut.authorize_transition(
            project_id="p_ic01test-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="g-ic01", reason="IC-01 sole authorization test path here",
        )
        calls = l1_01.request_state_transition.call_args_list
        assert len(calls) == 1
        kw = calls[0].kwargs
        assert kw["project_id"].startswith("p_")
        assert kw["from_state"] == "PLANNING"
        assert kw["to_state"] == "TDD_PLANNING"

    def test_TC_L102_L201_403_ic_09_gate_lifecycle_events(
        self, sut: StageGateController, event_bus: MagicMock,
    ) -> None:
        """Gate 生命周期事件：decision_computed / closed（approve 后）。"""
        dec = sut.request_gate_decision(_evidence_full("S2"))
        sut.receive_user_decision(
            gate_id=dec.gate_id, user_decision="approve",
            reason="approve for IC-09 event test gate closure chain",
        )
        events = [c.kwargs["event_type"] for c in event_bus.append_event.call_args_list]
        assert "gate_decision_computed" in events
        assert "state_transition_authorized" in events
        assert "gate_closed" in events

    def test_TC_L102_L201_405_ic_17_user_intervene_paths(
        self, sut: StageGateController,
    ) -> None:
        """IC-17 3 分支：approve / reject / request_change。"""
        for ud in ("approve", "reject", "request_change"):
            dec = sut.request_gate_decision(EvidenceBundle(
                project_id=f"p_intervene{ud:<10s}"[:10] + "-1234-5678-9abc-def012345678",
                stage="S2",
                request_id=f"req-{ud}",
                signals=("4_pieces_ready", "9_plans_ready", "togaf_ready", "wbs_ready"),
            ))
            result = sut.receive_user_decision(
                gate_id=dec.gate_id, user_decision=ud,
                reason="user decision path test with enough chars here",
            )
            assert result["user_decision"] == ud


class TestL2_01_IC01_Payload:
    """IC-01 §3.1.2 入参字段完整性 · fix-2026-04-23 P1-01。

    §3.1.2 required: [transition_id, project_id, from, to, reason,
                      trigger_tick, evidence_refs, ts]
    """

    def test_TC_L102_L201_410_ic_01_payload_contains_transition_id(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        """§3.1.2 · transition_id 必填 · 格式 trans-{uuid}."""
        sut.authorize_transition(
            project_id="p_payload0-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="g-payload-1",
            reason="P1-01 fix · IC-01 required field test transition_id",
            trigger_tick="tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a20",
            evidence_refs=("gate-payload-1",),
        )
        kw = l1_01.request_state_transition.call_args.kwargs
        assert "transition_id" in kw, "missing transition_id"
        assert kw["transition_id"].startswith("trans-"), \
            f"bad transition_id format: {kw['transition_id']!r}"

    def test_TC_L102_L201_411_ic_01_payload_contains_trigger_tick(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        """§3.1.2 · trigger_tick 必填 · 审计追溯链。"""
        sut.authorize_transition(
            project_id="p_payload1-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="g-payload-2",
            reason="P1-01 fix · IC-01 required field test trigger_tick here",
            trigger_tick="tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a20",
            evidence_refs=("g-payload-2",),
        )
        kw = l1_01.request_state_transition.call_args.kwargs
        assert "trigger_tick" in kw, "missing trigger_tick"
        assert kw["trigger_tick"] == "tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a20"

    def test_TC_L102_L201_412_ic_01_payload_contains_evidence_refs(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        """§3.1.2 · evidence_refs minItems=1."""
        sut.authorize_transition(
            project_id="p_payload2-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="g-payload-3",
            reason="P1-01 fix · IC-01 required evidence_refs test path here",
            trigger_tick="tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a21",
            evidence_refs=("g-payload-3", "artifact-abc-1"),
        )
        kw = l1_01.request_state_transition.call_args.kwargs
        assert "evidence_refs" in kw
        assert isinstance(kw["evidence_refs"], (list, tuple))
        assert len(kw["evidence_refs"]) >= 1
        assert "g-payload-3" in kw["evidence_refs"]

    def test_TC_L102_L201_413_ic_01_payload_contains_ts_iso8601(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        """§3.1.2 · ts ISO-8601 utc · Z 后缀。"""
        sut.authorize_transition(
            project_id="p_payload3-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="g-payload-4",
            reason="P1-01 fix · IC-01 required ts iso8601 test path here",
            trigger_tick="tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a22",
            evidence_refs=("g-payload-4",),
        )
        kw = l1_01.request_state_transition.call_args.kwargs
        assert "ts" in kw
        ts = kw["ts"]
        # ISO-8601 粗校验
        assert "T" in ts
        assert ts.endswith("Z"), f"ts should end with Z: {ts!r}"

    def test_TC_L102_L201_414_ic_01_payload_reject_empty_evidence_refs(
        self, sut: StageGateController,
    ) -> None:
        """§3.1.2 minItems:1 · evidence_refs 为空 raise（schema 校验）."""
        with pytest.raises(StageGateError):
            sut.authorize_transition(
                project_id="p_payload4-1234-5678-9abc-def012345678",
                from_state="PLANNING", to_state="TDD_PLANNING",
                gate_id="g-payload-5",
                reason="P1-01 fix · IC-01 schema check empty evidence_refs",
                trigger_tick="tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a23",
                evidence_refs=(),  # 空 → 拒
            )

    def test_TC_L102_L201_415_ic_01_transition_id_unique_per_call(
        self, sut: StageGateController, l1_01: MagicMock,
    ) -> None:
        """幂等键 transition_id · 同 instance 两次 call 得两个 transition_id（不缓存）。"""
        sut.authorize_transition(
            project_id="p_payload5-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="g-payload-6",
            reason="P1-01 fix · IC-01 transition_id uniqueness test 1",
            trigger_tick="tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a24",
            evidence_refs=("g-payload-6",),
        )
        sut.authorize_transition(
            project_id="p_payload5-1234-5678-9abc-def012345678",
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="g-payload-7",
            reason="P1-01 fix · IC-01 transition_id uniqueness test 2",
            trigger_tick="tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a25",
            evidence_refs=("g-payload-7",),
        )
        calls = l1_01.request_state_transition.call_args_list
        assert len(calls) == 2
        t1 = calls[0].kwargs["transition_id"]
        t2 = calls[1].kwargs["transition_id"]
        assert t1 != t2, "transition_id should be unique per invocation"


class TestL2_01_IC16_PushCard:
    """IC-16 push_stage_gate_card · fix-2026-04-23 P1-02。

    §3.16.2 required: [card_id, project_id, gate_id, stage_name,
                       artifacts_bundle, trim_level]
    """

    @pytest.fixture
    def ui_stub(self) -> MagicMock:
        """L1-10 UI IC-16 接收方 · mock ack。"""
        m = MagicMock()
        m.push_stage_gate_card_to_ui.return_value = {
            "card_id": "card-stub-1",
            "displayed": True,
            "render_ms": 120,
            "session_persisted": True,
        }
        return m

    @pytest.fixture
    def sut_with_ui(self, event_bus, l1_01, ui_stub) -> StageGateController:
        return StageGateController(
            event_bus=event_bus, l1_01_state_machine=l1_01, ui_bridge=ui_stub,
        )

    def test_TC_L102_L201_420_ic_16_push_card_called_on_gate_pass(
        self, sut_with_ui: StageGateController, ui_stub: MagicMock,
    ) -> None:
        """Gate pass 时 · push_stage_gate_card_to_ui 被调一次。"""
        sut_with_ui.request_gate_decision(_evidence_full("S2"))
        assert ui_stub.push_stage_gate_card_to_ui.call_count == 1

    def test_TC_L102_L201_421_ic_16_payload_required_fields(
        self, sut_with_ui: StageGateController, ui_stub: MagicMock,
    ) -> None:
        """§3.16.2 required 字段必备: card_id/project_id/gate_id/stage_name/artifacts_bundle/trim_level。"""
        dec = sut_with_ui.request_gate_decision(_evidence_full("S2"))
        payload = ui_stub.push_stage_gate_card_to_ui.call_args.kwargs["command"]
        for k in (
            "card_id", "project_id", "gate_id", "stage_name",
            "artifacts_bundle", "trim_level",
        ):
            assert k in payload, f"§3.16.2 missing required field {k!r}"
        assert payload["gate_id"] == dec.gate_id
        assert payload["stage_name"] == "S2"
        assert payload["card_id"].startswith("card-")

    def test_TC_L102_L201_422_ic_16_artifacts_bundle_min_items(
        self, sut_with_ui: StageGateController, ui_stub: MagicMock,
    ) -> None:
        """§3.16.5 E_CARD_BUNDLE_EMPTY · artifacts_bundle 至少 1 项。"""
        sut_with_ui.request_gate_decision(_evidence_full("S2"))
        payload = ui_stub.push_stage_gate_card_to_ui.call_args.kwargs["command"]
        assert isinstance(payload["artifacts_bundle"], (list, tuple))
        assert len(payload["artifacts_bundle"]) >= 1
        # 单项 schema: required [artifact_type, path, summary]
        for art in payload["artifacts_bundle"]:
            assert "artifact_type" in art
            assert "path" in art
            assert "summary" in art

    def test_TC_L102_L201_423_ic_16_allowed_decisions_and_blocks_progress(
        self, sut_with_ui: StageGateController, ui_stub: MagicMock,
    ) -> None:
        """§3.16.2 · allowed_decisions 含 approve/reject/request_change · blocks_progress=True。"""
        sut_with_ui.request_gate_decision(_evidence_full("S2"))
        payload = ui_stub.push_stage_gate_card_to_ui.call_args.kwargs["command"]
        assert "allowed_decisions" in payload
        assert set(payload["allowed_decisions"]) == {"approve", "reject", "request_change"}
        assert payload.get("blocks_progress", True) is True

    def test_TC_L102_L201_424_ic_16_not_called_on_need_input(
        self, sut_with_ui: StageGateController, ui_stub: MagicMock,
    ) -> None:
        """need_input 分支 · 不推送卡片（§3.16.1 只 pass 时推）。"""
        ev = _evidence_full("S2", signals=("4_pieces_ready",))  # 缺 3 个信号
        dec = sut_with_ui.request_gate_decision(ev)
        assert dec.decision == "need_input"
        assert ui_stub.push_stage_gate_card_to_ui.call_count == 0

    def test_TC_L102_L201_425_ic_16_no_ui_bridge_no_crash(
        self, sut: StageGateController,
    ) -> None:
        """未注入 ui_bridge · pass 正常工作 · IC-16 降级为 no-op（向后兼容）。"""
        dec = sut.request_gate_decision(_evidence_full("S2"))
        assert dec.decision == "pass"  # 不 crash · UI 缺失不阻塞决策

    def test_TC_L102_L201_426_ic_16_ts_iso8601(
        self, sut_with_ui: StageGateController, ui_stub: MagicMock,
    ) -> None:
        """§3.16.2 ts ISO-8601 Z。"""
        sut_with_ui.request_gate_decision(_evidence_full("S2"))
        payload = ui_stub.push_stage_gate_card_to_ui.call_args.kwargs["command"]
        assert "ts" in payload
        assert "T" in payload["ts"]
        assert payload["ts"].endswith("Z")


class TestL2_01_IC16_Stub:
    """IC-16 event-bus-only stub · 无 ui_bridge 时走 IC-09 事件。"""

    def test_TC_L102_L201_427_ic_16_event_fallback_emitted(
        self, sut: StageGateController, event_bus: MagicMock,
    ) -> None:
        """未注入 ui_bridge 时 · 发 IC-09 ic_16_push_stage_gate_card 事件（降级审计路径）。"""
        sut.request_gate_decision(_evidence_full("S2"))
        events = [c.kwargs["event_type"] for c in event_bus.append_event.call_args_list]
        assert "ic_16_push_stage_gate_card" in events

    def test_TC_L102_L201_428_ic_16_event_payload_schema(
        self, sut: StageGateController, event_bus: MagicMock,
    ) -> None:
        """降级事件 payload 与 §3.16.2 schema 对齐。"""
        sut.request_gate_decision(_evidence_full("S2"))
        ic16_events = [
            c for c in event_bus.append_event.call_args_list
            if c.kwargs["event_type"] == "ic_16_push_stage_gate_card"
        ]
        assert len(ic16_events) == 1
        payload = ic16_events[0].kwargs["payload"]
        for k in ("card_id", "project_id", "gate_id", "stage_name",
                  "artifacts_bundle", "trim_level", "allowed_decisions",
                  "blocks_progress", "ts"):
            assert k in payload, f"降级事件 missing {k}"


class TestL2_01_IC16_Builder:
    """ic_16_stub.build_push_stage_gate_card_command · 直接 unit-level 校验。"""

    def test_TC_L102_L201_430_builder_rejects_empty_gate_id(self) -> None:
        from app.project_lifecycle.stage_gate import build_push_stage_gate_card_command
        with pytest.raises(ValueError, match="E_CARD_GATE_ID_MISMATCH"):
            build_push_stage_gate_card_command(
                gate_id="", project_id="p_x", stage_name="S2",
            )

    def test_TC_L102_L201_431_builder_rejects_empty_project_id(self) -> None:
        from app.project_lifecycle.stage_gate import build_push_stage_gate_card_command
        with pytest.raises(ValueError, match="E_CARD_NO_PROJECT_ID"):
            build_push_stage_gate_card_command(
                gate_id="g1", project_id="", stage_name="S2",
            )

    def test_TC_L102_L201_432_builder_rejects_empty_bundle(self) -> None:
        from app.project_lifecycle.stage_gate import build_push_stage_gate_card_command
        with pytest.raises(ValueError, match="E_CARD_BUNDLE_EMPTY"):
            build_push_stage_gate_card_command(
                gate_id="g1", project_id="p_x", stage_name="S2",
                artifacts_bundle=[],
            )

    def test_TC_L102_L201_433_builder_rejects_bad_trim_level(self) -> None:
        from app.project_lifecycle.stage_gate import build_push_stage_gate_card_command
        with pytest.raises(ValueError, match="E_CARD_TRIM_UNSUPPORTED"):
            build_push_stage_gate_card_command(
                gate_id="g1", project_id="p_x", stage_name="S2",
                trim_level="bogus",
            )
