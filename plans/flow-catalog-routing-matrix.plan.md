# Plan: flow-catalog.md + routing-matrix.md

## Summary
Phase 3 双产出：(1) `flow-catalog.md` — A~F 六条编排路线的完整设计（每条含精神、定位、适用、skill 组合调度序列、优缺点、切换/降级条件、风险点）；(2) `routing-matrix.md` — 三维（体量 × 类型 × 风险）→ 路线推荐矩阵。两份文档把 method3.md § 4 的"路线精神"落实到可查表执行，并给主 skill（Phase 5）一份可 eval 的路由表。

## User Story
As a **主 skill（Phase 5 产出）**，
I want 在分诊完成后查一张矩阵立刻得到 top-2 推荐路线 + 查 flow-catalog 得到该路线的完整 skill 调度序列，
So that 路由决策变成"规则查表"（harnessFlow.md § 5.3 桥接 ④）而不是 LLM 黑盒推理。

## Problem → Solution
method3 § 4.1 只有 6 行路线精神表；harnessFlow.md § 5.3 桥接 ① 承诺"routing-matrix 版本化"但没内容；主 skill 需要的是"给我一个 (size, type, risk) 向量就能查到 [candidates, scores, reasons]"的可审计查表。→ 把 6 路线展开为完整调度设计（flow-catalog）+ 把路由决策规则化为矩阵（routing-matrix）。

## Metadata
- **Complexity**: Medium（两份文档 / 无代码 / 无测试套件）
- **Source PRD**: `/Users/zhongtianyi/work/code/harnessFlow /harness-flow.prd.md` Phase 3
- **Estimated Files**: 2（`flow-catalog.md` ~500 行 + `routing-matrix.md` ~300 行）
- **Target Size**: 合计 700-900 行

---

## UX Design

### Before
- method3 § 4.1 六条路线各 ≤15 字精神描述
- 无路由矩阵文件
- harnessFlow.md § 5.3 桥接 ① 仅承诺"版本化"

### After
```
flow-catalog.md (~500 行):
  § 1 路线设计通用框架 (7 字段 schema)
  § 2-7 路线 A~F 每条独立章节（7 字段）
  § 8 切换/降级规则（路线间）
  § 9 扩展位（G+ 预留）

routing-matrix.md (~300 行):
  § 1 三维决策 (size × type × risk) 维度定义
  § 2 矩阵主表（体量行 × 类型列 → 路线 candidates + 推荐权重）
  § 3 风险修正器（风险维度如何 bump 路线推荐）
  § 4 决策规则（查表 → 候选 → 权重 → top-2 输出）
  § 5 evolution_config（MVP 默认值 + 覆盖方式）
  § 6 查表示例（5 个典型任务向量演算）
```

### Interaction Changes
| Touchpoint | Before | After |
|---|---|---|
| 主 skill 路由 | 查 method3 § 2.4 五个例子类比 | 查 routing-matrix 主表直接 look up (size, type, risk) → candidates |
| 了解路线详情 | 读 method3 § 4.1 六字精神 + 脑补 | 读 flow-catalog 对应章节（skill 序列 / 切换条件 / 降级路径一览） |
| 改路线配置 | method3 是规则文档不应改 | routing-matrix 是数据文件，改权重走 PR |

---

## Mandatory Reading

| Priority | File | Why |
|---|---|---|
| P0 | `harnessFlow /harness-flow.prd.md` Phase 3 + § Solution Detail | Phase 3 scope |
| P0 | `harnessFlow /method3.md` § 2 分诊 + § 3 路由 + § 4 路线 + § 9.1 迁移表 | 路线精神锚点 |
| P0 | `harnessFlow /harnessFlow.md` § 5.1 能力映射表 + § 5.3 桥接 ① ④ | 不重造轮边界 + 决策引擎落地 |
| P1 | `~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/commands/*.md`（扫描） | 验证 skill 名真实存在，防 flow-catalog 写死链 |
| P1 | `~/.claude/skills/` 顶层目录 | 验证 gstack skill 真实可用 |

## External Documentation
N/A — 内部架构落地文档。

---

## Patterns to Mirror

### DOC_STYLE
// SOURCE: `harnessFlow /method3.md` + `harnessFlow.md`
- 版本号 + frontmatter
- `## § N` 章节层级
- 每章 Why + How + 反例/切换条件
- 表格 + 代码块做视觉锚点
- 禁 emoji

### CROSS_REF_STYLE
// SOURCE: `harnessFlow /method3.md` § 9
- 引 method3 用 `规则详见 method3.md § N`
- 引 harnessFlow.md 用 `架构详见 harnessFlow.md § N`
- 引未产出文档用 `(Phase X 产出)`

### SKILL_NAMING
// SOURCE: method3.md § 4.1 + 真实 skills 目录
- 所有 skill / command 引用必须真实存在（Phase 3 前置 scan）
- 格式：`SP:skill-name` / `ECC:command-name` / `gstack:skill-name` / `native:subagent-name`
- 避免死链：每写一条 skill 名都要 grep 验证

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `harnessFlow /flow-catalog.md` | CREATE | Phase 3 产出 1 |
| `harnessFlow /routing-matrix.md` | CREATE | Phase 3 产出 2 |
| `harnessFlow /harness-flow.prd.md` | UPDATE | Phase 3 status in-progress → complete |

## NOT Building

- ❌ `routing-matrix.json`（机器可 query 版本，留 Phase 5 主 skill 实现时生成）
- ❌ 状态机（Phase 4 `state-machine.md`）
- ❌ task-board schema（Phase 4 `task-board-template.md`）
- ❌ DoD 模板细节展开（已在 method3 § 6.1；Phase 6 做原语库）
- ❌ 主 skill prompt 本体（Phase 5）
- ❌ Supervisor / Verifier prompt 本体（Phase 6）
- ❌ 对每个 skill 的 API 细节展开（flow-catalog 只列序列和依据，不抄 skill 文档）
- ❌ 重复 method3 的路由规则细节（本文档落实执行层，不重定义规则）

---

## Step-by-Step Tasks

### Task 1: Skill 名真实性扫描
- **ACTION**: grep 真实存在的 skill/command 名避免 flow-catalog 写死链
- **IMPLEMENT**:
  ```bash
  ls ~/.claude/skills/ | sort > /tmp/gstack_skills.txt
  ls ~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/commands/ | sort > /tmp/ecc_commands.txt
  ls ~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/agents/ 2>/dev/null | sort > /tmp/ecc_agents.txt
  # superpowers 扫描 (如有)
  find ~/.claude -path "*superpowers*/skills/*" -type d 2>/dev/null | xargs -I{} basename {} | sort > /tmp/sp_skills.txt
  ```
- **VALIDATE**: 三个文件非空；每个预计在 flow-catalog 引用的 skill 都在对应文件里

### Task 2: 写 flow-catalog.md 骨架
- **ACTION**: 定 9 章节骨架 + 每条路线 7 字段 schema
- **IMPLEMENT**:
  ```
  # flow-catalog.md (title)
  frontmatter (version / status / readers)

  ## § 1 路线设计框架 (40-60 行)
  1.1 7 字段 schema: 精神 / 定位 / 适用场景 / 调度序列 / 切换条件 / 降级路径 / 风险点
  1.2 调度序列写法约定 (SP:xxx / ECC:xxx / gstack:xxx / native:xxx)
  1.3 DAG vs LLM 路由边界

  ## § 2 路线 A — 零 PRP 直改提交 (XS) (40-60 行)
  ## § 3 路线 B — 轻 PRP 快速交付 (S-M) (60-80 行)
  ## § 4 路线 C — 全 PRP 重验证 (L-XL) (80-120 行) [MVP 主路线]
  ## § 5 路线 D — UI 视觉专线 (S-M UI) (50-70 行)
  ## § 6 路线 E — agent graph 专线 (L-XL graph) (60-80 行)
  ## § 7 路线 F — 研究方案探索专线 (40-60 行)

  ## § 8 路线切换/降级规则 (40-60 行)
  8.1 切换触发矩阵（DRIFT_CRITICAL / 路线失败 / 体量重估）
  8.2 降级路径（C → C-lite / D → A / E → C）
  8.3 禁止回退（A → C 不允许中途升级；必须重开任务）

  ## § 9 扩展位 (G+ 预留) (15-25 行)
  9.1 新路线引入流程
  9.2 版本化与 PR 审批

  总计: ≥500 行
  ```
- **VALIDATE**: 骨架覆盖 method3 § 4.1 六条 + 切换降级 + 扩展位

### Task 3: 写路线 A/B（轻量路线）
- **ACTION**: 填 § 2 路线 A + § 3 路线 B
- **IMPLEMENT**:
  - **A（XS）**:
    - 精神：零 PRP 直改提交 / 调度序列：`native:Edit` → `native:pytest` / `ECC:commit`
    - 适用：单函数改 / typo / comment / docstring
    - 切换条件：发现改动面扩大 → 升 B / 发现不可逆 → 升 C
    - 降级路径：无（已是最轻）
    - 风险点：面积评估错会漏 DoD
  - **B（S-M）**:
    - 精神：轻 PRP 快速交付 / 调度序列：`SP:brainstorming`（2 轮）→ `ECC:prp-plan`（小 plan）→ `ECC:prp-implement` → `SP:code-reviewer` → `ECC:prp-commit`
    - 适用：单模块小 feature / bug fix
    - 切换：跨模块 → 升 C / 纯 UI → 转 D
    - 降级：省掉 brainstorming 走 A（仅 reviewer 确认无需澄清时）
    - 风险点：prp-plan 可能过轻导致实施中爆 scope
- **VALIDATE**: 每条路线 7 字段填满；skill 名通过 Task 1 扫描

### Task 4: 写路线 C（MVP 主路线，最详细）
- **ACTION**: 填 § 4 路线 C — 全 PRP 重验证
- **IMPLEMENT**:
  - 精神：全 PRP 重验证（方案 C 真完成版，对标 P20 事故升级版）
  - 调度序列（完整版）：
    ```
    SP:brainstorming (3 轮) →
    ECC:prp-prd →
    ECC:prp-plan →
    ECC:save-session (checkpoint 1) →
    ECC:prp-implement →
    SP:code-reviewer (执行中) →
    ECC:retro (中间反思) →
    native:Verifier (DoD eval) [强制] →
    ECC:santa-loop (FAIL 时迭代) →
    ECC:prp-commit →
    ECC:prp-pr →
    ECC:retro (收口) →
    native:failure-archive-append
    ```
  - 适用：L-XL 跨模块 feature / graph 改造 / 视频出片 / 不可逆操作
  - 切换条件：Verifier 反复 FAIL 3 次 → 考虑 E（agent graph 专线）；Supervisor 报 DRIFT_CRITICAL → 用户选切
  - 降级路径：C → C-lite（省 santa-loop 迭代 / 缩减 brainstorming 轮次），仅在体量重估为 M 时允许
  - 风险点：
    - 主 skill prompt 过长（用外置 routing-matrix / state-machine 缓解）
    - 跨会话目标漂移（用 save-session + goal-anchor 缓解）
    - 假完成（用 Verifier + DoD 表达式 + trap catalog 缓解）
  - **P20 事故对应**：指明 C 路线的哪一步原本缺失（无 Verifier、无 DoD eval），现在怎么补齐
- **GOTCHA**:
  - C 是 MVP 主路线，详细程度 > A/B
  - 明确"强制 Verifier 门"位置（调用 Verifier 必在收口前，借 Stop hook 兜底，详见 harnessFlow.md § 5.3 桥接 ⑤）
- **VALIDATE**: 调度序列 ≥10 步；P20 事故映射明确；切换/降级条件可执行

### Task 5: 写路线 D/E/F（专线）
- **ACTION**: 填 § 5 D + § 6 E + § 7 F
- **IMPLEMENT**:
  - **D（UI 视觉专线）**:
    - 精神：视觉任务走 frontend-design + screenshot-verify
    - 调度序列：`SP:brainstorming` → `ECC:frontend-design` → `native:Edit` → `gstack:browse`（或 `ECC:playwright`）screenshot → `SP:design-review` → `ECC:prp-commit`
    - 适用：Vue 页面 / Vue Flow 视觉 / 组件视觉优化
    - 切换：复杂 state 管理 → 退 B；纯 CSS 微调 → 降 A
  - **E（agent graph 专线）**:
    - 精神：LangGraph 节点改造用 graph-design + agent-eval + verification-loop
    - 调度序列：`SP:brainstorming` → 手工画 graph → `ECC:prp-plan` → `ECC:prp-implement`（节点级 TDD）→ `SP:agent-eval`（节点输出回归）→ `ECC:verification-loop` → `ECC:prp-commit`
    - 适用：aigcv2 视频生产 pipeline / subgraph 新增
    - 切换：graph 稳定，改节点内部逻辑 → 转 C；超大重构 → 升 C-重
  - **F（研究方案探索专线）**:
    - 精神：研究 / 调研 / 方案对比探索
    - 调度序列：`SP:brainstorming`（多轮）→ `ECC:research-agent` / `Explore` / `WebSearch` / `WebFetch` → `native:decision-log` → `ECC:retro`
    - 适用：选型调研 / 新技术评估 / 架构决策前置
    - 切换：方案确定后转 B/C 实施
    - 输出物：决策 log（非代码）
- **VALIDATE**: 三条专线 7 字段填满；skill 名均存在

### Task 6: 写 § 8 切换/降级 + § 9 扩展
- **ACTION**: 写路线间切换规则 + G+ 扩展位
- **IMPLEMENT**:
  - § 8.1 切换触发矩阵（表格：当前路线 × 触发条件 → 建议切换目标）
  - § 8.2 降级路径（C-lite / D → A / E → C 等）
  - § 8.3 禁止回退（A → C 要重开任务；C → A 是降级不是回退）
  - § 9.1 新路线引入：需 retro 3 次以上成功 combination 同一模式 → PR 进 flow-catalog
  - § 9.2 matrix 版本化：flow-catalog 改 = routing-matrix 可能改 = 版本号 bump
- **VALIDATE**: § 8 切换规则 ≥6 条，§ 9 流程清晰

### Task 7: 写 routing-matrix.md 骨架
- **ACTION**: 定 6 章节骨架
- **IMPLEMENT**:
  ```
  ## § 1 三维决策 (40-60 行)
  1.1 size 维度 (XS/S/M/L/XL/XXL+) 判定规则
  1.2 type 维度 (纯代码 / 后端 feature / UI / agent graph / 文档 / 重构 / 研究) 判定
  1.3 risk 维度 (低 / 中 / 高 / 不可逆) 判定

  ## § 2 矩阵主表 (80-120 行)
  2.1 表结构：行=体量，列=类型，cell=[候选路线列表 + 权重]
  2.2 主表（大表格，6 行 × 7 列）
  2.3 矩阵读法示例

  ## § 3 风险修正器 (40-60 行)
  3.1 风险 → 路线权重调整规则
  3.2 不可逆强制触发 IRREVERSIBLE_HALT 检查（详见 method3 § 5.2）

  ## § 4 决策规则 (30-50 行)
  4.1 查表算法: (size, type, risk) → candidates[] → 权重排序 → top-2
  4.2 降权规则: failure-archive 中失败过的组合 -20%
  4.3 特殊规则: 研究型无论体量都走 F

  ## § 5 evolution_config (20-30 行)
  5.1 MVP 默认阈值（route-outcome ≥ 10 / combination ≥ 5 / audit 每 20 次）
  5.2 覆盖方式 (JSON 字段 evolution_config)

  ## § 6 查表示例 (40-60 行)
  例 1: P20 视频出片任务向量 (XL, 视频出片, 不可逆) → 查表演算
  例 2: aigc 后端加素材源 (L, 后端 feature, 中)
  例 3: Vue 新页面 (M, UI, 低)
  例 4: 修 typo (XS, 纯代码, 低)
  例 5: 选型调研 (M, 研究, 低)

  总计: ≥300 行
  ```
- **VALIDATE**: 骨架覆盖 method3 § 2 分诊 + § 3 路由规则

### Task 8: 写 routing-matrix 主表 + 示例
- **ACTION**: 填 § 2 主表 + § 6 五个查表示例
- **IMPLEMENT**:
  - § 2 主表（mark down table）:
    ```
    | 体量＼类型 | 纯代码 | 后端 feature | UI | agent graph | 文档 | 重构 | 研究 |
    |---|---|---|---|---|---|---|---|
    | XS | A (1.0) / B (0.3) | A (0.7) / B (0.9) | A (0.5) / D (0.8) | - | A (1.0) | A (0.6) / B (0.7) | F (0.9) |
    | S | B (0.9) / A (0.6) | B (1.0) | D (1.0) / B (0.6) | B (0.7) / E (0.4) | B (0.8) | B (0.9) / C (0.4) | F (1.0) |
    | M | B (1.0) / C (0.5) | B (0.7) / C (0.9) | D (1.0) / B (0.4) | E (0.9) / B (0.5) | B (1.0) | C (1.0) / B (0.6) | F (1.0) |
    | L | C (1.0) / B (0.4) | C (1.0) | D (0.8) / C (0.7) | E (1.0) / C (0.6) | C (0.8) | C (1.0) | F (0.8) + 转 C |
    | XL | C (1.0) | C (1.0) | C (1.0) | E (1.0) / C (0.9) | C (1.0) | C (1.0) | 必转 C |
    | XXL+ | C (1.0) 分阶段 | C (1.0) 分阶段 | 分拆 | E (1.0) 分阶段 | C (1.0) 分阶段 | C (1.0) 分阶段 | 必转 C |
    ```
  - § 6 五个示例：每个含 (size, type, risk) → 查表 → candidates → 权重调整 → top-2 → 推荐
  - 示例 1 (P20): `(XL, agent graph / 视频出片, 不可逆)` → cell `E (1.0) / C (0.9)` → 风险修正不可逆 +强制 Verifier → top-1 E (含 Verifier 硬 gate)，top-2 C（MVP 重验证）
- **GOTCHA**:
  - 权重 0.0-1.0，非百分比
  - 视频出片按 agent graph 列 + 强风险修正
  - XXL+ 体量全部要求分阶段（PRD 原则）
- **VALIDATE**: 6×7 = 42 cell 每格有值或 "-"；5 个示例演算完整

### Task 9: 写 § 3 风险修正 + § 4 决策规则 + § 5 evolution
- **ACTION**: 填决策算法细节
- **IMPLEMENT**:
  - § 3.1 风险修正器表：
    ```
    | 风险 | 路线权重调整 |
    |---|---|
    | 低 | 无修正 |
    | 中 | C 权重 +0.1 |
    | 高 | C 权重 +0.2 / A 权重 -0.3 |
    | 不可逆 | C 权重 +0.3 / 强制 Verifier / IRREVERSIBLE_HALT 前置检查 / 禁止 A |
    ```
  - § 3.2 不可逆 → harnessFlow.md § 5.2 IRREVERSIBLE_HALT 红线（OSS 写入豁免见 method3 § 5.2）
  - § 4.1 算法伪码（Python-like）:
    ```python
    def route_decide(size, type, risk):
        cell = matrix[size][type]
        candidates = cell.candidates
        for c in candidates:
            c.weight += risk_modifier(risk, c.route)
            c.weight *= 1 - failure_penalty(c.route, type)
        return sorted(candidates, key=lambda x: -x.weight)[:2]
    ```
  - § 4.2 failure-archive 降权：同 (route, task_type) 组合失败率 > 30% → 权重 × 0.8
  - § 4.3 特殊规则：研究 type 默认 F；不可逆风险禁 A
  - § 5.1 MVP 默认：
    ```json
    {
      "route_outcome_min_samples": 10,
      "combination_min_success": 5,
      "audit_interval_tasks": 20,
      "failure_penalty_threshold": 0.3
    }
    ```
  - § 5.2 覆盖：编辑 routing-matrix.md § 5 → 走 PR → bump 版本号
- **VALIDATE**: 算法可逐字转 Python；风险修正表 4 行齐全

### Task 10: 统稿 + 交叉引用 + frontmatter
- **ACTION**: 拼两份文档 + 校交叉引用 + 写 frontmatter
- **IMPLEMENT**:
  - frontmatter（两文档同风格）:
    ```
    **版本**: v1.0 (2026-04-16)
    **Status**: DRAFT（Phase 3 产出）
    **Readers**: 主 skill (Phase 5) / Supervisor (Phase 6) / 贡献者
    ```
  - 每章首行一句话"这章回答什么问题"
  - 引 method3 / harnessFlow / 姐妹 Phase 文档用 `(Phase X 产出)`
  - 末尾版本号 + 日期
- **VALIDATE**:
  - flow-catalog.md ≥500 行
  - routing-matrix.md ≥300 行
  - 交叉引用无死链
  - 引 method3 ≥3 / 引 harnessFlow ≥2

### Task 11: 写入 + 更新 PRD
- **ACTION**: 落盘 + PRD Phase 3 状态 in-progress → complete
- **IMPLEMENT**:
  - `Write` 写 flow-catalog.md
  - `Write` 写 routing-matrix.md
  - `Edit` 改 PRD Phase 3 行: status `in-progress` → `complete`
- **VALIDATE**: 两文件存在且达标；PRD 改动 git diff 可见

### Task 12: 独立 code-reviewer 审查
- **ACTION**: 按 quality-over-speed 原则，启两个并行独立 reviewer
- **IMPLEMENT**:
  - Reviewer 1: 审 flow-catalog.md — skill 名真实性 / 调度序列可行性 / C 路线与 P20 事故对应 / 路线间切换规则一致性
  - Reviewer 2: 审 routing-matrix.md — 主表 42 cell 覆盖 / 权重合理性 / 算法伪码可 eval / 示例演算正确
- **VALIDATE**: 两份 punch list 产出

### Task 13: 应用 P0/P1 punch list + commit
- **ACTION**: Edit 修复 P0/P1，commit Phase 3
- **VALIDATE**: 所有 P0 修复，P1 修复或明确延后说明

---

## Testing Strategy

N/A — 纯文档任务。

### Doc-level checks

| Check | Method | Expected |
|---|---|---|
| flow-catalog 章节齐全 | grep `^## § [1-9]` | 9 章 |
| 6 路线 A~F 齐全 | grep `^## § [2-7] ` | 6 |
| flow-catalog 体量 | `wc -l` | ≥500 |
| routing-matrix 章节齐全 | grep `^## § [1-6]` | 6 |
| routing-matrix 体量 | `wc -l` | ≥300 |
| 主表 42 cell | 行 × 列 scan | 6 行 × 7 列 |
| 交叉引用 method3 | grep `method3.md § ` | ≥3 在 flow-catalog，≥2 在 routing-matrix |

---

## Validation Commands

```bash
# 1. flow-catalog 9 章
grep -c "^## § [1-9]" "/Users/zhongtianyi/work/code/harnessFlow /flow-catalog.md"
```
EXPECT: `9`

```bash
# 2. 六路线 A~F 齐全
grep -cE "^## § [2-7] 路线 [A-F]" "/Users/zhongtianyi/work/code/harnessFlow /flow-catalog.md"
```
EXPECT: `6`

```bash
# 3. routing-matrix 6 章
grep -c "^## § [1-6]" "/Users/zhongtianyi/work/code/harnessFlow /routing-matrix.md"
```
EXPECT: `6`

```bash
# 4. 体量
wc -l "/Users/zhongtianyi/work/code/harnessFlow /flow-catalog.md" "/Users/zhongtianyi/work/code/harnessFlow /routing-matrix.md"
```
EXPECT: flow-catalog ≥500; routing-matrix ≥300

```bash
# 5. 交叉引用
grep -c "method3.md §" "/Users/zhongtianyi/work/code/harnessFlow /flow-catalog.md"
grep -c "harnessFlow.md §" "/Users/zhongtianyi/work/code/harnessFlow /flow-catalog.md"
```
EXPECT: 各 ≥2

---

## Acceptance Criteria

- [ ] flow-catalog.md 9 章 + 6 路线 + ≥500 行
- [ ] routing-matrix.md 6 章 + 主表 42 cell + ≥300 行
- [ ] 所有 skill 名通过 Task 1 真实性扫描
- [ ] 路线 C 与 P20 事故对应明确（指明缺什么、现在怎么补）
- [ ] 决策算法伪码可逐字转 Python
- [ ] 5 个查表示例演算完整
- [ ] 交叉引用 method3 / harnessFlow 无死链
- [ ] 独立 reviewer P0/P1 punch list 全修复
- [ ] PRD Phase 3 状态 in-progress → complete

## Completion Checklist

- [ ] 文风与 method3 / harnessFlow 一致
- [ ] 无 emoji
- [ ] 无虚构 skill 名（全部 Task 1 scan 验证过）
- [ ] 主表权重有合理性依据（不拍脑袋）
- [ ] 引用到 Phase 4-7 文档用 "(Phase X 产出)"，不留死链

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| skill 名写死链 | H | H | Task 1 强制扫描 + Reviewer 1 抽查 |
| 主表权重拍脑袋 | H | M | § 6 五个示例演算验证；权重调整规则写进 evolution_config 可迭代 |
| 路线 C 调度序列过长主 skill 装不下 | M | M | 序列只列 skill 名，细节分到 state-machine (Phase 4) |
| 与 method3 § 4 规则冲突 | M | H | 每章首行声明"规则源头 method3 § N，本章落实执行"；Task 12 reviewer 检查一致性 |
| 矩阵无法覆盖真分叉 | M | M | § 4.3 特殊规则兜底 + LLM 路由仅真分叉（method3 § 3.1 二级路由） |

## Notes

- Phase 3 PRD 标 parallel with Phase 2。Phase 2 已 commit，Phase 3 可独立跑。
- 实施完后下一步 = Phase 4（state-machine + task-board-template + delivery-checklist）。
- 本 plan 是自包含实施指南；实施时不应再问"skill 名叫什么 / 主表权重怎么填"等问题。
