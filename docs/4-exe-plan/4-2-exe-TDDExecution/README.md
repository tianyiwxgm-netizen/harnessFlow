---
doc_id: exe-plan-4-2-tdd-merged-note
doc_type: merged-notice
layer: 4-exe-plan / 4-2-exe-TDDExecution
version: v1.0
status: merged
---

# 4-2 · TDD 执行 · 融合说明（不独立开会话）

> **决策**：TDD 执行计划**不独立开会话 · 全部融合进 4-1 各 Dev/main exe-plan**。

## 为什么融合（Q-04 铁律）

参见 `docs/4-exe-plan/4-0-master-execution-plan.md §1.3 Q-04`：

> **Code + TDD 必须在同一会话内完成** · 不可分开。
>
> **理由**：
> 1. TDD red-green-refactor 循环需实时在 code 和 test 之间切换 · 拆成不同会话会丢失节奏
> 2. 单元测试断言依赖代码实现细节 · 分离后 context 缺失
> 3. 3-2 TDD 规格 57 份已完整 · 各 Dev 会话读 3-2/<自己 L1>/ 直接落地即可

## TDD 执行入口（在 4-1 各 md）

每份 Dev/main exe-plan 的 §3 WP 拆解都**明确包含 TDD 动作**：

- 每 WP 先写 failing test（red）
- 实现代码让 test pass（green）
- 重构 + test 保持绿（refactor）
- 跑全 WP 测试 + commit

## 对应 3-2 TDD 规格（独立会话读）

| 4-1 会话 | 对应 3-2 TDD 规格目录 |
|:---:|:---|
| Dev-α L1-09 | `docs/3-2-Solution-TDD/L1-09-韧性+审计/*-tests.md`（6 份）|
| Dev-β L1-06 | `docs/3-2-Solution-TDD/L1-06-3层知识库/*-tests.md`（4 份）|
| Dev-γ L1-05 | `docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/*-tests.md`（5 份）|
| Dev-δ L1-02 | `docs/3-2-Solution-TDD/L1-02-项目生命周期编排/*-tests.md`（7 份）|
| Dev-ε L1-03 | `docs/3-2-Solution-TDD/L1-03-WBS+WP 拓扑调度/*-tests.md`（5 份）|
| Dev-ζ L1-07 | `docs/3-2-Solution-TDD/L1-07-Harness监督/*-tests.md`（6 份）|
| Dev-η L1-08 | `docs/3-2-Solution-TDD/L1-08-多模态内容处理/*-tests.md`（4 份）|
| Dev-θ L1-10 | `docs/3-2-Solution-TDD/L1-10-人机协作UI/*-tests.md`（7 份）|
| main-1 L1-04 | `docs/3-2-Solution-TDD/L1-04-Quality Loop/*-tests.md`（7 份）|
| main-2 L1-01 | `docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/*-tests.md`（6 份）|
| main-3 集成 | `docs/3-2-Solution-TDD/integration/*.md`（24 份）+ `acceptance/*.md`（12 份）|

**合计 3-2 TDD 规格 57 L2 tests + 24 integration + 12 acceptance = ~93 份规格**。

## 落地方式

各 Dev/main 会话读自己 L1 对应的 3-2 目录 → 直接按测试用例清单 pytest 写 test → 实现代码 pass → commit。

**无需独立 4-2 会话**。

---

*— 4-2 · TDD 执行融合说明 · v1.0（目录保留 · 不独立分派）—*
