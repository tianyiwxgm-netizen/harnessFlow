# Plan: harnessFlow.md 顶层架构文档

## Summary
写 `harnessFlow /harnessFlow.md`，把 PRD 里的顶层架构 + 三引擎 + Supervisor + 生态边界 + 5 处自建桥接展开为独立、可 10 分钟读懂的架构文档。method3.md 是"方法论规则"，harnessFlow.md 是"架构蓝图"，两份文档分工明确，互引不互重。

## User Story
As a **新读者 / 贡献者 / 主 skill 开发者**，
I want 打开 harnessFlow.md 10 分钟内理解 harnessFlow 是什么、三引擎怎么协作、Supervisor 是第 4 块、与 SP/ECC/gstack 各自的边界、五处桥接为什么只此五处，
So that 后续 Phase（主 skill prompt / Supervisor / Verifier / failure-archive）的设计决策有共同的架构基底可参考。

## Problem → Solution
PRD 里的架构段落散在多处（Top-level Architecture / 三引擎 / Supervisor / 生态集成 / 技术风险）→ 单一架构文档，按"是什么/三引擎/Supervisor/生态边界/桥接空白/与 Claude Code 原生能力协同/架构风险"分 7 章节组织。

## Metadata
- **Complexity**: Small（单文件 / 无代码 / 无测试套件）
- **Source PRD**: `/Users/zhongtianyi/work/code/harnessFlow /harness-flow.prd.md`
- **PRD Phase**: Phase 2 — 顶层架构 harnessFlow.md
- **Estimated Files**: 1（`harnessFlow /harnessFlow.md`）
- **Target Size**: 400-600 行

---

## UX Design

### Before
无 harnessFlow.md。读者要理解架构只能从 PRD Solution Detail 和 method3.md 两处拼。

### After
```
┌────────────────────────────────────────────────────┐
│ harnessFlow.md = 7 章节架构蓝图 (~500 行)          │
│  § 1 定位 (总编排器 + Supervisor + 三引擎)         │
│  § 2 组件图 (ASCII 架构图 + 数据流)                │
│  § 3 三引擎详解 (真完成 / 纠偏 / 进化)             │
│  § 4 Supervisor Agent (第 4 块 / 独立章节)         │
│  § 5 生态边界 (SP/ECC/gstack 各管什么 + 优先级)    │
│  § 6 与 Claude Code 原生协同 (hooks/subagent/skill)│
│  § 7 架构风险与兜底                                │
└────────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After |
|---|---|---|
| 新读者理解架构 | 读 PRD + method3 拼凑 | 读 harnessFlow.md 一份 10 分钟抓大局 |
| 贡献者改架构 | 不知道改哪个文档 | 架构决策改 harnessFlow.md；规则改 method3.md |
| 主 skill 开发者 | 规则散乱 | § 5 边界表 + § 6 原生协同表直接抄 |

---

## Mandatory Reading

| Priority | File | Why |
|---|---|---|
| P0 | `harnessFlow /harness-flow.prd.md` 全文 | 架构描述来源 |
| P0 | `harnessFlow /method3.md` § 0.3 + § 1.3 + § 5 + § 6 | 规则锚点，避免重复 |
| P1 | PRD § Technical Approach + Research Summary | 吸收/规避设计来源 |

## External Documentation
N/A — 内部架构文档。

---

## Patterns to Mirror

### DOC_STYLE
// SOURCE: `harnessFlow /method3.md`
- 版本号 + 日期头部
- `## § N` 章节层级
- 每章内容含 Why + How + 反例或边界说明
- 表格/ASCII 图做视觉锚点
- 禁 emoji

### CROSS_REF_STYLE
// SOURCE: `harnessFlow /method3.md` § 9 索引
- 引姐妹文档用 `详见 xxx.md` + "(Phase X 产出)"
- 引 method3 用 `规则详见 method3.md § N`

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `harnessFlow /harnessFlow.md` | CREATE | Phase 2 核心产出 |
| `harnessFlow /harness-flow.prd.md` | UPDATE | Phase 2 status pending → in-progress → complete + PRP Plan 列填本文件 |

## NOT Building

- ❌ A~F 路线详细设计（Phase 3 `flow-catalog.md`）
- ❌ 路由矩阵（Phase 3 `routing-matrix.md`）
- ❌ 状态机（Phase 4 `state-machine.md`）
- ❌ 主 skill prompt（Phase 5）
- ❌ Supervisor / Verifier agent prompt 本体（Phase 6）
- ❌ failure-archive schema 细节（Phase 7）
- ❌ 具体 skill 的 API 使用说明（Phase 5-6 负责）
- ❌ 复述 method3 的规则（架构文档只讲"有什么+怎么协作"，不讲判断规则）

---

## Step-by-Step Tasks

### Task 1: 骨架设计
- **ACTION**: 定 7 章节骨架与字数预算
- **IMPLEMENT**:
  ```
  # harnessFlow · 架构蓝图 (title)
  > 一句话定位
  metadata (version / status / readers)

  ## § 1 定位与边界 (40-60 行)
  1.1 是什么 / 不是什么
  1.2 与 method3.md 分工 (架构蓝图 vs 规则方法论)
  1.3 一句话价值

  ## § 2 组件图 (50-70 行)
  2.1 ASCII 架构图
  2.2 主要数据流 (输入 → 执行 → 验证 → 收口)
  2.3 控制流 (主 skill 调度 + Supervisor 旁观)

  ## § 3 三引擎详解 (100-140 行) [核心]
  3.1 真完成引擎 (DoD / Verifier / 三段证据 / trap catalog)
  3.2 纠偏引擎 (三层雷达 / 4 级 ladder / 信号源 / 审计)
  3.3 进化引擎 (retro / 三类记忆写回 / matrix 版本化 / failure-archive)

  ## § 4 Supervisor Agent — 第 4 块 (70-100 行) [核心]
  4.1 定位 (用户的眼睛+大脑)
  4.2 部署 (subagent + PostToolUse hook + 周期 wake-up + 只读)
  4.3 4 职责 / 6 干预 / 3 红线 (引 method3 § 5)
  4.4 结构化输出协议
  4.5 进化反哺 (所有提醒进 retro)

  ## § 5 生态边界 (80-110 行)
  5.1 SP / ECC / gstack 各管什么 (能力映射表)
  5.2 优先级声明 (harnessFlow > gstack > ECC > SP)
  5.3 5 处自建桥接列表 (每处 why + how)
  5.4 不重造轮的边界 (哪些绝对不碰)

  ## § 6 与 Claude Code 原生协同 (50-70 行)
  6.1 subagent 用法 (Supervisor / Verifier / 各 build-resolver)
  6.2 hooks 用法 (Pre/Post/Stop/SubagentStop/pre:task:complete 新建)
  6.3 skill 用法 (harnessFlow 主 skill + 调度现有 skill)
  6.4 MCP 用法 (context7 / playwright / github / memory)
  6.5 memory 用法 (feedback_* / project_* / routing state)

  ## § 7 架构风险与兜底 (50-70 行)
  7.1 Supervisor 延迟 / 成本
  7.2 三套库版本升级
  7.3 主 skill prompt 过长
  7.4 DoD 写不好
  7.5 全局 budget 超预算
  7.6 gstack / harnessFlow 优先级冲突
  每条 3 元素 [风险 / 触发条件 / 兜底动作]

  总计: ≥500 行 (目标 560)
  ```
- **GOTCHA**: § 3 § 4 不要重复 method3 § 5 § 6 的**规则细节**；只讲"由谁/在哪/怎么协作"
- **VALIDATE**: 骨架覆盖 PRD Solution Detail 全部段落

### Task 2: 写 § 1 定位 + § 2 组件图
- **ACTION**: 写 § 1（定位与边界）+ § 2（组件图 + 数据流 + 控制流）
- **IMPLEMENT**:
  - § 1 定位: "总编排器 + 总监督 + 总路由器"; "只编排不造轮"; 不是 skill 库 / 不是 workflow framework / 不是 multi-agent chat
  - § 1.2 与 method3 分工: harnessFlow.md = 蓝图（what）；method3.md = 规则（how to judge）
  - § 1.3 一句话价值: "让点菜后餐厅自动把真能吃的菜端到嘴边"（PRD 一句话副标题）
  - § 2.1 ASCII 架构图（在 PRD 基础上扩展 + 标信号流）：显示 [用户 → 主 skill → 三引擎（并列） + Supervisor（侧挂） + 现有生态（底座）→ Verifier → 收口]
  - § 2.2 主要数据流: 任务描述 → goal-anchor → DoD 表达式 → 执行 artifact → Verifier eval → retro → failure-archive
  - § 2.3 控制流: 确定性 DAG（默认） + LLM 路由（真分叉，记 reason）+ Supervisor 信号（INFO/WARN/BLOCK）
- **MIRROR**: method3.md 文风
- **VALIDATE**: § 1 读完明确"harnessFlow 是什么 / 不是什么"；§ 2 架构图 + 数据流 + 控制流三图齐全

### Task 3: 写 § 3 三引擎详解
- **ACTION**: 展开 PRD 三引擎段落为完整一章
- **IMPLEMENT**:
  - § 3.1 真完成: DoD 表达式（格式 + 原语库指引 + 与 method3 § 6.1 关联）/ Verifier（独立 / 只读 / 强制三动作 / FAIL 动作）/ 三段证据链（存在/行为/质量，与 method3 § 6.3 映射）/ trap catalog（jsonl schema 简述 + 7 条 MVP）
  - § 3.2 纠偏: 三层雷达表（L1 微 / L2 中 / L3 大）/ 4 级 ladder（L0-L3 + budget guard）/ 信号源 6 种 / 审计（每次写 task-board）
  - § 3.3 进化: retro 11 项 / 三类记忆写回（route-outcome / anti-pattern / combination）/ matrix 版本化（语义化版本 + 人审批 PR）/ failure-archive（结构化 jsonl + 每项目独立 + 全局视图）/ 进化边界（不自改代码）
  - 每引擎结尾指向 method3 对应 § 的链接
- **MIRROR**: PRD § Solution Detail 三引擎段
- **GOTCHA**:
  - 不重复 method3 的判断规则，只讲引擎组件和协作
  - 每引擎给 1 个实际调度示例（"真完成引擎被触发时的 step-by-step"）
- **VALIDATE**: 三引擎每段含"组件 + 协作 + 引用 method3 规则锚点"

### Task 4: 写 § 4 Supervisor Agent
- **ACTION**: 把 Supervisor 拎成独立章节，突出它是架构第 4 块
- **IMPLEMENT**:
  - § 4.1 定位: 用户的眼睛+大脑，不执行不写代码；副驾不是主驾
  - § 4.2 部署: subagent 拉起时机 + PostToolUse hook 配置 + 周期 wake-up 频率 + 只读权限列表
  - § 4.3 4 职责 / 6 干预 / 3 红线（引 method3 § 5，不重抄规则，只说职责对应）
  - § 4.4 结构化输出协议（`{status, diagnosis, suggested_action, severity, evidence}` 字段规范 + 主 skill 的 parse 逻辑）
  - § 4.5 进化反哺: 所有提醒进 retro → 同类反复报警 → matrix 权重调（引 § 3.3 + method3 § 7）
- **GOTCHA**: Supervisor 这章的价值是"架构中它在哪 / 怎么接入 / 怎么与主 skill 通信"，不是重复 method3 § 5 的干预分类
- **VALIDATE**: § 4 读完能回答"Supervisor 什么时候被唤起 / 什么时候打断我"

### Task 5: 写 § 5 生态边界 + § 6 原生协同
- **ACTION**: 列出生态分工 + Claude Code 原生能力使用方式
- **IMPLEMENT**:
  - § 5.1 能力映射表（三列：能力名 / 来源库 / harnessFlow 调度场景）
    - 覆盖 PRD Technical Approach 生态集成表 6 行
    - 每行展开 2-3 个具体能力名
  - § 5.2 优先级声明: `CLAUDE.md` 里应写 `harnessFlow > gstack > ECC > SP`，冲突时主 skill 按优先级解析
  - § 5.3 5 处自建桥接（每处 4 字段）:
    1. routing-matrix 版本化 (why / how / 产出文件 / 影响引擎)
    2. 假完成 trap catalog
    3. task-level state machine
    4. 路由决策引擎
    5. `pre:task:complete` hook
  - § 5.4 不重造轮的边界: e2e / verification / brainstorming / save-session / retro / commit / PR 等绝对不自造清单
  - § 6.1 subagent: 哪些 agent 用原生 subagent（Verifier / Supervisor / Build-resolver / Code-reviewer 等）+ 指向 Phase 6
  - § 6.2 hooks: 列 PreToolUse / PostToolUse / Stop / SubagentStop + 新建的 `pre:task:complete` + 每 hook 绑的动作
  - § 6.3 skill: 主 skill = harnessFlow，调度 ECC 的 prp-* + SP 的 brainstorming / verification-before-completion + gstack 的 careful / timeline-log
  - § 6.4 MCP: context7（技术文档查询）/ playwright（浏览器 e2e）/ github（PR 操作）/ memory（记忆存取）
  - § 6.5 memory: 项目 memory 存 feedback_* / project_* / routing state
- **MIRROR**: PRD § Technical Approach 生态集成表
- **GOTCHA**: § 5.3 每处桥接要写清"为什么只此五处"（对照 SP/ECC/gstack 确认无对应能力）
- **VALIDATE**:
  - § 5.1 表行数 ≥6
  - § 5.3 5 处桥接齐全且每处 4 字段填满
  - § 6 5 种原生能力各有独立小节

### Task 6: 写 § 7 架构风险与兜底
- **ACTION**: 把 PRD Technical Risks 7 条风险展开
- **IMPLEMENT**:
  - 每条风险 [描述 / 触发条件 / 兜底动作 / 监控信号] 4 字段
  - 7 条: Supervisor 延迟-成本 / 三库版本冲突 / 主 skill prompt 过长 / DoD 写不好 / 全局 budget 超 / gstack 优先级冲突 / Supervisor 报警疲劳
- **MIRROR**: PRD § Technical Risks 表
- **VALIDATE**: 7 条齐全且每条 4 字段

### Task 7: 统稿 + 交叉引用
- **ACTION**: 拼文档 + 校交叉引用 + 写 frontmatter
- **IMPLEMENT**:
  - frontmatter: version / status / readers（同 method3.md 风格）
  - 每章首行一句话说明"这章回答什么问题"
  - 引到 method3.md 的地方统一用 `规则详见 method3.md § N`
  - 引到未产出文档统一用 `(Phase X 产出，详见 xxx.md)`
  - 末尾版本号 + 日期
- **VALIDATE**:
  - § 7 章齐全
  - 交叉引用无死链
  - 总行数 ≥400（目标 560）

### Task 8: 写入 + 更新 PRD
- **ACTION**: 落盘 + PRD Phase 2 状态 pending → complete + PRP Plan 列
- **IMPLEMENT**:
  - `Write` 写 `harnessFlow /harnessFlow.md`
  - `Edit` 改 PRD Phase 2 行: status `pending` → `complete`，PRP Plan `-` → `plans/harnessFlow-architecture.plan.md`
- **VALIDATE**: 文件存在且 ≥400 行；PRD 改动 git diff 可见

### Task 9: 端到端自验
- **ACTION**: 跑 Validation Commands + 人工 10 分钟读者测试（自问："读完我能否回答 § 1.1 / § 3 每引擎职责 / § 5.3 5 处桥接"）
- **VALIDATE**: 见 Validation Commands

---

## Testing Strategy

N/A — 纯文档任务无单元测试。

### Doc-level checks

| Check | Method | Expected |
|---|---|---|
| 章节齐全 | grep `^## § [1-7]` | 7 章 |
| 体量 ≥400 行 | `wc -l` | ≥400 |
| 三引擎章节齐全 | grep `### 3\.[1-3]` | 3 小节 |
| Supervisor 4 小节齐全 | grep `### 4\.[1-5]` | 4-5 小节 |
| 5 处桥接齐全 | grep `桥接` section count | ≥5 |
| 交叉引用 method3 | grep `method3.md § ` | ≥3 |
| 不重抄 method3 规则 | 人工 | 本文档无"§ N.1 的 4 级 ladder"级细节 |

---

## Validation Commands

```bash
# 1. 章节齐全
grep -c "^## § [1-7]" "/Users/zhongtianyi/work/code/harnessFlow /harnessFlow.md"
```
EXPECT: `7`

```bash
# 2. 体量 ≥400
wc -l "/Users/zhongtianyi/work/code/harnessFlow /harnessFlow.md"
```
EXPECT: `≥ 400`

```bash
# 3. 三引擎章节齐全
grep -cE "^### 3\.[1-3]" "/Users/zhongtianyi/work/code/harnessFlow /harnessFlow.md"
```
EXPECT: `≥ 3`

```bash
# 4. 引用 method3 锚点
grep -c "method3.md § " "/Users/zhongtianyi/work/code/harnessFlow /harnessFlow.md"
```
EXPECT: `≥ 3`

---

## Acceptance Criteria

- [ ] 7 章齐全
- [ ] ≥400 行
- [ ] § 3 三引擎 + § 4 Supervisor + § 5 生态边界三大核心章齐全
- [ ] § 5.3 5 处自建桥接完整
- [ ] 引 method3 锚点 ≥3 处，不重抄规则
- [ ] PRD Phase 2 状态 pending → complete + PRP Plan 指向本 plan

## Completion Checklist

- [ ] 文风与 method3.md 一致（版本号 / 无 emoji / 每章 Why+How+例 或 组件+协作）
- [ ] 无重抄 method3 规则细节
- [ ] 软引用姐妹文档（"Phase X 产出"）避免死链
- [ ] 10 分钟读者测试：读完能答"三引擎职责 / Supervisor 干什么 / 5 处桥接为什么"

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 与 method3 重复 | H | M | 每章 GOTCHA 明示"讲什么/不讲什么"；Task 3-5 强边界 |
| 架构图过于复杂难懂 | M | M | § 2 ASCII 图 ≤15 行，配文字说明 |
| § 5.1 能力映射表漏能力 | M | L | MIRROR PRD 生态集成表，逐行复核 |
| § 6 原生能力说明过浅 | M | L | 每种原生能力 ≥1 具体使用场景 |

## Notes

- Phase 2 与 Phase 3 PRD 标记 parallel。本 plan 独立于 Phase 3，可先后也可并行实施。
- 实施完后下一步 = `/prp-implement` 本文件；之后并/顺 Phase 3（flow-catalog + routing-matrix）。
