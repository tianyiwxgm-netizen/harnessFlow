"""L1-06 L2-02 · IC contracts (4 TC) · 3-2 §4."""
from __future__ import annotations

from app.knowledge_base.reader.schemas import ApplicableContext, ReadRequest
from app.knowledge_base.reader.service import KBReadService


class TestL2_02_IC_Contracts:

    def test_TC_L106_L202_601_ic_06_contract_fields(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=1, project=1, global_=1)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        res = sut.read(req)
        for field in ("entries", "trace_id", "meta", "error_hint"):
            assert hasattr(res, field)

    def test_TC_L106_L202_602_l2_01_scope_check_invoked(
        self, sut: KBReadService, mock_l2_01, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=1)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        sut.read(req)
        mock_l2_01.scope_check.assert_called_once()

    def test_TC_L106_L202_603_l2_05_rerank_invoked_with_top_k(
        self, sut: KBReadService, mock_l2_05, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=3, project=3, global_=3)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=4,
        )
        sut.read(req)
        args = mock_l2_05.rerank.call_args[0][0]
        assert args.top_k == 4

    def test_TC_L106_L202_604_ic_09_audit_always(
        self, sut: KBReadService, mock_audit, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.fail_all_layers(OSError("down"))
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        sut.read(req)
        assert mock_audit.append.called
