---
doc_id: tests-L1-07-L2-06-死循环升级器+回退路由控制器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-07-Harness监督/L2-06-死循环升级器+回退路由控制器.md
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-07 L2-06-死循环升级器+回退路由控制器 · TDD 测试用例

> 基于 3-1 L2-06 §3（10 个对外方法）+ §11（19 项 `L2-06/E01~E19` 错误码）+ §12（detect 300ms / escalation 500ms / delivery 3s SLO）驱动。
> TC ID 统一格式：`TC-L107-L206-NNN`。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例
- [x] §3 负向用例
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × TC 矩阵

| 方法 | TC ID |
|---|---|
| `detect_loop_pattern()` · same_wp_3x | TC-L107-L206-001 |
| `detect_loop_pattern()` · same_phase_5x | TC-L107-L206-002 |
| `detect_loop_pattern()` · verdict_oscillation_3x | TC-L107-L206-003 |
| `detect_loop_pattern()` · supervisor_counter_overflow | TC-L107-L206-004 |
| `classify_loop_type()` · confidence ≥ 0.6 | TC-L107-L206-005 |
| `propose_escalation_decision()` · LIGHT→MEDIUM | TC-L107-L206-006 |
| `propose_escalation_decision()` · HEAVY→CRITICAL | TC-L107-L206-007 |
| `push_block_suggestion()` · HEAVY L1-01 | TC-L107-L206-008 |
| `push_block_suggestion()` · CRITICAL L2-03 | TC-L107-L206-009 |
| `coordinate_with_l2_07_router()` · in_sync | TC-L107-L206-010 |
| `emit_rollback_route()` · FAIL_L4 双保险 | TC-L107-L206-011 |
| `await_user_decision_on_deadlock()` · continue | TC-L107-L206-012 |
| `reset_counters_on_user_decision()` · change_strategy | TC-L107-L206-013 |
| `persist_loop_incident()` · hash-chain | TC-L107-L206-014 |
| `get_loop_incident_history()` · 时间范围 | TC-L107-L206-015 |

### §1.2 错误码 × TC 矩阵（19 项）

| 错误码 | TC ID |
|---|---|
| `L2-06/E01` loop_pattern_unclear | TC-L107-L206-101 |
| `L2-06/E02` counter_sync_failed | TC-L107-L206-102 |
| `L2-06/E03` user_decision_timeout_24h | TC-L107-L206-103 |
| `L2-06/E04` router_mismatch | TC-L107-L206-104 |
| `L2-06/E05` cross_level_jump_rejected | TC-L107-L206-105 |
| `L2-06/E06` delivery_to_l2_04_failed | TC-L107-L206-106 |
| `L2-06/E07` insufficient_evidence_rejected | TC-L107-L206-107 |
| `L2-06/E08` verdict_enum_invalid | TC-L107-L206-108 |
| `L2-06/E09` reset_conflict_with_concurrent_escalation | TC-L107-L206-109 |
| `L2-06/E10` missing_project_id | TC-L107-L206-110 |
| `L2-06/E11` corrupt_event_window | TC-L107-L206-111 |
| `L2-06/E12` pattern_enum_invalid | TC-L107-L206-112 |
| `L2-06/E13` current_level_out_of_range | TC-L107-L206-113 |
| `L2-06/E14` evidence_refs_missing | TC-L107-L206-114 |
| `L2-06/E15` target_resolution_failed | TC-L107-L206-115 |
| `L2-06/E16` router_unreachable | TC-L107-L206-116 |
| `L2-06/E17` from_state_not_s4 | TC-L107-L206-117 |
| `L2-06/E18` ui_alert_card_ack_failed | TC-L107-L206-118 |
| `L2-06/E19` counter_registry_write_failed | TC-L107-L206-119 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-L2-04 escalation_received | L2-05 → L2-06 | TC-L107-L206-601 |
| IC-17 counter_cross_check | L2-06 ↔ L2-07 | TC-L107-L206-602 |
| IC-15 rollback_route | L2-06 → L2-07 | TC-L107-L206-603 |
| IC-09 persist_incident | L2-06 → L1-09 | TC-L107-L206-604 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| detect_loop_pattern P99 | ≤ 300ms | TC-L107-L206-501 |
| propose_escalation P99 | ≤ 500ms | TC-L107-L206-502 |
| emit_rollback_route P99 | ≤ 500ms | TC-L107-L206-503 |
| push_block delivery P99 | ≤ 3s | TC-L107-L206-504 |
| counter_cross_check P99 | ≤ 2s | TC-L107-L206-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_07/test_l2_06_loop_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_06_Positive:

    def test_TC_L107_L206_001_same_wp_3x(self, sut, seed_events) -> None:
        """TC-L107-L206-001 · 同 WP 3 次 FAIL · same_wp_3x。"""
        res = sut.detect_loop_pattern(
            project_id="p", counter_key="wp:WP-42",
            rollback_events_window=seed_events(wp_id="WP-42", count=3,
                                                  level="FAIL_L1"))
        assert res.detected is True
        assert res.pattern == "same_wp_3x"

    def test_TC_L107_L206_002_same_phase_5x(self, sut, seed_events) -> None:
        """TC-L107-L206-002 · 同 phase 5x · same_phase_5x。"""
        res = sut.detect_loop_pattern(
            project_id="p", counter_key="stage:S4",
            rollback_events_window=seed_events(stage="S4", count=5,
                                                  level="FAIL_L2"))
        assert res.pattern == "same_phase_5x"

    def test_TC_L107_L206_003_verdict_oscillation(self, sut, seed_events) -> None:
        """TC-L107-L206-003 · PASS/FAIL 交替 · oscillation。"""
        res = sut.detect_loop_pattern(
            project_id="p", counter_key="wp:W",
            rollback_events_window=seed_events(oscillating=True, count=6))
        assert res.pattern == "verdict_oscillation_3x"

    def test_TC_L107_L206_004_counter_overflow(self, sut, seed_events) -> None:
        """TC-L107-L206-004 · 超过 count_window · overflow。"""
        res = sut.detect_loop_pattern(
            project_id="p", counter_key="wp:W",
            rollback_events_window=seed_events(count=12, level="FAIL_L1"),
            count_window=10)
        assert res.pattern == "supervisor_counter_overflow"

    def test_TC_L107_L206_005_classify_confidence_ok(self, sut) -> None:
        """TC-L107-L206-005 · classify confidence=0.8。"""
        raw = MagicMock(pattern="same_wp_3x", confidence=0.8,
                         matched_events=["e-1"])
        res = sut.classify_loop_type(project_id="p", pattern_raw=raw)
        assert res.classified_pattern == "same_wp_3x"

    def test_TC_L107_L206_006_escalate_light_to_medium(self, sut) -> None:
        """TC-L107-L206-006 · LIGHT → MEDIUM。"""
        res = sut.propose_escalation_decision(
            project_id="p", loop_type="same_wp_3x",
            current_level="LIGHT", counter_key="wp:W",
            evidence=MagicMock(verdict_refs=["v-1"]))
        assert res.escalation_decision.to_level == "MEDIUM"

    def test_TC_L107_L206_007_escalate_heavy_to_critical(self, sut) -> None:
        """TC-L107-L206-007 · HEAVY → CRITICAL → L2-03 hint。"""
        res = sut.propose_escalation_decision(
            project_id="p", loop_type="same_phase_5x",
            current_level="HEAVY", counter_key="wp:W",
            evidence=MagicMock(verdict_refs=["v-1"]))
        assert res.next_action_hint == "push_hard_halt_to_l2_03"

    def test_TC_L107_L206_008_push_heavy_to_l1_01(self, sut, mock_l2_04) -> None:
        """TC-L107-L206-008 · HEAVY 推 L1-01。"""
        dec = MagicMock(to_level="HEAVY", evidence_refs=[])
        res = sut.push_block_suggestion_to_l1_07_or_l1_01(
            project_id="p", escalation_decision=dec,
            target="l1_01_main_loop")
        assert res.delivered_to in ("l2_04_router", "direct_fallback")

    def test_TC_L107_L206_009_push_critical_to_l2_03(self, sut, mock_l2_04) -> None:
        """TC-L107-L206-009 · CRITICAL 推 L2-03。"""
        dec = MagicMock(to_level="CRITICAL", evidence_refs=[])
        res = sut.push_block_suggestion_to_l1_07_or_l1_01(
            project_id="p", escalation_decision=dec,
            target="l2_03_hard_red_line")
        assert res.delivery_id is not None

    def test_TC_L107_L206_010_coordinate_in_sync(self, sut, mock_l2_07) -> None:
        """TC-L107-L206-010 · drift=0 · in_sync。"""
        mock_l2_07.get_counter.return_value = 3
        res = sut.coordinate_with_l2_07_router(
            project_id="p", counter_key="wp:W",
            supervisor_side_count=3, expected_router_side_count=3)
        assert res.cross_check_status == "in_sync"

    def test_TC_L107_L206_011_fail_l4_double_insurance(self, sut) -> None:
        """TC-L107-L206-011 · FAIL_L4 双保险。"""
        vr = MagicMock(verdict="FAIL_L4", verdict_id="v-L4",
                        from_state="S4", verifier_report_ref="r-1")
        res = sut.emit_rollback_route(project_id="p", verifier_verdict=vr)
        assert res.double_insurance.triggered is True

    def test_TC_L107_L206_012_await_continue(self, sut, mock_ui) -> None:
        """TC-L107-L206-012 · 用户 continue。"""
        mock_ui.await_user_decision.return_value = MagicMock(
            decision="continue", decided_at="t")
        dec = sut.await_user_decision_on_deadlock(
            project_id="p", escalation_decision=MagicMock(),
            timeout_hours=24)
        assert dec.decision == "continue"

    def test_TC_L107_L206_013_reset_change_strategy(self, sut) -> None:
        """TC-L107-L206-013 · change_strategy · 全重置。"""
        sut._counter_buckets["wp:A"] = 3
        sut.reset_counters_on_user_decision(
            project_id="p",
            decision=MagicMock(decision="change_strategy"))
        assert sut._counter_buckets.get("wp:A", 0) == 0

    def test_TC_L107_L206_014_persist_hash_chain(
        self, sut, make_incident,
    ) -> None:
        """TC-L107-L206-014 · hash-chain。"""
        h1 = sut.persist_loop_incident(project_id="p",
                                         incident_payload=make_incident())
        h2 = sut.persist_loop_incident(project_id="p",
                                         incident_payload=make_incident())
        assert h1 != h2

    def test_TC_L107_L206_015_history_query(self, sut, make_incident) -> None:
        """TC-L107-L206-015 · 按时间查询。"""
        sut.persist_loop_incident(project_id="p",
                                    incident_payload=make_incident())
        hist = sut.get_loop_incident_history(
            project_id="p", since_ts="2026-04-22T00:00:00Z",
            until_ts="2026-04-23T00:00:00Z")
        assert len(hist) >= 1
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_07/test_l2_06_loop_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_07.l2_06.errors import LoopError


class TestL2_06_Negative:

    def test_TC_L107_L206_101_pattern_unclear(self, sut, seed_events) -> None:
        """TC-L107-L206-101 · E01 · confidence < 0.6 · INFO 降级。"""
        res = sut.detect_loop_pattern(
            project_id="p", counter_key="wp:W",
            rollback_events_window=seed_events(count=2, level="FAIL_L1"))
        assert res.confidence < 0.6
        assert res.pattern is None

    def test_TC_L107_L206_102_counter_sync_failed(self, sut, mock_l2_07) -> None:
        """TC-L107-L206-102 · E02 · cross_check 失败 · 重试 1 次后拒。"""
        mock_l2_07.get_counter.side_effect = TimeoutError("sync")
        with pytest.raises(LoopError) as exc:
            sut.coordinate_with_l2_07_router(
                project_id="p", counter_key="wp:W",
                supervisor_side_count=3, expected_router_side_count=3)
        assert exc.value.code == "L2-06/E02"

    def test_TC_L107_L206_103_user_timeout_24h_halt(self, sut, mock_ui) -> None:
        """TC-L107-L206-103 · E03 · 24h 无响应 · HALT_PROJECT_CONSERVATIVE。"""
        mock_ui.await_user_decision.side_effect = TimeoutError("24h")
        dec = sut.await_user_decision_on_deadlock(
            project_id="p", escalation_decision=MagicMock(),
            timeout_hours=24)
        assert dec.decision == "timeout" or dec.halt_action == "HALT_PROJECT_CONSERVATIVE"

    def test_TC_L107_L206_104_router_mismatch(self, sut, mock_l2_07) -> None:
        """TC-L107-L206-104 · E04 · drift > 1 · 拒升级 + 报警。"""
        mock_l2_07.get_counter.return_value = 5
        with pytest.raises(LoopError) as exc:
            sut.coordinate_with_l2_07_router(
                project_id="p", counter_key="wp:W",
                supervisor_side_count=3, expected_router_side_count=3)
        assert exc.value.code == "L2-06/E04"

    def test_TC_L107_L206_105_cross_level_jump_rejected(self, sut) -> None:
        """TC-L107-L206-105 · E05 · LIGHT → HEAVY 跨级 · 拒。"""
        with pytest.raises(LoopError) as exc:
            sut.propose_escalation_decision(
                project_id="p", loop_type="same_wp_3x",
                current_level="LIGHT", counter_key="wp:W",
                evidence=MagicMock(verdict_refs=["v"]),
                requested_to_level="HEAVY")
        assert exc.value.code == "L2-06/E05"

    def test_TC_L107_L206_106_delivery_fail_fallback(self, sut, mock_l2_04) -> None:
        """TC-L107-L206-106 · E06 · L2-04 不可达 · 降级直连 L2-03。"""
        mock_l2_04.dispatch.side_effect = ConnectionError("L2-04")
        dec = MagicMock(to_level="CRITICAL", evidence_refs=[])
        res = sut.push_block_suggestion_to_l1_07_or_l1_01(
            project_id="p", escalation_decision=dec,
            target="l2_03_hard_red_line")
        assert res.delivered_to == "direct_fallback"

    def test_TC_L107_L206_107_insufficient_evidence_rejected(self, sut) -> None:
        """TC-L107-L206-107 · E07 · INSUFFICIENT_EVIDENCE · 拒路由。"""
        vr = MagicMock(verdict="INSUFFICIENT_EVIDENCE",
                        verdict_id="v-ie", from_state="S4")
        with pytest.raises(LoopError) as exc:
            sut.emit_rollback_route(project_id="p", verifier_verdict=vr)
        assert exc.value.code == "L2-06/E07"

    def test_TC_L107_L206_108_verdict_enum_invalid(self, sut) -> None:
        """TC-L107-L206-108 · E08 · verdict=FAIL_L99 · 拒。"""
        vr = MagicMock(verdict="FAIL_L99", verdict_id="v", from_state="S4")
        with pytest.raises(LoopError) as exc:
            sut.emit_rollback_route(project_id="p", verifier_verdict=vr)
        assert exc.value.code == "L2-06/E08"

    def test_TC_L107_L206_109_reset_concurrent_conflict(self, sut) -> None:
        """TC-L107-L206-109 · E09 · 并发升级与 reset · 延后。"""
        sut._concurrent_escalation_in_flight = True
        with pytest.raises(LoopError) as exc:
            sut.reset_counters_on_user_decision(
                project_id="p",
                decision=MagicMock(decision="change_strategy"))
        assert exc.value.code == "L2-06/E09"

    def test_TC_L107_L206_110_missing_project_id(self, sut, seed_events) -> None:
        """TC-L107-L206-110 · E10 · project_id 缺。"""
        with pytest.raises(LoopError) as exc:
            sut.detect_loop_pattern(project_id=None, counter_key="wp:W",
                                     rollback_events_window=seed_events(count=3))
        assert exc.value.code == "L2-06/E10"

    def test_TC_L107_L206_111_corrupt_event_window(self, sut) -> None:
        """TC-L107-L206-111 · E11 · 事件窗口损坏。"""
        with pytest.raises(LoopError) as exc:
            sut.detect_loop_pattern(project_id="p", counter_key="wp:W",
                                     rollback_events_window="not-a-list")
        assert exc.value.code == "L2-06/E11"

    def test_TC_L107_L206_112_pattern_enum_invalid(self, sut) -> None:
        """TC-L107-L206-112 · E12 · pattern 不在 4 类。"""
        raw = MagicMock(pattern="UNKNOWN_PATTERN", confidence=0.9)
        with pytest.raises(LoopError) as exc:
            sut.classify_loop_type(project_id="p", pattern_raw=raw)
        assert exc.value.code == "L2-06/E12"

    def test_TC_L107_L206_113_current_level_out_of_range(self, sut) -> None:
        """TC-L107-L206-113 · E13 · current_level=UNKNOWN。"""
        with pytest.raises(LoopError) as exc:
            sut.propose_escalation_decision(
                project_id="p", loop_type="same_wp_3x",
                current_level="UNKNOWN_LEVEL", counter_key="wp:W",
                evidence=MagicMock(verdict_refs=["v"]))
        assert exc.value.code == "L2-06/E13"

    def test_TC_L107_L206_114_evidence_missing(self, sut) -> None:
        """TC-L107-L206-114 · E14 · 无 evidence 升级。"""
        with pytest.raises(LoopError) as exc:
            sut.propose_escalation_decision(
                project_id="p", loop_type="same_wp_3x",
                current_level="LIGHT", counter_key="wp:W",
                evidence=MagicMock(verdict_refs=[]))
        assert exc.value.code == "L2-06/E14"

    def test_TC_L107_L206_115_target_resolution_failed(self, sut) -> None:
        """TC-L107-L206-115 · E15 · target 解析失败。"""
        with pytest.raises(LoopError) as exc:
            sut.push_block_suggestion_to_l1_07_or_l1_01(
                project_id="p", escalation_decision=MagicMock(),
                target="INVALID_TARGET")
        assert exc.value.code == "L2-06/E15"

    def test_TC_L107_L206_116_router_unreachable_single_side(
        self, sut, mock_l2_07,
    ) -> None:
        """TC-L107-L206-116 · E16 · L2-07 长不可达 · 降级 supervisor 单边 + WARN。"""
        mock_l2_07.get_counter.side_effect = [ConnectionError()] * 5
        res = sut.coordinate_with_l2_07_router(
            project_id="p", counter_key="wp:W",
            supervisor_side_count=3, expected_router_side_count=3,
            single_side_fallback=True)
        assert res.cross_check_status == "drift_intolerable" or \
               res.single_side_mode is True

    def test_TC_L107_L206_117_from_state_not_s4(self, sut) -> None:
        """TC-L107-L206-117 · E17 · rollback 源 state ≠ S4 · 拒。"""
        vr = MagicMock(verdict="FAIL_L2", verdict_id="v",
                        from_state="S2", verifier_report_ref="r")
        with pytest.raises(LoopError) as exc:
            sut.emit_rollback_route(project_id="p", verifier_verdict=vr)
        assert exc.value.code == "L2-06/E17"

    def test_TC_L107_L206_118_ui_ack_failed(self, sut, mock_ui) -> None:
        """TC-L107-L206-118 · E18 · UI ack 失败。"""
        mock_ui.emit_alert_card.side_effect = ConnectionError("UI")
        with pytest.raises(LoopError) as exc:
            sut._push_alert_card_to_ui(project_id="p",
                                         escalation_decision=MagicMock())
        assert exc.value.code == "L2-06/E18"

    def test_TC_L107_L206_119_counter_registry_write_failed(
        self, sut, monkeypatch,
    ) -> None:
        """TC-L107-L206-119 · E19 · counter 注册表写失败。"""
        def boom(*a, **kw): raise IOError("registry")
        monkeypatch.setattr(sut, "_write_counter_registry", boom)
        with pytest.raises(LoopError) as exc:
            sut.reset_counters_on_user_decision(
                project_id="p",
                decision=MagicMock(decision="change_strategy"))
        assert exc.value.code == "L2-06/E19"
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_07/test_l2_06_loop_ic.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_06_IC_Contracts:

    def test_TC_L107_L206_601_escalation_from_l2_05(self, sut) -> None:
        """TC-L107-L206-601 · IC-L2-04 · L2-05 escalate 触发 L2-06。"""
        res = sut.on_escalation_signal(
            project_id="p", loop_type="same_wp_3x",
            current_level="LIGHT", counter_key="wp:W",
            evidence=MagicMock(verdict_refs=["v"]))
        assert res.escalation_decision is not None

    def test_TC_L107_L206_602_counter_cross_check_ic_17(
        self, sut, mock_l2_07,
    ) -> None:
        """TC-L107-L206-602 · IC-17 · counter_cross_check。"""
        mock_l2_07.get_counter.return_value = 3
        res = sut.coordinate_with_l2_07_router(
            project_id="p", counter_key="wp:W",
            supervisor_side_count=3, expected_router_side_count=3)
        mock_l2_07.get_counter.assert_called()
        assert res.cross_check_status is not None

    def test_TC_L107_L206_603_rollback_ic_15(self, sut, mock_l2_07) -> None:
        """TC-L107-L206-603 · IC-15 · rollback_route 发给 L2-07。"""
        vr = MagicMock(verdict="FAIL_L2", verdict_id="v",
                        from_state="S4", verifier_report_ref="r")
        res = sut.emit_rollback_route(project_id="p", verifier_verdict=vr)
        assert res.rollback_route is not None

    def test_TC_L107_L206_604_ic_09_audit(
        self, sut, mock_audit, make_incident,
    ) -> None:
        """TC-L107-L206-604 · IC-09 audit 落盘。"""
        sut.persist_loop_incident(project_id="p",
                                    incident_payload=make_incident())
        assert mock_audit.append.called
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_07/test_l2_06_loop_perf.py
from __future__ import annotations

import pytest
import time


@pytest.mark.perf
class TestL2_06_SLO:

    def test_TC_L107_L206_501_detect_p99_le_300ms(
        self, sut, seed_events, benchmark,
    ) -> None:
        """TC-L107-L206-501 · detect P99 ≤ 300ms。"""
        events = seed_events(count=10, level="FAIL_L1")
        benchmark.pedantic(
            sut.detect_loop_pattern,
            kwargs={"project_id": "p", "counter_key": "wp:W",
                    "rollback_events_window": events},
            iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 300.0

    def test_TC_L107_L206_502_escalation_p99_le_500ms(
        self, sut, benchmark,
    ) -> None:
        """TC-L107-L206-502 · escalation P99 ≤ 500ms。"""
        from unittest.mock import MagicMock
        benchmark.pedantic(
            sut.propose_escalation_decision,
            kwargs={"project_id": "p", "loop_type": "same_wp_3x",
                    "current_level": "LIGHT", "counter_key": "wp:W",
                    "evidence": MagicMock(verdict_refs=["v"])},
            iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 500.0

    def test_TC_L107_L206_503_rollback_p99_le_500ms(
        self, sut, benchmark,
    ) -> None:
        """TC-L107-L206-503 · rollback P99 ≤ 500ms。"""
        from unittest.mock import MagicMock
        vr = MagicMock(verdict="FAIL_L2", verdict_id="v",
                        from_state="S4", verifier_report_ref="r")
        benchmark.pedantic(
            sut.emit_rollback_route,
            kwargs={"project_id": "p", "verifier_verdict": vr},
            iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 500.0

    def test_TC_L107_L206_504_delivery_p99_le_3s(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L206-504 · delivery P99 ≤ 3s。"""
        from unittest.mock import MagicMock
        samples = []
        for _ in range(30):
            t0 = time.perf_counter()
            sut.push_block_suggestion_to_l1_07_or_l1_01(
                project_id="p",
                escalation_decision=MagicMock(to_level="HEAVY",
                                                evidence_refs=[]),
                target="l1_01_main_loop")
            samples.append(time.perf_counter() - t0)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99) - 1]
        assert p99 <= 3.0

    def test_TC_L107_L206_505_cross_check_p99_le_2s(
        self, sut, mock_l2_07, benchmark,
    ) -> None:
        """TC-L107-L206-505 · cross_check P99 ≤ 2s。"""
        mock_l2_07.get_counter.return_value = 3
        benchmark.pedantic(
            sut.coordinate_with_l2_07_router,
            kwargs={"project_id": "p", "counter_key": "wp:W",
                    "supervisor_side_count": 3,
                    "expected_router_side_count": 3},
            iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p99"] <= 2.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_07/test_l2_06_loop_e2e.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


@pytest.mark.e2e
class TestL2_06_E2E:

    def test_TC_L107_L206_701_detect_escalate_deliver(
        self, sut, seed_events, mock_l2_04, mock_audit,
    ) -> None:
        """TC-L107-L206-701 · detect → classify → escalate → deliver。"""
        events = seed_events(wp_id="WP-E2E", count=3, level="FAIL_L1")
        p = sut.detect_loop_pattern(project_id="p", counter_key="wp:WP-E2E",
                                      rollback_events_window=events)
        cls = sut.classify_loop_type(project_id="p",
                                       pattern_raw=MagicMock(
                                           pattern=p.pattern,
                                           confidence=p.confidence or 0.8,
                                           matched_events=p.matched_events))
        esc = sut.propose_escalation_decision(
            project_id="p", loop_type=cls.classified_pattern,
            current_level="LIGHT", counter_key="wp:WP-E2E",
            evidence=MagicMock(verdict_refs=["v"]))
        sut.push_block_suggestion_to_l1_07_or_l1_01(
            project_id="p",
            escalation_decision=esc.escalation_decision,
            target="l1_01_main_loop")
        assert mock_audit.append.called or mock_l2_04.dispatch.called

    def test_TC_L107_L206_702_fail_l4_full_rollback_flow(
        self, sut, mock_l2_07,
    ) -> None:
        """TC-L107-L206-702 · FAIL_L4 · emit_rollback → 双保险 → 回退 S1。"""
        vr = MagicMock(verdict="FAIL_L4", verdict_id="v-L4",
                        from_state="S4", verifier_report_ref="r")
        res = sut.emit_rollback_route(project_id="p", verifier_verdict=vr)
        assert res.double_insurance.triggered is True

    def test_TC_L107_L206_703_user_decision_abort_flow(
        self, sut, mock_ui,
    ) -> None:
        """TC-L107-L206-703 · 升 CRITICAL · 用户 abort · 标 ABORTED。"""
        mock_ui.await_user_decision.return_value = MagicMock(
            decision="abort", decided_at="t")
        dec = sut.await_user_decision_on_deadlock(
            project_id="p", escalation_decision=MagicMock(), timeout_hours=24)
        sut.reset_counters_on_user_decision(project_id="p", decision=dec)
        assert dec.decision == "abort"
```

---

## §7 测试 fixture

```python
# file: tests/l1_07/conftest_l2_06.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_07.l2_06.service import LoopEscalator


@pytest.fixture
def mock_l2_04() -> MagicMock:
    m = MagicMock()
    m.dispatch.return_value = MagicMock(dispatched=True,
                                         delivery_id="d-1")
    return m


@pytest.fixture
def mock_l2_07() -> MagicMock:
    m = MagicMock()
    m.get_counter.return_value = 3
    return m


@pytest.fixture
def mock_ui() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_l2_04, mock_l2_07, mock_ui, mock_audit):
    return LoopEscalator(
        l2_04=mock_l2_04, l2_07=mock_l2_07, ui=mock_ui,
        audit=mock_audit,
    )


@pytest.fixture
def seed_events():
    def _seed(wp_id: str = "WP-X", stage: str = "S4",
              count: int = 3, level: str = "FAIL_L1",
              oscillating: bool = False):
        events = []
        for i in range(count):
            verdict = level
            if oscillating:
                verdict = "PASS" if i % 2 else level
            events.append({
                "event_id": f"e-{i}",
                "event_type": "rollback_route_issued",
                "verdict_level": verdict,
                "timestamp": f"2026-04-22T10:{i:02d}:00Z",
                "wp_id": wp_id,
                "stage": stage,
            })
        return events
    return _seed


@pytest.fixture
def make_incident():
    def _make():
        return {
            "incident_id": "inc-1",
            "project_id": "p",
            "pattern": "same_wp_3x",
            "to_level": "MEDIUM",
            "created_at": "2026-04-22T10:00:00Z",
            "evidence_refs": ["e-1", "e-2", "e-3"],
        }
    return _make
```

---

## §8 集成点用例

```python
# file: tests/l1_07/test_l2_06_integration.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_06_Integration:

    def test_TC_L107_L206_801_with_l2_05_soft_escalation(
        self, sut,
    ) -> None:
        """TC-L107-L206-801 · L2-05 软红线 counter=3 触发升级。"""
        res = sut.on_escalation_signal(
            project_id="p", loop_type="soft:context_overflow",
            current_level="LIGHT", counter_key="soft:context_overflow",
            evidence=MagicMock(verdict_refs=["v"]))
        assert res.escalation_decision is not None

    def test_TC_L107_L206_802_with_l2_07_counter_sync(
        self, sut, mock_l2_07,
    ) -> None:
        """TC-L107-L206-802 · L2-07 counter sync 稳定。"""
        mock_l2_07.get_counter.return_value = 2
        res = sut.coordinate_with_l2_07_router(
            project_id="p", counter_key="wp:W",
            supervisor_side_count=2, expected_router_side_count=2)
        assert res.cross_check_status == "in_sync"
```

---

## §9 边界 / edge case

```python
# file: tests/l1_07/test_l2_06_edge.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_06_Edge:

    def test_TC_L107_L206_901_empty_event_window(self, sut) -> None:
        """TC-L107-L206-901 · 空 event 窗口 · detected=False。"""
        res = sut.detect_loop_pattern(project_id="p", counter_key="wp:W",
                                         rollback_events_window=[])
        assert res.detected is False

    def test_TC_L107_L206_902_drift_exactly_1_tolerable(
        self, sut, mock_l2_07,
    ) -> None:
        """TC-L107-L206-902 · drift=1 边界 · tolerable。"""
        mock_l2_07.get_counter.return_value = 3
        res = sut.coordinate_with_l2_07_router(
            project_id="p", counter_key="wp:W",
            supervisor_side_count=4, expected_router_side_count=3)
        assert res.cross_check_status == "drift_tolerable"

    def test_TC_L107_L206_903_concurrent_escalation_same_pid(
        self, sut,
    ) -> None:
        """TC-L107-L206-903 · 同 pid 并发 5 次 · 序列化。"""
        import threading
        results = []
        def _run(i):
            results.append(sut.propose_escalation_decision(
                project_id="p", loop_type="same_wp_3x",
                current_level="LIGHT", counter_key="wp:W",
                evidence=MagicMock(verdict_refs=[f"v-{i}"])))
        ts = [threading.Thread(target=_run, args=(i,)) for i in range(5)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert len(results) == 5

    def test_TC_L107_L206_904_hard_block_forever(self, sut) -> None:
        """TC-L107-L206-904 · HARD_BLOCK 状态 · 不再升级。"""
        res = sut.propose_escalation_decision(
            project_id="p", loop_type="same_wp_3x",
            current_level="HARD_BLOCK", counter_key="wp:W",
            evidence=MagicMock(verdict_refs=["v"]))
        assert res.next_action_hint == "trigger_aborted"

    def test_TC_L107_L206_905_rollback_from_s5_not_s4_reject(
        self, sut,
    ) -> None:
        """TC-L107-L206-905 · rollback from S5 · 契约违规 E17。"""
        from app.l1_07.l2_06.errors import LoopError
        vr = MagicMock(verdict="FAIL_L1", verdict_id="v",
                        from_state="S5", verifier_report_ref="r")
        with pytest.raises(LoopError) as exc:
            sut.emit_rollback_route(project_id="p", verifier_verdict=vr)
        assert exc.value.code == "L2-06/E17"
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
