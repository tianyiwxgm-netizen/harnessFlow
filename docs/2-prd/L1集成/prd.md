---
doc_id: prd-l1-integration-v1.0
doc_type: l1-integration-prd
parent_doc:
  - HarnessFlowGoal.md
  - docs/2-prd/L0/scope.md#8
  - docs/2-prd/L0/businessFlow.md
  - docs/2-prd/L0/projectModel.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md
  - docs/2-prd/L1-06 3层知识库/prd.md
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/2-prd/L1-08 多模态内容处理/prd.md
  - docs/2-prd/L1-09 韧性+审计/prd.md
  - docs/2-prd/L1-10 人机协作UI/prd.md
version: v1.0
status: draft
author: mixed
created_at: 2026-04-20
updated_at: 2026-04-20
traceability:
  goal_anchor: HarnessFlowGoal.md（10 L1 协同跑通超大项目）
  scope_anchor: docs/2-prd/L0/scope.md#8（L1 间产品业务流）
  business_flow: 全部 BF（L1 集成贯穿所有业务流）
  project_model: docs/2-prd/L0/projectModel.md（PM-14 跨 L1 一致性）
consumer:
  - TDD 阶段（集成测试矩阵 + 端到端场景作 Master Test Plan 输入）
  - docs/3-1-Solution-Technical/L1-integration/tech-design.md（集成层技术方案）
  - 项目交付（集成验收大纲）
---

# L1 集成 · PRD（10 L1 协同 PRD）

> **版本**：v1.0（基于 10 个 L1 PRD 全部 v1.0 ready_for_review 后整合）
> **定位**：把 10 个独立 L1 黏合成完整 HarnessFlow 系统的**集成层产品文档** —— 定义 L1 间契约一致性测试矩阵 + 端到端集成场景 + 失败传播规则 + 性能集成约束 + 多项目并发集成（PM-14）+ 跨 session 恢复集成。
> **严格遵循**：本 PRD 与 `docs/2-prd/L0/scope.md §8` 互补 —— scope §8 是**总括**（4 类整合图 + 20 IC + 5 场景），本 PRD 是**深化 + 测试设计**（10×10 测试矩阵 + 10+ 端到端场景 + PM-14 多项目集成 + 集成性能阈值 + TDD 集成蓝图输入）。冲突以 scope §8 为准。
> **严格产品级**：本文不含算法 / 伪码 / 代码块 / YAML schema 字段级 / 状态机代码 / 配置参数表 / 通信协议字段格式。所有实现细节迁到 `docs/3-1-Solution-Technical/L1-integration/tech-design.md`。
> **PM-14 集成贯穿声明**：本 PRD 全文以 `harnessFlowProjectId` 作为集成场景的核心维度 —— 所有 IC 一致性测试 / 端到端场景 / 失败传播链都按 project_id 范围内验证；多项目并发集成是 §8 单独章节。

---

## 0. 撰写进度

- [x] §1 定位与范围
- [x] §2 集成架构全景（综合图 + PM-14 维度）
- [x] §3 20 条 IC 契约深化 + 一致性测试点
- [x] §4 10 × 10 集成测试矩阵
- [x] §5 端到端集成场景（12 个）
- [x] §6 失败传播详细矩阵
- [x] §7 性能集成约束
- [x] §8 多项目并发集成（PM-14 V2+ 场景）
- [x] §9 跨 session 恢复集成验证
- [x] §10 集成验证大纲（TDD 输入）
- [x] §11 集成里程碑 + Gate
- [x] 附录 A 术语 / B 场景索引 / C IC 一致性检查清单

---

## 1. 定位与范围

### 1.1 与 scope §8 的关系

| 维度 | `scope.md §8` | 本 PRD（L1 集成）|
|---|---|---|
| **角色** | L1 间整合的**总括** | L1 间集成的**深化 + 测试设计** |
| **粒度** | 4 类图 + 20 IC 一句话 schema + 5 场景 | 10×10 一致性测试矩阵 + 12 端到端场景 + 失败传播详细矩阵 + 集成性能阈值 |
| **产出消费方** | 10 个 L1 PRD（作锚点）| TDD 集成蓝图（作 Master Test Plan 输入）+ 3-1 集成层技术方案 + 验收阶段（作集成验收清单） |
| **修改频率** | 与 scope.md 共冻结 | 随各 L1 PRD 更新而 sync |

### 1.2 In-scope（本 PRD 范围）

1. 10 个 L1 之间的**契约一致性测试设计**（每对 L1 间至少 1 条契约用例）
2. **端到端集成场景**（覆盖正常 + 异常 + 多项目 + 跨 session）
3. **失败传播规则的详细矩阵**（哪个 L1 失败时哪些下游受波及 + 兜底策略）
4. **性能集成约束**（端到端时延 / 吞吐 / 并发）
5. **多项目并发集成**（PM-14 V2+ 场景设计）
6. **跨 session 恢复集成验证**（PM-14 关键场景 + 持久化层驱动）
7. **集成验证大纲**（给 TDD 阶段作 Master Test Plan 直接输入）

### 1.3 Out-of-scope（本 PRD 不做）

- ❌ 不重复定义 IC schema（已在 scope §8.2，本 PRD 引用）
- ❌ 不重定义各 L1 内部职责（已在各 L1 PRD）
- ❌ 不写集成代码 / 测试代码（属 TDD 阶段）
- ❌ 不写集成层技术方案（属 3-1）
- ❌ 不做单 L1 内部测试设计（属各 L1 PRD §X.9 验收大纲）

### 1.4 阅读路径

| 你想知道 | 看这节 |
|---|---|
| 10 L1 怎么协同的全景图 | §2 |
| 某条 IC 应该怎么测 | §3 |
| 哪两个 L1 之间需要测什么 | §4 |
| 一个完整端到端流程怎么跑 | §5 |
| 某 L1 挂了下游会怎样 | §6 |
| 集成性能要达多少 | §7 |
| 多项目并发怎么设计 | §8 |
| 跨 session 恢复怎么验 | §9 |
| TDD 阶段集成测试要做什么 | §10 |

---

## 2. 集成架构全景

### 2.1 综合架构图（10 L1 + PM-14 维度）

```
                              ┌────────────────────────────────────────┐
                              │  user                                  │
                              └────────────────┬───────────────────────┘
                                               │
                         ┌─────────────────────┴─────────────────────┐
                         │                                           │
                         ▼                                           │ user_intervene
                ┏━━━━━━━━━━━━━━━━━━━━━┓                              │ (IC-17)
                ┃ L1-10 人机协作 UI    ┃ ─── push_stage_gate(IC-16) ─┘
                ┃ (按 project 过滤)    ┃ ◄─── progress_stream(IC-14)
                ┗━━━━━━━━━┳━━━━━━━━━━━┛
                          │
                          │ user_intervene → IC-17
                          ▼
              ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
              ┃ L1-01 主 Agent 决策循环         ┃ ◄── push_suggestion(IC-13)
              ┃ (心脏 · tick 必带 project_id)   ┃     push_rollback_route(IC-14)
              ┃                                ┃     request_hard_halt(IC-15)
              ┗━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━┛           ▲
   IC-01 │       │       │       │                       │
state    │  IC-02│  IC-03│  IC-04│ IC-04/IC-11           │ scan
trans    ▼  next ▼ enter ▼ invoke▼ (skill /              │ 30s
         │   wp  │ qual  │ skill   multimodal)           │
   ┏━━━━━━━━━━┓ ┏━━━━━━━━━━┓ ┏━━━━━━━━━━┓ ┏━━━━━━━━━━┓ ┏━━━━━━━━━━┓
   ┃ L1-02   ┃ ┃ L1-03   ┃ ┃ L1-04   ┃ ┃ L1-05   ┃ ┃ L1-07   ┃
   ┃ 项目    ┃ ┃ WBS+WP  ┃ ┃ Quality ┃ ┃ Skill+  ┃ ┃ Harness ┃
   ┃ 生命周期 ┃ ┃ 调度    ┃ ┃ Loop    ┃ ┃ 子 Agent ┃ ┃ 监督    ┃
   ┃          ┃ ┃          ┃ ┃          ┃ ┃          ┃ ┃ (旁路)  ┃
   ┃ ★ pid    ┃ ┃ WP 挂   ┃ ┃ 蓝图    ┃ ┃ ctx 必带 ┃ ┃ 按 pid  ┃
   ┃ 所有权方 ┃ ┃ pid     ┃ ┃ 挂 pid  ┃ ┃ pid     ┃ ┃ 订阅    ┃
   ┗━━┳━━━━━━┛ ┗━━━━━━━━━━┛ ┗━━━┳━━━━━━┛ ┗━━━┳━━━━━━┛ ┗━━━━━━━━━━┛
      │ IC-19                       │ IC-20      │
      │ wbs_decomp                  │ verifier   │
      │                             │            │
      └─────────► [L1-03] ◄─────────┘            │
                                                  │
                                                  │ IC-04 invoke
                                                  ▼
                                         ┏━━━━━━━━━━━┓
                                         ┃ L1-06    ┃
                                         ┃ 3 层 KB   ┃ ◄── IC-06/07/08
                                         ┃ ★ pid    ┃     (kb_read/write/promote)
                                         ┃ 作用域键 ┃
                                         ┗━━━━━━━━━━┛

                ┌─────── 全部 L1 通过 IC-09 append_event ────┐
                │                                            │
                ▼                                            │
       ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓                   │
       ┃ L1-09 韧性 + 审计 (脊柱 + 记忆)  ┃ ◄─────────────────┘
       ┃                                  ┃
       ┃ ★ 按 pid 物理分片：               ┃
       ┃   projects/<pid>/events.jsonl    ┃
       ┃   projects/<pid>/audit.jsonl     ┃
       ┃   projects/<pid>/checkpoints/    ┃
       ┗━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┛
                │ IC-12/IC-18
                ▼
         ┏━━━━━━━━━━━━━┓
         ┃ L1-08 多模态 ┃ (按 pid 隔离缓存)
         ┗━━━━━━━━━━━━━┛
```

**关键架构规则**（PM-14 增强后）：

1. **L1-01 是唯一控制源**（不变）
2. **L1-02 是 project_id 唯一所有权方**（PM-14 新增）
3. **L1-09 是 project_id 物理持久化的唯一落实方**（PM-14 新增）
4. **所有 IC 必须携带 project_id**（PM-14 硬约束 · scope §4.6）
5. **数据流单向**（不允许下游回写上游）
6. **L1-07 旁路监督 · 不直接改业务状态**（仅通过 IC-13/14/15 建议）

### 2.2 4 类整合流图（引用 scope §8.1）

详见 `docs/2-prd/L0/scope.md §8.1`：

| 类别 | 主线 | 补充（PM-14）|
|---|---|---|
| **控制流** | L1-01 → 其他做事的 L1 | 控制指令必带 project_id 上下文 |
| **数据流** | L1-02 4 件套 → L1-03 WBS → L1-04 TDD → 代码 → S5 → S7 | 全链路按 project 隔离，跨 project 引用必拷贝 |
| **监督流** | L1-07 旁路扫 L1-09 事件总线 → 8 维度 / 4 级 / 红线 | 多 project 时每 project 一独立 supervisor |
| **持久化流** | 全部 → L1-09 IC-09 append_event | 按 project 物理分片 |

### 2.3 PM-14 集成维度图

```
┌──────────────────────────────────────────────────────────────────┐
│  HarnessFlow 工作目录                                              │
│                                                                    │
│  projects/                                                         │
│  ├── <project_foo_id>/                                            │
│  │   ├── manifest.yaml         ← L1-02 拥有                       │
│  │   ├── state.yaml            ← L1-02 主状态                      │
│  │   ├── charter / planning / architecture / wbs / tdd / ...      │
│  │   ├── events.jsonl          ← L1-09 写入                       │
│  │   ├── audit.jsonl           ← L1-09 写入                       │
│  │   ├── supervisor_events.jsonl ← L1-07 写 / L1-09 落盘          │
│  │   ├── checkpoints/          ← L1-09 跨 session 恢复            │
│  │   ├── kb/                   ← L1-06 project 层                 │
│  │   ├── delivery/             ← L1-02 L2-06 S7 收尾产出           │
│  │   └── retros/               ← L1-02 L2-06 委托 L1-05 retro-gen │
│  │                                                                │
│  ├── <project_bar_id>/         ← 完全隔离的另一项目（V2+）          │
│  │   └── ...                                                      │
│  │                                                                │
│  └── _index.yaml               ← 所有 project 的索引                │
│                                                                    │
│  global_kb/                    ← L1-06 跨 project 共享层            │
│  failure_archive.jsonl         ← 全局 · 含 project_id 字段          │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘

各 L1 在此图中的"角色锚点"：
- L1-02: 创建/激活/归档 project（拥有 manifest + state）
- L1-09: 物理隔离落实（events / audit / checkpoints）
- L1-06: 3 层 KB (session 隐含 / project 在子目录 / global 在 global_kb/)
- L1-07: 多 project 时一 project 一 supervisor 实例
- L1-10: UI 按当前 project 过滤所有视图
- L1-01/03/04/05/08: 携带 project_id 上下文不直接物理隔离
```

---

## 3. 20 条 IC 契约深化 + 一致性测试点

### 3.1 IC 契约总览（按 L1 承担方分组）

| 承担方（被调） | IC 编号 | 调用方 | 一句话职责 | PM-14 必带 project_id |
|---|---|---|---|---|
| **L1-01** | IC-13 | L1-07 | push_suggestion（监督建议）| ✅ |
|   | IC-15 | L1-07 | request_hard_halt（硬红线）| ✅ |
|   | IC-17 | L1-10 | user_intervene（用户干预）| ✅ |
| **L1-02** | IC-01 | L1-01 | request_state_transition | ✅ |
|   | IC-19 | （内部触发 L1-03）| request_wbs_decomposition | ✅ |
| **L1-03** | IC-02 | L1-01 | get_next_wp | ✅ |
| **L1-04** | IC-03 | L1-01 | enter_quality_loop | ✅ |
|   | IC-14 | L1-07 | push_rollback_route | ✅ |
| **L1-05** | IC-04 | 多 L1 | invoke_skill | ✅（context 必带）|
|   | IC-05 | 多 L1 | delegate_subagent | ✅（context 必带）|
|   | IC-12 | L1-08 | delegate_codebase_onboarding | ✅ |
|   | IC-20 | L1-04 | delegate_verifier | ✅ |
| **L1-06** | IC-06 | 多 L1 | kb_read | ✅（默认作用域=当前 project + global）|
|   | IC-07 | 多 L1 | kb_write_session | ✅（隐含 session 归属 project）|
|   | IC-08 | 多 L1 | kb_promote | ✅（晋升源 project 需标）|
| **L1-08** | IC-11 | 多 L1 | process_content（多模态）| ✅ |
| **L1-09** | IC-09 | **全部 L1** | append_event | ✅（**根字段必含**）|
|   | IC-10 | L1-09 内 | replay_from_event | ✅（按 project 回放）|
|   | IC-18 | L1-10 | query_audit_trail | ✅（按 project 检索）|
| **L1-10** | IC-16 | L1-02 | push_stage_gate_card | ✅ |
|   |（部分）| 各 L1 | progress_stream（推 UI）| ✅ |

### 3.2 每条 IC 的一致性测试点（按 IC 编号）

#### IC-01 · L1-01 → L1-02 · request_state_transition

| 测试维度 | 验收点 |
|---|---|
| **正向** | from=PLAN to=TDD_PLAN 且当前 state=PLAN → accepted=true |
| **负向** | from=PLAN to=CLOSED（违 allowed_next）→ accepted=false + 原因明确 |
| **PM-14** | 缺 project_id → L1-02 拒绝 + 审计违规 |
| **横切** | gate_id 关联（若该 transition 是 Gate 通过触发的）|
| **失败** | L1-02 内部错误 → L1-01 收到 accepted=false + 不切 state |

#### IC-02 · L1-01 → L1-03 · get_next_wp

| 测试维度 | 验收点 |
|---|---|
| **正向** | 拓扑中下一可执行 WP 存在 → 返回 wp_id + wp_def + deps_met=true |
| **负向** | 全部 WP 已 done → 返回 null |
| **依赖未满足** | 拓扑中存在 WP 但前置 deps 未完成 → 返回 null + 说明等待 |
| **PM-14** | 跨 project 调用拒绝（project A 不能 get project B 的 WP）|
| **并发约束** | 同时 in-flight WP > 1（违 PM-04 最多 2）→ 返回 null |

#### IC-03 · L1-01 → L1-04 · enter_quality_loop

| 测试维度 | 验收点 |
|---|---|
| **正向** | wp_def 完整 → 返回 loop_session_id 异步启动 |
| **PM-14** | wp_def 必带 project_id |
| **并发** | 同 project 不允许同时启 > 2 quality loop |
| **失败** | wp_def 缺字段 → 拒绝启动 + 原因 |

#### IC-04 · 多 L1 → L1-05 · invoke_skill

| 测试维度 | 验收点 |
|---|---|
| **正向** | capability 注册 + ≥1 备选 skill → 返回 result + skill_id + duration_ms |
| **降级链** | 主 skill 失败 → 自动 fallback 到备选 → 返回 result + 标记 fallback |
| **超时** | 超 timeout → 返回错误 + 走 BF-E-05 fallback |
| **PM-14** | params 中必带 project_id（context 字段或 root）|
| **能力不存在** | capability 无注册 → 拒绝 + 提示 |

#### IC-05 · 多 L1 → L1-05 · delegate_subagent

| 测试维度 | 验收点 |
|---|---|
| **正向** | subagent 注册 + context_copy 完整 → 异步派发 + 返回 report |
| **PM-14** | context_copy 必带 project_id |
| **独立 session（PM-03）** | subagent 在独立 session 跑，不读主 session 状态 |
| **超时** | 超 timeout → 强终止 + 返回 partial report 或失败 |
| **结果回收** | subagent 完成 → IC-09 发 subagent_result 事件 → L1-01 路由回正确 project |

#### IC-06 · 多 L1 → L1-06 · kb_read

| 测试维度 | 验收点 |
|---|---|
| **正向** | 按 kind + scope + filter 返回 entries（按 rerank 排序）|
| **PM-14** | 默认 scope=session+project+global（不读其他 project）|
| **空结果** | 无匹配 → 返回 entries=[] + 不报错 |
| **降级** | KB 服务故障 → 返回空 + 告警，但不阻塞调用方 |
| **rerank** | 多源条目 → 按上下文相关性 rerank |

#### IC-07 · 多 L1 → L1-06 · kb_write_session

| 测试维度 | 验收点 |
|---|---|
| **正向** | entry 完整 → 返回 id + 写入 session 层 |
| **PM-14** | entry 隐含归属当前 project 的 session |
| **observe 累积** | 同类 entry 多次写入 → observed_count 累加 |
| **失败降级** | 写失败 → log 告警 + 不阻塞调用方 |

#### IC-08 · 多 L1 → L1-06 · kb_promote

| 测试维度 | 验收点 |
|---|---|
| **正向** | observed_count >= 阈值 或 user_approved=true → promoted=true |
| **PM-14** | 晋升源 project 需标（写入晋升记录）|
| **拒绝条件** | observed_count 不达标 + 无用户批准 → promoted=false |
| **目标层级** | target_scope=project / global 都支持 |

#### IC-09 · **全部 L1** → L1-09 · append_event

**这是最关键的契约**（所有 L1 写事件的唯一入口）。

| 测试维度 | 验收点 |
|---|---|
| **正向** | event 完整（含 project_id）→ 返回 event_id + sequence + hash |
| **PM-14** | **缺 project_id 拒绝**（系统级事件需显式 `project_scope: "system"`）|
| **append-only** | 不可修改已落盘事件 |
| **fsync 每次** | 写后立即落盘（防崩溃丢失）|
| **hash 链** | event.hash 含前事件 hash → 防篡改 |
| **失败行为** | 写盘失败 → **halt 整个系统**（PM-08 单一事实源不可破）|
| **物理隔离（PM-14）** | 写入路径必为 `projects/<project_id>/events.jsonl` |

#### IC-10 · L1-09 内部 · replay_from_event

| 测试维度 | 验收点 |
|---|---|
| **正向** | 按 from_seq + to_seq 重放 → 返回 task_board_state |
| **PM-14** | 按 project 回放（不混读其他 project 事件）|
| **事件损坏** | hash 链断裂 → 返回 err + 标记损坏点 |

#### IC-11 · 多 L1 → L1-08 · process_content

| 测试维度 | 验收点 |
|---|---|
| **正向** | type=md/code/image + path 存在 → 返回 structured_description |
| **PM-14** | 路径限定在当前 project 子树（防跨 project 读）|
| **路径不存在** | 返回 err + 提示 |
| **图片视觉理解** | type=image → 调 Claude vision，结构化输出 |
| **大代码库** | type=code 且 > 10 万行 → 委托 L1-05 IC-12（onboarding）|

#### IC-12 · L1-08 → L1-05 · delegate_codebase_onboarding

| 测试维度 | 验收点 |
|---|---|
| **正向** | repo_path 有效 → 返回 structure_summary + kb_entries |
| **PM-14** | repo 关联当前 project（kb_entries 写入 project 层）|
| **失败** | onboarding 子 Agent 失败 → 走 BF-E-09 降级 |

#### IC-13 · L1-07 → L1-01 · push_suggestion

| 测试维度 | 验收点 |
|---|---|
| **正向** | level=INFO/SUGG/WARN → L1-01 接收即落事件（fire-and-forget）|
| **BLOCK 级** | level=BLOCK → 必触发 L1-01 暂停 |
| **PM-14** | suggestion 必关联具体 project_id（不允许"全局"建议）|
| **多 project（V2+）** | 每 project supervisor 独立推 suggestion 到对应 project loop |

#### IC-14 · L1-07 → L1-04 · push_rollback_route

| 测试维度 | 验收点 |
|---|---|
| **正向** | level=L1/L2/L3/L4 + target_state 有效 → routing_applied=true |
| **PM-14** | 路由作用域限定 project（不能让 project A 的回退影响 project B）|
| **同级 ≥3 升级** | 同级 FAIL 累计 ≥ 3 → 自动升一级 |

#### IC-15 · L1-07 → L1-01 · request_hard_halt

| 测试维度 | 验收点 |
|---|---|
| **正向** | red_line_id 命中 → halted=true + 立即生效 |
| **PM-14** | 硬 halt 限定 project（project A 的红线不停 project B）|
| **要求用户授权** | require_user_authorization=true → 等用户 IC-17 authorize 才解 |
| **审计** | 硬 halt 事件 + 解 halt 事件全审计 |

#### IC-16 · L1-02 → L1-10 · push_stage_gate_card

| 测试维度 | 验收点 |
|---|---|
| **正向** | gate_id + bundle 完整 → UI 显示卡片 + blocks 直到用户决定 |
| **PM-14** | gate_id 必含 project_id 防误决定到错 project |
| **artifacts_bundle** | 按 trim_level 打包正确产出物子集 |
| **三种决定** | approve / reject / request_change 全支持 |
| **跨 session** | 用户决定前重启 → 恢复后 UI 重推卡片 |

#### IC-17 · L1-10 → L1-01 · user_intervene

| 测试维度 | 验收点 |
|---|---|
| **正向** | type=authorize/pause/resume/clarify/change_request 全支持 |
| **PM-14** | 用户干预必关联当前 project_id |
| **panic** | type=pause 立即 ≤ 100ms 中断 current tick + state=PAUSED |
| **resume** | type=resume 从 PAUSED/HALTED 回 IDLE |
| **change_request（运行时）** | 触发 L1-02 L2-01 ANALYZING 影响面分析 |

#### IC-18 · L1-10 → L1-09 · query_audit_trail

| 测试维度 | 验收点 |
|---|---|
| **正向** | 按锚点（file_path / artifact_id / decision_id）反查 → 完整链 |
| **PM-14** | 默认按当前 project 检索 |
| **跨 project 检索** | UI 显式选 "全 project" → 可跨 project（仅查询，不修改）|
| **链完整性** | 决策 → 事件 → supervisor 评论 → 用户授权 全段都返回 |

#### IC-19 · L1-02 → L1-03 · request_wbs_decomposition

| 测试维度 | 验收点 |
|---|---|
| **正向** | 4 件套 + architecture_output 完整 → 返回 wbs_topology |
| **PM-14** | wbs_topology 全部 WP 挂当前 project_id |
| **DAG 校验** | 拓扑必无环（L1-03 内部强约束）|
| **粒度约束** | 每 WP ≤ 5 天工时（违则 L1-03 自动再拆）|
| **失败回 S2** | 4 件套不齐 → 拒绝 + 通知 L1-02 回 S2 补 |

#### IC-20 · L1-04 → L1-05 · delegate_verifier

| 测试维度 | 验收点 |
|---|---|
| **正向** | s3_blueprint + s4_artifacts + dod_expressions → 返回 verifier_report_json（三段证据链）|
| **PM-14** | verifier context 必带 project_id |
| **独立 session（PM-03）** | verifier 在独立 session 跑 |
| **DoD 白名单 AST** | dod_expressions 走白名单 eval（禁 arbitrary exec）|
| **失败降级** | verifier 失败 → 降级到主 session 跑简化 DoD + 标 INSUFFICIENT |

---

## 4. 10 × 10 集成测试矩阵

### 4.1 矩阵总览

10 × 10 矩阵共 45 对（对称去重）。每对至少 1 条 IC。下表标"●"=必测，"○"=可选弱依赖，"-"=无直接 IC。

|  | L1-01 | L1-02 | L1-03 | L1-04 | L1-05 | L1-06 | L1-07 | L1-08 | L1-09 | L1-10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **L1-01** | — | ● | ● | ● | ● | ○ | ● | ○ | ● | ● |
| **L1-02** | ● | — | ● | ○ | ○ | ○ | - | - | ● | ● |
| **L1-03** | ● | ● | — | ○ | - | ○ | ○ | - | ● | ○ |
| **L1-04** | ● | ○ | ○ | — | ● | ○ | ● | - | ● | ○ |
| **L1-05** | ● | ○ | - | ● | — | ○ | - | ● | ● | ○ |
| **L1-06** | ○ | ○ | ○ | ○ | ○ | — | - | ○ | ● | ○ |
| **L1-07** | ● | - | ○ | ● | - | - | — | - | ● | ○ |
| **L1-08** | ○ | - | - | - | ● | ○ | - | — | ● | ○ |
| **L1-09** | ● | ● | ● | ● | ● | ● | ● | ● | — | ● |
| **L1-10** | ● | ● | ○ | ○ | ○ | ○ | ○ | ○ | ● | — |

### 4.2 必测对（●）的核心 IC 一致性用例

按上表 ● 标记列出 25 对必测对应的核心一致性用例：

| 对 | 主 IC | 关键用例 |
|---|---|---|
| **L1-01 ↔ L1-02** | IC-01 | state 转换合规性 + Gate 阻塞响应 |
| **L1-01 ↔ L1-03** | IC-02 | get_next_wp + 拓扑依赖判定 + 并发约束 |
| **L1-01 ↔ L1-04** | IC-03 | enter_quality_loop 异步启动 + 完成回调 |
| **L1-01 ↔ L1-05** | IC-04/05 | invoke_skill + delegate_subagent + 异步结果回收 |
| **L1-01 ↔ L1-07** | IC-13/15 | push_suggestion + request_hard_halt 响应 |
| **L1-01 ↔ L1-09** | IC-09 | append_event 单一事实源 + halt 失败行为 |
| **L1-01 ↔ L1-10** | IC-17 | user_intervene 5 类操作 + panic ≤ 100ms |
| **L1-02 ↔ L1-01** | IC-01 | （同上）|
| **L1-02 ↔ L1-03** | IC-19 | request_wbs_decomposition 4 件套→WBS 拓扑 |
| **L1-02 ↔ L1-09** | IC-09 | 4 件套 / 9 计划 / TOGAF / 章程 落盘 |
| **L1-02 ↔ L1-10** | IC-16 | Stage Gate 卡片推送 + 用户决定回路 |
| **L1-03 ↔ L1-09** | IC-09 | WBS / WP 状态变更落盘 |
| **L1-04 ↔ L1-05** | IC-20 | delegate_verifier + 三段证据链 + DoD 白名单 |
| **L1-04 ↔ L1-07** | IC-14 | push_rollback_route 4 级回退 + 同级升级 |
| **L1-04 ↔ L1-09** | IC-09 | TDD 蓝图 / verifier_report / verdict 落盘 |
| **L1-05 ↔ L1-09** | IC-09 | skill / subagent 调用 + 结果落盘 |
| **L1-05 ↔ L1-08** | IC-12 | delegate_codebase_onboarding |
| **L1-06 ↔ L1-09** | IC-09 | KB 写 + 晋升落盘 |
| **L1-07 ↔ L1-09** | IC-09 | supervisor_event 落盘（按 project）|
| **L1-08 ↔ L1-09** | IC-09 | 多模态处理事件落盘 |
| **L1-09 ↔ L1-10** | IC-18 | query_audit_trail 按 project 检索 |
| 其余 ● 对 | — | 见各对应 IC 在 §3 |

### 4.3 弱依赖对（○）的可选用例

弱依赖对通常是"非主线但有契约关系"的对，比如：
- L1-01 ↔ L1-06：决策时可选 KB 注入（IC-06）
- L1-04 ↔ L1-06：TDD 蓝图生成时可选 KB 模式参考
- L1-02 ↔ L1-04：S3 Gate 通过后 L1-04 接手（间接）

弱依赖对在集成测试中作 **smoke test**（起跑通即可，不深入边界覆盖）。

### 4.4 集成测试覆盖率目标

| 类别 | 覆盖率 |
|---|---|
| 必测对（●）每对至少 4 用例（正向 / 负向 / PM-14 / 失败降级） | 100% |
| 弱依赖对（○）每对至少 1 smoke test | 100% |
| 20 IC 每条至少 5 用例（覆盖 §3 每 IC 测试维度） | 100% |
| 端到端场景（§5 12 个） | 100% |
| 性能集成阈值（§7） | 100% |
| 多项目并发集成（§8） | 100%（V2+ 启用时）|
| 跨 session 恢复（§9） | 100% |

---

## 5. 端到端集成场景（12 个）

### 5.0 场景索引

| # | 场景 | 类型 | 涉及 L1 |
|---|---|---|---|
| 1 | WP 执行正常一轮 Quality Loop | 正常 | L1-01/02/03/04/05 |
| 2 | 项目从 S1 启动到 S7 交付完整流程 | 正常 | 全部 |
| 3 | S2 Gate No-Go + 4 件套部分重做 | 正常变体 | L1-01/02/03/10 |
| 4 | 运行时 change_request（TOGAF H）影响面分析 | 正常变体 | L1-01/02/03/04/10 |
| 5 | 硬红线触发（不可逆操作拦截）| 异常 | L1-01/05/07/10 |
| 6 | 用户 panic + state=PAUSED + resume | 异常 | L1-01/02/10 |
| 7 | S5 verifier FAIL → 4 级回退路由 | 异常 | L1-04/07 |
| 8 | 跨 session 重启恢复未决 Gate | 韧性 | L1-01/02/09/10 |
| 9 | 同级 FAIL ≥ 3 死循环升级 | 异常 | L1-04/07 |
| 10 | KB 晋升仪式（S7 收尾时）| 正常 | L1-02/05/06 |
| 11 | 多项目并发：用户在两 project 间切换（V2+）| PM-14 | L1-10/01/09 |
| 12 | 大代码库 onboarding 委托 | 多模态 | L1-08/05/06 |

### 5.1 场景 1 · WP 执行正常一轮 Quality Loop

**前置**：project foo 在 PLAN_TDD state，L1-03 拓扑中 WP-07 依赖已满足。

**流程**：
1. **L1-10** 用户点"下一 WP" → IC-17 user_intervene → L1-01
2. **L1-01** tick: 决策 = 取下一 WP → IC-02 get_next_wp(project_id=foo) → L1-03
3. **L1-03** 按拓扑找 WP-07 → 返回 wp_def
4. **L1-01** 决策 = 进 Quality Loop → IC-03 enter_quality_loop(project_id=foo, wp_def=WP-07) → L1-04
5. **L1-04 S4** tick: 决策 = 调 tdd skill → IC-04 invoke_skill(project_id=foo) → L1-05
6. **L1-05** 调 tdd → 接收代码 + 测试
7. **L1-04 S4** 测试绿 + WP-DoD 自检 PASS → 进 S5
8. **L1-04 S5** → IC-20 delegate_verifier(project_id=foo) → L1-05
9. **L1-05** 委托 verifier 子 Agent → 独立 session → 返回 report
10. **L1-04 S5** 组装三段证据链 → verdict = PASS
11. **L1-04** 反馈到 **L1-01** → 决策 = 取下一 WP（回 step 2）

**并行**：
- **L1-07** 每 30s 读 L1-09 事件总线 → 8 维度正常 → INFO 级"WP-07 完成"
- **L1-09** 全程 IC-09 append_event 落盘 `projects/foo/events.jsonl`
- **L1-10** 收 progress_stream 实时刷新 UI

**集成验证点**：
- IC-02 / IC-03 / IC-04 / IC-20 调用顺序正确
- 全部 IC 携带 project_id=foo
- L1-09 events.jsonl 中事件 hash 链完整
- L1-07 supervisor 事件按 project foo 订阅
- 端到端时延 ≤ 30 min（典型 WP）

### 5.2 场景 2 · S1→S7 完整项目流程

**前置**：用户首次启动 HarnessFlow，无任何 project。

**流程**：
1. **L1-10** 用户输入项目目标 → IC-17 user_intervene(type=clarify, payload=项目目标) → L1-01
2. **L1-01** 决策 = 进入 S1 启动 → IC-01 request_state_transition(to=CLARIFY) → L1-02
3. **L1-02 L2-02** 启动澄清子流程：委托 brainstorming skill 与用户对话（≤ 3 轮）
4. **L1-02 L2-02** 澄清通过 → **生成 harnessFlowProjectId（PM-14 创建点）**+ 写 manifest.yaml + 发 `project_created` 事件
5. **L1-02 L2-02** 生成 charter / stakeholders / goal_anchor_hash
6. **L1-02 L2-01** 触发 S1 Gate → IC-16 push_stage_gate_card → L1-10
7. **L1-10** 用户 review → 点 Go → IC-17 user_intervene(type=authorize) → L1-01
8. **L1-01** 决策 = 切到 PLAN → IC-01 → L1-02 进 S2
9. **L1-02 L2-03** 4 件套串行生成（needs/goals/AC/quality）→ `4_pieces_ready` 事件
10. **L1-02 L2-04** 9 计划生成 + L1-02 L2-05 TOGAF A→B→C→D 生成 + ADR ≥ 10 → 各 ready 事件
11. **L1-02 L2-01** 收齐信号 + 触发 IC-19 request_wbs_decomposition → **L1-03**
12. **L1-03** 按 4 件套 + TOGAF 拆 WBS → 返回 wbs_topology
13. **L1-02 L2-01** 触发 S2 Gate → IC-16 → L1-10 → 用户 Go
14. **L1-01** 切 TDD_PLAN → L1-04 接手 S3
15. **L1-04** 生成 TDD 蓝图（master-test-plan + DoD 表达式 + test 骨架 + quality-gates + acceptance-checklist）
16. **L1-04** S3 蓝图齐 → 触发 S3 Gate（经 L1-02 L2-01）→ L1-10 → 用户 Go
17. **L1-01** 切 IMPL → 进入 WP 执行循环（场景 1 重复 N 次）
18. 全部 WP done + 全部 S5 PASS → state=RETRO_CLOSE → **L1-02 L2-06** 接手 S7
19. **L1-02 L2-06** 5 步收尾：交付包打包 / retro 委托 / archive 委托 / KB 晋升 / 最终 Gate
20. **L1-02 L2-01** 触发 S7 Gate → L1-10 → 用户 Go
21. **L1-01** 切 CLOSED → **L1-09 冻结 project foo 根目录（只读）**
22. project foo 主状态 = CLOSED · 系统返回 IDLE 等下一 project

**集成验证点**：
- `project_created` 事件在 step 4 准时发出
- manifest.yaml 含完整字段（project_id / goal_anchor_hash / version / status）
- 所有产出物落在 `projects/<foo>/` 子树
- 4 次 Stage Gate 都正确推 + 阻塞 + 用户决定
- 最后归档时 events.jsonl 不再接受新事件
- 端到端时延：典型中等项目 1-3 周墙钟

### 5.3 场景 3 · S2 Gate No-Go + 4 件套部分重做

**前置**：场景 2 进展到 step 13（S2 Gate 推出）。

**流程**：
1. **L1-10** 用户 review S2 Gate bundle → 发现 AC-03 需修改 → 点 reject + 附 change_requests=['改 AC-03 增加边界条件']
2. **L1-10** → IC-17 → IC-L2-04 → **L1-02 L2-01**
3. **L1-02 L2-01** analyze_impact → 影响 L2-03 ['acceptance_criteria', 'quality_standards']（级联）
4. **L1-02 L2-01** → IC-L2-01 trigger_stage_production(target_subset=['ac', 'quality']) → L2-03
5. **L1-02 L2-03** 备份 v1 → 重做 AC + quality（依赖闭包）→ 发 `4_pieces_ready_v2`
6. **L1-02 L2-01** 收 v2 信号 → 重新打包 bundle（含 diff_from_previous_gate=v1）→ IC-16 推新 Gate 卡片
7. **L1-10** 用户二次 review → 点 Go
8. 流程回到场景 2 step 14 继续

**集成验证点**：
- 旧 v1 文件保留作 backup
- 影响面分析准确（不漏算下游）
- diff 视图正确
- L1-09 中 v1 / v2 都有审计记录
- 时延：影响面分析 ≤ 5s，重做 ≤ 10 min

### 5.4 场景 4 · 运行时 change_request（TOGAF H）

**前置**：项目在 IMPL state，L1-04 正跑 WP-05 S4。

**流程**：
1. **L1-10** 用户发 change_request："我想改 WP-05 验收标准"
2. → IC-17 user_intervene(type=change_request) → L1-01 → 路由到 **L1-02 L2-01**
3. **L1-02 L2-01** 创建临时"虚 Gate"进 ANALYZING 状态
4. **L1-02 L2-01** analyze_impact → 影响 L2-03 (AC) + L1-03 (WBS 可能重拆) + L1-04 (TDD 蓝图重做 + 已实现的 WP-05 测试失效)
5. **L1-02 L2-01** generate_impact_report (ADR 风格) → save `docs/adr/CR-001.md`
6. **L1-02 L2-01** 推影响面报告给用户
7. **L1-10** 用户审批 → 二次决定
   - **批准**：触发重做链 → L1-04 可能需要先 pause 当前 WP-05 → state 可能回退到 PLAN（重新 S2 Gate）
   - **取消**：销毁虚 Gate，原工作继续
8. （批准路径）后续走类似场景 3 的重做链 + Gate

**集成验证点**：
- 影响面分析涉及多 L1（L2-03 / L1-03 / L1-04）准确
- ADR 落盘格式合规
- 时延：影响面分析 ≤ 5s
- 用户取消则系统状态完全不变（ANALYZING → 销毁）

### 5.5 场景 5 · 硬红线触发（不可逆操作拦截）

**前置**：项目在 IMPL state，L1-01 决策调 tdd skill 实现功能 X。

**流程**：
1. **L1-01** → IC-04 invoke_skill(skill=tdd) → L1-05
2. **L1-05** 调 tdd → tdd 准备执行 `rm -rf some/path`
3. **L1-05** → IC-09 append_event "Bash: rm -rf" → L1-09 落盘
4. **L1-07** scan 事件 → 命中"不可逆操作硬红线"（如 IRREVERSIBLE_HALT）
5. **L1-07** → IC-15 request_hard_halt(red_line_id=IRREVERSIBLE_HALT) → L1-01
6. **L1-01** 立即 halt（≤ 100ms）+ state = HALTED
7. **L1-01** → IC-14（间接）+ IC-16 推强告警卡片到 L1-10
8. **L1-10** 显示告警 + 等用户授权
9. **L1-10** 用户 IC-17 user_intervene(type=authorize, payload=true/false) → L1-01
10. （授权）→ tdd 继续；（拒绝）→ 撤销 tdd 调用 + 决策 alternative

**集成验证点**：
- L1-07 检测到 ≤ 30s（监督周期）
- L1-01 halt 响应 ≤ 100ms
- 用户授权前 100% 阻塞
- L1-09 全过程审计

### 5.6 场景 6 · 用户 panic + PAUSED + resume

**前置**：项目在任意 EXECUTING state。

**流程**：
1. **L1-10** 用户点 panic 按钮 → IC-17 user_intervene(type=pause) → L1-01
2. **L1-01 L2-01** 立即 ≤ 100ms 中断 current tick → state=PAUSED
3. **L1-01** → IC-09 append_event(panic_intercepted) → L1-09
4. 系统冻结：无 tick 派发，但事件总线仍可收异步结果
5. **L1-10** 显示 PAUSED 提示
6. **L1-10** 用户决定 resume → IC-17 user_intervene(type=resume) → L1-01
7. **L1-01** state=PAUSED → IDLE → 继续处理 pending queue

**集成验证点**：
- panic 响应 ≤ 100ms
- PAUSED 期间不漏事件（异步结果仍入队）
- resume 后从中断点继续，不重做已完成

### 5.7 场景 7 · S5 verifier FAIL → 4 级回退路由

**前置**：场景 1 进到 step 10，verifier verdict=FAIL。

**流程**：
1. **L1-04 S5** verdict=FAIL → IC-09 append_event(s5_fail) → L1-09
2. **L1-04 S5** 自身判定偏差等级（轻/中/重/极重）
3. （等级 = 中度）→ 路由到 S3 重做 TDD 蓝图
4. **L1-04** 内部 state 回 S3 → 重生成蓝图（针对 FAIL 部分）
5. **L1-04** 再次跑 S4 + S5 → verdict
6. **如果同级再次 FAIL**：累计 += 1，到 3 次 → 升级到上一级（重 → 极重）
7. **L1-07** 并行 scan → 也发现同级 FAIL ≥ 3 → IC-14 push_rollback_route(level=L4, target_state=S1) → L1-04

**集成验证点**：
- verdict 三态严格（PASS / INSUFFICIENT / FAIL）
- 同级 FAIL 计数按 project 限定（不跨 project 累）
- 同级 ≥ 3 自动升级
- L1-07 也独立监测一次（双重保险）

### 5.8 场景 8 · 跨 session 重启恢复未决 Gate

**前置**：用户在 S2 Gate 评审中（state=REVIEWING，bundle 已推），临时关闭 Claude Code。

**流程**：
1. （用户重启 Claude Code）
2. **L1-09** bootstrap 读 `projects/_index.yaml` → 找最近活跃 project foo
3. **L1-09** 重建 task-board（从 events.jsonl 回放 + checkpoints 加速）
4. **L1-09** 发 `system_resumed` 事件（带 project_id=foo）
5. **L1-01 L2-01** bootstrap tick 触发（priority=100）
6. **L1-01 L2-02** 决策：检查未决 Gate
7. → 调 **L1-02 L2-01** query_open_gates(project_id=foo)
8. **L1-02 L2-01** 从持久化读 → 找到 gate_S2_abc state=REVIEWING
9. **L1-02 L2-01** 校验 artifacts_bundle 文件 hash 是否仍在
10. （文件齐全）→ 重新 push_gate_card(resumed_from_checkpoint=true) → L1-10
11. **L1-10** UI 显示 Gate 卡片（带"已恢复"标记）
12. 用户继续评审 + 决定

**集成验证点**：
- bootstrap 优先级 = 100（最高）
- 跨 session manifest 完整恢复 project_id
- artifacts_bundle 文件 hash 校验
- UI 上显示"已恢复"标记
- 时延：bootstrap 完成 ≤ 5s（中等项目）

### 5.9 场景 9 · 同级 FAIL ≥ 3 死循环升级

**前置**：项目在 IMPL，WP-03 经历多次失败。

**流程**：
1. **L1-04** S5 第 1 次 FAIL（轻度）→ 回 S4 重做
2. **L1-04** S5 第 2 次 FAIL（同级轻度）→ 回 S4 重做（计数 = 2）
3. **L1-04** S5 第 3 次 FAIL（同级轻度）→ **同级 ≥ 3 触发升级**
4. **L1-04** 自动升级 → 走中度路径，回 S3 重做 TDD 蓝图
5. （并行）**L1-07** 监测同级 FAIL ≥ 3 → IC-14 push_rollback_route(level=L2, target_state=S3) → L1-04（双重保险）
6. **L1-04** 收 IC-14 → 与自身升级一致 → 执行 S3 重做

**集成验证点**：
- 计数按 project 隔离
- 同级 ≥ 3 双重检测（L1-04 自身 + L1-07）一致
- 升级链：轻 → 中 → 重 → 极重
- 极重 → 极重 ≥ 3 → state=FAILED_TERMINAL → S7 失败闭环

### 5.10 场景 10 · KB 晋升仪式（S7 收尾时）

**前置**：项目接近 S7 完结。

**流程**：
1. **L1-02 L2-06** 进入 S7 Step 4（KB 晋升）
2. **L1-02 L2-06** 调 IC-06 kb_read(scope=session, project_id=foo) → 读本 session 候选
3. 对每个候选：
   - observed_count >= 3 → IC-08 kb_promote(target_scope=project) → L1-06
   - 否则 → 推到 L1-10 用户 review 列表
4. （用户在 UI 上勾选要晋升的）→ IC-17 → IC-08 kb_promote(...)
5. **L1-06** 把条目从 session 层移到 project 层（`projects/foo/kb/`）
6. （部分晋升到 global）→ 从 project 层移到 `global_kb/`（脱离 project 归属）
7. **L1-09** IC-09 全过程审计

**集成验证点**：
- observed_count 计算正确
- 晋升条目跨层移动正确
- global 层条目脱离 project 归属
- 审计完整

### 5.11 场景 11 · 多项目并发切换（V2+ PM-14）

**前置**：V2+ 启用，project foo 和 bar 都活跃，foo 在 IMPL，bar 在 PLANNING。

**流程**：
1. （当前激活 foo）**L1-01** 在 foo 上跑 tick
2. **L1-10** 用户在 UI 切换到 bar（点 Admin → 切换 project）
3. **L1-10** → IC-17 user_intervene(type=switch_project, payload={target=bar}) → L1-01
4. **L1-01** Save foo checkpoint → Load bar checkpoint
5. **L1-01** 主 loop 上下文换 → 后续 tick 全部带 project_id=bar
6. **L1-09** 主路径切：`projects/bar/events.jsonl` 读写
7. **L1-07** （V2+ 双 supervisor）已有的 bar supervisor 实例继续监督
8. **L1-10** 所有 UI 视图（task-board / Gate / KB / 进度）自动按 bar 过滤刷新

**集成验证点**：
- 切换响应 ≤ 1s
- 切换前后无数据交叉污染
- foo 的 supervisor 不监督 bar 的 tick
- KB 读默认作用域换为 bar + global（不读 foo）

### 5.12 场景 12 · 大代码库 onboarding 委托

**前置**：用户基于现有 50 万行代码仓库做 brownfield 项目。

**流程**：
1. **L1-02 L2-02** S1 启动时识别 brownfield 模式 → 需要先理解代码结构
2. **L1-08** → IC-11 process_content(type=code, path=repo) → 检测代码量 > 10 万行
3. **L1-08** → IC-12 delegate_codebase_onboarding(repo_path) → L1-05
4. **L1-05** 委托 codebase-onboarding 子 Agent → 独立 session
5. 子 Agent 用 Glob+Grep+Read 系统扫描 → 生成 structure_summary + 候选 KB entries
6. 子 Agent 完成 → IC-09 append_event(subagent_result) → L1-09
7. **L1-08** 收异步结果 → kb_entries 通过 IC-07 写到 project 层
8. **L1-08** 返回 structure_summary 给 L1-02 → 用作 S1 章程背景

**集成验证点**：
- 大代码库委托不阻塞主 loop
- 子 Agent 独立 session（不污染主 session 上下文）
- KB entries 写入 project 层（不进 global）
- 缓存键 = project_id + git_head（防同 repo 不同 commit 误命中）

---

## 6. 失败传播详细矩阵

### 6.1 单 L1 失败时的传播链

| 失败 L1 | 直接影响 | 间接影响 | 兜底策略 |
|---|---|---|---|
| **L1-01 主 loop** | 无 tick 派发 → 系统停滞 | 全部下游空闲 | bootstrap 重启或硬重启；事件总线落盘最近状态可恢复 |
| **L1-02 项目生命周期** | state 转换被拒 / Gate 推不出 | L1-03/04 无产出依赖 → 阻塞 | L1-09 持久化兜底；用户手动推进备份路径 |
| **L1-03 WBS 调度** | get_next_wp 返回 err | L1-01 无 WP 可调度 | 降级：手工指定 WP（用户在 UI）|
| **L1-04 Quality Loop** | enter_quality_loop 失败 | L1-01 无质量验证 | 紧急降级：跳过自动质量门，用户手工签 |
| **L1-05 Skill 调度** | invoke_skill 失败 | 多 L1 调用失败 → 走 BF-E-05 fallback 链 | 主 skill→备选 skill→主 session 简化跑→失败告警 |
| **L1-06 KB** | kb_read 失败 | 无 KB 上下文（决策弱化） | 降级：无 KB 模式继续，仅告警 |
| **L1-07 监督** | suggestion 推不出 | 监督失效 | （仅警告，不阻塞主流）+ 自动重启 supervisor 副 Agent |
| **L1-08 多模态** | process_content 失败 | 多模态产出受影响 | 降级：仅文本路径继续 |
| **L1-09 韧性+审计** | append_event 失败 | **halt 整个系统**（PM-08 单一事实源不可破）| 严重：等 L1-09 恢复才解 halt；用户无法绕过 |
| **L1-10 UI** | UI 推不出 / 查不到 | 用户无感知 | （后端不阻塞）+ UI 故障降级到 CLI 提示 |

### 6.2 失败传播的 PM-14 维度

**关键规则**：失败传播**不能跨 project 蔓延**。

| 失败场景 | 跨 project 影响 |
|---|---|
| project foo 的 L1-04 Quality Loop 失败 | ❌ 不影响 project bar 的 Quality Loop |
| project foo 的 L1-09 写盘失败（halt） | ⚠️ 系统级 halt（影响所有 project，因 L1-09 是共享层）|
| project foo 的 L1-07 supervisor 失败 | ❌ 不影响 project bar 的 supervisor（独立实例）|
| L1-05 子 Agent 委托失败 | ❌ 仅影响触发委托的那个 project |

**唯一系统级 halt 来源**：L1-09 持久化失败 → 全系统 halt（因事件总线是共享层）。

### 6.3 失败级联链（典型 3 步）

```
[L1-05 invoke_skill 主 skill 失败]
       ↓ BF-E-05 fallback
[L1-05 走备选 skill]
       ↓ 仍失败
[L1-05 降级到主 session 简化跑]
       ↓ 仍失败
[L1-05 IC-09 append_event(skill_fail) → L1-09]
       ↓
[L1-07 监测 → 标"质量"或"重试 Loop"维度告警]
       ↓
[L1-04 收降级 → 视严重度判 INSUFFICIENT 或 FAIL]
       ↓
[L1-04 重新调 IC-04 invoke_skill(其他 capability)]
```

---

## 7. 性能集成约束

### 7.1 端到端时延阈值（典型场景）

| 场景 | 目标时延 | 上限 |
|---|---|---|
| 单 tick（含 L1-02/03/04/05 各一调）| ≤ 5s | 30s（硬约束）|
| Stage Gate 推送（L1-02→L1-10）| ≤ 2s | 5s |
| 用户 Go → state 切换 | ≤ 1s | 3s |
| panic → state=PAUSED | ≤ 100ms | 500ms |
| hard_halt → state=HALTED | ≤ 100ms | 500ms |
| change_request 影响面分析 | ≤ 5s | 10s |
| KB 读取 | ≤ 500ms | 2s |
| 事件落盘（IC-09）| ≤ 50ms | 200ms |
| 跨 session bootstrap | ≤ 5s | 15s（中等项目）|
| 单 WP 端到端 Quality Loop | ≤ 30 min | 2h |
| 中等项目端到端（S1→S7）| 1-3 周墙钟 | 4 周 |

### 7.2 吞吐阈值

| 维度 | 目标 |
|---|---|
| L1-01 tick 吞吐 | ≥ 100 tick/s（无外部 IO） |
| 事件总线写入 QPS | ≥ 200 |
| KB 读 QPS | ≥ 50 |
| L1-08 多模态处理（小图）| ≥ 10/s |
| 多 project 并发数（V2+） | ≥ 10 |

### 7.3 资源约束

| 资源 | 限额 |
|---|---|
| 单 project 工作目录大小 | ≤ 10 GB（含交付包 / 检查点 / KB）|
| 事件总线单文件 | 滚动切分 ≥ 100 MB 即新建（按月）|
| supervisor 副 Agent 内存 | ≤ 500 MB |
| 子 Agent 单 session 上下文 | ≤ 200K tokens |

---

## 8. 多项目并发集成（PM-14 V2+）

### 8.1 V1 / V2 / V3 渐进规划

| 版本 | 多 project 模式 | 说明 |
|---|---|---|
| **V1** | **单 project 活跃** | 同时刻只有一个 project，切换需 Save+Load |
| **V2+** | **多 project 挂起，UI 切当前** | 多个 project 在 manifest 中标活跃，主 loop 按"当前 project"路由 |
| **V3+** | **多用户多 project** | 加 tenant_id 层 · 当前不实现但模型兼容 |

### 8.2 V2+ 多 project 集成设计

**架构关键变更**：
- L1-01 主 loop 实例：仍 1 个，但 tick 上下文按"当前 project"路由
- L1-07 supervisor：每 project 一独立实例，事件流分离
- L1-09 持久化：物理隔离不变（已 V1 起按 project 分目录）
- L1-10 UI：增"切换 project" + Admin 多 project 浏览
- L1-06 KB：默认作用域从"当前 project + global"自动切换
- L1-05 子 Agent 委托：context 必带正确 project_id

**关键 IC 调整**：
- IC-17 新增 type=switch_project（用户切换当前 project）
- IC-09 不变（已含 project_id）
- 其他 IC 不变（已要求 project_id）

### 8.3 多 project 并发集成测试用例

| # | 场景 | 验证点 |
|---|---|---|
| MP1 | 同时挂 foo + bar，激活 foo → tick 全在 foo | 上下文隔离 |
| MP2 | 切换到 bar → tick 全在 bar | 切换正确 |
| MP3 | foo 跑 S4 期间切到 bar，回 foo 后从中断点继续 | Save/Load 正确 |
| MP4 | foo 的 supervisor 不监督 bar | supervisor 隔离 |
| MP5 | foo 的 KB read 不返回 bar 的条目 | KB 隔离 |
| MP6 | bar 的 Gate 卡片不推到 foo 的 UI 视图 | UI 隔离 |
| MP7 | foo 的 supervisor 红线不停 bar 的推进 | 红线作用域 |
| MP8 | 同时 10 个 project（性能压力测试）| 资源 + 性能不退化 |

### 8.4 V1 → V2+ 迁移成本

由于 V1 已严格按 project_id 隔离（PM-14 设计），V2+ 升级**几乎无破坏性变更**：

- L1-09 已按 project 物理分目录 → 无需迁移
- 各 L1 的 IC 已要求 project_id → 无需修
- 只需补：L1-10 UI 切换功能 + L1-07 多 supervisor 调度

---

## 9. 跨 session 恢复集成验证

### 9.1 恢复完整性 4 级

| Tier | 恢复程度 | 触发条件 |
|---|---|---|
| **Tier 1 完美** | 全部 task-board / state / 进行中 WP / Gate / 子 Agent 都恢复 | events.jsonl + checkpoint 完整 |
| **Tier 2 良好** | task-board / state 恢复，进行中 WP 标 INTERRUPTED 待用户决定续跑/重做 | events.jsonl 完整，checkpoint 部分缺失 |
| **Tier 3 退化** | state 回退到最近 Gate 通过点 | events.jsonl 部分损坏（hash 链断裂）|
| **Tier 4 灾难** | 仅 manifest 可读，强制用户重启 project（保留产出物供导出）| events.jsonl 重大损坏 |

**禁止**：从 Tier 4 自动重建空白 task-board（PM-08 不可破）。

### 9.2 跨 session 集成测试用例

| # | 场景 | 验证 Tier |
|---|---|---|
| RC1 | 正常退出 + checkpoint 写完 + 重启 | Tier 1 |
| RC2 | Ctrl+C 急停 + 重启 | Tier 1 或 2 |
| RC3 | 进程 kill -9 + 重启 | Tier 2（events 完整 但 checkpoint 缺）|
| RC4 | 磁盘损坏 events.jsonl 最后 N 条 | Tier 3 |
| RC5 | manifest.yaml 完好 + 其他全损 | Tier 4（强制 reset）|
| RC6 | 跨设备恢复（同步 projects/ 目录到新机器）| Tier 1 |
| RC7 | bootstrap 期间硬红线还在生效 → state=HALTED 恢复后保持 | 状态恢复正确 |
| RC8 | 未决 Gate 在 bootstrap 后重推 UI 卡片 | Gate 恢复正确 |

---

## 10. 集成验证大纲（TDD 输入）

### 10.1 Master Test Plan 锚定

本节是给 `docs/3-2-Solution-TDD/integration/master-test-plan.md` 的输入草案。

**测试金字塔**：

| 层级 | 测试数量预估 | 内容 |
|---|---|---|
| **L0 单元**（各 L1 内部，归各 L1 PRD §X.9）| ~500 | 各 L1 单测（不在本 PRD）|
| **L1 IC 契约**（每 IC 5 用例）| ~100 | §3 每 IC 的 4-5 用例 |
| **L2 两两 L1 集成**（必测对 25 + 弱依赖 20，每对 4 用例）| ~150 | §4 矩阵 |
| **L3 端到端集成**（12 场景 × 平均 3-5 子用例）| ~50 | §5 |
| **L4 性能集成**（§7 阈值）| ~20 | §7 |
| **L5 多项目并发**（V2+，§8 8 用例 + 边界）| ~15 | §8 |
| **L6 跨 session 恢复**（§9 8 用例 + 边界）| ~15 | §9 |
| **总计** | ~850 | — |

### 10.2 集成验收硬约束

| 维度 | 必达指标 |
|---|---|
| IC 契约一致性测试通过率 | 100% |
| 端到端场景全过 | 12/12 |
| 性能阈值（§7）| 全部硬约束达标 |
| 多项目并发（V2+）| 8 用例全过 |
| 跨 session 恢复 | Tier 1-3 用例全过 |
| 无 PM-14 违规（无 project_id 事件）| 0 |

### 10.3 集成验收 Given-When-Then 模板（10 例）

**A1 · 端到端 S1→S7 集成**
- **Given** 用户输入完整项目目标 + 资源约束
- **When** 系统按场景 2 跑完 S1→S7
- **Then** 项目主状态 = CLOSED，交付包齐全，retro / archive 都生成

**A2 · 单 WP Quality Loop 集成**
- **Given** project 在 IMPL state，下一 WP 准备就绪
- **When** 系统按场景 1 跑完一轮 Quality Loop
- **Then** WP 标 done，verifier verdict = PASS，下一 tick 取下一 WP

**A3 · S2 Gate No-Go 重做集成**
- **Given** S2 Gate 推出，bundle 完整
- **When** 用户 reject + 附 change_requests
- **Then** 影响面分析 → 重做受影响产出 → 重推 Gate（带 diff）

**A4 · 硬红线集成**
- **Given** 项目 IMPL 期间出现不可逆操作
- **When** L1-07 检测到红线
- **Then** L1-01 ≤ 100ms halt + 用户授权前 100% 阻塞

**A5 · panic 集成**
- **Given** 项目任意 EXECUTING state
- **When** 用户点 panic
- **Then** ≤ 100ms PAUSED + 不漏异步事件 + resume 后从中断点继续

**A6 · 4 级回退路由集成**
- **Given** S5 verifier verdict = FAIL（中度）
- **When** L1-04 / L1-07 双重判定
- **Then** 路由到 S3 重做 TDD 蓝图，同级 ≥ 3 自动升级到重度

**A7 · 跨 session 恢复 Tier 1 集成**
- **Given** project 正常关闭 + checkpoint 完整
- **When** 用户重启 + bootstrap
- **Then** 完整恢复 task-board / state / Gate / WP，无数据丢失

**A8 · KB 晋升集成**
- **Given** 项目接近 S7，session 层有候选 KB 条目
- **When** L1-02 L2-06 进入 KB 晋升步骤
- **Then** observed_count >= 3 自动晋升 / 用户批准的也晋升 / 跨层移动正确

**A9 · 多 project 切换集成（V2+）**
- **Given** foo 和 bar 都活跃，foo 当前激活
- **When** 用户在 UI 切到 bar
- **Then** ≤ 1s 上下文换 + 视图刷新，foo 数据保护未污染

**A10 · 大代码库 brownfield 集成**
- **Given** 用户输入 brownfield 项目 + 50 万行 repo
- **When** L1-08 检测大代码库 + 委托 onboarding
- **Then** 子 Agent 独立 session 跑完，KB 写 project 层，主 loop 不阻塞

---

## 11. 集成里程碑 + Gate

### 11.1 集成里程碑表

| 里程碑 | 完成标志 | Gate 通过条件 |
|---|---|---|
| **IM-1 IC 契约测试齐** | §3 20 IC × 5 用例 ≈ 100 用例全实现 | 100% 通过 |
| **IM-2 必测对集成测试齐** | §4 必测对 25 × 4 用例 = 100 用例全实现 | 100% 通过 |
| **IM-3 端到端 12 场景齐** | §5 全 12 场景的子用例实现 | 12/12 通过 |
| **IM-4 性能阈值达标** | §7 全部硬约束的性能测试实现 | 全部达标 |
| **IM-5 跨 session 恢复齐** | §9 RC1-RC8 实现 | Tier 1-3 全过，Tier 4 走预期失败路径 |
| **IM-6 多项目并发（V2+）** | §8 MP1-MP8 实现 | V2+ 启动后全过 |
| **IM-7 PM-14 全链合规** | 全程 0 个无 project_id 事件 | 通过自动审计扫描 |
| **IM-8 集成完稿冻结** | 上述全完成 + 用户最终验收 | v1.0-integration-frozen |

### 11.2 集成测试关键约束

- 集成测试**禁止 mock L1-09**（事件总线必须真实落盘）
- 集成测试**必须用真实 project_id**（不允许 hardcode "test_project"）
- 集成测试**必须按 project 隔离运行**（不允许多 case 共享 project）

---

## 附录 A · 术语

| 术语 | 含义 |
|---|---|
| **L1 集成** | 10 个独立 L1 之间的契约一致性 + 端到端协作 |
| **IC 一致性** | 一对 L1 之间通过 IC 通信的字段 / 行为 / 时序符合 scope §8.2 定义 |
| **必测对** | §4 矩阵中标 ● 的 L1 对（有主 IC 关系）|
| **弱依赖对** | 标 ○ 的 L1 对（有契约但非主线）|
| **集成场景** | 一个完整的端到端业务流程（涉及 ≥ 3 L1）|
| **失败传播** | 一个 L1 失败时对其他 L1 的影响 |
| **Tier 1-4 恢复** | 跨 session 恢复的 4 个完整度等级（§9.1）|
| **PM-14 全链合规** | 全过程 0 个无 project_id 的事件 |

---

## 附录 B · 端到端场景索引

| # | 场景 | 主 L1 | §|
|---|---|---|---|
| 1 | WP Quality Loop | L1-01/02/03/04/05 | §5.1 |
| 2 | S1→S7 完整流程 | 全部 | §5.2 |
| 3 | S2 Gate No-Go 重做 | L1-02/03/10 | §5.3 |
| 4 | 运行时 change_request | L1-02/03/04/10 | §5.4 |
| 5 | 硬红线拦截 | L1-05/07 | §5.5 |
| 6 | panic + resume | L1-01/10 | §5.6 |
| 7 | 4 级回退路由 | L1-04/07 | §5.7 |
| 8 | 跨 session 恢复未决 Gate | L1-01/02/09/10 | §5.8 |
| 9 | 同级 FAIL ≥ 3 升级 | L1-04/07 | §5.9 |
| 10 | KB 晋升仪式 | L1-02/05/06 | §5.10 |
| 11 | 多 project 切换（V2+）| L1-10/01/09 | §5.11 |
| 12 | 大代码库 onboarding | L1-08/05/06 | §5.12 |

---

## 附录 C · IC 一致性检查清单

每条 IC 必查（§3 详化）：

- [ ] 字段 schema 符合 scope §8.2 定义
- [ ] **PM-14：携带 project_id（或显式 system 哨兵）**
- [ ] 正向用例通过
- [ ] 至少 1 个负向用例通过
- [ ] 失败降级路径通过
- [ ] 事件落盘审计通过（IC-09 关联）
- [ ] 性能阈值达标（§7）
- [ ] 跨 session 一致性（IC 在 bootstrap 后表现一致）

---

*— L1 集成 PRD v1.0 草案完 · 等待 user review · 通过后冻结作为 TDD 集成蓝图输入 —*
