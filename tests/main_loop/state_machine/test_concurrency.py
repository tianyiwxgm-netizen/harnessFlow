"""L2-03 · §3 并发 · E_TRANS_CONCURRENT + audit_sink 容错 (TC-41..42)。"""
from __future__ import annotations

from app.main_loop.state_machine import (
    E_TRANS_CONCURRENT,
    StateMachineOrchestrator,
    TransitionResult,
)


class _ReentrantAuditSink:
    """在 audit 里再次调 transition() · 用来模拟并发 lock held 场景。

    严格说, 真实多线程并发由 ThreadPoolExecutor 跑;这里更便捷:
    audit_sink 运行时 lock 已被持有, 再次进入 transition() 的第二个调用
    会走 try_acquire → False → CONCURRENT 拒绝路径 (因为是同线程递归)。
    """


class TestConcurrency:
    def test_tc41_concurrent_during_audit_rejected(
        self, project_id, make_request, clock_iter
    ):
        """TC-41 · audit_sink 回调里再起 transition() · 第二个返回 CONCURRENT。"""
        captured: list[TransitionResult] = []

        def reentrant_audit(res: TransitionResult) -> str:
            # 在 lock held 期间尝试重入
            req2 = make_request(
                from_state="INITIALIZED", to_state="PLANNING"
            )
            nested = orch.transition(req2)
            captured.append(nested)
            return "audit-entry-1"

        orch = StateMachineOrchestrator(
            project_id=project_id,
            clock=clock_iter,
            audit_sink=reentrant_audit,
            initial_state="NOT_EXIST",
        )

        req1 = make_request(from_state="NOT_EXIST", to_state="INITIALIZED")
        r1 = orch.transition(req1)
        # 外层还是成功 (lock try 内部)
        assert r1.accepted is True
        # 重入那次应拒绝
        assert len(captured) == 1
        assert captured[0].accepted is False
        assert captured[0].error_code == E_TRANS_CONCURRENT

    def test_tc42_audit_sink_exception_not_rolled_back(
        self, project_id, make_request, clock_iter
    ):
        """TC-42 · audit_sink 抛异常 · 状态仍前进 · audit_entry_id=None。"""
        def bad_audit(res: TransitionResult) -> str:
            raise RuntimeError("audit sink down (intentional for test)")

        orch = StateMachineOrchestrator(
            project_id=project_id,
            clock=clock_iter,
            audit_sink=bad_audit,
            initial_state="NOT_EXIST",
        )
        req = make_request(from_state="NOT_EXIST", to_state="INITIALIZED")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.audit_entry_id is None  # 审计失败不回滚
        assert orch.get_current_state() == "INITIALIZED"
