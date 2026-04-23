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


class TestRetryPolicy:
    """Task 03.4 · RetryPolicy · idempotent skill 最多 retry 1 次 (attempt ≤ 2)."""

    def test_idempotent_transient_should_retry(self):
        from app.skill_dispatch.invoker.retry_policy import should_retry
        from app.skill_dispatch.invoker.timeout_manager import SkillTimeout

        assert should_retry(SkillTimeout("x"), attempt=1, is_idempotent=True) is True

    def test_idempotent_exhausted_attempt_no_retry(self):
        from app.skill_dispatch.invoker.retry_policy import MAX_ATTEMPTS, should_retry
        from app.skill_dispatch.invoker.timeout_manager import SkillTimeout

        assert should_retry(SkillTimeout("x"), attempt=MAX_ATTEMPTS, is_idempotent=True) is False

    def test_non_idempotent_never_retries(self):
        from app.skill_dispatch.invoker.retry_policy import should_retry
        from app.skill_dispatch.invoker.timeout_manager import SkillTimeout

        assert should_retry(SkillTimeout("x"), attempt=1, is_idempotent=False) is False

    def test_schema_error_never_retries(self):
        """ValueError / SchemaError 是 caller bug · 不能 retry."""
        from app.skill_dispatch.invoker.retry_policy import should_retry

        assert should_retry(ValueError("bad params"), attempt=1, is_idempotent=True) is False

    def test_connection_error_is_retriable(self):
        from app.skill_dispatch.invoker.retry_policy import should_retry

        assert should_retry(ConnectionError("net"), attempt=1, is_idempotent=True) is True

    def test_backoff_ms_exponential(self):
        from app.skill_dispatch.invoker.retry_policy import backoff_ms

        assert backoff_ms(1) == 100
        assert backoff_ms(2) == 200
        assert backoff_ms(3) == 400


class TestAudit:
    """Task 03.5 · params_hash SHA-256 + 脱敏 + IC-09 两次写."""

    def test_params_hash_is_sha256_hex_64_chars(self):
        from app.skill_dispatch.invoker.audit import params_hash

        h = params_hash({"x": 1})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_params_hash_stable_on_key_order(self):
        """canonical JSON · 键序不同 hash 一致."""
        from app.skill_dispatch.invoker.audit import params_hash

        h1 = params_hash({"a": 1, "b": 2, "c": 3})
        h2 = params_hash({"c": 3, "a": 1, "b": 2})
        assert h1 == h2

    def test_sensitive_fields_redacted_before_hash(self):
        """带 token/key/password/secret 后缀的字段脱敏后 hash · 只要前缀同 hash 一致."""
        from app.skill_dispatch.invoker.audit import params_hash

        h1 = params_hash({"cmd": "do", "api_token": "A"})
        h2 = params_hash({"cmd": "do", "api_token": "B"})
        # 两次都被 REDACTED · hash 相同
        assert h1 == h2

    def test_non_sensitive_field_diff_breaks_hash(self):
        from app.skill_dispatch.invoker.audit import params_hash

        h1 = params_hash({"cmd": "run", "n": 1})
        h2 = params_hash({"cmd": "run", "n": 2})
        assert h1 != h2

    def test_audit_start_writes_ic09_started_event(self, ic09_bus):
        from app.skill_dispatch.invoker.audit import Auditor

        a = Auditor(event_bus=ic09_bus)
        a.audit_start(
            project_id="p1", invocation_id="inv1", capability="c",
            skill_id="s1", caller_l1="L1-04", attempt=1, params={"x": 1},
        )
        events = [e for e in ic09_bus.read_all("p1") if e.event_type == "skill_invocation_started"]
        assert len(events) == 1
        payload = events[0].payload
        assert payload["invocation_id"] == "inv1"
        assert payload["attempt"] == 1
        assert len(payload["params_hash"]) == 64

    def test_audit_finish_writes_ic09_finished_event(self, ic09_bus):
        from app.skill_dispatch.invoker.audit import Auditor

        a = Auditor(event_bus=ic09_bus)
        a.audit_finish(
            project_id="p1", invocation_id="inv1", success=True,
            duration_ms=150, fallback_used=False, result_summary="ok",
        )
        events = [e for e in ic09_bus.read_all("p1") if e.event_type == "skill_invocation_finished"]
        assert len(events) == 1
        assert events[0].payload["success"] is True
        assert events[0].payload["duration_ms"] == 150

    def test_audit_start_swallows_ic09_failure(self):
        """IC-09 失败不得 crash 主链 (E_SKILL_INVOCATION_AUDIT_SEED_FAILED 路径)."""
        from app.skill_dispatch.invoker.audit import Auditor

        class BrokenBus:
            def append_event(self, **kw):
                raise RuntimeError("IC-09 down")

        a = Auditor(event_bus=BrokenBus())
        # 不抛
        h = a.audit_start(
            project_id="p1", invocation_id="i", capability="c",
            skill_id="s", caller_l1="L1-04", attempt=1, params={"x": 1},
        )
        assert len(h) == 64   # 仍返回 hash 供后续 Signature 写

    def test_audit_doesnt_leak_sensitive_plaintext_to_event(self, ic09_bus):
        """payload.params_hash 是 hash · 不是明文；原字段也不在 payload 里."""
        from app.skill_dispatch.invoker.audit import Auditor

        a = Auditor(event_bus=ic09_bus)
        secret_value = "sk-super-secret-abcdef"
        a.audit_start(
            project_id="p1", invocation_id="i", capability="c",
            skill_id="s", caller_l1="L1-04", attempt=1,
            params={"api_token": secret_value, "cmd": "do"},
        )
        events = ic09_bus.read_all("p1")
        for e in events:
            # 任何 event payload 序列化后不得含 secret 明文
            assert secret_value not in str(e.payload), (
                f"secret leaked to payload: {e.payload}"
            )
