"""L2-03 · §3 幂等 · IdempotencyTracker + orchestrator 集成 (TC-36..40)。"""
from __future__ import annotations

import pytest

from app.main_loop.state_machine import (
    E_TRANS_IDEMPOTENT_REPLAY,
    IdempotencyTracker,
    StateMachineError,
)


class TestIdempotentCachedHit:
    def test_tc36_same_transition_id_returns_cached_result(
        self, orchestrator, make_request
    ):
        """TC-36 · 同 transition_id 第二次调用 → 返回缓存 result · 单次执行。"""
        tid = "trans-00000000-0000-0000-0000-00000000abcd"
        req1 = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            transition_id=tid,
        )
        r1 = orchestrator.transition(req1)
        assert r1.accepted is True
        assert orchestrator.snapshot.version == 1

        # 第二次调用同 transition_id
        req2 = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            transition_id=tid,
        )
        r2 = orchestrator.transition(req2)
        assert r2 is r1 or r2 == r1  # 缓存命中
        # 关键: version 不变 · 说明 snapshot 没被写第二次
        assert orchestrator.snapshot.version == 1
        assert orchestrator.get_current_state() == "INITIALIZED"

    def test_tc37_cached_rejected_result_also_replayed(
        self, orchestrator, make_request
    ):
        """TC-37 · 被拒的结果也会缓存 · 重放同样得拒绝 (不重试也不侧效)。"""
        tid = "trans-00000000-0000-0000-0000-0000000badbe"
        req1 = make_request(
            from_state="PLANNING",  # snapshot 实际是 NOT_EXIST → MISMATCH
            to_state="TDD_PLANNING",
            transition_id=tid,
        )
        r1 = orchestrator.transition(req1)
        assert r1.accepted is False
        assert r1.error_code == "E_TRANS_STATE_MISMATCH"

        # 第二次调用同 transition_id 直接拿 cached 拒绝
        req2 = make_request(
            from_state="PLANNING",
            to_state="TDD_PLANNING",
            transition_id=tid,
        )
        r2 = orchestrator.transition(req2)
        assert r2.accepted is False
        assert r2.error_code == "E_TRANS_STATE_MISMATCH"


class TestIdempotentConflict:
    def test_tc38_same_tid_different_payload_raises(
        self, orchestrator, make_request
    ):
        """TC-38 · 同 transition_id 但 payload 不同 → IDEMPOTENT_REPLAY。"""
        tid = "trans-00000000-0000-0000-0000-0000deadbeef"
        req1 = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            transition_id=tid,
            reason="first payload reason aligned with transition",
        )
        orchestrator.transition(req1)

        # 同 tid · 不同 reason → 幂等冲突
        req2 = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            transition_id=tid,
            reason="SECOND DIFFERENT payload reason for same tid test",
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req2)
        assert exc.value.error_code == E_TRANS_IDEMPOTENT_REPLAY


class TestTrackerUnit:
    def test_tc39_tracker_miss_returns_none(self, make_request, tracker):
        """TC-39 · tracker.lookup miss → None (非 raise)。"""
        req = make_request(transition_id="trans-00000000-0000-0000-0000-missing001")
        assert tracker.lookup(req) is None
        assert tracker.size() == 0

    def test_tc40_tracker_capacity_eviction(self, make_request):
        """TC-40 · LRU capacity=2 · put 3 条 → 最早被淘汰。"""
        t = IdempotencyTracker(capacity=2)
        req_a = make_request(transition_id="trans-00000000-0000-0000-0000-aaaaaaaaaaaa")
        req_b = make_request(transition_id="trans-00000000-0000-0000-0000-bbbbbbbbbbbb")
        req_c = make_request(transition_id="trans-00000000-0000-0000-0000-cccccccccccc")
        from app.main_loop.state_machine import TransitionResult

        def _mk(tid: str) -> TransitionResult:
            return TransitionResult(
                transition_id=tid,
                accepted=True,
                new_state="INITIALIZED",
                ts_applied="2026-04-23T00:00:00.000Z",
            )

        t.put(req_a, _mk(req_a.transition_id))
        t.put(req_b, _mk(req_b.transition_id))
        assert t.size() == 2
        t.put(req_c, _mk(req_c.transition_id))
        assert t.size() == 2
        # a 最早 · 已被淘汰
        assert t.lookup(req_a) is None
        # b / c 还在
        assert t.lookup(req_b) is not None
        assert t.lookup(req_c) is not None
