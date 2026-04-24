"""WP02 · §4 IC 契约集成测试（IC-03 / IC-09 / IC-L2-01 / IC-13 / IC-16）。

对齐 3-2 §4 · 真实 IC-06 kb_read 接入 / IC-20 verifier delegate 留下次。
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.quality_loop.tdd_blueprint import TDDBlueprintGenerator
from app.quality_loop.tdd_blueprint.schemas import BroadcastReadyRequest


class TestICContracts:
    """§4 · IC 契约（每 IC ≥ 1 join test）。"""

    def test_TC_L104_L201_601_ic_03_consumes_phase_s3(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id, clause_count=50, entry_phase="S3"
        )
        resp = sut.generate_blueprint(req)
        assert resp.status in ("ACCEPTED", "CACHED")

    def test_TC_L104_L201_602_ic_06_optional_recipe_miss_ok(
        self, sut, mock_project_id, make_generate_request,
        mock_l1_06_kb: MagicMock,
    ) -> None:
        mock_l1_06_kb.kb_read.return_value = {"hits": [], "miss": True}
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        # WP02 · KB recipe 为可选 · miss 不影响构造
        assert resp.status == "ACCEPTED"

    def test_TC_L104_L201_603_ic_09_state_transition_events(
        self, sut, mock_project_id, make_generate_request,
        mock_event_bus: MagicMock,
    ) -> None:
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        sut._await_published(resp.blueprint_id)
        transitions = [
            (
                c.kwargs["payload"]["prev_state"],
                c.kwargs["payload"]["new_state"],
            )
            for c in mock_event_bus.append_event.call_args_list
            if c.kwargs.get("event_type") == "L1-04:blueprint_state_transition"
        ]
        assert (None, "DRAFT") in transitions or ("DRAFT", "VALIDATING") in transitions
        assert ("DRAFT", "VALIDATING") in transitions
        assert ("VALIDATING", "READY") in transitions
        assert ("READY", "PUBLISHED") in transitions

    def test_TC_L104_L201_604_ic_l2_01_payload_schema(
        self, sut, mock_project_id, fresh_ready_blueprint_factory,
        mock_event_bus: MagicMock,
    ) -> None:
        bp_id = fresh_ready_blueprint_factory()
        sut._broadcast_events.pop(bp_id, None)
        req = BroadcastReadyRequest(
            blueprint_id=bp_id,
            project_id=sut.repo.get(bp_id).project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        sut.broadcast_ready(req)
        call = next(
            c for c in mock_event_bus.append_event.call_args_list
            if c.kwargs.get("event_type") == "L1-04:blueprint_ready"
        )
        p = call.kwargs["payload"]
        for k in (
            "blueprint_id", "project_id", "version",
            "master_test_plan_path", "ac_matrix_path",
            "coverage_target_summary", "publisher", "ts",
        ):
            assert k in p
        assert p["publisher"] == "L1-04:L2-01"
        assert p["master_test_plan_path"].endswith("/tdd/master-test-plan.md")
        assert p["ac_matrix_path"].endswith("/tdd/ac-matrix.yaml")

    def test_TC_L104_L201_605_ic_13_warn_escalated_to_l1_07(
        self, sut, mock_project_id, make_generate_request,
        mock_l1_07: MagicMock,
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id, clause_count=50, simulate_stage_delay_s=310
        )
        for _ in range(3):
            with pytest.raises(Exception):
                sut.generate_blueprint(req)
        assert mock_l1_07.push_suggestion.call_count >= 1
        call = mock_l1_07.push_suggestion.call_args.kwargs
        assert call.get("level") in ("WARN", "SUGGEST")

    def test_TC_L104_L201_606_ic_16_stage_gate_via_l1_02(
        self, sut, mock_project_id, ready_blueprint_id,
        mock_l1_02: MagicMock,
    ) -> None:
        sut._publish(ready_blueprint_id)
        calls = [
            c for c in mock_l1_02.receive_artifact.call_args_list
            if c.kwargs.get("artifact_type") == "master_test_plan"
        ]
        assert len(calls) >= 1
        assert calls[0].kwargs["project_id"] == mock_project_id
