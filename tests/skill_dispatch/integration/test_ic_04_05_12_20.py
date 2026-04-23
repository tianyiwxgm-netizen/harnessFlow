"""4 IC 契约集成测 · 字段级对齐 ic-contracts.md §3.4/3.5/3.12/3.20.

文档参照:
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
  - docs/superpowers/plans/Dev-γ-impl.md §8 Task 06.2
"""
from __future__ import annotations

import pytest


@pytest.mark.integration
class TestICContracts:
    """IC-04/05/12/20 schema 字段集合对齐校验."""

    def test_ic_04_request_matches_contract(self):
        """InvocationRequest 必含 §3.4.2 字段 + Signature ⊇ Response + ts."""
        from app.skill_dispatch.invoker.schemas import (
            InvocationRequest,
            InvocationResponse,
            InvocationSignature,
        )

        req_fields = set(InvocationRequest.model_fields.keys())
        required_req_fields = {
            "invocation_id", "project_id", "capability", "params",
            "caller_l1", "context", "timeout_ms", "allow_fallback", "trigger_tick",
            "ts",   # P1-01 · §3.4.2 required
        }
        assert required_req_fields.issubset(req_fields), (
            f"IC-04 §3.4.2 fields missing: {required_req_fields - req_fields}"
        )

        rsp_fields = set(InvocationResponse.model_fields.keys())
        required_rsp_fields = {
            "invocation_id", "success", "skill_id", "duration_ms", "fallback_used",
            "result", "error", "fallback_trace",
        }
        assert required_rsp_fields.issubset(rsp_fields)

        sig_fields = set(InvocationSignature.model_fields.keys())
        # Signature 必须有 params_hash 超集证据
        assert {"params_hash", "attempt", "started_at_ts_ns"}.issubset(sig_fields)

    def test_ic_05_delegation_request_matches_contract(self):
        """DelegationRequest 对齐 §3.5.2."""
        from app.skill_dispatch.subagent.schemas import DelegationRequest, DispatchAck, FinalReport

        req_fields = set(DelegationRequest.model_fields.keys())
        required = {
            "delegation_id", "project_id", "role", "task_brief",
            "context_copy", "caller_l1", "allowed_tools", "timeout_s",
            "ts",   # P1-01 · §3.5.2 required
        }
        assert required.issubset(req_fields)

        ack_fields = set(DispatchAck.model_fields.keys())
        assert {"delegation_id", "dispatched", "subagent_session_id"}.issubset(ack_fields)

        fr_fields = set(FinalReport.model_fields.keys())
        assert {
            "subagent_session_id", "delegation_id", "status",
            "artifacts", "final_message", "usage",
        }.issubset(fr_fields)

    def test_ic_12_codebase_onboarding_matches_contract(self):
        """CodebaseOnboardingRequest 对齐 §3.12.2."""
        from app.skill_dispatch.subagent.schemas import (
            CodebaseOnboardingRequest,
            OnboardingFinalReport,
        )

        req_fields = set(CodebaseOnboardingRequest.model_fields.keys())
        required = {
            "delegation_id", "project_id", "repo_path", "kb_write_back",
            "focus", "timeout_s",
            "ts",   # P1-01 · §3.12.2 required
        }
        assert required.issubset(req_fields)

        final_fields = set(OnboardingFinalReport.model_fields.keys())
        assert {"delegation_id", "status", "structure_summary", "kb_entries_written"}.issubset(
            final_fields
        )

    def test_ic_20_verifier_matches_contract(self):
        """VerifierRequest 对齐 §3.20.2 + allowed_tools 严格白名单 + acceptance_criteria type: object."""
        from app.skill_dispatch.subagent.schemas import (
            AcceptanceCriteria,
            VerifierRequest,
            VerifierVerdict,
        )

        req_fields = set(VerifierRequest.model_fields.keys())
        required = {
            "delegation_id", "project_id", "wp_id", "blueprint_slice",
            "s4_snapshot", "acceptance_criteria", "timeout_s", "allowed_tools",
            "ts",   # P1-01 · §3.20.2 required
        }
        assert required.issubset(req_fields)

        # 严格 allowed_tools 白名单硬约束（schema 层已测）
        with pytest.raises(ValueError):
            VerifierRequest(
                delegation_id="d", project_id="p1", wp_id="wp1",
                blueprint_slice={}, s4_snapshot={},
                acceptance_criteria=AcceptanceCriteria(),   # P1-02 · 对齐 type: object
                allowed_tools=["Read", "Write"],   # Write 禁用
            )

        verdict_fields = set(VerifierVerdict.model_fields.keys())
        assert {
            "delegation_id", "verdict", "three_segment_evidence",
            "confidence", "duration_ms",
        }.issubset(verdict_fields)
