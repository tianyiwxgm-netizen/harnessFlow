"""main-3 WP02 · IC-04 invoke_skill 集成测试.

IC-04 是 L1-05 skill-dispatch 的 skill 调用统一入口.
本包验证:
    - 5 正向
    - 5 负向 (缺 pid / pid 跨 / skill 不存在 / 超时 / LLM fail)
    - 5 SLO (P99 0.78ms Dev-γ 实测)

真实 import: app.skill_dispatch.invoker.* · registry/intent 真实装配.
"""
