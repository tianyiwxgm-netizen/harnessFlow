"""L2-01 · 8-dim supervisor state collector.

三入口协议：
- tick_collect            · 30s 周期 · 8 维全扫 · SLO P99 ≤ 5s
- post_tool_use_fast_collect · PostToolUse hook · 500ms 硬锁 · 仅刷 tool_calls + latency_slo
- on_demand_collect       · UI / CLI 查询 · cache hit 20ms SLO

聚合根：EightDimensionCollector
Schema：SupervisorSnapshot · EightDimensionVector (pydantic v2 · frozen)

注意：public re-export 在 collector + schemas 实现后追加。
"""
