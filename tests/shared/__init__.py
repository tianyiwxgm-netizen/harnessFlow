"""tests/shared/ · main-3 集成测试共享 harness(M3-WP01 · 地基层).

**给所有 M3-WP02~WP10 的 24 份 integration + 12 份 acceptance 测试共用的地基**.
每一项 helper / fixture 都已在 `_selfcheck/` 有 smoke TC 验证(当前 69 TC 全绿).

## 目录索引(9 个模块)

| 文件 | 定位 | 主要 API |
|------|------|----------|
| `conftest.py` | 全局 fixtures | `project_id` · `tmp_root` · `real_event_bus` · `no_sleep` · 及所有下游 fixture re-export |
| `project_factory.py` | 干净 project 构造器 | `project_factory(pid)` → `ProjectWorkspace` · `project_workspace`(默认 pid) |
| `ic_assertions.py` | 20 IC 契约公共断言 | `assert_ic_09_emitted` · `assert_ic_09_hash_chain_intact` · `assert_kb_read_returned` · `assert_ic_04_invoked` · `assert_ic_13_sense_emitted` · `assert_ic_14_pushed` · `assert_ic_15_halt_emitted` · `assert_panic_within_100ms` · `assert_ic_19_wbs_accepted` · `assert_ic_20_dispatched` · `assert_state_transition_to` · PM-14 隔离 `assert_no_events_for_pid` / `assert_events_only_for_pid` |
| `e2e_harness.py` | 真 tick loop 驱动器 | `E2EHarness` · `step/tick_n/panic/resume` · `e2e_harness` fixture · `e2e_harness_factory` · `run_with_timeout` |
| `stubs.py` | 跨 L1 mock 基础设施 | `StateTransitionSpy` · `DelegateVerifierStub` · `CallbackWaiterStub` · `FakeKBRepo/ScopeChecker/Reranker` · `FakeLLMClient` · `FakeSkillInvoker` · `FakeToolClient` · `AuditSink` · 10 fixture 全 conftest re-export |
| `gwt_helpers.py` | Given-When-Then DSL | `GWT` class · `gwt` fixture · 失败自动打印 step chain |
| `perf_helpers.py` | 延时采样 / SLO 断言 | `measure_async` · `collect_n` · `LatencyStats.compute` · `assert_p99_under` · `assert_p95_under` |
| `matrix_helpers.py` | 10×10 矩阵覆盖 | `L1_IDS` · `pairs()/undirected_pairs()` · `matrix_params()` · `MatrixCoverage` · `CaseType` 4 档 |
| `_selfcheck/` | harness 自检 TC | 9 个 test_* · 69 TC 全绿 · 本 WP 不产出业务 TC · 只保障自身可用 |

## 用法(下游 WP02~WP10)

```python
# integration TC
import pytest
from tests.shared.ic_assertions import assert_ic_09_emitted
from tests.shared.stubs import StateTransitionSpy

@pytest.mark.asyncio
async def test_ic_09_from_l1_04(real_event_bus, project_id, state_spy):
    # real_event_bus + state_spy 已通过 conftest 自动注入
    ...
    assert_ic_09_emitted(real_event_bus.root, project_id=project_id,
                         event_type='L1-04:verifier_report_issued')

# acceptance scenario
async def test_scenario_05_panic_100ms(gwt, e2e_harness):
    async with gwt('硬红线 · 用户 panic 100ms PAUSED'):
        gwt.given('scheduler RUNNING').when('user panics').then('≤100ms PAUSED')
        import time
        t0 = time.monotonic()
        e2e_harness.panic(reason='hard redline')
        assert_panic_within_100ms(t0, time.monotonic(), budget_ms=100.0)
```

## 铁律

- **PM-14**: `project_id` 根字段在所有 fixture / assertion 贯穿 · 跨 pid 必显式传
- **禁改 app/**: 本包是测试层 · 只 import + 组装 · 不修业务代码
- **真实性**: L1-09 EventBus 用真实落盘(`real_event_bus`) · L1-02 state_transition
  跨进程所以用 spy · L1-05 sub-agent 烧钱所以用 stub · 其余全部真 import

## 参考锚点

- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-3-integration-and-acceptance.md §3 M3-WP01`
- `docs/3-1-Solution-Technical/L1集成/architecture.md §4-§11`
- `docs/3-1-Solution-Technical/integration/ic-contracts.md §3.1~3.20`
- `docs/2-prd/L1集成/prd.md §3-§11`
"""
from __future__ import annotations

__all__: list[str] = [
    # 共享 package 不做 re-export · 各测试按路径 import. 示例:
    #     from tests.shared.ic_assertions import assert_ic_09_emitted
    #     from tests.shared.project_factory import ProjectWorkspace
    #     from tests.shared.e2e_harness import E2EHarness, run_with_timeout
    #     from tests.shared.stubs import StateTransitionSpy, DelegateVerifierStub
    #     from tests.shared.gwt_helpers import GWT
    #     from tests.shared.perf_helpers import measure_async, assert_p99_under
    #     from tests.shared.matrix_helpers import L1_IDS, pairs, matrix_params, CaseType
    # 或直接用 conftest fixture:
    #     def test_xx(project_id, project_workspace, real_event_bus, e2e_harness,
    #                 state_spy, delegate_stub, fake_llm, gwt): ...
]
