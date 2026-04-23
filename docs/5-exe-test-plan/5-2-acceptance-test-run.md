---
doc_id: exe-test-plan-5-2-acceptance-v1.0
doc_type: test-execution-plan
layer: 5-exe-test-plan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-3-integration-and-acceptance.md（acceptance 12 场景代码由 main-3 落地）
  - docs/3-2-Solution-TDD/acceptance/（12 份 · main-3 产出）
  - docs/2-prd/L1集成/prd.md（12 场景源头）
version: v1.0
status: draft
assignee: **QA-2 · 独立会话**
wave: 6（与 main-3 完成期并行 · 实际依赖 main-3 acceptance 代码 ready）
priority: P0（最终验收 · scenario-02 S1→S7 是核心）
estimated_duration: 3-4 天
---

# QA-2 · 验收测试（12 场景）Test Run Execution Plan

> **本 md 定位**：**独立会话** · 读本 md 即知如何跑 12 个 e2e 场景验收 + 产 scenario 报告。
>
> **本组做什么**：
> 1. 跑 main-3 acceptance/ 12 场景（scenario-01 ~ 12）
> 2. 每场景产 GWT 结构 report · 含审计链完整度 / 状态机路径 / IC 链 / 耗时
> 3. scenario-02 + scenario-08 为核心（S1→S7 全链 + 跨 session 恢复）
> 4. 交主会话（main-4 WP03-04 消费）
>
> **本组不做**：
> - ❌ 不写新 acceptance 代码（main-3 已落地）
> - ❌ 不独立 fix bug（main-4 主会话 fix）
> - ❌ scenario-11（V2+ 多 project）仅跑骨架 · skip

---

## §1 12 场景清单

| 场景 | 主题 | 复杂度 | SLO |
|:---:|:---|:---:|:---|
| scenario-01 | WP quality loop（S4 内反复直到 Gate 绿）| 中 | 合理耗时 |
| scenario-02 | S1→S7 全链（核心 · e2e）| 高 | 全链 20-60 min（mock LLM）|
| scenario-03 | S2 Gate 返工（Planning Gate 不过 · 回 S1）| 中 | - |
| scenario-04 | Change Request 插入 | 中 | - |
| scenario-05 | 硬红线（PM-14 违规 · HRL-01 halt）| 低 | **halt ≤ 100ms** |
| scenario-06 | panic 恢复（UI 异常 · IC-17）| 低 | **panic ≤ 100ms** |
| scenario-07 | Verifier fail + rollback（IC-20 + SDP-07）| 中 | - |
| scenario-08 | 跨 session 恢复（Tier 1-4 全测 · 核心）| 高 | Tier 1 ≤ 60s |
| scenario-09 | loop 升级（连续 rework → Stage Gate）| 中 | - |
| scenario-10 | KB promotion（session → project → global）| 低 | - |
| scenario-11 | 多 project V2+（骨架 · skip）| - | - |
| scenario-12 | 大代码库 onboarding（L1-08 VLM + path_safety）| 中 | - |

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | 3-2 acceptance/scenario-*.md 12 份（测试用例规格）|
| P0 | tests/acceptance/scenario_* 12 份代码（main-3 产出）|
| P0 | 2-prd/L1集成/prd.md §5 场景定义 |
| P0 | 3-1/L1集成/architecture.md §6 场景映射 |

---

## §3 WP 拆解（5 WP · 4 天）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| QA2-WP01 | 环境 + scenario-05/06（硬红线 + panic · 100ms）| main-3 WP08 | 0.5 天 |
| QA2-WP02 | scenario-01/03/04/07/09/10/12（7 场景 · 中低复杂度）| WP01 | 1.5 天 |
| QA2-WP03 | scenario-02 S1→S7 全链（核心 · 跑 3 次取均值）| WP01-02 | 1 天 |
| QA2-WP04 | scenario-08 跨 session 恢复（Tier 1-4）| WP03 | 0.75 天 |
| QA2-WP05 | 场景报告汇总 + 审计链验证 | 全 WP | 0.25 天 |

### 关键 WP 细节

**QA2-WP01 硬红线 + panic（100ms SLO）**：
- scenario-05：故意 L1-02 创建 pid 时漏 pid · 期望 HRL-01 trigger · L1-07 IC-15 · L1-01 halt
- 测量全链时延：必须 ≤ 100ms · 超则标 P0
- scenario-06：故意触发 UI panic 事件 · 期望 IC-17 · state=PAUSED ≤ 100ms

**QA2-WP02 7 场景批量**：
- 每场景独立 project pid · 跑单次 · 失败 retry 2 次
- 产物：每场景 `reports/scenario_XX.md`（GWT PASS/FAIL）

**QA2-WP03 scenario-02 S1→S7**（最复杂）：
- 输入：mock 用户 "做一个 TODO App"
- 跑全链：S1 kickoff → S2 Planning → S3 TDD Gate → S4 Executing × N WP → S5 Integration → S6 Closing → S7 Archive
- mock LLM（豆包 mock · 返固定 response）
- 期望链路（全匹配 · 任一失败 report P0）：
  - L1-02 创建 pid
  - L1-01 S1 → S2 transition + IC-16 Gate card
  - L1-04 Planning DoD 编译
  - L1-03 WBS 拆解（IC-19）· WP 队列 ready
  - L1-01 WP 分配（IC-02 + IC-03）
  - L1-05 subagent 执行（IC-04 / IC-05）
  - L1-04 Quality Gate 裁决（reject/rework/pass）
  - L1-04 Verifier（IC-20）
  - L1-01 S6/S7 transition
  - L1-02 归档 tar.zst（PM-14 尊重）
  - L1-09 审计链完整 100%（~N 千条事件 · hash 链不断）
- 跑 3 次（取成功率 + 均耗时）· 期望 3/3 pass

**QA2-WP04 scenario-08 跨 session 恢复**：
- 跑 `scripts/scenario_08_runner.sh`：
  - Tier 1：latest checkpoint 正常 → 启动后状态一致 ≤ 60s
  - Tier 2：checkpoint 坏 → fallback 到前一个 · 告警但继续
  - Tier 3：events.jsonl 中间破损 → 跳跃恢复（失最后一段 events）· 告警
  - Tier 4：全坏 → refused to fake recovery · halt
- 期望 4/4 tier 行为与预期一致

**QA2-WP05 汇总**：
- 12 场景报告矩阵 · PASS/FAIL/SKIP
- 审计链总验证：`pytest tests/acceptance/test_audit_chain_integrity.py`
- 交 `reports/QA2-scenario-summary.yaml`

---

## §4 依赖图

```
main-3 WP08-10 全绿（acceptance 代码 ready）
  ↓
QA2-WP01（硬红线 + panic）
  ↓
QA2-WP02（7 场景 · 可并行）
  ↓
QA2-WP03（S1→S7）
  ↓
QA2-WP04（跨 session）
  ↓
QA2-WP05 汇总 → main-4 WP03-04 消费
```

---

## §5-§10

- §5 standup · prefix `QA2-WPNN`
- §6 自修正：若场景 acceptance 本身有 bug · 回锤 main-3 · 走 4-0 §6 情形 C
- §7 无对外契约
- §8 DoD：
  - 11 场景 PASS（scenario-11 V2+ skip）
  - scenario-02 + 08 成功率 100%
  - 审计链完整 100%
  - 100ms 硬约束 100% 达成
- §9 风险：
  - R-QA2-01 scenario-02 全链超时（> 60 min mock LLM）· main-4 WP05 调优
  - R-QA2-02 跨 session Tier 4 难以构造 · 与主会话 pair 调试
- §10 交付：`reports/QA2-scenario-summary.yaml` + 每场景子报告

---

*— QA-2 · 验收测试（12 场景）Test Run · Execution Plan · v1.0 —*
