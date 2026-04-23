---
doc_id: exe-plan-main-1-L1-04-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α-L1-09-resilience-audit.md（标杆）
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/architecture.md（1965 行）
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-01~L2-07.md（19145 行 · 最复杂）
  - docs/3-2-Solution-TDD/L1-04-Quality Loop/L2-01~L2-07-tests.md（~21000 行 · ~469 TC）
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.3 IC-03 · §3.14 IC-14 · §3.20 IC-20
version: v1.0
status: draft
assignee: **主会话（不分派）**
wave: 4（核心集成）
priority: P0（最复杂 · 跨 L1 集成点）
estimated_loc: ~34500 行
estimated_duration: 10-14 天（主会话连续投入）
---

# main-1 · L1-04 Quality Loop · Execution Plan

> **定位**：**主会话必做**（4-0 master §3.3 Q-04）· 7 L2 · 19145 行 tech-design · 34500 行代码 · **M5 期间最复杂的组**。
>
> **为何主会话**：
> 1. 跨 L1 集成点：调 L1-05（IC-04/IC-20）+ L1-07（消费 IC-14）+ L1-09（IC-09 审计 · IC-10 replay）· 所有 Dev-X 组的结果都汇入此处
> 2. S3/S5 Gate 是全系统的质量门 · 错一条 cascade 全链
> 3. DoD 表达式编译器是核心算法（AST 白名单 · predicate_eval · 已有 v1.2 基础）
> 4. 3-2 TDD 用例最多（469 TC · G 会话首批 13 份之一）
>
> **前置依赖**：Dev-γ（IC-04/IC-20 真实）· Dev-ζ（IC-14 真实）· Dev-α（IC-09/IC-10 真实）。
>
> **拆批**：主-1a（L2-02/L2-01/L2-04 · DoD 核心 · 5 天）· 主-1b（L2-03/L2-05/L2-06/L2-07 · 执行+回退 · 7 天）· 中间 checkpoint。

---

## §0 撰写进度

- [x] §1-§10 全齐

---

## §1 范围

### 7 L2 清单

| L2 | 职责 | 3-1 行 | 估代码 | 估时 |
|:---:|:---|---:|---:|:---:|
| **L2-02** DoD 表达式编译器 | AST 白名单 + predicate_eval + evidence 映射（已有 v1.2 archive/ 基础）| 2800 | ~5000 | 1.5 天 |
| **L2-01** TDD 蓝图生成器 | 从 4 件套 + Plan → TDD 蓝图（GWT + 用例框架）| 2500 | ~4500 | 1.5 天 |
| **L2-04** 质量 Gate 编译器+验收 Checklist | DoD 表达式 → 可执行 Gate evidence + Checklist | 3000 | ~5400 | 1.5 天 |
| **L2-03** 测试用例生成器 | 从蓝图 → pytest 真实代码（委托 L1-05 test-generator skill）| 2800 | ~5000 | 1.5 天 |
| **L2-05** S4 执行驱动器 | WP 代码执行编排 · 调 L1-05 invoke_skill · 单 WP 生命周期 | 2700 | ~4900 | 2 天 |
| **L2-06** S5 TDDExe Verifier 编排器 | IC-20 delegate_verifier · 三段证据链 · 5 级 verdict | 2800 | ~5000 | 2 天 |
| **L2-07** 偏差判定+4 级回退路由器 | IC-14 消费 · 4 级回退决策 · 同级升级 | 2545 | ~4700 | 2 天 |
| 合计 | 7 | **19145** | **~34500** | **12 天** + 2 天集成 = **14 天** |

### 代码目录

```
app/l1_04/
├── dod_compiler/              # L2-02（DoD 核心 · 复用 v1.2 archive/）
├── blueprint_generator/       # L2-01
├── gate_compiler/             # L2-04
├── test_case_generator/       # L2-03
├── s4_executor/               # L2-05
├── s5_verifier/               # L2-06
└── rollback_router/           # L2-07
```

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | `2-prd/L1-04 .../prd.md` 5 段质量环定义 · 5 级 verdict · 4 级回退 |
| P0 | `3-1/L1-04/architecture.md` §11 L2 分工 · §5 S1-S5 时序 |
| P0 | `3-1/L1-04/L2-02.md`（DoD 表达式 · 最关键）· §3 compile · §6 AST 白名单 · §11 错误码 |
| P0 | `3-1/L1-04/L2-01 ~ L2-07.md`（每份 §3 接口 · §11 错误码）|
| P0 | `3-2/L1-04/*.md` 469 TC（G 首批标杆）|
| P0 | `ic-contracts.md §3.3 IC-03 · §3.14 IC-14 · §3.20 IC-20` |
| P0 | `archive/v1.2/` 现有代码（DoD 表达式 v1.2-A/B/C/D 已实现部分 · 参考/复用）|
| P1 | `3-3/dod-specs/*` O 会话产出 · DoD 规约 · fallback 用 3-1 §12 |

---

## §3 WP 拆解（8 WP · 14 天）

### 3.0 总表

| WP | 批 | L2 | 主题 | 前置 | 估时 | TC |
|:---:|:---:|:---:|:---|:---|:---:|:---:|
| M1-WP01 | 1a | L2-02 | DoD 表达式编译器 · AST 白名单 + predicate_eval | α/γ mock | 1.5 天 | ~67 |
| M1-WP02 | 1a | L2-01 | TDD 蓝图生成器 · GWT + 用例框架 | WP01 | 1.5 天 | ~68 |
| M1-WP03 | 1a | L2-04 | 质量 Gate 编译器 + Checklist | WP01 | 1.5 天 | ~65 |
| M1-WP04 | 1a | - | checkpoint 1 · 三 L2 集成（DoD → 蓝图 → Gate）| WP01-03 | 0.5 天 | ≥ 6 |
| M1-WP05 | 1b | L2-03 | 测试用例生成器 · 委托 test-generator skill | WP02 · γ 真实 | 1.5 天 | ~67 |
| M1-WP06 | 1b | L2-05 | S4 执行驱动器 · WP 代码执行编排 | γ 真实 · α 真实 | 2 天 | ~66 |
| M1-WP07 | 1b | L2-06 | S5 Verifier 编排 · IC-20 · 三段证据链 · 5 verdict | γ L2-04/05 真实 | 2 天 | ~65 |
| M1-WP08 | 1b | L2-07 | 偏差判定 + 4 级回退路由 | WP07 · ζ 真实 IC-14 | 2 天 | ~71 |
| M1-WP09 | - | 集成 | 全 7 L2 e2e · S1→S5 Quality Loop 一圈 | 全 WP | 1.5 天 | ≥ 15 |

### 3.1 M1-WP01 · L2-02 DoD 表达式编译器（最关键 · 最先做）

**源**：`3-1 L1-04/L2-02.md §3 compile_dod + eval_predicate · §6 AST 白名单 · §11 错误码` · 参考 `archive/v1.2-A/B/C/D` 现有实现

**L3**：
- `compile_dod(expression_str) -> CompiledDoD`
  - AST 白名单：允许 `and / or / not / comparison（==, !=, <, <=, >, >=）/ attribute access（wp.status）/ function call（count / exists / all / any）`
  - 禁：exec · eval · import · dunder attr
  - ast.parse + AST visitor 校验
- `eval_predicate(compiled_dod, evidence_context) -> EvalResult`
  - evidence_context 是 dict · 含 WP 状态 · test 结果 · coverage · audit 等
  - 返 `EvalResult(passed: bool, reason: str, missing: list)`
- `compute_dod_hash(compiled_dod)` · 确保 DoD 表达式篡改检测
- 幂等：同表达式编译返同 CompiledDoD（hash 相同）

**L4**：
```
app/l1_04/dod_compiler/parser.py           ~280 行（ast.parse + visitor · 复用 archive/v1.2-A）
app/l1_04/dod_compiler/ast_whitelist.py    ~200 行（白名单 AST node 集）
app/l1_04/dod_compiler/predicate_eval.py   ~250 行（复用 archive/v1.2-B）
app/l1_04/dod_compiler/evidence_context.py ~150 行
app/l1_04/dod_compiler/hash.py             ~60 行
app/l1_04/dod_compiler/schemas.py          ~180 行
```

**DoD**：
- [ ] ~67 TC 全绿
- [ ] 禁止 AST node 100% 拒绝（exec/eval/import/dunder 各 ≥ 3 TC）
- [ ] evidence_context 缺字段 · 返 missing · 不 raise
- [ ] DoD hash 幂等（重编译返相同 hash）
- [ ] 与 archive/v1.2 对比测试（输入一致 · 输出一致）
- [ ] commit `feat(harnessFlow-code): M1-WP01 L2-02 DoD 表达式编译器`

### 3.2 M1-WP02 · L2-01 TDD 蓝图生成器

**源**：`L2-01.md §3 generate_blueprint · §6 GWT 提取算法`

**L3**：
- `generate_blueprint(wp_def, four_set) -> TDDBlueprint`
  - 输入：WP 定义（WBS 拆解）· 4 件套（scope/prd/plan/tdd 源）
  - 输出：蓝图 md（含 GWT 场景清单 + 用例框架）
  - 算法：
    - 从 plan.md 提 "验证点"
    - 从 prd.md 提 GWT 八场景
    - 组装成蓝图 md
  - 调 L1-05 skill（`blueprint-generator` · IC-04）做实际 LLM 生成
- `validate_blueprint(blueprint)` · 校验 GWT 完整性（每 user action ≥ 1 正向 + 1 负向）

**L4**：
```
app/l1_04/blueprint_generator/generator.py        ~220 行
app/l1_04/blueprint_generator/gwt_extractor.py    ~180 行
app/l1_04/blueprint_generator/validator.py        ~150 行
app/l1_04/blueprint_generator/skill_invoker.py    ~100 行（调 L1-05）
app/l1_04/blueprint_generator/schemas.py          ~180 行
```

**DoD**：
- [ ] ~68 TC 全绿
- [ ] blueprint md 格式合规（可被 L2-03 消费）
- [ ] GWT 完整性校验
- [ ] skill 失败 fallback 测
- [ ] commit `feat(harnessFlow-code): M1-WP02 L2-01 TDD 蓝图`

### 3.3 M1-WP03 · L2-04 质量 Gate 编译器 + Checklist

**源**：`L2-04.md §3 compile_gate · §6 evidence 映射`

**L3**：
- `compile_gate(dod_expression, evidence_schema) -> ExecutableGate`
  - 调 L2-02 `compile_dod`
  - 将 DoD 转成 Gate executable（evidence 装配器）
  - 产出 `ExecutableGate(dod_hash · evidence_requirements · evaluator)`
- `evaluate_gate(wp_id, evidence_dict) -> GateResult(pass/reject/need_input, missing[])`
  - 调 predicate_eval
  - 缺 evidence → need_input（非 reject）
- 产出验收 Checklist（human-readable · Gate 决策卡片展示用）

**L4**：
```
app/l1_04/gate_compiler/compiler.py              ~250 行
app/l1_04/gate_compiler/evidence_assembler.py    ~200 行
app/l1_04/gate_compiler/checklist_renderer.py    ~150 行
app/l1_04/gate_compiler/schemas.py               ~180 行
```

**DoD**：~65 TC · Gate 三元（pass/reject/need_input）正确 · commit `M1-WP03`

### 3.4 M1-WP04 · checkpoint 1 · 1a 批集成

- 3 L2（L2-02/L2-01/L2-04）联调
- 验证：DoD 表达式 → 编译 → 蓝图 → Gate 可执行 全链
- ≥ 6 集成 TC · commit `M1-WP04`
- **checkpoint 点**：此时主会话已投入 5 天 · 可停下 review · 或继续 1b 批

### 3.5 M1-WP05 · L2-03 测试用例生成器（1b 开始）

**L3**：
- `generate_test_cases(blueprint) -> list[TestCaseCode]`
  - 委托 L1-05 `test-generator` skill（IC-04）
  - 输入：TDD 蓝图（GWT 场景）
  - 输出：pytest 真实代码（不是伪代码）· 每 GWT → 1 test 函数
  - 校验：语法合法（ast.parse）· 至少 1 assert

**L4**：
```
app/l1_04/test_case_generator/generator.py     ~220 行
app/l1_04/test_case_generator/code_validator.py ~150 行
app/l1_04/test_case_generator/skill_invoker.py  ~100 行
app/l1_04/test_case_generator/schemas.py        ~180 行
```

**DoD**：~67 TC · 语法合法 · 至少 1 assert · commit `M1-WP05`

### 3.6 M1-WP06 · L2-05 S4 执行驱动器

**L3**：
- `execute_wp(wp_def, blueprint, test_cases) -> ExecutionResult`
  - Step 1 · 准备：创建工作目录（`projects/<pid>/wp-<wp_id>/`）
  - Step 2 · 获锁（L1-09 L2-02）· `wp-<wp_id>` 资源
  - Step 3 · 调 L1-05 `impl-generator` skill（IC-04）· 生成实现代码
  - Step 4 · 写 test_cases 到 `tests/wp/`
  - Step 5 · 跑 pytest · 收集结果
  - Step 6 · 不通过 · retry（本级 · 最多 2 次）
  - Step 7 · 返 ExecutionResult（含 code_path · test_path · coverage · duration）
  - Step 8 · 释放锁 · 发 IC-09 `wp_executed`

**L4**：
```
app/l1_04/s4_executor/driver.py                 ~280 行
app/l1_04/s4_executor/workspace.py              ~150 行
app/l1_04/s4_executor/pytest_runner.py          ~180 行
app/l1_04/s4_executor/retry_policy.py           ~120 行
app/l1_04/s4_executor/schemas.py                ~180 行
```

**DoD**：~66 TC · workspace 隔离 · retry 2 次 · 锁正确释放 · commit `M1-WP06`

### 3.7 M1-WP07 · L2-06 S5 Verifier 编排器（IC-20 入口 · 最关键）

**L3**：
- `run_verifier(wp_id, execution_result) -> VerifierReport`
  - 调 L1-05 `verifier` 子 Agent（**IC-20 delegate_verifier**）· 独立 session · PM-03
  - 三段证据链：
    - 证据 1 · 静态（ruff + mypy + 代码 review）
    - 证据 2 · 动态（pytest + coverage）
    - 证据 3 · 集成（契约测 + e2e smoke）
  - 5 级 verdict：
    - `PASS` · 全绿
    - `PASS_WITH_WARNINGS` · 小问题（lint warning 等）
    - `INSUFFICIENT` · evidence 不全 · need_input
    - `FAIL_L1 ~ FAIL_L4` · 按失败严重度分级
    - `HARD_FAIL` · 不可恢复（硬红线）
- DoD 白名单守护：verifier 只能调 whitelist 工具
- 超时：单 WP verifier ≤ 20 分钟（config）

**L4**：
```
app/l1_04/s5_verifier/orchestrator.py            ~280 行
app/l1_04/s5_verifier/evidence_chain.py          ~200 行
app/l1_04/s5_verifier/verdict_classifier.py      ~180 行
app/l1_04/s5_verifier/dod_gate_check.py          ~150 行
app/l1_04/s5_verifier/schemas.py                 ~180 行
```

**DoD**：~65 TC · IC-20 契约严格 · 5 verdict 完整 · 三段证据链测 · commit `M1-WP07`

### 3.8 M1-WP08 · L2-07 偏差判定 + 4 级回退路由（IC-14 消费）

**L3**：
- 订阅 ζ L2-04 的 IC-14 push_rollback_route
- `process_rollback(rollback_payload) -> RollbackAction`
  - 根据 level（L1/L2/L3/L4）决定：
    - L1 · 重试同 WP（本 loop）
    - L2 · 换 skill（IC-04 exclude_set）
    - L3 · 回 S3 调整蓝图（重新 TDD 蓝图）
    - L4 · 回 S1 重启动（pid 级 · 罕见）
- 调 L2-05 / L2-06 执行回退动作
- FailureCounter（per wp_id）· 同级连 3 失败升级（通过 IC-09 通知 L1-07 L2-06）

**L4**：
```
app/l1_04/rollback_router/router.py             ~280 行
app/l1_04/rollback_router/level_handlers.py     ~220 行（4 级动作）
app/l1_04/rollback_router/counter.py            ~150 行
app/l1_04/rollback_router/schemas.py            ~180 行
```

**DoD**：~71 TC · 4 级回退各 ≥ 10 TC · counter 5 态机 · commit `M1-WP08`

### 3.9 M1-WP09 · 集成 · S1→S5 Quality Loop 一圈

**L3**：
- 完整 Quality Loop：WP 进 → S1 蓝图 → S2 用例 → S3 Gate 编译 → S4 执行 → S5 Verifier → verdict → 回退 or 进下一 WP
- IC-03 / IC-04 / IC-09 / IC-14 / IC-20 全链集成
- 性能：单 WP Quality Loop P95 ≤ 30 min（PRD §7.1）
- PM-14：不同 pid 并发 · 隔离

**L4**：`tests/l1_04/integration/test_quality_loop_e2e.py`

**DoD**：≥ 15 集成 TC · 端到端绿 · SLO 达标 · commit `M1-WP09`

---

## §4 依赖图

```
1a 批（5 天）：
  M1-WP01 DoD 编译器 ──┬─► M1-WP02 蓝图 ──► M1-WP04 checkpoint
                      └─► M1-WP03 Gate 编译

1b 批（7 天）：
  M1-WP02 蓝图 ──► M1-WP05 用例生成
                       ↓
  M1-WP06 S4 执行（需 γ 真实 + α 真实）
                       ↓
  M1-WP07 S5 Verifier（IC-20 · 需 γ L2-04 真实）
                       ↓
  M1-WP08 4 级回退（需 ζ 真实 IC-14）
                       ↓
  M1-WP09 集成 · Quality Loop 一圈
```

### 跨组依赖

| 外部 | 提供方 | 何时真实 |
|:---|:---|:---|
| IC-04 invoke_skill | Dev-γ | 1b 开始前必 ready |
| IC-20 delegate_verifier | Dev-γ L2-04 | WP07 前必 ready |
| IC-09 | Dev-α | WP06 前真实 |
| IC-14 push_rollback_route | Dev-ζ | WP08 前真实 |
| IC-16 Gate 卡片（推 UI） | Dev-δ L2-01 · Dev-θ2 | WP09 前真实 |

---

## §5 standup + commit

复用 Dev-α §5 · prefix `M1-WPNN`。主会话做 · 每 WP 独立 commit · 每 3 WP 提交一次 checkpoint 讨论。

---

## §6 自修正

- 情形 A · 5 verdict 实测不够细 · 改 PRD §8
- 情形 B · DoD AST 白名单漏某合法 construct · 改 3-1 L2-02 §6 + archive/v1.2
- 情形 D · IC-20 消费方（Dev-γ L2-04）对 payload 理解不一 · 仲裁 ic-contracts §3.20

---

## §7 对外契约

| IC | 方向 | 角色 |
|:---|:---|:---|
| IC-03 接收 | `enter_quality_loop(wp_def)` | L1-01 → L2-01 |
| IC-04 发起 | `invoke_skill(blueprint-generator/test-generator/impl-generator)` | → Dev-γ |
| IC-20 发起 | `delegate_verifier(wp_report)` | → Dev-γ L2-04 子 Agent |
| IC-14 接收 | `push_rollback_route` | Dev-ζ → L2-07 |
| IC-09 发起 | `append_event` | 每段 S1-S5 落盘 |

---

## §8 DoD

- 7 L2 全绿 · 469 TC · coverage ≥ 85%
- DoD 表达式 AST 白名单测（禁止 node 100% 拒绝）
- IC-20 契约严格 · 5 verdict + 三段证据链
- 4 级回退各 ≥ 10 TC
- Quality Loop e2e P95 ≤ 30 min（mock）
- PM-14 多 pid 并发隔离

---

## §9 风险

- **R-M1-01** DoD 表达式复杂度：AST 白名单漏合法 construct · 走 §6 情形 B · 迭代补
- **R-M1-02** IC-20 Claude SDK 版本变化 · 同 Dev-γ 风险
- **R-M1-03** 单 WP Quality Loop > 30 min · 走 §6 情形 B 改 SLO（降预期）
- **R-M1-04** 主会话 14 天连续投入 · context 管理挑战 · 1a/1b 拆批 + checkpoint

---

## §10 交付清单

### 代码（~34500 行）

```
app/l1_04/
├── dod_compiler/           (~1120 行 · 复用 archive/v1.2)
├── blueprint_generator/    (~830 行)
├── gate_compiler/          (~780 行)
├── test_case_generator/    (~650 行)
├── s4_executor/            (~910 行)
├── s5_verifier/            (~990 行)
└── rollback_router/        (~830 行)
```

### 测试（~13000 行）· 469 TC + 15 集成

### commit 18-22 个

---

*— main-1 · L1-04 Quality Loop · Execution Plan · v1.0 · 主会话最复杂组 —*
