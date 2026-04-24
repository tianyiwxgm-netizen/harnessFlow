"""L1-01 主 Agent 决策循环 · main_loop 聚合包（main-2 主会话）。

6 个 L2 · 语义命名子包:
    - tick_scheduler · L2-01 · 心脏 100ms tick(WP04 · 待)
    - decision_engine · L2-02 · AST 决策(WP03 · 待)
    - state_machine · L2-03 · 状态机编排(WP02 · orchestrator + IC01Producer 初版)
    - task_chain · L2-04 · 任务链执行(WP05 · 待)
    - decision_audit · L2-05 · 决策审计(WP01 · 进行中)
    - supervisor_receiver · L2-06 · Supervisor 接收(WP06 · 进行中)

包路径 `app/main_loop/<semantic_name>/`(§5.6 语义命名 · 非 `app/l1_01/l2_XX/`).
"""
