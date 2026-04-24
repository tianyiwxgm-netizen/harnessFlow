"""main-3 WP02 · IC-09 append_event 集成测试 (最热 IC · 脊柱).

IC-09 是 L1-09 EventBus 的唯一写入口 · 10 L1 全部产生方都要调.
本包验证:
    - 10 L1 生产方 × 各 1 TC(Dev-α/β/γ/δ/ε/ζ/η/θ/main-1/main-2 都写 IC-09 正确)
    - 正向/负向/PM-14 缺 pid/SLO/降级 各 1 TC
    - e2e 跨链 mini 1 TC

真实 import: app.l1_09.event_bus.EventBus / AuditQuery · 不 mock.
"""
