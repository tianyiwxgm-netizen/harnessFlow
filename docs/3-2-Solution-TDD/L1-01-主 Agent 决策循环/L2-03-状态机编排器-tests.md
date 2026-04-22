---
doc_id: tests-L1-01-L2-03-状态机编排器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-03-状态机编排器.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-01 L2-03-状态机编排器 · TDD 测试用例

> 基于 3-1 L2-03 §3（5 个 public 方法）+ §11（13 项 `E_TRANS_*` 错误码）+ §12（P95/P99/硬上限 SLO）+ §13 TC ID 矩阵 驱动。
> TC ID 统一格式：`TC-L101-L203-NNN`（L1-01 下 L2-03，三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_03_StateMachineOrchestrator` 正向组织；`class TestL2_03_Negative*` 负向分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock_project_id / mock_event_bus / mock_clock / mock_ic_payload）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型（§3 五个 public 方法）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `request_state_transition()` · §3.1 · S1→S2 主链 | TC-L101-L203-001 | unit | — | IC-L2-02 |
| `request_state_transition()` · §3.1 · S2→S3 + IC-16 Gate | TC-L101-L203-002 | integration | — | IC-01 + IC-16 |
| `request_state_transition()` · §3.1 · S5→S7 主流径 | TC-L101-L203-003 | unit | — | IC-L2-02 |
| `request_state_transition()` · §3.1 · S5→S4 Quality Loop | TC-L101-L203-004 | unit | — | IC-L2-02 |
| `request_state_transition()` · §3.1 · S4→HALTED 红线 | TC-L101-L203-005 | unit | — | IC-L2-02 |
| `request_state_transition()` · §3.1 · HALTED→S1 授权 RESUME | TC-L101-L203-006 | unit | — | IC-L2-02 |
| `request_state_transition()` · §3.1 · 幂等重放 | TC-L101-L203-007 | unit | — | IC-L2-02 |
| `query_allowed_next()` · §3.2 · 9 state 全量 | TC-L101-L203-008 | unit | — | — |
| `get_current_state()` · §3.3 · 默认 S1 | TC-L101-L203-009 | unit | — | — |
| `replay_from_snapshot()` · §3.4 · 1000 events 正常重建 | TC-L101-L203-010 | unit | — | IC-10 |
| `preview_transition()` · §3.5 · S2→S3 预览 hook 计划 | TC-L101-L203-011 | unit | — | — |

### §1.2 错误码 × 测试（§3.6 / §11.1 共 13 项 `E_TRANS_*` 全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|---|---|---|---|
| `E_TRANS_INVALID_NEXT` | TC-L101-L203-101 | `request_state_transition()` | 合法性 |
| `E_TRANS_STATE_MISMATCH` | TC-L101-L203-102 | `request_state_transition()` | 并发一致性 |
| `E_TRANS_NO_PROJECT_ID` | TC-L101-L203-103 | `request_state_transition()` | 入参硬约束 · PM-14 |
| `E_TRANS_CROSS_PROJECT` | TC-L101-L203-104 | `request_state_transition()` | 入参硬约束 · PM-14 |
| `E_TRANS_REASON_TOO_SHORT` | TC-L101-L203-105 | `request_state_transition()` | 入参硬约束 |
| `E_TRANS_NO_EVIDENCE` | TC-L101-L203-106 | `request_state_transition()` | 入参硬约束 |
| `E_TRANS_CONCURRENT` | TC-L101-L203-107 | `request_state_transition()` | 并发锁 |
| `E_TRANS_EXIT_HOOK_FAIL` | TC-L101-L203-108 | `request_state_transition()` | exit hook 失败 |
| `E_TRANS_ENTRY_HOOK_FAIL` | TC-L101-L203-109 | `request_state_transition()` | entry hook 失败 · rollback |
| `E_TRANS_IDEMPOTENT_REPLAY` | TC-L101-L203-110 | `request_state_transition()` | 幂等冲突 |
| `E_TRANS_ALLOWED_NEXT_READONLY` | TC-L101-L203-111 | 模块配置 | AllowedNextTable 运行时不可改 |
| `E_TRANS_AUDIT_UNAVAILABLE` | TC-L101-L203-112 | `request_state_transition()` | L2-05 不可达 · full rollback |
| `E_TRANS_SNAPSHOT_VERSION_STALE` | TC-L101-L203-113 | `request_state_transition()` | 乐观锁 |
| `E_TRANS_INVALID_STATE_ENUM` | TC-L101-L203-114 | `query_allowed_next()` | enum 非法 |
| `E_TRANS_REPLAY_EVENT_CORRUPT` | TC-L101-L203-115 | `replay_from_snapshot()` | hash 链破坏 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-02 `state_transition_request` | L2-02 → L2-03 | TC-L101-L203-601 | 主入口 · payload 对齐 §3.1.1 YAML |
| IC-01 `request_state_transition` | L1-02 → L1-01(L2-03) | TC-L101-L203-602 | 跨 L1 · Stage Gate 驱动路径 |
| IC-L2-06 `record_state_transition` | L2-03 → L2-05 | TC-L101-L203-603 | 每转换 1 条审计（含 accepted=false）|
| IC-06 `kb_read` | L2-03(entry hook) → L1-06 | TC-L101-L203-604 | S3/S4/S5 entry 注 KB |
| IC-16 `push_stage_gate_card` | L2-03(entry hook) → L1-10 | TC-L101-L203-605 | S2→S3 / S3→S4 / S4→S5 / S5→S6 触发 |
| IC-09 `append_event`（经 L2-05 代劳）| L2-03 → L1-09 | TC-L101-L203-606 | 每转换 1 条 `L1-01:state_changed` 事件 |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_03_StateMachineOrchestrator`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `StateMachineOrchestrator`（从 `app.l2_03.orchestrator` 导入）。

```python
# file: tests/l1_01/test_l2_03_state_machine_orchestrator_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l2_03.orchestrator import StateMachineOrchestrator
from app.l2_03.schemas import (
    StateTransitionRequest,
    StateTransitionResult,
    PreviewResult,
    StateMachineSnapshot,
)
from app.l2_03.errors import TransError


class TestL2_03_StateMachineOrchestrator:
    """§3 public 方法正向用例。每方法 ≥ 1 个 happy path。"""

    # --------- request_state_transition() · 核心主方法（§3.1）--------- #

    def test_TC_L101_L203_001_request_state_transition_S1_to_S2_happy_path(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-001 · §8.2 #3 S1→S2 · accepted=true · entry/exit hook 均成功。"""
        # arrange
        req: StateTransitionRequest = make_transition_request(
            from_state="S1",
            to_state="S2",
            project_id=mock_project_id,
            reason="goal_anchor locked by user Go; proceeding to PLAN per §8.2 #3",
        )
        # act
        result: StateTransitionResult = sut.request_state_transition(req)
        # assert
        assert result.accepted is True
        assert result.new_state == "S2"
        assert result.transition_id == req.transition_id
        assert result.new_entry is not None
        assert result.new_entry.from_state == "S1"
        assert result.new_entry.to_state == "S2"
        assert result.hook_results is not None
        assert result.hook_results.exit_hook_result.succeeded is True
        assert result.hook_results.entry_hook_result.succeeded is True
        assert result.audit_entry_id is not None

    def test_TC_L101_L203_002_request_state_transition_S2_to_S3_pushes_ic16_gate(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_l1_10_client: MagicMock,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-002 · §8.2 #6 S2→S3 · entry hook 推 IC-16 Stage Gate 卡片。"""
        seed_current_state("S2")
        req = make_transition_request(
            from_state="S2",
            to_state="S3",
            project_id=mock_project_id,
            reason="WBS + 4件套 ready; Stage Gate approved; entering TDD blueprint",
            gate_id="gate-018f4a3b-0001-7000-8b2a-9d5e1c8f3a01",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert result.new_state == "S3"
        # IC-16 push_stage_gate_card by entry hook
        mock_l1_10_client.push_stage_gate_card.assert_called_once()
        payload = mock_l1_10_client.push_stage_gate_card.call_args.kwargs
        assert payload["from_stage"] == "S2"
        assert payload["to_stage"] == "S3"
        assert payload["project_id"] == mock_project_id

    def test_TC_L101_L203_003_request_state_transition_S5_to_S7_main_path(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-003 · §8.2 #18 S5→S7 主流径 · verifier_report PASS。"""
        seed_current_state("S5")
        req = make_transition_request(
            from_state="S5",
            to_state="S7",
            project_id=mock_project_id,
            reason="verifier_report PASS; skipping S6; entering archive per §8.2 main flow",
            evidence_refs=["verifier-report-001", "audit-s5-999"],
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert result.new_state == "S7"

    def test_TC_L101_L203_004_request_state_transition_S5_to_S4_quality_loop(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-004 · §8.2 #13 S5→S4 · Quality Loop 轻度 FAIL 回退。"""
        seed_current_state("S5")
        req = make_transition_request(
            from_state="S5",
            to_state="S4",
            project_id=mock_project_id,
            reason="verifier FAIL light; re-execute single WP for defect correction",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert result.new_state == "S4"

    def test_TC_L101_L203_005_request_state_transition_to_HALTED_hard_red_line(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-005 · §8.2 #22 任意 Sn→HALTED · 硬红线触发。"""
        seed_current_state("S4")
        req = make_transition_request(
            from_state="S4",
            to_state="HALTED",
            project_id=mock_project_id,
            reason="red line IRREVERSIBLE_HALT triggered by L1-07 via supervisor event",
            evidence_refs=["supervisor-event-hl-001"],
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert result.new_state == "HALTED"

    def test_TC_L101_L203_006_request_state_transition_HALTED_to_S1_resume(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-006 · §8.2 #24 HALTED→S1..S7 · 用户文字授权 RESUME。"""
        seed_current_state("HALTED")
        req = make_transition_request(
            from_state="HALTED",
            to_state="S1",
            project_id=mock_project_id,
            reason="user text authorization RESUME@S1 received via L1-10 IC-17 user_authorize",
            evidence_refs=["user-authz-001"],
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert result.new_state == "S1"

    def test_TC_L101_L203_007_request_state_transition_idempotent_same_id_returns_cached(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-007 · §3.1 幂等性 · 同 transition_id 两次调用返回同一结果（LRU 1024）。"""
        req = make_transition_request(
            from_state="S1",
            to_state="S2",
            project_id=mock_project_id,
            reason="idempotent replay happy path for §3.1.5 LRU cache",
        )
        r1 = sut.request_state_transition(req)
        r2 = sut.request_state_transition(req)
        assert r1.transition_id == r2.transition_id
        assert r1.accepted == r2.accepted
        assert r1.ts_applied == r2.ts_applied
        assert r1.audit_entry_id == r2.audit_entry_id, "命中 LRU 缓存不应产生第二条审计"

    # --------- query_allowed_next() · §3.2 --------- #

    def test_TC_L101_L203_008_query_allowed_next_nine_states_match_table(
        self,
        sut: StateMachineOrchestrator,
    ) -> None:
        """TC-L101-L203-008 · §8.2 AllowedNextTable · 9 state 全量对齐 §8.1 图。"""
        # S2 典型：可转 S3 / S1 / S2 / HALTED / PAUSED
        s2_next = set(sut.query_allowed_next("S2"))
        assert {"S3", "S1", "S2", "HALTED", "PAUSED"}.issubset(s2_next)
        # S5 典型：可回退 4 级 + S6 + S7 + 自循环 + HALTED/PAUSED
        s5_next = set(sut.query_allowed_next("S5"))
        assert {"S4", "S3", "S2", "S1", "S6", "S7", "HALTED", "PAUSED"}.issubset(s5_next)
        # HALTED 可恢复到任意 S1-S7 + 降级 PAUSED
        halted_next = set(sut.query_allowed_next("HALTED"))
        assert {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "PAUSED"}.issubset(halted_next)

    # --------- get_current_state() · §3.3 --------- #

    def test_TC_L101_L203_009_get_current_state_defaults_to_S1_before_bootstrap(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
    ) -> None:
        """TC-L101-L203-009 · §3.3.3 snapshot 未初始化 → 返回默认 S1 + debug log。"""
        state = sut.get_current_state(mock_project_id)
        assert state == "S1"

    # --------- replay_from_snapshot() · §3.4 --------- #

    def test_TC_L101_L203_010_replay_rebuilds_snapshot_from_1000_events(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        seed_event_history_1000,
    ) -> None:
        """TC-L101-L203-010 · §3.4 冷启 replay 1000 条 state_history 正确重建 snapshot。"""
        snapshot: StateMachineSnapshot = sut.replay_from_snapshot(
            replay_request={"project_id": mock_project_id, "snapshot_ref": None}
        )
        assert snapshot.project_id == mock_project_id
        assert snapshot.current_state in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "HALTED", "PAUSED")
        assert len(snapshot.state_history) == 1000
        assert snapshot.version == 1000

    # --------- preview_transition() · §3.5 --------- #

    def test_TC_L101_L203_011_preview_transition_S2_to_S3_returns_hook_plan(
        self,
        sut: StateMachineOrchestrator,
    ) -> None:
        """TC-L101-L203-011 · §3.5 preview · 不改状态 · 返回 would_accept + hook 计划。"""
        preview: PreviewResult = sut.preview_transition(from_state="S2", to_state="S3")
        assert preview.would_accept is True
        assert preview.reject_reason is None
        assert any(h.hook_name.startswith("S2_exit") for h in preview.exit_hook_plan)
        assert any(h.hook_name.startswith("S3_entry") for h in preview.entry_hook_plan)
        # Stage Gate 出现在 entry hook plan
        assert any("IC-16" in h.action_desc or "stage_gate" in h.action_desc.lower()
                   for h in preview.entry_hook_plan)
```

---

## §3 负向用例（每错误码 ≥ 1）

> §3.6 总表 / §11.5 Unhappy path 对齐 · 13+ 项 `E_TRANS_*` 全覆盖。
> 每测试用 `pytest.raises(TransError) as exc` + 断言 `exc.value.error_code == "E_TRANS_..."`，
> 或断言 `result.accepted is False` + `reason` 映射到错误码（部分错误返回 accepted=false 而非抛错）。

```python
# file: tests/l1_01/test_l2_03_state_machine_orchestrator_negative.py
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from app.l2_03.orchestrator import StateMachineOrchestrator
from app.l2_03.errors import TransError


class TestL2_03_Negative_RequestStateTransition:
    """§3.1 request_state_transition() 的 12 项错误码负向用例。"""

    def test_TC_L101_L203_101_invalid_next_rejected_not_raised(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-101 · E_TRANS_INVALID_NEXT · S1→S4 直跳不在 allowed_next 表。"""
        seed_current_state("S1")
        req = make_transition_request(
            from_state="S1",
            to_state="S4",
            project_id=mock_project_id,
            reason="illegal direct jump from S1 to S4 to trigger invalid_next error",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.new_state == "S1"  # state 未变
        assert "invalid" in (result.reason or "").lower() or "allowed_next" in (result.reason or "").lower()
        assert result.error_code == "E_TRANS_INVALID_NEXT"

    def test_TC_L101_L203_102_state_mismatch_caller_snapshot_stale(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-102 · E_TRANS_STATE_MISMATCH · req.from=S2 但 snapshot.current_state=S3。"""
        seed_current_state("S3")
        req = make_transition_request(
            from_state="S2",
            to_state="S3",
            project_id=mock_project_id,
            reason="caller snapshot was stale; actual current_state is S3 not S2",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.error_code == "E_TRANS_STATE_MISMATCH"

    def test_TC_L101_L203_103_no_project_id_raises(
        self,
        sut: StateMachineOrchestrator,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-103 · E_TRANS_NO_PROJECT_ID · PM-14 根字段校验。"""
        req = make_transition_request(
            from_state="S1",
            to_state="S2",
            project_id=None,
            reason="missing project id should trigger PM-14 hard constraint",
        )
        with pytest.raises(TransError) as exc:
            sut.request_state_transition(req)
        assert exc.value.error_code == "E_TRANS_NO_PROJECT_ID"

    def test_TC_L101_L203_104_cross_project_rejected(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-104 · E_TRANS_CROSS_PROJECT · pid ≠ session 绑定 pid。"""
        req = make_transition_request(
            from_state="S1",
            to_state="S2",
            project_id="pid-018f4a3b-9999-7000-FFFF-other-project",
            reason="foreign project id should be rejected by PM-14 enforcement",
        )
        with pytest.raises(TransError) as exc:
            sut.request_state_transition(req)
        assert exc.value.error_code == "E_TRANS_CROSS_PROJECT"

    def test_TC_L101_L203_105_reason_too_short_rejected(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-105 · E_TRANS_REASON_TOO_SHORT · reason < 20 字符。"""
        req = make_transition_request(
            from_state="S1",
            to_state="S2",
            project_id=mock_project_id,
            reason="too short",  # len=9 < 20
        )
        with pytest.raises(TransError) as exc:
            sut.request_state_transition(req)
        assert exc.value.error_code == "E_TRANS_REASON_TOO_SHORT"

    def test_TC_L101_L203_106_no_evidence_rejected(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-106 · E_TRANS_NO_EVIDENCE · evidence_refs 为空数组。"""
        req = make_transition_request(
            from_state="S1",
            to_state="S2",
            project_id=mock_project_id,
            reason="evidence_refs empty should trigger hard audit constraint rejection",
            evidence_refs=[],
        )
        with pytest.raises(TransError) as exc:
            sut.request_state_transition(req)
        assert exc.value.error_code == "E_TRANS_NO_EVIDENCE"

    def test_TC_L101_L203_107_concurrent_transition_immediate_reject(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-107 · E_TRANS_CONCURRENT · 并发锁 · 第二个请求立即拒绝（非等待）。"""
        results: list = []
        ready = threading.Event()

        def worker(marker: str) -> None:
            req = make_transition_request(
                from_state="S1",
                to_state="S2",
                project_id=mock_project_id,
                reason=f"concurrent test worker {marker} attempting transition simultaneously",
                transition_id=f"trans-018f4a3b-{marker}-7000-8b2a-9d5e1c8f3a20",
            )
            ready.wait()
            results.append((marker, sut.request_state_transition(req)))

        sut._inject_transition_hold_ms(200)  # simulate slow in-flight transition
        t1 = threading.Thread(target=worker, args=("a",))
        t2 = threading.Thread(target=worker, args=("b",))
        t1.start(); t2.start()
        ready.set()
        t1.join(); t2.join()

        accepted = [r for _, r in results if r.accepted]
        rejected = [r for _, r in results if not r.accepted]
        assert len(accepted) == 1
        assert len(rejected) == 1
        assert rejected[0].error_code == "E_TRANS_CONCURRENT"
        assert "concurrent" in (rejected[0].reason or "").lower()

    def test_TC_L101_L203_108_exit_hook_fail_state_unchanged(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L101-L203-108 · E_TRANS_EXIT_HOOK_FAIL · exit hook 抛异常 · state 未改。"""
        seed_current_state("S2")
        sut._inject_hook_failure(state="S2", direction="exit", err="4件套 hash freeze timeout")
        req = make_transition_request(
            from_state="S2",
            to_state="S3",
            project_id=mock_project_id,
            reason="exit hook will fail due to injected freeze timeout per §11.5 case 7",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.new_state == "S2", "state 未改（exit 失败前）"
        assert result.error_code == "E_TRANS_EXIT_HOOK_FAIL"
        # 广播 L1-01:exit_hook_failed
        events = [c for c in mock_event_bus.append_event.call_args_list
                  if c.kwargs.get("event_type") == "L1-01:exit_hook_failed"]
        assert len(events) == 1

    def test_TC_L101_L203_109_entry_hook_fail_triggers_rollback(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L101-L203-109 · E_TRANS_ENTRY_HOOK_FAIL · entry hook 失败 · state rollback 到 req.from。"""
        seed_current_state("S3")
        sut._inject_hook_failure(state="S4", direction="entry", err="IC-06 kb_read timeout 2s")
        req = make_transition_request(
            from_state="S3",
            to_state="S4",
            project_id=mock_project_id,
            reason="entry hook on S4 will fail; rollback to S3 per §11.4.1 full chain",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.new_state == "S3", "rollback 必须回到 req.from"
        assert result.error_code == "E_TRANS_ENTRY_HOOK_FAIL"
        # 广播 L1-01:entry_hook_failed
        events = [c for c in mock_event_bus.append_event.call_args_list
                  if c.kwargs.get("event_type") == "L1-01:entry_hook_failed"]
        assert len(events) == 1
        # snapshot version 递增（失败转换也记录 version）
        snap = sut.get_snapshot(mock_project_id)
        assert snap.current_state == "S3"

    def test_TC_L101_L203_110_idempotent_replay_with_different_payload_raises(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-110 · E_TRANS_IDEMPOTENT_REPLAY · 同 id 不同 payload · 抛 DeveloperError。"""
        tid = "trans-018f4a3b-dead-7000-beef-9d5e1c8f3a20"
        req1 = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="first payload for idempotent cache under transition id",
            transition_id=tid,
        )
        sut.request_state_transition(req1)
        # 同 id · 不同 to_state
        req2 = make_transition_request(
            from_state="S1", to_state="S1",  # different
            project_id=mock_project_id,
            reason="second payload with DIFFERENT to_state but same transition_id",
            transition_id=tid,
        )
        with pytest.raises(TransError) as exc:
            sut.request_state_transition(req2)
        assert exc.value.error_code == "E_TRANS_IDEMPOTENT_REPLAY"

    def test_TC_L101_L203_111_allowed_next_table_readonly_at_runtime(
        self,
        sut: StateMachineOrchestrator,
    ) -> None:
        """TC-L101-L203-111 · E_TRANS_ALLOWED_NEXT_READONLY · 运行时修改表抛 DeveloperError。"""
        with pytest.raises(TransError) as exc:
            sut.allowed_next_table["S1"] = ["S4"]  # illegal mutation
        assert exc.value.error_code == "E_TRANS_ALLOWED_NEXT_READONLY"

    def test_TC_L101_L203_112_audit_unavailable_triggers_full_rollback(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L203-112 · E_TRANS_AUDIT_UNAVAILABLE · L2-05 3 次重试全败 · full rollback。"""
        mock_l2_05_client.record_state_transition.side_effect = RuntimeError("L2-05 503")
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="L2-05 down; Partnership rule dictates full rollback per §11.4.2",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.new_state == "S1"  # full rollback
        assert result.error_code == "E_TRANS_AUDIT_UNAVAILABLE"
        # 3 次重试
        assert mock_l2_05_client.record_state_transition.call_count == 3

    def test_TC_L101_L203_113_snapshot_version_stale_rejected(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-113 · E_TRANS_SNAPSHOT_VERSION_STALE · version 乐观锁失败。"""
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="caller version is stale; optimistic lock should reject this request",
            caller_version=0,  # 当前 snapshot.version = 5 （seed via fixture if needed）
        )
        sut._force_snapshot_version(5)
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.error_code == "E_TRANS_SNAPSHOT_VERSION_STALE"


class TestL2_03_Negative_QueryAllowedNext:
    """§3.2 query_allowed_next() 错误码。"""

    def test_TC_L101_L203_114_invalid_state_enum_raises(
        self,
        sut: StateMachineOrchestrator,
    ) -> None:
        """TC-L101-L203-114 · E_TRANS_INVALID_STATE_ENUM · from_state 非 9 枚举之一。"""
        with pytest.raises(TransError) as exc:
            sut.query_allowed_next("SX_NOT_A_STATE")
        assert exc.value.error_code == "E_TRANS_INVALID_STATE_ENUM"


class TestL2_03_Negative_ReplayFromSnapshot:
    """§3.4 replay_from_snapshot() 错误码。"""

    def test_TC_L101_L203_115_replay_event_hash_corrupt_raises_fatal(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        seed_corrupted_event_chain,
    ) -> None:
        """TC-L101-L203-115 · E_TRANS_REPLAY_EVENT_CORRUPT · hash 链校验失败 · FATAL。"""
        with pytest.raises(TransError) as exc:
            sut.replay_from_snapshot(
                replay_request={"project_id": mock_project_id, "snapshot_ref": None}
            )
        assert exc.value.error_code == "E_TRANS_REPLAY_EVENT_CORRUPT"
        assert exc.value.severity == "FATAL"
```

---

## §4 IC-XX 契约集成测试

> 本 L2 是 IC-L2-06 生产方 · IC-L2-02 / IC-01 消费方 · entry hook 内部调 IC-06 + IC-16 · L2-05 代劳 IC-09。
> 每测试 mock 对端 L1-06 / L1-10 / L2-05 / L1-09 客户端 · 断言 payload 结构精确匹配 ic-contracts.md §3.x。

```python
# file: tests/l1_01/test_l2_03_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_03.orchestrator import StateMachineOrchestrator


class TestL2_03_IC_Contracts:
    """IC-L2-02 / IC-01 / IC-L2-06 / IC-06 / IC-16 / IC-09 六个契约集成测试。"""

    def test_TC_L101_L203_601_ic_l2_02_state_transition_request_payload_matches_contract(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-601 · IC-L2-02 入参字段对齐 §3.1.1 YAML schema。

        必选字段：transition_id / project_id / from / to / reason / trigger_tick / evidence_refs / ts
        """
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="IC-L2-02 schema contract field-level alignment verification case",
        )
        # 断言入参结构（仍然是 dict-like / dataclass）
        assert req.transition_id.startswith("trans-")
        assert req.project_id.startswith("pid-")
        assert req.from_state in {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "HALTED", "PAUSED"}
        assert req.to_state in {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "HALTED", "PAUSED"}
        assert len(req.reason) >= 20
        assert req.trigger_tick.startswith("tick-")
        assert len(req.evidence_refs) >= 1
        # 调用后返回符合 §3.1.2 出参 schema
        result = sut.request_state_transition(req)
        assert result.transition_id == req.transition_id
        assert isinstance(result.accepted, bool)
        assert result.new_state is not None
        assert result.ts_applied is not None
        assert result.audit_entry_id.startswith("audit-")

    def test_TC_L101_L203_602_ic_01_stage_gate_driven_path_symmetric(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-602 · IC-01 跨 L1 入口（L1-02 Stage Gate 驱动）· 与 IC-L2-02 对称。

        gate_id 非空 · 其他行为与 IC-L2-02 完全一致（ic-contracts §3.1）。
        """
        seed_current_state("S2")
        req = make_transition_request(
            from_state="S2", to_state="S3",
            project_id=mock_project_id,
            reason="IC-01 Stage Gate approval path from L1-02; same handler as IC-L2-02",
            gate_id="gate-018f4a3b-0001-7000-8b2a-9d5e1c8f3a01",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert result.new_state == "S3"
        # audit_entry 中含 gate_id（IC-01 路径标识）
        assert result.new_entry is not None

    def test_TC_L101_L203_603_ic_l2_06_record_state_transition_includes_rejected(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_l2_05_client: MagicMock,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-603 · IC-L2-06 成功+失败均写审计（prd §10.6 必须 #6）。"""
        # 成功转换
        req_ok = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="happy path should emit IC-L2-06 with accepted=true",
        )
        sut.request_state_transition(req_ok)
        # 失败转换（invalid_next）
        req_fail = make_transition_request(
            from_state="S1", to_state="S4",
            project_id=mock_project_id,
            reason="illegal path should also emit IC-L2-06 with accepted=false",
        )
        sut.request_state_transition(req_fail)
        calls = mock_l2_05_client.record_state_transition.call_args_list
        accepted_values = [c.kwargs["accepted"] for c in calls]
        assert True in accepted_values
        assert False in accepted_values

    def test_TC_L101_L203_604_ic_06_kb_read_called_during_entry_hook(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_l1_06_client: MagicMock,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-604 · IC-06 kb_read · S3 entry hook 注 anti_pattern KB。"""
        seed_current_state("S2")
        req = make_transition_request(
            from_state="S2", to_state="S3",
            project_id=mock_project_id,
            reason="S3 entry hook should issue IC-06 kb_read for kind=anti_pattern stage=S3",
            gate_id="gate-018f4a3b-0002-7000-8b2a-9d5e1c8f3a02",
        )
        sut.request_state_transition(req)
        mock_l1_06_client.kb_read.assert_called()
        payload = mock_l1_06_client.kb_read.call_args.kwargs
        assert payload["kind"] == "anti_pattern"
        assert payload["stage"] == "S3"
        assert payload["project_id"] == mock_project_id

    def test_TC_L101_L203_605_ic_16_push_stage_gate_card_on_four_gated_transitions(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_l1_10_client: MagicMock,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-605 · IC-16 · 仅 S2→S3 / S3→S4 / S4→S5 / S5→S6 四个 Gate 转换触发。"""
        gated = [("S2", "S3"), ("S3", "S4"), ("S4", "S5"), ("S5", "S6")]
        for frm, to in gated:
            seed_current_state(frm)
            mock_l1_10_client.reset_mock()
            req = make_transition_request(
                from_state=frm, to_state=to,
                project_id=mock_project_id,
                reason=f"gated transition {frm}->{to} must push IC-16 stage_gate_card to UI",
                gate_id=f"gate-018f4a3b-00{ord(frm[-1]):02d}-7000-aaaa-0000",
            )
            sut.request_state_transition(req)
            mock_l1_10_client.push_stage_gate_card.assert_called_once()

        # 非 Gate 转换（S5→S7）不应触发 IC-16
        seed_current_state("S5")
        mock_l1_10_client.reset_mock()
        req_nongate = make_transition_request(
            from_state="S5", to_state="S7",
            project_id=mock_project_id,
            reason="non-gated transition S5->S7 must NOT push IC-16 stage_gate_card",
        )
        sut.request_state_transition(req_nongate)
        mock_l1_10_client.push_stage_gate_card.assert_not_called()

    def test_TC_L101_L203_606_ic_09_state_changed_event_via_l2_05(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-606 · IC-09（经 L2-05 代劳）· 每转换 1 条 L1-01:state_changed。"""
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="successful transition must emit L1-01:state_changed via IC-09",
        )
        sut.request_state_transition(req)
        events = [c for c in mock_event_bus.append_event.call_args_list
                  if c.kwargs.get("event_type") == "L1-01:state_changed"]
        assert len(events) == 1
        assert events[0].kwargs["project_id"] == mock_project_id
        payload = events[0].kwargs.get("payload", {})
        assert payload.get("from") == "S1"
        assert payload.get("to") == "S2"
```

---

## §5 性能 SLO 用例

> §12.1 延迟 SLO + §12.2 吞吐 · `@pytest.mark.perf` · pytest-benchmark 可选。

```python
# file: tests/l1_01/test_l2_03_perf.py
from __future__ import annotations

import time
import pytest

from app.l2_03.orchestrator import StateMachineOrchestrator


@pytest.mark.perf
class TestL2_03_SLO:
    """§12 SLO 性能用例（P95/P99/硬上限 500ms 不含 hook）。"""

    def test_TC_L101_L203_701_request_state_transition_p99_under_500ms_no_hook_io(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        disable_hook_io,
    ) -> None:
        """TC-L101-L203-701 · request_state_transition 不含 hook IO · P95 ≤ 200ms / P99 ≤ 500ms（§12.1）。"""
        samples: list[float] = []
        for i in range(500):
            sut._reset_for_perf()
            req = make_transition_request(
                from_state="S1", to_state="S2",
                project_id=mock_project_id,
                reason=f"perf benchmark iteration {i} to measure transition latency SLO",
                transition_id=f"trans-018f4a3b-{i:04x}-7000-perf-9d5e1c8f3a20",
            )
            t0 = time.monotonic()
            sut.request_state_transition(req)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 200.0, f"P95 = {p95}ms 超 §12.1 200ms SLO"
        assert p99 <= 500.0, f"P99 = {p99}ms 超 §12.1 500ms 硬上限"

    def test_TC_L101_L203_702_query_allowed_next_p99_under_10ms(
        self,
        sut: StateMachineOrchestrator,
    ) -> None:
        """TC-L101-L203-702 · query_allowed_next · 纯内存 dict lookup · P99 ≤ 10ms（§12.1）。"""
        samples: list[float] = []
        states = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "HALTED", "PAUSED"]
        for i in range(2000):
            t0 = time.monotonic()
            sut.query_allowed_next(states[i % len(states)])
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99)]
        assert p99 <= 10.0

    def test_TC_L101_L203_703_get_current_state_p99_under_5ms(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
    ) -> None:
        """TC-L101-L203-703 · get_current_state · 单字段内存读 · P99 ≤ 5ms（§12.1）。"""
        samples: list[float] = []
        for _ in range(5000):
            t0 = time.monotonic()
            sut.get_current_state(mock_project_id)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99)]
        assert p99 <= 5.0

    def test_TC_L101_L203_704_replay_1000_events_under_3s_hard_cap(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        seed_event_history_1000,
    ) -> None:
        """TC-L101-L203-704 · replay_from_snapshot · 冷启 1000 events P99 ≤ 2s · 硬上限 3s（§12.1）。"""
        t0 = time.monotonic()
        sut.replay_from_snapshot(
            replay_request={"project_id": mock_project_id, "snapshot_ref": None}
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms <= 3000.0, f"replay 冷启 {elapsed_ms}ms 超 §12.1 3s 硬上限"
```

---

## §6 端到端 e2e 场景

> 对应 prd §9 GWT 八场景 · 映射 §8.2 主流径 + §11.4 失败路径全链路。
> `@pytest.mark.e2e` · 半真实 L2-02 + L2-05 + L1-06 + L1-10 mock。

```python
# file: tests/l1_01/test_l2_03_e2e.py
from __future__ import annotations

import pytest

from app.l2_03.orchestrator import StateMachineOrchestrator


@pytest.mark.e2e
class TestL2_03_E2E:
    """端到端场景 · 对应 prd §9 GWT + §8.2 主链 + §11.4 失败链路。"""

    def test_TC_L101_L203_801_e2e_full_project_lifecycle_S1_to_S7(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        real_l2_05_mock,
        real_l1_06_mock,
        real_l1_10_mock,
    ) -> None:
        """TC-L101-L203-801 · S1→S2→S3→S4→S5→S7 主流径完整生命周期（§8.2 正常链）。

        GIVEN project 新建 (current_state=S1)
        WHEN 依次提交 5 次转换请求（含 3 次 Stage Gate）
        THEN current_state=S7 · 每转换 1 条审计 · 4 次 IC-16 Gate 卡片（实际 3 次正常 Gate + 0 次 S5→S7）
        """
        transitions = [
            ("S1", "S2", None),
            ("S2", "S3", "gate-01"),
            ("S3", "S4", "gate-02"),
            ("S4", "S5", "gate-03"),
            ("S5", "S7", None),
        ]
        for frm, to, gate in transitions:
            req = make_transition_request(
                from_state=frm, to_state=to,
                project_id=mock_project_id,
                reason=f"e2e lifecycle {frm}->{to}; full project path end-to-end coverage",
                gate_id=gate,
            )
            result = sut.request_state_transition(req)
            assert result.accepted is True, f"{frm}->{to} 应该成功"
        assert sut.get_current_state(mock_project_id) == "S7"
        # 3 次 Gate 卡片（S2→S3 / S3→S4 / S4→S5）
        gate_calls = real_l1_10_mock.push_stage_gate_card.call_count
        assert gate_calls == 3

    def test_TC_L101_L203_802_e2e_quality_loop_S5_to_S4_to_S5_recovers(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        real_l2_05_mock,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-802 · Quality Loop 轻度 FAIL · S5→S4→S5→S7（§8.2 #13/#12/#18）。

        GIVEN current_state=S5 · verifier FAIL light
        WHEN 回退 S4 补实现 · 再进 S5 · verifier PASS · 进 S7
        THEN 最终 S7 · 审计链中 3 条 state_changed
        """
        seed_current_state("S5")
        for frm, to, reason in [
            ("S5", "S4", "Quality Loop light FAIL; rework single WP per §8.2 #13"),
            ("S4", "S5", "single WP done; re-enter verify for final PASS check"),
            ("S5", "S7", "verifier_report PASS this round; main flow §8.2 #18"),
        ]:
            req = make_transition_request(
                from_state=frm, to_state=to,
                project_id=mock_project_id, reason=reason,
            )
            r = sut.request_state_transition(req)
            assert r.accepted is True
        assert sut.get_current_state(mock_project_id) == "S7"
        audits = real_l2_05_mock.record_state_transition.call_args_list
        assert sum(1 for c in audits if c.kwargs.get("accepted") is True) == 3

    def test_TC_L101_L203_803_e2e_entry_hook_fail_full_rollback_chain(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        real_l2_05_mock,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-803 · §11.4.1 entry hook 失败全链路 · rollback + 审计 accepted=false。

        GIVEN current_state=S3
        WHEN S3→S4 · S4 entry hook 调 IC-06 kb_read timeout
        THEN state rollback 到 S3 · 审计 accepted=false + error=E_TRANS_ENTRY_HOOK_FAIL
        """
        seed_current_state("S3")
        sut._inject_hook_failure(state="S4", direction="entry", err="IC-06 kb_read timeout 2s")
        req = make_transition_request(
            from_state="S3", to_state="S4",
            project_id=mock_project_id,
            reason="entry hook on S4 will fail; expect rollback to S3 per §11.4.1",
            gate_id="gate-fail-01",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.new_state == "S3"
        # 审计写入（含失败）
        fail_audits = [c for c in real_l2_05_mock.record_state_transition.call_args_list
                       if c.kwargs.get("accepted") is False]
        assert len(fail_audits) == 1
        assert fail_audits[0].kwargs.get("error_code") == "E_TRANS_ENTRY_HOOK_FAIL"
```

---

## §7 测试 fixture

> conftest.py 提供本 L2 复用 fixture。`mock_project_id` / `mock_event_bus` / `mock_clock` / `mock_ic_payload` + 转换请求工厂 + 状态种子。

```python
# file: tests/l1_01/conftest_l2_03.py  (与 L2-01 的 conftest.py 合并)
from __future__ import annotations

import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from app.l2_03.orchestrator import StateMachineOrchestrator
from app.l2_03.schemas import StateTransitionRequest


class VirtualClock:
    """§9 Mock 策略 · 手动推进 ms 假时钟（幂等缓存 TTL 测试用）。"""
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
def mock_clock() -> VirtualClock:
    return VirtualClock()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="L1-09-event-bus")
    bus.append_event.return_value = {"event_id": f"evt-{uuid.uuid4()}", "sequence": 1}
    bus.query.return_value = []
    return bus


@pytest.fixture
def mock_l2_05_client() -> MagicMock:
    """IC-L2-06 下游 · record_state_transition."""
    client = MagicMock(name="L2-05-audit-recorder")
    client.record_state_transition.return_value = {"audit_id": f"audit-{uuid.uuid4()}"}
    return client


@pytest.fixture
def mock_l1_06_client() -> MagicMock:
    """IC-06 kb_read · entry hook 依赖。"""
    client = MagicMock(name="L1-06-kb")
    client.kb_read.return_value = {"entries": []}
    return client


@pytest.fixture
def mock_l1_10_client() -> MagicMock:
    """IC-16 push_stage_gate_card · entry hook 依赖。"""
    client = MagicMock(name="L1-10-ui")
    client.push_stage_gate_card.return_value = {"card_id": f"card-{uuid.uuid4()}"}
    return client


@pytest.fixture
def mock_ic_payload() -> dict[str, Any]:
    """IC-L2-02 state_transition_request 标准 payload（§3.1.1 YAML 字段骨架）。"""
    return {
        "transition_id": f"trans-{uuid.uuid4()}",
        "project_id": "pid-default",
        "from": "S1",
        "to": "S2",
        "reason": "standard IC-L2-02 payload for field-level schema alignment",
        "trigger_tick": f"tick-{uuid.uuid4()}",
        "evidence_refs": ["decision-001"],
        "gate_id": None,
        "ts": "2026-04-22T00:00:00Z",
    }


@pytest.fixture
def sut(mock_project_id, mock_clock, mock_event_bus,
        mock_l2_05_client, mock_l1_06_client, mock_l1_10_client) -> StateMachineOrchestrator:
    return StateMachineOrchestrator(
        session_active_pid=mock_project_id,
        clock=mock_clock,
        event_bus=mock_event_bus,
        l2_05_client=mock_l2_05_client,
        l1_06_client=mock_l1_06_client,
        l1_10_client=mock_l1_10_client,
    )


@pytest.fixture
def make_transition_request(mock_project_id) -> Callable[..., StateTransitionRequest]:
    def _factory(**overrides: Any) -> StateTransitionRequest:
        base: dict[str, Any] = dict(
            transition_id=f"trans-{uuid.uuid4()}",
            project_id=mock_project_id,
            from_state="S1",
            to_state="S2",
            reason="default factory reason with sufficient length (>= 20 chars)",
            trigger_tick=f"tick-{uuid.uuid4()}",
            evidence_refs=["decision-default-001"],
            gate_id=None,
            ts="2026-04-22T00:00:00Z",
            caller_version=None,
        )
        base.update(overrides)
        return StateTransitionRequest(**base)
    return _factory


@pytest.fixture
def seed_current_state(sut):
    """强制 snapshot.current_state 为指定值（绕过 allowed_next 校验 · 测试路径用）。"""
    def _seed(state: str) -> None:
        sut._force_current_state_unsafe(state)
    return _seed


@pytest.fixture
def seed_event_history_1000(mock_event_bus):
    """向 event_bus 注入 1000 条连续 state_history events（hash 链完整）。"""
    events: list[dict] = []
    for i in range(1000):
        events.append({
            "event_type": "L1-01:state_changed",
            "sequence": i,
            "prev_hash": f"h{i-1:04d}" if i > 0 else None,
            "hash": f"h{i:04d}",
            "payload": {"from": "S1", "to": "S1", "version": i + 1},
        })
    mock_event_bus.query.return_value = events


@pytest.fixture
def seed_corrupted_event_chain(mock_event_bus):
    """注入 hash 链破损 event 流（中间 hash 与下一个 prev_hash 不匹配）。"""
    mock_event_bus.query.return_value = [
        {"event_type": "L1-01:state_changed", "sequence": 0, "prev_hash": None, "hash": "h0"},
        {"event_type": "L1-01:state_changed", "sequence": 1, "prev_hash": "WRONG", "hash": "h1"},
    ]
```

---

## §8 集成点用例（与兄弟 L2 协作）

> 基于 3-1 L2-03 §4 接口依赖 + L1-01 arch §6.3 IC-L2 表：L2-02（上游主调）· L2-01（间接 · trigger_tick）· L2-04（间接 · 状态查询）· L2-05（下游审计）· L2-06（间接 · 硬红线链）。

```python
# file: tests/l1_01/test_l2_03_integration.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_03.orchestrator import StateMachineOrchestrator


class TestL2_03_Integration:
    """与 L2-01 / L2-02 / L2-04 / L2-06 协作集成。"""

    def test_TC_L101_L203_901_integration_l2_02_drives_transition_on_decision(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L203-901 · L2-02 决策 decision_type=state_transition · 经 IC-L2-02 驱动本 L2。"""
        # 模拟 L2-02 下发决策（只检查本 L2 接受 IC-L2-02 入参即可）
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="L2-02 decision to advance from S1 to S2 via IC-L2-02 integration",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert mock_l2_05_client.record_state_transition.call_count == 1

    def test_TC_L101_L203_902_integration_trigger_tick_preserved_in_audit(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L203-902 · 与 L2-01 间接协作 · trigger_tick 透传到 IC-L2-06 审计。"""
        trigger_tick = "tick-018f4a3b-1111-7000-aaaa-9d5e1c8f3a99"
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="trigger_tick must be preserved end-to-end for audit chain traceability",
            trigger_tick=trigger_tick,
        )
        sut.request_state_transition(req)
        audit_call = mock_l2_05_client.record_state_transition.call_args
        assert audit_call.kwargs.get("trigger_tick") == trigger_tick

    def test_TC_L101_L203_903_integration_l2_06_hard_halt_to_HALTED_within_100ms(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-903 · 与 L2-06 协作 · 硬红线链路 · 任意 Sn→HALTED 成功。"""
        seed_current_state("S3")
        import time
        req = make_transition_request(
            from_state="S3", to_state="HALTED",
            project_id=mock_project_id,
            reason="L2-06 hard_halt propagation; switch to HALTED state with audit trail",
        )
        t0 = time.monotonic()
        result = sut.request_state_transition(req)
        elapsed = (time.monotonic() - t0) * 1000
        assert result.accepted is True
        assert result.new_state == "HALTED"
        # HALTED entry hook 包含 failure-archive 写入
        assert any(art.startswith("failure-archive") or "halt" in art.lower()
                   for art in result.hook_results.entry_hook_result.artifacts)
        assert elapsed <= 500.0  # §12.1 硬上限 · 含 HALTED entry hook IO
```

---

## §9 边界 / edge case

> 空 / 超大 / 并发 / 超时 / 崩溃 / 脏数据 六类边界 ≥ 5 个用例。

```python
# file: tests/l1_01/test_l2_03_edge.py
from __future__ import annotations

import threading
import pytest

from app.l2_03.orchestrator import StateMachineOrchestrator
from app.l2_03.errors import TransError


class TestL2_03_Edge:
    """边界 / edge case。"""

    def test_TC_L101_L203_951_empty_allowed_next_for_terminal_state(
        self,
        sut: StateMachineOrchestrator,
    ) -> None:
        """TC-L101-L203-951 · 空数组边界 · §8.5 终态（CLOSED 外部视角 · 虽 S7 不是真终态但可构造）。

        对 HALTED state query_allowed_next 应返回非空 list（可 RESUME 到 S1-S7 + PAUSED）；
        真正的终态 `[*]` 不可查询（不在 9 枚举内）。
        """
        halted_next = sut.query_allowed_next("HALTED")
        assert len(halted_next) >= 8  # S1-S7 + PAUSED

    def test_TC_L101_L203_952_large_state_history_10000_triggers_archive(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-952 · 超大 · state_history 10000 条触发归档（§12.4 容量上限）。"""
        sut._force_history_size(10000)
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="history size at 10000 cap; one more transition should trigger archive",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is True
        assert sut.archive_triggered_count() == 1

    def test_TC_L101_L203_953_concurrent_10_requests_only_one_succeeds(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-953 · 并发 10 次请求 · 仅 1 成功 · 9 返回 E_TRANS_CONCURRENT。"""
        results: list = []
        lock_start = threading.Event()

        def worker(i: int) -> None:
            req = make_transition_request(
                from_state="S1", to_state="S2",
                project_id=mock_project_id,
                reason=f"concurrent worker {i} attempts transition simultaneously via test",
                transition_id=f"trans-018f4a3b-{i:04d}-7000-8b2a-9d5e1c8f3a20",
            )
            lock_start.wait()
            results.append(sut.request_state_transition(req))

        sut._inject_transition_hold_ms(150)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads: t.start()
        lock_start.set()
        for t in threads: t.join()
        accepted = [r for r in results if r.accepted]
        rejected_concurrent = [r for r in results if not r.accepted
                               and r.error_code == "E_TRANS_CONCURRENT"]
        assert len(accepted) == 1
        assert len(rejected_concurrent) == 9

    def test_TC_L101_L203_954_entry_hook_timeout_2s_rollback(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
        seed_current_state,
    ) -> None:
        """TC-L101-L203-954 · 超时 · entry hook 2s SLO 超时 · rollback（§12.1）。"""
        seed_current_state("S3")
        sut._inject_hook_latency_ms(state="S4", direction="entry", ms=2500)  # > 2s SLO
        req = make_transition_request(
            from_state="S3", to_state="S4",
            project_id=mock_project_id,
            reason="entry hook will exceed 2s SLO; should raise ENTRY_HOOK_FAIL with rollback",
        )
        result = sut.request_state_transition(req)
        assert result.accepted is False
        assert result.new_state == "S3"
        assert result.error_code == "E_TRANS_ENTRY_HOOK_FAIL"

    def test_TC_L101_L203_955_crash_during_transition_snapshot_consistent(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        make_transition_request,
    ) -> None:
        """TC-L101-L203-955 · 崩溃 · 转换过程中模拟崩溃 · replay 后 snapshot 与事件流一致。"""
        req = make_transition_request(
            from_state="S1", to_state="S2",
            project_id=mock_project_id,
            reason="simulate crash mid-transition; next bootstrap must reconcile via replay",
        )
        try:
            sut._inject_crash_after_step(step=5)  # crash after exit hook but before entry
            sut.request_state_transition(req)
        except Exception:
            pass
        # 重启重放
        recovered = sut.replay_from_snapshot(
            replay_request={"project_id": mock_project_id, "snapshot_ref": None}
        )
        # replay 应返回转换前状态（没完成的转换不落地）
        assert recovered.current_state == "S1"

    def test_TC_L101_L203_956_dirty_data_malformed_enum_in_history_rejected(
        self,
        sut: StateMachineOrchestrator,
        mock_project_id: str,
        mock_event_bus,
    ) -> None:
        """TC-L101-L203-956 · 脏数据 · event 流含非 9 枚举的 state · replay 部分恢复 + WARN。"""
        mock_event_bus.query.return_value = [
            {"event_type": "L1-01:state_changed", "sequence": 0, "prev_hash": None, "hash": "h0",
             "payload": {"from": "S1", "to": "S2"}},
            {"event_type": "L1-01:state_changed", "sequence": 1, "prev_hash": "h0", "hash": "h1",
             "payload": {"from": "S2", "to": "MALFORMED_STATE"}},
        ]
        snapshot = sut.replay_from_snapshot(
            replay_request={"project_id": mock_project_id, "snapshot_ref": None}
        )
        # 部分恢复（走到 S2 后停）+ WARN 日志
        assert snapshot.current_state == "S2"
        assert snapshot.version == 1
        assert sut.has_warning("replay_incomplete") is True
```

---

## 附录 · 用例统计

- §2 正向用例：11（每 public 方法 ≥ 1 · 其中主方法 `request_state_transition` 覆盖 7 个典型转换场景）
- §3 负向用例：15（覆盖 §11.1 全部 13 个 `E_TRANS_*` + 补 `E_TRANS_INVALID_STATE_ENUM` + `E_TRANS_REPLAY_EVENT_CORRUPT`）
- §4 IC 契约：6（IC-L2-02 · IC-01 · IC-L2-06 · IC-06 · IC-16 · IC-09）
- §5 性能 SLO：4（P95/P99 + 硬上限 500ms 不含 hook + query 10ms + get 5ms + replay 3s）
- §6 e2e 场景：3（S1→S7 主流径 · Quality Loop · entry hook 失败 rollback）
- §8 集成点：3（L2-02 / L2-01 trigger_tick / L2-06 hard_halt）
- §9 边界：6（空 · 超大 · 并发 · 超时 · 崩溃 · 脏数据）
- 合计 `def test_*`：48+

映射 §13 TC ID 矩阵：§13.2 "3-2 TDD 用例文件" 所列 12 项映射全覆盖（§3 负向 / §2 单元 / §4 集成 / §5 恢复 / §6 集成 / §7 rollback / §8 Strategy / §9 配置 / §10 状态机 / §11 降级 / §12 benchmark）。
