"""main-2 WP07 · L1-01 主循环 6 L2 集成 + 跨 L1 e2e 测试包。

覆盖范围:
- 内部 6 L2 e2e (tick_scheduler / decision_engine / state_machine / task_chain /
  decision_audit / supervisor_receiver 全链路)
- 跨 L1 e2e (L1-01 ↔ L1-02/03/04/05/07/09)

铁律:
- 只改 tests/main_loop/integration/ · 不改 app/ 代码
- 真实 import · 不 mock (除 L1-05 skill 外部 API)
- 15-20 TC · 禁 git add -A
"""
