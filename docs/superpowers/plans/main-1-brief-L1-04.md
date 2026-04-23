---
doc_id: main-1-brief-L1-04
doc_type: superpowers-session-brief
session: main-1（主会话接力）
source_exe_plan: docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-1-L1-04-quality-loop.md
created_by: 主会话 · 波 1-3 阻塞期预热
created_at: 2026-04-23
status: prep-ready
---

# main-1 · L1-04 Quality Loop · Session Brief（启动前速读）

> **定位**：main-1 会话启动时 · 先读本 brief（10 分钟）· 再按 `superpowers:writing-plans` 写自己的 impl plan。
>
> **前置（启动门槛）**：波 3 全 8 Dev DoD 绿 · L1-09/L1-06/L1-05/L1-02/L1-03/L1-07/L1-08/L1-10 代码 ready。

---

## §1 一眼看完 L1-04 是什么

L1-04 = **Quality Loop 质量环** · harnessFlow 的"质量判官"。

**7 L2 职责**（来自 `3-1/L1-04/architecture.md §11`）：

| L2 | 职责 | 输入 | 输出 | 3-1 行数 | 估代码 |
|:---:|:---|:---|:---|:---:|:---:|
| L2-01 TDD 蓝图生成器 | 将需求拆成 test 覆盖计划 | 3-2 tests.md 规格 | TDD blueprint YAML | 2175 | ~4000 |
| L2-02 DoD 表达式编译器 | 把 DoD YAML 语法编译成 AST · 可裁决函数 | DoD YAML | AST + 裁决器 | 2277 | ~4500 |
| L2-03 测试用例生成器 | TDD blueprint → pytest 骨架代码 | L2-01 blueprint | pytest.py 文件 | 2336 | ~4500 |
| L2-04 质量 Gate 编译器 + 验收 checklist | 硬/软/metric 三类判据统一 Gate | DoD AST + metric | Gate 裁决（pass/tolerated/rework）| 2709 | ~5500 |
| L2-05 S4 执行驱动器 | S4 期驱动 subagent 跑 test + 收集 metric | L2-04 Gate + WP | S4 execution trace | 2884 | ~5800 |
| L2-06 S5 TDDExe Verifier 编排器 | Verifier 签发（IC-20）· 双签 | S4 trace + Verifier | IC-20 verified result | 3578 | ~6000 |
| L2-07 偏差判定 + 4 级回退路由器 | 消费 IC-14 · 4 级回退路径 | IC-14 + Gate 反馈 | rollback route | 3186 | ~4200 |
| **合计** | 7 L2 | - | - | 19145 | **~34500** |

---

## §2 9 WP 骨架（来自 main-1 exe-plan §3）

> main-1 exe-plan 已经定好 · 不要重拆 WP。在此基础上用 `superpowers:writing-plans` 产出 step 级。

```
主-1a（5 天 · 基础）
├── WP01 L2-02 DoD 表达式编译器（可复用 archive/v1.2 已写的 predicate_eval）
├── WP02 L2-01 TDD 蓝图生成器
├── WP03 L2-03 测试用例生成器（L2-01 输出 → pytest 骨架）
└── WP04 L2-04 质量 Gate 编译器（三判据统一）

主-1b（7 天 · 执行 + Verifier）
├── WP05 L2-05 S4 执行驱动器
├── WP06 L2-06 S5 Verifier 编排（发 IC-20）
└── WP07 L2-07 4 级回退路由（消费 IC-14）

集成（2 天）
├── WP08 L1-04 内部 7 L2 集成 · e2e 跑一次 Quality Loop
└── WP09 跨 L1 集成（用 Dev 组真实产出 · 不再 mock）
```

**关键点**：
- WP01 做 **L2-02 先**（不是 L2-01 · 因为 L2-01 的蓝图需要 L2-02 DoD 语义）
- archive/v1.2 有 predicate_eval 实现 · 直接 import 复用 · 省 1-2 天

---

## §3 跨 L1 消费清单（波 3 后应全部 ready）

| IC | 生产方 | 用途 |
|:---:|:---|:---|
| IC-09 append_event | L1-09（Dev-α）| 每 Gate 裁决发审计事件 |
| IC-06 kb_read | L1-06（Dev-β）| Verifier 查历史案例 |
| IC-04 invoke_skill | L1-05（Dev-γ）| S4 执行里调 Skill |
| IC-01 state_transition | L1-02（Dev-δ）| Gate 通过 → 状态推进 |
| IC-02/03 get/assign_wp | L1-03（Dev-ε）| S4 期分 WP |
| IC-18 audit_query | L1-09 | Verifier 追溯历史决策 |

**main-1 发起的 IC**：
- IC-14 push_rollback_route（生产 · L1-07 消费）
- IC-20 invoke_verifier（生产 · L1-05 子 Agent 消费）

---

## §4 100ms 硬约束（涉及本 L1）

本 L1 **无 100ms 硬约束**（panic/halt 在 L1-01/L1-07/L1-10）· 但 **Gate 裁决 P95 < 500ms**（来自 PRD §7.1）。

---

## §5 已知需求与限制

### 5.1 archive/v1.2 复用

- `archive/v1.2/predicate_eval.py` · AST 白名单断言 · **WP01 直接 import 或 vendor**
- `archive/v1.2/stage_contracts/` · DoD YAML 示例 · 参考格式

### 5.2 DoD 表达式语法（3-3 规约）

见 `docs/3-3-Solution-Monitoring&Controlling/dod-specs/` · DoD YAML：
```yaml
dod:
  hard: [project_exists, state_audited]
  soft: ["hard_pass_rate >= 95%"]
  metric: ["e2e_latency_p95 < 500ms"]
```

### 5.3 Gate 裁决 5 基线（3-3 quality-standards）

```
hard_pass → 100% 通过 · 继续
soft_pass → ≥ 80% 通过 · 继续
tolerated → 60-80% · 警告 + 记录
rework → < 60% · 返 S4 重执行
abort → 连续 3 rework · 升级 Stage Gate
```

---

## §6 主会话特权（与 Dev 组不同）

- **可改源文档**：2-prd / 3-1 / 3-2 / 3-3 / ic-contracts.md
- **可改共享文件**：pyproject.toml / tests/conftest.py / scripts/quality_gate.sh / docs/
- **走 §6 自修正情形 C/D/E** · 记 `projects/_correction_log.jsonl`
- **不用开独立分支**：直接在 main 上干（但高频 commit + push）

---

## §7 启动时立刻做（main-1 会话第一条消息收到后）

```
1. 读本 brief（当前文件）· 10 min
2. 读 main-1 exe-plan（9 WP · 5 min）
3. 读 3-1 L1-04 architecture.md §1-§11（30 min · 1965 行）
4. 读 3-1 L1-04 L2-02 · L2-01（配对理解 WP01+WP02 · 60 min）
5. 调 Skill(superpowers:using-superpowers)
6. 调 Skill(superpowers:writing-plans) 产 docs/superpowers/plans/main-1-L1-04-impl.md
7. 先只写 WP01+WP02 的 step 级（不一次写完 9 WP · 会烦 context）
8. 调 Skill(superpowers:subagent-driven-development) 启动 WP01
9. WP01 完成再扩展 plan 至 WP03
10. ... 滚动推进
```

**总启动时间**：~2 小时准备 · 然后进入 WP01 红灯。

---

## §8 源文档 checklist（全绿才能启动）

**P0（必读）**：
- [ ] `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-1-L1-04-quality-loop.md`（9 WP 骨架）
- [ ] `docs/3-1-Solution-Technical/L1-04-Quality Loop/architecture.md`
- [ ] `docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-01 ~ L2-07.md`（7 份 · ~17700 行）
- [ ] `docs/3-2-Solution-TDD/L1-04-Quality Loop/L2-01 ~ L2-07-tests.md`（7 份 · ~11400 行）
- [ ] `docs/3-1-Solution-Technical/integration/ic-contracts.md §3.14 IC-14 + §3.20 IC-20`

**P1（参考）**：
- [ ] `docs/3-3-Solution-Monitoring&Controlling/dod-specs/` 全 · DoD YAML 语法源
- [ ] `docs/3-3-Solution-Monitoring&Controlling/quality-standards/` 全 · 5 基线
- [ ] `archive/v1.2/` 历史实现 · WP01 复用
- [ ] `docs/MASTER-SESSION-DISPATCH.md §5.5 + §5.6`（代码所有权 + 包名铁律）

---

## §9 常见坑（主会话预警）

1. **WP01 的 predicate_eval 安全性**：AST 白名单不能绕 · 禁止 `eval()` · 禁止 `__import__`
2. **Gate 裁决的幂等性**：同 WP + 同 run_id 多次调用 · 结果必一致
3. **S5 Verifier 二签**：发 IC-20 后必须等 Verifier 回包 · 不能直接跳下一步
4. **IC-14 消费时 PM-14**：跨 pid 回退路由禁止（硬红线 HRL-01）
5. **L2-06 与 L2-07 职责切分**：L2-06 签发（主动）· L2-07 消费（被动）· 别写混
6. **metric DoD 需要实时采样**：调 L1-07 监控数据（采样 100ms）

---

## §10 等到时发什么启动命令

```
按 harnessFlow 会话分工执行任务 · 启动 superpowers 全链路：

目标 exe-plan md：/Users/zhongtianyi/work/code/harnessFlow/docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-1-L1-04-quality-loop.md
补充 brief：/Users/zhongtianyi/work/code/harnessFlow/docs/superpowers/plans/main-1-brief-L1-04.md

身份：主会话接力（可改源文档 + 共享文件）

执行流程（10 步 · 见 MASTER-SESSION-DISPATCH §6.2）...

开干。
```

---

*— main-1 brief · v1.0 · 主会话波 1-3 阻塞期预热产出 —*
