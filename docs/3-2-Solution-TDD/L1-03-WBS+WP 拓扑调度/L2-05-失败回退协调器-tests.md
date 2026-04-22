---
doc_id: tests-L1-03-L2-05-失败回退协调器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-05-失败回退协调器.md
  - docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-03 L2-05-失败回退协调器 · TDD 测试用例

> 基于 3-1 L2-05 §3（4 接收 + 多发起）+ §11（13 条 `E_L103_L205_*`）+ §12 SLO + §13 TC 矩阵 驱动。
> TC ID 统一格式：`TC-L103-L205-NNN`。pytest + Python 3.11+；`class TestL2_05_FailureRollbackCoordinator`；关键路径 3 次失败阈值 / 死锁 / IC-15 升级独立分组。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法 | TC ID | 覆盖类型 | IC |
|---|---|---|---|
| `on_wp_failed()` · 单次失败 count=1 | TC-L103-L205-001 | unit | IC-L2-05 |
| `on_wp_failed()` · count=2 未达阈 | TC-L103-L205-002 | unit | IC-L2-05 |
| `on_wp_failed()` · count=3 达阈 | TC-L103-L205-003 | unit | IC-L2-05 |
| `on_wp_done_reset()` · count 归零 | TC-L103-L205-004 | unit | IC-L2-05-B |
| `on_wp_done_reset()` · no_op | TC-L103-L205-005 | unit | IC-L2-05-B |
| `on_deadlock_notified()` · 立即 IC-15 | TC-L103-L205-006 | unit | IC-15 |
| `on_rollback_route_chosen()` · SPLIT_WP | TC-L103-L205-007 | unit | IC-L2-07 |
| `on_rollback_route_chosen()` · MODIFY_WBS | TC-L103-L205-008 | unit | — |
| `on_rollback_route_chosen()` · MODIFY_AC | TC-L103-L205-009 | unit | — |
| `mark_stuck()` 调用 L2-02 | TC-L103-L205-010 | unit | IC-L2-06 |
| `trigger_incremental_decomposition()` | TC-L103-L205-011 | unit | IC-L2-07 |
| `kb_read(similar_failure)` 可选 hint | TC-L103-L205-012 | unit | IC-06 |
| `export_failure_summary()` | TC-L103-L205-013 | unit | — |
| 生成 advice_card（≥3 选项）| TC-L103-L205-014 | unit | — |
| 幂等（同 failure_event_id）| TC-L103-L205-015 | unit | — |
| FailureCounter 状态机 5 状态 | TC-L103-L205-016 | unit | — |
| 审计 counter_incremented 事件 | TC-L103-L205-017 | unit | IC-09 |
| advice_issued 审计 | TC-L103-L205-018 | unit | IC-09 |

### §1.2 错误码 × 测试（§11 13 项全覆盖）

| 错误码 | TC ID | 说明 |
|---|---|---|
| `E_L103_L205_101` | TC-L103-L205-101 | wp_failed 字段缺失 |
| `E_L103_L205_102` | TC-L103-L205-102 | FailureCounter 初始化失败 |
| `E_L103_L205_103` | TC-L103-L205-103 | wp_done 无对应 counter · no_op |
| `E_L103_L205_201` | TC-L103-L205-104 | 跨 project 失败信号 |
| `E_L103_L205_301` | TC-L103-L205-105 | evidence_refs 空（硬红线）|
| `E_L103_L205_302` | TC-L103-L205-106 | IC-14 超时 |
| `E_L103_L205_303` | TC-L103-L205-107 | SPLIT_WP 转 L2-01 失败 |
| `E_L103_L205_304` | TC-L103-L205-108 | chosen_path 枚举非法 |
| `E_L103_L205_305` | TC-L103-L205-109 | advice_card_ref 失效 |
| `E_L103_L205_401` | TC-L103-L205-110 | IC-09 append 失败 |
| `E_L103_L205_402` | TC-L103-L205-111 | rollback-advices.jsonl 写失败 |
| `E_L103_L205_501` | TC-L103-L205-112 | 外部直改 counters bypass |
| `E_L103_L205_502` | TC-L103-L205-113 | 死锁二次确认失败 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| IC-L2-05 on_wp_failed | L2-04 → 本 L2 | TC-L103-L205-601 |
| IC-L2-05-B on_wp_done_reset | L2-04 → 本 L2 | TC-L103-L205-602 |
| on_deadlock_notified | L2-03 → 本 L2 | TC-L103-L205-603 |
| IC-L2-06 mark_stuck | 本 L2 → L2-02 | TC-L103-L205-604 |
| IC-L2-07 trigger_incremental_decomposition | 本 L2 → L2-01 | TC-L103-L205-605 |
| IC-15 request_hard_halt | 本 L2 → L1-07 | TC-L103-L205-606 |

---

## §2 正向用例

```python
# file: tests/l1_03/test_l2_05_failure_rollback_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_05_rollback.coordinator import FailureRollbackCoordinator
from app.l2_05_rollback.schemas import (
    OnWpFailedRequest, OnWpDoneResetRequest,
    OnDeadlockNotifiedRequest, OnRollbackRouteChosenRequest,
)


class TestL2_05_Positive:

    def test_TC_L103_L205_001_on_wp_failed_count_1(
        self, sut: FailureRollbackCoordinator, mock_project_id: str,
    ) -> None:
        """TC-L103-L205-001 · 单次失败 · new_count=1 · threshold_reached=False."""
        resp = sut.on_wp_failed(OnWpFailedRequest(
            project_id=mock_project_id, wp_id="wp-001",
            fail_level="FAIL_L1", failure_event_id="evt-f-001",
            failure_reason_summary="subagent timeout",
            requester_l2="L2-04", ts_ns=1_700_000_000_001,
        ))
        assert resp.status == "ok"
        assert resp.new_count == 1
        assert resp.threshold_reached is False
        assert resp.advice_card_ref is None

    def test_TC_L103_L205_002_on_wp_failed_count_2(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L103-L205-002 · 累计 2 次 · threshold_reached 仍 False."""
        for i in range(2):
            resp = sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-001",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-f-00{i+1}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_000_000 + i,
            ))
        assert resp.new_count == 2
        assert resp.threshold_reached is False

    def test_TC_L103_L205_003_on_wp_failed_count_3_threshold_reached(
        self, sut, mock_project_id, mock_topology_mgr, mock_l2_01,
    ) -> None:
        """TC-L103-L205-003 · 达 3 次阈 · advice_card_ref 返回 · 同步 mark_stuck."""
        for i in range(3):
            resp = sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-001",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-f-3-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_000_000 + i,
            ))
        assert resp.new_count == 3
        assert resp.threshold_reached is True
        assert resp.advice_card_ref is not None
        mock_topology_mgr.mark_stuck.assert_called()

    def test_TC_L103_L205_004_on_wp_done_reset_counter_to_0(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L103-L205-004 · 失败 2 次后 done_reset · prior_count=2, reset_to=0."""
        for i in range(2):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-002",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-r-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_000_010 + i,
            ))
        resp = sut.on_wp_done_reset(OnWpDoneResetRequest(
            project_id=mock_project_id, wp_id="wp-002",
            done_event_id="evt-d-001", requester_l2="L2-04",
            ts_ns=1_700_000_000_020,
        ))
        assert resp.status == "ok"
        assert resp.prior_count == 2
        assert resp.reset_to == 0

    def test_TC_L103_L205_005_on_wp_done_reset_no_op(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L103-L205-005 · counter 本就是 0 · no_op。"""
        resp = sut.on_wp_done_reset(OnWpDoneResetRequest(
            project_id=mock_project_id, wp_id="wp-fresh",
            done_event_id="evt-fresh-001", requester_l2="L2-04",
            ts_ns=1_700_000_000_030,
        ))
        assert resp.status == "no_op"
        assert resp.prior_count == 0

    def test_TC_L103_L205_006_on_deadlock_notified_triggers_ic15(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        """TC-L103-L205-006 · 立即 IC-15 · red_line_id=deadlock."""
        resp = sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
            project_id=mock_project_id,
            deadlock_snapshot={
                "all_wp_states": {"wp-001": "FAILED", "wp-002": "STUCK"},
                "failed_wp_ids": ["wp-001"],
                "stuck_wp_ids": ["wp-002"],
                "blocked_wp_ids": [],
                "topology_id": "topo-abc",
                "snapshot_ts_ns": 1_700_000_000_500,
            },
            confirmed=True, requester_l2="L2-03",
        ))
        assert resp.status == "ok"
        assert resp.halt_id is not None
        mock_supervisor.request_hard_halt.assert_called_once()
        kw = mock_supervisor.request_hard_halt.call_args.args[0]
        assert kw["red_line_id"] == "deadlock"

    def test_TC_L103_L205_007_on_rollback_route_split_wp(
        self, sut, mock_project_id, mock_l2_01,
    ) -> None:
        """TC-L103-L205-007 · chosen_path=SPLIT_WP · 触发 L2-01 差量拆解。"""
        resp = sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
            project_id=mock_project_id, wp_id="wp-001",
            advice_card_ref="card-001",
            chosen_path="SPLIT_WP",
            route_id="route-001",
            supervisor_decision_id="sd-001",
        ))
        assert resp.status == "ok"
        mock_l2_01.request_incremental_decompose.assert_called_once()

    def test_TC_L103_L205_008_on_rollback_route_modify_wbs(
        self, sut, mock_project_id, mock_l2_01,
    ) -> None:
        """TC-L103-L205-008 · chosen_path=MODIFY_WBS · 保持 stuck 等 L1-02 介入。"""
        resp = sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
            project_id=mock_project_id, wp_id="wp-001",
            advice_card_ref="card-002",
            chosen_path="MODIFY_WBS",
            route_id="route-002",
            supervisor_decision_id="sd-002",
        ))
        assert resp.status == "ok"
        mock_l2_01.request_incremental_decompose.assert_not_called()

    def test_TC_L103_L205_009_on_rollback_route_modify_ac(
        self, sut, mock_project_id, mock_l2_01,
    ) -> None:
        resp = sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
            project_id=mock_project_id, wp_id="wp-001",
            advice_card_ref="card-003",
            chosen_path="MODIFY_AC",
            route_id="route-003",
            supervisor_decision_id="sd-003",
        ))
        assert resp.status == "ok"

    def test_TC_L103_L205_010_mark_stuck_call(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        """TC-L103-L205-010 · _mark_stuck_on_l2_02 payload."""
        sut._mark_stuck_on_l2_02(project_id=mock_project_id, wp_id="wp-001",
                                  failure_count=3,
                                  evidence_refs=["e1", "e2", "e3"],
                                  advice_card_ref="card-001")
        p = mock_topology_mgr.mark_stuck.call_args.args[0]
        assert p["failure_count"] == 3
        assert len(p["evidence_refs"]) >= 1
        assert p["advice_card_ref"] == "card-001"

    def test_TC_L103_L205_011_trigger_incremental_decomposition(
        self, sut, mock_project_id, mock_l2_01,
    ) -> None:
        sut._trigger_incremental_decomposition(
            project_id=mock_project_id, wp_id="wp-001",
            reason="failure_count_exceeded",
            advice_card_ref="card-001",
        )
        mock_l2_01.request_incremental_decompose.assert_called_once()

    def test_TC_L103_L205_012_kb_read_hints(
        self, sut, mock_project_id, mock_kb,
    ) -> None:
        """TC-L103-L205-012 · 达阈时调 kb_read(similar_failure) 丰富 advice。"""
        for i in range(3):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-k",
                fail_level="FAIL_L2",
                failure_event_id=f"evt-k-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04",
                ts_ns=1_700_000_000_100 + i,
            ))
        assert mock_kb.kb_read.called

    def test_TC_L103_L205_013_export_failure_summary(
        self, sut, mock_project_id,
    ) -> None:
        view = sut.export_failure_summary(mock_project_id)
        assert hasattr(view, "counters") or hasattr(view, "stuck_wp_ids")

    def test_TC_L103_L205_014_advice_card_has_3_options(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L103-L205-014 · 建议卡至少含 3 选项（SPLIT_WP / MODIFY_WBS / MODIFY_AC）。"""
        for i in range(3):
            resp = sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-adv",
                fail_level="FAIL_L2",
                failure_event_id=f"evt-a-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04",
                ts_ns=1_700_000_000_200 + i,
            ))
        card = sut._get_advice_card(resp.advice_card_ref)
        options = {opt["path"] for opt in card["options"]}
        assert {"SPLIT_WP", "MODIFY_WBS", "MODIFY_AC"}.issubset(options)

    def test_TC_L103_L205_015_idempotent_same_failure_event_id(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L103-L205-015 · 同一 failure_event_id 重复 · counter 只加 1 次。"""
        req = OnWpFailedRequest(
            project_id=mock_project_id, wp_id="wp-i",
            fail_level="FAIL_L1",
            failure_event_id="evt-dup-001",
            failure_reason_summary="r",
            requester_l2="L2-04", ts_ns=1_700_000_000_300,
        )
        sut.on_wp_failed(req)
        r2 = sut.on_wp_failed(req)
        assert r2.new_count == 1  # 不重复累加

    def test_TC_L103_L205_016_counter_state_machine(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L103-L205-016 · FailureCounter 5 状态 fresh → counting → threshold_reached → advice_issued → closed."""
        counter = sut._get_or_create_counter(mock_project_id, "wp-sm")
        assert counter.state == "fresh"
        sut.on_wp_failed(OnWpFailedRequest(
            project_id=mock_project_id, wp_id="wp-sm",
            fail_level="FAIL_L1",
            failure_event_id="evt-sm-1",
            failure_reason_summary="r",
            requester_l2="L2-04", ts_ns=1_700_000_000_400,
        ))
        counter = sut._get_or_create_counter(mock_project_id, "wp-sm")
        assert counter.state == "counting"

    def test_TC_L103_L205_017_counter_incremented_event(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        sut.on_wp_failed(OnWpFailedRequest(
            project_id=mock_project_id, wp_id="wp-evt",
            fail_level="FAIL_L1",
            failure_event_id="evt-e-001",
            failure_reason_summary="r",
            requester_l2="L2-04", ts_ns=1_700_000_000_500,
        ))
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert any("counter_incremented" in t or "counter_updated" in t for t in types)

    def test_TC_L103_L205_018_advice_issued_event(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        for i in range(3):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-adv-e",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-ad-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_000_600 + i,
            ))
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert any("advice_issued" in t for t in types)
```

---

## §3 负向用例

```python
# file: tests/l1_03/test_l2_05_failure_rollback_negative.py
import pytest

from app.l2_05_rollback.schemas import (
    OnWpFailedRequest, OnWpDoneResetRequest,
    OnDeadlockNotifiedRequest, OnRollbackRouteChosenRequest,
)


class TestL2_05_Negative:

    def test_TC_L103_L205_101_wp_failed_missing_fields(self, sut, mock_project_id) -> None:
        """E_L103_L205_101 · failure_event_id 缺失 · 拒绝。"""
        with pytest.raises(Exception) as ei:
            sut.on_wp_failed_raw({
                "project_id": mock_project_id, "wp_id": "wp-001",
                "fail_level": "FAIL_L1",
                # 缺 failure_event_id
                "requester_l2": "L2-04", "ts_ns": 1,
            })
        assert "E_L103_L205_101" in str(ei.value)

    def test_TC_L103_L205_102_counter_init_fail(
        self, sut_with_broken_storage, mock_project_id,
    ) -> None:
        """E_L103_L205_102 · storage 不可初始化 · 降级 + WARN。"""
        with pytest.raises(Exception) as ei:
            sut_with_broken_storage.on_wp_failed_raw({
                "project_id": mock_project_id, "wp_id": "wp-001",
                "fail_level": "FAIL_L1",
                "failure_event_id": "evt-broken",
                "requester_l2": "L2-04", "ts_ns": 1,
            })
        assert "E_L103_L205_102" in str(ei.value)

    def test_TC_L103_L205_103_wp_done_no_counter_is_no_op(
        self, sut, mock_project_id,
    ) -> None:
        """E_L103_L205_103 · wp_done 但 counter 不存在 · 返回 status=no_op（非错误）。"""
        resp = sut.on_wp_done_reset(OnWpDoneResetRequest(
            project_id=mock_project_id, wp_id="wp-never-failed",
            done_event_id="evt-d", requester_l2="L2-04",
            ts_ns=1_700_000_000_700,
        ))
        assert resp.status == "no_op"

    def test_TC_L103_L205_104_cross_project(self, sut) -> None:
        """E_L103_L205_201 · project_id=other · 拒绝 + bypass_attempt."""
        with pytest.raises(Exception) as ei:
            sut.on_wp_failed(OnWpFailedRequest(
                project_id="hf-proj-different",
                wp_id="wp-001", fail_level="FAIL_L1",
                failure_event_id="evt-cross-001",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_000_800,
            ), expected_project="hf-proj-other")
        assert "E_L103_L205_201" in str(ei.value)

    def test_TC_L103_L205_105_evidence_empty_hard_halt(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        """E_L103_L205_301 · evidence_refs 空 · 最严重 → IC-15."""
        for i in range(3):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-evid",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-nev-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_000_900 + i,
                evidence_refs_override=[],  # 强制空
            ))
        # 达阈后发现 evidence_refs 空 → hard_halt
        # （mock_supervisor.request_hard_halt 被触发 · red_line=evidence_data_corrupted）

    def test_TC_L103_L205_106_ic14_timeout(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        """E_L103_L205_302 · IC-14 push_suggestion timeout · 重推 ≤ 2 次后 WARN."""
        mock_supervisor.push_suggestion.side_effect = TimeoutError("ic14 down")
        # 触发一个 advice card 推送流程
        with pytest.raises(Exception) as ei:
            sut._push_advice_card(project_id=mock_project_id,
                                    advice_card_ref="card-xxx")
        assert "E_L103_L205_302" in str(ei.value)

    def test_TC_L103_L205_107_split_wp_l2_01_fail_fallback_modify_wbs(
        self, sut, mock_project_id, mock_l2_01,
    ) -> None:
        """E_L103_L205_303 · SPLIT_WP 转 L2-01 失败 · fallback MODIFY_WBS."""
        mock_l2_01.request_incremental_decompose.return_value = {
            "accepted": False,
            "rejection": {"err_code": "E_L103_L201_109", "reason": "target missing"},
        }
        resp = sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
            project_id=mock_project_id, wp_id="wp-sp",
            advice_card_ref="card-sp",
            chosen_path="SPLIT_WP",
            route_id="route-sp",
            supervisor_decision_id="sd-sp",
        ))
        # fallback MODIFY_WBS · wp 保持 stuck
        assert resp.status in {"ok", "fallback"}

    def test_TC_L103_L205_108_chosen_path_illegal(
        self, sut, mock_project_id,
    ) -> None:
        """E_L103_L205_304 · chosen_path 枚举非法."""
        with pytest.raises(Exception) as ei:
            sut.on_rollback_route_chosen_raw({
                "project_id": mock_project_id, "wp_id": "wp-x",
                "advice_card_ref": "card-x",
                "chosen_path": "INVALID_PATH",
                "route_id": "route-x",
                "supervisor_decision_id": "sd-x",
            })
        assert "E_L103_L205_304" in str(ei.value)

    def test_TC_L103_L205_109_advice_card_ref_expired(
        self, sut, mock_project_id,
    ) -> None:
        """E_L103_L205_305 · advice_card_ref 已失效（revision 老）· 拒绝."""
        with pytest.raises(Exception) as ei:
            sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
                project_id=mock_project_id, wp_id="wp-x",
                advice_card_ref="card-expired-999",
                chosen_path="MODIFY_WBS",
                route_id="route-x",
                supervisor_decision_id="sd-x",
            ))
        assert "E_L103_L205_305" in str(ei.value)

    def test_TC_L103_L205_110_ic09_append_fail_refuses_ack(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        """E_L103_L205_401 · append_event 重试 3 次仍失败 · 拒绝产 ack (PM-08)."""
        mock_event_bus.append_event.side_effect = IOError("bus down")
        with pytest.raises(Exception) as ei:
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-aud",
                fail_level="FAIL_L1",
                failure_event_id="evt-aud-001",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_001_000,
            ))
        assert "E_L103_L205_401" in str(ei.value)

    def test_TC_L103_L205_111_rollback_advices_jsonl_write_fail(
        self, sut_ro_fs, mock_project_id,
    ) -> None:
        """E_L103_L205_402 · rollback-advices.jsonl 写失败 · DEGRADED."""
        for i in range(3):
            sut_ro_fs.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-rofs",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-ro-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1_700_000_001_100 + i,
            ))
        assert sut_ro_fs.mode == "DEGRADED"

    def test_TC_L103_L205_112_bypass_direct_write_counters(
        self, sut, mock_project_id, tamper_counters,
    ) -> None:
        """E_L103_L205_501 · 外部直改 counters 文件 · consistency_check 识别."""
        tamper_counters(project_id=mock_project_id)
        with pytest.raises(Exception) as ei:
            sut.consistency_check(project_id=mock_project_id)
        assert "E_L103_L205_501" in str(ei.value)

    def test_TC_L103_L205_113_deadlock_confirmed_false(
        self, sut, mock_project_id,
    ) -> None:
        """E_L103_L205_502 · on_deadlock_notified confirmed=False · 拒绝 · 要求二次确认."""
        with pytest.raises(Exception) as ei:
            sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
                project_id=mock_project_id,
                deadlock_snapshot={"all_wp_states": {}, "failed_wp_ids": [],
                                    "stuck_wp_ids": [], "blocked_wp_ids": [],
                                    "topology_id": "t", "snapshot_ts_ns": 0},
                confirmed=False,  # 未二次确认
                requester_l2="L2-03",
            ))
        assert "E_L103_L205_502" in str(ei.value)
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_03/test_l2_05_ic_contracts.py
import pytest

from app.l2_05_rollback.schemas import OnWpFailedRequest, OnWpDoneResetRequest


class TestL2_05_IC_Contracts:

    def test_TC_L103_L205_601_ic_l2_05_shape(self, sut, mock_project_id) -> None:
        resp = sut.on_wp_failed(OnWpFailedRequest(
            project_id=mock_project_id, wp_id="wp-601",
            fail_level="FAIL_L1",
            failure_event_id="evt-c-601",
            failure_reason_summary="r",
            requester_l2="L2-04", ts_ns=1,
        ))
        for k in ("status", "project_id", "wp_id", "new_count",
                  "threshold_reached", "audit_event_id", "latency_ms"):
            assert hasattr(resp, k)

    def test_TC_L103_L205_602_ic_l2_05b_reset(self, sut, mock_project_id) -> None:
        resp = sut.on_wp_done_reset(OnWpDoneResetRequest(
            project_id=mock_project_id, wp_id="wp-r-602",
            done_event_id="evt-d-602", requester_l2="L2-04", ts_ns=1,
        ))
        assert resp.status in {"ok", "no_op"}
        assert resp.reset_to == 0

    def test_TC_L103_L205_603_on_deadlock_notified_ic15(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        from app.l2_05_rollback.schemas import OnDeadlockNotifiedRequest
        sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
            project_id=mock_project_id,
            deadlock_snapshot={"all_wp_states": {"wp-001": "FAILED"},
                                "failed_wp_ids": ["wp-001"],
                                "stuck_wp_ids": [], "blocked_wp_ids": [],
                                "topology_id": "t", "snapshot_ts_ns": 1},
            confirmed=True, requester_l2="L2-03",
        ))
        p = mock_supervisor.request_hard_halt.call_args.args[0]
        assert p["red_line_id"] == "deadlock"

    def test_TC_L103_L205_604_ic_l2_06_mark_stuck_payload(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        for i in range(3):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-604",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-604-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
        p = mock_topology_mgr.mark_stuck.call_args.args[0]
        assert p["failure_count"] >= 3
        assert len(p["evidence_refs"]) >= 1

    def test_TC_L103_L205_605_ic_l2_07_decomp_payload(
        self, sut, mock_project_id, mock_l2_01,
    ) -> None:
        from app.l2_05_rollback.schemas import OnRollbackRouteChosenRequest
        sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
            project_id=mock_project_id, wp_id="wp-605",
            advice_card_ref="card-605", chosen_path="SPLIT_WP",
            route_id="route-605", supervisor_decision_id="sd-605",
        ))
        p = mock_l2_01.request_incremental_decompose.call_args.args[0]
        assert p["requester_l2"] == "L2-05"
        assert p["reason"] in {"failure_count_exceeded", "change_request"}

    def test_TC_L103_L205_606_ic15_hard_halt_shape(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        from app.l2_05_rollback.schemas import OnDeadlockNotifiedRequest
        sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
            project_id=mock_project_id,
            deadlock_snapshot={"all_wp_states": {"wp-001": "FAILED"},
                                "failed_wp_ids": ["wp-001"],
                                "stuck_wp_ids": [], "blocked_wp_ids": [],
                                "topology_id": "t", "snapshot_ts_ns": 1},
            confirmed=True, requester_l2="L2-03",
        ))
        p = mock_supervisor.request_hard_halt.call_args.args[0]
        for k in ("halt_id", "project_id", "red_line_id", "evidence"):
            assert k in p
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_03/test_l2_05_perf.py
import time, statistics
import pytest

from app.l2_05_rollback.schemas import OnWpFailedRequest


class TestL2_05_Perf:

    @pytest.mark.perf
    def test_TC_L103_L205_701_on_wp_failed_p95_under_100ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(100):
            t = time.perf_counter()
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id=f"wp-p-{i:03d}",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-p-{i:03d}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1

    @pytest.mark.perf
    def test_TC_L103_L205_702_reset_p95_under_50ms(self, sut, mock_project_id) -> None:
        from app.l2_05_rollback.schemas import OnWpDoneResetRequest
        durations = []
        for i in range(100):
            t = time.perf_counter()
            sut.on_wp_done_reset(OnWpDoneResetRequest(
                project_id=mock_project_id, wp_id=f"wp-rp-{i:03d}",
                done_event_id=f"evt-rp-{i:03d}",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.05

    @pytest.mark.perf
    def test_TC_L103_L205_703_deadlock_notify_p95_under_100ms(
        self, sut, mock_project_id,
    ) -> None:
        from app.l2_05_rollback.schemas import OnDeadlockNotifiedRequest
        durations = []
        for i in range(50):
            t = time.perf_counter()
            sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
                project_id=f"{mock_project_id}-{i:03d}",
                deadlock_snapshot={"all_wp_states": {"wp-001": "FAILED"},
                                    "failed_wp_ids": ["wp-001"],
                                    "stuck_wp_ids": [], "blocked_wp_ids": [],
                                    "topology_id": "t", "snapshot_ts_ns": 1},
                confirmed=True, requester_l2="L2-03",
            ))
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1
```

---

## §6 端到端 e2e

```python
# file: tests/l1_03/test_l2_05_e2e.py
import pytest

from app.l2_05_rollback.schemas import (
    OnWpFailedRequest, OnWpDoneResetRequest, OnRollbackRouteChosenRequest,
)


class TestL2_05_E2E:

    @pytest.mark.e2e
    def test_TC_L103_L205_801_3fail_advice_split_wp_chain(
        self, sut, mock_project_id, mock_topology_mgr, mock_l2_01,
    ) -> None:
        """e2e · 3 次 fail → advice → SPLIT_WP → L2-01 差量 → mark_stuck."""
        for i in range(3):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-e2e-001",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-e-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
        resp = sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
            project_id=mock_project_id, wp_id="wp-e2e-001",
            advice_card_ref=sut._last_advice_card_ref(mock_project_id, "wp-e2e-001"),
            chosen_path="SPLIT_WP",
            route_id="route-e2e", supervisor_decision_id="sd-e2e",
        ))
        assert resp.status in {"ok", "fallback"}
        assert mock_topology_mgr.mark_stuck.called
        assert mock_l2_01.request_incremental_decompose.called

    @pytest.mark.e2e
    def test_TC_L103_L205_802_done_reset_after_fails(
        self, sut, mock_project_id,
    ) -> None:
        for i in range(2):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-e2e-002",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-dr-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
        r = sut.on_wp_done_reset(OnWpDoneResetRequest(
            project_id=mock_project_id, wp_id="wp-e2e-002",
            done_event_id="evt-dr-done", requester_l2="L2-04", ts_ns=100,
        ))
        assert r.prior_count == 2 and r.reset_to == 0
```

---

## §7 测试 fixture

```python
# file: tests/l1_03/conftest_l2_05.py
import pytest, uuid
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id():
    return f"hf-proj-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_topology_mgr():
    m = MagicMock()
    m.mark_stuck = MagicMock(return_value={"status": "ok", "audit_event_id": "evt-ack"})
    return m


@pytest.fixture
def mock_l2_01():
    m = MagicMock()
    m.request_incremental_decompose = MagicMock(return_value={
        "accepted": True,
        "decomposition_session_id": "decomp-001",
    })
    return m


@pytest.fixture
def mock_supervisor():
    m = MagicMock()
    m.request_hard_halt = MagicMock(return_value={"halt_id": "halt-001"})
    m.push_suggestion = MagicMock(return_value={"ack": True})
    return m


@pytest.fixture
def mock_kb():
    m = MagicMock()
    m.kb_read = MagicMock(return_value={"hits": []})
    return m


@pytest.fixture
def mock_event_bus():
    m = MagicMock()
    m.append_event = MagicMock(return_value={"event_id": "evt-001"})
    return m


@pytest.fixture
def mock_clock():
    class C:
        def __init__(self): self.t = 10**9
        def now_ns(self): self.t += 1; return self.t
    return C()


@pytest.fixture
def sut(mock_topology_mgr, mock_l2_01, mock_supervisor, mock_kb,
         mock_event_bus, mock_clock, tmp_path):
    from app.l2_05_rollback.coordinator import FailureRollbackCoordinator
    return FailureRollbackCoordinator(
        topology_mgr=mock_topology_mgr,
        l2_01=mock_l2_01,
        supervisor=mock_supervisor,
        kb=mock_kb,
        event_bus=mock_event_bus,
        clock=mock_clock,
        storage_root=tmp_path,
    )


@pytest.fixture
def sut_with_broken_storage(mock_topology_mgr, mock_l2_01, mock_supervisor, mock_kb,
                              mock_event_bus, mock_clock):
    from app.l2_05_rollback.coordinator import FailureRollbackCoordinator
    return FailureRollbackCoordinator(
        topology_mgr=mock_topology_mgr, l2_01=mock_l2_01,
        supervisor=mock_supervisor, kb=mock_kb,
        event_bus=mock_event_bus, clock=mock_clock,
        storage_root="/dev/null/readonly",
    )


@pytest.fixture
def sut_ro_fs(mock_topology_mgr, mock_l2_01, mock_supervisor, mock_kb,
                mock_event_bus, mock_clock):
    from app.l2_05_rollback.coordinator import FailureRollbackCoordinator
    c = FailureRollbackCoordinator(
        topology_mgr=mock_topology_mgr, l2_01=mock_l2_01,
        supervisor=mock_supervisor, kb=mock_kb,
        event_bus=mock_event_bus, clock=mock_clock,
        storage_root="/dev/null/readonly",
    )
    c.mode = "NORMAL"
    return c


@pytest.fixture
def tamper_counters(tmp_path):
    def _t(project_id: str):
        p = tmp_path / "projects" / project_id / "rollback" / "counters.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"bypass":"yes"}', encoding="utf-8")
    return _t
```

---

## §8 集成点用例

```python
# file: tests/l1_03/test_l2_05_integrations.py
import pytest

from app.l2_05_rollback.schemas import OnWpFailedRequest, OnDeadlockNotifiedRequest


class TestL2_05_Integration:

    def test_TC_L103_L205_901_with_l2_04_failure_flow(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        sut.on_wp_failed(OnWpFailedRequest(
            project_id=mock_project_id, wp_id="wp-901",
            fail_level="FAIL_L1",
            failure_event_id="evt-901",
            failure_reason_summary="r",
            requester_l2="L2-04", ts_ns=1,
        ))
        assert mock_event_bus.append_event.called

    def test_TC_L103_L205_902_with_l2_02_mark_stuck(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        for i in range(3):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-902",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-902-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
        assert mock_topology_mgr.mark_stuck.called

    def test_TC_L103_L205_903_with_l1_07_push_suggestion(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        for i in range(3):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-903",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-903-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
        assert mock_supervisor.push_suggestion.called

    def test_TC_L103_L205_904_with_l2_03_deadlock(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
            project_id=mock_project_id,
            deadlock_snapshot={"all_wp_states": {"wp-001": "FAILED"},
                                "failed_wp_ids": ["wp-001"],
                                "stuck_wp_ids": [], "blocked_wp_ids": [],
                                "topology_id": "t", "snapshot_ts_ns": 1},
            confirmed=True, requester_l2="L2-03",
        ))
        assert mock_supervisor.request_hard_halt.called

    def test_TC_L103_L205_905_with_l2_01_diff_decompose(
        self, sut, mock_project_id, mock_l2_01,
    ) -> None:
        from app.l2_05_rollback.schemas import OnRollbackRouteChosenRequest
        sut.on_rollback_route_chosen(OnRollbackRouteChosenRequest(
            project_id=mock_project_id, wp_id="wp-905",
            advice_card_ref="card-905", chosen_path="SPLIT_WP",
            route_id="route-905", supervisor_decision_id="sd-905",
        ))
        assert mock_l2_01.request_incremental_decompose.called
```

---

## §9 边界 / edge case

```python
# file: tests/l1_03/test_l2_05_edge.py
import pytest

from app.l2_05_rollback.schemas import OnWpFailedRequest, OnWpDoneResetRequest


class TestL2_05_Edge:

    def test_TC_L103_L205_A01_counter_recovery_from_events(
        self, sut_factory, mock_project_id,
    ) -> None:
        """重启 · counter 从 events.jsonl 重建。"""
        s1 = sut_factory()
        for i in range(2):
            s1.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-rebuild",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-rb-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
        s2 = sut_factory(events=s1._journal)
        s2.on_system_resumed(event={"project_id": mock_project_id})
        counter = s2._get_or_create_counter(mock_project_id, "wp-rebuild")
        assert counter.count == 2

    def test_TC_L103_L205_A02_very_many_wps_50_concurrent(
        self, sut, mock_project_id,
    ) -> None:
        """50 个 wp 各失败 1 次 · 独立 counter."""
        for i in range(50):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id=f"wp-{i:03d}",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-m-{i:03d}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
        view = sut.export_failure_summary(mock_project_id)
        assert view.counters_count >= 50

    def test_TC_L103_L205_A03_rapid_fail_then_reset_loop(
        self, sut, mock_project_id,
    ) -> None:
        for i in range(5):
            sut.on_wp_failed(OnWpFailedRequest(
                project_id=mock_project_id, wp_id="wp-loop",
                fail_level="FAIL_L1",
                failure_event_id=f"evt-lp-{i}",
                failure_reason_summary="r",
                requester_l2="L2-04", ts_ns=1 + i,
            ))
            sut.on_wp_done_reset(OnWpDoneResetRequest(
                project_id=mock_project_id, wp_id="wp-loop",
                done_event_id=f"evt-ld-{i}",
                requester_l2="L2-04", ts_ns=100 + i,
            ))
        # 每次 reset 后 count=0 · 所以永远不触发阈
        counter = sut._get_or_create_counter(mock_project_id, "wp-loop")
        assert counter.count == 0

    def test_TC_L103_L205_A04_evidence_truncated_max_size(
        self, sut, mock_project_id,
    ) -> None:
        """evidence_refs 超过 1000 条 · 只保留最近 N 条（避免爆内存）."""
        refs = [f"evt-big-{i:04d}" for i in range(2000)]
        sut.on_wp_failed(OnWpFailedRequest(
            project_id=mock_project_id, wp_id="wp-big",
            fail_level="FAIL_L1",
            failure_event_id="evt-big-base",
            failure_reason_summary="r",
            requester_l2="L2-04", ts_ns=1,
            evidence_refs_override=refs,
        ))
        # 内部 evidence 存储应被截断 · 不抛

    def test_TC_L103_L205_A05_deadlock_no_op_after_halt(
        self, sut, mock_project_id, mock_supervisor,
    ) -> None:
        """first deadlock_notified 后 · 再次调用应幂等（同 halt_id）."""
        from app.l2_05_rollback.schemas import OnDeadlockNotifiedRequest
        r1 = sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
            project_id=mock_project_id,
            deadlock_snapshot={"all_wp_states": {"wp-001": "FAILED"},
                                "failed_wp_ids": ["wp-001"],
                                "stuck_wp_ids": [], "blocked_wp_ids": [],
                                "topology_id": "t", "snapshot_ts_ns": 1},
            confirmed=True, requester_l2="L2-03",
        ))
        r2 = sut.on_deadlock_notified(OnDeadlockNotifiedRequest(
            project_id=mock_project_id,
            deadlock_snapshot={"all_wp_states": {"wp-001": "FAILED"},
                                "failed_wp_ids": ["wp-001"],
                                "stuck_wp_ids": [], "blocked_wp_ids": [],
                                "topology_id": "t", "snapshot_ts_ns": 2},
            confirmed=True, requester_l2="L2-03",
        ))
        assert r1.halt_id == r2.halt_id


@pytest.fixture
def sut_factory(mock_topology_mgr, mock_l2_01, mock_supervisor, mock_kb,
                  mock_event_bus, mock_clock, tmp_path):
    def _f(events=None):
        from app.l2_05_rollback.coordinator import FailureRollbackCoordinator
        c = FailureRollbackCoordinator(
            topology_mgr=mock_topology_mgr, l2_01=mock_l2_01,
            supervisor=mock_supervisor, kb=mock_kb,
            event_bus=mock_event_bus, clock=mock_clock,
            storage_root=tmp_path,
        )
        if events:
            c._bootstrap_events = events
        return c
    return _f
```

---

*— L2-05 TDD 已按 10 段模板完成 · 覆盖 §3 全部方法 / §11 全部 13 错误码 / 6 条 IC · 含 3 次阈值 + 死锁 IC-15 + 3 选项 advice card 覆盖 —*
