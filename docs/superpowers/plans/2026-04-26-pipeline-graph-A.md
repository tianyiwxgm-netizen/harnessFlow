# Slice A — pipeline_graph 可视性 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `/harnessFlow + <任务>` 启动时强制生成 `pipeline_graph[]` 13 节点蓝图，节点完成强制写 `_derived.<field>`，缺数据 → BLOCK；dashboard 6 张空感卡显黄警示；历史 task 全量回填。

**Architecture:** 13-node yaml 契约表 + Python loader/eval 层 → 主 skill `INIT→ROUTE_SELECT` 后 emit pipeline_graph[] → 主循环按 DAG 拓扑 walk 节点（每节点 enter/exit gate + supervisor pulse） → dashboard 派生层读 task-board.pipeline_graph 反映状态 + 6 卡缺口黄警示。

**Tech Stack:** Python 3.11 / PyYAML / pytest / FastAPI (existing) / Vue 3 + Element Plus (existing) / Playwright (E2E)

**Spec source:** `docs/superpowers/specs/2026-04-26-pipeline-graph-A-design.md`

---

## File Structure

### New files

| 路径 | 责任 | 行数预估 |
|---|---|---|
| `pipelines/__init__.py` | 包标记 | 1 |
| `pipelines/13_node_contract.yaml` | 13 节点契约（单一真相源） | ~600 |
| `pipelines/contract_loader.py` | yaml 加载 + emit_pipeline_graph + validate_node_io | ~200 |
| `pipelines/gate_eval.py` | gate_predicate 白名单 AST eval | ~120 |
| `pipelines/card_emptiness.py` | 6 卡 emptiness 判断 | ~80 |
| `scripts/backfill_pipeline_graph.py` | 历史 task 一次性回填 | ~150 |
| `tests/__init__.py` | pytest 包 | 1 |
| `tests/conftest.py` | 共享 fixture（mock task-board） | ~80 |
| `tests/test_contract_loader.py` | T1 单元测试 | ~120 |
| `tests/test_gate_eval.py` | T4 单元测试 | ~100 |
| `tests/test_card_emptiness.py` | T5 单元测试 | ~80 |
| `tests/test_backfill.py` | T6 单元测试 | ~80 |
| `tests/test_node_validate.py` | T4 集成测试 | ~80 |
| `pytest.ini` | pytest 配置（rootdir + asyncio） | ~10 |

### Modified files

| 路径 | 改动 | 范围 |
|---|---|---|
| `harnessFlow-skill.md` | 加 § 2.5 PIPELINE_EMIT；改 § 5.1 主循环加 walk pipeline_graph | ~80 行新增 |
| `task-board-template.md` | § 1.2.x 加 `pipeline_graph[]` `supervision_graph[]`；§ 1.5 加 `prd` `execution_plan` `tdd_cases.{definitions,execution_results}` | ~70 行新增 |
| `state-machine.md` | § 1 状态枚举不动；§ 2 主路径加 ROUTE_SELECT → PIPELINE_EMIT 边描述 | ~30 行新增 |
| `ui/backend/mock_data.py` | 加 `_derive_cards()` + `is_card_empty()` 调用 | ~60 行新增 |
| `ui/frontend/index.html` | 6 卡渲染加 emptiness 黄警示样式 + 文案 | ~40 行新增 |

---

## 实施顺序与里程碑

| Phase | 任务 | M | 验收 |
|---|---|---|---|
| Phase 0 | 基础设施（pytest + 包结构） | — | `pytest -q` 跑空 0 错 |
| Phase 1 | 契约表 + loader | M1 | 13 节点 yaml + 单测全绿 |
| Phase 2 | gate_eval + node validate | M4 (前移) | gate FAIL → BLOCK 单测绿 |
| Phase 3 | card_emptiness + dashboard 派生 | M5 | 半成品 task 显 5 黄警示 |
| Phase 4 | backfill 脚本 | M6 | 21 task 全成功 dry-run |
| Phase 5 | task-board schema doc | M3 | template.md 加 5 字段 |
| Phase 6 | 主 skill prompt § 2.5 | M2 | skill md 加 PIPELINE_EMIT 段 |
| Phase 7 | per-node supervisor pulse | M7 | pulse spawn helper + 单测绿 |

**说明**：实施顺序与原 spec § 7 里程碑（M1-M7）不完全一致 — M4 和 M5 前移是因为 gate_eval 和 card_emptiness 是纯函数，可独立 TDD；M2/M3 文档放后是因为它们引用前面的 Python API 名字，需先稳定。

---

## Phase 0: Foundation（基础设施）

### Task 0.1: pytest + 包结构 setup

**Files:**
- Create: `/Users/zhongtianyi/work/code/harnessFlow/pytest.ini`
- Create: `/Users/zhongtianyi/work/code/harnessFlow/tests/__init__.py`
- Create: `/Users/zhongtianyi/work/code/harnessFlow/tests/conftest.py`
- Create: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/__init__.py`

- [ ] **Step 1: Create pytest.ini**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

- [ ] **Step 2: Create tests/__init__.py and pipelines/__init__.py**

```bash
touch /Users/zhongtianyi/work/code/harnessFlow/tests/__init__.py
touch /Users/zhongtianyi/work/code/harnessFlow/pipelines/__init__.py
```

- [ ] **Step 3: Create tests/conftest.py with shared fixtures**

```python
"""Shared pytest fixtures for Slice A pipeline_graph tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_BOARDS_DIR = REPO_ROOT / "task-boards"


@pytest.fixture
def empty_task_board() -> dict:
    """A minimum-fields task-board for testing emit logic."""
    return {
        "task_id": "test-task-001",
        "created_at": "2026-04-26T10:00:00Z",
        "size": "M",
        "task_type": "后端 feature",
        "risk": "中",
        "current_state": "ROUTE_SELECT",
        "route_id": "C",
        "goal_anchor": {
            "text": "test goal",
            "hash": "deadbeef",
            "claude_md_path": "CLAUDE.md#goal-anchor-test-task-001",
        },
        "stage_artifacts": [],
        "state_history": [],
        "_derived": {},
    }


@pytest.fixture
def closed_task_board() -> dict:
    """A real CLOSED task-board (tank-battle) for backfill / e2e tests."""
    p = TASK_BOARDS_DIR / "p-tank-battle-20260426T082459Z.json"
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def xs_task_board(empty_task_board) -> dict:
    """size=XS task-board (Route A — should skip pipeline_graph emit)."""
    empty_task_board["size"] = "XS"
    empty_task_board["route_id"] = "A"
    empty_task_board["task_type"] = "纯代码"
    empty_task_board["risk"] = "低"
    return empty_task_board
```

- [ ] **Step 4: Verify pytest finds the tests dir**

Run: `cd /Users/zhongtianyi/work/code/harnessFlow && pytest -q`
Expected: `no tests ran in 0.0Xs` (zero collected, exit code 5 — empty test suite)

- [ ] **Step 5: Commit Phase 0**

```bash
cd /Users/zhongtianyi/work/code/harnessFlow
git add pytest.ini tests/__init__.py tests/conftest.py pipelines/__init__.py
git commit -m "test(harnessFlow): scaffold pytest + tests/ + pipelines/ for Slice A

Foundation for Slice A implementation: pytest config, conftest with
empty/closed/xs task-board fixtures, empty pipelines/ package.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 1: M1 — 13_node_contract.yaml + contract_loader

### Task 1.1: 13 节点 yaml 契约表落盘

**Files:**
- Create: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/13_node_contract.yaml`

The yaml contains 13 node entries. Each node entry follows the schema defined in spec § 3.1. To keep the plan readable, the full yaml is generated by **the implementer** following:

1. Source-of-truth for node IDs / names / phases / steps / layouts: `ui/backend/pipeline_catalog.py:NODE_CATALOG`（已部署 13 节点的现成数据，prefer to mirror exactly）
2. Per-node fields to author manually: `inputs_required[]`, `outputs_produced[]`, `writes_to_field`, `gate_predicate`, `supervisor_pulse_code`, `dashboard_card_mapping`, `edges_out`

- [ ] **Step 1: Author yaml header + N1 entry**

```yaml
# pipelines/13_node_contract.yaml
# Slice A 单一真相源 — 13 节点 PMP 5 阶段全集契约
# 引用：docs/superpowers/specs/2026-04-26-pipeline-graph-A-design.md § 3
schema_version: "1.0"
nodes:
  - node_id: N1
    step: 1
    phase: initiating
    name: 任务采集
    code: task_intake
    owner_skill: superpowers:brainstorming + harnessFlow §2 bootstrap
    layout: { x: 15, y: 170, w: 105, h: 60 }
    inputs_required:
      - { field: initial_user_input, must_exist: true }
    outputs_produced:
      - field: _derived.delivery_goal.user_initial_prompt
        must_exist: true
      - field: task_id
        must_exist: true
    writes_to_field:
      - _derived.delivery_goal.user_initial_prompt
    gate_predicate:
      expression: "task_id != null AND _derived.delivery_goal.user_initial_prompt != null"
      on_fail: BLOCK
    supervisor_pulse_code: node_passed_N1
    dashboard_card_mapping: [delivery_goal]
    edges_out:
      - { to: N2, kind: forward }
```

- [ ] **Step 2: Add N2-N4 (Initiating phase remainder)**

Append to yaml. N2 (资料收集) writes `_derived.project_library.{docs,repos,process_docs}`; N3 (目标分析锁定) writes `goal_anchor` + `_derived.delivery_goal.locked_goal`; N4 (项目章程) writes `_derived.charter`. Each gets its own gate_predicate (e.g. for N2: `len(_derived.project_library.docs) >= 1 OR len(_derived.project_library.repos) >= 1`). Edges: N2→N3 forward; N3→N4 forward; N4→N5 forward; N3 has rollback edge from N4 with label "PRD 写不出".

(Concrete templates for N2-N4 mirror N1's structure; refer to `ui/backend/pipeline_catalog.py:NODE_CATALOG[1:4]` for inputs/outputs.)

- [ ] **Step 3: Add N5-N10 (Planning phase)**

N5 (PRD 编写) → `_derived.prd`; N6 (TDD 用例设计) → `tdd_cases.definitions[]`; N7 (详细技术方案) → `_derived.tech_design`; N8 (范围收口 converge) → `_derived.scope.{in_scope, out_of_scope}`; N9 (WBS 拆解) → `_derived.wbs[]`; N10 (执行计划) → `_derived.execution_plan`.

**Critical edges**:
- N5→N6 `kind: parallel_split`
- N5→N7 `kind: parallel_split`
- N6→N8 `kind: converge`
- N7→N8 `kind: converge`
- N5→N5 (self via rollback from N6) `kind: rollback` `label: "PRD 写不出"`

- [ ] **Step 4: Add N11-N13 (Executing / M&C / Closing)**

N11 (项目开发 LOOP) → `loop_history[]` + `stage_artifacts[]` + `tdd_cases.execution_results[]`; N12 (质量验证) → `verifier_report` + `dod_expression`; N13 (收尾归档) → `commit_sha` + `retro_link` + `archive_entry_link`.

**Critical edges**:
- N11→N6 `kind: augment` `label: "↩ 补 TDD"`
- N12→N11 `kind: rollback` `label: "FAIL → 重 loop"`
- N13→N12 `kind: rollback` `label: "commit/PR fail"`

For N12 gate_predicate: `verifier_report.verdict == 'PASS' AND len(verifier_report.red_lines_detected) == 0`.

- [ ] **Step 5: Verify yaml parses cleanly**

Run:
```bash
cd /Users/zhongtianyi/work/code/harnessFlow
python3 -c "import yaml; data = yaml.safe_load(open('pipelines/13_node_contract.yaml')); print('node_count:', len(data['nodes'])); ids = [n['node_id'] for n in data['nodes']]; print('ids:', ids)"
```
Expected output:
```
node_count: 13
ids: ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'N10', 'N11', 'N12', 'N13']
```

If `ModuleNotFoundError: yaml`, run `pip install pyyaml` first.

### Task 1.2: TDD contract_loader.load_contract()

**Files:**
- Test: `/Users/zhongtianyi/work/code/harnessFlow/tests/test_contract_loader.py`
- Create: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/contract_loader.py`

- [ ] **Step 1: Write failing test for load_contract**

`tests/test_contract_loader.py`:
```python
"""Tests for pipelines.contract_loader."""
from __future__ import annotations

import pytest

from pipelines.contract_loader import load_contract, get_node_def, NodeDef


def test_load_contract_returns_13_nodes():
    contract = load_contract()
    assert len(contract.nodes) == 13


def test_load_contract_node_ids_are_n1_through_n13():
    contract = load_contract()
    ids = [n.node_id for n in contract.nodes]
    assert ids == [f"N{i}" for i in range(1, 14)]


def test_get_node_def_returns_n3_correctly():
    n3 = get_node_def("N3")
    assert isinstance(n3, NodeDef)
    assert n3.name == "目标分析+锁定"
    assert n3.phase == "initiating"
    assert "delivery_goal" in n3.dashboard_card_mapping


def test_get_node_def_unknown_id_raises():
    with pytest.raises(KeyError, match="N99"):
        get_node_def("N99")
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd /Users/zhongtianyi/work/code/harnessFlow && pytest tests/test_contract_loader.py -v`
Expected: ImportError or ModuleNotFoundError on `from pipelines.contract_loader import ...` (4 errors)

- [ ] **Step 3: Implement contract_loader minimum**

`pipelines/contract_loader.py`:
```python
"""Slice A — 13_node_contract.yaml loader and runtime helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONTRACT_PATH = Path(__file__).resolve().parent / "13_node_contract.yaml"


@dataclass
class NodeDef:
    node_id: str
    step: int
    phase: str
    name: str
    code: str
    owner_skill: str
    layout: dict
    inputs_required: list[dict]
    outputs_produced: list[dict]
    writes_to_field: list[str]
    gate_predicate: dict
    supervisor_pulse_code: str
    dashboard_card_mapping: list[str] = field(default_factory=list)
    edges_out: list[dict] = field(default_factory=list)


@dataclass
class Contract:
    schema_version: str
    nodes: list[NodeDef]


@lru_cache(maxsize=1)
def load_contract() -> Contract:
    with CONTRACT_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    nodes = [NodeDef(**n) for n in raw["nodes"]]
    return Contract(schema_version=raw["schema_version"], nodes=nodes)


def get_node_def(node_id: str) -> NodeDef:
    for n in load_contract().nodes:
        if n.node_id == node_id:
            return n
    raise KeyError(f"unknown node_id: {node_id}")
```

- [ ] **Step 4: Run tests — expect all 4 to pass**

Run: `cd /Users/zhongtianyi/work/code/harnessFlow && pytest tests/test_contract_loader.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit Task 1.2**

```bash
git add pipelines/13_node_contract.yaml pipelines/contract_loader.py tests/test_contract_loader.py
git commit -m "feat(slice-a): contract_loader.load_contract() + 13_node yaml

M1 first half: yaml 单一真相源 + dataclass 加载器。NodeDef 含 8 字段
（inputs_required / outputs_produced / writes_to_field / gate_predicate
/ supervisor_pulse_code / dashboard_card_mapping / edges_out / 元数据）。
get_node_def() 提供 O(N) 节点查询；后续 emit_pipeline_graph + validate_node_io
基于此构建。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 1.3: TDD emit_pipeline_graph()

**Files:**
- Test: `/Users/zhongtianyi/work/code/harnessFlow/tests/test_contract_loader.py`（追加）
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/contract_loader.py`

- [ ] **Step 1: Write failing test for emit_pipeline_graph (non-XS task)**

Append to `tests/test_contract_loader.py`:
```python
from pipelines.contract_loader import emit_pipeline_graph


def test_emit_pipeline_graph_for_size_m_writes_13_nodes(empty_task_board):
    graph = emit_pipeline_graph(empty_task_board)
    assert graph is not None
    assert len(graph["nodes"]) == 13
    assert all(n["status"] == "pending" for n in graph["nodes"])


def test_emit_pipeline_graph_size_xs_returns_none(xs_task_board):
    """A 路线 (size=XS) 豁免 pipeline_graph emit。"""
    graph = emit_pipeline_graph(xs_task_board)
    assert graph is None


def test_emit_pipeline_graph_includes_edges(empty_task_board):
    graph = emit_pipeline_graph(empty_task_board)
    edge_kinds = {e["kind"] for e in graph["edges"]}
    assert "forward" in edge_kinds
    assert "parallel_split" in edge_kinds
    assert "converge" in edge_kinds
    assert "rollback" in edge_kinds
```

- [ ] **Step 2: Run tests — expect 3 failures (function not defined)**

Run: `pytest tests/test_contract_loader.py::test_emit_pipeline_graph_for_size_m_writes_13_nodes tests/test_contract_loader.py::test_emit_pipeline_graph_size_xs_returns_none tests/test_contract_loader.py::test_emit_pipeline_graph_includes_edges -v`
Expected: 3 errors with `ImportError: cannot import name 'emit_pipeline_graph'`

- [ ] **Step 3: Implement emit_pipeline_graph**

Append to `pipelines/contract_loader.py`:
```python
def emit_pipeline_graph(task_board: dict) -> dict | None:
    """Emit pipeline_graph[] blueprint at ROUTE_SELECT → IMPL boundary.

    Returns None for size=XS (Route A 豁免)；otherwise returns
    {nodes:[...13...], edges:[...], emitted_at, schema_version}.
    """
    if task_board.get("size") == "XS":
        return None

    contract = load_contract()
    nodes_view = []
    all_edges: list[dict] = []
    for nd in contract.nodes:
        nodes_view.append({
            "node_id": nd.node_id,
            "step": nd.step,
            "phase": nd.phase,
            "name": nd.name,
            "owner_skill": nd.owner_skill,
            "layout": dict(nd.layout),
            "writes_to_field": list(nd.writes_to_field),
            "status": "pending",
            "started_at": None,
            "completed_at": None,
        })
        for e in nd.edges_out:
            all_edges.append({
                "from": nd.node_id,
                "to": e["to"],
                "kind": e.get("kind", "forward"),
                "label": e.get("label"),
            })

    from datetime import datetime, timezone
    return {
        "schema_version": contract.schema_version,
        "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nodes": nodes_view,
        "edges": all_edges,
    }
```

- [ ] **Step 4: Run tests — expect all to pass**

Run: `pytest tests/test_contract_loader.py -v`
Expected: 7 passed (4 prior + 3 new)

- [ ] **Step 5: Commit Task 1.3**

```bash
git add tests/test_contract_loader.py pipelines/contract_loader.py
git commit -m "feat(slice-a): emit_pipeline_graph() + size=XS 豁免

M1 second half: 主 skill 在 ROUTE_SELECT → IMPL 边调用 emit；返回 None
对应 A 路线豁免（state-machine § 8.1 既有低频 tick 模式不变）。Output 含
13 nodes + edges (forward/parallel_split/converge/rollback) + emitted_at +
schema_version。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 2: M4 (前移) — gate_eval + node validate

### Task 2.1: TDD gate_eval — basic expressions

**Files:**
- Test: `/Users/zhongtianyi/work/code/harnessFlow/tests/test_gate_eval.py`
- Create: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/gate_eval.py`

- [ ] **Step 1: Write failing tests for gate_eval**

`tests/test_gate_eval.py`:
```python
"""Tests for pipelines.gate_eval — gate_predicate AST evaluator."""
from __future__ import annotations

import pytest

from pipelines.gate_eval import eval_predicate, GateEvalError


def test_eval_simple_not_null():
    ctx = {"task_id": "test-001"}
    assert eval_predicate("task_id != null", ctx) is True


def test_eval_null_field_returns_false():
    ctx = {"task_id": None}
    assert eval_predicate("task_id != null", ctx) is False


def test_eval_nested_field_path():
    ctx = {"goal_anchor": {"hash": "deadbeef"}}
    assert eval_predicate("goal_anchor.hash != null", ctx) is True


def test_eval_and_combinator():
    ctx = {"a": 1, "b": 2}
    assert eval_predicate("a != null AND b != null", ctx) is True


def test_eval_and_one_false():
    ctx = {"a": 1, "b": None}
    assert eval_predicate("a != null AND b != null", ctx) is False


def test_eval_or_combinator():
    ctx = {"a": None, "b": 2}
    assert eval_predicate("a != null OR b != null", ctx) is True


def test_eval_string_comparison():
    ctx = {"verdict": "PASS"}
    assert eval_predicate("verdict == 'PASS'", ctx) is True


def test_eval_forbidden_import_raises():
    with pytest.raises(GateEvalError, match="forbidden"):
        eval_predicate("__import__('os').system('ls')", {})


def test_eval_forbidden_lambda_raises():
    with pytest.raises(GateEvalError, match="forbidden"):
        eval_predicate("lambda x: x", {})
```

- [ ] **Step 2: Run tests — expect 9 failures**

Run: `pytest tests/test_gate_eval.py -v`
Expected: 9 errors with `ImportError`

- [ ] **Step 3: Implement gate_eval (white-list AST)**

`pipelines/gate_eval.py`:
```python
"""Slice A — gate_predicate evaluator (white-listed AST)."""
from __future__ import annotations

import ast
from typing import Any


class GateEvalError(Exception):
    pass


_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.Compare, ast.Name, ast.Constant,
    ast.Attribute, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
    ast.Gt, ast.GtE, ast.Load,
)


def _resolve(name_or_attr: ast.AST, ctx: dict) -> Any:
    """Resolve `a.b.c` → ctx['a']['b']['c'], returning None if any missing."""
    parts: list[str] = []
    n = name_or_attr
    while isinstance(n, ast.Attribute):
        parts.insert(0, n.attr)
        n = n.value
    if not isinstance(n, ast.Name):
        raise GateEvalError(f"unsupported lvalue: {ast.dump(n)}")
    parts.insert(0, n.id)
    cur: Any = ctx
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur


def _eval(node: ast.AST, ctx: dict) -> Any:
    if not isinstance(node, _ALLOWED_NODES):
        raise GateEvalError(f"forbidden AST node: {type(node).__name__}")
    if isinstance(node, ast.Expression):
        return _eval(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Name, ast.Attribute)):
        return _resolve(node, ctx)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, ctx) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(vals)
        if isinstance(node.op, ast.Or):
            return any(vals)
        raise GateEvalError(f"forbidden BoolOp: {type(node.op).__name__}")
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ctx)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, ctx)
            if isinstance(op, ast.Eq):
                if not (left == right):
                    return False
            elif isinstance(op, ast.NotEq):
                if not (left != right):
                    return False
            elif isinstance(op, ast.Lt):
                if not (left is not None and right is not None and left < right):
                    return False
            elif isinstance(op, ast.LtE):
                if not (left is not None and right is not None and left <= right):
                    return False
            elif isinstance(op, ast.Gt):
                if not (left is not None and right is not None and left > right):
                    return False
            elif isinstance(op, ast.GtE):
                if not (left is not None and right is not None and left >= right):
                    return False
            else:
                raise GateEvalError(f"forbidden cmp op: {type(op).__name__}")
            left = right
        return True
    raise GateEvalError(f"unhandled node: {type(node).__name__}")


def eval_predicate(expr: str, ctx: dict) -> bool:
    """Eval a gate_predicate expression against task-board ctx.

    `null` literal → Python None. AND/OR (uppercase) accepted as alias.
    """
    normalized = expr.replace(" AND ", " and ").replace(" OR ", " or ").replace("null", "None")
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as e:
        raise GateEvalError(f"parse error: {e}")
    result = _eval(tree, ctx)
    return bool(result)
```

- [ ] **Step 4: Run tests — expect 9 passes**

Run: `pytest tests/test_gate_eval.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit Task 2.1**

```bash
git add tests/test_gate_eval.py pipelines/gate_eval.py
git commit -m "feat(slice-a): gate_eval — white-listed AST predicate evaluator

M4 第一半：纯 Python AST 白名单 eval（禁 lambda / import / eval / exec）。
支持 ==/!=/</<=/>/>=, AND/OR, null literal, 嵌套字段路径 (a.b.c)。
后续 validate_node_io 据此判 BLOCK。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 2.2: TDD validate_node_io

**Files:**
- Test: `/Users/zhongtianyi/work/code/harnessFlow/tests/test_node_validate.py`
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/contract_loader.py`

- [ ] **Step 1: Write failing tests for validate_node_io**

`tests/test_node_validate.py`:
```python
"""Tests for validate_node_io enter/exit + gate_predicate enforcement."""
from __future__ import annotations

import pytest

from pipelines.contract_loader import validate_node_io


def test_validate_enter_missing_required_input_blocks(empty_task_board):
    # N3 requires goal_anchor.hash and initial_user_input
    empty_task_board.pop("goal_anchor", None)
    empty_task_board.pop("initial_user_input", None)
    verdict, violations = validate_node_io(empty_task_board, "N3", phase="enter")
    assert verdict == "BLOCK"
    assert any("initial_user_input" in v.get("field", "") for v in violations) or \
           any("goal_anchor" in v.get("field", "") for v in violations)


def test_validate_enter_with_inputs_returns_ok(empty_task_board):
    empty_task_board["initial_user_input"] = "做个坦克游戏"
    verdict, _ = validate_node_io(empty_task_board, "N3", phase="enter")
    assert verdict == "OK"


def test_validate_exit_gate_predicate_fail_blocks(empty_task_board):
    """N3 exit gate fails when delivery_goal.locked_goal is empty."""
    empty_task_board["initial_user_input"] = "x"
    empty_task_board["_derived"] = {"delivery_goal": {"locked_goal": ""}}
    verdict, violations = validate_node_io(empty_task_board, "N3", phase="exit")
    assert verdict == "BLOCK"
    assert any("gate_predicate" in v.get("reason", "") for v in violations)


def test_validate_exit_gate_predicate_pass_returns_ok(empty_task_board):
    empty_task_board["_derived"] = {
        "delivery_goal": {"locked_goal": "做个坦克大战网页小游戏"}
    }
    verdict, _ = validate_node_io(empty_task_board, "N3", phase="exit")
    assert verdict == "OK"
```

- [ ] **Step 2: Run tests — expect 4 failures**

Run: `pytest tests/test_node_validate.py -v`
Expected: 4 errors with ImportError

- [ ] **Step 3: Implement validate_node_io**

Append to `pipelines/contract_loader.py`:
```python
from pipelines.gate_eval import eval_predicate, GateEvalError


def _resolve_field(task_board: dict, field_path: str) -> Any:
    cur: Any = task_board
    for p in field_path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur


def validate_node_io(
    task_board: dict, node_id: str, phase: str
) -> tuple[str, list[dict]]:
    """Slice A node-level enter/exit gate.

    phase: 'enter' or 'exit'
    returns: (verdict, violations[])
      verdict: 'OK' | 'BLOCK'
      violations: list of {field, reason}
    """
    nd = get_node_def(node_id)
    violations: list[dict] = []

    if phase == "enter":
        for req in nd.inputs_required:
            if not req.get("must_exist"):
                continue
            field = req["field"]
            val = _resolve_field(task_board, field)
            empty = val is None or val == "" or val == [] or val == {}
            if empty:
                violations.append({
                    "field": field,
                    "reason": "required input missing or empty",
                })
        return ("BLOCK" if violations else "OK", violations)

    if phase == "exit":
        for out in nd.outputs_produced:
            if not out.get("must_exist"):
                continue
            field = out["field"]
            val = _resolve_field(task_board, field)
            if val is None:
                violations.append({
                    "field": field,
                    "reason": "declared output not produced",
                })
        if not violations:
            try:
                ok = eval_predicate(nd.gate_predicate["expression"], task_board)
            except GateEvalError as e:
                ok = False
                violations.append({"field": "_gate", "reason": f"gate_predicate parse error: {e}"})
            if not ok:
                violations.append({
                    "field": "_gate",
                    "reason": f"gate_predicate failed: {nd.gate_predicate['expression']}",
                })
        on_fail = nd.gate_predicate.get("on_fail", "BLOCK")
        return (on_fail if violations else "OK", violations)

    raise ValueError(f"unknown phase: {phase}")
```

- [ ] **Step 4: Run tests — expect 4 passes**

Run: `pytest tests/test_node_validate.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit Task 2.2**

```bash
git add tests/test_node_validate.py pipelines/contract_loader.py
git commit -m "feat(slice-a): validate_node_io enter/exit + gate_predicate enforce

M4 第二半：节点级 BLOCK runtime（Q1=A 严格）。enter 缺 required input →
BLOCK；exit 缺 declared output 或 gate_predicate eval=false → BLOCK；
violations 列出具体字段供 supervisor DOD_GAP_ALERT 用。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 3: M5 — card_emptiness + dashboard 派生 + frontend 黄警示

### Task 3.1: TDD card_emptiness 6 卡判断

**Files:**
- Test: `/Users/zhongtianyi/work/code/harnessFlow/tests/test_card_emptiness.py`
- Create: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/card_emptiness.py`

- [ ] **Step 1: Write failing tests for is_card_empty**

`tests/test_card_emptiness.py`:
```python
"""Tests for pipelines.card_emptiness — 6 dashboard cards emptiness check."""
from __future__ import annotations

from pipelines.card_emptiness import is_card_empty, derive_card_states, CARD_NODE_MAP


def test_card_node_map_has_six_entries():
    assert set(CARD_NODE_MAP.keys()) == {
        "delivery_goal", "scope", "project_library",
        "tdd", "supervision", "wbs",
    }


def test_delivery_goal_empty_when_locked_goal_missing(empty_task_board):
    assert is_card_empty("delivery_goal", empty_task_board) is True


def test_delivery_goal_filled(empty_task_board):
    empty_task_board["_derived"] = {"delivery_goal": {"locked_goal": "X"}}
    assert is_card_empty("delivery_goal", empty_task_board) is False


def test_project_library_empty_when_under_3_total(empty_task_board):
    empty_task_board["_derived"] = {"project_library": {"docs": [{"x": 1}], "repos": []}}
    assert is_card_empty("project_library", empty_task_board) is True


def test_project_library_filled_when_total_ge_3(empty_task_board):
    empty_task_board["_derived"] = {
        "project_library": {"docs": [{}, {}], "repos": [{}], "process_docs": []}
    }
    assert is_card_empty("project_library", empty_task_board) is False


def test_wbs_empty_when_array_empty(empty_task_board):
    empty_task_board["_derived"] = {"wbs": []}
    assert is_card_empty("wbs", empty_task_board) is True


def test_supervision_empty_when_no_interventions(empty_task_board):
    empty_task_board["supervisor_interventions"] = []
    empty_task_board["red_lines"] = []
    assert is_card_empty("supervision", empty_task_board) is True


def test_derive_card_states_returns_six_entries(empty_task_board):
    states = derive_card_states(empty_task_board)
    assert len(states) == 6
    assert all("card_id" in s and "is_empty" in s and "waiting_for_node" in s for s in states)
```

- [ ] **Step 2: Run tests — expect 8 failures**

Run: `pytest tests/test_card_emptiness.py -v`
Expected: 8 errors with ImportError

- [ ] **Step 3: Implement card_emptiness**

`pipelines/card_emptiness.py`:
```python
"""Slice A — 6 dashboard cards emptiness detection (Q5=A 黄警示数据源)."""
from __future__ import annotations

from typing import Any

# Map: card_id → (responsible_node_id, node_name, is_empty_predicate)
CARD_NODE_MAP: dict[str, tuple[str, str]] = {
    "delivery_goal":    ("N3", "目标分析+锁定"),
    "scope":            ("N8", "范围收口"),
    "project_library":  ("N2", "资料收集"),
    "tdd":              ("N6", "TDD 用例设计"),
    "supervision":      ("N12", "质量验证"),  # accumulating across nodes; assigned to N12 for waiting label
    "wbs":              ("N9", "WBS 拆解"),
}


def _resolve(tb: dict, path: str) -> Any:
    cur: Any = tb
    for p in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur


def is_card_empty(card_id: str, task_board: dict) -> bool:
    """Return True if the card has no/insufficient data to display."""
    if card_id == "delivery_goal":
        v = _resolve(task_board, "_derived.delivery_goal.locked_goal")
        return not v  # None or ""
    if card_id == "scope":
        in_s = _resolve(task_board, "_derived.scope.in_scope") or []
        out_s = _resolve(task_board, "_derived.scope.out_of_scope") or []
        return len(in_s) == 0 and len(out_s) == 0
    if card_id == "project_library":
        docs = _resolve(task_board, "_derived.project_library.docs") or []
        repos = _resolve(task_board, "_derived.project_library.repos") or []
        process = _resolve(task_board, "_derived.project_library.process_docs") or []
        return (len(docs) + len(repos) + len(process)) < 3
    if card_id == "tdd":
        defs = _resolve(task_board, "tdd_cases.definitions") or []
        # legacy compat: tdd_cases may be list (not dict)
        if not defs and isinstance(task_board.get("tdd_cases"), list):
            return len(task_board["tdd_cases"]) == 0
        return len(defs) == 0
    if card_id == "supervision":
        interventions = task_board.get("supervisor_interventions") or []
        red = task_board.get("red_lines") or []
        return len(interventions) == 0 and len(red) == 0
    if card_id == "wbs":
        wbs = _resolve(task_board, "_derived.wbs") or []
        return len(wbs) == 0
    raise KeyError(f"unknown card_id: {card_id}")


def derive_card_states(task_board: dict) -> list[dict]:
    """Return list of 6 entries: {card_id, is_empty, waiting_for_node, waiting_for_node_name}."""
    out = []
    for card_id, (node_id, node_name) in CARD_NODE_MAP.items():
        empty = is_card_empty(card_id, task_board)
        out.append({
            "card_id": card_id,
            "is_empty": empty,
            "waiting_for_node": node_id if empty else None,
            "waiting_for_node_name": node_name if empty else None,
        })
    return out
```

- [ ] **Step 4: Run tests — expect 8 passes**

Run: `pytest tests/test_card_emptiness.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit Task 3.1**

```bash
git add tests/test_card_emptiness.py pipelines/card_emptiness.py
git commit -m "feat(slice-a): card_emptiness — 6 dashboard cards 黄警示数据源

M5 第一半：6 卡 ↔ 节点映射 + emptiness 判据。delivery_goal/scope/
project_library/tdd/supervision/wbs 各自检测；project_library 阈值 < 3
（spec § 3.2）；输出 derive_card_states() 供 mock_data.py 注入到
_derived.cards[]。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 3.2: 接入 mock_data.py + frontend 黄警示

**Files:**
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/ui/backend/mock_data.py`（加 `_derived.cards`）
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/ui/frontend/index.html`（黄警示样式）

- [ ] **Step 1: Modify mock_data.py to add `_derived.cards`**

In `_enrich_task_board()` (line ~257), add `cards` key.

Locate the block:
```python
    data["_derived"] = {
        "summary": _derive_summary(data),
        "delivery_goal": _derive_delivery_goal(data),
        ...
        "supervision": _derive_supervision(data),
    }
```

Add at the top of the file imports (line ~34, after the existing `from pipeline_catalog import` line):
```python
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.card_emptiness import derive_card_states
```

Then after the `data["_derived"] = {...}` block, append:
```python
    data["_derived"]["cards"] = derive_card_states(data)
```

- [ ] **Step 2: Smoke test the API**

Run:
```bash
cd /Users/zhongtianyi/work/code/harnessFlow/ui/backend && python -c "
from mock_data import get_task_board
import json
tb = get_task_board('p-tank-battle-20260426T082459Z')
print(json.dumps(tb['_derived']['cards'], indent=2, ensure_ascii=False))
"
```
Expected: 6 entries, tank-battle is CLOSED so most cards filled (`is_empty: false`); some may still be empty (e.g. tdd if no `_derived.tdd`).

- [ ] **Step 3: Add yellow warning style to index.html**

In `/Users/zhongtianyi/work/code/harnessFlow/ui/frontend/index.html`, locate `<style>` block (search for `.pl-node-rect` and add nearby):

```html
<!-- Slice A 黄警示样式 -->
<style>
  .card-empty-warning {
    border: 1px solid #e6a23c !important;
    background: #fdf6ec !important;
  }
  .card-empty-hint {
    color: #b88230;
    font-size: 11px;
    padding: 6px 10px;
    background: #fdf6ec;
    border-radius: 3px;
    margin-top: 6px;
  }
</style>
```

- [ ] **Step 4: Render emptiness on the 6 cards in drawer**

In the drawer's "📊 本任务实际数据" section, find the 6 card render blocks (already exist as separate `<div>`s for delivery_goal / scope / project_library / tdd / supervision / wbs).

For each card (e.g. delivery_goal), wrap with:
```html
<div :class="cardWarningClass('delivery_goal')">
  <!-- existing card content -->
  <div v-if="isCardEmpty('delivery_goal')" class="card-empty-hint">
    ⚠️ 等待 {{ cardWaitingNode('delivery_goal') }} · {{ cardWaitingNodeName('delivery_goal') }} 写入
  </div>
</div>
```

Add helpers in `setup()` block (where `pipelineFullscreen` is declared):
```javascript
const cardStates = computed(() => (detail.value?._derived?.cards) || []);
const findCard = (id) => cardStates.value.find(c => c.card_id === id) || {};
const isCardEmpty = (id) => !!findCard(id).is_empty;
const cardWaitingNode = (id) => findCard(id).waiting_for_node || '';
const cardWaitingNodeName = (id) => findCard(id).waiting_for_node_name || '';
const cardWarningClass = (id) => isCardEmpty(id) ? 'card-empty-warning' : '';
```

Add to setup() return:
```javascript
isCardEmpty, cardWaitingNode, cardWaitingNodeName, cardWarningClass, cardStates,
```

- [ ] **Step 5: Verify in browser via Playwright**

Run (assumes backend already up on :8765):
- Navigate `http://127.0.0.1:8765/?task=p-tank-battle-20260426T082459Z`
- Click pipeline node N3 → drawer opens → 📊 section shows delivery_goal card filled (no warning, since tank-battle is CLOSED with locked_goal set)
- Pick a half-done task (e.g. `e2e-hello-walkthrough-20260426T062858Z` or any with current_state ≠ CLOSED) → expect at least 1 card with yellow warning border

- [ ] **Step 6: Commit Task 3.2**

```bash
git add ui/backend/mock_data.py ui/frontend/index.html
git commit -m "feat(slice-a): wire card_emptiness into dashboard 6 卡黄警示

M5 第二半：mock_data.py 注入 _derived.cards[]；index.html 加
.card-empty-warning 黄边样式 + '⚠️ 等待 N<id> · <name> 写入' 文案。
半成品任务即可看到缺失卡片高亮，符合 Q5=A 设计。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 4: M6 — backfill 历史 task

### Task 4.1: TDD backfill_pipeline_graph

**Files:**
- Test: `/Users/zhongtianyi/work/code/harnessFlow/tests/test_backfill.py`
- Create: `/Users/zhongtianyi/work/code/harnessFlow/scripts/backfill_pipeline_graph.py`

- [ ] **Step 1: Write failing tests**

`tests/test_backfill.py`:
```python
"""Tests for scripts/backfill_pipeline_graph.py — historical task replay."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backfill_pipeline_graph import backfill_one


def test_backfill_closed_marks_all_nodes_passed(closed_task_board):
    out = backfill_one(closed_task_board)
    pg = out["_derived"]["pipeline"]
    assert pg is not None
    assert all(n["status"] == "passed" for n in pg["nodes"])


def test_backfill_aborted_marks_last_node_failed():
    tb = {
        "task_id": "x", "size": "M", "task_type": "后端 feature", "risk": "中",
        "current_state": "ABORTED",
        "state_history": [
            {"state": "INIT", "timestamp": "t0"},
            {"state": "IMPL", "timestamp": "t1"},
            {"state": "ABORTED", "timestamp": "t2"},
        ],
        "stage_artifacts": [],
        "_derived": {},
    }
    out = backfill_one(tb)
    pg = out["_derived"]["pipeline"]
    failed_nodes = [n for n in pg["nodes"] if n["status"] == "failed"]
    assert len(failed_nodes) >= 1


def test_backfill_size_xs_skips():
    tb = {
        "task_id": "y", "size": "XS", "task_type": "纯代码", "risk": "低",
        "current_state": "CLOSED",
        "state_history": [], "stage_artifacts": [],
    }
    out = backfill_one(tb)
    assert out["_derived"].get("pipeline") is None
```

- [ ] **Step 2: Run tests — expect 3 failures**

Run: `pytest tests/test_backfill.py -v`
Expected: 3 errors (import / module not found)

- [ ] **Step 3: Implement backfill script**

`scripts/backfill_pipeline_graph.py`:
```python
"""One-shot script: backfill _derived.pipeline for archived task-boards.

Reads task-boards/*.json, derives pipeline_graph view from state_history +
stage_artifacts, writes back to _derived.pipeline (does NOT touch original
task_board fields).

Usage:
    python scripts/backfill_pipeline_graph.py --dry-run
    python scripts/backfill_pipeline_graph.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines.contract_loader import emit_pipeline_graph

TASK_BOARDS_DIR = REPO_ROOT / "task-boards"
SKIP_LOG = REPO_ROOT / "archive" / "backfill-skipped.jsonl"


def backfill_one(task_board: dict) -> dict:
    """Compute _derived.pipeline (do not mutate original keys)."""
    pg = emit_pipeline_graph(task_board)
    if pg is None:
        task_board.setdefault("_derived", {})["pipeline"] = None
        return task_board

    state = task_board.get("current_state", "INIT")
    state_history = task_board.get("state_history") or []

    # Map state → step (rough)
    state_to_step = {
        "INIT": 1, "CLARIFY": 3, "ROUTE_SELECT": 4, "PLAN": 10,
        "IMPL": 11, "MID_CHECKPOINT": 11, "MID_RETRO": 11,
        "VERIFY": 12, "SANTA_LOOP": 11, "COMMIT": 13,
        "RETRO_CLOSE": 13, "CLOSED": 13, "ABORTED": 0,
        "PAUSED_ESCALATED": 11,
    }
    last_step = state_to_step.get(state, 0)

    if state == "CLOSED":
        for n in pg["nodes"]:
            n["status"] = "passed"
    elif state == "ABORTED":
        # Last reached step → failed; rest pending
        last_real = next(
            (e["state"] for e in reversed(state_history)
             if e.get("state") not in ("ABORTED", "PAUSED_ESCALATED")),
            None,
        )
        last_step = state_to_step.get(last_real or "", 0)
        for n in pg["nodes"]:
            if n["step"] < last_step:
                n["status"] = "passed"
            elif n["step"] == last_step:
                n["status"] = "failed"
            else:
                n["status"] = "pending"
    else:  # in-progress / PAUSED_ESCALATED
        for n in pg["nodes"]:
            if n["step"] < last_step:
                n["status"] = "passed"
            elif n["step"] == last_step:
                n["status"] = "running"
            else:
                n["status"] = "pending"

    task_board.setdefault("_derived", {})["pipeline"] = pg
    return task_board


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print stats; no writes")
    ap.add_argument("--apply", action="store_true", help="write back to disk")
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        ap.error("must pass --dry-run or --apply")

    SKIP_LOG.parent.mkdir(parents=True, exist_ok=True)
    processed, skipped = 0, 0
    for p in sorted(TASK_BOARDS_DIR.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            with p.open("r", encoding="utf-8") as f:
                tb = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            with SKIP_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"path": str(p), "error": str(e)}) + "\n")
            skipped += 1
            continue
        try:
            backfill_one(tb)
        except Exception as e:
            with SKIP_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"path": str(p), "error": str(e)}) + "\n")
            skipped += 1
            continue
        processed += 1
        if args.apply:
            with p.open("w", encoding="utf-8") as f:
                json.dump(tb, f, indent=2, ensure_ascii=False)

    print(f"processed={processed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests — expect 3 passes**

Run: `pytest tests/test_backfill.py -v`
Expected: 3 passed

- [ ] **Step 5: Dry-run on real task-boards**

Run:
```bash
cd /Users/zhongtianyi/work/code/harnessFlow
python scripts/backfill_pipeline_graph.py --dry-run
```
Expected output: `processed=21 skipped=0` (matches the 21 files in `task-boards/`).

- [ ] **Step 6: Commit Task 4.1**

```bash
git add tests/test_backfill.py scripts/backfill_pipeline_graph.py
git commit -m "feat(slice-a): backfill_pipeline_graph 历史 task 一次性回填

M6: 读 task-boards/*.json，按 state_history 推 status (CLOSED→all passed /
ABORTED→last failed / 进行中→last running)，写到 _derived.pipeline。size=XS
跳过（A 路线豁免）。--dry-run 默认；--apply 写盘；解析失败写
archive/backfill-skipped.jsonl。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 4.2: 应用 backfill（生产数据写盘）

- [ ] **Step 1: Backup task-boards/ before mutating**

```bash
cd /Users/zhongtianyi/work/code/harnessFlow
cp -r task-boards task-boards.bak-$(date +%Y%m%d-%H%M%S)
```

- [ ] **Step 2: Run --apply**

```bash
python scripts/backfill_pipeline_graph.py --apply
```
Expected: `processed=21 skipped=0`

- [ ] **Step 3: Spot-check one task-board**

```bash
python -c "
import json
tb = json.load(open('task-boards/p-tank-battle-20260426T082459Z.json'))
pg = tb['_derived']['pipeline']
print('nodes:', len(pg['nodes']))
print('all passed:', all(n['status']=='passed' for n in pg['nodes']))
"
```
Expected: `nodes: 13` and `all passed: True`.

- [ ] **Step 4: Commit Task 4.2 (data write)**

```bash
git add task-boards/
git commit -m "data(slice-a): apply backfill_pipeline_graph to 21 历史 task-boards

应用 --apply 后：每 task-board 多 _derived.pipeline 字段（含 13 节点状态
overlay + edges）。dashboard 历史任务现可显示完整 pipeline 视图。task-boards.bak
已留作回滚保险（gitignore 不入库）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 5: M3 — task-board-template.md schema 文档

### Task 5.1: 加 5 字段 schema 到 template.md

**Files:**
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/task-board-template.md`

- [ ] **Step 1: Add `pipeline_graph[]` to § 1.2 (轨迹字段)**

Find the `stage_artifacts[]` row in § 1.2 and append a new row right after:

```markdown
| `pipeline_graph` | object `{schema_version, emitted_at, nodes[], edges[]}` | `null` | 主 skill `@PIPELINE_EMIT`（ROUTE_SELECT 后） | `pipelines.contract_loader.emit_pipeline_graph()` 一次性 emit | dashboard / Supervisor / Verifier | **Slice A 新增**：13-节点 PMP 蓝图，节点完成时 `nodes[i].status` += `passed/running/failed/rolled_back`；edges 含 forward/parallel_split/converge/rollback/augment |
| `supervision_graph` | object | `null` | （Slice C 落地） | — | — | **Slice C 占位**：6-节点监督流水线，本片仅 schema 占位不写入 |
| `prd` | object `{背景, 目标, 用户故事[], 功能[], 验收标准[], 原型链接, 技术方案, 风险[]}` | `null` | 主 skill `@PLAN`（C/E 路线） | N5 节点完成时 | dashboard / retro | **Slice A 新增**：阿里风 PRD 八段；A/B/D/F 路线 null |
| `execution_plan` | object `{wbs_ref, gantt[{wp_id, start, end, depends_on[]}]}` | `null` | 主 skill `@PLAN` | N10 节点完成时 | dashboard / retro | **Slice A 新增**：WBS 时间+顺序+依赖 |
| `tdd_cases.definitions[]` | array of `{case_id, given, when, then, priority}` | `[]` | 主 skill `@PLAN` | N6 节点完成时 | Verifier / dashboard TDD 卡 | **Slice A 拆分**：原 `tdd_cases[]` 的"定义"段，写在 N6 |
| `tdd_cases.execution_results[]` | array of `{case_id, status, evidence_path, executed_at}` | `[]` | 主 skill `@IMPL` / Verifier `@VERIFY` | N11 节点 loop 内 + N12 验证时 | retro | **Slice A 拆分**：原 `tdd_cases[]` 的"执行"段，写在 N11/N12 |
```

- [ ] **Step 2: Add detailed schema section §  1.2.x (mid-document)**

After § 1.2 table, before § 1.3, insert a new sub-section detailing the new fields' shape with concrete JSON examples (mirror style of stage_artifacts § 10 in stage-contracts.md).

```markdown
#### § 1.2.1 pipeline_graph 详细 schema（Slice A 新增）

```json
{
  "pipeline_graph": {
    "schema_version": "1.0",
    "emitted_at": "2026-04-26T18:30:00Z",
    "nodes": [
      {
        "node_id": "N3",
        "step": 3,
        "phase": "initiating",
        "name": "目标分析+锁定",
        "owner_skill": "superpowers:brainstorming",
        "layout": {"x": 255, "y": 170, "w": 105, "h": 60},
        "writes_to_field": ["goal_anchor", "_derived.delivery_goal.locked_goal"],
        "status": "passed",
        "started_at": "2026-04-26T18:31:10Z",
        "completed_at": "2026-04-26T18:33:42Z"
      }
    ],
    "edges": [
      {"from": "N5", "to": "N6", "kind": "parallel_split", "label": null},
      {"from": "N6", "to": "N8", "kind": "converge", "label": null},
      {"from": "N12", "to": "N11", "kind": "rollback", "label": "FAIL → 重 loop"}
    ]
  }
}
```

`nodes[i].status` 取值：`pending | running | passed | failed | rolled_back | augmenting`。

每节点完成时，主 skill 同时 append 一条 `state_history[]`（已存在）+ 写
`pipeline_graph.nodes[i]` 状态/时间戳，并触发 `supervisor_pulse_code`（见
`pipelines/13_node_contract.yaml`）spawn 一次 Supervisor pulse。

任一节点 `validate_node_io(phase='exit')` 返 BLOCK → `current_state →
PAUSED_ESCALATED`，节点 status 标 `failed`，Supervisor 写
`DOD_GAP_ALERT` 红线。
```

- [ ] **Step 3: Verify markdown renders cleanly**

Open in editor or run a markdown linter:
```bash
cd /Users/zhongtianyi/work/code/harnessFlow
grep -c "^| " task-board-template.md  # row count sanity
```
Expected: substantially more rows than before edit (e.g. +6).

- [ ] **Step 4: Commit Task 5.1**

```bash
git add task-board-template.md
git commit -m "doc(slice-a): task-board-template 加 5 字段 schema (M3)

新增 pipeline_graph / supervision_graph (占位) / prd / execution_plan /
tdd_cases.{definitions, execution_results}。每字段含 写入方/写入时机/读取方/
用途，对齐 Slice A § 3 节点契约。§ 1.2.1 给出 pipeline_graph 完整 JSON 示例。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 6: M2 — 主 skill prompt § 2.5 PIPELINE_EMIT

### Task 6.1: 编辑 harnessFlow-skill.md 加 § 2.5

**Files:**
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/harnessFlow-skill.md`

- [ ] **Step 1: Locate § 4 路由决策协议 — insert § 2.5 BEFORE it (logically belongs after CLARIFY/ROUTE_SELECT)**

Use Grep to find the exact line: `grep -n "^## § 4 路由决策协议\|^## § 5 执行调度" harnessFlow-skill.md`. Insert the new § 4.5 after § 4 (PIPELINE_EMIT happens after route is picked).

Open `harnessFlow-skill.md`, find the `^## § 5 执行调度` line; insert this block immediately before it:

```markdown
## § 4.5 Pipeline Bootstrap 协议（这章回答：路线选定后，怎么生成 pipeline_graph 蓝图）

对应状态机 `ROUTE_SELECT → PLAN`（边 E3 中段）；A 路线（size=XS）跳过本节直接进 § 5。

### 4.5.1 触发时机

`route_id` 已写入 task-board 的瞬间（即 § 4.3 用户 pick 后的下一步），主 skill **强制**：

1. 检查 `size != "XS"`；若 XS（A 路线）→ skip（state-machine § 8.1 既有低频 tick 模式不变）
2. 调 `pipelines.contract_loader.emit_pipeline_graph(task_board)`
3. 把返回的 13-node 蓝图写到 `task_board.pipeline_graph`
4. 写 task-board 加新 entry `state_history[] += {state: "PIPELINE_EMITTED", timestamp, trigger: "route_select_completed"}`（这是逻辑标记，不算独立 current_state）
5. 进 § 5 执行调度

### 4.5.2 节点级 BLOCK 强制（Q1=A）

§ 5.1 主循环改造：每 step（即每个 pipeline 节点）执行前后必须调
`pipelines.contract_loader.validate_node_io(task_board, node_id, phase)`：

```python
def execute_pipeline_node(node_id: str, task_board: dict):
    # 入口
    verdict, violations = validate_node_io(task_board, node_id, phase="enter")
    if verdict == "BLOCK":
        supervisor_log("BLOCK", "DOD_GAP_ALERT",
                       f"node {node_id} missing required inputs",
                       violations)
        transition(task_board, "PAUSED_ESCALATED")
        return False

    # 派发 owner_skill (read from contract)
    nd = get_node_def(node_id)
    result = dispatch(nd.owner_skill, task_board)

    # 出口（含 gate_predicate eval）
    verdict, violations = validate_node_io(task_board, node_id, phase="exit")
    if verdict == "BLOCK":
        supervisor_log("BLOCK", "DOD_GAP_ALERT",
                       f"node {node_id} gate FAIL",
                       violations)
        # 标节点 failed，转 PAUSED_ESCALATED（Slice B 实现 rollback 真 runtime）
        update_pipeline_node_status(task_board, node_id, "failed")
        transition(task_board, "PAUSED_ESCALATED")
        return False

    # 成功：标 passed + 触发 supervisor pulse（§ 4.5.3）
    update_pipeline_node_status(task_board, node_id, "passed")
    spawn_supervisor_pulse(task_board, nd.supervisor_pulse_code)
    return True
```

### 4.5.3 Per-node Supervisor Pulse（Q3=A）

每节点完成后强制：

```python
def spawn_supervisor_pulse(task_board: dict, code: str):
    # spawn lightweight Supervisor subagent for this node
    Agent({
        "subagent_type": "harnessFlow:supervisor",
        "description": f"per-node pulse {code}",
        "prompt": f"""
任务 <task_id>。节点 {code} 刚完成。读 task-board.pipeline_graph 当前节点
outputs；按 harnessFlow.md § 4.3 的 6 类干预规则输出 INFO/WARN/BLOCK 到
task-board.supervisor_interventions[]。同 code 5 min 内自动去重。
"""
    })
```

注意：pulse 失败（dispatch 异常 / 超时）→ 降级 INFO + 记
`supervisor_interventions[].dispatch_failed=true`，**不阻塞主流程**（spec § 4.3）。

### 4.5.4 Dashboard 6 卡黄警示（Q5=A）

主 skill 不直接管渲染；dashboard backend 通过
`pipelines.card_emptiness.derive_card_states(task_board)` 获取每张卡
`is_empty / waiting_for_node`，frontend 据此加 `.card-empty-warning`
样式（spec § 5）。
```

- [ ] **Step 2: Update § 5 调度 DSL 引用 § 4.5**

Find `^### 5.1 调用 DSL 模板`; replace the existing pseudo-code block (~line 350-395) so the loop walks `pipeline_graph.nodes` instead of `flow_catalog` step list:

```python
def execute_route(route_id: str, task_board: dict):
    if route_id == "A":
        # A 路线无 pipeline_graph（§ 4.5.1）；走原 flow-catalog § 2 序列
        return execute_route_a(task_board)

    # 其他路线必有 pipeline_graph[]，按 DAG 拓扑序 walk
    pg = task_board["pipeline_graph"]
    supervisor = spawn_supervisor(task_board)  # § 6 sidecar

    for node in topo_sort(pg["nodes"], pg["edges"]):
        ok = execute_pipeline_node(node["node_id"], task_board)
        if not ok:
            return  # PAUSED_ESCALATED already set by execute_pipeline_node
```

- [ ] **Step 3: Verify the skill markdown still parses**

```bash
cd /Users/zhongtianyi/work/code/harnessFlow
wc -l harnessFlow-skill.md
grep -c "^## § " harnessFlow-skill.md
```
Expected: lines ~1010 (was 927, +~80); `## § ` count = previous + 1.

- [ ] **Step 4: Commit Task 6.1**

```bash
git add harnessFlow-skill.md
git commit -m "feat(slice-a): harnessFlow-skill § 4.5 PIPELINE_EMIT 协议 (M2)

加 § 4.5 强制 ROUTE_SELECT 后 emit 13-node pipeline_graph[]（A 路线豁免）；
§ 5.1 主循环改成 walk pipeline_graph nodes (DAG topo 序)；每节点 enter/exit
调 validate_node_io，BLOCK → PAUSED_ESCALATED + DOD_GAP_ALERT；passed → 强制
spawn supervisor pulse；落地 Q1=A + Q3=A 设计决策。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 6.2: state-machine.md 加 PIPELINE_EMIT 边描述

**Files:**
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/state-machine.md`

- [ ] **Step 1: Locate § 2 主路径 / § 1 状态枚举**

```bash
grep -n "^## §\|ROUTE_SELECT.*PLAN\|^### 2" state-machine.md | head -20
```

- [ ] **Step 2: Append a § 2.x sub-section after main-path table**

Find the line with `ROUTE_SELECT → PLAN` and append (do NOT add new state — `PIPELINE_EMITTED` is a logical marker only):

```markdown
#### § 2.1.1 PIPELINE_EMITTED 逻辑标记（Slice A 新增）

`ROUTE_SELECT → PLAN` 边内（即 E3）插入一个**不占独立 current_state** 的逻辑步：
主 skill 在写完 `route_id` 后、进入 `PLAN` 状态前，**强制**调
`pipelines.contract_loader.emit_pipeline_graph(task_board)`，把 13-node
蓝图写到 `task_board.pipeline_graph`，并 append `state_history[]` 一笔
`{state: "PIPELINE_EMITTED", trigger: "post_route_select"}`（这是审计标记，
`current_state` 跳过此值不停留）。

A 路线（`size == XS`）跳过本步，`pipeline_graph` 保持 `null`。
```

- [ ] **Step 3: Commit Task 6.2**

```bash
git add state-machine.md
git commit -m "doc(slice-a): state-machine § 2.1.1 PIPELINE_EMITTED 逻辑标记

ROUTE_SELECT → PLAN 边内插入 emit pipeline_graph 步骤；非独立 state，
仅 state_history 留审计 entry。A 路线豁免。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 7: M7 — Per-node Supervisor Pulse helper

### Task 7.1: TDD spawn_supervisor_pulse

**Files:**
- Test: `/Users/zhongtianyi/work/code/harnessFlow/tests/test_supervisor_pulse.py`
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/pipelines/contract_loader.py`

- [ ] **Step 1: Write failing tests**

`tests/test_supervisor_pulse.py`:
```python
"""Tests for per-node supervisor pulse helper (Q3=A)."""
from __future__ import annotations

from pipelines.contract_loader import record_supervisor_pulse


def test_record_pulse_appends_intervention(empty_task_board):
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    assert "supervisor_interventions" in empty_task_board
    assert len(empty_task_board["supervisor_interventions"]) == 1
    iv = empty_task_board["supervisor_interventions"][0]
    assert iv["code"] == "node_passed_N3"
    assert iv["severity"] == "INFO"
    assert iv["context"]["node_id"] == "N3"


def test_record_pulse_dedup_within_5min(empty_task_board):
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    # 5min dedup → second call merges (count incremented), not duplicated
    assert len(empty_task_board["supervisor_interventions"]) == 1
    assert empty_task_board["supervisor_interventions"][0].get("count", 1) == 2


def test_record_pulse_different_codes_not_deduped(empty_task_board):
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    record_supervisor_pulse(empty_task_board, "node_passed_N4", node_id="N4")
    assert len(empty_task_board["supervisor_interventions"]) == 2
```

- [ ] **Step 2: Run tests — expect 3 failures**

Run: `pytest tests/test_supervisor_pulse.py -v`
Expected: 3 errors (ImportError on `record_supervisor_pulse`)

- [ ] **Step 3: Implement record_supervisor_pulse**

Append to `pipelines/contract_loader.py`:
```python
from datetime import datetime, timezone, timedelta

DEDUP_WINDOW_SEC = 5 * 60  # 5 min per harnessFlow.md § 7.7


def record_supervisor_pulse(
    task_board: dict, code: str, node_id: str | None = None
) -> dict:
    """Record a per-node supervisor pulse intervention; dedup within 5 min by code."""
    ivs = task_board.setdefault("supervisor_interventions", [])
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=DEDUP_WINDOW_SEC)

    # Find recent same-code entry
    for iv in reversed(ivs):
        if iv.get("code") != code:
            continue
        ts = iv.get("timestamp")
        if not ts:
            continue
        try:
            iv_t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if iv_t >= cutoff:
            iv["count"] = iv.get("count", 1) + 1
            iv["last_at"] = now.isoformat(timespec="seconds")
            return iv

    new_iv = {
        "severity": "INFO",
        "code": code,
        "diagnosis": f"node pulse: {code}",
        "suggested_action": None,
        "evidence": [],
        "timestamp": now.isoformat(timespec="seconds"),
        "context": {"node_id": node_id} if node_id else {},
    }
    ivs.append(new_iv)
    return new_iv
```

- [ ] **Step 4: Run tests — expect 3 passes**

Run: `pytest tests/test_supervisor_pulse.py -v`
Expected: 3 passed

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: all tests across all files pass; total ≥ 30 tests.

- [ ] **Step 6: Commit Task 7.1**

```bash
git add tests/test_supervisor_pulse.py pipelines/contract_loader.py
git commit -m "feat(slice-a): record_supervisor_pulse helper + 5min dedup (M7)

每节点完成时主 skill 调 record_supervisor_pulse() 写一笔 INFO 到
supervisor_interventions[]；同 code 5min 内合并 count++；不同 code 不去重。
落地 Q3=A 设计决策；harnessFlow.md § 7.7 既有去重规则复用。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 8: 集成验证（端到端）

### Task 8.1: dashboard 端到端 Playwright 验证

**Files:** none new (验证步骤)

- [ ] **Step 1: 起 dashboard backend**

```bash
cd /Users/zhongtianyi/work/code/harnessFlow/ui/backend
python server.py &
# 等 1 秒确保起来
curl -sf http://127.0.0.1:8765/api/health
```
Expected: `{"status":"ok",...}`

- [ ] **Step 2: 验证 6 卡 emptiness API**

```bash
curl -s "http://127.0.0.1:8765/api/tasks/p-tank-battle-20260426T082459Z" | \
  python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['_derived']['cards'], indent=2, ensure_ascii=False))"
```
Expected: 6 entries; tank-battle CLOSED → 大多 `is_empty: false`。

- [ ] **Step 3: 验证 pipeline_graph 已回填**

```bash
curl -s "http://127.0.0.1:8765/api/tasks/p-tank-battle-20260426T082459Z/pipeline" | \
  python -c "import sys,json; d=json.load(sys.stdin); print('nodes:', len(d['nodes']), 'edges:', len(d['edges']))"
```
Expected: `nodes: 13 edges: 18`（或近似）

- [ ] **Step 4: Playwright 验证黄警示**

Pick 一个有部分卡空的 task（例如 `e2e-hello-walkthrough-20260426T062858Z`，若 tank-battle 全绿可换非 CLOSED 任务）：

```bash
# Use Playwright via the playwright MCP tool from the controlling agent
# Navigate http://127.0.0.1:8765/?task=<chosen-task-id>
# Click any pipeline node → drawer opens
# Assert: at least 1 card has yellow border + "⚠️ 等待 N<id>" text
```

预期：DOM 含 `class="card-empty-warning"` 至少 1 处；text 含 "等待 N"。

- [ ] **Step 5: 收尾 commit (no code changes; record verification doc)**

```bash
# 如有需要，把 Playwright session log 存档：
# screenshots → docs/superpowers/specs/_visuals/2026-04-26-slice-a-verification/
# 此 step 可跳过实际 commit if no artifacts produced。
```

---

## Phase 9: Slice A 收口

### Task 9.1: 更新 spec § 9 进度 + 标 Slice A 完成

**Files:**
- Modify: `/Users/zhongtianyi/work/code/harnessFlow/docs/superpowers/specs/2026-04-26-pipeline-graph-A-design.md`
- Modify: memory `project_harnessflow_pipeline_graph_abc.md`

- [ ] **Step 1: Update spec status to "已落地"**

Edit `docs/superpowers/specs/2026-04-26-pipeline-graph-A-design.md` § 0 frontmatter:

```diff
- > **状态**：待用户 review
+ > **状态**：已落地（plan 8 phases 全绿）
```

Append to § 9:
```markdown
- 2026-04-26 — Slice A M1-M7 全部交付，全测绿，dashboard e2e 通过；切换到 Slice B 准备
```

- [ ] **Step 2: Update memory ABC roadmap**

Edit `/Users/zhongtianyi/.claude/projects/-Users-zhongtianyi-work-code/memory/project_harnessflow_pipeline_graph_abc.md`：

```diff
- - [ ] 切片 A spec 写就（docs/superpowers/specs/2026-04-26-pipeline-graph-A-design.md）
- - [ ] 切片 A plan 写就
- - [ ] 切片 A 落地
+ - [x] 切片 A spec 写就（docs/superpowers/specs/2026-04-26-pipeline-graph-A-design.md）
+ - [x] 切片 A plan 写就（docs/superpowers/plans/2026-04-26-pipeline-graph-A.md）
+ - [x] 切片 A 落地（21 task-boards 回填 + 13-node pipeline_graph emit + 节点级 BLOCK + 黄警示）
```

- [ ] **Step 3: Final commit**

```bash
git add docs/superpowers/specs/2026-04-26-pipeline-graph-A-design.md
git commit -m "doc(slice-a): mark Slice A delivered, ready for Slice B

M1-M7 全部交付；Slice B (运行时升级 — node-level checkpoint + rollback runtime)
为下一步。memory ABC 路线图同步勾选。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-review checklist（写完 plan 后我自己跑过）

**Spec coverage:**
- ✅ Q1 (节点级 BLOCK) → Phase 2 Task 2.2 `validate_node_io`
- ✅ Q2 (13 节点全集) → Phase 1 Task 1.1 yaml 含 N1-N13
- ✅ Q3 (per-node pulse) → Phase 7 Task 7.1 `record_supervisor_pulse`
- ✅ Q4 (历史回填) → Phase 4 Task 4.1+4.2 `backfill_pipeline_graph.py` + apply
- ✅ Q5 (黄警示) → Phase 3 Task 3.1+3.2 `card_emptiness` + frontend wire
- ✅ Q6 (全量) → 8 phases 同时覆盖文档 (M2/M3) + runtime (M1/M4/M7) + dashboard (M5/M6)
- ✅ M1-M7 7 milestones → 8 phases mapping (M4 前移 → Phase 2; M5 前移 → Phase 3; M6 → Phase 4; M3 → Phase 5; M2 → Phase 6; M7 → Phase 7)

**Type consistency:**
- `NodeDef.gate_predicate` 字段一致：`{expression: str, on_fail: enum}`（Phase 1 Task 1.1 yaml + Task 2.2 implementation 同名）
- `validate_node_io(task_board, node_id, phase)` 签名一致（spec § 4.1 + Phase 2 Task 2.2 + Phase 6 Task 6.1）
- `derive_card_states(task_board) -> list[dict]` 签名一致（Phase 3 Task 3.1 + Task 3.2 调用）

**Placeholder scan:**
- N2-N10 yaml 内容由 Step 2-4 实施时基于 `ui/backend/pipeline_catalog.py:NODE_CATALOG` 派生（明确指出 source-of-truth）
- 没有"add error handling" / "fill in details" 这类
- 所有 commit message 都是完整中文

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-pipeline-graph-A.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — 我每个 Task 派一个 fresh subagent；两阶段 review（spec compliance → code quality）；快速迭代

**2. Inline Execution** — 在本 session 直接执行 plan，按 phase 批量提交

**Which approach?**

如选 Subagent-Driven → 调 `superpowers:subagent-driven-development` skill。
如选 Inline → 调 `superpowers:executing-plans` skill。
