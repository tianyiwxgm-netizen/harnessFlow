"""IC-01 · 幂等 / transition_id / PM-14 / 错误码 集成测试.

覆盖(补齐 WP02 spec 要求):
    幂等 · TC 4 (同 transition_id 重放 / 成功+失败都幂等 / 不同 pid 不冲突)
    transition_id · TC 2 (格式 + 非法格式拒)
    PM-14 · TC 3 (缺 pid / 非法格式 / 跨 project bound)
    错误码 · TC 4 (REASON_TOO_SHORT / NO_EVIDENCE / INVALID_STATE_ENUM / STATE_MISMATCH)

总 13 TC.
"""
from __future__ import annotations

import pytest

from app.main_loop.state_machine import StateMachineOrchestrator
from app.main_loop.state_machine.schemas import (
    E_TRANS_CROSS_PROJECT,
    E_TRANS_INVALID_STATE_ENUM,
    E_TRANS_NO_EVIDENCE,
    E_TRANS_NO_PROJECT_ID,
    E_TRANS_REASON_TOO_SHORT,
    E_TRANS_STATE_MISMATCH,
    E_TRANS_TRANSITION_ID_FORMAT,
    StateMachineError,
)


# ==============================================================================
# 幂等 · 4 TC
# ==============================================================================


class TestIdempotencyByTransitionId:
    """相同 transition_id 重放 · 返 cached 结果 · 不二次 apply."""

    def test_success_replay_returns_cached(
        self, orchestrator, make_request,
    ) -> None:
        """成功后相同 tid 重放 · version 不增 · state 不变."""
        req = make_request(from_state="NOT_EXIST", to_state="INITIALIZED")
        r1 = orchestrator.transition(req)
        r2 = orchestrator.transition(req)   # 同 req → 同 tid
        assert r1.accepted is True
        assert r2.accepted is True
        # 版本只 +1 一次
        assert orchestrator.snapshot.version == 1
        # state 保持
        assert orchestrator.get_current_state() == "INITIALIZED"

    def test_failure_replay_returns_cached_failure(
        self, build_at_state, make_request, project_id: str,
    ) -> None:
        """失败结果也缓存 · 重放同 tid 返同一 rejection · 不触发二次 side effect."""
        orch = build_at_state(project_id, "NOT_EXIST")
        # 非法边: NOT_EXIST → PLANNING
        req = make_request(from_state="NOT_EXIST", to_state="PLANNING")
        r1 = orch.transition(req)
        r2 = orch.transition(req)
        assert r1.accepted is False
        assert r2.accepted is False
        assert r1.error_code == r2.error_code
        assert r1.transition_id == r2.transition_id

    def test_different_tid_treated_separately(
        self, orchestrator, make_request, transition_id_factory,
    ) -> None:
        """两个不同 tid · 即使字段相同 · 各自执行 · version 累加."""
        req1 = make_request(
            transition_id=transition_id_factory(),
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
        )
        # 第一次: NOT→INITIALIZED 成功 · version=1
        r1 = orchestrator.transition(req1)
        assert r1.accepted is True
        assert orchestrator.snapshot.version == 1
        # 第二次同 tid 重放 · version 不变
        r1b = orchestrator.transition(req1)
        assert r1b.accepted is True
        assert orchestrator.snapshot.version == 1

    def test_idempotent_cache_scoped_by_pid(
        self, make_request, transition_id_factory,
    ) -> None:
        """同一 tid 在两个 orchestrator(不同 pid)下独立 · 不串."""
        pid_a = "pid-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        pid_b = "pid-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        orch_a = StateMachineOrchestrator(project_id=pid_a, initial_state="NOT_EXIST")
        orch_b = StateMachineOrchestrator(project_id=pid_b, initial_state="NOT_EXIST")

        tid = transition_id_factory()
        req_a = make_request(
            transition_id=tid, project_id_override=pid_a,
            from_state="NOT_EXIST", to_state="INITIALIZED",
        )
        req_b = make_request(
            transition_id=tid, project_id_override=pid_b,
            from_state="NOT_EXIST", to_state="INITIALIZED",
        )
        ra = orch_a.transition(req_a)
        rb = orch_b.transition(req_b)
        assert ra.accepted is True
        assert rb.accepted is True
        # 各 orchestrator version 都 = 1(独立)
        assert orch_a.snapshot.version == 1
        assert orch_b.snapshot.version == 1


# ==============================================================================
# transition_id · 2 TC
# ==============================================================================


class TestTransitionIdFormat:
    """transition_id 必须 `^trans-[0-9a-fA-F-]{8,}$`."""

    def test_invalid_tid_format_raises(
        self, orchestrator, make_request,
    ) -> None:
        """非 `trans-` 前缀 · E_TRANS_TRANSITION_ID_FORMAT."""
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(
                make_request(transition_id="badid-123"),
            )
        assert exc.value.error_code == E_TRANS_TRANSITION_ID_FORMAT

    def test_empty_tid_raises(
        self, orchestrator, project_id: str,
    ) -> None:
        """直构造 TransitionRequest(factory 会用默认填充 · 绕开之)."""
        from app.main_loop.state_machine import TransitionRequest

        req = TransitionRequest(
            transition_id="",   # 显式空
            project_id=project_id,
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            reason="IC-01 WP02 集成测试标准 reason ≥ 20 字",
            trigger_tick="tick-00000000-0000-0000-0000-000000000001",
            evidence_refs=("ev-wp02-1",),
            ts="2026-04-23T10:00:00.000000Z",
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_TRANSITION_ID_FORMAT


# ==============================================================================
# PM-14 · 3 TC
# ==============================================================================


class TestPm14:
    """PM-14 根字段守恒 · 缺 pid / 非法格式 / 跨 project 拒绝."""

    def test_empty_project_id_raises_no_project_id(
        self, orchestrator, make_request,
    ) -> None:
        """空 project_id · E_TRANS_NO_PROJECT_ID."""
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(
                make_request(project_id_override=""),
            )
        assert exc.value.error_code == E_TRANS_NO_PROJECT_ID

    def test_bad_format_project_id_raises(
        self, orchestrator, make_request,
    ) -> None:
        """不匹配 `^pid-[0-9a-fA-F-]{8,}$` · E_TRANS_NO_PROJECT_ID(格式)."""
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(
                make_request(project_id_override="not-a-pid"),
            )
        assert exc.value.error_code == E_TRANS_NO_PROJECT_ID

    def test_cross_project_raises(
        self, orchestrator, make_request,
    ) -> None:
        """req.pid ≠ orchestrator 绑定 pid · E_TRANS_CROSS_PROJECT."""
        # orchestrator bound 到 fixture pid · 传合法格式但不同 pid
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(
                make_request(
                    project_id_override="pid-ffffffff-ffff-ffff-ffff-ffffffffffff",
                ),
            )
        assert exc.value.error_code == E_TRANS_CROSS_PROJECT


# ==============================================================================
# 错误码 · 4 TC
# ==============================================================================


class TestErrorCodes:
    """4 种硬拒错误码 · reason 短/无 evidence/非法 enum/state mismatch."""

    def test_reason_too_short_raises(
        self, orchestrator, make_request,
    ) -> None:
        """reason < 20 字 · E_TRANS_REASON_TOO_SHORT."""
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(
                make_request(reason="too short"),
            )
        assert exc.value.error_code == E_TRANS_REASON_TOO_SHORT

    def test_no_evidence_raises(
        self, orchestrator, make_request,
    ) -> None:
        """evidence_refs 空 · E_TRANS_NO_EVIDENCE."""
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(
                make_request(evidence_refs=()),
            )
        assert exc.value.error_code == E_TRANS_NO_EVIDENCE

    def test_invalid_state_enum_raises(
        self, orchestrator, make_request,
    ) -> None:
        """不在 7 态 · E_TRANS_INVALID_STATE_ENUM."""
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(
                make_request(from_state="FOO", to_state="INITIALIZED"),  # type: ignore[arg-type]
            )
        assert exc.value.error_code == E_TRANS_INVALID_STATE_ENUM

    def test_state_mismatch_returns_reject_not_raise(
        self, build_at_state, make_request, project_id: str,
    ) -> None:
        """from_state 与 snapshot 不符 · accepted=False + E_TRANS_STATE_MISMATCH.

        (契约 §3.1.4: STATE_MISMATCH 不抛 · 走 reject 路径)
        """
        orch = build_at_state(project_id, "EXECUTING")
        # req.from=PLANNING 但实际 state 是 EXECUTING
        req = make_request(from_state="PLANNING", to_state="TDD_PLANNING")
        result = orch.transition(req)
        assert result.accepted is False
        assert result.error_code == E_TRANS_STATE_MISMATCH
