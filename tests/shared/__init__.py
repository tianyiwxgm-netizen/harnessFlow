"""tests/shared/ · main-3 集成测试共享 harness(M3-WP01).

给所有后续 integration + acceptance 测试用的公共地基:
    - conftest.py        全局 fixtures (project_id / real_event_bus / tmp_root ...)
    - project_factory.py pid fixture · 构造干净 project(chart/wbs/tdd/quality/kb 初始化)
    - ic_assertions.py   公共断言 (assert_ic_09_emitted / assert_state_transition_to / ...)
    - e2e_harness.py     启动真 tick loop · step / tick_n 调用
    - stubs.py           跨 L1 mock 基础设施(LLM mock / tool mock 等)

参考:
    - docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-3-integration-and-acceptance.md §3 M3-WP01
    - docs/3-1-Solution-Technical/L1集成/architecture.md §4-§11
    - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.1~3.20

铁律:
    - PM-14 根字段 project_id 在所有 fixture 贯穿
    - 本包**禁改 app/ 代码** · 只供测试侧调用
    - fixture / harness / stub 小步 commit(每 1 个 1 commit · push 30s 内)
"""
from __future__ import annotations

__all__ = [
    # 共享 package 不做 re-export · 各测试按路径 import:
    # from tests.shared.ic_assertions import assert_ic_09_emitted
    # from tests.shared.project_factory import project_factory
    # from tests.shared.e2e_harness import E2EHarness
    # from tests.shared.stubs import FakeLLMClient
]
