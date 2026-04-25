"""IC-17 panic 集成测试.

Dev-α L1-09 + L2-01 PanicHandler · IC-17 user_panic → PAUSED ≤ 100ms.

3 panic 触发条件(系统/用户):
- 事件总线写失败(BusFsyncFailed)
- hash chain 断(BusHashChainBroken)
- IC-09 落盘失败(BusWriteFailed/BusDiskFull)

5 IC-17 流程 TC:
- 100ms SLO 命中 panic_latency_ms <= 100
- L1-01 全停(state=PAUSED · enforce_can_dispatch 拒)
- L1-09 audit 闭环(panic_history 留痕)
- 恢复路径(resume → state=RUNNING)
- 已 HALTED 期间 panic 静默(HALTED 不被降级)
"""
