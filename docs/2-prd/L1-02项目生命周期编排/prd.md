---
doc_id: prd-l1-02-project-lifecycle-v0.1
doc_type: l1-prd
parent_doc:
  - HarnessFlowGoal.md
  - docs/2-prd/businessFlow.md
  - docs/2-prd/scope.md#5.2
version: v1.0
status: ready_for_review
author: mixed
created_at: 2026-04-20
updated_at: 2026-04-20
traceability:
  goal_anchor: HarnessFlowGoal.md#2.2 双层骨架 · §3.3 methodology-paced
  business_flow: [BF-S1-全部, BF-S2-全部, BF-S3-全部, BF-S7-全部, BF-L3-10, BF-X-06]
  scope: [L1-02]
consumer:
  - docs/2-prd/flowOutInput.md#4.3
  - docs/2-prd/L1集成/prd.md
  - TDD 阶段
---

# L1-02 · 项目生命周期编排能力 · PRD

> **版本**：v1.0（全 7 个 L2 详细定义完备，待 review）
> **定位**：L1-02 的独立 PRD · 7 阶段 × 4 Stage Gate × PMP+TOGAF 产出物编排 · 整个 HarnessFlow 最复杂、产出物最多的 L1
> **严格遵循**：本 PRD **不得与** `docs/2-prd/scope.md §5.2` 冲突。如冲突以 scope 为准。

---

## 0. 撰写进度

- [x] §1 L1-02 范围锚定（引用 scope）
- [x] §2 L2 清单（7 个）
- [x] §3 L2 整体架构 · 图 A 主干控制流
- [x] §4 L2 整体架构 · 图 B 横切响应面
- [x] §5 L2 间业务流程（9 条）
- [x] §6 IC-L2 契约清单（10 条 · 字段粗案）
- [x] §7 L2 定义模板（9 小节标准）
- [x] §8 L2-01 · Stage Gate 控制器 ✅ R3 完成
- [x] §9 L2-02 · 启动阶段产出器（S1） ✅ R4 完成
- [x] §10 L2-03 · 4 件套生产器（S2 核心） ✅ R5 完成
- [x] §11 L2-04 · PMP 9 计划生产器 + §12 L2-05 · TOGAF ADM 架构生产器 ✅ R6 完成
- [x] §13 L2-06 · 收尾阶段执行器（S7） ✅ R7 完成
- [x] §14 L2-07 · 产出物模板引擎 ✅ R7 完成
- [x] §15 对外 scope §8 IC 契约映射 ✅ R8 完成
- [x] §16 本 L1 retro 位点 ✅ R8 完成
- [x] 附录 A 术语 · 附录 B BF 映射 · 附录 C IC-L2 字段示例

---

## 1. L1-02 范围锚定（引自 scope §5.2，不重复写）

| scope §5.2 子节 | 内容摘要 | 锚点 |
|---|---|---|
| §5.2.1 职责 | 推进 7 阶段 × Stage Gate × PMP+TOGAF 矩阵 × 产出物模板 | scope#5.2.1 |
| §5.2.2 输入/输出 | 输入 L1-01 state 请求 + 用户 Gate 决定；输出 4 件套 + 9 计划 + TOGAF A-D + 交付包 | scope#5.2.2 |
| §5.2.3 边界 | 只做阶段编排 + 产出物生产，不做 WBS / TDD 蓝图 / 代码 / 验证 | scope#5.2.3 |
| §5.2.4 约束 | Goal §3.5 L1 硬约束 1-8 全适用；PM-01/07/13 | scope#5.2.4 |
| §5.2.5 🚫 禁止行为 | 7 条（跳 Gate / 4 件套不齐进 S3 / S5 未 PASS 进 S7...） | scope#5.2.5 |
| §5.2.6 ✅ 必须义务 | 6 条（按矩阵编织产出 / Stage Gate 阻塞 / 产出物齐全 / 裁剪 3 档...） | scope#5.2.6 |
| §5.2.7 与其他 L1 交互 | 接 L1-01/03/04/05/06/07/10 | scope#5.2.7 |
| 对外 IC 契约 | IC-01/IC-16/IC-19 等（scope §8.2） | scope#8.2 |

**本 PRD 的职责**：把 L1-02 内部拆成 **7 个 L2** + 画清楚它们之间的 **架构 / 业务流 / 契约**。

---

## 2. L2 清单（7 个）

| L2 ID | 名称 | 一句话职责 | 聚合自 BF | 核心问题 |
|---|---|---|---|---|
| **L2-01** | Stage Gate 控制器 | 4 次 Gate（S1/S2/S3/S7 末）+ 推卡片 + 阻塞放行 + 用户 Go/No-Go 路由 + 阶段切换触发 | BF-S1-04 / BF-S2-09 / BF-S3-05 / BF-S7-05 | 怎么控 Gate |
| **L2-02** | 启动阶段产出器（S1） | 章程生成 + 干系人登记 + goal_anchor sha256 锁定 | BF-S1-01/02/03 | S1 产什么 |
| **L2-03** | 4 件套生产器（S2 核心） | 需求 / 目标 / 验收标准 / 质量标准 四份文档 · 串行生成 | BF-S2-01/02/03/04 | S2 4 件套怎么产 |
| **L2-04** | PMP 9 计划生产器（S2） | 范围/进度/成本/质量/资源/沟通/风险/采购/干系人整合 9 份计划 · 可并行 | BF-S2-05 | 9 计划怎么产 |
| **L2-05** | TOGAF ADM 架构生产器（S2） | A 愿景 / B 业务 / C 数据+应用 / D 技术 + ADR · 顺序生成（A→B→C→D 依赖链） | BF-S2-06 / BF-S2-08 | TOGAF 怎么做 |
| **L2-06** | 收尾阶段执行器（S7） | retro 生成 + archive 归档 + KB 晋升 + 交付包打包 + 最终验收 | BF-S7-01/02/03/04 | S7 怎么收 |
| **L2-07** | 产出物模板引擎（横切） | 统一模板驱动 + 裁剪（完整/精简/自定义 · PM-13）+ 模板参数化 + 模板版本管理 | BF-X-06 | 产出物怎么按模板 |

---

## 3. L2 整体架构 · 图 A 主干控制流

```
              L1-02 项目生命周期编排（7 个 L2）
              ═════════════════════════════════

 L1-01 state 转换请求 / Stage Gate 触发信号
          │
          ▼
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃  L2-01 Stage Gate 控制器               ┃ ← IC-L2-04 用户 Go/No-Go (来自 L1-10)
  ┃   · 4 次 Gate 时机判定                  ┃
  ┃   · Gate 卡片推送 (via IC-16)           ┃
  ┃   · 阻塞 L1-01 直到用户决定              ┃
  ┃   · 阶段转换发起 (via IC-01)            ┃
  ┃   · 裁剪配置查询 (via IC-L2-09)         ┃
  ┗━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┛
                   │ IC-L2-01 (按当前 state 分派)
                   ▼
    ┌──────────┬──────────┬──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼          ▼          ▼
 ┏━━━━━━━━┓ ┏━━━━━━━━┓ ┏━━━━━━━━┓ ┏━━━━━━━━┓ ┏━━━━━━━━┓
 ┃ L2-02  ┃ ┃ L2-03  ┃ ┃ L2-04  ┃ ┃ L2-05  ┃ ┃ L2-06  ┃
 ┃ 启动   ┃ ┃ 4件套   ┃ ┃ 9计划   ┃ ┃ TOGAF  ┃ ┃ 收尾   ┃
 ┃ (S1)   ┃ ┃ (S2)   ┃ ┃ (S2)   ┃ ┃ (S2)   ┃ ┃ (S7)   ┃
 ┃        ┃ ┃        ┃ ┃        ┃ ┃        ┃ ┃        ┃
 ┃ 章程   ┃ ┃ 需求   ┃ ┃ 范围   ┃ ┃ A 愿景 ┃ ┃ retro ┃
 ┃ 干系人 ┃ ┃ 目标   ┃ ┃ 进度   ┃ ┃ B 业务 ┃ ┃ archive┃
 ┃ goal  ┃ ┃ 验收   ┃ ┃ 成本   ┃ ┃ C 数据 ┃ ┃ KB 晋升┃
 ┃ anchor ┃ ┃ 质量   ┃ ┃ ... 6 ┃ ┃ D 技术 ┃ ┃ 交付包 ┃
 ┃        ┃ ┃        ┃ ┃        ┃ ┃ ADR    ┃ ┃        ┃
 ┗━━━━━┳━━┛ ┗━━━━━┳━━┛ ┗━━━━━┳━━┛ ┗━━━━━┳━━┛ ┗━━━━━┳━━┛
        │         │         │         │         │
        │  IC-L2-02 模板请求 (横切)             │
        ▼         ▼         ▼         ▼         ▼
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃  L2-07 产出物模板引擎（横切）            ┃
  ┃   · 模板库管理                          ┃
  ┃   · 裁剪规则应用 (3 档)                  ┃
  ┃   · 参数化填充                          ┃
  ┃   · 版本追踪                            ┃
  ┗━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┛
                   │ 产出物填充
                   ▼
             md / yaml / ADR 落盘
                   │
                   ▼
      docs/charters / docs/stakeholders /
      docs/planning/*-plan.md /
      docs/architecture/{A,B,C,D}.md + ADR/*.md /
      delivery/*（S7 交付包）
```

**关键规则**：
- **L2-01 是入口**（所有阶段编排从这里走）
- **L2-02/03/04/05/06 各司一阶段产出**（按 state 分派）
- **L2-07 是横切**（所有产出物都走统一模板引擎）
- **L2-01 是唯一对 L1-10 推 Stage Gate 的入口**（IC-16 由它承担）

---

## 4. L2 整体架构 · 图 B 横切响应面

```
 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 1 · 用户变更请求（TOGAF H 变更管理）                        ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ (L1-10 UI) → user_change_request 事件                            ║
 ║   → L1-01 → L2-01 Stage Gate 控制器                              ║
 ║   → L2-01 分析影响面 (涉及哪些 S2 产出物?)                        ║
 ║   → 路由到对应 L2-03/04/05 重做产出                                ║
 ║   → 重新进 Stage Gate 等用户 Re-Go                                ║
 ║                                                                  ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 2 · 裁剪控制（PM-13 合规可裁剪 · 3 档）                     ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ 项目初始化时用户选择：完整 / 精简 / 自定义                         ║
 ║   → L2-01 接收配置                                                 ║
 ║   → IC-L2-09 query_trim → L2-07                                   ║
 ║   → L2-07 返回启用的模板子集                                       ║
 ║   → L2-03/04/05 按子集生成产出物                                    ║
 ║                                                                  ║
 ║ 完整档: 全部 PMP 9 计划 + TOGAF A-D + ADR 详细                      ║
 ║ 精简档: PMP 核心 5 计划 + TOGAF A+D + ADR 精选                      ║
 ║ 自定义: 用户逐项勾选                                                ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 3 · 4 件套消费链（跨 L1）                                   ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-03 生成 4 件套 (需求/目标/验收/质量)                           ║
 ║   → 消费者 1: L1-03 WBS 拆解（IC-19 request_wbs_decomposition）  ║
 ║   → 消费者 2: L1-04 TDD 蓝图（S3 阶段，Master Test Plan 依据）    ║
 ║   → 消费者 3: 本 L1 L2-04/05（PMP 9 计划 + TOGAF 生成的依据）     ║
 ║                                                                  ║
 ║ L2-03 完成后广播 `4_pieces_ready` 事件 → 消费者订阅              ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 4 · 紧急中止（L1-07 硬红线路径）                            ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L1-07 supervisor 触发硬红线 (IC-15 request_hard_halt)            ║
 ║   → L1-01 L2-06 接收 → 停 tick                                    ║
 ║   → 本 L1 的 L2-01 收到 state=PAUSED 转换信号                      ║
 ║   → L2-01 停止进入下一阶段（阻塞 Gate）                            ║
 ║   → 等用户授权后 → L2-01 重新判定 state 应走向何处                 ║
 ║                                                                  ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 5 · PMP × TOGAF 交织矩阵（L2-04 + L2-05 协同）             ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ PMP 9 计划（质量计划）需要 TOGAF D 技术架构作输入                  ║
 ║   → L2-04 生成质量计划时需等 L2-05 的 D 产出                      ║
 ║   → L2-05 D 生成时需 L2-04 的范围计划作上下文                      ║
 ║   → L2-01 协调两者顺序：                                           ║
 ║     1. L2-04 先出范围+进度+成本计划                                ║
 ║     2. L2-05 A→B→C→D 顺序出架构                                   ║
 ║     3. L2-04 基于 D 再出质量+风险计划                              ║
 ║     4. L2-04 出剩余计划（资源/沟通/采购/干系人整合）                ║
 ║                                                                  ║
 ╚══════════════════════════════════════════════════════════════════╝
```

---

## 5. L2 间业务流程（9 条）

### 流 A · 正常 7 阶段端到端推进（最长链路）

```
[用户输入项目目标] → L1-01 → L2-01
     ↓ state=INIT
L2-01 判定: INIT → CLARIFY
     ↓ IC-L2-01 to L2-02
L2-02 (S1 启动):
   1. 澄清对话 (调 L1-05 skill=brainstorming)
   2. 章程生成 (用 L2-07 模板)
   3. 干系人识别
   4. goal_anchor sha256 锁定
     ↓ S1 产出齐全
L2-01 → S1 Stage Gate
     ↓ IC-16 push_stage_gate_card → L1-10 UI
用户 Go
     ↓ IC-L2-04 user decision → L2-01
L2-01: state=CLARIFY → PLAN (via IC-01 to L1-01)
     ↓
L2-03 (S2 · 4 件套串行):
   需求 → 目标 → 验收 → 质量
     ↓
L2-04 (S2 · 9 计划 · 与 L2-05 协同):
   范围/进度/成本 → 质量/风险 → 资源/沟通/采购/干系人
     ↓
L2-05 (S2 · TOGAF A→B→C→D):
   A 愿景 → B 业务 → C 数据+应用 → D 技术 → ADR
     ↓
L2-01 → S2 Stage Gate (7 产出物齐: 4件套 + 9计划 + TOGAF A-D + ADR + WBS via L1-03)
     ↓ 用户 Go
state=PLAN → TDD_PLAN (L1-04 接手 S3)
     ↓ (S3 由 L1-04 承担, 本 L1 暂歇)
L2-01 → S3 Stage Gate (L1-04 S3 蓝图齐)
     ↓ 用户 Go
state=TDD_PLAN → IMPL (L1-04 继续 S4)
     ↓
... (L1-04 Quality Loop 自跑 S4-S5-S6)
     ↓ (S5 PASS)
state → COMMIT → RETRO_CLOSE
     ↓
L2-06 (S7 收尾):
   1. 交付物汇总打包
   2. retro 生成 (委托 L1-05 子 Agent retro-generator)
   3. archive 归档 (委托 failure-archive-writer)
   4. KB 晋升 (调 L1-06 IC-08 kb_promote)
     ↓
L2-01 → S7 Stage Gate (最终验收)
     ↓ 用户 Go
state → CLOSED 终态
```

### 流 B · 4 件套串行生成（S2 内部）

```
L2-03 启动 (IC-L2-01 from L2-01)
     ↓
Step 1: 生成 requirements.md
  · 调 L1-06 kb_read (recipe kind, 历史需求模式)
  · 调 L1-05 invoke_skill(capability='requirements-analysis', skill='prp-prd')
  · L2-07 填模板 → docs/planning/requirements.md
  · 用户 review (inline · 非 Stage Gate)
     ↓
Step 2: 生成 goals.md
  · 依赖 requirements.md
  · 同上套路
     ↓
Step 3: 生成 acceptance-criteria.md (Given-When-Then)
  · 依赖 goals.md
     ↓
Step 4: 生成 quality-standards.md
  · 依赖 AC + 非功能需求
     ↓
4 件套齐全 → 广播 `4_pieces_ready` 事件
     ↓
L2-04/05 订阅事件开始生产 9 计划 + TOGAF
```

### 流 C · PMP 9 计划并行生成

```
L2-04 启动 (4 件套齐后)
     ↓
分 3 组并行:
  Group 1 (基础 3 计划): 范围 / 进度 / 成本 - 可并行
  Group 2 (依赖 TOGAF D): 质量 / 风险 - 等 L2-05 D 完成
  Group 3 (协同): 资源 / 沟通 / 采购 / 干系人整合 - 可并行
     ↓
每计划:
  · 调 L1-05 invoke_skill(capability='plan-writing', skill='writing-plans')
  · L2-07 填模板 → docs/planning/{X}-plan.md
  · L2-01 监控进度
     ↓
9 计划齐 → 广播 `9_plans_ready`
```

### 流 D · TOGAF A-D 顺序生成

```
L2-05 启动 (4 件套 + 范围/进度计划齐后)
     ↓
A 愿景 (Architecture Vision):
  · 基于 goals.md + requirements.md
  · 产出 docs/architecture/A-vision.md
  · 可能产 ADR-A1 ADR-A2
     ↓
B 业务架构 (Business Architecture):
  · 基于 A 愿景 + 4 件套
  · 产出 docs/architecture/B-business.md
  · ADR-B*
     ↓
C 信息系统架构 (数据 + 应用):
  · 基于 B
  · 可能委托 architecture-reviewer 子 Agent (IC-05 to L1-05)
  · 产出 C-data.md + C-application.md
  · ADR-C*
     ↓
D 技术架构:
  · 基于 C + 技术栈约束
  · 产出 D-technology.md
  · ADR-D* (技术选型最多 ADR)
     ↓
TOGAF 产出齐 + ADR ≥ 10 条 → 广播 `togaf_ready`
```

### 流 E · Stage Gate 用户 Go/No-Go

```
[阶段产出齐全] → L2-01 判定 Gate 时机
     ↓
L2-01 打包 artifacts_bundle (本阶段所有产出物路径 + 预览)
     ↓
IC-16 push_stage_gate_card → L1-10 UI
     ↓
L2-01 阻塞 L1-01 (不再接受 state 转换请求)
     ↓
用户 review artifacts → 决定
     ├── Go: IC-L2-04 user_decision(approve) → L2-01
     │        ↓
     │   L2-01 解除阻塞 → IC-01 request_state_transition(to=下一阶段)
     │        ↓
     │   进入下阶段的 L2 工作
     │
     ├── No-Go + 修改意见:
     │   L2-01 记录 change_requests
     │   按意见路由到对应 L2-02/03/04/05 重做部分产出
     │   重新推 Gate 卡片
     │
     └── Request change (重大调整):
         走响应面 1 · 用户变更请求流 (TOGAF H)
```

### 流 F · 用户变更请求（TOGAF H · 运行时任意阶段）

```
(项目进行中, S3 或 S4 阶段)
     ↓
用户从 L1-10 UI 发变更请求: "我想改 WP-05 的验收标准"
     ↓
L1-01 → L2-01 接收 change_request
     ↓
L2-01 分析影响面:
  · 涉及 4 件套? 哪份?
  · 涉及 9 计划? 哪份?
  · 涉及 TOGAF? 哪段?
  · 涉及 WBS? (下游 L1-03 需要改)
  · 涉及 TDD 蓝图? (下游 L1-04 需要改)
     ↓
L2-01 生成影响评估报告 (ADR 风格)
     ↓
推给用户确认影响 → 用户批准
     ↓
L2-01 路由到对应 L2 重做 (L2-03/04/05 按需)
     ↓
L2-01 广播 `artifact_changed` 事件 → L1-03/04 也消费 → 它们重做 WBS / TDD 蓝图
     ↓
所有受影响产出物齐 → 新一轮 Stage Gate
```

### 流 G · 收尾阶段（S7 · retro/archive/KB 晋升/交付）

```
(L1-04 Quality Loop S5 PASS 且全部 WP 完成)
     ↓
state → RETRO_CLOSE
     ↓ IC-L2-01 to L2-06
L2-06 (S7 收尾):

Step 1: 交付物汇总
  · 遍历所有产出物: 代码 commit / PMP 9 计划 / TOGAF A-D + ADR / 4 件套 / TDD 蓝图 / verifier_reports
  · 打包 delivery/<project_id>/
  · 生成 delivery-manifest.md
     ↓
Step 2: retro 生成
  · 委托 L1-05 IC-05 delegate_subagent(subagent='retro-generator')
  · retro-generator 读事件总线 + 决策链 → 按 11 项模板产出 retros/<project_id>.md
     ↓
Step 3: archive 归档
  · 委托 L1-05 IC-05 delegate_subagent(subagent='failure-archive-writer')
  · archive-writer 写 failure-archive.jsonl 一条 (无论成功失败都归档)
     ↓
Step 4: KB 晋升
  · 读 session KB 候选条目
  · 调 L1-06 IC-08 kb_promote (按用户批准或 observed_count ≥ 3)
     ↓
Step 5: 最终 Stage Gate
  · L2-01 推 S7 Gate 卡片 (含交付包路径 + retro + 验收清单)
  · 用户最终 Go → state → CLOSED
  · 用户 No-Go → 回 state=RETRO_CLOSE 修交付包
```

### 流 H · 裁剪控制（完整/精简/自定义）

```
[项目初始化] 用户选择裁剪档 (via L1-10 UI)
     ↓
L1-01 → L2-01 接收
     ↓
L2-01 IC-L2-09 query_trim → L2-07
     ↓
L2-07 根据档次返回启用的模板子集:

完整档:
  · PMP 9 计划全部
  · TOGAF A + B + C + D 全部
  · ADR 详细模板 (每决策 full 格式)
  · retro 11 项全部

精简档:
  · PMP 5 计划 (范围/进度/质量/风险/干系人)
  · TOGAF A + D (跳 B + C 简化)
  · ADR 简化模板 (title + decision + rationale)
  · retro 6 项核心

自定义:
  · 用户逐项勾选
     ↓
L2-01 按子集配置 L2-03/04/05/06 的工作范围
     ↓
后续产出按裁剪执行
```

### 流 I · Gate 不通过 → 阶段回退

```
(S2 Stage Gate) 用户 No-Go
     ↓
L2-01 记录 change_requests (用户的修改意见)
     ↓
L2-01 分析:
  · 意见涉及 4 件套? → 标 L2-03 重做
  · 涉及 9 计划? → 标 L2-04 重做 (某几份)
  · 涉及 TOGAF? → 标 L2-05 重做
  · 涉及 WBS? → 通知 L1-03 重拆
     ↓
IC-L2-01 to 对应 L2 (只重做受影响部分)
     ↓
L2 重做 → 产出更新
     ↓
重新推 S2 Gate 卡片给用户 (含 diff)
     ↓
用户 Re-review → Re-Go
```

---

## 6. IC-L2 契约清单（10 条 · 字段粗案）

| ID | 调用方 | 被调方 | 方法 | 意义 | 字段骨架 |
|---|---|---|---|---|---|
| **IC-L2-01** | L2-01 | L2-02/03/04/05/06 | `trigger_stage_production(stage, context)` | Stage Gate 控制器分派阶段生产任务 | `{stage: S1/S2/S7, context: ctx, trim_level: full/minimal/custom}` |
| **IC-L2-02** | L2-02/03/04/05/06 | L2-07 | `request_template(doc_type, trim_level)` | 请求模板引擎返回对应产出物模板 | `{doc_type, trim_level, variables: {}}` → `{template_body, required_fields}` |
| **IC-L2-03** | L2-01 | L1-10（via IC-16 外部） | `push_stage_gate_card(bundle)` | 推 Gate 卡片给用户 | `{gate_id, stage_from, stage_to, artifacts_bundle, required_decisions}` |
| **IC-L2-04** | L1-10 → L2-01 | L2-01 | `receive_user_decision(gate_id, decision, change_requests?)` | 接收用户 Go/No-Go/Request_change | `{gate_id, decision: approve/reject/request_change, change_requests?: [str]}` |
| **IC-L2-05** | L2-01 | L1-01（via IC-01 外部） | `request_state_transition(from, to, reason)` | 发起 state 转换 | 见 scope §8.2 IC-01 |
| **IC-L2-06** | 全 L2-* | L2-05（通过 L1-01 的 L2-05 审计记录器，即外部 IC-09） | `record_audit(entry)` | 产出物生成 / Gate 决定 / 阶段切换等审计 | 见 L1-01 §12.10.1 audit_entry |
| **IC-L2-07** | L2-03/04/05 | L1-06（via IC-06 外部） | `kb_read(kind, filter)` | 读历史 KB 作模板参考 | 见 scope §8.2 IC-06 |
| **IC-L2-08** | L2-06 | L1-05（via IC-05 外部） | `delegate_subagent(subagent, goal)` | 委托 retro-generator / failure-archive-writer | 见 scope §8.2 IC-05 |
| **IC-L2-09** | L2-01 | L2-07 | `query_trim(level)` | 查询裁剪档启用的模板子集 | `{level: full/minimal/custom}` → `{enabled_templates: [doc_type]}` |
| **IC-L2-10** | L2-03 | L1-03（via IC-19 外部） | `request_wbs_decomposition(4_pieces, architecture)` | 4 件套齐后触发 L1-03 拆 WBS | 见 scope §8.2 IC-19 |

---

## 7. L2 定义模板（每 L2 必含 9 小节）

每个 L2 详细定义（§8-§14）严格按以下模板（同 L1-01 §7）：

| # | 小节 | 内容 |
|---|---|---|
| 1 | 职责 + 锚定 | 一句话职责 + Goal/BF/scope §5.2 锚点 |
| 2 | 输入 / 输出 | 输入事件 + 方法调用 / 产出事件 + 方法调用 |
| 3 | 边界 | In-scope / Out-of-scope / 边界规则 |
| 4 | 约束 | 业务模式 + 硬约束 + 性能约束 |
| 5 | 🚫 禁止行为 | 明确清单（5-8 条） |
| 6 | ✅ 必须职责 | 明确清单（5-8 条） |
| 7 | 🔧 可选功能职责 | 3-5 条 |
| 8 | 与其他 L2 交互 | IC-L2-XX 契约表 |
| 9 | 🎯 交付验证大纲 | 正向 / 负向 / 集成 / 性能 |

L3 在每 L2 的 §X.10 展开（算法 / 数据结构 / 内部状态机 / 流程图 / 配置参数）。

---

## 8. L2-01 · Stage Gate 控制器 详细定义

### 8.1 职责 + 锚定

**一句话职责**：HarnessFlow 的"阶段门卫" —— 在 S1/S2/S3/S7 四个阶段末自动识别 Gate 时机、打包产出物 bundle 推给用户评审、阻塞 L1-01 state 转换直到用户给出 Go/No-Go/Request-change 决定、分派下一阶段生产任务到对应 L2，并在用户变更请求时承担影响面分析与重做路由。

**上游锚定**：
- Goal §2.2 双层骨架："PMP 阶段闸（Stage Gate）"
- Goal §3.3 methodology-paced："用户 Stage Gate 闸控制节奏"
- scope §5.2.5 禁止行为 1："禁止跳 Gate 直进下阶段"
- scope §5.2.6 必须义务 2："Stage Gate 阻塞等用户"
- businessFlow BF-S1-04 / BF-S2-09 / BF-S3-05 / BF-S7-05（4 次 Gate 业务流）
- businessFlow BF-L3-10（方法论驱动的阶段编排）

**下游服务**：
- L2-02/03/04/05/06（分派阶段生产 via IC-L2-01）
- L2-07（裁剪配置查询 via IC-L2-09）
- L1-01 L2-03（状态转换请求 via IC-L2-05 → IC-01）
- L1-10（Gate 卡片推送 via IC-L2-03 → IC-16）
- L1-03（4 件套齐后触发 WBS via IC-L2-10 → IC-19）

---

### 8.2 输入 / 输出

#### 输入（5 类事件 + 1 配置查询）

| 类别 | 输入事件 | 来源 | 说明 |
|---|---|---|---|
| **stage_progress** | 阶段产出物"齐全"信号（e.g. `4_pieces_ready`, `9_plans_ready`, `togaf_ready`, `tdd_blueprint_ready`, `s5_pass`, `delivery_bundled`） | L2-02/03/04/05/06、L1-04 | 判定 Gate 时机 |
| **user_decision** | 用户 Go/No-Go/Request-change（IC-L2-04） | L1-10 UI（经 IC-17） | Gate 决定路由的触发源 |
| **change_request**（进行中） | 用户运行时变更请求（TOGAF H） | L1-10 UI（经 IC-17） | 触发响应面 1 · 影响分析 |
| **trim_config** | 项目初始化裁剪档配置（完整 / 精简 / 自定义） | L1-10 UI（首次配置） | 下发至 L2-07 查询启用模板子集 |
| **pause/resume** | state=PAUSED / HALTED / 恢复（横切） | L1-01 L2-03 状态机 | 暂停/恢复 Gate 机器 |
| **config_query** | 裁剪档查询（返回启用模板集） | L2-01 → L2-07（IC-L2-09） | Gate 前必查（决定打包哪些产出物） |

#### 输出（5 类）

| 类别 | 输出 | 去向 | schema |
|---|---|---|---|
| **stage_production_trigger** | IC-L2-01 `trigger_stage_production(stage, context, trim_level)` | L2-02/03/04/05/06 | §6 IC-L2-01 字段骨架 |
| **gate_card_push** | IC-L2-03 `push_stage_gate_card(bundle)`（最终经 IC-16 到 L1-10） | L1-10 UI | §8.10.4 GateCard schema |
| **state_transition_request** | IC-L2-05 `request_state_transition(from, to, reason)`（最终经 IC-01 到 L1-01 L2-03） | L1-01 L2-03 | scope §8.2 IC-01 |
| **audit_entry** | IC-L2-06 `record_audit(action=gate_opened/pushed/decided/rerouted/closed)` | L1-01 L2-05 | L1-01 §12.10.1 audit_entry |
| **wbs_decomposition_request** | IC-L2-10 `request_wbs_decomposition(4_pieces, architecture)`（经 IC-19） | L1-03 | 4 件套齐后触发 |

---

### 8.3 边界

#### In-scope（本 L2 做什么）

1. **4 次 Gate 时机判定**（S1/S2/S3/S7 末；S1/S2/S3 由本 L2 从 stage_progress 事件判定；S3 则由 L1-04 推"蓝图齐"信号到本 L2 再开 Gate）
2. **Gate 卡片 bundle 打包**（收集阶段全部产出物路径 + 预览 + 预期决定选项）
3. **Gate 阻塞机制**（阻塞 L1-01 不再接收下一阶段的 state 转换请求直到用户决定）
4. **用户 Go/No-Go/Request-change 三路路由**
5. **裁剪配置查询**（开 Gate 前 IC-L2-09 查 L2-07，决定 bundle 打包哪些产出物）
6. **阶段生产任务分派**（Gate 通过后 IC-L2-01 触发下一阶段对应 L2）
7. **变更请求影响面分析**（进行中 change_request → 分析哪些 4 件套/9 计划/TOGAF 段/下游 WBS/TDD 蓝图受影响 + 生成 ADR 风格评估报告）
8. **受影响 L2 重做路由**（change_request 批准后分派到 L2-03/04/05 重做部分产出）
9. **Gate 历史追踪**（每次 Gate 的决定记录 + No-Go 次数 + change_requests 清单）
10. **内部状态机**（Gate 生命周期：WAITING → OPEN → REVIEWING → DECIDED → CLOSED；异常 → RE_OPENED）

#### Out-of-scope（本 L2 不做，谁做）

- ❌ **不生成任何产出物内容** → L2-02/03/04/05/06
- ❌ **不做阶段内部的小步 review**（inline review 由各 L2 自己处理） → 对应 L2
- ❌ **不维护 L1-01 的 state 机器**（只发 request） → L1-01 L2-03
- ❌ **不执行 TDD 阶段 S3-S6 业务**（只识别 L1-04 的"蓝图齐/S5 PASS"信号） → L1-04
- ❌ **不决定 WBS 拆分**（只在 4 件套齐后发请求） → L1-03
- ❌ **不判定硬红线/空转**（那是 L1-07 supervisor） → L1-07
- ❌ **不持久化产出物文件**（只收集路径） → L2-07 与各 L2 自己落盘

#### 边界规则

- 本 L2 只做"**Gate 控制**"，不碰产出物"**内容**"
- Gate 阻塞是"**状态级**"（L1-01 state 不切），非"**事件级**"（事件总线仍可收异步结果）
- 所有 Gate 决定必须由用户做（系统没有"自动通过"模式；最小确认 = click-only）
- 变更请求的"影响面分析"是**建议**，由用户最终确认是否重做

---

### 8.4 约束

#### 业务模式引用

- **PM-01 methodology-paced**：Stage Gate 是节奏的核心；所有阶段切换必走本 L2
- **PM-07 user-intervene-always-wins**：用户 Gate 决定 override 系统推荐
- **PM-13 合规可裁剪**：裁剪档决定 Gate 打包内容（不决定是否开 Gate，Gate 一律开）

#### 硬约束清单

1. **Gate 阻塞时长无上限**（等用户决定；不可超时自动放行）
2. **同一阶段 Gate 同一时刻只能有一个 OPEN 状态**（不可并行双开）
3. **Gate 推送延迟 ≤ 2s**（从 stage_progress 事件到 gate_card_push；性能保底）
4. **change_request 影响面分析 ≤ 5s**（不阻塞太久；超时 degrade 为"全量重做"建议）
5. **Gate 决定到 state 转换 ≤ 1s**（用户 Go 后立即切阶段；否则感官卡顿）
6. **四次 Gate 的触发时机锚定 scope**（不可擅自增减 Gate 节点）
7. **HALTED 状态下拒绝开新 Gate**（scope §5.1 硬约束路径；Gate 队列挂起）
8. **PAUSED 状态下允许继续评审已 OPEN 的 Gate**（panic 不应阻塞人类 review）

#### 性能约束

- Gate bundle 打包（10 份产出物，每份 ≤ 50KB）≤ 1s
- change_request 影响面分析（全面扫 4 件套 + 9 计划 + TOGAF + 下游）≤ 5s
- Gate 决定入站处理 ≤ 500ms
- 支持并发：单 project 至多 1 个活跃 Gate，多 project（如未来多 workspace）≤ 10 Gate 并发

---

### 8.5 🚫 禁止行为（明确清单）

- 🚫 **禁止在产出物不齐的情况下开 Gate**（必须等 stage_progress 事件 + 裁剪档启用产出物全部落盘）
- 🚫 **禁止绕过本 L2 直接发 state 转换请求**（例：L2-03 生成 4 件套后不能自己调 IC-01 切 PLAN → TDD_PLAN）
- 🚫 **禁止为 Gate 设置超时自动放行**（永远等用户）
- 🚫 **禁止在同一阶段已有 OPEN Gate 时再开新 Gate**（必须先 DECIDE 或 CLOSE）
- 🚫 **禁止在 Gate 被用户 No-Go 时静默清空 change_requests**（必须持久化、可追溯）
- 🚫 **禁止未查询裁剪档就打包**（trim_level 是打包策略的输入）
- 🚫 **禁止在 change_request 影响面分析时直接改产出物**（只生成评估报告 + 路由）
- 🚫 **禁止跨越 4 Gate 边界分派任务**（不可 S1 Gate 未过就发 S2 trigger）

---

### 8.6 ✅ 必须职责（明确清单）

- ✅ **必须**识别 4 次 Gate 时机（S1 末 / S2 末 / S3 末 / S7 末）
- ✅ **必须**在开 Gate 前 IC-L2-09 查询裁剪档
- ✅ **必须**完成 Gate 推送到用户决定之间阻塞 L1-01 state 转换
- ✅ **必须**接收用户三种决定（approve / reject / request_change）并正确路由
- ✅ **必须**在用户 Go 后 ≤ 1s 内发 IC-L2-05 state_transition 请求
- ✅ **必须**对变更请求生成影响面分析报告（ADR 风格）
- ✅ **必须**在 No-Go 或 change_request 被批准后路由到对应 L2 重做（非全量重跑）
- ✅ **必须**每次 Gate 事件（open/push/decided/rerouted/closed）走 IC-L2-06 审计
- ✅ **必须**在 4 件套齐且 S2 Gate 通过后发 IC-L2-10 触发 L1-03 拆 WBS
- ✅ **必须**跨 session 恢复未决 Gate（bootstrap 时若有 OPEN Gate，直接恢复 UI 卡片）

---

### 8.7 🔧 可选功能职责（可做但不硬性要求）

- 🔧 **Gate 评审的并发预览**：同一 bundle 可 diff 上一版本（增值 UI，给用户看 change_request 带来的改动）
- 🔧 **Gate 决定预测建议**：根据 KB 历史 Gate 结果给用户"推荐决定"（仅建议，用户仍需确认）
- 🔧 **Gate 评审时限统计**：记录每次 Gate 用户决定耗时，用于 retro 分析瓶颈
- 🔧 **Change-request 自动拆条**：当用户写自然语言 change_requests 时用 L1-05 LLM skill 拆成 atomic 条目
- 🔧 **Gate 评审协作（多用户）**：未来多用户场景下支持多人签字（本阶段非必需）

---

### 8.8 与其他 L2 交互（IC-L2 契约实现）

**L2-01 作为调用方**：

| IC | 被调方 | 何时调 | 调用字段（关键） |
|---|---|---|---|
| **IC-L2-01** | L2-02/03/04/05/06 | Gate 通过后触发下阶段生产，或 No-Go 后重做部分 | `{stage, context, trim_level, target_subset?: ['requirements','goals']}`（target_subset 仅在重做时非空）|
| **IC-L2-03** | L1-10（经 IC-16） | 产出物齐 + 裁剪档查过 + 阻塞就位 | `{gate_id, stage_from, stage_to, artifacts_bundle, trim_level, required_decisions, diff_from_previous?}` |
| **IC-L2-05** | L1-01 L2-03（经 IC-01） | 用户 Go 后 | `{from, to, reason: 'user_gate_approved', gate_id}` |
| **IC-L2-06** | L1-01 L2-05（经 IC-09） | 每次 Gate 生命周期转换 | `{actor: L2-01, action: gate_opened/pushed/decided/rerouted/closed, reason, evidence, ts, linked_gate}` |
| **IC-L2-09** | L2-07 | 开 Gate 前 | `{level: full/minimal/custom}` → `{enabled_templates: [doc_type]}` |
| **IC-L2-10** | L1-03（经 IC-19） | S2 Gate 通过（4 件套 + TOGAF 齐全）后 | `{four_pieces_refs, architecture_refs, trim_level}` |

**L2-01 作为被调方**：

| IC | 调用方 | 何时被调 | 接收字段 |
|---|---|---|---|
| **stage_progress 事件订阅** | L2-02/03/04/05/06 | 阶段产出物齐全信号 | `{stage, event_name: 4_pieces_ready/9_plans_ready/..., artifact_refs}` |
| **IC-L2-04** | L1-10（经 IC-17） | 用户在 Gate 卡片上点 Go/No-Go/Request-change | `{gate_id, decision, change_requests?: [str], rationale?: str}` |
| **change_request 事件订阅** | L1-10（经 IC-17）| 用户运行时发变更请求 | `{request_id, description, affected_scope_hint?: str}` |
| **state transition 横切通知** | L1-01 L2-03 | state 进入 PAUSED/HALTED/恢复 | `{from, to, reason}` → L2-01 挂起/恢复 Gate 机器 |

---

### 8.9 🎯 交付验证大纲（TDD 直接消费）

#### 成功信号（系统跑起来能看到的）

- 启动后 `L2-01.gate_controller.state = READY` 且订阅了 5 类事件
- S1 产出齐后 ≤ 2s 内看到 `gate_card_push` 审计事件 + L1-10 UI 出现 Gate 卡片
- 用户点 Go 后 ≤ 1s state_transition 审计事件落 + L1-01 state 切到下一阶段
- No-Go 后 ≤ 1s 看到 `gate_rerouted` 审计 + 对应 L2 收到 IC-L2-01 重做 trigger
- change_request 后 ≤ 5s 看到 "影响面分析报告" ADR 落盘 + 推给用户

#### 最小正向测试用例（对应 ✅ 必须职责）

| # | 场景 | 验证点 |
|---|---|---|
| P1 | S1 产出齐（章程 + 干系人 + goal_anchor_hash）→ 期望 `gate_opened` + Gate 卡片推出 | S1 Gate 正常开 |
| P2 | S2 产出齐（4 件套 + 9 计划 + TOGAF A-D + ADR ≥ 10）→ 期望 Gate 打包完整 | S2 Gate 正常开 |
| P3 | L1-04 推 `tdd_blueprint_ready` → 期望 S3 Gate 正常开 | S3 Gate（由 L1-04 触发）|
| P4 | L2-06 推 `delivery_bundled` → 期望 S7 Gate 正常开（最终验收）| S7 Gate |
| P5 | 用户 Go → 期望 ≤ 1s 发 state_transition + 分派下阶段 | Go 路径 |
| P6 | 用户 No-Go + change_requests=['改验收标准 AC-03'] → 期望重做 L2-03 受影响部分 | No-Go 路径 |
| P7 | 用户 Request-change（运行时）"我想改 WP-05 的验收" → 期望 ≤ 5s 出影响面报告 | change_request 路径 |
| P8 | 裁剪档=minimal → Gate 打包只含启用模板子集 | 裁剪打包 |
| P9 | 4 件套齐（S2 Gate 通过后）→ 期望发 IC-L2-10 给 L1-03 拆 WBS | WBS 触发 |
| P10 | 用户在 Gate OPEN 时重启 Claude Code → 期望 bootstrap 后 UI 恢复 Gate 卡片 | 跨 session 恢复 |

#### 最小负向测试用例（对应 🚫 禁止行为）

| # | 场景 | 验证点 |
|---|---|---|
| N1 | stage_progress 事件但产出物不齐（缺 TOGAF D）→ 期望拒绝开 Gate + 审计违规 | 产出不齐 |
| N2 | 同一阶段已 OPEN Gate 时再发 stage_progress → 期望忽略 + 审计 duplicate_open | 单 Gate 约束 |
| N3 | 未查 trim_level 直接打包 → 期望内部自检失败 + 审计 | 查裁剪档必须 |
| N4 | 用户 No-Go 但未附 change_requests → 期望要求用户补充（拒绝路由）| 输入校验 |
| N5 | state=HALTED 时 stage_progress 到达 → 期望 Gate 挂起（不推卡片，审计 queued） | HALTED 下挂起 |
| N6 | L2-03 绕过本 L2 直接调 IC-01 切 PLAN→TDD_PLAN → 期望 L1-01 L2-03 拒绝 + 审计违规（依赖 L1-01 侧也有校验） | 路由合规 |
| N7 | 设置 Gate 超时 = 30s 自动放行 → 期望配置拒绝加载 + 启动失败 | 配置硬拦 |

#### 集成用例（跨 L2 / 跨 L1）

| # | 场景 | 涉及 |
|---|---|---|
| I1 | S1 端到端（产出齐 → Gate → Go → 切 PLAN → L2-03 启动）| L2-02 → L2-01 → L2-03 |
| I2 | S2 端到端含 4 件套 + 9 计划 + TOGAF + WBS 触发 | L2-03/04/05 → L2-01 → L1-03 |
| I3 | S3 Gate（L1-04 侧蓝图齐）→ L2-01 推 → 用户 Go → L1-04 进 S4 | L1-04 → L2-01 → L1-04 |
| I4 | S7 最终验收 Gate（交付包齐 → 用户 Go → state=CLOSED）| L2-06 → L2-01 → L1-01 |
| I5 | 运行时 change_request 影响 WP-05 → 影响面分析 → 批准 → 重做 L2-03 部分 + L1-03 重拆 WBS + L1-04 重做 TDD | L1-10 → L2-01 → L2-03 → L1-03 → L1-04 |
| I6 | Gate OPEN 时系统 panic → state=PAUSED → Gate 仍可评审 → 用户 Go → resume → 切阶段 | L2-01 与 L1-01 L2-03 横切 |

#### 性能阈值

- Gate 推送延迟 ≤ 2s（P99）
- change_request 影响面分析 ≤ 5s（P99）
- Gate 决定到 state_transition ≤ 1s（P99）
- Gate bundle 打包 ≤ 1s（10 产出物）
- 配置查询（IC-L2-09）≤ 100ms

---

### 8.10 L3 · Stage Gate 控制器实现设计（产品视角）

> L3 粒度：算法 + 数据结构 + 状态机 + 产品逻辑流程图。**不含技术栈选型**，供下游技术方案阶段输入。

#### 8.10.1 Gate 生命周期内部状态机

```
     [ WAITING ]
        │ stage_progress 事件到达 + 产出物齐校验通过
        │ + 裁剪档查询完成 + 阻塞就位
        ▼
      [ OPEN ]
        │ IC-L2-03 push_stage_gate_card (推到 L1-10)
        ▼
   [ REVIEWING ]
        │ 用户 IC-L2-04 user_decision
        ▼
     [ DECIDED ]
        │
        ├── decision=approve ──→ [ CLOSED ]（正常关闭，发 state_transition）
        │                               │ 下阶段触发完成
        │                               ▼
        │                           [ ARCHIVED ]
        │
        ├── decision=reject + change_requests ──→ [ REROUTING ]
        │                                              │ 重做路由分派完成
        │                                              ▼
        │                                          [ WAITING ]（等重做完的 stage_progress）
        │
        └── decision=request_change (运行时 · 少见)
                │ 做影响面分析
                ▼
            [ ANALYZING ]
                │ 分析完 + 用户 Re-Go
                ▼
            [ REROUTING ]
                │
                ▼
            [ WAITING ]

 横切中断：
  - state=HALTED → 任何态 → [ SUSPENDED ] (挂起)
  - user_intervene(resume) → SUSPENDED → 原态
```

**状态不变量**：
- 同一阶段同时刻只能有一个非终态 Gate（WAITING/OPEN/REVIEWING/DECIDED/REROUTING/ANALYZING）
- DECIDED 是瞬态（≤ 1s 内必转 CLOSED / REROUTING / ANALYZING）
- ARCHIVED 是最终态（Gate 结束，但历史保留给 retro）
- SUSPENDED 可从任意非 ARCHIVED 态进入 + 返回原态

#### 8.10.2 4 次 Gate 触发时机判定算法

```
function should_open_gate(stage_progress_event):
    stage = stage_progress_event.stage
    event_name = stage_progress_event.event_name

    # 定义每阶段的"齐全信号集"
    ready_signals = {
        'S1': {'charter_ready', 'stakeholders_ready', 'goal_anchor_hash_locked'},
        'S2': {'4_pieces_ready', '9_plans_ready', 'togaf_ready', 'adr_count>=10',
               'wbs_ready'},  # WBS 也要齐（L1-03 完成）
        'S3': {'tdd_blueprint_ready'},   # L1-04 推送
        'S7': {'delivery_bundled', 'retro_ready', 'archive_written',
               'kb_promotion_done'}
    }

    # 累积已到达的信号到 project_state
    project_state.accumulated_ready[stage].add(event_name)

    # 判定齐全
    required = ready_signals[stage]
    if project_state.accumulated_ready[stage] >= required:
        # 齐全 → 触发 Gate
        if has_active_gate(stage):
            emit_audit('duplicate_open_rejected', stage)
            return False
        return True
    return False

function on_stage_progress(event):
    if not should_open_gate(event):
        return
    # 开 Gate
    trim_level = query_trim(current_project.trim_config)  # IC-L2-09
    bundle = collect_artifacts_bundle(event.stage, trim_level)
    gate_id = open_gate(stage=event.stage, bundle=bundle, trim_level=trim_level)
    emit_audit('gate_opened', gate_id)
    push_gate_card(gate_id, bundle)  # IC-L2-03
    emit_audit('gate_pushed', gate_id)
    block_state_transition(reason='waiting_for_gate_decision', gate_id=gate_id)
```

**关键设计**：
- "齐全信号集"是**声明式**的，不同裁剪档不同（完整 vs 精简），由 L2-07 裁剪配置决定
- 信号可以在任意顺序到达（异步），本 L2 累积在 `project_state.accumulated_ready` 中
- 只要齐就开 Gate，不等"全阶段跑完时点"这种东西

#### 8.10.3 Gate 卡片 bundle 打包协议

```yaml
# GateCard schema (随 IC-L2-03 传给 L1-10)
gate_card:
  gate_id: gate_{stage}_{uuid}
  project_id: p_xxx
  stage_from: S1               # S1/S2/S3/S7
  stage_to: S2                 # 对应下一阶段
  opened_at: iso8601
  trim_level: full | minimal | custom
  enabled_templates:           # 来自 IC-L2-09 查询结果
    - charter
    - stakeholders
    - requirements
    - goals
    - acceptance_criteria
    - quality_standards
    # ... 按 trim_level 不同而不同
  artifacts_bundle:
    - path: "docs/planning/requirements.md"
      doc_type: requirements
      status: ready
      size_bytes: 12345
      preview_url: "http://localhost:8765/preview?path=docs/planning/requirements.md"
      hash: "sha256:..."
      produced_by: L2-03
      produced_at: iso8601
    - path: "docs/planning/goals.md"
      doc_type: goals
      status: ready
      # ...
    # ... 共 N 份 (按 enabled_templates 数量)
  bundle_meta:
    total_artifacts: 12
    total_size_bytes: 150000
    diff_from_previous_gate: null   # 若是 re-open，则填 diff ref
  required_decisions:
    - approve    # 对应 Go
    - reject     # 对应 No-Go (需附 change_requests)
    - request_change   # 对应运行时变更 (少见)
  decision_context:
    estimated_review_duration_min: 15   # 给用户的建议
    critical_checks:                     # 引导用户重点看什么
      - "验收标准是否可测"
      - "TOGAF D 的技术选型是否合规"
      - "9 计划的成本预估是否合理"
  previous_gate_history:                 # 该阶段的 re-open 历史
    - gate_id: gate_S2_abc
      decision: reject
      change_requests: ["改 AC-03"]
      decided_at: iso
```

**关键设计**：
- bundle **只传路径 + 元数据**，不传文件内容（L1-10 自己去 preview_url 读）
- `enabled_templates` 来自 IC-L2-09，用户能看到"裁剪档是否少了东西"
- `critical_checks` 是给 UI 的提示（可按阶段定制，精简档少几条）
- `previous_gate_history` 给 re-open 场景用，让用户知道"上次为什么 reject"

#### 8.10.4 用户 Go/No-Go/Request-change 路由算法

```
function on_user_decision(gate_id, decision, change_requests=[], rationale=None):
    gate = find_gate(gate_id)
    assert gate.state == REVIEWING, f"gate not in REVIEWING: {gate.state}"

    gate.user_decision = decision
    gate.change_requests = change_requests
    gate.rationale = rationale
    gate.decided_at = now()
    gate.state = DECIDED
    emit_audit('gate_decided', gate_id, decision=decision)

    # 分路由
    if decision == 'approve':
        # Go 路径
        gate.state = CLOSED
        emit_audit('gate_closed', gate_id)
        # 解锁 L1-01
        unblock_state_transition(gate_id)
        # 发 state_transition
        state_from = current_state()
        state_to = next_state_after_stage(gate.stage_from)  # S1 → CLARIFY, S2 → PLAN, etc.
        send_ic_l2_05(request_state_transition(state_from, state_to,
            reason=f'user_gate_approved:{gate_id}'))
        # 分派下阶段
        dispatch_next_stage(gate.stage_to)  # IC-L2-01

    elif decision == 'reject':
        # No-Go 路径
        assert len(change_requests) > 0, "reject must include change_requests"
        gate.state = REROUTING
        # 影响面分析（简化版，因为是明确的 change_requests，不是模糊 request）
        affected_l2s = analyze_impact(gate.stage_from, change_requests)
        # 分派重做
        for l2, subset in affected_l2s.items():
            send_ic_l2_01(trigger_stage_production(
                stage=gate.stage_from,
                context={'rerouting': True, 'change_requests': change_requests},
                target_subset=subset  # 只重做这几份
            ))
        emit_audit('gate_rerouted', gate_id, target_l2s=list(affected_l2s.keys()))
        gate.state = WAITING   # 等重做后的 stage_progress
        # 注意：state_transition 不发，L1-01 保持原 state（不进下阶段）

    elif decision == 'request_change':
        # 运行时变更路径
        gate.state = ANALYZING
        report = generate_impact_report(gate.stage_from, change_requests)  # ADR 风格
        save_adr(report, path=f"docs/adr/CR-{gate.gate_id}.md")
        push_impact_report_to_user(report)
        # 等用户 Re-Go (变 reject 或 approve 的二次决定)
```

**关键设计**：
- `approve` → 立即 CLOSED + 切 state + 分派下阶段
- `reject` → 同阶段内重做受影响部分，**不退 state**（state 保持在本阶段）
- `request_change` → 先出影响面报告（ADR），**等用户二次确认**后才走 reject 路径

#### 8.10.5 变更请求影响面分析算法

```
function analyze_impact(stage, change_requests):
    """
    输入: change_requests (list of natural language or structured edits)
    输出: {L2 ID: subset of docs to redo}
    """
    affected = {'L2-03': set(), 'L2-04': set(), 'L2-05': set(), 'L2-06': set()}
    downstream_affected = {'L1-03': False, 'L1-04': False}

    for cr in change_requests:
        # 1. 用 LLM (L1-05 skill) 把自然语言 CR 拆 + 匹配到产出物
        parsed = parse_change_request(cr)
        # parsed = { 'target_doc_type': 'acceptance_criteria',
        #            'target_section': 'AC-03',
        #            'intent': 'modify AC-03 to include...', ... }

        # 2. 根据 target_doc_type 映射到 L2
        if parsed.target_doc_type in ['requirements', 'goals',
                                       'acceptance_criteria', 'quality_standards']:
            affected['L2-03'].add(parsed.target_doc_type)
            # 4 件套之间有依赖链, 级联
            if parsed.target_doc_type == 'goals':
                affected['L2-03'].update(['acceptance_criteria', 'quality_standards'])
            # 验收/质量改了 → 下游 WBS / TDD 蓝图也要改
            if parsed.target_doc_type in ['acceptance_criteria', 'quality_standards']:
                downstream_affected['L1-03'] = True
                downstream_affected['L1-04'] = True

        elif parsed.target_doc_type in ['scope_plan', 'schedule_plan',
                                         'cost_plan', 'quality_plan',
                                         'resource_plan', 'communication_plan',
                                         'risk_plan', 'procurement_plan',
                                         'stakeholder_engagement_plan']:
            affected['L2-04'].add(parsed.target_doc_type)
            # 质量计划改了 → 也影响 L2-05 D (技术架构的质量属性)
            if parsed.target_doc_type == 'quality_plan':
                affected['L2-05'].add('D-technology')

        elif parsed.target_doc_type in ['A-vision', 'B-business',
                                         'C-data', 'C-application', 'D-technology',
                                         'adr']:
            affected['L2-05'].add(parsed.target_doc_type)
            # A/B/C 改了 → 下游依赖级联
            if parsed.target_doc_type == 'A-vision':
                affected['L2-05'].update(['B-business', 'C-data', 'C-application',
                                           'D-technology'])
            if parsed.target_doc_type == 'B-business':
                affected['L2-05'].update(['C-data', 'C-application', 'D-technology'])
            # TOGAF D 改了 → L2-04 质量/风险计划也要跟
            if parsed.target_doc_type == 'D-technology':
                affected['L2-04'].update(['quality_plan', 'risk_plan'])

    # 3. 生成结构化报告
    return {
        'affected_l2s': {k: list(v) for k, v in affected.items() if v},
        'downstream_affected': {k: v for k, v in downstream_affected.items() if v},
        'total_docs_to_redo': sum(len(v) for v in affected.values()),
        'estimated_duration_min': estimate_redo_duration(affected)
    }
```

**级联规则**（矩阵形式）：

| 改了什么 | 同 L2 内级联 | 跨 L2 级联 | 跨 L1 级联 |
|---|---|---|---|
| requirements | goals, AC, quality | L2-04 范围计划 | L1-03 WBS |
| goals | AC, quality | L2-04 进度计划 | L1-03, L1-04 |
| acceptance_criteria | quality | — | L1-03, L1-04 |
| A-vision (TOGAF) | B, C, D | — | — |
| B-business (TOGAF) | C, D | L2-04 范围计划 | — |
| D-technology (TOGAF) | ADR | L2-04 质量、风险 | L1-04 TDD 蓝图 |
| quality_plan | — | L2-05 D | L1-04 质量标准 |

#### 8.10.6 阻塞 / 解锁机制

```
function block_state_transition(reason, gate_id):
    # 注册到 L1-01 L2-03 的"阻塞者"列表
    l1_01_state_machine.register_blocker(
        blocker_type='gate_controller',
        gate_id=gate_id,
        reason=reason,
        set_at=now()
    )
    emit_audit('state_transition_blocked', gate_id, reason=reason)

function unblock_state_transition(gate_id):
    l1_01_state_machine.unregister_blocker(gate_id=gate_id)
    emit_audit('state_transition_unblocked', gate_id)

# L1-01 L2-03 侧的行为（跨 L1 协议）:
# - 当 register_blocker 被调用时, state 机器拒绝所有 IC-01 request_state_transition
# - 直到 unregister_blocker 才恢复处理
# - 阻塞期间入队的请求保留, 解锁后按 FIFO 处理
```

**关键设计**：
- 阻塞是"**状态机级**"（只挡 state 转换），**不挡事件总线**（异步结果仍可收）
- 一个 gate_id 对应一个 blocker；多 Gate 并发时多 blocker（但同 project 同阶段最多 1）
- 若 Gate 被 reject 进入 REROUTING → **blocker 不解除**（还要等重做完再开新 Gate）
- 若 user_intervene(resume) from PAUSED → 不影响 blocker（Gate 机制独立）

#### 8.10.7 核心数据结构 schema

**Gate**：

```yaml
gate:
  gate_id: gate_{stage}_{uuid}
  project_id: p_xxx
  stage_from: S1|S2|S3|S7
  stage_to: CLARIFY|PLAN|TDD_PLAN|CLOSED
  state: WAITING|OPEN|REVIEWING|DECIDED|REROUTING|ANALYZING|SUSPENDED|CLOSED|ARCHIVED
  trim_level: full|minimal|custom
  enabled_templates: [str]
  artifacts_bundle: [ArtifactRef]
  opened_at: iso
  pushed_at: iso | null
  decided_at: iso | null
  closed_at: iso | null
  user_decision: approve | reject | request_change | null
  change_requests: [str]
  rationale: str | null
  rerouting_target_l2s: [str] | null
  rerouting_target_subset: {L2: [doc_type]} | null
  impact_report_ref: path | null     # request_change 时的 ADR
  previous_gate_id: gate_id | null   # re-open 时链接
  suspend_context:
    suspended_at: iso | null
    suspended_reason: str | null
  audit_trail: [audit_entry]         # 本 Gate 的所有审计事件 ID
```

**ArtifactRef**：

```yaml
artifact_ref:
  path: str
  doc_type: str
  status: ready|stale|missing
  size_bytes: int
  hash: sha256
  produced_by: L2-XX
  produced_at: iso
  preview_url: url
```

**ProjectGateState**（本 L2 的全局状态）：

```yaml
project_gate_state:
  project_id: p_xxx
  trim_config:
    level: full|minimal|custom
    custom_overrides: {doc_type: bool}
  accumulated_ready:        # 每阶段已到达的齐全信号
    S1: [str]
    S2: [str]
    S3: [str]
    S7: [str]
  active_gates: {stage: gate_id}    # 每阶段至多 1 个活跃
  gate_history: [gate_id]           # 所有历史 Gate（含 re-open）
  blockers_registered: [gate_id]    # 对 L1-01 L2-03 注册的 blocker
```

**GateEvent**（审计事件专用）：

```yaml
gate_event:
  event_id: evt_{uuid}
  gate_id: gate_id
  action: gate_opened|pushed|decided|rerouted|closed|archived|suspended|resumed
  actor: L2-01 | user | L1-01 | ...
  ts: iso
  evidence: object          # 场景不同字段不同
  linked_state_transition: state_transition_id | null
```

#### 8.10.8 核心产品逻辑流程图（4 张 ASCII）

**图 1 · Gate 开-推-决定-分派 正常端到端**

```
[stage_progress 事件]
     ↓
should_open_gate(event)? （齐全信号集判定）
     ↓ YES
has_active_gate(stage)? （同阶段单 Gate 约束）
     ↓ NO
query_trim(trim_config) → IC-L2-09 → L2-07
     ↓
collect_artifacts_bundle(stage, trim_level)
     ↓
open_gate(...)  → Gate.state = OPEN
     ↓
emit_audit('gate_opened')
     ↓
push_gate_card(gate_id, bundle)  → IC-L2-03 → IC-16 → L1-10
     ↓
emit_audit('gate_pushed')
     ↓
block_state_transition(gate_id)  (register_blocker to L1-01 L2-03)
     ↓
Gate.state = REVIEWING
     ↓
...等待用户...
     ↓
[用户 IC-L2-04 user_decision 到达]
     ↓
Gate.user_decision = decision
Gate.state = DECIDED
     ↓
emit_audit('gate_decided')
     ↓
 ┌───┴───────────────────────┬─────────────────────────────┐
 ▼                           ▼                             ▼
decision=approve        decision=reject               decision=request_change
 ▼                           ▼                             ▼
Gate.state=CLOSED        analyze_impact(change_req)     generate_impact_report
unblock_state_transition  ▼                             (ADR 风格)
 ▼                       dispatch_redo(subset) →           ▼
send state_transition     IC-L2-01 to 对应 L2          save_adr + push_to_user
 (approve)                   ▼                             ▼
 ▼                       Gate.state=REROUTING           Gate.state=ANALYZING
dispatch_next_stage      Gate.state=WAITING (回)        (等用户二次决定)
 → IC-L2-01                 ▼
 ▼                       (等新 stage_progress)
下阶段 L2 开工
```

**图 2 · No-Go 重做 + Re-Open**

```
Gate.state = REVIEWING  (首次 Gate)
     ↓
用户 decision = reject, change_requests = ['改 AC-03']
     ↓
analyze_impact(S2, ['改 AC-03'])
 → {'L2-03': ['acceptance_criteria', 'quality_standards'],   # 级联
    'L1-03': True}  # WBS 也受影响
     ↓
dispatch:
  - IC-L2-01(stage=S2, target_subset=['AC', 'quality']) → L2-03
  - (不立即派 L1-03, 等 L2-03 重做完后再经 4_pieces_ready 重新触发)
     ↓
Gate.state = REROUTING → WAITING
     ↓
(L2-03 重做 AC + quality 约 10min)
     ↓
L2-03 发 4_pieces_ready_v2 事件
     ↓
本 L2 收到 → should_open_gate(S2)?  YES (accumulated_ready 仍齐)
     ↓
has_active_gate(S2)?  YES (旧 Gate 在 WAITING)
     ↓
(特殊路径) close_old_gate + open_new_gate(previous_gate_id=旧)
     ↓
新 Gate.state = OPEN, bundle 包括 diff_from_previous_gate
     ↓
push_gate_card (UI 显示变更 diff)
     ↓
用户二次 review → 决定 (Go / 再 No-Go)
```

**图 3 · 运行时 change_request (TOGAF H)**

```
[项目进行中, state=IMPL, L1-04 正跑 S4]
     ↓
用户从 L1-10 UI 发 change_request: "我想改 WP-05 验收"
     ↓
IC-17 user_intervene(type=change_request) → L1-01 → 本 L2-01
     ↓
(进行中 change_request, 非 Gate 上下文)
     ↓
本 L2 创建临时 "虚 Gate"（仅用于承载 ANALYZING 态）
 → Gate.state = ANALYZING
     ↓
analyze_impact(current_stage=IMPL, CR)
 →  解析 CR: "WP-05 的 AC"
 →  affected: L2-03 (AC), L1-03 (WBS 可能重拆), L1-04 (TDD 重做 + 若已实现 → 代码改)
     ↓
generate_impact_report (ADR 格式)
  title: "CR-001: 修改 WP-05 验收标准"
  context: 运行时变更
  decision_required: 是否批准
  consequences:
    - L2-03 重做 AC (5min)
    - L1-03 重拆 WP-05 (10min)
    - L1-04 TDD 蓝图重做 (20min)
    - 代码改 (视 WP-05 完成度)
    - 风险：已完成的 WP-05 测试失效
     ↓
save_adr(docs/adr/CR-001.md)
     ↓
push_impact_report_to_user (UI 显示报告 + 批准/取消按钮)
     ↓
用户二次决定
 ├── 批准 → 走 reject 路径（触发重做, 可能先回退 state）
 │         → 若影响面大, 可能先暂停 L1-04 (IC-15 hard_halt 或 pause)
 │         → state 可能回退到 PLAN (重新 S2 Gate)
 └── 取消 → Gate 销毁, 继续原工作
```

**图 4 · 跨 session bootstrap 恢复未决 Gate**

```
(Claude Code 重启)
     ↓
L1-09 bootstrap 重建 task-board
     ↓
L1-01 bootstrap tick → L2-02 决策
     ↓
L2-02 决策: "检查未决 Gate"
     ↓
调本 L2-01 query_open_gates(project_id)
     ↓
本 L2-01 从持久化存储读 project_gate_state
     ↓
找到 gate_S2_abc, state=REVIEWING
     ↓
验证 artifacts_bundle 文件是否仍在 (hash 比对)
 ├── 全在 → 直接恢复 UI 卡片
 │         push_gate_card (带 resumed_from_checkpoint 标记)
 │         Gate.state 保持 REVIEWING
 ├── 部分失效 → Gate.state = SUSPENDED
 │             emit_audit('gate_suspended_artifacts_stale')
 │             通知用户 "Gate 需重新生成产出物"
 └── 全失效 → Gate.state = ARCHIVED (归档)
             state_transition → 回退到本阶段入口
```

#### 8.10.9 配置参数清单

供运维/部署调整（默认值属 L1-02 标准，可覆盖但要审计）：

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `GATE_PUSH_TIMEOUT_MS` | 2000 | 500-5000 | stage_progress → push_gate_card 延迟阈值 |
| `IMPACT_ANALYSIS_TIMEOUT_MS` | 5000 | 2000-10000 | change_request 影响面分析超时 |
| `STATE_TRANSITION_TIMEOUT_MS` | 1000 | 500-3000 | 用户 Go → state_transition 延迟阈值 |
| `BUNDLE_PACK_TIMEOUT_MS` | 1000 | 500-3000 | artifacts_bundle 打包延迟 |
| `MAX_CONCURRENT_GATES_PER_PROJECT` | 1 | 1-1 | 硬上限，不可改（单项目单 Gate）|
| `MAX_GATE_HISTORY_PER_STAGE` | 10 | 5-50 | re-open 次数上限（防无限循环）|
| `CRITICAL_CHECKS_S1` | [default list] | — | S1 Gate 的 UI 提示 checks |
| `CRITICAL_CHECKS_S2` | [default list] | — | S2 Gate 的 UI 提示 checks |
| `CRITICAL_CHECKS_S3` | [default list] | — | S3 Gate 的 UI 提示 checks |
| `CRITICAL_CHECKS_S7` | [default list] | — | S7 Gate 的 UI 提示 checks |
| `IMPACT_MATRIX_CONFIG_PATH` | builtin | path | 级联矩阵配置文件（图 2 的级联规则可外化） |
| `GATE_AUTO_TIMEOUT_ENABLED` | false | false-only | 硬禁用（永不超时自动放行） |

---

*— L2-01 详细定义 R3 完（§8 全量 + L3 实现设计齐全，约 500 行）*

---

## 9. L2-02 · 启动阶段产出器（S1） 详细定义

### 9.1 职责 + 锚定

**一句话职责**：S1 启动阶段的产出执行者 —— 接 L2-01 触发后完成"澄清→章程→干系人→goal_anchor 锁定"4 步产出链，产出齐全后发 `S1_ready` 事件。

**上游锚定**：
- Goal §2.3："S1 启动 · 章程 · 干系人"
- scope §5.2.2 输入："用户初始目标描述"
- businessFlow BF-S1-01（澄清）/ BF-S1-02（章程）/ BF-S1-03（干系人）

**下游服务**：L2-01（产出齐全后发信号开 S1 Gate）/ L2-07（请模板）/ L1-05（调澄清 skill）/ L1-06（读历史章程 KB）

---

### 9.2 输入 / 输出

| 类别 | 内容 | 来源 / 去向 |
|---|---|---|
| **输入 trigger** | IC-L2-01 trigger_stage_production(stage=S1, context, trim_level) | L2-01 → L2-02 |
| **输入 context** | 用户初始目标描述（自然语言）+ 项目 id | L2-01 传入 |
| **输出 产出物** | docs/charter.md / docs/stakeholders.md / project_manifest.yaml (含 goal_anchor_hash) | 落盘 + L2-01 订阅 |
| **输出 事件** | `charter_ready` / `stakeholders_ready` / `goal_anchor_hash_locked` | 事件总线 → L2-01 |

---

### 9.3 边界

#### In-scope
1. 4 步产出链的顺序执行（澄清 → 章程 → 干系人 → goal_anchor 锁定）
2. 委托 L1-05 brainstorming skill 与用户对话澄清
3. 调 L2-07 拿章程/干系人模板 + 填入
4. 计算 goal_anchor 的 sha256 hash 并持久化
5. 事件发布（每步产出齐发对应 ready 事件）

#### Out-of-scope
- ❌ 不做 Gate 判定与推送 → L2-01
- ❌ 不做 4 件套 / 9 计划 / TOGAF → L2-03/04/05
- ❌ 不自写 LLM 澄清逻辑 → L1-05 skill
- ❌ 不做模板管理 → L2-07

#### 边界规则
- goal_anchor 一经锁定（hash 入库）即不可在本项目生命周期内修改（PM-01 硬约束）
- 澄清失败（用户打断 / 3 次无法收敛）→ degrade 为最小章程 + 标记 clarification_incomplete

---

### 9.4 约束

#### 业务模式
- **PM-01 methodology-paced**：S1 先于一切（先澄清再谈计划）
- **PM-03 user-goal-anchored**：goal_anchor_hash 是全生命周期的"契约锚"

#### 硬约束
1. 澄清会话至多 3 轮（超出降级为最小章程）
2. goal_anchor hash 必须 sha256（不接受更弱算法）
3. 章程必填字段 8 项（title / purpose / scope / success_criteria / constraints / risks_initial / stakeholders_initial / authority）
4. 干系人识别至少 1 人（至少有 project_owner = 用户自己）

#### 性能约束
- 单步产出 ≤ 2min（含 LLM 时间）
- 整个 S1 产出链 ≤ 10min（用户响应不计）

---

### 9.5 🚫 禁止行为

- 🚫 禁止在未澄清通过的情况下生成章程
- 🚫 禁止跳过 goal_anchor 锁定直接广播 S1_ready
- 🚫 禁止自写章程模板（必须经 L2-07）
- 🚫 禁止直接改用户输入（LLM 澄清只能问，不能篡改）
- 🚫 禁止复用上项目的 goal_anchor（每项目独立）

---

### 9.6 ✅ 必须职责

- ✅ **必须**按顺序执行 4 步（澄清 → 章程 → 干系人 → goal_anchor）
- ✅ **必须**把章程存成 markdown + frontmatter（可被 L2-07 模板引擎识别）
- ✅ **必须**把 goal_anchor_hash 写入 `docs/project_manifest.yaml`（单一事实源）
- ✅ **必须**每步完成发对应 ready 事件到事件总线
- ✅ **必须**支持中断恢复（若 Claude Code 重启，从当前步继续）

---

### 9.7 🔧 可选功能

- 🔧 干系人 RACI 矩阵自动生成（基于干系人角色 LLM 建议 RACI 分配）
- 🔧 多语言章程输出（中/英双版，默认中文）
- 🔧 章程历史版本 diff（若用户 S1 re-open 时看变化）

---

### 9.8 与其他 L2 / L1 交互

| IC | 对方 | 何时 | 字段 |
|---|---|---|---|
| IC-L2-02 request_template | L2-07 | 生成章程/干系人时 | `{doc_type: charter|stakeholders}` |
| IC-L2-06 record_audit | L1-01 L2-05 | 每步产出 | `{actor:L2-02, action:charter_generated/...}` |
| IC-L2-07 kb_read | L1-06 | 可选，读历史章程模式 | `{kind: charter_pattern, filter}` |
| IC-05 delegate_subagent | L1-05 | 澄清对话 | `{subagent: brainstorming, goal: clarify_intent}` |

---

### 9.9 🎯 交付验证大纲

| # | 场景 | 验证点 |
|---|---|---|
| P1 | 用户输入 "做一个 todo 应用" → 期望 3 轮内澄清 + 章程落盘 + goal_anchor_hash 写入 manifest | 端到端正常 |
| P2 | 章程落盘后 → 期望 `charter_ready` 事件发出 | 事件发布 |
| P3 | goal_anchor 锁定后 → 期望 `goal_anchor_hash_locked` 事件 | 锁定信号 |
| N1 | 未澄清通过强行调 generate_charter → 期望拒绝 | 顺序约束 |
| N2 | 复用上项目的 manifest → 期望 hash mismatch 失败 | 独立性 |
| N3 | 澄清 3 轮未收敛 → 期望 degrade 到最小章程 + 标记 clarification_incomplete | 降级机制 |
| I1 | S1 端到端（L2-01 触发 → L2-02 4 步 → S1_ready → L2-01 开 Gate）| 跨 L2 集成 |

**性能**：整个 S1 ≤ 10min（用户响应外）；goal_anchor hash 计算 ≤ 10ms。

---

### 9.10 L3 · S1 启动阶段产出实现设计

#### 9.10.1 4 步产出链状态机

```
[IDLE]
  │ IC-L2-01 triggered
  ▼
[CLARIFYING]
  │ delegate_subagent(brainstorming) → 用户 Q&A 循环 ≤ 3 轮
  │ └── 用户收敛 → intent_clarified
  │ └── 3 轮未收敛 → degrade_to_minimal
  ▼
[CHARTER_GEN]
  │ IC-L2-02 request_template(charter) → L2-07
  │ LLM 填模板 → docs/charter.md
  │ emit charter_ready
  ▼
[STAKEHOLDERS_GEN]
  │ IC-L2-02 request_template(stakeholders) → L2-07
  │ LLM 识别干系人 → docs/stakeholders.md
  │ emit stakeholders_ready
  ▼
[GOAL_ANCHOR_LOCKING]
  │ 组装 goal_anchor text (title + purpose + scope + AC)
  │ sha256(goal_anchor text) → hash
  │ 写 docs/project_manifest.yaml
  │ emit goal_anchor_hash_locked
  ▼
[DONE]
```

#### 9.10.2 澄清对话算法（简化）

```
function clarify(initial_input):
    sub_agent = delegate('brainstorming', goal='refine user intent to SMART goal')
    answers = []
    for round in 1..3:
        questions = sub_agent.propose_questions(initial_input, answers)
        if questions.empty():  # LLM 认为已清晰
            return build_clarified_intent(answers)
        user_response = ui_ask(questions)
        answers.append(user_response)
        if sub_agent.is_converged(answers):
            return build_clarified_intent(answers)
    # 3 轮仍未收敛
    return build_minimal_intent(initial_input, answers, flag='clarification_incomplete')
```

#### 9.10.3 章程模板 8 字段

```yaml
charter:
  title: str                 # 项目名称
  purpose: str               # 为什么做
  scope:                     # 范围声明
    in_scope: [str]
    out_of_scope: [str]
  success_criteria: [str]    # 成功判据（后面会精化为 AC）
  constraints: [str]         # 约束（时间 / 预算 / 技术）
  risks_initial: [str]       # 初识风险
  stakeholders_initial: [str] # 初识干系人
  authority:                 # 决策授权
    approver: str
    escalation_path: [str]
```

#### 9.10.4 干系人识别规则

```
function identify_stakeholders(charter):
    candidates = []

    # 规则 1: 用户自己始终是 project_owner
    candidates.append({role: 'project_owner', who: 'user', influence: 'high'})

    # 规则 2: LLM 从 purpose + scope 推断
    llm_candidates = llm.analyze(charter, prompt='who_benefits_who_affects')
    candidates.extend(llm_candidates)

    # 规则 3: 若 purpose 涉及团队 → 加 team_members 占位
    if '团队' in charter.purpose or 'team' in charter.purpose.lower():
        candidates.append({role: 'team_members', who: 'TBD', influence: 'medium'})

    # 规则 4: 若技术选型敏感 → 加 tech_lead 占位
    if has_tech_selection_concern(charter):
        candidates.append({role: 'tech_lead', who: 'user', influence: 'high'})

    return candidates
```

#### 9.10.5 goal_anchor 锁定协议

```yaml
# docs/project_manifest.yaml (写入后 S2/S3/S4/S5 不可改本字段)
project_manifest:
  project_id: p_{uuid}
  created_at: iso
  goal_anchor:
    title: str
    purpose: str
    scope_ref: docs/charter.md#scope
    ac_ref: docs/charter.md#success_criteria
  goal_anchor_hash: sha256:{hex}      # 锚定 hash
  goal_anchor_text_snapshot: |
    {组装 goal_anchor 所用的完整文本，用于后续任何时候的 hash 比对}
  locked_at: iso
  locked_by: L2-02
```

**hash 组装规则**：
```
text_to_hash = f"{title}\n{purpose}\n{scope.in_scope joined}\n{scope.out_of_scope joined}\n{success_criteria joined}"
hash = sha256(text_to_hash.encode('utf-8'))
```

#### 9.10.6 配置参数

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `CLARIFICATION_MAX_ROUNDS` | 3 | 1-5 | 澄清最大轮数 |
| `CHARTER_FIELDS_REQUIRED` | [8 项] | — | 章程必填字段列表 |
| `HASH_ALGO` | sha256 | sha256-only | goal_anchor hash 算法（不接受弱算法） |
| `S1_STEP_TIMEOUT_MS` | 120000 | 30000-300000 | 单步产出超时 |
| `S1_TOTAL_TIMEOUT_MS` | 600000 | 180000-1800000 | 整个 S1 超时（不含用户响应） |

---

*— L2-02 详细定义 R4 完（约 220 行，简单型 L2 粒度）*

---

## 10. L2-03 · 4 件套生产器（S2 核心） 详细定义

### 10.1 职责 + 锚定

**一句话职责**：S2 规划阶段的"需求锚定器" —— 按**依赖顺序串行**生成需求文档 / 目标文档 / 验收标准 / 质量标准 四份文档（Stage Gate 硬性产出物），做质量自检后广播 `4_pieces_ready` 事件，供下游 L2-04 (9 计划) / L2-05 (TOGAF) / L1-03 (WBS) / L1-04 (TDD) 同步消费。

**上游锚定**：
- Goal §2.4："S2 规划 · 4 件套 · 硬门槛"
- scope §5.2.5 禁止 2："禁止 4 件套不齐进 S3"
- scope §5.2.6 必须义务 3："4 件套产出齐全"
- businessFlow BF-S2-01（需求）/ BF-S2-02（目标）/ BF-S2-03（验收）/ BF-S2-04（质量）
- 响应面 3：跨 L1 消费链（4 件套齐 → L1-03/04 订阅触发）

**下游服务**：L2-04（9 计划前置依赖）/ L2-05（TOGAF 业务架构前置依赖）/ L1-03（WBS 拆解依赖）/ L1-04（Master Test Plan 依据）/ L2-01（`4_pieces_ready` 事件触发 S2 Gate 累积判定）

---

### 10.2 输入 / 输出

#### 输入

| 类别 | 内容 | 来源 |
|---|---|---|
| **触发** | IC-L2-01 trigger_stage_production(stage=S2, context, trim_level, target_subset?) | L2-01（S1 Gate 通过后 / No-Go 后重做） |
| **上下文依赖** | docs/charter.md / docs/stakeholders.md / docs/project_manifest.yaml | 上游 L2-02 产出物 |
| **模板请求返回** | 4 个模板 (requirements/goals/AC/quality_standards) | IC-L2-02 → L2-07 |
| **KB 历史** | 可选，类似项目的 4 件套模式 | IC-L2-07 → L1-06 |
| **用户 inline review**（非 Stage Gate） | 每份文档生成后可选的 inline 确认 | L1-10 UI（轻量）|

#### 输出

| 类别 | 内容 | 去向 |
|---|---|---|
| **产出物** | docs/planning/requirements.md / goals.md / acceptance-criteria.md / quality-standards.md | 本地文件 |
| **事件** | requirements_ready → goals_ready → ac_ready → quality_ready → `4_pieces_ready`（总结事件） | 事件总线（L1-09）|
| **审计** | IC-L2-06 record_audit(actor=L2-03, action=doc_generated / doc_reviewed / 4_pieces_complete) | L1-01 L2-05 |

---

### 10.3 边界

#### In-scope（做什么）

1. **4 份文档的串行生成**（严格按依赖顺序：requirements → goals → AC → quality）
2. **依赖上游产出物**（charter / stakeholders / goal_anchor）
3. **调 L2-07 拿模板 + LLM 填充**（via L1-05 invoke_skill）
4. **质量自检**（每份文档做合规性检查 · 字段完整性 · 可测性）
5. **inline review 点**（可选的用户轻 review，非 Gate）
6. **事件发布**（逐份 ready + 总 4_pieces_ready）
7. **重做路由响应**（L2-01 No-Go 后只重做 target_subset 中指定的文档）
8. **产出物版本管理**（重做时生成 v2, v3 保留历史）
9. **跨文档一致性校验**（goals 引用 requirements id / AC 引用 goals id / quality 关联 AC）

#### Out-of-scope（不做）

- ❌ **不做 Gate 判定 / 推送** → L2-01
- ❌ **不做 9 计划 / TOGAF / WBS / TDD** → L2-04/05/L1-03/L1-04
- ❌ **不写 LLM 底层** → 走 L1-05 skill 调度
- ❌ **不管模板本身** → L2-07
- ❌ **不决定何时触发 WBS** → 总事件由 L2-01 接收后发 IC-L2-10 触发

#### 边界规则

- 4 份文档的**依赖顺序不可并行**（goals 依赖 requirements, AC 依赖 goals, quality 依赖 AC）
- 重做（No-Go 后）时**只重做 target_subset**，不改其他（保留链式一致性）
- 每份文档必须经质量自检才发 ready 事件
- 跨文档引用（e.g. AC-03 引用 REQ-01）必须 id 可回溯

---

### 10.4 约束

#### 业务模式引用

- **PM-01 methodology-paced**：S2 的 4 件套是 S3 (TDD) 的前置硬门槛
- **PM-04 TDD-driven**：AC 必须"Given-When-Then"结构（为 S3 TDD 做输入）
- **PM-13 合规可裁剪**：本 4 件套在"精简档"下仍全保留（核心最小集，不可裁）

#### 硬约束清单

1. **4 份文档全量必保**（裁剪档不影响 4 件套数量，只影响 9 计划 / TOGAF 深度）
2. **依赖顺序串行**（不可并行）
3. **质量自检失败不发 ready 事件**（必须修到过）
4. **AC 必须 Given-When-Then 结构**（格式硬约束，为 L1-04 TDD 消费）
5. **需求/目标/AC 的 id 规则固定**（REQ-NNN / GOAL-NN / AC-NNN / QS-NNN 命名规范）
6. **单份文档生成 ≤ 5min**（含 LLM 时间）
7. **整个 4 件套 ≤ 20min**（顺序执行总时长上限）
8. **跨文档引用必须合法**（下游文档引用的上游 id 必须真实存在）

#### 性能约束

- 单份文档生成（含 LLM + 模板填充 + 质量自检）≤ 5min
- 4 件套总时长 ≤ 20min
- 质量自检 ≤ 10s/份
- 重做（target_subset 只含 1-2 份）≤ 10min

---

### 10.5 🚫 禁止行为

- 🚫 **禁止并行生成 4 份文档**（必须串行依赖）
- 🚫 **禁止跳过质量自检发 ready 事件**
- 🚝 **禁止在依赖未齐时生成下游文档**（如 goals 在 requirements 未 ready 时开工）
- 🚫 **禁止引用不存在的上游 id**（如 AC-01 引用 REQ-999 但 REQ-999 不存在）
- 🚫 **禁止在精简档下裁减 4 件套数量**（本 4 件套是核心最小集）
- 🚫 **禁止重做时修改 target_subset 外的文档**
- 🚫 **禁止不带 frontmatter 的文档发 ready**（模板引擎要的元数据必须有）

---

### 10.6 ✅ 必须职责

- ✅ **必须**按 requirements → goals → AC → quality 顺序串行生成
- ✅ **必须**每份文档用 L2-07 模板（不自造）
- ✅ **必须**每份文档做质量自检（合规 + 完整 + 可测）
- ✅ **必须**每份文档 ready 后发对应事件 + 总 4_pieces_ready
- ✅ **必须**支持 target_subset 重做（No-Go 重做路径）
- ✅ **必须**维护跨文档 id 引用链（可回溯）
- ✅ **必须**重做时保留历史版本（v1/v2 共存）
- ✅ **必须**暴露 4 件套的索引 API 给 L2-01 打包 Gate bundle

---

### 10.7 🔧 可选功能

- 🔧 **相似需求 KB 提示**：生成 requirements 时查 L1-06 KB 找相似需求提示 LLM
- 🔧 **需求澄清辅助子 Agent**：遇 ambiguous requirement 时委托 L1-05 反问用户
- 🔧 **AC 覆盖矩阵自动生成**：AC 生成后自动画 goals × AC 覆盖矩阵（可视化）
- 🔧 **质量标准自动关联 NFR**：quality_standards 生成时自动识别非功能需求（性能/安全/可用性）
- 🔧 **跨项目需求模式学习**：累计多个项目的需求 KB 给 L1-05 reranker

---

### 10.8 与其他 L2 / L1 交互

**L2-03 作为调用方**：

| IC | 对方 | 何时 | 字段 |
|---|---|---|---|
| IC-L2-02 request_template | L2-07 | 每份文档生成前 | `{doc_type: requirements|goals|acceptance_criteria|quality_standards, trim_level, variables: {...}}` |
| IC-L2-06 record_audit | L1-01 L2-05 | 每份文档生成 / review / 重做 | 标准 audit entry |
| IC-L2-07 kb_read | L1-06 | 可选，读相似项目需求模式 | `{kind: requirements_pattern, filter: domain=...}` |
| IC-05 delegate_subagent | L1-05 | 需要子 Agent 澄清时 | `{subagent: requirements-clarification, goal}` |
| 事件发布 | L1-09 事件总线 | 每份文档 ready + 总 4_pieces_ready | 事件名 + artifact_ref |

**L2-03 作为被调方**：

| IC | 调用方 | 何时 | 字段 |
|---|---|---|---|
| IC-L2-01 trigger_stage_production | L2-01 | 首次 S2 启动 / No-Go 重做 | `{stage=S2, context, trim_level, target_subset?: ['requirements','goals']}` |
| query_artifact_refs | L2-01 | 打包 Gate bundle 时 | → 返回 4 件套路径 + hash + 版本 |

---

### 10.9 🎯 交付验证大纲

#### 成功信号

- L2-01 trigger 后 20min 内看到 `4_pieces_ready` 事件
- 4 个 doc 文件都落盘 + frontmatter 齐全 + 质量自检通过
- L1-03 订阅 `4_pieces_ready` 后开始拆 WBS（集成证据）

#### 最小正向测试用例

| # | 场景 | 验证点 |
|---|---|---|
| P1 | 正常触发 → 顺序生成 4 份 → 总事件发出 | 串行 + 总事件 |
| P2 | 需求文档生成后 → 期望 `requirements_ready` 事件 | 逐份事件 |
| P3 | AC 文档内引用 REQ-01 / GOAL-01 → 校验 id 存在 | 跨文档引用 |
| P4 | AC 文档的每条 AC 按 Given-When-Then 结构 | 格式硬约束 |
| P5 | 重做（target_subset=['acceptance_criteria']）→ 只重做 AC，其他不动 | 部分重做 |
| P6 | 重做后保留 v1（requirements.md.v1）| 历史版本 |
| P7 | query_artifact_refs → 返回 4 份 + hash | API 暴露 |
| P8 | 精简档 trim_level=minimal → 4 件套仍全出（不裁数量）| 核心最小集 |

#### 最小负向测试用例

| # | 场景 | 验证点 |
|---|---|---|
| N1 | 并行生成 requirements + goals → 期望拒绝 + 审计违规 | 顺序约束 |
| N2 | 质量自检失败 → 期望不发 ready 事件 + 停在 FAILED | 自检阻塞 |
| N3 | AC 引用 REQ-999（不存在）→ 期望自检失败 | id 校验 |
| N4 | AC 不是 Given-When-Then → 期望自检失败 | 格式约束 |
| N5 | 重做时改了 target_subset 外的 quality → 期望拒绝 | 范围约束 |
| N6 | 上游 charter 缺失 → 期望拒绝启动 S2 | 前置依赖 |

#### 集成用例

| # | 场景 | 涉及 |
|---|---|---|
| I1 | S2 端到端：L2-01 trigger → L2-03 4 步 → 4_pieces_ready → L2-04/05/L1-03 消费 | 跨 L2/L1 |
| I2 | S2 No-Go 重做链：L2-01 reject + change_requests=['改 AC-03'] → L2-03 重做 AC → 新 4_pieces_ready | 重做链 |
| I3 | 跨 session 恢复：生成 requirements 后重启 → 恢复到 goals_gen 继续 | 恢复 |

**性能**：单份 ≤ 5min；总 ≤ 20min；重做（1-2 份）≤ 10min；质量自检 ≤ 10s。

---

### 10.10 L3 · 4 件套生产器实现设计

#### 10.10.1 4 步串行状态机

```
[IDLE]
  │ IC-L2-01 triggered (stage=S2)
  │ target_subset? → 全量 or 部分重做
  ▼
[REQUIREMENTS_GEN]              ← 若 target_subset 不含 requirements，跳过
  │ IC-L2-02 request_template(requirements)
  │ LLM 填模板 + 调 L1-06 可选 KB
  │ 质量自检
  │   ├── PASS → save + emit requirements_ready
  │   └── FAIL → retry (≤ 2 次) or FAILED
  ▼
[GOALS_GEN]                    ← 若 target_subset 不含 goals，跳过
  │ 依赖 requirements_ready（若本次跳过需求则直接读既有 requirements.md）
  │ 同上套路
  │ emit goals_ready
  ▼
[AC_GEN]
  │ 依赖 goals_ready
  │ 同上套路 + Given-When-Then 结构自检
  │ emit ac_ready
  ▼
[QUALITY_GEN]
  │ 依赖 ac_ready + stakeholders 的 NFR 字段
  │ 同上套路
  │ emit quality_ready
  ▼
[CROSS_CHECK]
  │ 跨文档一致性校验（id 引用链完整性）
  │   ├── PASS → emit 4_pieces_ready
  │   └── FAIL → 定位问题文档 → 回到对应 step 重做
  ▼
[DONE]

异常路径：
  - 任一 step 3 次自检仍 FAIL → state=FAILED, 审计 + 通知 L2-01
  - 中途收到 panic/halt → 保存当前进度 (checkpoint) → SUSPENDED
```

#### 10.10.2 4 份文档的内容 schema

**requirements.md (frontmatter + body)**：

```yaml
---
doc_id: req-p-{uuid}-v1
doc_type: requirements
stage: S2
produced_by: L2-03
produced_at: iso
parent_doc: [charter.md, goal_anchor_hash: sha256:xxx]
trim_level: full
version: v1
---

# 需求文档

## REQ-001 <需求标题>
- **描述**: ...
- **来源**: charter.purpose / stakeholders.role / ...
- **优先级**: P0 | P1 | P2
- **类型**: functional | non-functional
- **依赖**: REQ-NNN (如有)

## REQ-002 ...

## 非功能需求汇总
- NFR-P01 性能: ...
- NFR-S01 安全: ...
- NFR-A01 可用性: ...
```

**goals.md**：

```yaml
---
doc_id: goal-p-{uuid}-v1
doc_type: goals
parent_doc: [requirements.md]
---

# 目标文档

## GOAL-01 <目标标题>
- **SMART**: specific/measurable/achievable/relevant/time-bound
- **度量**: <具体 metric>
- **关联需求**: REQ-001, REQ-003
- **成功阈值**: ...

## GOAL-02 ...
```

**acceptance-criteria.md（核心硬约束：Given-When-Then）**：

```yaml
---
doc_id: ac-p-{uuid}-v1
doc_type: acceptance_criteria
parent_doc: [goals.md, requirements.md]
---

# 验收标准

## AC-001 <标题>
- **关联目标**: GOAL-01
- **关联需求**: REQ-001
- **场景**:
  - **Given** <前置条件>
  - **When** <触发动作>
  - **Then** <期望结果>
- **优先级**: must | should | may
- **可测性**: automated | manual | ambiguous

## AC-002 ...
```

**quality-standards.md**：

```yaml
---
doc_id: qs-p-{uuid}-v1
doc_type: quality_standards
parent_doc: [acceptance-criteria.md]
---

# 质量标准

## QS-001 性能
- **关联 NFR**: NFR-P01
- **标准**: P99 ≤ 500ms
- **验证方法**: load_test / benchmark

## QS-002 覆盖率
- **关联 AC**: 全部 AC
- **标准**: 单元测试覆盖率 ≥ 80% + 集成测试覆盖关键路径
- **验证方法**: coverage_report

## QS-003 安全
- **关联 NFR**: NFR-S01
- **标准**: OWASP Top 10 自查通过 + 无高危 CVE
- **验证方法**: security_scan
```

#### 10.10.3 质量自检算法

```
function quality_check(doc_type, doc_content):
    errors = []
    warnings = []

    # 通用检查
    if not has_valid_frontmatter(doc_content):
        errors.append('missing_or_invalid_frontmatter')

    if not has_required_sections(doc_type, doc_content):
        errors.append('missing_required_sections')

    # 类型特定检查
    if doc_type == 'requirements':
        if not has_id_pattern(r'REQ-\d{3}', doc_content):
            errors.append('requirements_id_pattern_violation')
        if not has_nfr_section(doc_content):
            warnings.append('missing_nfr_summary')

    elif doc_type == 'goals':
        goals = parse_goals(doc_content)
        for goal in goals:
            if not is_smart(goal):  # 检查 SMART 5 字段
                errors.append(f'{goal.id}_not_smart')
            if not ref_valid(goal.linked_req, 'requirements.md'):
                errors.append(f'{goal.id}_invalid_req_ref')

    elif doc_type == 'acceptance_criteria':
        acs = parse_acs(doc_content)
        for ac in acs:
            if not has_given_when_then(ac):
                errors.append(f'{ac.id}_not_given_when_then')
            if not ref_valid(ac.linked_goal, 'goals.md'):
                errors.append(f'{ac.id}_invalid_goal_ref')
            if ac.testability == 'ambiguous':
                warnings.append(f'{ac.id}_ambiguous_testability')

    elif doc_type == 'quality_standards':
        qss = parse_qss(doc_content)
        for qs in qss:
            if not has_measurable_criteria(qs):
                errors.append(f'{qs.id}_not_measurable')
            if not has_verification_method(qs):
                errors.append(f'{qs.id}_missing_verification')

    return {
        'pass': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
```

#### 10.10.4 跨文档一致性校验

```
function cross_check():
    req_ids = extract_all_ids('docs/planning/requirements.md', r'REQ-\d{3}')
    goal_ids = extract_all_ids('docs/planning/goals.md', r'GOAL-\d{2}')
    ac_ids = extract_all_ids('docs/planning/acceptance-criteria.md', r'AC-\d{3}')
    qs_ids = extract_all_ids('docs/planning/quality-standards.md', r'QS-\d{3}')

    errors = []

    # 1. goals 的 linked_req 必须在 req_ids 中
    for goal in parse_goals(docs/planning/goals.md):
        for req_ref in goal.linked_reqs:
            if req_ref not in req_ids:
                errors.append(f'{goal.id} references non-existent {req_ref}')

    # 2. AC 的 linked_goal 必须在 goal_ids 中, linked_req 必须在 req_ids 中
    for ac in parse_acs(docs/planning/acceptance-criteria.md):
        if ac.linked_goal not in goal_ids:
            errors.append(f'{ac.id} references non-existent {ac.linked_goal}')
        for req in ac.linked_reqs:
            if req not in req_ids:
                errors.append(f'{ac.id} references non-existent {req}')

    # 3. QS 的 linked_ac 必须在 ac_ids 中 (或 "全部 AC")
    for qs in parse_qss(docs/planning/quality-standards.md):
        for ac_ref in qs.linked_acs:
            if ac_ref != 'all' and ac_ref not in ac_ids:
                errors.append(f'{qs.id} references non-existent {ac_ref}')

    # 4. 覆盖率检查（warning，非 error）
    uncovered_reqs = req_ids - {req for ac in acs for req in ac.linked_reqs}
    if uncovered_reqs:
        warnings.append(f'Requirements not covered by any AC: {uncovered_reqs}')

    return {'pass': len(errors) == 0, 'errors': errors, 'warnings': warnings}
```

#### 10.10.5 重做路由处理

```
function handle_rerouting(target_subset):
    """
    输入: target_subset = ['acceptance_criteria', 'quality_standards']
         (来自 L2-01 No-Go 时的 change_requests 分析结果)
    """
    # 先做依赖闭包（如改 goals 必然级联 AC + quality）
    dependency_closure = {
        'requirements': ['requirements', 'goals', 'acceptance_criteria', 'quality_standards'],
        'goals': ['goals', 'acceptance_criteria', 'quality_standards'],
        'acceptance_criteria': ['acceptance_criteria', 'quality_standards'],
        'quality_standards': ['quality_standards']
    }
    to_redo = set()
    for t in target_subset:
        to_redo.update(dependency_closure[t])

    # 备份旧版本 (v1 → v2)
    for doc in to_redo:
        path = f'docs/planning/{doc}.md'
        current_version = read_frontmatter(path).get('version', 'v1')
        next_version = f'v{int(current_version[1:]) + 1}'
        backup_path = f'{path}.{current_version}'
        copy(path, backup_path)

    # 按顺序重做
    for doc_type in ordered(['requirements', 'goals', 'acceptance_criteria', 'quality_standards']):
        if doc_type in to_redo:
            regenerate(doc_type, previous_version_ref=backup_path)
            emit(f'{doc_type}_ready_v{next_version}')

    emit('4_pieces_ready_v{next_version}')  # 总事件带 v
```

**级联规则**：
- 改 requirements → 四份全重做（依赖链）
- 改 goals → goals + AC + quality 重做
- 改 AC → AC + quality 重做
- 改 quality → 只 quality 重做

#### 10.10.6 核心产品逻辑流程图（3 张 ASCII）

**图 1 · 4 件套正常串行生成**

```
[IC-L2-01 trigger(S2, target_subset=[all])]
                   ↓
          读上游依赖:
          charter.md, stakeholders.md, project_manifest.yaml
                   ↓
          query_trim(trim_level) → L2-07 → enabled_templates
          （本轮 4 件套必全在 enabled_templates，不然配置违规）
                   ↓
          ─────────── Step 1 ───────────
          IC-L2-02 request_template(requirements)
                   ↓
          LLM 填模板 (L1-05 invoke_skill requirements-analysis)
                   ↓
          质量自检: pass?
            ├── NO → retry (≤ 2 次) or FAIL
            └── YES → write docs/planning/requirements.md
                   ↓
          emit requirements_ready → 事件总线
                   ↓
          ─────────── Step 2 ───────────
          依赖 requirements.md → 生成 goals
            (同上套路)
                   ↓
          emit goals_ready
                   ↓
          ─────────── Step 3 ───────────
          依赖 goals.md + requirements.md → 生成 AC
            + Given-When-Then 结构硬自检
                   ↓
          emit ac_ready
                   ↓
          ─────────── Step 4 ───────────
          依赖 AC.md + NFR 字段 → 生成 quality
            (含 measurable + verification_method 硬自检)
                   ↓
          emit quality_ready
                   ↓
          ─────────── Cross-check ───────────
          cross_check() → id 引用链完整性
            ├── errors → 定位文档 → 回对应 Step
            └── pass → emit 4_pieces_ready
                   ↓
          [DONE]
          L2-01 订阅 4_pieces_ready
          + 累积到 accumulated_ready[S2]
          + 若 S2 信号齐 → 开 S2 Gate
```

**图 2 · No-Go 重做链**

```
[L2-01 Gate 被 No-Go + change_requests=['改 AC-03']]
                   ↓
L2-01.analyze_impact → affected_l2s={L2-03: ['acceptance_criteria']}
                   ↓
IC-L2-01 to L2-03(target_subset=['acceptance_criteria'])
                   ↓
L2-03 dependency_closure(['acceptance_criteria']) = ['AC', 'quality']
                   ↓
备份：
  acceptance-criteria.md → .v1 保留
  quality-standards.md → .v1 保留
                   ↓
Step 3 重做 AC (LLM 知道用户 change_request)
                   ↓
emit ac_ready_v2
                   ↓
Step 4 重做 quality (自动级联)
                   ↓
emit quality_ready_v2
                   ↓
Cross-check
                   ↓
emit 4_pieces_ready_v2
                   ↓
L2-01 收到 → 开新 S2 Gate（带 diff_from_previous_gate = v1）
```

**图 3 · 跨文档 id 引用链**

```
requirements.md:  REQ-001  REQ-002  REQ-003
                    │        │        │
                    ↓        ↓        ↓
goals.md:         GOAL-01 (refs REQ-001+REQ-002)
                  GOAL-02 (refs REQ-003)
                    │        │
                    ↓        ↓
AC.md:            AC-001 (goal=GOAL-01, req=REQ-001)
                  AC-002 (goal=GOAL-01, req=REQ-002)
                  AC-003 (goal=GOAL-02, req=REQ-003)
                    │        │         │
                    ↓        ↓         ↓
quality.md:       QS-001 (ac=ALL, NFR-P)
                  QS-002 (ac=ALL, coverage)
                  QS-003 (ac=AC-001+AC-003, security)

cross_check 规则：
  - 每个下游 id 的所有上游 ref 必须存在
  - 上游 id 若被删除 → 触发 "孤儿 ref" 警告
```

#### 10.10.7 配置参数清单

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `DOC_GEN_TIMEOUT_MS` | 300000 | 60000-600000 | 单份文档生成超时 (5min) |
| `TOTAL_4_PIECES_TIMEOUT_MS` | 1200000 | 600000-3600000 | 4 件套总超时 (20min) |
| `QUALITY_CHECK_RETRY_MAX` | 2 | 0-5 | 自检失败重试次数 |
| `ID_PATTERN_REQ` | `REQ-\d{3}` | — | 需求 id 正则 |
| `ID_PATTERN_GOAL` | `GOAL-\d{2}` | — | 目标 id 正则 |
| `ID_PATTERN_AC` | `AC-\d{3}` | — | AC id 正则 |
| `ID_PATTERN_QS` | `QS-\d{3}` | — | QS id 正则 |
| `AC_FORMAT_HARD_CHECK` | true | true-only | Given-When-Then 硬拦 (不可关) |
| `KB_READ_ENABLED` | true | — | 开关 L1-06 KB 辅助 |
| `VERSION_BACKUP_PATTERN` | `{filename}.v{N}` | — | 重做时历史版本命名 |

---

*— L2-03 详细定义 R5 完（约 500 行，核心型 L2 粒度）*

---

## 11. L2-04 · PMP 9 计划生产器（S2） 详细定义

### 11.1 职责 + 锚定

**一句话职责**：S2 规划阶段的"PMP 知识领域并行生产者" —— 分 3 组（基础 3 / 依赖 TOGAF-D 的 2 / 协同 4）并行调度生成 PMP 九大管理计划，解决计划间的**依赖等待**问题，齐全后广播 `9_plans_ready` 事件。

**上游锚定**：
- Goal §2.5："S2 PMP 9 计划"
- scope §5.2.6 必须义务 4："产出物齐全"
- businessFlow BF-S2-05（PMP 9 计划）
- 响应面 5：PMP × TOGAF 交织矩阵

**下游服务**：L2-01（事件累积开 S2 Gate）/ L2-05（部分输入/输出互为依赖）/ L1-03（资源/进度计划作 WBS 输入）

---

### 11.2 输入 / 输出

| 类别 | 内容 | 来源 / 去向 |
|---|---|---|
| **触发** | IC-L2-01(stage=S2, target_subset?) + 4_pieces_ready 信号 | L2-01 分派 + 订阅 |
| **输入依赖** | 4 件套 (requirements/goals/AC/quality) + charter + stakeholders | 读磁盘 |
| **输入依赖（部分）** | TOGAF D-technology.md（给 quality_plan / risk_plan 做参考） | 等 L2-05 的 D 产出事件 |
| **输出产出物** | docs/planning/{scope,schedule,cost,quality,resource,communication,risk,procurement,stakeholder_engagement}-plan.md | 本地文件 |
| **输出事件** | 各 plan 的 ready 事件 → 总 `9_plans_ready` | 事件总线 |

---

### 11.3 边界

#### In-scope
1. 9 份 PMP 计划的生成（分 3 组调度）
2. 组间依赖等待（Group 2 等 TOGAF D）
3. 组内并行（Group 1/3 内部可同时跑，Group 2 串行）
4. 调 L2-07 拿模板 + L1-05 LLM 填充
5. 各 plan 的合规性自检
6. 总事件广播

#### Out-of-scope
- ❌ 不做 TOGAF 架构内容 → L2-05
- ❌ 不做 4 件套 → L2-03
- ❌ 不持久化 task-board → L1-09

#### 边界规则
- 精简档下（PM-13）只出 5 计划（scope/schedule/quality/risk/stakeholder_engagement），其余跳过
- quality_plan 和 risk_plan 必须等 TOGAF D 完成（硬依赖）
- 组内并发度由配置（默认 3 路并行）

---

### 11.4 约束

#### 业务模式
- **PM-01 methodology-paced**：PMP 是 S2 两条产出线之一（另一条 TOGAF）
- **PM-13 合规可裁剪**：精简档只出 5 计划

#### 硬约束
1. 9 计划的分组 + 依赖不可变（不得在 Group 1 把 quality_plan 也并发）
2. 精简档启用子集固定（不得用户自定义精简内容）
3. 单份计划生成 ≤ 3min
4. 9 计划总时长（含并发）≤ 15min
5. quality_plan / risk_plan 必须引用 TOGAF D 的决策 ADR（硬关联）

#### 性能
- 单份 ≤ 3min
- 总（完整档 9 份）≤ 15min（并发效益）
- 精简档 ≤ 8min

---

### 11.5 🚫 禁止行为

- 🚫 禁止在 TOGAF D 未 ready 时生成 quality_plan / risk_plan
- 🚫 禁止在 4 件套未齐时启动
- 🚫 禁止全 9 计划串行跑（浪费时间；必须按组并行）
- 🚫 禁止精简档下擅自增加计划（只能按预设子集）
- 🚫 禁止 quality_plan 里不引用 TOGAF D 的 ADR

---

### 11.6 ✅ 必须职责

- ✅ **必须**分 3 组调度（Group 1 基础 / Group 2 TOGAF 依赖 / Group 3 协同）
- ✅ **必须**按 trim_level 启用对应子集
- ✅ **必须**每份计划用 L2-07 模板
- ✅ **必须**每份计划做合规自检（有预算 / 有时间线 / 有责任人）
- ✅ **必须**等 togaf_d_ready 事件再启 Group 2
- ✅ **必须**总完成后发 `9_plans_ready`（完整档）或 `5_plans_ready`（精简档）

---

### 11.7 🔧 可选功能

- 🔧 Gantt 图自动绘制（从 schedule_plan 生成 mermaid Gantt）
- 🔧 风险矩阵热力图（risk_plan 的可视化增强）
- 🔧 成本模型模拟（给 cost_plan 多方案比较）

---

### 11.8 与其他 L2 / L1 交互

| IC | 对方 | 何时 | 字段 |
|---|---|---|---|
| IC-L2-02 request_template | L2-07 | 每份 plan 生成 | `{doc_type: scope_plan/...}` |
| IC-L2-06 record_audit | L1-01 L2-05 | 每份 / 组 / 总事件 | 标准 |
| IC-L2-07 kb_read | L1-06 | 可选，类似项目的 plan 模式 | `{kind: plan_pattern}` |
| IC-05 delegate_subagent | L1-05 | 调 writing-plans skill | `{subagent: plan-writing}` |
| 事件订阅 | L2-05 | 等 togaf_d_ready | — |
| 事件订阅 | L2-03 | 等 4_pieces_ready | — |

---

### 11.9 🎯 交付验证大纲

| # | 场景 | 验证点 |
|---|---|---|
| P1 | 4_pieces_ready → Group 1 (scope/schedule/cost) 并行启动 | 分组调度 |
| P2 | togaf_d_ready 后 → Group 2 (quality/risk) 启动 | 依赖等待 |
| P3 | Group 1+2 完成后 → Group 3 (resource/communication/procurement/stakeholder) 并行 | 顺序 |
| P4 | 精简档 → 只出 5 计划 | 裁剪 |
| P5 | quality_plan 引用 TOGAF ADR-D1 | 硬关联 |
| N1 | 在 TOGAF D 未 ready 时强行启 quality_plan → 拒绝 | 依赖约束 |
| N2 | 全 9 串行跑 → 配置拒绝 | 并行约束 |
| I1 | S2 端到端：4_pieces + togaf → 9 plans | 跨 L2 集成 |

**性能**：完整 9 ≤ 15min，精简 5 ≤ 8min，单份 ≤ 3min。

---

### 11.10 L3 · PMP 9 计划生产器实现设计

#### 11.10.1 3 组调度状态机

```
[IDLE]
  │ IC-L2-01 triggered
  ▼
[WAITING_4_PIECES]
  │ 等 4_pieces_ready 事件
  ▼
[GROUP_1_RUNNING] (基础 3 计划并行)
  │   scope_plan │ schedule_plan │ cost_plan  （并发）
  │   合并等最慢完成
  ▼
[WAITING_TOGAF_D]  ← 横切：同时启 Group 1，但 Group 2 在此等
  │ 等 togaf_d_ready 事件
  ▼
[GROUP_2_RUNNING] (依赖 TOGAF D 的 2 计划并行)
  │   quality_plan │ risk_plan
  ▼
[GROUP_3_RUNNING] (协同 4 计划并行)
  │   resource │ communication │ procurement │ stakeholder_engagement
  ▼
[ALL_READY]
  │ emit 9_plans_ready
  ▼
[DONE]

精简档（trim=minimal）：
  Group 1: scope / schedule
  Group 2: quality (等 TOGAF D) / risk (等 TOGAF D)
  Group 3: stakeholder_engagement
  → emit 5_plans_ready
```

#### 11.10.2 9 计划内容大纲

| 计划 | 核心字段 | 依赖 |
|---|---|---|
| scope_plan | in_scope / out_of_scope / WBS 边界 / 变更控制流程 | 4 件套 |
| schedule_plan | 里程碑 / Gantt / 关键路径 / buffer | scope_plan |
| cost_plan | 预算分项 / 控制阈值 / ROI 模型 | scope / schedule |
| quality_plan | 质量目标 / 度量 / 验证方法 / 引用 TOGAF D-ADR | TOGAF D |
| resource_plan | 人力 / 工具 / 环境 / 分配矩阵 | scope |
| communication_plan | 会议 / 报告 / 受众 / 频率 | stakeholders |
| risk_plan | 风险登记册 / 概率 × 影响 / 应对 / 引用 TOGAF D-ADR | TOGAF D / quality |
| procurement_plan | 外采项 / 合同类型 / 供应商评估 | scope / resource |
| stakeholder_engagement_plan | 期望管理 / 参与策略 / RACI | stakeholders / communication |

#### 11.10.3 组内并发算法

```
function run_group_parallel(plans: list, concurrency=3):
    semaphore = Semaphore(concurrency)
    tasks = []
    for plan in plans:
        tasks.append(async_run(produce_plan, plan, semaphore))
    results = await_all(tasks)
    for p, r in zip(plans, results):
        if r.status == 'failed':
            emit_audit('plan_failed', plan=p, error=r.error)
            retry_or_fail(p)
    emit_audit('group_complete', plans=[p for p in plans if results matched pass])

function produce_plan(plan_type, semaphore):
    with semaphore:
        template = request_template(plan_type)
        content = llm_generate(template, context=read_dependencies(plan_type))
        check = self_check(plan_type, content)
        if not check.pass:
            retry(≤ 2)
        write(f'docs/planning/{plan_type}-plan.md', content)
        emit(f'{plan_type}_ready')
```

#### 11.10.4 计划合规自检

```
function check_plan(plan_type, content):
    errors = []
    common_required = ['budget_or_estimate', 'timeline', 'responsible_role']
    for field in common_required:
        if not has_section(content, field):
            errors.append(f'{plan_type} missing {field}')

    # 特定检查
    if plan_type == 'quality_plan':
        if not refs_togaf_adr(content):
            errors.append('quality_plan must reference TOGAF D-ADR')
    if plan_type == 'risk_plan':
        if not has_prob_impact_matrix(content):
            errors.append('risk_plan missing prob×impact matrix')
    if plan_type == 'schedule_plan':
        if not has_critical_path(content):
            errors.append('schedule_plan missing critical path')

    return {'pass': len(errors) == 0, 'errors': errors}
```

#### 11.10.5 配置参数

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `GROUP_CONCURRENCY` | 3 | 1-5 | 组内并发度 |
| `PLAN_GEN_TIMEOUT_MS` | 180000 | 60000-600000 | 单份计划超时 |
| `PLANS_TOTAL_TIMEOUT_MS` | 900000 | 300000-1800000 | 9 计划总超时 |
| `MINIMAL_PLAN_SUBSET` | [scope,schedule,quality,risk,stakeholder_engagement] | — | 精简档固定子集 |
| `TOGAF_D_WAIT_TIMEOUT_MS` | 900000 | 300000-1800000 | 等 TOGAF D 超时 |

---

*— L2-04 详细定义 R6 上半完 —*

---

## 12. L2-05 · TOGAF ADM 架构生产器（S2） 详细定义

### 12.1 职责 + 锚定

**一句话职责**：S2 规划阶段的"架构师角色" —— 按 TOGAF ADM 的 A→B→C→D 顺序生成架构愿景/业务架构/信息系统架构/技术架构四份文档 + 每个关键决策配套 ADR（架构决策记录），完成后广播 `togaf_ready` 事件，中间态 `togaf_d_ready` 提前通知 L2-04 解除其阻塞。

**上游锚定**：
- Goal §2.5："S2 TOGAF ADM A-D"
- scope §5.2.6 必须义务 5："架构产出齐全"
- businessFlow BF-S2-06（TOGAF A-D）/ BF-S2-08（架构评审委托）

**下游服务**：L2-04（togaf_d_ready 解其阻塞）/ L2-01（togaf_ready 累积开 S2 Gate）/ L1-04（TDD 蓝图依据）

---

### 12.2 输入 / 输出

| 类别 | 内容 | 来源 / 去向 |
|---|---|---|
| **触发** | IC-L2-01(stage=S2) + 4_pieces_ready 事件 | L2-01 / 订阅 |
| **输入依赖** | 4 件套 + charter + scope_plan (from L2-04) + KB 历史架构 | 读磁盘 + KB |
| **输出产出物** | docs/architecture/A-vision.md / B-business.md / C-data.md / C-application.md / D-technology.md + docs/adr/ADR-*.md (≥ 10 条) | 本地文件 |
| **输出事件** | A_ready / B_ready / C_ready / D_ready / togaf_ready（ADR 齐也归在 D_ready 前）| 事件总线 |
| **委托** | IC-05 → L1-05 architecture-reviewer 子 Agent（C 阶段评审） | 子 Agent |

---

### 12.3 边界

#### In-scope
1. A→B→C→D 顺序串行生成
2. 每阶段产出主文档 + 配套 ADR
3. C 阶段拆成 C-data + C-application 两份
4. 委托 architecture-reviewer 子 Agent 做 C 评审
5. togaf_d_ready 提前信号（用于 L2-04 解阻塞）
6. ADR 数量硬底（≥ 10 条完整档 / ≥ 5 条精简档）

#### Out-of-scope
- ❌ 不做 PMP 9 计划 → L2-04
- ❌ 不做 4 件套 → L2-03
- ❌ 不做 WBS / TDD 蓝图 → L1-03 / L1-04
- ❌ 不做实际代码实现 → S4 阶段

#### 边界规则
- A→B→C→D 顺序不可变（ADM 硬约束）
- 精简档下跳 B + C 简化（只出 A + D + 合并 C 为概要）
- ADR 的格式固定（title + status + context + decision + consequences + alternatives）

---

### 12.4 约束

#### 业务模式
- **PM-01 methodology-paced**：TOGAF ADM 是 S2 与 PMP 并列的另一条产出线
- **PM-13 合规可裁剪**：精简档下 TOGAF A + D 简化版

#### 硬约束
1. ADR 最小数量：完整档 ≥ 10 条 / 精简档 ≥ 5 条（硬拦）
2. D-technology 必须包含技术栈约束（从 Goal § 硬约束继承）
3. C 阶段必须走 architecture-reviewer 评审（质量门禁）
4. A → B → C → D 顺序硬约束
5. 单阶段 ≤ 5min / 总 ≤ 20min（完整档）

#### 性能
- A ≤ 3min / B ≤ 3min / C ≤ 5min / D ≤ 5min
- 总（完整）≤ 20min
- 总（精简）≤ 10min

---

### 12.5 🚫 禁止行为

- 🚫 禁止打乱 A→B→C→D 顺序
- 🚫 禁止少于最小 ADR 数量
- 🚫 禁止在 C 阶段跳过 architecture-reviewer 评审
- 🚫 禁止 D 阶段不包含技术栈约束说明
- 🚫 禁止不产 ADR 的 "重大决策"（凡决策必 ADR）

---

### 12.6 ✅ 必须职责

- ✅ **必须**按 ADM A→B→C→D 顺序生成
- ✅ **必须**每阶段完成发对应 ready 事件
- ✅ **必须**D 完成后发 togaf_d_ready（解 L2-04 Group 2 阻塞）
- ✅ **必须**ADR 数量达标 + 格式合规
- ✅ **必须**C 阶段委托 architecture-reviewer 子 Agent
- ✅ **必须**总完成发 togaf_ready（含 ADR 齐全校验）
- ✅ **必须**A-D 每份文档带引用链（B 引 A / C 引 B / D 引 C）

---

### 12.7 🔧 可选功能

- 🔧 架构图自动生成（从 YAML 描述产 mermaid / plantuml）
- 🔧 ADR 影响矩阵（可视化 ADR 间的级联影响）
- 🔧 架构质量评分（用 KB 历史 ADR 比较给出建议）

---

### 12.8 与其他 L2 / L1 交互

| IC | 对方 | 何时 | 字段 |
|---|---|---|---|
| IC-L2-02 request_template | L2-07 | 每阶段 / ADR 生成 | `{doc_type: togaf_a/b/c/d/adr}` |
| IC-L2-06 record_audit | L1-01 L2-05 | 每阶段 / ADR | 标准 |
| IC-L2-07 kb_read | L1-06 | 类似项目架构模式 | `{kind: architecture_pattern}` |
| IC-05 delegate_subagent | L1-05 | C 评审 | `{subagent: architecture-reviewer}` |
| 事件发布 | L1-09 | A_ready/B_ready/C_ready/D_ready/togaf_d_ready/togaf_ready | — |

---

### 12.9 🎯 交付验证大纲

| # | 场景 | 验证点 |
|---|---|---|
| P1 | 正常触发 → A→B→C→D 顺序产 | 顺序 |
| P2 | C 阶段触发 architecture-reviewer 子 Agent | 委托 |
| P3 | D 完成发 togaf_d_ready | 中间信号 |
| P4 | 全部完成发 togaf_ready | 总事件 |
| P5 | ADR 数量 ≥ 10 | 硬底 |
| P6 | 精简档 → A + D 简化，ADR ≥ 5 | 裁剪 |
| N1 | 打乱顺序调 B → 拒绝（A 未完成）| 顺序约束 |
| N2 | ADR 数量不达标 → togaf_ready 不发 + 审计违规 | 数量约束 |
| N3 | D 不含技术栈约束 → 自检失败 | 内容约束 |
| I1 | S2 端到端 togaf + pmp 交织：L2-04 等 L2-05 D | 协同 |

**性能**：完整 ≤ 20min，精简 ≤ 10min。

---

### 12.10 L3 · TOGAF ADM 架构生产器实现设计

#### 12.10.1 顺序状态机

```
[IDLE]
  │ IC-L2-01 triggered (stage=S2)
  │ 等 4_pieces_ready
  ▼
[A_VISION]
  │ request_template(togaf_a) + LLM + 用 KB 历史 vision 模式
  │ 产 A-vision.md + 若决策 → ADR-A*
  │ emit A_ready
  ▼
[B_BUSINESS]
  │ 依赖 A + 4 件套
  │ 产 B-business.md + ADR-B*
  │ emit B_ready
  ▼
[C_DATA_APPLICATION]
  │ 依赖 B
  │ 产 C-data.md + C-application.md + ADR-C*
  │ 委托 architecture-reviewer → 评审报告
  │ 若评审 reject → retry (≤ 1 次)
  │ emit C_ready
  ▼
[D_TECHNOLOGY]
  │ 依赖 C + 技术栈约束 (来自 Goal §)
  │ 产 D-technology.md + ADR-D* (通常最多)
  │ emit D_ready
  │ emit togaf_d_ready  ← 提前信号给 L2-04 Group 2
  ▼
[VALIDATE_ADR_COUNT]
  │ 数 ADR 总数
  │ ├── 完整档 ≥ 10 且 D 有技术栈 → emit togaf_ready
  │ └── 不达标 → state=FAILED + 审计
  ▼
[DONE]

精简档:
  [A_VISION_MIN] → [C_COMBINED_MIN] → [D_TECHNOLOGY_MIN] → emit togaf_ready (ADR ≥ 5)
```

#### 12.10.2 四阶段内容大纲

**A · Architecture Vision（愿景）**：
- 项目架构定位（问题空间 / 解决空间）
- 高层价值主张
- 核心干系人 concerns
- 假设与约束
- 成功判据

**B · Business Architecture（业务架构）**：
- 业务能力地图
- 业务流程图
- 组织 / 角色 / 职责
- 业务数据模型（概念级）

**C · Information Systems Architecture**（拆两份）：
- **C-data**：数据模型 / 存储方案 / 数据流 / 数据安全分级
- **C-application**：应用组件 / 服务拆分 / 通讯协议 / API 设计

**D · Technology Architecture（技术架构）**：
- 技术栈选型（含替代方案比较）
- 运行时拓扑（部署视图）
- 基础设施依赖
- NFR 实现方案（性能 / 可用性 / 扩展）
- 安全技术方案

#### 12.10.3 ADR 模板

```yaml
---
adr_id: ADR-{letter}-{seq}   # e.g. ADR-D-07
status: proposed | accepted | deprecated | superseded
stage: A | B | C | D
created_at: iso
parent_adr: ADR-X-Y | null   # 若 superseded
---

# {标题}

## Context
<为什么需要这个决策，背景、问题>

## Decision
<决定做什么>

## Consequences
### 正面
- ...
### 负面
- ...

## Alternatives Considered
- Alt 1: ...
  - 不选原因: ...
- Alt 2: ...
  - 不选原因: ...

## Related
- ADR-X-Y (引用 / 依赖)
```

#### 12.10.4 C 阶段评审协议

```
function review_c_architecture(c_data_md, c_application_md):
    report = delegate_subagent(
        subagent='architecture-reviewer',
        goal=f'Review C architecture for consistency, completeness, and quality',
        inputs={
            'c_data': c_data_md,
            'c_application': c_application_md,
            'upstream_a': read('A-vision.md'),
            'upstream_b': read('B-business.md'),
            '4_pieces': read_all_4_pieces()
        }
    )
    # 评审报告格式
    # { verdict: 'pass' | 'needs_rework', findings: [str], recommendations: [str] }
    if report.verdict == 'needs_rework':
        # 基于 findings 重做
        retry_c_with_feedback(report.findings)
        return review_c_architecture(...)  # recursion ≤ 1
    return report
```

#### 12.10.5 核心产品逻辑流程图

**图 1 · ADM A→B→C→D 顺序产出**

```
[4_pieces_ready event]
         ↓
    A phase
  A-vision.md + ADR-A1..
         ↓
    emit A_ready
         ↓
    B phase (deps A + 4件套)
  B-business.md + ADR-B*
         ↓
    emit B_ready
         ↓
    C phase (deps B)
  C-data.md + C-application.md + ADR-C*
         ↓
  delegate architecture-reviewer
         ↓
  review pass? ─NO─→ retry with feedback (≤ 1)
         ↓ YES
    emit C_ready
         ↓
    D phase (deps C + Goal 技术栈约束)
  D-technology.md + ADR-D* (通常多)
         ↓
    emit D_ready
    emit togaf_d_ready  ← 提前给 L2-04
         ↓
  ADR 数量 check
   ├── 完整档 ≥ 10 → PASS
   └── 不达标 → FAILED + 审计
         ↓
    emit togaf_ready
```

#### 12.10.6 配置参数

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `ADR_MIN_FULL` | 10 | 5-30 | 完整档 ADR 最低数 |
| `ADR_MIN_MINIMAL` | 5 | 3-10 | 精简档 ADR 最低数 |
| `C_REVIEW_ENABLED` | true | true-only | C 阶段必评审（硬拦）|
| `C_REVIEW_MAX_RETRY` | 1 | 0-3 | 评审 rework 最大次数 |
| `PHASE_TIMEOUT_MS` | 300000 | 60000-900000 | 单阶段超时 |
| `TOGAF_TOTAL_TIMEOUT_MS` | 1200000 | 600000-3600000 | 完整总超时 |
| `ADR_TEMPLATE_REQUIRED_FIELDS` | [context,decision,consequences,alternatives] | — | ADR 必填 |

---

*— L2-05 详细定义 R6 下半完（L2-04+L2-05 合并一轮，约 450 行）*

---

## 13. L2-06 · 收尾阶段执行器（S7） 详细定义

### 13.1 职责 + 锚定

**一句话职责**：S7 收尾阶段的"项目经理交付角色" —— 在 L1-04 Quality Loop S5 PASS 后接手，按"交付包打包 → retro 生成 → archive 归档 → KB 晋升 → 最终验收 Gate"5 步串行执行，是整个项目的"最后一公里"。

**上游锚定**：
- Goal §2.7："S7 收尾"
- scope §5.2.6 必须义务 6："retro + archive + KB 晋升全执行"
- businessFlow BF-S7-01（交付汇总）/ BF-S7-02（retro）/ BF-S7-03（archive）/ BF-S7-04（KB 晋升）/ BF-S7-05（最终 Gate）

**下游服务**：L1-05（委托 retro-generator / failure-archive-writer 子 Agent）/ L1-06（IC-08 kb_promote）/ L2-01（`delivery_bundled` → 开 S7 Gate）

---

### 13.2 输入 / 输出

| 类别 | 内容 | 来源 / 去向 |
|---|---|---|
| **触发** | IC-L2-01(stage=S7) + state=RETRO_CLOSE 信号（L1-04 S5 PASS 后）| L2-01 / L1-01 |
| **输入依赖** | 代码 commit / PMP 9 计划 / TOGAF A-D + ADR / 4 件套 / TDD 蓝图 / verifier_reports / event 总线历史 / 决策链 | 全局读 |
| **输出产出物** | delivery/<project_id>/ 目录（交付包）/ retros/<project_id>.md / failure-archive.jsonl 一条 / KB 新条目 | 本地 + KB |
| **输出事件** | delivery_bundled → retro_ready → archive_written → kb_promotion_done | 事件总线 |

---

### 13.3 边界

#### In-scope
1. 交付物汇总打包（遍历各类产出物 → 统一交付目录）
2. delivery-manifest.md 生成（交付物索引）
3. 委托 retro-generator 子 Agent 产 11 项 retro
4. 委托 failure-archive-writer 写归档（无论成败）
5. KB 晋升（候选条目 → 正式 KB，按 observed_count ≥ 3 或用户批准）
6. 最终 Gate 事件发布（让 L2-01 开 S7 Gate）

#### Out-of-scope
- ❌ 不自写 retro 内容 → 委托 L1-05
- ❌ 不自写 archive 内容 → 委托 L1-05
- ❌ 不做 KB 实际存储 → L1-06
- ❌ 不做代码修复 → S4/S5 阶段

#### 边界规则
- 即便项目失败（state=FAILED_TERMINAL）也必执行 archive + retro（闭环义务）
- retro + archive 必走子 Agent 委托（职责隔离）
- KB 晋升是"候选 → 正式"的确认动作，不创建新知识

---

### 13.4 约束

#### 业务模式
- **PM-11 失败也要闭环**：任何终态（SUCCESS / FAILED）都必走 retro + archive
- **PM-12 知识晋升**：KB 候选 → 正式需要 observed_count 或用户批准

#### 硬约束
1. 5 步串行顺序不可乱
2. retro 必含 11 项模板段（不可减）
3. archive 必写 failure-archive.jsonl 一条（即便成功）
4. 交付包必含 delivery-manifest.md
5. KB 晋升数量无下限（可以 0 条），但必须走流程

#### 性能
- 交付包打包 ≤ 2min
- retro 生成 ≤ 5min（委托子 Agent）
- archive 写 ≤ 10s
- KB 晋升 ≤ 30s/条
- S7 总 ≤ 10min

---

### 13.5 🚫 禁止行为

- 🚫 禁止失败项目跳过 retro / archive
- 🚫 禁止自写 retro 内容（必须委托子 Agent）
- 🚫 禁止 5 步乱序
- 🚫 禁止 retro 少于 11 项模板段
- 🚫 禁止无 delivery-manifest 的交付包

---

### 13.6 ✅ 必须职责

- ✅ **必须**按顺序执行 5 步
- ✅ **必须**委托 L1-05 的 retro-generator + failure-archive-writer
- ✅ **必须**KB 晋升调 L1-06 IC-08
- ✅ **必须**每步完成发对应事件
- ✅ **必须**失败项目也闭环（终态自动进 S7）
- ✅ **必须**delivery-manifest 索引所有交付物路径 + hash

---

### 13.7 🔧 可选功能

- 🔧 交付包格式化：生成 zip / tar.gz 便于分发
- 🔧 retro 双语输出（中/英）
- 🔧 KB 晋升建议排序（按置信度优先推送）

---

### 13.8 与其他 L2 / L1 交互

| IC | 对方 | 何时 | 字段 |
|---|---|---|---|
| IC-L2-08 delegate_subagent | L1-05 | retro + archive 委托 | `{subagent: retro-generator/failure-archive-writer}` |
| IC-08 kb_promote | L1-06 | 晋升候选条目 | `{candidate_id, evidence}` |
| IC-L2-06 record_audit | L1-01 L2-05 | 每步 | 标准 |
| 事件发布 | L1-09 | delivery_bundled/retro_ready/archive_written/kb_promotion_done | — |

---

### 13.9 🎯 交付验证大纲

| # | 场景 | 验证点 |
|---|---|---|
| P1 | S5 PASS → S7 自动触发 → 5 步完成 | 端到端 |
| P2 | 交付包内含 delivery-manifest.md | 索引必有 |
| P3 | retro 含 11 项段 | 完整性 |
| P4 | archive 写 failure-archive.jsonl 1 条 | 闭环 |
| P5 | KB 候选 observed_count ≥ 3 → 自动晋升 | 晋升规则 |
| N1 | 项目 FAILED → 也走 retro + archive | 闭环义务 |
| N2 | 跳过 archive 直发 kb_promote → 拒绝 | 顺序约束 |
| I1 | S7 端到端 + S7 Gate 推送用户 Go → state=CLOSED | 跨 L2 |

**性能**：S7 总 ≤ 10min。

---

### 13.10 L3 · S7 收尾实现设计

#### 13.10.1 5 步状态机

```
[IDLE]
  │ IC-L2-01 triggered (stage=S7) or state=RETRO_CLOSE
  ▼
[DELIVERY_BUNDLE]
  │ 遍历代码 commit / 9 计划 / TOGAF / 4 件套 / TDD 蓝图 / verifier reports
  │ 拷贝到 delivery/<pid>/
  │ 生成 delivery-manifest.md (含 hash + 时间线)
  │ emit delivery_bundled
  ▼
[RETRO_GEN]
  │ delegate_subagent('retro-generator', 11 项模板)
  │ 子 Agent 读 event bus 历史 + 决策链
  │ 产 retros/<pid>.md
  │ emit retro_ready
  ▼
[ARCHIVE_WRITE]
  │ delegate_subagent('failure-archive-writer')
  │ 子 Agent 写 failure-archive.jsonl 一条 (无论成败)
  │ emit archive_written
  ▼
[KB_PROMOTE]
  │ 读本 session 的 KB 候选 (来自 L1-06 observation 累积)
  │ 对每个候选:
  │   if observed_count >= 3 → 自动晋升
  │   else → 推用户批准（UI 列表）
  │ IC-08 kb_promote
  │ emit kb_promotion_done
  ▼
[FINAL_GATE_REQUEST]
  │ 所有产出齐全信号发完 → L2-01 累积到 S7
  │ 等 L2-01 推 S7 Gate 给用户
  ▼
[WAITING_GATE]
  │ 阻塞 state 转 CLOSED
  ▼
[DONE]（用户 Go 后 L2-01 发 state_transition → CLOSED）
```

#### 13.10.2 delivery-manifest 结构

```yaml
---
manifest_id: delivery-{pid}-{ts}
project_id: p_xxx
generated_at: iso
total_artifacts: 42
---

# 交付清单

## 代码
- git_commit: sha256:abc
- branch: main
- tag: v1.0.0

## PMP 9 计划
- [scope-plan.md](../planning/scope-plan.md) (hash: ...)
- [schedule-plan.md](...)
- ...

## TOGAF
- [A-vision.md](../architecture/A-vision.md)
- [B-business.md](...)
- [C-data.md](...)
- [C-application.md](...)
- [D-technology.md](...)
- ADR 集（12 条）：
  - [ADR-A-01](../adr/ADR-A-01.md)
  - ...

## 4 件套
- [requirements.md]
- [goals.md]
- [acceptance-criteria.md]
- [quality-standards.md]

## TDD 蓝图
- [master-test-plan.md](../tdd/master-test-plan.md)
- test suites 索引

## 验证报告
- [verifier_report_s5.md]
- 质量指标：通过率 95% / 覆盖率 85% / 性能 P99 ≤ 450ms

## retro
- [retros/p-xxx.md]
```

#### 13.10.3 retro 11 项模板（委托规范）

```yaml
# 传给 retro-generator 子 Agent 的 contract
retro_contract:
  sections_required:
    1. 项目概览
    2. 目标达成度（对 charter.success_criteria / AC 逐项评分）
    3. 关键决策复盘（ADR 视角）
    4. 困难与突破
    5. 成本回顾（计划 vs 实际）
    6. 进度回顾（Gantt 实际 vs 计划）
    7. 质量指标汇总
    8. 沟通 & 干系人管理复盘
    9. 风险事件复盘
    10. 知识沉淀（可晋升 KB 候选）
    11. 后续行动项（open items）
  min_word_count: 2000
  evidence_required: event_bus_history + decision_chain
```

#### 13.10.4 KB 晋升算法

```
function promote_kb_candidates(project_id):
    candidates = kb_read(L1-06, kind='candidate', filter={project_id, session_recent=True})
    promoted = []
    for c in candidates:
        if c.observed_count >= 3:
            # 自动晋升
            ic_08_kb_promote(c.id, evidence='observed_count>=3')
            promoted.append(c)
        elif c.user_approved:
            ic_08_kb_promote(c.id, evidence='user_approved_in_ui')
            promoted.append(c)
        else:
            # 保留候选，推给用户 UI 列表（可选）
            push_candidate_for_user_review(c)
    return promoted
```

#### 13.10.5 失败路径处理

```
if project_state.final_state == 'FAILED_TERMINAL':
    # 仍然执行 S7，但 delivery_bundle 特别标注
    delivery_manifest.status = 'FAILED'
    delivery_manifest.failure_reason = project_state.last_error
    # retro 强调失败原因分析（11 项照常）
    retro_contract.focus = 'failure_root_cause'
    # archive 写 jsonl 时 status='failed'
    archive_entry.status = 'failed'
    # KB 晋升只推"失败模式"候选
```

#### 13.10.6 配置参数

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `S7_TOTAL_TIMEOUT_MS` | 600000 | 300000-1800000 | S7 总超时 |
| `RETRO_SECTIONS_MIN` | 11 | 11-11 | 硬锁（不可减）|
| `KB_AUTO_PROMOTE_THRESHOLD` | 3 | 2-10 | observed_count 自动晋升阈值 |
| `DELIVERY_MANIFEST_REQUIRED` | true | true-only | 硬拦 |
| `ARCHIVE_ON_FAILURE_REQUIRED` | true | true-only | 失败也闭环 |

---

*— L2-06 详细定义 R7 上半完（约 300 行）—*

---

## 14. L2-07 · 产出物模板引擎（横切） 详细定义

### 14.1 职责 + 锚定

**一句话职责**：L1-02 的"统一模板中台" —— 为 L2-02/03/04/05/06 的每类产出物提供模板（charter / stakeholders / requirements / goals / AC / quality / 9 计划 / TOGAF A-D / ADR / retro 等共 20+ 类型），做裁剪档映射（full / minimal / custom）+ 参数化填充 + 版本追踪，保证"同一类产出物在不同项目间格式一致"。

**上游锚定**：
- Goal §3.4："产出物统一模板驱动"
- scope §5.2.6 必须义务 7："产出物模板一致"
- businessFlow BF-X-06（横切 · 产出物模板驱动）
- PM-13 合规可裁剪（本 L2 是裁剪能力的载体）

**下游服务**：L2-02/03/04/05/06 全部（横切服务）/ L2-01（裁剪档查询）

---

### 14.2 输入 / 输出

| 类别 | 内容 | 来源 / 去向 |
|---|---|---|
| **输入 请求（模板获取）** | IC-L2-02 request_template(doc_type, trim_level, variables) | L2-02/03/04/05/06 |
| **输入 请求（裁剪查询）** | IC-L2-09 query_trim(level) | L2-01 |
| **输入 配置** | templates/*.md（模板文件）+ trim_config.yaml（裁剪规则） | 本地配置目录 |
| **输出 模板主体** | 返回 `{template_body, required_fields, frontmatter_schema}` | 调用方 |
| **输出 启用清单** | 返回 `{enabled_templates: [doc_type]}` | L2-01 |
| **输出 审计** | IC-L2-06 record_audit(actor=L2-07, action=template_served / trim_queried) | L1-01 L2-05 |

---

### 14.3 边界

#### In-scope
1. 模板库管理（加载 / 校验 / 版本）
2. 裁剪档映射（3 档：full / minimal / custom）
3. 模板参数化（变量替换 + 条件块）
4. 模板版本管理（每次修改 bump 版本号 + changelog）
5. frontmatter schema 提供（给调用方做填充校验）
6. 模板选择策略（裁剪档决定 enabled_templates 集合）

#### Out-of-scope
- ❌ 不自写产出物内容 → 各 L2
- ❌ 不做 LLM 填充 → 各 L2 调 L1-05 自己填
- ❌ 不做 Gate 控制 → L2-01
- ❌ 不做跨文档引用校验 → 对应 L2（如 L2-03 的 cross_check）

#### 边界规则
- 模板是"结构 + 占位符"，不是"内容"
- 裁剪规则是"声明式"配置（不允许硬编码）
- 同一 doc_type 在不同裁剪档下使用的是"同一模板的不同分支"（template 本身支持 trim 条件块）
- 模板版本 bump 后旧版本保留（便于回滚）

---

### 14.4 约束

#### 业务模式
- **PM-13 合规可裁剪**：本 L2 是此模式的技术实现
- **PM-14 模板统一**：所有产出物走本 L2，禁止各自造轮子

#### 硬约束
1. 所有模板必含 frontmatter（doc_id / doc_type / produced_by / produced_at）
2. 3 档裁剪配置必须覆盖所有 doc_type（不允许某 doc_type 未定义裁剪）
3. 模板版本号强制递增（不可退版）
4. 单次请求返回 ≤ 100ms（作为横切服务）
5. 模板加载在启动时完成（运行时热更新需重载）

#### 性能
- request_template 延迟 ≤ 100ms
- query_trim 延迟 ≤ 50ms
- 模板加载（启动时）≤ 1s
- 支持并发：≥ 50 QPS

---

### 14.5 🚫 禁止行为

- 🚫 禁止各 L2 绕本 L2 自写模板
- 🚫 禁止返回无 frontmatter 的模板
- 🚫 禁止运行时修改模板文件（除非主动调 reload）
- 🚫 禁止 trim_config 对某 doc_type 缺失裁剪映射
- 🚫 禁止返回不存在的 doc_type 的模板（应明确 404）

---

### 14.6 ✅ 必须职责

- ✅ **必须**为所有 L1-02 涉及的产出物类型提供模板（charter / stakeholders / 4 件套 / 9 计划 / TOGAF A-D / ADR / retro / delivery-manifest 等）
- ✅ **必须**3 档裁剪规则完整覆盖
- ✅ **必须**参数化填充（变量 + 条件块）
- ✅ **必须**模板版本 bump + changelog
- ✅ **必须**frontmatter schema 暴露给调用方
- ✅ **必须**查询 / 请求性能达标

---

### 14.7 🔧 可选功能

- 🔧 模板语法校验 CLI（启动前跑）
- 🔧 模板热更新 watch（dev 模式，prod 默认关）
- 🔧 模板 preview 端点（给 UI 看效果）
- 🔧 多语言模板（中 / 英对照）

---

### 14.8 与其他 L2 / L1 交互

**作为被调方**：

| IC | 调用方 | 何时 | 字段 |
|---|---|---|---|
| IC-L2-02 request_template | L2-02/03/04/05/06 | 产出物生成前 | `{doc_type, trim_level, variables: {}}` → `{template_body, required_fields, frontmatter_schema, version}` |
| IC-L2-09 query_trim | L2-01 | 开 Gate 前 / 启动时 | `{level}` → `{enabled_templates: [doc_type]}` |

**作为调用方**：无（本 L2 被动服务）

**横切依赖**：
- 本地配置目录：`.harnessflow/templates/*.md` + `.harnessflow/trim_config.yaml`

---

### 14.9 🎯 交付验证大纲

| # | 场景 | 验证点 |
|---|---|---|
| P1 | request_template(charter, full) → 返回 charter 完整模板 | 基本获取 |
| P2 | request_template(charter, minimal) → 返回 charter 精简模板（同 doc_type，不同分支）| 裁剪 |
| P3 | request_template(unknown_doc_type) → 返回 404 明确错误 | 错误处理 |
| P4 | query_trim(full) → 返回完整档启用清单（全部 20+）| 查询 |
| P5 | query_trim(minimal) → 返回精简档清单（少 6-8 项）| 查询 |
| P6 | 模板含 {{variable}} 参数 → 正确替换 | 参数化 |
| P7 | 模板含 {% if trim=='full' %}...{% endif %} 条件块 → minimal 下跳过 | 条件块 |
| P8 | 修改模板文件 + reload → 新版本生效 + version bump | 版本 |
| N1 | trim_config 缺某 doc_type → 启动失败 | 配置完整性 |
| N2 | 模板无 frontmatter → 启动校验失败 | frontmatter 必备 |
| N3 | 运行时修改模板文件未 reload → 仍返回旧版 | 热更新策略 |
| I1 | 各 L2 端到端调 → 模板正确返回 + L2 填充成功 | 跨 L2 |

**性能**：request ≤ 100ms / query ≤ 50ms / 启动加载 ≤ 1s / QPS ≥ 50。

---

### 14.10 L3 · 产出物模板引擎实现设计

#### 14.10.1 模板库结构

```
.harnessflow/
├── trim_config.yaml              # 裁剪规则
├── templates/
│   ├── charter.md                # 章程模板
│   ├── stakeholders.md
│   ├── requirements.md
│   ├── goals.md
│   ├── acceptance-criteria.md
│   ├── quality-standards.md
│   ├── plans/
│   │   ├── scope-plan.md
│   │   ├── schedule-plan.md
│   │   ├── cost-plan.md
│   │   ├── quality-plan.md
│   │   ├── risk-plan.md
│   │   ├── resource-plan.md
│   │   ├── communication-plan.md
│   │   ├── procurement-plan.md
│   │   └── stakeholder-engagement-plan.md
│   ├── togaf/
│   │   ├── A-vision.md
│   │   ├── B-business.md
│   │   ├── C-data.md
│   │   ├── C-application.md
│   │   ├── D-technology.md
│   │   └── ADR.md
│   ├── retro.md
│   ├── delivery-manifest.md
│   └── versions/                 # 历史版本
│       ├── charter.md.v1
│       ├── charter.md.v2
│       └── ...
└── template-changelog.md         # 所有模板变更日志
```

#### 14.10.2 trim_config.yaml 规范

```yaml
trim_levels:
  full:
    enabled_templates:
      - charter
      - stakeholders
      - requirements
      - goals
      - acceptance_criteria
      - quality_standards
      - scope_plan
      - schedule_plan
      - cost_plan
      - quality_plan
      - risk_plan
      - resource_plan
      - communication_plan
      - procurement_plan
      - stakeholder_engagement_plan
      - A_vision
      - B_business
      - C_data
      - C_application
      - D_technology
      - adr
      - retro
      - delivery_manifest
    # 22 项

  minimal:
    enabled_templates:
      # 4 件套保全 + 5 计划 + TOGAF A+D + ADR + 4 收尾
      - charter
      - stakeholders
      - requirements
      - goals
      - acceptance_criteria
      - quality_standards
      - scope_plan
      - schedule_plan
      - quality_plan
      - risk_plan
      - stakeholder_engagement_plan
      - A_vision
      - D_technology
      - adr
      - retro
      - delivery_manifest
    # 16 项

  custom:
    # 用户在 UI 勾选；本服务动态读用户选择

branch_overrides:
  # 部分模板在 minimal 下用简化分支（同 doc_type 但内部 trim_block 不同）
  togaf/D-technology.md:
    minimal: use_simplified_branch
  retro.md:
    minimal: 6_sections_only   # 11→6 段
```

#### 14.10.3 模板参数化语法

```markdown
<!-- templates/charter.md -->
---
doc_id: {{doc_id}}
doc_type: charter
produced_by: L2-02
produced_at: {{timestamp}}
project_id: {{project_id}}
version: {{template_version}}
---

# {{project_title}} · 章程

## 目的
{{purpose}}

## 范围
### In Scope
{{#each in_scope}}
- {{this}}
{{/each}}

### Out of Scope
{{#each out_of_scope}}
- {{this}}
{{/each}}

{% if trim_level == 'full' %}
## 详细背景
{{detailed_context}}

## 风险详细表
{{#each risks_detailed}}
| {{id}} | {{description}} | {{probability}} | {{impact}} |
{{/each}}
{% else %}
## 简要背景
{{brief_context}}

## 主要风险
{{#each top_risks}}
- {{this}}
{{/each}}
{% endif %}

## 授权
- Approver: {{approver}}
- Escalation path: {{escalation_path}}
```

**参数化规则**：
- `{{var}}` · 变量替换
- `{{#each array}}...{{/each}}` · 数组迭代
- `{% if cond %}...{% else %}...{% endif %}` · 条件块（支持 trim_level 判定）
- 内置变量：`timestamp`, `project_id`, `doc_id`, `template_version`, `trim_level`

#### 14.10.4 模板服务状态机

```
[UNINITIALIZED]
  │ start()
  ▼
[LOADING]
  │ 扫 .harnessflow/templates/*.md
  │ 加载 trim_config.yaml
  │ 校验每个模板 (frontmatter + 语法)
  │ 校验 trim_config 覆盖完整性
  │   ├── FAIL → [INIT_FAILED] → L1-01 启动失败告警
  │   └── PASS → next
  ▼
[READY]
  │ 服务 request_template / query_trim
  │ 若收 reload_signal → 回到 LOADING
  ▼
[RELOADING]
  │ (hot reload, 热更新)
  │ 加载新模板到 shadow cache
  │ 校验 shadow cache 通过后原子切换
  │   ├── FAIL → 保留旧版 + 审计告警
  │   └── PASS → bump version + changelog
  ▼
[READY] (切换后)
```

#### 14.10.5 request_template 流程

```
function request_template(doc_type, trim_level, variables):
    # 1. 校验 doc_type 存在
    if doc_type not in loaded_templates:
        return Error(404, f'doc_type {doc_type} not found')

    # 2. 校验 trim_level 下启用
    enabled = trim_config[trim_level].enabled_templates
    if doc_type not in enabled:
        return Error(403, f'{doc_type} not enabled for trim={trim_level}')

    # 3. 取模板 body
    template = loaded_templates[doc_type]

    # 4. 判断是否用简化分支
    if branch_override := trim_config.branch_overrides.get(doc_type, {}).get(trim_level):
        template = apply_branch(template, branch_override)

    # 5. 注入内置变量
    variables = {
        'timestamp': now_iso(),
        'project_id': variables.get('project_id', 'unknown'),
        'doc_id': f"{doc_type}-{variables['project_id']}-v1",
        'template_version': loaded_templates[doc_type].version,
        'trim_level': trim_level,
        **variables
    }

    # 6. 返回（不填充，由调用方 LLM 填充）
    return {
        'template_body': template.body,
        'required_fields': template.frontmatter_schema.required,
        'frontmatter_schema': template.frontmatter_schema,
        'version': template.version,
        'built_in_variables': variables
    }
```

#### 14.10.6 核心数据结构

```yaml
template:
  doc_type: str
  path: str
  version: str              # e.g. v1.3.2
  body: str                 # raw markdown with {{vars}} and {% if %}
  frontmatter_schema:
    required: [str]
    optional: [str]
    types: {field: type}
  trim_branches:            # 若 doc_type 支持分支
    full: body_full
    minimal: body_minimal
  changelog: [entry]
  loaded_at: iso

trim_config_loaded:
  levels:
    full: {enabled_templates: [str]}
    minimal: {enabled_templates: [str]}
    custom: {enabled_templates: [str]}   # 运行时由用户覆盖
  branch_overrides: {doc_type: {trim: branch_name}}
  version_hash: sha256       # 配置文件 hash，用于变更检测
```

#### 14.10.7 配置参数

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `TEMPLATES_DIR` | `.harnessflow/templates` | path | 模板目录 |
| `TRIM_CONFIG_PATH` | `.harnessflow/trim_config.yaml` | path | 裁剪配置 |
| `HOT_RELOAD_ENABLED` | false | — | dev 模式开 |
| `TEMPLATE_VERSION_STRATEGY` | semver | semver/timestamp | 版本号风格 |
| `REQUEST_TIMEOUT_MS` | 100 | 50-500 | request 超时 |
| `QPS_LIMIT` | 50 | 10-500 | 并发限流（防刷）|
| `FRONTMATTER_REQUIRED_FIELDS` | [doc_id,doc_type,produced_by,produced_at] | — | 每模板必含 |

---

*— L2-07 详细定义 R7 下半完（约 400 行，横切型 L2 粒度）*

---

---

## 15. L1-02 对外 scope §8 IC 契约映射（本 L1 实际承担）

本表列出 L1-02 对 scope §8 中 20 条 IC 契约的实际承担（发起方 or 接收方）+ 内部 L2 承担者。

### 15.1 L1-02 作为发起方的 IC

| scope §8 IC | 内部 L2 承担者 | 触发时机 | 目标 L1 |
|---|---|---|---|
| **IC-01** request_state_transition | L2-01（Gate 通过后 Go 路径）| 用户 Gate 决定 approve → 切下一 state | L1-01 L2-03 |
| **IC-05** delegate_subagent | L2-06（S7 委托 retro-generator / failure-archive-writer）+ L2-05（C 阶段 architecture-reviewer）+ L2-02（澄清 brainstorming）+ L2-03（可选 requirements-clarification）+ L2-04（writing-plans）| S7 收尾 / C 评审 / S1 澄清 / 需求生成等 | L1-05 |
| **IC-06** kb_read | L2-02（章程历史模式）+ L2-03（需求模式）+ L2-04（计划模式）+ L2-05（架构模式） | 各 L2 产出物生成前可选查 KB | L1-06 |
| **IC-08** kb_promote | L2-06（S7 晋升候选 → 正式）| S7 步骤 4 KB 晋升 | L1-06 |
| **IC-09** record_event | 全 L2（每步产出 / Gate / 决定 / 变更都走审计）| 贯穿 | L1-09（经 L1-01 L2-05 汇入）|
| **IC-16** push_stage_gate_card | L2-01（唯一入口）| 阶段产出物齐全 + 裁剪档查过 + 阻塞就位 | L1-10 |
| **IC-19** request_wbs_decomposition | L2-03（S2 Gate 通过 + 4 件套 + TOGAF 齐后由 L2-01 触发，本质仍是 L2-03 的 API 供 L2-01 调）| S2 Gate 通过后 | L1-03 |

### 15.2 L1-02 作为接收方的 IC

| scope §8 IC | 内部 L2 承接者 | 触发时机 | 来源 L1 |
|---|---|---|---|
| **IC-17** user_intervene | L2-01（Gate 决定：approve/reject/request_change）+ L2-01（运行时 change_request 走 ANALYZING 分支）| 用户在 UI 操作 | L1-10 |
| **事件订阅** `system_resumed` | L2-01（bootstrap 恢复未决 Gate）+ L2-02~L2-06（恢复中间态）| 跨 session | L1-09 |
| **事件订阅** `hard_halt_received`（广播态） | L2-01（挂起 Gate 机器） | supervisor 红线 | L1-07（经 L1-01 转发） |
| **事件订阅** `subagent_result` | L2-02/03/04/05/06（委托的子 Agent 回传） | 委托 subagent 完成 | L1-05（经 L1-09 事件总线）|

### 15.3 L1-02 IC 承担总览图

```
                    ┌──────────────────────────────┐
  L1-10 UI  ────IC-17→  L2-01(Stage Gate 控制器)    │
                    │     │                         │
                    │     ├── IC-16 ←── L2-01 ──→ L1-10
                    │     ├── IC-01 ←── L2-01 ──→ L1-01 L2-03
                    │     └── IC-19 ←── L2-03 ──→ L1-03
                    │                               │
                    │  L2-02~L2-06:                  │
                    │   ├── IC-05 → L1-05（多处委托）│
                    │   ├── IC-06 → L1-06（多处查 KB）│
                    │   └── IC-09 → L1-09（全审计）  │
                    │                               │
                    │  L2-06 (S7):                   │
                    │   └── IC-08 → L1-06（KB 晋升） │
                    └──────────────────────────────┘
```

### 15.4 未承担的 IC

scope §8 中 L1-02 明确**不承担**的契约（避免越界）：

| scope §8 IC | 所属 L1 | 说明 |
|---|---|---|
| IC-02 tick (决策循环) | L1-01 | 本 L1 不发 tick |
| IC-03 dispatch_wbs | L1-03 | 本 L1 只触发 wbs_decomposition, 不管内部调度 |
| IC-04 request_tdd | L1-04 | 本 L1 不做 TDD |
| IC-07 acquire_lock | L1-09 | 本 L1 无锁 |
| IC-10 forward_supervisor_event | L1-07 | supervisor 本 L1 不 forward |
| IC-11 multimodal_pipeline | L1-08 | 本 L1 不处理 multimodal |
| IC-12 resilience | L1-09 | 本 L1 不做 resilience |
| IC-13 skill_dispatch (底层) | L1-05 | 本 L1 是通过 IC-05 调用 skill，不做 dispatch 本身 |
| IC-14 progress_stream | L1-10 | 本 L1 不做 progress stream |
| IC-15 request_hard_halt | L1-07 | 本 L1 只接收 halt 广播 |
| IC-18 verify_artifact | L1-04 | 本 L1 不做 verifier |
| IC-20 retrieve_kb (search) | L1-06 | 本 L1 只 read/promote, 不 search |

---

## 16. 本 L1 retro 位点

**占位说明**：
L1-02 实现完成 + 集成测试通过后，按 11 项 retro 模板撰写本 L1 的 retro（存入 `retros/L1-02.md`）。

**11 项模板锚定**（同 L1-01 §15.1）：

1. **本 L1 目标达成度**：PMP + TOGAF 7 阶段编排是否全实现 + Stage Gate 4 次是否正常
2. **与 scope §5.2 的契合度**：禁止行为清单 / 必须义务清单 / 边界是否严守
3. **关键决策复盘**：各 L2 切分决定 / Stage Gate 打包协议设计 / 裁剪档实现方式 等
4. **困难与突破**：TOGAF D 与 PMP 质量 / 风险计划的依赖等待协调 / change_request 影响面分析算法
5. **成本回顾**：L1-02 开发总耗时 / 子 Agent 委托次数 / 模板库维护成本
6. **进度回顾**：7 个 L2 的实际工作量 vs 估算（L2-01/03 最重，L2-02/06 最轻）
7. **质量指标汇总**：单测覆盖率 / 集成测试通过率 / 性能指标达标情况（Gate 推送延迟 / 影响面分析延迟）
8. **沟通 & 干系人**：本 L1 对 L1-10 UI 的依赖（Gate 卡片 UX）协同情况
9. **风险事件**：无 Gate 超时/自动放行的硬禁用是否被尝试绕过
10. **知识沉淀**：ADR-L1-02-* 累积条目 / 模板库沉淀的产出物模式（可晋升 KB 候选）
11. **后续行动项**：L1-02 后续 v1.1 / v2.0 的增强方向（如多项目多 Gate 并发 / 协作签字）

---

## 附录 A · 术语（L1-02 本地）

| 术语 | 含义 |
|---|---|
| **4 件套** | 需求 / 目标 / 验收标准 / 质量标准 4 份文档（S2 Gate 硬性产出） |
| **9 计划** | PMP 5 过程组 10 知识领域中"规划过程组"产出的 9 份计划 |
| **TOGAF ADM A-D** | Architecture Development Method 的 A 愿景 / B 业务 / C 信息系统 / D 技术 4 阶段 |
| **ADR** | Architecture Decision Record 架构决策记录 |
| **Stage Gate** | 阶段门：S1/S2/S3/S7 末的强制用户 Go/No-Go 检查点 |
| **artifacts_bundle** | Gate 卡片里打包的产出物清单 + 预览 |
| **trim_level** | 裁剪档：full / minimal / custom |
| **change_request** | 用户在 Gate 或进行中提出的变更请求 |
| **4_pieces_ready** | 4 件套齐全事件（触发下游消费）|
| **9_plans_ready** | 9 计划齐全事件 |
| **togaf_ready** | TOGAF 架构齐全事件 |

---

## 附录 B · businessFlow BF 映射

| L2 | 聚合的 BF |
|---|---|
| L2-01 | BF-S1-04 / BF-S2-09 / BF-S3-05 / BF-S7-05（4 Gate）+ BF-L3-10（方法论驱动） |
| L2-02 | BF-S1-01（澄清）+ BF-S1-02（章程）+ BF-S1-03（干系人） |
| L2-03 | BF-S2-01/02/03/04（4 件套各一） |
| L2-04 | BF-S2-05（9 计划） |
| L2-05 | BF-S2-06（TOGAF A-D）+ BF-S2-08（架构评审委托） |
| L2-06 | BF-S7-01（交付汇总）+ BF-S7-02（retro）+ BF-S7-03（archive）+ BF-S7-04（KB 晋升） |
| L2-07 | BF-X-06（产出物模板驱动）横切 |

---

## 附录 C · IC-L2 字段示例

> 本轮仅 IC-L2-01 + IC-L2-03 示例，其他在各 L2 详细定义时给出完整 schema。

```yaml
# IC-L2-01 trigger_stage_production 调用示例
call:
  method: trigger_stage_production
  caller: L2-01
  callee: L2-02  # 或 L2-03/04/05/06
  params:
    stage: "S1"           # S1 / S2 / S7
    context:
      project_id: "p-xxx"
      goal_anchor_hash: "sha256..."
      task_board_snapshot_ref: "ts_XXX"
    trim_level: "full"    # full / minimal / custom
  expected_return:
    ack:
      started_at: "2026-04-20T..."
      estimated_duration_ms: 300000

# IC-L2-03 push_stage_gate_card 调用示例
call:
  method: push_stage_gate_card
  caller: L2-01
  callee: L1-10 (via IC-16)
  params:
    gate_id: "gate_S2_end"
    stage_from: "S2"
    stage_to: "S3"
    artifacts_bundle:
      - path: "docs/planning/requirements.md"
        type: "requirements"
        status: "ready"
        preview_url: "http://localhost:8765/preview?path=..."
      - path: "docs/planning/goals.md"
        type: "goals"
        status: "ready"
      # ... 共 7 组产出物
    required_decisions: ["approve", "reject", "request_change"]
  expected_return:
    decision:
      gate_id: "gate_S2_end"
      user_decision: "approve"  # or reject / request_change
      decided_at: "2026-04-20T..."
      deciding_user: "zhongtianyi"
      change_requests: []  # 若 request_change 则非空
```

---

*— L1-02 PRD v0.1 骨架轮完（R1 brainstorming + R2 落盘合一）· 等待下一轮 L2 详细 —*
