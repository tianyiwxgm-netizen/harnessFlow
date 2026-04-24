"""WP02 · §2 正向用例（每 §3 public 方法 ≥ 1）。

对齐 3-2 §2 · 从 49 TC 中挑 WP02 核心路径 · 真实 nlp/dod/perf/e2e 留下次。
"""

from __future__ import annotations

import pytest
from typing import Callable
from unittest.mock import MagicMock

from app.quality_loop.tdd_blueprint import TDDBlueprintGenerator
from app.quality_loop.tdd_blueprint.schemas import (
    BroadcastReadyRequest,
    GenerateBlueprintRequest,
    GetBlueprintQuery,
    ValidateCoverageQuery,
)


class TestGenerateBlueprintPositive:
    """§3.1 正向。"""

    def test_TC_L104_L201_001_happy_path_50_ac(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request: Callable[..., GenerateBlueprintRequest],
    ) -> None:
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        assert resp.blueprint_id.startswith("bp-")
        assert resp.project_id == mock_project_id
        assert resp.status == "ACCEPTED"
        assert resp.version == 1
        assert resp.ts_accepted is not None

    def test_TC_L104_L201_002_idempotent_cache_hit(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        first = sut.generate_blueprint(req)
        second = sut.generate_blueprint(req)
        assert first.blueprint_id == second.blueprint_id
        assert second.status == "CACHED"

    def test_TC_L104_L201_003_async_accept_estimated_ts(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        assert resp.estimated_completion_ts is not None

    def test_TC_L104_L201_004_fail_l2_rebuild_with_previous(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req1 = make_generate_request(project_id=mock_project_id, clause_count=50)
        first = sut.generate_blueprint(req1)
        sut._force_state(first.blueprint_id, "FAILED")

        req2 = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            previous_blueprint_id=first.blueprint_id,
            nonce="retry-1",  # 打破幂等 cache
        )
        second = sut.generate_blueprint(req2)
        assert second.blueprint_id != first.blueprint_id
        assert second.version == first.version + 1

    def test_TC_L104_L201_005_retry_focus_partial_rebuild(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req1 = make_generate_request(project_id=mock_project_id, clause_count=50)
        first = sut.generate_blueprint(req1)
        sut._force_state(first.blueprint_id, "FAILED")

        req2 = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            previous_blueprint_id=first.blueprint_id,
            retry_focus=["test_pyramid", "coverage_target"],
            nonce="retry-2",
        )
        second = sut.generate_blueprint(req2)
        meta = sut._debug_rebuild_meta(second.blueprint_id)
        assert set(meta["rebuilt_sections"]) == {"test_pyramid", "coverage_target"}
        assert "ac_matrix" in meta["preserved_sections"]

    def test_TC_L104_L201_006_config_overrides_applied(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        req = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            config_overrides={"pyramid_default_ratio": [0.6, 0.3, 0.1]},
        )
        resp = sut.generate_blueprint(req)
        sut._await_ready(resp.blueprint_id)
        snap = sut.get_blueprint(
            GetBlueprintQuery(
                query_id="q-override",
                project_id=mock_project_id,
                blueprint_id=resp.blueprint_id,
                mode="full",
            )
        )
        assert snap.test_pyramid["unit_ratio"] == pytest.approx(0.6, abs=1e-6)
        assert snap.test_pyramid["integration_ratio"] == pytest.approx(0.3, abs=1e-6)
        assert snap.test_pyramid["e2e_ratio"] == pytest.approx(0.1, abs=1e-6)

    def test_TC_L104_L201_007_version_increment(
        self, sut, mock_project_id, make_generate_request
    ) -> None:
        r1 = sut.generate_blueprint(
            make_generate_request(project_id=mock_project_id, clause_count=50, nonce="v1")
        )
        sut._force_state(r1.blueprint_id, "FAILED")
        r2 = sut.generate_blueprint(
            make_generate_request(
                project_id=mock_project_id,
                clause_count=50,
                previous_blueprint_id=r1.blueprint_id,
                nonce="v2",
            )
        )
        sut._force_state(r2.blueprint_id, "FAILED")
        r3 = sut.generate_blueprint(
            make_generate_request(
                project_id=mock_project_id,
                clause_count=50,
                previous_blueprint_id=r2.blueprint_id,
                nonce="v3",
            )
        )
        assert (r1.version, r2.version, r3.version) == (1, 2, 3)


class TestGetBlueprintPositive:
    """§3.2 三种 mode。"""

    def test_TC_L104_L201_010_mode_full_returns_aggregate(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-001", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="full",
        )
        resp = sut.get_blueprint(query)
        assert resp.state in ("READY", "PUBLISHED")
        assert resp.test_pyramid is not None
        assert resp.ac_matrix is not None and len(resp.ac_matrix) > 0
        assert resp.coverage_target["ac"] == 1.0
        assert resp.test_env_blueprint is not None

    def test_TC_L104_L201_011_mode_wp_slice_returns_slice(
        self, sut, mock_project_id, ready_blueprint_id, sample_wp_id
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-002", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="wp_slice",
            wp_id=sample_wp_id,
        )
        resp = sut.get_blueprint(query)
        assert resp.wp_slice is not None
        assert resp.wp_slice["wp_id"] == sample_wp_id
        assert len(resp.wp_slice["related_ac_ids"]) >= 1
        assert "coverage_slice" in resp.wp_slice

    def test_TC_L104_L201_012_mode_metadata_only_omits_matrix(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-003", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="metadata_only",
        )
        resp = sut.get_blueprint(query)
        assert resp.blueprint_id == ready_blueprint_id
        assert resp.version is not None
        assert resp.state is not None
        assert resp.ac_matrix is None

    def test_TC_L104_L201_013_version_pinned(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        query = GetBlueprintQuery(
            query_id="q-004", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="full",
            version=1,
        )
        resp = sut.get_blueprint(query)
        assert resp.version == 1


class TestValidateCoveragePositive:
    """§3.3 AC 硬锁 1.0。"""

    def test_TC_L104_L201_020_ac_100_passes(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        q = ValidateCoverageQuery(
            query_id="q-cov-001",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            strict_mode=True,
        )
        rep = sut.validate_coverage(q)
        assert rep.valid is True
        assert rep.ac_coverage == 1.0
        assert rep.missing_ac_ids == []
        assert rep.priority_annotation_complete is True

    def test_TC_L104_L201_021_pyramid_ratios_normalized(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        rep = sut.validate_coverage(
            ValidateCoverageQuery(
                query_id="q-cov-002",
                project_id=mock_project_id,
                blueprint_id=ready_blueprint_id,
                strict_mode=True,
            )
        )
        assert rep.pyramid_ratios_valid is True

    def test_TC_L104_L201_022_strict_false_only_warns(
        self, sut, mock_project_id, blueprint_id_with_missing_ac
    ) -> None:
        rep = sut.validate_coverage(
            ValidateCoverageQuery(
                query_id="q-cov-003",
                project_id=mock_project_id,
                blueprint_id=blueprint_id_with_missing_ac,
                strict_mode=False,
            )
        )
        assert rep.valid is True
        assert any(iss["severity"] == "WARN" for iss in rep.issues)


class TestBroadcastReadyPositive:
    """§3.4 fanout + 幂等。"""

    def test_TC_L104_L201_030_fanout_to_three(
        self, sut, mock_project_id, fresh_ready_blueprint_factory,
        mock_event_bus: MagicMock,
    ) -> None:
        bp_id = fresh_ready_blueprint_factory()
        req = BroadcastReadyRequest(
            blueprint_id=bp_id,
            project_id=sut.repo.get(bp_id).project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        # 本次幂等 cache 已由 generate 内部写入 · 先清掉确保 fanout 真跑
        sut._broadcast_events.pop(bp_id, None)
        resp = sut.broadcast_ready(req)
        assert resp.published is True
        assert len(resp.fanout_acks) == 3
        assert {a["subscriber"] for a in resp.fanout_acks} == {"L2-02", "L2-03", "L2-04"}
        calls = [
            c for c in mock_event_bus.append_event.call_args_list
            if c.kwargs.get("event_type") == "L1-04:blueprint_ready"
        ]
        assert len(calls) >= 1

    def test_TC_L104_L201_031_duplicate_call_idempotent(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        bp = sut.repo.get(ready_blueprint_id)
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=bp.project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        r1 = sut.broadcast_ready(req)
        r2 = sut.broadcast_ready(req)
        assert r1.event_id == r2.event_id

    def test_TC_L104_L201_032_records_latency_ms(
        self, sut, mock_project_id, fresh_ready_blueprint_factory
    ) -> None:
        bp_id = fresh_ready_blueprint_factory()
        bp = sut.repo.get(bp_id)
        # 清 cache 让它真算一次
        sut._broadcast_events.pop(bp_id, None)
        req = BroadcastReadyRequest(
            blueprint_id=bp_id,
            project_id=bp.project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        resp = sut.broadcast_ready(req)
        assert isinstance(resp.latency_ms, int)
        assert resp.latency_ms >= 0
