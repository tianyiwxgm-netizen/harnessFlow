"""IC-13 push_suggestion 集成测试.

Dev-ζ L1-07 · SuggestionPusher → L1-01 · fire-and-forget · 不阻断主 loop.

8 类软漂移 (SDP-01..08):
- SDP-01 gate_overrun         · Gate 过度让步 ≥ 3 次 TOLERATED
- SDP-02 wp_loop              · WP 循环反复 fail_count ≥ 3
- SDP-03 skill_fallback       · Skill fallback 过度
- SDP-04 kb_miss              · KB 命中率骤降 < 30%
- SDP-05 audit_tail           · Audit 写入 P95 > 20ms
- SDP-06 ui_panic             · UI panic 频发 24h ≥ 3
- SDP-07 verifier_reject      · Verifier 连续拒绝 ≥ 3
- SDP-08 state_reverse        · 状态机逆转

软漂移走 IC-13 fire-and-forget · 严禁升格为 IC-15(BLOCK 级走 IC-15).
接收方 L1-01/L2-06 仅记录 · 不阻断主 loop.
"""
