"""main-3 WP07 · 性能 7 SLO 全量验证测试.

引 docs/3-2-IC/integration/ic-contracts.md §3 + scope §3.5 PM-05 · 7 项硬约束 · 每 SLO 5-6 TC.

7 SLO 列表:
1. tick_drift_p99 ≤ 5ms        (tick 调度抖动 · main-2 WP04)
2. halt_latency_p99 ≤ 100ms    (IC-15 硬红线触发)
3. panic_latency_p99 ≤ 100ms   (IC-17 panic 全停)
4. gate_latency_p95 ≤ 3s       (DoD AST 编译 + 评估)
5. ic_09_emit_p99 ≤ 50ms       (event-bus 写延迟)
6. ic_04_invoke_p99 ≤ 200ms    (skill 调用)
7. ic_14_verdict_p99 ≤ 50ms    (Gate verdict emit)

铁律:
- 真实 import L1 模块 (perf 测试必须真跑)
- 用 tests/shared/perf_helpers.py LatencyStats / assert_p99_under
- 标 @pytest.mark.perf · CI hint · 容忍 0% flake
"""
