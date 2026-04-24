"""TC-L104-L207 · retry_coordinator · 同级连续失败计数 + dedup。

核心 TC（对齐 Dev-ε `_escalated_wps` dedup + Dev-ζ escalator 5 态机）：
- 同级连续失败 ≥ 3 触发升级（is_escalated=True）
- 同 wp 已升级过 · 后续失败 · 静默吃掉（不重复 escalate）
- reset（on_wp_done_reset）· 解除升级去重标记 · 下轮可再升级
- per-wp 独立 · 不同 wp 互不影响
- per-project 隔离 · 跨 pid 不干扰（PM-14）
"""
from __future__ import annotations

import pytest

from app.quality_loop.rollback_router.retry_coordinator import RetryCoordinator


class TestRetryCoordinatorCounting:
    """同级连续失败计数。"""

    def test_first_fail_count_is_one(self) -> None:
        rc = RetryCoordinator(project_id="p1")
        n = rc.on_failed(wp_id="wp-1", verdict_level="FAIL_L1")
        assert n == 1

    def test_second_fail_count_is_two(self) -> None:
        rc = RetryCoordinator(project_id="p1")
        rc.on_failed(wp_id="wp-1", verdict_level="FAIL_L1")
        n = rc.on_failed(wp_id="wp-1", verdict_level="FAIL_L1")
        assert n == 2

    def test_third_fail_count_is_three_and_escalates(self) -> None:
        rc = RetryCoordinator(project_id="p1")
        for _ in range(2):
            rc.on_failed(wp_id="wp-1", verdict_level="FAIL_L1")
        n = rc.on_failed(wp_id="wp-1", verdict_level="FAIL_L1")
        assert n == 3
        assert rc.is_escalated(wp_id="wp-1", verdict_level="FAIL_L1") is True


class TestRetryCoordinatorDedupLikeDevEpsilon:
    """对齐 Dev-ε `_escalated_wps` dedup 模式 · 已升级后静默吃掉。"""

    def test_already_escalated_dedup_silently_absorbs(self) -> None:
        rc = RetryCoordinator(project_id="p1")
        for _ in range(3):
            rc.on_failed(wp_id="wp-1", verdict_level="FAIL_L1")
        assert rc.is_escalated(wp_id="wp-1", verdict_level="FAIL_L1") is True

        # 首次 should_notify_escalation 触发 dedup 标记（首次升级通知）
        assert rc.should_notify_escalation(wp_id="wp-1", verdict_level="FAIL_L1") is True

        # 再次失败 · dedup 静默 · 不重复升级 · 计数可继续走（≥ 3 持续升级态）
        rc.on_failed(wp_id="wp-1", verdict_level="FAIL_L1")
        assert rc.is_escalated(wp_id="wp-1", verdict_level="FAIL_L1") is True
        assert rc.was_escalation_notified(wp_id="wp-1", verdict_level="FAIL_L1") is True
        # dedup 保护：二次 should_notify 必 False
        assert rc.should_notify_escalation(wp_id="wp-1", verdict_level="FAIL_L1") is False

    def test_escalation_notify_fires_once_only(self) -> None:
        """should_notify_escalation 首次 True · 后续 False（dedup）。"""
        rc = RetryCoordinator(project_id="p1")
        # 走到 3 · 首次升级通知
        rc.on_failed("wp-1", "FAIL_L1")
        rc.on_failed("wp-1", "FAIL_L1")
        assert rc.should_notify_escalation("wp-1", "FAIL_L1") is False  # count=2 · 未到
        rc.on_failed("wp-1", "FAIL_L1")
        assert rc.should_notify_escalation("wp-1", "FAIL_L1") is True  # count=3 · 首次
        # dedup · 第二次 should_notify 返回 False（已通知过）
        rc.on_failed("wp-1", "FAIL_L1")
        assert rc.should_notify_escalation("wp-1", "FAIL_L1") is False


class TestRetryCoordinatorReset:
    """on_wp_done_reset · 成功后清零计数 + 解除升级 dedup。"""

    def test_reset_clears_count_and_escalation(self) -> None:
        rc = RetryCoordinator(project_id="p1")
        for _ in range(3):
            rc.on_failed("wp-1", "FAIL_L1")
        rc.on_wp_done_reset("wp-1", "FAIL_L1")
        assert rc.count_of("wp-1", "FAIL_L1") == 0
        assert rc.is_escalated("wp-1", "FAIL_L1") is False

    def test_after_reset_can_re_escalate(self) -> None:
        """重跑成功后再次 3 次失败 · 可重新升级（解除 dedup）。"""
        rc = RetryCoordinator(project_id="p1")
        for _ in range(3):
            rc.on_failed("wp-1", "FAIL_L1")
        rc.on_wp_done_reset("wp-1", "FAIL_L1")
        for _ in range(3):
            rc.on_failed("wp-1", "FAIL_L1")
        assert rc.should_notify_escalation("wp-1", "FAIL_L1") is True

    def test_reset_idempotent_no_raise_on_empty(self) -> None:
        rc = RetryCoordinator(project_id="p1")
        rc.on_wp_done_reset("wp-1", "FAIL_L1")  # no prior state · idempotent
        assert rc.count_of("wp-1", "FAIL_L1") == 0


class TestRetryCoordinatorPerWpIsolation:
    """per-wp 独立 · 不同 wp 互不影响。"""

    def test_different_wps_isolated(self) -> None:
        rc = RetryCoordinator(project_id="p1")
        rc.on_failed("wp-A", "FAIL_L1")
        rc.on_failed("wp-A", "FAIL_L1")
        rc.on_failed("wp-A", "FAIL_L1")
        rc.on_failed("wp-B", "FAIL_L1")
        assert rc.is_escalated("wp-A", "FAIL_L1") is True
        assert rc.is_escalated("wp-B", "FAIL_L1") is False

    def test_different_verdict_levels_isolated_per_wp(self) -> None:
        """同 wp 不同 verdict_level 分别计数。"""
        rc = RetryCoordinator(project_id="p1")
        for _ in range(3):
            rc.on_failed("wp-A", "FAIL_L1")
        # FAIL_L2 独立计数
        rc.on_failed("wp-A", "FAIL_L2")
        assert rc.is_escalated("wp-A", "FAIL_L1") is True
        assert rc.is_escalated("wp-A", "FAIL_L2") is False


class TestRetryCoordinatorPM14:
    """PM-14 · project_id 隔离。"""

    def test_wrong_project_id_rejected(self) -> None:
        """构造时带 pid · 之后的所有操作隐式绑该 pid · 跨 pid 调用独立实例。"""
        rc_a = RetryCoordinator(project_id="proj-A")
        rc_b = RetryCoordinator(project_id="proj-B")
        for _ in range(3):
            rc_a.on_failed("wp-1", "FAIL_L1")
        # rc_b 没有任何状态
        assert rc_b.count_of("wp-1", "FAIL_L1") == 0
        assert rc_b.is_escalated("wp-1", "FAIL_L1") is False

    def test_empty_project_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="project_id"):
            RetryCoordinator(project_id="")
