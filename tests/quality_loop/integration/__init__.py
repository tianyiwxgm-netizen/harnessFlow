"""main-1 WP08 · L1-04 Quality Loop · 跨 L2 e2e 集成测试.

覆盖 7 个 L2 模块真实 import 的端到端组合场景:
- test_dod_to_gate_e2e     · WP01 DoD → WP04 Gate 全链
- test_blueprint_to_s4_e2e · WP02 蓝图 → WP03 TestSuite → WP05 S4 全链
- test_s4_to_verifier_e2e  · WP05 S4 Trace → WP06 Verifier IC-20 全链
- test_verifier_to_rollback_e2e · WP06 FAIL_Lx → WP07 IC-14 回退全链
- test_full_s3_s4_s5_e2e   · S3 → S4 → S5 完整 Quality Loop 一圈

所有依赖均为真实 import(不 mock 跨 L2 边界)· 仅 mock L1 外部依赖
(L1-05 IC-20 delegator · L1-02 state_transition · L1-09 event bus)。
"""
