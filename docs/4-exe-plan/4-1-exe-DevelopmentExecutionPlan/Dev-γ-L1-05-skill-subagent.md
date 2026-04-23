---
doc_id: exe-plan-dev-gamma-L1-05-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α-L1-09-resilience-audit.md（标杆）
  - docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/architecture.md
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01~L2-05.md（7677 行）
  - docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/L2-01~L2-05-tests.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.4 IC-04 · §3.5 IC-05 · §3.12 IC-12 · §3.20 IC-20
version: v1.0
status: draft
author: main-session
assignee: Dev-γ
wave: 2
priority: P0（多 L1 调 IC-04/05）
estimated_loc: ~13800 行
estimated_duration: 4-6 天
---

# Dev-γ · L1-05 Skill 生态+子 Agent 调度 · Execution Plan

> **组一句话**：实现 Skill 注册表 + 意图选择 + 调用执行 + 子 Agent 委托 + 异步结果回收 · 5 L2 共 ~13800 行代码 · 提供 **IC-04 invoke_skill** / **IC-05 delegate_subagent** / **IC-12** / **IC-20** 4 个全局 IC · 是 L1-01 决策链的 skill 入口 · L1-04 质量环的 verifier 入口。
>
> **依赖**：Dev-α IC-09 mock + Dev-β IC-06 mock（kb 历史经验读）· 波 2 启动。
>
> **PM-14 特别**：所有 skill/subagent 调用 context 必带 project_id · 子 Agent 独立 session 但继承 pid（PM-03）。

---

## §0 撰写进度

- [x] §1 组定位 + 5 L2 清单
- [x] §2 源文档导读
- [x] §3 WP 拆解（6 WP · 5 天）
- [x] §4 依赖图 + mock
- [x] §5 standup（复用标杆）
- [x] §6 自修正触发点
- [x] §7 对外契约
- [x] §8 DoD（skill 特化）
- [x] §9 风险 + 降级
- [x] §10 交付清单

---

## §1 组定位 + 范围

### 1.1 5 L2 清单

| L2 | 职责 | 3-1 行 | 估代码 | 估时 | IC |
|:---:|:---|---:|---:|:---:|:---|
| **L2-01** Skill 注册表 | 启动加载 · 热更新 · 账本回写 · query_candidates | 1777 | ~3200 | 1 天 | 内部 |
| **L2-02** 意图选择器 | 5 信号混合打分 · 硬编码 scan · KB boost | 1549 | ~2800 | 1 天 | 内部（被 L2-03 调）|
| **L2-03** 调用执行器 | context 注入 · timeout · retry · audit · **IC-04 入口** | 1793 | ~3200 | 1 天 | **IC-04** |
| **L2-04** 子 Agent 委托器 | Claude Agent SDK · 独立 session · PM-03 · 资源上限 · **IC-05/12/20 入口** | 812 | ~1500 | 1 天 | **IC-05 · IC-12 · IC-20** |
| **L2-05** 异步结果回收器 | 子 Agent 完成事件订阅 · schema 校验 · DoD 网关 · forward | 1749 | ~3100 | 1 天 | 内部（L2-03/04 结果）|
| **合计** | 5 | **7680** | **~13800** | **5 天** | 4 全局 IC |

### 1.2 Out-of-scope

- ❌ Skill 的具体实现（那是 skill 自己的事 · 本 L2 只调）
- ❌ 跨进程子 Agent 通信协议自研（用 Claude Agent SDK）
- ❌ Skill 版本管理 V2+（V1 只装一套）

### 1.3 代码目录

```
app/l1_05/
├── registry/              # L2-01
│   ├── loader.py          # 启动加载 + fs_watch 热更新
│   ├── query_api.py       # query_candidates / query_subagent / query_tool
│   ├── ledger.py          # 账本回写 (IC-L2-07)
│   └── schemas.py
├── intent_selector/       # L2-02
│   ├── scorer.py          # 5 信号打分（capability/cost/success_rate/recency/kb_boost）
│   ├── hard_edge_scan.py  # 启动硬编码扫描
│   ├── fallback_advancer.py
│   └── schemas.py
├── invoker/               # L2-03
│   ├── executor.py        # IC-04 主入口
│   ├── context_injector.py
│   ├── timeout_manager.py
│   ├── retry_policy.py
│   ├── audit.py           # IC-09 emit
│   └── schemas.py
├── subagent/              # L2-04
│   ├── delegator.py       # IC-05/12/20 主入口
│   ├── claude_sdk_client.py  # Claude Agent SDK 封装
│   ├── resource_limiter.py   # max_concurrent + memory + timeout
│   ├── context_scope.py      # PM-03 独立 session + pid 继承
│   └── schemas.py
└── async_receiver/        # L2-05
    ├── validator.py       # schema 校验 · IC-to-L1-04:dod_gate_check
    ├── forwarder.py       # 结果转发到原调用方
    ├── crash_recovery.py  # pending.jsonl 重启恢复
    └── schemas.py
```

---

## §2 源文档导读

| 优先级 | 文档 | 用途 |
|:---:|:---|:---|
| P0 | `2-prd/L1-05 .../prd.md` | 硬约束：硬编码 skill 禁止 · 子 Agent 必独立 session · capability 抽象 |
| P0 | `3-1/L1-05/architecture.md` §11 分工 · §5 时序 | L2 协作 |
| P0 | `3-1/L1-05/L2-01~L2-05.md` §3 IC · §11 错误码 | 每 L2 实现依据 |
| P0 | `3-2/L1-05/L2-01~L2-05-tests.md` | ~249 TC（40-40-39-39-38）|
| P0 | `ic-contracts.md §3.4 IC-04 · §3.5 IC-05 · §3.12 · §3.20` | 4 IC 契约字段级 |
| P1 | `integration/p0-seq.md §3` IC-04 时序 | 看 invoke_skill 在主干的位置 |
| P1 | Claude Agent SDK 官方文档 | L2-04 子 Agent 技术栈 |

---

## §3 WP 拆解（6 WP · 5 天）

### 3.0 总表

| WP | L2 | 主题 | 前置 | 估时 | TC |
|:---:|:---:|:---|:---|:---:|:---:|
| γ-WP01 | L2-01 | Skill 注册表加载 + query_candidates | α WP04 mock | 1 天 | ~40 |
| γ-WP02 | L2-02 | 意图选择器 · 5 信号 + 硬编码 scan | WP01 | 1 天 | ~40 |
| γ-WP03 | L2-03 | IC-04 invoke_skill 调用执行 | WP01+02 | 1 天 | ~39 |
| γ-WP04 | L2-04 | 子 Agent 委托（Claude Agent SDK 集成）| WP03 | 1 天 | ~39 |
| γ-WP05 | L2-05 | 异步结果回收 + DoD 网关 | WP04 | 1 天 | ~38 |
| γ-WP06 | 集成 | 组内 5 L2 联调 + e2e | WP01-05 | 0.5 天 | ≥ 8 |

### 3.1 WP-γ-01 · L2-01 Skill 注册表

**源**：`3-1 L2-01-Skill 注册表.md §3（6 IC · 5 接收 + 1 发起）· §6 启动加载 5 阶段 · §11 12 错误码`

**L3**：
- 启动加载：扫 `skills/` 目录 · 读 SkillSpec（frontmatter + 能力声明）· 5 阶段（filesystem scan → yaml parse → schema validate → capability index → snapshot）
- `query_candidates(capability, constraints) -> list[SkillCandidate]` · 按 capability 返候选集
- `query_subagent(name)` · 查 SubagentEntry（5 类：codebase_onboarding · verifier · ...）
- `query_tool(tool_name)` · 查 ToolEntry（Bash / Read / ...）
- `query_schema_pointer(capability)` · 返 JSON schema 文件路径
- `write_ledger(capability, skill_id, outcome)` · IC-L2-07（仅 L2-02 调 · 账本回写）
- fs_watch 热更新（监听 `skills/` 目录变化 · 增量更新 registry）
- snapshot 兜底（启动失败读 last known good）

**L4**：
```
app/l1_05/registry/loader.py              ~250 行（5 阶段加载）
app/l1_05/registry/query_api.py           ~200 行（4 query 方法）
app/l1_05/registry/ledger.py              ~180 行（账本 · L1-09 锁保护）
app/l1_05/registry/fs_watcher.py          ~150 行（watchdog lib）
app/l1_05/registry/schemas.py             ~200 行
```

**DoD**：
- [ ] ~40 TC 全绿 · coverage ≥ 80%
- [ ] 启动加载 P99 ≤ 500ms
- [ ] 热更新：fs_watch 触发到 registry 更新 ≤ 500ms
- [ ] 账本并发回写（L1-09 锁保）· 无竞态
- [ ] 12 错误码全覆盖
- [ ] commit `feat(harnessFlow-code): γ-WP01 L2-01 Skill 注册表`

### 3.2 WP-γ-02 · L2-02 意图选择器

**源**：`3-1 L2-02.md §3 select · §6 5 信号算法 · §9.5 硬编码 scan（PRD 红线）`

**L3**：
- 启动硬编码扫描（`HardEdgeScan`）：扫全仓 Python · 禁任何硬编码 skill 名（`superpowers:xxx` / `skill_id="..."`）· 违反 crash
- `select(capability, constraints, context) -> Chain[SkillCandidate]`
  - 调 L2-01 `query_candidates`
  - 5 信号打分：
    - `capability_match_score`（capability 白名单）
    - `cost_score`（token / 时间）
    - `success_rate_score`（账本 history · 指数衰减 24h 半衰期）
    - `recency_score`
    - `kb_boost`（调 L1-06 IC-06 读 recipe · 旁路 · 超时 150ms 降级无 KB）
  - 混合权重（config · 和 = 1.0）
  - 兜底：全 unavailable · 注 `builtin_min` 最低能力候选 + warn
- `advance_fallback(chain, reason) -> next_candidate` · 当前候选失败 · 返下一候选
- capability 未注册 → 抛 `capability_exhausted` · L1-07 IC-15 hard_halt

**L4**：
```
app/l1_05/intent_selector/scorer.py             ~250 行
app/l1_05/intent_selector/hard_edge_scan.py     ~120 行（启动扫）
app/l1_05/intent_selector/fallback_advancer.py  ~180 行
app/l1_05/intent_selector/kb_boost.py           ~100 行（调 L1-06）
app/l1_05/intent_selector/schemas.py            ~150 行
```

**DoD**：
- [ ] ~40 TC 全绿
- [ ] 硬编码扫描必触发（故意注入 · 启动 crash）
- [ ] 5 信号独立单测 · 混合打分测
- [ ] KB 旁路降级（mock L1-06 超时 · 仍产链）
- [ ] capability_exhausted 触发 IC-15
- [ ] commit `feat(harnessFlow-code): γ-WP02 L2-02 意图选择`

### 3.3 WP-γ-03 · L2-03 IC-04 invoke_skill

**源**：`3-1 L2-03.md §3 IC-04 入参/出参 · §6 context 注入 + timeout · §11 错误码`

**L3**：
- `invoke_skill(capability, params, context, caller_l1, deadline_ms) -> SkillResult`（IC-04）
  - Step 1 · PM-14 校验（params 或 context 必含 project_id）
  - Step 2 · 调 L2-02 `select` 拿 chain
  - Step 3 · 遍历 chain：
    - context_injector 注入（pid · session · caller · correlation_id）
    - 启动 skill（通过 Skill tool 或子 Agent 路径）
    - timeout 控制（min(deadline_ms, skill_max_timeout)）
    - 成功 → IC-09 emit + L2-01 account（success_rate 更新）· 返
    - 失败 → retry_policy（最多 max_retry · 默认 2）· 若 retry_exhausted · L2-02 `advance_fallback`
  - Step 4 · 全链失败 · 返 `SkillResult(success=false, reason="all_failed")` · 调用方决定 BF-E-05
- context_injector 特别：correlation_id 透传（复用 L1-09 context）

**L4**：
```
app/l1_05/invoker/executor.py               ~280 行
app/l1_05/invoker/context_injector.py       ~150 行
app/l1_05/invoker/timeout_manager.py        ~120 行
app/l1_05/invoker/retry_policy.py           ~120 行
app/l1_05/invoker/audit.py                  ~100 行
app/l1_05/invoker/schemas.py                ~180 行
```

**DoD**：
- [ ] ~39 TC 全绿
- [ ] IC-04 schema 严格对齐 `ic-contracts.md §3.4`
- [ ] timeout 精度 ± 100ms
- [ ] retry_policy 边界（exactly 2 retries · 不多不少）
- [ ] 全链失败返 `success=false` 不 raise（调用方判断）
- [ ] PM-14 缺 pid · 拒绝
- [ ] commit `feat(harnessFlow-code): γ-WP03 L2-03 IC-04 invoke_skill`

### 3.4 WP-γ-04 · L2-04 子 Agent 委托

**源**：`3-1 L2-04.md §3 IC-14-Spawn + IC-14-Delegate · §6 Claude SDK 集成 · §11 错误码`

**L3**：
- `delegate_subagent(subagent_name, payload, ctx)` → IC-05 / IC-12 / IC-20（按 subagent_name 路由）
  - Step 1 · 调 L2-01 `query_subagent(name)` · 取 SubagentEntry（tool_whitelist · timeout · schema_pointer）
  - Step 2 · 并发守护：`max_concurrent=3`（默认 · config）· 超排队
  - Step 3 · context COW 快照（PM-03 · 独立 session）· 继承 pid
  - Step 4 · 用 Claude Agent SDK 启动：
    - 创建 SDK session · 传 tool_whitelist · timeout
    - 发 payload · 等返 report
  - Step 5 · 超时强杀（SIGTERM → SIGKILL · 5s grace）
  - Step 6 · 结果回收交 L2-05（异步 · 通过 IC-09 事件）
  - Step 7 · TrustLedger 记（IC-05 · 账本 · spawn/complete/abort 全链）
- 降级链：
  - context overflow → `memory_readonly` / `summary_only` fallback
  - spawn fail · retry 2 次 → inline 模式（主 session 简化跑）

**L4**：
```
app/l1_05/subagent/delegator.py             ~250 行（IC-05/12/20 路由）
app/l1_05/subagent/claude_sdk_client.py     ~200 行（SDK 封装）
app/l1_05/subagent/resource_limiter.py      ~150 行（并发 + 内存）
app/l1_05/subagent/context_scope.py         ~120 行（COW · pid 继承）
app/l1_05/subagent/schemas.py               ~180 行
```

**DoD**：
- [ ] ~39 TC 全绿（对齐 L1-05 L2-04 tests）
- [ ] PM-03 独立 session 测（mock SDK · 验证不共享主 session 状态）
- [ ] 并发上限测（第 4 个 spawn 排队 or 拒绝）
- [ ] timeout 强杀测（mock slow subagent · SIGTERM 后 5s SIGKILL）
- [ ] context overflow 降级链测（memory_readonly → summary_only → FAIL-L2）
- [ ] 跨项目访问拒绝（ctx.pid 与 spawn 参数不一致 · raise）
- [ ] commit `feat(harnessFlow-code): γ-WP04 L2-04 子 Agent 委托`

### 3.5 WP-γ-05 · L2-05 异步结果回收

**源**：`3-1 L2-05.md §3 validate_async_return · §5 时序 · §11 错误码`

**L3**：
- 订阅 IC-09 `L1-05:subagent_completed` 事件（L2-04 在 complete 时 emit）
- `validate_async_return(raw_return) -> ValidationResult`
  - Step 1 · schema 校验（从 L2-01 `lookup_schema_pointer` 取 · cached）
  - Step 2 · schema 不匹配 → `schema_mismatch` · 调用方可决定 fallback
  - Step 3 · DoD 网关（可选 · `dod_gate_required` 字段）· 调 L1-04 IC-to-L1-04:dod_gate_check · 不通过 · 返 `dod_rejected`
  - Step 4 · forward 到原调用方（`caller_ref`）· 通过 IC-09 事件 route back
- 幂等：同 `result_id` 第二次提交返 cached response
- crash recovery：启动读 `pending.jsonl` · 恢复未完成的 validation
- 静默 patch 检测（E09 · raise · L1-07 CRITICAL）· 硬约束

**L4**：
```
app/l1_05/async_receiver/validator.py          ~250 行
app/l1_05/async_receiver/forwarder.py          ~150 行
app/l1_05/async_receiver/crash_recovery.py     ~150 行
app/l1_05/async_receiver/schemas.py            ~180 行
```

**DoD**：
- [ ] ~38 TC 全绿
- [ ] schema 校验严格（mock L2-01 pointer · 不匹配返 `schema_mismatch`）
- [ ] DoD 网关双路径（required=true → 调 L1-04 · false → 跳过）
- [ ] 幂等 result_id
- [ ] crash recovery（模拟重启 · pending 恢复）
- [ ] 静默 patch 检测（尝试改 raw_return · raise CRITICAL）
- [ ] commit `feat(harnessFlow-code): γ-WP05 L2-05 异步结果回收`

### 3.6 WP-γ-06 · 集成

- 组内 5 L2 联调：invoke_skill → select → registry → subagent → result_receiver 全链
- IC-04 + IC-05 + IC-12 + IC-20 4 IC 契约集成测
- 组完工：Dev-γ-M1 · 其他组可切真实 IC-04/05

**DoD**：≥ 8 集成 TC 绿 · IC 契约一致 · commit `feat(harnessFlow-code): γ-WP06 集成`。

---

## §4 依赖图

### 4.1 组内 WP 依赖

```
γ-WP01（Registry）
   ↓
γ-WP02（Intent） ← kb_boost from 外部 Dev-β mock
   ↓
γ-WP03（Invoker IC-04）
   ↓
γ-WP04（Subagent IC-05/12/20） ← Claude Agent SDK
   ↓
γ-WP05（Result receiver） ← DoD gate mock from 外部 主-1
   ↓
γ-WP06（集成）
```

### 4.2 跨组 mock

| 外部 IC | 提供方 | mock | 替换时机 |
|:---|:---|:---|:---|
| IC-09 append_event | Dev-α | mock `EventBus.append` | α WP04 完 |
| IC-06 kb_read | Dev-β | mock `kb_read` 返 `[]` | β WP03 完 |
| IC-L2-07 account（锁）| Dev-α L2-02 | mock LockManager | α WP07 完 |
| dod_gate_check | 主-1 L1-04 | mock 返 `approved` | 主-1 L1-04 L2-02 完 · Dev-γ WP05 可切真实 |

---

## §5 standup + commit 规范

复用 Dev-α §5 · prefix `γ-WPNN`。

---

## §6 自修正触发点

- **情形 B · 3-1 不可行**：Claude Agent SDK 实测与 3-1 L2-04 §6 描述有差（版本更新）· 回改 3-1 §6
- **情形 D · IC-04 契约矛盾**：L1-01/04 消费方对 `deadline_ms` 语义理解不同 · 仲裁 ic-contracts.md §3.4
- **情形 E · 3-3 DoD 规约**：DoD 表达式语法在 validator 中解析失败 · O 会话补 3-3 `dod-specs/general-dod.md`

---

## §7 对外契约

| IC | 方法 | 消费方 | SLO |
|:---|:---|:---|:---|
| IC-04 | `invoke_skill(capability, params, ctx)` | 多 L1 | P95 按 skill（10s-60s）· dispatch ≤ 200ms |
| IC-05 | `delegate_subagent(name, payload, ctx)` | 多 L1 | dispatch ≤ 200ms · result 异步 |
| IC-12 | `delegate_codebase_onboarding(code_dir)` | L1-08 | dispatch ≤ 200ms · result ≤ 10min |
| IC-20 | `delegate_verifier(wp_report)` | L1-04 | dispatch ≤ 200ms · result 分钟级 |

**替换时机**：

- L1-01 决策（主-2）· L1-04 质量环（主-1）· L1-08 多模态（Dev-η）· 全部波 4 开始切真实
- Dev-γ WP06 完 · 其他消费方可预演集成（mock → real 切换 smoke 测）

---

## §8 DoD（Skill 特化）

### 组级加码

| 维度 | 判据 |
|:---|:---|
| 硬编码 scan | 启动期扫全仓 · 0 硬编码 skill 名 |
| PM-03 独立 session | 子 Agent 不访问主 session 变量（测试验证） |
| PM-14 pid 继承 | 子 Agent ctx.pid = 调用方 pid（测试验证） |
| capability 穷举 | L1-01 决策时 · 若 capability 未注册 · 必 IC-15 halt（不静默降级） |
| TrustLedger 完整 | spawn / complete / abort 全链落账（IC-05 审计） |
| 子 Agent 超时 | SIGTERM → 5s → SIGKILL · 不留僵尸进程 |
| Claude SDK 失败 | retry 2 次 → inline fallback（不 halt 主 loop） |

### 组级 DoD

- [ ] pytest 249 passed · coverage ≥ 85%
- [ ] IC-04/05/12/20 schema 严格对齐
- [ ] 启动硬编码 scan 绿
- [ ] 子 Agent e2e（spawn → complete）绿
- [ ] 降级链 4 路径全测
- [ ] commit 11-12 个

---

## §9 风险

| 风险 | 降级 |
|:---|:---|
| **R-γ-01** Claude Agent SDK API 变更 | pin SDK 版本 · 变更走 §6 情形 B 改 3-1 §6 |
| **R-γ-02** 子 Agent 资源爆炸（超过 max_concurrent）| 排队 + 硬限 · 超则 IC-15 halt |
| **R-γ-03** KB boost 实测无效 · 反拖性能 | weights 调 · kb_boost=0 退化 · 走 §6 情形 A 改 PRD |
| **R-γ-04** context COW 在大 payload 下慢 | Reject 超大 payload · 建议调用方分批 |

---

## §10 交付清单

### 代码（~13800 行）

```
app/l1_05/
├── registry/              (5 文件 · ~980 行)
├── intent_selector/       (5 文件 · ~800 行)
├── invoker/               (6 文件 · ~950 行)
├── subagent/              (5 文件 · ~900 行)
└── async_receiver/        (4 文件 · ~730 行)
```

### 测试（~5500 行）

```
tests/l1_05/
├── conftest.py
├── test_l2_01_registry.py        (~40 TC)
├── test_l2_02_intent.py          (~40)
├── test_l2_03_invoker.py         (~39)
├── test_l2_04_subagent.py        (~39)
├── test_l2_05_receiver.py        (~38)
├── integration/
│   ├── test_l1_05_e2e.py
│   ├── test_ic_04_05_12_20.py
│   └── test_pm14_subagent_isolation.py
└── perf/
    ├── bench_ic_04_dispatch.py   (≤ 200ms)
    └── bench_subagent_spawn.py   (≤ 1.2s)
```

### commit 汇总（11-12 个）

### 验收 checklist

- [ ] 6 WP closed · 249 TC 绿 · coverage ≥ 85%
- [ ] IC-04/05/12/20 schema 一致
- [ ] Claude SDK 集成测绿
- [ ] 硬编码 scan 绿
- [ ] PM-03/PM-14 隔离验证绿
- [ ] `app/l1_05/README.md`

---

*— Dev-γ · L1-05 Skill 生态+子 Agent · Execution Plan · v1.0 · 2026-04-23 —*
