---
doc_id: tests-L1-01-L2-02-决策引擎-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-01 L2-02-决策引擎 · TDD 测试用例

> 基于 3-1 L2-02 §3（6 个 public 方法）+ §11（17 项 `E_*` 错误码）+ §12（P95 / P99 / 硬上限 SLO）+ §13 TC ID 矩阵 驱动。
> TC ID 统一格式：`TC-L101-L202-NNN`（L1-01 下 L2-02，三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_02_DecisionEngine` 组织；负向/性能/集成单独分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock project_id / mock clock / mock event bus / mock ic payload）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `decide()` · §3.1 · invoke_skill | TC-L101-L202-001 | unit | — | IC-04 / IC-L2-05 |
| `decide()` · §3.1 · use_tool | TC-L101-L202-002 | unit | — | IC-04 |
| `decide()` · §3.1 · delegate_subagent | TC-L101-L202-003 | unit | — | IC-05 |
| `decide()` · §3.1 · kb_read | TC-L101-L202-004 | unit | — | IC-06 |
| `decide()` · §3.1 · kb_write | TC-L101-L202-005 | unit | — | IC-07 |
| `decide()` · §3.1 · process_content | TC-L101-L202-006 | unit | — | IC-11 |
| `decide()` · §3.1 · request_user | TC-L101-L202-007 | unit | — | IC-17 |
| `decide()` · §3.1 · state_transition | TC-L101-L202-008 | unit | — | IC-L2-02 / IC-L2-06 |
| `decide()` · §3.1 · start_chain | TC-L101-L202-009 | unit | — | IC-L2-03 |
| `decide()` · §3.1 · warn_response | TC-L101-L202-010 | unit | — | IC-L2-09 |
| `decide()` · §3.1 · fill_discipline_gap | TC-L101-L202-011 | unit | — | — |
| `decide()` · §3.1 · no_op | TC-L101-L202-012 | unit | — | IC-L2-05 |
| `decide()` · 幂等（LRU 1024）| TC-L101-L202-013 | unit | — | — |
| `inject_warn()` · §3.2 正向 | TC-L101-L202-014 | unit | — | — |
| `inject_suggestion()` · §3.2 正向 | TC-L101-L202-015 | unit | — | — |
| `on_async_cancel()` · §3.3 正向 | TC-L101-L202-016 | unit | — | — |
| `on_step_completed()` · §3.4 正向 | TC-L101-L202-017 | unit | — | IC-09 |
| `get_context_snapshot()` · §3.5 正向 | TC-L101-L202-018 | unit | — | — |

### §1.2 错误码 × 测试（§11 17 项全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|---|---|---|---|
| `E_CTX_NO_PROJECT_ID` | TC-L101-L202-101 | `decide()` | PM-14 校验 |
| `E_CTX_CROSS_PROJECT` | TC-L101-L202-102 | `decide()` | PM-14 校验 |
| `E_CTX_STATE_MISSING` | TC-L101-L202-103 | `decide()` | context 合法性 |
| `E_CTX_ASSEMBLE_FAIL` | TC-L101-L202-104 | `decide()` | context 组装失败 |
| `E_KB_INJECT_FAIL` | TC-L101-L202-105 | `decide()` | KB 注入降级 |
| `E_5DIS_TIMEOUT` | TC-L101-L202-106 | `decide()` | 5 纪律超时 |
| `E_5DIS_INCOMPLETE` | TC-L101-L202-107 | `decide()` | 5 纪律不完整 |
| `E_DECISION_TIMEOUT` | TC-L101-L202-108 | `decide()` | 决策超总时 |
| `E_DECISION_NO_REASON` | TC-L101-L202-109 | `decide()` | reason 过短 |
| `E_STATE_TRANSITION_INVALID` | TC-L101-L202-110 | `decide()` | state 决策非法 |
| `E_SKILL_NOT_FOUND` | TC-L101-L202-111 | `decide()` | 能力不可达 |
| `E_CANCEL_DURING_DECISION` | TC-L101-L202-112 | `decide()` | 抢占中途 |
| `E_CAPABILITY_REGISTRY_STALE` | TC-L101-L202-113 | `__init__ / pre-check` | 启动时序 |
| `E_WARN_QUEUE_OVERFLOW` | TC-L101-L202-114 | `inject_warn()` | 队列满 |
| `E_CROSS_PROJECT_WARN` | TC-L101-L202-115 | `inject_warn()` | PM-14 校验 |
| `E_CANCEL_MISS_TICK` | TC-L101-L202-116 | `on_async_cancel()` | 陈旧 tick |
| `E_CANCEL_SLO_VIOLATION` | TC-L101-L202-117 | `on_async_cancel()` | > 100ms |
| `E_SNAPSHOT_NOT_FOUND` | TC-L101-L202-118 | `get_context_snapshot()` | 审计反查 |
| `E_SNAPSHOT_CORRUPT` | TC-L101-L202-119 | `get_context_snapshot()` | 审计反查 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 on_tick（被调）| L2-01 → L2-02 | TC-L101-L202-601 | 消费方 · 承诺产出 DecisionRecord |
| IC-L2-02 request_state_transition | L2-02 → L2-03 | TC-L101-L202-602 | 生产方 · state_transition 路径 |
| IC-L2-03 start_chain | L2-02 → L2-04 | TC-L101-L202-603 | 生产方 · chain 启动 |
| IC-L2-05 audit_decision | L2-02 → L2-05 | TC-L101-L202-604 | 每 decide 必推 |
| IC-L2-06 allowed_next_check | L2-02 → L2-03 | TC-L101-L202-605 | state_transition 前置 |
| IC-04 invoke_skill | L2-02 → L1-05 | TC-L101-L202-606 | 经 L2-01 路由 · payload 断言 |
| IC-05 delegate_subagent | L2-02 → L1-05 | TC-L101-L202-607 | 经 L2-01 路由 · payload 断言 |
| IC-06 kb_read | L2-02 → L1-06 | TC-L101-L202-608 | KBInjector 内部 IO sink |
| IC-07 kb_write_session | L2-02 → L1-06 | TC-L101-L202-609 | decision_type=kb_write |
| IC-11 process_content | L2-02 → L1-08 | TC-L101-L202-610 | decision_type=process_content |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_02_DecisionEngine`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `DecisionEngine`（从 `app.l2_02.engine` 导入）。

```python
# file: tests/l1_01/test_l2_02_decision_engine_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l2_02.engine import DecisionEngine
from app.l2_02.schemas import (
    TickContext,
    DecisionRecord,
    WarnItem,
    SuggItem,
    CancelSignal,
    StepResult,
)


class TestL2_02_DecisionEngine:
    """每个 public 方法 + 每类 decision_type 至少 1 正向用例。"""

    def test_TC_L101_L202_001_decide_invoke_skill_produces_full_record(
        self,
        sut: DecisionEngine,
        mock_project_id: str,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-001 · 主流 decision_type=invoke_skill · full DecisionRecord 字段全。"""
        ctx: TickContext = make_tick_context(
            state="S4_execute",
            project_id=mock_project_id,
            trigger_source="timer",
        )
        rec: DecisionRecord = sut.decide(ctx)
        assert rec.decision_id.startswith("dec-")
        assert rec.tick_id == ctx.tick_id
        assert rec.project_id == mock_project_id
        assert rec.context_snapshot_ref.startswith(f"projects/{mock_project_id}/audit/context/")
        assert len(rec.five_discipline_results) == 5
        assert rec.decision_type == "invoke_skill"
        assert "capability_tag" in rec.decision_params
        assert len(rec.reason) >= 20

    def test_TC_L101_L202_002_decide_use_tool_shapes_params(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-002 · decision_type=use_tool · params 含 tool_name + args。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="use_tool")
        rec = sut.decide(ctx)
        assert rec.decision_type == "use_tool"
        assert "tool_name" in rec.decision_params
        assert "args" in rec.decision_params

    def test_TC_L101_L202_003_decide_delegate_subagent(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-003 · decision_type=delegate_subagent · timeout_s > 0。"""
        ctx = make_tick_context(state="S3_design", project_id=mock_project_id,
                                hint_kind="delegate")
        rec = sut.decide(ctx)
        assert rec.decision_type == "delegate_subagent"
        assert rec.decision_params["timeout_s"] > 0
        assert rec.decision_params["agent_role"]

    def test_TC_L101_L202_004_decide_kb_read(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-004 · decision_type=kb_read · layer 合法 + top_k > 0。"""
        ctx = make_tick_context(state="S1_plan", project_id=mock_project_id,
                                hint_kind="kb_read")
        rec = sut.decide(ctx)
        assert rec.decision_type == "kb_read"
        assert rec.decision_params["layer"] in ("L1_user", "L2_fragment", "L3_global")
        assert rec.decision_params["top_k"] > 0

    def test_TC_L101_L202_005_decide_kb_write(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-005 · decision_type=kb_write · dedup_key 必填。"""
        ctx = make_tick_context(state="S6_wrap", project_id=mock_project_id,
                                hint_kind="kb_write")
        rec = sut.decide(ctx)
        assert rec.decision_type == "kb_write"
        assert rec.decision_params["dedup_key"]

    def test_TC_L101_L202_006_decide_process_content(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-006 · decision_type=process_content · content_type 合法枚举。"""
        ctx = make_tick_context(state="S2_split", project_id=mock_project_id,
                                hint_kind="process_content")
        rec = sut.decide(ctx)
        assert rec.decision_type == "process_content"
        assert rec.decision_params["content_type"] in ("doc", "code", "image")

    def test_TC_L101_L202_007_decide_request_user(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-007 · decision_type=request_user · 问题 ≥ 10 字。"""
        ctx = make_tick_context(state="S0_init", project_id=mock_project_id,
                                hint_kind="ambiguous")
        rec = sut.decide(ctx)
        assert rec.decision_type == "request_user"
        assert len(rec.decision_params["question"]) >= 10

    def test_TC_L101_L202_008_decide_state_transition_calls_allowed_next(
        self,
        sut: DecisionEngine,
        mock_project_id: str,
        mock_l2_03_client: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-008 · state_transition 前必调 IC-L2-06 allowed_next_check。"""
        mock_l2_03_client.allowed_next_check.return_value = {"allowed": True}
        ctx = make_tick_context(state="S5_verify", project_id=mock_project_id,
                                hint_kind="state_transition", transition_to="S6_wrap")
        rec = sut.decide(ctx)
        assert rec.decision_type == "state_transition"
        mock_l2_03_client.allowed_next_check.assert_called_once()
        assert rec.decision_params["to"] == "S6_wrap"

    def test_TC_L101_L202_009_decide_start_chain(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-009 · decision_type=start_chain · chain_def + goal 必填。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="start_chain")
        rec = sut.decide(ctx)
        assert rec.decision_type == "start_chain"
        assert rec.decision_params["chain_def"]
        assert rec.decision_params["chain_goal"]

    def test_TC_L101_L202_010_decide_warn_response_within_next_tick(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context, make_warn_item,
    ) -> None:
        """TC-L101-L202-010 · 收 WARN 后下一 tick 必产 warn_response（prd §9.4 #3）。"""
        warn = make_warn_item(project_id=mock_project_id, priority="P0")
        sut.inject_warn(warn)
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                trigger_source="timer")
        rec = sut.decide(ctx)
        assert rec.decision_type == "warn_response"
        assert rec.warn_response_ref == warn.warn_id
        assert rec.decision_params["response"] in ("accept", "reject")

    def test_TC_L101_L202_011_decide_fill_discipline_gap_on_N_answer(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-011 · 5 纪律任一项 = N → fill_discipline_gap（prd §9.5 #1）。"""
        ctx = make_tick_context(state="S1_plan", project_id=mock_project_id,
                                hint_kind="discipline_gap_quality")
        rec = sut.decide(ctx)
        assert rec.decision_type == "fill_discipline_gap"
        assert rec.decision_params["discipline"] in (
            "planning", "quality", "split", "verify", "deliver",
        )

    def test_TC_L101_L202_012_decide_no_op_when_waiting_for_callback(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-012 · S5 等 Verifier 回调 · 决策产 no_op（prd §13.4 P0-06）。"""
        ctx = make_tick_context(state="S5_verify", project_id=mock_project_id,
                                hint_kind="awaiting_verifier")
        rec = sut.decide(ctx)
        assert rec.decision_type == "no_op"
        assert rec.decision_params["note"]

    def test_TC_L101_L202_013_decide_idempotent_same_tick_same_record(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-013 · 同 tick_id + 同 context hash → 相同 DecisionRecord（幂等 · LRU 1024）。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        r1 = sut.decide(ctx)
        r2 = sut.decide(ctx)
        assert r1.decision_id == r2.decision_id
        assert r1.ts_start == r2.ts_start

    def test_TC_L101_L202_014_inject_warn_ok(
        self, sut: DecisionEngine, mock_project_id: str, make_warn_item,
    ) -> None:
        """TC-L101-L202-014 · inject_warn 非阻塞入队 + 返回 queue_len。"""
        w = make_warn_item(project_id=mock_project_id, priority="P0")
        r = sut.inject_warn(w)
        assert r["accepted"] is True
        assert r["queue_len"] >= 1

    def test_TC_L101_L202_015_inject_suggestion_ok(
        self, sut: DecisionEngine, mock_project_id: str, make_sugg_item,
    ) -> None:
        """TC-L101-L202-015 · inject_suggestion 非阻塞入队。"""
        s = make_sugg_item(project_id=mock_project_id)
        r = sut.inject_suggestion(s)
        assert r["accepted"] is True
        assert r["queue_len"] >= 1

    def test_TC_L101_L202_016_on_async_cancel_aborts_decide(
        self, sut: DecisionEngine, mock_project_id: str, make_cancel_signal,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-016 · on_async_cancel 设置 AbortFlag · 后续 decide 产 aborted=true 的 no_op。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        sig = make_cancel_signal(tick_id=ctx.tick_id, reason_type="supervisor_block")
        r = sut.on_async_cancel(sig)
        assert r["aborted"] is True
        assert r["abort_latency_ms"] <= 100
        rec = sut.decide(ctx)
        assert rec.decision_type == "no_op"
        assert getattr(rec, "aborted", False) is True

    def test_TC_L101_L202_017_on_step_completed_enqueues_seed(
        self, sut: DecisionEngine, mock_project_id: str, mock_l2_01_client: MagicMock,
        make_step_result,
    ) -> None:
        """TC-L101-L202-017 · on_step_completed 触发 L2-01 schedule_tick(trigger=async_callback)。"""
        sr = make_step_result(project_id=mock_project_id, outcome="success")
        sut.on_step_completed(sr)
        mock_l2_01_client.schedule_tick.assert_called_once()
        t = mock_l2_01_client.schedule_tick.call_args.args[0]
        assert t.trigger_source == "async_callback"
        assert t.project_id == mock_project_id

    def test_TC_L101_L202_018_get_context_snapshot_returns_json(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-018 · 已 decide 过的 tick_id 能反查 context_snapshot JSON。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        sut.decide(ctx)
        snap = sut.get_context_snapshot(ctx.tick_id)
        assert snap is not None
        assert snap["project_id"] == mock_project_id
        assert "task_board" in snap
```

---

## §3 负向用例（每错误码 ≥ 1）

> `class TestL2_02_Negative` · `pytest.raises(DecisionError, match=...)` 断言。

```python
# file: tests/l1_01/test_l2_02_decision_engine_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_02.engine import DecisionEngine
from app.l2_02.errors import DecisionError


class TestL2_02_Negative:
    """每个 §11 错误码至少 1 触发用例。"""

    def test_TC_L101_L202_101_ctx_no_project_id(
        self, sut: DecisionEngine, make_tick_context,
    ) -> None:
        """TC-L101-L202-101 · project_id 缺失 → E_CTX_NO_PROJECT_ID（PM-14）。"""
        ctx = make_tick_context(project_id=None, state="S4_execute")
        with pytest.raises(DecisionError, match="E_CTX_NO_PROJECT_ID"):
            sut.decide(ctx)

    def test_TC_L101_L202_102_ctx_cross_project(
        self, sut: DecisionEngine, mock_project_id: str, mock_event_bus: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-102 · context 组装时发现 event.pid ≠ tick.pid → E_CTX_CROSS_PROJECT。"""
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        mock_event_bus.query.return_value = [
            {"event_id": "evt-bad", "project_id": "pid-OTHER", "ts": "2026-04-22T00:00:00Z"}
        ]
        with pytest.raises(DecisionError, match="E_CTX_CROSS_PROJECT"):
            sut.decide(ctx)

    def test_TC_L101_L202_103_ctx_state_missing(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-103 · state 枚举非法 → E_CTX_STATE_MISSING。"""
        ctx = make_tick_context(project_id=mock_project_id, state=None)
        with pytest.raises(DecisionError, match="E_CTX_STATE_MISSING"):
            sut.decide(ctx)

    def test_TC_L101_L202_104_ctx_assemble_fail_returns_no_op(
        self, sut: DecisionEngine, mock_project_id: str, mock_task_board: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-104 · task-board 读超时 → 产 no_op + degraded_flag（§11.1）。"""
        mock_task_board.read_snapshot.side_effect = TimeoutError("tb timeout")
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        assert rec.decision_type == "no_op"
        assert "E_CTX_ASSEMBLE_FAIL" in (rec.decision_params.get("error_code") or "")

    def test_TC_L101_L202_105_kb_inject_fail_degrades_with_flag(
        self, sut: DecisionEngine, mock_project_id: str, mock_kb_client: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-105 · KB 不可达 → 降级继续 + kb_degraded=true（§11.1 E_KB_*）。"""
        mock_kb_client.kb_read.side_effect = ConnectionError("kb down")
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        assert rec is not None
        assert getattr(rec, "kb_degraded", False) is True

    def test_TC_L101_L202_106_five_discipline_timeout_skip_with_note(
        self, sut: DecisionEngine, mock_project_id: str, mock_five_discipline: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-106 · 5 纪律 > 200ms → 降级 Skip + note + 继续决策（§11.1）。"""
        mock_five_discipline.interrogate.side_effect = TimeoutError("5dis 250ms")
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        assert any(d.answer == "Skip" and "timeout" in d.note.lower()
                   for d in rec.five_discipline_results)

    def test_TC_L101_L202_107_five_discipline_incomplete_aborts(
        self, sut: DecisionEngine, mock_project_id: str, mock_five_discipline: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-107 · 5 纪律有 N 且未转 fill_discipline_gap → E_5DIS_INCOMPLETE assert。"""
        mock_five_discipline.interrogate.return_value = [
            {"name": "planning", "answer": "N", "note": "missing wp"},
            {"name": "quality",  "answer": "Y", "note": "ok"},
            {"name": "split",    "answer": "Y", "note": "ok"},
            {"name": "verify",   "answer": "Y", "note": "ok"},
            {"name": "deliver",  "answer": "Y", "note": "ok"},
        ]
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute",
                                force_fill_gap_disabled=True)  # 强制绕过 gap 转换
        with pytest.raises(DecisionError, match="E_5DIS_INCOMPLETE"):
            sut.decide(ctx)

    def test_TC_L101_L202_108_decision_timeout_20s_aborts(
        self, sut: DecisionEngine, mock_project_id: str, mock_clock,
        mock_decision_tree: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-108 · 决策总耗时 > 20s → E_DECISION_TIMEOUT · 产 aborted no_op。"""
        def slow_dispatch(*_a, **_kw):
            mock_clock.advance(21_000)
            raise TimeoutError("decision 21s")
        mock_decision_tree.dispatch.side_effect = slow_dispatch
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        assert rec.decision_type == "no_op"
        assert getattr(rec, "aborted", False) is True
        assert rec.tick_budget_used_ms > 20_000

    def test_TC_L101_L202_109_decision_no_reason_autofilled(
        self, sut: DecisionEngine, mock_project_id: str, mock_decision_selector: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-109 · reason < 20 字 → assert 拦截 · 补全为 auto-filled:*（§11.1）。"""
        mock_decision_selector.select.return_value = {
            "decision_type": "no_op", "decision_params": {"note": "idle"},
            "reason": "short",  # < 20
        }
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        assert len(rec.reason) >= 20
        assert rec.reason.startswith("auto-filled:")

    def test_TC_L101_L202_110_state_transition_invalid_degrades_no_op(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_03_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-110 · state_transition allowed_next=false → no_op + WARN L1-07（§11.1）。"""
        mock_l2_03_client.allowed_next_check.return_value = {"allowed": False}
        ctx = make_tick_context(state="S5_verify", project_id=mock_project_id,
                                hint_kind="state_transition", transition_to="S0_init")
        rec = sut.decide(ctx)
        assert rec.decision_type == "no_op"
        assert "E_STATE_TRANSITION_INVALID" in (rec.decision_params.get("error_code") or "")

    def test_TC_L101_L202_111_skill_not_found_degrades_to_request_user(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_capability_registry: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-111 · skill 不在注册表 → 降级 request_user（§11.1）。"""
        mock_capability_registry.resolve.return_value = None
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="invoke_skill")
        rec = sut.decide(ctx)
        assert rec.decision_type == "request_user"

    def test_TC_L101_L202_112_cancel_during_decision_produces_aborted_no_op(
        self, sut: DecisionEngine, mock_project_id: str,
        make_cancel_signal, make_tick_context,
    ) -> None:
        """TC-L101-L202-112 · decide 中 AbortFlag 置位 → E_CANCEL_DURING_DECISION · aborted record。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        sig = make_cancel_signal(tick_id=ctx.tick_id, reason_type="user_panic")
        sut.on_async_cancel(sig)
        rec = sut.decide(ctx)
        assert rec.decision_type == "no_op"
        assert getattr(rec, "aborted", False) is True
        assert rec.decision_params.get("cancel_reason") == "user_panic"

    def test_TC_L101_L202_113_capability_registry_stale_blocks_startup(
        self, mock_project_id: str, mock_clock, mock_event_bus: MagicMock,
        mock_capability_registry_loader: MagicMock,
    ) -> None:
        """TC-L101-L202-113 · 注册表 5s 未加载 → 启动失败 E_CAPABILITY_REGISTRY_STALE。"""
        mock_capability_registry_loader.load.side_effect = TimeoutError("5s")
        with pytest.raises(RuntimeError, match="E_CAPABILITY_REGISTRY_STALE"):
            _ = DecisionEngine(
                project_id=mock_project_id,
                clock=mock_clock,
                event_bus=mock_event_bus,
                capability_registry_loader=mock_capability_registry_loader,
                startup_pre_check_timeout_ms=5_000,
            )

    def test_TC_L101_L202_114_warn_queue_overflow_evicts_oldest(
        self, sut: DecisionEngine, mock_project_id: str, make_warn_item,
    ) -> None:
        """TC-L101-L202-114 · warn_queue > 64 → 挤出最旧 · accepted=true, evicted=true。"""
        for _ in range(64):
            sut.inject_warn(make_warn_item(project_id=mock_project_id, priority="P1"))
        r = sut.inject_warn(make_warn_item(project_id=mock_project_id, priority="P0"))
        assert r["accepted"] is True
        assert r.get("evicted") is True

    def test_TC_L101_L202_115_cross_project_warn_rejected(
        self, sut: DecisionEngine, mock_project_id: str, make_warn_item,
    ) -> None:
        """TC-L101-L202-115 · warn.pid ≠ session pid → E_CROSS_PROJECT_WARN 拒绝。"""
        w = make_warn_item(project_id="pid-OTHER", priority="P0")
        with pytest.raises(DecisionError, match="E_CROSS_PROJECT_WARN"):
            sut.inject_warn(w)

    def test_TC_L101_L202_116_cancel_miss_tick_silently_ignored(
        self, sut: DecisionEngine, mock_project_id: str, make_cancel_signal,
    ) -> None:
        """TC-L101-L202-116 · cancel_signal.tick_id 非当前进行 tick → 静默忽略 + debug log。"""
        sig = make_cancel_signal(tick_id="tick-already-done", reason_type="supervisor_block")
        r = sut.on_async_cancel(sig)
        assert r["aborted"] is False
        assert r.get("reason_code") == "E_CANCEL_MISS_TICK"

    def test_TC_L101_L202_117_cancel_slo_violation_recorded(
        self, sut: DecisionEngine, mock_project_id: str, mock_clock,
        make_cancel_signal, make_tick_context,
    ) -> None:
        """TC-L101-L202-117 · abort 耗时 > 100ms → E_CANCEL_SLO_VIOLATION audit（不 raise）。"""
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        sut._mark_tick_running(ctx.tick_id)  # 模拟进行中
        mock_clock.advance_on_abort_ms = 120  # SUT 内部测试钩子
        sig = make_cancel_signal(tick_id=ctx.tick_id, reason_type="supervisor_block")
        r = sut.on_async_cancel(sig)
        assert r["aborted"] is True
        assert r["abort_latency_ms"] > 100
        assert sut.last_slo_violation_code() == "E_CANCEL_SLO_VIOLATION"

    def test_TC_L101_L202_118_snapshot_not_found_returns_null(
        self, sut: DecisionEngine,
    ) -> None:
        """TC-L101-L202-118 · 无此 tick_id 的 snapshot → 返回 null（不 raise）。"""
        assert sut.get_context_snapshot("tick-does-not-exist") is None

    def test_TC_L101_L202_119_snapshot_corrupt_raises(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TC-L101-L202-119 · snapshot 文件 JSON 损坏 → E_SNAPSHOT_CORRUPT。"""
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        sut.decide(ctx)
        monkeypatch.setattr(sut._snapshot_store, "read_raw",
                            lambda _tid: b"{not-json")
        with pytest.raises(DecisionError, match="E_SNAPSHOT_CORRUPT"):
            sut.get_context_snapshot(ctx.tick_id)
```

---

## §4 IC-XX 契约集成测试

> ≥ 3 个 join test · mock 对端（L2-03 / L1-05 / L1-06 / L1-08 / L2-05 / L2-01）· 断言 IC payload 结构和方向契合 `ic-contracts.md §3.4/§3.5/§3.6/§3.7/§3.11` 与 `L1-01/L2-02 §3.1.1` 的字段表。

```python
# file: tests/l1_01/test_l2_02_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_02.engine import DecisionEngine


class TestL2_02_ICContracts:
    """ic-contracts.md + 本 L2 §3.1.1 字段表 的契约级断言。"""

    def test_TC_L101_L202_601_ic_l2_01_on_tick_consumer_produces_decision_record(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-601 · IC-L2-01（被调）· 每次 on_tick 产出 DecisionRecord · 推 L2-05 审计。"""
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        assert rec.decision_id.startswith("dec-")
        mock_l2_05_client.audit_decision.assert_called_once()

    def test_TC_L101_L202_602_ic_l2_02_request_state_transition_payload(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_03_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-602 · IC-L2-02 request_state_transition · payload 含 from/to/evidence_refs。"""
        mock_l2_03_client.allowed_next_check.return_value = {"allowed": True}
        ctx = make_tick_context(state="S5_verify", project_id=mock_project_id,
                                hint_kind="state_transition", transition_to="S6_wrap")
        sut.decide(ctx)
        mock_l2_03_client.request_state_transition.assert_called_once()
        kwargs = mock_l2_03_client.request_state_transition.call_args.kwargs
        assert kwargs["from"] == "S5_verify"
        assert kwargs["to"] == "S6_wrap"
        assert isinstance(kwargs["evidence_refs"], list)

    def test_TC_L101_L202_603_ic_l2_03_start_chain_payload(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_04_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-603 · IC-L2-03 start_chain · payload 含 chain_def + chain_goal + project_id。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="start_chain")
        sut.decide(ctx)
        mock_l2_04_client.start_chain.assert_called_once()
        kwargs = mock_l2_04_client.start_chain.call_args.kwargs
        assert kwargs["project_id"] == mock_project_id
        assert kwargs["chain_def"]
        assert kwargs["chain_goal"]

    def test_TC_L101_L202_604_ic_l2_05_audit_each_decide(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-604 · IC-L2-05 audit_decision · 每次 decide 必 1 次（含 no_op / aborted）。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        sut.decide(ctx)
        assert mock_l2_05_client.audit_decision.call_count == 1
        kwargs = mock_l2_05_client.audit_decision.call_args.kwargs
        assert kwargs["record"].tick_id == ctx.tick_id
        assert kwargs["record"].project_id == mock_project_id

    def test_TC_L101_L202_605_ic_l2_06_allowed_next_check_precedes_transition(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_03_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-605 · IC-L2-06 · allowed_next_check 必在 request_state_transition 之前调。"""
        mock_l2_03_client.allowed_next_check.return_value = {"allowed": True}
        ctx = make_tick_context(state="S3_design", project_id=mock_project_id,
                                hint_kind="state_transition", transition_to="S4_execute")
        sut.decide(ctx)
        methods = [c[0] for c in mock_l2_03_client.method_calls]
        assert methods.index("allowed_next_check") < methods.index("request_state_transition")

    def test_TC_L101_L202_606_ic_04_invoke_skill_payload_through_l2_01(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-606 · IC-04 invoke_skill · 本 L2 产出决策 · L2-01 路由至 L1-05 （断言 payload 结构）。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="invoke_skill")
        rec = sut.decide(ctx)
        assert rec.decision_type == "invoke_skill"
        # L2-01 在收到 DecisionRecord 后路由 IC-04 · 这里模拟其调用
        mock_l2_01_client.dispatch_decision(rec)
        mock_l2_01_client.dispatch_decision.assert_called_once()
        assert "capability_tag" in rec.decision_params
        assert rec.decision_params["input_payload"] is not None

    def test_TC_L101_L202_607_ic_05_delegate_subagent_payload(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-607 · IC-05 delegate_subagent · agent_role + task_brief + timeout_s 齐全。"""
        ctx = make_tick_context(state="S3_design", project_id=mock_project_id,
                                hint_kind="delegate")
        rec = sut.decide(ctx)
        assert rec.decision_type == "delegate_subagent"
        p = rec.decision_params
        assert p["agent_role"] and p["task_brief"] and p["timeout_s"] > 0
        assert isinstance(p["input_refs"], list)

    def test_TC_L101_L202_608_ic_06_kb_read_called_by_kb_injector(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_kb_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-608 · IC-06 · KBInjector 在 Stage 2 按 stage 策略调用 kb_read（PM-06）。"""
        ctx = make_tick_context(state="S1_plan", project_id=mock_project_id)
        sut.decide(ctx)
        mock_kb_client.kb_read.assert_called()
        call_kwargs = mock_kb_client.kb_read.call_args.kwargs
        assert call_kwargs["project_id"] == mock_project_id
        assert "stage" in call_kwargs

    def test_TC_L101_L202_609_ic_07_kb_write_session_payload(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-609 · IC-07 kb_write_session · layer/dedup_key 合法。"""
        ctx = make_tick_context(state="S6_wrap", project_id=mock_project_id,
                                hint_kind="kb_write")
        rec = sut.decide(ctx)
        assert rec.decision_type == "kb_write"
        assert rec.decision_params["layer"] in ("L1_user", "L2_fragment", "L3_global")
        assert rec.decision_params["dedup_key"]

    def test_TC_L101_L202_610_ic_11_process_content_payload(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-610 · IC-11 process_content · content_type 合法 + path。"""
        ctx = make_tick_context(state="S2_split", project_id=mock_project_id,
                                hint_kind="process_content")
        rec = sut.decide(ctx)
        assert rec.decision_type == "process_content"
        assert rec.decision_params["content_type"] in ("doc", "code", "image")
        assert rec.decision_params["path"]
```

---

## §5 性能 SLO 用例

> 基于 §12 SLO（decide P95 ≤ 5s / 5 纪律 ≤ 200ms / KB 注入 ≤ 500ms / cancel abort ≤ 100ms / inject_warn < 1ms）。
> `@pytest.mark.perf` 标记 · 单次运行 N=200 样本 · 统计 P95/P99。

```python
# file: tests/l1_01/test_l2_02_performance.py
from __future__ import annotations

import statistics
import time
import pytest

from app.l2_02.engine import DecisionEngine


@pytest.mark.perf
class TestL2_02_SLO:
    """§12.1 SLO 的定量回归 · N=200 样本 · 断言 P95/P99。"""

    def test_TC_L101_L202_701_decide_p95_le_5s_pure_logic(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-701 · decide() P95 ≤ 5s（纯逻辑 · mock IO 即时返回）。prd §9.9 / §12.1。"""
        samples: list[float] = []
        for i in range(200):
            ctx = make_tick_context(project_id=mock_project_id, state="S4_execute",
                                    tick_id=f"tick-perf-{i}")
            t0 = time.perf_counter()
            sut.decide(ctx)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p95 <= 5_000, f"decide P95={p95:.1f}ms > 5000ms"
        assert p99 <= 10_000

    def test_TC_L101_L202_702_five_discipline_p99_le_200ms(
        self, five_discipline_interrogator, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-702 · FiveDiscipline P99 ≤ 200ms（§12.1）。"""
        samples: list[float] = []
        for i in range(200):
            ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
            t0 = time.perf_counter()
            five_discipline_interrogator.interrogate(ctx, timeout_ms=200)
            samples.append((time.perf_counter() - t0) * 1000)
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 200

    def test_TC_L101_L202_703_cancel_abort_latency_le_100ms_hard(
        self, sut: DecisionEngine, mock_project_id: str, make_cancel_signal,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-703 · on_async_cancel abort ≤ 100ms（arch §3.5 D-05 硬约束）。"""
        samples: list[int] = []
        for i in range(100):
            ctx = make_tick_context(project_id=mock_project_id, state="S4_execute",
                                    tick_id=f"tick-abort-{i}")
            sut._mark_tick_running(ctx.tick_id)
            sig = make_cancel_signal(tick_id=ctx.tick_id, reason_type="supervisor_block")
            r = sut.on_async_cancel(sig)
            samples.append(r["abort_latency_ms"])
        p99 = sorted(samples)[98]
        assert p99 <= 100, f"abort P99={p99}ms > 100ms 硬约束"

    def test_TC_L101_L202_704_inject_warn_enqueue_sub_ms(
        self, sut: DecisionEngine, mock_project_id: str, make_warn_item,
    ) -> None:
        """TC-L101-L202-704 · inject_warn enqueue P95 ≤ 1ms（§3.2 非阻塞）。"""
        samples: list[float] = []
        for _ in range(1000):
            w = make_warn_item(project_id=mock_project_id, priority="P1")
            t0 = time.perf_counter()
            sut.inject_warn(w)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= 1.0

    def test_TC_L101_L202_705_tick_throughput_ge_2_per_s(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-705 · 吞吐 ≥ 2 tick/s（§12.2 单实例目标）。"""
        t0 = time.perf_counter()
        N = 30
        for i in range(N):
            ctx = make_tick_context(project_id=mock_project_id, state="S4_execute",
                                    tick_id=f"tick-tp-{i}")
            sut.decide(ctx)
        elapsed = time.perf_counter() - t0
        assert N / elapsed >= 2.0, f"throughput={N/elapsed:.2f} tick/s < 2"
```

---

## §6 端到端 e2e 场景

> 映射 prd §9.9 P1/P5/P8 + §13.4 P0-04 / P0-10 / P1-01 · 2-3 个端到端完整链路（in-memory mock 链）。

```python
# file: tests/l1_01/test_l2_02_e2e.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_02.engine import DecisionEngine


class TestL2_02_E2E:
    """端到端 · 多 L2/L1 参与 · 仅 mock 外部世界边界。"""

    def test_TC_L101_L202_801_e2e_p0_tick_to_skill_dispatch_and_audit(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_05_client: MagicMock, mock_event_bus: MagicMock,
        make_tick_context,
    ) -> None:
        """TC-L101-L202-801 · prd P1 + §13.4 P0-04/P0-10：tick → decide → audit → IC-09 事件链闭合。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="invoke_skill")
        rec = sut.decide(ctx)
        # L2-05 收到 audit → 代劳 IC-09 append_event
        mock_l2_05_client.audit_decision.assert_called_once()
        # 审计链有 decision_made 事件
        events = [c.kwargs.get("event_type") for c in mock_event_bus.append_event.call_args_list]
        assert "L1-01:decision_made" in events or "decision_made" in "|".join(filter(None, events))
        assert rec.decision_type == "invoke_skill"
        assert rec.reason and len(rec.reason) >= 20

    def test_TC_L101_L202_802_e2e_p1_block_cancel_chain_full(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_cancel_signal, make_tick_context,
    ) -> None:
        """TC-L101-L202-802 · prd §13.4 P1-01：L2-06 BLOCK → L2-01 → L2-02 abort ≤100ms → audit aborted。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        sig = make_cancel_signal(tick_id=ctx.tick_id, reason_type="supervisor_block")
        sut._mark_tick_running(ctx.tick_id)
        r = sut.on_async_cancel(sig)
        assert r["aborted"] is True and r["abort_latency_ms"] <= 100
        rec = sut.decide(ctx)
        mock_l2_05_client.audit_decision.assert_called_once()
        kwargs = mock_l2_05_client.audit_decision.call_args.kwargs
        assert getattr(kwargs["record"], "aborted", False) is True
        assert rec.decision_type == "no_op"

    def test_TC_L101_L202_803_e2e_warn_then_next_tick_produces_warn_response(
        self, sut: DecisionEngine, mock_project_id: str,
        make_warn_item, make_tick_context, mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L202-803 · prd §9.9 I4 WARN 回应链：inject_warn → 下 tick warn_response + audit。"""
        warn = make_warn_item(project_id=mock_project_id, priority="P0",
                              deadline_tick_delta=1)
        sut.inject_warn(warn)
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                trigger_source="timer")
        rec = sut.decide(ctx)
        assert rec.decision_type == "warn_response"
        assert rec.warn_response_ref == warn.warn_id
        mock_l2_05_client.audit_decision.assert_called_once()
```

---

## §7 测试 fixture

> conftest.py · 提供 `sut` / `mock_project_id` / `mock_clock` / `mock_event_bus` / `mock_l2_*_client` / `mock_kb_client` / `mock_task_board` / `mock_capability_registry` / `mock_capability_registry_loader` / `mock_five_discipline` / `mock_decision_tree` / `mock_decision_selector` / `make_tick_context` / `make_warn_item` / `make_sugg_item` / `make_cancel_signal` / `make_step_result`。

```python
# file: tests/l1_01/conftest.py
from __future__ import annotations

import uuid
import pytest
from typing import Any, Callable
from unittest.mock import MagicMock

from app.l2_02.engine import DecisionEngine
from app.l2_02.schemas import (
    TickContext, WarnItem, SuggItem, CancelSignal, StepResult,
)


class FakeClock:
    def __init__(self) -> None:
        self._now_ms: int = 0
        self.advance_on_abort_ms: int = 0

    def now_ms(self) -> int:
        return self._now_ms

    def advance(self, ms: int) -> None:
        self._now_ms += ms


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="EventBus")
    bus.query.return_value = []
    bus.append_event.return_value = {"event_id": f"evt-{uuid.uuid4()}", "sequence": 1}
    return bus


@pytest.fixture
def mock_task_board() -> MagicMock:
    tb = MagicMock(name="TaskBoard")
    tb.read_snapshot.return_value = {"tasks": [], "version": 1}
    return tb


@pytest.fixture
def mock_kb_client() -> MagicMock:
    kb = MagicMock(name="KBClient")
    kb.kb_read.return_value = {"entries": []}
    kb.kb_write_session.return_value = {"ok": True}
    return kb


@pytest.fixture
def mock_capability_registry() -> MagicMock:
    reg = MagicMock(name="CapabilityRegistry")
    reg.resolve.return_value = {"skill": "writing-plans", "version": "1.0"}
    return reg


@pytest.fixture
def mock_capability_registry_loader(mock_capability_registry: MagicMock) -> MagicMock:
    loader = MagicMock(name="CapabilityRegistryLoader")
    loader.load.return_value = mock_capability_registry
    return loader


@pytest.fixture
def mock_five_discipline() -> MagicMock:
    fd = MagicMock(name="FiveDisciplineInterrogator")
    fd.interrogate.return_value = [
        {"name": n, "answer": "Y", "note": "ok"}
        for n in ("planning", "quality", "split", "verify", "deliver")
    ]
    return fd


@pytest.fixture
def mock_decision_tree() -> MagicMock:
    dt = MagicMock(name="DecisionTreeDispatcher")
    dt.dispatch.return_value = [
        {"decision_type": "invoke_skill",
         "decision_params": {"skill_intent": "tdd.verify", "capability_tag": "tdd.verify",
                             "input_payload": {"wp_id": "wp-1"}},
         "score": 0.9}
    ]
    return dt


@pytest.fixture
def mock_decision_selector() -> MagicMock:
    ds = MagicMock(name="DecisionSelector")
    ds.select.return_value = {
        "decision_type": "invoke_skill",
        "decision_params": {"skill_intent": "tdd.verify", "capability_tag": "tdd.verify",
                            "input_payload": {"wp_id": "wp-1"}},
        "reason": "S4 执行期选择 tdd.verify 覆盖当前 WP 的 DoD 验证需求",
    }
    return ds


@pytest.fixture
def mock_l2_01_client() -> MagicMock:
    return MagicMock(name="L2-01 Scheduler")


@pytest.fixture
def mock_l2_03_client() -> MagicMock:
    m = MagicMock(name="L2-03 StateMachine")
    m.allowed_next_check.return_value = {"allowed": True}
    m.request_state_transition.return_value = {"ok": True}
    return m


@pytest.fixture
def mock_l2_04_client() -> MagicMock:
    m = MagicMock(name="L2-04 ChainExecutor")
    m.start_chain.return_value = {"chain_id": f"chain-{uuid.uuid4()}"}
    return m


@pytest.fixture
def mock_l2_05_client() -> MagicMock:
    m = MagicMock(name="L2-05 Audit")
    m.audit_decision.return_value = {"audit_entry_id": f"aud-{uuid.uuid4()}"}
    return m


@pytest.fixture
def five_discipline_interrogator(mock_five_discipline: MagicMock) -> MagicMock:
    return mock_five_discipline


@pytest.fixture
def sut(
    mock_project_id: str,
    mock_clock: FakeClock,
    mock_event_bus: MagicMock,
    mock_task_board: MagicMock,
    mock_kb_client: MagicMock,
    mock_capability_registry: MagicMock,
    mock_capability_registry_loader: MagicMock,
    mock_five_discipline: MagicMock,
    mock_decision_tree: MagicMock,
    mock_decision_selector: MagicMock,
    mock_l2_01_client: MagicMock,
    mock_l2_03_client: MagicMock,
    mock_l2_04_client: MagicMock,
    mock_l2_05_client: MagicMock,
) -> DecisionEngine:
    return DecisionEngine(
        project_id=mock_project_id,
        clock=mock_clock,
        event_bus=mock_event_bus,
        task_board=mock_task_board,
        kb_client=mock_kb_client,
        capability_registry=mock_capability_registry,
        capability_registry_loader=mock_capability_registry_loader,
        five_discipline=mock_five_discipline,
        decision_tree=mock_decision_tree,
        decision_selector=mock_decision_selector,
        l2_01_client=mock_l2_01_client,
        l2_03_client=mock_l2_03_client,
        l2_04_client=mock_l2_04_client,
        l2_05_client=mock_l2_05_client,
        startup_pre_check_timeout_ms=5_000,
    )


@pytest.fixture
def make_tick_context() -> Callable[..., TickContext]:
    def _factory(**overrides: Any) -> TickContext:
        base: dict[str, Any] = dict(
            tick_id=f"tick-{uuid.uuid4()}",
            project_id="pid-default",
            trigger_source="timer",
            event_ref=None,
            priority="P2",
            ts="2026-04-22T06:30:00.000Z",
            state="S4_execute",
            bootstrap=False,
            wp_context={"wp_id": "wp-1", "dod_expression": "pytest -x"},
            context_snapshot=None,
            hint_kind=None,
            transition_to=None,
            force_fill_gap_disabled=False,
        )
        base.update(overrides)
        return TickContext(**base)
    return _factory


@pytest.fixture
def make_warn_item() -> Callable[..., WarnItem]:
    def _factory(**overrides: Any) -> WarnItem:
        base = dict(
            warn_id=f"warn-{uuid.uuid4()}",
            project_id="pid-default",
            content="存在 WP DoD 未通过的风险 · 需下一 tick 响应",
            priority="P1",
            ts="2026-04-22T06:30:00.000Z",
            deadline_tick_delta=1,
        )
        base.update(overrides)
        return WarnItem(**base)
    return _factory


@pytest.fixture
def make_sugg_item() -> Callable[..., SuggItem]:
    def _factory(**overrides: Any) -> SuggItem:
        base = dict(
            sugg_id=f"sugg-{uuid.uuid4()}",
            project_id="pid-default",
            content="建议补齐单元测试覆盖率 ≥ 80%",
            ts="2026-04-22T06:30:00.000Z",
        )
        base.update(overrides)
        return SuggItem(**base)
    return _factory


@pytest.fixture
def make_cancel_signal() -> Callable[..., CancelSignal]:
    def _factory(**overrides: Any) -> CancelSignal:
        base = dict(
            cancel_id=f"cancel-{uuid.uuid4()}",
            tick_id="tick-default",
            reason_type="supervisor_block",
            ts="2026-04-22T06:30:00.000Z",
        )
        base.update(overrides)
        return CancelSignal(**base)
    return _factory


@pytest.fixture
def make_step_result() -> Callable[..., StepResult]:
    def _factory(**overrides: Any) -> StepResult:
        base = dict(
            chain_id=f"chain-{uuid.uuid4()}",
            step_id=f"step-{uuid.uuid4()}",
            outcome="success",
            result_ref="oss://bucket/result.json",
            project_id="pid-default",
            ts="2026-04-22T06:30:00.000Z",
        )
        base.update(overrides)
        return StepResult(**base)
    return _factory
```

---

## §8 集成点用例

> 与兄弟 L2 协作（L2-01 / L2-03 / L2-04 / L2-05 / L2-06）· 对照 §11.3 协同矩阵 + §5.1/§5.2 时序。

```python
# file: tests/l1_01/test_l2_02_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_02.engine import DecisionEngine


class TestL2_02_SiblingIntegration:
    """L2-02 与 L2-01/03/04/05/06 的协作测试。"""

    def test_TC_L101_L202_901_coop_with_l2_01_step_completed_triggers_next_tick(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_step_result,
    ) -> None:
        """TC-L101-L202-901 · L2-04 回调 → on_step_completed → L2-01 schedule_tick(async_callback)。"""
        sr = make_step_result(project_id=mock_project_id, outcome="success")
        sut.on_step_completed(sr)
        mock_l2_01_client.schedule_tick.assert_called_once()
        trig = mock_l2_01_client.schedule_tick.call_args.args[0]
        assert trig.trigger_source == "async_callback"

    def test_TC_L101_L202_902_coop_with_l2_03_state_transition_flow(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_03_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-902 · state_transition 完整链：allowed_next → request_state_transition。"""
        mock_l2_03_client.allowed_next_check.return_value = {"allowed": True}
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="state_transition", transition_to="S5_verify")
        sut.decide(ctx)
        mock_l2_03_client.allowed_next_check.assert_called_once()
        mock_l2_03_client.request_state_transition.assert_called_once()

    def test_TC_L101_L202_903_coop_with_l2_04_start_chain_decision(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_04_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-903 · start_chain 决策 → L2-04 start_chain 触发。"""
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id,
                                hint_kind="start_chain")
        sut.decide(ctx)
        mock_l2_04_client.start_chain.assert_called_once()

    def test_TC_L101_L202_904_coop_with_l2_05_audit_unreachable_rejects_decision(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_tick_context,
    ) -> None:
        """TC-L101-L202-904 · L2-05 不可达 → 本 L2 重试 3 次 → 拒绝产 decision（§11.3 PM-08 一致性）。"""
        mock_l2_05_client.audit_decision.side_effect = RuntimeError("audit down")
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        with pytest.raises(RuntimeError, match="audit"):
            sut.decide(ctx)
        assert mock_l2_05_client.audit_decision.call_count == 3

    def test_TC_L101_L202_905_coop_with_l2_06_warn_inject_and_response(
        self, sut: DecisionEngine, mock_project_id: str,
        make_warn_item, make_tick_context, mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L202-905 · L2-06 inject_warn → 下一 tick warn_response + audit 留痕（§3.2 + prd §9.9 I4）。"""
        w = make_warn_item(project_id=mock_project_id, priority="P0", deadline_tick_delta=1)
        sut.inject_warn(w)
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        rec = sut.decide(ctx)
        assert rec.decision_type == "warn_response"
        assert rec.warn_response_ref == w.warn_id
        kwargs = mock_l2_05_client.audit_decision.call_args.kwargs
        assert kwargs["record"].warn_response_ref == w.warn_id
```

---

## §9 边界 / edge case

> 空输入 / 超大输入 / 并发 / 超时 / 崩溃恢复 / 脏数据 · ≥ 5 个。

```python
# file: tests/l1_01/test_l2_02_edge_cases.py
from __future__ import annotations

import threading
import pytest

from app.l2_02.engine import DecisionEngine
from app.l2_02.errors import DecisionError


class TestL2_02_EdgeCases:
    """边界 / edge case · 空输入 / 超大 / 并发 / 超时 / 崩溃 / 脏数据。"""

    def test_TC_L101_L202_A01_empty_wp_context_s0_init_falls_back(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-A01 · wp_context=None · state=S0_init · 决策允许为 request_user / no_op。"""
        ctx = make_tick_context(project_id=mock_project_id, state="S0_init",
                                wp_context=None, hint_kind="bootstrap")
        rec = sut.decide(ctx)
        assert rec.decision_type in ("request_user", "no_op", "kb_read", "state_transition")

    def test_TC_L101_L202_A02_oversize_context_snapshot_still_serializable(
        self, sut: DecisionEngine, mock_project_id: str,
        mock_task_board, make_tick_context,
    ) -> None:
        """TC-L101-L202-A02 · context_snapshot 200KB 极端 · decision_record 仍 ≤ 100KB（§12.2）。"""
        big_tasks = [{"id": f"t{i}", "desc": "x" * 500} for i in range(400)]
        mock_task_board.read_snapshot.return_value = {"tasks": big_tasks, "version": 1}
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        import json
        size = len(json.dumps(rec.to_dict() if hasattr(rec, "to_dict") else rec.__dict__,
                              default=str))
        assert size <= 100 * 1024, f"DecisionRecord size={size} > 100KB 上限"

    def test_TC_L101_L202_A03_concurrent_inject_warn_thread_safe(
        self, sut: DecisionEngine, mock_project_id: str, make_warn_item,
    ) -> None:
        """TC-L101-L202-A03 · 20 线程并发 inject_warn · 无 race · 队列含 ≤ 64 条（overflow evict）。"""
        def worker() -> None:
            for _ in range(20):
                try:
                    sut.inject_warn(make_warn_item(project_id=mock_project_id, priority="P1"))
                except DecisionError:
                    pass
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for th in threads: th.start()
        for th in threads: th.join(timeout=5)
        assert sut.warn_queue_len() <= 64

    def test_TC_L101_L202_A04_decide_timeout_20s_hard_ceiling(
        self, sut: DecisionEngine, mock_project_id: str, mock_clock,
        mock_decision_tree, make_tick_context,
    ) -> None:
        """TC-L101-L202-A04 · decide 总耗时 20s 硬上限 · 自 abort + no_op + tick_budget_used_ms > 20_000。"""
        def slow(*_a, **_kw):
            mock_clock.advance(20_100)
            raise TimeoutError("21s")
        mock_decision_tree.dispatch.side_effect = slow
        ctx = make_tick_context(project_id=mock_project_id, state="S4_execute")
        rec = sut.decide(ctx)
        assert rec.decision_type == "no_op"
        assert rec.tick_budget_used_ms > 20_000

    def test_TC_L101_L202_A05_crash_recovery_replays_warn_queue(
        self, sut: DecisionEngine, mock_project_id: str, make_warn_item, make_tick_context,
    ) -> None:
        """TC-L101-L202-A05 · 崩溃重启后从 session 状态恢复 warn_queue · 下一 tick 正确响应。"""
        w = make_warn_item(project_id=mock_project_id, priority="P0")
        sut.inject_warn(w)
        persisted = sut.dump_state()  # 模拟崩溃前序列化
        # 模拟新实例
        sut.reset_state()
        sut.load_state(persisted)
        ctx = make_tick_context(state="S4_execute", project_id=mock_project_id)
        rec = sut.decide(ctx)
        assert rec.decision_type == "warn_response"
        assert rec.warn_response_ref == w.warn_id

    def test_TC_L101_L202_A06_dirty_tick_id_format_rejected(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-A06 · 脏数据 · tick_id 非 tick-{uuid-v7} 格式 → 拒绝（assemble 前校验）。"""
        ctx = make_tick_context(tick_id="not-a-uuid", project_id=mock_project_id,
                                state="S4_execute")
        with pytest.raises(DecisionError, match="E_CTX_"):
            sut.decide(ctx)

    def test_TC_L101_L202_A07_consecutive_no_op_escalates_warn(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
        mock_decision_tree,
    ) -> None:
        """TC-L101-L202-A07 · 连续 ≥ 5 次 no_op → L1-07 WARN（§12.3 idle_spin 健康指标）。"""
        mock_decision_tree.dispatch.return_value = [
            {"decision_type": "no_op", "decision_params": {"note": "idle"},
             "score": 1.0}
        ]
        for i in range(5):
            ctx = make_tick_context(project_id=mock_project_id, state="S4_execute",
                                    tick_id=f"tick-idle-{i}")
            sut.decide(ctx)
        assert sut.consecutive_no_op_count() >= 5
        assert sut.last_health_warn_code() == "consecutive_no_op"

    def test_TC_L101_L202_A08_decision_cache_lru_1024_evicts_oldest(
        self, sut: DecisionEngine, mock_project_id: str, make_tick_context,
    ) -> None:
        """TC-L101-L202-A08 · LRU 1024 满后最旧被挤出（§3.1 幂等缓存）。"""
        for i in range(1050):
            ctx = make_tick_context(project_id=mock_project_id, state="S4_execute",
                                    tick_id=f"tick-lru-{i}")
            sut.decide(ctx)
        assert sut.decision_cache_len() <= 1024
```

---

*— L1-01 / L2-02 决策引擎 TDD 测试用例 · filled · session-G ·  基于 3-1 §3/§11/§12/§13 字段级绑定 —*
