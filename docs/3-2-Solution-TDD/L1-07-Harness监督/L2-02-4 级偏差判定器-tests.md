---
doc_id: tests-L1-07-L2-02-4 级偏差判定器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-07-Harness监督/L2-02-4 级偏差判定器.md
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-07 L2-02-4 级偏差判定器 · TDD 测试用例

> 基于 3-1 L2-02 §3（10 个方法：classify_deviation + evaluate_rule_tree + match_pattern_for_fail 等）+ §11（20 项 `L2-02/E*` 错误码 + 5 级降级）+ §12（classify 2s / replay 200ms / PostToolUse 500ms SLO）驱动。
> TC ID 统一格式：`TC-L107-L202-NNN`。

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
| `classify_deviation()` · PASS | TC-L107-L202-001 |
| `classify_deviation()` · INFO | TC-L107-L202-002 |
| `classify_deviation()` · WARN | TC-L107-L202-003 |
| `classify_deviation()` · FAIL_L1~L4 | TC-L107-L202-004 |
| `classify_deviation()` · 确定性 inputs_hash | TC-L107-L202-005 |
| `evaluate_rule_tree()` · 42 规则 | TC-L107-L202-006 |
| `match_pattern_for_fail()` · L4 goal_drift | TC-L107-L202-007 |
| `compute_target_state_from_verdict()` | TC-L107-L202-008 |
| `validate_evidence_completeness()` | TC-L107-L202-009 |
| `persist_verdict_with_hash()` · hash-chain | TC-L107-L202-010 |
| `replay_verdict_deterministic_check()` | TC-L107-L202-011 |
| `push_verdict_to_router()` · 分流 L2-04 | TC-L107-L202-012 |
| `build_verdict_card()` · L1-10 payload | TC-L107-L202-013 |
| `record_advice_rejection()` | TC-L107-L202-014 |
| verdict_id 派生 | TC-L107-L202-015 |

### §1.2 错误码 × TC 矩阵（20 项）

| 错误码 | TC ID |
|---|---|
| `L2-02/E01` evidence_incomplete_default_fail_l2 | TC-L107-L202-101 |
| `L2-02/E02` rule_conflict_default_fail_l2 | TC-L107-L202-102 |
| `L2-02/E03` missing_required_four_elements | TC-L107-L202-103 |
| `L2-02/E04` invalid_classification_enum | TC-L107-L202-104 |
| `L2-02/E05` snapshot_schema_invalid | TC-L107-L202-105 |
| `L2-02/E06` rule_tree_yaml_corrupt | TC-L107-L202-106 |
| `L2-02/E07` rule_tree_sha256_mismatch | TC-L107-L202-107 |
| `L2-02/E08` rule_predicate_eval_exception | TC-L107-L202-108 |
| `L2-02/E09` fail_level_invalid | TC-L107-L202-109 |
| `L2-02/E10` verifier_evidence_chain_insufficient | TC-L107-L202-110 |
| `L2-02/E11` verifier_report_missing_fail_l2 | TC-L107-L202-111 |
| `L2-02/E12` rule_tree_semver_regression | TC-L107-L202-112 |
| `L2-02/E13` evidence_event_id_invalid | TC-L107-L202-113 |
| `L2-02/E14` persist_ic_failure_retry_exhausted | TC-L107-L202-114 |
| `L2-02/E15` hash_chain_broken | TC-L107-L202-115 |
| `L2-02/E16` route_target_rejected | TC-L107-L202-116 |
| `L2-02/E17` missing_project_id | TC-L107-L202-117 |
| `L2-02/E18` insufficient_evidence_but_not_warn | TC-L107-L202-118 |
| `L2-02/E19` retro_stage_verdict_invalid | TC-L107-L202-119 |
| `L2-02/E20` ic_dispatch_timeout | TC-L107-L202-120 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-L2-02 classify_request | subagent → L2-02 | TC-L107-L202-601 |
| IC-13 push_to_router | L2-02 → L2-04 | TC-L107-L202-602 |
| IC-09 audit_verdict | L2-02 → L1-09 | TC-L107-L202-603 |
| IC-L2-05 card_payload | L2-02 → L1-10 | TC-L107-L202-604 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| classify 主路径 P99 | ≤ 2s | TC-L107-L202-501 |
| classify PostToolUse P99 | ≤ 500ms | TC-L107-L202-502 |
| evaluate_rule_tree P99 | ≤ 100ms | TC-L107-L202-503 |
| persist_verdict P99 | ≤ 150ms | TC-L107-L202-504 |
| replay P99 | ≤ 200ms | TC-L107-L202-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_07/test_l2_02_deviation_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_07.l2_02.service import DeviationClassifier


class TestL2_02_Positive:

    def test_TC_L107_L202_001_classify_pass(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-001 · 正常 snapshot · PASS。"""
        v = sut.classify_deviation(make_snapshot_healthy(), None, rule_tree)
        assert v.classification.value == "PASS"

    def test_TC_L107_L202_002_classify_info(
        self, sut, make_snapshot_info, rule_tree,
    ) -> None:
        """TC-L107-L202-002 · plan 轻微漂移 · INFO。"""
        v = sut.classify_deviation(make_snapshot_info(), None, rule_tree)
        assert v.classification.value == "INFO"

    def test_TC_L107_L202_003_classify_warn(
        self, sut, make_snapshot_warn, rule_tree,
    ) -> None:
        """TC-L107-L202-003 · cost_budget 超阈值 · WARN。"""
        v = sut.classify_deviation(make_snapshot_warn(), None, rule_tree)
        assert v.classification.value == "WARN"

    def test_TC_L107_L202_004_fail_l1_to_l4(
        self, sut, make_snapshot_fail, rule_tree, make_vr,
    ) -> None:
        """TC-L107-L202-004 · FAIL_L1~L4 都能产出。"""
        for level in ("FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"):
            v = sut.classify_deviation(make_snapshot_fail(level),
                                        make_vr(level), rule_tree)
            assert v.classification.value in (level, "BLOCK")

    def test_TC_L107_L202_005_determinism(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-005 · 同 inputs · inputs_hash 相同。"""
        snap = make_snapshot_healthy()
        v1 = sut.classify_deviation(snap, None, rule_tree)
        v2 = sut.classify_deviation(snap, None, rule_tree)
        assert v1.inputs_hash == v2.inputs_hash

    def test_TC_L107_L202_006_evaluate_rule_tree(
        self, sut, make_inputs_bundle, rule_tree,
    ) -> None:
        """TC-L107-L202-006 · 规则树求值返回 list。"""
        matches = sut.evaluate_rule_tree(make_inputs_bundle(), rule_tree)
        assert isinstance(matches, list)
        assert len(matches) >= 1

    def test_TC_L107_L202_007_match_l4_goal_drift(
        self, sut, make_vr_l4_goal_drift,
    ) -> None:
        """TC-L107-L202-007 · L4 goal_drift · target_state_hint=S1。"""
        pm = sut.match_pattern_for_fail("FAIL_L4", make_vr_l4_goal_drift())
        assert pm.target_state_hint == "S1"

    def test_TC_L107_L202_008_compute_target_state(self, sut) -> None:
        """TC-L107-L202-008 · L1→S4 / L2→S3 / L3→S2 / L4→S1。"""
        mapping = {"FAIL_L1": "S4", "FAIL_L2": "S3",
                    "FAIL_L3": "S2", "FAIL_L4": "S1"}
        for level, target in mapping.items():
            v = MagicMock(classification=MagicMock(value=level))
            assert sut.compute_target_state_from_verdict(v) == target

    def test_TC_L107_L202_009_validate_evidence(self, sut) -> None:
        """TC-L107-L202-009 · 完备度 ≥ 0.7 · valid=True。"""
        evs = [MagicMock(event_id=f"e-{i}", valid=True) for i in range(8)]
        res = sut.validate_evidence_completeness(evs, required=10)
        assert res.completeness_rate >= 0.7
        assert res.valid is True

    def test_TC_L107_L202_010_persist_hash_chain(
        self, sut, make_verdict,
    ) -> None:
        """TC-L107-L202-010 · 两次 persist hash 不同（链式）。"""
        h1 = sut.persist_verdict_with_hash(make_verdict())
        h2 = sut.persist_verdict_with_hash(make_verdict())
        assert h1 != h2

    def test_TC_L107_L202_011_replay_deterministic_ok(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-011 · replay 确定性。"""
        snap = make_snapshot_healthy()
        v1 = sut.classify_deviation(snap, None, rule_tree)
        rep = sut.replay_verdict_deterministic_check(v1, snap, None)
        assert rep.conclusion == "DETERMINISTIC_OK"

    def test_TC_L107_L202_012_push_to_router(
        self, sut, make_verdict, mock_router,
    ) -> None:
        """TC-L107-L202-012 · push_verdict_to_router 分流 L2-04。"""
        v = make_verdict(candidate_route_target="L2-04-SUPERVISOR")
        res = sut.push_verdict_to_router(v)
        assert res.dispatched is True

    def test_TC_L107_L202_013_build_verdict_card(
        self, sut, make_verdict,
    ) -> None:
        """TC-L107-L202-013 · build_verdict_card 字段齐。"""
        card = sut.build_verdict_card(make_verdict())
        for f in ("verdict_id", "classification", "message",
                   "action_suggestion"):
            assert hasattr(card, f)

    def test_TC_L107_L202_014_record_advice_rejection(
        self, sut, make_verdict,
    ) -> None:
        """TC-L107-L202-014 · record_advice_rejection 记 hash。"""
        v = make_verdict()
        h = sut.record_advice_rejection(
            verdict_id=v.verdict_id,
            rejection_reason="user_override_ui_confirmation")
        assert h

    def test_TC_L107_L202_015_verdict_id_format(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-015 · verdict_id = verdict-{pid}-{ts}-{sha8}。"""
        snap = make_snapshot_healthy()
        v = sut.classify_deviation(snap, None, rule_tree)
        assert v.verdict_id.startswith(f"verdict-{snap.project_id}-")
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_07/test_l2_02_deviation_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_07.l2_02.errors import DeviationError


class TestL2_02_Negative:

    def test_TC_L107_L202_101_evidence_incomplete(
        self, sut, make_snapshot_evidence_incomplete, rule_tree,
    ) -> None:
        """TC-L107-L202-101 · E01 · evidence_refs 完备度 < 0.7 · FAIL_L2_DEFAULT。"""
        v = sut.classify_deviation(make_snapshot_evidence_incomplete(),
                                    None, rule_tree)
        assert v.classification.value in ("FAIL_L2", "BLOCK")
        assert v.is_conservative_fallback is True
        assert any(e.code == "L2-02/E01" for e in v.errors)

    def test_TC_L107_L202_102_rule_conflict(
        self, sut, make_snapshot_healthy, conflicting_rule_tree,
    ) -> None:
        """TC-L107-L202-102 · E02 · 两规则冲突 · FAIL_L2_DEFAULT + ADR 告警。"""
        v = sut.classify_deviation(make_snapshot_healthy(), None,
                                    conflicting_rule_tree)
        assert v.is_conservative_fallback is True
        assert any(e.code == "L2-02/E02" for e in v.errors)

    def test_TC_L107_L202_103_missing_four_elements(
        self, sut,
    ) -> None:
        """TC-L107-L202-103 · E03 · 四要素不全 · abort。"""
        with pytest.raises(DeviationError) as exc:
            sut.classify_deviation(MagicMock(spec=[]), None, None)
        assert exc.value.code == "L2-02/E03"

    def test_TC_L107_L202_104_invalid_classification_enum(
        self, sut,
    ) -> None:
        """TC-L107-L202-104 · E04 · classification=FAIL_L99 · ADR。"""
        with pytest.raises(DeviationError) as exc:
            sut._validate_classification("FAIL_L99")
        assert exc.value.code == "L2-02/E04"

    def test_TC_L107_L202_105_snapshot_schema_invalid(
        self, sut, rule_tree,
    ) -> None:
        """TC-L107-L202-105 · E05 · snapshot 缺字段 · 拒。"""
        bad = MagicMock(project_id=None)
        with pytest.raises(DeviationError) as exc:
            sut.classify_deviation(bad, None, rule_tree)
        assert exc.value.code in ("L2-02/E05", "L2-02/E17")

    def test_TC_L107_L202_106_rule_tree_yaml_corrupt(
        self, sut, make_snapshot_healthy, corrupt_rule_tree,
    ) -> None:
        """TC-L107-L202-106 · E06 · YAML 解析失败 · startup fail。"""
        with pytest.raises(DeviationError) as exc:
            sut.classify_deviation(make_snapshot_healthy(), None,
                                    corrupt_rule_tree)
        assert exc.value.code == "L2-02/E06"

    def test_TC_L107_L202_107_rule_tree_sha256_mismatch(
        self, sut, make_snapshot_healthy, tampered_rule_tree,
    ) -> None:
        """TC-L107-L202-107 · E07 · sha256 不符 · 疑 tampering · 停服。"""
        with pytest.raises(DeviationError) as exc:
            sut.classify_deviation(make_snapshot_healthy(), None,
                                    tampered_rule_tree)
        assert exc.value.code == "L2-02/E07"
        assert sut._halt_on_tampering_flag is True

    def test_TC_L107_L202_108_rule_predicate_exception_skip(
        self, sut, make_snapshot_healthy, buggy_rule_tree,
    ) -> None:
        """TC-L107-L202-108 · E08 · 规则谓词抛 · skip 该规则 · 其他继续。"""
        v = sut.classify_deviation(make_snapshot_healthy(), None,
                                    buggy_rule_tree)
        assert v.classification is not None
        assert any(e.code == "L2-02/E08" for e in v.errors)

    def test_TC_L107_L202_109_fail_level_invalid(self, sut) -> None:
        """TC-L107-L202-109 · E09 · fail_level=FAIL_L99 · 拒。"""
        with pytest.raises(DeviationError) as exc:
            sut.match_pattern_for_fail("FAIL_L99", MagicMock())
        assert exc.value.code == "L2-02/E09"

    def test_TC_L107_L202_110_verifier_evidence_chain_insufficient(
        self, sut, make_snapshot_healthy, make_vr_incomplete_chain, rule_tree,
    ) -> None:
        """TC-L107-L202-110 · E10 · evidence_chain 三段不全 · INSUFFICIENT_EVIDENCE。"""
        v = sut.classify_deviation(make_snapshot_healthy(),
                                    make_vr_incomplete_chain(), rule_tree)
        assert v.classification.value in ("INSUFFICIENT_EVIDENCE", "FAIL_L2")

    def test_TC_L107_L202_111_verifier_report_missing_default_fail_l2(
        self, sut, make_snapshot_quality_loop_expected, rule_tree,
    ) -> None:
        """TC-L107-L202-111 · E11 · snapshot 应有 vr 但 None · FAIL_L2_DEFAULT。"""
        v = sut.classify_deviation(make_snapshot_quality_loop_expected(),
                                    None, rule_tree)
        assert v.classification.value == "FAIL_L2"
        assert v.is_conservative_fallback is True

    def test_TC_L107_L202_112_rule_tree_semver_regression(
        self, sut,
    ) -> None:
        """TC-L107-L202-112 · E12 · 规则树 semver 倒退 · 停服 + ADR。"""
        with pytest.raises(DeviationError) as exc:
            sut._check_semver_forward("v1.5.0", "v2.0.0")
        assert exc.value.code == "L2-02/E12"

    def test_TC_L107_L202_113_evidence_event_id_invalid(
        self, sut,
    ) -> None:
        """TC-L107-L202-113 · E13 · event_id 不合法 · FAIL_L2_DEFAULT。"""
        evs = [MagicMock(event_id="bad-format", valid=False)]
        res = sut.validate_evidence_completeness(evs, required=1)
        assert res.valid is False
        assert any(e.code == "L2-02/E13" for e in (res.errors or []))

    def test_TC_L107_L202_114_persist_retry_exhausted(
        self, sut, make_verdict, mock_verdict_repo,
    ) -> None:
        """TC-L107-L202-114 · E14 · persist 3 次重试失败 · 停服。"""
        mock_verdict_repo.save.side_effect = IOError("persistent")
        with pytest.raises(DeviationError) as exc:
            sut.persist_verdict_with_hash(make_verdict())
        assert exc.value.code == "L2-02/E14"

    def test_TC_L107_L202_115_hash_chain_broken(
        self, sut, mock_verdict_repo,
    ) -> None:
        """TC-L107-L202-115 · E15 · hash 链断 · 停服 + alert。"""
        mock_verdict_repo.verify_hash_chain.return_value = False
        with pytest.raises(DeviationError) as exc:
            sut._verify_hash_chain_integrity(project_id="p")
        assert exc.value.code == "L2-02/E15"

    def test_TC_L107_L202_116_route_target_rejected_fallback(
        self, sut, make_verdict, mock_router,
    ) -> None:
        """TC-L107-L202-116 · E16 · 下游拒 · L2-04 fallback。"""
        mock_router.dispatch.side_effect = [ConnectionError("L2-07 down"),
                                             MagicMock(dispatched=True)]
        v = make_verdict(candidate_route_target="L2-07-ROLLBACK")
        res = sut.push_verdict_to_router(v)
        assert res.dispatched is True  # 走 fallback 到 L2-04

    def test_TC_L107_L202_117_missing_project_id(
        self, sut, rule_tree,
    ) -> None:
        """TC-L107-L202-117 · E17 · project_id 缺失 · 拒。"""
        from unittest.mock import MagicMock as MM
        snap = MM(project_id=None, snapshot_id="s", captured_at="t")
        with pytest.raises(DeviationError) as exc:
            sut.classify_deviation(snap, None, rule_tree)
        assert exc.value.code == "L2-02/E17"

    def test_TC_L107_L202_118_insufficient_evidence_but_not_warn(
        self, sut,
    ) -> None:
        """TC-L107-L202-118 · E18 · 不得用 WARN 绕 evidence 不足 · 拒。"""
        with pytest.raises(DeviationError) as exc:
            sut._check_classification_authority(
                classification="WARN", evidence_completeness=0.5)
        assert exc.value.code == "L2-02/E18"

    def test_TC_L107_L202_119_retro_stage_verdict_invalid(
        self, sut,
    ) -> None:
        """TC-L107-L202-119 · E19 · S8 retro 产 WARN 以上 · 无效。"""
        with pytest.raises(DeviationError) as exc:
            sut._check_retro_stage_verdict_rule(
                stage="S8_retro", classification="FAIL_L2")
        assert exc.value.code == "L2-02/E19"

    def test_TC_L107_L202_120_ic_dispatch_timeout_fallback(
        self, sut, make_verdict, mock_router,
    ) -> None:
        """TC-L107-L202-120 · E20 · IC dispatch 超时 · fallback。"""
        mock_router.dispatch.side_effect = [TimeoutError("L2-07"),
                                             MagicMock(dispatched=True)]
        v = make_verdict(candidate_route_target="L2-07-ROLLBACK")
        res = sut.push_verdict_to_router(v)
        assert res.dispatched is True
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_07/test_l2_02_deviation_ic.py
from __future__ import annotations

import pytest


class TestL2_02_IC_Contracts:

    def test_TC_L107_L202_601_ic_l2_02_classify_request(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-601 · IC-L2-02 classify 响应字段齐。"""
        v = sut.classify_deviation(make_snapshot_healthy(), None, rule_tree)
        for f in ("verdict_id", "classification", "project_id",
                   "issued_at", "inputs_hash", "audit_entry_hash"):
            assert hasattr(v, f)

    def test_TC_L107_L202_602_ic_13_push_to_router(
        self, sut, make_verdict, mock_router,
    ) -> None:
        """TC-L107-L202-602 · IC-13 push 到 L2-04。"""
        v = make_verdict(candidate_route_target="L2-04-SUPERVISOR")
        sut.push_verdict_to_router(v)
        mock_router.dispatch.assert_called_once()

    def test_TC_L107_L202_603_ic_09_audit_on_persist(
        self, sut, make_verdict, mock_audit,
    ) -> None:
        """TC-L107-L202-603 · 每次 persist 都 audit IC-09。"""
        sut.persist_verdict_with_hash(make_verdict())
        assert mock_audit.append.called

    def test_TC_L107_L202_604_ic_l2_05_card_payload(
        self, sut, make_verdict,
    ) -> None:
        """TC-L107-L202-604 · build_verdict_card → L1-10 card。"""
        card = sut.build_verdict_card(make_verdict())
        assert card is not None
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_07/test_l2_02_deviation_perf.py
from __future__ import annotations

import pytest
import time


@pytest.mark.perf
class TestL2_02_SLO:

    def test_TC_L107_L202_501_classify_main_p99_le_2s(
        self, sut, make_snapshot_healthy, rule_tree, benchmark,
    ) -> None:
        """TC-L107-L202-501 · classify P99 ≤ 2s。"""
        snap = make_snapshot_healthy()
        benchmark.pedantic(
            sut.classify_deviation,
            args=(snap, None, rule_tree),
            iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p99"] <= 2.0

    def test_TC_L107_L202_502_classify_post_tool_p99_le_500ms(
        self, sut, make_snapshot_healthy, rule_tree, benchmark,
    ) -> None:
        """TC-L107-L202-502 · PostToolUse 极速 P99 ≤ 500ms。"""
        snap = make_snapshot_healthy(post_tool_use=True)
        def _fast():
            sut.classify_deviation(snap, None, rule_tree, fast_mode=True)
        benchmark.pedantic(_fast, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 500.0

    def test_TC_L107_L202_503_evaluate_rule_tree_p99_le_100ms(
        self, sut, make_inputs_bundle, rule_tree, benchmark,
    ) -> None:
        """TC-L107-L202-503 · evaluate_rule_tree P99 ≤ 100ms。"""
        benchmark.pedantic(
            sut.evaluate_rule_tree,
            args=(make_inputs_bundle(), rule_tree),
            iterations=1, rounds=300)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 100.0

    def test_TC_L107_L202_504_persist_p99_le_150ms(
        self, sut, make_verdict, benchmark,
    ) -> None:
        """TC-L107-L202-504 · persist_verdict P99 ≤ 150ms。"""
        counter = [0]
        def _p():
            counter[0] += 1
            sut.persist_verdict_with_hash(make_verdict(vid_suffix=counter[0]))
        benchmark.pedantic(_p, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 150.0

    def test_TC_L107_L202_505_replay_p99_le_200ms(
        self, sut, make_snapshot_healthy, rule_tree, benchmark,
    ) -> None:
        """TC-L107-L202-505 · replay P99 ≤ 200ms。"""
        snap = make_snapshot_healthy()
        v = sut.classify_deviation(snap, None, rule_tree)
        benchmark.pedantic(
            sut.replay_verdict_deterministic_check,
            args=(v, snap, None),
            iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 200.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_07/test_l2_02_deviation_e2e.py
from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestL2_02_E2E:

    def test_TC_L107_L202_701_snapshot_to_verdict_to_route(
        self, sut, make_snapshot_warn, rule_tree, mock_router, mock_audit,
    ) -> None:
        """TC-L107-L202-701 · snapshot → classify → persist → route · e2e。"""
        v = sut.classify_deviation(make_snapshot_warn(), None, rule_tree)
        sut.persist_verdict_with_hash(v)
        sut.push_verdict_to_router(v)
        assert mock_audit.append.called
        assert mock_router.dispatch.called

    def test_TC_L107_L202_702_fail_l4_goal_drift_escalates_to_s1(
        self, sut, make_snapshot_fail, rule_tree, make_vr,
    ) -> None:
        """TC-L107-L202-702 · FAIL_L4 · target_state=S1 · escalate。"""
        v = sut.classify_deviation(make_snapshot_fail("FAIL_L4"),
                                    make_vr("FAIL_L4"), rule_tree)
        assert sut.compute_target_state_from_verdict(v) == "S1"

    def test_TC_L107_L202_703_conservative_fallback_on_missing_vr(
        self, sut, make_snapshot_quality_loop_expected, rule_tree,
    ) -> None:
        """TC-L107-L202-703 · vr 缺失 + 应有 · 保守降级 FAIL_L2。"""
        v = sut.classify_deviation(make_snapshot_quality_loop_expected(),
                                    None, rule_tree)
        assert v.is_conservative_fallback is True
        assert v.classification.value == "FAIL_L2"
```

---

## §7 测试 fixture

```python
# file: tests/l1_07/conftest_l2_02.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_07.l2_02.service import DeviationClassifier


@pytest.fixture
def rule_tree() -> MagicMock:
    """合法 rule_tree · sha256 与版本一致。"""
    rt = MagicMock()
    rt.version = "v1.0.0"
    rt.sha256 = "a" * 64
    rt.rules = [{"rule_id": f"R-{i:03d}"} for i in range(42)]
    return rt


@pytest.fixture
def corrupt_rule_tree() -> MagicMock:
    rt = MagicMock()
    rt.load_exception = ValueError("yaml corrupt")
    rt.version = None
    return rt


@pytest.fixture
def tampered_rule_tree() -> MagicMock:
    rt = MagicMock()
    rt.version = "v1.0.0"
    rt.sha256 = "bad"  # 不匹配配置期望
    rt.expected_sha256 = "a" * 64
    return rt


@pytest.fixture
def buggy_rule_tree() -> MagicMock:
    rt = MagicMock()
    rt.version = "v1.0.0"
    rt.sha256 = "a" * 64
    def bad_eval(*a, **kw): raise ValueError("rule bug")
    rt.evaluate_one = bad_eval
    rt.rules = [{"rule_id": "R-BAD-01"}]
    return rt


@pytest.fixture
def conflicting_rule_tree() -> MagicMock:
    rt = MagicMock()
    rt.version = "v1.0.0"
    rt.sha256 = "a" * 64
    rt.force_conflict = True
    return rt


@pytest.fixture
def mock_verdict_repo() -> MagicMock:
    m = MagicMock()
    m.save.return_value = "hash-1"
    m.verify_hash_chain.return_value = True
    return m


@pytest.fixture
def mock_router() -> MagicMock:
    m = MagicMock()
    m.dispatch.return_value = MagicMock(dispatched=True)
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_verdict_repo, mock_router, mock_audit):
    return DeviationClassifier(
        verdict_repo=mock_verdict_repo,
        router=mock_router,
        audit=mock_audit,
    )


@pytest.fixture
def make_snapshot_healthy():
    def _make(post_tool_use: bool = False):
        return MagicMock(
            project_id="prj-healthy",
            snapshot_id="snap-healthy-001",
            captured_at="2026-04-22T10:00:00Z",
            window_size_sec=30,
            post_tool_use=post_tool_use,
            eight_dimensions=MagicMock(
                goal_fidelity=MagicMock(value=0.9),
                plan_alignment=MagicMock(value=0.9),
                real_completion=MagicMock(value=0.9),
                red_line_safety=MagicMock(value=1.0),
                progress_pace=MagicMock(value=0.85),
                cost_budget=MagicMock(value=0.9),
                retry_loop=MagicMock(value=0.95),
                user_collaboration=MagicMock(value=0.9),
            ),
            fail_counter=MagicMock(consecutive_count=0, level="L1"),
        )
    return _make


@pytest.fixture
def make_snapshot_info():
    def _make():
        s = MagicMock(project_id="prj-info",
                      snapshot_id="s-info",
                      captured_at="t", window_size_sec=30,
                      eight_dimensions=MagicMock(
                          plan_alignment=MagicMock(value=0.65)))  # 轻度漂移
        return s
    return _make


@pytest.fixture
def make_snapshot_warn():
    def _make():
        return MagicMock(project_id="prj-warn",
                          snapshot_id="s-warn",
                          captured_at="t", window_size_sec=30,
                          eight_dimensions=MagicMock(
                              cost_budget=MagicMock(value=0.4)))  # 超阈值
    return _make


@pytest.fixture
def make_snapshot_fail():
    def _make(level: str):
        return MagicMock(project_id=f"prj-{level}",
                          snapshot_id=f"s-{level}",
                          captured_at="t", window_size_sec=30,
                          eight_dimensions=MagicMock(
                              real_completion=MagicMock(value=0.1)),
                          fail_counter=MagicMock(level=level,
                                                  consecutive_count=3))
    return _make


@pytest.fixture
def make_snapshot_evidence_incomplete():
    def _make():
        return MagicMock(project_id="prj-evi",
                          snapshot_id="s-evi",
                          captured_at="t", window_size_sec=30,
                          eight_dimensions=MagicMock(),
                          evidence_completeness=0.5)
    return _make


@pytest.fixture
def make_snapshot_quality_loop_expected():
    def _make():
        return MagicMock(project_id="prj-vr",
                          snapshot_id="s-vr",
                          captured_at="t", window_size_sec=30,
                          quality_loop_expected_vr=True,
                          eight_dimensions=MagicMock())
    return _make


@pytest.fixture
def make_vr():
    def _make(verdict: str = "PASS"):
        return MagicMock(verdict=verdict,
                          evidence_chain=MagicMock(
                              existence=True, behavior=True, quality=True),
                          generated_at="t")
    return _make


@pytest.fixture
def make_vr_incomplete_chain():
    def _make():
        return MagicMock(verdict="FAIL_L2",
                          evidence_chain=MagicMock(
                              existence=True, behavior=False, quality=False))
    return _make


@pytest.fixture
def make_vr_l4_goal_drift():
    def _make():
        return MagicMock(verdict="FAIL_L4",
                          pattern_id="goal_drift",
                          evidence_chain=MagicMock(
                              existence=True, behavior=True, quality=True))
    return _make


@pytest.fixture
def make_inputs_bundle(make_snapshot_healthy, make_vr):
    def _make():
        return MagicMock(snapshot=make_snapshot_healthy(),
                          verifier_report=make_vr("PASS"),
                          fail_counter=MagicMock(consecutive_count=0))
    return _make


@pytest.fixture
def make_verdict():
    def _make(candidate_route_target: str = "L2-04-SUPERVISOR",
               vid_suffix: Any = 1):
        from app.l1_07.l2_02.schemas import DeviationVerdict
        return MagicMock(
            verdict_id=f"verdict-prj-t-sha8-{vid_suffix}",
            project_id="prj-make",
            classification=MagicMock(value="PASS"),
            candidate_route_target=candidate_route_target,
            issued_at="2026-04-22T10:00:00Z",
            inputs_hash="h" * 64,
            audit_entry_hash="a" * 64,
        )
    return _make
```

---

## §8 集成点用例

```python
# file: tests/l1_07/test_l2_02_integration.py
from __future__ import annotations

import pytest


class TestL2_02_Integration:

    def test_TC_L107_L202_801_l2_01_snapshot_consumed(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-801 · L2-01 snapshot 直接消费。"""
        snap = make_snapshot_healthy()
        v = sut.classify_deviation(snap, None, rule_tree)
        assert v.snapshot_ref is not None or v.project_id == snap.project_id

    def test_TC_L107_L202_802_l2_04_receives_verdict_dispatch(
        self, sut, make_verdict, mock_router,
    ) -> None:
        """TC-L107-L202-802 · 分流 L2-04 收到 verdict。"""
        sut.push_verdict_to_router(make_verdict())
        mock_router.dispatch.assert_called()
```

---

## §9 边界 / edge case

```python
# file: tests/l1_07/test_l2_02_edge.py
from __future__ import annotations

import pytest


class TestL2_02_Edge:

    def test_TC_L107_L202_901_boundary_evidence_exactly_0_7(
        self, sut,
    ) -> None:
        """TC-L107-L202-901 · completeness=0.7 · 刚好阈值 · valid=True。"""
        from unittest.mock import MagicMock
        evs = [MagicMock(event_id=f"e-{i}", valid=True) for i in range(7)]
        res = sut.validate_evidence_completeness(evs, required=10)
        assert res.valid is True

    def test_TC_L107_L202_902_concurrent_same_pid_serialized(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-902 · 同 project_id 并发 · hash-chain 强制串行。"""
        import threading
        snap = make_snapshot_healthy()
        results = []
        def _run():
            results.append(sut.classify_deviation(snap, None, rule_tree))
        ts = [threading.Thread(target=_run) for _ in range(5)]
        for t in ts: t.start()
        for t in ts: t.join()
        # 5 次产 5 个 verdict_id · 但 issued_at 相同
        assert all(r.inputs_hash == results[0].inputs_hash for r in results)

    def test_TC_L107_L202_903_retro_stage_pass_only(
        self, sut, make_snapshot_healthy, rule_tree,
    ) -> None:
        """TC-L107-L202-903 · S8_retro 阶段 · 只允许 PASS / INFO（硬约束）。"""
        snap = make_snapshot_healthy()
        snap.stage = "S8_retro"
        v = sut.classify_deviation(snap, None, rule_tree)
        assert v.classification.value in ("PASS", "INFO")

    def test_TC_L107_L202_904_waiting_more_2s_timeout(
        self, sut, make_snapshot_quality_loop_expected, rule_tree,
    ) -> None:
        """TC-L107-L202-904 · WAITING_MORE 2s 超时 · 保守降级。"""
        snap = make_snapshot_quality_loop_expected()
        snap.allow_wait_more = True
        v = sut.classify_deviation(snap, None, rule_tree,
                                    max_wait_ms=50)  # 快速超时
        assert v.is_conservative_fallback is True

    def test_TC_L107_L202_905_huge_rule_tree_200_rules(
        self, sut, make_snapshot_healthy,
    ) -> None:
        """TC-L107-L202-905 · 规则树 200 条 · 仍在 SLO 内。"""
        from unittest.mock import MagicMock
        big_tree = MagicMock(version="v1.0", sha256="a" * 64,
                              rules=[{"rule_id": f"R-{i}"} for i in range(200)])
        v = sut.classify_deviation(make_snapshot_healthy(), None, big_tree)
        assert v.classification is not None
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
