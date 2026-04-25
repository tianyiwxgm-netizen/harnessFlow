"""Acceptance scenarios · M3-WP08 100ms 硬约束端到端验证 + 后续 10 场景.

scenario_05_hard_redline · 5 类硬红线 5 步链 · ≤ 100ms BLOCK p99
scenario_06_panic         · 3 panic 模式 · ≤ 100ms PAUSED p99

铁律:
- Given-When-Then DSL · `from tests.shared.gwt_helpers import GWT`
- 100ms 硬约束 · 任一 TC P99 超 → 直接 fail
- 真实 import L1-09 EventBus + L1-07 HaltRequester + L2-01 HaltEnforcer/PanicHandler
- 5 步链:detect → emit IC-15 → consume → audit → UI(本 WP 略 UI · 落 audit 即可)
"""
