"""L1-04 · L2-05 · S4 Driver · MetricCollector（§6.5 + §6.7）.

**职责**：
  从 ExecutionTrace 的 attempts / subagent_calls 聚合出 MetricData ·
  喂给 WP04 `GateVerdict` 评估（5 基线）。

**4 个核心 metric**（WP04 Gate 白名单输入）：
  - `coverage_pct`     · 测试覆盖率（默认从 raw.coverage 读 · 缺省 0.0）
  - `latency_ms_p95`   · 聚合 latency P95
  - `test_pass_ratio`  · green / (green+red+error) · 全空 → 1.0
  - `memory_peak_mb`   · mock 模式返 0 · 真实 hook psutil

**为何 P95 而不是 avg**：
  - 3-1 §12.1 SLO 明确用 P95 （长尾感知）
  - avg 对离群点不敏感 · 测试 flaky 时会骗人

**raw 字段**：
  保留原始 sample（coverage report / resource usage 等）· 下游 Gate 可按需抽字段。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.quality_loop.s4_driver.schemas import (
    ExecutionTrace,
    MetricData,
    SubagentInvokeResult,
    TestRunResult,
)


# ---------------------------------------------------------------------------
# 纯函数 helpers（无状态 · 方便 unit test）
# ---------------------------------------------------------------------------


def compute_test_pass_ratio(run: TestRunResult) -> float:
    """§6.7 · green / (green+red+error) · 分母 0 → 返 1.0（无测试等同无失败）。"""
    denom = run.green_count + run.red_count + run.error_count
    if denom == 0:
        return 1.0
    return round(run.green_count / denom, 4)


def compute_latency_p95(values_ms: list[int]) -> int:
    """§12.1 · 计算 P95 latency · 空列表 → 0。

    使用 "nearest rank" 法（NIST / ISO 13528）：
        rank = ceil(0.95 * n) · 1-indexed
    """
    if not values_ms:
        return 0
    sorted_vals = sorted(values_ms)
    n = len(sorted_vals)
    # nearest rank: ceil(0.95 * n) · 1-indexed · 转 0-indexed
    rank = max(1, math.ceil(0.95 * n))
    idx = min(rank - 1, n - 1)
    return int(sorted_vals[idx])


def aggregate_durations(attempts: list[TestRunResult]) -> list[int]:
    """把 attempts 里每个 case 的 duration_ms 拍平 · 返 list。"""
    out: list[int] = []
    for a in attempts:
        for c in a.cases:
            out.append(int(c.duration_ms))
    return out


def aggregate_skill_durations(calls: list[SubagentInvokeResult]) -> list[int]:
    """skill call 的 duration_ms 列表。"""
    return [int(c.duration_ms) for c in calls if c.duration_ms > 0]


# ---------------------------------------------------------------------------
# MetricCollector
# ---------------------------------------------------------------------------


@dataclass
class MetricCollectorConfig:
    """§10 配置参数 · WP05 裁。"""

    include_skill_latency: bool = True   # 混入 skill 调用的 latency 做 P95
    default_coverage_pct: float = 0.0    # 真实 cov 未接入时的兜底
    mock_memory_peak_mb: int = 0         # 真实 psutil hook 未接时的兜底


class MetricCollector:
    """§6.7 · 从 ExecutionTrace 聚合 MetricData · 喂 WP04 Gate。

    **无状态 · 可 share instance**（配置 immutable）。

    **纯函数 pipeline**：
      collect(trace) →
        - pass_ratio = last_attempt green / total
        - latency = P95(case durations + optional skill durations)
        - coverage = trace.raw.coverage_pct 或 default
        - memory = mock 返 0 / real 返 psutil 峰值
      → MetricData(+ raw dict 保留原始样本)
    """

    def __init__(self, config: MetricCollectorConfig | None = None) -> None:
        self._config = config or MetricCollectorConfig()

    @property
    def config(self) -> MetricCollectorConfig:
        return self._config

    def collect(
        self,
        trace: ExecutionTrace,
        *,
        coverage_pct_override: float | None = None,
        raw_extra: dict[str, Any] | None = None,
    ) -> MetricData:
        """§6.7 主函数 · 从 trace 聚合 MetricData。

        **输入**：
          - trace              · 已跑完（或 halted）的 ExecutionTrace
          - coverage_pct_override · 真实 coverage 可由 driver 传入（WP05 mock 默认兜底）
          - raw_extra          · 额外 raw 字段（tag / hash / span_id 等）

        **输出**：
          MetricData · 4 core + raw dict
        """
        # 1) test_pass_ratio · 取最后 attempt（若有）
        if trace.attempts:
            pass_ratio = compute_test_pass_ratio(trace.attempts[-1])
        else:
            pass_ratio = 1.0

        # 2) latency P95 · case durations + (可选) skill durations
        case_durs = aggregate_durations(trace.attempts)
        if self._config.include_skill_latency:
            case_durs += aggregate_skill_durations(trace.subagent_calls)
        p95 = compute_latency_p95(case_durs)

        # 3) coverage
        if coverage_pct_override is not None:
            cov = float(coverage_pct_override)
        else:
            cov = self._config.default_coverage_pct

        # 4) memory（mock 模式兜底）
        mem = self._config.mock_memory_peak_mb

        # 5) raw 聚合（下游 gate 可抽 field）
        raw: dict[str, Any] = {
            "attempt_count": trace.attempt_count,
            "self_repair_count": trace.self_repair_count,
            "skill_call_count": len(trace.subagent_calls),
            "durations_ms": case_durs,
        }
        if raw_extra:
            raw.update(raw_extra)

        return MetricData(
            coverage_pct=round(cov, 4),
            latency_ms_p95=p95,
            test_pass_ratio=pass_ratio,
            memory_peak_mb=mem,
            raw=raw,
        )


__all__ = [
    "MetricCollector",
    "MetricCollectorConfig",
    "compute_test_pass_ratio",
    "compute_latency_p95",
    "aggregate_durations",
    "aggregate_skill_durations",
]
