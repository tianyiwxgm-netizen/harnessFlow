# harnessFlow Slice A — pipeline_graph 可视性 MVP 设计

> **范围**：Slice A（A→B→C 三切片路线第 1 片，见 memory `project_harnessflow_pipeline_graph_abc.md`）
> **创建**：2026-04-26
> **状态**：待用户 review
> **关联 plan**：`docs/superpowers/plans/2026-04-26-pipeline-graph-A.md`（Slice A 落地后写）

---

## 0. 缘起 + 目标

### 0.1 缘起

用户在 dashboard (`127.0.0.1:8765`) 看到 6 张"空感强"的卡片（项目交付目标 / 范围 / 资料库 / TDD 质量 / Harness 监督 / WBS 工作包），误以为系统只是"美化数据展示"。深度查证后真实缺口是：

- 当前 `harnessFlow.md` 主 skill **不强制** 在 `INIT → ROUTE_SELECT` 之间生成 `pipeline_graph[]` 显式蓝图
- `_derived.project_library.docs[]` 没有"任务期间查阅过的资料"登记机制（CLARIFY/PLAN 阶段查的文档没回写）
- Dashboard 6 张卡的写入路径**隐式**散落在 IMPL 各处，没有 node→field 的契约
- 每节点完成时**没有**强制 timeline append + supervisor pulse 触发点

### 0.2 目标

让 `/harnessFlow + <任务>` 启动后，主 skill **强制生成** `pipeline_graph[]` 蓝图（13 节点 PMP 5 阶段全集），每个节点显式声明：

1. 写入 task-board 哪个 `_derived.<field>` 子树
2. 该字段的"完成"判据（用于节点级 BLOCK）
3. 完成时调用哪个 supervisor pulse 钩子
4. 与上下游节点的 forward / parallel_split / converge / rollback 关系

**Slice A 的成功判据**（来自 memory `project_harnessflow_pipeline_graph_abc.md`）：

> 用户开 `/harnessFlow` 任意新任务后：
> 1) dashboard 看见两条 DAG（业务交付 + 监督）
> 2) 每节点有具体写入数据
> 3) 任一节点缺数据 → BLOCK 不放过

### 0.3 不在本片范围（Slice B/C 留）

- ❌ 节点级 process_ref + checkpoint resume（Slice B）
- ❌ Rollback / Loop 真运行时（沿 backward edge 回退，重 loop 状态机）（Slice B）
- ❌ Supervisor 监督流水线 6 节点（goal_drift / dod_progress / red_line_scan / cost_pulse / quality_gate / WARN_dedup）真实落地（Slice C）

本片**只**做"显式 pipeline_graph + 节点级 BLOCK + 6 张卡 node→field 契约 + per-node 监督 pulse 触发点 + dashboard 黄警示 + 历史 task 回填"。

---

## 1. 设计决策（Q1-Q6 锁定）

### Q1 — 节点级失败处理：**A · 节点级严格 BLOCK**（用户 2026-04-26 显式批准）

任一节点的 `outputs_required[]` 在 `gate_predicate` eval 后未通过 → 主 skill 立即 `current_state → PAUSED_ESCALATED` + Supervisor 写 `DOD_GAP_ALERT` 红线，不允许"软提示后继续"。

**Why**：用户原话 "我理解现在验证的问题就是这些 根本没有完成工作"——任何"软放过"都会再次让卡片变空。

### Q2 — pipeline_graph 节点集合：**A · 13 节点 PMP 5 阶段全集**（最高质量自动锁）

```
①启动 Initiating  : N1 任务采集 → N2 资料收集 → N3 目标分析+锁定 → N4 项目章程
②规划 Planning    : N5 PRD 编写 → N6 TDD 用例设计 (parallel_split) → N7 详细技术方案 (parallel_split)
                    → N8 范围收口 (converge) → N9 WBS 拆解 → N10 执行计划
③执行 Executing   : N11 项目开发 LOOP (内含 augment 边到 N6 补 TDD)
④监控 M&C        : N12 质量验证 (rollback 边到 N11 重 loop)
⑤收尾 Closing    : N13 收尾归档 (rollback 边到 N12 commit/PR fail)
```

**Why** 选 13 节点而非候选的 6 节点：

1. 已对齐 dashboard 部署的 13 节点 SVG（`pipeline_catalog.py:13_NODE_DAG`），无需返工前端
2. 覆盖 PMP 五阶段，可向 PMI 标准对齐，便于未来引入 EVM / 挣值管理
3. 每张"空感卡"都有明确归属：6 卡 ↔ 6 个特定节点（见 § 3.2）
4. 单一节点集；不分"轻量 task 体量"（A 路线 size=XS）单独子集——A 路线本就豁免 pipeline_graph（保持现有 § 4.4 状态机）

### Q3 — Supervisor 触发频率：**A · 每节点完成强制 pulse**（最高质量自动锁）

每个节点 `current_state → next_state` 转移成功后，主 skill **强制**调用一次 `Agent(subagent_type="harnessFlow:supervisor", description="per-node pulse <node_id>")`，输入 task-board 当前快照 + 该节点 `outputs_produced[]`。Supervisor 输出 INFO/WARN/BLOCK 写 `supervisor_interventions[]`。

**Why**：节点完成是天然检查点；事后回看时间轴每节点都有一笔 pulse，便于审计；A 路线（XS）也豁免（state-machine § 8.1 既有"低频 tick"模式不变）。

**去重**：同 `code` 5 min 内归并（沿用 harnessFlow.md § 7.7 既定规则，不重复实现）。

### Q4 — 历史 task 回填：**A · 全量回填**（最高质量自动锁）

所有现存 `archive/task-boards/*.json`（按 `_index.jsonl` 列举）由一次性 backfill 脚本派生 `pipeline_graph[]` 视图（不动原 task-board，仅在 `_derived.pipeline.{nodes,edges,progress}` 加补字段）。

**Why**：tank-battle 已 CLOSED；如果不回填，dashboard pipeline 卡只对未来 task 有效，破坏"立即可视"承诺。一次性脚本（运行后即弃，提交到 `scripts/backfill_pipeline_graph.py`）成本可控，收益直接。

**回填策略**：
- 新 task：runtime 写真实 `pipeline_graph[]`（节点状态实时推进）
- 历史 task：根据 `state_history[]` + `stage_artifacts[]` 推导节点状态（CLOSED → 全 passed；ABORTED → 末节点 failed；其他 → 按已有 stage_artifacts 段位推 passed/pending）

### Q5 — Dashboard 显示策略：**A · 新增 🗺️ Pipeline Graph 卡 + 6 张空感卡加"未填写黄警示"**（最高质量自动锁）

**Slice A UI MVP 已完成**（commit `bf0dd83` + `8ba081f`）：
- Pipeline 视图作为主视图（替代 11-tabs）
- 抽屉含"📊 本任务实际数据"section
- Fullscreen 🔍 全屏查看按钮（commit `8ba081f`）

**Slice A 剩余**（本 spec 范围）：
- 6 张空感卡（项目交付目标 / 范围 / 资料库 / TDD 质量 / Harness 监督 / WBS 工作包）当 `_derived.<对应字段>` 为空 / 缺失 / 仅占位时，渲染 ⚠️ 黄边框 + "等待 N<id> · <node 名> 写入"提示
- 黄警示样式：`border:1px solid #e6a23c; background:#fdf6ec;`（沿用 Element Plus warning 色）

### Q6 — 实施粒度：**A · 全量**（最高质量自动锁）

落地涵盖：
1. `harnessFlow.md` 主 skill 加 § 2.5 pipeline_graph bootstrap 协议（INIT → CLARIFY 后强制 emit）
2. `task-board-template.md` 加 schema：`pipeline_graph[]` / `supervision_graph[]` / `prd` / `execution_plan` / `tdd_cases.{definitions, execution_results}`
3. 节点契约库 `pipelines/13_node_contract.yaml`（13 节点 × node_id / owner_skill / inputs_required / outputs_produced / writes_to_field / gate_predicate / supervisor_pulse_code / edges）
4. backfill 脚本 `scripts/backfill_pipeline_graph.py`（一次性，回填历史 task）
5. `ui/backend/mock_data.py` 派生层：从 task-board `pipeline_graph[]` 直接渲染（替代当前 derive 派生）；6 卡 emptiness 检测函数 `is_card_empty(card_id, task_board)`
6. `ui/frontend/index.html` 6 卡黄警示样式 + 提示文案（仅当 emptiness=true 时显示）

**Why** 全量而非"仅文档"：
- 文档不落地 = 只有 README，下一个 LLM 实例不会真执行
- "节点级 BLOCK"必须有 runtime 校验代码（`gate_predicate` 引擎），不能靠 prompt
- 用户目标"看得见的、强制执行的"——dashboard 黄警示是可视证据

---

## 2. 架构

### 2.1 数据流

```
/harnessFlow <任务>
  ↓
INIT (分配 task_id)
  ↓
CLARIFY (brainstorming 三维 size/task_type/risk + goal_anchor)
  ↓
ROUTE_SELECT (查 routing-matrix)
  ↓
[NEW] PIPELINE_EMIT — 主 skill 强制 emit pipeline_graph[]
  - 读 pipelines/13_node_contract.yaml
  - 按 task_type 选 13 节点子集（默认全 13；A 路线豁免）
  - 写 task-board.pipeline_graph + .supervision_graph (Slice C 占位)
  - status=pending for all nodes
  ↓
PLAN → IMPL_START
  ↓
主循环 walk pipeline_graph nodes (按 step 序 + DAG 拓扑):
  for node in topo_sort(pipeline_graph):
    1. enter check (validate_stage_io phase=enter)
    2. dispatch owner_skill / Agent / native tool
    3. write outputs to task-board.<writes_to_field>
    4. exit check (validate_stage_io phase=exit + gate_predicate)
       FAIL → PAUSED_ESCALATED + DOD_GAP_ALERT (Q1=A)
    5. append timeline entry to task-board.timeline[]
    6. spawn supervisor pulse (Q3=A)
    7. node.status = passed
  ↓
VERIFY (现有逻辑) → COMMIT → CLOSED
```

### 2.2 组件清单

| # | 文件 | 类型 | 责任 |
|---|---|---|---|
| C1 | `harnessFlow/.claude/skills/harnessFlow/harnessFlow.md` | skill prompt | 加 § 2.5 PIPELINE_EMIT 协议；§ 5 主循环改成 walk pipeline_graph |
| C2 | `harnessFlow/.claude/skills/harnessFlow/task-board-template.md` | schema doc | 加 5 个新字段定义 + JSON schema |
| C3 | `harnessFlow/pipelines/13_node_contract.yaml` | data | 13 节点 × 8 字段契约表 |
| C4 | `harnessFlow/pipelines/contract_loader.py` | py module | 加载 yaml + emit pipeline_graph[] + validate gate_predicate |
| C5 | `harnessFlow/scripts/backfill_pipeline_graph.py` | py one-shot | 历史 task 回填 |
| C6 | `harnessFlow/ui/backend/mock_data.py` | py module | 加 `derive_pipeline_from_board()` + `is_card_empty()` |
| C7 | `harnessFlow/ui/frontend/index.html` | vue | 6 卡黄警示渲染 |
| C8 | `harnessFlow/.claude/skills/harnessFlow/state-machine.md` | doc | 更新边定义（加 PIPELINE_EMIT 阶段） |

### 2.3 边界与隔离

- **主 skill prompt** 不内嵌 13 节点定义（避免 prompt 膨胀），通过 `read_yaml('pipelines/13_node_contract.yaml')` 读
- **`contract_loader.py`** 是纯函数模块，不依赖 FastAPI，便于 backfill 脚本复用
- **dashboard 派生层**（mock_data.py）只读 task-board，不改写；emptiness 判断从 yaml contract 推（不写死字段名到 frontend）
- **frontend** 收 `_derived.cards[]` 携 `is_empty / waiting_for_node` 字段，渲染纯样式逻辑

---

## 3. 节点契约 schema

### 3.1 单节点字段

```yaml
- node_id: N3
  step: 3
  phase: initiating              # PMP 5 阶段之一
  name: 目标分析+锁定
  owner_skill: superpowers:brainstorming
  inputs_required:               # validate_stage_io phase=enter 检查
    - field: initial_user_input
      must_exist: true
    - field: _derived.project_library.docs
      must_exist: false          # 软依赖
  outputs_produced:               # validate_stage_io phase=exit 检查
    - field: goal_anchor
      shape: { hash: str, claude_md_path: str, text: str }
      must_exist: true
    - field: _derived.delivery_goal
      shape: { user_initial_prompt: str, locked_goal: str, dod_summary: str }
      must_exist: true
  writes_to_field:                # 主写字段（dashboard 卡映射用）
    - _derived.delivery_goal     # → 项目交付目标卡
  gate_predicate:                 # 节点完成判据
    expression: "goal_anchor.hash != null AND _derived.delivery_goal.locked_goal.length > 0"
    on_fail: BLOCK                # Q1=A 严格
  supervisor_pulse_code: "node_passed_N3"
  dashboard_card_mapping:         # 哪些卡受本节点影响（用于黄警示）
    - delivery_goal
  edges_out:
    - to: N4
      kind: forward
    - to: N3
      kind: rollback
      from: N4
      label: "PRD 写不出"
```

### 3.2 6 张空感卡 ↔ 节点映射（Q5 黄警示数据源）

| dashboard 卡 | 写入节点 | _derived.<field> | emptiness 判据 |
|---|---|---|---|
| 项目交付目标 | N3 | `delivery_goal.locked_goal` | 字段缺 / null / 空字符串 |
| 项目范围 | N8 | `scope.in_scope` + `scope.out_of_scope` | 两数组都为空 |
| 项目资料库 | N2（动态追加） | `project_library.docs[]` + `project_library.repos[]` | 总计 < 3 |
| TDD 质量 | N6 | `tdd_cases.definitions[]` | 数组为空 |
| Harness 监督 | 全节点（N1-N13 累加） | `supervisor_interventions[]` + `red_lines[]` | 数组为空 |
| WBS 工作包 | N9 | `wbs[]` | 数组为空 |

### 3.3 13 节点完整列表（详见 `pipelines/13_node_contract.yaml`）

```
N1 任务采集     → writes _derived.delivery_goal.user_initial_prompt
N2 资料收集     → writes _derived.project_library.{docs,repos,process_docs}
N3 目标分析锁定 → writes goal_anchor + _derived.delivery_goal.locked_goal
N4 项目章程     → writes _derived.charter
N5 PRD 编写     → writes _derived.prd
N6 TDD 用例设计 → writes tdd_cases.definitions[]
N7 详细技术方案 → writes _derived.tech_design
N8 范围收口     → writes _derived.scope.{in_scope, out_of_scope}
N9 WBS 拆解     → writes _derived.wbs[]
N10 执行计划    → writes _derived.execution_plan
N11 项目开发 LOOP → writes loop_history[] + stage_artifacts[] + tdd_cases.execution_results[]
N12 质量验证    → writes verifier_report + dod_expression
N13 收尾归档    → writes commit_sha + retro_link + archive_entry_link
```

---

## 4. 错误处理

### 4.1 节点 BLOCK（Q1=A）

```python
def execute_node(node_def: dict, task_board: dict):
    # 入口校验
    enter_verdict = validate_stage_io(task_board, node_def, phase="enter")
    if enter_verdict.has_blocking:
        supervisor_log("BLOCK", "DOD_GAP_ALERT",
                       f"node {node_def['node_id']} missing required inputs",
                       enter_verdict.violations)
        transition(task_board, "PAUSED_ESCALATED")
        return False

    # 派单
    result = dispatch(node_def["owner_skill"], task_board, node_def["inputs"])

    # 出口校验 + gate_predicate
    exit_verdict = validate_stage_io(task_board, node_def, phase="exit")
    gate_pass = eval_predicate(node_def["gate_predicate"]["expression"], task_board)
    if not exit_verdict.ok or not gate_pass:
        supervisor_log("BLOCK", "DOD_GAP_ALERT",
                       f"node {node_def['node_id']} gate FAIL",
                       exit_verdict.violations + [f"gate_expr eval={gate_pass}"])
        # rollback edge: 看 edges_in_kind=rollback 是否存在 → 若存在，回退到上游节点重 loop（Slice B 实现）
        # Slice A: 不实现 rollback runtime；直接 PAUSED_ESCALATED
        transition(task_board, "PAUSED_ESCALATED")
        node_def["status"] = "failed"
        return False

    node_def["status"] = "passed"
    return True
```

### 4.2 Backfill 失败

回填脚本若遇 task-board schema 损坏 / state_history 残缺：

- 跳过该 task，记入 `archive/backfill-skipped.jsonl`
- 不抛异常中断整批
- 输出统计 `processed=N skipped=M`

### 4.3 Supervisor pulse 失败

per-node supervisor pulse 失败（subagent dispatch 异常 / 超时）→ 降级 INFO（不阻塞主流程），记 `supervisor_interventions[].dispatch_failed=true` 字段；下一节点继续。

**Why** 不 BLOCK pulse 失败：pulse 是观察者非阻塞侧；阻塞会让无关 infra 故障升级成任务停摆。

---

## 5. 测试策略

### 5.1 Unit（pytest）

| 测试 | 文件 | 验证点 |
|---|---|---|
| `test_contract_loader_loads_13_nodes` | `tests/test_contract_loader.py` | yaml → 13 个 NodeDef 实例 |
| `test_validate_stage_io_enter_missing_input_blocks` | 同上 | enter 校验缺 input → has_blocking=true |
| `test_validate_stage_io_exit_gate_fail_blocks` | 同上 | gate_predicate eval=false → has_blocking=true |
| `test_emit_pipeline_graph_for_size_xs_skips` | 同上 | A 路线 (size=XS) 不 emit |
| `test_is_card_empty_delivery_goal` | `tests/test_card_emptiness.py` | _derived.delivery_goal 缺 → empty=true, waiting_for=N3 |
| `test_backfill_handles_closed_task` | `tests/test_backfill.py` | CLOSED task → all nodes status=passed |

### 5.2 Integration（Playwright）

| 测试 | 验证点 |
|---|---|
| `e2e_new_task_emits_pipeline_graph` | `/harnessFlow tank-battle-v2`（新 task） → 1 秒内 task-board 出现 `pipeline_graph[]` 含 13 节点 |
| `e2e_node_block_on_missing_output` | mock 强制 N3 缺 `goal_anchor` → 主 skill 转 PAUSED_ESCALATED + supervisor 写 DOD_GAP_ALERT |
| `e2e_dashboard_yellow_warning_on_empty_card` | 半成品 task（仅 N1 done）→ 5 卡显黄警示 + 文案"等待 N3 · 目标分析+锁定 写入" |
| `e2e_per_node_supervisor_pulse_recorded` | 完整 task 跑完 → `supervisor_interventions[]` ≥ 13 entry（每节点至少 1 pulse） |

### 5.3 回填验收

```bash
python scripts/backfill_pipeline_graph.py --dry-run
# 输出: would process 12 tasks, skip 0
python scripts/backfill_pipeline_graph.py --apply
# 输出: processed 12, skipped 0
# 之后 dashboard 打开任意历史 task → pipeline 视图全 13 节点绿
```

---

## 6. 风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 13 节点对小任务（XS/S）过重 | 中 | 中 | A 路线豁免 pipeline_graph；XS 走原状态机 |
| `gate_predicate` 表达式复杂度爆炸 | 中 | 高 | 沿用 stage-contracts.md 既有 AST 白名单解析器；本片不引入新算子 |
| 回填脚本破坏历史 task-board | 低 | 高 | 只写 `_derived.pipeline`（派生层），不改原始字段；脚本带 `--dry-run` 默认 |
| 6 卡映射在未来扩展时漂移 | 中 | 低 | 单一真相源 yaml；frontend 从 `_derived.cards[]` 渲染，不写死字段 |
| 主 skill prompt 加 § 2.5 后超长 | 低 | 中 | § 2.5 只 emit 引用 yaml；prompt 增量 < 50 行 |
| Supervisor pulse 13× 每节点导致 token 成本 | 中 | 中 | pulse 同 code 5min 去重（既有规则）；A 路线豁免；XS 走低频 tick |

---

## 7. 落地里程碑（plan 详写，本节仅概要）

| M | 验收 |
|---|---|
| M1 — 契约表 + loader | yaml 13 节点完整 + pytest unit 全绿 |
| M2 — 主 skill prompt 改造 | § 2.5 PIPELINE_EMIT 落地 + 新任务 task-board 含 pipeline_graph |
| M3 — task-board schema doc 更新 | template.md 加 5 字段 + 现有任务向前兼容 |
| M4 — 节点级 BLOCK runtime | validate_stage_io 接 gate_predicate + Playwright e2e_node_block 通过 |
| M5 — 6 卡黄警示 + dashboard 派生层 | dashboard 渲染 + e2e_dashboard_yellow_warning 通过 |
| M6 — 历史回填脚本 | 12 task 全成功回填 + dashboard 历史 task pipeline 视图绿 |
| M7 — Supervisor per-node pulse | 完整任务跑完 ≥ 13 pulse entry |

**Slice A 全部 M 完成 → 切 Slice B。**

---

## 8. 决策附录（用户互动记录）

- 2026-04-26 — 用户开 brainstorm topic，列 Q1-Q6 + 6 目标
- 2026-04-26 — 用户回 Q1=A（节点级严格 BLOCK），后请"哪种产出质量最高"自动锁 Q2-Q6
- 2026-04-26 — 中场切到 fullscreen 按钮（commit `8ba081f`），完成后回主线
- 2026-04-26 — 本 spec 落盘，待用户 review

每次 Q 决策后均依据 memory `feedback_quality_over_speed.md`（多方案选择时永远自动选质量最高，含外部验证 / 独立 review）。

---

## 9. 下一步

1. **用户 review 本 spec**，确认 6 个 Q 锁定无误
2. 若批准 → 调 `superpowers:writing-plans` skill 写实施 plan（拆 M1-M7 为 ≤ 5 分钟 step）
3. 若有改动 → 改 spec 后再 review
