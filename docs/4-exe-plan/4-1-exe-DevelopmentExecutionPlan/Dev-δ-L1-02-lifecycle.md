---
doc_id: exe-plan-dev-delta-L1-02-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α-L1-09-resilience-audit.md（标杆）
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/architecture.md
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-01 ~ L2-07.md（7398 行）
  - docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-01 ~ L2-07-tests.md（13505 行 · 409 TC）
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.1 IC-01 · §3.19 IC-19 · §3.16 IC-16
version: v1.0
status: draft
author: main-session
assignee: Dev-δ（拆 δ1 + δ2 · 2 会话接力）
wave: 2-3
priority: P0（PM-14 pid 创建 + 归档唯一入口）
estimated_loc: ~13300 行
estimated_duration: 7 天（δ1 · 4 天 + δ2 · 3 天）
---

# Dev-δ · L1-02 项目生命周期编排 · Execution Plan

> **组一句话**：7 L2 · S1-S7 全生命周期 · **PM-14 pid 创建（L2-02）+ 归档（L2-06）唯一入口** · Stage Gate 控制（L2-01）+ 4 件套/PMP/TOGAF 产出器（L2-03/04/05）+ 模板引擎（L2-07）。
>
> **拆批**：δ1 做 L2-07（地基）+ L2-02（PM-14 起点）+ L2-03（4 件套）+ L2-01（Gate 控制器）= 4 L2 · 4 天。δ2 做 L2-04（PMP）+ L2-05（TOGAF）+ L2-06（收尾）= 3 L2 · 3 天。
>
> **依赖**：Dev-α IC-09 mock · Dev-β IC-06 mock（KB 历史）· Dev-θ1 UI Gate 卡片 mock（IC-16 消费方）· Dev-ε L1-03 IC-19 消费方（WBS 拆解）。

---

## §0 撰写进度

- [x] §1 组定位 + 7 L2 + δ1/δ2 拆批
- [x] §2 源文档导读
- [x] §3 WP 拆解（8 WP · 7 天）
- [x] §4 依赖图 + mock
- [x] §5 standup（复用）
- [x] §6 自修正
- [x] §7 对外契约
- [x] §8 DoD（PM-14 特化）
- [x] §9 风险
- [x] §10 交付清单

---

## §1 组定位

### 1.1 7 L2 清单 · δ1/δ2 拆批

**δ1 批**（4 天 · 4 L2 · 一个会话）：

| L2 | 职责 | 估时 | IC |
|:---:|:---|:---:|:---|
| L2-07 产出物模板引擎 | 无状态 Domain Service · Jinja2 sandboxed · 被 L2-02/03/04/05/06 调 | 1 天 | 内部 |
| L2-02 启动阶段产出器 | S1 章程（Goal.md + PrdScope.md）· **PM-14 pid 创建唯一入口** | 1 天 | 内部 |
| L2-03 4 件套生产器 | Scope/PRD/Plan/TDD 4 件套（S2）| 1 天 | 内部 |
| L2-01 Stage Gate 控制器 | 7 阶段 × 4 Gate（S1-S7）主状态机 · **IC-01 接收方** | 1 天 | **IC-01** |

**δ2 批**（3 天 · 3 L2 · 接力会话）：

| L2 | 职责 | 估时 | IC |
|:---:|:---|:---:|:---|
| L2-04 PMP 9 计划生产器 | PMP 9 知识域（integration/scope/schedule/.../procurement）· 并发产出 | 1.25 天 | 内部 |
| L2-05 TOGAF ADM 架构生产器 | TOGAF 9 Phase（A-H + Preliminary）· 串行产出 · togaf_d_ready 提前信号 | 1 天 | 内部 |
| L2-06 收尾阶段执行器 | S6 lessons + S7 archive（tar.zst）· **PM-14 pid 归档唯一入口** | 0.75 天 | 内部 |

**合计** 7 L2 · 13300 行代码 · 7 天 · **对外 IC-01 + IC-19 发起 + IC-16 发起 + IC-17 接收**。

### 1.2 代码目录

```
app/l1_02/
├── stage_gate/            # L2-01 · Stage Gate 控制器
├── kickoff/               # L2-02 · 启动阶段（PM-14 pid 创建）
├── four_set/              # L2-03 · 4 件套生产器
├── pmp/                   # L2-04 · PMP 9 计划
├── togaf/                 # L2-05 · TOGAF 9 Phase
├── closing/               # L2-06 · 收尾执行器（PM-14 pid 归档）
└── template_engine/       # L2-07 · Jinja2 sandboxed 引擎（被上面调）
```

---

## §2 源文档导读

| 优先级 | 文档 | 用途 |
|:---:|:---|:---|
| P0 | `2-prd/L1-02.../prd.md §5.2` | 7 L2 产品边界 · S1-S7 流程 |
| P0 | `3-1/L1-02/architecture.md` §2 S1-S7 主状态机 · §3 PMP×TOGAF 交织 · §6 PM-14 所有权 | L2 协作图 |
| P0 | `3-1/L1-02/L2-07.md` §3 render_template · §4 sandbox | **最先做 · 地基** |
| P0 | `3-1/L1-02/L2-02.md` §3 produce_kickoff · §6 activate_pid | PM-14 创建起点 |
| P0 | `3-1/L1-02/L2-01.md` §3 request_gate_decision · §8 状态机 | IC-01 + 7 阶段 × 4 Gate |
| P0 | `3-1/L1-02/L2-06.md` §3 archive_project · §6 tar.zst | PM-14 归档起点 |
| P0 | `3-2/L1-02/*.md` | 409 TC |
| P0 | `ic-contracts.md §3.1 IC-01 · §3.16 IC-16 · §3.19 IC-19` | 3 对外 IC |
| P1 | `integration/p0-seq.md §5 S1→S7 主时序` | 全链 |

---

## §3 WP 拆解（8 WP · 7 天）

### 3.0 总表

| WP | 批 | L2 | 主题 | 前置 | 估时 | TC |
|:---:|:---:|:---:|:---|:---|:---:|:---:|
| δ-WP01 | δ1 | L2-07 | 模板引擎 Jinja2 sandboxed | α IC-09 mock | 1 天 | 56 |
| δ-WP02 | δ1 | L2-02 | 启动阶段 · PM-14 pid 创建 | WP01 | 1 天 | 61 |
| δ-WP03 | δ1 | L2-03 | 4 件套生产器 | WP01+02 | 1 天 | 60 |
| δ-WP04 | δ1 | L2-01 | Stage Gate 控制器 · IC-01 | WP01-03 | 1 天 | 60 |
| δ-WP05 | δ2 | L2-04 | PMP 9 计划（并发）| WP01+WP04 | 1.25 天 | 63 |
| δ-WP06 | δ2 | L2-05 | TOGAF 9 Phase · togaf_d_ready | WP01+WP05 | 1 天 | 55 |
| δ-WP07 | δ2 | L2-06 | 收尾 · PM-14 归档 | WP04 | 0.75 天 | 54 |
| δ-WP08 | - | 集成 | 组内 7 L2 联调 + S1→S7 mock 全链 | WP01-07 | 0.5 天 | ≥ 15 |

### 3.1 WP-δ-01 · L2-07 模板引擎（最先做 · 地基）

**源**：`L2-07.md §3 render_template · §6 Jinja2 SandboxedEnvironment · §10 27 模板 kind 清单`

**L3**：
- `render_template(kind, slots, pid) -> RenderedOutput`
  - caller_l2 白名单（只允许 L2-02/03/04/05/06）
  - kind 正则校验 `^[a-z0-9._-]+$`
  - jsonschema 校验 slots
  - Jinja2 SandboxedEnvironment（`autoescape=False` · `StrictUndefined`）
  - 白名单 filter 集（upper/lower/trim/length/first/join/int/round · 禁 import/getattr）
  - 输出大小 ≤ 200KB
  - 计算 output_hash · 注入 frontmatter 元数据（template_id · template_version · rendered_at）
  - IC-09 emit `template_rendered`（异步）
- 启动加载：扫 `templates/` 目录 · 27 kind 必全 · 任一缺启动 crash

**L4**：
```
app/l1_02/template_engine/renderer.py        ~250 行
app/l1_02/template_engine/registry.py        ~180 行（模板加载 + slot_schema 校验）
app/l1_02/template_engine/sandbox.py         ~120 行（Jinja2 env 配置）
app/l1_02/template_engine/schemas.py         ~180 行
```

**DoD**：
- [ ] ~56 TC 全绿
- [ ] sandbox 拦截：`{% import os %}` / `{{ .__class__ }}` 等必 raise
- [ ] 启动加载 P95 ≤ 500ms（27 模板）
- [ ] 27 kind 必全（缺任一 crash）
- [ ] 调用方白名单硬断言
- [ ] commit `feat(harnessFlow-code): δ-WP01 L2-07 模板引擎`

### 3.2 WP-δ-02 · L2-02 启动阶段 · PM-14 pid 创建

**源**：`L2-02.md §3 produce_kickoff + activate_project_id · §6 anchor_hash · PM-14 硬锁`

**L3**：
- `produce_kickoff(user_utterance) -> S1ProductionResult`
  - Step 1 · 生成 pid（ULID · 含 ms 时间戳）
  - Step 2 · 建目录 `projects/<pid>/{chart,meta,stage-gates}/`
  - Step 3 · 写 `state.json:DRAFT`
  - Step 4 · brainstorming（IC-L2-03 调 L1-05 · mock · 3 轮 QA）
  - Step 5 · 调 L2-07 `render_template("kickoff.goal", slots)` / `("kickoff.scope", slots)` 产 2 章程
  - Step 6 · atomic_write（调 L1-09 L2-05 · mock）· `chart/HarnessFlowGoal.md` + `chart/HarnessFlowPrdScope.md`
  - Step 7 · `compute_anchor_hash(pid)`（goal + scope concat sha256 · 规范化换行）
  - Step 8 · 写 `meta/project_manifest.yaml`
  - Step 9 · 发 4 IC-09 事件（`project_created` / `chart_written` / `manifest_written` / `s1_ready`）
  - Step 10 · 返 `S1ProductionResult(pid, state=DRAFT, anchor_hash, chart_paths, ...)`
- `activate_project_id(pid, gate_decision)` · L2-01 S1 Gate approve 后调
  - PM-14 越权检查（非 L2-01 调 · 拒绝）
  - 校验 anchor_hash 未篡改
  - 状态 DRAFT → INITIALIZED · fsync
- `recover_draft(pid)` · L1-09 崩溃恢复调

**L4**：
```
app/l1_02/kickoff/producer.py             ~250 行
app/l1_02/kickoff/anchor_hash.py          ~80 行
app/l1_02/kickoff/activator.py            ~150 行
app/l1_02/kickoff/recovery.py             ~120 行
app/l1_02/kickoff/schemas.py              ~180 行
```

**DoD**：
- [ ] ~61 TC 全绿
- [ ] PM-14：activate 非 L2-01 调 · 拒绝
- [ ] anchor_hash 篡改检测：改章程后 activate 必失败
- [ ] 15 错误码全覆盖
- [ ] 原子写 · fsync 失败走 halt
- [ ] commit `feat(harnessFlow-code): δ-WP02 L2-02 启动阶段 PM-14 创建`

### 3.3 WP-δ-03 · L2-03 4 件套生产器

**源**：`L2-03.md §3 produce_four_set · §6 装配算法 · §13 ADR`

**L3**：
- `produce_four_set(pid) -> FourSetResult`（S2 阶段产出）
  - 并行产 4 件：scope / prd / plan / tdd
  - 每件调 L2-07 `render_template("fourset.<name>", slots)`
  - 装配 frontmatter（traceability · doc_id · cross-ref）
  - 写 `projects/<pid>/four-set/{scope,prd,plan,tdd}.md`
  - 交叉引用校验（cross_ref 字段 · 禁 dead link）
- `rework_items(pid, items_to_rework)` · Gate reject 后只重做指定件
  - 保留未 rework 的件（anchor 复用）

**L4**：
```
app/l1_02/four_set/producer.py           ~220 行
app/l1_02/four_set/cross_ref_checker.py  ~120 行
app/l1_02/four_set/rework.py             ~150 行
app/l1_02/four_set/schemas.py            ~160 行
```

**DoD**：
- [ ] ~60 TC 全绿
- [ ] 4 件套并行产出（asyncio.gather）
- [ ] cross_ref 检查严格（mock dead link · 返错）
- [ ] rework 保留未指定件
- [ ] 13 错误码全覆盖
- [ ] commit `feat(harnessFlow-code): δ-WP03 L2-03 4 件套生产器`

### 3.4 WP-δ-04 · L2-01 Stage Gate 控制器（IC-01 入口）

**源**：`L2-01.md §3 request_gate_decision · §8 7 状态 × 12 转换 · §11 14 错误码`

**L3**：
- `request_gate_decision(stage, evidence) -> GateDecision`
  - 3 元决策：pass / reject / need_input
  - evidence 装配（4 件套 + PMP + TOGAF 齐否 · 证据不过期 72h）
  - LLM 归因（若 reject · 调 L1-05 `rejection-analyzer` · 返 root_cause + fix_advice）
  - 降级：LLM 超时 → 规则模板归因
- `authorize_transition(pid, from_state, to_state)` · IC-01 入口
  - 状态机硬转换（INITIALIZED → PLANNING → TDD_PLANNING → EXECUTING → CLOSING → CLOSED · 12 条合法边）
  - 非法转换拒绝
  - PM-14 校验（调用方必是 L1-01 主循环）
  - S3 TDD Gate 调 L1-03 L2-02 DAG 环检测
- `rollback_gate(gate_id)` · Gate reject 24h 内可滚
- `emit_rejection_analysis` · 归因结果经 IC-09 审计
- 硬约束：`GATE_AUTO_TIMEOUT_ENABLED=false`（永禁自动放行）

**L4**：
```
app/l1_02/stage_gate/controller.py        ~250 行（主入口）
app/l1_02/stage_gate/state_machine.py     ~200 行（12 条转换）
app/l1_02/stage_gate/evidence_assembler.py ~180 行
app/l1_02/stage_gate/rejection_analyzer.py ~180 行（LLM + 规则降级）
app/l1_02/stage_gate/rollback.py          ~100 行
app/l1_02/stage_gate/schemas.py           ~200 行
```

**DoD**：
- [ ] ~60 TC 全绿
- [ ] IC-01 schema 对齐
- [ ] 12 合法转换测（每条 ≥ 1 pass · 每条非法 ≥ 1 reject）
- [ ] PM-14 越权拒绝测
- [ ] rollback 24h 硬限
- [ ] 自动放行硬禁（启动配置 `GATE_AUTO_TIMEOUT_ENABLED=true` crash）
- [ ] commit `feat(harnessFlow-code): δ-WP04 L2-01 Stage Gate IC-01`

**δ1 批小结**（4 WP · 4 天 · δ1 会话完）：7398 行 tech-design 的前 4 L2 ready · PM-14 pid 可创建 · Gate 可决策 · 4 件套可产出。

### 3.5 WP-δ-05 · L2-04 PMP 9 计划生产器（δ2 开始）

**源**：`L2-04.md §3 produce_all_9 · §6 并发 + 分级降级 · §11 16 错误码`

**L3**：
- `produce_all_9(pid) -> PmpBundleResult`
  - 9 kda 并行产出（asyncio.gather · `PMP_9_KDAS = [integration, scope, schedule, cost, quality, resource, communication, risk, procurement]`）
  - 分级降级：
    - `CORE_KDAS = {scope, schedule, cost}` · 任一失败 → 整批 reject
    - 非核心失败 ≤ 4 → PARTIAL 通过（evidence 标降级）
    - 失败 ≥ 5 → EMERGENCY_MANUAL
  - `compute_pmp_bundle_hash(pid)` · 9 md 固定顺序 concat + sha256
  - `cross_check_togaf_alignment(pid)` · 调 L2-05 · PMP × TOGAF 矩阵校验
- `rework_plans(pid, rework_list)` · Gate reject 后只重做指定 kda

**L4**：
```
app/l1_02/pmp/producer.py                 ~250 行
app/l1_02/pmp/worker_pool.py              ~180 行（asyncio.gather · 9 worker）
app/l1_02/pmp/bundle_hash.py              ~80 行
app/l1_02/pmp/togaf_cross_check.py        ~150 行
app/l1_02/pmp/rework.py                   ~120 行
app/l1_02/pmp/schemas.py                  ~180 行
```

**DoD**：
- [ ] ~63 TC 全绿
- [ ] 9 并行 P95 ≤ 30s · 单 kda P95 ≤ 5s
- [ ] 核心失败 → 整批 reject 测
- [ ] PARTIAL 模式 evidence 必标降级
- [ ] rework 保留 8 重做 1 测
- [ ] commit `feat(harnessFlow-code): δ-WP05 L2-04 PMP 9 并行`

### 3.6 WP-δ-06 · L2-05 TOGAF ADM 架构生产器

**源**：`L2-05.md §3 produce_togaf · §6 Phase A-H 串行 · §11 15 错误码 · IC-L2-06 togaf_d_ready 提前信号`

**L3**：
- `produce_togaf(pid, profile="STANDARD")` · 按 profile 产出 Phase 集合
  - `LIGHT`：A/B/C/D 4 Phase（ADR ≥ 5）
  - `STANDARD`：Preliminary + A/B/C/D + H 6 Phase（ADR ≥ 10）
  - `HEAVY`：全 9 Phase（ADR ≥ 15）
- Phase 严格顺序：Preliminary → A → B → C → D → E → F → G → H
- Phase D 完成立即发 IC-L2-06 `togaf_d_ready` 事件 · 解 L2-04 PMP Group 2（quality/risk）阻塞（关键性能路径）
- Phase C `architecture-reviewer` 委托（IC-05 调 L1-05）· 超时降级本地规则评审
- 每 Phase 产 md + 若干 ADR（`ADR-<letter>-<seq>.md`）

**L4**：
```
app/l1_02/togaf/producer.py                  ~250 行
app/l1_02/togaf/phase_runner.py              ~200 行
app/l1_02/togaf/adr_generator.py             ~150 行
app/l1_02/togaf/togaf_d_ready_emitter.py     ~100 行（关键提前信号）
app/l1_02/togaf/rework.py                    ~120 行
app/l1_02/togaf/schemas.py                   ~180 行
```

**DoD**：
- [ ] ~55 TC 全绿
- [ ] LIGHT/STANDARD/HEAVY 3 档测
- [ ] Phase 非法顺序拒绝（B 跳 A · 拒绝）
- [ ] togaf_d_ready 发送延迟 P95 ≤ 200ms（关键路径）
- [ ] Phase C reviewer 降级测
- [ ] commit `feat(harnessFlow-code): δ-WP06 L2-05 TOGAF ADM`

### 3.7 WP-δ-07 · L2-06 收尾阶段（PM-14 归档唯一入口）

**源**：`L2-06.md §3 produce_closing + archive_project · §6 tar.zst · §11 15 错误码`

**L3**：
- `produce_closing(pid)` · S6 阶段
  - 读 L1-06 KB learn 层（lessons 数据源）
  - 读 L1-09 audit 事件（retro 数据源）
  - 调 L2-07 render 3 md：`lessons_learned.md` / `delivery_manifest.md` / `retro_summary.md`
  - 原子写 `projects/<pid>/closing/`
  - 计算 `closing_bundle_hash` · state → CLOSING_PRODUCED
- `archive_project(pid)` · S7 阶段 · **PM-14 归档唯一入口**
  - PM-14 越权检查
  - state 必 CLOSING_GATE_APPROVED
  - 预检 size ≤ 20GB
  - `tar --zstd -cf projects/_archive/<pid>.tar.zst projects/<pid>/`
  - 复验 sha256
  - 写 manifest.json
  - `chmod 0444 projects/<pid>/`（只读保护）
  - state → ARCHIVED · fsync
  - 发 `project_archived` 事件
- `purge_project(pid, confirm_token)` · 归档后 ≥ 90 天 · 双重确认
- `recover_from_interruption` · 磁盘满等中断后 resume

**L4**：
```
app/l1_02/closing/producer.py              ~200 行
app/l1_02/closing/archiver.py              ~220 行（tar.zst + sha256 + chmod）
app/l1_02/closing/purger.py                ~120 行（90 天 + 双确认）
app/l1_02/closing/retro_aggregator.py      ~120 行（读 audit）
app/l1_02/closing/schemas.py               ~180 行
```

**DoD**：
- [ ] ~54 TC 全绿
- [ ] PM-14 归档越权拒绝测
- [ ] sha256 复验测（写后读回 · 一致）
- [ ] chmod 0444 测（归档后尝试写 · 拒绝）
- [ ] purge 90 天硬限 + token 不匹配测
- [ ] resume 续做测（mock 磁盘满中断 · 恢复续做）
- [ ] commit `feat(harnessFlow-code): δ-WP07 L2-06 收尾 PM-14 归档`

### 3.8 WP-δ-08 · 集成

- 组内 7 L2 联调：S1 pid 创建 → 4 件套 → PMP/TOGAF → Gate 决策 → S7 归档 全链
- PM-14 全链（pid 从创建到归档 唯一入口测）
- IC-01 + IC-19 + IC-16 发起测

**DoD**：≥ 15 集成 TC 绿 · S1-S7 mock 全链跑通 · commit `feat(harnessFlow-code): δ-WP08 集成`。

---

## §4 依赖图

```
δ-WP01 L2-07 模板引擎（地基）
  ↓
δ-WP02 L2-02 启动（PM-14 创建）
  ↓
δ-WP03 L2-03 4 件套
  ↓
δ-WP04 L2-01 Gate 控制（IC-01）
  ↓ ─────┬─────┐
δ-WP05   δ-WP06  δ-WP07
L2-04    L2-05   L2-06
PMP      TOGAF   收尾
 ↓       ↓       ↓
         └───────┴──── δ-WP08 集成
```

### 4.1 跨组 mock

| 外部 | 提供方 | mock |
|:---|:---|:---|
| IC-09 append_event | Dev-α | mock |
| L1-09 L2-05 write_atomic | Dev-α | mock · 直接写文件 |
| IC-06 kb_read | Dev-β | mock |
| L1-05 brainstorming / architecture-reviewer | Dev-γ | mock · 返固定 response |
| IC-16 push UI（Gate 卡片）| Dev-θ1 | mock · 不真推 · 只校验 payload |
| IC-19 WBS 拆解（L2-01 发）| Dev-ε | mock · 返 dummy WBS 结果 |

---

## §5 standup + commit

复用 Dev-α §5 · prefix `δ-WPNN`。**δ1 会话做 WP01-04 · 第一次 WP04 完成后 commit + 交接 δ2 会话**。

---

## §6 自修正

- **情形 A · PRD 偏差**：S2 Gate reject 策略在实际用户场景下过严 · 走 §6 改 PRD
- **情形 B · 3-1 不可行**：PMP × TOGAF 交织矩阵算法在 edge case 有歧义 · 改 3-1 L2-04/05 §6
- **情形 D · IC-01 契约**：L1-01 消费方对 `from_state` 字段理解不一 · 仲裁 ic-contracts.md §3.1

---

## §7 对外契约

| IC | 方法 | 角色 | SLO |
|:---|:---|:---|:---|
| IC-01 接收 | `authorize_transition(from, to, pid)` | L1-01 → L2-01 | P95 ≤ 100ms |
| IC-19 发起 | `request_wbs_decomposition(pid, plan_content)` | L2-01 → L1-03 | dispatch ≤ 100ms |
| IC-16 发起 | `push_stage_gate_card(gate_id, decision)` | L2-01 → L1-10 UI | dispatch ≤ 50ms |
| IC-17 接收 | `user_intervene(type="gate_approve")` | L1-10 → 本 L1 | Sync |

**替换时机**：δ1 WP04 完 · 其他组可切真实 IC-01 · δ2 WP07 完 · PM-14 pid 全生命周期可用。

---

## §8 DoD（PM-14 特化）

**组级加码**：

| 维度 | 判据 |
|:---|:---|
| PM-14 pid 唯一入口 | L2-02 是 pid 创建唯一路径 · L2-06 是归档唯一路径 · 非此两路径创建/归档 · 拒绝 |
| anchor_hash 不可变 | 章程 md 修改后 activate 必失败 |
| Stage Gate 不可绕 | `GATE_AUTO_TIMEOUT_ENABLED=true` 启动 crash |
| 核心 kda 强保 | PMP 核心（scope/schedule/cost）任一失败整批 reject |
| TOGAF 顺序硬 | Phase B 不可跳 Phase A |
| tar.zst sha256 复验 | 归档后内容被改 · sha256 mismatch raise |

### 组级 DoD

- [ ] pytest 409 passed · coverage ≥ 85%
- [ ] IC-01/16/19 schema 一致
- [ ] S1-S7 mock 全链跑通（scenario-02 简化版）
- [ ] PM-14 pid 创建/归档唯一入口测
- [ ] commit 14-16 个

---

## §9 风险

| 风险 | 降级 |
|:---|:---|
| **R-δ-01** PMP 9 并行资源争抢（LLM token 限流）| 降并行度到 3 · 串行 · 耗时增 · 但稳 |
| **R-δ-02** TOGAF Phase C reviewer 不稳定 | 本地规则 fallback · config 开关 |
| **R-δ-03** L2-01 LLM 归因超时 | 规则模板降级（无 LLM 也可产出 reject reason） |
| **R-δ-04** tar.zst 大 project（20GB）耗时超预期 | 分卷 · 或 level 降（19 → 9 · 速度优先） |

---

## §10 交付清单

### 代码（~13300 行）

```
app/l1_02/
├── template_engine/  (~700 行)
├── kickoff/          (~800 行)
├── four_set/         (~650 行)
├── stage_gate/       (~1100 行)
├── pmp/              (~900 行)
├── togaf/            (~1000 行)
└── closing/          (~850 行)
```

### 测试（~6500 行）

```
tests/l1_02/
├── test_l2_07_template_engine.py    (56 TC)
├── test_l2_02_kickoff.py            (61)
├── test_l2_03_four_set.py           (60)
├── test_l2_01_stage_gate.py         (60)
├── test_l2_04_pmp.py                (63)
├── test_l2_05_togaf.py              (55)
├── test_l2_06_closing.py            (54)
├── integration/
│   ├── test_l1_02_e2e.py            (S1-S7 mock 全链 ≥ 15 TC)
│   ├── test_pm14_pid_lifecycle.py
│   └── test_ic_01_16_19.py
└── perf/
    ├── bench_pmp_parallel.py        (≤ 30s)
    ├── bench_togaf_d_ready.py       (≤ 200ms)
    └── bench_archive.py             (1GB ≤ 60s)
```

### commit（14-16 个 · δ1 + δ2）

### 验收 checklist

- [ ] 8 WP closed · 409 TC 绿 · coverage ≥ 85%
- [ ] PM-14 pid 全生命周期 e2e 绿
- [ ] IC-01/16/19 契约一致
- [ ] 硬约束（自动放行禁 · 核心 kda 保 · TOGAF 顺序）全绿
- [ ] `app/l1_02/README.md`

---

*— Dev-δ · L1-02 项目生命周期 · Execution Plan · v1.0 · 2026-04-23 —*
