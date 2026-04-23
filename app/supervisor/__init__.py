"""Supervisor · L1-07 Harness 监督层。

6 L2 子包：
- dim_collector  · 8 维度采集（tick / PostToolUse / on-demand）
- deviation_judge · 4 级偏差判定（INFO / WARN / FAIL / CRITICAL）
- red_line       · 硬红线拦截（5 类）
- event_sender   · IC-13 / IC-14 对外出口（队列 + 背压 + halt 抢占）
- soft_drift     · 软漂移模式识别（8 类 trap）
- escalator      · 死循环升级器（同级连 >=3 failed 自动升级）

对外 IC public API：V1 MVP 仅 on-demand 查询入口（供 L1-10 UI 使用）。
V1 MVP 不 re-export · 各 L2 内部按需直接 import（避免循环）。
"""

__version__ = "0.1.0"
