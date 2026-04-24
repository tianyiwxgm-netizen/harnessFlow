"""main-1 WP09 · L1-04 Quality Loop 跨 L1 集成测试包.

覆盖 L1-04 Verifier/RollbackRouter 与其他 L1 (L1-02/03/05/06/07/09) 的真实契约集成:

- IC-01 state_transition  (L1-04 → L1-02 · Dev-δ)
- IC-06 kb_read           (L1-04 ← L1-06 · Dev-β)
- IC-09 audit emit        (L1-04 → L1-09 · Dev-α)
- IC-14 rollback_route    (L1-04 ← L1-07 · Dev-ζ)
- IC-18 audit_query       (L1-04 → L1-09 · Dev-α)
- IC-20 invoke_verifier   (L1-04 → L1-05 · Dev-γ)
- WP assign               (L1-04 ← L1-03 · Dev-ε)

全部依赖 已 merged 的 main 分支代码 · 直接真实 import · 无 mock 业务逻辑.
仅外部适配器（state_transition / delegator / callback_waiter）使用测试替身，
因这些接口的真实实现跨进程/子 agent · 在集成层只能靠契约对齐.
"""
