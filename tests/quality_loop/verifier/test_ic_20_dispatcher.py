"""TC-L104-L206 · ic_20_dispatcher · IC-20 delegate_verifier 生产端.

核心 TC：
- build_ic_20_command · VerificationRequest → IC20Command 字段级转换
- verify_session_prefix · 合法 sub- · 非法 main./ 空 / =main_session_id 硬红线
- dispatch_with_retry happy 第 1 次成功
- dispatch_with_retry attempt 2 成功 · backoff 记录
- dispatch_with_retry 3 次全失败 → DelegationFailureError
- dispatched=False 也算失败 · 走重试
- SessionPrefixViolationError 不重试 · 直接 up
- max_retries 硬锁 ≤ 3
- audit emitter 正常收事件（dispatched / failed）
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.verifier.ic_20_dispatcher import (
    DelegationFailureError,
    DispatcherError,
    SessionPrefixViolationError,
    build_ic_20_command,
    dispatch_with_retry,
    verify_session_prefix,
)
from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerificationRequest,
)


def _mk_req(**o: Any) -> VerificationRequest:
    defaults: dict[str, Any] = {
        "project_id": "proj-A",
        "wp_id": "wp-1",
        "blueprint_slice": {"dod_expression": "tests_pass", "red_tests": ["t1"]},
        "s4_snapshot": {"artifact_refs": ["a.py"], "git_head": "abc", "test_report": {}},
        "acceptance_criteria": {"gate": True},
        "main_session_id": "main-12345",
        "delegation_id": "ver-abc123",
        "timeout_s": 600,
        "ts": "2026-04-23T10:00:00Z",
    }
    defaults.update(o)
    return VerificationRequest(**defaults)


# ==============================================================================
# build_ic_20_command
# ==============================================================================


class TestBuildIC20Command:
    """TC-L104-L206-300 · 构造 IC-20 Command."""

    def test_build_from_request(self) -> None:
        """happy · 字段级映射 · frozen."""
        req = _mk_req()
        cmd = build_ic_20_command(req)
        assert isinstance(cmd, IC20Command)
        assert cmd.delegation_id == req.delegation_id
        assert cmd.project_id == req.project_id
        assert cmd.wp_id == req.wp_id
        assert cmd.blueprint_slice == req.blueprint_slice
        assert cmd.timeout_s == req.timeout_s
        # default allowed_tools
        assert cmd.allowed_tools == ("Read", "Glob", "Grep", "Bash")

    def test_build_is_pure_function(self) -> None:
        """同入参 · 同出参 (frozen)."""
        req = _mk_req()
        c1 = build_ic_20_command(req)
        c2 = build_ic_20_command(req)
        assert c1 == c2


# ==============================================================================
# verify_session_prefix
# ==============================================================================


class TestVerifySessionPrefix:
    """TC-L104-L206-310 · session_id 前缀校验硬红线."""

    def test_valid_sub_prefix(self) -> None:
        """合法 · sub-... 前缀."""
        verify_session_prefix("sub-xyz-12345", "main-12345")  # no raise

    def test_empty_rejected(self) -> None:
        """空 → E17."""
        with pytest.raises(SessionPrefixViolationError) as exc:
            verify_session_prefix("", "main-123")
        assert "E17" in str(exc.value)

    def test_none_rejected(self) -> None:
        """None → E17."""
        with pytest.raises(SessionPrefixViolationError):
            verify_session_prefix(None, "main-123")

    def test_non_sub_prefix_rejected(self) -> None:
        """非 sub- 前缀 → E17."""
        with pytest.raises(SessionPrefixViolationError) as exc:
            verify_session_prefix("verifier-12345", "main-123")
        assert "E17" in str(exc.value)

    def test_equals_main_session_rejected(self) -> None:
        """等于 main_session_id → E20."""
        with pytest.raises(SessionPrefixViolationError) as exc:
            verify_session_prefix("main-12345", "main-12345")
        assert "E17" in str(exc.value) or "E20" in str(exc.value)

    def test_main_dot_prefix_rejected(self) -> None:
        """main. 前缀 → E17（防 L1-05 退化）."""
        with pytest.raises(SessionPrefixViolationError) as exc:
            verify_session_prefix("main.child-xyz", "main-12345")
        assert "E17" in str(exc.value) or "PM-03" in str(exc.value)


# ==============================================================================
# dispatch_with_retry
# ==============================================================================


class FakeDelegator:
    """L1-05 delegate_verifier mock stub · 可注入故障."""

    def __init__(
        self,
        *,
        behavior: list[Any] | None = None,
        session_id: str | None = "sub-gen-001",
    ) -> None:
        """Args:
        behavior: 每次 delegate_verifier() 调用的返回值列表（按顺序）· 元素可以是:
            - IC20DispatchResult · 正常返回
            - Exception instance · 抛此异常
            - None · 用 default session_id 返回 dispatched=True
        session_id: 默认的 session_id（非 None 时）。
        """
        self.behavior = behavior or []
        self.session_id = session_id
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        idx = len(self.calls) - 1
        if idx < len(self.behavior):
            b = self.behavior[idx]
            if isinstance(b, Exception):
                raise b
            if isinstance(b, IC20DispatchResult):
                return b
        # default
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id=self.session_id,
        )


async def no_sleep(_: float) -> None:
    """Test sleep · 不延迟."""
    return None


class AuditCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


class TestDispatchWithRetryHappy:
    """TC-L104-L206-320 · dispatch happy."""

    @pytest.mark.asyncio
    async def test_first_attempt_success(self) -> None:
        """第 1 次就成功 · 不重试."""
        req = _mk_req()
        fake = FakeDelegator(session_id="sub-xyz-001")
        result = await dispatch_with_retry(req, fake, sleep=no_sleep)
        assert result.dispatched is True
        assert result.verifier_session_id == "sub-xyz-001"
        assert len(fake.calls) == 1

    @pytest.mark.asyncio
    async def test_audit_dispatched_event_emitted(self) -> None:
        """派发成功 · audit emitter 收到 `verifier_delegation_dispatched`."""
        req = _mk_req()
        fake = FakeDelegator()
        audit = AuditCollector()
        await dispatch_with_retry(req, fake, sleep=no_sleep, audit_emitter=audit.emit)
        types = [e[0] for e in audit.events]
        assert "L1-04:verifier_delegation_dispatched" in types


class TestDispatchWithRetryRetries:
    """TC-L104-L206-330 · 重试链路."""

    @pytest.mark.asyncio
    async def test_retry_on_api_error_then_success(self) -> None:
        """attempt 1 抛 500 · attempt 2 成功."""
        req = _mk_req()
        fake = FakeDelegator(
            behavior=[RuntimeError("500 server error"), None],  # 第 2 次用 default
        )
        result = await dispatch_with_retry(req, fake, sleep=no_sleep)
        assert result.dispatched is True
        assert len(fake.calls) == 2

    @pytest.mark.asyncio
    async def test_dispatched_false_counts_as_retry(self) -> None:
        """dispatched=False 也算失败 · 走重试."""
        req = _mk_req()
        fake = FakeDelegator(behavior=[
            IC20DispatchResult(delegation_id=req.delegation_id, dispatched=False),
            IC20DispatchResult(
                delegation_id=req.delegation_id,
                dispatched=True,
                verifier_session_id="sub-retried-001",
            ),
        ])
        result = await dispatch_with_retry(req, fake, sleep=no_sleep)
        assert result.dispatched is True
        assert len(fake.calls) == 2

    @pytest.mark.asyncio
    async def test_three_failures_raises_delegation_failure(self) -> None:
        """3 次全失败 → DelegationFailureError · retry_log 有 3 项."""
        req = _mk_req()
        fake = FakeDelegator(behavior=[
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
        ])
        with pytest.raises(DelegationFailureError) as exc:
            await dispatch_with_retry(req, fake, sleep=no_sleep)
        assert exc.value.max_retries == 3
        assert len(exc.value.retry_log) == 3

    @pytest.mark.asyncio
    async def test_audit_failed_events_emitted_per_attempt(self) -> None:
        """每次失败 · audit 有 `verifier_delegation_failed` 事件."""
        req = _mk_req()
        fake = FakeDelegator(behavior=[
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
        ])
        audit = AuditCollector()
        with pytest.raises(DelegationFailureError):
            await dispatch_with_retry(req, fake, sleep=no_sleep, audit_emitter=audit.emit)
        failed_events = [e for e in audit.events if e[0] == "L1-04:verifier_delegation_failed"]
        assert len(failed_events) == 3

    @pytest.mark.asyncio
    async def test_rate_limit_classified_correctly(self) -> None:
        """429 rate limit · 错误分类归 ic_20_api_rate_limit."""
        req = _mk_req()
        fake = FakeDelegator(behavior=[
            RuntimeError("429 rate limit exceeded"),
            RuntimeError("429 rate limit exceeded"),
            RuntimeError("429 rate limit exceeded"),
        ])
        with pytest.raises(DelegationFailureError) as exc:
            await dispatch_with_retry(req, fake, sleep=no_sleep)
        outcomes = [log["outcome"] for log in exc.value.retry_log]
        assert all(o == "ic_20_api_rate_limit" for o in outcomes)


class TestDispatchWithRetrySessionPrefix:
    """TC-L104-L206-340 · session_id 前缀硬红线 · 不重试."""

    @pytest.mark.asyncio
    async def test_main_dot_prefix_hard_red_line(self) -> None:
        """delegator 返回 main.xxx · 硬红线 · 直接传 SessionPrefixViolationError."""
        req = _mk_req()
        fake = FakeDelegator(session_id="main.bad-session")
        with pytest.raises(SessionPrefixViolationError):
            await dispatch_with_retry(req, fake, sleep=no_sleep)
        # 只调了 1 次 · 不重试
        assert len(fake.calls) == 1

    @pytest.mark.asyncio
    async def test_non_sub_prefix_hard_red_line(self) -> None:
        """非 sub- 前缀 · 直接 up."""
        req = _mk_req()
        fake = FakeDelegator(session_id="verifier-not-allowed")
        with pytest.raises(SessionPrefixViolationError):
            await dispatch_with_retry(req, fake, sleep=no_sleep)

    @pytest.mark.asyncio
    async def test_empty_session_id_hard_red_line(self) -> None:
        """L1-05 返回 dispatched=True + 空 session_id · 不合法."""
        req = _mk_req()
        fake = FakeDelegator(behavior=[
            IC20DispatchResult(
                delegation_id=req.delegation_id,
                dispatched=True,
                verifier_session_id=None,
            ),
        ])
        with pytest.raises(SessionPrefixViolationError):
            await dispatch_with_retry(req, fake, sleep=no_sleep)


class TestMaxRetriesHardLock:
    """TC-L104-L206-350 · max_retries 硬锁 ≤ 3."""

    @pytest.mark.asyncio
    async def test_max_retries_over_3_rejected(self) -> None:
        """max_retries=5 · raise ValueError."""
        req = _mk_req()
        fake = FakeDelegator()
        with pytest.raises(ValueError) as exc:
            await dispatch_with_retry(req, fake, max_retries=5, sleep=no_sleep)
        assert "hard-locked" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_max_retries_zero_rejected(self) -> None:
        """max_retries=0 · raise ValueError."""
        req = _mk_req()
        fake = FakeDelegator()
        with pytest.raises(ValueError):
            await dispatch_with_retry(req, fake, max_retries=0, sleep=no_sleep)

    @pytest.mark.asyncio
    async def test_max_retries_one_ok(self) -> None:
        """max_retries=1 合法 · 1 次失败就抛 DelegationFailureError."""
        req = _mk_req()
        fake = FakeDelegator(behavior=[RuntimeError("500 server error")])
        with pytest.raises(DelegationFailureError) as exc:
            await dispatch_with_retry(req, fake, max_retries=1, sleep=no_sleep)
        assert len(exc.value.retry_log) == 1


class TestBackoffBehavior:
    """TC-L104-L206-360 · backoff 2s / 4s (backoff_factor=2)."""

    @pytest.mark.asyncio
    async def test_backoff_grows_exponentially(self) -> None:
        """3 次重试间隔 2s · 4s (最后一次失败后不 sleep)."""
        req = _mk_req()
        fake = FakeDelegator(behavior=[
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
        ])
        recorded: list[float] = []

        async def recording_sleep(s: float) -> None:
            recorded.append(s)

        with pytest.raises(DelegationFailureError):
            await dispatch_with_retry(req, fake, sleep=recording_sleep)
        # attempt 1 失败后 sleep 2s · attempt 2 失败后 sleep 4s
        # attempt 3 失败后不 sleep · 直接抛
        assert recorded == [2.0, 4.0]
