"""tests/integration/matrix/ · main-3 WP05 · 10×10 跨 L1 矩阵集成测试.

**定位**:
    波 6 收官 WP · 完整 10×10 跨 L1 矩阵端到端集成 · 覆盖 ~30 关键 cells.
    每 cell ≥ 4 TC（正向 / 负向 / SLO / e2e）· 总 ~180 TC.

**矩阵 cell 分布**(按 cross-l1-integration.md §1.3 + §2):
    - Row L1-01 主决策 → others : 4 cells × 6 TC = 24 TC
    - Row L1-02 项目生命周期 → others : 3 cells × 6 TC = 18 TC
    - Row L1-03 WBS+WP → others : 3 cells × 6 TC = 18 TC
    - Row L1-04 Quality Loop → others : 3 cells × 6 TC = 18 TC
    - Row L1-05 Skill → others : 3 cells × 6 TC = 18 TC
    - Row L1-06 KB → others : 3 cells × 6 TC = 18 TC
    - Row L1-07 Supervisor → others : 4 cells × 6 TC = 24 TC
    - Row L1-08 Multimodal → others : 2 cells × 6 TC = 12 TC
    - Row L1-09 Resilience → others : 3 cells × 6 TC = 18 TC
    - Row L1-10 UI → others : 2 cells × 6 TC = 12 TC

    总: 30 cells × 6 = 180 TC + aggregate 1.

**铁律**:
    - 真实 import L1 模块 · 不 mock 核心
    - 用 tests/shared 公共 fixture / stub
    - 每 cell ≥ 1 TC · 用 MatrixCoverage 工具断言全覆盖
    - PM-14 分片合规
"""
