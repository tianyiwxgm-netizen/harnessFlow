---
doc_id: spec-3-solution-resume-v2.0
doc_type: design-spec
created_at: 2026-04-21
supersedes: docs/superpowers/specs/2026-04-20-3-solution-design.md (v1.0)
brainstorming_skill_version: superpowers 5.0.7
approved_by: user (2026-04-21 Q1/Q2/Q3/Q4 逐节审批 + Section 1-4 逐节审批)
status: approved_for_implementation
---

# 3-Solution Resume 推进方案 v2.0（Brainstorming 输出）

## 0. 为什么要 v2.0

**v1.0 现状** ↓ **v1.0 推进遇到的问题** ↓ **v2.0 调整点**

v1.0（2026-04-20-3-solution-design.md）定义了 162 份文档的 Phase 1-6 并行撰写策略。执行到中期遇到 3 个问题：

1. **subagent 并发稳定性不足**：单批 11 个并发 subagent 中 7 个因 Anthropic API `certificate verification error` / `socket closed` / 600s watchdog 失败，实际产出极少（仅留下 0-3 行脏改动，可忽略）。
2. **粒度过宽导致不可完成**：v1.0 要求每 L2 tech-design 达"实现级 + 时序图强调"（推算 1000-1500 行），57 份 L2 × 1000 行 = 57k 行，单轮推进不可能完成——质量锚点未锁死就扩散并发批次，返工风险高。
3. **图形式约束变更**：用户 IDE（IntelliJ + Markdown + PlantUML 插件）要求全部 UML 图一律 PlantUML；v1.0 的 170 个 Mermaid 块需全量转换，且新增文档必须用 `@startuml/@enduml` 语法。

v2.0 针对以上 3 点做**粒度分级 + 契约优先 + 关键路径主写 + 脚本化图迁移**四项调整。

## 1. 范围

**v2.0 不重写 v1.0**，只定义 v1.0 剩余工作的**推进策略**。v1.0 的以下结论保持：

- 162 份文档总量
- 3 个子方案（3-1 Technical / 3-2 TDD / 3-3 Monitoring）
- 每 L2 的 13 段模板
- DDD 映射 / 接口驱动设计 / 开源调研硬要求 / "串不起来反向修 PRD" 规则

**v2.0 新增的硬约束**：

1. **全文档图表一律 PlantUML**（`\`\`\`plantuml` + `@startuml`/`@enduml`）— 与全局 memory `feedback_diagrams_plantuml.md` 对齐
2. **粒度分级**（§3 Q1 = C）
3. **契约优先顺序**（§3 Q2 = D）
4. **关键路径主写 + 外围 subagent 并发**（§3 Q3 = C）
5. **多回写规范**（§5 防 600s watchdog）

## 2. 当前真实完成度（2026-04-21 开工基线）

| 维度 | 数量 | 状态 |
|---|---|---|
| 3-1 L0（tech-stack / ddd-context-map / open-source-research / sequence-diagrams-index / architecture-overview）| 5/5 | ✓ 已填 · Mermaid→PlantUML 已转（L0 全部 5 份完成 64/64 块）|
| 3-1 projectModel | 1/1 | ✓ 已填 · Mermaid→PlantUML 已转（7/7 块）|
| 3-1 L1-01~10 architecture | 10/10 | ✓ 已填（762-2325 行）· Mermaid 转换：L1-07/08/10 已完成（28/28 块）；L1-01/02/03/04/05/06/09 剩 62 块未转 |
| 3-1 L2 tech-design | 2/57 | L2-02 已填 §1+§3（563 行 · 质量标杆）· L1-09/L2-03 有旧填充（188 行）· 其余 55 份仍 130 行骨架 |
| 3-1 integration | 0/4 | 未启动（p0-seq / p1-seq / ic-contracts / cross-l1）|
| 3-2 Solution-TDD | 0/~75 | 未启动 |
| 3-3 Monitoring | 0/10 | 未启动 |
| 剩余 Mermaid 块 | 15 块（L1-09/L2-01 5 + L2-02 6 + L2-05 6 估算中；已完成 92/~170） | 脚本 + 精修待做 |

**实际开工点**：L0 + projectModel + 10 L1 architecture + 2 L2（L2-02 + L1-09/L2-03）已可消费；后续需补 55 L2 + 4 integration + 75 TDD + 10 监督 + 剩余 Mermaid 迁移。

## 3. 4 个关键架构决策（Brainstorming Q1-Q4）

| # | 决策 | 选项 | 选定 | 理由 |
|---|---|---|---|---|
| **Q1** | 粒度基调 | A 全量深度 / B MVP 精华 / **C 分级** / D 两阶段铺后深 | **C · 分级 · 核心深度 + 外围精简** | L1-01（主 loop） + L1-04（Quality Loop） + L1-07（Harness 监督）= 3 大核心 L1 = 19 份 L2 用 A 全量（1000-1500 行）；其余 7 个 L1 = 38 份 L2 用 B 精简（400-600 行 · §1/§3/§5/§11/§13 硬必填，余 8 段精简小结）。总产出 ~50k 行 · 质量最高核心深度 + 总量可控 + 外围不延期 |
| **Q2** | 推进顺序 | A 原 Phase / B L1 纵切 / C 混合模板复刻 / **D 契约优先** | **D · 契约优先** | 先做 integration 4 份把 10 条 IC-01~IC-17 跨 L2 契约字段级锁死；后续 57 份 L2 引用 IC 时只能对齐已锁契约；3-2 TDD 能对契约做字段级断言；PRD 反向修触发最早（矛盾浓缩区）——三项叠加 = **零返工风险** = 质量最高 |
| **Q3** | 并发/重试 | A 主 session 全顺序 / B 全 subagent / **C 关键路径主写 + 外围 subagent** / D 3 并发 + 2 重试 | **C · 混合** · 用户后续修正为"全批量上 subagent + 多回写" | 质量锚点（契约 ic-contracts · L1-01 模板 · 硬红线/DoD 规约）仍主 session 保精度；其余 L2/TDD/监督辅助全 subagent 并发 + 每 subagent 多回写（8-15 tool calls · 单 Edit ≤ 400 行防 watchdog）|
| **Q4** | Mermaid 迁移 | A Python 脚本 / B 重跑 subagent / **C 脚本 + 精修** / D 延后背景 | **C · 脚本 + 主 session 精修** | Python regex 机械转覆盖 ~80%（sequence + state 近似同构 · flowchart→component 规则转），主 session 精修剩 20% 复杂图（L1-04 architecture 15 块最复杂）——双保险质量最高，一步到位 |

## 4. Phase R0-R7 推进大图

| Phase | 内容 | 执行者 | 并发度 | 产出 | 预计 |
|---|---|---|---|---|---|
| **R0** | Mermaid→PlantUML 剩 62 块（L1-01/02/03/04/05/06/09 architecture + L1-09 3 L2）| 主 session 脚本 + 精修 | 脚本主导 | 全文档视觉统一 | 40 min |
| **R1** | integration 4 份：**主 session 写 ic-contracts.md**（10 条 IC 字段级 YAML · 质量锚点）+ **subagent 3 并发写** p0-seq.md / p1-seq.md / cross-l1-integration.md | 1 主 + 3 subagent | 契约字段级锁死 = **M1 消费单元** | 1.5 h |
| **R2** | L1-01 模板 6 份：**主 session 补 L2-02 §2/§4-§13**（已有 §1+§3 标杆 · 补 ~900 行）+ **subagent 5 并发写 L2-01/03/04/05/06** | 1 主 + 5 subagent | 6 份深度 = 标杆 + **M2 L1-01 端到端可消费** | 1.5 h |
| **R3a** | L1-04 Quality Loop 7 份深度 | subagent 5 并发 × 2 批（5+2）| 全 subagent | 7 份深度 | 1 h |
| **R3b** | L1-07 Harness 监督 6 份深度 | subagent 5 并发 × 2 批（5+1）| 全 subagent | 6 份深度 + **M3 系统骨架可跑** | 1 h |
| **R4** | 外围 35 份精简（L1-02×7 + L1-03×5 + L1-05×5 + L1-06×5 + L1-08×4 + L1-09 剩 2 + L1-10×7 · 精简 B 粒度）| subagent 5 并发 × 7 批 | 全 subagent | 57 L2 全铺 = **M4 完整 3-1** | 2 h |
| **R5** | 3-2 TDD 75 份（镜像 3-1）| subagent 5 并发 × 15 批 | 全 subagent | 验证层就位 = **M5 可入 4-Exe** | 3 h |
| **R6** | 3-3 监督 10 份：**主 session 写 hard-redlines + dod-specs 2 份**（硬约束核心）+ **subagent 4 并发写 8 份** | 1 主 + 4 subagent | 规约层就位 | 1.5 h |
| **R7** | 质量 Gate（§7）+ 一致性审计 + 抽样 5 份比对标杆 + `plantuml` CLI lint（可选）+ git commit + push | 主 session | — | **M6 可交付状态** | 1 h |

**新总估：~14 h**（比 v1.0 的 ~20h 缩短 6h · 通过契约先行消除返工）

**关键分界**：
- R0-R2 = **质量锚点建立期**（3.7 h · 主 session 主导）
- R3-R5 = **批量复刻期**（7 h · subagent 并发主导）
- R6-R7 = **规约收尾期**（2.5 h · 主+副混合）

## 5. 多回写规范（subagent 必须遵守）

### 5.1 防 watchdog 硬规则

每 subagent 任务必须**分 8-15 次 tool call**，单次 Edit ≤ 400 行 patch。单次 Write 超过 500 行或 Edit 超过 400 行视为违规。

### 5.2 标准 11 步 tool call 时序（subagent prompt 模板固化）

```
1. Read 骨架文件（确认 baseline · 1 call）
2. Read 质量标杆 L2-02 §1+§3（学风格 · 1 call）
3. Read 上游 prd §X.X + architecture.md（并行 2-3 call）
4. Read L0/ddd-context-map.md + L0/open-source-research.md（并行 2 call）
5. Write 1 · 补 frontmatter + §0 撰写进度 + §1 框架（≤ 200 行）
6. Edit 2 · §1 精确映射表 + 关键决策 D-XX（≤ 300 行）
7. Edit 3 · §3 字段级 YAML schema 上半（≤ 400 行）
8. Edit 4 · §3 错误码表 + §4 依赖（≤ 400 行）
9. Edit 5 · §5 PlantUML 时序 2 张 + §6 Python-like 伪代码（≤ 400 行）
10. Edit 6 · §7 schema + §8 状态机 + §9 开源 3+ 项（≤ 400 行）
11. Edit 7 · §10 配置 + §11 降级 + §12 SLO + §13 映射表（≤ 400 行）
12. Bash 验证（wc -l / grep mermaid / grep "<!-- FILL"）
13. 交付简报 ≤ 150 字
```

**精简粒度 B 的 subagent 省去 step 9-11，固化 6-8 步**。

### 5.3 subagent prompt 标准模板（含变量槽位）

```
任务：把 `<骨架路径>` 从 130 行骨架填成 <目标行数> L2 tech-design。

**必读参考（按优先级 · 强制 Read）**：
1. 质量标杆：`<L2-02 标杆路径>` §1+§3（学风格）
2. 产品 PRD：`<prd 路径>` §<X.X> <L2-XX 名称>
3. L1 架构：`<architecture 路径>`
4. L0 支撑：`L0/ddd-context-map.md`（BC-XX）+ `L0/open-source-research.md`
5. integration 契约：`docs/3-1-Solution-Technical/integration/ic-contracts.md`

**本 L2 定位**：<一句话 · 由主 session 调度时填>

**填写顺序（严格）**：§1 → §3 → §4 → §2 → §5 → §6 → §7 → §8 → §9 → §10 → §11 → §12 → §13

**硬约束**：
- 图一律 PlantUML（@startuml/@enduml）；禁止 Mermaid
- §3 字段级 YAML schema + 错误码表
- §5 ≥ 2 张 PlantUML 时序图
- §9 ≥ 3 个 GitHub ≥1k stars 项目对标
- §13 映射表 ↔ prd ↔ 3-2 TDD

**多回写**：按 §5.2 的 11 步时序（或精简 6-8 步）；单次 Edit ≤ 400 行

**交付**：简报 ≤ 150 字（总行数 / 各段填充状况 / PlantUML 图数 / 发现 PRD 串不起来反向修的地方）
```

## 6. 失败恢复链

```
subagent fail
  ├─ certificate error / socket closed  （启动期网络问题 · 概率 ~30%）
  ├─ 600s watchdog（未按多回写规范 · 应通过 §5 避免）
  └─ tool error（Edit old_string not unique 等）
        ↓
主 session 拉 output file 诊断（不读完整 JSONL · 只看 summary 字段）
        ↓
检查骨架是否有部分产出可用
  ├─ 有部分产出 → 保留 · 主 session 补齐剩余
  └─ 无产出 → 重发同一 prompt 1 次
        ├─ 第 2 次仍失败 → **降级主 session 自写该份**（保质量）
        └─ 成功 → 合并进度
```

**硬规则**：
- 单份 subagent 失败不重试 ≥ 2 次（避免 retry storm 浪费 token）
- 任何 subagent 失败后**立即 commit 已完成的其他并发份**（防丢）
- 失败份归档到 `docs/3-solution-resume-status.md` 的 "failed & escalated" 表

## 7. 质量 Gate（每 Phase 结束强制）

### 7.1 自动化 Gate 脚本

```bash
# scripts/quality_gate.sh
#!/usr/bin/env bash
set -euo pipefail

BASE="docs/3-1-Solution-Technical docs/3-2-Solution-TDD docs/3-3-Monitoring-Controlling"

echo "=== Gate 1: Mermaid 残留（硬约束：0）==="
m=$(grep -rc '```mermaid' $BASE 2>/dev/null | grep -v ':0$' || true)
[ -z "$m" ] && echo "PASS: 0 Mermaid 残留" || { echo "FAIL: $m"; exit 1; }

echo "=== Gate 2: 未填段 <!-- FILL 残留（硬约束：0）==="
f=$(grep -rc '<!-- FILL' $BASE 2>/dev/null | grep -v ':0$' || true)
[ -z "$f" ] && echo "PASS: 0 未填段" || { echo "FAIL: $f"; exit 1; }

echo "=== Gate 3: 占位残留（硬约束：0 · 注：Gate 脚本自己的 pattern 字符串需用另一种拼法避免自误报）==="
# 用拼接避免 grep 自匹配本行
t=$(grep -rc 'T''BD\|T''O''DO\|待''填' $BASE 2>/dev/null | grep -v ':0$' || true)
[ -z "$t" ] && echo "PASS: 0 占位" || { echo "FAIL: $t"; exit 1; }

echo "=== Gate 4: IC 交叉引用完整性 ==="
for f in $(find $BASE -name "L2-*.md"); do
  if ! grep -q 'IC-' "$f"; then
    echo "WARN: $f 无 IC-XX 引用"
  fi
done

echo "=== Gate 5: PlantUML 语法 lint（可选 · 若 plantuml CLI 可用）==="
command -v plantuml &>/dev/null && find $BASE -name "*.md" -exec plantuml -checkonly {} \; || echo "SKIP: plantuml CLI 未装"

echo "=== Gate 通过 · 可 git commit ==="
```

### 7.2 Gate 失败处理

Gate 硬失败（G1/G2/G3）→ 立即 block git commit → 主 session 定位问题 → 原地 fix → 再跑 Gate。

### 7.3 每 Phase 结束动作

1. 跑 Gate 脚本
2. `git add -A` · `git commit -m "feat(harnessFlow): Phase R{N} · {desc}"`
3. `git push`
4. 更新 `docs/3-solution-resume-status.md`（§8）
5. 向用户报告里程碑达成（M1/M2/...）

## 8. 跨 session 恢复机制

### 8.1 Resume 状态文件

**路径**：`docs/3-solution-resume-status.md`

**结构**：

```markdown
---
doc_id: resume-status
last_updated: <ISO-8601>
current_phase: R<N>
next_action: <一句话>
---

# 3-Solution Resume Status

## Phase 完成状态

| Phase | Status | Completed At | Commit |
|---|---|---|---|
| R0 Mermaid 迁移 | ✓/⚠/○ | <ts> | <hash> |
| R1 integration 契约 | ○ | — | — |
| ...

## 已完成 L2 清单

- docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md（深度 A · 563 行 · 质量标杆）
- ...

## Failed & Escalated（需主 session 补救）

- <file>（失败原因 / 重试次数 / 降级策略）

## 下次会话 Action Items

1. <具体动作>
2. <具体动作>
```

### 8.2 Resume 触发条件

- 单次会话到 context 85% 阈值 → 主动 commit + 更新 status + save-session skill + 告知用户"建议开新会话继续"
- 用户主动 /clear 或开新会话 → 读 status → 跳 current_phase
- 系统 API 大面积失败 → save-session → status 记录 + 等待恢复

## 9. 里程碑 M1-M6（消费单元 · 契合"真完成"原则）

| M | 达成 Phase | 交付物 | 可消费场景 |
|---|---|---|---|
| **M1** | R0+R1 后 | Mermaid→PlantUML 全转 + integration 4 份（含 10 条 IC 字段级契约）| 利益相关人看跨 L2 接口 + 架构师做 IC 评审 |
| **M2** | R2 后 | L1-01 主 Agent 决策循环全链（6 L2 深度 + 标杆）| 主 loop 的工程师可直接开工 TDD |
| **M3** | R3 后 | L1-01/04/07 三大核心 L1 全链（19 L2 深度）| 系统骨架可跑 · 其余 L1 的工程师可参照模板开工 |
| **M4** | R4 后 | 57 L2 全铺（19 深度 + 38 精简）| 完整 3-1 Technical 可消费 |
| **M5** | R5 后 | 3-2 TDD 75 份 · 与 3-1 1:1 镜像 | 可入 4-Execution TDD 驱动开发 |
| **M6** | R7 后 | 3-3 监督 10 份 + 质量 Gate 全绿 + 一致性审计通过 | 162 份文档**可交付** · 关闭本次 3-Solution ticket |

**每 M 独立可消费**：即使在 M3 之后暂停，M3 就是一个真完成里程碑（系统骨架 + 核心 19 L2 可跑）。

## 10. 与 v1.0 的 diff 总览

| 维度 | v1.0 | v2.0 |
|---|---|---|
| 图形式 | Mermaid | **PlantUML（@startuml/@enduml）** |
| 粒度 | 全量 B+ 实现级（隐含 1000-1500 行/L2）| **分级 A/B**（核心 19 份深度 · 外围 38 份精简）|
| 推进顺序 | Phase 1-6 按层推 | **契约先行 R0-R7** |
| 执行策略 | subagent 6 批 × 10 并发（激进）| **关键路径主写 + 外围 subagent 并发 + 多回写**（稳健 + 质量）|
| 失败处理 | 未定义 | **显式失败恢复链 + 降级主 session 自写** |
| 质量 Gate | 未定义 | **自动化 Gate 脚本 + 6 项硬约束** |
| 跨 session | 未定义 | **resume-status.md + save-session skill** |
| 里程碑 | 未定义 | **M1-M6 消费单元（契合真完成原则）** |

## 11. 自审 checklist（Brainstorming skill step 7）

- [x] **Placeholder 扫描**：无 TBD/TODO/待填（全部以 "待做" 明示到具体 Phase）
- [x] **内部一致性**：Q1-Q4 决策与 §4 Phase 大图一致；§5 多回写规范与 §6 失败恢复衔接；§7 Gate 脚本与 §9 里程碑关联
- [x] **Scope 检查**：v2.0 仅定义"剩余推进策略" · 不改 v1.0 文件清单 · 适合单次 writing-plans 展开为实施计划
- [x] **歧义检查**：
  - "核心 L1" 精确定义 = L1-01/04/07（§3 Q1 · §4 Phase R2/R3）
  - "深度 A" 精确定义 = 1000-1500 行 + §1-§13 全段 · "精简 B" = 400-600 行 + 5 段硬必填（§3 Q1）
  - "多回写" 精确定义 = 8-15 tool call / 单 Edit ≤ 400 行（§5.1）
  - "质量锚点" 精确定义 = ic-contracts.md + L1-01 模板 6 份 + hard-redlines.md + dod-specs.md（§3 Q3 + §4 R1/R2/R6）

## 12. 与现有项目约束的对齐

- **PM-14 project_id as root**：v2.0 所有 L2 schema 必须按 `projects/<pid>/...` 分片存储（继承 v1.0）
- **Claude Skill 底座**：v2.0 所有技术方案仍以 Skill + hooks + jsonl 为实现底座（继承 v1.0 决策 #1）
- **全局 memory 约束**：
  - `feedback_diagrams_plantuml.md`（图一律 PlantUML）→ 强制遵循
  - `feedback_quality_over_speed.md`（质量最高不问直接选）→ 本 spec Q2/Q4 选 D/C 即质量最优
  - `feedback_real_completion.md`（真完成原则）→ 本 spec §9 M1-M6 里程碑设计
  - `feedback_prp_flow.md`（PRP 流程）→ 本 spec 完成后过渡 writing-plans skill

## 13. 下一步（Brainstorming skill step 9）

本 spec 批准后立即：

1. 主 session 跑 §7 Gate 脚本基线（记录当前 baseline）
2. 调用 **writing-plans skill** 生成 Phase R0-R7 的详细实施计划（含每 Phase 的 subagent prompt 变量槽位、主 session 动作步骤、Gate checkpoint 动作）
3. 按 plan 执行（implementing-plans skill）

---

*— 设计 spec v2.0 · user 已在 Brainstorming Phase 批准（Q1-Q4 + Section 1-4）· 进入 writing-plans Phase —*
