"""main-3 WP02 · IC-01 state_transition 集成测试.

IC-01 是 L1-02 项目生命周期状态机的唯一写入口 · 7 态 / 12 边.
本包验证:
    - 状态机 7 态全转换
    - 12 合法边
    - 幂等 (transition_id)
    - PM-14 (project_id 格式 + 跨 project 拒)
    - 错误码 E_TRANS_*

真实 import: app.main_loop.state_machine.StateMachineOrchestrator / TransitionRequest.
"""
