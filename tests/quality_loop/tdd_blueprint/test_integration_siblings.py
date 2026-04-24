"""WP02 · §8 集成点用例（与 L2-02/03/04 协作 · IC-L2-01 fanout + get_blueprint pull）。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.quality_loop.tdd_blueprint.schemas import (
    GetBlueprintQuery,
    ValidateCoverageQuery,
)


class TestSiblingIntegration:
    def test_TC_L104_L201_901_l2_02_03_04_read_same_ac_matrix(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        q = GetBlueprintQuery(
            query_id="q-int", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="full",
        )
        r_l202 = sut.get_blueprint(q)
        r_l203 = sut.get_blueprint(q)
        r_l204 = sut.get_blueprint(q)
        assert r_l202.ac_matrix == r_l203.ac_matrix == r_l204.ac_matrix
        assert r_l202.version == r_l203.version == r_l204.version

    def test_TC_L104_L201_902_fail_l2_rebuild_rebroadcasts(
        self, sut, mock_project_id, make_generate_request,
        mock_l2_02: MagicMock, mock_l2_03: MagicMock, mock_l2_04: MagicMock,
    ) -> None:
        r1 = sut.generate_blueprint(
            make_generate_request(project_id=mock_project_id, clause_count=50, nonce="sib-1")
        )
        sut._await_published(r1.blueprint_id)
        mock_l2_02.on_blueprint_ready.reset_mock()
        mock_l2_03.on_blueprint_ready.reset_mock()
        mock_l2_04.on_blueprint_ready.reset_mock()

        sut._force_state(r1.blueprint_id, "FAILED")
        r2 = sut.generate_blueprint(
            make_generate_request(
                project_id=mock_project_id,
                clause_count=50,
                previous_blueprint_id=r1.blueprint_id,
                retry_focus=["ac_matrix"],
                nonce="sib-2",
            )
        )
        sut._await_published(r2.blueprint_id)
        assert r2.version == 2
        assert mock_l2_02.on_blueprint_ready.called
        assert mock_l2_03.on_blueprint_ready.called
        assert mock_l2_04.on_blueprint_ready.called

    def test_TC_L104_L201_903_l2_04_calls_validate_coverage(
        self, sut, mock_project_id, ready_blueprint_id
    ) -> None:
        q = ValidateCoverageQuery(
            query_id="q-l204",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            strict_mode=True,
        )
        rep = sut.validate_coverage(q)
        assert rep.valid is True
        assert rep.ac_coverage == 1.0
