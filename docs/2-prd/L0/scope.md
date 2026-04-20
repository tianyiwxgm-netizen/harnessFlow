# HarnessFlow 产品范围规格说明书（Scope Spec）

> 版本：v1.0（scope 主体完成 · L1 + §8 集成闭环）
> 更新时间：2026-04-20
> 配套文档：`HarnessFlowGoal.md`（Why）+ `businessFlow.md`（How does it flow）
> 本文件回答：HarnessFlow 作为产品，**范围是什么 + 能力如何分层 + 边界在哪 + 各能力如何衔接 + 主 skill / 监督 skill / UI 如何承载**

---

## 0. 撰写进度

- [x] 第 1 章 · 范围总览 + 文档定位 + 上下游关系
- [x] 第 2 章 · L1 能力地图（10 个，一句话职责）
- [x] 第 3 章 · L1 × 主 skill / 监督 skill / UI 映射（总览）
- [x] 第 4 章 · 产品范围粗线条（In-Scope / Out-of-Scope / 边界消歧）
- [x] 第 5 章 · L1 详细定义（10 个 L1 全部完成，含 职责 / 输入输出 / 边界 / 约束 / 🚫 禁止行为 / ✅ 必须义务 / 交互）
- [x] 第 6 章 · 每 L1 独立文档索引（L2/L3 移出 scope.md，每 L1 单独文档）
- [x] 第 7 章 · L1 集成验证大纲（4 层级 + 硬约束 + 失败处理）
- [x] 第 8 章 · L1 间产品业务流（关键整合 · 4 类关系图 + 20 条 IC 契约 + 5 典型端到端场景 + 集成约束 + 失败传播规则）
- [ ] 第 9 章 · UI 交互功能全景（后续轮次）
- [ ] 附录 A · L1 ↔ businessFlow 聚类映射表
- [ ] 附录 B · L1 ↔ Goal 追溯矩阵
- [ ] 附录 C · 术语速查

---

## 1. 范围总览

### 1.1 定位（引自 Goal §1）

> HarnessFlow 是一个 Claude Code Skill 生态下的 "AI 技术项目经理 + 架构师"——以 PMP + TOGAF 双主干方法论 + 5 大纪律为骨架，从"项目目标 + 资源约束"出发，以 methodology-paced 自治方式端到端推进一个超大型复杂软件项目。

本文件从"**产品范围**"视角回答：**这个产品到底要建成什么样子 / 它能做什么 / 它不做什么**。

### 1.2 本文档回答的 3 个核心问题

1. **做哪些 / 不做哪些？** —— 产品能力边界（In-Scope / Out-of-Scope）。
2. **能力如何分层？** —— L1 / L2 / L3 粒度的产品能力地图。
3. **各能力之间如何衔接？** —— 控制流 / 数据流 / 监督流 / 持久化流。

### 1.3 文档与上下游关系

```
┌─────────────────────────────────────┐
│ HarnessFlowGoal.md (Why)             │  方向 / 意图
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ businessFlow.md (How does work flow) │  业务流 / 流程编织
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ scope.md (What the product is)       │ ← YOU ARE HERE
│ · L1 能力地图                         │
│ · 主 skill / 监督 skill / UI 映射     │
│ · 范围边界                             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ systemArchitecture.md (How built)    │  下游 · 技术架构
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ prd.md (What each feature looks)     │  下游 · 产品特性
└──────────────┬──────────────────────┘
               ↓
  plan / tdd / code / ui
```

### 1.4 撰写原则：总 → 分

本文件**分阶段撰写**，每轮用户 review 后推进下一轮：

| 轮次 | 产出 | 对应章节 |
|---|---|---|
| **本轮 v0.1** | 总 layer — L1 地图 + 映射 + 范围粗线条 | §1-§4 |
| 下一轮 v0.2 | L1 详细定义（职责/边界/约束/交互） | §5 |
| 再下一轮 v0.3 | L2 子能力分解 | §6 |
| 再下一轮 v0.4 | L3 细粒度能力 | §7 |
| 再下一轮 v0.5 | 关系图 + UI 交互全景 | §8-§9 |

**不一次性写完**，防止过早锁死未想清楚的细节。

### 1.5 派生方法论（非假设）

L1 能力**不是自上而下假设**，是从 `businessFlow.md` 的 ~65 条业务流**聚类**派生：
- 每个 L1 = 一个"职责聚合簇"
- L1 边界 = 聚类内所有流的共同责任面
- L1 之间的交互 = 跨聚类的流衔接点

聚类证据链见附录 A（L1 ↔ businessFlow 映射表）。

---

## 2. L1 能力地图（10 个）

### 2.0 L1 / L2 / L3 / 集成 语义澄清（2026-04-20 用户对齐）

> ⚠️ scope.md 里 L1 / L2 / L3 的含义**独立于** businessFlow.md 的流层级。
>
> **本 scope.md（产品方案）语境**：
> - **L1 能力域**（10 个）：顶层产品能力，每个 L1 定义独立职责边界
> - **L2 子能力**：每个 L1 **内部的细化拆解**（L2 属于 L1 的内部结构）
> - **L3 实现设计**：每个 L1 的**实际实现设计**（产品视角描述"这个 L1 对外提供什么功能、内部如何运作"；**不含技术栈 / 语言 / 库选型**）
> - **L1 间集成**：基于 L1 边界 + 接口 + 约束的**整体集成设计**（§8）
>
> **下游**：scope.md 完整（含 L1 + L2 + L3 + 集成 + UI 全景）→ 才进入技术架构 / 技术方案设计（另行产出，不在 scope.md 内）。
>
> **businessFlow.md（业务流）里**：L1/L2/L3 仍是业务流层级（主流程 / 分子流 / 活动细节），与本文档**同名但含义不同**，不要混淆。

### 2.0a 本 scope 文档各层级产出对照

| 层级 | 粒度 | 预计规模 | 本文档产出章节 |
|---|---|---|---|
| **L1 能力域** | 顶层产品能力 | 10 个 | §5 · L1 详细定义（职责/边界/输入输出/约束/交互） |
| **L2 子能力** | 每 L1 内部 3-5 个 | ~35 个 | §6 · L2 子能力分解 |
| **L3 实现设计** | 每 L1 一份实现设计（产品视角） | ~10 份 | §7 · L3 实现设计 |
| **L1 间集成** | 跨 L1 协同：4 类关系 + 典型场景 | 3-5 场景 | §8 · L1 间产品业务流 |
| **UI 全景** | 用户可见功能 | 现 11 tab+9 admin + 新增 | §9 · UI 交互全景 |

### 2.1 L1 清单（本轮只到"一句话职责"）

| ID | L1 能力名 | 一句话职责 | 现状 |
|---|---|---|---|
| **L1-01** | 主 Agent 决策循环能力 | 持续 tick → 查 KB + 拷问 5 纪律 → 决策下一步动作 → 执行 + 留痕 | 🔴 需新建（现 harnessFlow 是被动 skill，非持续 loop） |
| **L1-02** | 项目生命周期编排能力 | 7 阶段 × Stage Gate × 产出物模板推进 PMP+TOGAF 双主干 + 4 件套生产 | 🟡 state-machine.md 雏形，需重写 |
| **L1-03** | WBS + WP 拓扑调度能力 | 超大项目拆 WP 拓扑 → 1-2 个并行 → WP 级 mini-PMP → 拓扑依赖判定 | 🔴 需新建 |
| **L1-04** | Quality Loop 能力 | TDD 蓝图生成 → 执行 → TDDExe 独立验证 → 4 级回退路由 → 死循环保护 | 🟡 verifier 原语已有，需封装 Loop + 回退路由 |
| **L1-05** | Skill 生态 + 子 Agent 调度能力 | 能力抽象层匹配 skill / 委托独立 session 子 Agent / 工具柜原子调用 / 失败降级 | 🟡 flow-catalog + 4 subagent 有基础 |
| **L1-06** | 3 层知识库能力 | Global / Project / Session 存储 + 按阶段注入策略 + 候选→晋升仪式 | 🟡 mock 数据 + UI 已有 |
| **L1-07** | Harness 监督能力 | 8 维度观察 + 4 级干预（INFO/SUGG/WARN/BLOCK）+ 软红线 8 类自治 / 硬红线 5 类上报 | 🟡 supervisor.md 定义 + UI 监督模块 |
| **L1-08** | 多模态内容处理能力 | 读写 md / 读代码结构（AST+Grep）/ 读图片（架构图/截图/UI mock） | 🔴 需新建 |
| **L1-09** | 韧性 + 审计能力 | 事件总线单一事实源 + 跨 session 无损恢复 + 审计追溯链 + 异常降级 | 🟡 task-boards/retros 有基线，需统一事件总线 |
| **L1-10** | 人机协作 UI 能力 | 看板 / 决策轨迹 / 架构图 / Stage Gate 待办 / 交付物预览 / 后台管理 / 干预台 | 🟡 UI mock 基线已建（11 tab + 9 admin），需升级 |

图例：🟢 已有复用 · 🟡 部分有需升级 · 🔴 需新建

### 2.2 L1 之间 4 类典型关系（摘要；详细图见下一轮 §8）

```
       ╭─────────────╮
       │ L1-01 主 loop │ ── 控制流 ──→ 驱动 L1-02 / 03 / 04 / 05 / 06 / 08
       ╰──────┬──────╯
              │
              │  ↕ 生产-消费链
              │
   [L1-02 4件套] → [L1-04 TDD 蓝图] → [L1-03 WP 调度] → [L1-04 执行+TDDExe] → [L1-02 交付]
              │
              │  观察-干预 (旁路)
              │
       ╭──────┴──────╮
       │ L1-07 监督    │ ── INFO/SUGG → L1-01 / 04
       │             │ ── WARN → L1-10 UI 告警
       │             │ ── BLOCK → L1-01 硬暂停
       ╰─────────────╯
              │
              │  单一事实源
              ↓
       ╭─────────────╮
       │ L1-09 事件总线│ ← 所有 L1 的事件都进
       ╰──────┬──────╯
              ↓
       ╭─────────────╮
       │ L1-10 UI     │ ← 消费事件总线 + 展示
       ╰─────────────╯
```

- **控制流**：L1-01 统一调度
- **生产-消费**：L1-02 ↔ L1-04 ↔ L1-03 ↔ L1-02 形成主干链
- **观察-干预**：L1-07 旁路，有硬拦截权
- **单一事实源**：所有 L1 → L1-09 事件总线 → L1-10 UI 消费

---

## 3. L1 × 主 skill / 监督 skill / UI 映射（总览）

HarnessFlow 在 Claude Code 生态里由 **3 个"载体"**对外呈现：

1. **主 skill**：`/harnessFlow`（或 `/harnessFlow-v2`）— 用户唯一直接触发的 slash command
2. **监督 skill**：`harnessFlow:supervisor` — 常驻旁路 subagent
3. **UI**：`localhost:8765` Web 界面

**每个载体承担哪些 L1，下面是映射总览。**

### 3.1 主 skill `/harnessFlow` 的职责承载

主 skill 是整栋楼的"大门 + 大厅 + 电梯"：用户从主 skill 进入，主 skill 内部运行主 Agent loop，驱动所有业务。

| 主 skill 承担的事 | 对应 L1 |
|---|---|
| 接收用户输入（目标 + 资源 + 启动模式） | L1-01 决策循环（入口）+ L1-10 UI（输入面板） |
| 驱动 7 阶段项目生命周期 | **L1-02 项目生命周期编排** |
| WBS 拆解 + WP 拓扑推进 | **L1-03 WBS + WP 拓扑调度** |
| Quality Loop 执行（S3 TDD 蓝图 → S4 执行 → S5 TDDExe） | **L1-04 Quality Loop** |
| 决策调什么 skill / 工具 / 子 Agent | **L1-01 决策循环** + **L1-05 Skill & 子 Agent 调度** |
| 读写 3 层知识库 | **L1-06 知识库** |
| 读代码 / 读文档 / 读图片 | **L1-08 多模态内容处理** |
| 每个 decision / event 落事件总线 | **L1-09 韧性 + 审计** |
| 生成 PMP / TOGAF 产出物 | L1-02 编排内部 |

**主 skill 承载 8 个 L1**：L1-01 / L1-02 / L1-03 / L1-04 / L1-05 / L1-06 / L1-08 / L1-09

### 3.2 监督 skill `harnessFlow:supervisor` 的职责承载

监督 skill 是旁路独立 subagent，只读观察主 skill 工作。不直接执行业务动作，只通过分级建议通道影响主 skill。

| 监督 skill 承担的事 | 对应 L1 |
|---|---|
| 常驻观察（每 30s tick + PostToolUse hook） | **L1-07 Harness 监督** |
| 8 维度指标计算（目标保真度 / 计划对齐 / 真完成质量 / 红线安全 / 进度节奏 / 成本预算 / 重试 Loop / 用户协作） | **L1-07** |
| 4 级干预（INFO / SUGGESTION / WARN / BLOCK） | **L1-07** + L1-10 UI 告警推送 |
| 软红线 8 类自治修复 | **L1-07** + L1-09 事件总线触发动作 |
| 硬红线 5 类硬拦截 | **L1-07** + L1-01 暂停主 loop + L1-10 UI 强通知 |
| 偏差 4 级回退路由（轻/中/重/极重） | **L1-07** + L1-04 Quality Loop 接收回退指令 |
| 死循环保护（同级 ≥3 次 → 自动升级） | **L1-07** |

**监督 skill 承载 1 个主 L1（L1-07）+ 横切干预 L1-01/04/09/10**

### 3.3 UI 的职责承载（现有 mock 基线）

UI 承担 L1-10 本身，并把其他 L1 的状态可视化消费。

#### 3.3.1 任务详情 11 tab（现有）

| UI tab | 承载 L1 |
|---|---|
| 📘 项目交付目标 | L1-02（S1 章程 + goal_anchor） |
| 📏 项目范围 | L1-02 + 本 scope.md 引用 |
| 📖 项目资料库 | L1-06 知识库 + L1-08 文档清单 |
| ✅ TDD 质量 | **L1-04 Quality Loop**（核心视图） |
| 🛡️ Harness 监督 | **L1-07 Harness 监督**（核心视图） |
| 🔧 项目 WBS 工作包 | **L1-03 WBS + WP 拓扑** |
| ⏱️ 执行时间轴 | L1-09 事件总线渲染 |
| 📂 产出物链接 | L1-02 产出物清单 |
| 🔄 Loop 历史 | L1-04 + L1-01 决策心跳轨迹 |
| 📦 交付 Bundle | L1-02（S7 收尾产出） |
| 🔍 Verifier 证据链 | L1-04（S5 TDDExe 三段证据链） |

#### 3.3.2 后台管理 9 模块（现有）

| UI 后台模块 | 承载 L1 |
|---|---|
| ⚙️ 执行引擎配置 | L1-01 + L1-02 + L1-05（横切配置） |
| 🚀 执行实例 | L1-01 + L1-09（运行时状态） |
| 📚 知识库 | **L1-06**（核心视图） |
| 🛡️ Harness 监督智能体 | **L1-07**（核心视图） |
| 🔬 Verifier 原语库 | L1-04（原语工具层） |
| 🤖 Subagents 注册表 | **L1-05 子 Agent**（核心视图） |
| 🧩 Skills 调用图 | **L1-05 Skill 生态**（核心视图） |
| 📊 统计分析 | 跨 L1 横向视图 |
| 🔍 系统诊断 | 跨 L1 + L1-09 一致性校验 |

### 3.4 需要新增的 UI（下一轮 §9 详述）

对照 10 个 L1 清单，现有 UI mock 有以下缺口，**后续需补**：

| 缺口 | 对应 L1 | 优先级 |
|---|---|---|
| Quality Loop 动态视图（TDDExe 实时 verdict + 4 级回退路径可视化） | L1-04 | P0 |
| 4 件套产出物视图（需求 / 目标 / 验收 / 质量 4 份文档专门展示） | L1-02 | P0 |
| 决策轨迹走廊（L1-01 每次 tick 决策链的顺序浏览 + 原因 + 监督点评） | L1-01 | P0 |
| Stage Gate 待办中心（跨所有项目的待审 Gate 集中视图） | L1-02 + L1-10 | P1 |
| 多模态内容展示（代码结构图 / 架构图 / 截图预览） | L1-08 | P1 |
| 红线事件告警角（实时推送软/硬红线告警） | L1-07 | P0 |
| 审计追溯查询面板（从代码行反查决策） | L1-09 | P1 |
| Loop 触发统计面板（事件驱动/周期驱动/Hook 驱动 比例） | L1-01 | P2 |

### 3.5 3 个载体之间的协作

```
  用户
    ↓ (slash command / UI 交互)
┌─────────────────────────────────────┐
│ 主 skill /harnessFlow                │
│ · 运行主 Agent loop (L1-01)          │
│ · 驱动项目生命周期 (L1-02 至 L1-06, 08, 09) │
└──────┬──────────────────┬───────────┘
       │                  │
       │ 事件总线          │ 调用
       ↓                  ↓
┌─────────────────┐  ┌─────────────────────────┐
│ L1-09 事件总线   │  │ 监督 skill :supervisor   │
│ (持久化)         │  │ · 8 维度观察 (L1-07)     │
└────┬────────────┘  │ · 4 级干预                │
     │                │ · 红线分级处理             │
     │                │ · 回退路由                 │
     │                └──────────┬──────────────┘
     │                           │
     │                           │ 建议/告警/硬拦截
     │                           │
     │                           ↓
     │                    回主 skill (L1-01)
     │
     ↓
┌─────────────────────────────────────┐
│ UI localhost:8765                    │
│ · 消费事件总线 + 监督事件流           │
│ · 11 tab 任务详情 + 9 admin 模块     │
│ · 用户干预入口 (Stage Gate / 授权)   │
└─────────────────────────────────────┘
```

---

## 4. 产品范围粗线条

### 4.1 In-Scope（10 个 L1 覆盖范围）

HarnessFlow 作为一个 Claude Code Skill，**做且仅做**以下 10 类能力（L1-01 至 L1-10 的职责聚合）：

1. 运行主 Agent 决策 loop（L1-01）
2. 编排 PMP+TOGAF 7 阶段项目生命周期（L1-02）
3. 调度 WBS + WP 拓扑（L1-03）
4. 运行 Quality Loop（TDD 定义 + 执行 + TDDExe）（L1-04）
5. 调度外部 skill 生态 + 委托子 Agent（L1-05）
6. 读写 3 层知识库（L1-06）
7. 常驻 Harness 监督（L1-07）
8. 处理多模态内容（md / 代码 / 图片）（L1-08）
9. 事件总线 + 持久化 + 审计 + 异常韧性（L1-09）
10. 提供人机协作 UI（L1-10）

### 4.2 Out-of-Scope（明确不做，引自 Goal §6）

1. 不替代 AI 工程师（写代码交给下层 skill）
2. 不替代 PM 工具（不做 Jira / Linear 看板）
3. 不做通用 Agent 框架
4. 不追求"零人工介入"（三阶段必须人类参与是 feature）
5. 不做 Scrum / 敏捷 Master Agent
6. 不做非软件类项目
7. 不做商业 SaaS（开源 Claude Code Skill 形态）
8. 不自研 LLM
9. 不做 CI/CD 流水线
10. 不做移动端 / 桌面端 App（UI 只有 localhost Web）
11. V1-V2 不做跨项目并行（同时只管一个项目）

### 4.3 边界模糊地带 + 消歧声明

以下情形初看在 in-scope 边界，但本产品 **明确不做**：

| 情形 | 看似属于 | 实际不做的理由 |
|---|---|---|
| "智能补全代码" | L1-01 决策循环 | 由下层 skill（`tdd` / `prp-implement`）承担；L1-01 只调度不直接补全 |
| "SQL 优化建议" | L1-08 代码分析 | 专业 DB 技能不是 L1-08 职责；走外部 `database-reviewer` 子 Agent |
| "生产部署" | L1-02 S7 收尾 | S7 只产出 commit + PR；部署交人类或外部 CI |
| "设计师对接" | L1-10 UI | 本产品只做 dev-oriented UI（localhost Web）；不含 Figma / Sketch 同步 |
| "多项目协同" | L1-01 主 Agent | V1-V2 单项目；V3 才考虑 |
| "自研知识图谱 / 向量库" | L1-06 知识库 | 3 层 KB 走 jsonl + markdown 文件存储；不自建向量检索 |
| "Agent 性能调优" | L1-01 / L1-05 | 交给 Claude 主模型；本产品只做编排不优化模型推理 |
| "多语言支持" | L1-10 UI | UI 只做中 / 英双语（Goal §软装可调），不支持其他 |

### 4.4 范围扩展候选（V3+ 的潜在方向，本 Scope 不做）

列出但明确 V3+ 才考虑，避免 scope creep：

- 跨项目并行管理
- 团队协作（多用户同时干预一个项目）
- 外部 webhook 推送（Slack / 飞书）
- 项目模板市场
- AI 架构师独立付费能力（SaaS 商业化）

### 4.5 全局业务模式（PM）清单

贯穿所有 L1 的 14 条业务模式（Pattern-of-Mind · PM-01 ~ PM-14）：

| PM | 名称 | 一句话 |
|---|---|---|
| **PM-01** | methodology-paced 节奏 | S1/S2/S3 强协同、S4/S5/S6 自走、S7 强 Gate |
| **PM-02** | 主-副 Agent 协作 | 只读 supervisor 建议，不改 supervisor 状态 |
| **PM-03** | 子 Agent 独立 session 委托 | 只读 context 副本 + 结构化回传，禁 session 间共享状态 |
| **PM-04** | WP 拓扑并行推进 | 同时最多 1-2 个 WP 并行（防认知爆炸）|
| **PM-05** | Stage Contract 机器可校验 | DoD 走白名单 AST eval，禁 arbitrary exec |
| **PM-06** | KB 三层 + 阶段注入 | session / project / global 三层 + 阶段切换主动注入 |
| **PM-07** | 产出物模板驱动 | 所有产出按标准模板，无消费者不产出 |
| **PM-08** | 可审计全链追溯 | 决策可追溯率 100% · 三段证据链完整 |
| **PM-09** | 能力抽象层调度 | 主 Agent 绑"能力点"不绑 skill 名；每能力 ≥ 2 备选 |
| **PM-10** | 事件总线单一事实源 | 所有决策必经事件总线（**按 project_id 分片**） |
| **PM-11** | 5 纪律贯穿 | 规划/质量/拆解/检验/交付每关键决策前强制拷问 |
| **PM-12** | 失败也要闭环 | 任何终态（SUCCESS / FAILED）都必走 retro + archive |
| **PM-13** | 合规可裁剪 | 3 档裁剪（完整 / 精简 / 自定义）不得违背 L1 硬约束 |
| **PM-14** | **project-id-as-root（新增）** | **`harnessFlowProjectId` 是所有数据归属根键 + 多项目 / 多会话隔离键；所有 IC 通信必须携带**。详见 `docs/2-prd/L0/projectModel.md` |

### 4.6 PM-14 衍生硬约束（对所有 L1 适用）

1. **任何数据条目必须归属一个 `project_id`**（global 层 KB 除外）
2. **所有 IC 通信必须携带 `project_id` 字段**（或显式标 `project_scope: "system"` 表示系统级 IC）
3. **跨 project 引用必须拷贝数据**（不做软链接 / 直接引用）
4. **事件总线 / 审计 / 监督事件必须按 project 物理隔离**（分目录 / 分 jsonl 文件）
5. **归档后的 project 数据保留至少 90 天**（可配置）
6. **删除 project 是强操作 + 二次确认 + 全连带删除**（global 层晋升条目不删）
7. **Supervisor 必拦截"无 project_id 的事件"**（归入"契约违规"维度）

详细归属清单、生命周期、主状态机、目录模型、多项目并发规则 → 见 `docs/2-prd/L0/projectModel.md`。

---

## 5. L1 详细定义（分批撰写 · 每 L1 锚定 Goal + businessFlow）

### 5.0 撰写原则

每个 L1 严格锚定两份基础文档：
- **Goal 锚定**：L1 职责引自 `HarnessFlowGoal.md` 的具体章节
- **businessFlow 锚定**：L1 边界和交互引自 `businessFlow.md` 的 BF 编号

分 3 批撰写，每批 3-4 个 L1：

- **批次 A（本轮 v0.2）**：L1-01 / L1-02 / L1-03 / L1-04 —— 执行引擎核心
- 批次 B（下一轮）：L1-05 / L1-06 / L1-07 —— 生态调度 + 记忆 + 监督
- 批次 C（再下一轮）：L1-08 / L1-09 / L1-10 —— 内容 + 韧性 + UI

---

### 5.1 L1-01 · 主 Agent 决策循环能力

#### 5.1.1 职责

HarnessFlow 的**心脏**。持续 tick → 每个 tick 做一个原子决策 → 执行 → 留痕。所有其他 L1 都被本 L1 驱动或被调用，是 HarnessFlow 的**控制流唯一源**。

**锚定**：
- Goal §1 "以主 Skill Agent loop 为执行核心"（一句话目标）
- Goal §2 产品定位 "是"第 2 条："以主 Skill Agent loop 为执行核心"
- BF-L3-01 决策心跳 tick 流（核心业务流）
- BF-L3-12 loop 触发机制流
- BF-L3-13 阶段切换触发流
- BF-L3-14 决策（skill / 工具 / 任务链）选择流
- BF-X-01 主 Agent 决策心跳（横切）

#### 5.1.2 输入 / 输出

**输入**：
- 事件总线新事件（BF-L3-12 触发条件）
- 当前 task-board 状态（读自 L1-09）
- Supervisor 建议队列（来自 L1-07）
- KB 注入内容（来自 L1-06）
- 用户输入事件（来自 L1-10）

**输出**：
- 一次"下一步动作"决策（BF-L3-01）
- 决策事件 → 事件总线（落盘到 L1-09）
- 执行动作（调 skill / 工具 / 子 Agent / KB 读写 / 请示用户 / state 转换等）
- state 转换事件（若阶段切换，告知 L1-02）

#### 5.1.3 边界

**In-scope**（本 L1 做）：
- tick 循环机制 + 4 种触发源（事件 / 主动 / 周期 / hook）
- 决策树分派（需要澄清 / 需要能力 / 需要验证 / 需要记忆）
- 5 纪律拷问（BF-L3-11）
- KB 相关条目注入到决策上下文
- 决策留痕（自然语言理由 + 事件落盘）
- tick 调度优先级（事件驱动 > 主动 > 周期）

**Out-of-scope**（委托给别的 L1）：
- 不自己写代码 → 委托 L1-05 调 `tdd` / `prp-implement` skill
- 不自己跑测试 → 委托 L1-04 Quality Loop 驱动 + L1-05 调 verifier 子 Agent
- 不自己做业务规划 → 委托 L1-02 驱动 `writing-plans` skill
- 不自己做异常恢复 → 走 L1-09 持久化机制

**边界规则**：只做"决策 + 调度 + 留痕"，不做具体"业务操作"。

#### 5.1.4 约束

- **PM-02 主-副 Agent 协作**：只读 supervisor 建议，不改 supervisor 状态
- **PM-10 事件总线单一事实源**：所有决策必经事件总线
- **PM-11 5 纪律贯穿**：每关键决策前强制 5 纪律拷问，任一 N 先补齐
- **硬约束 1**：单 session 内只有一个主 Agent loop 实例（Goal §3.5 硬约束 8）
- **硬约束 2**：任一 tick 失败必须记录原因，不得静默失败
- **硬约束 3**：决策理由必须是自然语言可审计文本（Goal §4.1 "决策可追溯率 100%"）
- **硬约束 4**：tick 调度不得被阻塞 > 30s 无反应（健康心跳）

#### 5.1.5 🚫 禁止行为（明确清单）

- 🚫 **禁止直接改 task-board**（必经 L1-09 `append_event`）
- 🚫 **禁止跳过 5 纪律拷问**（每关键决策前必过 5 问）
- 🚫 **禁止单 session 启多个 loop 实例**（Goal §3.5 硬约束 8）
- 🚫 **禁止 tick 静默失败**（任一失败必留原因 + 事件）
- 🚫 **禁止未经 KB 注入直接决策**（阶段开始时必注）
- 🚫 **禁止跨越 state_machine.allowed_next 强制转换**

#### 5.1.6 ✅ 必须义务（明确清单）

- ✅ **必须**每 tick 留自然语言决策理由（Goal §4.1 "决策可追溯率 100%"）
- ✅ **必须**响应 supervisor BLOCK 指令（立即暂停 tick）
- ✅ **必须**保证 tick 响应 ≤ 30s（否则触发健康心跳告警）
- ✅ **必须**走 L1-09 事件总线记录所有 decision / tool call / skill call / KB 读写
- ✅ **必须**在阶段切换前查 `allowed_next`，合法才触发
- ✅ **必须**在收到 supervisor WARN 后书面回应（采纳或驳回+理由）

#### 5.1.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-02 生命周期编排 | 控制流 | 驱动 → | state 转换触发请求 | BF-L3-13 |
| L1-03 WBS+WP 调度 | 控制流 | 驱动 → | "取下一 WP" 请求 | BF-S4-01 |
| L1-04 Quality Loop | 控制流 | 驱动 → | 进入 S3/S4/S5 阶段指令 | BF-S3/S4/S5 入口 |
| L1-05 Skill+子 Agent | 控制流 | 调用 → | "调 skill X" / "委托子 Agent Y" | BF-L3-02 / 03 |
| L1-06 知识库 | 数据流 | 读 ↔ 写 | KB 读（入阶段）/ 写（session 候选） | BF-L3-05 |
| L1-07 监督 | 观察-干预 | 接收 ← | supervisor 建议 / 告警 / 硬拦截 | BF-X-02 |
| L1-08 多模态内容 | 控制流 | 调用 → | 读文档 / 代码 / 图片请求 | BF-L3-06 / 07 / 08 |
| L1-09 韧性+审计 | 持久化 | 写 → | decision + event 落总线 | BF-X-03 |
| L1-10 UI | 输入-输出 | 接收 ← / 推送 → | 接用户输入 / 推决策轨迹 | BF-L3-09 |

---

### 5.2 L1-02 · 项目生命周期编排能力

#### 5.2.1 职责

推进 **7 阶段主骨架**（S1 启动 → S2 规划+架构 → S3 TDD 规划 → S4 执行 → S5 TDDExe → S6 监控 → S7 收尾），管理 **4 次 Stage Gate**，维护 PMP 5 过程组 × TOGAF 9 ADM 二维矩阵的当前格子，驱动**所有 PMP + TOGAF 产出物**（含 4 件套）的生产。

**锚定**：
- Goal §2.2 双层骨架（主骨架 PMP × TOGAF + 5 纪律横切）
- Goal §3.3 methodology-paced autonomy（三段协同度节奏）
- Goal §3.2.B 完整 PMP 产出物包 · §3.2.C 完整 TOGAF 产出物包
- BF-S1 全部（启动阶段 4 条 L2）
- BF-S2 全部（规划+架构阶段 9 条 L2，含 4 件套 + 9 计划 + TOGAF A-D + WBS + ADR）
- BF-S3 全部（TDD 规划阶段 5 条 L2）
- BF-S7 全部（收尾阶段 5 条 L2）
- BF-L3-10 方法论驱动决策流
- BF-X-06 产出物模板驱动流

#### 5.2.2 输入 / 输出

**输入**：
- L1-01 的 state 转换请求（BF-L3-13）
- 4 件套生成依据：章程 + goal_anchor（from S1）
- 9 大计划输入：4 件套作为前置（BF-S2-05）
- TOGAF A-D 架构依据：4 件套 + 9 计划（BF-S2-06）
- WBS 产出：from L1-03（但 4 件套+架构是 L1-03 的输入，这是反向依赖）
- Stage Gate 用户 Go/No-Go（from L1-10）

**输出**：
- 4 件套 markdown（requirements / goals / acceptance-criteria / quality-standards）
- PMP 9 大计划 markdown（9 份）
- TOGAF A-D 架构文档 + ADR（≥ 10 条）
- WBS 调度依据传给 L1-03
- Stage 转换事件（落 L1-09 + 通知 L1-01）
- S7 最终交付包（代码 + PMP 包 + TOGAF 包 + 决策审计链）

#### 5.2.3 边界

**In-scope**：
- 7 阶段定义 + allowed_next 状态机
- 4 次 Stage Gate 机制（S1/S2/S3/S7 末）
- PMP 5 过程组 × TOGAF 9 ADM 矩阵当前格维护
- 4 件套生产（需求/目标/验收/质量）
- 9 大计划生产
- TOGAF A-D 架构文档生产 + ADR 记录
- 产出物模板驱动（PM-07）
- 合规裁剪机制（PM-13 完整 / 精简 / 自定义）
- **`harnessFlowProjectId` 的全生命周期管理权**（PM-14 · S1 创建点 / 激活 / S7 归档 / 用户主动删除）· 详见 `docs/2-prd/L0/projectModel.md` §4

**Out-of-scope**：
- 不做 WBS 结构 → L1-03
- 不做 TDD 蓝图 → L1-04 S3
- 不做代码实现 → L1-04 S4 驱动 + L1-05 调 skill
- 不做验收判定 → L1-04 S5 委托 verifier
- 不做具体 skill 调用 → L1-05
- 不做 state 转换触发（转换由 L1-01 触发，本 L1 只定义 allowed_next + 产出物）

**边界规则**：本 L1 负责"阶段编排 + 产出物生产"，不负责"拆解 + 执行 + 验证"。

#### 5.2.4 约束

- **Goal §3.5 L1 硬约束 1-8 全部适用**（必经 7 阶段 / 必 4 次 Gate / methodology-paced 节奏 / S5 PASS 不得回头 / 4 件套硬性 / 死循环保护 / 终态三态 / S5 PASS = Goal 达成）
- **PM-01 methodology-paced 节奏**：S1/S2/S3 强协同、S4/S5/S6 自走、S7 强 Gate
- **PM-07 产出物模板驱动**：所有产出按标准模板，无消费者不产出
- **PM-13 合规可裁剪**：3 档裁剪不得违背 L1 硬约束
- **硬约束**：S2 Stage Gate 必 4 件套齐全才能进 S3

#### 5.2.5 🚫 禁止行为（明确清单）

- 🚫 **禁止跳过任一 Stage Gate**（S1/S2/S3/S7 末 4 次 Gate 硬性）
- 🚫 **禁止 4 件套不齐时进 S3**（needs/goals/AC/quality 必须全齐）
- 🚫 **禁止 S5 未 PASS 时进 S7**（Goal §3.5 硬约束 4）
- 🚫 **禁止 state 转换越过 allowed_next**
- 🚫 **禁止生成无消费者的产出物**（防 paperwork theater）
- 🚫 **禁止修改 goal_anchor.hash**（除非走极重度 FAIL 回 S1 重锚）
- 🚫 **禁止绕过裁剪控制台强行全量 / 强行精简**（必须用户显式裁剪）

#### 5.2.6 ✅ 必须义务（明确清单）

- ✅ **必须**按 PMP 5 × TOGAF 9 矩阵编织每阶段产出物
- ✅ **必须**在每次 Stage Gate 阻塞 L1-01 直到用户 Go/No-Go
- ✅ **必须**保证 4 件套 + 9 计划 + TOGAF A-D + WBS + ADR 全部落盘
- ✅ **必须**支持裁剪 3 档（完整 / 精简 / 自定义）且不违反 Goal §3.5 L1 硬约束
- ✅ **必须**在 state_history 每次转换留时间戳 + trigger 原因
- ✅ **必须**走 PM-07 产出物模板驱动（禁自由格式）

#### 5.2.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 控制流 | 接收 ← | state 转换指令 | BF-L3-13 |
| L1-03 WBS+WP 调度 | 生产-消费 | 传递 → | 4 件套 + 9 计划 + 架构 → WBS 拆解依据 | BF-S2-07 |
| L1-04 Quality Loop | 生产-消费 | 传递 → | 4 件套 → TDD 蓝图生成依据（S3） | BF-S3-01/02/03 |
| L1-05 Skill+子 Agent | 控制流 | 调用 → | 调 `writing-plans` / `prp-plan` / `architecture-decision-records` skill | BF-L3-02 |
| L1-06 知识库 | 数据流 | 读 | 阶段注入策略（S1 注 trap+pattern / S2 注 recipe+tool_combo / ...） | BF-X-05 |
| L1-07 监督 | 观察 | 被观察 | Supervisor 读 state_history 判"计划对齐"维度 | BF-X-02 |
| L1-10 UI | 输出 | 推送 → | Stage Gate 待办卡片 + 产出物预览 + 4 件套文档查看 | BF-L3-09 + BF-S1-04/S2-09/S3-05/S7-05 |

---

### 5.3 L1-03 · WBS + WP 拓扑调度能力

#### 5.3.1 职责

把**超大项目**按 4 件套 + 架构边界**拆成若干 WP（Work Package）**；维护 WP **拓扑图**（依赖关系 + 关键路径 + 并行度）；在 S4 执行阶段调度"**取下一可执行 WP**"；每 WP 具备独立 Goal / DoD / 工时估算 / 推荐 skill。

**锚定**：
- Goal §2.3 WP 拓扑（唯一对应条目）
- Goal §7.1 风险应对：WP 拓扑拆解 wrap 长程不确定性
- BF-S2-07 WBS 拆解流
- BF-S4-01 WP 取任务流（拓扑调度）
- BF-S4-02 WP 内 mini-PMP 流
- BF-S4-05 WP commit 流

#### 5.3.2 输入 / 输出

**输入**：
- 4 件套 from L1-02（需求 / 目标 / AC / 质量标准）
- TOGAF A-D 架构产出 from L1-02（用于按架构边界拆 WP）
- WP 完成事件 from L1-04（用来推进拓扑）

**输出**：
- WBS 拓扑图 markdown（`docs/planning/wbs.md`，含层级树 + 依赖图 + 工时估算）
- "下一可执行 WP" 调度决定（告知 L1-01）
- WP 定义结构化数据（含 Goal / DoD / 依赖 / 工时 / 推荐 skill）
- WP 级 mini-PMP 事件流（落 L1-09）

#### 5.3.3 边界

**In-scope**：
- WBS 层级拆解（从项目 → 模块 → WP）
- WP 定义结构（Goal / DoD / 依赖 / 工时）
- 拓扑依赖管理（DAG 校验）
- WP 调度算法（依赖 satisfied 的优先级最高 WP）
- 并行度控制（同时 ≤ 1-2 个 WP）
- WP 完成度跟踪

**Out-of-scope**：
- 不做 WP 内部的 mini-PMP 推进 → 复用 L1-02 + L1-04 在 WP 粒度执行
- 不做 WP 内的代码实现 → L1-05 调 skill
- 不做 WP 级 TDD 定义 → L1-04 S3
- 不做 WP 级验证 → L1-04 S5
- 不做 WP 失败诊断 → L1-07 soft-drift + WP 失败回退（BF-E-08）

**边界规则**：本 L1 只管"WP 拓扑 + 调度"，WP 内部推进复用 L1-02/04/05。

#### 5.3.4 约束

- **PM-04 WP 拓扑并行推进**：同时最多 1-2 个 WP 并行（防认知爆炸）
- **硬约束**：WP 粒度 ≤ 5 天工时（粒度过大 → 触发 WP 拆分流）
- **硬约束**：WP 依赖图必须 DAG（无环）
- **硬约束**：未完成的前置依赖 → 不得取该 WP
- **硬约束**：WP 失败 ≥ 3 次 → 触发 BF-E-08 回退建议

#### 5.3.5 🚫 禁止行为（明确清单）

- 🚫 **禁止取依赖未 satisfied 的 WP**（按拓扑序硬约束）
- 🚫 **禁止同时并行 > 2 个 WP**（PM-04 防认知爆炸）
- 🚫 **禁止 WP 粒度 > 5 天工时**（超过必须再拆）
- 🚫 **禁止 WBS 拓扑存在环**（必 DAG，必校验）
- 🚫 **禁止 WP 定义缺 Goal / DoD / 依赖 / 工时**（4 要素硬性）
- 🚫 **禁止绕过 L1-04 直接标 WP done**（必经 Quality Loop 验证）

#### 5.3.6 ✅ 必须义务（明确清单）

- ✅ **必须**保证 WBS 拓扑是 DAG（产出后自动校验无环）
- ✅ **必须**每 WP 有独立 Goal + DoD + 依赖 + 工时估算
- ✅ **必须**按拓扑序调度（不跳级）
- ✅ **必须**在 WP 失败 ≥ 3 次时触发 BF-E-08 回退建议
- ✅ **必须**向 L1-10 暴露 WBS 拓扑可视化数据（供 🔧 WBS tab）
- ✅ **必须**维护已完成 WP 清单 + 未完成 WP 剩余工时估算

#### 5.3.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 控制流 | 接收 ← | "取 WP" 调度请求 | BF-S4-01 |
| L1-02 生命周期 | 生产-消费 | 接收 ← | 4 件套 + 架构（拆解依据） | BF-S2-07 |
| L1-04 Quality Loop | 生产-消费 | 传递 → | 当前 WP 定义 → Quality Loop 执行 | BF-S4-01 |
| L1-07 监督 | 观察 | 被观察 | Supervisor 读 WP 完成率判"进度节奏" | BF-X-02 |
| L1-09 持久化 | 持久化 | 写 → | WP 状态变更事件落总线 | BF-X-03 |
| L1-10 UI | 输出 | 推送 → | WBS 拓扑图可视化（现有 🔧 wbs tab） | 现有 UI |

---

### 5.4 L1-04 · Quality Loop 能力

#### 5.4.1 职责

运行 HarnessFlow 的**质量闭环**：**S3 TDD 蓝图 → S4 执行 → S5 TDDExe → 4 级回退路由**。具体包括：
- S3 阶段：生成 Master Test Plan + DoD 表达式 + 全量用例 + 质量 gate + 验收 checklist
- S4 阶段：驱动每个 WP 的 IMPL → 单元/集成测试 → WP-DoD 自检 → commit
- S5 阶段：委托 verifier 子 Agent 跑独立验证 → 组装三段证据链
- 判定 verdict（PASS / 轻/中/重/极重 FAIL）→ 自动路由回退到对应阶段
- 死循环保护（同级 ≥3 次升级）

**锚定**：
- Goal §2.2 五大纪律："质量" + "检验"
- Goal §4.1 V1 量化指标："决策可追溯率 100%" + "监督 Agent 3 红线准确率 100%"
- Goal §3.3 "交付验收阶段强 Gate"
- BF-S3 全部（TDD 规划 5 条 L2）
- BF-S4-03 TDD 驱动实现流 / BF-S4-04 WP-DoD 自检流
- BF-S5 全部（TDDExe 质量执行 4 条 L2）
- BF-E-10 死循环保护流

#### 5.4.2 输入 / 输出

**输入**：
- 4 件套 from L1-02（作 TDD 蓝图生成依据）
- 当前 WP 定义 from L1-03
- WP 实现产出 from L1-05（调 tdd / prp-implement 产出的代码）
- verifier 子 Agent 结果 from L1-05（BF-S5-01）
- Supervisor 回退指令 from L1-07（BF-S5-04）

**输出**：
- **S3 产出**：TDD 蓝图（`docs/testing/master-test-plan.md` + `dod-expressions.yaml` + `tests/generated/*.py` + `quality-gates.yaml` + `acceptance-checklist.md`）
- **S4 产出**：代码 + 测试变绿 + WP commit（每 WP 一个）
- **S5 产出**：`verifier_reports/*.json` 三段证据链（existence / behavior / quality）
- **verdict + 回退路由指令**（告知 L1-01 控制 state 转换）

#### 5.4.3 边界

**In-scope**：
- TDD 蓝图生成机制（4 件套 → 可机器校验形式）
- DoD 表达式编译（AST eval，白名单谓词）
- 测试用例骨架生成（先红灯，符合 TDD）
- 质量 gate 规则（覆盖率 / 性能 / 安全扫描）
- 验收 checklist
- 测试执行驱动（调 tdd 的时机）
- WP-DoD 自检（非独立验证）
- TDDExe 独立验证编排（委托 verifier）
- 三态 verdict 判定规则（PASS / FAIL / INSUFFICIENT_EVIDENCE）
- 4 级偏差回退路由（轻/中/重/极重 → 回 S4/S3/S2/S1）
- 死循环保护（同级 ≥ 3 次自动升级）

**Out-of-scope**：
- 不写业务代码 → L1-05 调 `tdd` skill
- 不管 WP 调度 → L1-03
- 不管 8 维度其他监督（仅"真完成质量"一维） → L1-07
- 不做 KB 读写 → L1-06
- 不做事件落盘 → L1-09
- 不管硬红线拦截（只管自己的 4 级回退） → L1-07

**边界规则**：本 L1 只管"质量与检验"，执行动作委托 L1-05，硬拦截委托 L1-07。

#### 5.4.4 约束

- **PM-05 Stage Contract 机器可校验**：DoD 走白名单 AST eval，禁 arbitrary exec
- **PM-08 可审计全链追溯**：三段证据链必须完整，任一段缺失 → INSUFFICIENT
- **硬约束 1**：S5 未 PASS 不得进 S7（Goal §3.5 硬约束 4）
- **硬约束 2**：verifier 必须独立 session（PM-03 子 Agent 独立 session 委托）
- **硬约束 3**：同级 FAIL ≥ 3 次触发自动升级（Goal §3.5 硬约束 6）
- **硬约束 4**：TDD 蓝图必须在 S4 前全部生成（不可边执行边补）

#### 5.4.5 🚫 禁止行为（明确清单）

- 🚫 **禁止 S5 未 PASS 进 S7**（Goal §3.5 硬约束 4）
- 🚫 **禁止跳过三段证据链**（existence / behavior / quality 三段必全）
- 🚫 **禁止 verifier 在主 session 跑**（必经 L1-05 独立 session 委托）
- 🚫 **禁止 DoD 表达式含 arbitrary exec**（仅白名单 AST，PM-05）
- 🚫 **禁止同级 FAIL ≥ 3 次不升级**（死循环保护硬性）
- 🚫 **禁止绕过 Quality Loop 直接让主 loop 报完成**
- 🚫 **禁止 S3 TDD 蓝图边执行 S4 边补**（蓝图必须 S3 Gate 前全齐）
- 🚫 **禁止自己做偏差 4 级判定**（判定由 L1-07 supervisor 负责，L1-04 接收路由指令）

#### 5.4.6 ✅ 必须义务（明确清单）

- ✅ **必须**在 S3 阶段**先于** S4 生成完整 TDD 蓝图（Master Test Plan + DoD + 用例 + gate + checklist）
- ✅ **必须**委托 verifier 子 Agent 独立 session 跑 S5（不得主 session 自跑）
- ✅ **必须**组装三段证据链并落 `verifier_reports/*.json`
- ✅ **必须**按 L1-07 路由的 4 级 verdict 精确跳转（轻→S4 / 中→S3 / 重→S2 / 极重→S1）
- ✅ **必须**在死循环 ≥ 3 次时配合 L1-07 自动升级 + 硬暂停
- ✅ **必须**对每次 FAIL 留原因到事件总线

#### 5.4.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 控制流 | 接收 ← / 反馈 → | 进 S3/S4/S5 指令；verdict + 回退路由反馈 | BF-S3/4/5 全部 |
| L1-02 生命周期 | 生产-消费 | 接收 ← | 4 件套 → TDD 蓝图生成依据 | BF-S3-01/02/03/04 |
| L1-03 WBS | 生产-消费 | 接收 ← | 当前 WP 定义 | BF-S4-01 |
| L1-05 Skill+子 Agent | 控制流 | 调用 → | 调 `tdd` / `prp-implement` 写代码；委托 `verifier` 子 Agent 跑 TDDExe | BF-S4-03 + BF-S5-01 |
| L1-06 知识库 | 数据流 | 读 | trap pattern（防假完成陷阱）+ recipe（TDD 最佳实践） | BF-X-05 |
| L1-07 监督 | 观察-干预 | 接收 ← | 4 级回退路由指令 + 死循环升级指令 | BF-S5-04 + BF-E-10 |
| L1-09 韧性+审计 | 持久化 | 写 → | verifier_report + verdict + 每次 FAIL 原因落总线 | BF-X-03 |
| L1-10 UI | 输出 | 推送 → | TDD 质量 tab + Verifier 证据链 tab + Loop 历史 tab（现有） | 现有 UI |

---

### 5.5 L1-05 · Skill 生态 + 子 Agent 调度能力

#### 5.5.1 职责

HarnessFlow 作为**调度器**的核心载体：
- 对接 **superpowers / gstack / everything-claude-code / 自定义** 4 大 skill 生态
- 通过**能力抽象层**匹配可用 skill（不绑死 skill 名，支持 fallback）
- 委托**独立 session 的子 Agent**（verifier / retro-generator / failure-archive-writer / architecture-reviewer / security-reviewer / codebase-onboarding 等）
- **原子工具柜**（Read / Write / Edit / Bash / Grep / Glob / WebSearch / WebFetch / Playwright / MCP）调度
- **失败降级链**（首选 → fallback → 内建逻辑 → 硬暂停）

**锚定**：
- Goal §2 产品定位"调度整个 Skill 生态的高阶调度器"
- Goal §7.4 风险应对"Skill 能力抽象层 + 多 skill 可替代映射"
- BF-L3-02 Skill 调度流
- BF-L3-03 子 Agent 委托流
- BF-L3-04 工具调用流
- BF-X-07 能力抽象层调度流
- BF-E-05 Skill 失败降级流
- BF-E-09 子 Agent 失败流

#### 5.5.2 输入 / 输出

**输入**：
- L1-01 主 loop 的"需要能力 X / 工具 Y / 子 Agent Z"请求
- L1-02 / L1-04 等其他 L1 的 skill 调用请求
- Skill 注册表 + 可用性状态（即 UI 后台模块 Skills 调用图）
- 子 Agent 注册表（4+ 个，即 UI 后台模块 Subagents 注册表）
- 工具柜元数据

**输出**：
- 调用某 skill 的结构化结果
- 子 Agent 独立 session 的结构化报告
- 原子工具的返回值（含签名登记）
- 失败降级方案 + 告警事件（落 L1-09）

#### 5.5.3 边界

**In-scope**：
- Skill 匹配 + 优先级排序（可用性 / 成本 / 历史成功率）
- fallback 链管理（每能力点 ≥ 2 备选）
- 子 Agent 委托（包 context 副本 + 启动独立 session + 回收结果）
- 子 Agent 生命周期管理（启动 / 监控 / 超时 / 回收）
- 原子工具调用登记（工具名 / 入参 / 返回 / 耗时签名）
- 失败降级策略执行

**Out-of-scope**：
- 不做 skill 本身的实现（skill 来自外部生态，生态更新不由本 L1 控制）
- 不做子 Agent 的业务逻辑（子 Agent 各自的 SKILL.md 定义）
- 不做监督（由 L1-07 观察 skill 调用密度和子 Agent 失败率）
- 不做 KB 读写（由 L1-06 承担）
- 不做事件落盘（由 L1-09 承担）

**边界规则**：本 L1 是"调度层 + 适配层"，不做业务执行。所有"做事"都委托出去。

#### 5.5.4 约束

- **PM-03 子 Agent 独立 session 委托**：只读 context 副本 + 结构化回传，禁 session 间共享状态
- **PM-09 能力抽象层调度**：主 Agent 绑"能力点"不绑 skill 名；每能力 ≥ 2 备选
- **硬约束 1**：工具调用必须留签名登记（可审计，Goal §4.1 决策可追溯 100%）
- **硬约束 2**：子 Agent 失败 2 次自动降级到 fallback
- **硬约束 3**：skill 调用失败走 BF-E-05 降级链，不得裸报错退出
- **硬约束 4**：子 Agent 超时（默认 5 分钟）必须 kill + 回收

#### 5.5.5 🚫 禁止行为（明确清单）

- 🚫 **禁止绑死 skill 名**（必走能力抽象层，PM-09）
- 🚫 **禁止子 Agent 共享主 session 上下文**（PM-03 独立 session 委托）
- 🚫 **禁止工具调用不留签名**（违反 Goal §4.1 可追溯）
- 🚫 **禁止 skill 失败硬退出**（必走 fallback 链 BF-E-05）
- 🚫 **禁止子 Agent 超时不 kill**（防僵尸进程）
- 🚫 **禁止子 Agent 反向写主 task-board**（只结构化回传）
- 🚫 **禁止绕过能力抽象层直接字符串匹配 skill 名**

#### 5.5.6 ✅ 必须义务（明确清单）

- ✅ **必须**每"能力点"注册 ≥ 2 个备选 skill（PM-09）
- ✅ **必须**在调用失败时执行 fallback 链（首选 → 备选 → 内建 → 硬暂停）
- ✅ **必须**为每次 skill / tool / subagent 调用落事件（含 version / 耗时 / 结果 / 入参 hash）
- ✅ **必须**给子 Agent 包 context 副本（只读）+ 明确 goal + 工具白名单
- ✅ **必须**在子 Agent 超时后 kill + 回收资源 + 走 BF-E-09
- ✅ **必须**对子 Agent 回传做 schema validate（格式错算失败）

#### 5.5.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 控制流 | 接收 ← / 反馈 → | "调 skill X / 工具 Y / 子 Agent Z"请求；结构化产出反馈 | BF-L3-02 / 03 / 04 |
| L1-02 生命周期 | 控制流 | 接收 ← | S2 调 `writing-plans` / `prp-plan` / `architecture-decision-records` | BF-S2-05 / 06 / 08 |
| L1-04 Quality Loop | 控制流 | 接收 ← | S3 调 `test-driven-development`；S4 调 `tdd` / `prp-implement`；S5 委托 `verifier` 子 Agent | BF-S3-01 / BF-S4-03 / BF-S5-01 |
| L1-07 监督 | 被观察 | 被观察 ← | Supervisor 读 skill 调用密度、子 Agent 失败率判"真完成质量" + "重试 Loop" 维度 | BF-X-02 |
| L1-08 多模态 | 控制流 | 调用 → | Read/Grep/Glob 等工具承担文档/代码分析 | BF-L3-06/07 |
| L1-09 韧性+审计 | 持久化 | 写 → | 每次 skill/tool/子 Agent 调用事件落总线 | BF-X-03 |

---

### 5.6 L1-06 · 3 层知识库能力

#### 5.6.1 职责

维护 **Global（跨项目永久）/ Project（跨 session 本项目）/ Session（本次会话临时）** 3 层知识库；按 PMP+TOGAF 阶段执行**注入策略**；运行**晋升仪式**（Session → Project / Global）；KB 条目的增删改查与 `applicable_context` 匹配。

**锚定**：
- Goal §3.2.D 知识沉淀 "有价值的 pattern / trap / tool_combo 自动晋升"
- Goal 附录 A 术语 "KB 三层"
- BF-L3-05 KB 读写流
- BF-X-05 KB 注入策略执行流
- BF-S7-04 KB 晋升仪式流
- BF-E-02 会话恢复（读 KB 确定"已恢复项目"的历史决策）

#### 5.6.2 输入 / 输出

**输入**：
- L1-01 主 loop 的 KB 读 / 写请求
- L1-02 的阶段切换事件（触发注入）
- L1-04 的 session 候选（发现新 trap / pattern）
- L1-07 的 soft-drift 识别（匹配已知 trap）
- 用户显式晋升批准

**输出**：
- 注入到主 loop 上下文的相关 KB 条目（按 kind / scope / applicable_context 过滤）
- session-kb / project-kb / global-kb 的增量更新
- KB 晋升结果（session → project / global 或丢弃）

#### 5.6.3 边界

**In-scope**：
- 3 层物理存储（jsonl / md 文件系统）
- kind 分类：pattern / trap / recipe / tool_combo / anti_pattern / project_context / external_ref / effective_combo
- 注入策略执行（按阶段 + applicable_context 过滤）
- 晋升仪式（observed_count ≥ threshold 或用户批准）
- evidence 追踪（observed_count 自动累计、first_observed_at、last_observed_at）
- 条目 schema 校验

**Out-of-scope**：
- 不做向量检索（文件系统存储，scope 内不做 embedding）
- 不做自动学习（晋升必须 observed_count ≥ 2 或用户批准，不自动写入 Global）
- 不做跨项目知识联邦（多项目只走 Global）
- 不做外部 RAG 对接（future）
- 不做自然语言问答（KB 是结构化条目，不做 chat 接口）

**边界规则**：本 L1 只做"存储 + 注入 + 晋升"，不做向量化 / 不做智能推断。

#### 5.6.4 约束

- **PM-06 KB 三层 + 阶段注入**
- **硬约束 1**：Session 条目默认临时，会话结束 7 天内未晋升自动过期
- **硬约束 2**：晋升到 Global 需 observed_count ≥ 3 **或**用户显式批准
- **硬约束 3**：KB 条目必有 schema validate（防损坏数据写入）
- **硬约束 4**：注入策略按 PM-06 表，不得绕过

#### 5.6.5 🚫 禁止行为（明确清单）

- 🚫 **禁止 Session 条目直接晋升 Global**（必先 Project → Global）
- 🚫 **禁止 observed_count < 3 且无用户批准就写 Global**
- 🚫 **禁止跨项目共享 Project KB**（仅 Global 允许跨项目）
- 🚫 **禁止 KB 条目不走 schema validate** 就写入
- 🚫 **禁止做向量 embedding / 外部 RAG**（Goal 非目标）
- 🚫 **禁止用自然语言问答代替结构化读**（KB 是结构化条目不是 chat 接口）
- 🚫 **禁止阶段切换时绕过注入策略表**（PM-06）

#### 5.6.6 ✅ 必须义务（明确清单）

- ✅ **必须**按 scope 优先级读（Session > Project > Global）
- ✅ **必须**按 `applicable_context` 过滤（route / task_type / 技术栈）
- ✅ **必须**在阶段切换时按注入策略表推条目给 L1-01
- ✅ **必须**对每次 KB 读写落事件（kind / scope / id）
- ✅ **必须**对 Session 条目在会话结束 7 天内未晋升自动过期
- ✅ **必须**自动累计 observed_count（不等用户手动加）

#### 5.6.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 数据流 | 读 ↔ 写 | KB 读（决策前注入）/ 写（session 候选） | BF-L3-05 |
| L1-02 生命周期 | 数据流 | 读 | 阶段切换时按注入策略推条目 | BF-X-05 |
| L1-04 Quality Loop | 数据流 | 读 ↔ 写 | S3/S4/S5 读 trap / anti_pattern；S4 发现新经验写 session KB | BF-X-05 |
| L1-07 监督 | 数据流 | 读 | 软红线识别时读已知 trap 对比 | 跨 BF |
| L1-09 持久化 | 持久化 | 写 → | KB 增删改查事件落总线 | BF-X-03 |
| L1-10 UI | 输出 | 推送 → | 📚 知识库后台模块 + 📖 项目资料库 tab | 现有 UI |

---

### 5.7 L1-07 · Harness 监督能力

#### 5.7.1 职责

常驻**旁路 subagent**，**只读**观察主 Agent 工作：
- **8 维度指标实时计算**：目标保真度 / 计划对齐 / 真完成质量 / 红线安全 / 进度节奏 / 成本预算 / 重试 Loop / 用户协作
- **4 级分级干预**：INFO（记录）/ SUGGESTION（可选采纳）/ WARN（必须书面回应）/ BLOCK（硬拦截）
- **软红线 8 类自治修复**（不打扰用户）
- **硬红线 5 类硬拦截**（必须用户文字授权）
- **Quality Loop 偏差 4 级回退路由**（轻 → S4 / 中 → S3 / 重 → S2 / 极重 → S1）
- **死循环保护**（同级 ≥ 3 次 → 自动升级）
- **周期状态报告** / 风险登记 / 变更请求评估

**锚定**：
- Goal §4.3 methodology-paced autonomy "监督 Agent 密集观察"
- Goal §7.3 风险"Supervisor 分级干预权威"
- Goal 附录 A 术语 "监督 Agent（Supervisor）"
- BF-S6 全部（周期状态报告 / 风险识别 / 变更请求 / 软红线自治 / 硬红线上报 5 条 L2）
- BF-X-02 监督观察流
- BF-S5-03 偏差等级判定流
- BF-S5-04 回退路由流
- BF-E-07 任务走偏 soft-drift 检测流
- BF-E-10 死循环保护流
- BF-E-11 软红线自治修复流（8 类）
- BF-E-12 硬红线上报流（5 类）

#### 5.7.2 输入 / 输出

**输入**：
- 事件总线全量事件（从 L1-09 读）
- task-board 快照
- verifier_report 结果（从 L1-04）
- 主 loop 决策链（从 L1-01 落盘的事件）
- KB 已知 trap（从 L1-06）

**输出**：
- INFO / SUGGESTION / WARN / BLOCK 事件（落 L1-09 + 推给主 loop 建议队列）
- 软红线自治动作指令（触发其他 L1 动作，如重跑 verifier / 压缩上下文 / fallback skill）
- 硬红线硬暂停指令（to L1-01）
- Quality Loop 回退路由指令（to L1-04）
- 周期状态报告 md（落盘 `docs/status-reports/YYYY-MM-DD.md`）
- 风险登记册更新（`docs/risk-register.md`）
- 变更请求评估报告

#### 5.7.3 边界

**In-scope**：
- 8 维度观察 + 阈值对比
- 4 级建议管道
- 软红线 8 类自治逻辑
- 硬红线 5 类上报逻辑
- Quality Loop 回退路由
- 死循环升级
- 周期状态报告生成
- 风险 / 变更流程

**Out-of-scope**：
- **不做业务执行**（只观察不做）
- **不修数据**（任何修改都必须通过主 loop，本 L1 无写权限）
- **不调 skill**（只发建议，由主 loop 决定采纳）
- **不做产出物生产**（本 L1 是 S6 的监控者，不是产出物生产者）
- 不做用户界面（建议展示由 L1-10）

**边界规则**：本 L1 只做"**观察 + 建议 + 回退路由 + 硬拦截**"，绝不做业务执行。

#### 5.7.4 约束

- **PM-02 主-副 Agent 协作**：supervisor 不直接改数据
- **PM-12 红线分级自治**：软红线必须不打扰用户；硬红线必须文字授权
- **硬约束 1**：只读权限，不得改 task-board / 事件总线 / KB（写自己的 supervisor_events 除外）
- **硬约束 2**：硬拦截必须附文字告警，用户授权才能解除
- **硬约束 3**：建议被主 loop 驳回必须书面理由留痕（可审计）
- **硬约束 4**：Quality Loop 回退路由必须基于 verifier_report 的结构化判定，不得主观越权回退

#### 5.7.5 🚫 禁止行为（明确清单）

- 🚫 **禁止直接改 task-board / 事件总线**（只写 `supervisor_events` 子命名空间）
- 🚫 **禁止调 skill / 子 Agent**（只发建议，由 L1-01 决定采纳）
- 🚫 **禁止硬拦截不附文字告警**（黑盒拦截 = 破坏可审计）
- 🚫 **禁止软红线打扰用户**（仅 WARN+ 才通知用户）
- 🚫 **禁止采纳 / 驳回 supervisor 建议无书面理由**
- 🚫 **禁止偏差判定主观越权**（只按 verifier_report 结构化判定）
- 🚫 **禁止关闭死循环保护**（同级 ≥ 3 次必升级）
- 🚫 **禁止 supervisor 自身跑代码执行**

#### 5.7.6 ✅ 必须义务（明确清单）

- ✅ **必须**只读权限访问 task-board / 事件总线
- ✅ **必须**对硬红线 5 类立即 BLOCK L1-01 + 告警 L1-10
- ✅ **必须**对软红线 8 类执行自治修复（不打扰用户）并落事件
- ✅ **必须**按 4 级 verdict 精确触发 Quality Loop 回退（L1-04）
- ✅ **必须**对同级 FAIL ≥ 3 次触发死循环升级
- ✅ **必须**生成周期状态报告（每周 + 每里程碑）落 `docs/status-reports/`
- ✅ **必须**每次建议明确 level（INFO/SUGG/WARN/BLOCK）+ 消息内容 + 动作建议

#### 5.7.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 观察-干预 | 推送 → | INFO / SUGG / WARN / BLOCK 建议；硬暂停指令 | BF-X-02 |
| L1-02 生命周期 | 观察 | 观察 ← | 读 state_history 算"计划对齐"维度 | BF-X-02 |
| L1-03 WBS | 观察 | 观察 ← | 读 WP 完成率算"进度节奏"维度 | BF-X-02 |
| L1-04 Quality Loop | 观察-干预 | 推送 → | 4 级回退路由指令 + 死循环升级指令 | BF-S5-04 + BF-E-10 |
| L1-05 Skill+子 Agent | 观察 | 观察 ← | 读 skill 调用密度、子 Agent 失败率算"真完成质量" + "重试 Loop" | BF-X-02 |
| L1-06 KB | 数据流 | 读 ← | 读已知 trap / anti_pattern 辅助软红线识别 | 跨 BF |
| L1-09 持久化 | 数据流 | 读 ← / 写 → | 读全量事件 + 写 supervisor_events | BF-X-03 |
| L1-10 UI | 输出 | 推送 → | 🛡️ Harness 监督 tab + 后台智能体模块 + 未来"红线告警角" | 现有 UI + 新增（§3.4 P0） |

---

### 5.8 L1-08 · 多模态内容处理能力

#### 5.8.1 职责

为 L1-01 决策与 L1-02 规划提供**多模态内容理解**能力：读写 md 文档、读懂代码结构、读懂图片（架构图 / 截图 / UI mock）。结构化产物注入主 loop 上下文或 session KB。

**锚定**：
- Goal §3.1 输入（Brownfield / 多仓库 / 用户提供的架构图 / 现有代码库）
- BF-L3-06 文档处理流
- BF-L3-07 代码读取与分析流
- BF-L3-08 图片/截图分析流

#### 5.8.2 输入 / 输出

**输入**：
- L1-01 / L1-02 / L1-04 的"读/写/分析"请求（文档 / 代码 / 图片三类）
- 用户上传的架构图 / UI mock 图片
- L1-07 需读取 verifier_report / status-report 做观察

**输出**：
- **文档读**：结构化 sections（含 frontmatter + headings + 关键段落）
- **文档写**：按模板填充的 md（落盘到 docs/ 或 tests/）
- **代码分析**：语言 + 框架 + 入口文件 + 依赖图 + 关键模式（写入 Project KB）
- **图片分析**：按图片类型的结构化描述（架构图节点+关系 / UI mock 组件+交互 / 截图状态+错误迹象）

#### 5.8.3 边界

**In-scope**：
- md 文件 Read / Write / Edit（走 L1-05 工具柜）的封装
- 大文件（> 2000 行）分页处理
- 代码结构扫描（Glob + Grep + Read 入口）
- 代码仓库 > 10 万行时委托 `codebase-onboarding` 子 Agent
- 图片视觉理解（Claude 多模态原生能力）
- 按类型生成结构化描述

**Out-of-scope**：
- 不做代码生成（由 L1-05 调 `tdd` / `prp-implement` skill）
- 不做 AST 深度分析（专业分析委托 `codebase-onboarding` 子 Agent）
- 不做图片生成（只读不生成）
- 不做 PDF / Excel / 二进制文件解析（V1 不支持）
- 不做 OCR（未来）
- 不做代码重构（L1-05 承担）

**边界规则**：本 L1 只做"内容理解 + 读写",不改变代码本身的语义。

#### 5.8.4 约束

- **PM-08 可审计全链追溯**：每次读写必落事件
- **硬约束 1**：md 文件 > 2000 行必分页读（一次不得全量读）
- **硬约束 2**：代码仓库 > 10 万行必委托 `codebase-onboarding` 子 Agent，不得单体 Agent 硬读
- **硬约束 3**：所有读写路径必须是项目内相对路径或显式允许的外部路径（安全约束）

#### 5.8.5 🚫 禁止行为（明确清单）

- 🚫 **禁止直接修改用户源代码文件**（代码修改必经 L1-05 调 skill）
- 🚫 **禁止写入非 `docs/` / `tests/` / `harnessFlow/` 路径**（业务代码写入走 L1-05）
- 🚫 **禁止图片上传到外部服务**（隐私保护；只本地 Read）
- 🚫 **禁止执行代码中的 shell command**（只读不执行用户代码）
- 🚫 **禁止返回未经结构化的原始图片二进制给其他 L1**
- 🚫 **禁止跨项目读写**（仅当前项目 scope 内）

#### 5.8.6 ✅ 必须义务（明确清单）

- ✅ **必须**为每次读写产生 L1-09 事件（路径 + 大小 + 签名 + 结果摘要）
- ✅ **必须**对 > 2000 行文档分页处理
- ✅ **必须**为图片产出结构化描述（不只是"我看到了一张图"；必须列节点 / 组件 / 状态）
- ✅ **必须**在代码分析后写入 session KB（供 L1-01 后续决策复用）
- ✅ **必须**对不可读文件（权限 / 不存在 / 二进制未支持）明确告警，**禁止静默失败**
- ✅ **必须**对 > 10 万行代码仓库委托 `codebase-onboarding`，**不得硬扛**

#### 5.8.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 控制流 | 接收 ← / 反馈 → | `process_content({type, path, action})` | BF-L3-06/07/08 |
| L1-02 生命周期 | 控制流 | 接收 ← | 阅读现有 docs / 写 PMP 产出物 md | BF-S1-02/S2-* |
| L1-04 Quality Loop | 控制流 | 接收 ← | 写 TDD 蓝图 md + 读 verifier_report | BF-S3-01/04 |
| L1-05 Skill+子 Agent | 控制流 | 调用 → | 使用 Read/Write/Edit/Glob/Grep 工具；委托 `codebase-onboarding` | BF-L3-06/07 |
| L1-06 KB | 数据流 | 写 → | 代码分析结果写 Project KB | BF-X-05 |
| L1-09 韧性+审计 | 持久化 | 写 → | 所有读写操作事件 | BF-X-03 |
| L1-10 UI | 输出 | 推送 → | 代码结构图 / 架构图展厅 / 截图预览（P1 新增） | 新增 |

---

### 5.9 L1-09 · 韧性 + 审计能力

#### 5.9.1 职责

HarnessFlow 的**记忆与脊柱**：
- **事件总线**单一事实源（所有状态变更必经此 L1）
- 跨 session **无损恢复**（Ctrl+C 或崩溃后重启可无缝继续）
- **审计追溯链**（任一代码/产出物 → 反查决策 + 理由 + 证据）
- **异常降级**机制（网络 / API / 上下文爆炸 / WP 失败 / 子 Agent crash 各类异常恢复）

**锚定**：
- Goal §4.1 量化指标"可跨 session 无损恢复" + "决策可追溯率 100%"
- BF-X-03 事件总线落盘流
- BF-X-04 审计追溯流
- BF-X-08 持久化与跨 session 恢复流
- BF-E-01 会话退出流
- BF-E-02 跨 session 恢复流
- BF-E-03 网络异常恢复流
- BF-E-04 Claude API 限流处理流
- BF-E-06 上下文爆炸处理流
- BF-E-08 WP 失败回退流

#### 5.9.2 输入 / 输出

**输入**：
- 所有 L1（01-10）的 decision / event / user_action / supervisor_event
- 外部信号（SIGINT / SIGTERM / 网络异常 / API 429 / context 占用 > 80%）

**输出**：
- `events/YYYY-MM-DD.jsonl`（事件总线，单一事实源）
- `task-boards/<project_id>.json`（当前快照）
- `checkpoints/`（周期快照，用于快速恢复）
- 跨 session 恢复后的 task-board 重建结果
- 审计查询结果（用户查询锚点 → 返回完整决策链）
- 异常降级的替代方案（注入 L1-01 上下文）

#### 5.9.3 边界

**In-scope**：
- 事件 schema：`{ts, type (L1-XX:subtype), actor, state, content, links, hash}`（**必含 `project_id` 根字段**，PM-14）
- 事件总线**只追加**（append-only）写
- task-board snapshot（周期 + 关键事件后）
- 事件总线回放 → task-board 重建
- 会话退出 / 恢复 / 网络 / API / 上下文 / WP / 子 Agent 的降级机制
- 审计查询（按锚点：代码行 / 产出物路径 / 决策 id 反查完整链）
- **`harnessFlowProjectId` 的物理持久化根目录结构维护**（事件总线 / 审计 / 检查点 / 锁按 project 分片存储 · PM-14）· 详见 `docs/2-prd/L0/projectModel.md` §8

**Out-of-scope**：
- 不做业务决策（L1-01）
- 不做监督判定（L1-07）
- 不做数据统计可视化（L1-10）
- 不做外部云存储（本地文件系统即可；外部备份是部署运维事项不是 L1 职责）
- 不做事件总线的全文检索（grep-level 即可；未来需 elastic 再考虑）

#### 5.9.4 约束

- **PM-10 事件总线单一事实源**
- **硬约束 1**：事件**只追加**不修改（不可变日志）
- **硬约束 2**：任何 L1 的状态变更必须经事件总线（禁绕过）
- **硬约束 3**：checkpoint 频率 ≤ 1 分钟（防丢失超过 1 分钟工作量）
- **硬约束 4**：重启后 30 秒内必须完成恢复或明确失败告警
- **硬约束 5**：事件 hash 链（每事件的 hash 含前事件 hash）——防篡改

#### 5.9.5 🚫 禁止行为（明确清单）

- 🚫 **禁止修改已落盘的事件**（append-only，违反 = 审计链断裂）
- 🚫 **禁止绕过事件总线**直接改 task-board（违反 = 破坏单一事实源）
- 🚫 **禁止丢弃未处理事件**（即使降级也必须落盘记录）
- 🚫 **禁止跨项目共享事件总线**（每项目独立 jsonl 文件）
- 🚫 **禁止异常时静默退出**（必须留 checkpoint + 告警）
- 🚫 **禁止在恢复失败时自动重建空白 task-board**（必须告警用户）

#### 5.9.6 ✅ 必须义务（明确清单）

- ✅ **必须**每次事件追加后 `fsync`（防系统崩溃丢失）
- ✅ **必须**保证 task-board 可从事件总线完全重建（不依赖 snapshot）
- ✅ **必须**对 SIGINT / SIGTERM 做干净 flush + checkpoint + 优雅退出
- ✅ **必须**为每个 L1 的事件分配独立 type 前缀（`L1-01:decision` / `L1-04:verdict` / ...）
- ✅ **必须**在重启时自动触发恢复（BF-E-02）并向用户明示 `已恢复 project X, state=Y, 继续？`
- ✅ **必须**在审计查询时返回完整链（决策 + 理由 + 事件 + 监督点评 + 用户批复）

#### 5.9.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| 全部 L1-01~08/10 | 持久化 | 接收 ← | `append_event(event)` / `snapshot_task_board()` | BF-X-03 / X-08 |
| L1-07 监督 | 数据流 | 读 ← / 写 → | `scan_events(filter)` 供 supervisor 观察 + 写 `supervisor_events` | BF-X-02 |
| L1-10 UI | 数据流 | 读 ← | 时间轴渲染 / 审计追溯查询 | BF-X-04 + BF-L3-09 |

---

### 5.10 L1-10 · 人机协作 UI 能力

#### 5.10.1 职责

用户与 HarnessFlow **交互的所有入口**：
- 项目实时看板 / 决策轨迹走廊 / 架构图展厅 / Stage Gate 待办中心 / 交付物预览 / 后台管理 / 干预控制台 / 红线告警角
- 消费 L1-09 事件总线 + 推用户输入回 L1-01
- 承载现有 UI mock（11 tab + 9 admin）+ 新增 UI 缺口（§3.4 P0-P2）

**锚定**：
- Goal §4 过程（methodology-paced autonomy 的用户介入面）
- Goal §3.3 Stage Gate 节奏
- BF-L3-09 请示用户流
- BF-S1-04 / BF-S2-09 / BF-S3-05 / BF-S7-05 各 Stage Gate
- 现有 UI mock（localhost:8765，11 tab + 9 admin）

#### 5.10.2 输入 / 输出

**输入**：
- 全部 L1 的事件流（从 L1-09 读）
- 用户交互（点击 / 输入 / Stage Gate Go/No-Go / 红线授权）
- L1-07 supervisor 建议 / 告警推送
- L1-02 Stage Gate 待办卡片推送

**输出**：
- UI 展示（消费性，无业务写入）
- 用户输入回传（授权 / 澄清答案 / Go 决定 / 变更请求）推给 L1-01

#### 5.10.3 边界

**In-scope**：
- 现有 UI mock 11 tab（项目详情）+ 9 admin（后台管理）
- 新增 UI 缺口（§3.4 P0-P2 清单）：
  - P0 · Quality Loop 动态视图（TDDExe verdict + 4 级回退可视化）
  - P0 · 4 件套产出物视图
  - P0 · 决策轨迹走廊
  - P0 · 红线事件告警角
  - P1 · Stage Gate 待办中心（跨项目）
  - P1 · 多模态内容展示
  - P1 · 审计追溯查询面板
  - P2 · Loop 触发统计面板
- Stage Gate 交互（Go / No-Go + 修改意见）
- 用户紧急介入（panic button / 暂停 / 变更请求）
- localhost Web 形态（FastAPI + Vue CDN）

**Out-of-scope**：
- 不做业务逻辑（只 UI + 读事件总线 + 推用户输入）
- 不做移动端 App（Goal §6.10 明确）
- 不做多用户协同（单用户单 session）
- 不做 Figma / Sketch 集成（Goal §4.3 边界消歧）
- 不做响应式移动 UI（仅桌面 Web）
- 不做 UI 国际化超过中英双语

**边界规则**：本 L1 **只读事件总线 + 推用户输入**，不直接改业务状态。

#### 5.10.4 约束

- **Goal §6 非目标**：不做 App / 不做 SaaS
- **硬约束 1**：UI **只读事件总线** + 推用户输入到 L1-01，不直接改业务状态
- **硬约束 2**：Stage Gate 待审卡片**不得自动通过**（必须用户显式 Go）
- **硬约束 3**：硬红线告警必须可视化突出（红色 + 声音 + 持久化展示）
- **硬约束 4**：UI 消费事件总线延迟 ≤ 2 秒（用户感知实时）
- **硬约束 5**：一个 UI session 只展一个项目（Goal §6.11 V1-V2 单项目）

#### 5.10.5 🚫 禁止行为（明确清单）

- 🚫 **禁止直接改 task-board / 事件总线**（UI 是只读 + 输入消费者）
- 🚫 **禁止替用户做 Stage Gate 决定**（必须用户显式 Go/No-Go，禁止自动通过）
- 🚫 **禁止后台静默跳过硬红线告警**（必须强视觉提示直到用户确认）
- 🚫 **禁止存储用户凭证**（GitHub PAT 等仅 runtime 内存，不落盘 / 不 cookie）
- 🚫 **禁止跨项目数据混展**（一个 UI session 仅当前 project）
- 🚫 **禁止阻塞 L1-01 tick**（UI 展示不能占住主 loop）

#### 5.10.6 ✅ 必须义务（明确清单）

- ✅ **必须**实时消费事件总线（≤ 2 秒延迟）
- ✅ **必须**保留用户介入的完整审计日志（每次 Go/No-Go / 授权都落 L1-09）
- ✅ **必须**对硬红线告警强视觉提示（色 + 声 + 持久化直到确认）
- ✅ **必须**在 Stage Gate 待审时**阻断** L1-01 推进（不得跳过 Gate）
- ✅ **必须**为每个 L1 的核心状态提供独立可见视图（对应 §3.3 映射表）
- ✅ **必须**在用户主动 panic 时立即 flush + 暂停整个系统

#### 5.10.7 与其他 L1 的交互

| 对端 L1 | 关系类型 | 方向 | 接口 / 数据 | BF 衔接点 |
|---|---|---|---|---|
| L1-01 主 loop | 输入-输出 | 接收 ← / 推送 → | 用户介入 → L1-01；决策轨迹推送 → UI | BF-L3-09 |
| L1-02 生命周期 | 输出 | 接收 ← | Stage Gate 待审卡片 + 产出物预览 | BF-S1-04/S2-09/S3-05/S7-05 |
| L1-03 WBS | 输出 | 接收 ← | WBS 拓扑可视化（🔧 WBS tab） | 现有 UI |
| L1-04 Quality Loop | 输出 | 接收 ← | TDD 质量 tab / Verifier 证据链 tab / Loop 历史 tab | 现有 UI |
| L1-05 Skill+子 Agent | 输出 | 接收 ← | Skills 调用图 / Subagents 注册表 后台模块 | 现有 UI |
| L1-06 KB | 输出 | 接收 ← | 知识库后台 + 项目资料库 tab | 现有 UI |
| L1-07 监督 | 输出 | 接收 ← | Harness 监督 tab + 后台智能体 + 红线告警角（P0） | 现有 + 新增 |
| L1-08 多模态 | 输出 | 接收 ← | 代码结构图 / 架构图展厅 / 截图预览（P1） | 新增 |
| L1-09 韧性+审计 | 数据流 | 读 ← | 时间轴渲染 + 审计追溯查询面板（P1） | BF-X-04 |

---

## 6. 每 L1 独立文档索引

每个 L1 的 **L2 子能力分解 + L3 实现设计**由**独立文档**承载，**不在 scope.md 内**。scope.md 通过本章链接到这些独立文档，形成"scope 总纲 + L1 详细本"的两层结构。

### 6.0 为什么拆成独立文档

- **独立启动流程**：用户可为每个 L1 单独启动一个完整的 brainstorm → write-plan → TDD → execute → verify → commit 生命周期
- **并行开发**：不同 session 可并行推进不同 L1 的详细设计
- **scope.md 稳定**：独立文档更新不污染 scope.md 的版本节奏
- **集成点明确**：所有独立文档必须遵守 scope.md §5（L1 详细定义）+ §8（L1 间集成）的边界 + 接口 + 约束 + 禁止 + 义务

### 6.1 每 L1 独立文档位置

| L1 | 独立 PRD 文件夹 | 当前状态 |
|---|---|---|
| L1-01 主 Agent 决策循环 | `docs/2-prd/L1-01主 Agent 决策循环/prd.md` | ✅ PRD v1.0 完成（6 L2 全详细 + §14 对外 IC 映射 + §15 retro 位点） |
| L1-02 项目生命周期编排 | `docs/2-prd/L1-02项目生命周期编排/prd.md` | ⏸ 待撰写 |
| L1-03 WBS + WP 拓扑调度 | `docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md` | ⏸ 待撰写 |
| L1-04 Quality Loop | `docs/2-prd/L1-04 Quality Loop/prd.md` | ⏸ 待撰写 |
| L1-05 Skill + 子 Agent 调度 | `docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md` | ⏸ 待撰写 |
| L1-06 3 层知识库 | `docs/2-prd/L1-06 3层知识库/prd.md` | ⏸ 待撰写 |
| L1-07 Harness 监督 | `docs/2-prd/L1-07 Harness监督/prd.md` | ⏸ 待撰写 |
| L1-08 多模态内容处理 | `docs/2-prd/L1-08 多模态内容处理/prd.md` | ⏸ 待撰写 |
| L1-09 韧性 + 审计 | `docs/2-prd/L1-09 韧性+审计/prd.md` | ⏸ 待撰写 |
| L1-10 人机协作 UI | `docs/2-prd/L1-10 人机协作UI/prd.md` | ⏸ 待撰写 |
| **L1 集成方案** | `docs/2-prd/L1集成/prd.md` | ⏸ 待撰写（关键整合，最后写） |

### 6.2 每 L1 独立文档必须包含（模板）

每份 L1 独立文档必须按以下模板撰写（**不得省略**）：

| 章节 | 内容 | 承担来源 |
|---|---|---|
| 1. 引用 scope.md | 本 L1 在 scope.md 的章节号 + 外部契约引用 | 自动（必须） |
| 2. L2 子能力分解 | 3-5 个 L2，每个有职责/边界/输入输出 | 本文档（scope.md 不写） |
| 3. L3 实现设计 | 每 L2 下的具体实现设计（产品视角，不含技术栈） | 本文档 |
| 4. 内部状态机 | 本 L1 的内部状态 + 转换规则 | 本文档 |
| 5. 内部数据结构 | 本 L1 持有的数据模型 | 本文档 |
| 6. 对外契约实现 | 如何实现 scope.md §8.2 里本 L1 涉及的 IC-XX 契约 | 必须对齐 scope.md |
| 7. 内部异常处理 | 本 L1 如何处理内部异常 + 对外暴露的降级 | 本文档 |
| 8. 独立测试策略 | 如何单独 mock 其他 L1 测试本 L1 | 本文档 |
| 9. 本 L1 retro 位点 | 本 L1 完成实现后的复盘模板 | 本文档 |

### 6.3 独立文档与 scope.md 的一致性规则（必须遵守）

1. **独立文档不得修改 scope.md 定义的 L1 边界 / 接口 / 约束 / 禁止 / 义务**
2. 独立文档可**细化**（添加内部子能力 / 子状态）但**不得放宽** scope.md 的约束
3. 如独立文档发现 scope.md 有错 → 必须先 update scope.md → 再 update 独立文档（不得反向）
4. 独立文档必须通过"scope 一致性检查"（下游自动化校验，本期留 TODO）

---

## 7. L1 集成验证大纲

本章回答：**10 个 L1 全部独立实现后，如何验证它们能无缝集成成 HarnessFlow 完整系统**。

### 7.1 集成验证的 4 个层级

| 层级 | 内容 | 通过标准 |
|---|---|---|
| **L0 · 单 L1 独立单元测试** | 每 L1 mock 其他 L1 的接口跑通本 L1 功能 | 所有 L1 独立单测通过 |
| **L1 · 两两 L1 契约集成测试** | 按 §8.2 契约清单每对 L1 的 IC-XX 跑契约一致性 | 20+ 条 IC 契约全绿 |
| **L2 · 典型场景端到端测试** | §8.3 的 5 个端到端场景跑通 | 5 场景端到端通过 |
| **L3 · 全量系统压测** | 模拟完整超大型项目跑 7 阶段 + Quality Loop 多轮 | Goal §5 V1 量化指标达成 |

### 7.2 集成验证硬约束（任一不过 = 不达标）

1. 事件总线可完整重放 = task-board 可完全重建（property-based test）
2. 跨 session 恢复端到端测试通过（kill + restart 无损）
3. 硬红线 5 类全部集成测试通过
4. 软红线 8 类全部集成测试通过
5. Quality Loop 4 级回退路由全部集成测试通过
6. 每个 L1 的"禁止行为"都有对应的负向测试（violation → 应报错）
7. 每个 L1 的"必须义务"都有对应的正向测试（missing → 应报错）

### 7.3 集成失败处理

集成验证不过 = 独立文档或 scope.md 有问题：
- 如"L1 禁止行为"被违反 → 独立文档实现有 bug，回独立文档修
- 如"IC-XX 契约"不对 → scope.md §8.2 契约定义不精确，回 scope.md 修
- 如"场景端到端"不通 → 可能是边界定义有漏洞，回 scope.md §5 修

---

## 8. L1 间产品业务流（关键整合）

### 8.0 本章目的

回答**核心集成问题**：10 个独立实现的 L1 如何通过 scope.md 定义的**边界 + 接口 + 约束**组合成完整 HarnessFlow 系统。本章定义：

1. **4 类跨 L1 关系整合图**（控制流 / 数据流 / 监督流 / 持久化流）—— 见 §8.1
2. **L1 间接口契约清单**（IC-01 至 IC-20+）—— 见 §8.2
3. **典型端到端协作场景**（5 个覆盖正常 + 异常路径）—— 见 §8.3
4. **集成约束与失败传播规则**—— 见 §8.4

---

### 8.1 4 类跨 L1 关系整合图

#### 8.1.1 控制流图（L1-01 是唯一控制源）

```
                 用户输入 / 事件触发
                         ↓
                  ┏━━━━━━━━━━━━━┓
                  ┃ L1-10 UI    ┃ (用户入口)
                  ┗━━━━━━┳━━━━━━┛
                         │ 用户输入
                         ▼
                  ┏━━━━━━━━━━━━━━━━━━━┓
                  ┃ L1-01 主 loop     ┃ ← 心脏 · 控制唯一源
                  ┃ (持续 tick + 决策) ┃
                  ┗━━━━━━┳━━━━━━━━━━━━┛
                         │ 控制指令
            ┌────────────┼────────────┬────────────┐
            ▼            ▼            ▼            ▼
       ┏━━━━━━━┓  ┏━━━━━━━┓  ┏━━━━━━━┓  ┏━━━━━━━┓
       ┃ L1-02 ┃  ┃ L1-03 ┃  ┃ L1-04 ┃  ┃ L1-05 ┃
       ┃生命周期┃  ┃ WBS   ┃  ┃Quality┃  ┃Skill+ ┃
       ┃ 编排  ┃  ┃ 调度  ┃  ┃ Loop  ┃  ┃子Agent┃
       ┗━━━━━━━┛  ┗━━━━━━━┛  ┗━━━━━━━┛  ┗━━━━━━━┛
                              │            │
                              ▼            ▼
                        ┏━━━━━━━┓    ┏━━━━━━━━┓
                        ┃ L1-06 ┃    ┃ L1-08  ┃
                        ┃  KB   ┃    ┃多模态  ┃
                        ┗━━━━━━━┛    ┗━━━━━━━━┛
```

**关键规则**：L1-01 是**唯一控制源**。其他"做事的 L1" 不会互相直接调用（例如 L1-02 不直接调 L1-03），所有跨 L1 控制必经 L1-01 路由。这保证**单一决策路径 + 可审计**。

#### 8.1.2 数据流图（生产-消费链）

```
 用户输入
    ↓
[L1-02 S1 产出]    ═══→  章程 + goal_anchor
                              ↓
[L1-02 S2 产出]    ═══→  4 件套 (需求/目标/AC/质量)
                              ↓
                    ┌──────────┴──────────┐
                    ↓                      ↓
[L1-03]         WBS 拓扑                 TDD 蓝图 [L1-04 S3]
                    ↓                      │
                WP 定义                    │
                    ↓                      ↓
                    └──────→ [L1-04 S4] ←──┘
                                ↓
                              代码 + 测试
                                ↓
                         [L1-04 S5 TDDExe]
                                ↓
                          verifier_report
                                ↓
                     verdict + 回退路由 [L1-07 判定]
                                ↓
                              PASS
                                ↓
                         [L1-02 S7 收尾]
                                ↓
                          交付包（代码 + PMP + TOGAF + 审计链）
```

**关键规则**：数据流是**单向生产-消费链**，不允许"下游回写上游"。如 S4 发现 4 件套错 → 不直接改 4 件套，而是走 Quality Loop 回退路由（§8.3 场景 4）。

#### 8.1.3 监督流图（L1-07 旁路观察 + 干预）

```
  [L1-01 主 loop]
     │
     │ decision + event
     ▼
  ╔═══════════════════╗
  ║ L1-09 事件总线     ║ ← 单一事实源
  ╚════════╦══════════╝
           │ scan (只读)
           ▼
  ┏━━━━━━━━━━━━━━━━━━┓
  ┃ L1-07 Supervisor ┃ ← 旁路常驻 · 只读 · 每 30s + hook
  ┃                  ┃
  ┃ 8 维度计算        ┃
  ┃ 4 级分级判定      ┃
  ┗━━━┳━━━━━━━━┳━━━━━┛
      │        │
      │ 通道 A │ 通道 B
      ▼        ▼
  [L1-01]  [L1-04]
   收建议   收回退
   队列     路由
   (INFO/  (轻/中/重/
   SUGG/    极重)
   WARN/
   BLOCK)

        │
        │ 通道 C (软红线自治)
        ▼
  [触发对应 L1 动作]
  (如 L1-05 fallback, L1-09 压缩上下文)

        │
        │ 通道 D (硬红线上报)
        ▼
  [L1-01 硬暂停 + L1-10 强告警]
```

**关键规则**：
- L1-07 **不直接改业务状态**，所有修改通过"建议通道"请求 L1-01 / L1-04 执行
- BLOCK 级权力：仅 L1-07 能硬暂停 L1-01（其他 L1 不可）
- 4 级回退路由权力：仅 L1-07 能向 L1-04 发 rollback_route

#### 8.1.4 持久化流图（全部 → L1-09）

```
  全部 L1 (01-08, 10) 的 event
             ↓
   IC-09 append_event()
             ↓
    ┏━━━━━━━━━━━━━━━━━━┓
    ┃ L1-09 事件总线    ┃
    ┃ (append-only)    ┃
    ┃ fsync 每次       ┃
    ┗━━━━━━━┳━━━━━━━━━┛
            ↓
    /events/YYYY-MM-DD.jsonl
            ↓
      周期 snapshot
            ↓
    /task-boards/<id>.json
    /checkpoints/*.json
            ↓
    ┌───────┴────────┐
    ↓                ↓
[重启恢复]        [审计追溯]
    ↓                ↓
 task-board       [L1-10 时间轴]
 重建              [L1-10 审计面板]
```

**关键规则**：
- 单一写入点：`L1-09.append_event()`
- 不可变日志：append-only，禁止修改
- 重启必重放：事件总线是重建 task-board 的唯一来源
- 事件 hash 链：每事件 hash 含前事件 hash → 防篡改

---

### 8.2 L1 间接口契约清单（IC-01 至 IC-20）

**核心契约**（各 L1 独立实现时必须按此 schema 实现，违反 = 集成失败）：

| 契约 ID | 调用方 | 被调方 | 方法名 | 输入 schema | 输出 schema | 失败策略 |
|---|---|---|---|---|---|---|
| **IC-01** | L1-01 | L1-02 | `request_state_transition` | `{from, to, reason}` | `{accepted: bool, new_entry}` | reject if not in allowed_next |
| **IC-02** | L1-01 | L1-03 | `get_next_wp` | `{}` | `{wp_id, wp_def, deps_met: bool}` | null if all done |
| **IC-03** | L1-01 | L1-04 | `enter_quality_loop` | `{current_wp}` | `{loop_session_id}` | async, 立即返回 |
| **IC-04** | L1-01 / 其他 | L1-05 | `invoke_skill` | `{capability, params, timeout}` | `{result, skill_id, skill_version, duration_ms}` | 走 BF-E-05 fallback 链 |
| **IC-05** | L1-01 / 其他 | L1-05 | `delegate_subagent` | `{subagent_name, context_copy, goal, tools_whitelist, timeout}` | `{report}` | 走 BF-E-09 降级 |
| **IC-06** | L1-01 / 其他 | L1-06 | `kb_read` | `{kind?, scope?, context_filter, top_k?}` | `{entries[]}` | 降级到无 KB + 告警 |
| **IC-07** | L1-01 / 其他 | L1-06 | `kb_write_session` | `{entry: {kind, title, evidence, applicable_context, ...}}` | `{id}` | 写失败降级 log 告警 |
| **IC-08** | L1-01 / 其他 | L1-06 | `kb_promote` | `{id, target_scope: project/global, reason}` | `{promoted: bool}` | 拒绝如 observed_count 不达标且无用户批准 |
| **IC-09** | **全部 L1** | L1-09 | `append_event` | `{ts, type, actor, state, content, links}` | `{event_id, sequence, hash}` | 持久化失败 → **halt 整个系统** |
| **IC-10** | L1-09 | L1-09 | `replay_from_event` | `{from_seq?, to_seq?}` | `{task_board_state}` | 返回 err if 事件损坏 |
| **IC-11** | L1-01 / 其他 | L1-08 | `process_content` | `{type: 'md'/'code'/'image', path, action: 'read'/'write'/'update'/'analyze'}` | `{structured_description}` | err + log |
| **IC-12** | L1-08 | L1-05 | `delegate_codebase_onboarding` | `{repo_path}` | `{structure_summary, kb_entries}` | 同 IC-05 |
| **IC-13** | L1-07 | L1-01 | `push_suggestion` | `{level: 'INFO'/'SUGG'/'WARN'/'BLOCK', dimension, message, suggested_action}` | `{received_at}` | fire-and-forget (落事件) |
| **IC-14** | L1-07 | L1-04 | `push_rollback_route` | `{level: 'L1'/'L2'/'L3'/'L4', target_state, reason}` | `{routing_applied: bool}` | — |
| **IC-15** | L1-07 | L1-01 | `request_hard_halt` | `{red_line_id, message, require_user_authorization: true}` | `{halted: bool}` | halt 立即生效 |
| **IC-16** | L1-02 | L1-10 | `push_stage_gate_card` | `{gate_id, stage_from, stage_to, artifacts_bundle, required_decisions}` | `{user_decision, decided_at}` | blocks 直到用户决定 |
| **IC-17** | L1-10 | L1-01 | `user_intervene` | `{type: 'authorize'/'pause'/'resume'/'clarify'/'change_request', payload}` | `{accepted: bool}` | 接收即反馈 |
| **IC-18** | L1-10 | L1-09 | `query_audit_trail` | `{anchor: file_path/artifact_id/decision_id}` | `{trail: [decision, event, supervisor_comment, user_authz]}` | — |
| **IC-19** | L1-02 | L1-03 | `request_wbs_decomposition` | `{4_件套, architecture_output}` | `{wbs_topology}` | 失败回 S2 |
| **IC-20** | L1-04 | L1-05 | `delegate_verifier` | `{s3_blueprint, s4_artifacts, dod_expressions}` | `{verifier_report_json}` | 同 IC-05，失败降级到主 session 跑简化 DoD |

**契约版本规则**：
- 每条 IC 有 `version` 字段（v1 起）
- L1 升级必须保 backward compat 至少 1 个 minor 版本
- 升级点在对应独立 L1 文档的"对外契约实现"章节记录

---

### 8.3 典型端到端协作场景（5 个）

#### 场景 1 · WP 执行一轮 Quality Loop（正常路径）

```
[用户] → [L1-10 UI] 触发"下一 WP"
    │
    ▼
[L1-01] tick: 决策 = 取下一 WP
    │
    │ IC-02 get_next_wp
    ▼
[L1-03] 按拓扑找 WP-07 (依赖满足) → 返回 wp_def
    │
    ▼
[L1-01] 决策 = 进 Quality Loop
    │
    │ IC-03 enter_quality_loop
    ▼
[L1-04 S4] tick: 决策 = 调 `tdd` skill
    │
    │ IC-04 invoke_skill
    ▼
[L1-05] 调 `tdd` → 接收代码 + 测试
    │
    ▼
[L1-04 S4] 测试绿 + WP-DoD 自检 PASS → 进 S5
    │
    │ IC-20 delegate_verifier
    ▼
[L1-05] 委托 `verifier` 子 Agent → 独立 session → 返回 report
    │
    ▼
[L1-04 S5] 组装三段证据链 → verdict = PASS
    │
    ▼ (反馈)
[L1-01] 决策 = 取下一 WP (回 IC-02)

(并行: L1-07 每 30s 读事件总线 → 8 维度正常 → INFO 级"WP-07 完成")
(全程: 每步 IC-09 append_event 落盘)
```

#### 场景 2 · 硬红线触发（不可逆操作拦截）

```
[L1-01] 决策 = 调 `tdd` skill 实现功能 X
    │
    │ IC-04
    ▼
[L1-05] 调 tdd → tdd 准备执行 `rm -rf some/path`
    │
    │ IC-09 记录 "Bash: rm -rf" event
    ▼
[L1-09] 事件落盘
    │
    ▼ (L1-07 30s tick 读到)
[L1-07] 命中 IRREVERSIBLE_HALT 红线
    │
    │ IC-15 request_hard_halt
    ▼
[L1-01] 立即暂停 tick
    │
    │ UI 推送（通过事件总线 → UI 消费）
    ▼
[L1-10] 展示硬红线告警卡片 + 要求文本授权
    │
[用户] 文本授权 "允许"
    │
    │ IC-17 user_intervene
    ▼
[L1-01] 解除暂停 → 继续 tdd → rm -rf 执行
    │
    │ IC-09 记录 "user_authorized_rm_rf" event
    ▼
[L1-09] 审计链完整留痕
```

#### 场景 3 · 跨 session 恢复

```
[Session A 运行中]
    │
    │ (用户 Ctrl+C)
    ▼
[L1-01] 收 SIGINT
    │
    │ IC-09 最终事件 "session_exit"
    ▼
[L1-09] flush + checkpoint + fsync → 退出
[Session A 退出]

──────────────── (1 天后) ────────────────

[Session B 用户重启 Claude Code + /harnessFlow]
    │
    ▼
[L1-09] 扫 task-boards/ 找未 CLOSED 项目
    │
    │ IC-10 replay_from_event
    ▼
[L1-09] 重建 task-board 到 session_exit 前 state
    │
    ▼
[L1-10] 展示"已恢复 project X, state=S4/WP-07/VERIFY, 继续？"
    │
[用户] 点 Go
    │
    │ IC-17 user_intervene type=resume
    ▼
[L1-01] 接管 → 继续 tick
```

#### 场景 4 · 中度 FAIL 触发回退到 S3

```
[L1-04 S5 TDDExe 跑完]
    │
    ▼
[L1-05] verifier_report: verdict=INSUFFICIENT_EVIDENCE
        (3 条 AC 用例漏覆盖)
    │
    │ IC-09 落盘 verdict
    ▼
[L1-07] 读 report → 判定"中度 FAIL"（AC 用例盲区）
    │
    │ IC-14 push_rollback_route L2 → target=S3
    ▼
[L1-04] 接收 route → 请求 state 转换
    │
    │ IC-01 request_state_transition to=S3
    ▼
[L1-01] 验 allowed_next → 执行转换
    │
    ▼
[L1-02] S3 入口 → 告知 L1-04 重做 TDD 定义
    │
    ▼
[L1-04 S3] 增补用例覆盖漏的 AC → 产新蓝图
    │
    │ IC-16 push_stage_gate_card
    ▼
[L1-10] 用户 review 新蓝图 → Go
    │
    ▼
[L1-04] 回 Quality Loop (S4 → S5 重跑)
```

#### 场景 5 · Stage Gate 走完（S2 → S3）

```
[L1-02] S2 阶段产出齐全:
        4 件套 + 9 计划 + TOGAF A-D + WBS + ADR
    │
    │ IC-16 push_stage_gate_card
    ▼
[L1-10] 展示 Stage Gate 待审卡片 + 产出物预览
    │
[用户] 逐项 review + 点 Go
    │
    │ IC-17 user_intervene type=authorize
    ▼
[L1-01] 记录用户决定 → IC-01 request_state_transition S2→S3
    │
    ▼
[L1-02] 验 allowed_next → 执行转换
    │
    ▼ (阶段切换 hook)
[L1-06] IC-06 kb_read: 按 S3 注入策略（trap + anti_pattern）
    │
    │ 返回 KB entries
    ▼
[L1-01] 注入上下文
    │
    ▼
[L1-04] 开始 S3 TDD 规划
```

---

### 8.4 集成约束与失败传播规则

#### 8.4.1 集成约束（硬性）

1. **命名空间约束**：每个 L1 的事件 type 必须 `L1-XX:subtype` 前缀（`L1-01:decision`、`L1-04:verdict`）。禁止混用。
2. **事件总线单一访问点**：所有 L1 只通过 IC-09 改 task-board，禁止直接 file I/O。
3. **契约版本兼容**：每条 IC 有 version；升级必须 backward compat ≥ 1 minor。
4. **接口调用超时**：跨 L1 IC 调用默认 timeout = 30 秒；跨 session 子 Agent 例外（5 min）。
5. **数据一致性**：task-board 是单一事实源；若事件总线与 task-board 冲突 → 以事件总线为准（重新 replay）。
6. **L1 独立性**：每个 L1 可独立单元测试，mock 其他 L1 的接口。
7. **禁止直接跨 L1 调用（除 IC 外）**：L1 之间只能通过 scope.md §8.2 的 IC-XX 契约交互，禁止私下调用。

#### 8.4.2 失败传播规则

| 失败源 | 传播路径 | 最终影响 | 用户可见性 |
|---|---|---|---|
| L1-05 skill 调用失败 | → BF-E-05 降级链 → 全失败则硬暂停 | L1-01 暂停 | 用户上报 |
| L1-05 子 Agent crash | → BF-E-09 降级（重试 1 次 → 降级 / 硬暂停） | 可能降级或硬暂停 | 仅硬暂停告警 |
| L1-06 KB 读失败 | → 降级到无 KB 决策 + 告警 | L1-01 可继续，质量降 | 告警角 INFO |
| L1-08 文件读失败 | → err + log + 重试 / 跳过 | 不致命 | INFO |
| L1-09 事件总线写失败 | → **halt 整个系统**（无法降级） | 硬终止 | 强告警 + 诊断 |
| L1-07 supervisor crash | → 重启 + 告警 | L1-01 可继续但失监督 | WARN |
| **硬红线触发** | → L1-07 → IC-15 L1-01 暂停 | 用户授权才解除 | **强告警** |
| Quality Loop 死循环 | → L1-07 同级 ≥ 3 升级 → 最终硬暂停 | 用户介入 | WARN → 强告警 |
| 网络异常 | → BF-E-03 指数 backoff → MCP 重连 / 本地替代 / 硬暂停 | 取决于恢复 | 视情况 |
| API 限流 | → BF-E-04 backoff / 节能模式 / 硬暂停 | 取决于恢复 | 节能模式 INFO，硬暂停强告警 |
| 上下文爆炸 (> 80%) | → BF-E-06 自动压缩 / compact session | 无用户感知 | INFO |

#### 8.4.3 集成验证清单（详见 §7）

- [ ] 10 个 L1 全部独立单元测试绿
- [ ] 20+ IC 契约全部 schema + 测试
- [ ] 5 典型协作场景端到端测试通过
- [ ] 事件总线可重放 = task-board 可重建（property test）
- [ ] 跨 session 恢复端到端测试通过
- [ ] 硬红线 5 类全集成测试
- [ ] 软红线 8 类全集成测试
- [ ] 每 L1 禁止行为有负向测试
- [ ] 每 L1 必须义务有正向测试

---

## 9. UI 交互功能全景（占位 · 后续轮次）

UI 承载能力 L1-10 已在 §5.10 详细定义。本章后续轮次将补齐：
- 现有 11 tab + 9 admin 的完整交互说明
- 新增 P0 / P1 / P2 UI 缺口的交互用例（§3.4）
- UI 与其他 L1 的事件消费详细映射

---

## 附录 A · L1 ↔ businessFlow 聚类映射表

| L1 | 聚合自 businessFlow.md 的流 |
|---|---|
| L1-01 主 Agent 决策循环 | BF-L3-01 / 12 / 13 / 14 / 15 + BF-X-01 |
| L1-02 项目生命周期编排 | BF-S1 全部 + BF-S2 全部 + BF-S3 全部 + BF-S7 全部 + BF-L3-10 + BF-X-06 |
| L1-03 WBS + WP 拓扑 | BF-S2-07 + BF-S4-01 / 02 / 05 |
| L1-04 Quality Loop | BF-S3-01/02/03/04/05 + BF-S4-03/04 + BF-S5 全部 + BF-E-10 |
| L1-05 Skill 生态 + 子 Agent | BF-L3-02 / 03 / 04 + BF-X-07 + BF-E-05 / 09 |
| L1-06 3 层知识库 | BF-L3-05 + BF-X-05 + BF-S7-04 |
| L1-07 Harness 监督 | BF-S6 全部 + BF-X-02 + BF-E-07 / 10 / 11 / 12 |
| L1-08 多模态内容处理 | BF-L3-06 / 07 / 08 |
| L1-09 韧性 + 审计 | BF-X-03 / 04 / 08 + BF-E-01 / 02 / 03 / 04 / 06 / 08 |
| L1-10 人机协作 UI | BF-L3-09 + BF-S1-04 / BF-S2-09 / BF-S3-05 / BF-S7-05 各 Stage Gate + 现有 UI mock |

---

## 附录 B · L1 ↔ Goal 追溯矩阵

| L1 | 对应 Goal 条目 |
|---|---|
| L1-01 | §1 一句话目标 · §2 产品定位（主 Agent loop 核心） |
| L1-02 | §2.2 双层骨架 · §4.3 methodology-paced autonomy |
| L1-03 | §2.3 WP 拓扑 |
| L1-04 | §2.2 五大纪律"质量+检验" · §4.1 决策可追溯率 100% |
| L1-05 | §2 产品定位"调度 Skill 生态"· 附录 A 术语 |
| L1-06 | §3.2.D 知识沉淀 · 附录 A KB 三层 |
| L1-07 | §7.3 supervisor 分级权威 · §3.3 低频通知 |
| L1-08 | §3.1 输入（含 Brownfield / 多仓库） |
| L1-09 | §4.1 "可跨 session 恢复" + "决策可追溯 100%" |
| L1-10 | §4 过程（人机互动）· §3.3 Stage Gate |

---

## 附录 C · 术语速查

| 术语 | 含义 |
|---|---|
| **L1** | 顶层产品能力，聚合自 business flow 簇 |
| **L2** | L1 内部的子能力（下一轮展开） |
| **L3** | L2 内部的细粒度能力（再下一轮展开） |
| **主 skill** | `/harnessFlow` 总入口 slash command |
| **监督 skill** | `harnessFlow:supervisor` 常驻旁路 subagent |
| **UI** | localhost:8765 Web 界面（11 tab 任务详情 + 9 admin 后台） |
| **4 件套** | 需求 / 目标 / 验收 / 质量 四份文档（S2 Gate 硬性产出） |
| **TDD 蓝图** | Master Test Plan + DoD + 用例 + 质量 gate + 验收 checklist（S3 产出） |
| **Quality Loop** | S4 执行 ↔ S5 TDDExe 循环 + S6 监督 |
| **4 级回退** | 轻度（回 S4）/ 中度（回 S3）/ 重度（回 S2）/ 极重度（回 S1） |
| **In-Scope** | 产品范围内做的事（10 个 L1 覆盖） |
| **Out-of-Scope** | 明确不做的事（11 条） |
| **边界** | L1 之间 / 产品与外部之间的职责分界 |

---

*— Scope Spec v0.1 · 本轮完（总 layer · L1 地图 + 载体映射 + 范围粗线条） —*
*— 等待用户 review §1-§4 → Go 则推进 §5 L1 详细定义 —*
