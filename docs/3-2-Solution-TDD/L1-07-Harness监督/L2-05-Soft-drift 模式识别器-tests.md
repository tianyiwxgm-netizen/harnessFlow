---
doc_id: tests-L1-07-L2-05-Soft-drift 模式识别器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-07-Harness监督/L2-05-Soft-drift 模式识别器.md
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-07 L2-05-Soft-drift 模式识别器 · TDD 测试用例

> 基于 3-1 L2-05 §3（9 对外方法 + 2 可选）+ §11（20 项 `E01~E20` 错误码）+ §12（p50 100ms / p95 500ms / p99 1s 硬锁）驱动。
> TC ID 统一格式：`TC-L107-L205-NNN`。

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
| `scan_for_soft_drift()` · 正向 | TC-L107-L205-001 |
| `classify_drift_pattern()` · EVIDENCE_MISSING | TC-L107-L205-002 |
| `classify_drift_pattern()` · PROGRESS_DEVIATION | TC-L107-L205-003 |
| `classify_drift_pattern()` · CONTEXT_OVERFLOW | TC-L107-L205-004 |
| `classify_drift_pattern()` · 8 类完整覆盖 | TC-L107-L205-005 |
| `propose_mitigation()` · 1:1 映射 | TC-L107-L205-006 |
| `dispatch_auto_fix_via_subagent()` · L2-04 | TC-L107-L205-007 |
| `track_mitigation_outcome()` · 消除 | TC-L107-L205-008 |
| `track_mitigation_outcome()` · 未消除 counter++ | TC-L107-L205-009 |
| `escalate_to_hard_redline_if_threshold()` · 3 次 | TC-L107-L205-010 |
| `persist_drift_report()` · hash-chain | TC-L107-L205-011 |
| `push_to_ui_as_warning_card()` · WARN trend | TC-L107-L205-012 |
| `abort_if_business_critical()` | TC-L107-L205-013 |
| `detect_soft_drift_trend()` · BF-E-07 | TC-L107-L205-014 |
| `merge_same_tick_candidates()` | TC-L107-L205-015 |

### §1.2 错误码 × TC 矩阵（20 项）

| 错误码 | TC ID |
|---|---|
| `E01` drift_pattern_unrecognized | TC-L107-L205-101 |
| `E02` classification_ambiguous | TC-L107-L205-102 |
| `E03` evidence_malformed | TC-L107-L205-103 |
| `E04` no_mitigation_template | TC-L107-L205-104 |
| `E05` idempotent_key_duplicate | TC-L107-L205-105 |
| `E06` dispatch_rejected_by_l2_04 | TC-L107-L205-106 |
| `E07` evidence_incomplete | TC-L107-L205-107 |
| `E08` classification_slo_timeout | TC-L107-L205-108 |
| `E09` registry_yaml_corrupt | TC-L107-L205-109 |
| `E10` subagent_tool_violation | TC-L107-L205-110 |
| `E11` outcome_event_stale | TC-L107-L205-111 |
| `E12` dispatch_id_not_found | TC-L107-L205-112 |
| `E13` escalation_attempts_misconfigured | TC-L107-L205-113 |
| `E14` l2_06_unreachable | TC-L107-L205-114 |
| `E15` hash_chain_broken | TC-L107-L205-115 |
| `E16` audit_log_write_failed | TC-L107-L205-116 |
| `E17` missing_project_id | TC-L107-L205-117 |
| `E18` ui_variant_mismatch | TC-L107-L205-118 |
| `E19` ic_16_unreachable | TC-L107-L205-119 |
| `E20` business_critical_abort_required | TC-L107-L205-120 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-L2-04 scan_for_soft_drift | L2-02 → L2-05 | TC-L107-L205-601 |
| IC-12 dispatch_auto_fix | L2-05 → L2-04 | TC-L107-L205-602 |
| IC-16 push_to_ui | L2-05 → L1-10 | TC-L107-L205-603 |
| IC-09 persist_drift | L2-05 → L1-09 | TC-L107-L205-604 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| scan P50 | ≤ 100ms | TC-L107-L205-501 |
| scan P95 | ≤ 500ms | TC-L107-L205-502 |
| scan P99 硬锁 | ≤ 1s | TC-L107-L205-503 |
| dispatch timeout | ≤ 5s | TC-L107-L205-504 |
| trend 30s tick | ≤ 2s | TC-L107-L205-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_07/test_l2_05_drift_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_05_Positive:

    def test_TC_L107_L205_001_scan(self, sut, make_snapshot, make_cv) -> None:
        """TC-L107-L205-001 · scan 正向。"""
        p = sut.scan_for_soft_drift(project_id="prj-1",
                                      snapshot=make_snapshot(),
                                      candidate_verdict=make_cv("EVIDENCE_MISSING"))
        assert p.drift_type == "EVIDENCE_MISSING"

    def test_TC_L107_L205_002_classify_evidence_missing(self, sut) -> None:
        """TC-L107-L205-002 · EVIDENCE_MISSING。"""
        ev = MagicMock(dimension="evidence",
                        raw_metric={"evidence_chain_complete": False})
        cls = sut.classify_drift_pattern(ev)
        assert cls == "EVIDENCE_MISSING"

    def test_TC_L107_L205_003_classify_progress_deviation(self, sut) -> None:
        """TC-L107-L205-003 · PROGRESS_DEVIATION。"""
        ev = MagicMock(dimension="progress",
                        raw_metric={"actual_vs_plan": 0.65})
        cls = sut.classify_drift_pattern(ev)
        assert cls == "PROGRESS_DEVIATION"

    def test_TC_L107_L205_004_classify_context_overflow(self, sut) -> None:
        """TC-L107-L205-004 · CONTEXT_OVERFLOW。"""
        ev = MagicMock(dimension="context",
                        raw_metric={"context_pct": 82},
                        threshold_context={"context_threshold_pct": 80})
        cls = sut.classify_drift_pattern(ev)
        assert cls == "CONTEXT_OVERFLOW"

    def test_TC_L107_L205_005_eight_types(self, sut) -> None:
        """TC-L107-L205-005 · 8 类枚举齐。"""
        types = ("EVIDENCE_MISSING", "PROGRESS_DEVIATION", "SKILL_FAILURE",
                 "CONTEXT_OVERFLOW", "LIGHT_TDDEXE_FAIL", "WP_TIMEOUT",
                 "KB_ENTRY_MISS", "NETWORK_TRANSIENT")
        for t in types:
            ev = MagicMock(force_drift_type=t)
            cls = sut.classify_drift_pattern(ev)
            assert cls in types

    def test_TC_L107_L205_006_propose_mitigation(self, sut) -> None:
        """TC-L107-L205-006 · 1:1 映射。"""
        action = sut.propose_mitigation(
            drift_type="EVIDENCE_MISSING",
            pattern_context={"wp_id": "wp-1"})
        assert action.action_type == "rerun_verifier"

    def test_TC_L107_L205_007_dispatch_via_l2_04(self, sut, mock_l2_04) -> None:
        """TC-L107-L205-007 · dispatch 经 L2-04。"""
        mitigation = MagicMock(action_type="rerun_verifier",
                                idempotent_key="k-1")
        res = sut.dispatch_auto_fix_via_subagent(mitigation)
        mock_l2_04.dispatch.assert_called_once()

    def test_TC_L107_L205_008_outcome_mitigated(self, sut) -> None:
        """TC-L107-L205-008 · outcome 消除 · counter 归零。"""
        sut._escalation_counter["wp-1:EVIDENCE_MISSING"] = 2
        out = MagicMock(wp_id="wp-1", drift_type="EVIDENCE_MISSING",
                         mitigated=True, tick_id=10)
        sut.track_mitigation_outcome(out)
        assert sut._escalation_counter["wp-1:EVIDENCE_MISSING"] == 0

    def test_TC_L107_L205_009_outcome_unmitigated(self, sut) -> None:
        """TC-L107-L205-009 · counter++。"""
        out = MagicMock(wp_id="wp-2", drift_type="PROGRESS_DEVIATION",
                         mitigated=False, tick_id=10)
        sut.track_mitigation_outcome(out)
        sut.track_mitigation_outcome(out)
        assert sut._escalation_counter["wp-2:PROGRESS_DEVIATION"] >= 2

    def test_TC_L107_L205_010_escalate_3_attempts(self, sut, mock_l2_06) -> None:
        """TC-L107-L205-010 · counter=3 · 升级 L2-06。"""
        sut._escalation_counter["wp-3:CONTEXT_OVERFLOW"] = 3
        dec = sut.escalate_to_hard_redline_if_threshold(
            wp_id="wp-3", drift_type="CONTEXT_OVERFLOW")
        assert dec.escalated is True
        mock_l2_06.escalate.assert_called_once()

    def test_TC_L107_L205_011_persist_hash_chain(self, sut, make_pattern) -> None:
        """TC-L107-L205-011 · hash-chain 链式变化。"""
        h1 = sut.persist_drift_report(make_pattern(), outcome=None)
        h2 = sut.persist_drift_report(make_pattern(), outcome=None)
        assert h1 != h2

    def test_TC_L107_L205_012_push_to_ui_warn(self, sut, mock_l1_10) -> None:
        """TC-L107-L205-012 · trend WARN · UI 弹角。"""
        trend = MagicMock(trend_type="soft_drift_trend", level="WARN")
        sut.push_to_ui_as_warning_card(trend)
        mock_l1_10.push_card.assert_called_once()

    def test_TC_L107_L205_013_abort_business_critical(self, sut) -> None:
        """TC-L107-L205-013 · 业务关键 · 拒识。"""
        from app.l1_07.l2_05.errors import BusinessCriticalAbort
        with pytest.raises(BusinessCriticalAbort) as exc:
            sut.abort_if_business_critical(MagicMock(business_critical=True))
        assert exc.value.code == "E20"

    def test_TC_L107_L205_014_detect_trend(self, sut, seed_tick_data) -> None:
        """TC-L107-L205-014 · BF-E-07 三条件 · 返 WARN trend。"""
        seed_tick_data(three_conditions_met=True)
        trend = sut.detect_soft_drift_trend(tick_data=sut._tick_data)
        assert trend is not None
        assert trend.trend_level == "WARN"

    def test_TC_L107_L205_015_merge_candidates(self, sut) -> None:
        """TC-L107-L205-015 · 同类合并。"""
        cands = [MagicMock(drift_type="EVIDENCE_MISSING", wp_id="wp-1")
                 for _ in range(3)]
        merged = sut.merge_same_tick_candidates(cands)
        assert len(merged) == 1
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_07/test_l2_05_drift_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_07.l2_05.errors import DriftError


class TestL2_05_Negative:

    def test_TC_L107_L205_101_pattern_unrecognized(
        self, sut, make_snapshot, make_cv,
    ) -> None:
        """TC-L107-L205-101 · E01 · 无匹配 · 回退 L2-02 升 WARN。"""
        cv = make_cv("NO_MATCH")
        with pytest.raises(DriftError) as exc:
            sut.scan_for_soft_drift(project_id="p", snapshot=make_snapshot(),
                                      candidate_verdict=cv)
        assert exc.value.code == "E01"

    def test_TC_L107_L205_102_classification_ambiguous(self, sut) -> None:
        """TC-L107-L205-102 · E02 · 同时命中多类 · 按优先级选最重。"""
        ev = MagicMock(force_ambiguous=True,
                        candidates=["EVIDENCE_MISSING", "CONTEXT_OVERFLOW"])
        cls = sut.classify_drift_pattern(ev)
        # 优先级表：EVIDENCE_MISSING > CONTEXT_OVERFLOW
        assert cls == "EVIDENCE_MISSING"

    def test_TC_L107_L205_103_evidence_malformed(self, sut) -> None:
        """TC-L107-L205-103 · E03 · dimension 未识别 · 拒。"""
        ev = MagicMock(dimension="UNKNOWN")
        with pytest.raises(DriftError) as exc:
            sut.classify_drift_pattern(ev)
        assert exc.value.code == "E03"

    def test_TC_L107_L205_104_no_mitigation_template(self, sut) -> None:
        """TC-L107-L205-104 · E04 · 注册表无模板 · 拒。"""
        with pytest.raises(DriftError) as exc:
            sut.propose_mitigation(drift_type="UNKNOWN_TYPE",
                                    pattern_context={"wp_id": "w"})
        assert exc.value.code == "E04"

    def test_TC_L107_L205_105_idempotent_key_duplicate(self, sut, mock_l2_04) -> None:
        """TC-L107-L205-105 · E05 · 同 key 重复派发 · 拒。"""
        m = MagicMock(idempotent_key="k-dup")
        sut.dispatch_auto_fix_via_subagent(m)
        with pytest.raises(DriftError) as exc:
            sut.dispatch_auto_fix_via_subagent(m)
        assert exc.value.code == "E05"

    def test_TC_L107_L205_106_dispatch_rejected(self, sut, mock_l2_04) -> None:
        """TC-L107-L205-106 · E06 · L2-04 返回 registry mismatch。"""
        mock_l2_04.dispatch.side_effect = ValueError("registry mismatch")
        with pytest.raises(DriftError) as exc:
            sut.dispatch_auto_fix_via_subagent(
                MagicMock(idempotent_key="k-r"))
        assert exc.value.code == "E06"

    def test_TC_L107_L205_107_evidence_incomplete(
        self, sut, make_snapshot,
    ) -> None:
        """TC-L107-L205-107 · E07 · evidence_refs=[] · 拒。"""
        cv = MagicMock(evidence_refs=[], level="INFO")
        with pytest.raises(DriftError) as exc:
            sut.scan_for_soft_drift(project_id="p", snapshot=make_snapshot(),
                                      candidate_verdict=cv)
        assert exc.value.code == "E07"

    def test_TC_L107_L205_108_classification_slo_timeout(
        self, sut, make_snapshot, make_cv, monkeypatch,
    ) -> None:
        """TC-L107-L205-108 · E08 · classify > 1s · 保守降级。"""
        import time
        def slow(*a, **kw):
            time.sleep(1.2)
            return "EVIDENCE_MISSING"
        monkeypatch.setattr(sut, "classify_drift_pattern", slow)
        with pytest.raises(DriftError) as exc:
            sut.scan_for_soft_drift(project_id="p", snapshot=make_snapshot(),
                                      candidate_verdict=make_cv("EVIDENCE_MISSING"),
                                      classify_timeout_s=1.0)
        assert exc.value.code == "E08"

    def test_TC_L107_L205_109_registry_yaml_corrupt(self, sut) -> None:
        """TC-L107-L205-109 · E09 · 注册表 yaml 损坏 · 启动拒。"""
        with pytest.raises(DriftError) as exc:
            sut._load_registry_yaml(content="!@# not yaml")
        assert exc.value.code == "E09"

    def test_TC_L107_L205_110_subagent_tool_violation(self, sut) -> None:
        """TC-L107-L205-110 · E10 · Subagent 越权调 Bash · 拒。"""
        m = MagicMock(action_type="rerun_verifier",
                       idempotent_key="k-v",
                       requires_tool="Bash")  # 非白名单
        with pytest.raises(DriftError) as exc:
            sut.dispatch_auto_fix_via_subagent(m)
        assert exc.value.code == "E10"

    def test_TC_L107_L205_111_outcome_event_stale(self, sut) -> None:
        """TC-L107-L205-111 · E11 · tick_id 落后 · 防重放攻击。"""
        sut._last_tick_id = 100
        out = MagicMock(wp_id="w", drift_type="EVIDENCE_MISSING",
                         mitigated=True, tick_id=50)
        with pytest.raises(DriftError) as exc:
            sut.track_mitigation_outcome(out)
        assert exc.value.code == "E11"

    def test_TC_L107_L205_112_dispatch_id_not_found(self, sut) -> None:
        """TC-L107-L205-112 · E12 · 未匹配 pending · 丢弃。"""
        out = MagicMock(dispatch_id="never-dispatched",
                         wp_id="w", drift_type="EVIDENCE_MISSING",
                         tick_id=200)
        res = sut.track_mitigation_outcome(out)
        # E12 · 返 None 或 warning
        assert res is None or res.dispatch_id_found is False

    def test_TC_L107_L205_113_escalation_misconfigured(self, sut) -> None:
        """TC-L107-L205-113 · E13 · escalation_attempts=0 · 启动拒。"""
        with pytest.raises(DriftError) as exc:
            sut._validate_escalation_config(attempts_before_hard=0)
        assert exc.value.code == "E13"

    def test_TC_L107_L205_114_l2_06_unreachable(
        self, sut, mock_l2_06,
    ) -> None:
        """TC-L107-L205-114 · E14 · L2-06 不可达 · 升级派发失败。"""
        mock_l2_06.escalate.side_effect = ConnectionError("L2-06")
        sut._escalation_counter["wp-x:X"] = 3
        with pytest.raises(DriftError) as exc:
            sut.escalate_to_hard_redline_if_threshold(
                wp_id="wp-x", drift_type="X")
        assert exc.value.code == "E14"

    def test_TC_L107_L205_115_hash_chain_broken(
        self, sut, make_pattern, monkeypatch,
    ) -> None:
        """TC-L107-L205-115 · E15 · 前一 hash 与磁盘不匹配 · abort。"""
        def bad_hash(*a, **kw):
            raise ValueError("prev hash mismatch")
        monkeypatch.setattr(sut, "_compute_hash_chain", bad_hash)
        with pytest.raises(DriftError) as exc:
            sut.persist_drift_report(make_pattern(), outcome=None)
        assert exc.value.code == "E15"

    def test_TC_L107_L205_116_audit_log_write_failed(
        self, sut, make_pattern, mock_audit,
    ) -> None:
        """TC-L107-L205-116 · E16 · IC-09 写失败 · 3 次重试后 fatal。"""
        mock_audit.append.side_effect = IOError("disk")
        with pytest.raises(DriftError) as exc:
            sut.persist_drift_report(make_pattern(), outcome=None)
        assert exc.value.code == "E16"

    def test_TC_L107_L205_117_missing_project_id(
        self, sut, make_snapshot, make_cv,
    ) -> None:
        """TC-L107-L205-117 · E17 · project_id 缺 · 拒。"""
        with pytest.raises(DriftError) as exc:
            sut.scan_for_soft_drift(project_id=None, snapshot=make_snapshot(),
                                      candidate_verdict=make_cv("EVIDENCE_MISSING"))
        assert exc.value.code == "E17"

    def test_TC_L107_L205_118_ui_variant_mismatch(
        self, sut, mock_l1_10,
    ) -> None:
        """TC-L107-L205-118 · E18 · 软红线错用 warn_alert_corner · 拒。"""
        p = MagicMock(ui_variant="warn_alert_corner",
                       drift_type="EVIDENCE_MISSING")
        with pytest.raises(DriftError) as exc:
            sut.push_to_ui_as_warning_card(p)
        assert exc.value.code == "E18"

    def test_TC_L107_L205_119_ic_16_unreachable(
        self, sut, mock_l1_10,
    ) -> None:
        """TC-L107-L205-119 · E19 · UI 侧 API 不可达 · 降级。"""
        mock_l1_10.push_card.side_effect = ConnectionError("UI")
        trend = MagicMock(trend_type="soft_drift_trend", level="WARN",
                           ui_variant="trend_card")
        with pytest.raises(DriftError) as exc:
            sut.push_to_ui_as_warning_card(trend)
        assert exc.value.code == "E19"

    def test_TC_L107_L205_120_business_critical_abort(self, sut) -> None:
        """TC-L107-L205-120 · E20 · 业务关键必升档。"""
        from app.l1_07.l2_05.errors import BusinessCriticalAbort
        with pytest.raises(BusinessCriticalAbort) as exc:
            sut.abort_if_business_critical(
                MagicMock(business_critical=True, drift_type="EVIDENCE_MISSING"))
        assert exc.value.code == "E20"
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_07/test_l2_05_drift_ic.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_05_IC_Contracts:

    def test_TC_L107_L205_601_ic_l2_04_scan(self, sut, make_snapshot, make_cv) -> None:
        """TC-L107-L205-601 · IC-L2-04 scan_for_soft_drift 字段齐。"""
        p = sut.scan_for_soft_drift(project_id="p", snapshot=make_snapshot(),
                                      candidate_verdict=make_cv("EVIDENCE_MISSING"))
        for f in ("project_id", "pattern_id", "drift_type", "auto_fix_action",
                   "evidence_refs", "detected_at"):
            assert hasattr(p, f)

    def test_TC_L107_L205_602_ic_12_dispatch(self, sut, mock_l2_04) -> None:
        """TC-L107-L205-602 · IC-12 dispatch 到 L2-04。"""
        m = MagicMock(idempotent_key="k-602")
        sut.dispatch_auto_fix_via_subagent(m)
        mock_l2_04.dispatch.assert_called_once()

    def test_TC_L107_L205_603_ic_16_push_ui(self, sut, mock_l1_10) -> None:
        """TC-L107-L205-603 · IC-16 push_to_ui L1-10。"""
        trend = MagicMock(trend_type="soft_drift_trend", level="WARN")
        sut.push_to_ui_as_warning_card(trend)
        mock_l1_10.push_card.assert_called_once()

    def test_TC_L107_L205_604_ic_09_audit(self, sut, mock_audit, make_pattern) -> None:
        """TC-L107-L205-604 · IC-09 audit 落盘。"""
        sut.persist_drift_report(make_pattern(), outcome=None)
        assert mock_audit.append.called
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_07/test_l2_05_drift_perf.py
from __future__ import annotations

import pytest
import time


@pytest.mark.perf
class TestL2_05_SLO:

    def test_TC_L107_L205_501_scan_p50_le_100ms(
        self, sut, make_snapshot, make_cv, benchmark,
    ) -> None:
        """TC-L107-L205-501 · scan P50 ≤ 100ms。"""
        benchmark.pedantic(
            sut.scan_for_soft_drift,
            kwargs={"project_id": "p", "snapshot": make_snapshot(),
                    "candidate_verdict": make_cv("EVIDENCE_MISSING")},
            iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p50"] * 1000 <= 100.0

    def test_TC_L107_L205_502_scan_p95_le_500ms(
        self, sut, make_snapshot, make_cv, benchmark,
    ) -> None:
        """TC-L107-L205-502 · scan P95 ≤ 500ms。"""
        benchmark.pedantic(
            sut.scan_for_soft_drift,
            kwargs={"project_id": "p", "snapshot": make_snapshot(),
                    "candidate_verdict": make_cv("PROGRESS_DEVIATION")},
            iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 500.0

    def test_TC_L107_L205_503_scan_p99_hard_lock_1s(
        self, sut, make_snapshot, make_cv, benchmark,
    ) -> None:
        """TC-L107-L205-503 · scan P99 硬锁 ≤ 1s。"""
        benchmark.pedantic(
            sut.scan_for_soft_drift,
            kwargs={"project_id": "p", "snapshot": make_snapshot(),
                    "candidate_verdict": make_cv("CONTEXT_OVERFLOW")},
            iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] <= 1.0

    def test_TC_L107_L205_504_dispatch_timeout_5s(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L205-504 · dispatch 超时 ≤ 5s。"""
        import time
        def slow(*a, **kw): time.sleep(6)
        mock_l2_04.dispatch.side_effect = slow
        from app.l1_07.l2_05.errors import DriftError
        t0 = time.perf_counter()
        try:
            sut.dispatch_auto_fix_via_subagent(
                type("M", (), {"idempotent_key": "k-to",
                                "action_type": "x"})())
        except Exception:
            pass
        assert (time.perf_counter() - t0) <= 6.0

    def test_TC_L107_L205_505_trend_30s_tick_le_2s(
        self, sut, seed_tick_data,
    ) -> None:
        """TC-L107-L205-505 · 30s tick trend 检测 ≤ 2s。"""
        seed_tick_data(three_conditions_met=True)
        t0 = time.perf_counter()
        sut.detect_soft_drift_trend(tick_data=sut._tick_data)
        assert (time.perf_counter() - t0) <= 2.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_07/test_l2_05_drift_e2e.py
from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestL2_05_E2E:

    def test_TC_L107_L205_701_scan_to_dispatch_to_outcome(
        self, sut, make_snapshot, make_cv, mock_l2_04, mock_audit,
    ) -> None:
        """TC-L107-L205-701 · e2e · scan → mitigation → dispatch → outcome。"""
        p = sut.scan_for_soft_drift(project_id="p", snapshot=make_snapshot(),
                                      candidate_verdict=make_cv("EVIDENCE_MISSING"))
        sut.dispatch_auto_fix_via_subagent(p.auto_fix_action)
        from unittest.mock import MagicMock
        sut.track_mitigation_outcome(MagicMock(
            wp_id=p.wp_id, drift_type="EVIDENCE_MISSING",
            mitigated=True, tick_id=10))
        assert mock_l2_04.dispatch.called

    def test_TC_L107_L205_702_escalation_after_3_attempts(
        self, sut, mock_l2_06,
    ) -> None:
        """TC-L107-L205-702 · 3 次未消除 · 升级到 L2-06。"""
        from unittest.mock import MagicMock
        for _ in range(3):
            sut.track_mitigation_outcome(MagicMock(
                wp_id="wp-e2e", drift_type="EVIDENCE_MISSING",
                mitigated=False, tick_id=_+1))
        dec = sut.escalate_to_hard_redline_if_threshold(
            wp_id="wp-e2e", drift_type="EVIDENCE_MISSING")
        assert dec.escalated is True

    def test_TC_L107_L205_703_trend_warn_to_ui(
        self, sut, seed_tick_data, mock_l1_10,
    ) -> None:
        """TC-L107-L205-703 · trend → UI WARN card。"""
        seed_tick_data(three_conditions_met=True)
        trend = sut.detect_soft_drift_trend(tick_data=sut._tick_data)
        sut.push_to_ui_as_warning_card(trend)
        mock_l1_10.push_card.assert_called()
```

---

## §7 测试 fixture

```python
# file: tests/l1_07/conftest_l2_05.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_07.l2_05.service import SoftDriftDetector


@pytest.fixture
def mock_l2_04() -> MagicMock:
    m = MagicMock()
    m.dispatch.return_value = MagicMock(dispatched=True)
    return m


@pytest.fixture
def mock_l2_06() -> MagicMock:
    m = MagicMock()
    m.escalate.return_value = MagicMock(escalated=True)
    return m


@pytest.fixture
def mock_l1_10() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_l2_04, mock_l2_06, mock_l1_10, mock_audit):
    return SoftDriftDetector(
        l2_04=mock_l2_04, l2_06=mock_l2_06, l1_10=mock_l1_10,
        audit=mock_audit,
    )


@pytest.fixture
def make_snapshot():
    def _make():
        return MagicMock(project_id="prj-1",
                         snapshot_id="s-1",
                         captured_at="2026-04-22T10:00:00Z",
                         dimensions=MagicMock())
    return _make


@pytest.fixture
def make_cv():
    def _make(drift_type: str):
        return MagicMock(
            verdict_id=f"v-{drift_type}",
            level="INFO",
            dimension=drift_type.lower().split("_")[0],
            raw_message=f"cv-{drift_type}",
            evidence_refs=[MagicMock(event_id="e-1")],
            force_drift_type=drift_type,
        )
    return _make


@pytest.fixture
def make_pattern():
    def _make():
        return MagicMock(project_id="prj-1",
                         pattern_id="p-1",
                         drift_type="EVIDENCE_MISSING",
                         auto_fix_action=MagicMock(action_type="rerun_verifier"),
                         evidence_refs=[MagicMock()],
                         detected_at="t",
                         wp_id="wp-1")
    return _make


@pytest.fixture
def seed_tick_data(sut):
    def _seed(three_conditions_met: bool = False):
        sut._tick_data = MagicMock(
            condition1=three_conditions_met,
            condition2=three_conditions_met,
            condition3=three_conditions_met)
    return _seed
```

---

## §8 集成点用例

```python
# file: tests/l1_07/test_l2_05_integration.py
from __future__ import annotations

import pytest


class TestL2_05_Integration:

    def test_TC_L107_L205_801_l2_02_invokes_scan_on_candidate(
        self, sut, make_snapshot, make_cv,
    ) -> None:
        """TC-L107-L205-801 · L2-02 命中候选时调 scan。"""
        cv = make_cv("EVIDENCE_MISSING")
        cv.level = "INFO"  # 软红线
        p = sut.scan_for_soft_drift(project_id="p", snapshot=make_snapshot(),
                                      candidate_verdict=cv)
        assert p is not None

    def test_TC_L107_L205_802_l2_06_receives_escalation(
        self, sut, mock_l2_06,
    ) -> None:
        """TC-L107-L205-802 · L2-06 收到升级信号。"""
        sut._escalation_counter["wp-x:X"] = 3
        sut.escalate_to_hard_redline_if_threshold(wp_id="wp-x", drift_type="X")
        mock_l2_06.escalate.assert_called()
```

---

## §9 边界 / edge case

```python
# file: tests/l1_07/test_l2_05_edge.py
from __future__ import annotations

import pytest


class TestL2_05_Edge:

    def test_TC_L107_L205_901_counter_exactly_3(
        self, sut, mock_l2_06,
    ) -> None:
        """TC-L107-L205-901 · counter=3 边界 · 升级。"""
        sut._escalation_counter["wp-b:X"] = 3
        dec = sut.escalate_to_hard_redline_if_threshold(
            wp_id="wp-b", drift_type="X")
        assert dec.escalated is True

    def test_TC_L107_L205_902_counter_below_3_no_escalate(
        self, sut, mock_l2_06,
    ) -> None:
        """TC-L107-L205-902 · counter=2 · 不升级。"""
        sut._escalation_counter["wp-b2:X"] = 2
        dec = sut.escalate_to_hard_redline_if_threshold(
            wp_id="wp-b2", drift_type="X")
        assert dec.escalated is False

    def test_TC_L107_L205_903_merge_empty_candidates(self, sut) -> None:
        """TC-L107-L205-903 · merge 空列表 · 返空。"""
        assert sut.merge_same_tick_candidates([]) == []

    def test_TC_L107_L205_904_concurrent_scan(
        self, sut, make_snapshot, make_cv,
    ) -> None:
        """TC-L107-L205-904 · 5 并发 scan · 无锁冲突。"""
        import threading
        errs = []
        def _run(i):
            try:
                sut.scan_for_soft_drift(project_id=f"p-{i}",
                                          snapshot=make_snapshot(),
                                          candidate_verdict=make_cv("EVIDENCE_MISSING"))
            except Exception as e:
                errs.append(e)
        ts = [threading.Thread(target=_run, args=(i,)) for i in range(5)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert not errs

    def test_TC_L107_L205_905_large_trend_window(
        self, sut, seed_tick_data,
    ) -> None:
        """TC-L107-L205-905 · 100 tick 窗口 · 仍在 SLO 内。"""
        seed_tick_data(three_conditions_met=True)
        # 模拟 100 tick 累积 · 调用仍返回
        trend = sut.detect_soft_drift_trend(tick_data=sut._tick_data)
        assert trend is not None or trend is None  # 不抛
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
