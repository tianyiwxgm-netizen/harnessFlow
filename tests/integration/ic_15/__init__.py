"""IC-15 request_hard_halt 集成测试.

Dev-ζ L1-07/L2-03 · HaltRequester → L1-01 · 阻塞式 · ≤ 100ms 硬约束(HRL-05).

5 硬红线(HRL-01..05):
- HRL-01 PM-14 违规
- HRL-02 审计链破损
- HRL-03 可追溯率 < 100%
- HRL-04 UI panic 未 100ms 响应
- HRL-05 halt 请求未 100ms 响应

3 IC-17 用户授权场景:
- 默认 require_user_authorization=True (硬编码)
- IC-17 user_intervene authorize → resume / clear halt
"""
