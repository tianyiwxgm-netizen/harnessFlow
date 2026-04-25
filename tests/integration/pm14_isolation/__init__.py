"""tests/integration/pm14_isolation · PM-14 project_id 跨分片隔离边界 (~25 TC).

main-3 WP06 子目录 1.

覆盖:
    - A1 路径隔离: 写 A 的 audit-ledger · B 查不到(IC-09 + IC-18)
    - A2 锁互斥不跨 pid: A 的锁不阻 B 同名资源(IC-10/11)
    - A3 状态机不跨 pid: A 的 state_transition 不影响 B(IC-01)
    - A4 WP 隔离: A 的 WP 不被 B 调度(IC-02)
    - A5 KB 不跨 pid: A 写 · B 查不到(IC-07/08)
    - A6 空 pid / 错格式 / 系统保留 pid: reject(IC-09 缺 pid → BusWriteFailed)
    - A7 PM-14 跨 pid 引用 evidence: reject as audit fault

依赖: tests/shared(real_event_bus / project_factory / ic_assertions).
"""
