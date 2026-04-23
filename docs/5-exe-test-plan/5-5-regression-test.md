---
doc_id: exe-test-plan-5-5-regression-v1.0
doc_type: test-execution-plan
layer: 5-exe-test-plan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/5-exe-test-plan/5-1-integration-test-run.md
  - docs/5-exe-test-plan/5-2-acceptance-test-run.md
  - docs/5-exe-test-plan/5-3-performance-test-run.md
  - docs/5-exe-test-plan/5-4-failure-injection.md
version: v1.0
status: draft
assignee: **QA-5 · 独立会话（或主会话兼）**
wave: 6-7（main-4 修 bug 后 · release 前必跑）
priority: P0（release gate · 退化即阻塞发布）
estimated_duration: 1-2 天
---

# QA-5 · 回归测试 Test Run Execution Plan

> **本 md 定位**：**独立会话** · 读本 md 即知如何跑回归验证 · 确保 main-4 WP06 bug fix 不引入退化。
>
> **本组做什么**：
> 1. 全量跑 QA-1 + QA-2 + QA-3 + QA-4 套件
> 2. 对比上轮结果 · 产 diff 报告
> 3. 任何退化项（原 PASS → FAIL）· 标 P0 · 返 main-4
> 4. 最终 release gate：0 退化 · 才能进 main-4 WP07 打包
>
> **本组不做**：
> - ❌ 不写新测试
> - ❌ 不 fix bug（返 main-4）

---

## §1 范围

### 回归全量范围

- QA-1 集成测试 620 TC
- QA-2 验收测试 11 场景（scenario-11 skip）
- QA-3 性能 18 项
- QA-4 失败注入 42 用例
- **合计 ~691 TC/用例**

### 跑几轮

- **R1 · 首轮 full**（main-4 WP06 bug fix 第一批后）
- **R2 · 二轮 full**（bug fix 第二批后）
- **R3 · 终轮 release gate**（main-4 WP07 前 · 必须 0 退化 · 0 P0/P1）

### 对比维度

| 维度 | 对比源 | 容忍 |
|:---:|:---|:---|
| TC 状态 | 上轮 PASS 的 TC | 0 退化（新 FAIL 不容忍）|
| 性能 SLO | QA-3 baseline | P95 波动 ≤ 10%（超则 P1）|
| 恢复时间 | QA-4 Tier 1 baseline | ≤ 10% 波动 |
| 审计链完整 | 任一轮 | 100%（任何破损 → halt）|

---

## §2 源导读

- QA-1 `reports/QA1-final-bug-report.yaml`（上轮基线）
- QA-2 `reports/QA2-scenario-summary.yaml`
- QA-3 `reports/QA3-slo-matrix.yaml`
- QA-4 `reports/QA4-resilience-matrix.yaml`
- main-4 `reports/main4-fix-log.yaml`（本轮改动清单）

---

## §3 WP 拆解（3 WP × N 轮 · 1-2 天/轮）

| WP | 主题 | 估时/轮 |
|:---:|:---|:---:|
| QA5-WP01 | 全量重跑（4 套件 · 顺序或并行）| 1 天 |
| QA5-WP02 | 结果对比 · 退化检测 | 0.25 天 |
| QA5-WP03 | 回归报告 · release gate 裁决 | 0.25 天 |

### 关键 WP 细节

**QA5-WP01 重跑**：
- 脚本：`scripts/regression_runner.sh --round N`
- 顺序：QA-1（1 天）→ QA-2（1 天）→ QA-3（0.5 天）→ QA-4（0.5 天）
- 或并行（需 4 slot）：QA-1/2/3/4 同时 · 0.75 天 done

**QA5-WP02 对比**：
- Python 脚本：`scripts/regression_diff.py --before reports/r{N-1} --after reports/r{N}`
- 输出：
  ```yaml
  regression:
    total_tc: 691
    passed: 688
    failed: 3
    newly_failed: 2   # 退化（之前 PASS 现 FAIL）
    newly_passed: 0   # 修复
    still_failed: 1   # 上轮已知 · 未修
    regression_items:
      - tc: test_ic09_chain_after_fsync_retry
        before: PASS
        after: FAIL
        severity: P0
  ```

**QA5-WP03 release gate**：
- 判据：
  - `newly_failed == 0` ✅
  - P0 count == 0 ✅
  - P1 count == 0 ✅
  - 性能 SLO 硬约束 100% 达 ✅
  - 审计链完整 100% ✅
- 全绿 · release gate **PASSED** → main-4 WP07 打包
- 任一红 · **FAILED** → 返 main-4 WP06 继续 fix · 跑 R{N+1}

---

## §4 依赖图

```
main-4 WP06 bug fix
  ↓
QA5-WP01 重跑（R1）
  ↓
QA5-WP02 对比
  ↓
QA5-WP03 gate
  ├── PASS → main-4 WP07（release）
  └── FAIL → main-4 WP06 继续（迭代 R2/R3）
```

---

## §5-§10

- §5 standup · prefix `QA5-WPNN-R{N}`
- §6 自修正：若发现 regression 根因是测试用例本身 flaky（非被测对象）· 回锤 main-3
- §7 无对外契约
- §8 DoD：
  - 终轮 R{final}：0 退化 · 0 P0/P1 · 硬 SLO 100% · 审计 100%
  - release gate PASSED 签字
- §9 风险：
  - R-QA5-01 迭代次数过多 · 项目整体延期 → main-4 主会话加大 fix 带宽
  - R-QA5-02 flaky 难定性 · 3 次重试制度化
- §10 交付：`reports/QA5-regression-final.yaml` · release gate yes/no

---

*— QA-5 · 回归测试 Test Run · Execution Plan · v1.0 —*
