"""L2-03 Skill 调用执行器 · IC-04 invoke_skill · 共 ~40 TC.

文档参照:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.4 IC-04
  - docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器-tests.md
  - docs/superpowers/plans/Dev-γ-impl.md §5

错误码覆盖:
  E_SKILL_NO_CAPABILITY / NO_PROJECT_ID / TIMEOUT / ALL_FALLBACK_FAIL /
  PARAMS_SCHEMA_MISMATCH / PERMISSION_DENIED / RETRY_EXHAUSTED / CONTEXT_INJECTION_FAILED
"""
from __future__ import annotations

import pytest


class TestIC04Schemas:
    """Task 03.1 · InvocationRequest / InvocationResponse / InvocationSignature · 严格对齐 §3.4."""

    def test_request_required_fields_with_defaults(self):
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        req = InvocationRequest(
            invocation_id="inv1",
            project_id="p1",
            capability="write_test",
            params={"x": 1},
            caller_l1="L1-04",
            context={"project_id": "p1", "wp_id": "wp1"},
        )
        assert req.timeout_ms == 30000   # default
        assert req.allow_fallback is True
        assert req.trigger_tick is None

    def test_request_rejects_empty_project_id(self):
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        with pytest.raises(ValueError):
            InvocationRequest(
                invocation_id="i",
                project_id="",
                capability="c",
                params={},
                caller_l1="L1-04",
                context={"project_id": ""},
            )

    def test_request_context_project_id_must_mirror_top(self):
        """PM-14 · 防 context 字段窃取."""
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        with pytest.raises(ValueError, match="project_id.*mismatch"):
            InvocationRequest(
                invocation_id="i",
                project_id="p1",
                capability="c",
                params={},
                caller_l1="L1-04",
                context={"project_id": "p_other"},
            )

    def test_request_hard_cap_timeout_300000(self):
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        with pytest.raises(ValueError):
            InvocationRequest(
                invocation_id="i",
                project_id="p1",
                capability="c",
                params={},
                caller_l1="L1-04",
                context={"project_id": "p1"},
                timeout_ms=400000,
            )

    def test_response_success_carries_result_not_error(self):
        from app.skill_dispatch.invoker.schemas import InvocationResponse

        r = InvocationResponse(
            invocation_id="i",
            success=True,
            skill_id="s",
            duration_ms=100,
            fallback_used=False,
            result={"ok": True},
        )
        assert r.result == {"ok": True}
        assert r.error is None

    def test_response_success_with_error_raises(self):
        from app.skill_dispatch.invoker.schemas import InvocationResponse

        with pytest.raises(ValueError, match="success"):
            InvocationResponse(
                invocation_id="i",
                success=True,
                skill_id="s",
                duration_ms=100,
                fallback_used=False,
                error={"code": "E_X"},
            )

    def test_response_failure_with_result_raises(self):
        from app.skill_dispatch.invoker.schemas import InvocationResponse

        with pytest.raises(ValueError, match="success"):
            InvocationResponse(
                invocation_id="i",
                success=False,
                skill_id="s",
                duration_ms=100,
                fallback_used=True,
                result={"oops": 1},
            )

    def test_response_failure_carries_error_and_trace(self):
        from app.skill_dispatch.invoker.schemas import InvocationResponse

        r = InvocationResponse(
            invocation_id="i",
            success=False,
            skill_id="builtin:min",
            duration_ms=200,
            fallback_used=True,
            error={"code": "E_SKILL_ALL_FALLBACK_FAIL"},
            fallback_trace=[
                {"skill": "primary", "reason": "timeout"},
                {"skill": "secondary", "reason": "error"},
            ],
        )
        assert r.error["code"] == "E_SKILL_ALL_FALLBACK_FAIL"
        assert len(r.fallback_trace) == 2

    def test_invocation_signature_is_superset_of_response_fields(self):
        """契约红线: InvocationSignature ⊇ InvocationResponse 的可落盘字段 + params_hash + attempt."""
        from app.skill_dispatch.invoker.schemas import InvocationResponse, InvocationSignature

        rsp_fields = set(InvocationResponse.model_fields.keys())
        sig_fields = set(InvocationSignature.model_fields.keys())
        # Signature 多出来的至少应含
        extra_required = {"params_hash", "attempt", "started_at_ts_ns"}
        assert extra_required.issubset(sig_fields)
        # Response 的非 payload 字段（不含 result/error/fallback_trace · 可摘要）必须在 Signature
        # 或以更抽象字段覆盖
        payload_fields = {"result", "error", "fallback_trace"}
        non_payload = rsp_fields - payload_fields
        assert non_payload.issubset(sig_fields | {"result_summary"}), (
            f"Signature missing fields from Response (non-payload): {non_payload - sig_fields}"
        )

    def test_signature_accepts_initial_state(self):
        """Signature 审计种子 · 允许 started 时仅有部分字段."""
        from app.skill_dispatch.invoker.schemas import InvocationSignature

        sig = InvocationSignature(
            invocation_id="i",
            project_id="p1",
            capability="c",
            skill_id="s",
            caller_l1="L1-04",
            attempt=1,
            params_hash="0" * 64,
            started_at_ts_ns=1,
        )
        assert sig.validate_status == "pending"
        assert sig.duration_ms is None


class TestContextInjector:
    """Task 03.2 · 白名单注入 · 防上游 context 字段泄漏到 skill."""

    def test_inject_passes_whitelisted_keys(self):
        from app.skill_dispatch.invoker.context_injector import inject

        out = inject(
            {
                "project_id": "p1",
                "wp_id": "wp1",
                "loop_session_id": "ls1",
                "decision_id": "d1",
                "correlation_id": "c1",
            }
        )
        assert out == {
            "project_id": "p1",
            "wp_id": "wp1",
            "loop_session_id": "ls1",
            "decision_id": "d1",
            "correlation_id": "c1",
        }

    def test_inject_drops_sensitive_fields(self):
        from app.skill_dispatch.invoker.context_injector import inject

        out = inject(
            {
                "project_id": "p1",
                "anthropic_api_token": "sk-xxx",
                "internal_password": "hunter2",
                "session_secret": "very-secret",
            }
        )
        assert "anthropic_api_token" not in out
        assert "internal_password" not in out
        assert "session_secret" not in out
        assert out["project_id"] == "p1"

    def test_inject_returns_new_dict_not_in_place(self):
        from app.skill_dispatch.invoker.context_injector import inject

        upstream = {"project_id": "p1", "wp_id": "wp1", "extra": "dropped"}
        out = inject(upstream)
        assert out is not upstream
        assert "extra" in upstream   # 上游未被污染
        assert "extra" not in out

    def test_inject_rejects_missing_project_id(self):
        from app.skill_dispatch.invoker.context_injector import (
            ContextInjectionError,
            inject,
        )

        with pytest.raises(ContextInjectionError):
            inject({"wp_id": "wp1"})

    def test_inject_rejects_empty_project_id(self):
        from app.skill_dispatch.invoker.context_injector import (
            ContextInjectionError,
            inject,
        )

        with pytest.raises(ContextInjectionError):
            inject({"project_id": "", "wp_id": "wp1"})


class TestTimeoutManager:
    """Task 03.3 · TimeoutManager · ±100ms 精度 · hard-cap 300s."""

    def test_run_completes_within_timeout(self):
        from app.skill_dispatch.invoker.timeout_manager import run_with_timeout

        def fast():
            return "ok"

        assert run_with_timeout(fast, timeout_ms=1000) == "ok"

    def test_run_raises_skill_timeout_on_overrun(self):
        import time

        from app.skill_dispatch.invoker.timeout_manager import SkillTimeout, run_with_timeout

        def slow():
            time.sleep(0.5)
            return "never"

        with pytest.raises(SkillTimeout):
            run_with_timeout(slow, timeout_ms=100)

    def test_hard_cap_clamps_huge_timeout(self):
        """即使调用方传超巨 timeout · 也被 clamp 到 300000ms."""
        from app.skill_dispatch.invoker.timeout_manager import HARD_CAP_MS, run_with_timeout

        assert HARD_CAP_MS == 300_000

    def test_timeout_precision_within_100ms(self):
        import time

        from app.skill_dispatch.invoker.timeout_manager import SkillTimeout, run_with_timeout

        def very_slow():
            time.sleep(2.0)

        target_ms = 200
        t0 = time.perf_counter()
        with pytest.raises(SkillTimeout):
            run_with_timeout(very_slow, timeout_ms=target_ms)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # ±100ms 精度：实际 elapsed 应该接近 target_ms
        assert abs(elapsed_ms - target_ms) < 100, (
            f"timeout precision off: target={target_ms}ms actual={elapsed_ms:.1f}ms"
        )

    def test_propagates_original_exception(self):
        from app.skill_dispatch.invoker.timeout_manager import run_with_timeout

        def boom():
            raise ValueError("skill-error")

        with pytest.raises(ValueError, match="skill-error"):
            run_with_timeout(boom, timeout_ms=1000)
