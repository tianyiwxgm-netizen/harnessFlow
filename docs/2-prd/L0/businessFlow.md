# HarnessFlow 业务流程地图（Business Flow Map）

> 版本：v1.0（最终稿）· 更新时间：2026-04-20
> 本文件是 `HarnessFlowPrdScope.md` 的配套业务流底稿。
> 回答："为实现 Goal，HarnessFlow 内部必须发生哪些业务流程、流程如何衔接、异常如何处理。"
>
> **分层原则：** L1 主流程 → L2 阶段内分流程 → L3 活动级细节 → 横切流 → 异常流 → 业务模式。
> **核心架构：** 7 阶段主骨架 + Quality Loop 闭环 + Supervisor 监督 + 4 级偏差回退 + 红线分级自治。

---

## 0. 撰写进度

- [x] 第 1 章 · 业务目标还原
- [x] 第 2 章 · 业务流分层原则 + 13 业务模式清单
- [x] 第 3 章 · L1 主流程（7 阶段 + Quality Loop 总图 + 回退规则 + 硬约束）
- [x] 第 4 章 · L2 分子流程（每阶段 3-6 子流，共 ~25 条）
- [x] 第 5 章 · L3 活动级流程（含文档处理 / 代码分析 / 图片分析 / KB 读写 / loop 触发 等）
- [x] 第 6 章 · 横切流（决策心跳 / 监督观察 / 事件总线 / 审计等）
- [x] 第 7 章 · 异常与降级流（会话退出 / 网络 / API 限流 / 任务走偏 / 死循环等）
- [x] 第 8 章 · 13 业务模式详解
- [x] 附录 A · 业务流 ↔ Goal 追溯矩阵
- [x] 附录 B · 术语速查

---

## 1. 业务目标还原

引自 `HarnessFlowGoal.md`：

> HarnessFlow 接收「项目目标 + 资源约束」→ 以 PMP 5 过程组 × TOGAF 9 ADM 双主干骨架 + 5 大纪律（规划 / 质量 / 拆解 / 检验 / 交付）为指引 → 按 methodology-paced 节奏（规划协同 / 执行自走 / 交付强 Gate）→ 端到端自治推进一个超大型复杂软件项目 → 产出可运行软件 + 完整 PMP 产出物包 + 完整 TOGAF 产出物包 + 可审计决策链。

### 业务流设计必须回答的 5 个 First-Principle 问题

1. **用户如何启动？** HarnessFlow 如何理解目标并锚定？
2. **如何规划与设计？** PMP 9 计划 + TOGAF A-D 架构 + 4 件套（需求/目标/验收/质量）+ WBS 如何产出？
3. **如何以质量为核心去执行？** TDD 规划 → 执行 → TDDExe 闭环如何跑？偏差如何回退？
4. **如何自我监督？** Supervisor 如何识别偏差 / 触发回退 / 分级处理红线？
5. **如何交付与沉淀？** 用户如何验收？知识如何晋升到 Global / Project KB？

所有业务流必须回答上述 5 问之一且相互衔接。

---

## 2. 业务流分层原则

### 2.1 层级定义

| 层级 | 粒度 | 典型规模 | 示例 |
|---|---|---|---|
| **L1 主流程** | 用户旅程级（一个项目=一条 L1） | 1 个（7 阶段） | 项目启动→规划架构→TDD规划→执行→TDDExe→监控→收尾 |
| **L2 分子流程** | 阶段内 / 过程组级 | ~25 个 | 澄清对齐流 / 4 件套生成流 / WBS 拆解流 / TDDExe 裁定流 |
| **L3 活动级细节** | 单一活动级 | ~15 个 | 调 skill / 读 KB / 写 md / 分析图片 / 读代码 / 请示用户 |
| **横切流** | 贯穿所有阶段 | 8 个 | 决策心跳 / 监督观察 / 事件总线 / 审计追溯 / loop 触发 |
| **异常流** | 失败与恢复 | 12 个 | 会话退出恢复 / 网络异常 / API 限流 / 任务走偏 / 死循环保护 |

### 2.2 13 个业务模式（横切约束，详见第 8 章）

PM-01 methodology-paced 节奏 · PM-02 主-副 Agent 协作 · PM-03 子 Agent 独立 session 委托 · PM-04 WP 拓扑并行推进 · PM-05 Stage Contract 机器可校验 · PM-06 KB 三层 + 阶段注入 · PM-07 产出物模板驱动 · PM-08 可审计全链追溯 · PM-09 能力抽象层调度 · PM-10 事件总线单一事实源 · PM-11 5 纪律贯穿拷问 · PM-12 红线分级自治（软/硬）· PM-13 合规可裁剪

---

## 3. L1 主流程：一个超大型项目的完整旅程

### 3.1 L1 总图（7 阶段 + Quality Loop）

```
┌──────────────────────── 起点 ────────────────────────┐
│ 用户输入: 项目目标 + 资源约束 + 启动模式              │
└──────────────────────────┬───────────────────────────┘
                           ▼
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ S1 启动阶段 (PMP 启动过程组)                  ┃ 🟢 强协同
  ┃ • 需求澄清 (2-3 轮)                          ┃
  ┃ • 项目章程 (Project Charter)                  ┃
  ┃ • 干系人登记 (Stakeholder Register)           ┃
  ┃ • goal_anchor sha256 锁定                     ┃
  ┗━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┛
                       ▼ Stage Gate · 用户 Go/No-Go
                       ▼                                     ←─────╮
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓                 │
  ┃ S2 规划+架构阶段 (PMP 规划 × TOGAF A-D)       ┃ 🟢 强协同        │
  ┃ ┌─ 4 件套强制产出: ─────────────────────────┐ ┃                 │
  ┃ │ ① 需求 (功能+非功能+约束+依赖)             │ ┃                 │
  ┃ │ ② 目标 (终极+WP子目标+成功标准+非目标)     │ ┃                 │
  ┃ │ ③ 验收标准 (项目级+WP级+场景+验收人)        │ ┃                 │
  ┃ │ ④ 质量标准 (代码/文档/性能/安全/审计)       │ ┃                 │
  ┃ └───────────────────────────────────────────┘ ┃                 │
  ┃ + PMP 9 大计划                                ┃                 │
  ┃ + TOGAF A 愿景 / B 业务 / C 信息系统 /        ┃                 │
  ┃   D 技术架构 / ADR                            ┃                 │
  ┃ + WBS 拓扑 (WP 分解 + 依赖图 + 工时估算)      ┃                 │
  ┗━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┛                 │
                       ▼ Stage Gate · 用户 Go/No-Go                  │
                       ▼                                    ←──╮     │
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓              │     │
  ┃ S3 TDD 规划阶段 (NEW · 质量蓝图)              ┃ 🟢 协同        │     │
  ┃ 基于 S2 4 件套, 产出可机器校验的:              ┃              │     │
  ┃ • Master Test Plan (项目级测试总览)           ┃              │     │
  ┃ • DoD 表达式 (每 state + 每 WP, AST 可 eval) ┃              │     │
  ┃ • 全量测试用例 (unit / integration / E2E)    ┃              │     │
  ┃ • 质量 gate 规则 (覆盖率 / 性能阈值 / 审查)   ┃              │     │
  ┃ • 验收 checklist (项目级 + 每 WP 级)          ┃              │     │
  ┗━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┛              │     │
                       ▼ Stage Gate                          │     │
  ╔════════════════════════════════════════════════════════╗  │     │
  ║  ★ Quality Loop — WP 拓扑驱动, Supervisor 监督 ★        ║  │     │
  ║                                                        ║  │     │
  ║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓          ║  │     │
  ║  ┃ S4 执行阶段 (PMP 执行 × TOGAF E-G)        ┃ 🟡 自走    ║  │     │
  ║  ┃ 按 WBS 拓扑取下一可执行 WP →             ┃          ║  │     │
  ║  ┃ WP 内 mini-PMP: IMPL → 调 skill →        ┃          ║  │     │
  ║  ┃ 单元/集成测试 →                          ┃          ║  │     │
  ║  ┃ WP-DoD 自检                              ┃          ║  │     │
  ║  ┗━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┛          ║  │     │
  ║                      ▼                                 ║  │     │
  ║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓          ║  │     │
  ║  ┃ S5 TDDExe 质量执行验收 (NEW · 强 Gate)     ┃ 🟡 自治    ║  │     │
  ║  ┃ Verifier 独立子 Agent 对照 S3 蓝图跑:      ┃          ║  │     │
  ║  ┃ • 全量测试用例 (AST eval)                 ┃          ║  │     │
  ║  ┃ • DoD 逐条校验                            ┃          ║  │     │
  ║  ┃ • 质量 gate 规则 eval                     ┃          ║  │     │
  ║  ┃ • 验收 checklist 逐条走                   ┃          ║  │     │
  ║  ┃ • 组装三段证据链:                         ┃          ║  │     │
  ║  ┃   existence / behavior / quality          ┃          ║  │     │
  ║  ┗━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┛          ║  │     │
  ║                      ▼                                 ║  │     │
  ║          ╔═══════════════════════════╗                 ║  │     │
  ║          ║   TDDExe Verdict 判定     ║                 ║  │     │
  ║          ╚═══════════════════════════╝                 ║  │     │
  ║           │     │      │      │      │                 ║  │     │
  ║           ▼     ▼      ▼      ▼      ▼                 ║  │     │
  ║         PASS 轻度  中度   重度   极重度                  ║  │     │
  ║           │  FAIL  FAIL   FAIL    FAIL                  ║  │     │
  ║           │   │     │       │      │                   ║  │     │
  ║           │  回S4  回S3   回S2   回S1  ───────────────────╯
  ║           │ (改码)(改TDD  (重规   (重锚                  │
  ║           │       定义)   划架构) 定 goal) ──────────────────╯
  ║           │                                            ║
  ║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓          ║
  ║  ┃ S6 监控阶段 (旁路 · 并行 S4/S5 全程)       ┃ 🔵 自治    ║
  ║  ┃ Supervisor 常驻:                          ┃          ║
  ║  ┃ • 读 task-board + verifier_report         ┃          ║
  ║  ┃ • 识别偏差等级 → 路由回退                 ┃          ║
  ║  ┃ • 软红线自治 / 硬红线上报                 ┃          ║
  ║  ┃ • 死循环检测 (同级 ≥3 次 → 升级)          ┃          ║
  ║  ┃ • 周期状态报告 (周/里程碑)                 ┃          ║
  ║  ┃ • 事件总线落盘                            ┃          ║
  ║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛          ║
  ╚════════════════════════════════════════════════════════╝
                       ▼ (S5 PASS → 退出 loop)
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ S7 收尾阶段 (PMP 收尾 × TOGAF H)               ┃ 🔴 强制 Gate
  ┃ • 交付物汇总 (代码 + PMP 包 + TOGAF 包)        ┃
  ┃ • 最终验收 (用户 Go/No-Go)                    ┃
  ┃ • retro 11 项复盘                              ┃
  ┃ • archive 归档                                 ┃
  ┃ • KB 晋升 (Session → Project / Global)         ┃
  ┗━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┛
                       ▼ 用户最终验收
                       ▼
             ┌──────────────────────────┐
             │ 终态:                      │
             │  CLOSED (成功)             │
             │  ABORTED (失败)            │
             │  PAUSED (待人)             │
             └──────────────────────────┘

═══════════════════════════════════════════════════════════════
分叉出口（任意阶段可能触发, 详见第 7 章异常流）:
  ├── 🚨 硬红线 BLOCK → 暂停 loop → 用户授权 → 解除/终止
  ├── 🔄 用户变更请求 → TOGAF H 变更管理流 → 更新计划
  ├── 🛑 用户放弃 / 红线终止 → ABORTED 中止旅程
  ├── 💤 会话退出 → 持久化事件总线 → 跨 session 恢复到退出点
  ├── 🌐 网络异常 → 降级重试 / MCP 断连兜底
  ├── 🎫 API 限流 → backoff + 任务重排
  └── 📉 soft-drift → supervisor WARN → replan 建议
═══════════════════════════════════════════════════════════════
```

### 3.2 4 级偏差判定规则（Supervisor 自动判定）

| 级别 | 判定信号 | 回退到 | 典型场景 | 自治 vs 人工 |
|---|---|---|---|---|
| **PASS** | 全部用例 pass + DoD 全 pass + 质量 gate 通过 | 退出 loop | 正常通过 | 🔵 自治通过 |
| **轻度 FAIL** | 单测 fail / DoD 某项布尔 false / 代码 bug 可定位 | 回 S4 修代码 | 代码 bug、边界条件漏 | 🔵 自治回退，不问人 |
| **中度 FAIL** | 测试用例漏覆盖 / DoD 表达式错 / AC 不合理 | 回 S3 重做 TDD 规划 | AC 歧义、用例盲区 | 🟡 软通知用户，自治重做 |
| **重度 FAIL** | 架构选型错 / WBS 拓扑不对 / 9 计划违反现实 | 回 S2 重规划 | 技术方案不可行、资源不足 | 🔴 必须人工确认 |
| **极重度 FAIL** | goal_anchor 与现实根本冲突 / 用户本意被误解 | 回 S1 重锚定 | 需求理解错、方向错 | 🔴 必须人工重锚 |

**死循环保护**：同一级别 FAIL 连续 ≥ 3 次 → 自动升级到上一级。3 次重度 FAIL → 硬拦截上报用户。

### 3.3 各阶段用户协同度

| 阶段 | 协同度 | 用户介入频率 | 典型介入形式 |
|---|---|---|---|
| **S1 启动** | 🟢 强协同 | 3-5 次/阶段 | 澄清问答、章程评审、干系人确认、Stage Gate |
| **S2 规划+架构** | 🟢 强协同 | 5-10 次/阶段 | 4 件套评审、WBS 评审、架构方案评审、ADR 确认、Stage Gate |
| **S3 TDD 规划** | 🟢 协同 | 3-5 次/阶段 | Master Test Plan 评审、AC 细化、质量 gate 阈值确认、Stage Gate |
| **S4 执行** | 🟡 自走 | 0-3 次/周 | 红线授权、凭证提供、紧急变更 |
| **S5 TDDExe** | 🟡 自治 | 0-1 次/周 | 中度 FAIL 软通知 |
| **S6 监控** | 🔵 自治 | 0-1 次/周 | 阅读状态报告 |
| **S7 收尾** | 🔴 强制 Gate | 1-3 次 | 全量验收、最终报告确认、retro 共评 |

### 3.4 主 Agent loop 在各阶段的核心职责

| 阶段 | 主 Agent 做什么 | 典型调用 skill / 子 Agent |
|---|---|---|
| S1 启动 | 引导澄清 → 章程 → 干系人 → goal_anchor 锁定 | `brainstorming`、`prp-prd` |
| S2 规划+架构 | 生成 4 件套 + 9 计划 + TOGAF A-D + WBS + ADR | `writing-plans`、`prp-plan`、`architecture-decision-records`、`architecture-reviewer`（子 Agent） |
| S3 TDD 规划 | 翻译 4 件套为可机器校验形式 | `test-driven-development`、`prp-plan`（测试维度）、`verifier`（规则编译） |
| S4 执行 | WP 拓扑推进 → WP mini-PMP → 调 TDD 写代码 → WP-DoD 自检 | `tdd`、`prp-implement`、`executing-plans` |
| S5 TDDExe | 独立 Verifier 跑全量验证 + 三段证据链 | `verifier`（子 Agent）、`verification-before-completion` |
| S6 监控 | 识别偏差 → 路由回退 → 软红线自治 → 硬红线上报 | `supervisor`（子 Agent，常驻） |
| S7 收尾 | 交付汇总 → retro → archive → KB 晋升 | `retro-generator`、`failure-archive-writer`、内建交付打包器 |

### 3.5 L1 硬约束（任何裁剪版不可违背）

1. **必经 7 阶段 + Quality Loop**：S1 → S2 → S3 → {S4 ↔ S5}（loop）+ S6 并行 → S7；不可跳过任一阶段。
2. **必有 4 次 Stage Gate**：S1 末、S2 末、S3 末、S7 末。每次必须用户明确 Go/No-Go。
3. **必有 methodology-paced 节奏**：协同度按 §3.3 严格执行。
4. **Quality Loop 硬性规则**：S5 未 PASS 不得进 S7；S5 PASS 不得回 S4 之前阶段。
5. **4 件套硬性要求**：S2 Stage Gate 必须齐全 4 份文档才能进 S3。
6. **死循环保护**：同级 FAIL ≥ 3 次触发自动升级。
7. **终态必为 CLOSED / ABORTED / PAUSED 之一**。
8. **S5 PASS = Goal 达成**：所有后续 L2/L3 终点汇入 S5 PASS。

---

## 4. L2 分子流程（~25 条，按 S1-S7 分组）

### 4.1 S1 启动阶段内子流（4 条）

| 编号 | 流名 | 触发 | 输入 | 输出 | 下一流 |
|---|---|---|---|---|---|
| **BF-S1-01** | 需求澄清对齐流 | 用户提交目标 | 原始目标 + 资源 | 澄清后目标 + goal_anchor 草稿 + unclear 清单 | BF-S1-02 |
| **BF-S1-02** | 项目章程生成流 | goal_anchor 草稿就绪 | 草稿 + 资源 | `docs/charters/*.md` | BF-S1-03 |
| **BF-S1-03** | 干系人识别登记流 | 章程初稿就绪 | 章程 | `docs/stakeholders/*.md` | BF-S1-04 |
| **BF-S1-04** | S1 Stage Gate | 章程+干系人齐全 | 全 S1 产出 | Go（→S2）/ No-Go | S2 或 S1 回修 |

### 4.2 S2 规划+架构阶段内子流（9 条）

| 编号 | 流名 | 输入 | 输出 |
|---|---|---|---|
| **BF-S2-01** | 4件套①：需求文档生成流 | 章程 + goal_anchor | `docs/planning/requirements.md` |
| **BF-S2-02** | 4件套②：目标文档生成流 | 需求文档 | `docs/planning/goals.md` |
| **BF-S2-03** | 4件套③：验收标准生成流 | 目标文档 | `docs/planning/acceptance-criteria.md`（Given-When-Then） |
| **BF-S2-04** | 4件套④：质量标准生成流 | AC + 非功能需求 | `docs/planning/quality-standards.md` |
| **BF-S2-05** | PMP 9 大计划生成流 | 4 件套 | 9 份 plan md |
| **BF-S2-06** | TOGAF ADM A-D 产出流 | 4 件套 + 9 计划 | `docs/architecture/{A,B,C,D}.md` + ADR |
| **BF-S2-07** | WBS 拆解流 | 4 件套 + 9 计划 + 架构 | `docs/planning/wbs.md`（拓扑 + 依赖 + 工时） |
| **BF-S2-08** | 架构评审委托流（可选） | 全 S2 产出 | 评审报告 |
| **BF-S2-09** | S2 Stage Gate | 全 S2 产出齐全 | Go（→S3）/ No-Go |

### 4.3 S3 TDD 规划阶段内子流（5 条）

| 编号 | 流名 | 输入 | 输出 |
|---|---|---|---|
| **BF-S3-01** | Master Test Plan 生成流 | 4 件套 + WBS | `docs/testing/master-test-plan.md` |
| **BF-S3-02** | DoD 表达式编译流 | 4 件套 + WBS | `docs/testing/dod-expressions.yaml` |
| **BF-S3-03** | 全量测试用例生成流 | AC + 用例矩阵 | `tests/generated/*.py` 骨架（先红灯） |
| **BF-S3-04** | 质量 gate + 验收 checklist 生成流 | 质量标准 + AC | `docs/testing/quality-gates.yaml` + `acceptance-checklist.md` |
| **BF-S3-05** | S3 Stage Gate | 全 S3 产出齐全 | Go（→ Quality Loop）/ No-Go |

### 4.4 S4 执行阶段内子流（5 条）

| 编号 | 流名 | 触发 | 输出 |
|---|---|---|---|
| **BF-S4-01** | WP 取任务流（拓扑调度） | 上一 WP 完成 / 进 loop | 锁定下一 WP |
| **BF-S4-02** | WP 内 mini-PMP 流 | WP 锁定 | WP 推进记录 |
| **BF-S4-03** | TDD 驱动实现流 | WP IMPL | 代码 + 测试变绿 |
| **BF-S4-04** | WP-DoD 自检流 | 测试变绿 | 自检报告 |
| **BF-S4-05** | WP commit 流 | 自检 PASS | git commit（WP 粒度） |

### 4.5 S5 TDDExe 阶段内子流（4 条）

| 编号 | 流名 | 输入 | 输出 |
|---|---|---|---|
| **BF-S5-01** | Verifier 独立调用流 | S4 完成 | `verifier_reports/*.json` |
| **BF-S5-02** | 三段证据链组装流 | Verifier 结果 | three_segments{existence, behavior, quality} |
| **BF-S5-03** | 偏差等级判定流 | verifier_report | verdict ∈ {PASS, FAIL_L1-L4} |
| **BF-S5-04** | 回退路由流 | verdict != PASS | loop back 指令 |

### 4.6 S6 监控阶段内子流（5 条）

| 编号 | 流名 | 触发 | 输出 |
|---|---|---|---|
| **BF-S6-01** | 周期状态报告生成流 | 周触发 / 里程碑 | `docs/status-reports/*.md` |
| **BF-S6-02** | 风险识别与登记流 | 事件扫描 | `docs/risk-register.md` 更新 |
| **BF-S6-03** | 变更请求处理流 | 用户提交 / 识别变更 | 变更评估 + 计划更新 |
| **BF-S6-04** | 软红线自治修复流 | 软红线命中 | 自动修复动作 |
| **BF-S6-05** | 硬红线上报流 | 硬红线命中 | 硬暂停 + 用户上报 |

### 4.7 S7 收尾阶段内子流（5 条）

| 编号 | 流名 | 输入 | 输出 |
|---|---|---|---|
| **BF-S7-01** | 交付物汇总流 | 全部 WP + S5 PASS | `delivery/` 交付包 |
| **BF-S7-02** | retro 11 项复盘生成流 | 交付包 | `retros/*.md` |
| **BF-S7-03** | archive 归档流 | retro 就绪 | `failure-archive.jsonl` 追加 |
| **BF-S7-04** | KB 晋升仪式流 | archive 就绪 | Project / Global KB 新增 |
| **BF-S7-05** | S7 最终验收 Stage Gate | 全 S7 产出齐全 | Go（→ CLOSED）/ No-Go |

---

## 5. L3 活动级流程（~15 条，最细粒度）

### 5.1 主 Agent 决策循环原子流（核心！）

#### BF-L3-01 · 决策心跳 tick 流
- **触发**：事件总线新事件 / PostToolUse hook / 30s 周期 tick / 用户输入
- **输入**：当前 task-board 状态 + 近 N 条事件 + supervisor 建议 + KB 注入
- **输出**：一个"下一步动作"决策
- **正常路径**：

```
(新 tick 触发)
  ↓
① 读当前 state + 5 纪律拷问
  ↓
② 查 KB (Global/Project/Session) 找相关模式
  ↓
③ 读 supervisor 建议队列
  ↓
④ 决策树:
     "需要澄清？" → BF-L3-09 请示用户
     "需要某能力？" → BF-L3-02 Skill 调度
     "需要外部事实？" → BF-L3-04 工具调用
     "需要独立验证？" → BF-L3-03 子 Agent 委托
     "需要读文档？" → BF-L3-06 文档处理
     "需要读代码？" → BF-L3-07 代码分析
     "需要读图？" → BF-L3-08 图片分析
     "需要存记忆？" → BF-L3-05 KB 写入
     "当前 DoD 满足？" → 进下个 state
  ↓
⑤ 执行动作
  ↓
⑥ 记录决策到事件总线 (decision + reason + result)
  ↓
⑦ 返回 loop 等下一 tick
```

### 5.2 资源调度类

#### BF-L3-02 · Skill 调度流
- **触发**：决策心跳选择"调 skill"
- **输出**：skill 产出
- **路径**：查能力抽象层（PM-09）→ 匹配可用 skill → 优先级排序 → 调用 → 接收结构化回传 → 写回 task-board
- **分支**：首选 skill 不可用 → fallback（BF-E-05）

#### BF-L3-03 · 子 Agent 委托流
- **触发**：决策心跳选择"委托子 Agent"
- **路径**：包 context 副本（避免污染）→ 新 session 启动子 Agent（verifier / retro / archive / reviewer）→ 子 Agent 独立决策心跳 → 返回结果 → 主 Agent 整合
- **分支**：子 Agent crash / 超时 → BF-E-09

#### BF-L3-04 · 工具调用流
- **触发**：决策心跳选择"用原子工具"
- **工具集**：Read / Write / Edit / Bash / Grep / WebSearch / WebFetch / Playwright / MCP
- **路径**：从工具柜取 → 调用 → 记录签名 → 返回
- **分支**：工具失败 → 重试 3 次 → 仍失败则 BF-E-04

### 5.3 内容处理类

#### BF-L3-06 · 文档处理流（读 md / 写 md / 更新产出物）
- **action 分派**：

```
action == "read":
  → Read 工具 → 解析 frontmatter / sections → 返回结构化
action == "write":
  → 按模板生成 markdown → Write 工具落盘 → 记入事件总线
action == "update":
  → Read 原内容 → Edit 工具做增量修改 → 保留历史 diff
action == "analyze":
  → Read + 按 section 分析 → 提取关键信息 → 存入 session KB
```

- **分支**：文档 > 2000 行 → 分页读取；不存在 → 创建或报错

#### BF-L3-07 · 代码读取与分析流
- **触发**：Brownfield 项目启动 / 理解现有仓库
- **路径**：

```
① Glob 扫目录结构 → 识别语言 / 框架 / 入口
② Read 关键入口文件 (main.py / index.ts / pom.xml / package.json)
③ Grep 关键模式（类/函数/API 端点/DB 访问）
④ 生成代码结构摘要（含依赖图）
⑤ 写入 Project KB (持久化)
```

- **分支**：代码量大（>10万行）→ 按模块分批 + 委托 `codebase-onboarding` 子 Agent

#### BF-L3-08 · 图片/截图分析流
- **触发**：用户上传架构图 / Playwright 截图 / UI mock 需读
- **路径**：

```
① Read 工具加载图片（Claude 多模态直接读）
② 主 Agent 视觉理解
③ 产出描述（按图片类型）:
   - 架构图 → 节点列表 + 关系图 + 技术栈
   - UI mock → 布局描述 + 组件清单 + 交互点
   - 截图 → 当前页面状态 + 文本 + 错误迹象
④ 结构化结果写入事件总线 + session KB
```

### 5.4 记忆读写类

#### BF-L3-05 · KB 读写流
- **read 路径**：

```
① 按 scope 优先级（Session > Project > Global）搜索
② 按 kind (pattern/trap/recipe/tool_combo) 过滤
③ 按 applicable_context 匹配（route / task_type / 技术栈）
④ 排序（observed_count desc）
⑤ 注入到主 Agent 上下文
```

- **write 路径**：

```
① 识别新经验（trap / pattern / tool_combo / anti_pattern）
② 生成 KB 条目 (按 schema)
③ 默认写入 session-kb（临时）
④ 等晋升仪式决定是否升到 Project / Global
```

### 5.5 人机交互 + 方法论驱动

#### BF-L3-09 · 请示用户流
- **触发**：决策需用户输入 / Stage Gate / 硬红线 / 重度 FAIL / 极重度 FAIL
- **路径**：生成交互卡片（text / radio / multi-select / free-text）→ UI 推送 → 用户操作 → 回收答案
- **分支**：用户长时间不响应 → 软暂停 + 通知；紧急中止 → ABORTED

#### BF-L3-10 · 方法论驱动决策流（PMP+TOGAF 骨架查询）
- **触发**：每次关键决策前
- **输出**：本阶段允许的动作 + 必产出物清单 + Skill 推荐
- **路径**：查 PMP 5 × TOGAF 9 矩阵 → 返回当前交叉格 guidance → 约束决策不出格

#### BF-L3-11 · 5 纪律自拷问流
- **触发**：每次关键决策前（与 L3-10 并行）
- **路径**：依次问：
  - 规划？（有清晰 plan + DoD）
  - 质量？（有 TDD / 审查 / 证据链）
  - 拆解？（WBS 粒度够细）
  - 检验？（verifier 会跑）
  - 交付？（产出可消费）
  任一 N → 先补齐再决策

### 5.6 Loop 与阶段切换

#### BF-L3-12 · loop 触发机制流
- **触发条件（并集）**：
  - 🟢 事件驱动：事件总线新事件（PostToolUse hook / subagent 回传 / 用户输入）
  - 🟡 主动驱动：上一决策完成 + 等待其他事件超时 → 自主 tick
  - 🔵 周期驱动：30s cron tick（Supervisor 心跳）
  - 🔴 Hook 驱动：SessionStart / state transition hook
- **调度规则**：事件驱动 > 主动驱动 > 周期驱动；事件驱动高优先级可打断周期驱动

#### BF-L3-13 · 阶段切换触发流（Stage Gate 机制）
- **触发**：
  - 进入某 state 的 DoD 全 PASS → 自动尝试切换
  - 用户 Stage Gate Go 按钮 → 手动切换
  - Supervisor 回退指令 → 强制切换
- **路径**：

```
① 查 allowed_next（来自 §3.5 硬约束）
② 如目标 state 不在 allowed_next → 拒绝 + 告警
③ 执行退出当前 state 的 exit_DoD
④ 执行进入目标 state 的 entry_DoD
⑤ 更新 current_state + state_history + 事件总线
⑥ 触发阶段切换后的注入策略（BF-L3-05 读新阶段 KB）
```

#### BF-L3-14 · 决策（skill / 工具 / 任务链）选择流
- **分派树**：

```
is_atomic_op(需要) →
  YES: 选工具（Read/Write/Bash/Grep）
  NO: is_needs_methodology → 
    YES: 选 skill (superpowers/prp/gstack/ecc)
    NO: is_needs_independent_check →
      YES: 委托子 Agent
      NO: is_chained_tasks →
        YES: 生成任务链 + 逐步执行
        NO: 内建逻辑处理
```

#### BF-L3-15 · 任务链执行流
- **触发**：识别到多步串联任务
- **路径**：主 Agent 维护 mini-state machine → 按链推进 → 每步完成登记 → 全完成整合
- **分支**：某步失败 → 回退 / 重试 / 升级告警

---

## 6. 横切流（贯穿所有 L1 阶段）

| 编号 | 流名 | 触发 | 输出 |
|---|---|---|---|
| **BF-X-01** | 主 Agent 决策心跳（见 BF-L3-01） | 事件 / hook / 30s | 决策执行 |
| **BF-X-02** | 监督观察流 | 30s + PostToolUse + state 转换 | 8 维度 INFO/SUGG/WARN/BLOCK 事件 |
| **BF-X-03** | 事件总线落盘流 | 任何 decision / event | `events/YYYY-MM-DD.jsonl` |
| **BF-X-04** | 审计追溯流 | 用户查询"为什么" | 完整决策链 |
| **BF-X-05** | KB 注入策略执行流（PM-06） | 阶段切换 / 决策前 | 注入条目到 context |
| **BF-X-06** | 产出物模板驱动流（PM-07） | 产出物生成 | 按模板填充的 md/yaml/json |
| **BF-X-07** | 能力抽象层调度流（PM-09） | Skill 调度决策 | 可用 skill 列表（按优先级） |
| **BF-X-08** | 持久化与跨 session 恢复流（PM-10） | 每事件 / 重启 | 落盘 / 回放恢复 |
| **BF-X-10** | **项目生命周期横切流（PM-14 · 新增）** | S1 启动 / 激活 / 归档 / 删除 | harnessFlowProjectId 创建 · 激活 · 归档 · 删除 全链路 |

### BF-X-10 · 项目生命周期横切流（PM-14）

**触发场景**：
- **创建**：用户首次输入项目目标，S1 澄清通过，L1-02 L2-02 启动阶段产出器生成 project_id
- **激活**：跨 session 启动 Claude Code，L1-09 bootstrap 读 projects/_index.yaml 激活最近 project
- **切换**（V2+）：用户在 L1-10 UI 显式切换"当前 project"，主 loop 上下文随之切换
- **归档**：S7 最终 Gate 通过，project 主状态转 CLOSED；或极端失败（FAILED_TERMINAL）走失败闭环
- **删除**：用户在 UI 显式"删除项目"+ 二次确认

**关键路径**：
```
[用户首次输入项目目标]
     ↓
L1-02 L2-02 澄清对话 (≤ 3 轮)
     ↓ 澄清通过
生成 harnessFlowProjectId (slug + uuid-short)
     ↓
写 projects/<pid>/manifest.yaml
     ↓
发 project_created 事件 (IC-09 to L1-09)
     ↓
L1-09 创建 project 根目录 (events.jsonl / audit.jsonl / checkpoints/ / kb/)
     ↓
project 主状态 = INITIALIZED
     ↓
... 后续所有 tick / IC / 事件 / 产出物都带 project_id 归属 ...
     ↓
S7 Gate 通过 → project 主状态 = CLOSING → CLOSED
     ↓
L1-09 冻结 project 根目录 (只读 · 归档)
```

**横切覆盖**：本流贯穿 L1-02（所有权方）+ L1-09（持久化落实方）+ L1-01（tick 上下文绑定方）+ L1-10（UI 切换方）。

**详见** `docs/2-prd/L0/projectModel.md` §4（生命周期）+ §5（主状态机）+ §9（与 10 L1 关系矩阵）。

**关键约束**：
- BF-X-02 监督 8 维度：目标保真度 / 计划对齐 / 真完成质量 / 红线安全 / 进度节奏 / 成本预算 / 重试 Loop / 用户协作
- BF-X-03 事件 schema：`{ts, type, actor, state, content, links, hash, project_id}` · **PM-14 必含 project_id 根字段**
- BF-X-05 注入策略：S1→trap+pattern；S2→recipe+tool_combo；S3→anti_pattern；S4→pattern；S5→trap；S7→反向收集
- **BF-X-10（本流）关键约束**：所有数据归属 project_id · 事件总线按 project 物理分片 · 跨 project 引用必拷贝不软链

---

## 7. 异常与降级流

### BF-E-01 · 会话退出流
- **触发**：Ctrl+C / 窗口关闭 / kill 进程
- **路径**：信号捕获 → flush 事件总线 → 写 checkpoint → 记录"退出时 state=X" → 退出
- **保证**：任何退出都有 checkpoint

### BF-E-02 · 跨 session 恢复流
- **触发**：Claude Code 重启 + 存在未 CLOSED 项目
- **路径**：

```
启动 harnessFlow skill →
查 task-boards/ 找未 CLOSED 项目 →
读该项目 checkpoint →
重放事件总线（从 checkpoint 后）→
恢复 task-board 到退出时 state →
显示"已恢复 project X, 当前 state = Y, 继续？"→
用户确认 → 主 Agent 接管继续决策心跳
```

- **降级**：checkpoint 损坏 → 从事件总线完整重放；都损坏 → 从上一有效 state 降级 + 告警

### BF-E-03 · 网络异常恢复流
- **路径**：

```
① 指数 backoff 重试（1s → 2s → 4s → 8s, 最多 5 次）
② 若 MCP 服务器断连 → 尝试重连
③ 仍失败 → 降级到本地替代（如 Playwright MCP 挂 → 用 playwright-python 直 launch）
④ 无本地替代 → 告警 + 任务置 PAUSED_ESCALATED + 请示用户
```

### BF-E-04 · Claude API 限流处理流
- **路径**：

```
429 收到 → 读 Retry-After header → sleep → 重试
token 预算 < 20% → 主 Agent 进入"节能模式":
  • 压缩历史上下文
  • 丢弃非关键事件
  • 只保留 task-board + 最近 10 条决策
  • 广播"已进节能模式, 请求增加预算"
```

- **分支**：节能模式仍不够 → 硬暂停 + 上报用户

### BF-E-05 · Skill 失败降级流
- **路径**：

```
① 能力抽象层查 fallback 列表
② 尝试第 2 优先 skill
③ 仍失败 → 尝试第 3
④ 全失败 → 降级到内建逻辑 + 告警
⑤ 内建也失败 → 硬暂停 + 上报
```

### BF-E-06 · 上下文爆炸处理流
- **触发**：context 占用 > 80%
- **路径**：

```
① 识别可压缩项（旧事件 / 已完成 WP 详情 / 重复 KB 条目）
② 压缩：保留摘要、删除原文
③ 重要信息落盘到 task-board（以便后续按需取）
④ 广播"已压缩, 如需详情从 task-board 查"
⑤ 仍 > 80% → 主动 compact session
```

### BF-E-07 · 任务走偏 soft-drift 检测流
- **触发**：
  - 实际 state 序列与路线骨架偏差 > 30%
  - goal_anchor 关键句在最近 10 条决策命中率 < 60%
  - 决策理由重复"暂时跳过" ≥ 5 次
- **输出**：WARN 级告警 + replan 建议
- **区别于硬红线 DRIFT_CRITICAL**：soft-drift 是趋势告警；DRIFT_CRITICAL 是 sha256 变化硬拦截

### BF-E-08 · WP 失败回退流
- **触发**：某 WP 连续 ≥ 3 次 WP-DoD 自检失败
- **路径**：Supervisor 标记 STUCK → 生成回退建议（拆 WP / 改 WBS / 改 AC）→ 主 Agent 自决或请示

### BF-E-09 · 子 Agent 失败流
- **路径**：重试 1 次（新 session）→ 仍失败则降级（verifier 简化版 / retro 最简 / 跳过 review / 归档 TODO）→ 降级失败则硬暂停

### BF-E-10 · 死循环保护流
- **触发**：同级 FAIL 连续 ≥ 3 次
- **路径**：自动升级上一级（轻度→中度→重度→极重度→硬拦截）

### BF-E-11 · 软红线自治修复流（8 类）

| 软红线 | 自治动作 |
|---|---|
| DoD 证据链缺一段 | Supervisor 自动 trigger verifier 重跑 / 补证据 |
| 进度偏差 < 30% | 自动 replan WP 拓扑 |
| Skill 调用失败 | 能力抽象层 fallback（BF-E-05） |
| Context 占用 > 80% | 自动压缩（BF-E-06） |
| 轻度 TDDExe FAIL | 回 S4 自修（BF-S5-04） |
| WP 超时 < 2× 估算 | 自动延长 + 记入风险登记 |
| 单 KB 条目读不到 | 降级到无 KB 决策 + 告警 |
| 网络瞬时失败 | 指数 backoff 重试（BF-E-03） |

**原则**：软红线必须不打扰用户；只在事件总线和 UI 告警角记录。

### BF-E-12 · 硬红线上报流（5 类）

| 硬红线 | 上报动作 |
|---|---|
| **DRIFT_CRITICAL**（goal_anchor sha256 变 / CLAUDE.md 被篡改） | 硬暂停 + 用户文字重新锚定 |
| **IRREVERSIBLE_HALT**（rm -rf / force push / DB drop / prod deploy） | 硬暂停 + 用户显式文本授权 |
| 预算超 200% | 硬暂停 + 用户决策是否继续 |
| 死循环 ≥ 3 次升级（BF-E-10） | 硬暂停 + 用户介入 |
| 极重度 FAIL（回 S1） | 硬暂停 + 用户重锚 goal |

**原则**：硬红线触发 → 立刻暂停主 loop → UI 强通知 → 等用户文本授权才能解除。

---

## 8. 业务模式详解（13 个横切约束）

### PM-01 · methodology-paced 节奏
**定义**：协同度按阶段变速。
**约束**：S1+S2+S3 强协同；S4+S5+S6 自走；S7 强制 Gate。不得反向。

### PM-02 · 主-副 Agent 协作
**定义**：主 Agent 持续决策执行，Supervisor 旁路观察。
**约束**：Supervisor 不改数据、不调 skill、不执行动作；仅通过 4 级建议通道影响主 Agent。

### PM-03 · 子 Agent 独立 session 委托
**定义**：独立任务走独立 session。
**约束**：只读 context 副本 + 结构化回传；禁 session 间共享状态。

### PM-04 · WP 拓扑并行推进
**定义**：超大项目按 WBS 拆成 WP，按拓扑序推进。
**约束**：同时最多 1-2 个 WP 并行；WP 粒度 ≤ 5 天工时。

### PM-05 · Stage Contract 机器可校验
**定义**：每个 state 的 DoD 是可机器 eval 的谓词表达式。
**约束**：走白名单 AST eval，禁 arbitrary exec；原语来自 `verifier_primitives/`。

### PM-06 · KB 三层 + 阶段注入
**定义**：Global / Project / Session 三层知识库 + 按阶段注入不同 kind。
**约束**：Session 条目默认临时；晋升需 observed_count ≥ 2 或用户显式批准。

### PM-07 · 产出物模板驱动
**定义**：所有 PMP / TOGAF 产出物按标准模板填充。
**约束**：每产出物必须有模板 id + 消费者；无消费者不产出（防 paperwork theater）。

### PM-08 · 可审计全链追溯
**定义**：代码 → 决策 → 证据 → 理由 可反查。
**约束**：任何产出物必能追溯到某次主 Agent 决策；任何决策必有自然语言理由。

### PM-09 · 能力抽象层调度
**定义**：主 Agent 绑"能力点"不绑 skill 名。
**约束**：每个能力点 ≥ 2 个备选 skill；下层 skill 变更不破坏上层语义。

### PM-10 · 事件总线单一事实源
**定义**：所有状态变更经事件总线落盘。
**约束**：禁绕过事件总线直接改 task-board；重启可重放事件总线恢复。

### PM-11 · 5 纪律贯穿拷问
**定义**：每关键决策前问 规划 / 质量 / 拆解 / 检验 / 交付。
**约束**：任一 N 必须先补齐才能决策；全流程记录 5 纪律回答。

### PM-12 · 红线分级自治（软/硬）
**定义**：8 类软红线自治 / 5 类硬红线硬拦截。
**约束**：软红线不打扰用户；硬红线必须文本授权。

### PM-13 · 合规可裁剪
**定义**：方法论深度 3 档（完整 / 精简 / 自定义）。
**约束**：任何裁剪不得违背 §3.5 L1 硬约束。

---

## 附录 A · 业务流 ↔ Goal 追溯矩阵

| 业务流组 | 对应 Goal 条目 |
|---|---|
| L1 S1 启动 | Goal §3.1 输入 · §2.2 PMP 启动过程组 · §3.3 规划强协同 |
| L1 S2 规划+架构 | Goal §2.2 PMP 规划 × TOGAF A-D · §2.3 WP 拓扑 |
| L1 S3 TDD 规划 | Goal §2.2 五大纪律"质量+检验" · §3.2.B/C 产出物 |
| L1 S4 执行 | Goal §2.3 WP 拓扑 · §3.3 执行自走 · §3.2.A 代码产出 |
| L1 S5 TDDExe | Goal §2.2 五大纪律"检验" · §4.1 "决策可追溯率 100%" |
| L1 S6 监控 | Goal §7.3 supervisor 分级权威 · §3.3 低频通知 |
| L1 S7 收尾 | Goal §2.2 PMP 收尾 × TOGAF H · §3.2.B/C/D 产出物包 |
| L3 文档处理 / 代码分析 / 图片分析 | Goal §3.1 输入（含 Brownfield） |
| L3 KB 读写 | Goal §3.2.D 知识沉淀 |
| L3 loop 触发 / 决策 | Goal §2 主产品定位（主 Agent loop） |
| 横切流 | Goal §4 过程 · §7 风险认知 |
| 异常流 7.10 红线分级 | Goal §2.2 PMP 质量 + 五大纪律 · §7.3 监督权威 |
| 业务模式 13 条 | Goal §2 产品定位 + §3 输入输出 + §5 成功判定 |

---

## 附录 B · 术语速查

| 术语 | 含义 |
|---|---|
| **L1/L2/L3** | 业务流层级 |
| **Quality Loop** | S4 执行 ↔ S5 TDDExe 循环 + S6 监督 |
| **4 级回退** | 轻度（回 S4）/ 中度（回 S3）/ 重度（回 S2）/ 极重度（回 S1） |
| **4 件套** | 需求 / 目标 / 验收 / 质量（S2 Stage Gate 硬性产出） |
| **TDD 蓝图** | Master Test Plan + DoD + 测试用例 + 质量 gate + 验收 checklist（S3 产出） |
| **三段证据链** | existence_evidence / behavior_evidence / quality_evidence |
| **三态 verdict** | PASS / FAIL / INSUFFICIENT_EVIDENCE |
| **软红线** | Supervisor 自治修复的 8 类事件 |
| **硬红线** | 必须人工介入的 5 类事件 |
| **死循环保护** | 同级 FAIL ≥ 3 次 → 自动升级 |
| **事件总线** | 单一事实源 jsonl 总线 |
| **能力抽象层** | 主 Agent ↔ skill 生态之间的解耦层 |
| **Stage Gate** | 阶段门，强制用户 Go/No-Go |
| **WP（Work Package）** | WBS 最小可执行单元 |
| **ADR** | Architecture Decision Record |

---

*— businessFlow.md v1.0 最终稿完 —*
