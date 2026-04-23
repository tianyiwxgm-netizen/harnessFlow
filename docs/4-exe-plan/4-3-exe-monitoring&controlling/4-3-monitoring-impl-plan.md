---
doc_id: exe-plan-4-3-monitoring-v1.0
doc_type: monitoring-controlling-execution-plan
layer: 4-exe-plan / 4-3-exe-monitoring&controlling
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/3-3-Solution-Monitoring&Controlling/monitoring-metrics/（监督原语规约 · O 产出）
  - docs/3-3-Solution-Monitoring&Controlling/acceptance-criteria/（最终验收标准）
  - docs/3-3-Solution-Monitoring&Controlling/dod-specs/（DoD 规约）
  - docs/3-3-Solution-Monitoring&Controlling/quality-standards/（质量标准）
  - docs/3-3-Solution-Monitoring&Controlling/hard-redlines/（5 条硬红线）
  - docs/3-3-Solution-Monitoring&Controlling/soft-drift-patterns/（8 类 soft-drift 模式）
  - docs/3-1-Solution-Technical/L1-07-Harness监督/（L1-07 实现端）
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/（L1-04 DoD 编译 · 质量 Gate）
version: v1.0
status: draft
assignee: **拆为多段**：Dev-ζ（L1-07 监督规则落代码）+ 主-1（L1-04 DoD/质量规则）+ main-1（最终集成期验证监督效果）
wave: 与对应 Dev/主-1 同拨（波 3 + 波 5）
priority: P0（Harness 闭环的上限约束）
estimated_loc: ~6000 行（规则字典 · YAML 配置 · Python 引擎）
estimated_duration: 2 天（并入 Dev-ζ / 主-1 · 不单独开会话）
---

# 4-3 · 监督 + 质量规约落地 Execution Plan（3-3 O 产出 → 代码）

> **本 md 定位**：**3-3 监督规约**（O 会话 · final delivery 验收标准源）**→ 实际代码落地**的桥梁。
>
> **重要设计决策**：本 md 不开独立会话 · 而是**融合进 Dev-ζ（L1-07 监督引擎 · ~8 硬规则 + 8 模式）和主-1（L1-04 质量 Gate · DoD 编译器）**两组。原因：
> 1. 监督规则是 L1-07 的本分工作 · 拆开反倒增集成成本
> 2. DoD/质量 Gate 是 L1-04 的核心能力 · 也无需拆
> 3. 独立唯一的是「**最终验收 checklist**」· 由 main-4 最终集成期验证 · 已列 main-4 WP08
>
> **本 md 主要职责**：提供**源导读 + 映射表**（监督规约 → 代码位置）· 让 Dev-ζ / 主-1 作为参考。
>
> **前置**：3-3 O 会话产出完成（2026-04-21 完成）· 规约具备结构化可机读。

---

## §0 撰写进度

- [x] §1-§6 全齐

---

## §1 本 md 范围

### 做什么

1. **监督原语 → L1-07 代码映射**（融合到 Dev-ζ · WP01-02）
   - 5 条硬红线（`hard-redlines/`）→ L2-01 Halt 决策器
   - 8 类 soft-drift 模式（`soft-drift-patterns.md`）→ L2-02 偏移检测器
   - 8 维度监控指标（`monitoring-metrics/`）→ L2-03 监控采样器
   - 4 级严重度分级 + 建议构造 → L2-04/05
2. **DoD 规约 → L1-04 质量 Gate 代码映射**（融合到主-1 · WP01/04）
   - DoD 表达式语法（`dod-specs/`）→ L2-01 DoD 表达式编译器
   - 质量标准（`quality-standards/`）→ L2-02 质量 Gate 编译器
3. **最终验收 checklist**（`acceptance-criteria/` · O 产出）→ **main-4 WP08 消费**（已列）

### 不做什么

- ❌ 不重写 L1-07 / L1-04 代码（已在各自 exe-plan）
- ❌ 不单独开会话（并入 Dev-ζ + 主-1）
- ❌ 不改监督规约本体（若需改 · 走 4-0 §6 情形 E）

---

## §2 源导读（3-3 规约全景）

### 2.1 5 条硬红线（触发立即 halt）

| 红线 | 触发条件 | 落地位置 |
|:---:|:---|:---|
| HRL-01 | PM-14 违规（写操作缺 pid）| L1-09 L2-04 audit · L1-07 L2-01 halt |
| HRL-02 | 审计链破损（hash 断链）| L1-09 L2-02 event_bus · L1-07 L2-01 |
| HRL-03 | 可追溯率 < 100%（Goal §4.1）| L1-01 L2-05 audit · L1-07 监控 |
| HRL-04 | panic 未 100ms 响应 | L1-10 L2-07 panic · L1-07 L2-01 |
| HRL-05 | halt 请求未 100ms 响应 | L1-07 L2-06 + L1-01 L2-06 |

**代码位置**：`app/l1_07/hard_redline_detector.py` + `app/l1_01/tick_scheduler/halt_enforcer.py`

### 2.2 8 类 soft-drift 模式（触发 rollback suggestion）

| 模式 | 语义 | 落地位置 |
|:---:|:---|:---|
| SDP-01 | Gate 过度让步（连续 ≥ 3 次 TOLERATED 降级）| L1-04 L2-02 Gate 裁决 · L1-07 L2-02 |
| SDP-02 | WP 循环反复失败（同 WP `fail_count ≥ 3`）| L1-03 + L1-07 L2-02 |
| SDP-03 | Skill fallback 过度（Claude 原生调用异常增）| L1-05 + L1-07 监控 |
| SDP-04 | KB 命中率骤降（< 30%）| L1-06 监控 · L1-07 L2-02 |
| SDP-05 | Audit 写入延时 tailing（P95 > 20ms）| L1-09 监控 · L1-07 L2-02 |
| SDP-06 | UI panic 频发（24h ≥ 3 次）| L1-10 · L1-07 L2-02 |
| SDP-07 | Verifier 连续拒绝（同 WP ≥ 3）| L1-04 L2-06 · L1-07 L2-02 |
| SDP-08 | 状态机逆转回撤（S-forward 后 repeat S-back）| L1-01 L2-03 · L1-07 L2-02 |

**代码位置**：`app/l1_07/soft_drift_detector.py` · 每模式一个 checker class

### 2.3 8 维度监控指标

| 维度 | 示例指标 | 采样频率 |
|:---:|:---|:---:|
| 审计可追溯 | 未审计决策数 / 单 tick | 100ms |
| 质量 Gate | hard_pass_rate / tolerated_rate | 每 Gate |
| WP 成功率 | 成功 / 失败 / 循环 | 每 WP |
| Skill 调用 | subagent 调用次数 / fallback 率 | 每调用 |
| KB 命中 | session/project/global 命中率 | 每 read |
| Audit 延时 | fsync P50/P95/P99 | 100ms |
| UI 健康 | panic 次数 / 连接数 / 心跳 | 1s |
| 状态机 | 转换次数 / 卡住时间 | 100ms |

**代码位置**：`app/l1_07/metrics_sampler.py` + `app/l1_07/drift_scorer.py`

### 2.4 4 级严重度分级

| 级 | 语义 | 响应 |
|:---:|:---|:---|
| L1 INFO | 健康波动 | 记录 |
| L2 WARN | 需关注 | IC-13 push_suggestion |
| L3 ERROR | 建议降级 | IC-14 push_rollback_route |
| L4 CRITICAL | 立即止损 | IC-15 request_hard_halt |

**代码位置**：`app/l1_07/severity_classifier.py`

### 2.5 DoD 表达式语法（质量 Gate 编译器输入）

```yaml
# 示例：L1-02 L2-01 stage-gate 的 DoD
dod:
  hard:
    - project_exists
    - state_transition_audited
    - gate_card_emitted_to_ui
  soft:
    - "hard_pass_rate >= 95%"
    - "soft_pass_rate >= 80%"
  metric:
    - "e2e_latency_p95 < 500ms"
```

**代码位置**：`app/l1_04/dod_compiler/` · 表达式 AST → 裁决函数

### 2.6 质量标准（5 基线）

- **hard_pass**：硬约束必须 100% 通过
- **soft_pass**：软约束 ≥ 80% 通过（可 tolerated）
- **tolerated**：软约束 60-80% 通过（警告 + 记录）
- **rework**：< 60% 通过 · 返 S4 重执行
- **abort**：连续 3 次 rework 失败 · 升级 stage gate

**代码位置**：`app/l1_04/quality_gate_compiler/` + `app/l1_04/rollback_router/`

### 2.7 最终验收 checklist（main-4 消费）

见 `acceptance-criteria/*.md` · ~50 条目 · main-4 WP08 签收时逐条勾。

---

## §3 融合到其他 exe-plan 的映射表

| 3-3 规约 | 融合到 | WP 标识 | 备注 |
|:---:|:---|:---:|:---|
| 5 硬红线 | Dev-ζ L1-07 | ζ-WP01 HRL 检测器 | 融合入 L2-01 · +300 行 |
| 8 soft-drift | Dev-ζ L1-07 | ζ-WP02 SDP 检测器 | 融合入 L2-02 · +600 行 |
| 8 维度指标 | Dev-ζ L1-07 | ζ-WP01 采样 | 已在 Dev-ζ L2-03 |
| 4 级严重度 | Dev-ζ L1-07 | ζ-WP03 分类 | 已在 Dev-ζ L2-04 |
| DoD 语法 | 主-1 L1-04 | 主-1 WP01 编译器 | 已在主-1a |
| 质量 5 基线 | 主-1 L1-04 | 主-1 WP04 Gate | 已在主-1a |
| 验收 checklist | main-4 | main-4 WP08 | 已在 main-4 |

**累计新增代码**：~6000 行（并入 Dev-ζ + 主-1 · 不新增 md 文件）

---

## §4 集成期验证（main-4 WP05/06 消费）

**监督效果端到端验证**：
- scenario-05（硬红线）：故意触发 PM-14 违规 · 验证 HRL-01 halt ≤ 100ms
- scenario-07（Verifier fail）：故意 Verifier 3 次拒绝 · 验证 SDP-07 rollback
- scenario-09（loop escalation）：故意连续 rework · 验证升级到 stage gate

**DoD 编译器验证**：
- 跑 `tests/l1_04/test_dod_compiler.py` 全绿
- 跑示例 DoD · 期望裁决结果正确

**质量 Gate 验证**：
- 跑主-1 WP04-05 · 全 GWT 绿

---

## §5 自修正

若集成期发现监督规约的问题（如 SDP-08 误报率高 · 硬红线漏判）：
- 走 4-0 §6 情形 E（监督规约偏差）
- 主会话仲裁 · 改 3-3 规约本体 · 回锤 Dev-ζ / 主-1 修代码
- 通知 main-4 重跑相关验收

---

## §6 DoD + 风险

**DoD**：
- ζ-WP01/02 全绿（监督规则代码）
- 主-1 WP01/04 全绿（DoD 编译器 + 质量 Gate）
- scenario-05/07/09 验证全绿（main-4 WP05 期）
- acceptance-criteria/*.md 全勾（main-4 WP08）

**风险**：
- R-4-3-01 监督规则误报率高 · main-4 集成期发现 · 走 §6 情形 E 调优
- R-4-3-02 DoD 表达式 AST 解析 edge case · 主-1a WP01 单元测试需充分

---

*— 4-3 · 监督 + 质量规约落地 · Execution Plan · v1.0（融合方案 · 不开独立会话）—*
