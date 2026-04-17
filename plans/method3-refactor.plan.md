# Plan: 重构 method3.md（速查表 → 真完成第一原则方法论）

## Summary
把 `harnessFlow /method3.md`（35 行命令速查表）重构为 harnessFlow 的方法论根文档。新版以"真完成"为第一原则，把原来 6 条经验规则升级为 9 章节显式判断逻辑（分诊/路由/监督/验证/交付/反模式/索引），为后续 Phase 2-8（顶层架构 / 路线 / 状态机 / 主 skill / Supervisor / Verifier / archive）提供规则源头。

## User Story
As a **harnessFlow 主 skill**（调度规则读者）+ **用户**（方法论读者），
I want 把 method3.md 从命令速查表升级为以"真完成"为根的方法论文档，
So that 主 skill 能依据显式判断逻辑做分诊/路由/监督/收口决策，用户能理解 harnessFlow 为什么这么设计 + 旧方案 C 为什么会假完成。

## Problem → Solution
35 行速查表，只到"体量→命令"映射 + 3 条经验硬规则，缺真完成 / Supervisor / 纠偏 / 进化任何机制 → 9 章节方法论文档，真完成为第一原则，显式判断逻辑驱动主 skill + Supervisor 决策。

## Metadata
- **Complexity**: Small（单文件 / 无代码 / 无测试套件）— 但内容密度高
- **Source PRD**: `/Users/zhongtianyi/work/code/harnessFlow /harness-flow.prd.md`
- **PRD Phase**: Phase 1 — 重构 method3.md
- **Estimated Files**: 1 （`harnessFlow /method3.md`）
- **Target Size**: ≥500 行（旧版 35 行的 14x+，超 PRD 要求的 5x 下限）

---

## UX Design

### Before
```
┌────────────────────────────────────────────────────────┐
│ method3.md = 35 行速查表                                │
│ - 表一: 体量(XS-XL) → 推荐命令组合                      │
│ - 表二: 具体任务 → 路线                                 │
│ - 三条硬规则(S 以下别上重/L 以上要 artifact/视觉用 gan) │
│                                                         │
│ 用户查找 → 套表 → 手动拼 skill 序列 → 中途靠感觉切      │
│ 缺: 真完成判定 / Supervisor / 纠偏 / 进化              │
└────────────────────────────────────────────────────────┘
```

### After
```
┌──────────────────────────────────────────────────────────┐
│ method3.md = 9 章节方法论 (~500-800 行)                   │
│ 1. 第一原则 (真完成 + 客人点菜 + 不重复造轮)              │
│ 2. 任务分诊规则 (体量 XS-XXL+ × 类型 7 类 显式判断)       │
│ 3. 路由规则 (→ routing-matrix.md)                         │
│ 4. 编排路线规则 (A~F 精神 → flow-catalog.md)             │
│ 5. 监督推进规则 (Supervisor 6 干预 / 3 红线 / 4 级 ladder)│
│ 6. 验证 QA review gate 规则 (DoD + 三段证据链 + Verifier) │
│ 7. 交付收口规则 (post-mortem + retro + failure-archive)  │
│ 8. 反模式清单 (公开方案 + 自家失败归纳)                  │
│ 9. 快速索引 (新旧对照 + 场景到规则映射)                  │
│                                                           │
│ 用户/主 skill 读章节 → 依显式判断逻辑决策                │
│ 旧 3 条硬规则全部升级为章节内细则 + 反例                 │
└──────────────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| 主 skill 启动 | 无引用 method3 | 主 skill prompt 引用 method3 § 1-2-3 作为分诊/路由根 | Phase 5 实施时接 |
| 用户初看 | 3 秒扫完速查表 | 前言 + § 1 第一原则 5 分钟读完抓大局 | 有"快速索引" § 9 兜底 |
| 方案 C 回放 | 照速查表选路线就完事 | § 6 验证规则显式要求 Verifier PASS 才算完成，P20 假完成写进 § 8 反例 | 真完成为根 |
| 新手上手 | 只能看到"用啥命令" | § 4 给路线精神 + § 9 快速索引 + § 8 反例 → 知道怎么选、为什么选 | 降入门成本 |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 (critical) | `harnessFlow /method3.md` | 1-35 | 旧版全文，重构前提保留其原意 |
| P0 (critical) | `harnessFlow /harness-flow.prd.md` | 全文 | PRD = 新 method3 的规则源头 |
| P0 (critical) | `~/.claude/projects/-Users-zhongtianyi-work-code/memory/feedback_real_completion.md` | 全文 | 真完成原则根据 — 逐字引入 § 1 |
| P0 (critical) | `~/.claude/projects/-Users-zhongtianyi-work-code/memory/feedback_workflow_scheme_c.md` | 全文 | 方案 C 失败案例根据 — 引入 § 8 |
| P1 (important) | `harnessFlow /harnessFlow_prompt_v2.docx` | 全文 | 用户原始需求文本，章节结构对齐 |
| P1 (important) | PRD § Core Capabilities (MoSCoW) | Must 段 | 9 章节必须全覆盖 Must 条目 |
| P1 (important) | PRD § Decisions Log | 全表 | 每章决策必须与 PRD Decisions 对齐 |
| P2 (reference) | PRD § Research Summary | 全段 | § 8 反模式来源 |

## External Documentation
| Topic | Source | Key Takeaway |
|---|---|---|
| N/A | — | 内部文档任务，无外部 lib 研究 |

---

## Patterns to Mirror

纯文档任务，无代码 pattern。只需保持风格与 harnessFlow PRD 一致：

### DOC_STYLE
// SOURCE: `harnessFlow /harness-flow.prd.md` 全文
- 中英文混用可接受，术语保留英文（DoD / Supervisor / Verifier / trap catalog / retro / failure-archive）
- 每条规则必须 **Why + How + 反例/例子** 三段
- 用表格和代码框做视觉锚点
- 用 `✅ / ❌` 标记正反例
- 严禁 fluff，严禁口号层（如"重视验证"），必须显式判断逻辑
- 禁 emoji（用户未请求）

### HEADING_STYLE
// SOURCE: PRD 章节层级
- `# 标题` 文档名
- `## § N · 章节名` 主章节
- `### 子节名` 子节
- `**关键词**:` 内联强调

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `harnessFlow /method3.md` | **OVERWRITE** | 35 行速查表完全重写为 ≥500 行方法论（用户硬要求重构不照搬）|
| `harnessFlow /harness-flow.prd.md` | UPDATE | Implementation Phases 表 Phase 1 status: pending → in-progress；PRP Plan 列填本文件路径 |

## NOT Building

**范围硬边界 — 严格 OUT OF SCOPE**：
- ❌ 路线 A~F 详细设计（每条路线 简称/定位/适用/调度顺序/优点/缺点/切换/风险控制点）→ 放 `flow-catalog.md`（PRD Phase 3）
- ❌ 路由矩阵详细表格（任务类型 × 体量 → 推荐 skills/commands/agents/hooks/MCP）→ 放 `routing-matrix.md`（PRD Phase 3）
- ❌ 状态机细节（路线启动 → 阶段切换 → 偏航处理 → 收口的状态流转图）→ 放 `state-machine.md`（PRD Phase 4）
- ❌ 任务表/状态表字段定义 → 放 `task-board-template.md`（PRD Phase 4）
- ❌ 交付清单（强制 DoD 验证项目）→ 放 `delivery-checklist.md`（PRD Phase 4）
- ❌ harnessFlow 主 skill prompt → 放 Phase 5
- ❌ Supervisor/Verifier agent prompt → 放 Phase 6
- ❌ DoD 表达式模板库（按任务类型）→ 放 Phase 6
- ❌ failure-archive.jsonl schema → 放 Phase 7
- ❌ 新造 method3 之外的其他文档

method3.md 作为**方法论根**，定义判断原则；细节填充由后续 Phase 的专题文档完成。method3.md 可以 reference 这些文档（如"详见 flow-catalog.md"），但不写细节。

---

## Step-by-Step Tasks

### Task 1: 准备前置 — 读齐输入
- **ACTION**: 核对手上已有的所有输入完整
- **IMPLEMENT**: 无代码，只是确认
  - 旧 method3.md 已在 context（之前 Read 过）
  - PRD 已在 context（刚刚写）
  - memory 三条 feedback 已在 context（保存过）
  - 需求文档内容已在 context（首轮读过 docx）
  - Phase 3 调研 Agent 返回已在 context
  - web 调研 Agent 返回已在 context
- **MIRROR**: N/A
- **IMPORTS**: N/A
- **GOTCHA**: 目录末尾有空格（`harnessFlow /`），所有路径要引号
- **VALIDATE**: 心算确认：旧 method3 = 35 行，PRD 表格已有 9 处 NOT Building 指向对应 phase 文档；无遗漏

### Task 2: 设计 method3.md 新版骨架（大纲 + 每节字数预算）
- **ACTION**: 定骨架、定字数分配、定每节核心意图
- **IMPLEMENT**:
```
# method3 · harnessFlow 方法论 (标题层)
> 一句话定位（20 字内）

## § 0 前言 (30-50 行)
- 这是什么
- 为什么重构
- 和 harnessFlow 其他文档关系

## § 1 第一原则 (80-120 行) [最核心章节]
### 1.1 真完成 (Real Completion) — 根中之根
### 1.2 客人点菜 (Restaurant Model) — 中途零废问题
### 1.3 不重复造轮 (No-Reinvent) — 只编排

## § 2 任务分诊规则 (80-120 行)
### 2.1 体量判定 (XS / S / M / L / XL / XXL+)
### 2.2 类型判定 (7 类 — 纯代码/UI/多模块/架构/agent graph/高验证/研究)
### 2.3 风险判定 (低/中/高/不可逆)
### 2.4 组合 → 决策

## § 3 路由规则 (50-70 行)
- 确定性 DAG 优先 / LLM 路由仅真分叉
- 每次 LLM 路由必记 reason
- 详细矩阵见 routing-matrix.md

## § 4 编排路线规则 (60-80 行)
- A-F 路线精神（每条 1 段）
- 何时切换 / 降级
- 详细设计见 flow-catalog.md

## § 5 监督推进规则 (80-120 行)
### 5.1 Supervisor 6 类干预 (忘开火/漏菜/走偏/节奏/顺序/冗余)
### 5.2 Supervisor 3 红线打断 (DRIFT_CRITICAL/DOD_GAP_ALERT/IRREVERSIBLE_HALT)
### 5.3 纠偏 4 级 retry ladder (L0-L3)
### 5.4 信号源 6 种

## § 6 验证 QA review gate 规则 (80-120 行) [最核心章节]
### 6.1 DoD 布尔表达式 — 机器可执行，非 LLM 自报
### 6.2 Verifier subagent — 执行/审查分离
### 6.3 三段证据链 (存在/行为/质量)
### 6.4 假完成 trap catalog

## § 7 交付收口规则 (50-70 行)
### 7.1 强制 post-mortem
### 7.2 三类记忆分级写回 (route-outcome/anti-pattern/combination)
### 7.3 failure-archive 驱动下次进化

## § 8 反模式清单 (50-80 行)
- 8.1 方案 C P20 假完成事件（自家）
- 8.2 AutoGen is_termination_msg（LLM 自报 TERMINATE）
- 8.3 CrewAI 全 LLM 黑盒路由
- 8.4 MetaGPT 硬 SOP 不灵活
- 8.5 无界 retry 循环
- 8.6 post-mortem 遗忘
- 8.7 隔空谈兵（口号层"重视验证"而无机制）

## § 9 快速索引 (30-50 行)
- 新旧对照表（旧速查表的每条规则指到新章节）
- 场景 → 规则映射（"我要 X" → 查 § Y）

总计: ≥580 行（目标 700 行上下）
```
- **MIRROR**: `harnessFlow /harness-flow.prd.md` § 章节组织
- **IMPORTS**: N/A
- **GOTCHA**:
  - § 1 和 § 6 是最核心两章，字数不能压
  - § 3 § 4 要严格短，把细节指到姐妹文档（避免重复维护）
  - § 8 必须包含方案 C P20 案例（用户硬要求，也是用户提 harnessFlow 的直接动因）
- **VALIDATE**:
  - 骨架覆盖 PRD MoSCoW Must 全部 7 条
  - 骨架覆盖需求文档第十条的"十、输出顺序"顺序（见 docx）
  - 总行数 ≥500（PRD 要求 ≥5x 旧版 = ≥175 行），目标 700 远超

### Task 3: 写 § 0 前言 + § 1 第一原则
- **ACTION**: 产出最核心的锚定章节
- **IMPLEMENT**:
  - § 0 前言:
    - 一句话定位："Claude Code 总编排器 harnessFlow 的方法论根文档"
    - 为什么重构：引方案 C P20 假完成事件（用户截图证据）
    - 和其他文档的关系（harness-flow.prd.md / harnessFlow.md / flow-catalog.md / routing-matrix.md / state-machine.md / ...）
    - 旧版保留什么/丢什么
  - § 1.1 真完成:
    - 引 memory `feedback_real_completion.md` 的餐厅/盖房类比
    - 定义完成 = 用户可直接消费的 artifact（5 类任务各举 1 例：mp4 + OSS key / 可 curl 后端 / 可点击 UI / 可渲染文档 / 重构后全测试绿 + 性能基线）
    - 两条铁律 [强证据收口 / 中途零废问题]
    - 反例: "代码 push 完了" / "build green" / "Phase X 通过" / "LLM 说 TERMINATE"
    - Why: 不这么写假完成率 30%
    - How to apply: 五步自检 + 三段证据
  - § 1.2 客人点菜:
    - 比喻: 点菜 → 餐厅自动跑 → 端到桌
    - 标准中间步骤 **100% 自动决策**，不打断用户
    - 只在 DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT 3 种打断
    - 反例: "水泥到了要不要砌墙？"、"菜切好了要不要炒？"
  - § 1.3 不重复造轮:
    - 只调度 SP/ECC/gstack + Claude Code 原生
    - 方案 A/B/C/D/E/F 是编排路线不是新底层 skill
    - 仅 5 处空白允许自建桥接（列出）
- **MIRROR**: PRD § Top-level Architecture + § Proposed Solution + memory feedback_real_completion
- **IMPORTS**: N/A（纯 md）
- **GOTCHA**: 真完成定义**必须是机器可执行**，不能写成"认真验证"这种口号；铁律写清楚"什么样的输出才算证据"
- **VALIDATE**:
  - § 1 三小节每节都有 Why + How + 反例
  - § 1.1 引 P20 方案 C 事件具体信息（无 mp4 / 无 OSS key / 服务未起）
  - 读者读完 § 1 能够独立判断"这个任务算不算真完成"

### Task 4: 写 § 2 任务分诊 + § 3 路由 + § 4 路线
- **ACTION**: 产出分诊/路由/路线规则，§ 3 § 4 故意保持薄
- **IMPLEMENT**:
  - § 2.1 体量: XS/S/M/L/XL/XXL+ 六级；每级给【特征】【典型耗时】【典型文件数】【警告信号】四维
  - § 2.2 类型: 7 类(纯代码改动/UI 视觉/多模块 feature/系统架构/agent graph-pipeline/高验证高风险/研究方案探索)，每类给【识别关键词】【典型任务】【风险点】
  - § 2.3 风险: 低/中/高/不可逆 4 级，每级给【例子】【必须的 gate】
  - § 2.4 三维组合 → 决策: "体量 × 类型 × 风险"三维如何综合（给 3-5 个具体组合例子，如"M 级 UI 低风险 = 短路线"、"XL 级 agent graph 不可逆 = 重路线 + 强 Supervisor"）
  - § 3 路由规则: 确定性 DAG 优先；LLM 路由仅真分叉；每次路由记 reason 入 task-board；矩阵见 routing-matrix.md；反模式 = 全 LLM 黑盒（引 CrewAI 反例）
  - § 4 路线规则: A-F 各 1 段精神；何时切换（L3 大偏航触发）；何时降级（reduce-scope）；详细设计见 flow-catalog.md
- **MIRROR**: PRD § Solution Detail + § Implementation Phases + § Research Summary
- **IMPORTS**: N/A
- **GOTCHA**:
  - § 3 § 4 字数必须严格控制（各 50-80 行），避免和 flow-catalog.md / routing-matrix.md 重复维护
  - 每次主 skill 调 method3 读的就是 § 2 体量/类型识别 — 判断规则要**完全显式**，不能留"看情况"这种模糊表述
- **VALIDATE**:
  - § 2 读完能判定任意 6 个具体任务的体量 + 类型 + 风险（举例校验）
  - § 3 § 4 明确指向姐妹文档且不重复细节
  - 旧版 3 条硬规则有显式继承（"S 以下别用重组合" → § 2.4 决策矩阵; "L 往上不用 artifact 会吃亏" → § 7 交付收口; "视觉用 gan-design" → § 2.2 UI 类型路线)

### Task 5: 写 § 5 监督 + § 6 验证（最核心之一）
- **ACTION**: 产出 Supervisor + 真完成引擎的完整规则
- **IMPLEMENT**:
  - § 5.1 Supervisor 6 类干预: 忘开火/漏菜/走偏/节奏失衡/顺序错/冗余；每类给【检测条件】【典型例子】【严重度 INFO/WARN/BLOCK】
  - § 5.2 3 红线打断: DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT；每红线给【触发条件】【动作】【恢复路径】
  - § 5.3 纠偏 4 级 retry ladder:
```
L0 retry-same   → 单步 timeout / 临时网络错
L1 retry-tweaked + scope down → L0 失败 / schema 不符
L2 switch-skill / interrupt + HITL → L1 失败 / DoD 子契约不可达
L3 force finalize degraded OR escalate-user → L2 失败 / budget 临界
```
  - § 5.4 信号源 6 种: hook output / subagent status / Verifier 中间评估 / context budget / time budget / cost budget
  - § 6.1 DoD 布尔表达式: 举 5 类任务各 1 例，强调**Python boolean eval 不 LLM 自报**；格式:
```
DoD = (artifact.path exists)
  AND (curl http://localhost:8000/produce returns 200)
  AND (mp4.duration > 0)
  AND (pytest exit_code == 0)
```
  - § 6.2 Verifier subagent: 执行/审查分离；只读权限；强制三动作（物理存在校验 / 重跑 DoD 命令 / 关键路径抽测）；FAIL 禁止汇报完成
  - § 6.3 三段证据链: 存在证据 / 行为证据 / 质量证据；缺一不可
  - § 6.4 假完成 trap catalog: "代码 push" / "build green" / "Phase X 通过" / "测试全过" / "LLM TERMINATE" / "Phase 4 通过即报完成" → 每条给【识别模式】【拦截动作】
- **MIRROR**: PRD § Top-level Architecture + § 三引擎详解 + § Supervisor Agent + web 调研 (AutoGen / LangGraph / Devin) 章节
- **IMPORTS**: N/A
- **GOTCHA**:
  - § 5.1 6 类干预每类**必须给具体例子**（如"忘开火 = PR 前没 lint"、"漏菜 = DoD 5 项做 3 项"）
  - § 6.1 DoD 表达式**必须给 5 类任务各 1 个真实可 eval 的例子**；禁止给口号清单
  - § 6.4 trap catalog 每条**必须写具体识别正则/关键词**，让主 skill/Supervisor 可以机器匹配
- **VALIDATE**:
  - § 5 读完能识别 10 个"Supervisor 该不该打断"的场景 ≥8 正确
  - § 6 DoD 5 例都能贴 eval 命令（不能有"验证 mp4 是对的"这种模糊）
  - § 6.4 trap catalog ≥5 条且每条有机器可匹配模式

### Task 6: 写 § 7 交付收口 + § 8 反模式 + § 9 索引
- **ACTION**: 产出进化引擎规则 + 反模式清单 + 新旧对照索引
- **IMPLEMENT**:
  - § 7.1 强制 post-mortem: 任务收口前必跑；retro report 11 项内容（DoD 实际 diff / 路线偏差 / 纠偏次数 / Verifier FAIL 次数 / 用户打断次数 / 耗时 vs 估算 / 成本 vs 估算 / 新 trap / 新有效组合 / 进化建议 / 下次推荐）
  - § 7.2 三类记忆分级写回:
    - route-outcome → routing-matrix.json 权重更新输入
    - anti-pattern → trap catalog 扩充输入
    - combination → 路由器候选池
  - § 7.3 failure-archive.jsonl: 结构化字段 schema（10+）；每 N 次触发权重审计；**失败记忆 > 成功记忆**
  - § 8 反模式 7 条:
    - 8.1 方案 C P20 假完成（自家，2026-04-16）—— 具体：method3 旧版方案 C 跑 P20，没起 uvicorn、没 POST /produce、没校验 mp4 时长/OSS key 就报完成；用户截图反馈"先手工 e2e 验一次再说"
    - 8.2 AutoGen is_termination_msg — LLM 说 "TERMINATE" 就终止 → 虚报完成
    - 8.3 CrewAI Hierarchical Manager LLM 全路由 → 不可审计 → 失败定位困难
    - 8.4 MetaGPT 硬 SOP → 灵活性差，新分支需改代码
    - 8.5 无界 retry 循环 → token budget 耗尽不终止
    - 8.6 post-mortem 遗忘（所有公开方案）→ 相同失败重复踩
    - 8.7 口号层"重视验证"而无机制 → 等于没说
    - 每条给【反模式特征】【造成的问题】【harnessFlow 如何规避】
  - § 9.1 新旧对照: 旧版每个 cell 指到新章节（如旧"XS→直接改"→ § 2.4 决策矩阵；旧"L→方案 C 混搭"→ § 4 路线规则 + § 6 验证）
  - § 9.2 场景 → 规则: "我要判断完成" → § 6；"我要选路线" → § 2+§ 4+routing-matrix.md；"我要纠偏" → § 5.3；"我要防假完成" → § 1.1 + § 6 + § 8；"我想改 method3" → § 7.3 进化流程
- **MIRROR**: PRD § Decisions Log + § Research Summary；memory feedback_real_completion + feedback_workflow_scheme_c
- **IMPORTS**: N/A
- **GOTCHA**:
  - § 8.1 方案 C 案例**必须写详细**（具体漏做了什么 / 用户怎么反馈 / 日期），这是用户启动 harnessFlow 的直接动因，不能轻写
  - § 9.1 必须完整覆盖旧版所有 cells，不能漏
- **VALIDATE**:
  - § 8 7 条每条 Why/问题/规避 三段
  - § 9.1 对旧版 35 行每条规则都有明确去向
  - 旧版读者 5 分钟内能通过 § 9 找到新 method3 对应章节

### Task 7: 写全文贯通 — 统稿与交叉引用
- **ACTION**: 把 Task 3-6 产出拼成完整 method3.md，检查章节间交叉引用正确 + 写 Frontmatter
- **IMPLEMENT**:
  - Frontmatter（如果加）/ 文件顶部一句话定位
  - § 顺序严格按 0→9
  - 章节互引（如 § 1 引 § 6 / § 2 引 § 4 / § 8.1 引 § 6 验证规则）全部可点击
  - 引到姐妹文档的指针: `详见 flow-catalog.md` / `详见 routing-matrix.md` / `详见 state-machine.md` / `详见 delivery-checklist.md` / `详见 task-board-template.md` / `详见 harnessFlow.md`
  - 版本号 + 日期: "v1.0 — 2026-04-16 — harnessFlow MVP"
  - 开头加"本文档与 harnessFlow 其他文档的关系"一段
- **MIRROR**: PRD 整体文风
- **IMPORTS**: N/A
- **GOTCHA**:
  - 不要提前 reference 到 Phase 2-8 里不存在的 section（那些文档还没写），用 "（Phase 3 产出，详见 flow-catalog.md）" 软引用
  - 保留中英术语一致性（DoD / Supervisor / Verifier / trap catalog / retro / failure-archive 全文统一）
- **VALIDATE**:
  - 文件总行数 ≥500（目标 700）
  - grep 所有章节 `## § N` 有 0 1 2 3 4 5 6 7 8 9 十节齐全
  - 每个 `详见 xxx.md` 的文件名拼写正确
  - `# method3` 文件头有一句话定位

### Task 8: 写入 + 更新 PRD
- **ACTION**: 落盘 + 更新 PRD Phase 1 status
- **IMPLEMENT**:
  - `Write` 工具写 `harnessFlow /method3.md`（覆盖旧版）
  - `Edit` 工具改 `harnessFlow /harness-flow.prd.md` Implementation Phases 表:
    - Phase 1 Status: `pending` → `in-progress`
    - Phase 1 PRP Plan 列: `-` → `plans/method3-refactor.plan.md`
- **MIRROR**: N/A
- **IMPORTS**: N/A
- **GOTCHA**: 目录带空格，Write 路径用绝对路径
- **VALIDATE**: `ls` 新 method3.md 大小 ≥15KB；PRD 改动过 git diff 可见

### Task 9: 端到端自验（真完成收口）
- **ACTION**: 按 Validation Commands 全跑一遍，写自检结论
- **IMPLEMENT**: 见下方 Validation Commands
- **MIRROR**: N/A
- **IMPORTS**: N/A
- **GOTCHA**: **不能只跑 "文件存在" 就报完成**（反模式 8.7）；必须跑内容校验
- **VALIDATE**: 见 Acceptance Criteria + Completion Checklist

---

## Testing Strategy

### Unit Tests
N/A — 纯文档任务无单元测试。

### Doc-level "tests"（替代单元测试）

| Check | Method | Expected |
|---|---|---|
| 章节齐全 | grep `^## § [0-9]` 数 10 个 | 0-9 十章 |
| 体量 ≥500 行 | `wc -l` | ≥500 |
| § 1 含真完成根原则 | grep "真完成" in § 1 | ≥3 处 |
| § 6 含 DoD 布尔表达式例 | grep `DoD =` in § 6 | ≥5 个例子 |
| § 8.1 含方案 C P20 事件 | grep "P20" + "方案 C" in § 8 | 两词共现 ≥1 段 |
| 每章有 Why + How + 反例 | 人工检查 | 各章齐全 |
| 交叉引用无死链 | grep `详见 xxx.md` 对应文件名与 PRD NOT Building 段一致 | 一致 |
| 术语统一 | grep 中英文混用一致性（DoD / Supervisor / Verifier / retro）| 全文一致 |

### Edge Cases Checklist
- [ ] 旧版 35 行每条规则在 § 9.1 都有明确去向
- [ ] § 1 三小节都有 Why + How + 反例
- [ ] § 6.1 DoD 例子真的可 Python eval（不是伪代码）
- [ ] § 6.4 trap catalog 每条有机器可匹配模式
- [ ] § 8 反模式 ≥7 条且每条三段
- [ ] § 9 新旧对照覆盖旧版所有 cells
- [ ] 引用到 Phase 2-8 文档时使用 "（Phase X 产出，详见 xxx.md）" 软引用
- [ ] 文件末尾版本号 + 日期

---

## Validation Commands

### 静态校验（文档层）
```bash
# 1. 章节齐全 — 应输出 10 行
grep -c "^## § [0-9]" "/Users/zhongtianyi/work/code/harnessFlow /method3.md"
```
EXPECT: `10`

```bash
# 2. 体量达标 — 应 ≥500 行
wc -l "/Users/zhongtianyi/work/code/harnessFlow /method3.md"
```
EXPECT: `≥ 500`

```bash
# 3. 真完成词频 — 应 ≥8 次
grep -c "真完成" "/Users/zhongtianyi/work/code/harnessFlow /method3.md"
```
EXPECT: `≥ 8`

```bash
# 4. DoD 布尔表达式样例 — 应 ≥5
grep -cE "DoD = \(" "/Users/zhongtianyi/work/code/harnessFlow /method3.md"
```
EXPECT: `≥ 5`

```bash
# 5. 方案 C + P20 共现 — 应在 § 8 段落
grep -A 10 "§ 8" "/Users/zhongtianyi/work/code/harnessFlow /method3.md" | grep -E "(P20|方案 C)"
```
EXPECT: 至少返回 P20 + 方案 C 两词

```bash
# 6. 交叉引用 — 姐妹文档文件名拼写
grep -oE "详见 [a-zA-Z.-]+\.md" "/Users/zhongtianyi/work/code/harnessFlow /method3.md" | sort -u
```
EXPECT: `详见 flow-catalog.md / routing-matrix.md / state-machine.md / task-board-template.md / delivery-checklist.md / harnessFlow.md / harness-flow.prd.md` 子集且拼写正确

### 行为校验（读者层 — 人工）
- [ ] 打开 method3.md，5 分钟内抓到 3 个核心原则（§ 1 三小节）
- [ ] 拿一个具体任务（如"给 aigc 后端加素材源"），依 § 2 能完成体量 × 类型 × 风险判定
- [ ] 依 § 6.1 能写出该任务的 DoD 布尔表达式
- [ ] 依 § 5 能判断 Supervisor 该不该打断某个场景
- [ ] 依 § 9.1 能从旧版 3 条硬规则任意一条找到新章节去向

### 质量校验（与 PRD 对齐）
- [ ] PRD Phase 1 Success signal: "文档 ≥ 旧版 5 倍体量" → 实测 ≥14x ✅
- [ ] PRD MoSCoW Must: 7 条（主 skill 引用 / Supervisor / DoD / task-board 相关 / 路线 C / 9 输出物 / 重构 method3）→ 全覆盖
- [ ] PRD Decisions Log 10 条每条在 method3 有对应显式规则

---

## Acceptance Criteria

- [ ] 所有 9 个 Task 完成
- [ ] 所有 Validation Commands PASS
- [ ] § 0-9 十章齐全
- [ ] 文件 ≥500 行（目标 700）
- [ ] § 1 + § 6 每节含 Why + How + 反例
- [ ] § 6.1 DoD 布尔表达式样例 ≥5 个真实可 eval
- [ ] § 6.4 trap catalog ≥5 条且含机器可匹配模式
- [ ] § 8.1 含完整方案 C P20 事件描述
- [ ] § 9.1 完整覆盖旧版 35 行每条规则去向
- [ ] PRD Phase 1 状态 pending → in-progress，PRP Plan 列填本文件路径

## Completion Checklist

- [ ] 代码跟随 PRD 文风（中英混用 / 每节 Why+How+反例 / 表格视觉锚点 / 无 emoji / 无 fluff）
- [ ] 错误处理 N/A（纯文档）
- [ ] 日志 N/A
- [ ] 测试 → 替代为 doc-level check（见 Testing Strategy）
- [ ] 无 hardcoded 具体 skill 版本号（method3 是方法论，不是速查表）
- [ ] 引用姐妹文档用软引用（"（Phase X 产出）"）避免死链
- [ ] 未添加范围外章节（路由矩阵/状态机/任务表/主 skill prompt 都留给后续 Phase）
- [ ] 自包含 — 实施时不需再问问题

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| method3 写成口号层缺机器可执行规则 | H | H | § 1.1 和 § 6.1 强制 "Python boolean eval 例子 ≥5 个"；Task 5 Validate 含此强检查 |
| 和 flow-catalog.md / routing-matrix.md 重复维护 | M | M | § 3 § 4 严格字数控制 50-80 行；细节一律用 "详见 xxx.md"；Task 4 GOTCHA 明确 |
| 方案 C P20 事件写得太模糊 | M | H | Task 6 强制详细（漏做什么 / 用户怎么反馈 / 日期）；§ 8.1 单独成小节 |
| 交叉引用到未产出文档出现"死链"观感 | L | L | 统一用"（Phase X 产出，详见 xxx.md）"软引用；Task 7 VALIDATE 检查 |
| 旧版 3 条硬规则漏继承 | M | M | § 9.1 强制每条显式映射；Task 6 VALIDATE 检查 |
| 文风不统一，读起来像多人写的 | M | L | Task 7 统稿步骤专门做；所有子任务 MIRROR 都指向 PRD 文风 |
| 术语中英文不一致（DoD / Definition of Done / 定义-完成）| M | L | Task 7 术语统一检查；建议英文术语保留原形，中文解释在首次出现时 |

## Notes

- **这是 harnessFlow 的奠基文档**，所有后续 Phase (2-8) 的文档都会引用 method3 的章节作为规则源头。写得质量不达标，下游全偏。
- Phase 1 实施完毕后下一步 = `/prp-implement harnessFlow /plans/method3-refactor.plan.md`（本文件）；之后顺着 PRP 流程 `/santa-loop` → `/prp-commit` → `/prp-pr`。
- **真完成自检**（本 plan 自己也要真完成）: 本文件完成标准 = 后续实施者按此 plan **无需再问任何问题** 就能一次性产出符合 Acceptance Criteria 的 method3.md。
- 若实施中发现漏项，回本 plan 加 Task / 改 Task，然后继续；不直接偏离 plan。
