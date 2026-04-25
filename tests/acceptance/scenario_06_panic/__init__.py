"""Scenario 06 · panic 场景全闭环 · ≤ 100ms PAUSED p99 (HRL-04).

3 panic 触发模式 (IC-17 panic + scope §8.4 失败传播):
    M1. event-bus 写失败  (disk full / fsync ENOSPC)
    M2. hash chain 断     (prev_hash 不连续 · seq 缺失)
    M3. IC-09 落盘失败    (write_atomic 重试耗尽)

总 panic latency p99 ≤ 100ms (HRL-04 release blocker)。

20 TC 划分:
- T1-T3 · 3 模式各 1 端到端 5 步链 (3 TC)
- T4-T6 · 100ms SLO (baseline / 持续负载 / 冷启动) (3 TC)
- T7-T9 · 全停验证 (tick stop · 业务 fail · heartbeat ok) (3 TC)
- T10-T12 · 跨 session 持久 (重启 readonly · 直至运维清 panic) (3 TC)
- T13-T15 · 恢复路径 (运维清 panic + 重启 · audit 链重建 · resume) (3 TC)
- T16-T18 · panic 期间不接受新决策 (IC-01/02/03/14 拒收) (3 TC)
- T19-T20 · panic 期间用户告警 (UI 红屏 · IC-19 强通知) (2 TC)
"""
