---
doc_id: exe-test-plan-5-3-performance-v1.0
doc_type: test-execution-plan
layer: 5-exe-test-plan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/2-prd/L1集成/prd.md §7 性能 SLO（11 时延 + 5 吞吐 + 2 资源）
  - docs/3-1-Solution-Technical/L1集成/architecture.md §8 性能模型
version: v1.0
status: draft
assignee: **QA-3 · 独立会话**
wave: 6（与 QA-1/2 并行）
priority: P0（硬约束不达将阻塞 release · 100ms × 2 + 500ms × N）
estimated_duration: 2-3 天
---

# QA-3 · 性能测试 Test Run Execution Plan

> **本 md 定位**：**独立会话** · 读本 md 即可跑 18 项性能 benchmark + 出 SLO 达标报告。
>
> **本组做什么**：
> 1. 跑 7 大类性能 benchmark（11 时延 + 5 吞吐 + 2 资源）
> 2. 对比 PRD §7 SLO · 产 **SLO 达标矩阵**
> 3. 不达标项交 main-4 WP05（调优专项）
>
> **本组不做**：
> - ❌ 不调优（main-4 WP05 做）
> - ❌ 不改 SLO 预期（若发现 SLO 本身不合理 · 走 §6 情形 A · 改 PRD）

---

## §1 18 项 benchmark 清单

### 1.1 时延 11 项（PRD §7.1）

| ID | 指标 | SLO | 硬约束 |
|:---:|:---|:---:|:---:|
| T-01 | IC-01 state_transition P95 | < 50ms | - |
| T-02 | IC-09 events_append P50 | < 5ms | - |
| T-03 | IC-09 events_append P95 | < 20ms | - |
| T-04 | IC-06 kb_read P95 | < 500ms | - |
| T-05 | IC-15 hard_halt e2e | **≤ 100ms** | **硬**|
| T-06 | IC-17 panic e2e | **≤ 100ms** | **硬**|
| T-07 | L1-01 tick drift P95 | **≤ 100ms** | **硬**|
| T-08 | L1-04 DoD 编译 | < 200ms | - |
| T-09 | L1-08 VLM 单次 | < 3000ms | - |
| T-10 | L1-05 subagent 派发 | < 500ms | - |
| T-11 | L1-09 Tier 1 恢复 | < 60000ms | - |

### 1.2 吞吐 5 项（PRD §7.2）

| ID | 指标 | SLO |
|:---:|:---|:---:|
| TP-01 | IC-09 events/s（单 project）| ≥ 100/s |
| TP-02 | IC-06 kb_read/s（热路径）| ≥ 50/s |
| TP-03 | WP 并发（V1 · 1 project）| 1 project × 1 WP tick |
| TP-04 | Skill invoke/min | ≥ 30/min |
| TP-05 | audit append/s（峰值）| ≥ 500/s（短时）|

### 1.3 资源 2 项（PRD §7.3）

| ID | 指标 | SLO |
|:---:|:---|:---:|
| R-01 | 内存（1 project 运行）| < 800MB |
| R-02 | 磁盘（events.jsonl/天）| < 100MB |

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | PRD §7 SLO 原文 |
| P0 | architecture.md §8 性能模型（期望值） |
| P1 | main-3 perf-integration-tests 代码（运行基础）|
| P1 | QA-1 Block E 已跑的性能测试（复用）|

---

## §3 WP 拆解（4 WP · 2.5 天）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| QA3-WP01 | 环境 + benchmark harness | main-3 ready | 0.5 天 |
| QA3-WP02 | 时延 11 项（含 3 硬约束）| WP01 | 1 天 |
| QA3-WP03 | 吞吐 5 项 + 资源 2 项 | WP01 | 0.5 天 |
| QA3-WP04 | SLO 达标矩阵 + 报告 | 全 WP | 0.5 天 |

### 关键 WP 细节

**QA3-WP01 harness**：
- 装 `pytest-benchmark` · 配 `--benchmark-json` 导出
- 准备 baseline project（含代表性 WP · 复用 scenario-02 准备数据）
- 启动完整 harnessFlow（真实 tick loop · 非 mock）

**QA3-WP02 时延 11 项**：
- 每项跑 1000 次采样 · 取 P50/P95/P99
- **3 硬约束**（T-05/T-06/T-07）：
  - 跑 10000 次采样（样本更大）
  - 任一样本 > SLO → 标 P0（主会话 main-4 WP05 必调）
- 产物：`benchmarks/latency_*.json`

**QA3-WP03 吞吐 + 资源**：
- 吞吐：持续 1 min 压力 · 统计 QPS
- 资源：跑 1 小时 · `psutil` 监控 · 峰值 + 均值
- 磁盘：跑 24h baseline（或插 mock · 按 pattern 放大）

**QA3-WP04 SLO 矩阵**：
```yaml
slo_matrix:
  T-05_ic15_halt_e2e_100ms:
    samples: 10000
    p50: 62ms
    p95: 87ms
    p99: 95ms
    max: 98ms
    slo: 100ms
    status: PASS  # 或 FAIL
  T-06_ic17_panic_100ms:
    samples: 10000
    p95: 72ms
    ...
  ...
overall:
  total: 18
  pass: 16
  fail: 2
  fail_list:
    - T-09_vlm_3000ms  # 实际 P95 3400ms
    - R-01_memory_800MB  # 实际 880MB
```
- 不达标 · 附 `debug_trace` 帮主会话定位

---

## §4 依赖图

```
main-3 + Dev/主-1/2 全绿
  ↓
QA3-WP01 harness
  ↓
QA3-WP02 ──┬── QA3-WP03（并行）
  ↓         ↓
QA3-WP04 → main-4 WP05 调优消费
```

---

## §5-§10

- §5 standup · prefix `QA3-WPNN`
- §6 自修正：若 SLO 本身不合理（如 T-09 VLM 3000ms 实际硬件无法达）· 走 §6 情形 A · 改 PRD §7
- §7 无对外契约
- §8 DoD：
  - 18 项全跑
  - **3 硬约束 100% 达**（否则 release 阻塞）
  - 其余达标率 ≥ 85%（不达项数交 main-4 WP05）
- §9 风险：
  - R-QA3-01 VLM 依赖外部 API · 环境抖动影响
  - R-QA3-02 tick drift 100ms 硬约束在低配机难达 · 规约最低硬件
- §10 交付：`reports/QA3-slo-matrix.yaml` + 每项 benchmark json

---

*— QA-3 · 性能测试 Test Run · Execution Plan · v1.0 —*
