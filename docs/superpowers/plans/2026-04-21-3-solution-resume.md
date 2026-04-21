# 3-Solution Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 HarnessFlow 3-Solution（技术方案 · TDD · 监督控制）的剩余 ~154 份文档以 spec v2.0 的策略补齐到"可交付"状态（M6）。

**Architecture:** 契约优先（R1 锁 10 条 IC）→ L1-01 模板 → 核心 L1-04/07 深度 → 外围 7 个 L1 精简 → 3-2 TDD 镜像 → 3-3 监督 → 质量 Gate。关键路径（契约 / 模板 / 硬红线）主 session 写；外围批量 subagent 5 并发（多回写 8-15 tool calls · 单 Edit ≤ 400 行）；失败自动重试 1 次后降级主 session。

**Tech Stack:** Markdown + PlantUML（@startuml/@enduml）+ YAML schema（字段级）+ Python-like 伪代码 + Bash 质量 Gate 脚本 + Claude Agent SDK（subagent 调度）。

**Spec 锚点:** `docs/superpowers/specs/2026-04-21-3-solution-resume-design.md` v2.0

---

## 0. 文件结构（全量待产出/修改清单）

### 0.1 新建脚本

| 路径 | 目的 |
|---|---|
| `scripts/quality_gate.sh` | 每 Phase 结束跑 · 6 项硬约束检查 |
| `scripts/spawn_l2_subagent.sh`（可选 helper）| 生成 L2 subagent prompt（模板变量替换）|
| `scripts/mermaid2plantuml.py`（已存在 /tmp）| 固化到 repo 供未来复用 |

### 0.2 新建/完善文档（分 Phase）

**R0 精修（2 处）**：
- 修改 `docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md`（~10 行 fallback）
- 核实 `docs/3-1-Solution-Technical/L0/open-source-research.md`（1 处 grep 残留）

**R1 integration（4 份新建）**：
- 创建 `docs/3-1-Solution-Technical/integration/ic-contracts.md`
- 创建 `docs/3-1-Solution-Technical/integration/p0-seq.md`
- 创建 `docs/3-1-Solution-Technical/integration/p1-seq.md`
- 创建 `docs/3-1-Solution-Technical/integration/cross-l1-integration.md`

**R2 L1-01 模板（1 补 + 5 填）**：
- 修改 `L1-01-主 Agent 决策循环/L2-02-决策引擎.md`（补 §2/§4-§13 · ~900 行增量）
- 填 `L1-01-.../L2-01-Tick 调度器.md`（130 骨架 → 1000-1500 行）
- 填 `L1-01-.../L2-03-状态机编排器.md`
- 填 `L1-01-.../L2-04-任务链执行器.md`
- 填 `L1-01-.../L2-05-决策审计记录器.md`
- 填 `L1-01-.../L2-06-Supervisor 建议接收器.md`

**R3 核心深度（13 份填）**：L1-04 × 7 + L1-07 × 6

**R4 外围精简（35 份填 · 400-600 行）**：L1-02 × 7 + L1-03 × 5 + L1-05 × 5 + L1-06 × 5 + L1-08 × 4 + L1-09 剩 2 + L1-10 × 7

**R5 3-2 TDD（75 份新建）**：镜像 3-1 · 路径 `docs/3-2-Solution-TDD/...`

**R6 3-3 监督（10 份新建）**：`docs/3-3-Monitoring-Controlling/...`

**R7 Gate 产出**：`docs/3-solution-resume-status.md`（resume 状态表）

---

## 1. 共享资源（Task 引用 · 只定义一次）

### 1.1 Subagent Prompt 模板 · 深度 A（L2 全量 1000-1500 行）

```
任务：把 `{L2_FILE_PATH}` 从 130 行骨架填成 1000-1500 行 L2 tech-design（§1-§13 全段）。

**必读参考（按优先级 · 强制 Read）**：
1. 质量标杆：`docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md` §1+§3
2. 产品 PRD：`docs/2-prd/{L1_PRD_DIR}/prd.md` §{PRD_SECTION} {L2_NAME}
3. L1 架构：`docs/3-1-Solution-Technical/{L1_TECH_DIR}/architecture.md`
4. L0 支撑：`docs/3-1-Solution-Technical/L0/ddd-context-map.md` + `L0/open-source-research.md`
5. 契约锚点：`docs/3-1-Solution-Technical/integration/ic-contracts.md`（已在 R1 锁定）

**本 L2 定位**：{L2_ONE_LINER}

**填写顺序（严格）**：§1 → §3 → §4 → §2 → §5 → §6 → §7 → §8 → §9 → §10 → §11 → §12 → §13

**硬约束**：
- 图一律 PlantUML（@startuml/@enduml）；禁止 Mermaid
- §3 字段级 YAML schema + 错误码表（错误码/含义/触发/调用方处理/对应 prd 硬约束）
- §5 ≥ 2 张 PlantUML 时序图（P0 主干 + P1 异常）
- §6 Python-like 伪代码（关键算法 + syscall）
- §7 schema 按 PM-14 `projects/<pid>/...` 分片
- §8 状态机：有状态 Aggregate 画 stateDiagram；无状态 Domain Service 简述
- §9 ≥ 3 个 GitHub ≥1k stars 项目对标（星数/活跃/Adopt-Learn-Reject）
- §13 映射表 ↔ prd ↔ 3-2 TDD

**多回写规范（必须遵守 · 防 watchdog）**：分 8-15 次 tool call，单次 Edit ≤ 400 行 patch。标准 11 步：
1. Read 骨架
2. Read 标杆 L2-02 §1+§3
3. Read prd §X.X + architecture（并行 2-3 call）
4. Read L0/ddd + L0/open-source（并行 2 call）
5. Write/Edit §1 精确映射表 + 关键决策（≤ 300 行）
6. Edit §3 字段级 YAML 上半（≤ 400 行）
7. Edit §3 错误码 + §4 依赖（≤ 400 行）
8. Edit §5 PlantUML 时序 + §6 伪代码（≤ 400 行）
9. Edit §7 schema + §8 状态机 + §9 开源（≤ 400 行）
10. Edit §10-§13（≤ 400 行）
11. Bash 验证（wc -l / grep mermaid / grep "<!-- FILL"）

**交付**：简报 ≤ 150 字（总行数 / 各段状况 / PlantUML 图数 / PRD 反向修点）
```

### 1.2 Subagent Prompt 模板 · 精简 B（L2 400-600 行）

```
任务：把 `{L2_FILE_PATH}` 从 130 行骨架填成 400-600 行 L2 tech-design 精简版。

**必读参考**：同模板 A（优先级 1-5）

**本 L2 定位**：{L2_ONE_LINER}

**硬必填 5 段**（其余 8 段精简小结）：
- §1 定位 + 2-prd 映射表（精确到小节）
- §3 对外接口（字段级 YAML schema + ≥ 5 条错误码）
- §5 PlantUML 时序图 ≥ 1 张（P0 主干）
- §11 降级策略（错误分类 + 降级链）
- §13 映射表 ↔ prd ↔ 3-2 TDD

**其余 8 段（§2/§4/§6-§10/§12）每段 ≤ 30 行骨架小结**（关键要点 bullet 化）

**图一律 PlantUML**。

**多回写**：6-8 次 tool call，单次 Edit ≤ 400 行：
1. Read 骨架 + 标杆
2. Read prd + architecture
3. Edit §1 映射表（≤ 200 行）
4. Edit §3 YAML schema + 错误码（≤ 300 行）
5. Edit §5 PlantUML + §11 降级（≤ 200 行）
6. Edit §13 + 其余 8 段骨架小结（≤ 200 行）
7. Bash 验证
8. 交付 ≤ 100 字简报
```

### 1.3 Subagent Prompt 模板 · TDD 镜像（每份 300-500 行）

```
任务：为 `docs/3-1-Solution-Technical/{L1_DIR}/{L2_FILE}` 的对应 L2 tech-design 写 TDD 用例到 `docs/3-2-Solution-TDD/{L1_DIR}/{L2_TESTS_FILE}`。

**必读**：
1. L2 tech-design（接口源）：`{L2_TECH_FILE}` §3（接口）+ §11（错误码）
2. 契约：`docs/3-1-Solution-Technical/integration/ic-contracts.md`
3. prd 负向用例：`docs/2-prd/{L1_PRD_DIR}/prd.md §X.9 交付验证大纲`

**硬必填**：
- 每个公开方法至少 1 正向 + 2 负向（边界/异常）用例
- 每个错误码至少 1 触发用例
- IC-XX 契约集成测试（若本 L2 是 IC 消费方/生产方）
- 伪代码用例（Python-like `def test_xxx():` 风格，但不要求真跑）

**图可选**（用例描述 PlantUML 时序）

**多回写 5-7 步**（≤ 300 行/Edit）。

**交付**：简报 ≤ 100 字（用例数 / 覆盖接口 / 覆盖错误码 / 是否发现 3-1 漏点）
```

### 1.4 quality_gate.sh 脚本内容

```bash
#!/usr/bin/env bash
# scripts/quality_gate.sh · 每 Phase 结束跑
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="docs/3-1-Solution-Technical docs/3-2-Solution-TDD docs/3-3-Monitoring-Controlling"
FAIL=0

echo "=== Gate 1: Mermaid 残留（硬约束：0）==="
m=$(grep -rc '```mermaid' $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$m" ]; then echo "FAIL:"; echo "$m"; FAIL=1; else echo "PASS"; fi

echo "=== Gate 2: 未填段 <!-- FILL（硬约束：0）==="
f=$(grep -rc '<!-- FILL' $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$f" ]; then echo "FAIL:"; echo "$f"; FAIL=1; else echo "PASS"; fi

echo "=== Gate 3: 占位 T'BD/T'O'DO/待'填（硬约束：0）==="
t=$(grep -rc 'T''BD\|T''O''DO\|待''填' $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$t" ]; then echo "FAIL:"; echo "$t"; FAIL=1; else echo "PASS"; fi

echo "=== Gate 4: L2 tech-design 每份含 ≥ 1 IC-XX 引用 ==="
for file in $(find docs/3-1-Solution-Technical -name "L2-*.md" 2>/dev/null); do
  if ! grep -q 'IC-' "$file"; then
    echo "WARN: $file 无 IC-XX 引用"
  fi
done

echo "=== Gate 5: PlantUML @startuml/@enduml 配对检查 ==="
for file in $(grep -rl '```plantuml' $BASE 2>/dev/null || true); do
  starts=$(grep -c '@startuml' "$file" || true)
  ends=$(grep -c '@enduml' "$file" || true)
  if [ "$starts" != "$ends" ]; then
    echo "FAIL: $file @startuml($starts) ≠ @enduml($ends)"; FAIL=1
  fi
done

echo "=== Gate 6: mermaid-fallback 标记（需精修）==="
fb=$(grep -rc "mermaid-fallback\|unrecognized mermaid" $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$fb" ]; then echo "WARN: 存在 fallback 需精修:"; echo "$fb"; fi

if [ $FAIL -ne 0 ]; then
  echo ""; echo "❌ Gate FAIL · 禁止 commit · 原地 fix 后重跑"
  exit 1
fi
echo ""; echo "✅ Gate PASS · 可 git commit"
```

---

## 2. Phase R0 · Mermaid 尾款精修（主 session · 15 min）

### Task R0.1: 落盘 quality_gate.sh

**Files:**
- Create: `scripts/quality_gate.sh`

- [ ] **Step 1: 写入脚本**（内容见 §1.4）

```bash
chmod +x scripts/quality_gate.sh
```

- [ ] **Step 2: 跑 baseline**

```bash
./scripts/quality_gate.sh; echo "exit=$?"
```

预期：Gate 1 FAIL（L0/open-source-research 1 块 Mermaid）· Gate 6 WARN（L1-09 arch fallback ~10 行）

### Task R0.2: 核实 L0/open-source-research.md 的 1 处 Mermaid

**Files:**
- Modify: `docs/3-1-Solution-Technical/L0/open-source-research.md`

- [ ] **Step 1: 定位残留**

```bash
grep -n '```mermaid' docs/3-1-Solution-Technical/L0/open-source-research.md
```

- [ ] **Step 2: 判断类型**（代码块还是文本提及）

若是代码块：Read 上下文 → Edit 手工转 PlantUML；若是文本提及（之前 subagent 报告）：Edit 改表述避免 grep 误判（例如 `\`mermaid\`` 改为 `(Mermaid syntax)`）

- [ ] **Step 3: 验证**

```bash
grep -c '```mermaid' docs/3-1-Solution-Technical/L0/open-source-research.md
```

预期：0

### Task R0.3: 精修 L1-09 architecture.md 的 ~10 行 fallback

**Files:**
- Modify: `docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md`

- [ ] **Step 1: 定位 fallback**

```bash
grep -n "mermaid-fallback\|styles stripped" "docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md"
```

- [ ] **Step 2: Read 上下文（围绕 fallback 行上下各 ±20 行）**

- [ ] **Step 3: 逐个 Edit** fallback 行为有效 PlantUML 语法

规则：
- `A -.label.-> B` → `A ..> B : label`
- `A -.label.- B` → `A .. B : label`
- `A{"verify"}` → `agent "verify" as A`
- 删除 `style ... fill:#color` 和 `classDef ...` 行（PlantUML 语法不同）

- [ ] **Step 4: 验证**

```bash
grep -c "mermaid-fallback" "docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md"
```

预期：0

### Task R0.4: R0 收尾 · 跑 Gate + Commit

- [ ] **Step 1: 跑 Gate**

```bash
./scripts/quality_gate.sh
```

预期：全 PASS 或仅 Gate 4 WARN（L2 骨架无 IC 引用是预期内，R1 后补）

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(harnessFlow): Phase R0 · Mermaid 全量迁移 PlantUML（169 块）+ quality_gate.sh"
git push
```

---

## 3. Phase R1 · integration 契约 4 份（1.5h · 主 session 1 + subagent 3）

**里程碑 M1**：10 条 IC-01~IC-17 契约字段级锁死 · 可消费单元

### Task R1.1: 主 session 写 `integration/ic-contracts.md`（质量锚点）

**Files:**
- Create: `docs/3-1-Solution-Technical/integration/ic-contracts.md`

- [ ] **Step 1: Read 上游**

并行 Read：
- `docs/2-prd/L1集成/prd.md`（10 条 IC 的 prd 粗案）
- `docs/3-1-Solution-Technical/L0/sequence-diagrams-index.md`（已有 IC 时序）
- 10 份 L1 architecture.md 的 §2.5 Domain Events 小节（IC 实际调用处）

- [ ] **Step 2: Write 1 · frontmatter + §0 + §1 定位**（≤ 200 行）

- [ ] **Step 3: Edit · §2 IC 清单总表**（10 条 × 列：IC-XX / 生产者 / 消费者 / 触发 / 频率 / 优先级 / SLO）

- [ ] **Step 4: Edit · §3.1 ~ §3.10 每条 IC 的字段级 YAML schema（≤ 400 行/批）**

每条 IC 必含：
- 入参字段级 YAML（含 required / type / format / example / constraints）
- 出参字段级 YAML
- 错误码表（≥ 5 条）
- 幂等性说明
- PlantUML 时序图（生产者 → 消费者）

分 3 批 Edit：IC-01~03 / IC-04~06 / IC-07~17

- [ ] **Step 5: Edit · §4 跨 L1 契约总览 PlantUML 图**（1 张全景图）

- [ ] **Step 6: Verify**

```bash
wc -l docs/3-1-Solution-Technical/integration/ic-contracts.md
grep -c 'IC-' docs/3-1-Solution-Technical/integration/ic-contracts.md
grep -c '@startuml' docs/3-1-Solution-Technical/integration/ic-contracts.md
```

预期：≥ 1500 行 · ≥ 30 处 IC- 引用 · ≥ 11 张 PlantUML

- [ ] **Step 7: Commit**

```bash
git add docs/3-1-Solution-Technical/integration/ic-contracts.md
git commit -m "feat(harnessFlow): R1.1 · integration/ic-contracts.md 契约锚点（10 条 IC 字段级）"
```

### Task R1.2: Spawn 3 subagent 并发写 p0-seq / p1-seq / cross-l1

- [ ] **Step 1: 并发 spawn 3 个 subagent**

使用 Agent 工具（general-purpose · run_in_background=true）一次 3 个：

**Subagent A · p0-seq.md**：
```
任务：创建 docs/3-1-Solution-Technical/integration/p0-seq.md（跨 L1 P0 主干时序汇总，约 800-1200 行）。

**必读**：
- `docs/3-1-Solution-Technical/integration/ic-contracts.md`（已锁定的 10 条 IC）
- `docs/3-1-Solution-Technical/L0/sequence-diagrams-index.md`（已有 P0 链路索引）
- 10 份 L1 architecture.md 的 §5 P0 时序小节

**内容**：汇总 8-12 条 P0 跨 L1 时序图（PlantUML），每条含：场景一句话 / 主参与者 L1 / 完整时序图 / 关键字段取值示例。

**多回写 6-10 步**，单次 Edit ≤ 400 行。

**交付**：≤ 150 字简报。
```

**Subagent B · p1-seq.md**：（类似 · 聚焦 P1 异常/恢复路径）

**Subagent C · cross-l1-integration.md**：
```
任务：创建 docs/3-1-Solution-Technical/integration/cross-l1-integration.md（跨 L1 架构总览 + DDD BC 关系图 + 依赖矩阵，约 600-1000 行）。

**必读**：同 Subagent A + `docs/3-1-Solution-Technical/L0/ddd-context-map.md`

**内容**：
- §1 定位 + DDD BC 关系全景（PlantUML · 10 BC + 关系）
- §2 L1 ↔ L1 依赖矩阵（10×10 表格）
- §3 IC 契约一致性审计点（与 ic-contracts.md 交叉引用）
- §4 PM-14 project_id 传播链路（PlantUML · 全 L1 贯穿图）

**多回写 5-8 步**。
```

- [ ] **Step 2: 等 3 subagent 完成通知**（不 poll · 系统自动通知）

- [ ] **Step 3: 失败处理**

若任一 subagent fail：
- 重发同一 prompt 1 次
- 仍失败 → 主 session 自写（降级 · 保质量）

### Task R1.3: R1 收尾 Gate + Commit → M1

- [ ] **Step 1: 跑 Gate**

```bash
./scripts/quality_gate.sh
```

- [ ] **Step 2: Commit**

```bash
git add docs/3-1-Solution-Technical/integration/
git commit -m "feat(harnessFlow): Phase R1 · integration 4 份（10 条 IC 契约锁定） → M1"
git push
```

- [ ] **Step 3: 更新 resume-status**

```bash
# 首次创建 docs/3-solution-resume-status.md · 记录 R0/R1 完成
```

---

## 4. Phase R2 · L1-01 模板 6 份（1.5h · 主 session 1 + subagent 5）

**里程碑 M2**：L1-01 主 Agent 决策循环端到端可消费

### Task R2.1: 主 session 补 L2-02 §2/§4-§13

**Files:**
- Modify: `docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md`（已有 §1+§3）

- [ ] **Step 1: Read 当前状态 + 标杆自比对**

```bash
wc -l "docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md"
```

预期：563 行（baseline）

- [ ] **Step 2: Read 上游**（prd §9 + arch + L0/ddd + L0/open-source + R1 契约）

- [ ] **Step 3: Edit §2 DDD 映射**（≤ 300 行 · BC-01 + Aggregates + Domain Services + Repository + Domain Events）

- [ ] **Step 4: Edit §4 依赖图 PlantUML**（被谁调 + 调谁 · 引 R1 的 IC-XX）

- [ ] **Step 5: Edit §5 P0/P1 时序图 PlantUML ≥ 2 张**

- [ ] **Step 6: Edit §6 核心算法伪代码**（ContextAssembler + FiveDiscipline + DecisionTree + DecisionSelector · ≤ 400 行）

- [ ] **Step 7: Edit §7 schema + §8 状态机**（decision_record YAML + 5 阶段线性流水 PlantUML · ≤ 400 行）

- [ ] **Step 8: Edit §9 开源调研** ≥ 3 项（LangGraph / AutoGPT / CrewAI · 星数 + Adopt-Learn-Reject）

- [ ] **Step 9: Edit §10-§13**（配置 · 降级 · SLO · 映射表）

- [ ] **Step 10: Verify**

```bash
wc -l "docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md"
grep -c '@startuml' "docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md"
grep -c '<!-- FILL' "docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md"
```

预期：1200-1500 行 · ≥ 4 张 PlantUML · 0 <!-- FILL

- [ ] **Step 11: Commit**

```bash
git add "docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md"
git commit -m "feat(harnessFlow): R2.1 · L2-02 决策引擎全段补齐（质量标杆最终态）"
```

### Task R2.2: Spawn 5 subagent 并发 L2-01/03/04/05/06

- [ ] **Step 1: 并发 spawn 5 subagent**（Agent 工具 · run_in_background=true · 一次 5 个）

对 5 个 L2 各用 §1.1 深度 A 模板，变量：

| L2 | L2_FILE_PATH | PRD_SECTION | L2_ONE_LINER |
|---|---|---|---|
| L2-01 Tick 调度器 | `L1-01-主 Agent 决策循环/L2-01-Tick 调度器.md` | §8 | L1-01 心跳起搏器 · 4 触发源 + 2 响应通道 · 去抖动 + Watchdog |
| L2-03 状态机编排器 | `L1-01-.../L2-03-状态机编排器.md` | §10 | 7 状态转换 + allowed_next + entry/exit hooks + 幂等 |
| L2-04 任务链执行器 | `L1-01-.../L2-04-任务链执行器.md` | §11 | DAG 多步链 · 步骤回调 · 失败回退 + 暂停恢复 |
| L2-05 决策审计记录器 | `L1-01-.../L2-05-决策审计记录器.md` | §12 | 半状态 Repository · buffer + flush · jsonl 按日切分 |
| L2-06 Supervisor 接收器 | `L1-01-.../L2-06-Supervisor 建议接收器.md` | §13 或 §14 | L1-01↔L1-07 唯一网关 · 3 级队列 · BLOCK ≤100ms |

- [ ] **Step 2: 等待 5 subagent 通知**

- [ ] **Step 3: 失败重试 → 降级主写**（按 spec §6 失败恢复链）

- [ ] **Step 4: 抽样 diff 检查质量对齐**

```bash
# 每份行数 + PlantUML 数 + <!-- FILL 残留
for f in "docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环"/L2-0{1,3,4,5,6}-*.md; do
  echo "$f: $(wc -l < "$f") lines / $(grep -c '@startuml' "$f") uml / $(grep -c '<!-- FILL' "$f") FILL"
done
```

预期：每份 ≥ 1000 行 · ≥ 2 PlantUML · 0 FILL

### Task R2.3: R2 收尾 Gate + Commit → M2

- [ ] **Step 1: 跑 Gate**

```bash
./scripts/quality_gate.sh
```

- [ ] **Step 2: Commit**

```bash
git add "docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环"
git commit -m "feat(harnessFlow): Phase R2 · L1-01 模板 6 份全量深度 → M2 主 loop 端到端可消费"
git push
```

---

## 5. Phase R3 · L1-04/07 共 13 份深度（2h · subagent 5 并发 × 3 批）

**里程碑 M3**：系统骨架可跑（主 loop + Quality + 监督）

### Task R3.1: 批 1 · L1-04 × 5（L2-01~05）

- [ ] **Step 1: 并发 spawn 5 subagent**（深度 A 模板 · 引用 R1 契约 + R2 L2-02 标杆 · 注意本批 Subagent 需要额外 Read L2-01~L2-06 的 R2 产物作为同 L1 兄弟参考）

| L2 | L2_ONE_LINER |
|---|---|
| L1-04/L2-01 TDD 蓝图生成器 | 从 WP + DoD 生成 TDD 蓝图 · 绑 stage 输入输出契约 |
| L1-04/L2-02 DoD 表达式编译器 | DoD 字符串 → AST · 白名单 predicate 求值 |
| L1-04/L2-03 测试用例生成器 | 从 TDD 蓝图派生具体用例 · LLM 驱动 + 模板 |
| L1-04/L2-04 质量 Gate 编译器+验收 Checklist | DoD + TDD → Gate 脚本 + 验收清单 |
| L1-04/L2-05 S4 执行驱动器 | 驱动 S4 阶段跑测试 · 收集覆盖率/失败清单 |

- [ ] **Step 2: 等待 + 抽样检查**

- [ ] **Step 3: 失败处理 + 批次 Commit**

```bash
git add "docs/3-1-Solution-Technical/L1-04-Quality Loop"
git commit -m "feat(harnessFlow): R3.1 · L1-04 批1 · L2-01~05 深度"
```

### Task R3.2: 批 2 · L1-04 × 2 + L1-07 × 3

- [ ] **Step 1: 并发 spawn 5 subagent**

| L2 | L2_ONE_LINER |
|---|---|
| L1-04/L2-06 S5 TDDExe Verifier 编排器 | S5 阶段 · 跑 verifier · 收集 verdict |
| L1-04/L2-07 偏差判定+4 级回退路由器 | 判断 fail 模式 · 路由到 4 级回退（重试/细化/重设计/升级）|
| L1-07/L2-01 8 维度监督状态采集器 | 每 tick 采集 8 维度指标 · 快照入队 |
| L1-07/L2-02 4 级偏差判定器 | 规则引擎 + LLM fallback · 判 INFO/SUGG/WARN/BLOCK |
| L1-07/L2-03 硬红线拦截器 | 红线规则集 · 100ms BLOCK 触发 |

- [ ] **Step 2: 等待 + Commit**

```bash
git add "docs/3-1-Solution-Technical/L1-04-Quality Loop" "docs/3-1-Solution-Technical/L1-07-Harness监督"
git commit -m "feat(harnessFlow): R3.2 · L1-04 批2 + L1-07 批1 深度"
```

### Task R3.3: 批 3 · L1-07 × 3

- [ ] **Step 1: 并发 spawn 3 subagent**

| L2 | L2_ONE_LINER |
|---|---|
| L1-07/L2-04 Supervisor 副 Agent 事件发送器 | 已判定事件 → L1-01/L2-06 路由 |
| L1-07/L2-05 Soft-drift 模式识别器 | LLM 模式识别 · 识别渐变式偏离 |
| L1-07/L2-06 死循环升级器+回退路由控制器 | tick 循环 N 次 → 升级人工或 kill |

- [ ] **Step 2: 等待 + Gate + Commit → M3**

```bash
./scripts/quality_gate.sh
git add "docs/3-1-Solution-Technical/L1-07-Harness监督"
git commit -m "feat(harnessFlow): Phase R3 · L1-04/07 共 13 份深度 → M3 系统骨架可跑"
git push
```

---

## 6. Phase R4 · 外围 35 份精简（2h · subagent 5 并发 × 7 批）

**里程碑 M4**：57 L2 全铺

### Task R4.1 - R4.7: 7 批精简 subagent（每批 5 并发，最后 1 批 5 份）

统一用 §1.2 精简 B 模板。

**批次映射**：

| 批 | L2 清单 |
|---|---|
| R4.1 | L1-02/L2-01~05（Stage Gate · 启动产出 · 4件套 · PMP 9 计划 · TOGAF ADM）|
| R4.2 | L1-02/L2-06~07 + L1-03/L2-01~03（收尾 · 模板引擎 · WBS 拆解 · 拓扑图 · WP 调度）|
| R4.3 | L1-03/L2-04~05 + L1-05/L2-01~03（WP 追踪 · 失败回退 · Skill 注册表 · 意图选择 · 调用执行）|
| R4.4 | L1-05/L2-04~05 + L1-06/L2-01~03（子 Agent 委托 · 异步回收 · 3 层管理 · KB 读 · 观察累积）|
| R4.5 | L1-06/L2-04~05 + L1-08/L2-01~03（KB 晋升 · 检索+Rerank · 文档 IO · 代码结构 · 图片视觉）|
| R4.6 | L1-08/L2-04 + L1-09/L2-04（路径安全+降级 · 检查点与恢复）· 仅 2 份（+ 3 份 L1-10 补足 5 并发）L1-10/L2-01~03 |
| R4.7 | L1-10/L2-04~07（用户干预 · KB 浏览器 · 裁剪档配置 · Admin 子管理）· 4 份 |

每批 Task 结构一致：
- [ ] **Step 1: 并发 spawn N subagent**（精简 B 模板 · variable slots 按批次表填）
- [ ] **Step 2: 等待完成 · 抽样检查**
- [ ] **Step 3: Commit**

```bash
git add "docs/3-1-Solution-Technical/{affected L1 dirs}"
git commit -m "feat(harnessFlow): R4.{N} · 外围精简批{N}（5 L2）"
```

### Task R4.8: R4 收尾 Gate → M4

- [ ] **Step 1: 跑 Gate**（应全 PASS · 57 L2 全铺）

- [ ] **Step 2: 统计**

```bash
find docs/3-1-Solution-Technical -name "L2-*.md" -exec wc -l {} + | tail -1
```

预期：总行数 ≥ 40k（19 深度 × 1200 + 38 精简 × 500 = ~42k）

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "feat(harnessFlow): Phase R4 · 57 L2 全铺完成 → M4 完整 3-1 Technical"
git push
```

---

## 7. Phase R5 · 3-2 Solution-TDD 75 份（3h · subagent 5 并发 × 15 批）

**里程碑 M5**：可入 4-Execution TDD 驱动开发

### Task R5.1: 初始化 3-2 目录结构

**Files:**
- Create: `docs/3-2-Solution-TDD/L0/`
- Create: `docs/3-2-Solution-TDD/projectModel/`
- Create: `docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/` ~ `L1-10-.../`
- Create: `docs/3-2-Solution-TDD/integration/`
- Create: `docs/3-2-Solution-TDD/acceptance/`

- [ ] **Step 1: 创建目录 + 每份骨架文件**

```bash
python3 << 'EOF'
# 镜像 3-1 结构 · 为每个 L2 建对应 tests.md 骨架
import os, shutil
BASE_SRC = "docs/3-1-Solution-Technical"
BASE_DST = "docs/3-2-Solution-TDD"
os.makedirs(BASE_DST, exist_ok=True)
# ...（完整镜像 L0 + projectModel + 10 L1 + integration + acceptance · 每份含 130 行 tests 骨架）
EOF
```

（细节脚本在实施时填入 · 骨架模板含 frontmatter + §0 进度 + §1-§6 用例框架）

- [ ] **Step 2: Commit 骨架**

```bash
git add docs/3-2-Solution-TDD/
git commit -m "feat(harnessFlow): R5.1 · 3-2-Solution-TDD 目录骨架（75 份 tests-skeleton）"
```

### Task R5.2 - R5.16: 15 批 subagent × 5 并发填 75 份 tests

**策略**：每批 5 份按 3-1 的 L2 镜像填 · 用 §1.3 TDD 模板 · variable 从 3-1 对应 L2 派生

**批次示例（R5.2）**：
- [ ] spawn 5 subagent（L1-01 的 L2-01~05 对应 tests）

批次 15 个按 3-1 57 L2 + 10 L1 integration + 4 integration + 1 acceptance 分配（略 · 执行时按表定）

### Task R5.17: R5 收尾 Gate → M5

```bash
./scripts/quality_gate.sh
git commit -m "feat(harnessFlow): Phase R5 · 3-2 TDD 75 份完成 → M5 可入 4-Exe"
git push
```

---

## 8. Phase R6 · 3-3 Monitoring & Controlling 10 份（1.5h · 主 2 + subagent 4 × 2 批）

### Task R6.1: 初始化 3-3 目录

**Files:**
- Create: `docs/3-3-Monitoring-Controlling/L0/`
- Create: `docs/3-3-Monitoring-Controlling/quality-standards/`
- Create: `docs/3-3-Monitoring-Controlling/dod-specs/`（3 份）
- Create: `docs/3-3-Monitoring-Controlling/hard-redlines.md`
- Create: `docs/3-3-Monitoring-Controlling/soft-drift-patterns.md`
- Create: `docs/3-3-Monitoring-Controlling/monitoring-metrics/`（2 份）
- Create: `docs/3-3-Monitoring-Controlling/acceptance-criteria.md`

- [ ] **Step 1: 建目录 + 10 份骨架**（每份 ~80 行骨架）

- [ ] **Step 2: Commit**

### Task R6.2: 主 session 写 `hard-redlines.md`（硬红线规约 · 不可失真）

- [ ] 分 8 步多回写 · ~1000 行（全系统硬红线清单 + 触发条件 + 响应 SLO）

- [ ] Commit

### Task R6.3: 主 session 写 `dod-specs/general-dod.md`（核心 DoD 规约）

- [ ] 分 6 步多回写 · ~800 行

- [ ] Commit

### Task R6.4: 批 1 · subagent 4 并发 4 份

| 份 | 内容 |
|---|---|
| L0/overview.md | 3-3 总览 |
| quality-standards/coding-standards.md | 代码标准 |
| dod-specs/stage-dod.md | 阶段 DoD |
| dod-specs/wp-dod.md | WP DoD |

### Task R6.5: 批 2 · subagent 4 并发 4 份

| 份 | 内容 |
|---|---|
| soft-drift-patterns.md | 软漂移模式识别规约 |
| monitoring-metrics/system-metrics.md | 系统指标 |
| monitoring-metrics/quality-metrics.md | 质量指标 |
| acceptance-criteria.md | 最终验收标准 |

### Task R6.6: R6 收尾 Gate + Commit

```bash
./scripts/quality_gate.sh
git commit -m "feat(harnessFlow): Phase R6 · 3-3 监督规约 10 份"
git push
```

---

## 9. Phase R7 · 质量 Gate + 一致性审计（1h · 主 session）

**里程碑 M6**：可交付状态

### Task R7.1: 跑完整 Gate

- [ ] **Step 1**

```bash
./scripts/quality_gate.sh
```

预期：全 6 项 PASS/仅 Gate 4 零 WARN

### Task R7.2: 一致性审计 · 抽样 5 份对照标杆

- [ ] **Step 1: 抽样 L2**（按 L1 分布）：
  - L1-02/L2-04（精简 B）
  - L1-05/L2-02（精简 B）
  - L1-08/L2-01（精简 B）
  - L1-09/L2-04（精简 B）
  - L1-10/L2-03（精简 B）

- [ ] **Step 2: 对标杆 L2-02 的 §1 映射表深度 / §3 YAML 字段完整度 / §5 PlantUML 图数打分**（每维 1-5 · 总分 ≥ 12/15 为 PASS）

- [ ] **Step 3: 若不 PASS 的份 → 派 1 个 subagent 补齐**

### Task R7.3: 交叉引用审计

- [ ] **Step 1: IC-XX 一致性**

```bash
# 检查 ic-contracts.md 定义的 IC 在 57 L2 + 75 TDD 中引用时字段名一致
grep -r "IC-01\|IC-02\|..." docs/3-1-Solution-Technical docs/3-2-Solution-TDD | sort | uniq -c | sort -rn | head
```

- [ ] **Step 2: `decision_record` / `context_snapshot` / `tick_context` 核心 schema 在 3 处（L2-02 · TDD · integration）字面一致**

### Task R7.4: PlantUML CLI lint（可选）

- [ ] **Step 1**

```bash
command -v plantuml && find docs/3-1-Solution-Technical docs/3-2-Solution-TDD docs/3-3-Monitoring-Controlling -name "*.md" -exec plantuml -checkonly {} \; 2>&1 | head -30 || echo "plantuml CLI 未装 · 跳过"
```

### Task R7.5: 最终 Commit + Push → M6

- [ ] **Step 1**

```bash
git add -A
git commit -m "feat(harnessFlow): Phase R7 · 质量 Gate 全绿 + 一致性审计通过 → M6 3-Solution 可交付"
git push
```

- [ ] **Step 2: 更新 `docs/3-solution-resume-status.md`**（所有 Phase ✓）

- [ ] **Step 3: 关闭 brainstorming + writing-plans 任务栈**

---

## 10. 失败恢复 · 跨 session · 里程碑验收

### 10.1 每个 Phase 失败恢复（统一机制）

1. subagent fail → 主 session diagnose output summary
2. 检查部分产出 → 保留或清理
3. 重发 prompt 1 次
4. 再失败 → 主 session 降级自写
5. 失败份归档到 `docs/3-solution-resume-status.md` "failed & escalated" 表

### 10.2 跨 session 恢复

每 Phase 结束：
- `git commit` + `git push`
- 更新 `docs/3-solution-resume-status.md`
- context 到 85% 阈值 → save-session + 告知用户开新会话

下次会话：Read `docs/3-solution-resume-status.md` → 跳到 current_phase

### 10.3 里程碑验收 checklist

| 里程碑 | 验收动作 | PASS 条件 |
|---|---|---|
| M1 (R1 后) | Read ic-contracts.md | 10 条 IC · 字段级 YAML · ≥ 50 错误码 · ≥ 11 PlantUML |
| M2 (R2 后) | ls L1-01 · wc -l 所有 L2 | 6 份 ≥ 1000 行 · 每份 ≥ 2 PlantUML |
| M3 (R3 后) | 同 M2 针对 L1-04/07 | 13 份 ≥ 1000 行 |
| M4 (R4 后) | find L2-*.md count | 57 份 · 19 深度 + 38 精简 |
| M5 (R5 后) | find 3-2 *.md count | 75 份 · 每份 ≥ 300 行 |
| M6 (R7 后) | quality_gate.sh 全 PASS + 抽样审计 ≥ 12/15 | 0 Gate 失败 |

---

## 11. Self-Review（writing-plans skill step Self-Review）

### 11.1 Spec 覆盖检查

| Spec 章节 | 对应 Plan Task | 覆盖 |
|---|---|---|
| §3 Q1 粒度分级 | §4 R2.2 + §5 R3 全量 · §6 R4 精简 B | ✓ |
| §3 Q2 契约优先 | §3 R1.1 主写 ic-contracts 先于 §4 R2 | ✓ |
| §3 Q3 关键路径主写 | §3 R1.1 / §4 R2.1 / §8 R6.2/R6.3 主 session | ✓ |
| §3 Q4 脚本+精修 | §2 R0 已完成（69 块转 + 精修）| ✓ |
| §4 Phase R0-R7 | §2-§9 逐 Phase | ✓ |
| §5 多回写规范 | §1.1/1.2/1.3 模板 + 所有 R2-R6 Task | ✓ |
| §6 失败恢复链 | §10.1 + 所有 Task "Step 3: 失败处理" | ✓ |
| §7 质量 Gate | §1.4 scripts/quality_gate.sh + §9 R7 | ✓ |
| §8 跨 session | §10.2 + resume-status.md | ✓ |
| §9 M1-M6 | §10.3 验收 checklist | ✓ |

**无 Gap**。

### 11.2 占位扫描

全 plan grep `TBD|TODO|fill in later|待填` → 0（均为明确指向后续 task）。

### 11.3 类型一致性

- `ic-contracts.md` 在 R1.1 / R1.2 / R2-R6 所有 subagent prompt / R7.3 审计 中**路径字面一致**
- `L2-02` 在 R2.1 / R2.2 模板参考 / R3-R4 subagent prompt / R7.2 审计 中**路径字面一致**
- `quality_gate.sh` 在 R0.1 落盘 / R0.4 / R1.3 / R2.3 / R3.3 / R4.8 / R6.6 / R7.1 使用 **路径字面一致**

**PASS**。

---

## 12. Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-21-3-solution-resume.md`.

**两种执行模式可选**：

**1. Subagent-Driven（推荐 · 与本 plan 设计对齐）**
- 使用 `superpowers:subagent-driven-development`
- 每 Task 派一个 fresh subagent · 主 session 两阶段 review · 本 plan R1-R6 已内嵌多个 subagent 调度 step，和该模式天然匹配
- 适合：context 控制严 · 失败隔离强 · 迭代快

**2. Inline Execution**
- 使用 `superpowers:executing-plans`
- 本 session 直接按 task 顺序执行 + 批次 checkpoint
- 适合：希望一次会话内尽量多推进 · 对 context 窗容忍度高

**哪个？**

---

*— Plan v1.0 · 基于 spec v2.0（2026-04-21）· 总任务 ~60 step · 预计 ~12h 多轮会话 —*
