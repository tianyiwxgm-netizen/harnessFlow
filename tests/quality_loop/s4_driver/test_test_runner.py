"""main-1 WP05 · L2-05 S4 Driver · TestRunner unit tests。

对齐 3-2 §2 正向 · §3 负向 · §9 边界：
  - TC-L104-L205-013 · skeleton 为空 · 直接绿
  - TC-L104-L205-014 · 1 次 fix 后绿
  - TC-L104-L205-108 · TEST_RUN_CRASH 子进程崩溃
  - TC-L104-L205-901 · 空 WP
  - TC-L104-L205-902 · 超大 WP（1000 测试）
"""
from __future__ import annotations

import pytest

from app.quality_loop.s4_driver.schemas import (
    TEST_RUN_CRASH,
    DriverError,
    TestCaseOutcome,
    TestOutcomeStatus,
    TestRunResult,
)
from app.quality_loop.s4_driver.test_runner import (
    StubTestExecutor,
    TestRunner,
)


class TestRunnerHappy:
    """§2 正向 · run + recount + 剧本回放。"""

    def test_TC_L104_L205_013_empty_test_ids_direct_green(self) -> None:
        """TC-L104-L205-013 · skeleton 为空 · default_all_green=True · 0 red 0 green。"""
        runner = TestRunner(executor=StubTestExecutor(default_all_green=True))
        r = runner.run(workspace_path="/tmp/ws", test_ids=[], attempt=0)
        assert r.red_count == 0
        assert r.green_count == 0
        assert r.is_all_green is True

    def test_TC_L104_L205_013b_empty_counts_to_total_zero(self) -> None:
        """TC-L104-L205-013b · total_count=0 边界。"""
        runner = TestRunner(executor=StubTestExecutor(default_all_green=True))
        r = runner.run(workspace_path="/tmp/ws", test_ids=[], attempt=0)
        assert r.total_count == 0

    def test_TC_L104_L205_014_run_plan_first_red_then_green(self) -> None:
        """TC-L104-L205-014 · 剧本：第 1 attempt 全红 · 第 2 attempt 全绿（1 次 fix 后绿）。"""
        cases_red = (TestCaseOutcome("t1", TestOutcomeStatus.RED, failure_message="fail"),)
        cases_green = (TestCaseOutcome("t1", TestOutcomeStatus.GREEN),)
        plan = [
            TestRunResult(cases=cases_red, red_count=1, green_count=0, error_count=0, total_duration_ms=50),
            TestRunResult(cases=cases_green, red_count=0, green_count=1, error_count=0, total_duration_ms=50),
        ]
        runner = TestRunner(executor=StubTestExecutor(plan=plan))
        r1 = runner.run(workspace_path="/tmp/ws", test_ids=["t1"], attempt=0)
        r2 = runner.run(workspace_path="/tmp/ws", test_ids=["t1"], attempt=1)
        assert r1.is_all_green is False
        assert r2.is_all_green is True
        assert r2.attempted_at == 1, "driver 指定 attempt=1 · VO 重建"

    def test_TC_L104_L205_014b_attempt_injected_into_result(self) -> None:
        """TC-L104-L205-014b · runner.run(attempt=N) · 返回 VO.attempted_at==N（即使 executor 返 0）。"""
        runner = TestRunner(executor=StubTestExecutor(default_all_green=True))
        r = runner.run(workspace_path="/tmp/ws", test_ids=["t1"], attempt=2)
        assert r.attempted_at == 2

    def test_default_executor_builds_green_cases(self) -> None:
        """default_all_green=True 下 stub 自动造 green cases。"""
        runner = TestRunner(executor=StubTestExecutor(default_all_green=True))
        r = runner.run(workspace_path="/tmp/ws", test_ids=["a", "b", "c"], attempt=0)
        assert r.green_count == 3
        assert r.red_count == 0
        assert all(c.status == TestOutcomeStatus.GREEN for c in r.cases)

    def test_default_executor_all_red_when_flag_false(self) -> None:
        """default_all_green=False 下 stub 造 red cases。"""
        runner = TestRunner(executor=StubTestExecutor(default_all_green=False))
        r = runner.run(workspace_path="/tmp/ws", test_ids=["a", "b"], attempt=0)
        assert r.red_count == 2
        assert r.green_count == 0

    def test_recount_sums_three_buckets(self) -> None:
        """recount 辅助方法：按 status 分桶。"""
        cases = (
            TestCaseOutcome("t1", TestOutcomeStatus.RED),
            TestCaseOutcome("t2", TestOutcomeStatus.GREEN),
            TestCaseOutcome("t3", TestOutcomeStatus.GREEN),
            TestCaseOutcome("t4", TestOutcomeStatus.ERROR),
        )
        runner = TestRunner()
        red, green, error = runner.recount(cases)
        assert (red, green, error) == (1, 2, 1)


class TestRunnerNegative:
    """§3 负向 · TEST_RUN_CRASH 子进程崩溃。"""

    def test_TC_L104_L205_108_crash_raises_driver_error(self) -> None:
        """TC-L104-L205-108 · TEST_RUN_CRASH · DriverError.code 匹配。"""
        runner = TestRunner(executor=StubTestExecutor(crash_on_call_n=1))
        with pytest.raises(DriverError) as exc:
            runner.run(workspace_path="/tmp/ws", test_ids=["t1"], attempt=0)
        assert exc.value.code == TEST_RUN_CRASH

    def test_TC_L104_L205_108b_crash_on_second_call_not_first(self) -> None:
        """TC-L104-L205-108b · crash_on_call_n=2 · 第 1 次 OK · 第 2 次 crash。"""
        runner = TestRunner(executor=StubTestExecutor(crash_on_call_n=2, default_all_green=True))
        # 1st call OK
        r1 = runner.run(workspace_path="/tmp/ws", test_ids=["t1"], attempt=0)
        assert r1.is_all_green is True
        # 2nd call crash
        with pytest.raises(DriverError) as exc:
            runner.run(workspace_path="/tmp/ws", test_ids=["t1"], attempt=1)
        assert exc.value.code == TEST_RUN_CRASH


class TestRunnerBoundary:
    """§9 边界 · 空 WP / 超大 WP。"""

    def test_TC_L104_L205_901_empty_wp_candidate_built(self) -> None:
        """TC-L104-L205-901 · 空 WP · red=0 green=0 · runner 能跑完不抛。"""
        runner = TestRunner(executor=StubTestExecutor(default_all_green=True))
        r = runner.run(workspace_path="/tmp/ws", test_ids=[], attempt=0)
        assert r.red_count == 0 and r.green_count == 0

    def test_TC_L104_L205_902_thousand_tests_still_green(self) -> None:
        """TC-L104-L205-902 · 1000 个 test case · 仍能跑完 · 内存 / 语义不 blow up。"""
        ids = [f"t{i}" for i in range(1000)]
        runner = TestRunner(executor=StubTestExecutor(default_all_green=True))
        r = runner.run(workspace_path="/tmp/ws", test_ids=ids, attempt=0)
        assert r.green_count == 1000
        assert r.total_count == 1000
