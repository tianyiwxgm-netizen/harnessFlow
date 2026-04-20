---
doc_id: prd-project-model-v1.0
doc_type: domain-model
parent_doc:
  - HarnessFlowGoal.md
  - docs/2-prd/L0/scope.md
  - docs/2-prd/L0/businessFlow.md
version: v1.0
status: draft
author: mixed
created_at: 2026-04-20
updated_at: 2026-04-20
traceability:
  goal_anchor: HarnessFlowGoal.md（新增"全局灵魂"概念节）
  scope: 新增 PM-14 · project-id-as-root（跨 L1 贯穿）
  business_flow: 新增 BF-X-10（project 生命周期横切）
consumer:
  - 10 个 L1 PRD（全部需在 §X.2 I/O / §X.8 交互中补 project_id 字段要求）
  - flowOutInput.md（I/O 规范需在 ITTO 中加 project_id 上下文要求）
  - docs/3-1-Solution-Technical/project-model/（技术方案阶段实现）
---

# HarnessFlow 项目域模型（Project Domain Model）

> **地位**：本文档是 HarnessFlow 的**架构骨干**文档之一，与 `HarnessFlowGoal.md` / `scope.md` / `businessFlow.md` / `flowOutInput.md` 并列。
> **严格遵循**：所有 L1 PRD 都必须遵循本文档定义的 `harnessFlowProjectId` 契约。违反者回头改 L1 PRD，不改本文档。
> **性质**：产品级域模型（what）+ 概念级规则。具体 ID 生成算法 / 目录实现 / 锁粒度等技术细节在 `docs/3-1-Solution-Technical/project-model/`。

---

## 0. 撰写进度

- [x] §1 定位与战略意义
- [x] §2 概念定义
- [x] §3 ID 属性要求（产品级）
- [x] §4 项目生命周期
- [x] §5 项目主状态机
- [x] §6 "所有物"模型（project_id 是什么的根）
- [x] §7 多会话隔离规则
- [x] §8 项目级持久化根（概念级目录模型）
- [x] §9 与 10 个 L1 的关系矩阵
- [x] §10 IC 契约中 project_id 必须出现的位置
- [x] §11 多项目并发规则
- [x] §12 新增业务模式 PM-14 · project-id-as-root
- [x] §13 对 Goal / scope / businessFlow / L1 PRD 的修补建议
- [x] §14 验收大纲
- [x] 附录 A 术语
- [x] 附录 B 命名规则示例

---

## 1. 定位与战略意义

### 1.1 一句话定义

**`harnessFlowProjectId` 是 HarnessFlow 每次承接一个"超大软件项目"时生成的全局唯一标识 —— 它是系统的"灵魂"**，贯穿项目从 S1 启动到 S7 交付的全生命周期，承载**所有运行数据 / 决策记录 / 产出物 / 任务 / 测试 / 监督事件 / KB**，并作为**多会话 / 多项目并发时的隔离边界键**。

### 1.2 为什么必须有这个概念

HarnessFlow 作为"AI 项目经理 + 架构师"，同一用户环境下可能：

1. **时间维度**：同一用户先后做多个项目（A 项目做完后做 B 项目），它们的产出物 / KB / retro 必须**不互相污染**
2. **并发维度**：同一用户可能同时挂起 A、B 两个项目（未来形态 V2+）
3. **会话维度**：Claude Code 会话可能中断、重启、切换设备，跨 session 恢复必须**精确回到某个项目的某个状态**，不能恢复错对象
4. **可审计维度**：retro / archive / failure-archive.jsonl 按项目检索（"项目 A 历史上这个阶段怎么失败过？"）必须按 `project_id` 过滤，不能跨项目混淆
5. **可分享维度**：交付包（delivery/ 目录）按项目整体输出给用户，必须自成闭包，不漏到别的项目

**若缺失此概念**，所有产出物 / 事件 / KB 全部"扁平"堆在 HarnessFlow 的工作目录根部，多项目一混，系统的"可追溯"、"可恢复"、"可审计"、"可分享"四大能力**全部坍塌**。

### 1.3 战略地位

| 角色 | 类比 |
|---|---|
| `harnessFlowProjectId` 之于 HarnessFlow | `tenant_id` 之于 SaaS 平台 / `tx_id` 之于数据库事务 / `run_id` 之于 CI 流水线 / `session_id` 之于 Claude 会话 |
| 本文档之于 HarnessFlow | Goal 回答 "为什么做"，scope 回答 "做什么"，本文档回答 "**围绕什么做**" |

---

## 2. 概念定义

### 2.1 是什么

`harnessFlowProjectId` 是：

- **一个全局唯一、不可变、人类可读 + 机器可读双形态的标识符**
- **由 HarnessFlow 在 S1 启动阶段自动生成**（用户可提议名称组件但不能提议 UUID 部分）
- **贯穿项目全生命周期**直至项目归档（CLOSED 终态）
- **所有跨组件通信、持久化、审计的"基底键"**

### 2.2 不是什么

- ❌ **不是**用户账号 ID（单用户环境下无账号概念）
- ❌ **不是**会话 ID（一个 project 可能跨多个 Claude session）
- ❌ **不是**任务 ID / WP ID（它是这些 ID 的**父**）
- ❌ **不是**git 仓库标识（一个 repo 可能被多个 project 使用）
- ❌ **不是**version 号（project 不迭代 version，直接另起新 project）

### 2.3 与其他 ID 的从属关系

```
harnessFlowProjectId (全局根)
  │
  ├── state_machine_id (本 project 的主状态机实例，1:1)
  ├── goal_anchor_hash (本 project 的目标锚定 sha256，1:1)
  ├── charter_id (S1 章程，1:1)
  │
  ├── session_id[] (本 project 涉及的 Claude session 列表，1:N)
  │     │ session 可来自不同设备 / 不同时间
  │     └── tick_id[] (每 session 的 tick 序列)
  │
  ├── gate_id[] (4 次 Stage Gate，≤ N（含 re-open）)
  ├── wp_id[] (WBS 拆出的 Work Package 列表，N)
  │     └── step_id[] (WP 内部步骤)
  │
  ├── wbs_id (本 project 的 WBS 拓扑，1:1)
  ├── tdd_blueprint_id (S3 TDD 蓝图，1:1)
  │     └── test_case_id[] (测试用例，N)
  │
  ├── decision_id[] (所有决策记录，N)
  ├── audit_event_id[] (所有审计事件，N)
  ├── kb_entry_id[] (本 project KB 条目，N，project 层 KB 专属)
  ├── supervisor_event_id[] (supervisor 告警事件，N)
  ├── verifier_report_id[] (S5 验证报告，N)
  └── artifact_id[] (所有产出物路径指针，N · 涵盖 4 件套 / 9 计划 / TOGAF / ADR / retro / 交付包)
```

**关键规则**：除 `session_id` 之外，所有子 ID **仅在本 project 内有意义**；`session_id` 与 project 是"N 个 session 可服务 1 个 project"的关系（跨 session 恢复时多个 session 共同推进同一 project）。

---

## 3. ID 属性要求（产品级）

### 3.1 唯一性

- 全局唯一 · 在本 HarnessFlow 安装的工作目录内不重复
- 跨设备 / 跨用户环境同步时也必须保持全局唯一（未来形态考虑用户维度）

### 3.2 不可变性

- 一经生成 + 锁定，**项目生命周期内绝对不可改**（即便用户想改项目名）
- 若用户想"重命名项目"，本质是用户侧可见字段可改（`project_title`），但 `harnessFlowProjectId` 保持不变

### 3.3 人类可读 + 机器可读双形态

- **机器态**：uuid 后缀，保证唯一性与机器处理
- **人类态**：带人类可读前缀（如项目名的简短 slug），便于用户在 UI 上辨认"这是哪个项目"
- 两态必须能**互推**：给 UI 一个易读名，给系统一个唯一键

### 3.4 可搜索性

- 必须出现在所有事件 / 决策 / 审计记录的**根字段**位置，便于检索
- 所有按 project 过滤的查询（retro / failure-archive / KB）以此为主键

### 3.5 敏感性

- 本身**不含敏感信息**（不是 PII、不含用户账号、不含 git URL）
- 可安全出现在日志、UI、交付包中

**注**：以上是**产品级属性要求**。具体生成算法、长度、字符集、校验方式在 `docs/3-1-Solution-Technical/project-model/id-generation.md`。

---

## 4. 项目生命周期

### 4.1 7 个生命周期阶段（对齐 scope 的 7 阶段）

`harnessFlowProjectId` 的生命周期与 HarnessFlow 的 7 阶段严格对齐：

| 阶段 | project_id 状态 | 关键事件 |
|---|---|---|
| **S0 未创建** | 不存在 | 用户未发起任何输入 |
| **S1 启动** | **创建 · 锁定** | 章程 + 干系人 + goal_anchor_hash 锁定时 project_id 同时锁定 |
| **S2 规划** | 活跃 | 4 件套 / 9 计划 / TOGAF 产出挂 project_id |
| **S3 TDD 规划** | 活跃 | TDD 蓝图挂 project_id |
| **S4 执行** | 活跃 | WP commit / 测试 / skill 委托都带 project_id |
| **S5 TDDExe** | 活跃 | verifier 报告挂 project_id |
| **S6 监控** | 活跃 · 受监督 | supervisor 事件流按 project_id 订阅 |
| **S7 收尾** | 活跃 → **归档态** | 交付包 / retro / archive 齐后 project_id 转 ARCHIVED 终态 |
| **CLOSED** | **归档** | 项目完结。project_id 仍存在（供历史查询），但不再接收新事件 |

### 4.2 创建条件（S1 创建点）

**谁创建**：L1-02 L2-02 启动阶段产出器（章程生成后、干系人识别前）

**触发条件**：
- 用户首次输入项目目标
- L1-02 的 S1 阶段进入 `CLARIFYING` 状态之后、`CHARTER_GEN` 之前
- 澄清会话至少完成 1 轮并确认项目意图

**创建成功的验收**：
- ID 被写入**项目根 manifest 文件**（持久化单一事实源）
- 立即发布 `project_created` 事件到事件总线（L1-09）
- 所有后续操作必须携带此 ID

**创建失败**：
- 澄清未通过（3 轮未收敛）→ 不创建 project_id，session 里记录"用户未启动 project"
- 用户取消 → 不创建

### 4.3 激活 / 切换

**激活**：项目 manifest 存在 + state != CLOSED → 此 project 可继续推进

**切换**：
- 单 project 模式（当前 V1）：同一时间只有一个"活跃" project
- 多 project 模式（V2+）：可同时保留多个活跃 project，用户在 L1-10 UI 切换"当前 project"
- 切换时 **所有 tick 的上下文都按切换后的 project_id 路由**

### 4.4 归档（S7 CLOSED）

**何时归档**：
- S7 最终 Gate 通过 → state=CLOSED
- 或用户主动 abandon（异常路径，仍归档记录 status=ABANDONED）

**归档之后**：
- 项目数据 **冷存但不删除**（support retro 查询 + KB 历史挖掘）
- 不再接收新事件（事件总线按 project_id 过滤拒绝）
- UI 可查看但标"归档"
- KB 条目可被 global 层使用（跨项目知识复用）

### 4.5 删除（极少 · 用户主动）

- 只有用户在 UI 显式选"删除项目"时才硬删
- 删除是**强操作 + 强确认**（二次确认 + 影响提示）
- 删除后所有 project 归属数据连带销毁（本项目的 KB 条目 / 审计 / 产出 / 交付包）
- **global 层 KB 中的晋升条目不删**（它们已脱离 project 归属）

---

## 5. 项目主状态机

### 5.1 主状态（project 级别）

`harnessFlowProjectId` 本身有一个**项目级主状态**，与 L1-01 的"决策循环 state"不同（后者是 tick 级）。

```
[NOT_EXIST]
    │ S1 章程 + goal_anchor_hash 锁定时创建
    ▼
[INITIALIZED]
    │ 用户通过 S1 Gate
    ▼
[PLANNING]           ← S2 阶段
    │ 用户通过 S2 Gate
    ▼
[TDD_PLANNING]       ← S3 阶段
    │ 用户通过 S3 Gate
    ▼
[EXECUTING]          ← S4 + S5 + S6 合并态
    │ S5 全 PASS + 所有 WP done
    ▼
[CLOSING]            ← S7 阶段
    │ S7 Gate 最终通过
    ▼
[CLOSED]             ← 归档终态
```

**横切暂停态**：
- **PAUSED**（用户 panic）· 可从任意非终态进入 / 返回
- **HALTED**（supervisor 硬红线）· 可从任意非终态进入 / 返回
- **FAILED_TERMINAL**（极端失败 · 极重度偏差仍无法恢复）· 直接进 CLOSING 做失败闭环

### 5.2 主状态 vs L1-01 决策循环 state 的关系

| 层级 | 含义 | 拥有者 | 粒度 |
|---|---|---|---|
| **project 主状态**（本文档 §5.1） | 项目宏观生命周期 | L1-02 L2-01 Stage Gate 控制器 + L1-09 持久化 | 整个项目 |
| **L1-01 决策循环 state** | 每个 tick 的"当前做什么"微观态 | L1-01 L2-03 状态机编排器 | Tick 级 |

**关系**：`project 主状态 = 一段连续的决策循环 state 段`。例如 project 主状态 `EXECUTING` 期间，L1-01 的 state 会在 `IMPL / TESTING / COMMIT` 间循环；而 project 主状态 `PLANNING` 期间，L1-01 的 state 在 `PLAN_4_PIECES / PLAN_9_PLANS / PLAN_TOGAF` 间循环。

主状态的切换由 L1-02 L2-01（Stage Gate 控制器）独占 —— 只有它能提议"切主状态"。

### 5.3 子状态

每个主状态下有若干子状态，定义归 L1-02 相关 L2 管理，与产出物齐全信号配合判 Gate 时机。子状态具体定义详见 L1-02 PRD §5（L2 间业务流程）。

---

## 6. "所有物"模型：project_id 是什么的根

### 6.1 全部归属清单

以下所有资产 / 状态 / 事件 **必须**归属到一个 `harnessFlowProjectId`：

| 类别 | 具体条目 | 负责 L1 |
|---|---|---|
| **运行数据** | task-board 当前快照 + 历史 state 序列 + tick 历史 | L1-01 + L1-09 |
| **决策数据** | 所有 decision_id 记录 + 决策链 | L1-01 L2-05 审计 |
| **项目章程** | charter.md / stakeholders.md / project_manifest.yaml | L1-02 L2-02 |
| **4 件套** | requirements / goals / acceptance_criteria / quality_standards | L1-02 L2-03 |
| **9 计划** | PMP 9 计划（scope / schedule / cost / quality / resource / communication / risk / procurement / stakeholder_engagement） | L1-02 L2-04 |
| **TOGAF 产出** | A-vision / B-business / C-data / C-application / D-technology + ADR 集 | L1-02 L2-05 |
| **WBS + WP** | wbs.md + 每个 wp_id 的定义 + 拓扑图 | L1-03 全部 |
| **TDD 蓝图** | master-test-plan / dod-expressions / test_case 骨架 / quality-gates / acceptance-checklist | L1-04 S3 L2 |
| **测试用例** | 全量测试代码（tests/generated/*.py） | L1-04 S3 L2 |
| **实现代码** | WP 产出的业务代码（通过 git commit 关联） | L1-04 L1-05 |
| **验证报告** | verifier_reports/\*.json（三段证据链） | L1-04 S5 L2 |
| **监督事件** | supervisor_events.jsonl（8 维度 / 4 级 / 硬红线 / Soft-drift） | L1-07 全部 |
| **硬红线拦截记录** | hard_halt 事件 + 授权链 | L1-07 |
| **事件总线** | events.jsonl（全局单一事实源） | L1-09 L2-01 |
| **锁状态** | project 粒度锁 / WP 粒度锁 | L1-09 L2-02 |
| **审计记录** | audit_entries.jsonl（每 IC 调用 / 每决定 / 每 state 切换） | L1-09 L2-03 + L1-01 L2-05 |
| **检查点** | 跨 session 恢复用的 checkpoint 文件 | L1-09 L2-04 |
| **KB 条目（project 层）** | session 累积 → 可晋升到 project 的 KB | L1-06 L2-03 + L2-04 |
| **多模态素材** | 图片 / 代码结构摘要等 | L1-08 全部 |
| **Skill 调用记录** | 每次 skill 调用 / 子 Agent 委托 / 异步结果 | L1-05 全部 |
| **Gate 决定记录** | 4 次 Gate 的完整历史（含 re-open） | L1-02 L2-01 |
| **变更请求记录** | 运行时 change_request + 影响报告 ADR | L1-02 L2-01 |
| **retro** | retros/\<project_id\>.md（11 项复盘） | L1-02 L2-06 |
| **archive** | failure-archive.jsonl 中本 project 的条目 | L1-02 L2-06 委托 L1-05 |
| **交付包** | delivery/\<project_id\>/ 全部产出汇总 | L1-02 L2-06 |

### 6.2 归属唯一性约束

- **任何数据条目不得同时归属两个 project**（硬约束）
- **跨 project 引用**必须**拷贝数据**（例：如果 project B 想复用 project A 的章程模板，必须拷贝一份到 project B 的 manifest，不能做软链接）
- **global 层 KB** 是例外 —— 晋升后它**脱离所有 project**，成为"无主资产"，可被任何 project 读

### 6.3 归属的验证

L1-09 审计层可运行"**归属完整性自检**"：

- 对每个 `project_id`，扫所有归属数据，是否齐全（该有的都有）
- 扫所有数据，是否都有 `project_id` 归属字段（没有归属的 = 脏数据）
- 扫 project_id 之间，是否有交叉引用违规

---

## 7. 多会话隔离规则

### 7.1 单 project 多 session

**典型场景**：用户今天下午开始 project-foo，晚上关机。第二天早上打开 Claude Code 继续。

**隔离要求**：
- Claude session 变了（session_id 不同），但 project_id 必须**同一个**被激活
- L1-09 bootstrap 流程：读 project manifest 列表 → 找到 status=活跃 的 → 用最近使用的那个（或 UI 让用户选）
- 恢复后，主 loop 的 tick 上下文、事件总线、KB 读取、WP 调度**全部**按当前 project_id 作用域

### 7.2 单 session 多 project（V2+）

**V1 限制**：一个 Claude session 同时刻只能激活一个 project（防误操作 + 简化实现）

**V2+ 目标**：单 session 可挂多个 project，用户在 L1-10 UI 显式切换"当前 project"
- 切换时主 loop 的 tick 上下文随之换
- 不同 project 的事件总线 / task-board **物理隔离**（分目录 / 分 jsonl）
- 不同 project 的 KB 读取作用域自动按当前 project 过滤

### 7.3 多 session 多 project（团队形态 · V3+ 展望）

未考虑实现细节，但本文档的 project_id 模型设计**不阻止**未来扩展到多用户多项目的 SaaS 形态（加一层 tenant_id 即可）。

### 7.4 横切事件的 project 标记

事件总线中的所有事件必须携带 `project_id` 字段：

- 即便是"系统全局事件"（如系统启动 / supervisor 唤醒），也必须标"当前 project 是哪个"
- 无 project 状态下的事件（如首次启动、未创建任何 project 时）标 `project_id: null` 或专用哨兵值（如 `__system__`）

---

## 8. 项目级持久化根（概念级目录模型）

### 8.1 概念级布局

**注**：以下是产品级"逻辑模型"，具体目录名 / 文件格式 / 索引结构在 `docs/3-1-Solution-Technical/project-model/persistence-layout.md`。

```
<HarnessFlow 工作目录>/
│
├── projects/                              ← 所有项目的根
│   ├── <project_id_foo>/                  ← 每项目一个子目录
│   │   ├── manifest.yaml                  ← 项目元数据 + goal_anchor_hash
│   │   ├── state.yaml                     ← project 主状态当前态
│   │   ├── charter.md / stakeholders.md
│   │   ├── planning/                      ← 4 件套 + 9 计划
│   │   ├── architecture/                  ← TOGAF + ADR
│   │   ├── wbs.md + wp/<wp_id>/           ← WBS + 每 WP 详细
│   │   ├── tdd/                           ← TDD 蓝图 + 测试代码
│   │   ├── verifier_reports/              ← S5 验证报告
│   │   ├── events.jsonl                   ← 本 project 的事件总线
│   │   ├── audit.jsonl                    ← 审计记录
│   │   ├── supervisor_events.jsonl        ← 监督事件
│   │   ├── checkpoints/                   ← 跨 session 恢复用
│   │   ├── kb/                            ← project 层 KB
│   │   ├── delivery/                      ← S7 交付包（若已 closing+）
│   │   └── retros/                        ← retro 文档
│   │
│   ├── <project_id_bar>/                  ← 另一个项目，完全隔离
│   │   └── ...
│   │
│   └── _index.yaml                        ← 所有 project 的索引（ID + status + created_at）
│
├── global_kb/                              ← 跨项目共享 KB（晋升自 project 层）
│   └── entries/
│
├── failure_archive.jsonl                   ← 跨项目的失败归档（每条含 project_id）
│
└── system.log                              ← 系统级非 project 事件
```

### 8.2 关键隔离原则

1. 每 project 一个独立根目录 · **物理隔离**
2. **事件总线 / 审计 / 监督事件**都**按 project 独立文件**（不再有全局 events.jsonl 混读）
3. **KB**有 3 层：session 层（隐含在 Claude session 上下文）/ project 层（在 projects/\<id\>/kb/）/ global 层（在 global_kb/）
4. **failure_archive.jsonl** 是**唯一全局级**的失败档案（每条带 project_id 字段供检索）

### 8.3 跨 session 恢复时的读路径

1. 读 `projects/_index.yaml` 列出所有活跃 project
2. 用户/UI 选择或默认加载最近 project
3. 激活该 project 后，所有读写路径收窄到 `projects/<project_id>/` 子树

---

## 9. 与 10 个 L1 的关系矩阵

### 9.1 每个 L1 使用 project_id 的方式

| L1 | 使用方式 | 关键点 |
|---|---|---|
| **L1-01 主决策循环** | Tick 必带 project_id 上下文；决策 / 审计记录根字段 | state 切换前验证 project_id 一致 |
| **L1-02 项目生命周期** | **project_id 的所有权者** · 创建 / 激活 / 归档 / 删除的唯一执行者 | L2-02（S1 启动产出器）是创建点；L2-06（S7）是归档点 |
| **L1-03 WBS+WP 调度** | WBS 挂 project_id · WP 全部挂 project_id · 调度按 project 范围 | 不允许跨 project 调度 WP |
| **L1-04 Quality Loop** | TDD 蓝图 / 测试 / verifier 报告全挂 project_id · 回退路由按 project 限定 | 不允许跨 project 的同级 FAIL 计数合并 |
| **L1-05 Skill+subagent** | skill 调用 / 子 Agent 委托**必须**在 context 中带 project_id · 异步结果回传带 project_id | subagent 隔离 session 但仍带 project_id |
| **L1-06 3 层 KB** | project 层 KB 的作用域键就是 project_id · 读时默认只读当前 project 层 + global 层 | session 层 KB 是 Claude session 自带隔离，不需 project_id 显式标记但建议标 |
| **L1-07 Supervisor** | 监督事件按 project 订阅 · 硬红线拦截按 project 生效 · 8 维度状态按 project 独立计算 | 多 project 下 supervisor 并行监督但事件流分离 |
| **L1-08 多模态** | 素材缓存 / 代码结构摘要按 project 隔离 | 避免跨项目素材污染 |
| **L1-09 韧性+审计** | 事件总线 / 锁 / 审计 / 检查点 **全部按 project 分目录物理隔离** · 是 project_id 物理持久化的执行层 | 本 L1 是 project_id 的"存储根"落实层 |
| **L1-10 人机 UI** | 所有 UI 视图（11 tab + admin）按当前 project 筛选 · 用户可在 UI 切换 project | Gate 卡片 / progress stream / KB 浏览器 / 审计查询都受 project_id 限定 |

### 9.2 必须补的 L1 PRD 修正

以下 L1 PRD 在产品级需**补充"project_id 上下文"段**（具体见 §13 修补建议）：

- L1-01：补 tick / 决策 / 审计带 project_id
- L1-03 / L1-04 / L1-05 / L1-07 / L1-08：补 IC 通信契约的 project_id 要求
- L1-06 / L1-09 / L1-10：已有零散提及，补强骨架
- L1-02：已有 16 处提及，补"创建 / 归档 / 删除"的标准流程锚定本文档 §4

---

## 10. IC 契约中 project_id 必须出现的位置

### 10.1 全局原则

**所有 20 条对外 IC 契约（scope §8）以及所有 IC-L2 契约**，**首位参数必须是 `project_id`**（除极少数系统级例外）。

### 10.2 IC-by-IC 要求

| IC | 必带 project_id | 备注 |
|---|---|---|
| IC-01 request_state_transition | ✅ | state 变更受 project 约束 |
| IC-02 tick | ✅ | tick 必知道当前是哪个 project |
| IC-03 dispatch_wbs | ✅ | WBS 按 project 隔离 |
| IC-04 request_tdd | ✅ | TDD 按 project 限定 |
| IC-05 delegate_subagent | ✅ | subagent context 必带 |
| IC-06 kb_read | ✅ | KB 读按 project 作用域 |
| IC-07 acquire_lock | ✅ | 锁按 project 粒度 |
| IC-08 kb_promote | ✅ | 晋升源 project 需标 |
| IC-09 append_event | ✅ | 事件总线主键之一 |
| IC-10 forward_supervisor_event | ✅ | supervisor 事件按 project |
| IC-11 multimodal_pipeline | ✅ | 素材按 project 缓存 |
| IC-12 resilience | ✅ | 恢复按 project 针对 |
| IC-13 skill_dispatch | ✅ | skill 调用按 project 记录 |
| IC-14 progress_stream | ✅ | UI 流按 project 过滤 |
| IC-15 request_hard_halt | ✅ | halt 作用于某个 project |
| IC-16 push_stage_gate_card | ✅ | Gate 卡片归属 project |
| IC-17 user_intervene | ✅ | 用户干预针对某 project |
| IC-18 verify_artifact | ✅ | 验证归属 project |
| IC-19 request_wbs_decomposition | ✅ | WBS 拆归 project |
| IC-20 retrieve_kb | ✅ | KB 检索按 project + global |

### 10.3 例外

以下**系统级 IC**可以省略 project_id 或用哨兵值：

- 系统启动事件（bootstrap 前尚未有 project 概念时）
- 用户在 UI 点"创建新 project"这一刻（project_id 尚未生成，请求本身是"创建它"的动作）
- 系统级健康检查 / 资源使用上报（不归属任何 project）

### 10.4 对 scope §8 IC 契约表的修补要求

scope §8.2 的 IC 契约表目前没有显式把 project_id 列为必填字段。需要**新增一条全局约束**：

> **PM-14 硬约束**：所有 IC 的字段骨架里 `project_id` 必须是**第一或第二位**字段（与 IC ID 并列），没有 project_id 的 IC 必须显式标 `project_scope: "system"`。

详见 §12。

---

## 11. 多项目并发规则

### 11.1 V1（当前目标）：单 project 活跃

- 同一 Claude session 同时刻只有一个活跃 project
- 切换 project 时需 Save 当前 project checkpoint → Load 新 project checkpoint
- 主 loop 的 tick 队列随切换清空（或按 project 分队列，切换即换队列）

### 11.2 V2+（未来）：多 project 并行

**定义**：同一 Claude session 可同时保留多个活跃 project，用户在 UI 显式切换"当前 project"

**约束**：
- supervisor 可能同时监督 N 个 project，每 project 独立一个 supervisor 实例
- 事件总线按 project 分 jsonl 文件
- L1-01 主 loop 实例是 1 个，但 tick 按"当前 project"路由（切换 project 即换上下文）

**性能考虑**：多 project 并发时内存占用正比于 N，KB 读取时需明确作用域（仅当前 + global），避免全量扫

### 11.3 V3+（团队形态展望）

多用户多 project，加一层 tenant_id。当前不实现但模型兼容。

---

## 12. 新增业务模式 PM-14 · project-id-as-root

### 12.1 声明

| 编号 | 名称 | 一句话 |
|---|---|---|
| **PM-14** | **project-id-as-root**（项目根 ID 模式） | harnessFlowProjectId 是所有运行数据 / 产出 / 事件 / KB 的归属根键，所有跨组件通信必须携带；多 project / 多 session 按此键做强隔离 |

### 12.2 本 PM 的硬约束清单

1. 任何数据条目必须归属一个 project_id（global KB 除外）
2. 所有 IC 通信必须携带 project_id（或显式 `project_scope: "system"`）
3. 跨 project 引用必须拷贝数据（不做软链接 / 引用）
4. 事件总线 / 审计 / 监督事件必须按 project 物理隔离
5. 归档后的 project 数据保留至少 90 天（可配置）
6. 删除 project 是强操作 + 二次确认 + 全连带删除

### 12.3 本 PM 的典型违反 / 拦截点

- supervisor 可识别"无 project_id 的事件"作为硬红线（归入"契约违规"维度）
- 审计层自检扫"脏数据"（无归属字段的条目）

### 12.4 与现有 PM 的关系

- **PM-01 methodology-paced**：7 阶段的编排都在某个 project 内推进
- **PM-07 产出物模板驱动**：模板填充时 project_id 是内置变量之一
- **PM-08 可审计全链追溯**：追溯链的根字段就是 project_id
- **PM-10 事件总线单一事实源**：事件总线**按 project 分片**而非全局单表
- **PM-13 合规可裁剪**：裁剪档配置本身挂在 project_id 下
- **PM-14（本 PM）**：为上述所有 PM 提供"作用域锚点"

---

## 13. 对 Goal / scope / businessFlow / L1 PRD 的修补建议

### 13.1 HarnessFlowGoal.md 修补

**位置**：在"战略定位"或"核心概念"章节后新增一节：

> ## 全局灵魂：harnessFlowProjectId
> HarnessFlow 每次承接一个超大软件项目时生成一个全局唯一标识 `harnessFlowProjectId`，作为所有运行数据 / 产出 / 监督 / 知识 / 交付包的归属根键，并作为多会话 / 多项目场景的隔离边界。详见 `docs/2-prd/L0/projectModel.md`。

### 13.2 scope.md 修补

**位置 1**：在 "§X 业务模式" 章节（当前 PM-01~PM-13）新增 PM-14（复用本文档 §12）

**位置 2**：在 §8 IC 契约表前加一条"全局字段约束"：

> 所有 IC 契约的参数必须携带 `project_id`（除系统级 IC 显式标 `project_scope: "system"`）。未标 project_id 的 IC 为契约违规，supervisor 必拦截。

**位置 3**：在 §5.2（L1-02 定义）的 "In-scope" 补：

> L1-02 拥有 harnessFlowProjectId 的**全生命周期管理权**（创建 / 激活 / 归档 / 删除），详见 `docs/2-prd/L0/projectModel.md`。

**位置 4**：在 §5.9（L1-09 定义）的 "In-scope" 补：

> L1-09 负责 harnessFlowProjectId 的**物理持久化根目录结构**的维护（事件总线 / 审计 / 检查点按 project 分片存储），详见 `docs/2-prd/L0/projectModel.md` §8。

### 13.3 businessFlow.md 修补

新增一条横切业务流：

> **BF-X-10 · project 生命周期横切**
>
> 从 S1 启动首次生成 project_id → S7 归档 project_id 的端到端流程。贯穿 L1-02（所有权）+ L1-09（持久化）+ L1-01（tick 上下文）+ L1-10（UI 切换）。

### 13.4 flowOutInput.md 修补

在 §2 "全局输入规范" / §4 "ITTO 表" 中新增：

> **项目上下文（Project Context）**：所有 I/O 必须携带 `harnessFlowProjectId`（创建 project 的那一刻除外）。

### 13.5 L1 PRD 修补（10 份 PRD 逐个检查）

**优先级 1（必须修）**：
- L1-01：在 L2-01（Tick 调度器）和 L2-03（状态机编排器）补"每 tick / 每 state 切换必带 project_id"；在对外 IC 映射补 project_id 必填约束
- L1-02：在 L2-02（S1 启动产出器）补"project_id 创建点"；在 L2-06（S7 收尾）补"归档点"；新增 L2 候选"项目生命周期管理器"（或并入 L2-01 Stage Gate 控制器的扩展）管全生命周期创建 / 激活 / 归档 / 删除
- L1-09：明确"事件总线 / 审计 / 检查点按 project 物理隔离"；L2-02（锁管理器）加"锁粒度含 project"；L2-04（检查点 / 恢复器）明确"读 projects/\_index.yaml 决定激活哪个"

**优先级 2（应修）**：
- L1-03：WBS + WP 挂 project_id 的归属声明
- L1-04：TDD 蓝图 / verifier 报告挂 project_id
- L1-06：3 层 KB 的作用域键是 project_id
- L1-07：supervisor 按 project 订阅 / 监督
- L1-10：UI 按 project 过滤 + 切换

**优先级 3（细化）**：
- L1-05：skill 调用 / 子 Agent 委托 context 中带 project_id
- L1-08：素材缓存按 project 隔离

---

## 14. 验收大纲（产品级）

### 14.1 创建 + 锁定（P1）

- **Given** 用户在 Claude Code 发起新项目目标输入
- **When** L1-02 S1 阶段澄清通过
- **Then** 系统生成一个唯一 `harnessFlowProjectId` + 写入 manifest + 发 `project_created` 事件

### 14.2 全产出归属（P2）

- **Given** project foo 已创建且在 S2 阶段
- **When** L1-02 L2-03 生成 requirements.md
- **Then** 文件落在 `projects/foo/planning/requirements.md`（不在根目录、不在其他 project 子树）

### 14.3 事件总线隔离（P3）

- **Given** 同时有 project foo 和 project bar（V2+ 场景）
- **When** foo 发 `4_pieces_ready` 事件
- **Then** 事件只出现在 `projects/foo/events.jsonl`，不出现在 `projects/bar/events.jsonl`

### 14.4 跨 session 恢复（P4）

- **Given** 用户昨天启动 project foo 跑到 S3，今天重启 Claude Code
- **When** 系统 bootstrap
- **Then** 自动激活 project foo 并恢复到 S3 最后检查点；用户可继续推进

### 14.5 归档（P5）

- **Given** project foo 在 S7 最终 Gate 通过
- **When** 用户 Go
- **Then** project foo 主状态转 CLOSED；后续事件拒绝入 foo 事件总线；UI 标"已归档"

### 14.6 负向：无 project_id 的 IC（N1）

- **Given** 开发者错写了一个 IC 调用不带 project_id
- **When** 该调用到达接收 L1
- **Then** 接收 L1 拒绝 + 发"契约违规"审计；supervisor 将其归入"契约维度"偏差

### 14.7 负向：跨 project 归属（N2）

- **Given** project foo 的 WP 定义试图引用 project bar 的 goal_anchor
- **When** L1-03 生成 WBS
- **Then** 系统拒绝 + 报"跨 project 引用违规"

### 14.8 集成：多 project 切换（I1 · V2+）

- **Given** 用户有活跃 project foo 和 bar
- **When** 用户在 L1-10 UI 切到 bar
- **Then** 主 loop tick 上下文换到 bar；所有视图（task-board / KB / 事件流）按 bar 过滤

### 14.9 性能

- 创建 project 端到端 ≤ 2s（含 manifest 写盘）
- 切换 project 上下文 ≤ 1s
- 事件总线按 project 写入时延 ≤ 50ms

---

## 附录 A · 术语

| 术语 | 含义 |
|---|---|
| **harnessFlowProjectId** | HarnessFlow 每个项目的全局唯一 + 不可变标识 |
| **项目根** | `projects/<harnessFlowProjectId>/` 目录 |
| **项目 manifest** | 项目根下的元数据文件，含 project_id / goal_anchor_hash / state / created_at / 等 |
| **激活 project** | 当前 session 把某 project 置为"正在推进"的动作 |
| **归档 project** | S7 完结后 project 进入 CLOSED 状态，数据保留但不再接收事件 |
| **全局灵魂** | 本文档对 harnessFlowProjectId 的定位表述（战略地位） |
| **归属根键** | project_id 作为所有数据的父键 |
| **隔离边界** | 不同 project_id 的数据物理 / 逻辑都不互通 |
| **project 主状态** | 本文档 §5.1 的项目级状态机（区别于 L1-01 的 tick 级 state） |

---

## 附录 B · 命名规则示例（产品级约束）

**注**：具体格式 / 字符集 / 长度在 3-1 技术方案中决定，本附录只列产品级约束示例。

**形态示例**（非强制格式）：
- 机器态：`<slug>-<uuid-short>` 形如 `todo-app-a1b2c3d4`
- 人类态：`<project_title>` 形如 "TODO 应用"（用户看到的）
- 两态的映射在 manifest.yaml 里

**禁止的命名**：
- 含 PII（邮箱 / 姓名 / 手机号）
- 含敏感业务词（密钥 / token）
- 纯数字（可读性差，易混淆）
- 与 HarnessFlow 内部保留词冲突（如 `__system__` / `global` / `test`）

---

*— projectModel.md v1.0 草案 · 等待 user review · review 通过后触发 10 个 L1 PRD 修补轮 —*
