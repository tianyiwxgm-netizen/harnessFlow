"""WP02 · §3 负向用例 · 每错误码 ≥ 1。

对齐 3-2 §3 · 只覆盖 WP02 能判定的错误码（真实文件 mutate / concurrent race 留下次）。
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.quality_loop.tdd_blueprint import TDDBlueprintGenerator
from app.quality_loop.tdd_blueprint.schemas import (
    BroadcastReadyRequest,
    GetBlueprintQuery,
    TDDBlueprintError,
    ValidateCoverageQuery,
)


class TestNegativeGenerate:
    """§3.1 · 10 项错误码 + §11 扩展。"""

    def test_TC_L104_L201_101_missing_project_id_raises(
        self, sut: TDDBlueprintGenerator, make_generate_request
    ) -> None:
        req = make_generate_request(project_id=None, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_NO_PROJECT_ID"

    def test_TC_L104_L201_102_cross_project_previous_rejected(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id_of_other_project: str,
        make_generate_request,
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            previous_blueprint_id=ready_blueprint_id_of_other_project,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_CROSS_PROJECT_BLUEPRINT"

    def test_TC_L104_L201_103_invalid_phase_rejected(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id, clause_count=50, entry_phase="S2"
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_INVALID_PHASE"

    def test_TC_L104_L201_104_ac_empty_triggers_clarify(
        self,
        sut,
        mock_project_id,
        make_generate_request,
        mock_event_bus: MagicMock,
        mock_l1_07: MagicMock,
    ) -> None:
        req = make_generate_request(project_id=mock_project_id, clause_count=0)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_AC_EMPTY"
        types = [
            c.kwargs.get("event_type")
            for c in mock_event_bus.append_event.call_args_list
        ]
        assert "L1-04:blueprint_validation_failed" in types
        assert mock_l1_07.push_suggestion.called

    def test_TC_L104_L201_105_ac_missing_goes_to_awaiting(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id, clause_count=50, inject_unmapped_ac_count=1
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_AC_MISSING"

    def test_TC_L104_L201_106_four_pieces_missing_rejects(
        self, sut, mock_project_id, make_generate_request, mock_fs
    ) -> None:
        mock_fs.mark_missing(
            f"projects/{mock_project_id}/four-pieces/requirements.md"
        )
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_FOUR_PIECES_MISSING"

    def test_TC_L104_L201_107_wbs_not_ready_rejects(
        self, sut, mock_project_id, make_generate_request, mock_fs
    ) -> None:
        mock_fs.mark_missing(f"projects/{mock_project_id}/wbs/topology.yaml")
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_WBS_NOT_READY"

    def test_TC_L104_L201_108_build_timeout(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id, clause_count=50, simulate_stage_delay_s=310
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BUILD_TIMEOUT"

    def test_TC_L104_L201_109_source_refs_mutated(
        self, sut, mock_project_id, make_generate_request, mock_fs
    ) -> None:
        mock_fs.mutate_after_load(
            f"projects/{mock_project_id}/four-pieces/requirements.md"
        )
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_SOURCE_REFS_MUTATED"

    def test_TC_L104_L201_110_blueprint_too_large(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(project_id=mock_project_id, clause_count=5001)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_TOO_LARGE"


class TestNegativeGetBlueprint:
    """§3.2 · 4 项错误码。"""

    def test_TC_L104_L201_201_blueprint_not_found(
        self, sut, mock_project_id
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-nf", project_id=mock_project_id,
            blueprint_id="bp-does-not-exist", mode="full",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_NOT_FOUND"

    def test_TC_L104_L201_202_cross_project_read_blocked(
        self, sut, mock_project_id, ready_blueprint_id_of_other_project
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-xp", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id_of_other_project, mode="full",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_CROSS_PROJECT_READ"

    def test_TC_L104_L201_203_wp_slice_not_found(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-wp", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="wp_slice",
            wp_id="wp-ghost-999",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_WP_SLICE_NOT_FOUND"

    def test_TC_L104_L201_204_version_not_found(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-v", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="full", version=99,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_VERSION_NOT_FOUND"


class TestNegativeValidateCoverage:
    """§3.3 · 2 项错误码。"""

    def test_TC_L104_L201_301_validation_blueprint_not_found(
        self, sut, mock_project_id
    ) -> None:
        query = ValidateCoverageQuery(
            query_id="q-cov-nf",
            project_id=mock_project_id,
            blueprint_id="bp-ghost",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.validate_coverage(query)
        assert ei.value.code == "E_L204_L201_VALIDATION_BLUEPRINT_NOT_FOUND"

    def test_TC_L104_L201_302_validation_stale_read_race(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        sut._arm_concurrent_mutation(ready_blueprint_id)
        query = ValidateCoverageQuery(
            query_id="q-cov-stale",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.validate_coverage(query)
        assert ei.value.code == "E_L204_L201_VALIDATION_STALE_READ"


class TestNegativeBroadcast:
    """§3.4 · 3 项错误码 + §11 BROADCAST_FAILED 聚合。"""

    def test_TC_L104_L201_401_slo_violation_records_but_not_fails(
        self, sut, mock_project_id, ready_blueprint_id,
        mock_event_bus: MagicMock,
    ) -> None:
        mock_event_bus.set_broadcast_latency_ms(1500)
        sut._broadcast_events.pop(ready_blueprint_id, None)
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=sut.repo.get(ready_blueprint_id).project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        resp = sut.broadcast_ready(req)
        assert resp.published is True
        types = [
            c.kwargs.get("event_type")
            for c in mock_event_bus.append_event.call_args_list
        ]
        assert any(
            "blueprint_broadcast_slo_violation" in (t or "") for t in types
        )

    def test_TC_L104_L201_402_fanout_incomplete_one_offline(
        self, sut, mock_project_id, fresh_ready_blueprint_factory,
        mock_event_bus: MagicMock,
    ) -> None:
        bp_id = fresh_ready_blueprint_factory()
        sut._broadcast_events.pop(bp_id, None)
        mock_event_bus.set_subscriber_timeout("L2-02")
        req = BroadcastReadyRequest(
            blueprint_id=bp_id,
            project_id=sut.repo.get(bp_id).project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        resp = sut.broadcast_ready(req)
        assert resp.published is True
        types = [
            c.kwargs.get("event_type")
            for c in mock_event_bus.append_event.call_args_list
        ]
        assert "L1-04:blueprint_subscriber_unreachable" in types

    def test_TC_L104_L201_403_duplicate_broadcast_silent(
        self, sut, mock_project_id, ready_blueprint_id,
        mock_event_bus: MagicMock,
    ) -> None:
        sut._force_redundant_broadcast(ready_blueprint_id)
        types = [
            c.kwargs.get("event_type")
            for c in mock_event_bus.append_event.call_args_list
        ]
        assert "L1-04:blueprint_duplicate_broadcast" in types


class TestNegativeDegradationChain:
    """§11 降级等级扩展。"""

    def test_TC_L104_L201_501_ac_coverage_not_100_fail_l3(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id, clause_count=50, inject_unmapped_ac_count=2
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code in (
            "E_L204_L201_AC_COVERAGE_NOT_100",
            "E_L204_L201_BLUEPRINT_AC_MISSING",
        )
        assert ei.value.severity == "FAIL-L3"

    def test_TC_L104_L201_502_ac_case_explosion_truncates_and_warns(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            inject_ac_case_explosion_on_ac_index=3,
        )
        resp = sut.generate_blueprint(req)
        meta = sut._debug_build_meta(resp.blueprint_id)
        assert meta["warnings"]
        assert any(
            w["code"] == "E_L204_L201_AC_CASE_EXPLOSION" for w in meta["warnings"]
        )
        assert meta["truncated_slots_count"] > 0

    def test_TC_L104_L201_503_nlp_parse_failed_falls_back(
        self, sut, mock_project_id, make_generate_request,
        mock_nlp_backend: MagicMock,
    ) -> None:
        mock_nlp_backend.side_effect = RuntimeError("nlp_service_down")
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        assert resp.status == "ACCEPTED"
        meta = sut._debug_build_meta(resp.blueprint_id)
        assert meta["nlp_fallback_used"] is True

    def test_TC_L104_L201_504_broadcast_failed_fail_l2(
        self, sut, mock_project_id, fresh_ready_blueprint_factory,
        mock_event_bus: MagicMock,
    ) -> None:
        bp_id = fresh_ready_blueprint_factory()
        sut._broadcast_events.pop(bp_id, None)
        mock_event_bus.set_broadcast_all_fail()
        req = BroadcastReadyRequest(
            blueprint_id=bp_id,
            project_id=sut.repo.get(bp_id).project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.broadcast_ready(req)
        assert ei.value.code == "E_L204_L201_BROADCAST_FAILED"
        assert ei.value.severity == "FAIL-L2"
