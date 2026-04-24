"""L1-04 · L2-05 · S4 Driver · main entry（§2.1 WPExecutionOrchestrator · §6.2 execute_wp）.

**职责**（brief · driver.py 主入口）：
  - `drive_s4(input, suite_test_ids) → ExecutionTrace`
  - 编排 SubagentDispatcher → TestRunner → MetricCollector
  - self-repair 硬锁 3 次（§2.1 D3）
  - no-self-verdict（本 WP 不裁决 · 只产 trace + metric 供 WP04 Gate / WP06 Verifier 消费）
  - WP05 scope 不做：git worktree / WAL / delegate_L206（留 WP06/07）

**核心流程**（§6.2 Step 1-6 的 WP05 精简）：
  1. 初始化 ExecutionTrace（state=PREPARING）
  2. 跑 attempt=0：invoke skill(red) → invoke skill(green) → test_runner.run
  3. 若全绿 → state=COMPLETED · collect metric · 返
  4. 若仍红 · attempt < budget → invoke skill(code_fix_attempt) → re-run → 递增 attempt
  5. attempt ≥ budget 仍红 → state=COMPLETED · error_code=SELF_REPAIR_EXHAUSTED
  6. 任何阶段 timeout / crash → state=HALTED · error_code 对应

**幂等**（§6.16）：
  同 (project_id, wp_id, suite_id) 已完成 · 二次调用返原 trace。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

from app.quality_loop.s4_driver.metric_collector import MetricCollector
from app.quality_loop.s4_driver.schemas import (
    INTERNAL_ASSERT,
    SELF_REPAIR_EXHAUSTED,
    SKILL_INVOKE_FAIL,
    SUITE_MISSING,
    TEST_RUN_CRASH,
    WP_NOT_FOUND,
    WP_TIMEOUT,
    DriverError,
    DriverState,
    ExecutionTrace,
    MetricData,
    SubagentInvokeResult,
    TestRunResult,
    WPExecutionInput,
)
from app.quality_loop.s4_driver.subagent_dispatcher import SubagentDispatcher
from app.quality_loop.s4_driver.test_runner import TestRunner


# ---------------------------------------------------------------------------
# Clock 协议（方便测试用 frozen clock · 主线用 system clock）
# ---------------------------------------------------------------------------


class Clock:
    """默认 system clock · 测试可注入 mock。"""

    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def monotonic_ms(self) -> int:
        return int(time.monotonic() * 1000)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


@dataclass
class DriverConfig:
    """§10 配置（WP05 裁）。"""

    self_repair_max_attempts: int = 3     # 硬锁（§2.1 D3）
    wp_execution_timeout_ms: int = 180_000
    coverage_pct_override: float | None = None  # mock 模式下 test driver 给定 cov


class S4Driver:
    """§2.1 WPExecutionOrchestrator · WP05 精简版。

    **为何不在构造函数写死 dispatcher/runner/collector**：
      - 方便单元测试注入 stub
      - 生产用 default · 单元测可覆盖

    **线程安全性**（WP05 scope）：
      单 driver 实例支持 per-WP 幂等表 · 不承诺跨 WP 并发无锁。
      跨 WP 并发由上层 (main-1 WP09 集成层) 管。
    """

    def __init__(
        self,
        *,
        dispatcher: SubagentDispatcher | None = None,
        runner: TestRunner | None = None,
        collector: MetricCollector | None = None,
        clock: Clock | None = None,
        config: DriverConfig | None = None,
    ) -> None:
        self._dispatcher = dispatcher or SubagentDispatcher()
        self._runner = runner or TestRunner()
        self._collector = collector or MetricCollector()
        self._clock = clock or Clock()
        self._config = config or DriverConfig()
        # §6.16 幂等 cache · key = (pid, wp_id, suite_id) → trace
        self._trace_cache: dict[tuple[str, str, str], ExecutionTrace] = {}

    # -- accessors（测试断言用） -- #

    @property
    def dispatcher(self) -> SubagentDispatcher:
        return self._dispatcher

    @property
    def runner(self) -> TestRunner:
        return self._runner

    @property
    def collector(self) -> MetricCollector:
        return self._collector

    @property
    def config(self) -> DriverConfig:
        return self._config

    # -- 主入口 -- #

    def drive_s4(
        self,
        input: WPExecutionInput,
        *,
        suite_test_ids: list[str],
        workspace_path: str = "",
    ) -> ExecutionTrace:
        """§6.2 execute_wp 入口 · WP05 精简。

        **前置校验**：
          - project_id / wp_id / suite_id 必填
          - suite_test_ids 可为空（走 013 路径）

        **返回**：始终返 ExecutionTrace（即使失败 · 错误进 error_code / error_message）
        """
        # 校验 input
        self._validate_input(input, suite_test_ids)

        # §6.16 幂等
        cache_key = (input.project_id, input.wp_id, input.suite_id)
        cached = self._trace_cache.get(cache_key)
        if cached is not None and cached.state == DriverState.COMPLETED:
            return cached

        # 初始化 trace
        trace = ExecutionTrace(
            trace_id="tr-" + uuid.uuid4().hex[:16],
            project_id=input.project_id,
            wp_id=input.wp_id,
            suite_id=input.suite_id,
            state=DriverState.PREPARING,
            started_at=self._clock.now_iso(),
        )
        workspace = workspace_path or f"projects/{input.project_id}/workspaces/{input.wp_id}"

        # 主循环（attempt 0..budget）
        t0 = self._clock.monotonic_ms()
        try:
            self._run_main_loop(
                input=input,
                trace=trace,
                workspace=workspace,
                suite_test_ids=suite_test_ids,
                started_ms=t0,
            )
        except DriverError as exc:
            # crash / timeout / internal 类错误 · 统一 halt
            trace.state = DriverState.HALTED
            trace.error_code = exc.code
            trace.error_message = str(exc)

        # 收尾 · collect metric（仅 COMPLETED 时）
        trace.ended_at = self._clock.now_iso()
        if trace.state == DriverState.COMPLETED:
            trace.metric = self._collector.collect(
                trace,
                coverage_pct_override=self._config.coverage_pct_override,
            )
        self._trace_cache[cache_key] = trace
        return trace

    # -- internals -- #

    def _validate_input(self, input: WPExecutionInput, suite_test_ids: list[str]) -> None:
        """§3.2 E_L205_L205_WP_NOT_FOUND / SUITE_MISSING 前置校验。"""
        if not input.wp_id:
            raise DriverError(WP_NOT_FOUND, message="wp_id required", input=repr(input))
        if not input.suite_id:
            raise DriverError(SUITE_MISSING, message="suite_id required")
        if not input.project_id:
            raise DriverError(
                INTERNAL_ASSERT, message="project_id required (PM-14)", input=repr(input)
            )
        # suite_test_ids 允许空（§901 · 空 WP 正向路径）
        if suite_test_ids is None:
            raise DriverError(INTERNAL_ASSERT, message="suite_test_ids must be list[str]")

    def _run_main_loop(
        self,
        *,
        input: WPExecutionInput,
        trace: ExecutionTrace,
        workspace: str,
        suite_test_ids: list[str],
        started_ms: int,
    ) -> None:
        """§6.3 run_red_green_loop · attempt 0..budget。

        **流程**：
          attempt 0 · red → green → run → 若绿 break · 若红且 attempt<budget · self-repair
          attempt 1-3 · code_fix_attempt → re-run → 若绿 break · 若红且 attempt<budget · 继续
          attempt == budget 仍红 → error_code=SELF_REPAIR_EXHAUSTED
        """
        budget = max(1, input.attempt_budget)
        trace.state = DriverState.RUNNING

        for attempt in range(budget + 1):
            # 超时检查（WP05 粗粒度 · 主循环入口 check 一次）
            elapsed = self._clock.monotonic_ms() - started_ms
            if elapsed > input.timeout_ms:
                raise DriverError(
                    WP_TIMEOUT,
                    message=f"wp {input.wp_id} exceeded {input.timeout_ms}ms",
                    elapsed_ms=elapsed,
                )

            # 决定本 attempt 的 intent 序列
            intents = self._resolve_intents(input, attempt)

            # 调 skill 序列
            any_fail = False
            for intent in intents:
                r = self._dispatcher.invoke(intent=intent)
                trace.subagent_calls.append(r)
                if r.status == "fail":
                    any_fail = True
                    # §11 降级 · skill fail 标为 partial · 继续 run 测试
                    # （如果 fail 到底 · test 跑出来就是 red · 走 self-repair）

            # 跑测试
            try:
                run_result = self._runner.run(
                    workspace_path=workspace,
                    test_ids=suite_test_ids,
                    attempt=attempt,
                    timeout_ms=input.timeout_ms,
                )
            except DriverError as exc:
                # test run crash · 视作本轮 error · 继续 self-repair（如 budget 允许）
                if exc.code == TEST_RUN_CRASH:
                    # 合成一个 error-only 的 TestRunResult · 保证 attempts 单调增
                    run_result = TestRunResult(
                        cases=tuple(),
                        red_count=0,
                        green_count=0,
                        error_count=max(1, len(suite_test_ids)),
                        total_duration_ms=0,
                        attempted_at=attempt,
                    )
                    trace.attempts.append(run_result)
                    # 若 budget 耗尽 · 直接 exhausted（不 raise · 让主循环走到 exhausted 分支）
                    if attempt >= budget:
                        trace.state = DriverState.COMPLETED
                        trace.error_code = SELF_REPAIR_EXHAUSTED
                        trace.error_message = f"test crash and exhausted after {budget} attempts"
                        return
                    # 继续下一 attempt
                    trace.state = DriverState.REPAIRING
                    continue
                raise  # 其他错误原样抛

            trace.attempts.append(run_result)

            # 全绿 → 成功 · break
            if run_result.is_all_green:
                trace.state = DriverState.COMPLETED
                return

            # 仍红 · 判定是否还能 self-repair
            if attempt >= budget:
                # self-repair 硬锁耗尽 (§2.1 D3)
                trace.state = DriverState.COMPLETED
                trace.error_code = SELF_REPAIR_EXHAUSTED
                trace.error_message = (
                    f"wp {input.wp_id} self-repair exhausted after {budget} attempts "
                    f"(final red={run_result.red_count}, error={run_result.error_count})"
                )
                return

            # 继续下一轮 · state → REPAIRING
            trace.state = DriverState.REPAIRING

        # 理论上不会到这（loop 内部必 return）
        raise DriverError(INTERNAL_ASSERT, message="main loop exited without state set")

    def _resolve_intents(self, input: WPExecutionInput, attempt: int) -> tuple[str, ...]:
        """§6.3 · 按 attempt 决定 skill intent 序列。

        - attempt 0   · 走 `skill_intent_plan`（默认 red_test_creation + green_test_implementation）
        - attempt ≥ 1 · 走 `code_fix_attempt`（self-repair）
        """
        if attempt == 0:
            return input.skill_intent_plan
        return ("code_fix_attempt",)


# ---------------------------------------------------------------------------
# Facade 函数（简化调用点）
# ---------------------------------------------------------------------------


def drive_s4(
    input: WPExecutionInput,
    *,
    suite_test_ids: list[str],
    workspace_path: str = "",
    driver: S4Driver | None = None,
) -> ExecutionTrace:
    """brief 要求的 facade `drive_s4(wp, suite) → ExecutionTrace`。

    - 不传 driver · 每次 new 默认实例（有 trace cache · 单调用无 side effect）
    - 传 driver · 复用（命中幂等 cache）
    """
    d = driver or S4Driver()
    return d.drive_s4(input, suite_test_ids=suite_test_ids, workspace_path=workspace_path)


__all__ = [
    "Clock",
    "DriverConfig",
    "S4Driver",
    "drive_s4",
]
