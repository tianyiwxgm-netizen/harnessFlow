"""L1-04 · L2-05 · S4 Driver · TestRunner（§6.3 _run_tests + §6.12 子进程）。

**职责**：
  - 驱 pytest 跑测试（WP05 mock 模式：直接按 stub 返结果）
  - 真实模式（留 hook）：subprocess 调 pytest · parse junit.xml
  - 收集 TestCaseOutcome 列表 → TestRunResult

**WP05 裁**：
  - 默认 `StubTestExecutor`（不真跑 pytest · 按 plan 返）· 单元测试用
  - 真实 `SubprocessTestExecutor` 留 hook · main-2 补
  - `TEST_RUN_CRASH` 错误码（子进程崩溃 · WP05 模拟）

**为何分离 Executor**：
  - 单元测试可控（按剧本返）
  - 真跑 pytest 留给 e2e 层
  - 符合 D2 决策（隔离是 WP05 的职责）
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from app.quality_loop.s4_driver.schemas import (
    TEST_RUN_CRASH,
    DriverError,
    TestCaseOutcome,
    TestOutcomeStatus,
    TestRunResult,
)


# ---------------------------------------------------------------------------
# 协议（真实 main-2 接 pytest 需要实现这个）
# ---------------------------------------------------------------------------


class TestExecutor(Protocol):
    """pytest 执行器协议 · 真实/stub 都实现这个。"""

    # pytest 别收以 Test 开头的 Protocol
    __test__ = False

    def run(
        self,
        *,
        workspace_path: str,
        test_ids: list[str],
        timeout_ms: int,
    ) -> TestRunResult: ...


# ---------------------------------------------------------------------------
# Stub 实现（WP05 默认）
# ---------------------------------------------------------------------------


@dataclass
class StubTestExecutor:
    """按剧本返的 executor · WP05 默认。

    **剧本配置**：
      - `plan: list[TestRunResult]` · 按序弹 · 耗尽用 default
      - `default_all_green: bool` · 无 plan 时 test_ids 全绿
      - `crash_on_call_n: int | None` · 第 n 次 call 触发 TEST_RUN_CRASH

    **不真跑 pytest** · 完全由 plan 决定。
    """

    plan: list[TestRunResult] = field(default_factory=list)
    default_all_green: bool = True
    default_duration_ms_per_case: int = 10
    crash_on_call_n: int | None = None
    _count: int = 0

    def run(
        self,
        *,
        workspace_path: str,
        test_ids: list[str],
        timeout_ms: int = 60_000,
    ) -> TestRunResult:
        """按剧本 / default 返 TestRunResult。"""
        self._count += 1
        n = self._count

        if self.crash_on_call_n is not None and n >= self.crash_on_call_n:
            raise DriverError(
                TEST_RUN_CRASH,
                message=f"stub injected crash on call #{n}",
                workspace_path=workspace_path,
                call_n=n,
            )

        if self.plan:
            return self.plan.pop(0)

        # default 全绿 / 全红
        status = (
            TestOutcomeStatus.GREEN if self.default_all_green else TestOutcomeStatus.RED
        )
        cases = tuple(
            TestCaseOutcome(
                test_id=tid,
                status=status,
                duration_ms=self.default_duration_ms_per_case,
                failure_message="" if self.default_all_green else "stub red",
            )
            for tid in test_ids
        )
        total_dur = self.default_duration_ms_per_case * max(1, len(test_ids))
        return TestRunResult(
            cases=cases,
            red_count=0 if self.default_all_green else len(test_ids),
            green_count=len(test_ids) if self.default_all_green else 0,
            error_count=0,
            total_duration_ms=total_dur,
            attempted_at=0,
        )


# ---------------------------------------------------------------------------
# TestRunner（§6.3 · WP05 编排 · 不调 pytest CLI · 委托 executor）
# ---------------------------------------------------------------------------


class TestRunner:
    """§6.3 _run_tests 的 WP05 封装。

    pytest 别收（产线 class · 不是测试）。

    职责薄：
      - 取 executor.run · 记录 attempted_at（= driver 传入的 attempt 编号）
      - 聚合 red/green/error count（若 executor 已算 · 透传；否则重算）

    用法：
      runner = TestRunner(executor=StubTestExecutor(...))
      result = runner.run(workspace_path=..., test_ids=..., attempt=0)
    """

    # pytest 别收这个以 Test 开头的类（我们是产线代码）
    __test__ = False

    def __init__(self, executor: TestExecutor | None = None) -> None:
        self._executor = executor or StubTestExecutor()

    @property
    def executor(self) -> TestExecutor:
        return self._executor

    def run(
        self,
        *,
        workspace_path: str,
        test_ids: list[str],
        attempt: int = 0,
        timeout_ms: int = 60_000,
    ) -> TestRunResult:
        """§6.3 调 executor · 返 TestRunResult（attempted_at 由 driver 注入）。

        **行为**：
          - executor 返了就透传
          - 若 executor 返的 attempted_at == 0 而 driver 要 1-3 · 重建 VO
        """
        result = self._executor.run(
            workspace_path=workspace_path,
            test_ids=test_ids,
            timeout_ms=timeout_ms,
        )
        if result.attempted_at != attempt:
            result = TestRunResult(
                cases=result.cases,
                red_count=result.red_count,
                green_count=result.green_count,
                error_count=result.error_count,
                total_duration_ms=result.total_duration_ms,
                attempted_at=attempt,
            )
        return result

    def recount(self, cases: tuple[TestCaseOutcome, ...]) -> tuple[int, int, int]:
        """§6.3 · 从 cases 元组重算 (red, green, error) · 供 driver 聚合用。"""
        red = sum(1 for c in cases if c.status == TestOutcomeStatus.RED)
        green = sum(1 for c in cases if c.status == TestOutcomeStatus.GREEN)
        error = sum(1 for c in cases if c.status == TestOutcomeStatus.ERROR)
        return red, green, error


__all__ = [
    "TestExecutor",
    "StubTestExecutor",
    "TestRunner",
]
