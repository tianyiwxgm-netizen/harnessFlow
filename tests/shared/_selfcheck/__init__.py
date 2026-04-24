"""tests/shared/_selfcheck/ · shared/ fixture 自检(M3-WP01).

**目的**: 本 WP 不产生 integration TC · 但必须保证**共享 harness 自身可跑**.
每 fixture / assertion / harness 加一个 ≤ 5 行 smoke · 作"这东西至少能 import + 基本
形态正确" 的 CI 屏障.

下游 WP02~WP10 的真正集成 TC 另开目录.
"""
