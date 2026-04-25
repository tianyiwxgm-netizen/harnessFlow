"""IC-02 wp_status_change 集成测试.

Dev-ε L1-03/L2-04 · WBSTopologyManager.transition_state →
L1-03:wp_state_changed event 经 IC-09 落盘.

WP 6 状态合法跃迁(对齐 app.l1_03.topology.state_machine):
- READY → RUNNING       (IC-L2-03 锁定)
- RUNNING → DONE        (wp_done)
- RUNNING → FAILED      (wp_failed)
- FAILED → READY        (放回重试)
- FAILED → STUCK        (连续失败 ≥ 3 · L2-05/06)
- READY → BLOCKED       (依赖链含 FAILED/STUCK)
- BLOCKED → READY       (依赖恢复)
"""
