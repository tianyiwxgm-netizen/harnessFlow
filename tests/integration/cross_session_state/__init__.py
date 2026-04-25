"""tests/integration/cross_session_state · 重启后状态恢复 (~15 TC).

main-3 WP06 子目录 3 · 引 scope §11 跨 session.

覆盖:
    - C1 崩溃 → 重启 → 状态恢复(L1-09 检查点)· 5 TC
    - C2 决策记录可重放(audit-ledger 重放回 verdict 一致)· 3 TC
    - C3 未完成 WP 状态保留(WP IN_PROGRESS · 重启 · 仍 IN_PROGRESS)· 3 TC
    - C4 arc-history hash 链跨 session 校验 · 2 TC
    - C5 未授权硬红线 halt 跨 session 持续(halt 状态被持久化)· 2 TC
"""
