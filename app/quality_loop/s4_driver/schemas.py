"""L1-04 · L2-05 · S4 Driver · schema / 错误码。

对齐：
  - 3-1 §2 VO（WPExecutionSnapshot / WPRunState / CandidateReport）· WP05 裁出 `ExecutionTrace`
  - 3-1 §3.2 `execute_wp` 入/出参字段级 YAML
  - 3-1 §11 错误码（24 项 · WP05 scope 先取 10 核心 · 其余留 hook）

**PM-14 红线**：所有顶层 VO 首字段 `project_id`（除 `TestCaseOutcome` 这种子 VO 外）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# 错误（§11 · WP05 先取 10 核心 · 其余错误码留 hook）
# ---------------------------------------------------------------------------


class DriverError(Exception):
    """L2-05 S4 Driver 统一异常 · code + severity 二元暴露。"""

    def __init__(
        self,
        code: str,
        *,
        message: str | None = None,
        severity: str = "ERROR",
        **context: Any,
    ) -> None:
        super().__init__(message or code)
        self.code = code
        self.severity = severity
        self.context = context

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"DriverError(code={self.code!r}, severity={self.severity!r})"


# 10 核心错误码（前缀按 3-1 §11.1 原样保留）
WP_NOT_FOUND = "E_L205_L205_WP_NOT_FOUND"
SUITE_MISSING = "E_L205_L205_SUITE_MISSING"
SKILL_INVOKE_FAIL = "E_L205_L205_SKILL_INVOKE_FAIL"
SKILL_NOT_FOUND = "E_L205_L105_SKILL_NOT_FOUND"
SKILL_TIMEOUT = "E_L205_L105_SKILL_TIMEOUT"
SKILL_BUDGET_EXHAUSTED = "E_L205_L105_SKILL_BUDGET_EXHAUSTED"
TEST_RUN_CRASH = "E_L205_L205_TEST_RUN_CRASH"
SELF_REPAIR_EXHAUSTED = "E_L205_L205_SELF_REPAIR_EXHAUSTED"
WP_TIMEOUT = "E_L205_L205_WP_TIMEOUT"
INTERNAL_ASSERT = "E_L205_INTERNAL_ASSERT_FAILED"


# ---------------------------------------------------------------------------
# State machine（§8 · WP05 裁出 5 态 · 其余大态机留 L2-06 做）
# ---------------------------------------------------------------------------


class DriverState(str, Enum):
    """S4 Driver 运行态（§8 主状态的 WP05 子集）。"""

    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    REPAIRING = "REPAIRING"      # attempt ≥ 1 self-repair
    COMPLETED = "COMPLETED"      # 最终落 trace（green/exhausted 都走这）
    HALTED = "HALTED"            # 强 halt（timeout / supervisor 等）


class TestOutcomeStatus(str, Enum):
    """单 test case 状态（§6.3 + §10.5 红绿）。"""

    # pytest 别收这个以 Test 开头的枚举（我们是产线代码）
    __test__ = False

    GREEN = "green"
    RED = "red"
    ERROR = "error"   # 子进程崩溃等


# ---------------------------------------------------------------------------
# Value Objects（§2.2 + §2.4 · WP05 裁）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestCaseOutcome:
    """§2.2 · test_results 的单条（WP05 裁 frozen VO）。"""

    # pytest 别收以 Test 开头的产线 dataclass
    __test__ = False

    test_id: str
    status: TestOutcomeStatus
    duration_ms: int = 0
    failure_message: str = ""


@dataclass(frozen=True)
class TestRunResult:
    """§6.3 · _run_tests 返回值（WP05 裁）。

    pytest 别收：产线 dataclass。

    - `cases`         · 每个 test case 的结果
    - `red_count` / `green_count` / `error_count`
    - `total_duration_ms`
    - `attempted_at`  · 本次 attempt 编号（0 是首跑 · 1-3 是 self-repair）
    """

    # pytest 别收以 Test 开头的产线 dataclass
    __test__ = False

    cases: tuple[TestCaseOutcome, ...]
    red_count: int
    green_count: int
    error_count: int
    total_duration_ms: int
    attempted_at: int = 0

    @property
    def is_all_green(self) -> bool:
        """全绿谓词 · red=0 且 error=0（§6.3 判定条件）。"""
        return self.red_count == 0 and self.error_count == 0

    @property
    def total_count(self) -> int:
        return len(self.cases)


@dataclass(frozen=True)
class SubagentInvokeResult:
    """§6.9 · SkillInvoker.invoke 返回值（WP05 mock+真实 hook 都返这）。"""

    invoke_id: str
    skill_intent: str
    status: str  # success / partial / fail
    duration_ms: int = 0
    token_cost: int = 0
    output_summary: str = ""
    artifacts_written: tuple[str, ...] = field(default_factory=tuple)
    error_code: str | None = None
    error_message: str = ""


@dataclass(frozen=True)
class MetricData:
    """§2.4 predicate_outcomes 的 WP05 聚合 · 喂 WP04 Gate。

    **WP05 只抓 4 个核心 metric**（其余 metric 由 WP06 Verifier 补）:
      - coverage_pct    · 测试覆盖率（0.0-1.0）
      - latency_ms_p95  · 单 WP 执行 P95 latency
      - test_pass_ratio · green / total
      - memory_peak_mb  · 单 WP 峰值内存（mock 模式下返 0）

    `raw` 字段保留原 metric 对象 · 方便下游 Gate 按需抽字段。
    """

    coverage_pct: float
    latency_ms_p95: int
    test_pass_ratio: float
    memory_peak_mb: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    """§2.2 WPExecutionSnapshot 的 WP05 精简（mutable · 便于 attempt 追加）。

    **字段映射**：
      - `trace_id`      · 3-1 snapshot_id 的 WP05 等价
      - `project_id`    · PM-14 顶层
      - `wp_id`         · 本 trace 绑定的 WP
      - `suite_id`      · 关联 TestSuite
      - `state`         · DriverState
      - `attempts`      · 每轮 attempt 的 TestRunResult
      - `metric`        · 聚合 metric（WP04 Gate 消费）
      - `subagent_calls` · Skill 调用日志
      - `started_at` / `ended_at` · ISO 8601
      - `error`         · 失败时填 DriverError code
    """

    trace_id: str
    project_id: str
    wp_id: str
    suite_id: str
    state: DriverState = DriverState.PREPARING
    attempts: list[TestRunResult] = field(default_factory=list)
    metric: MetricData | None = None
    subagent_calls: list[SubagentInvokeResult] = field(default_factory=list)
    started_at: str = ""
    ended_at: str | None = None
    error_code: str | None = None
    error_message: str = ""

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def self_repair_count(self) -> int:
        """§2.3 total_self_repair_count · = attempts - 1（≤ 3 硬锁）。"""
        return max(0, self.attempt_count - 1)

    @property
    def is_success(self) -> bool:
        """最后一轮 attempt 全绿即成功（§6.2 Step 5）。"""
        return (
            self.state == DriverState.COMPLETED
            and self.error_code is None
            and bool(self.attempts)
            and self.attempts[-1].is_all_green
        )

    @property
    def is_exhausted(self) -> bool:
        """self-repair 3 次仍红（§6.3 _exhausted_result）。"""
        return (
            self.state == DriverState.COMPLETED
            and self.error_code == SELF_REPAIR_EXHAUSTED
        )


@dataclass(frozen=True)
class WPExecutionInput:
    """drive_s4 入参 · PM-14 顶层首字段。

    WP05 scope：
      - `project_id`   · PM-14 必填
      - `wp_id`        · 本次 execute 的 WP
      - `suite_id`     · 关联 TestSuite（L2-03 产）
      - `attempt_budget` · 最大 attempt 数 · 默认 3（含 self-repair · 硬锁 §2.1 D3）
      - `timeout_ms`   · 单 WP 执行上限 · 默认 180_000 ms（3 min）
      - `skill_intent_plan` · Skill 意图序列（mock 时用）· 默认：
            ('red_test_creation', 'green_test_implementation')
    """

    project_id: str
    wp_id: str
    suite_id: str
    attempt_budget: int = 3
    timeout_ms: int = 180_000
    skill_intent_plan: tuple[str, ...] = (
        "red_test_creation",
        "green_test_implementation",
    )


__all__ = [
    "DriverError",
    "DriverState",
    "ExecutionTrace",
    "MetricData",
    "SubagentInvokeResult",
    "TestCaseOutcome",
    "TestRunResult",
    "TestOutcomeStatus",
    "WPExecutionInput",
    "WP_NOT_FOUND",
    "SUITE_MISSING",
    "SKILL_INVOKE_FAIL",
    "SKILL_NOT_FOUND",
    "SKILL_TIMEOUT",
    "SKILL_BUDGET_EXHAUSTED",
    "TEST_RUN_CRASH",
    "SELF_REPAIR_EXHAUSTED",
    "WP_TIMEOUT",
    "INTERNAL_ASSERT",
]
