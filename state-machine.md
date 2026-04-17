# state-machine.md

**版本**: v1.0 (2026-04-16)
**Status**: DRAFT（Phase 4 产出）
**Readers**: 主 skill (Phase 5) / Supervisor (Phase 6) / Verifier (Phase 6)

> 本文档把 `flow-catalog.md` 六条路线的调度序列**结构化为任务级状态机**：所有状态 + 允许转移 + guard + retry ladder 集成 + save-session re-entry 协议。主 skill 在 Phase 5 里以本文档为状态转换的唯一真相源。

---

## § 1 顶层状态列表

**完整状态枚举（20 个）= 核心状态 15 个 + 路线专有状态 5 个**。整套 enum 在任务全生命周期封闭，`current_state` 字段只能取下列值之一。

- **核心骨架状态（12 个）**：`INIT` / `CLARIFY` / `ROUTE_SELECT` / `PLAN` / `CHECKPOINT_SAVE` / `IMPL` / `MID_CHECKPOINT` / `MID_RETRO` / `VERIFY` / `SANTA_LOOP` / `COMMIT` / `RETRO_CLOSE`
- **终态（3 个）**：`CLOSED` / `PAUSED_ESCALATED` / `ABORTED`
- **路线专有状态（5 个，见 § 1.2）**：`UI_SCREENSHOT`（D） / `NODE_UNIT_TEST`（E） / `GRAPH_COMPILE`（E） / `RESEARCH`（F） / `DECISION_LOG`（F）

### 1.1 核心状态（15 个）

| 代号 | 名称 | 所属阶段 | 语义 |
|---|---|---|---|
| `INIT` | 初始化 | bootstrap | `/harnessFlow` 拉起，task_id 分配 + CLAUDE.md 读取 + goal 初始为空 |
| `CLARIFY` | 澄清中 | @clarify | brainstorming 轮询 + 任务三维打标（size/type/risk） |
| `ROUTE_SELECT` | 路由选择 | @clarify | 主 skill 查 `routing-matrix` + 呈现 top-2 + 等用户 pick |
| `PLAN` | 计划中 | @plan | prp-prd（仅 C）+ prp-plan + 生成 DoD 表达式 |
| `CHECKPOINT_SAVE` | 计划 checkpoint | @plan | save-session 快照，goal_anchor 写入 CLAUDE.md |
| `IMPL` | 实施中 | @impl | prp-implement + code-reviewer + Supervisor sidecar 监听 |
| `MID_CHECKPOINT` | 实施 checkpoint | @impl | 二次 save-session（C/E 强制；B/D 可选） |
| `MID_RETRO` | 阶段 retro | @impl | 仅 XL C 任务强制；其他路线跳过 |
| `VERIFY` | 收口验证 | @verify | harnessFlow:verifier 执行 DoD eval（F 路线也过 VERIFY） |
| `SANTA_LOOP` | 自动纠偏迭代 | @verify | Verifier FAIL → santa-loop 迭代；≤ 4 级 retry ladder |
| `COMMIT` | 提交 | @commit | prp-commit + prp-pr |
| `RETRO_CLOSE` | 收口 retro | @retro | 强制 11 项 retro + failure-archive 写入 |
| `CLOSED` | 已关闭 | terminal | Stop hook 兜底校验通过，task 归档 |
| `PAUSED_ESCALATED` | 暂停等用户 | terminal（软） | 红线触发 / L3 纠偏 / DRIFT_CRITICAL；等用户决策 |
| `ABORTED` | 任务中止 | terminal（硬） | 用户主动放弃 / 不可恢复失败 |

**终态**：`CLOSED` / `ABORTED`。
**软终态**：`PAUSED_ESCALATED`（可由用户恢复到任意前置状态 + 新决策触发）。

### 1.2 路线专有状态（5 个）

| 代号 | 路线 | 插入位置 | 语义 | 触发边 |
|---|---|---|---|---|
| `UI_SCREENSHOT` | D | `IMPL → UI_SCREENSHOT → VERIFY` | playwright 起 vite + 访问页面 + 截图，screenshot 作为硬证据 | E9b / E9b2 |
| `NODE_UNIT_TEST` | E | `IMPL` 内循环 | 每节点 TDD 单测通过 | E-loop-1 |
| `GRAPH_COMPILE` | E | `IMPL` 内循环 | graph 级 compile + 环路检查 | E-loop-2 |
| `RESEARCH` | F | `CLARIFY → RESEARCH → DECISION_LOG` | Explore + WebSearch + docs-lookup 并行 | F1 |
| `DECISION_LOG` | F | `RESEARCH → DECISION_LOG → VERIFY` | 决策 md 落盘，行数 / 选项数 / 决策数达标 | F2 |

---

## § 2 状态转移图

### 2.1 主路径（ASCII，C 路线完整版）

```
                                    ┌──────────┐
                                    │   INIT   │
                                    └────┬─────┘
                                         │ user runs /harnessFlow
                                         ▼
                                    ┌──────────┐
                                    │ CLARIFY  │ ← SP:brainstorming 轮询
                                    └────┬─────┘
                                         │ clarify 轮数 ≥ 1 且 三维标签完整
                                         ▼
                                   ┌──────────────┐
                                   │ ROUTE_SELECT │ ← 查 routing-matrix
                                   └──────┬───────┘
                                          │ user picks route / 主 skill 自动选
                                          ▼
                                    ┌──────────┐
                    ┌───────────────│   PLAN   │────────────┐
                    │               └─────┬────┘            │
                    │                     │ plan ✓          │ (B/D 轻 plan)
                    │                     ▼                 │
                    │             ┌──────────────────┐      │
                    │             │ CHECKPOINT_SAVE  │      │
                    │             └────────┬─────────┘      │
                    │                      │ save-session ✓ │
                    │                      ▼                │
                    │                 ┌──────────┐          │
                    └──────→ resume ──│   IMPL   │←─────────┘
                                      └─────┬────┘
                                            │ Supervisor sidecar 监听
                                            │ (INFO/WARN/BLOCK)
                                            ▼
                                    ┌──────────────────┐
                       ┌───────────→│ MID_CHECKPOINT   │ (C/E 强制)
                       │            └────────┬─────────┘
                       │                     │
                       │                     ▼
                       │              ┌────────────┐
                       │              │ MID_RETRO  │ (XL C only)
                       │              └─────┬──────┘
                       │                    │
                       │                    ▼
                       │                ┌────────┐
                       │  ┌────PASS────│ VERIFY │  ← harnessFlow:verifier
                       │  │            └────┬───┘    (DoD.eval())
                       │  │                 │ FAIL
                       │  │                 ▼
                       │  │         ┌──────────────┐
                       └──┼─────────│  SANTA_LOOP  │ ← ≤ 4 级 retry
                          │         └──────┬───────┘
                          │                │ ladder 封顶 / DoD 仍 FAIL
                          │                ▼
                          │       ┌──────────────────┐
                          │       │ PAUSED_ESCALATED │ (L3)
                          │       └──────────────────┘
                          ▼
                      ┌────────┐
                      │ COMMIT │ ← prp-commit + prp-pr
                      └───┬────┘
                          ▼
                   ┌────────────┐
                   │ RETRO_CLOSE│ ← 强制 11 项
                   └─────┬──────┘
                         ▼
                    ┌──────────┐
                    │  CLOSED  │ ← Stop hook 兜底 gate
                    └──────────┘
```

### 2.2 非主路径（异常/软终态分支）

```
(任意状态)
    │
    ├── user /halt           → ABORTED
    ├── Supervisor BLOCK     → PAUSED_ESCALATED
    ├── IRREVERSIBLE_HALT    → PAUSED_ESCALATED（强制拦截）
    ├── DRIFT_CRITICAL       → PAUSED_ESCALATED（等用户切目标）
    └── context 临界         → PAUSED_ESCALATED（L2 → L3 escalate）
```

`PAUSED_ESCALATED` → 用户决策后可回到：`CLARIFY`（重新分诊）/ `ROUTE_SELECT`（切路线）/ `IMPL`（纠偏重做）/ `VERIFY`（修 DoD）之一，绝不会直接进 CLOSED。

---

## § 3 转移边表（含 guard / side effects / 回滚）

### 3.1 主路径转移边

| 边号 | from | to | trigger | guard | side effects | 允许回滚 |
|---|---|---|---|---|---|---|
| E1 | `INIT` | `CLARIFY` | user 调 `/harnessFlow` | `task_id` 分配成功 | 写 task-board 初始 entry | 否（中止即 ABORTED）|
| E2 | `CLARIFY` | `ROUTE_SELECT` | brainstorming 轮 ≥ 1 且 `(size, type, risk)` 三维完整 | 三维非空 | 三维标签写 task-board | 可回（clarify 重开） |
| E3 | `ROUTE_SELECT` | `PLAN` | user pick 路线 or 主 skill 自动选 top-1 | routing-matrix 查表成功 + 非 `-` cell | 写 `route_id` 到 task-board | 可回（重选路线） |
| E4 | `PLAN` | `CHECKPOINT_SAVE` | `prp-plan` exit OK | plan 文件存在 + line ≥ 20 | 写 `plan_path` | 否 |
| E5 | `CHECKPOINT_SAVE` | `IMPL` | `save-session` exit OK | session_id 写回 task-board | Supervisor sidecar 拉起 | 否（checkpoint 不可 undo） |
| E6 | `IMPL` | `MID_CHECKPOINT` | C/E 路线 + 实施行数 > 500 | 增量 diff 可生成 | 二次 save-session | 否 |
| E7 | `MID_CHECKPOINT` | `MID_RETRO` | size == XL 且 route == C | XL 条件 | mid-retro 写 `.md` | 否 |
| E8 | `MID_RETRO` | `VERIFY` | mid-retro 写完 | retro 文件存在 | 进入收口判定 | 否 |
| E9a | `IMPL` | `VERIFY` | A/B 路线 impl OK（跳过 MID_CHECKPOINT） | impl exit OK + `route_id ∈ {A, B}` | - | 否 |
| E9b | `IMPL` | `UI_SCREENSHOT` | D 路线 impl OK | `route_id == D` + playwright 就绪 | vite_started 校验 | 否 |
| E9b2 | `UI_SCREENSHOT` | `VERIFY` | screenshot 产出 | `screenshot_has_content == True` | 写 `artifacts[]` screenshot entry | 同状态 L0 retry（最多 1 次） |
| E9c | `DECISION_LOG` | `VERIFY` | F 路线决策 log 完成 | `file_exists(decision_log) + wc_lines ≥ 200` | - | 否 |
| E10 | `VERIFY` | `COMMIT` | DoD.eval() == True | verifier_report.pass_all == True | `verifier_report` 写 task-board | 否 |
| E11 | `VERIFY` | `SANTA_LOOP` | DoD.eval() == False | `overall == "FAIL"` + 红线空 + `route_id != A` + `try_recover` 未 escalate | 写 `retries[]` entry | 否 |
| E12 | `SANTA_LOOP` | `IMPL` | santa-loop 产出修复 patch | `try_recover` 返回 retry_at | 写 `retries[]` entry | 否 |
| E13 | `SANTA_LOOP` | `PAUSED_ESCALATED` | ladder 耗尽 | `try_recover` 返回 escalate（§ 4.3） | 写 `red_lines[]` `L3_LADDER_EXHAUSTED` | 否 |
| E14 | `COMMIT` | `RETRO_CLOSE` | `prp-commit` + `prp-pr` OK | commit SHA 生成 | `commit_sha` 写 task-board | 否 |
| E15 | `RETRO_CLOSE` | `CLOSED` | 11 项 retro 完整 + failure-archive 写回完成 | retro 文件 + archive ref | Stop hook 兜底检查 `verifier_report` 存在 | 否 |

### 3.2 异常边

| 边号 | from | to | trigger | guard | side effects | 回滚路径 |
|---|---|---|---|---|---|---|
| X1 | 任意非终态 | `PAUSED_ESCALATED` | Supervisor BLOCK / red_line | red_line.code ∈ {DRIFT_CRITICAL, DOD_GAP_ALERT, IRREVERSIBLE_HALT} | 写 `red_lines[]` + pause session | 用户决策后回 CLARIFY / ROUTE_SELECT / IMPL / VERIFY |
| X2 | 任意非终态 | `ABORTED` | user `/halt` 或 不可恢复错误 | 用户显式 / error_class == fatal | 写 `abort_reason` | 无（终态） |
| X3 | `CLARIFY` | `ROUTE_SELECT` | 三维不完整超 5 轮 | clarify_rounds > 5 | Supervisor INFO "over-clarify" | 可（用户强制继续） |
| X4 | `IMPL` | `IMPL` | code-reviewer critical FAIL | review_verdict == "CRITICAL" | retry_count++（L1） | 同状态 retry |
| X5 | `PAUSED_ESCALATED` | `CLARIFY` / `ROUTE_SELECT` / `IMPL` / `VERIFY` | 用户决策后 resume | resume_decision 非空 | task-board `route_changes[]` append | 否 |
| X6 | `VERIFY` | `PAUSED_ESCALATED` | A 路线 FAIL（无 santa-loop） | `route_id == A` + `verifier_report.overall == "FAIL"` | 写 `red_lines[]` entry `A_ROUTE_FAIL` | 否（等用户决策后走 X5） |
| X7 | `VERIFY` | `PAUSED_ESCALATED` | FAIL + 有红线（优先于 retry）| `overall == "FAIL" AND red_lines_detected != []` | 写 `red_lines[]` | 否 |
| X8 | `VERIFY` | `PAUSED_ESCALATED` | INSUFFICIENT_EVIDENCE 连续 ≥ 2 次 | `insufficient_evidence_count ≥ 2` | 写 `red_lines[]` `INSUFFICIENT_EVIDENCE_LOOP` | 否 |

### 3.3 路线专有转移边（D/E/F 补丁）

| 边号 | from | to | trigger | guard | side effects | 允许回滚 |
|---|---|---|---|---|---|---|
| E-loop-1 | `IMPL` | `NODE_UNIT_TEST` | E 路线写完一个节点 | `route_id == E` + 节点 diff 可生成 | 拉 pytest 单节点 | 同状态 L0/L1 retry |
| E-loop-2 | `NODE_UNIT_TEST` | `GRAPH_COMPILE` | 节点单测通过 | `pytest_exit_code == 0` | graph 级 compile | 回 IMPL 修节点 |
| E-loop-3 | `GRAPH_COMPILE` | `IMPL` | 还有未完成节点 | `graph_compile_success == True` + 节点队列非空 | 下一个节点 | - |
| E-loop-4 | `GRAPH_COMPILE` | `MID_CHECKPOINT` | 所有节点完成 | 节点队列空 + 无环路 | save-session | 否 |
| F1 | `CLARIFY` | `RESEARCH` | F 路线三维打标完成 | `route_id == F` | Explore + WebSearch 拉起 | 可回 CLARIFY |
| F2 | `RESEARCH` | `DECISION_LOG` | research 信息收齐 | 检索覆盖率 ≥ plan 列出的维度 | 写 decision md | 回 RESEARCH 补调研 |

**F 路线说明**：F 路线**仍走 VERIFY**（不写代码不代表不收口）。VERIFY 评估 DoD = decision log 存在 + 行数 + 选项数 + 决策结论；PASS 后跳过 COMMIT（无代码可提交）直接进 RETRO_CLOSE。对应边 F3：`VERIFY → RETRO_CLOSE`（guard: `route_id == F + verifier_report.pass_all == True`）。

---

## § 4 Retry ladder 集成点

对齐 `method3.md § 5.3` 四级 retry ladder；**ladder 不是单一线性阶梯，而是 `state × error_class` 的二维映射**——不是每个状态都允许所有级别。

### 4.1 Ladder 级别定义（级别本身与状态无关）

| 级别 | 动作 | 典型开销 |
|---|---|---|
| **L0 retry-same** | 同步 retry，不改参数 | < 5 sec，零 token |
| **L1 retry-tweaked** | 改 prompt / 缩 scope / 换 subagent 参数 | 数秒，~5% token 开销 |
| **L2 switch-skill** | 换 skill（例如 `ECC:code-reviewer → gstack:review`） | 10-30 sec，新 subagent token |
| **L3 escalate-user** | 转 `PAUSED_ESCALATED`，等用户决策 | 阻塞 |

### 4.2 LADDER_MATRIX（state × error_class → 允许级别序列）

```python
# key: (state, error_class) → value: ordered list of allowed levels
LADDER_MATRIX = {
    # 瞬态错误：全阶梯
    ("IMPL", "tool_transient"):        ["L0", "L1", "L2", "L3"],
    ("VERIFY", "primitive_transient"): ["L0", "L1", "L3"],   # primitive 只允许两轮 tweak
    ("UI_SCREENSHOT", "timeout"):      ["L0", "L3"],         # playwright 等待或放弃
    # 语义错误：跳过 L0（同参 retry 无意义）
    ("IMPL", "code_review_critical"):  ["L1", "L2", "L3"],
    ("VERIFY", "dod_fail"):            ["L1", "L2", "L3"],   # 进 SANTA_LOOP 再 retry
    ("SANTA_LOOP", "fail"):            ["L1", "L2", "L3"],
    # 路线硬规则
    ("VERIFY", "a_route_fail"):        ["L3"],               # A 路线禁 retry
    ("*", "red_line"):                 ["L3"],               # 红线一律 escalate
    ("*", "irreversible_halt"):        ["L3"],
    ("*", "drift_critical"):           ["L3"],
}
LADDER_CAP = {"L0": 2, "L1": 2, "L2": 1, "L3": 0}
```

### 4.3 State-aware 算法

```python
def try_recover(state, err_class, retries_list):
    """
    retries_list: task-board.retries[] 列表，每 entry {level, state, trigger, outcome, timestamp}
    count_by_level: 按 level 聚合当前累计次数
    """
    allowed = LADDER_MATRIX.get((state, err_class)) \
              or LADDER_MATRIX.get(("*", err_class)) \
              or ["L3"]  # 未登记组合 → 保守 escalate
    counts = count_by_level(retries_list)  # {"L0": 2, "L1": 1, ...}
    for level in allowed:
        if counts.get(level, 0) < LADDER_CAP[level]:
            return retry_at(level, state)
    return transition(state, "PAUSED_ESCALATED",
                      reason=f"ladder_exhausted:{state}:{err_class}")

def count_by_level(retries_list):
    from collections import Counter
    return Counter(r["level"] for r in retries_list)
```

**counter 归一化**：`retries[]` 以**列表形态**为真相源（见 task-board §1.2）；所有"cap 检查"通过 `count_by_level` 聚合，不在任务级保留 `L0_count` / `L1_count` 独立字段。这避免写入方多处维护计数器导致漂移。

### 4.4 E13 触发条件（统一语义）

`SANTA_LOOP → PAUSED_ESCALATED` 的触发 = `try_recover` 返回 escalate（即 allowed 列表中所有级别都已触顶），不再用模糊的"retry_count ≥ ladder cap"。

---

## § 5 save-session / resume-session re-entry 协议

### 5.1 保存时（进入 `CHECKPOINT_SAVE` / `MID_CHECKPOINT`）

**必写字段**（task-board.json + session snapshot 双写）：
- `task_id` / `session_id`
- `current_state`（枚举 § 1）
- `stage`（@clarify / @plan / @impl / ...）
- `route_id`
- `goal_anchor`（CLAUDE.md 中的不可变 block hash）
- `dod_expression`（字符串）
- `artifacts[]`（已产出）
- `retries[]` 累计
- `routing_events[]` 累计
- `timestamp` UTC

### 5.2 恢复时（resume-session 入口）

主 skill 执行以下顺序（guard）：
1. 读 `session_id` → 加载 snapshot
2. 读 `task_id` → 加载 task-board.json
3. 比较 `goal_anchor` 与 CLAUDE.md 当前 block：**diff != 0 → 必须 PAUSED_ESCALATED + 等用户确认**
4. 根据 `current_state` 恢复：
   - `INIT` / `CLARIFY` / `ROUTE_SELECT`：重新拉 brainstorming + routing-matrix
   - `PLAN` / `CHECKPOINT_SAVE`：直接进 `IMPL`（已有 plan）
   - `IMPL` / `MID_CHECKPOINT`：重拉 Supervisor sidecar + 继续 impl
   - `VERIFY` / `SANTA_LOOP`：重跑 verifier（不信旧 report，物理重算）
   - `COMMIT` / `RETRO_CLOSE` / `CLOSED`：guard 检测到应进 terminal 而未 terminal → Stop hook 补扫
   - `PAUSED_ESCALATED`：等用户决策才能继续
5. 记录 `cross_session_ids[]` append 当前 session_id

### 5.3 invariants（resume 必须一致）

| 字段 | 规则 | 不一致时 |
|---|---|---|
| `task_id` | 必须相同 | 错误任务，转 ABORTED |
| `goal_anchor` hash | 必须相同（CLAUDE.md 对应 block） | PAUSED_ESCALATED + 等用户手动对齐 |
| `route_id` | 必须相同（除非用户显式切路线） | 记 `route_changes[]` + audit |
| `dod_expression` | 必须相同（锁定后不可改） | PAUSED_ESCALATED + L3 red_line |

**goal drift 兜底**（method3 § 5.2 DRIFT_CRITICAL）：resume 时 goal_anchor diff 检测是最强保护；但运行时同样需要监控，否则单 session 内悄悄改 CLAUDE.md block 会绕过 resume-guard。

### 5.4 运行时 drift 监控（单 session 内）

在**非 resume 时机**也需 hook：
- **PostToolUse hook**（Phase 6）：每次 `Edit` / `Write` 结束后，若文件是 `CLAUDE.md`，重算 `goal_anchor.hash` → 与 task-board 的 hash 比较
- diff != 0 → Supervisor 写 `BLOCK + DRIFT_CRITICAL` → 任意非终态 → `PAUSED_ESCALATED`（走 X1）
- 降噪：同一 session 内 5 min 去重（对应 harnessFlow.md § 7.7 WARN 去重逻辑）

---

## § 6 Supervisor INFO/WARN/BLOCK → 状态转移

Supervisor（harnessFlow.md § 4.3）产出事件分三级：

| 事件 | 状态转移 | 主 skill 行为 |
|---|---|---|
| **INFO** | 不转移 | 写 task-board `supervisor_interventions[]`，继续当前状态 |
| **WARN** | 不转移（达阈值前） | 写 entry + 计数 `warn_counter++`；超 `warn_downgrade_threshold_per_task`（routing-matrix § 5.1 MVP=10）后新 WARN 自动降 INFO |
| **BLOCK + 红线** | 任意非终态 → `PAUSED_ESCALATED` | 写 `red_lines[]` + pause session + 提示用户决策 |
| **BLOCK + 非红线** | 同状态 retry（L1/L2） | 等 retry ladder 自然 escalate |

**WARN 降级避免用户疲劳**：harnessFlow.md § 7.7 同类 WARN 5min 去重 + 累计超阈值自动降 INFO。

---

## § 7 Verifier PASS/FAIL → 下一状态决策树

**决策优先级（自上而下，先匹配先执行，不回退）**：

```
VERIFY 状态结束，读 verifier_report：
│
├── P0 [红线优先]: red_lines_detected != []
│      → PAUSED_ESCALATED（走 X1 / X7；无论 overall 是 PASS 还是 FAIL）
│
├── P1 [PASS path]: overall == "PASS"
│      → E10: COMMIT
│
├── P2 [FAIL path]: overall == "FAIL"
│      ├── route_id == A           → X6: PAUSED_ESCALATED（A 路线无 santa-loop）
│      ├── try_recover 未 escalate → E11: SANTA_LOOP（进 retry ladder）
│      └── try_recover 已 escalate → E13: PAUSED_ESCALATED（ladder 耗尽）
│
└── P3 [INSUFFICIENT_EVIDENCE]: overall == "INSUFFICIENT_EVIDENCE"
       ├── insufficient_evidence_count < 2
       │      → 回 IMPL + red_lines[] append DOD_GAP_ALERT + counter++
       └── insufficient_evidence_count ≥ 2
              → X8: PAUSED_ESCALATED（避免 IMPL↔VERIFY 死循环，等用户修 DoD 表达式或补证据）
```

**关键规则**：
1. **P0 最高优先**：PASS 或 FAIL 只要有红线，一律进 `PAUSED_ESCALATED`（防 `(True AND red_line_exists())` 绕过）
2. **A 路线 carve-out**：A 路线 FAIL 不走 santa-loop（size == XS 的小任务无纠偏必要），直接 escalate
3. **INSUFFICIENT_EVIDENCE cap**：同任务累计 ≥ 2 次 → escalate（DoD 表达式或证据机制本身有问题，continuing retry 解不了）
4. **counter 归属**：`insufficient_evidence_count` 存 task-board 度量字段（不在 retries[] 里）

---

## § 8 6 路线状态机差异

### 8.1 路线 A（零 PRP）— 简化版

状态子集：`INIT → CLARIFY → ROUTE_SELECT → IMPL → VERIFY → COMMIT → CLOSED`

- 省 `PLAN` / `CHECKPOINT_SAVE` / `MID_CHECKPOINT` / `MID_RETRO` / `SANTA_LOOP` / `RETRO_CLOSE`
- Supervisor 仍挂（低频事件）
- Verifier **强制**（DoD = `pytest_exit_code == 0` + `diff_lines_net < 50`）
- **无 santa-loop**：FAIL → X6 → `PAUSED_ESCALATED`（等用户决策）
- retro 可跳过（delivery-checklist § 1 允许 `retro_link = null`）

### 8.2 路线 B（轻 PRP）— 中等版

状态子集：主路径去掉 `MID_RETRO`；`MID_CHECKPOINT` 为 optional（>500 行改动时触发）

### 8.3 路线 C（全 PRP）— 完整版

如 § 2.1 主图；**MVP 主路线**，所有状态全开。

**C-lite 变体**（routing-matrix § 2.2 `C-lite` cell）：
- 状态子集与 C 相同，但 `MID_RETRO` 变为 **optional**（仅当 `size == XL` 触发；`L` / `C-lite` 任务跳过）
- `CHECKPOINT_SAVE` 仍强制（计划 checkpoint 不可省）
- Verifier / retro 与 C 同等严格

### 8.4 路线 D（UI 视觉专线）

加 `UI_SCREENSHOT` 状态插在 `IMPL` 与 `VERIFY` 之间（screenshot 作为 DoD 硬证据的收口前置）：

```
IMPL → UI_SCREENSHOT → VERIFY
         ↓ (screenshot 空/全白/超时)
         retry L0 / 等 playwright_wait_for
```

### 8.5 路线 E（agent graph 专线）

加 `NODE_UNIT_TEST` + `GRAPH_COMPILE` 两个状态在 `IMPL` 内部循环（每节点独立 TDD + graph 级 compile）：

```
IMPL ⇄ NODE_UNIT_TEST ⇄ GRAPH_COMPILE → MID_CHECKPOINT
```

### 8.6 路线 F（研究探索）

状态子集：`INIT → CLARIFY → RESEARCH → DECISION_LOG → VERIFY → RETRO_CLOSE → CLOSED`

- 无 `PLAN` / `IMPL` / `SANTA_LOOP` / `COMMIT`（F 不写代码，无需提交）
- 新状态 `RESEARCH`（含 Explore subagent + WebSearch + docs-lookup 并行）
- 新状态 `DECISION_LOG`（写决策 md）
- **保留 VERIFY**：F 不写代码 ≠ 不收口。Verifier 评估 DoD = 决策 md 存在 + 行数 ≥ 200 + ≥ 2 个选项 + 1 个决策结论
- `VERIFY PASS → RETRO_CLOSE`（F3 边；跳过 COMMIT，因无代码可提交）
- `VERIFY FAIL`：走 P2 分支，但 F 无 santa-loop（等价 A 路线处理）→ PAUSED_ESCALATED

---

## § 9 实现契约（Phase 5/6 主 skill 遵循）

### 9.1 状态读写

- 读：主 skill 每步 tool call 前读 `task-board.current_state` 决定下一步
- 写：每次状态转移都写 task-board（append `state_history[]` entry），带 timestamp
- 持久化：`task-board.json` 每次写入后 fsync；resume 必读最新

### 9.2 guard 强制

- 任何转移必须通过 § 3 guard 检查；guard 失败 → INFO 给用户 + 停在当前状态
- 强 guard（不可绕过）：E5 `save-session` / E10 `verifier_report.pass_all` / E15 `retro + archive ref`

### 9.3 状态机单元测试（Phase 8 验证）

拿 3 个真任务回放：
- P20 视频出片：must 走 `INIT → CLARIFY → ROUTE_SELECT → PLAN → CHECKPOINT_SAVE → IMPL → MID_CHECKPOINT → VERIFY → COMMIT → RETRO_CLOSE → CLOSED` 全绿
- P20 假完成回放：must 在 `VERIFY` 拦下（DoD FAIL）→ `SANTA_LOOP` → 经 3 次 retry → `COMMIT` 绿
- goal drift 回放：resume 时 goal_anchor diff → `PAUSED_ESCALATED`

---

*本文档结构化 flow-catalog.md 调度序列为状态机。字段 schema 见 task-board-template.md；收口证据清单见 delivery-checklist.md；主 skill 按本文档状态转换逻辑 Phase 5 落地。*

*— v1.0 end —*
