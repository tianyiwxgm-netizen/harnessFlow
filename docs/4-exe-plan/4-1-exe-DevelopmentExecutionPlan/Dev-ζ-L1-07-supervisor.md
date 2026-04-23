---
doc_id: exe-plan-dev-zeta-L1-07-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α-L1-09-resilience-audit.md（标杆）
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/3-1-Solution-Technical/L1-07-Harness监督/architecture.md
  - docs/3-1-Solution-Technical/L1-07-Harness监督/L2-01~L2-06.md（14172 行）
  - docs/3-2-Solution-TDD/L1-07-Harness监督/L2-01~L2-06-tests.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.13 IC-13 · §3.14 IC-14 · §3.15 IC-15
version: v1.0
status: draft
assignee: Dev-ζ（拆 ζ1 + ζ2 · 2 会话接力）
wave: 3
priority: P0（发 IC-13/14/15 · 主循环依赖）
estimated_loc: ~25500 行
estimated_duration: 7-9 天（ζ1 · 3 天 + ζ2 · 4 天）
---

# Dev-ζ · L1-07 Harness 监督 · Execution Plan

> **组一句话**：6 L2 · 8 维度监督采集 + 4 级偏差判定 + 硬红线拦截 + Supervisor 事件发送 + Soft-drift 模式识别 + 死循环升级。**发起 IC-13/14/15** 三大监督契约 · 旁路订阅 IC-09（Dev-α） · 不阻塞主流。

---

## §0 撰写进度

- [x] §1-§10 全齐

---

## §1 范围

### 6 L2 · ζ1/ζ2 拆批

**ζ1 批**（3 天 · 3 L2）：
| L2 | 职责 | 估时 |
|:---:|:---|:---:|
| L2-01 8 维度采集器 | 主动调 IC-11 read_event_stream + 写 IC-09 · 30s tick / PostToolUse fast / on-demand 3 入口 · 8 维度（phase/artifacts/wp_status/tool_calls/latency_slo/self_repair_rate/rollback_counter/event_bus）| 1.25 天 |
| L2-04 Supervisor 事件发送器 | IC-13/14/15 出口 · 队列 + 背压 · BLOCK 抢占 | 1 天 |
| L2-06 死循环升级器+回退路由 | 同级连 ≥ 3 failed · 自动升级 | 0.75 天 |

**ζ2 批**（4 天 · 3 L2）：
| L2 | 职责 | 估时 |
|:---:|:---|:---:|
| L2-02 4 级偏差判定器 | INFO/WARN/FAIL/CRITICAL 分级 · 基于 8 维度 state | 1 天 |
| L2-03 硬红线拦截器 | 5 类硬红线 · ≤ 100ms 响应 · IC-15 出口 | 1.5 天 |
| L2-05 Soft-drift 模式识别器 | 滑窗统计 · 8 类 trap 模式 · 温水煮青蛙识别 | 1.5 天 |

合计 **6 L2 · 7 天** + 0.5 集成 = **7.5 天** · ~25500 行代码。

### 代码目录

```
app/l1_07/
├── dim_collector/       # L2-01 · 8 维度采集
├── deviation_judge/     # L2-02 · 4 级判定
├── red_line/            # L2-03 · 硬红线拦截（100ms 硬约束）
├── event_sender/        # L2-04 · IC-13/14/15 出口
├── soft_drift/          # L2-05 · 软漂移识别
└── escalator/           # L2-06 · 死循环升级
```

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | `2-prd/L1-07 .../prd.md` 硬红线 5 类 · 软漂移 8 类 · 4 级偏差 |
| P0 | `3-1/L1-07/architecture.md` §11 L2 分工 · §5 监督时序 |
| P0 | `3-1/L1-07/L2-01~L2-06.md` 每份 §3 接口 · §11 错误码 |
| P0 | `3-2/L1-07/*.md` ~333 TC |
| P0 | `ic-contracts.md §3.13 IC-13 · §3.14 IC-14 · §3.15 IC-15` |
| P0 | `3-3/hard-redlines.md`（O 会话 · fallback 用 PRD §8.5） |

---

## §3 WP 拆解（7 WP · 7.5 天）

| WP | 批 | L2 | 主题 | 估时 | TC |
|:---:|:---:|:---:|:---|:---:|:---:|
| ζ-WP01 | ζ1 | L2-01 | 订阅 IC-09 + 8 维度采集 | 1.25 天 | ~57 |
| ζ-WP02 | ζ1 | L2-04 | IC-13/14/15 出口 + 队列背压 | 1 天 | ~56 |
| ζ-WP03 | ζ1 | L2-06 | 死循环升级器 · 同级连 ≥ 3 触发 | 0.75 天 | ~54 |
| ζ-WP04 | ζ2 | L2-02 | 4 级偏差判定 | 1 天 | ~55 |
| ζ-WP05 | ζ2 | L2-03 | 硬红线拦截（100ms 硬约束）| 1.5 天 | ~57 |
| ζ-WP06 | ζ2 | L2-05 | Soft-drift 模式识别 | 1.5 天 | ~55 |
| ζ-WP07 | - | 集成 | 组内 6 L2 联调 | 0.5 天 | ≥ 12 |

### 3.1 WP-ζ-01 · L2-01 8 维度采集（订阅 IC-09）

**L3**：
- 调 Dev-α `register_subscriber(filter={event_type=*}) -> SubscriberHandle`
- 订阅所有 IC-09 事件
- 每 30s 扫一次（`scan_interval_sec`）
- 8 维度 state 更新：
  - `code_quality` / `progress` / `risk` / `compliance` / `resource` / `cost` / `quality` / `security`
- 发 `L1-07:scan_completed` IC-09 事件

**L4**：
```
app/l1_07/dim_collector/subscriber.py    ~200 行
app/l1_07/dim_collector/dim_scanner.py   ~250 行（8 维度各独立 scanner）
app/l1_07/dim_collector/state_cache.py   ~150 行
app/l1_07/dim_collector/schemas.py       ~150 行
```

**DoD**：~57 TC · 8 维度独立测 · 每 30s 扫准 · commit `ζ-WP01`

### 3.2 WP-ζ-02 · L2-04 IC-13/14/15 出口

**L3**：
- `push_suggestion(suggestion) -> Ack`（IC-13 · fire-and-forget）
  - 异步队列（bounded 1000 · 满则 drop oldest WARN）
- `push_rollback_route(wp_id, verdict_id, level)` → L1-04（IC-14）
  - Sync · 幂等（同 wp_id+verdict_id 返原 ack）
- `request_hard_halt(red_line_id)` → L1-01（IC-15）
  - **Sync 阻塞 ≤ 100ms 硬约束**
  - 优先级最高（抢占 IC-13 队列）

**L4**：
```
app/l1_07/event_sender/suggestion_queue.py   ~180 行
app/l1_07/event_sender/rollback_pusher.py    ~150 行
app/l1_07/event_sender/halt_requester.py     ~120 行（100ms 硬约束）
app/l1_07/event_sender/schemas.py            ~150 行
```

**DoD**：~56 TC · IC-15 100ms 硬约束测 · 队列背压测 · commit `ζ-WP02`

### 3.3 WP-ζ-03 · L2-06 死循环升级

**L3**：
- 订阅 L1-04 `wp_failed` 事件 · 维护 `FailureCounter` per wp_id
- 同级连 ≥ 3 failed → 升级到下一级（L1→L2→L3→L4→硬红线）
- 升级时调 L2-04 `push_rollback_route(level=L+1)`
- `on_wp_done_reset` · 成功后 counter 归零

**L4**：
```
app/l1_07/escalator/counter.py         ~150 行
app/l1_07/escalator/escalation_logic.py ~180 行
app/l1_07/escalator/schemas.py         ~120 行
```

**DoD**：~54 TC · 5 态机严格 · 连 3 升级测 · reset 幂等 · commit `ζ-WP03`

**ζ1 批完**：3 L2 + 3 天 · IC-13/14/15 出口可用 · 8 维度采集 ready · 连续升级 ready。

### 3.4 WP-ζ-04 · L2-02 4 级偏差判定

**L3**：
- `evaluate_deviation(dim_state) -> DeviationVerdict`
- 4 级：INFO / WARN / FAIL / CRITICAL
- 基于阈值矩阵（config）· 例：代码质量 coverage < 70% → WARN · < 50% → FAIL
- 触发 L2-04 push_suggestion

**L4**：
```
app/l1_07/deviation_judge/evaluator.py     ~250 行
app/l1_07/deviation_judge/threshold_matrix.py ~180 行
app/l1_07/deviation_judge/schemas.py       ~120 行
```

**DoD**：~55 TC · 4 级阈值测 · commit `ζ-WP04`

### 3.5 WP-ζ-05 · L2-03 硬红线拦截（100ms 硬约束）

**L3**：
- `intercept_red_line(event)` · 每 event 扫 5 类硬红线
  - HRL-01 不可逆操作（rm -rf / drop / force push main）
  - HRL-02 跨 project 数据泄漏
  - HRL-03 硬编码 skill 名违规
  - HRL-04 安全凭证泄漏
  - HRL-05 审计绕过尝试
- 拦截到 → 立即调 L2-04 `request_hard_halt` · **全链 ≤ 100ms 硬约束**
- evidence 完整性（必附证据 · 无证据 raise）

**L4**：
```
app/l1_07/red_line/detector.py            ~250 行（5 类 detector）
app/l1_07/red_line/irreversible_ops.py    ~120 行
app/l1_07/red_line/cross_project_check.py ~120 行
app/l1_07/red_line/hardcoded_scan.py      ~100 行
app/l1_07/red_line/secret_scan.py         ~120 行
app/l1_07/red_line/schemas.py             ~150 行
```

**DoD**：~57 TC · 5 类红线各 ≥ 5 TC · e2e ≤ 100ms（benchmark）· commit `ζ-WP05`

### 3.6 WP-ζ-06 · L2-05 Soft-drift 识别

**L3**：
- 滑窗统计（60 tick 窗口）· 8 类 trap 模式：
  - 温水煮青蛙（slow burn · 每 tick 轻微变差）
  - 范围蔓延（scope creep）
  - 优化僵局 · 伪同意 · 测试作弊 · 证据薄弱 · 性能退化 · 审计遗漏
- 命中 → 触发 L2-04 push_suggestion（WARN 级 · 不阻塞）

**L4**：
```
app/l1_07/soft_drift/pattern_matcher.py     ~250 行
app/l1_07/soft_drift/window_stats.py        ~180 行
app/l1_07/soft_drift/trap_patterns.py       ~180 行（8 类定义）
app/l1_07/soft_drift/schemas.py             ~150 行
```

**DoD**：~55 TC · 8 类模式各 ≥ 3 TC · commit `ζ-WP06`

### 3.7 WP-ζ-07 · 集成

- 组内 6 L2 联调：IC-09 事件 → 采集 → 判定 → 红线拦截 / 软漂移识别 → 升级路由 → IC-13/14/15 出口
- IC-15 100ms 硬约束端到端测
- commit `ζ-WP07`

---

## §4 依赖图

```
ζ-WP01 采集 ← IC-09 from α
  ↓
ζ-WP04 判定  ζ-WP05 红线  ζ-WP06 drift
  └──────────┴─────────────┘
               ↓
           ζ-WP02 出口 IC-13/14/15
               ↓
           ζ-WP03 升级
               ↓
           ζ-WP07 集成
```

### 跨组 mock

| 外部 | mock |
|:---|:---|
| IC-09 (α) | mock · 生成模拟事件流驱动 |
| IC-13/14/15 消费方（L1-01 / L1-04）| mock · assert 收到 |

---

## §5 standup + commit

复用 Dev-α · prefix `ζ-WPNN`。ζ1 会话做 WP01-03 · 然后 ζ2 会话做 WP04-07。

---

## §6 自修正

- 情形 A · 硬红线 5 类实际场景需调整 · 改 3-3 hard-redlines + scope §8.5
- 情形 B · 软漂移 8 类模式实测不全 · 改 3-1 L2-05 §6 + 3-3 soft-drift-patterns

---

## §7 对外契约

| IC | 方法 | 角色 |
|:---|:---|:---|
| IC-13 发起 | `push_suggestion` | → L1-01 · fire-and-forget |
| IC-14 发起 | `push_rollback_route` | → L1-04 · 幂等 |
| IC-15 发起 | `request_hard_halt` | → L1-01 · **Sync ≤ 100ms 硬约束** |

---

## §8 DoD

- 6 L2 全绿 · 333 TC · coverage ≥ 85%
- IC-15 100ms 硬约束测（benchmark 3 次均值）
- 8 维度采集 + 4 级判定 + 5 红线 + 8 软漂移 · 全覆盖
- PM-14 per-pid supervisor 实例（V2+ 准备）

---

## §9 风险

- **R-ζ-01** IC-15 100ms 硬约束实测不达 · 优化热路径 / 走 §6 情形 B 改 3-1 §12 SLO
- **R-ζ-02** Soft-drift 误报率高 · 调阈值 + 窗口 + 走 §6 情形 A 改 PRD 定义

---

## §10 交付清单

### 代码（~25500 行）

```
app/l1_07/
├── dim_collector/      (~750 行)
├── deviation_judge/    (~550 行)
├── red_line/           (~860 行)
├── event_sender/       (~600 行)
├── soft_drift/         (~760 行)
└── escalator/          (~450 行)
```

### 测试（~8000 行）· 333 TC

### commit（13-15 个）

---

*— Dev-ζ · L1-07 监督 · Execution Plan · v1.0 —*
