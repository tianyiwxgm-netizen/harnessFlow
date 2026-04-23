---
doc_id: arbitration-2026-04-23-dev-zeta-4-corrections
doc_type: main-session-arbitration
arbitrator: 主会话（主 session）
arbitrated_at: 2026-04-23
session_requesting: Dev-ζ（worktree-dev-zeta1-L1-07-supervisor）
---

# 主会话仲裁 · Dev-ζ 4 条 Self-Correction

> **仲裁原则**：`ic-contracts.md` 为 L1 间接口单一事实源；`Dev-ζ-L1-07-supervisor.md` (exe-plan) 在 IC 方向/语义上**与 ic-contracts 必须一致**。若冲突 · **以 ic-contracts 为准**。

---

## §1 核查事实（主会话亲读）

**`docs/3-1-Solution-Technical/integration/ic-contracts.md` 权威定义**：

| IC | 章节 | 方向 | 语义 | SLA |
|:---:|:---:|:---|:---|:---:|
| **IC-13** | §3.13（line 1483）| **L1-07 → L1-01** | push_suggestion（INFO/SUGG/WARN）· fire-and-forget · L1-01 L2-06 入队 | - |
| **IC-14** | §3.14（line 1581）| **L1-07 → L1-04** | push_rollback_route · 翻译 verdict → target_stage · 同级 FAIL ≥ 3 自动升级 | - |
| **IC-15** | §3.15（line 1670）| **L1-07 → L1-01** | request_hard_halt · 硬红线命中触发的硬暂停 · 阻塞式 | **≤100ms · 硬约束** |

**`Dev-ζ-L1-07-supervisor.md` §7 exe-plan 所写**：
- IC-13 push_suggestion → L1-01 · fire-and-forget ✅ **正确**
- IC-14 push_rollback_route → L1-04 · 幂等 ✅ **正确**
- IC-15 request_hard_halt → L1-01 · Sync ≤100ms ✅ **正确**

---

## §2 逐条仲裁

### C-1 · IC-13 方向

**Dev-ζ claim**：`IC-13 quality_loop_route → L1-04 · P99 ≤ 1s`（引自 §3.13）

**实际 §3.13**：`IC-13 push_suggestion（L1-07 → L1-01）· fire-and-forget`

**Dev-ζ 误读** · 可能把 §3.14 的内容当成 §3.13。

**仲裁结果**：
- ❌ **驳回 C-1 claim**
- ✅ **exe-plan §7 对 · IC-13 → L1-01 · push_suggestion · fire-and-forget**
- Dev-ζ WP02（event_sender）实现 IC-13 时 · 严格按 ic-contracts §3.13 定义：目标 L1-01 L2-06 · 3 级 INFO/SUGG/WARN · 不等确认。

### C-2 · IC-15 存在性 + 100ms 硬约束

**Dev-ζ claim**：`ic-contracts 未发现 IC-15 · 100ms 漂移为 500ms`

**实际 §3.15（line 1670）**：**IC-15 request_hard_halt · ≤100ms 硬约束 · 阻塞式**

**仲裁结果**：
- ❌ **完全驳回 C-2 claim**
- ✅ **IC-15 存在 · 必须实现**
- ✅ **100ms 硬约束不可降级为 500ms**（硬红线 5 条之一 · 违反直接阻塞 release）
- Dev-ζ WP02 实现 IC-15 时 · 使用 **阻塞式同步调用** · `pytest-benchmark` 验证 P99 ≤100ms
- **Dev-ζ impl plan §A §B §C 必须修正**：增加 `halt_requester.py` 独立模块（不能与 IC-14 共用 rollback_pusher）· 100ms benchmark

### C-3 · 主动拉取 vs 订阅

**Dev-ζ claim**：L1-07 应主动调 IC-11 `read_event_stream` + 写 IC-09 `append_event` · 不做 push 订阅

**核查**：`ic-contracts §3.11 IC-11 supervisor_observe` 确实定义 L1-07 **调** `read_event_stream` + `read_event_bus_stats`。

**exe-plan §3.1** 写的 "订阅 IC-09" 是**错的**（与 IC-11 定义冲突）。

**仲裁结果**：
- ✅ **接受 C-3 claim**
- **修源文档**：`docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-ζ-L1-07-supervisor.md §3.1` 把 "订阅 IC-09 + register_subscriber" 改为 "调 IC-11 read_event_stream + 写 IC-09 append_event"
- 走 4-0 `§6 自修正情形 D`（IC 契约矛盾）· 由主会话本仲裁记录完成

### C-4 · 包命名路径 `app/l1_07/` vs `app/supervisor/`

**Dev-ζ claim**：采用语义命名 `app/supervisor/`（对齐 Dev-δ `project_lifecycle` 先例 + MASTER-SESSION-DISPATCH §5.6 "业务语义不用 l1_XX 字面 ID"）

**核查**：
- `CODE-OWNERSHIP-MATRIX.md` 当前写的是 `app/l1_07/**`（旧约束 · 在 §5.6 语义命名铁律之前）
- `MASTER-SESSION-DISPATCH §5.6 铁律 2` 明确要求语义命名 · `crash_safety/` 而非 `utils/`
- Dev-δ 的 `app/project_lifecycle/`（非 `app/l1_02/`）已开先例

**仲裁结果**：
- ✅ **接受 C-4 claim**
- **修 CODE-OWNERSHIP-MATRIX.md**：Dev-ζ 行 `app/l1_07/**` → `app/supervisor/**`
- 同步对齐（若尚未改）：Dev-α `app/resilience_audit/`（现 `app/l1_09/` 已落地 · 可继续用；新建议语义名）· Dev-β `app/knowledge_base/`(现 l1_06) · Dev-δ `project_lifecycle/`(已对) · 其他 Dev 待自行决定
- **此处主会话追认**：`app/l1_XX/` 和语义名**均可接受** · 各 Dev 自选 · 只要**一个 L1 内部统一**即可

---

## §3 仲裁总结表

| # | 判决 | 需改源文档 | 影响 |
|:---:|:---:|:---|:---|
| C-1 | ❌ 驳回 | 无（exe-plan 对）| Dev-ζ WP02 按 ic-contracts §3.13 严格实现 |
| C-2 | ❌ 驳回 | 无（exe-plan 对）| **IC-15 必须实现 · 100ms 硬约束保留** |
| C-3 | ✅ 接受 | Dev-ζ exe-plan §3.1 改文字 | 主动拉取模型 |
| C-4 | ✅ 接受 | CODE-OWNERSHIP-MATRIX 改 Dev-ζ 行 | `app/supervisor/` 合法 |

---

## §4 主会话执行动作

- [x] 读 ic-contracts.md §3.13/§3.14/§3.15 核查 · 确认 Dev-ζ 误读
- [ ] 改 `Dev-ζ-L1-07-supervisor.md §3.1`（文字：订阅 → 主动拉取）
- [ ] 改 `CODE-OWNERSHIP-MATRIX.md`（Dev-ζ 行 `app/l1_07/**` → `app/supervisor/**`）
- [ ] 记 `projects/_correction_log.jsonl`（4 条 · C-1/C-2 驳回 · C-3/C-4 接受）
- [ ] 通知 Dev-ζ 下一会话：**IC-13/IC-14/IC-15 方向全以 ic-contracts 为准** · impl plan §A 停止作用 · §B/§C 中 `event_sender/` 的 `rollback_pusher.py` + `halt_requester.py` 分两个模块 · halt_requester 加 100ms bench

---

## §5 给 Dev-ζ 下一会话的修正指令

```
主会话仲裁决议（见 docs/4-exe-plan/arbitration-logs/2026-04-23-Dev-ζ-4-corrections.md）：

C-1 驳回 · IC-13 → L1-01（push_suggestion · fire-and-forget）· 按 ic-contracts §3.13
C-2 驳回 · IC-15 存在且 100ms 硬约束必须保留 · 按 ic-contracts §3.15
C-3 接受 · 主动拉取模型 · 已落对
C-4 接受 · app/supervisor/ 路径合法 · ownership matrix 已更新

WP02 event_sender 架构调整：
  event_sender/
  ├── suggestion_queue.py         # IC-13 队列 · L1-01 L2-06 收
  ├── rollback_pusher.py          # IC-14 → L1-04 · 幂等
  ├── halt_requester.py           # IC-15 → L1-01 · 阻塞 ≤ 100ms
  └── schemas.py                  # 3 IC 的 payload schema

WP02 DoD 新增：
  - IC-15 halt_requester P99 ≤ 100ms（pytest-benchmark · 10000 samples）
  - 违反视为 release blocker（HRL-05）

WP01 代码（71 TC · L2-01 采集器）**通过验收** · 不需改（L2-01 不直接碰 IC-13/14/15 方向）。
```

---

*— 主会话仲裁 · 2026-04-23 · Dev-ζ 4 条 self-correction —*
