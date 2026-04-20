---
doc_id: prd-l1-01-main-agent-loop-v0.1
doc_type: l1-prd
parent_doc:
  - HarnessFlowGoal.md
  - docs/prd/businessFlow.md
  - docs/prd/scope.md#5.1
version: v0.1-skeleton
status: draft
author: mixed
created_at: 2026-04-20
updated_at: 2026-04-20
traceability:
  goal_anchor: HarnessFlowGoal.md#2 产品定位 "主 Agent loop"
  business_flow: [BF-L3-01, BF-L3-12, BF-L3-13, BF-L3-14, BF-L3-15, BF-X-01]
  scope: [L1-01]
consumer:
  - docs/prd/flowOutInput.md#4.3
  - docs/prd/L1集成/prd.md
  - TDD 阶段
---

# L1-01 · 主 Agent 决策循环能力 · PRD

> **版本**：v0.1 (骨架 · 待 L2 详细填充)
> **定位**：L1-01 的独立 PRD，细化到 L2（6 个子能力）→ L3（算法/数据结构/接口/流程图），为技术方案做输入。
> **严格遵循**：本 PRD **不得与** `docs/prd/scope.md §5.1` 定义冲突。如冲突，以 scope.md 为准。

---

## 0. 撰写进度

- [x] §1 L1-01 范围锚定（引用 scope）
- [x] §2 L2 清单（6 个）
- [x] §3 L2 整体架构 · 图 A 主干控制流
- [x] §4 L2 整体架构 · 图 B 横切响应面
- [x] §5 L2 间业务流程（9 条）
- [x] §6 IC-L2 契约清单（10 条 · 字段粗案）
- [x] §7 L2 定义模板（9 小节标准）
- [x] §8 L2-01 · Tick 调度器 详细定义（R3 完成：9 小节 + L3 实现设计 7 子节）
- [x] §9 L2-02 · 决策引擎（R4 完成：9 小节 + L3 实现设计 10 子节）
- [x] §10 L2-03 · 状态机编排器（R5 完成：9 小节 + L3 · allowed_next 表 + 转换算法 + hook 清单 + 幂等性）
- [x] §11 L2-04 · 任务链执行器（R5 完成：9 小节 + L3 · chain_def schema + mini SM + 步调度/超时/嵌套）
- [x] §12 L2-05 · 决策审计记录器（R6 完成：9 小节 + L3 · audit_entry schema + 打包算法 + event type 映射 + 反查索引）
- [x] §13 L2-06 · Supervisor 建议接收器（R6 完成：9 小节 + L3 · 建议队列 schema + 4 级路由算法 + BLOCK 广播 + 健康监测）
- [x] §14 L1-01 对外 scope §8 IC 契约映射（R7 完成：被调 4 条 + 发起 7 条 + 承担矩阵图）
- [x] §15 本 L1 retro 位点（R7 完成：11 项 retro 模板）
- [x] §16 L3 详细（已合并到每 L2 的 §X.10 · 不单独章节）
- [x] 附录 A 术语 · 附录 B BF 映射 · 附录 C IC-L2 字段示例

---

## 1. L1-01 范围锚定（引自 scope §5.1，不重复写）

| scope §5.1 子节 | 内容摘要 | 锚点 |
|---|---|---|
| §5.1.1 职责 | 持续 tick → 决策 → 执行 → 留痕；HarnessFlow 控制流唯一源 | scope#5.1.1 |
| §5.1.2 输入/输出 | 输入 5 类事件 / 输出决策 + 执行 + 事件 | scope#5.1.2 |
| §5.1.3 边界 | 只做决策调度，不做业务；6 条 Out-of-scope | scope#5.1.3 |
| §5.1.4 约束 | PM-02/10/11 + 4 条硬约束 | scope#5.1.4 |
| §5.1.5 🚫 禁止行为 | 6 条（直接改 task-board、跳过 5 纪律、多 loop 实例...） | scope#5.1.5 |
| §5.1.6 ✅ 必须义务 | 6 条（留决策理由、响应 BLOCK、tick ≤ 30s...） | scope#5.1.6 |
| §5.1.7 与其他 L1 交互 | 9 行交互表 | scope#5.1.7 |
| 对外 IC 契约 | IC-01/09/13/14/15/17（scope §8.2） | scope#8.2 |

**本 PRD 的职责**：把 L1-01 内部拆成 **6 个 L2** + 画清楚它们之间的 **架构 / 业务流 / 契约**，为各 L2 独立实现提供边界。

---

## 2. L2 清单（6 个 · 含新增 L2-06）

| L2 ID | 名称 | 一句话职责 | 聚合自 BF | 核心问题 |
|---|---|---|---|---|
| **L2-01** | Tick 调度器 | 4 触发源统一接入 + 优先级仲裁 + 去抖 + 健康心跳（≤30s）+ 异步结果回收入口 + 启动恢复入口 | BF-L3-12 | 何时 tick |
| **L2-02** | 决策引擎 | 上下文组装 + KB 注入 + 5 纪律拷问 + 决策树分派 + 对外调度（L1-05/06/08/10） | BF-L3-01 + BF-L3-14 | tick 做什么 |
| **L2-03** | 状态机编排器 | allowed_next 查询 + state 转换 + 阶段 entry/exit hook（KB 注入 / 事件广播） | BF-L3-13 | state 怎么转 |
| **L2-04** | 任务链执行器 | 多步 chain 管理 + mini state machine + 步完成回调 + 步失败回滚 | BF-L3-15 | 复杂决策怎么展开 |
| **L2-05** | 决策审计记录器 | 决策留痕打包 + 证据链组装 + IC-09 落事件总线 + 审计反查索引 | BF-L3-01 step⑥ + BF-X-01 | 决策怎么留痕 |
| **L2-06** | Supervisor 建议接收器（NEW） | 接收 L1-07 的 INFO/SUGG/WARN/BLOCK → 4 级路由分派（L2-01/02/05）+ 建议队列持久化 + 4 级计数 | BF-X-02 + scope §5.1.6"必须响应 BLOCK/WARN" | supervisor 建议怎么分派 |

---

## 3. L2 整体架构 · 图 A 主干控制流

```
                    L1-01 主 Agent 决策循环（6 个 L2）
                    ═══════════════════════════════════════

 外部触发源 (4 种)
 ────────────────────────┐
 事件总线新事件 ┐        │
 PostToolUse   ┤        │
 30s 周期 tick ┤        ▼
 Hook 信号     ┘ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                 ┃  L2-01 Tick 调度器        ┃ ←── IC-L2-08 propagate_hard_halt
                 ┃   · 4 触发源接入          ┃     (from L2-06 BLOCK 级)
                 ┃   · 优先级 / 去抖          ┃
                 ┃   · 心跳 watchdog (30s)   ┃
                 ┃   · 异步结果回收入口       ┃ ← 子 Agent / 长 skill 回传事件
                 ┃   · 首次启动 / 恢复入口    ┃ ← 跨 session 恢复
                 ┗━━━━━━━━━┳━━━━━━━━━━━━━━━━━┛
                           │ IC-L2-01 on_tick()
                           ▼
                 ┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                 ┃  L2-02 决策引擎            ┃ ←── IC-L2-10 dispatch_suggestion
                 ┃   · 上下文组装（L3）        ┃     (from L2-06 SUGG/WARN 级)
                 ┃   · KB 注入                ┃
                 ┃   · 5 纪律拷问             ┃ ─── 调 skill / 工具 → (外部 L1-05)
                 ┃   · 决策树分派             ┃ ─── 读写 KB          → (外部 L1-06)
                 ┃   · 决策选择               ┃ ─── 读内容           → (外部 L1-08)
                 ┃                          ┃ ─── 请示用户          → (外部 L1-10)
                 ┗━┳━━━━━━━━━━━━━━┳━━━━━━━━━┛
                   │IC-L2-02        │IC-L2-03
            ┌──────▼───────┐   ┌────▼───────────┐
            ┃ L2-03        ┃   ┃ L2-04          ┃
            ┃ 状态机编排器  ┃   ┃ 任务链执行器    ┃
            ┃  · allowed_  ┃   ┃  · chain 管理   ┃
            ┃    next      ┃   ┃  · mini SM     ┃
            ┃  · 转换执行  ┃    ┃  · 步失败回滚   ┃
            ┃  · 阶段 hook ┃   ┃  · 升级告警     ┃
            ┗━━┳━━━━━━━━━━━┛   ┗━━┳━━━━━━━━━━━━━┛
               │ IC-L2-06          │ IC-L2-04 (步完成回调 L2-02)
               │                   │ IC-L2-07
               ▼                   ▼
       ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
       ┃  L2-05 决策审计记录器                 ┃
       ┃   · IC-L2-05 统一审计入口            ┃ ← IC-L2-09 (L2-02 WARN 书面回应)
       ┃   · 打包 + 证据链 + IC-09 落事件总线   ┃
       ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                         │
                         │ 通过 IC-09 append_event
                         ▼
                  (外部 L1-09 事件总线)
```

**关键规则**：
- L2-01 是唯一触发口（4 种触发源统一接入）
- L2-02 是唯一决策源（所有决策都经它）
- L2-05 是唯一审计口（所有 L2 留痕走它）
- L2-06 是 supervisor 建议唯一入口（4 级分派到 L2-01/02/05）

---

## 4. L2 整体架构 · 图 B 横切响应面

```
 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 1 · Supervisor 建议 4 级分派                               ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║          (外部 L1-07 supervisor)                                 ║
 ║               │                                                  ║
 ║               │ IC-13 push_suggestion + IC-15 request_hard_halt  ║
 ║               ▼                                                  ║
 ║   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓                          ║
 ║   ┃ L2-06 Supervisor 建议接收器       ┃                          ║
 ║   ┃  · 建议队列 (FIFO + 优先级)        ┃                          ║
 ║   ┃  · 4 级计数 (观察 supervisor 是否健康)┃                       ║
 ║   ┃                                   ┃                          ║
 ║   ┃  4 级路由:                         ┃                          ║
 ║   ┃   INFO  ─→ IC-L2-05 L2-05 只记录    ┃                          ║
 ║   ┃   SUGG  ─→ IC-L2-10 L2-02 下轮参考  ┃                          ║
 ║   ┃   WARN  ─→ IC-L2-10 L2-02 必书面回应│                          ║
 ║   ┃           → IC-L2-09 L2-05 留痕     ┃                          ║
 ║   ┃   BLOCK ─→ IC-L2-08 L2-01 硬暂停     ┃                          ║
 ║   ┃           → IC-L2-05 L2-05 留痕       ┃                        ║
 ║   ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛                          ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 2 · 异步结果回收（子 Agent / 长 skill 回传）                ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-02 决策 = "委托子 Agent / 长 skill"                            ║
 ║   → 调 L1-05 delegate_subagent (异步)                            ║
 ║   → L2-02 立即结束当前 tick（不阻塞）                              ║
 ║   → 子 Agent 独立 session 执行中... (可能几分钟)                  ║
 ║   → 完成后 L1-05 发 `subagent_result` 事件 → L1-09 事件总线       ║
 ║   → L2-01 作为新触发源收到 → 新一轮 tick                          ║
 ║   → L2-02 决策 = 消费回传结果继续执行                              ║
 ║                                                                  ║
 ║ 原则: tick 不阻塞等外部，外部回来 = 新事件 = 新 tick               ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 3 · 用户紧急介入 panic                                     ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ (外部 L1-10 UI panic 按钮) → user_panic 事件                     ║
 ║   → L2-01 最高优先级中断当前 tick（不管在哪一步）                   ║
 ║   → L2-01 调 L2-05 flush 当前 snapshot                            ║
 ║   → L2-05 通过 IC-09 落 checkpoint 到 L1-09                      ║
 ║   → L2-03 请求 state 转为 PAUSED                                 ║
 ║   → 等用户恢复指令（从 L1-10 IC-17 user_intervene type=resume）    ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 4 · 跨 session 恢复首次 tick (bootstrap)                   ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ Claude Code 重启 → L1-09 task-board 重建完成                      ║
 ║   → 发 `system_resumed` 事件                                     ║
 ║   → L2-01 特殊首次 tick (标 bootstrap=true, priority=highest)      ║
 ║   → L2-02 决策: 从 state_history 末尾分析"退出时在做什么"          ║
 ║     → 如在 WP 执行中 → 继续该 WP                                   ║
 ║     → 如在 Stage Gate 等待 → 重推 Stage Gate 卡片给 UI             ║
 ║     → 如在 PAUSED → 等用户解除                                     ║
 ╚══════════════════════════════════════════════════════════════════╝
```

---

## 5. L2 间业务流程（9 条）

### 流 A · 正常一轮 tick（决策 = 调外部能力）

```
[外部事件到达]
   ↓
L2-01: 4 触发源仲裁 + 去抖 + 优先级 → IC-L2-01 on_tick()
   ↓
L2-02:
   1. 上下文组装（current state + 近 N 事件 + supervisor 建议队列 + KB 注入）
   2. 5 纪律拷问（规划/质量/拆解/检验/交付）
   3. 决策树分派 → 决定 = "调 skill X"
   ↓
L2-02 → IC-04 invoke_skill() → (外部 L1-05)
   ↓ 接收结构化 skill 结果
L2-02: 整合结果 → 本 tick 收尾
   ↓ IC-L2-05 record_audit()
L2-05: 打包决策 + 理由 + 证据 → IC-09 落事件总线
   ↓
循环等下一个 tick
```

### 流 B · 决策 = 阶段切换（跨 state 转换）

```
L2-02 决策 = "当前阶段 DoD 已满足, 进下阶段"
  ↓ IC-L2-02 request_state_transition(to=X, reason)
L2-03: 查 allowed_next (来自 state-machine 定义)
    ├── 合法 → 执行转换 → 触发 exit hook (本 state 清理)
    │                  → 触发 entry hook (KB 注入新阶段模式)
    │                  → IC-L2-06 → L2-05 审计 "state Y → X"
    │                  → 返回 L2-02 accepted
    └── 非法 → 返回 reject → L2-02 停留原阶段 → L2-05 记"非法转换"
```

### 流 C · 决策 = 启动多步任务链

```
L2-02 识别"多步串联"（如 "先 brainstorm 再 writing-plans 再 TDD"）
  ↓ IC-L2-03 start_chain(chain_def=[step1, step2, step3])
L2-04: 启动 mini state machine
  → 执行 step1 (可能调 L2-02 继续决策 → 调 L1-05)
  → step1 完成 → IC-L2-04 step_completed → L2-02
  → L2-02 决策: 继续 / 中止 / 调整
  → L2-04 继续 step2 → ...
  → 全 chain 完成 → 整合结果给 L2-02
  ↓ IC-L2-07 → L2-05 审计每步
```

### 流 D · 健康心跳 + 空转检测

```
L2-01 watchdog 每 5s 检查:
  1. 当前 tick 处理时间 > 30s
     → 告警 (L2-05 记 tick_timeout)
     → 通知 L1-07 (external supervisor 会读到)
  2. 连续 N 次 tick 后 L2-02 持续返回 "无可做"
     → tick 空转告警 (INFO 级, L2-05 记)
  3. L2-04 同 step 失败 ≥ 3 次
     → 升级请求 → IC-L2-10 to L2-06 → 转发 L1-07
```

### 流 E · Supervisor 建议 4 级分派（P0 新增）

```
(外部) L1-07 supervisor 发 IC-13 push_suggestion / IC-15 request_hard_halt
  ↓
L2-06: 接收 → 归入建议队列 → 4 级计数器 +1
  ↓ 按 level 分派:
  ├── INFO
  │    → IC-L2-05 直接调 L2-05 记录（"supervisor INFO: xxx"）
  │    → 不干预 L2-02/01
  │
  ├── SUGG (SUGGESTION)
  │    → IC-L2-10 dispatch_suggestion(SUGG, content) → L2-02 建议队列
  │    → L2-02 下一次决策 tick 时参考，可采纳或驳回
  │    → 如驳回 → IC-L2-09 record_warn_response 记"驳回理由"
  │
  ├── WARN
  │    → IC-L2-10 dispatch_suggestion(WARN, content) → L2-02 必回应队列
  │    → L2-02 **下一次 tick 必须响应**（采纳或书面驳回+理由）
  │    → IC-L2-09 L2-05 记录回应（PM-12 书面回应留痕）
  │
  └── BLOCK
       → IC-L2-08 propagate_hard_halt(red_line_id) → L2-01
       → L2-01 立即暂停 tick 调度
       → L2-02 当前决策被中断（若在进行中）
       → IC-L2-05 L2-05 记"supervisor BLOCK: xxx"
       → 等待用户文本授权（IC-17 from L1-10）才解除
```

### 流 F · 异步结果回收（P0 新增）

```
L2-02 决策 = "委托子 Agent / 长 skill"
  → IC-05 delegate_subagent() (异步, L1-05 启独立 session)
  → L2-02 立即结束当前 tick（不阻塞等待）
  → IC-L2-05 记"子 Agent X 已委托"

(几分钟后)
子 Agent 完成 → L1-05 发 subagent_result 事件 → L1-09 事件总线
  ↓
L2-01 作为"事件总线新事件"触发源接收 → IC-L2-01 on_tick(priority=high)
  ↓
L2-02: 上下文组装 → 发现"有一个委托回传结果要消费"
  → 决策 = "消费结果, 继续业务"
  → 整合 result 到当前业务流 (可能进入下一 WP / 下阶段)
```

### 流 G · 用户紧急 panic 介入（P1 新增）

```
(外部) L1-10 UI panic 按钮 → user_panic 事件 → L1-09 事件总线
  ↓
L2-01 最高优先级（panic 不走常规去抖）→ 中断当前 tick
  → 不管 L2-02 / L2-03 / L2-04 在做什么都立即暂停
  → IC-L2-05 flush 当前所有待审计事件 → L2-05 → IC-09 落盘
  → IC-L2-02 request_state_transition(to=PAUSED, reason=user_panic)
  → L2-03 执行转换 → entry hook 生成"已暂停"卡片给 L1-10

(等用户)
用户解除 → L1-10 IC-17 user_intervene(type=resume)
  → L2-01 接收 → 按"从 PAUSED 恢复"处理 → 回流 H bootstrap
```

### 流 H · 跨 session 恢复首次 tick（P1 新增）

```
(Session 启动)
Claude Code 重启 → L1-09 扫 task-boards/ → 重建 task-board
  → 发 system_resumed 事件
  ↓
L2-01 接收（特殊首 tick, bootstrap=true, priority=highest）
  → IC-L2-01 on_tick(trigger_source=bootstrap)
  ↓
L2-02:
  → 读 task-board 当前 state + state_history 末尾 3 条
  → 判定"退出时在做什么"：
     ├── WP 执行中 → 继续该 WP (决策 = 恢复 WP 执行)
     ├── Stage Gate 等待 → 重推 Stage Gate 卡片到 L1-10
     ├── PAUSED → 等用户恢复指令
     └── 不明状态 → 告警给用户"状态不明, 请确认如何继续"
  → IC-L2-05 记 "system_resumed: continuing from state=X"
```

### 流 I · 硬红线 BLOCK 拦截完整链（P0 新增）

```
(前提: L1-07 supervisor 识别硬红线, 如 IRREVERSIBLE_HALT)
  ↓ IC-15 request_hard_halt(red_line_id)
L2-06: 接收 → level=BLOCK
  → IC-L2-08 propagate_hard_halt(red_line_id) → L2-01
  ↓
L2-01:
  1. 立即停止接受新 tick
  2. 如当前有正在进行的 tick → 发中断信号给 L2-02
  3. L2-02 放下当前决策 → 回到"等待"状态
  → IC-L2-05 L2-05 记"hard_halt triggered"
  → L2-01 向 L1-10 UI 广播"系统硬暂停, 等待用户授权"
  ↓
(用户看 UI 告警 → 决定)
用户 IC-17 user_intervene(type=authorize, payload=授权理由)
  → L1-01 接收 → L2-01 解除硬暂停
  → 恢复接受 tick
  → IC-L2-05 记"hard_halt cleared by user"
```

---

## 6. IC-L2 契约清单（10 条 · 字段粗案）

> 字段级详细 schema 在 R3+ 各 L2 详细定义时精确化。本表为"结构骨架"。

| ID | 调用方 | 被调方 | 方法签名 | 意义 | 字段骨架 |
|---|---|---|---|---|---|
| **IC-L2-01** | L2-01 | L2-02 | `on_tick(trigger_source, event_ref, priority, ts, bootstrap?)` | Tick 调度器把"可决策信号"交给决策引擎 | `{trigger_source: event/proactive/periodic/hook/bootstrap, event_ref: event_id?, priority: int [0-10], ts: iso, bootstrap: bool}` |
| **IC-L2-02** | L2-02 | L2-03 | `request_state_transition(from, to, reason, evidence_refs)` | 决策引擎决定换 state 时统一走编排器 | `{from_state, to_state, reason: str, evidence_refs: [event_id], trigger_tick: tick_id}` · returns `{accepted: bool, new_entry: state_history_entry}` |
| **IC-L2-03** | L2-02 | L2-04 | `start_chain(chain_def, chain_goal, context)` | 启动多步任务链 | `{chain_def: [{step_id, action, deps, expected_outcome}], chain_goal: str, context: obj}` · returns `{chain_id}` |
| **IC-L2-04** | L2-04 | L2-02 | `step_completed(chain_id, step_id, outcome, result_ref)` | 每步完成回调决策引擎 | `{chain_id, step_id, outcome: pass/fail/skip, result_ref: event_id, next_hint?}` |
| **IC-L2-05** | 全 L2 | L2-05 | `record_audit(audit_entry)` | 统一审计入口 | `{actor: L2-XX, action, reason: str, evidence: [event_id], ts, linked_tick?: tick_id}` · returns `{audit_id}` |
| **IC-L2-06** | L2-03 | L2-05 | `record_state_transition(from, to, reason, pre, post)` | 状态转换专用审计 | `{from_state, to_state, reason, pre_snapshot_ref, post_snapshot_ref, entry_hook_result?, ts}` |
| **IC-L2-07** | L2-04 | L2-05 | `record_chain_step(chain_id, step, outcome)` | 任务链步骤审计 | `{chain_id, step_id, action, outcome, step_result, ts}` |
| **IC-L2-08** ⭐ | L2-06 | L2-01 | `propagate_hard_halt(red_line_id, message)` | BLOCK 级硬暂停广播 | `{red_line_id: DRIFT_CRITICAL/IRREVERSIBLE_HALT/..., message: str, supervisor_event_id}` · returns `{halted_at_tick: tick_id}` |
| **IC-L2-09** ⭐ | L2-02 | L2-05 | `record_warn_response(warn_id, response, reason)` | WARN 级书面回应留痕 | `{supervisor_warn_id, response: accept/reject, reason: str, applied_action?: obj, ts}` |
| **IC-L2-10** ⭐ | L2-06 | L2-02 / L2-05 | `dispatch_suggestion(level, content, target)` | 4 级路由分派 | `{level: INFO/SUGG/WARN/BLOCK, content: obj, target_l2: L2-02/L2-05, priority, ts}` |

⭐ = 本 PRD 新增（scope §8 没有，属 L2 内部契约）

---

## 7. L2 定义模板（每 L2 必含 9 小节）

每个 L2 的详细定义（§8-§13）必须按以下模板撰写，**不得省略任一小节**：

| # | 小节 | 内容 |
|---|---|---|
| 1 | **职责 + 锚定** | 一句话职责 + Goal / BF / scope §5.1 的锚点 |
| 2 | **输入 / 输出** | 输入事件 / 方法调用清单 + 产出事件 / 方法调用清单（含 schema 引用） |
| 3 | **边界** | In-scope（做什么）/ Out-of-scope（不做什么，谁做）/ 边界规则 |
| 4 | **约束** | 业务模式引用（PM-XX）+ 硬约束清单 + 性能约束（如有） |
| 5 | **🚫 禁止行为** | 明确清单（5-8 条）· 违反即破坏 L2 边界 |
| 6 | **✅ 必须职责** | 明确清单（5-8 条）· 必做否则 L2 失职 |
| 7 | **🔧 可选功能职责** | 明确清单（3-5 条）· 可做但不硬性要求（增值） |
| 8 | **与其他 L2 交互** | IC-L2-XX 契约表（接口签名 + 字段 + 使用说明 + 意义） |
| 9 | **🎯 交付验证大纲** | 成功信号 + 最小正向测试 + 最小负向测试（对应 🚫/✅）+ 集成用例 + 性能阈值 — **TDD 阶段直接以本节为输入** |

L3 详细（算法 / 数据结构 / 内部状态机 / 流程图）在每个 L2 的小节内或追加的 L3 子章节展开。

---

## 8. L2-01 · Tick 调度器 详细定义

### 8.1 职责 + 锚定

**一句话职责**：HarnessFlow 的"心跳起搏器" —— 接收所有外部触发源，按优先级 + 去抖规则仲裁后，派发 tick 到 L2-02 决策引擎；全程守护 tick 健康（≤30s 心跳、空转检测、硬暂停响应、异步结果回收、跨 session bootstrap）。

**上游锚定**：
- Goal §1 一句话目标："以主 Skill Agent loop 为执行核心"
- scope §5.1.6 必须义务："tick 响应 ≤ 30s"、"响应 BLOCK 立即暂停"
- businessFlow BF-L3-12 loop 触发机制流（4 种触发源并集）
- businessFlow BF-X-01 主 Agent 决策心跳横切

**下游服务**：L2-02（决策引擎）· L2-05（通过 IC-L2-05 审计）· L2-06（接收 IC-L2-08 硬暂停）

---

### 8.2 输入 / 输出

#### 输入（5 类触发源 + 2 个响应通道）

| 类别 | 输入事件 | 来源 | 特征 |
|---|---|---|---|
| **event_driven** | 事件总线新事件（非 L2-01 自己产生的） | L1-09 事件总线订阅 | 异步、高频、受去抖约束 |
| **proactive** | 主动唤醒（上一 tick 完成 + 有未消费的 pending 队列） | L2-01 内部自调度 | 保持 loop 活跃 |
| **periodic** | 30s 周期心跳 tick | OS timer / 内置 scheduler | 低频、用于 L2-02 做空闲自省 |
| **hook** | SessionStart / state_transition hook | Claude Code hook 机制 | 事件型 |
| **bootstrap** | `system_resumed` 事件（重启后 task-board 重建完成） | L1-09 恢复流程 | 一次性、最高优先级 |
| **panic**（响应通道 1） | `user_panic` 事件 | L1-10 UI panic 按钮 | 中断现行 tick |
| **hard_halt**（响应通道 2） | IC-L2-08 propagate_hard_halt | L2-06 BLOCK 级分派 | 立即暂停整个调度 |

#### 输出（3 类）

| 类别 | 输出 | 去向 | schema |
|---|---|---|---|
| **on_tick 调用** | IC-L2-01 `on_tick(trigger_source, event_ref, priority, ts, bootstrap?)` | L2-02 决策引擎 | §6 IC-L2-01 字段骨架 |
| **审计事件** | IC-L2-05 `record_audit(tick_scheduled / tick_completed / watchdog_alert / hard_halt_received / panic_intercepted)` | L2-05 决策审计记录器 | §5 audit_entry schema |
| **state 暂停请求**（panic 场景） | IC-L2-02 `request_state_transition(to=PAUSED)` | L2-03 状态机编排器 | §5 state_transition schema |

---

### 8.3 边界

#### In-scope（本 L2 做什么）

1. 4 触发源 + 2 响应通道的统一接入
2. 优先级表（含可配置覆盖）+ 仲裁算法
3. 去抖动（按 trigger_source 分桶 + 合并窗口）
4. 健康 watchdog（tick 超时 / 空转 / 死循环升级转发）
5. 异步结果回收入口（L1-05 子 Agent 异步回传 → 作为 event_driven 触发源 → 新 tick）
6. Bootstrap tick（跨 session 恢复首次触发）
7. Panic 中断处理 + PAUSED 状态进入
8. Hard_halt 接收 + RUNNING 中断 + 保持 HALTED
9. 调度队列管理（pending / current / debounce buckets）
10. 内部状态机（INIT / IDLE / RUNNING / DEGRADED / HALTED / PAUSED）

#### Out-of-scope（本 L2 不做，谁做）

- ❌ **不做决策内容** → L2-02
- ❌ **不改 task-board / 事件总线** → L2-05 走 IC-09 落盘
- ❌ **不生成 supervisor 事件**（watchdog 只记审计，真正发 supervisor 事件是 L1-07 读审计后自己发） → L1-07
- ❌ **不处理 state 转换业务**（仅在 panic 时请求 PAUSED） → L2-03
- ❌ **不拉取 KB** → L2-02 的职责（决策时注入）
- ❌ **不管 chain 内部步骤超时**（只管整个 tick 超时） → L2-04

#### 边界规则

- 本 L2 只做"**调度**"，不碰"**内容**"
- 触发源增加（如未来新增 webhook / MCP event）只改本 L2 的接入层，不影响其他 L2
- 优先级表可配置，但**默认值属于 L1-01 标准**

---

### 8.4 约束

#### 业务模式引用

- **PM-10 事件总线单一事实源**：所有 tick 审计走 IC-L2-05 → L2-05 → IC-09 → L1-09
- **PM-02 主-副 Agent 协作**：watchdog 只生成审计事件，不主动发 supervisor 事件（避免竞争）

#### 硬约束清单

1. **tick 响应健康阈值 = 30s**（scope §5.1.4 硬约束 4；超时必告警）
2. **watchdog 扫描间隔 = 5s**（默认，可配置 3-10s）
3. **去抖窗口 = 500ms**（默认，可配置 100-2000ms）
4. **bootstrap / panic / hard_halt 3 类永不去抖**（延迟 = 0）
5. **单 session 只能有一个 L2-01 实例**（scope §5.1.4 硬约束 1）
6. **队列深度上限 = 1000**（防雪崩；超限丢弃最低 priority，记审计）
7. **优先级表的默认值不可删减**（可改值，不可删键）

#### 性能约束

- trigger 接入 → 入 queue 延迟 ≤ 10ms
- 仲裁决策 ≤ 5ms
- watchdog 扫描开销 ≤ 1% CPU
- 调度吞吐 ≥ 100 tick/s（无外部 IO）

---

### 8.5 🚫 禁止行为（明确清单）

- 🚫 **禁止直接调 L2-02 以外的 L2**（除 panic 时调 L2-03 / 硬暂停内部响应）——保持单一决策入口
- 🚫 **禁止跳过去抖**（仅 bootstrap / panic / hard_halt 例外，且必须显式标记）
- 🚫 **禁止阻塞 tick 调度线程 > 30s**（watchdog 会抓，违反即硬约束破坏）
- 🚫 **禁止消费外部事件总线事件后不入队列直接丢弃**（所有 trigger 必须留痕）
- 🚫 **禁止在 HALTED 状态下派发新 tick**（除非收到 user_intervene 解除）
- 🚫 **禁止绕过优先级仲裁直接派发**（除非 bootstrap / panic / hard_halt 3 类）
- 🚫 **禁止修改已入队的 TickTrigger**（入队即不可变）

---

### 8.6 ✅ 必须职责（明确清单）

- ✅ **必须**接入 5 类触发源（event / proactive / periodic / hook / bootstrap）+ 2 响应通道（panic / hard_halt）
- ✅ **必须**在 hard_halt 到达 ≤ 100ms 内暂停调度（scope §5.1.6 必须义务"响应 BLOCK"）
- ✅ **必须**每 5s 扫 watchdog
- ✅ **必须**每 tick 生成 TickRecord + IC-L2-05 审计
- ✅ **必须**支持 bootstrap tick（跨 session 恢复 BF-E-02）
- ✅ **必须**对 panic 做 ≤ 100ms 响应 + flush 当前审计 + 请求 PAUSED
- ✅ **必须**维护调度队列的 priority + FIFO 次序不变量（incoming same-priority FIFO）
- ✅ **必须**暴露内部状态给 L1-10 UI 查询（queue 深度 / current tick / 近 N 条 TickRecord）

---

### 8.7 🔧 可选功能职责（可做但不硬性要求）

- 🔧 **触发源可视化面板**：实时展示 5 类触发频率柱状图（增值 UI，L1-10 消费）
- 🔧 **自适应去抖窗口**：根据近 1min 触发密度动态调整去抖窗口（100-2000ms 自适应，默认关）
- 🔧 **触发源限速**（rate limit）：同 trigger_source 超过 N/sec 自动降级到 periodic 模式（防刷）
- 🔧 **tick 回放**：从事件总线读历史 trigger + 重放（给调试用，release 时默认关）
- 🔧 **优先级 A/B 测试钩子**：允许测试不同优先级表对决策质量的影响（实验特性）

---

### 8.8 与其他 L2 交互（IC-L2 契约实现）

L2-01 **作为调用方**：

| IC | 被调方 | 何时调 | 调用字段（关键） |
|---|---|---|---|
| **IC-L2-01** | L2-02 | 每次派发 tick | `{trigger_source, event_ref, priority, ts, bootstrap?}`（见 §6） |
| **IC-L2-05** | L2-05 | 每次 tick 完成 / watchdog 告警 / hard_halt 收到 / panic 拦截 | `{actor: L2-01, action: tick_scheduled/completed/timeout/..., reason, evidence, ts, linked_tick}` |
| **IC-L2-02** | L2-03 | 仅 panic 场景 | `{from, to: PAUSED, reason: user_panic}` |

L2-01 **作为被调方**：

| IC | 调用方 | 何时被调 | 接收字段 |
|---|---|---|---|
| **IC-L2-08** | L2-06 | supervisor BLOCK 级触发 | `{red_line_id, message, supervisor_event_id}` → L2-01 必须 ≤ 100ms 响应 state=HALTED |

**外部对 L2-01 的调用**（通过 L1-01 对外 IC 路径）：

| 外部 IC | 来自 | 使用说明 |
|---|---|---|
| L1-09 事件订阅 | L1-09 事件总线 | L2-01 订阅 `system_resumed` / `subagent_result` / `user_panic` / 其他 event_driven |
| L1-10 user_intervene(resume) | L1-10 UI | 从 HALTED / PAUSED 返回 IDLE |

---

### 8.9 🎯 交付验证大纲（TDD 直接消费）

#### 成功信号（系统跑起来能看到的）

- 启动后 `L2-01.state = IDLE` 且 watchdog 已开始扫
- 外部事件到达后 `TickRecord.duration_ms < 30000` 连续 100 条
- queue 深度长期 < 100（健康）
- bootstrap 事件到达后，首个 TickRecord 标 `trigger.bootstrap=true`

#### 最小正向测试用例（对应 ✅ 必须职责）

| # | 场景 | 验证点 |
|---|---|---|
| P1 | 发送 event_driven trigger → 期望 `on_tick` 被调 + TickRecord 落 | 接入 + 派发 |
| P2 | 发送 hard_halt → 期望 ≤ 100ms `state=HALTED` + 拒绝新 tick 派发 | hard_halt 响应 |
| P3 | 发送 user_panic → 期望 ≤ 100ms 中断 current tick + `state=PAUSED` | panic 响应 |
| P4 | 发送 bootstrap → 期望首 tick `trigger.bootstrap=true` + priority=100 | bootstrap |
| P5 | 500ms 内同 trigger_source 发 10 次 → 期望只派发 1 次 on_tick（去抖） | 去抖 |
| P6 | 多源同时到达（periodic + event） → 期望先派发 event（priority 高） | 仲裁 |
| P7 | 连续 5 次 tick 返回"无可做" → 期望 `idle_spin_detected` 审计事件 | 空转检测 |
| P8 | tick 模拟耗时 35s → 期望 `tick_timeout` 审计事件 + `state=DEGRADED` | watchdog |

#### 最小负向测试用例（对应 🚫 禁止行为）

| # | 场景 | 验证点 |
|---|---|---|
| N1 | 尝试直接调 L2-03 request_state_transition（非 panic 上下文）→ 期望拒绝 + 审计违规 | 禁止 |
| N2 | 尝试 bootstrap 走去抖 → 期望立即派发不被合并 | 禁止 |
| N3 | 队列满（1000 条）+ 新 trigger → 期望丢弃最低 priority + 审计 | 防雪崩 |
| N4 | HALTED 状态下发 event_driven → 期望不派发（入队暂存） | HALTED 禁派 |
| N5 | 同时启动 2 个 L2-01 实例 → 期望第二个拒绝启动 | 单实例 |

#### 集成用例（跨 L2）

| # | 场景 | 涉及 L2 |
|---|---|---|
| I1 | 正常一轮 tick 端到端（流 A） | L2-01 → L2-02 → L2-05 |
| I2 | hard_halt 链路端到端（流 I） | L2-06 → L2-01 → L2-02 (中断) → L2-05 |
| I3 | panic 链路端到端（流 G） | L1-10 → L2-01 → L2-05 → L2-03 (PAUSED) |
| I4 | bootstrap 链路端到端（流 H） | L1-09 → L2-01 (bootstrap) → L2-02 |
| I5 | 异步结果回收链路端到端（流 F） | L1-05 → L1-09 → L2-01 → L2-02 消费 |

#### 性能阈值

- trigger 接入 → 入 queue ≤ 10ms (P99)
- hard_halt 响应 ≤ 100ms (P99)
- panic 响应 ≤ 100ms (P99)
- 调度吞吐 ≥ 100 tick/s
- watchdog 扫描开销 ≤ 1% CPU

---

### 8.10 L3 · Tick 调度器实现设计（产品视角）

> L3 粒度：算法 + 数据结构 + 状态机 + 产品逻辑流程图。**不含技术栈选型**，供下游技术方案阶段输入。

#### 8.10.1 内部状态机

```
       [INIT]
         │ on_start (L1-01 初始化)
         ▼
  ┌──→ [IDLE] ──────────────────────────┐
  │      │                              │
  │      │ trigger 到达                  │
  │      │ (入 queue 经 debounce+仲裁)    │
  │      ▼                              │
  │    [RUNNING] ─ tick_timeout (>30s) →[DEGRADED] ← WARN 只记录
  │      │                              │     │
  │      │ tick 完成                    │     │ 下一 tick 正常
  │      └──────────────────────────────┘     │ 回 RUNNING
  │                                            │
  │      IC-L2-08 hard_halt 到达               │
  │      (可从 IDLE / RUNNING / DEGRADED 进入)  │
  │                                            │
  │          ▼                                 │
  │      [HALTED] ───── user_intervene(authorize) ──→ [IDLE]
  │                                            │
  │      user_panic 到达                       │
  │      (从 IDLE / RUNNING / DEGRADED 进入)   │
  │          ▼                                 │
  └──── [PAUSED] ──── user_intervene(resume) ──→ [IDLE]
```

**状态不变量**：
- 同一时刻只有一个状态
- HALTED / PAUSED 必须用户显式解除
- DEGRADED 是非阻塞告警态，下一 tick 正常可自愈

#### 8.10.2 4 触发源 + 2 响应通道 优先级仲裁算法

**默认优先级表**：

| 优先级 | 类别 | 说明 |
|---|---|---|
| 100 | bootstrap | 跨 session 恢复 · 一次性 · 最高 |
| 90 | user_panic | 用户紧急介入 · 立即中断 |
| 85 | supervisor_block | 硬红线拦截 · 立即暂停 |
| 60 | async_result（event_driven 特殊） | 子 Agent / 长 skill 回传 · 高于普通事件 |
| 50 | event_driven | 事件总线新事件 · 标准优先级 |
| 40 | hook_driven | SessionStart / state_transition hook |
| 30 | proactive | 主动唤醒（上一 tick 完成）· 保持 loop 活跃 |
| 10 | periodic_tick | 30s 周期 · 最低 · 用于自省 |

**仲裁伪码**：

```
function arbitrate(pending_queue, current):
    if current is not None and current.state == RUNNING:
        # 检查是否要抢占
        if incoming.priority >= 85:  # BLOCK / panic 可抢占
            interrupt(current)
            return incoming
        else:
            return current  # 不抢占
    else:
        # 从 pending 取优先级最高的
        if pending.empty():
            return None
        # 同优先级按 FIFO
        next = pending.pop_highest_priority_fifo()
        return next
```

#### 8.10.3 去抖动算法

**规则**：

```
function debounce(new_trigger):
    if new_trigger.trigger_source in [bootstrap, user_panic, hard_halt]:
        return new_trigger  # 永不去抖

    bucket = debounce_buckets[new_trigger.trigger_source]
    now = time.now()
    if bucket.last_trigger is None or now > bucket.window_end_ts:
        # 新窗口
        bucket.last_trigger = new_trigger
        bucket.window_end_ts = now + DEBOUNCE_WINDOW  # 500ms
        schedule_after(DEBOUNCE_WINDOW, flush_bucket, bucket)
        return None  # 不立即派发，等窗口结束
    else:
        # 窗口内 → 合并，保留最后一条
        new_trigger.debounced = true
        bucket.last_trigger = new_trigger  # 覆盖，保留最新
        return None

function flush_bucket(bucket):
    if bucket.last_trigger:
        emit(bucket.last_trigger)  # 派发合并后的最终 trigger
        bucket.last_trigger = None
        bucket.window_end_ts = None
```

#### 8.10.4 Watchdog 健康心跳算法

```
function watchdog_scan():  # 每 5s 调一次
    now = time.now()

    # 检测 1: tick 超时
    if current is not None and state == RUNNING:
        if now - current.started_at > TICK_TIMEOUT:  # 30s
            emit_audit(action=tick_timeout, linked_tick=current.tick_id)
            transition_to(DEGRADED)
            # 注意: 不中断 tick, 继续等 (L2-02 自己负责结束)

    # 检测 2: 空转检测
    recent_ticks = get_last_n_tick_records(5)
    if all(t.result.decision_type == 'no_op' for t in recent_ticks):
        emit_audit(action=idle_spin_detected, reason='5 ticks returned no_op')

    # 检测 3: 死循环升级（来自 L2-04 通知）
    if pending_death_loop_escalation:
        # L2-04 自己会通过 IC-L2-10 (L2-06) 升级
        # 本 L2-01 仅转发其扫到的持续高频 chain_step_failed 审计
        forward_to_supervisor_pipeline()
```

#### 8.10.5 核心数据结构 schema

**TickTrigger**：

```yaml
tick_trigger:
  id: trig_{uuid}
  trigger_source: enum
    # bootstrap | user_panic | supervisor_block | async_result |
    # event_driven | hook_driven | proactive | periodic_tick
  priority: int               # 0-100
  event_ref: event_id | null   # 若 event_driven, 关联事件总线事件 ID
  ts: iso8601
  payload: object              # trigger-specific context
  debounced: bool              # 是否被合并
  bootstrap_context: object | null  # 仅 bootstrap 时有
    resumed_from_checkpoint: ts
    last_state: str
```

**TickRecord**：

```yaml
tick_record:
  tick_id: tick_{uuid}
  trigger: TickTrigger
  scheduled_at: iso              # 入队时间
  started_at: iso                # 开始 RUNNING
  dispatched_at: iso             # IC-L2-01 on_tick 调用时间
  completed_at: iso
  duration_ms: int
  decision_id: dec_XXX | null
  result:
    status: success | error | interrupted
    decision_type: str | null
    error_message: str | null
  watchdog_events: [event_id, ...]
  interrupted_by: hard_halt | panic | null
```

**ScheduleQueue**：

```yaml
schedule_queue:
  # 待派发队列（priority desc, same-priority FIFO）
  pending:
    - tick_trigger: {...}
      inserted_at: iso
    - ...
  max_depth: 1000
  current: tick_trigger | null    # 当前在派发的

  debounce_buckets:
    event_driven:
      last_trigger: TickTrigger | null
      window_end_ts: iso | null
    hook_driven: {...}
    proactive: {...}
    periodic_tick: {...}

  stats:
    total_scheduled: int
    total_dispatched: int
    total_debounced_merged: int
    total_dropped_queue_full: int
```

#### 8.10.6 核心产品逻辑流程图（4 张 ASCII）

**图 1 · 触发源接入 + 去抖 + 仲裁 + 派发**

```
[外部触发到达 L2-01]
     ↓
判断 trigger_source 类型
     ↓
 ┌───┴─────────────────────────────────────────┐
 ▼                                             ▼
[bootstrap / panic / hard_halt]        [其他 4 类触发源]
 ▼                                             ▼
priority 设为对应最高值                     进入 debounce_buckets
 ▼                                             │
(跳过去抖)                                      ▼
 ▼                                      已在 500ms 窗口内?
写 TickTrigger                                  │
 ▼                                      ┌───────┴───────┐
直接入 schedule_queue 队首              YES             NO
 ▼                                       │              │
(抢占 RUNNING tick if 需要)               ▼              ▼
                                       合并 (保留最后)   开新窗口
                                        记 debounced     设 500ms 定时器
                                        = true              ↓
                                         ↓              等窗口到期
                                      继续等窗口到期     ↓
                                         ↓              flush_bucket
                                         ↓              ↓
                                    ─────┴──────────────┘
                                         ↓
                                    派发合并后的 TickTrigger
                                         ↓
                                    按 priority 插入 queue
                                         ↓
 └─────────────────────────────────────┐
                                       ▼
                              arbitrate(queue, current)
                                       ↓
                                 current = 选出的 TickTrigger
                                       ↓
                                state = RUNNING
                                       ↓
                             启动 tick watchdog 计时
                                       ↓
                             IC-L2-01 on_tick() → L2-02
                                       ↓
                             (阻塞等 L2-02 返回)
                                       ↓
                             记 TickRecord
                                       ↓
                             IC-L2-05 record_audit(tick_completed)
                                       ↓
                                current = null
                                       ↓
                                state = IDLE
                                       ↓
                                循环 (continue arbitrate)
```

**图 2 · Watchdog 健康心跳**

```
[每 5s 定时触发]
     ↓
检测 1: 当前 tick 超时?
     ↓
if current != null && state == RUNNING:
    if now - current.started_at > 30s:
        ↓
    IC-L2-05 record_audit(tick_timeout)
        ↓
    state = DEGRADED
        ↓
    (不中断, 等 L2-02 自己结束)
     ↓
检测 2: 空转检测
     ↓
recent = 最近 5 条 TickRecord
if all(r.result.decision_type == 'no_op'):
    ↓
IC-L2-05 record_audit(idle_spin_detected)
     ↓
检测 3: 转发 L2-04 的死循环信号
     ↓
(L2-04 自己通过 L2-06 → IC-L2-08 升级;
 本 L2-01 仅看其审计事件做被动告警)
```

**图 3 · 异步结果回收 + Bootstrap**

```
异步结果回收:
────────────
(外部 L1-05 子 Agent 完成)
     ↓
发 subagent_result 事件 → L1-09 事件总线
     ↓
L2-01 event_driven 订阅到
     ↓
识别 event type 为 'subagent_result'
     ↓
priority 设为 60 (async_result 级)
     ↓
入 debounce_bucket (event_driven)
     ↓
... 正常调度流程 ... → L2-02 on_tick
     ↓
L2-02 决策 = "消费异步结果, 继续业务"

Bootstrap:
──────────
(Claude Code 重启)
     ↓
L1-09 扫 task-boards → 重建 task-board
     ↓
L1-09 发 system_resumed 事件
     ↓
L2-01 识别 event type = 'system_resumed'
     ↓
trigger_source = bootstrap, priority = 100
     ↓
bootstrap_context = {
    resumed_from_checkpoint: <ts>,
    last_state: <state>,
    ...
}
     ↓
(跳过去抖 + 抢占)
     ↓
IC-L2-01 on_tick(bootstrap=true) → L2-02
     ↓
L2-02 特殊决策: 分析 state_history 末尾
     ├── WP 执行中 → 继续
     ├── Stage Gate 等待 → 重推 UI
     └── PAUSED → 等用户
```

**图 4 · 硬暂停 (hard_halt) + Panic + Resume**

```
Hard_halt (BLOCK 级):
─────────────────────
IC-L2-08 propagate_hard_halt 到达
     ↓
记 IC-L2-05 record_audit(action=hard_halt_received)
     ↓
state → HALTED (无论当前是什么状态)
     ↓
if current != null && state was RUNNING:
    发 async cancel 信号给 L2-02
     ↓
current.interrupted_by = 'hard_halt'
     ↓
写 TickRecord (status=interrupted)
     ↓
pending queue 保留但不派发
     ↓
(等待 user IC-17 authorize)

Panic:
──────
user_panic 事件 → event_driven 订阅到
     ↓
识别 → priority = 90 (最高非 bootstrap)
     ↓
if current != null:
    发 async cancel 给 L2-02
     ↓
current.interrupted_by = 'panic'
     ↓
写 TickRecord (status=interrupted)
     ↓
IC-L2-05 record_audit(action=panic_intercepted)
     ↓
IC-L2-02 request_state_transition(to=PAUSED)
     ↓
state = PAUSED

Resume (from HALTED or PAUSED):
───────────────────────────────
L1-10 IC-17 user_intervene(type=resume) → L1-01 → L2-01
     ↓
state → IDLE
     ↓
(处理 pending queue, 继续调度)
```

#### 8.10.7 配置参数清单

供运维/部署调整（默认值属 L1-01 标准，可覆盖但要审计）：

| 参数 | 默认 | 范围 | 意义 |
|---|---|---|---|
| `TICK_TIMEOUT_MS` | 30000 | 10000-60000 | tick 超时阈值 |
| `WATCHDOG_INTERVAL_MS` | 5000 | 1000-10000 | watchdog 扫描间隔 |
| `DEBOUNCE_WINDOW_MS` | 500 | 100-2000 | 去抖窗口 |
| `QUEUE_MAX_DEPTH` | 1000 | 100-10000 | 队列上限 |
| `IDLE_SPIN_THRESHOLD` | 5 | 3-20 | 连续空转次数告警 |
| `PERIODIC_TICK_INTERVAL_SEC` | 30 | 10-300 | 周期 tick 间隔 |
| `PRIORITY_OVERRIDE_TABLE` | 默认表 | 受限 | 优先级可配置（不可删键） |

## 9. L2-02 · 决策引擎 详细定义

### 9.1 职责 + 锚定

**一句话职责**：每次 tick 做"这一步做什么"的决策——组装上下文 → 注入 KB → 5 纪律拷问 → 决策树分派 → 选出决策动作（调 skill / 工具 / 子 Agent / KB 读写 / 请示用户 / 状态转换 / 启动任务链）→ 返回给 L2-01。**整个 HarnessFlow 的"脑"**。

**上游锚定**：
- Goal §1 一句话目标："以主 Skill Agent loop 为执行核心"
- Goal §4.3 methodology-paced autonomy
- scope §5.1.1 职责：持续 tick → 决策 → 执行 → 留痕
- scope §5.1.5 禁止：跳过 5 纪律 / 未经 KB 注入决策 / 静默失败
- scope §5.1.6 必须：每 tick 留决策理由 / 书面回应 WARN
- BF-L3-01 决策心跳 tick 流
- BF-L3-14 决策选择流
- BF-L3-11 5 纪律自拷问流
- BF-L3-10 方法论驱动决策流

**下游服务**：L2-01（返回决策结果）· L2-03（发起 state 转换）· L2-04（启动任务链）· L2-05（审计留痕）· L1-05/06/08/10（对外调度）

---

### 9.2 输入 / 输出

#### 输入（5 类）

| 类别 | 接收方式 | 内容 |
|---|---|---|
| **tick 调用** | IC-L2-01 on_tick（from L2-01） | `{trigger_source, event_ref, priority, ts, bootstrap?}` |
| **任务链回调** | IC-L2-04 step_completed（from L2-04） | `{chain_id, step_id, outcome, result_ref}` |
| **Supervisor 建议** | IC-L2-10 dispatch_suggestion（from L2-06） | `{level: SUGG/WARN, content, priority, ts}` |
| **外部执行结果** | 通过 L1-09 事件总线新事件再进 L2-01 新 tick | 异步回传（子 Agent / 长 skill 完成） |
| **用户输入** | 通过 L1-10 → L1-01 → L2-01 → 本 L2 | 澄清答案 / 授权 / 变更等 |

#### 读取源（本 L2 主动读）

- task-board 当前 snapshot（调 L1-09 读接口）
- 近 N 条事件（调 L1-09）
- KB 条目（调 L1-06 IC-06 kb_read）
- 当前 WP 定义 + DoD 表达式（读 WBS）
- skill 注册表 + 能力抽象层映射

#### 输出（12 类决策动作 + 3 类副产出）

**决策动作**（返回给 L2-01 完成 tick，或触发下游）：

| 决策类型 | 执行通道 | 目标 L2/L1 |
|---|---|---|
| `invoke_skill` | 外部 IC-04 | L1-05 |
| `use_tool` | 外部 IC（工具柜） | L1-05 |
| `delegate_subagent` | 外部 IC-05 | L1-05 |
| `kb_read` | 外部 IC-06 | L1-06 |
| `kb_write` | 外部 IC-07 | L1-06 |
| `process_content` | 外部 IC-11 | L1-08 |
| `request_user` | 外部 IC-17 反向 | L1-10 |
| `state_transition` | IC-L2-02 | L2-03 |
| `start_chain` | IC-L2-03 | L2-04 |
| `warn_response` | IC-L2-09 | L2-05 |
| `fill_discipline_gap` | 内部循环（补 5 纪律缺项）| 本 L2 下次 tick |
| `no_op` | 无动作（返回"无可做"）| - |

**副产出**：

| 产出 | 去向 | schema |
|---|---|---|
| `decision_record` | L2-05（IC-L2-05） | §9.10.7 schema |
| `context_snapshot` | L1-09 落盘供审计反查 | §9.10.1 schema |
| `warn_response` | L2-05（IC-L2-09） | §5.4 audit_entry 变种 |

---

### 9.3 边界

#### In-scope

1. 上下文组装（task-board snapshot + 近 N 事件 + supervisor 队列 + KB + 用户输入 + 当前 WP/DoD）
2. KB 注入（按当前阶段 PM-06 策略 + 5 纪律关注点匹配）
3. 5 纪律拷问（规划/质量/拆解/检验/交付 逐条 Y/N/Skip + note）
4. 决策树分派（多层 if-elif 路由：硬暂停→WARN→阶段 Gate→链回调→异步→用户→state 主决策树→兜底）
5. 决策选择（候选多个时按能力抽象层 + 优先级选首选）
6. Supervisor 建议处理（SUGG 参考 / WARN 必回应 / BLOCK 通过 L2-01 中断）
7. decision_record 打包
8. 决策产出传递（通过 IC-L2-XX 调 L2-03/04/05 或外部 IC 调 L1-05/06/08/10）

#### Out-of-scope

- ❌ **不做 tick 调度** → L2-01
- ❌ **不做 state 转换执行** → L2-03（本 L2 只发起请求）
- ❌ **不做任务链推进** → L2-04（本 L2 只启动）
- ❌ **不写事件总线** → L2-05
- ❌ **不做 KB 物理存储** → L1-06
- ❌ **不自己跑 skill / 代码** → L1-05
- ❌ **不做 supervisor 接收分派** → L2-06
- ❌ **不做外部内容读写** → L1-08

#### 边界规则

- **本 L2 只做"决策产出"，不做"决策执行"**
- 所有决策动作必须通过 IC-XX（跨 L1）或 IC-L2-XX（跨 L2）发出，**不可直接调用外部模块**
- 一次 tick = 一个决策动作（不多决策合并）

---

### 9.4 约束

#### 业务模式引用

- **PM-11 5 纪律贯穿拷问**：每关键决策前必过 5 问
- **PM-06 KB 三层 + 阶段注入**：按阶段注入策略表（§9.10.2）
- **PM-09 能力抽象层调度**：不绑 skill 名，走映射表
- **PM-02 主-副 Agent 协作**：采纳 / 驳回 supervisor 建议必留痕

#### 硬约束

1. **每决策必有 reason**（自然语言，≥ 20 字，可审计 · scope §5.1.6）
2. **5 纪律拷问每 tick 必做**（任一 N → 先补齐该纪律）
3. **WARN 必在 1 tick 内回应**（采纳或驳回 + 理由）
4. **决策总耗时 ≤ 20s**（给 watchdog 30s 预留 10s buffer）
5. **一 tick 一决策**（禁止合并多个动作）
6. **决策前必查 allowed_next**（如决策 = state_transition）
7. **决策 context 必包含 state**（防 state 不一致决策）
8. **能力抽象层不可绕过**（禁止硬编码 skill 名）

#### 性能约束

- 决策逻辑纯计算 ≤ 5s（不含外部 IO）
- KB 注入查询 ≤ 500ms
- 5 纪律拷问 ≤ 200ms
- 上下文组装 ≤ 1s

---

### 9.5 🚫 禁止行为（明确清单）

- 🚫 **禁止跳过 5 纪律拷问**（scope §5.1.5，硬违反）
- 🚫 **禁止决策无 reason**（scope §5.1.6 "留决策理由"）
- 🚫 **禁止未注入 KB 直接决策**（除非 KB 层本身 unavailable 且已告警）
- 🚫 **禁止同一 tick 合并多个决策**（一 tick = 一决策）
- 🚫 **禁止直接修改 task-board / 事件总线**（走 L2-05）
- 🚫 **禁止硬编码 skill 名**（必走能力抽象层）
- 🚫 **禁止 WARN 级建议积压 > 1 tick 不回应**
- 🚫 **禁止决策逻辑耗时 > 20s**
- 🚫 **禁止在硬暂停中继续决策**（收到 IC-L2-08 传递的 cancel 信号必 abort）
- 🚫 **禁止伪造 5 纪律答案**（Skip 必有 reason，不可无脑全 Y）

---

### 9.6 ✅ 必须职责（明确清单）

- ✅ **必须**每 tick 组装完整 context_snapshot（6 要素：task-board / 近 N 事件 / supervisor 队列 / 用户输入 / 当前 WP / 当前 DoD）
- ✅ **必须**按 PM-06 阶段注入策略注入 KB（除非 KB 层失败）
- ✅ **必须** 5 纪律拷问（每项填 Y/N/Skip + note；Skip 必有 reason）
- ✅ **必须**对 supervisor WARN 级建议在下 1 tick 内书面回应（IC-L2-09）
- ✅ **必须**从能力抽象层获取 skill 列表（走 L1-05 skill 注册表）
- ✅ **必须**为每决策生成 decision_record（含 context_snapshot_ref + 5 纪律 + reason + decision_type + decision_params）
- ✅ **必须**决策为 state_transition 时先查 allowed_next（调 L2-03 验证）
- ✅ **必须**决策耗时超阈值时中断自己（防 L2-01 watchdog 告警）
- ✅ **必须**收到 async cancel 信号立即 abort 并留痕

---

### 9.7 🔧 可选功能职责（可做但不硬性要求）

- 🔧 **决策置信度评分**：为每决策打 0-1 分（confidence_score · 辅助 UI 展示 + 调试）
- 🔧 **多决策候选并列**：返回 top-3 候选（alternative_decisions · 审计/调试用 · 默认关）
- 🔧 **决策历史学习**：从历史 decision_records 中学习同场景倾向（实验性 · 默认关）
- 🔧 **决策回溯推理**：支持"如果选另一个决策会怎样"假设分析（调试用）
- 🔧 **决策缓存**：同参数决策可缓存（需精细失效规则；默认关）
- 🔧 **决策树可视化输出**：每 tick 产出决策树走过的路径供 L1-10 UI 展示

---

### 9.8 与其他 L2 交互

**作为调用方**：

| IC | 被调方 | 触发条件 | 调用字段（关键） |
|---|---|---|---|
| **IC-L2-02** | L2-03 | 决策 = state_transition | `{from, to, reason, evidence_refs, trigger_tick}` |
| **IC-L2-03** | L2-04 | 决策 = start_chain | `{chain_def, chain_goal, context}` |
| **IC-L2-05** | L2-05 | 每次决策完成 | `{actor: L2-02, action: decision_made, reason, evidence: [decision_id], linked_tick}` |
| **IC-L2-09** | L2-05 | 回应 supervisor WARN | `{supervisor_warn_id, response: accept/reject, reason, applied_action?}` |

**作为被调方**：

| IC | 调用方 | 触发 | 接收字段 |
|---|---|---|---|
| **IC-L2-01** | L2-01 | 每次 tick 派发 | `{trigger_source, event_ref, priority, ts, bootstrap?}` |
| **IC-L2-04** | L2-04 | 任务链步完成 | `{chain_id, step_id, outcome, result_ref, next_hint?}` |
| **IC-L2-10** | L2-06 | SUGG/WARN 级建议分派 | `{level, content, priority, ts}` |
| **async_cancel 信号** | L2-01（转发 L2-06 的 BLOCK） | 硬暂停 | 中断当前决策 |

**外部 IC**（跨 L1，经过本 L2 发起或接收）：

| IC | 方向 | 说明 |
|---|---|---|
| IC-04 invoke_skill | 发起 → L1-05 | 决策 = invoke_skill |
| IC-05 delegate_subagent | 发起 → L1-05 | 决策 = delegate_subagent |
| IC-06 kb_read | 发起 → L1-06 | KB 注入阶段 |
| IC-07 kb_write_session | 发起 → L1-06 | 决策 = kb_write |
| IC-11 process_content | 发起 → L1-08 | 决策 = process_content |
| IC-17 user_intervene | 接收 ← L1-10 | 用户反馈澄清/授权 |

---

### 9.9 🎯 交付验证大纲（TDD 直接消费）

#### 成功信号

- 每 TickRecord 有对应 `decision_record`（非 null）
- `decision_record.five_disciplines` 5 项都有答案
- `decision_record.reason` 长度 ≥ 20 字
- supervisor WARN 在 1 tick 内必有 warn_response 审计
- 决策耗时 P99 ≤ 5s（纯逻辑，不含外部 IO）

#### 正向测试用例（对应 ✅ 必须职责）

| # | 场景 | 验证点 |
|---|---|---|
| P1 | 收到 on_tick 调用 | 期望产出完整 decision_record |
| P2 | 进入 CLARIFY 阶段的 tick | 期望 KB 注入含 trap + pattern kind |
| P3 | 进入 VERIFY 阶段的 tick | 期望 KB 注入含 trap kind（假完成陷阱） |
| P4 | 5 纪律拷问 | 期望每项填 Y/N/Skip + note，且 Skip 必有 reason |
| P5 | 决策 = state_transition | 期望先发 IC-L2-02 验证 allowed_next 合法 |
| P6 | supervisor WARN 到达 | 期望下一 tick 必发 IC-L2-09 record_warn_response |
| P7 | 能力抽象层匹配 `writing-plans` | 期望返回注册表中首选 skill + version |
| P8 | 任务链 step_completed 回调 | 期望决策基于 outcome 继续/中止/调整 |
| P9 | 决策产出 decision_record | 期望含 context_snapshot_ref + reason ≥ 20 字 |

#### 负向测试用例（对应 🚫 禁止行为）

| # | 场景 | 验证点 |
|---|---|---|
| N1 | 强制跳过 5 纪律 | 期望拒绝 + 审计违规 |
| N2 | decision_record.reason 为空 | 期望 assert 失败 |
| N3 | 同 tick 返回多决策 | 期望拒绝 + 告警 |
| N4 | 决策逻辑耗时 25s | 期望中断自己 + 告警 `decision_timeout` |
| N5 | 硬编码 skill 名 `tdd` 不走抽象层 | 期望拒绝 + 告警 |
| N6 | WARN 积压 > 1 tick | 期望告警 `warn_response_overdue` |
| N7 | Skip 5 纪律无 reason | 期望拒绝决策 |
| N8 | 收到 async cancel 继续决策 | 期望立即 abort + 留痕 |
| N9 | state_transition 未查 allowed_next | 期望拒绝 |

#### 集成用例（跨 L2）

| # | 场景 | 涉及 L2 |
|---|---|---|
| I1 | 端到端"调 skill"决策链 | L2-02 → L1-05 → 结果回传 → 新 tick 消费 |
| I2 | state 转换决策链 | L2-02 → L2-03 → L2-05 审计 |
| I3 | 启动任务链决策 | L2-02 → L2-04 → step_completed → 回 L2-02 决策 |
| I4 | WARN 回应链 | L2-06 → L2-02 → L2-05 |
| I5 | 5 纪律未过补齐 | L2-02 连续 2 tick 补齐"规划"纪律 → 第 3 tick 主决策 |
| I6 | 硬暂停中断决策 | L2-01 async_cancel → L2-02 abort → 审计 |
| I7 | Bootstrap tick 决策 | L2-02 从 state_history 末尾分析 → 决策恢复路径 |

#### 性能阈值

- 决策逻辑 ≤ 5s P99
- KB 注入 ≤ 500ms P99
- 5 纪律拷问 ≤ 200ms P99
- 上下文组装 ≤ 1s P99
- decision_record 打包 ≤ 50ms P99

---

### 9.10 L3 · 决策引擎实现设计（产品视角）

#### 9.10.1 上下文组装器（Context Assembler）

**职责**：为每次决策准备完整的决策上下文。

**组装步骤**（按顺序）：

```
function assemble_context(tick_trigger):
    ctx = ContextSnapshot(
        snapshot_id = generate_id(),
        tick_id = tick_trigger.id,
        ts = now(),
    )

    # 1. task-board 快照
    ctx.task_board = L1-09.read_task_board_snapshot()
    # 含: current_state, current_wp, stage_progress, goal_anchor

    # 2. 近 N 条事件（默认 20）
    ctx.recent_events = L1-09.scan_events(
        from_ts = now() - 24h,
        limit = CONTEXT_RECENT_EVENTS_N
    )

    # 3. supervisor 建议队列（持久于 L2-06）
    ctx.supervisor_suggestions_pending = L2-06.get_pending_suggestions()
    # 已包含 SUGG 待参考 + WARN 待回应

    # 4. 用户输入待消费事件
    ctx.user_input_pending = find_unconsumed_user_events(ctx.recent_events)

    # 5. 当前 WP 定义（如在 S4 阶段）
    if ctx.task_board.current_wp:
        ctx.current_wp_def = L1-03.get_wp_definition(ctx.task_board.current_wp)

    # 6. 当前 DoD 表达式（如在 S5 阶段）
    if ctx.task_board.current_state in [S5]:
        ctx.current_dod = L1-04.get_active_dod_expressions()

    ctx.metadata.duration_ms = now() - ctx.ts
    return ctx
```

**schema** 见 §5.1（`context_snapshot` 仿 `event`）：

```yaml
context_snapshot:
  snapshot_id: ctx_{uuid}
  tick_id: tick_XXX
  ts: iso
  task_board:
    current_state: str
    current_wp: str | null
    stage_progress: float [0-1]
    goal_anchor:
      hash: sha256
      text: str
  recent_events: [event_ref, ...]
  supervisor_suggestions_pending: [suggestion, ...]
  user_input_pending: event_ref | null
  current_wp_def: object | null
  current_dod: object | null
  metadata:
    assembled_at: iso
    duration_ms: int
```

#### 9.10.2 KB 注入策略表 + 算法

**注入策略表**（PM-06，scope §6 注入策略）：

| 阶段 | 注入 kind | top_k | 备注 |
|---|---|---|---|
| S1 CLARIFY | trap + pattern + project_context | 5 each | 避免已知澄清坑 |
| S2 PLAN | recipe + tool_combo | 5 each | 复用有效组合 |
| S3 TDD | anti_pattern | 10 | 测试反模式 |
| S4 IMPL | pattern + anti_pattern | 5 each | 代码模式 + 反模式 |
| S5 VERIFY | trap（假完成陷阱为主）| 10 | 防假完成 |
| S6 MONITOR | - | 0 | 只产出不注入 |
| S7 CLOSE | - | 0 | 反向收集新 KB |

**注入算法**：

```
function inject_kb(current_state, ctx):
    policy = KB_INJECTION_POLICY[current_state]
    if not policy.kinds:
        return []  # 不注入

    kb_entries = []
    for kind in policy.kinds:
        entries = L1-06.IC-06 kb_read(
            kind = kind,
            scope = [session, project, global],  # 按优先级
            context_filter = {
                route: ctx.task_board.route_id,
                task_type: ctx.task_board.task_type,
                stack: detect_stack(ctx),  # 从当前 artifact 推断
            },
            top_k = policy.top_k
        )
        kb_entries.extend(entries)

    # 按 observed_count 降序 + 去重
    return deduplicate_and_sort(kb_entries, by='observed_count', desc=True)
```

**注入失败容错**：

- KB 层失败（L1-06 不可用）→ 决策继续但 warn 告警 `kb_injection_failed`
- 超时（> 500ms）→ 截断返回已查到的部分
- 单条目 schema 校验失败 → 跳过 + 告警

#### 9.10.3 5 纪律拷问算法

**5 问模板**：

| 纪律 | 问题 | 默认判定规则 |
|---|---|---|
| **规划** | 当前阶段有清晰 plan + DoD 吗？ | 检查 ctx.current_dod 非空；检查该阶段产出物齐全 |
| **质量** | 当前产出有 TDD / 审查 / 证据链？ | 检查 S3 蓝图存在；检查近 N 事件含 verifier_report 或待验证 |
| **拆解** | 当前 WP 已拆到可执行粒度（≤ 5 天）？ | 检查 ctx.current_wp_def.estimated_hours ≤ 40 |
| **检验** | 有独立 verifier + 三段证据链吗？ | 检查 L1-04 配置 + verifier subagent 可用 |
| **交付** | 本阶段产出可消费 / 可验收 / 可审计？ | 检查产出物是否 in delivery_bundle + 有 audit trail |

**算法**：

```
function five_disciplines_check(ctx):
    answers = {}
    for discipline in [规划, 质量, 拆解, 检验, 交付]:
        check_fn = DISCIPLINE_CHECKERS[discipline]
        result = check_fn(ctx)  # returns Y | N | Skip
        note = generate_note(discipline, ctx, result)
        skip_reason = None if result != Skip else generate_skip_reason(...)
        answers[discipline] = {
            answer: result,
            note: note,
            skip_reason: skip_reason,
        }

    summary = {
        all_passed: all(a.answer == Y for a in answers.values()),
        missing: [d for d, a in answers.items() if a.answer == N],
        skipped: [d for d, a in answers.items() if a.answer == Skip],
    }

    return {answers, summary}
```

**不过的处理**（任一 N）：

- 生成"补齐该纪律"子决策（`fill_discipline_gap`）
- 进入下一 tick 时优先处理
- 连续 3 tick 无法补齐 → 告警 + 升级

#### 9.10.4 主决策树（分派算法）

**多层 if-elif 路由**（按优先级从高到低）：

```
function decide(ctx):
    # Priority 1: 5 纪律拷问（硬性先过）
    disciplines = five_disciplines_check(ctx)
    if not disciplines.summary.all_passed:
        missing = disciplines.summary.missing[0]  # 取首个缺的
        return Decision(
            decision_type = 'fill_discipline_gap',
            params = {discipline: missing, suggested_action: ...},
            reason = f"纪律'{missing}' 未过，先补齐再决策"
        )

    # Priority 2: 硬暂停中断（虽然 L2-01 应该已经 abort 了，防御性检查）
    if is_hard_halt_pending():
        return Decision(decision_type='abort', reason='hard halt pending')

    # Priority 3: WARN 待回应
    warn = find_pending_warn(ctx.supervisor_suggestions_pending)
    if warn:
        return decide_warn_response(warn, ctx)

    # Priority 4: 阶段 Gate（state 转换条件满足）
    if should_advance_stage(ctx):
        return decide_state_transition(ctx)

    # Priority 5: 任务链回调待消费
    chain_callback = find_pending_chain_callback(ctx.recent_events)
    if chain_callback:
        return decide_chain_next_step(chain_callback, ctx)

    # Priority 6: 异步结果待消费（子 Agent / 长 skill 回传）
    async_result = find_pending_async_result(ctx.recent_events)
    if async_result:
        return decide_consume_async(async_result, ctx)

    # Priority 7: 用户输入待处理
    if ctx.user_input_pending:
        return decide_process_user(ctx.user_input_pending, ctx)

    # Priority 8: SUGG 级建议（可选参考）
    suggs = find_pending_suggs(ctx.supervisor_suggestions_pending)
    if suggs and should_apply_sugg(suggs, ctx):
        return decide_apply_sugg(suggs[0], ctx)

    # Priority 9: 按当前 state 主决策树
    state = ctx.task_board.current_state
    if state in [CLARIFY, PLAN]:
        return decide_planning_action(ctx)
    elif state == TDD_PLAN:
        return decide_tdd_planning_action(ctx)
    elif state == IMPL:
        return decide_impl_action(ctx)
    elif state == VERIFY:
        return decide_verify_action(ctx)
    elif state in [COMMIT, RETRO_CLOSE]:
        return decide_closing_action(ctx)

    # 兜底
    return Decision(
        decision_type = 'no_op',
        reason = '无可做，空转一次，等下一 tick'
    )
```

**各阶段子决策函数**（举 2 例，其他类似）：

```
function decide_planning_action(ctx):
    # CLARIFY / PLAN 阶段典型决策
    missing_artifacts = check_missing_planning_artifacts(ctx)
    if '项目章程' in missing_artifacts:
        return Decision(
            decision_type = 'invoke_skill',
            params = {
                capability: 'project-charter-generation',
                input: ctx.task_board.goal_anchor,
            },
            reason = "S1 阶段缺项目章程，调 prp-prd skill 生成"
        )
    if '4 件套' in missing_artifacts:
        return Decision(
            decision_type = 'start_chain',
            params = {
                chain_def: [
                    {step: 'requirements'},
                    {step: 'goals'},
                    {step: 'acceptance_criteria'},
                    {step: 'quality_standards'},
                ],
            },
            reason = "S2 阶段 4 件套需串行生成，启动任务链"
        )
    ...

function decide_verify_action(ctx):
    # VERIFY 阶段
    if not verifier_report_exists(ctx):
        return Decision(
            decision_type = 'delegate_subagent',
            params = {
                subagent_name: 'harnessFlow:verifier',
                context_copy: ctx.current_wp_def,
                goal: f"对 WP-{ctx.task_board.current_wp} 跑三段证据链验证",
                tools_whitelist: [Read, Grep, Glob, Bash],
            },
            reason = "S5 阶段需独立 verifier 验证"
        )
    # 有 report 但 verdict 未出 → 等
    if not verdict_decided(ctx):
        return Decision(decision_type='no_op', reason='等 verifier 结果')
    # verdict 已出 → 交 L2-07（其实是 L2-06 级联）路由回退 → 本 L2 不直接管
    ...
```

#### 9.10.5 决策选择（在多候选中选首选）

**能力抽象层匹配**：

```
function match_capability(capability_name, ctx) -> Skill | None:
    # capability_name 例: 'writing-plans', 'test-driven-development'
    registry = L1-05.get_skill_registry()  # 缓存 60s

    candidates = []
    for skill in registry:
        if skill.provides_capability(capability_name):
            candidates.append(skill)

    if not candidates:
        return None  # fallback 到内建或告警

    # 排序：可用性 > 历史成功率 > 成本低
    sorted_candidates = sorted(candidates, key=lambda s: (
        -s.availability,              # 可用 desc
        -s.historical_success_rate,   # 成功率 desc
        s.cost_estimate,              # 成本 asc
    ))
    return sorted_candidates[0]
```

**Skill 不可用时 fallback**：

```
function select_skill_with_fallback(capability, ctx):
    skill = match_capability(capability, ctx)
    if skill and skill.available:
        return skill

    # Fallback 链（来自 L1-05 能力抽象层配置）
    fallback_list = get_fallback_skills(capability)
    for fb_skill in fallback_list:
        if fb_skill.available:
            log_fallback_used(capability, primary=None, fallback=fb_skill)
            return fb_skill

    # 全失败 → 走内建逻辑（如果有）
    if has_builtin_handler(capability):
        log_fallback_to_builtin(capability)
        return 'builtin'

    # 全无 → 硬暂停
    return None  # 上层调用者决定是否 abort
```

#### 9.10.6 Supervisor 建议处理策略

**SUGG 级**（下轮参考 · 非强制）：

```
function should_apply_sugg(sugg, ctx):
    # 策略示例
    if sugg.priority > 7:  # 高优先级倾向采纳
        return True
    if sugg.similar_past_sugg_accepted_ratio > 0.7:
        return True
    # 默认不强求，只在相关决策时参考
    return False
```

**WARN 级**（必书面回应）：

```
function decide_warn_response(warn, ctx):
    # 分析 warn 内容 → 决定 accept / reject
    if warn.dimension in [red_lines_safety, true_completion_quality]:
        # 偏安全/质量的 WARN 倾向采纳
        return Decision(
            decision_type = 'warn_response',
            params = {
                warn_id: warn.id,
                response: 'accept',
                reason: f"采纳: {warn.message} 涉及{warn.dimension}, 应对...",
                applied_action: generate_remediation(warn, ctx),
            }
        )
    elif can_safely_dismiss(warn, ctx):
        return Decision(
            decision_type = 'warn_response',
            params = {
                warn_id: warn.id,
                response: 'reject',
                reason: f"驳回: {warn.message} 因为...（具体理由）",
            }
        )
    # 其他情况默认采纳
    return Decision(
        decision_type = 'warn_response',
        params = {
            warn_id: warn.id,
            response: 'accept',
            reason: f"默认采纳 supervisor WARN",
            applied_action: best_effort_remediation(warn, ctx),
        }
    )
```

#### 9.10.7 decision_record schema

```yaml
decision_record:
  decision_id: dec_{uuid}
  tick_id: tick_XXX
  ts: iso

  # 上下文
  context_snapshot_ref: ctx_XXX
  kb_injected:
    - id: kb_XXX
      kind: trap
      title: str
    - ...

  # 5 纪律
  five_disciplines:
    规划:
      answer: Y | N | Skip
      note: str
      skip_reason: str | null
    质量: ...
    拆解: ...
    检验: ...
    交付: ...
  five_disciplines_summary:
    all_passed: bool
    missing: [str, ...]
    skipped: [str, ...]

  # supervisor 互动
  supervisor_context:
    pending_warns: [warn_id, ...]
    applied_suggestions: [sugg_id, ...]
    dismissed_suggestions:
      - sugg_id: sugg_XXX
        reason: str
    warn_responded:
      - warn_id: warn_XXX
        response: accept | reject
        reason: str

  # 决策产出
  decision_type: invoke_skill | use_tool | delegate_subagent |
                 kb_read | kb_write | process_content |
                 request_user | state_transition | start_chain |
                 warn_response | fill_discipline_gap | no_op
  decision_params: {...}  # type-specific
  reason: str  # ≥ 20 字自然语言，必填
  confidence_score: float [0-1]  # 可选
  alternative_decisions:  # 可选 top-3 备选
    - decision_type: ...
      reason: ...

  # 执行通道
  ic_call_made:
    ic_id: IC-L2-02 | IC-04 | ...
    target: L2-03 | L1-05 | ...
    params: {...}
  result_ref: event_id | null  # 外部返回
  result_summary: str | null

  # 元数据
  duration_ms: int
  timeout_status: null | warned | interrupted
  audit_id: audit_XXX
```

#### 9.10.8 产品逻辑流程图（ASCII）

**图 1 · 单次决策完整流程**

```
IC-L2-01 on_tick 到达
         ↓
┌────────────────────────────┐
│ 1. 上下文组装               │
│  · task-board snapshot      │
│  · 近 20 条事件              │
│  · supervisor 建议队列       │
│  · 用户输入待消费             │
│  · 当前 WP / DoD            │
│ ↓                           │
│ 产出 context_snapshot        │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│ 2. KB 注入                  │
│  · 按当前 state 的策略表     │
│  · 按 kind + applicable     │
│  · top_k 返回 + 降序         │
│ ↓                           │
│ 产出 kb_injected list        │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│ 3. 5 纪律拷问                │
│  · 规划 / 质量 / 拆解 /       │
│    检验 / 交付                │
│  · 每项 Y / N / Skip + note  │
│ ↓                           │
│ 产出 five_disciplines        │
└────────────┬───────────────┘
             ↓
     任一 N? ── YES → 决策 = fill_discipline_gap → 跳 step 11
             ↓
             NO
             ↓
┌────────────────────────────┐
│ 4-8. 高优先级检查（by order）│
│  · 硬暂停？                  │
│  · WARN 待回应？              │
│  · 阶段 Gate 满足？            │
│  · 任务链回调？               │
│  · 异步结果？                 │
│  · 用户输入？                 │
│  · SUGG 可采纳？              │
│ ↓                           │
│ 命中 → 直接生成决策            │
└────────────┬───────────────┘
             ↓
             都不命中
             ↓
┌────────────────────────────┐
│ 9. 主决策树（按 state）       │
│  · CLARIFY/PLAN → planning   │
│  · TDD_PLAN → tdd_planning   │
│  · IMPL → impl_action        │
│  · VERIFY → verify_action    │
│  · CLOSING → closing_action  │
│  · 兜底 → no_op              │
│ ↓                           │
│ 产出候选决策                  │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│ 10. 决策选择                 │
│  · 能力抽象层匹配 skill       │
│  · fallback 链               │
│  · 选首选                     │
│ ↓                           │
│ 产出 final_decision          │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│ 11. 生成 decision_record    │
│  · 打包 context_snapshot_ref │
│  · 打包 5 纪律               │
│  · reason ≥ 20 字             │
│  · audit_id                   │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│ 12. 执行决策                 │
│  · state_transition → IC-L2-02│
│  · start_chain → IC-L2-03    │
│  · invoke_skill → IC-04       │
│  · delegate_subagent → IC-05  │
│  · kb_read/write → IC-06/07  │
│  · process_content → IC-11   │
│  · warn_response → IC-L2-09   │
│  · request_user → IC-17 反向 │
│  · no_op → 无 IC              │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│ 13. 等返回 / 立即返回         │
│  · 同步调用 → 等 response     │
│  · 异步委托 → 立即返回 (见 L2-01 流 F) │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│ 14. IC-L2-05 record_audit   │
└────────────┬───────────────┘
             ↓
        返回给 L2-01
     (tick 结束, duration_ms 记录)
```

**图 2 · 5 纪律拷问未过时的补齐循环**

```
Tick N: 5 纪律拷问
    ↓
发现"拆解"= N（WP 粒度 > 5 天）
    ↓
决策 = fill_discipline_gap
    ↓
params:
  discipline: 拆解
  suggested_action: "调用 L1-03 重新拆 WP"
    ↓
执行 → IC-L2-03 start_chain 或 IC-04 invoke_skill(wbs-refinement)
    ↓
记 decision_record

─────────────────

Tick N+1: 5 纪律拷问（重新检查）
    ↓
"拆解"现在 = Y（WP 粒度 ≤ 5 天）
    ↓
所有纪律过 → 进入主决策树
    ↓
做"正事"决策
```

**图 3 · Supervisor WARN 回应流**

```
(上一轮) supervisor 发 WARN → L2-06 → IC-L2-10 → L2-02 建议队列

Tick N: 上下文组装时读队列
    ↓
find_pending_warn() → 发现 warn_W1
    ↓
decide_warn_response(W1, ctx)
    ↓
分析 W1.dimension + 严重程度
    ├── 应采纳 → response=accept, 生成 applied_action
    └── 可驳回 → response=reject + 详细理由
    ↓
decision_type = warn_response
    ↓
IC-L2-09 record_warn_response(warn_id=W1, response, reason, applied_action?)
    ↓
L2-05 落审计 → 事件总线 → L1-07 可回读
```

#### 9.10.9 配置参数清单

| 参数 | 默认 | 意义 |
|---|---|---|
| `CONTEXT_RECENT_EVENTS_N` | 20 | 上下文带近 N 条事件 |
| `KB_TOP_K` | 5 | 每 kind 注入 top-K |
| `DECISION_TIMEOUT_MS` | 20000 | 决策总耗时上限（留 10s 给 watchdog buffer） |
| `KB_INJECTION_TIMEOUT_MS` | 500 | KB 注入超时 |
| `FIVE_DISCIPLINES_TIMEOUT_MS` | 200 | 5 纪律拷问超时 |
| `SKILL_REGISTRY_CACHE_TTL_SEC` | 60 | skill 注册表缓存 |
| `WARN_RESPONSE_DEADLINE_TICKS` | 1 | WARN 必在 N 次 tick 内回应 |
| `DISCIPLINE_FILL_MAX_ATTEMPTS` | 3 | 同一纪律补齐连续尝试 N 次后升级告警 |
| `CONFIDENCE_SCORE_ENABLED` | false | 可选功能: 决策置信度 |
| `ALTERNATIVE_DECISIONS_ENABLED` | false | 可选功能: top-3 候选 |

#### 9.10.10 与 scope §8 对外 IC 的映射

本 L2 承担的 scope §8 IC：

| scope IC | 实现方式 |
|---|---|
| IC-04 invoke_skill | 本 L2 的 `decide_*_action` 产出 `decision_type=invoke_skill` → 外发 |
| IC-05 delegate_subagent | 同上，`decision_type=delegate_subagent` |
| IC-06 kb_read | KB 注入阶段主动发起（不对外暴露为决策类型） |
| IC-07 kb_write_session | 决策 = `kb_write` 时发起 |
| IC-11 process_content | 决策 = `process_content` 时发起 |
| IC-13 push_suggestion | 通过 L2-06 接收 → IC-L2-10 分派到本 L2 建议队列 |
| IC-14 push_rollback_route | L2-06 接收后经 IC-L2-10 WARN 级分派，决策引擎处理 |
| IC-17 user_intervene | 接收 ← L1-10，处理 = `decide_process_user` |

## 10. L2-03 · 状态机编排器 详细定义

### 10.1 职责 + 锚定

**一句话职责**：负责 HarnessFlow 7 阶段 state 转换的"合法性 + 执行 + 钩子联动"——查 allowed_next → 执行转换（exit hook + entry hook）→ 广播事件 → 审计留痕。**状态机的唯一执行者**。

**上游锚定**：
- scope §5.1.6 必须义务："在阶段切换前查 allowed_next"
- scope §3.5 L1 硬约束 1-4（必经 7 阶段 + 必 4 Stage Gate + methodology-paced）
- BF-L3-13 阶段切换触发流
- BF-X-05 KB 注入策略（阶段切换时触发）

**下游服务**：L2-02（返回转换结果）· L2-05（审计）· L1-06（entry hook 触发 KB 注入）

---

### 10.2 输入 / 输出

#### 输入

| 类别 | schema | 来源 |
|---|---|---|
| state 转换请求 | IC-L2-02 `{from, to, reason, evidence_refs, trigger_tick}` | L2-02 |
| 配置：allowed_next 表 | 静态配置（source: scope §5.2 + harnessFlow state-machine.md） | 启动加载 |

#### 输出

| 类别 | schema | 去向 |
|---|---|---|
| 转换结果 | `{accepted: bool, new_entry: state_history_entry, hook_results}` | 返回 L2-02 |
| 状态转换审计 | IC-L2-06 `{from, to, reason, pre_snapshot_ref, post_snapshot_ref, entry_hook_result, exit_hook_result, ts}` | L2-05 |
| entry hook 触发 | 内部事件 `{hook_type: entry/exit, state, ctx}` | 触发 KB 注入（L1-06）等 |
| 广播事件 | `state_transitioned` 事件 | L1-09 事件总线 |

---

### 10.3 边界

#### In-scope

1. allowed_next 表管理（静态 + 运行时校验）
2. state 转换原子执行（verify → exit hook → update state → entry hook → broadcast）
3. 阶段 entry hook 编排（S1→S2 切换时触发 KB 注入策略 / S3→S4 时触发 TDD 蓝图检查 等）
4. 阶段 exit hook 编排（每 state 离开前的清理动作）
5. 转换幂等性（相同转换请求多次调用结果一致）
6. 失败回滚（entry hook 失败时 rollback state + 告警）

#### Out-of-scope

- ❌ **不做决策**（什么时候转 state 由 L2-02 决定）
- ❌ **不做 KB 注入本身**（hook 只是触发，注入由 L1-06）
- ❌ **不管 Quality Loop 4 级回退路由**（L1-07 via IC-L2-10 发路由 → L2-02 → 本 L2）
- ❌ **不做 tick 调度** → L2-01
- ❌ **不写事件总线** → L2-05

#### 边界规则

- 本 L2 **只管 state 转换的执行**，不管"要不要转"
- allowed_next 表是静态配置，本 L2 只读不改

---

### 10.4 约束

#### 业务模式引用

- **PM-10 事件总线**：转换事件必落
- **PM-07 产出物模板**：state_history 按模板追加

#### 硬约束

1. **allowed_next 表不可被运行时修改**（只读）
2. **转换必须原子**（exit hook + state update + entry hook 构成事务）
3. **entry hook 失败必须 rollback** state
4. **转换延迟 ≤ 500ms**（不含 hook 内的外部 IO）
5. **一次只处理一个转换请求**（并发转换拒绝）
6. **所有转换必经 IC-L2-06 审计**（不可跳过）

#### 性能约束

- 转换执行 ≤ 500ms P99
- allowed_next 查询 ≤ 10ms P99
- entry hook 触发 ≤ 2s（含 KB 注入）

---

### 10.5 🚫 禁止行为（明确清单）

- 🚫 **禁止接受不在 allowed_next 的转换**（硬性拒绝 + 审计）
- 🚫 **禁止跳过 entry / exit hook**（无 hook 声明也要调空 hook 走完流程）
- 🚝 **禁止并发执行多个转换**（同一时间只能处理一个）
- 🚫 **禁止 entry hook 失败时不 rollback**（必须留痕 + 回退 state）
- 🚫 **禁止 state_history 无追加**（每次转换必 append）
- 🚫 **禁止本 L2 内部修改 allowed_next 表**（只读）
- 🚫 **禁止跳过审计**（IC-L2-06 必调）

---

### 10.6 ✅ 必须职责（明确清单）

- ✅ **必须**对每个转换请求查 allowed_next
- ✅ **必须**转换过程原子（失败 rollback）
- ✅ **必须**触发当前 state 的 exit hook（清理当前阶段的临时态）
- ✅ **必须**触发目标 state 的 entry hook（如 KB 注入 / DoD 检查）
- ✅ **必须**追加 state_history_entry（带时间戳 + trigger_reason + hook_results）
- ✅ **必须**通过 IC-L2-06 审计 state 转换
- ✅ **必须**广播 `state_transitioned` 事件（让 L1-07 / L1-10 等消费）
- ✅ **必须**转换失败时返回 `{accepted: false, reason: ...}` 给调用方

---

### 10.7 🔧 可选功能职责

- 🔧 **转换预览**：`preview_transition(from, to)` 接口 — 不执行，只返回"若执行会做什么"（给 UI 用）
- 🔧 **转换统计**：维护每个 state 的停留时长 + 转换次数（给 L1-07 "计划对齐"维度用）
- 🔧 **转换可视化**：产出 state_history 的时间轴 JSON（L1-10 UI 用）
- 🔧 **hook 超时降级**：entry hook > 2s 时告警但继续（默认关）

---

### 10.8 与其他 L2 交互

**作为被调方**：

| IC | 调用方 | 触发 | 接收字段 |
|---|---|---|---|
| **IC-L2-02** | L2-02 | 决策 = state_transition | `{from, to, reason, evidence_refs, trigger_tick}` |

**作为调用方**：

| IC | 被调方 | 触发 | 调用字段 |
|---|---|---|---|
| **IC-L2-06** | L2-05 | 每次转换（成功或失败） | `{from, to, reason, pre_snapshot_ref, post_snapshot_ref, entry_hook_result, exit_hook_result, ts, accepted}` |
| IC-06 kb_read | L1-06（via 外部） | entry hook 触发 KB 注入（PM-06） | `{kind, scope, context_filter}` |

---

### 10.9 🎯 交付验证大纲

#### 成功信号

- 每次 state 转换后 `task-board.state_history` 追加一条
- 每次转换有对应 IC-L2-06 审计事件
- entry hook 失败时 state **不变**（rollback 生效）

#### 正向测试

| # | 场景 | 验证点 |
|---|---|---|
| P1 | 合法转换（CLARIFY → PLAN） | `{accepted: true}` + state_history 追加 |
| P2 | state 转换触发 entry hook | PLAN entry hook 触发 KB 注入 recipe+tool_combo |
| P3 | 转换过程原子 | exit hook + state update + entry hook 三阶段全执行 |
| P4 | 所有转换 IC-L2-06 审计 | audit 含 pre/post snapshot + hook result |
| P5 | 广播 `state_transitioned` | L1-07 / L1-10 可订阅读到 |

#### 负向测试

| # | 场景 | 验证点 |
|---|---|---|
| N1 | 非法转换（CLARIFY → VERIFY，跳过 PLAN） | `{accepted: false, reason: not in allowed_next}` |
| N2 | 并发转换 | 第二个请求被拒 + 告警 |
| N3 | entry hook 失败 | state rollback + audit 记 hook_failed |
| N4 | 尝试修改 allowed_next 表 | 拒绝 |
| N5 | 跳过审计调用（mock 去掉 IC-L2-06） | 集成测试发现 audit 缺失 |

#### 集成用例

| # | 场景 | 涉及 L2 |
|---|---|---|
| I1 | 端到端 state 转换链：L2-02 决策 → L2-03 转换 → L2-05 审计 → L1-09 落盘 | L2-02/03/05 + L1-09 |
| I2 | 阶段切换触发 KB 注入：L2-03 entry hook → L1-06 kb_read | L2-03 + L1-06 |
| I3 | S2→S3 Stage Gate 联动：L2-02 决定 Gate 通过 → L2-03 转换 → L2-05 审计 | L2-02/03/05 |
| I4 | 极重度 FAIL 回 S1 重锚：L2-02（受 L1-07 指令）发 to=CLARIFY → L2-03 执行 | L2-02/03/05 + L1-07 |

#### 性能阈值

- 转换执行 ≤ 500ms P99
- allowed_next 查询 ≤ 10ms
- entry hook ≤ 2s（含 KB 注入）

---

### 10.10 L3 · 状态机编排器实现设计

#### 10.10.1 allowed_next 表（7 state + allowed_next）

来源：scope §5.2 L1-02 allowed_next + HarnessFlow 7 阶段设计。

| state | allowed_next | 备注 |
|---|---|---|
| **INIT** | [CLARIFY] | 系统初始化 → 必进 CLARIFY |
| **CLARIFY** | [PLAN, CLARIFY（循环）, ABORTED] | 澄清循环 / 进规划 / 用户放弃 |
| **PLAN** | [TDD_PLAN, CLARIFY（回退）, PLAN（循环）, ABORTED] | 进 TDD / 回 CLARIFY / 规划迭代 / 终止 |
| **TDD_PLAN** | [IMPL, PLAN（回退）, TDD_PLAN（循环）, ABORTED] | 进执行 / 回规划 / TDD 迭代 |
| **IMPL** | [VERIFY, IMPL（循环, 多 WP）, TDD_PLAN（回退）, ABORTED, PAUSED] | 进验证 / WP 内部循环 / 回 TDD / 暂停 |
| **VERIFY** | [COMMIT, IMPL（回退轻度）, TDD_PLAN（回退中度）, PLAN（回退重度）, CLARIFY（回退极重度）, ABORTED] | Quality Loop 4 级回退路由 |
| **COMMIT** | [RETRO_CLOSE, VERIFY（回退）, ABORTED] | 收尾 / 回验证 |
| **RETRO_CLOSE** | [CLOSED, ABORTED] | 终态 |
| **PAUSED** | [INIT, CLARIFY, PLAN, TDD_PLAN, IMPL, VERIFY, COMMIT, RETRO_CLOSE, ABORTED] | 恢复到任意前态或终止 |
| **CLOSED** | [] | 终态无出 |
| **ABORTED** | [] | 终态无出 |

#### 10.10.2 state 转换执行算法

```
function execute_transition(req):
    # req: {from, to, reason, evidence_refs, trigger_tick}

    # Step 1: 并发检查
    if is_transition_in_progress():
        return {accepted: false, reason: 'concurrent transition in progress'}
    lock_transition()

    try:
        # Step 2: 合法性检查
        current_state = read_task_board_state()
        if req.from != current_state:
            return {accepted: false, reason: f'state mismatch: current={current_state}, from={req.from}'}
        if req.to not in ALLOWED_NEXT[current_state]:
            return {accepted: false, reason: f'{req.to} not in allowed_next of {current_state}'}

        # Step 3: 快照（供 rollback 使用）
        pre_snapshot = snapshot_state_and_context()

        # Step 4: 执行 exit hook
        try:
            exit_hook_result = run_exit_hook(current_state, context)
        except Exception as e:
            unlock_transition()
            return {accepted: false, reason: f'exit_hook_failed: {e}'}

        # Step 5: 更新 state（原子）
        try:
            atomic_update_state(from=current_state, to=req.to)
        except Exception as e:
            # 恢复 exit hook 的副作用（如有）
            rollback_exit_hook_effects(exit_hook_result)
            unlock_transition()
            return {accepted: false, reason: f'state_update_failed: {e}'}

        # Step 6: 执行 entry hook
        try:
            entry_hook_result = run_entry_hook(req.to, context)
        except Exception as e:
            # 关键: entry hook 失败 → 回滚 state
            rollback_state_to(current_state)
            rollback_exit_hook_effects(exit_hook_result)
            unlock_transition()
            return {accepted: false, reason: f'entry_hook_failed: {e}'}

        # Step 7: 追加 state_history
        new_entry = {
            from_state: current_state,
            to_state: req.to,
            timestamp: now(),
            trigger: req.reason,
            trigger_tick: req.trigger_tick,
            evidence_refs: req.evidence_refs,
            exit_hook_result: exit_hook_result,
            entry_hook_result: entry_hook_result,
        }
        append_state_history(new_entry)

        # Step 8: 广播事件
        emit_event('state_transitioned', {
            from: current_state,
            to: req.to,
            ts: now(),
            entry_id: new_entry.id,
        })

        # Step 9: 审计 IC-L2-06
        L2-05.record_state_transition(
            from=current_state,
            to=req.to,
            reason=req.reason,
            pre_snapshot_ref=pre_snapshot.ref,
            post_snapshot_ref=take_post_snapshot().ref,
            entry_hook_result=entry_hook_result,
            exit_hook_result=exit_hook_result,
            ts=now()
        )

        unlock_transition()
        return {accepted: true, new_entry: new_entry, hook_results: {entry_hook_result, exit_hook_result}}

    except Exception as e:
        # 最外层兜底
        unlock_transition()
        L2-05.record_state_transition(from=..., to=..., accepted=false, reason=str(e))
        return {accepted: false, reason: f'uncaught: {e}'}
```

#### 10.10.3 entry hook / exit hook 清单

**entry hooks**（按 to state）：

| to state | entry hook 动作 |
|---|---|
| CLARIFY | 注入 trap + pattern + project_context KB；检查 goal_anchor 非空 |
| PLAN | 注入 recipe + tool_combo KB；触发 4 件套生成检查 |
| TDD_PLAN | 注入 anti_pattern KB；检查 4 件套齐全 |
| IMPL | 注入 pattern + anti_pattern KB；选定当前 WP |
| VERIFY | 注入 trap KB（假完成陷阱）；准备 verifier context |
| COMMIT | 检查 verifier_report PASS；准备 commit message 模板 |
| RETRO_CLOSE | 触发 retro 生成 ；准备 archive |
| CLOSED | 触发 KB 晋升仪式 |
| ABORTED | 触发 failure-archive.jsonl 写入 |
| PAUSED | 冻结 task-board; 生成 UI 暂停卡片 |

**exit hooks**（按 from state）：

| from state | exit hook 动作 |
|---|---|
| CLARIFY | 锁定 goal_anchor.hash |
| PLAN | 冻结 4 件套；确保 WBS 可读 |
| TDD_PLAN | 冻结 TDD 蓝图 |
| IMPL | 清理 WP 锁定 |
| VERIFY | 保存 verifier_report 引用 |
| COMMIT | 确保 commit 已落盘 |
| PAUSED | 清理暂停标记 |

#### 10.10.4 转换幂等性设计

同一 `(from, to, trigger_tick)` 的转换请求在**同 tick 内**多次调用应产生同一结果（幂等）：

```
function execute_transition_idempotent(req):
    # Key = (from, to, trigger_tick)
    key = f"{req.from}-{req.to}-{req.trigger_tick}"
    if key in recent_transitions:  # 近 5s 去重
        return recent_transitions[key]  # 返回缓存结果

    result = execute_transition(req)
    recent_transitions[key] = result
    schedule_cache_eviction(key, 5)  # 5s 后过期
    return result
```

#### 10.10.5 产品逻辑流程图

```
IC-L2-02 request_state_transition(from, to, reason) 到达
     ↓
检查并发锁 → 已有转换? → YES → 拒绝返回
     ↓ NO
锁定
     ↓
读 task-board.current_state → 对比 req.from → 不匹配? → YES → 拒绝返回
     ↓ NO
查 ALLOWED_NEXT[current_state] → req.to 在里面? → NO → 拒绝返回
     ↓ YES
快照 pre_snapshot
     ↓
执行 exit_hook(current_state)
     ├── 失败 → rollback + 拒绝返回
     └── 成功 ↓
atomic_update_state(from, to)
     ├── 失败 → rollback exit_hook + 拒绝返回
     └── 成功 ↓
执行 entry_hook(to)
     ├── 失败 → rollback state + rollback exit_hook + 拒绝返回
     └── 成功 ↓
追加 state_history_entry
     ↓
广播 state_transitioned 事件
     ↓
IC-L2-06 record_state_transition 审计
     ↓
解锁
     ↓
返回 {accepted: true}
```

#### 10.10.6 配置参数

| 参数 | 默认 | 意义 |
|---|---|---|
| `TRANSITION_TIMEOUT_MS` | 500 | 单次转换超时（不含 hook） |
| `ENTRY_HOOK_TIMEOUT_MS` | 2000 | entry hook 执行超时 |
| `IDEMPOTENCY_WINDOW_SEC` | 5 | 幂等窗口 |
| `ALLOWED_NEXT_SOURCE` | `static-config` | allowed_next 表来源 |

---

## 11. L2-04 · 任务链执行器 详细定义

### 11.1 职责 + 锚定

**一句话职责**：接收多步任务链定义 → 启动 mini state machine → 按序执行每步（委托外部执行）→ 步完成回调 L2-02 决策下一步 → 步失败回滚/重试/升级。**复杂决策的展开器**。

**锚定**：
- BF-L3-15 任务链执行流
- scope §5.1 "决策选择（skill/工具/任务链）"

**下游**：L2-02（步完成回调）· L2-05（步审计）· L1-05（执行委托）

---

### 11.2 输入 / 输出

#### 输入

| 类别 | schema | 来源 |
|---|---|---|
| 启动任务链 | IC-L2-03 `{chain_def, chain_goal, context}` | L2-02 |
| 外部步结果 | 事件 `step_result` from L1-05（子 Agent / skill 回传） | L1-09 事件总线 |

#### 输出

| 类别 | schema | 去向 |
|---|---|---|
| 步完成回调 | IC-L2-04 `{chain_id, step_id, outcome, result_ref, next_hint?}` | L2-02 |
| 步审计 | IC-L2-07 `{chain_id, step_id, action, outcome, step_result, ts}` | L2-05 |
| 外部步执行委托 | IC-04 / IC-05 via L1-05 | L1-05 |
| chain 升级告警 | 通过 L2-06 IC-L2-10 | L2-06 |

---

### 11.3 边界

#### In-scope

1. chain_def schema 管理 + 验证
2. mini state machine（per chain）驱动
3. 步执行调度（按依赖拓扑 + 串行/并行）
4. 步回滚策略（失败时回退前步成果）
5. 步超时处理（单步超时阈值）
6. chain 嵌套规则（chain 内启新 chain）
7. 死循环保护（同步连续失败 ≥ 3）

#### Out-of-scope

- ❌ **不做步本身的执行**（委托 L1-05）
- ❌ **不做决策**（每步完成回调 L2-02 决策下一步）
- ❌ **不写事件总线** → L2-05
- ❌ **不做 state 转换** → L2-03
- ❌ **不做 Quality Loop 4 级回退**（L1-07 的事）

#### 边界规则

- chain 和 tick 是**独立概念**：一个 chain 跨多个 tick（因为每步完成要回调决策引擎）
- chain 失败不影响 L2-01 tick 调度（失败 chain 会被标 stuck）

---

### 11.4 约束

#### 业务模式

- **PM-04 WP 拓扑并行推进**（chain 内同时最多 N 步并行，默认 N=2）
- **PM-10 事件总线** 步审计

#### 硬约束

1. **chain_def 必须 DAG**（无环）
2. **同一 chain_id 只能有一个 mini SM 运行**
3. **单步超时 = 60s 默认**（可按 step 覆盖）
4. **连续失败 ≥ 3 → 升级** BF-E-10 死循环保护
5. **步结果必通过 IC-L2-04 回调 L2-02**（不得跳过决策）
6. **chain 嵌套深度 ≤ 3**（防套娃爆炸）

#### 性能约束

- 步派发 ≤ 50ms
- 步完成回调 ≤ 100ms

---

### 11.5 🚫 禁止行为

- 🚫 **禁止 chain_def 有环**（硬性 DAG 校验）
- 🚫 **禁止并行 > 2 步**（同一 chain 内）
- 🚫 **禁止 chain 嵌套深度 > 3**
- 🚫 **禁止跳过 IC-L2-04 回调直接决定下一步**
- 🚫 **禁止步结果无 IC-L2-07 审计**
- 🚫 **禁止连续失败 ≥ 3 次不升级**
- 🚫 **禁止 chain 永不终止**（必有终止条件）

---

### 11.6 ✅ 必须职责

- ✅ **必须** chain_def DAG 校验（启动时）
- ✅ **必须**按拓扑序 + 依赖满足调度步
- ✅ **必须**每步完成通过 IC-L2-04 回调 L2-02
- ✅ **必须**每步通过 IC-L2-07 审计
- ✅ **必须**单步超时后做 retry / rollback / 升级（不得无限等）
- ✅ **必须**连续失败 ≥ 3 触发升级（通过 L2-06）
- ✅ **必须**chain 完成后清理资源

---

### 11.7 🔧 可选功能职责

- 🔧 **chain 可视化**：输出当前 chain 的执行拓扑图 + 进度（L1-10 UI 用）
- 🔧 **chain 暂停/恢复**：长链支持手动暂停
- 🔧 **chain checkpoint**：关键步后落 checkpoint（跨 session 恢复）
- 🔧 **chain 重试策略 per step**：不同步可配置不同重试策略

---

### 11.8 与其他 L2 交互

**作为被调方**：

| IC | 调用方 | 触发 | 接收 |
|---|---|---|---|
| **IC-L2-03** | L2-02 | 决策 = start_chain | `{chain_def, chain_goal, context}` |

**作为调用方**：

| IC | 被调方 | 触发 | 调用字段 |
|---|---|---|---|
| **IC-L2-04** | L2-02 | 每步完成 | `{chain_id, step_id, outcome, result_ref, next_hint?}` |
| **IC-L2-07** | L2-05 | 每步审计 | `{chain_id, step_id, action, outcome, step_result, ts}` |
| IC-04/IC-05 | L1-05（外部） | 委托步执行 | step-specific params |
| IC-L2-10 via L2-06 | L2-06 | 连续失败升级 | `{level: WARN, content: 'chain stuck'}` |

---

### 11.9 🎯 交付验证大纲

#### 成功信号

- 每 chain 启动产出 `chain_id`
- 每步完成有对应 IC-L2-04 + IC-L2-07
- chain 完成后资源清理（无泄漏）

#### 正向测试

| # | 场景 | 验证 |
|---|---|---|
| P1 | 启动 3 步串行 chain | 按序执行 + 每步 IC-L2-04 回调 |
| P2 | 2 步并行 chain（独立依赖） | 并行执行 + 全完成后汇总回调 |
| P3 | 步超时触发重试 | 重试 1 次后成功 |
| P4 | chain 嵌套（depth=2） | 内 chain 完成后回主 chain |

#### 负向测试

| # | 场景 | 验证 |
|---|---|---|
| N1 | chain_def 有环 | 启动时拒绝 + 告警 |
| N2 | 并行 > 2 步 | 拒绝 + 告警 |
| N3 | 嵌套深度 > 3 | 拒绝 + 告警 |
| N4 | 连续 3 次失败 | 升级 + 硬暂停请求 |
| N5 | 步超时 60s+ 无结果 | 触发 retry 或 rollback |

#### 集成用例

| # | 场景 | L2 |
|---|---|---|
| I1 | 3 步 chain 端到端 | L2-02 → L2-04 → L1-05 → L2-04 → L2-02 反复 |
| I2 | 死循环升级链 | L2-04 3 次失败 → L2-06 → L2-01 硬暂停 |
| I3 | chain 审计链 | L2-04 → L2-05 → L1-09 事件总线 |

#### 性能阈值

- 步派发 ≤ 50ms P99
- 步回调 ≤ 100ms P99
- chain 整体无泄漏（内存 / 句柄）

---

### 11.10 L3 · 任务链执行器实现设计

#### 11.10.1 chain_def schema

```yaml
chain_def:
  chain_id: ch_{uuid}           # 系统生成
  chain_goal: str               # 一句话目标
  steps:
    - step_id: s1
      action:
        type: invoke_skill | delegate_subagent | use_tool | ...
        params: {...}
      deps: []                  # 依赖的 step_id 列表（空 = 可立即执行）
      timeout_ms: 60000         # 可覆盖默认
      retry_policy:
        max_retries: 1
        backoff_ms: 1000
      expected_outcome: pass | fail | any
      rollback_action:          # 失败时执行
        type: ...
        params: {...}
    - step_id: s2
      deps: [s1]                # 依赖 s1
      ...
  termination_condition:
    all_steps_completed: true   # 默认: 所有步完成
    # or: first_success / until_condition(fn)
  nesting_depth: int            # 当前 chain 所处嵌套深度（≤ 3）
  parent_chain_id: str | null
```

#### 11.10.2 mini state machine

每 chain 的状态：

```
[PENDING] → chain 创建
    ↓ 启动
[RUNNING] ───┐
    │        │ 步失败（retriable）
    │        └──→ [STEP_RETRYING]
    │                  │ 重试成功
    │                  └──→ 回 RUNNING
    │                  │ 重试失败（max_retries 用完）
    │                  └──→ [STEP_FAILED]
    │                          │ 有 rollback
    │                          ├──→ [ROLLING_BACK]
    │                          │       ↓
    │                          │     [ROLLED_BACK]
    │                          │       ↓
    │                          │     [FAILED] (终态)
    │                          │ 无 rollback
    │                          └──→ [FAILED]
    │ 全部步完成
    └──→ [COMPLETED] (终态)
    │ 连续失败 ≥ 3
    └──→ [ESCALATED] → 通知 L2-06 → 硬暂停
    │ 外部 cancel
    └──→ [CANCELED] (终态)
```

#### 11.10.3 步调度算法

```
function schedule_next_steps(chain):
    ready_steps = []
    for step in chain.steps:
        if step.status != 'pending':
            continue
        if all(dep.status == 'completed' for dep in step.deps):
            ready_steps.append(step)

    # 并行上限
    running_count = count(s for s in chain.steps if s.status == 'running')
    can_start = MAX_PARALLEL - running_count

    for step in ready_steps[:can_start]:
        dispatch_step(step)

function dispatch_step(step):
    step.status = 'running'
    step.started_at = now()
    # 委托 L1-05 执行
    if step.action.type == 'invoke_skill':
        L1-05.IC-04 invoke_skill(capability=..., params=...)
    elif step.action.type == 'delegate_subagent':
        L1-05.IC-05 delegate_subagent(...)
    # 结果通过事件总线回来 → 触发 handle_step_result
```

#### 11.10.4 步结果处理

```
function handle_step_result(chain_id, step_id, result):
    chain = get_chain(chain_id)
    step = chain.steps[step_id]

    # 审计
    L2-05.IC-L2-07 record_chain_step(
        chain_id=chain_id, step_id=step_id,
        action=step.action.type, outcome=result.outcome,
        step_result=result, ts=now()
    )

    if result.outcome == 'pass':
        step.status = 'completed'
        chain.consecutive_failures = 0
    elif result.outcome == 'fail':
        if step.retry_count < step.retry_policy.max_retries:
            # 重试
            step.retry_count += 1
            schedule_after(step.retry_policy.backoff_ms, lambda: dispatch_step(step))
            return
        else:
            step.status = 'failed'
            chain.consecutive_failures += 1
            # 检查是否有 rollback
            if step.rollback_action:
                execute_rollback(step)

    # 通过 IC-L2-04 回调 L2-02
    L2-02.IC-L2-04 step_completed(
        chain_id=chain_id, step_id=step_id,
        outcome=result.outcome, result_ref=result.event_id
    )
    # L2-02 会决定"继续 chain / 中止 chain / 调整 chain"

    # 检查 chain 终止条件
    if chain.consecutive_failures >= 3:
        chain.state = 'ESCALATED'
        escalate_to_L2_06(chain)
    elif all_steps_completed(chain):
        chain.state = 'COMPLETED'
        cleanup_chain(chain)
    else:
        schedule_next_steps(chain)
```

#### 11.10.5 步超时处理

```
# 每 5s 扫
function watchdog_steps():
    for chain in active_chains:
        for step in chain.steps:
            if step.status == 'running':
                elapsed = now() - step.started_at
                if elapsed > step.timeout_ms:
                    # 超时
                    L2-05.record_audit(action='step_timeout', ...)
                    handle_step_result(chain.id, step.id, result={
                        outcome: 'fail',
                        error: 'timeout'
                    })
```

#### 11.10.6 chain 嵌套规则

- 嵌套深度 ≤ 3
- 内 chain 的步可以引用外 chain 的步结果（通过 context）
- 内 chain 失败不自动终止外 chain（由 L2-02 回调时决策）
- 内 chain completed 后通过正常步完成回调回外 chain

#### 11.10.7 配置参数

| 参数 | 默认 | 意义 |
|---|---|---|
| `MAX_PARALLEL_STEPS` | 2 | chain 内并行步上限 |
| `DEFAULT_STEP_TIMEOUT_MS` | 60000 | 单步默认超时 |
| `MAX_NESTING_DEPTH` | 3 | chain 嵌套深度上限 |
| `CONSECUTIVE_FAILURE_ESCALATE` | 3 | 连续失败升级阈值 |
| `WATCHDOG_INTERVAL_MS` | 5000 | 步超时扫描间隔 |

## 11. L2-04 · 任务链执行器 详细定义

> ⏸ 待 R5 撰写。含 chain_def schema / mini SM 算法 / 步回滚策略 / 步超时处理 / chain 嵌套规则。

## 12. L2-05 · 决策审计记录器 详细定义

### 12.1 职责 + 锚定

**一句话职责**：L1-01 所有审计的**唯一落盘入口** —— 接收其他 5 个 L2 的审计调用（IC-L2-05/06/07/09），打包证据链，通过外部 IC-09 落到 L1-09 事件总线；维护本 L1 内部的审计反查索引。

**锚定**：
- scope §5.1.6 必须义务："走事件总线记录所有 decision / tool call"
- Goal §4.1 "决策可追溯率 100%"
- BF-X-01 决策心跳横切
- BF-L3-01 step⑥ 决策留痕
- PM-10 事件总线单一事实源

**下游**：L1-09 事件总线（唯一写入点 IC-09）

---

### 12.2 输入 / 输出

#### 输入（4 类审计调用）

| IC | 调用方 | 场景 | 字段 |
|---|---|---|---|
| **IC-L2-05** | L2-01 / L2-02 / L2-04 / L2-06 | 通用审计（tick / 决策 / supervisor INFO 等） | `{actor, action, reason, evidence, linked_tick?, ts}` |
| **IC-L2-06** | L2-03 | state 转换专用 | `{from, to, reason, pre/post_snapshot, hook_results, accepted, ts}` |
| **IC-L2-07** | L2-04 | 任务链步审计 | `{chain_id, step_id, action, outcome, step_result, ts}` |
| **IC-L2-09** | L2-02 | WARN 书面回应 | `{warn_id, response, reason, applied_action?, ts}` |

#### 输出

| 类别 | schema | 去向 |
|---|---|---|
| 外部 IC-09 append_event | `{ts, type: 'L1-01:subtype', actor, state, content, links, hash}` | L1-09 |
| 审计反查索引 | `{audit_id → {tick_id, decision_id, linked_events}}` in-memory | 内部 |

---

### 12.3 边界

#### In-scope

1. 接收 4 类 IC-L2 审计调用
2. 审计 entry 打包（证据链组装 + hash 计算 + 关联关系）
3. 通过 IC-09 原子落盘事件总线
4. 审计反查索引（by audit_id / tick_id / decision_id）
5. 事件 type 命名规范（`L1-01:decision` / `L1-01:state_transition` / `L1-01:chain_step` / `L1-01:warn_response` / `L1-01:supervisor_info` 等）

#### Out-of-scope

- ❌ **不做业务判断**（只打包落盘）
- ❌ **不做 8 维度观察**（L1-07）
- ❌ **不做持久化机制本身**（L1-09）
- ❌ **不做审计数据分析 / 可视化**（L1-10 UI 消费）

#### 边界规则

- **L1-01 内唯一写事件总线的入口**（其他 L2 一律通过本 L2 走）
- 不可丢弃审计请求（队列满时告警但不丢）

---

### 12.4 约束

#### 业务模式

- **PM-10 事件总线单一事实源**：所有 L2 审计必经本 L2
- **PM-08 可审计全链追溯**：每审计 entry 必有 reason + evidence

#### 硬约束

1. **每个审计 entry 必有 audit_id**（UUID）
2. **每个 entry 必有 reason**（空 reason 拒绝）
3. **IC-09 append 失败 → halt 整个 L1**（scope §5.9.6 硬约束）
4. **审计顺序与调用顺序一致**（FIFO）
5. **事件 type 前缀必须 `L1-01:`**

#### 性能约束

- 审计接收 ≤ 10ms
- IC-09 落盘 ≤ 50ms P99
- 反查索引查询 ≤ 5ms

---

### 12.5 🚫 禁止行为

- 🚫 **禁止丢弃审计调用**（队列满 → 告警但持续排队）
- 🚫 **禁止修改已落盘事件**（append-only）
- 🚫 **禁止跳过 audit_id 生成**
- 🚫 **禁止跳过 reason 校验**（reason 空 → 拒绝）
- 🚫 **禁止 event type 不带 `L1-01:` 前缀**
- 🚫 **禁止 IC-09 失败静默**（必 halt 整个 L1）

---

### 12.6 ✅ 必须职责

- ✅ **必须**接收所有 4 类 IC-L2 审计调用
- ✅ **必须**按 FIFO 顺序处理
- ✅ **必须**每 entry 生成 audit_id + 计算 hash
- ✅ **必须**通过 IC-09 原子落盘
- ✅ **必须**维护 in-memory 反查索引（audit_id / tick_id / decision_id）
- ✅ **必须**审计失败时向 L1-01 发 halt 信号

---

### 12.7 🔧 可选功能职责

- 🔧 **批量 flush**：小批量审计合并一次 IC-09 调用（性能优化，默认关）
- 🔧 **审计查询 API**：`query_audit(filter)` 供内部调试用
- 🔧 **审计完整性扫描**：周期扫 task-board 的 state_history + 比对事件总线 → 发现缺失

---

### 12.8 与其他 L2 交互

**作为被调方**（接收审计请求）：

| IC | 调用方 | 字段 |
|---|---|---|
| IC-L2-05 | L2-01 / L2-02 / L2-04 / L2-06 | 通用 |
| IC-L2-06 | L2-03 | state 转换 |
| IC-L2-07 | L2-04 | chain 步 |
| IC-L2-09 | L2-02 | WARN 回应 |

**作为调用方**（对外）：

| IC | 被调方 | 字段 |
|---|---|---|
| IC-09 append_event | L1-09 | `{ts, type: L1-01:X, actor, state, content, links, hash}` |

---

### 12.9 🎯 交付验证大纲

#### 成功信号
- 每次 L2 审计调用都有对应 IC-09 落盘事件（1:1 无丢失）
- 事件 type 100% 以 `L1-01:` 前缀
- 反查索引覆盖 100% 当前 session 审计

#### 正向测试
| # | 场景 | 验证 |
|---|---|---|
| P1 | IC-L2-05 调用 → 期望 IC-09 event 落盘 | L1-01:decision 事件 |
| P2 | IC-L2-06 调用 → 期望 L1-01:state_transition event | state 转换事件 |
| P3 | IC-L2-07 调用 → 期望 L1-01:chain_step event | chain 步事件 |
| P4 | IC-L2-09 调用 → 期望 L1-01:warn_response event | WARN 回应 |
| P5 | 查 audit_id → 期望返回完整 entry | 反查索引 |

#### 负向测试
| # | 场景 | 验证 |
|---|---|---|
| N1 | reason 为空 | 拒绝 + 告警 |
| N2 | IC-09 失败 | L1-01 halt 信号 |
| N3 | 并发调用 | FIFO 顺序保持 |
| N4 | event type 不带前缀 | 自动修正或拒绝 |
| N5 | 尝试修改已落盘 entry | 拒绝 |

#### 集成用例
- I1: L2-02 决策 → IC-L2-05 → L2-05 → IC-09 → L1-09 事件总线
- I2: L2-03 state 转换 → IC-L2-06 → L2-05 → IC-09（含 pre/post snapshot）
- I3: L2-04 chain 步 → IC-L2-07 → L2-05 → IC-09
- I4: L2-02 WARN 回应 → IC-L2-09 → L2-05 → IC-09（L1-07 可回读到）

---

### 12.10 L3 · 审计记录器实现设计

#### 12.10.1 audit_entry schema

```yaml
audit_entry:
  audit_id: audit_{uuid}
  source_ic: IC-L2-05 | IC-L2-06 | IC-L2-07 | IC-L2-09
  actor: L2-01 | L2-02 | L2-03 | L2-04 | L2-06
  action: str             # 如 tick_scheduled / decision_made / state_transitioned / chain_step / warn_response
  reason: str             # 必有, ≥ 20 字（决策类）
  evidence: [event_id, ...]
  linked_tick: tick_id?
  linked_decision: decision_id?
  linked_chain: chain_id?
  payload: {...}          # source_ic 特定内容
  ts: iso
  hash: sha256(prev_hash + content)
```

#### 12.10.2 打包算法

```
function record_audit(source_ic, data):
    # 1. 校验 reason 非空
    if not data.reason or len(data.reason) < 1:
        raise ValidationError('audit reason required')

    # 2. 生成 audit_id + 计算 hash
    audit_id = generate_uuid('audit')
    prev_hash = get_last_event_hash()  # from L1-09
    content_str = serialize(data)
    hash = sha256(prev_hash + content_str)

    # 3. 打包 event type
    event_type = map_to_event_type(source_ic, data.action)
    # 例: IC-L2-05 + decision_made → 'L1-01:decision'
    #     IC-L2-06 → 'L1-01:state_transition'

    # 4. 构造 event
    event = {
        ts: data.ts,
        type: event_type,
        actor: data.actor,
        state: get_current_project_state(),
        content: data.payload,
        links: {
            audit_id: audit_id,
            tick_id: data.linked_tick,
            decision_id: data.linked_decision,
            chain_id: data.linked_chain,
        },
        hash: hash,
    }

    # 5. IC-09 原子落盘
    try:
        result = L1-09.IC-09 append_event(event)
    except IOError as e:
        emit_halt_signal('L2-05 audit persist failed')
        raise

    # 6. 更新反查索引
    reverse_index[audit_id] = {
        event_id: result.event_id,
        tick_id: data.linked_tick,
        decision_id: data.linked_decision,
    }

    return {audit_id: audit_id, event_id: result.event_id}
```

#### 12.10.3 event type 映射表

| source_ic + action | event type |
|---|---|
| IC-L2-05 + tick_scheduled | `L1-01:tick_scheduled` |
| IC-L2-05 + tick_completed | `L1-01:tick_completed` |
| IC-L2-05 + tick_timeout | `L1-01:tick_timeout` |
| IC-L2-05 + idle_spin_detected | `L1-01:idle_spin` |
| IC-L2-05 + hard_halt_received | `L1-01:hard_halt` |
| IC-L2-05 + panic_intercepted | `L1-01:panic` |
| IC-L2-05 + decision_made | `L1-01:decision` |
| IC-L2-05 + supervisor_info | `L1-01:supervisor_info` |
| IC-L2-06 + * | `L1-01:state_transition` |
| IC-L2-07 + * | `L1-01:chain_step` |
| IC-L2-09 + * | `L1-01:warn_response` |

#### 12.10.4 反查索引

```yaml
reverse_index:
  by_audit_id:
    audit_XXX: {event_id, tick_id, decision_id, ts}
  by_tick_id:
    tick_XXX: [audit_id, audit_id, ...]
  by_decision_id:
    dec_XXX: audit_id  # 1:1
  by_chain_id:
    ch_XXX: [audit_id, ...]

# 索引仅 in-memory；跨 session 恢复时从事件总线 replay 重建
```

#### 12.10.5 配置参数

| 参数 | 默认 | 意义 |
|---|---|---|
| `BATCH_FLUSH_ENABLED` | false | 批量 flush（可选功能） |
| `REASON_MIN_LENGTH` | 1 | reason 最小长度（decision 类强制 ≥ 20） |
| `REVERSE_INDEX_MAX_SIZE` | 100000 | 反查索引条目上限 |

---

## 13. L2-06 · Supervisor 建议接收器 详细定义

### 13.1 职责 + 锚定

**一句话职责**：接收 L1-07 Supervisor 的 IC-13 push_suggestion / IC-15 request_hard_halt → 按 INFO/SUGG/WARN/BLOCK **4 级路由分派**到 L2-01/02/05；维护建议队列 + 4 级计数器（观察 supervisor 自身健康）。**本 L1 唯一对接 L1-07 的网关**。

**锚定**：
- scope §5.1.6 必须义务："响应 supervisor BLOCK"、"书面回应 WARN"
- scope §8.2 IC-13 / IC-15（本 L2 承担）
- BF-X-02 监督观察流（本 L2 是消费方）
- PM-12 红线分级自治

**下游**：L2-01（BLOCK）· L2-02（SUGG/WARN）· L2-05（INFO 审计）

---

### 13.2 输入 / 输出

#### 输入

| IC | 来源 | 字段 |
|---|---|---|
| **IC-13 push_suggestion** | L1-07 | `{level: INFO/SUGG/WARN, dimension, message, suggested_action, ts}` |
| **IC-15 request_hard_halt** | L1-07 | `{red_line_id, message, supervisor_event_id}` |

#### 输出

| IC | 去向 | 触发条件 |
|---|---|---|
| **IC-L2-05** | L2-05 | INFO 级 |
| **IC-L2-10** | L2-02 | SUGG / WARN 级（入建议队列）|
| **IC-L2-09 记录** | L2-05 | WARN 回应时由 L2-02 调 |
| **IC-L2-08** | L2-01 | BLOCK 级（硬暂停） |

---

### 13.3 边界

#### In-scope

1. IC-13 / IC-15 接收
2. 4 级路由分派（INFO/SUGG/WARN/BLOCK）
3. 建议队列管理（FIFO + 优先级）
4. 4 级计数器（观察 supervisor 频率，供 L1-07 自身健康）
5. WARN 回应追踪（warn_id → 回应状态）
6. BLOCK 广播 + user_authorize 接收后清除

#### Out-of-scope

- ❌ **不做 supervisor 的观察**（L1-07 的事）
- ❌ **不做建议内容解析**（L2-02 消费时做）
- ❌ **不做决策**（只路由）
- ❌ **不做 state 转换**（L2-03）

#### 边界规则

- 本 L2 是**纯网关**：只接收 + 路由 + 计数
- 4 级路由规则**不可变**（严格按 INFO/SUGG/WARN/BLOCK 分派）

---

### 13.4 约束

#### 业务模式

- **PM-12 红线分级自治**（4 级严格路由）
- **PM-02 主-副协作**（supervisor 建议不可丢失）

#### 硬约束

1. **BLOCK 级必 ≤ 100ms 响应**（IC-L2-08 到 L2-01）
2. **INFO 不打扰用户**（仅落审计）
3. **WARN 必进建议队列**（L2-02 下 tick 必读）
4. **建议队列无上限**（防丢失；但 > 1000 告警）
5. **BLOCK 必等 user authorize 才清除**

---

### 13.5 🚫 禁止行为

- 🚫 **禁止丢弃任何 supervisor 建议**
- 🚫 **禁止越级路由**（INFO 不得路由到 L2-02 / BLOCK 不得路由到 L2-05）
- 🚫 **禁止 BLOCK 响应 > 100ms**
- 🚫 **禁止未经 user authorize 清除 BLOCK**
- 🚫 **禁止修改建议内容**（只转发不改）

---

### 13.6 ✅ 必须职责

- ✅ **必须**按 level 严格 4 级路由
- ✅ **必须**INFO 级走 IC-L2-05 审计（不打扰用户）
- ✅ **必须**BLOCK 级 ≤ 100ms 发 IC-L2-08
- ✅ **必须**维护建议队列持久化（跨 session 恢复不丢）
- ✅ **必须**4 级计数器（INFO/SUGG/WARN/BLOCK 分别计）
- ✅ **必须**接收 user_intervene(authorize) 清除 BLOCK

---

### 13.7 🔧 可选功能职责

- 🔧 **建议去重**：相同 warn_id 短时间多次 → 合并
- 🔧 **supervisor 健康监测**：周期无任何建议 → 告警（supervisor 可能挂了）
- 🔧 **建议优先级微调**：允许配置 WARN 内部的优先级

---

### 13.8 与其他 L2 交互

**作为被调方**（外部）：

| IC | 调用方 | 字段 |
|---|---|---|
| **IC-13** | L1-07 | `{level, dimension, message, suggested_action}` |
| **IC-15** | L1-07 | `{red_line_id, message}` |
| **IC-17** user_intervene(authorize) | L1-10 → L1-01 | BLOCK 解除 |

**作为调用方**：

| IC | 被调方 | 触发 |
|---|---|---|
| **IC-L2-10** dispatch_suggestion | L2-02 | SUGG / WARN 级 |
| **IC-L2-08** propagate_hard_halt | L2-01 | BLOCK 级 |
| **IC-L2-05** record_audit | L2-05 | INFO 级 |

---

### 13.9 🎯 交付验证大纲

#### 成功信号
- 每 IC-13/15 接收有对应下游调用（IC-L2-05/08/10）
- BLOCK 响应 ≤ 100ms
- 4 级计数器准确

#### 正向测试
| # | 场景 | 验证 |
|---|---|---|
| P1 | IC-13 INFO 到达 | 期望仅 IC-L2-05 审计 |
| P2 | IC-13 SUGG 到达 | 期望 IC-L2-10 to L2-02 + 建议队列追加 |
| P3 | IC-13 WARN 到达 | 期望 IC-L2-10 WARN 级 + 入必回应队列 |
| P4 | IC-15 BLOCK 到达 | 期望 IC-L2-08 to L2-01 ≤ 100ms |
| P5 | user authorize 到达 | 期望 BLOCK 清除 + 允许新 tick |

#### 负向测试
| # | 场景 | 验证 |
|---|---|---|
| N1 | BLOCK 越级路由到 L2-05 | 拒绝 + 告警 |
| N2 | BLOCK 响应 > 100ms | 性能告警 |
| N3 | 丢弃 INFO 级建议 | 审计缺失 → 拒绝 |
| N4 | 未授权清除 BLOCK | 拒绝 |

#### 集成用例
- I1: 端到端 BLOCK 链：L1-07 → IC-15 → L2-06 → IC-L2-08 → L2-01 → 暂停 tick
- I2: 端到端 WARN 回应：L1-07 → IC-13 WARN → L2-06 → IC-L2-10 → L2-02 回应 → IC-L2-09 → L2-05
- I3: user authorize 链：L1-10 → IC-17 → L1-01 → L2-06 → 清除 BLOCK

---

### 13.10 L3 · Supervisor 建议接收器实现设计

#### 13.10.1 建议队列 schema

```yaml
suggestion_queue:
  pending_suggs:           # SUGG 级队列
    - sugg_id: sugg_XXX
      level: SUGG
      dimension: str
      message: str
      suggested_action: str
      ts: iso
      added_at: iso
  pending_warns:           # WARN 级队列（必回应）
    - warn_id: warn_XXX
      level: WARN
      dimension: str
      message: str
      suggested_action: str
      ts: iso
      added_at: iso
      response_deadline_tick: int  # L2-02 必在第 N 轮 tick 回应
  active_blocks:           # 当前硬暂停（可多个）
    - block_id: block_XXX
      red_line_id: str
      message: str
      issued_at: iso
      cleared_at: null       # null 表示未解除
  counters:
    info: int
    sugg: int
    warn: int
    block: int
    last_suggestion_at: iso  # 用于 supervisor 健康监测
```

#### 13.10.2 4 级路由算法

```
function route_suggestion(ic_call):
    if ic_call.source == 'IC-15':
        # 硬暂停
        block = {block_id: uuid, red_line_id: ic_call.red_line_id, ...}
        active_blocks.append(block)
        counters.block += 1
        # 立即广播
        L2-01.IC-L2-08 propagate_hard_halt(red_line_id, message)
        L2-05.IC-L2-05 record_audit(actor=L2-06, action='hard_halt_received', ...)
        return

    # IC-13 按 level 分派
    sugg = ic_call.payload
    if sugg.level == 'INFO':
        counters.info += 1
        L2-05.IC-L2-05 record_audit(actor=L2-06, action='supervisor_info', reason=sugg.message, ts=sugg.ts)
        # 不转发给 L2-02
        return

    elif sugg.level == 'SUGG':
        counters.sugg += 1
        sugg_id = uuid
        pending_suggs.append({sugg_id, ...})
        L2-02.IC-L2-10 dispatch_suggestion(level=SUGG, content=sugg, target=L2-02)
        return

    elif sugg.level == 'WARN':
        counters.warn += 1
        warn_id = uuid
        current_tick_n = get_current_tick_number()
        pending_warns.append({
            warn_id, response_deadline_tick: current_tick_n + 1, ...
        })
        L2-02.IC-L2-10 dispatch_suggestion(level=WARN, content=sugg, target=L2-02)
        return

    # 其他 level - 异常
    emit_audit_error('unknown supervisor level')
```

#### 13.10.3 user authorize 处理

```
function handle_user_authorize(authz_payload):
    # 清除对应 block
    for block in active_blocks:
        if block.red_line_id == authz_payload.red_line_id:
            block.cleared_at = now()
            block.cleared_by = 'user'
            block.authorize_payload = authz_payload

    # 若无待 block，通知 L2-01 恢复
    if all(b.cleared_at for b in active_blocks):
        L2-01.send_resume_signal()
        L2-05.record_audit(action='blocks_all_cleared', reason='user authorized')
```

#### 13.10.4 supervisor 健康监测

```
# 每 60s 扫
function watchdog_supervisor_health():
    elapsed = now() - counters.last_suggestion_at
    if elapsed > 300:  # 5 min 没收到任何 supervisor 事件
        L2-05.record_audit(
            actor='L2-06',
            action='supervisor_silent_warn',
            reason='supervisor 5min 无建议, 可能挂了',
            ts=now()
        )
```

#### 13.10.5 配置参数

| 参数 | 默认 | 意义 |
|---|---|---|
| `WARN_DEADLINE_TICKS` | 1 | WARN 必在 N tick 内回应 |
| `SUPERVISOR_SILENT_THRESHOLD_SEC` | 300 | supervisor 沉默告警阈值 |
| `QUEUE_WARN_THRESHOLD` | 1000 | 队列过大告警 |

## 13. L2-06 · Supervisor 建议接收器 详细定义

> ⏸ 待 R6 撰写。含建议队列 schema / 4 级分派算法 / WARN 回应追踪 / BLOCK 广播协议 / supervisor 健康监测。

---

## 14. L1-01 对外 scope §8 IC 契约映射（本 L1 实际承担）

本节详细列出 `scope.md §8.2 IC 契约清单` 中 L1-01 涉及的 IC，以及每条 IC 在本 L1 内部由哪个 L2 实现 / 接收 / 转发。

### 14.1 作为被调方（接收外部 IC）

| 外部 IC | 来自 L1 | 承担 L2 | 接收后动作 |
|---|---|---|---|
| **IC-13** push_suggestion（INFO/SUGG/WARN） | L1-07 Supervisor | **L2-06** | 4 级路由：INFO→L2-05 审计 / SUGG/WARN→L2-02 建议队列 |
| **IC-14** push_rollback_route（Quality Loop 4 级回退）| L1-07 Supervisor | **L2-06** | 转发到 L2-02 作为 WARN 级处理 → L2-02 决策 state_transition |
| **IC-15** request_hard_halt（BLOCK 硬暂停）| L1-07 Supervisor | **L2-06** | IC-L2-08 → L2-01 立即 HALTED ≤ 100ms |
| **IC-17** user_intervene | L1-10 UI（经 L1-09 事件总线） | **L2-01** / **L2-02** | panic/resume → L2-01；authorize/clarify → L2-02 |

### 14.2 作为调用方（发起外部 IC）

| 外部 IC | 去往 L1 | 发起 L2 | 触发条件 |
|---|---|---|---|
| **IC-01** request_state_transition | L1-02（但执行在本 L1 内由 L2-03 完成） | **L2-03** 通过 IC-L2-02 接 L2-02 的请求 | 决策 = state_transition |
| **IC-04** invoke_skill | L1-05 | **L2-02** | 决策 = invoke_skill |
| **IC-05** delegate_subagent | L1-05 | **L2-02** | 决策 = delegate_subagent |
| **IC-06** kb_read | L1-06 | **L2-02** | KB 注入阶段（每 tick 前置）+ 决策 = kb_read |
| **IC-07** kb_write_session | L1-06 | **L2-02** | 决策 = kb_write |
| **IC-09** append_event | L1-09 事件总线 | **L2-05** | 每次审计（IC-L2-05/06/07/09 触发）|
| **IC-11** process_content | L1-08 | **L2-02** | 决策 = process_content |

### 14.3 对外 IC 承担矩阵总览

```
外部 IC 矩阵（L1-01 涉及的 IC × 内部 L2）:

             │ L2-01 │ L2-02 │ L2-03 │ L2-04 │ L2-05 │ L2-06 │
─────────────┼───────┼───────┼───────┼───────┼───────┼───────┤
IC-01 state  │       │   →   │  ⭐   │       │       │       │
IC-04 skill  │       │  ⭐   │       │       │       │       │
IC-05 subag  │       │  ⭐   │       │       │       │       │
IC-06 kb_r   │       │  ⭐   │       │       │       │       │
IC-07 kb_w   │       │  ⭐   │       │       │       │       │
IC-09 event  │       │       │       │       │  ⭐   │       │
IC-11 content│       │  ⭐   │       │       │       │       │
IC-13 sugg   │       │   ←   │       │       │   ←   │  ⭐   │
IC-14 rollbk │       │   ←   │       │       │       │  ⭐   │
IC-15 halt   │   ←   │       │       │       │       │  ⭐   │
IC-17 user   │  ⭐   │  ⭐   │       │       │       │   ←   │

⭐ = 主要承担  ← = 被路由到  → = 发起调用但最终目标在别 L1
```

### 14.4 IC 实现验证要求（TDD 集成测试的源头之一）

对每条外部 IC，集成测试必验证：

- 调用发起时的字段完整性（参数 schema 齐全）
- 调用发起者身份（必须是上表指定的 L2）
- 返回值结构（schema）
- 超时处理
- 失败降级

例如 IC-15 request_hard_halt 的集成测试：
- 从 L1-07 模拟发起 IC-15 → 验证 L2-06 接收 → IC-L2-08 → L2-01 HALTED 状态
- 全链路 ≤ 100ms
- 过程中每跳有 IC-L2-05 审计

---

## 15. 本 L1 retro 位点

本节为 L1-01 **独立实现完成后**的复盘模板位。待 L1-01 所有 L2 实现 + 集成测试通过后，按以下 11 项写 retro。

### 15.1 retro 11 项模板（本 L1 初始化填好）

| # | 项 | 初始化内容（L1-01 PRD 层的自述） |
|---|---|---|
| 1 | **DoD diff** | scope §5.1.6 必须 6 条 + prd §X.6 每 L2 必须 ≈ 45 条；实现时逐条勾检 |
| 2 | **路线偏差** | L1-01 无路线（本身是路线的核心），偏差看 prd 和 scope 的 consistency |
| 3 | **纠偏次数** | L0-L3：实现中每次回头改 prd（因 L2 定义不一致）算纠偏 |
| 4 | **Verifier FAIL** | TDD 阶段，每个 L2 的负向测试 N1-N9 是否都触发 |
| 5 | **用户打断** | 本 L1 独立实现时记录用户介入次数 |
| 6 | **耗时 vs 估算** | prd 撰写 7 轮（实际）vs 预估 8 轮（M4）|
| 7 | **新发现的 trap** | 本 L1 实现时踩的新坑 → 晋升到 Global KB |
| 8 | **新发现的有效组合** | 实现本 L1 时发现的好的 skill 组合 → 晋升 KB |
| 9 | **进化建议** | L1-01 下一版本（v1.1+）改进建议 |
| 10 | **下次推荐** | 实现 L1-02 至 L1-10 时从本 L1 经验借鉴什么 |
| 11 | **artifact 清单** | 本 L1 实现交付的所有代码/文档/测试文件列表 |

### 15.2 retro 产出要求

- 路径：`docs/prd/L1-01主 Agent 决策循环/retro.md`
- 触发时机：L1-01 独立集成测试全绿
- 审计：retro 本身也是一次审计 entry（以 `L1-01:retro` 事件 type 落事件总线）

---

## 15. 本 L1 retro 位点

> ⏸ 待 L2 全部完成后撰写。将记录：
> - L2 切分回溯（6 个是否合理？事后看合并/拆分倾向？）
> - 新 L2-06 价值评估（加之后真的变清楚了吗？）
> - 9 业务流是否真覆盖所有运行时场景
> - 10 IC-L2 契约是否稳定（有无后续需要新增/修改）
> - 本 L1 独立实现遇到的边界纠纷（哪些边界没说清）

---

## 附录 A · 术语（L1-01 本地）

| 术语 | 含义 |
|---|---|
| **tick** | 一次决策心跳，由 L2-01 触发 |
| **触发源** | event / proactive / periodic / hook / bootstrap 5 种 |
| **去抖 (debounce)** | 短时间内多次触发合并为一次 tick |
| **优先级仲裁** | 多源同时触发时按优先级调度 |
| **健康心跳 watchdog** | L2-01 监控 tick 是否及时响应（≤ 30s） |
| **5 纪律拷问** | 规划 / 质量 / 拆解 / 检验 / 交付（PM-11） |
| **决策树分派** | 按决策类型路由（调 skill / 工具 / KB / 子 Agent / 状态转换等） |
| **mini SM** | task chain 的 mini state machine |
| **审计 entry** | 一次审计留痕的结构化记录 |
| **supervisor 建议 4 级** | INFO / SUGG / WARN / BLOCK |
| **bootstrap tick** | 跨 session 恢复后的首次特殊 tick |

---

## 附录 B · businessFlow BF 映射

| L2 | 聚合的 BF |
|---|---|
| L2-01 | BF-L3-12 loop 触发机制 |
| L2-02 | BF-L3-01 决策心跳 tick 流 + BF-L3-14 决策选择 |
| L2-03 | BF-L3-13 阶段切换触发 |
| L2-04 | BF-L3-15 任务链执行 |
| L2-05 | BF-L3-01 step⑥ 决策留痕 + BF-X-01 决策心跳横切 |
| L2-06 | BF-X-02 监督观察流（消费方） + scope §5.1.6 必须义务"响应 BLOCK/WARN" |

---

## 附录 C · IC-L2 字段示例（R3+ 各 L2 精确化后完整给出）

> 本轮仅 IC-L2-01 示例。其他 IC 在对应 L2 详细定义时给出完整 schema + 例子。

```yaml
# IC-L2-01 on_tick 调用示例
call:
  method: on_tick
  caller: L2-01
  callee: L2-02
  params:
    trigger_source: "event"      # event | proactive | periodic | hook | bootstrap
    event_ref: "evt_2026042012345"
    priority: 7                   # 0-10, higher = more urgent
    ts: "2026-04-20T10:30:15Z"
    bootstrap: false              # true only for system_resumed first tick
  expected_return:
    tick_result:
      decision: "invoke_skill"
      skill_name: "writing-plans"
      reason: "当前 state=PLAN, 需要生成 WBS..."
      audit_id: "audit_2026042012350"
```

---

*— L1-01 PRD v0.1 骨架轮完 · 等待 R3 推进 L2-01 详细定义 —*
