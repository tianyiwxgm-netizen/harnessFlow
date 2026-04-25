"""tests/integration/failure_propagation · 跨 L1 失败传播链路 (~25 TC).

main-3 WP06 子目录 2.

覆盖:
    - B1 L1-07 → L1-01 硬红线 BLOCK 链(IC-15) ≤ 100ms
    - B2 L1-04 Gate FAIL → L1-02 拒推进(IC-14)
    - B3 L1-09 panic → L1-01 全停(IC-17)
    - B4 L1-05 子 Agent timeout → L1-01 升级(IC-04 → fallback → IC-13)
    - B5 L1-03 WP fail → L1-04 回退(IC-02 → IC-14 INCONCLUSIVE)
    - B6 L1-09 hash-chain 断 → L1-01 readonly(IC-17 audit_chain_broken)
    - B7 跨 5 L1 panic 链路: l1-05 → l1-09 → l1-07 → l1-01 → l1-10
"""
