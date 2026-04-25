"""Scenario 05 · 硬红线场景全闭环 · ≤ 100ms BLOCK p99 (HRL-04/05).

5 步链路 (3-1 hard-redlines.md §3.5):
    1. detect    L1-07 RedLineDetector 命中 (5 类 R-1~R-5)
    2. emit      IC-15 request_hard_halt
    3. consume   L1-01 IC15Consumer 接收 + halt
    4. audit     L1-09 IC-09 hard_halted 落盘
    5. UI        IC-19 红屏卡片 push (本 WP 仅断言 audit 含 authorize 字段 + halt_id)

总 BLOCK p99 ≤ 100ms (HRL-04/05 release blocker)。

20 TC 划分:
- T1-T5  · 5 类红线各 1 端到端 5 步链 (5 TC)
- T6-T8  · 100ms SLO (baseline / 持续负载 / 冷启动) (3 TC)
- T9-T11 · 用户授权放行 (AUTHORIZE 有效 / 失效 / 过期) (3 TC)
- T12-T14 · halt 持续性 (用户离线 / UI 不可达 / 跨 tick 仍 halt) (3 TC)
- T15-T16 · 误杀保护 (pattern 误命中 + 用户授权恢复) (2 TC)
- T17-T18 · 审计完整性 (hash chain · cross-session 持久) (2 TC)
- T19-T20 · 降级 (pattern_db 默认 BLOCK · IC-15 emit 失败 panic) (2 TC)
"""
