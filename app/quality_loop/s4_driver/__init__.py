"""L1-04 · L2-05 · S4 执行驱动器（WP05 scope）。

**职责**（brief · driver.py 主入口）：
  S4 期驱动 subagent 跑测试 · 收集 metric · 输出 ExecutionTrace + MetricData 喂给 WP04 Gate。

**WP05 裁**：
  - 本包聚焦 `drive_s4(wp, suite) → ExecutionTrace`
  - L1-05 `invoke_skill` 用 mock stub（真实在 main-2 会接）· 不阻塞本 WP
  - 三段式：test_runner（驱 pytest 跑）+ metric_collector（抓 cov/latency）
    + subagent_dispatcher（调 skill）+ driver（主入口编排）

**对齐**：
  - 源 3-1 `L2-05 S4 执行驱动器.md` §3（10 IC）+ §6（主算法）+ §11（24 错误码）
  - 3-2 tests `L2-05-...-tests.md`（~60 TC）
  - WP05 scope 暂不做 git worktree / WAL / crash_recovery / delegate_L206（留 WP06/07）

**子模块**：
  - `schemas.py`              · ExecutionTrace / MetricData / DriverState / 错误
  - `test_runner.py`          · 驱 pytest 跑 · 收集结果
  - `metric_collector.py`     · 抓 coverage / latency / 收集 metric
  - `subagent_dispatcher.py`  · L1-05 invoke_skill（mock + 真实 hook）
  - `driver.py`               · 主入口 · drive_s4(wp, suite) → ExecutionTrace
"""

from __future__ import annotations

from app.quality_loop.s4_driver.schemas import (
    DriverError,
    DriverState,
    ExecutionTrace,
    MetricData,
    SubagentInvokeResult,
    TestCaseOutcome,
    TestRunResult,
    WPExecutionInput,
)

__all__ = [
    "DriverError",
    "DriverState",
    "ExecutionTrace",
    "MetricData",
    "SubagentInvokeResult",
    "TestCaseOutcome",
    "TestRunResult",
    "WPExecutionInput",
]
