"""L1-02 项目生命周期编排 (BC-02).

7 L2：
- template_engine (L2-07) · 无状态 Domain Service · 地基
- kickoff        (L2-02) · PM-14 pid 创建唯一入口
- four_set       (L2-03) · 4 件套生产器
- stage_gate     (L2-01) · IC-01 入口 · 7 状态 × 12 转换 · 硬禁自动放行
- pmp            (L2-04) · PMP 9 计划生产器（并发）
- togaf          (L2-05) · TOGAF ADM 9 Phase + togaf_d_ready
- closing        (L2-06) · PM-14 归档唯一入口（tar.zst）

PM-14 硬约束：L2-02 创建 → L2-01 驱动 → L2-06 归档 · 三段闭环 · 其他 L2 禁创建/归档。
"""
