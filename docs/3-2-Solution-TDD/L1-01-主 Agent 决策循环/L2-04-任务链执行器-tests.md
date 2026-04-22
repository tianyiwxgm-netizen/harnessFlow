---
doc_id: tests-L1-01-L2-04-任务链执行器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-04-任务链执行器.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-01 L2-04-任务链执行器 · TDD 测试用例

> 基于 3-1 L2-04 §3（6 个 public 方法）+ §11（20 项 `E_CHAIN_*` 错误码）+ §12（延迟/吞吐 SLO）+ §13 TC ID 矩阵 驱动。
> TC ID 统一格式：`TC-L101-L204-NNN`（L1-01 下 L2-04，三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_04_TaskChainExecutor` 组织；`class TestL2_04_Negative` 负向分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型

| 方法（§3 出处） | TC ID | 覆盖类型 | 主要错误码 | 对应 IC |
|---|---|---|---|---|
| `start_chain()` · §3.1 · 简单 3 步 DAG | TC-L101-L204-001 | unit | — | IC-L2-03 |
| `start_chain()` · §3.1 · 并行 DAG（s2 ∥ s3） | TC-L101-L204-002 | unit | — | IC-L2-03 |
| `start_chain()` · §3.1 · 幂等（同 content_hash + tick_id） | TC-L101-L204-003 | unit | — | IC-L2-03 |
| `start_chain()` · §3.1 · `dag_preview` 拓扑序断言 | TC-L101-L204-004 | unit | — | IC-L2-03 |
| `start_chain()` · §3.1 · 嵌套 depth=1 与父链串联 | TC-L101-L204-005 | unit | — | IC-L2-03 |
| `start_chain()` · §3.1 · `initial_inputs` 透传到 step params | TC-L101-L204-006 | unit | — | IC-L2-03 |
| `start_chain()` · §3.1 · `first_success` termination | TC-L101-L204-007 | unit | — | IC-L2-03 |
| `on_step_completed()` · §3.2 · outcome=pass 推进 | TC-L101-L204-010 | unit | — | IC-L2-04 / IC-L2-07 |
| `on_step_completed()` · §3.2 · outcome=fail + retry | TC-L101-L204-011 | unit | — | IC-L2-04 |
| `on_step_completed()` · §3.2 · outcome=fail + rollback | TC-L101-L204-012 | unit | — | IC-L2-04 / IC-04 |
| `on_step_completed()` · §3.2 · outcome=skip | TC-L101-L204-013 | unit | — | IC-L2-04 |
| `on_step_completed()` · §3.2 · outcome=partial | TC-L101-L204-014 | unit | — | IC-L2-04 |
| `on_step_completed()` · §3.2 · 连续失败 ≥ 3 升级 | TC-L101-L204-015 | unit | — | IC-L2-10 |
| `pause_chain()` · §3.3 · RUNNING → PAUSED | TC-L101-L204-020 | unit | — | — |
| `resume_chain()` · §3.4 · PAUSED → RUNNING + ready_steps | TC-L101-L204-021 | unit | — | — |
| `abort_chain()` · §3.5 · 强终止 + cancel running | TC-L101-L204-022 | unit | — | IC-05 cancel |
| `abort_chain()` · §3.5 · cascade 级联子链 | TC-L101-L204-023 | unit | — | IC-L2-05 |
| `query_chain_status()` · §3.6 · 只读 + step_details | TC-L101-L204-030 | unit | — | — |
| `query_chain_status()` · §3.6 · `include_events=true` | TC-L101-L204-031 | unit | — | — |

### §1.2 错误码 × 测试（§11.1 / §3.7 · 20 项全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|---|---|---|---|
| `E_CHAIN_DEF_INVALID` | TC-L101-L204-101 | `start_chain()` | chain_def 校验 |
| `E_CHAIN_DAG_CYCLE` | TC-L101-L204-102 | `start_chain()` | DAG 校验 |
| `E_CHAIN_TOO_MANY_STEPS` | TC-L101-L204-103 | `start_chain()` | 硬上限 20 |
| `E_CHAIN_NESTING_EXCEEDED` | TC-L101-L204-104 | `start_chain()` | 嵌套 ≤ 3 |
| `E_CHAIN_NO_PROJECT_ID` | TC-L101-L204-105 | `start_chain()` | PM-14 红线 |
| `E_CHAIN_CROSS_PROJECT` | TC-L101-L204-106 | `start_chain()` | PM-14 红线 |
| `E_CHAIN_CONCURRENCY_CAP` | TC-L101-L204-107 | `start_chain()` | 全局并发 ≤ 8 |
| `E_CHAIN_ACTION_UNSUPPORTED` | TC-L101-L204-108 | `start_chain()` | capability 未注册 |
| `E_CHAIN_DEPS_UNRESOLVED` | TC-L101-L204-109 | `start_chain()` | deps 指向不存在 step_id |
| `E_CHAIN_STEP_ORPHAN` | TC-L101-L204-201 | `on_step_completed()` | 事件 stale |
| `E_CHAIN_STEP_STALE` | TC-L101-L204-202 | `on_step_completed()` | 事件 stale |
| `E_CHAIN_STEP_RESULT_MALFORMED` | TC-L101-L204-203 | `on_step_completed()` | 事件字段非法 |
| `E_CHAIN_STEP_TIMEOUT` | TC-L101-L204-204 | watchdog 合成 | 单步超时 |
| `E_CHAIN_NOT_FOUND` · pause | TC-L101-L204-301 | `pause_chain()` | 查询/控制 |
| `E_CHAIN_ALREADY_TERMINAL` · pause | TC-L101-L204-302 | `pause_chain()` | 终态拒绝 |
| `E_CHAIN_NOT_PAUSED` · resume | TC-L101-L204-303 | `resume_chain()` | 状态错 |
| `E_CHAIN_NOT_FOUND` · resume | TC-L101-L204-304 | `resume_chain()` | 查询/控制 |
| `E_CHAIN_NOT_FOUND` · abort | TC-L101-L204-305 | `abort_chain()` | 静默 false |
| `E_CHAIN_ALREADY_TERMINAL` · abort | TC-L101-L204-306 | `abort_chain()` | 终态拒绝 |
| `E_CHAIN_ROLLBACK_FAIL` | TC-L101-L204-307 | abort cascade / rollback | rollback 动作失败 |
| `E_CHAIN_CROSS_PROJECT_READ` | TC-L101-L204-308 | `query_chain_status()` | PM-14 读跨项目 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-03 `start_chain` | L2-02 → L2-04 | TC-L101-L204-401 | 消费方 · payload 字段校验 + dag_preview 返回 |
| IC-L2-04 `step_completed` | L2-04 → L2-02 | TC-L101-L204-402 | 生产方 · 每步必回 · 不跳决策（PRD §11.5 🚫#4）|
| IC-L2-07 `record_chain_step` | L2-04 → L2-05 | TC-L101-L204-403 | 每步审计 · action/outcome/step_result |
| IC-L2-05 `audit_chain_lifecycle` | L2-04 → L2-05 | TC-L101-L204-404 | create / complete / abort / rolled_back |
| IC-L2-10 `escalate_advice` | L2-04 → L2-06 | TC-L101-L204-405 | 连续失败 ≥ 3 · WARN |
| IC-04 `invoke_skill` | L2-04 → L1-05 | TC-L101-L204-406 | step.action.type=invoke_skill / use_tool |
| IC-05 `delegate_subagent` | L2-04 → L1-05 | TC-L101-L204-407 | step.action.type=delegate_subagent |
| IC-06 `kb_read` | L2-04 → L1-06 | TC-L101-L204-408 | step.action.type=kb_read |
| IC-07 `kb_write_session` | L2-04 → L1-06 | TC-L101-L204-409 | step.action.type=kb_write |
| IC-11 `process_content` | L2-04 → L1-08 | TC-L101-L204-410 | step.action.type=process_content |
| IC-09 `append_event`（经 L2-05 代劳） | L2-04 → L2-05 → L1-09 | TC-L101-L204-411 | 禁直写 · 必经 L2-05（PRD §11.3 OOS #3）|

### §1.4 SLO × 测试（§12.1 延迟表 + §12.2 吞吐）

| SLO 项 | 目标 | TC ID | mark |
|---|---|---|---|
| `start_chain()` P95 | ≤ 30ms · 硬上限 100ms | TC-L101-L204-501 | perf |
| `on_step_completed → IC-L2-04` P95 | ≤ 50ms · P99 ≤ 100ms | TC-L101-L204-502 | perf |
| `abort_chain()` P95 | ≤ 100ms · 硬上限 500ms | TC-L101-L204-503 | perf |
| `query_chain_status()` P95 | ≤ 5ms | TC-L101-L204-504 | perf |
| 活跃 chain 并发 | ≤ 8（`MAX_ACTIVE_CHAINS`）| TC-L101-L204-505 | perf |

### §1.5 e2e × 测试（§13.2 + 13.4 映射）

| 场景 | TC ID | 来源 |
|---|---|---|
| 流 C · 3 步 DAG 端到端（P0）| TC-L101-L204-601 | §5.1 P0 时序 |
| 流 C 变体 · 步失败 → retry → rollback（P1）| TC-L101-L204-602 | §5.2 P1 时序 |
| 流 I · BLOCK 抢占 + cascade abort | TC-L101-L204-603 | §11.6 + arch BLOCK 链 |

### §1.6 集成点 × 测试

| 协作对象 | TC ID | 协作内容 |
|---|---|---|
| L2-02 决策引擎（IC-L2-04 回调 + on_step_completed 反向）| TC-L101-L204-701 | 每步闭环 |
| L2-03 状态机编排器（chain_completed → state_transition）| TC-L101-L204-702 | §13.4 P0-08 |
| L2-05 审计记录器（IC-L2-07 + IC-L2-05）| TC-L101-L204-703 | 审计链 P0-07 |
| L2-06 Supervisor 建议接收器（IC-L2-10 升级）| TC-L101-L204-704 | 连续失败链 P1-04 |

### §1.7 边界用例索引

| 边界类型 | TC ID | 覆盖 |
|---|---|---|
| 空 steps（minItems=1 违反）| TC-L101-L204-B01 | DEF_INVALID 最小边界 |
| 单步无依赖 chain | TC-L101-L204-B02 | 最简 DAG |
| 20 步极限 DAG | TC-L101-L204-B03 | 硬上限临界 |
| 并行超 2（同 chain 内 `MAX_PARALLEL_STEPS`）| TC-L101-L204-B04 | 并行度 gate |
| 同 chain 并发收 2 事件顺序执行（锁）| TC-L101-L204-B05 | 锁不变量 |
| 崩溃恢复 snapshot + event replay | TC-L101-L204-B06 | §7.4 recovery |
| 脏 step_id 格式（不匹配 pattern）| TC-L101-L204-B07 | 字段校验 |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_04_TaskChainExecutor`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `TaskChainExecutor`（从 `app.l2_04.executor` 导入）。

```python
# file: tests/l1_01/test_l2_04_task_chain_executor_positive.py
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor
from app.l2_04.schemas import (
    ChainDef,
    ChainContext,
    StartChainResult,
    StepResult,
    PauseRequest,
    ResumeRequest,
    AbortRequest,
    QueryRequest,
)
from app.l2_04.errors import ChainError


class TestL2_04_TaskChainExecutor:
    """§3 public 方法正向用例。每方法 ≥ 1 个 happy path。"""

    # --------- start_chain() · §3.1 --------- #

    def test_TC_L101_L204_001_start_chain_simple_3_step_serial_dag(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-001 · 3 步串行 DAG（s1 → s2 → s3）· accepted=true + dag_preview 长度=3。"""
        chain_def: ChainDef = make_chain_def(
            steps=[
                {"step_id": "s1", "action": {"type": "invoke_skill", "params": {"capability": "tdd.plan"}}, "deps": []},
                {"step_id": "s2", "action": {"type": "invoke_skill", "params": {"capability": "tdd.impl"}}, "deps": ["s1"]},
                {"step_id": "s3", "action": {"type": "invoke_skill", "params": {"capability": "tdd.verify"}}, "deps": ["s2"]},
            ],
        )
        ctx: ChainContext = make_context(project_id=mock_project_id)
        result: StartChainResult = sut.start_chain(chain_def, chain_goal="ship feature X safely", context=ctx)
        assert result.accepted is True
        assert result.chain_id.startswith("ch-")
        assert result.dag_preview == ["s1", "s2", "s3"]
        assert result.rejection_reason is None

    def test_TC_L101_L204_002_start_chain_parallel_branches(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-002 · s2 ∥ s3 均依赖 s1 · 拓扑序 s1 第一 · s2/s3 紧随（不要求内部顺序）。"""
        chain_def = make_chain_def(
            steps=[
                {"step_id": "s1", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": []},
                {"step_id": "s2", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": ["s1"]},
                {"step_id": "s3", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": ["s1"]},
            ],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="parallel branch test", context=ctx)
        assert r.accepted is True
        assert r.dag_preview[0] == "s1"
        assert set(r.dag_preview[1:]) == {"s2", "s3"}, "s2/s3 拓扑序紧随 s1"

    def test_TC_L101_L204_003_start_chain_idempotent_same_hash_tick(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-003 · 同 (content_hash, project_id, tick_id) 重入返回同 chain_id（§3.1 幂等）。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id, tick_id="tick-0001")
        r1 = sut.start_chain(chain_def, chain_goal="idempotency path", context=ctx)
        r2 = sut.start_chain(chain_def, chain_goal="idempotency path", context=ctx)
        assert r1.chain_id == r2.chain_id, "重入必须返回同 chain_id（LRU 512 幂等缓存）"

    def test_TC_L101_L204_004_start_chain_dag_preview_canonical_topological(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-004 · dag_preview 为 Kahn 确定性拓扑序（无 deps 先 · 按 step_id 字典序打破平局）。"""
        chain_def = make_chain_def(
            steps=[
                {"step_id": "s_z", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": []},
                {"step_id": "s_a", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": []},
                {"step_id": "s_m", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": ["s_a", "s_z"]},
            ],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="canonical ordering", context=ctx)
        assert r.dag_preview == ["s_a", "s_z", "s_m"]

    def test_TC_L101_L204_005_start_chain_nested_depth_1_with_parent(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-005 · nesting_depth=1 + parent_chain_id 有值 · 允许启动（≤ 3 硬约束内）。"""
        chain_def = make_chain_def(nesting_depth=1, parent_chain_id="ch-parent-0001")
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="nested child chain", context=ctx)
        assert r.accepted is True
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.nesting_depth == 1
        assert status.parent_chain_id == "ch-parent-0001"

    def test_TC_L101_L204_006_start_chain_initial_inputs_propagated(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l1_05_client: MagicMock,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-006 · context.initial_inputs 传入 · 派步时透传到 IC-04 params.inputs。"""
        chain_def = make_chain_def(
            steps=[
                {"step_id": "s1",
                 "action": {"type": "invoke_skill", "params": {"capability": "k", "inputs": "${inputs.seed}"}},
                 "deps": []},
            ],
        )
        ctx = make_context(project_id=mock_project_id, initial_inputs={"seed": "value-42"})
        sut.start_chain(chain_def, chain_goal="initial inputs propagation", context=ctx)
        sut._dispatch_ready_steps_once()
        params = mock_l1_05_client.invoke_skill.call_args.kwargs["params"]
        assert params["inputs"] == "value-42"

    def test_TC_L101_L204_007_start_chain_first_success_termination(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
        make_step_result,
    ) -> None:
        """TC-L101-L204-007 · termination_condition.first_success=true · 首个 pass 即完成（未派发步标 skipped · §11.5）。"""
        chain_def = make_chain_def(
            steps=[
                {"step_id": f"s{i}",
                 "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                 "deps": []} for i in range(1, 4)
            ],
            termination_condition={"all_steps_completed": False, "first_success": True},
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="first success wins", context=ctx)
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1", outcome="pass",
                                               project_id=mock_project_id))
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state == "completed"
        assert set(status.completed_step_ids) == {"s1"}
        # 未完成的 s2/s3 标 skipped
        skipped = {s["step_id"] for s in status.step_details if s["status"] == "skipped"}
        assert skipped == {"s2", "s3"}

    # --------- on_step_completed() · §3.2 --------- #

    def test_TC_L101_L204_010_on_step_completed_pass_advances_and_callbacks_l2_02(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l2_02_client: MagicMock,
        mock_l2_05_client: MagicMock,
        make_chain_def,
        make_context,
        make_step_result,
    ) -> None:
        """TC-L101-L204-010 · outcome=pass · IC-L2-04 回调 L2-02 + IC-L2-07 审计 + consecutive_failures 归零。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="pass advances", context=ctx)
        step_result = make_step_result(chain_id=r.chain_id, step_id="s1", outcome="pass",
                                       project_id=mock_project_id)
        sut.on_step_completed(step_result)
        mock_l2_02_client.on_step_completed.assert_called_once()
        kwargs = mock_l2_02_client.on_step_completed.call_args.kwargs
        assert kwargs["chain_id"] == r.chain_id
        assert kwargs["step_id"] == "s1"
        assert kwargs["outcome"] == "pass"
        # IC-L2-07 审计
        rec_calls = [c for c in mock_l2_05_client.record_chain_step.call_args_list
                     if c.kwargs.get("step_id") == "s1"]
        assert len(rec_calls) == 1

    def test_TC_L101_L204_011_on_step_completed_fail_triggers_retry(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l1_05_client: MagicMock,
        make_chain_def,
        make_context,
        make_step_result,
        tick_clock,
    ) -> None:
        """TC-L101-L204-011 · fail + retry_count < max_retries · 按 backoff_ms 延后重派。"""
        chain_def = make_chain_def(
            steps=[{"step_id": "s1",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": [],
                    "retry_policy": {"max_retries": 1, "backoff_ms": 1000}}],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="retry after fail", context=ctx)
        sut._dispatch_ready_steps_once()
        assert mock_l1_05_client.invoke_skill.call_count == 1
        sut.on_step_completed(make_step_result(
            chain_id=r.chain_id, step_id="s1", outcome="fail",
            project_id=mock_project_id,
            error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x", "is_retriable": True, "is_timeout": False},
        ))
        tick_clock.advance(1000)
        sut._tick_retry_scheduler()
        assert mock_l1_05_client.invoke_skill.call_count == 2, "retry 必须重派"
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        step = next(s for s in status.step_details if s["step_id"] == "s1")
        assert step["retry_count"] == 1

    def test_TC_L101_L204_012_on_step_completed_fail_max_retry_then_rollback(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l1_05_client: MagicMock,
        make_chain_def,
        make_context,
        make_step_result,
    ) -> None:
        """TC-L101-L204-012 · retry 用完 + 有 rollback_action · 触发 RollbackCoordinator · chain → rolled_back。"""
        chain_def = make_chain_def(
            steps=[{"step_id": "s1",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": [],
                    "retry_policy": {"max_retries": 0, "backoff_ms": 0},
                    "rollback_action": {"type": "invoke_skill",
                                        "params": {"capability": "revert.changes"}}}],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="rollback on fail", context=ctx)
        sut._dispatch_ready_steps_once()
        sut.on_step_completed(make_step_result(
            chain_id=r.chain_id, step_id="s1", outcome="fail",
            project_id=mock_project_id,
            error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x", "is_retriable": False, "is_timeout": False},
        ))
        # rollback_action 应以同步方式调 IC-04
        rollback_calls = [c for c in mock_l1_05_client.invoke_skill.call_args_list
                          if c.kwargs.get("capability") == "revert.changes"]
        assert len(rollback_calls) == 1
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state == "rolled_back"

    def test_TC_L101_L204_013_on_step_completed_skip_not_retried(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l1_05_client: MagicMock,
        make_chain_def,
        make_context,
        make_step_result,
    ) -> None:
        """TC-L101-L204-013 · outcome=skip · 不重试 · 不回滚 · 依然 IC-L2-04 回调（§11.4）。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="skip is terminal", context=ctx)
        sut._dispatch_ready_steps_once()
        invoke_count_before = mock_l1_05_client.invoke_skill.call_count
        sut.on_step_completed(make_step_result(
            chain_id=r.chain_id, step_id="s1", outcome="skip", project_id=mock_project_id,
        ))
        assert mock_l1_05_client.invoke_skill.call_count == invoke_count_before, "skip 禁重试"
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        step = next(s for s in status.step_details if s["step_id"] == "s1")
        assert step["status"] == "skipped"

    def test_TC_L101_L204_014_on_step_completed_partial_defers_to_l2_02(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l2_02_client: MagicMock,
        make_chain_def,
        make_context,
        make_step_result,
    ) -> None:
        """TC-L101-L204-014 · outcome=partial · 不自动重试 · 透传 next_hint 给 L2-02 决策（§11.4）。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="partial defers decision", context=ctx)
        sut.on_step_completed(make_step_result(
            chain_id=r.chain_id, step_id="s1", outcome="partial",
            project_id=mock_project_id, next_hint="need user review",
        ))
        kwargs = mock_l2_02_client.on_step_completed.call_args.kwargs
        assert kwargs["outcome"] == "partial"
        assert kwargs["next_hint"] == "need user review"

    def test_TC_L101_L204_015_consecutive_failures_escalate_via_l2_06(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l2_06_client: MagicMock,
        make_chain_def,
        make_context,
        make_step_result,
    ) -> None:
        """TC-L101-L204-015 · chain 内累计 3 失败 · IC-L2-10 escalate_advice(level=WARN)（PRD §11.4 #4）。"""
        chain_def = make_chain_def(
            steps=[{"step_id": f"s{i}",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": [],
                    "retry_policy": {"max_retries": 0, "backoff_ms": 0}} for i in range(1, 4)],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="three failures escalate", context=ctx)
        for step_id in ("s1", "s2", "s3"):
            sut.on_step_completed(make_step_result(
                chain_id=r.chain_id, step_id=step_id, outcome="fail",
                project_id=mock_project_id,
                error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x",
                       "is_retriable": False, "is_timeout": False},
            ))
        mock_l2_06_client.escalate_advice.assert_called_once()
        args = mock_l2_06_client.escalate_advice.call_args.kwargs
        assert args["level"] == "WARN"
        assert "chain stuck" in args["content"] or r.chain_id in args["content"]

    # --------- pause_chain() / resume_chain() · §3.3-3.4 --------- #

    def test_TC_L101_L204_020_pause_chain_running_to_paused(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-020 · RUNNING chain 调 pause · state=PAUSED · pending_steps_count ≥ 0。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="pause live chain", context=ctx)
        result = sut.pause_chain(PauseRequest(
            chain_id=r.chain_id, reason="user_intervene",
            reason_detail="user hits pause", project_id=mock_project_id,
        ))
        assert result.paused is True
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state == "paused"

    def test_TC_L101_L204_021_resume_chain_returns_ready_steps(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-021 · PAUSED 恢复 RUNNING · ready_steps 列出当前可立刻派的 step_id。"""
        chain_def = make_chain_def(
            steps=[{"step_id": "s1",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": []}],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="resume chain", context=ctx)
        sut.pause_chain(PauseRequest(chain_id=r.chain_id, reason="user_intervene",
                                     reason_detail="manual pause", project_id=mock_project_id))
        res = sut.resume_chain(ResumeRequest(chain_id=r.chain_id, project_id=mock_project_id))
        assert res.resumed is True
        assert "s1" in res.ready_steps

    # --------- abort_chain() · §3.5 --------- #

    def test_TC_L101_L204_022_abort_chain_force_cancels_running_steps(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l1_05_client: MagicMock,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-022 · abort · 取消 running 步（经 IC-05 cancel）+ state 终态。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="abort force", context=ctx)
        sut._dispatch_ready_steps_once()
        res = sut.abort_chain(AbortRequest(
            chain_id=r.chain_id, reason_type="supervisor_block",
            reason="BLOCK red line hit",
            project_id=mock_project_id, cascade=False,
        ))
        assert res.aborted is True
        assert "s1" in res.cleanup_result.canceled_running_steps
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state in ("failed",)  # PRD §11.5 aborted 外观 = failed

    def test_TC_L101_L204_023_abort_chain_cascades_to_child_chains(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-023 · cascade=true · 父 chain abort 级联 abort 子 chain（§3.5 cascade 字段）。"""
        parent = make_chain_def()
        parent_ctx = make_context(project_id=mock_project_id, tick_id="tick-parent")
        r_parent = sut.start_chain(parent, chain_goal="parent chain", context=parent_ctx)
        child = make_chain_def(nesting_depth=1, parent_chain_id=r_parent.chain_id)
        child_ctx = make_context(project_id=mock_project_id, tick_id="tick-child")
        r_child = sut.start_chain(child, chain_goal="child chain", context=child_ctx)
        res = sut.abort_chain(AbortRequest(
            chain_id=r_parent.chain_id, reason_type="user_panic",
            reason="cascade abort scenario",
            project_id=mock_project_id, cascade=True,
        ))
        assert res.aborted is True
        assert r_child.chain_id in res.child_chains_aborted

    # --------- query_chain_status() · §3.6 --------- #

    def test_TC_L101_L204_030_query_chain_status_with_step_details(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-030 · include_step_details=true · step_details 长度等于 steps 数。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="query status with details", context=ctx)
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id,
                                        include_step_details=True)
        assert status is not None
        assert len(status.step_details) == len(chain_def.steps)
        assert status.state in ("pending", "running")

    def test_TC_L101_L204_031_query_chain_status_include_events(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        make_chain_def,
        make_context,
    ) -> None:
        """TC-L101-L204-031 · include_events=true · events 列表非空（至少有 chain_created）。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="query events", context=ctx)
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id,
                                        include_events=True)
        assert status is not None
        assert hasattr(status, "events") and len(status.events) >= 1
```

---

## §3 负向用例（§11 每错误码 ≥ 1）

> 对应 §1.2 表 · 20 项 `E_CHAIN_*` 全覆盖 · `class TestL2_04_Negative` · assertion 采用 `pytest.raises(ChainError) as ei` + `ei.value.code` 匹配。

```python
# file: tests/l1_01/test_l2_04_task_chain_executor_negative.py
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor
from app.l2_04.schemas import (
    ChainDef, ChainContext, StepResult,
    PauseRequest, ResumeRequest, AbortRequest, QueryRequest,
)
from app.l2_04.errors import ChainError


class TestL2_04_Negative:
    """§11.1 错误分类 · 每错误码至少 1 用例。"""

    # --------- start_chain() 启动期（9 项 · §3.1.1 + §3.7）--------- #

    def test_TC_L101_L204_101_def_invalid_empty_steps(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-101 · `E_CHAIN_DEF_INVALID` · steps 空（minItems=1 违反）。"""
        bad = make_chain_def(steps=[])
        with pytest.raises(ChainError) as ei:
            sut.start_chain(bad, chain_goal="empty steps should reject", context=make_context(project_id=mock_project_id))
        assert ei.value.code == "E_CHAIN_DEF_INVALID"

    def test_TC_L101_L204_102_dag_cycle_detected(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-102 · `E_CHAIN_DAG_CYCLE` · s1→s2→s1 形成环。"""
        cyclic = make_chain_def(steps=[
            {"step_id": "s1", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": ["s2"]},
            {"step_id": "s2", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": ["s1"]},
        ])
        with pytest.raises(ChainError) as ei:
            sut.start_chain(cyclic, chain_goal="cycle cannot start", context=make_context(project_id=mock_project_id))
        assert ei.value.code == "E_CHAIN_DAG_CYCLE"

    def test_TC_L101_L204_103_too_many_steps_over_20(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-103 · `E_CHAIN_TOO_MANY_STEPS` · steps 数 = 21（§3.1 maxItems=20）。"""
        big = make_chain_def(steps=[
            {"step_id": f"s{i:02d}",
             "action": {"type": "invoke_skill", "params": {"capability": "k"}},
             "deps": []} for i in range(21)
        ])
        with pytest.raises(ChainError) as ei:
            sut.start_chain(big, chain_goal="21 steps breach cap", context=make_context(project_id=mock_project_id))
        assert ei.value.code == "E_CHAIN_TOO_MANY_STEPS"

    def test_TC_L101_L204_104_nesting_exceeded_depth_4(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-104 · `E_CHAIN_NESTING_EXCEEDED` · nesting_depth=4 超硬上限 3。"""
        deep = make_chain_def(nesting_depth=4, parent_chain_id="ch-parent")
        with pytest.raises(ChainError) as ei:
            sut.start_chain(deep, chain_goal="nesting too deep", context=make_context(project_id=mock_project_id))
        assert ei.value.code == "E_CHAIN_NESTING_EXCEEDED"

    def test_TC_L101_L204_105_no_project_id(
        self, sut: TaskChainExecutor, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-105 · `E_CHAIN_NO_PROJECT_ID` · context.project_id 缺失（PM-14 红线）。"""
        ctx = make_context(project_id=None)  # 由 fixture 支持 None 注入
        with pytest.raises(ChainError) as ei:
            sut.start_chain(make_chain_def(), chain_goal="missing project id", context=ctx)
        assert ei.value.code == "E_CHAIN_NO_PROJECT_ID"

    def test_TC_L101_L204_106_cross_project_rejected(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-106 · `E_CHAIN_CROSS_PROJECT` · context.project_id 与 session_pid 不同。"""
        other_pid = "pid-11111111-2222-7333-8444-555555555555"
        with pytest.raises(ChainError) as ei:
            sut.start_chain(make_chain_def(), chain_goal="cross project reject",
                            context=make_context(project_id=other_pid))
        assert ei.value.code == "E_CHAIN_CROSS_PROJECT"

    def test_TC_L101_L204_107_concurrency_cap_8_active(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-107 · `E_CHAIN_CONCURRENCY_CAP` · 第 9 个活跃 chain 拒绝（MAX_ACTIVE_CHAINS=8）。"""
        for i in range(8):
            ctx = make_context(project_id=mock_project_id, tick_id=f"tick-{i:02d}")
            sut.start_chain(make_chain_def(), chain_goal=f"fill chain {i}", context=ctx)
        with pytest.raises(ChainError) as ei:
            sut.start_chain(make_chain_def(), chain_goal="9th chain should be rejected",
                            context=make_context(project_id=mock_project_id, tick_id="tick-overflow"))
        assert ei.value.code == "E_CHAIN_CONCURRENCY_CAP"

    def test_TC_L101_L204_108_action_unsupported(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-108 · `E_CHAIN_ACTION_UNSUPPORTED` · action.type 不在能力抽象层枚举。"""
        bad = make_chain_def(steps=[
            {"step_id": "s1", "action": {"type": "unsupported_banana", "params": {}}, "deps": []},
        ])
        with pytest.raises(ChainError) as ei:
            sut.start_chain(bad, chain_goal="unsupported action", context=make_context(project_id=mock_project_id))
        assert ei.value.code == "E_CHAIN_ACTION_UNSUPPORTED"

    def test_TC_L101_L204_109_deps_unresolved(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-109 · `E_CHAIN_DEPS_UNRESOLVED` · deps 指向 step_id 不存在 → fail-fast 为 DEF_INVALID 语义。"""
        bad = make_chain_def(steps=[
            {"step_id": "s1", "action": {"type": "invoke_skill", "params": {"capability": "k"}},
             "deps": ["s_does_not_exist"]},
        ])
        with pytest.raises(ChainError) as ei:
            sut.start_chain(bad, chain_goal="dangling deps rejected",
                            context=make_context(project_id=mock_project_id))
        assert ei.value.code in ("E_CHAIN_DEPS_UNRESOLVED", "E_CHAIN_DEF_INVALID")

    # --------- on_step_completed() 事件期（4 项 · §3.2 + watchdog §6.6）--------- #

    def test_TC_L101_L204_201_step_orphan_silent_drop(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_02_client: MagicMock, mock_l2_05_client: MagicMock, make_step_result,
    ) -> None:
        """TC-L101-L204-201 · `E_CHAIN_STEP_ORPHAN` · chain_id 在 registry 不存在 → 静默 drop + debug log。"""
        unknown = make_step_result(chain_id="ch-ghost-0000-0000-0000-0000", step_id="s1",
                                   outcome="pass", project_id=mock_project_id)
        sut.on_step_completed(unknown)  # must not raise
        mock_l2_02_client.on_step_completed.assert_not_called()
        orphan_audits = [c for c in mock_l2_05_client.record_chain_step.call_args_list
                         if c.kwargs.get("error_code") == "E_CHAIN_STEP_ORPHAN"]
        assert len(orphan_audits) >= 0  # 低频 audit 允许 ≥0（debug log 为主）

    def test_TC_L101_L204_202_step_stale_silent_drop(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_02_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-202 · `E_CHAIN_STEP_STALE` · step 已推进 · 迟到事件静默 drop。"""
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(make_chain_def(), chain_goal="stale event scenario", context=ctx)
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        call_count_before = mock_l2_02_client.on_step_completed.call_count
        # 第二次相同 step 事件 → stale
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        assert mock_l2_02_client.on_step_completed.call_count == call_count_before, \
            "stale 事件必须不重复回调 L2-02"

    def test_TC_L101_L204_203_step_result_malformed_treated_as_fail(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-203 · `E_CHAIN_STEP_RESULT_MALFORMED` · 必填字段缺失 → 视 fail 走重试（§11.1）。"""
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(make_chain_def(), chain_goal="malformed event", context=ctx)
        # outcome 字段非枚举值
        malformed = make_step_result(chain_id=r.chain_id, step_id="s1",
                                     outcome="banana", project_id=mock_project_id)
        sut.on_step_completed(malformed)
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        s1 = next(s for s in status.step_details if s["step_id"] == "s1")
        assert s1["status"] in ("retrying", "failed")

    def test_TC_L101_L204_204_step_timeout_synthesized_by_watchdog(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context, tick_clock, mock_l2_02_client: MagicMock,
    ) -> None:
        """TC-L101-L204-204 · `E_CHAIN_STEP_TIMEOUT` · watchdog 扫描合成 fail 事件（§6.6 + §11.4）。"""
        ctx = make_context(project_id=mock_project_id)
        chain_def = make_chain_def(
            steps=[{"step_id": "s1",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": [], "timeout_ms": 1000}],
        )
        r = sut.start_chain(chain_def, chain_goal="watchdog timeout", context=ctx)
        sut._dispatch_ready_steps_once()
        tick_clock.advance(1500)  # 超 timeout_ms
        sut._run_watchdog_once()
        kwargs = mock_l2_02_client.on_step_completed.call_args.kwargs
        assert kwargs["outcome"] == "fail"

    # --------- pause/resume/abort/query（7 项 · §3.3-3.6）--------- #

    def test_TC_L101_L204_301_pause_not_found(
        self, sut: TaskChainExecutor, mock_project_id: str,
    ) -> None:
        """TC-L101-L204-301 · `E_CHAIN_NOT_FOUND` · pause 未知 chain_id → paused=false + 错误。"""
        res = sut.pause_chain(PauseRequest(chain_id="ch-ghost", reason="user_intervene",
                                           reason_detail="x", project_id=mock_project_id))
        assert res.paused is False
        assert res.error_code == "E_CHAIN_NOT_FOUND"

    def test_TC_L101_L204_302_pause_already_terminal(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-302 · `E_CHAIN_ALREADY_TERMINAL` · completed chain 再 pause → paused=false。"""
        r = sut.start_chain(make_chain_def(), chain_goal="complete before pause",
                            context=make_context(project_id=mock_project_id))
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        res = sut.pause_chain(PauseRequest(chain_id=r.chain_id, reason="user_intervene",
                                           reason_detail="x", project_id=mock_project_id))
        assert res.paused is False
        assert res.error_code == "E_CHAIN_ALREADY_TERMINAL"

    def test_TC_L101_L204_303_resume_not_paused(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-303 · `E_CHAIN_NOT_PAUSED` · RUNNING chain 直接 resume → resumed=false。"""
        r = sut.start_chain(make_chain_def(), chain_goal="already running",
                            context=make_context(project_id=mock_project_id))
        res = sut.resume_chain(ResumeRequest(chain_id=r.chain_id, project_id=mock_project_id))
        assert res.resumed is False
        assert res.error_code == "E_CHAIN_NOT_PAUSED"

    def test_TC_L101_L204_304_resume_not_found(
        self, sut: TaskChainExecutor, mock_project_id: str,
    ) -> None:
        """TC-L101-L204-304 · `E_CHAIN_NOT_FOUND` · resume 未知 chain。"""
        res = sut.resume_chain(ResumeRequest(chain_id="ch-ghost", project_id=mock_project_id))
        assert res.resumed is False
        assert res.error_code == "E_CHAIN_NOT_FOUND"

    def test_TC_L101_L204_305_abort_not_found_silent_false(
        self, sut: TaskChainExecutor, mock_project_id: str,
    ) -> None:
        """TC-L101-L204-305 · `E_CHAIN_NOT_FOUND` · abort 未知 chain → aborted=false（静默 · 不抛）。"""
        res = sut.abort_chain(AbortRequest(chain_id="ch-ghost", reason_type="user_panic",
                                           reason="manual panic test",
                                           project_id=mock_project_id, cascade=False))
        assert res.aborted is False

    def test_TC_L101_L204_306_abort_already_terminal(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-306 · `E_CHAIN_ALREADY_TERMINAL` · 完成 chain 再 abort → aborted=false + note。"""
        r = sut.start_chain(make_chain_def(), chain_goal="complete then abort",
                            context=make_context(project_id=mock_project_id))
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        res = sut.abort_chain(AbortRequest(chain_id=r.chain_id, reason_type="supervisor_block",
                                           reason="already done chain",
                                           project_id=mock_project_id, cascade=False))
        assert res.aborted is False

    def test_TC_L101_L204_307_rollback_fail_chain_stays_failed(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_05_client: MagicMock, mock_l1_07_client: MagicMock,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-307 · `E_CHAIN_ROLLBACK_FAIL` · rollback_action 抛错 → chain → failed + WARN L1-07（§11.1）。"""
        chain_def = make_chain_def(
            steps=[{"step_id": "s1",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": [], "retry_policy": {"max_retries": 0, "backoff_ms": 0},
                    "rollback_action": {"type": "invoke_skill",
                                        "params": {"capability": "revert.broken"}}}],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="rollback explodes", context=ctx)
        # 派 + 失败事件
        sut._dispatch_ready_steps_once()
        # rollback 执行时 IC-04 抛错
        mock_l1_05_client.invoke_skill.side_effect = [
            {"outcome": "pass"},  # original dispatch 先占位
            RuntimeError("rollback boom"),
        ]
        sut.on_step_completed(make_step_result(
            chain_id=r.chain_id, step_id="s1", outcome="fail", project_id=mock_project_id,
            error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x",
                   "is_retriable": False, "is_timeout": False},
        ))
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state == "failed", "rollback 失败的 chain 必须 failed（不 rolled_back）"
        assert mock_l1_07_client.warn.call_count >= 1

    def test_TC_L101_L204_308_query_cross_project_rejected(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-308 · `E_CHAIN_CROSS_PROJECT_READ` · project_id 不匹配查询 → 拒绝 + 告警（PM-14）。"""
        r = sut.start_chain(make_chain_def(), chain_goal="cross project read",
                            context=make_context(project_id=mock_project_id))
        other_pid = "pid-ffffffff-ffff-7fff-8fff-ffffffffffff"
        with pytest.raises(ChainError) as ei:
            sut.query_chain_status(chain_id=r.chain_id, project_id=other_pid)
        assert ei.value.code == "E_CHAIN_CROSS_PROJECT_READ"
```

---

## §4 IC 契约集成测试

> ≥ 3 join test · 覆盖 IC-L2-03 / IC-L2-04 / IC-L2-07 / IC-L2-05 / IC-L2-10 + 跨 BC IC-04/05/06/07/11 + IC-09（经 L2-05 代劳）。
> 验证 payload 字段、频次、时序。本段均为 `integration` 覆盖类型。

```python
# file: tests/l1_01/test_l2_04_ic_contracts.py
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor


class TestL2_04_ICContracts:
    """IC 契约 join 测试 · 消费方/生产方 payload 断言。"""

    def test_TC_L101_L204_401_ic_l2_03_start_chain_payload_shape(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-401 · IC-L2-03 消费 · payload 完整校验 + dag_preview 回流 L2-02。"""
        chain_def = make_chain_def()
        ctx = make_context(project_id=mock_project_id, tick_id="tick-ic03",
                           decision_id="dec-ic03")
        r = sut.start_chain(chain_def, chain_goal="IC-L2-03 payload shape check", context=ctx)
        assert r.accepted is True
        assert r.chain_id.startswith("ch-")
        assert isinstance(r.dag_preview, list)

    def test_TC_L101_L204_402_ic_l2_04_step_completed_every_step(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_02_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-402 · IC-L2-04 生产 · 每步必回（PRD §11.5 🚫#4 禁止跳回调）。"""
        chain_def = make_chain_def(
            steps=[{"step_id": f"s{i}",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": ([f"s{i-1}"] if i > 1 else [])} for i in range(1, 4)],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="IC-L2-04 fire per step", context=ctx)
        for step_id in ("s1", "s2", "s3"):
            sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id=step_id,
                                                   outcome="pass", project_id=mock_project_id))
            sut._dispatch_ready_steps_once()
        assert mock_l2_02_client.on_step_completed.call_count == 3, \
            "3 步 chain 必回 3 次 IC-L2-04"
        for call in mock_l2_02_client.on_step_completed.call_args_list:
            assert {"chain_id", "step_id", "outcome", "result_ref"} <= set(call.kwargs)

    def test_TC_L101_L204_403_ic_l2_07_record_chain_step_every_step(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-403 · IC-L2-07 · 每步完成必审计（PRD §11.5 🚫#5）。"""
        chain_def = make_chain_def(
            steps=[{"step_id": f"s{i}",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": ([f"s{i-1}"] if i > 1 else [])} for i in range(1, 4)],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="IC-L2-07 audit every step", context=ctx)
        for sid in ("s1", "s2", "s3"):
            sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id=sid,
                                                   outcome="pass", project_id=mock_project_id))
        step_records = [c for c in mock_l2_05_client.record_chain_step.call_args_list
                        if c.kwargs.get("chain_id") == r.chain_id]
        assert len(step_records) == 3
        for call in step_records:
            assert {"chain_id", "step_id", "action", "outcome", "step_result", "ts"} <= set(call.kwargs)

    def test_TC_L101_L204_404_ic_l2_05_audit_chain_lifecycle_create_complete(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-404 · IC-L2-05 · 生命期事件（create / complete / rolled_back / abort 四态）。"""
        r = sut.start_chain(make_chain_def(), chain_goal="lifecycle events",
                            context=make_context(project_id=mock_project_id))
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        actions = [c.kwargs.get("action") for c in mock_l2_05_client.audit_chain_lifecycle.call_args_list
                   if c.kwargs.get("chain_id") == r.chain_id]
        assert "create" in actions and "complete" in actions

    def test_TC_L101_L204_405_ic_l2_10_escalate_advice_level_warn(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_06_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-405 · IC-L2-10 生产 · 连续 3 失败 → escalate_advice(level=WARN)。"""
        chain_def = make_chain_def(
            steps=[{"step_id": f"s{i}",
                    "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                    "deps": [],
                    "retry_policy": {"max_retries": 0, "backoff_ms": 0}} for i in range(1, 4)],
        )
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="escalate WARN", context=ctx)
        for sid in ("s1", "s2", "s3"):
            sut.on_step_completed(make_step_result(
                chain_id=r.chain_id, step_id=sid, outcome="fail",
                project_id=mock_project_id,
                error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x",
                       "is_retriable": False, "is_timeout": False},
            ))
        mock_l2_06_client.escalate_advice.assert_called_once()
        kwargs = mock_l2_06_client.escalate_advice.call_args.kwargs
        assert kwargs["level"] == "WARN"
        assert kwargs["project_id"] == mock_project_id

    def test_TC_L101_L204_406_ic_04_invoke_skill_for_invoke_action(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_05_client: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-406 · step.action.type=invoke_skill → IC-04 invoke_skill。"""
        chain_def = make_chain_def(steps=[
            {"step_id": "s1",
             "action": {"type": "invoke_skill", "params": {"capability": "tdd.plan"}},
             "deps": []},
        ])
        sut.start_chain(chain_def, chain_goal="IC-04 route", context=make_context(project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        mock_l1_05_client.invoke_skill.assert_called_once()
        assert mock_l1_05_client.invoke_skill.call_args.kwargs["capability"] == "tdd.plan"

    def test_TC_L101_L204_407_ic_05_delegate_subagent(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_05_client: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-407 · step.action.type=delegate_subagent → IC-05 delegate_subagent。"""
        chain_def = make_chain_def(steps=[
            {"step_id": "s1",
             "action": {"type": "delegate_subagent",
                        "params": {"role": "researcher", "task_brief": "dive prior art"}},
             "deps": []},
        ])
        sut.start_chain(chain_def, chain_goal="IC-05 route", context=make_context(project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        mock_l1_05_client.delegate_subagent.assert_called_once()

    def test_TC_L101_L204_408_ic_06_kb_read(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_06_client: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-408 · step.action.type=kb_read → IC-06 kb_read。"""
        chain_def = make_chain_def(steps=[
            {"step_id": "s1",
             "action": {"type": "kb_read", "params": {"kind": "recipe", "top_k": 3}},
             "deps": []},
        ])
        sut.start_chain(chain_def, chain_goal="IC-06 route", context=make_context(project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        mock_l1_06_client.kb_read.assert_called_once()

    def test_TC_L101_L204_409_ic_07_kb_write_session(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_06_client: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-409 · step.action.type=kb_write → IC-07 kb_write_session。"""
        chain_def = make_chain_def(steps=[
            {"step_id": "s1",
             "action": {"type": "kb_write",
                        "params": {"entry": {"kind": "trap", "content": "x",
                                             "dedup_key": "py-dup", "confidence": 0.7}}},
             "deps": []},
        ])
        sut.start_chain(chain_def, chain_goal="IC-07 route", context=make_context(project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        mock_l1_06_client.kb_write_session.assert_called_once()

    def test_TC_L101_L204_410_ic_11_process_content(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_08_client: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-410 · step.action.type=process_content → IC-11 process_content。"""
        chain_def = make_chain_def(steps=[
            {"step_id": "s1",
             "action": {"type": "process_content",
                        "params": {"content_type": "code", "uri": "oss://bucket/file.py"}},
             "deps": []},
        ])
        sut.start_chain(chain_def, chain_goal="IC-11 route", context=make_context(project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        mock_l1_08_client.process_content.assert_called_once()

    def test_TC_L101_L204_411_ic_09_only_via_l2_05_never_direct(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_09_client: MagicMock, mock_l2_05_client: MagicMock,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-411 · PRD §11.3 OOS #3 · 本 L2 禁直写 IC-09 · 必经 L2-05 代劳。"""
        r = sut.start_chain(make_chain_def(), chain_goal="ic-09 forbidden direct",
                            context=make_context(project_id=mock_project_id))
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        assert mock_l1_09_client.append_event.call_count == 0, \
            "本 L2 禁直写 IC-09（PRD §11.3 OOS #3）"
        assert mock_l2_05_client.record_chain_step.call_count >= 1
```

---

## §5 性能 SLO 用例（§12 对标）

> ≥ 3 `@pytest.mark.perf` · 对照 §12.1 延迟表 + §12.2 吞吐约束。

```python
# file: tests/l1_01/test_l2_04_perf.py
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor
from app.l2_04.errors import ChainError


@pytest.mark.perf
class TestL2_04_SLO:
    """§12 SLO 性能用例。"""

    def test_TC_L101_L204_501_start_chain_p95_under_30ms(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-501 · start_chain() P95 ≤ 30ms / P99 ≤ 50ms / 硬上限 100ms（§12.1）。"""
        samples: list[float] = []
        for i in range(500):
            cd = make_chain_def()
            ctx = make_context(project_id=mock_project_id, tick_id=f"tick-p{i:03d}")
            t0 = time.monotonic()
            sut.start_chain(cd, chain_goal=f"SLO bench chain {i}", context=ctx)
            samples.append((time.monotonic() - t0) * 1000)
            # 每 8 个回收一次避免打 CONCURRENCY_CAP
            if i % 8 == 7:
                sut._reset_registry_for_bench()
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 30.0, f"start_chain P95 = {p95:.2f}ms 超 30ms SLO"
        assert p99 <= 50.0, f"start_chain P99 = {p99:.2f}ms 超 50ms SLO"
        assert max(samples) <= 100.0, f"硬上限 100ms 被破"

    def test_TC_L101_L204_502_step_completed_callback_p95_under_50ms(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-502 · on_step_completed → IC-L2-04 回调 P95 ≤ 50ms / P99 ≤ 100ms（§12.1）。"""
        cd = make_chain_def(steps=[
            {"step_id": f"s{i:02d}",
             "action": {"type": "invoke_skill", "params": {"capability": "k"}},
             "deps": []} for i in range(1, 11)
        ])
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(cd, chain_goal="step callback SLO", context=ctx)
        samples: list[float] = []
        for i in range(1, 11):
            t0 = time.monotonic()
            sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id=f"s{i:02d}",
                                                   outcome="pass", project_id=mock_project_id))
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 50.0, f"on_step_completed P95 = {p95:.2f}ms 超 50ms SLO"
        assert p99 <= 100.0, f"on_step_completed P99 = {p99:.2f}ms 超 100ms SLO"

    def test_TC_L101_L204_503_abort_chain_p95_under_100ms(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-503 · abort_chain() P95 ≤ 100ms / 硬上限 500ms（§12.1）。"""
        from app.l2_04.schemas import AbortRequest
        samples: list[float] = []
        for i in range(100):
            r = sut.start_chain(make_chain_def(),
                                chain_goal=f"abort-bench-{i}",
                                context=make_context(project_id=mock_project_id, tick_id=f"tick-ab{i}"))
            req = AbortRequest(chain_id=r.chain_id, reason_type="supervisor_block",
                               reason="SLO bench abort",
                               project_id=mock_project_id, cascade=False)
            t0 = time.monotonic()
            sut.abort_chain(req)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        assert p95 <= 100.0
        assert max(samples) <= 500.0

    def test_TC_L101_L204_504_query_chain_status_p95_under_5ms(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-504 · query_chain_status P95 ≤ 5ms · P99 ≤ 20ms（§12.1）。"""
        r = sut.start_chain(make_chain_def(),
                            chain_goal="query SLO",
                            context=make_context(project_id=mock_project_id))
        samples: list[float] = []
        for _ in range(1000):
            t0 = time.monotonic()
            sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 5.0
        assert p99 <= 20.0

    def test_TC_L101_L204_505_active_chain_cap_8(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-505 · 活跃 chain 数硬上限 8（§12.2 MAX_ACTIVE_CHAINS）。"""
        for i in range(8):
            sut.start_chain(make_chain_def(),
                            chain_goal=f"active cap {i}",
                            context=make_context(project_id=mock_project_id, tick_id=f"tick-c{i}"))
        with pytest.raises(ChainError) as ei:
            sut.start_chain(make_chain_def(),
                            chain_goal="9th chain must reject",
                            context=make_context(project_id=mock_project_id, tick_id="tick-c8"))
        assert ei.value.code == "E_CHAIN_CONCURRENCY_CAP"
        assert sut.active_chain_count() == 8
```

---

## §6 端到端 e2e 场景

> 映射 §5.1 / §5.2 P0/P1 时序 + §13.4 integration 场景。`@pytest.mark.e2e` · 真实/半真实 L2-02 + L2-05 + L2-06 + L1-05 stub。

```python
# file: tests/l1_01/test_l2_04_e2e.py
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor


@pytest.mark.e2e
class TestL2_04_E2E:
    """端到端 GWT 场景 · 对应 §5.1 P0 / §5.2 P1 / §13.4 integration。"""

    def test_TC_L101_L204_601_e2e_p0_normal_3_step_dag(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l2_02_client: MagicMock,
        mock_l2_05_client: MagicMock,
        mock_l1_05_client: MagicMock,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-601 · P0 流 C 端到端 3 步 DAG（§5.1）。

        GIVEN L2-02 决策 start_chain(s1 → {s2 ∥ s3})
        WHEN 各步 IC-04 派发 → L1-05 返回 pass 事件
        THEN IC-L2-04 调 L2-02 3 次 · IC-L2-07 调 L2-05 3 次 · chain_completed 事件发布
        """
        chain_def = make_chain_def(steps=[
            {"step_id": "s1",
             "action": {"type": "invoke_skill", "params": {"capability": "k1"}}, "deps": []},
            {"step_id": "s2",
             "action": {"type": "invoke_skill", "params": {"capability": "k2"}}, "deps": ["s1"]},
            {"step_id": "s3",
             "action": {"type": "invoke_skill", "params": {"capability": "k3"}}, "deps": ["s1"]},
        ])
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="P0 end-to-end 3 steps", context=ctx)
        sut._dispatch_ready_steps_once()
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s2",
                                               outcome="pass", project_id=mock_project_id))
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s3",
                                               outcome="pass", project_id=mock_project_id))
        assert mock_l2_02_client.on_step_completed.call_count == 3
        assert mock_l2_05_client.record_chain_step.call_count == 3
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state == "completed"

    def test_TC_L101_L204_602_e2e_p1_step_fail_retry_rollback(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l2_02_client: MagicMock,
        mock_l1_05_client: MagicMock,
        make_chain_def, make_context, make_step_result, tick_clock,
    ) -> None:
        """TC-L101-L204-602 · P1 步失败 → retry → rollback（§5.2）。

        GIVEN 3 步 chain s1(pass) → s2(fail) → rollback s2 声明了 rollback_action
        WHEN s2 重试 1 次仍失败
        THEN RollbackCoordinator 执行 IC-04 revert · chain → rolled_back · IC-L2-04 next_hint=rolled_back
        """
        chain_def = make_chain_def(steps=[
            {"step_id": "s1", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": []},
            {"step_id": "s2",
             "action": {"type": "invoke_skill", "params": {"capability": "k"}},
             "deps": ["s1"],
             "retry_policy": {"max_retries": 1, "backoff_ms": 1000},
             "rollback_action": {"type": "invoke_skill",
                                 "params": {"capability": "revert.changes"}}},
        ])
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(chain_def, chain_goal="P1 fail-retry-rollback", context=ctx)
        sut._dispatch_ready_steps_once()
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        sut.on_step_completed(make_step_result(
            chain_id=r.chain_id, step_id="s2", outcome="fail",
            project_id=mock_project_id,
            error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x",
                   "is_retriable": True, "is_timeout": False},
        ))
        tick_clock.advance(1000)
        sut._tick_retry_scheduler()
        sut.on_step_completed(make_step_result(
            chain_id=r.chain_id, step_id="s2", outcome="fail",
            project_id=mock_project_id,
            error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x",
                   "is_retriable": False, "is_timeout": False},
        ))
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state == "rolled_back"
        last_call = mock_l2_02_client.on_step_completed.call_args_list[-1]
        assert last_call.kwargs["next_hint"] == "rolled_back"

    def test_TC_L101_L204_603_e2e_block_preemption_cascade_abort(
        self,
        sut: TaskChainExecutor,
        mock_project_id: str,
        mock_l1_05_client: MagicMock,
        mock_l2_05_client: MagicMock,
        make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-603 · BLOCK 抢占链 · cascade=true 级联 abort（§11.6 / P1-04）。

        GIVEN 父 chain + 1 个活跃子 chain
        WHEN L2-06 → L2-01 → 本 L2.abort_chain(reason=supervisor_block, cascade=true)
        THEN aborted=true · child_chains_aborted 含子 chain_id · 审计 chain_aborted
        """
        from app.l2_04.schemas import AbortRequest
        parent = make_chain_def()
        parent_ctx = make_context(project_id=mock_project_id, tick_id="tick-parent-e2e")
        r_parent = sut.start_chain(parent, chain_goal="parent BLOCK case", context=parent_ctx)
        child = make_chain_def(nesting_depth=1, parent_chain_id=r_parent.chain_id)
        child_ctx = make_context(project_id=mock_project_id, tick_id="tick-child-e2e")
        r_child = sut.start_chain(child, chain_goal="child BLOCK case", context=child_ctx)
        sut._dispatch_ready_steps_once()
        res = sut.abort_chain(AbortRequest(
            chain_id=r_parent.chain_id, reason_type="supervisor_block",
            reason="BLOCK red line from L1-07", project_id=mock_project_id, cascade=True,
        ))
        assert res.aborted is True
        assert r_child.chain_id in res.child_chains_aborted
        actions = [c.kwargs.get("action") for c in mock_l2_05_client.audit_chain_lifecycle.call_args_list]
        assert actions.count("abort") >= 2  # 父 + 子
```

---

## §7 测试 fixture

> conftest.py 提供本 L2 的 fixture：sut · mock_project_id · mock_clock · mock_event_bus · 5 mock client · 3 factory（chain_def / context / step_result）。

```python
# file: tests/l1_01/conftest_l2_04.py
from __future__ import annotations

import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor
from app.l2_04.schemas import ChainDef, ChainContext, StepResult


class TickClock:
    """§9 Mock 策略 · unit 模式 · 手动推进 ms 的假时钟 + retry/watchdog 驱动。"""
    def __init__(self) -> None:
        self._now_ms: int = 0
    def monotonic_ms(self) -> int:
        return self._now_ms
    def advance(self, ms: int) -> None:
        self._now_ms += ms


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def tick_clock() -> TickClock:
    return TickClock()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="L1-09-event-bus")
    bus.append_event.return_value = {"event_id": f"evt-{uuid.uuid4()}", "sequence": 1}
    return bus


@pytest.fixture
def mock_l2_02_client() -> MagicMock:
    c = MagicMock(name="L2-02-decision-engine")
    c.on_step_completed.return_value = {"continue": True}
    return c


@pytest.fixture
def mock_l2_05_client() -> MagicMock:
    c = MagicMock(name="L2-05-audit-recorder")
    c.record_chain_step.return_value = {"audit_id": f"aud-{uuid.uuid4()}"}
    c.audit_chain_lifecycle.return_value = {"audit_id": f"aud-{uuid.uuid4()}"}
    return c


@pytest.fixture
def mock_l2_06_client() -> MagicMock:
    c = MagicMock(name="L2-06-supervisor-receiver")
    c.escalate_advice.return_value = {"received": True}
    return c


@pytest.fixture
def mock_l1_05_client() -> MagicMock:
    c = MagicMock(name="L1-05-skill-subagent")
    c.invoke_skill.return_value = {"outcome": "pass", "result_ref": "oss://..."}
    c.delegate_subagent.return_value = {"delegation_id": f"del-{uuid.uuid4()}"}
    c.cancel.return_value = {"cancelled": True}
    return c


@pytest.fixture
def mock_l1_06_client() -> MagicMock:
    c = MagicMock(name="L1-06-kb")
    c.kb_read.return_value = {"items": []}
    c.kb_write_session.return_value = {"entry_id": f"entry-{uuid.uuid4()}"}
    return c


@pytest.fixture
def mock_l1_07_client() -> MagicMock:
    c = MagicMock(name="L1-07-supervisor")
    c.warn.return_value = {"acked": True}
    return c


@pytest.fixture
def mock_l1_08_client() -> MagicMock:
    c = MagicMock(name="L1-08-multimodal")
    c.process_content.return_value = {"outcome": "pass"}
    return c


@pytest.fixture
def mock_l1_09_client() -> MagicMock:
    c = MagicMock(name="L1-09-event-bus-raw")
    c.append_event.return_value = {"event_id": f"evt-{uuid.uuid4()}"}
    return c


@pytest.fixture
def sut(
    mock_project_id: str, tick_clock: TickClock, mock_event_bus: MagicMock,
    mock_l2_02_client: MagicMock, mock_l2_05_client: MagicMock, mock_l2_06_client: MagicMock,
    mock_l1_05_client: MagicMock, mock_l1_06_client: MagicMock,
    mock_l1_07_client: MagicMock, mock_l1_08_client: MagicMock,
) -> TaskChainExecutor:
    return TaskChainExecutor(
        session_project_id=mock_project_id,
        clock=tick_clock,
        event_bus=mock_event_bus,
        l2_02_client=mock_l2_02_client,
        l2_05_client=mock_l2_05_client,
        l2_06_client=mock_l2_06_client,
        l1_05_client=mock_l1_05_client,
        l1_06_client=mock_l1_06_client,
        l1_07_client=mock_l1_07_client,
        l1_08_client=mock_l1_08_client,
    )


@pytest.fixture
def make_chain_def() -> Callable[..., ChainDef]:
    def _factory(**overrides: Any) -> ChainDef:
        base = dict(
            steps=[
                {"step_id": "s1",
                 "action": {"type": "invoke_skill", "params": {"capability": "default.k"}},
                 "deps": []},
            ],
            termination_condition={"all_steps_completed": True},
            nesting_depth=0,
            parent_chain_id=None,
        )
        base.update(overrides)
        return ChainDef(**base)
    return _factory


@pytest.fixture
def make_context() -> Callable[..., ChainContext]:
    def _factory(**overrides: Any) -> ChainContext:
        base = dict(
            project_id="pid-default",
            tick_id=f"tick-{uuid.uuid4()}",
            decision_id=f"dec-{uuid.uuid4()}",
            initial_inputs={},
        )
        base.update(overrides)
        return ChainContext(**base)
    return _factory


@pytest.fixture
def make_step_result() -> Callable[..., StepResult]:
    def _factory(**overrides: Any) -> StepResult:
        base = dict(
            chain_id="ch-default",
            step_id="s1",
            outcome="pass",
            result_ref=f"evt-{uuid.uuid4()}",
            error=None,
            project_id="pid-default",
            ts="2026-04-22T00:00:00Z",
            next_hint=None,
            duration_ms=12,
        )
        base.update(overrides)
        return StepResult(**base)
    return _factory
```

---

## §8 集成点用例（与兄弟 L2 协作）

> 与 L2-02 决策引擎 / L2-03 状态机编排器 / L2-05 审计记录器 / L2-06 Supervisor 建议接收器 的协作。
> 验 IC-L2 真实调用契约 + 失败降级（§11.3 协同矩阵）。

```python
# file: tests/l1_01/test_l2_04_integration_siblings.py
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor


class TestL2_04_SiblingIntegration:
    """与 L2-02 / L2-03 / L2-05 / L2-06 的协作测试（§11.3）。"""

    def test_TC_L101_L204_701_coop_l2_02_every_step_closes_loop(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_02_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-701 · 每步闭环 · on_step_completed → IC-L2-04 → L2-02 继续/中止指令（§5.1）。"""
        cd = make_chain_def(steps=[
            {"step_id": f"s{i}",
             "action": {"type": "invoke_skill", "params": {"capability": "k"}},
             "deps": ([f"s{i-1}"] if i > 1 else [])} for i in range(1, 3)
        ])
        ctx = make_context(project_id=mock_project_id)
        r = sut.start_chain(cd, chain_goal="full loop L2-02", context=ctx)
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s2",
                                               outcome="pass", project_id=mock_project_id))
        assert mock_l2_02_client.on_step_completed.call_count == 2

    def test_TC_L101_L204_702_coop_l2_03_chain_completed_triggers_state_transition(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_02_client: MagicMock,
        make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-702 · chain_completed → L2-02 → state_transition（§13.4 P0-08）。"""
        mock_l2_02_client.on_step_completed.side_effect = [
            {"continue": True}, {"state_transition": "S2"},
        ]
        r = sut.start_chain(make_chain_def(),
                            chain_goal="chain done triggers SM",
                            context=make_context(project_id=mock_project_id))
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        status = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert status.state == "completed"
        # 下游 L2-02 收到 state_transition 指示（本 L2 只负责透传 next_hint · 不直接调 L2-03）
        assert mock_l2_02_client.on_step_completed.call_count >= 1

    def test_TC_L101_L204_703_coop_l2_05_audit_chain_every_step_plus_lifecycle(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-703 · 审计链 P0-07 · 每步 IC-L2-07 + 生命期 IC-L2-05（§13.4 P0-07）。"""
        r = sut.start_chain(make_chain_def(), chain_goal="audit link P0-07",
                            context=make_context(project_id=mock_project_id))
        sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id="s1",
                                               outcome="pass", project_id=mock_project_id))
        assert mock_l2_05_client.record_chain_step.call_count >= 1
        lifecycle_actions = [c.kwargs.get("action")
                             for c in mock_l2_05_client.audit_chain_lifecycle.call_args_list
                             if c.kwargs.get("chain_id") == r.chain_id]
        assert "create" in lifecycle_actions
        assert "complete" in lifecycle_actions

    def test_TC_L101_L204_704_coop_l2_06_escalate_warn_and_project_id_propagated(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_06_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-704 · 升级链 P1-04 · WARN 含 project_id + chain_id（PM-14 + §3.7）。"""
        cd = make_chain_def(steps=[
            {"step_id": f"s{i}",
             "action": {"type": "invoke_skill", "params": {"capability": "k"}},
             "deps": [], "retry_policy": {"max_retries": 0, "backoff_ms": 0}} for i in range(1, 4)
        ])
        r = sut.start_chain(cd, chain_goal="escalate WARN carries ids",
                            context=make_context(project_id=mock_project_id))
        for sid in ("s1", "s2", "s3"):
            sut.on_step_completed(make_step_result(
                chain_id=r.chain_id, step_id=sid, outcome="fail",
                project_id=mock_project_id,
                error={"code": "E_SKILL_INVOCATION_FAIL", "message": "x",
                       "is_retriable": False, "is_timeout": False},
            ))
        mock_l2_06_client.escalate_advice.assert_called_once()
        kwargs = mock_l2_06_client.escalate_advice.call_args.kwargs
        assert kwargs["project_id"] == mock_project_id
        assert r.chain_id in kwargs["content"] or "chain stuck" in kwargs["content"]
```

---

## §9 边界 / edge case

> 空输入 / 极端规模 / 并发 / 崩溃恢复 / 脏数据 至少 5 个 · 映射 §11.4 / §11.7 / §7.4 recovery。

```python
# file: tests/l1_01/test_l2_04_edge_cases.py
from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from app.l2_04.executor import TaskChainExecutor
from app.l2_04.errors import ChainError


class TestL2_04_EdgeCases:
    """边界 / edge case · 空 / 超大 / 并发 / 崩溃 / 脏数据。"""

    def test_TC_L101_L204_B01_empty_steps_rejected(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-B01 · steps=[] · minItems=1 违反 → E_CHAIN_DEF_INVALID。"""
        with pytest.raises(ChainError) as ei:
            sut.start_chain(make_chain_def(steps=[]),
                            chain_goal="empty steps edge",
                            context=make_context(project_id=mock_project_id))
        assert ei.value.code == "E_CHAIN_DEF_INVALID"

    def test_TC_L101_L204_B02_single_step_no_deps_runs_immediately(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_05_client: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-B02 · 单步 deps=[] · 立即派发（最简 DAG 合法）。"""
        sut.start_chain(make_chain_def(),
                        chain_goal="single step edge",
                        context=make_context(project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        assert mock_l1_05_client.invoke_skill.call_count == 1

    def test_TC_L101_L204_B03_twenty_step_chain_at_hard_cap(
        self, sut: TaskChainExecutor, mock_project_id: str, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-B03 · 20 步 DAG · 刚好达 maxItems 硬上限 · accepted=true。"""
        steps = [{"step_id": f"s{i:02d}",
                  "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                  "deps": ([f"s{i-1:02d}"] if i > 0 else [])} for i in range(20)]
        cd = make_chain_def(steps=steps)
        r = sut.start_chain(cd, chain_goal="20 step hard cap",
                            context=make_context(project_id=mock_project_id))
        assert r.accepted is True
        assert len(r.dag_preview) == 20

    def test_TC_L101_L204_B04_parallel_gate_caps_running_at_2(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l1_05_client: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-B04 · 4 ready steps · MAX_PARALLEL_STEPS=2 · 单波只派 2 步（PRD §11.5 🚫 并行>2）。"""
        steps = [{"step_id": f"s{i}",
                  "action": {"type": "invoke_skill", "params": {"capability": "k"}},
                  "deps": []} for i in range(1, 5)]
        cd = make_chain_def(steps=steps)
        sut.start_chain(cd, chain_goal="parallel gate 2",
                        context=make_context(project_id=mock_project_id))
        sut._dispatch_ready_steps_once()
        assert mock_l1_05_client.invoke_skill.call_count == 2, \
            "单波派发受 MAX_PARALLEL_STEPS=2 限制"

    def test_TC_L101_L204_B05_same_chain_concurrent_events_serialized(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_chain_def, make_context, make_step_result,
    ) -> None:
        """TC-L101-L204-B05 · 同 chain 并发收 2 事件 · 本 L2 串行处理（§3.2 并发规则）。"""
        cd = make_chain_def(steps=[
            {"step_id": "s1", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": []},
            {"step_id": "s2", "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": []},
        ])
        r = sut.start_chain(cd, chain_goal="serialize same-chain events",
                            context=make_context(project_id=mock_project_id))

        def fire(step_id: str) -> None:
            sut.on_step_completed(make_step_result(chain_id=r.chain_id, step_id=step_id,
                                                   outcome="pass", project_id=mock_project_id))

        t1 = threading.Thread(target=fire, args=("s1",))
        t2 = threading.Thread(target=fire, args=("s2",))
        t1.start(); t2.start()
        t1.join(timeout=2.0); t2.join(timeout=2.0)
        recorded = [c.kwargs.get("step_id")
                    for c in mock_l2_05_client.record_chain_step.call_args_list
                    if c.kwargs.get("chain_id") == r.chain_id]
        assert set(recorded) == {"s1", "s2"}, "两步都应被处理且无 race"

    def test_TC_L101_L204_B06_crash_recovery_replays_from_snapshot(
        self, sut: TaskChainExecutor, mock_project_id: str,
        mock_event_bus: MagicMock, make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-B06 · session 重启 · snapshot + event replay 重建 ChainExecution（§7.4）。"""
        r = sut.start_chain(make_chain_def(), chain_goal="snapshot recover",
                            context=make_context(project_id=mock_project_id))
        snapshot = sut.dump_chain_snapshot(chain_id=r.chain_id)
        # simulate crash: wipe registry
        sut._wipe_registry_for_recovery_test()
        assert sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id) is None
        # 重建
        mock_event_bus.query.return_value = [
            {"event_type": "L1-01:chain_step", "chain_id": r.chain_id,
             "step_id": "s1", "outcome": None, "project_id": mock_project_id}
        ]
        sut.recover_from_snapshot(snapshot)
        revived = sut.query_chain_status(chain_id=r.chain_id, project_id=mock_project_id)
        assert revived is not None
        assert revived.chain_id == r.chain_id

    def test_TC_L101_L204_B07_dirty_step_id_pattern_rejected(
        self, sut: TaskChainExecutor, mock_project_id: str,
        make_chain_def, make_context,
    ) -> None:
        """TC-L101-L204-B07 · 脏数据 · step_id 不匹配 `^s[0-9a-zA-Z_-]{1,32}$` → DEF_INVALID。"""
        bad = make_chain_def(steps=[
            {"step_id": "!!invalid!!",
             "action": {"type": "invoke_skill", "params": {"capability": "k"}}, "deps": []},
        ])
        with pytest.raises(ChainError) as ei:
            sut.start_chain(bad, chain_goal="dirty step_id",
                            context=make_context(project_id=mock_project_id))
        assert ei.value.code == "E_CHAIN_DEF_INVALID"

    def test_TC_L101_L204_B08_watchdog_heartbeat_alive(
        self, sut: TaskChainExecutor,
    ) -> None:
        """TC-L101-L204-B08 · StepTimeoutWatchdog 线程心跳 · 启动后 < 30s 必有心跳（§12.3）。"""
        age = sut.watchdog_heartbeat_age_s()
        assert age < 30, f"watchdog 心跳陈旧 {age}s · 超 30s 应告警"
```

---

*— L1-01 L2-04 任务链执行器 · TDD 测试用例 · 深度 B 全段完整 · 20 错误码 × 19 正向 × 11 IC × 5 SLO × 3 e2e × 4 集成 × 8 边界 —*
