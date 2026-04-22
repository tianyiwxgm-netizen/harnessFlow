---
doc_id: tests-L1-06-L2-05-检索+Rerank-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-06-3层知识库/L2-05-检索+Rerank.md
  - docs/2-prd/L1-06 3层知识库/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-06 L2-05-检索+Rerank · TDD 测试用例

> 基于 3-1 L2-05 §3（IC-L2-04 rerank + IC-L2-05 reverse_recall + stage_transitioned 订阅 + push_to_l101）+ §11（≥ 15 项 `E_L205_*` 错误码）+ §12（rerank P50 30ms / P99 100ms / stage_injection P95 2s SLO）驱动。
> TC ID 统一格式：`TC-L106-L205-NNN`。

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
| `rerank()` · 100 候选 top_k=5 | TC-L106-L205-001 |
| `rerank()` · 空候选集不降级 | TC-L106-L205-002 |
| `rerank()` · 5 信号权重组合 | TC-L106-L205-003 |
| `rerank()` · include_trace=True | TC-L106-L205-004 |
| `rerank()` · 幂等 cache 命中 | TC-L106-L205-005 |
| `reverse_recall()` · 正向转发 | TC-L106-L205-006 |
| `on_stage_transitioned()` · S3 注入 | TC-L106-L205-007 |
| `on_stage_transitioned()` · S7 反向收集 | TC-L106-L205-008 |
| `push_to_l101()` · 正向 | TC-L106-L205-009 |
| scorer · stage_match | TC-L106-L205-010 |
| scorer · context_match | TC-L106-L205-011 |
| scorer · observed_count | TC-L106-L205-012 |
| scorer · recency | TC-L106-L205-013 |
| scorer · kind_priority | TC-L106-L205-014 |
| 权重和 = 1.0 校验 | TC-L106-L205-015 |

### §1.2 错误码 × TC 矩阵

| 错误码 | TC ID |
|---|---|
| `E_L205_IC04_EMPTY_CANDIDATES` | TC-L106-L205-101 |
| `E_L205_IC04_INVALID_TOP_K` | TC-L106-L205-102 |
| `E_L205_IC04_PROJECT_ID_MISSING` | TC-L106-L205-103 |
| `E_L205_IC04_CONTEXT_INVALID` | TC-L106-L205-104 |
| `E_L205_IC04_SCORE_COMPUTE_FAIL` | TC-L106-L205-105 |
| `E_L205_IC04_ALL_SCORERS_FAILED` | TC-L106-L205-106 |
| `E_L205_IC04_WEIGHTS_SUM_INVALID` | TC-L106-L205-107 |
| `E_L205_IC04_TOP_K_CAPPED` | TC-L106-L205-108 |
| `E_L205_IC04_ISOLATION_VIOLATION` | TC-L106-L205-109 |
| `E_L205_IC04_TIMEOUT` | TC-L106-L205-110 |
| `E_L205_IC04_TRACE_CACHE_FAIL` | TC-L106-L205-111 |
| `E_L205_IC04_ENTRY_FIELD_TAMPERED` | TC-L106-L205-112 |
| `E_L205_IC05_L202_UNAVAILABLE` | TC-L106-L205-113 |
| `E_L205_IC05_EMPTY_RECALL` | TC-L106-L205-114 |
| `E_L205_IC05_TIMEOUT` | TC-L106-L205-115 |
| `E_L205_STAGE_UNKNOWN` | TC-L106-L205-116 |
| `E_L205_STRATEGY_NOT_FOUND` | TC-L106-L205-117 |
| `E_L205_STAGE_INJECT_TIMEOUT` | TC-L106-L205-118 |
| `E_L205_L101_PUSH_FAIL` | TC-L106-L205-119 |
| `E_L205_DUPLICATE_EVENT` | TC-L106-L205-120 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-L2-04 rerank | L2-02 → L2-05 | TC-L106-L205-601 |
| IC-L2-05 reverse_recall | L2-05 → L2-02 | TC-L106-L205-602 |
| L1-02 stage_transitioned | subscribe | TC-L106-L205-603 |
| IC-09 append_event | L2-05 → L1-09 | TC-L106-L205-604 |
| push_to_l101 | L2-05 → L1-01 | TC-L106-L205-605 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| rerank @ 100 P50 | ≤ 30ms | TC-L106-L205-501 |
| rerank @ 100 P99 | ≤ 100ms | TC-L106-L205-502 |
| rerank @ 1K P99 | ≤ 200ms | TC-L106-L205-503 |
| stage_injection e2e P95 | ≤ 2s | TC-L106-L205-504 |
| 策略表查表 P99 | ≤ 5ms | TC-L106-L205-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_06/test_l2_05_rerank_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_06.l2_05.service import RerankService
from app.l1_06.l2_05.schemas import (
    RerankRequest, RerankContext, ReverseRecallRequest,
    StageTransitionedEvent,
)


class TestL2_05_Positive:

    def test_TC_L106_L205_001_rerank_100_top_k_5(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-001 · 100 候选 · top_k=5 · status=success + score DESC。"""
        cands = make_candidates(count=100)
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r-001",
            candidates=cands,
            context=RerankContext(current_stage="S3", task_type="coding",
                                   tech_stack=["python"]),
            top_k=5, include_trace=False, trace_id="t"))
        assert resp.status == "success"
        assert len(resp.entries) == 5
        assert resp.entries[0].rank == 1
        assert resp.entries[0].score >= resp.entries[-1].score

    def test_TC_L106_L205_002_empty_candidates_not_degraded(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L205-002 · 0 候选 · 返空 · 不 degraded。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r-002",
            candidates=[],
            context=RerankContext(current_stage="S3", task_type=None,
                                   tech_stack=[]),
            top_k=5, trace_id="t"))
        assert resp.entries == []
        assert resp.degraded is False

    def test_TC_L106_L205_003_five_signals_weighted(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-003 · weights_applied 5 key 齐。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r-003",
            candidates=make_candidates(count=10),
            context=RerankContext(current_stage="S3", task_type="coding",
                                   tech_stack=["python"]),
            top_k=5, trace_id="t"))
        for k in ("context_match", "stage_match", "observed_count",
                   "recency", "kind_priority"):
            assert k in resp.weights_applied

    def test_TC_L106_L205_004_include_trace_reason(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-004 · include_trace=True · reason 非空。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r-004",
            candidates=make_candidates(count=5),
            context=RerankContext(current_stage="S3", task_type="coding",
                                   tech_stack=["python"]),
            top_k=3, include_trace=True, trace_id="t"))
        assert resp.entries[0].reason is not None
        assert resp.entries[0].reason.top_signal

    def test_TC_L106_L205_005_idem_same_id(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-005 · 同 rerank_id 二次 · idem hit。"""
        cands = make_candidates(count=5)
        ctx = RerankContext(current_stage="S3", task_type="coding",
                             tech_stack=["python"])
        r1 = sut.rerank(RerankRequest(project_id=mock_project_id,
                                        rerank_id="r-idem", candidates=cands,
                                        context=ctx, top_k=3, trace_id="t"))
        r2 = sut.rerank(RerankRequest(project_id=mock_project_id,
                                        rerank_id="r-idem", candidates=cands,
                                        context=ctx, top_k=3, trace_id="t"))
        assert [e.entry_id for e in r1.entries] == [e.entry_id for e in r2.entries]

    def test_TC_L106_L205_006_reverse_recall_forwards_to_l2_02(
        self, sut, mock_project_id, mock_l2_02,
    ) -> None:
        """TC-L106-L205-006 · 反向召回 forward。"""
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[{"entry_id": f"c-{i}"} for i in range(18)],
            recalled_count=18, scope_layers_hit=["session", "project"],
            duration_ms=45)
        resp = sut.reverse_recall(ReverseRecallRequest(
            project_id=mock_project_id, injection_id="i-001", stage_to="S3",
            kinds=["anti_pattern"],
            scope_priority=["session", "project", "global"],
            recall_top_k=20, trace_id="t"))
        assert resp.recalled_count == 18

    def test_TC_L106_L205_007_stage_s3_injection(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01,
    ) -> None:
        """TC-L106-L205-007 · S3 注入 · 触发 reverse_recall + push_context。"""
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[{"entry_id": "c-1", "kind": "anti_pattern"}],
            recalled_count=1, scope_layers_hit=["project"], duration_ms=30)
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e-1", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S3",
            transition_reason="gate_approved",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        mock_l2_02.reverse_recall.assert_called_once()
        mock_l1_01.push_context.assert_called_once()

    def test_TC_L106_L205_008_stage_s7_reverse_collect(
        self, sut, mock_project_id, mock_l2_03,
    ) -> None:
        """TC-L106-L205-008 · stage_to=S7 · 触发 L2-03 snapshot。"""
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e-2", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S6", stage_to="S7",
            transition_reason="gate_approved",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        mock_l2_03.provide_candidate_snapshot.assert_called()

    def test_TC_L106_L205_009_push_to_l101_success(
        self, sut, mock_l1_01, mock_project_id,
    ) -> None:
        """TC-L106-L205-009 · push_to_l101 accepted=True。"""
        mock_l1_01.push_context.return_value = MagicMock(
            accepted=True, context_id="ctx-001", rejection_reason=None)
        resp = sut._push_to_l101(project_id=mock_project_id,
                                  injection_id="i", stage="S3",
                                  entries=[{"entry_id": "c"}],
                                  trace_id="t")
        assert resp.accepted is True

    def test_TC_L106_L205_010_scorer_stage_match(self, sut) -> None:
        """TC-L106-L205-010 · stage_match · 完全匹配 score=1.0。"""
        score = sut._scorers.stage_match(
            entry=MagicMock(applicable_context=MagicMock(stages=["S3", "S4"])),
            context=MagicMock(current_stage="S3"))
        assert score == 1.0

    def test_TC_L106_L205_011_scorer_context_match(self, sut) -> None:
        """TC-L106-L205-011 · context_match 正向。"""
        score = sut._scorers.context_match(
            entry=MagicMock(applicable_context=MagicMock(
                task_types=["coding"], tech_stacks=["python", "fastapi"])),
            context=MagicMock(task_type="coding", tech_stack=["python"]))
        assert 0 < score <= 1.0

    def test_TC_L106_L205_012_scorer_observed_count_saturated(self, sut) -> None:
        """TC-L106-L205-012 · observed_count 饱和曲线。"""
        s1 = sut._scorers.observed_count(entry=MagicMock(observed_count=1))
        s15 = sut._scorers.observed_count(entry=MagicMock(observed_count=15))
        s100 = sut._scorers.observed_count(entry=MagicMock(observed_count=100))
        assert s1 < s15 <= s100

    def test_TC_L106_L205_013_scorer_recency_newer_higher(self, sut) -> None:
        """TC-L106-L205-013 · 近期得分高。"""
        s_new = sut._scorers.recency(
            entry=MagicMock(last_observed_at="2026-04-21T00:00:00Z"),
            now_iso="2026-04-22T00:00:00Z")
        s_old = sut._scorers.recency(
            entry=MagicMock(last_observed_at="2024-01-01T00:00:00Z"),
            now_iso="2026-04-22T00:00:00Z")
        assert s_new > s_old

    def test_TC_L106_L205_014_scorer_kind_priority_stage_dependent(self, sut) -> None:
        """TC-L106-L205-014 · anti_pattern 在 S3 优先级 ≥ pattern。"""
        p_anti = sut._scorers.kind_priority(
            entry=MagicMock(kind="anti_pattern"),
            context=MagicMock(current_stage="S3"))
        p_pat = sut._scorers.kind_priority(
            entry=MagicMock(kind="pattern"),
            context=MagicMock(current_stage="S3"))
        assert p_anti >= p_pat

    def test_TC_L106_L205_015_weights_sum_one(self, sut) -> None:
        """TC-L106-L205-015 · 启动权重和 ≈ 1.0。"""
        total = sum(sut._config.weights.values())
        assert abs(total - 1.0) < 0.001
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_06/test_l2_05_rerank_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_06.l2_05.schemas import RerankRequest, RerankContext


class TestL2_05_Negative:

    def test_TC_L106_L205_101_empty_candidates(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L205-101 · 0 候选 · entries=[] · 非降级。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r", candidates=[],
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=[]),
            top_k=5, trace_id="t"))
        assert resp.entries == []

    def test_TC_L106_L205_102_invalid_top_k(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-102 · top_k=-1 · 用策略默认 + 告警。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r", candidates=make_candidates(5),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=[]),
            top_k=-1, trace_id="t"))
        assert "E_L205_IC04_INVALID_TOP_K" in (resp.warnings or []) \
               or resp.top_k_capped is True

    def test_TC_L106_L205_103_project_id_missing(
        self, sut, make_candidates,
    ) -> None:
        """TC-L106-L205-103 · project_id=None · REJECTED。"""
        resp = sut.rerank(RerankRequest(
            project_id=None, rerank_id="r",
            candidates=make_candidates(5),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=[]),
            top_k=5, trace_id="t"))
        assert resp.status == "rejected"
        assert resp.error_code == "E_L205_IC04_PROJECT_ID_MISSING"

    def test_TC_L106_L205_104_context_invalid(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-104 · context 缺必填 current_stage · REJECTED。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(5),
            context=RerankContext(current_stage=None, task_type="c",
                                   tech_stack=[]),
            top_k=5, trace_id="t"))
        assert resp.error_code == "E_L205_IC04_CONTEXT_INVALID"

    def test_TC_L106_L205_105_scorer_fail_skip_signal(
        self, sut, mock_project_id, make_candidates, monkeypatch,
    ) -> None:
        """TC-L106-L205-105 · 某 scorer 抛 · SKIP_SIGNAL 降级。"""
        def boom(*a, **kw):
            raise ValueError("scorer bug")
        monkeypatch.setattr(sut._scorers, "stage_match", boom)
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(5),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=3, trace_id="t"))
        assert "stage_match" in resp.signals_skipped

    def test_TC_L106_L205_106_all_scorers_fail_fallback_raw(
        self, sut, mock_project_id, make_candidates, monkeypatch,
    ) -> None:
        """TC-L106-L205-106 · 5 scorer 全部抛 · FALLBACK_RAW 降级。"""
        def boom(*a, **kw): raise ValueError("all bug")
        for s in ("stage_match", "context_match", "observed_count",
                   "recency", "kind_priority"):
            monkeypatch.setattr(sut._scorers, s, boom)
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(5),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=3, trace_id="t"))
        assert resp.degraded is True
        assert resp.fallback_mode == "FALLBACK_RAW"

    def test_TC_L106_L205_107_weights_sum_invalid(
        self, sut,
    ) -> None:
        """TC-L106-L205-107 · weights 配置和 = 0.8 · 启动校验告警。"""
        sut._config.weights = {"context_match": 0.2, "stage_match": 0.2,
                                "observed_count": 0.1, "recency": 0.2,
                                "kind_priority": 0.1}  # sum = 0.8
        from app.l1_06.l2_05.errors import WeightsSumError
        with pytest.raises(WeightsSumError) as exc:
            sut._validate_weights()
        assert exc.value.code == "E_L205_IC04_WEIGHTS_SUM_INVALID"

    def test_TC_L106_L205_108_top_k_capped(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-108 · top_k=10000 超上限 · 截断 + 审计。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(50),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=10000, trace_id="t"))
        assert resp.top_k_capped is True

    def test_TC_L106_L205_109_isolation_violation(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-109 · 候选 project_id ≠ 请求 · REJECTED + 上报 L1-07。"""
        cands = make_candidates(5, project_override="p-WRONG")
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=cands,
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=3, trace_id="t"))
        assert resp.status == "rejected"
        assert resp.error_code == "E_L205_IC04_ISOLATION_VIOLATION"

    def test_TC_L106_L205_110_rerank_timeout(
        self, sut, mock_project_id, make_candidates, monkeypatch,
    ) -> None:
        """TC-L106-L205-110 · rerank > 100ms · 降级 + SUGG。"""
        import time
        def slow(*a, **kw): time.sleep(0.15); return 0.5
        monkeypatch.setattr(sut._scorers, "stage_match", slow)
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(10),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=3, trace_id="t", timeout_ms=100))
        assert resp.degraded is True
        assert resp.error_code == "E_L205_IC04_TIMEOUT" or \
               "E_L205_IC04_TIMEOUT" in (resp.signals_skipped or [])

    def test_TC_L106_L205_111_trace_cache_fail_non_blocking(
        self, sut, mock_project_id, make_candidates, monkeypatch,
    ) -> None:
        """TC-L106-L205-111 · trace 缓存写失败 · 非关键路径 · 继续。"""
        def boom(*a, **kw): raise IOError("fs")
        monkeypatch.setattr(sut._trace_cache, "write", boom)
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(5),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=3, include_trace=True, trace_id="t"))
        assert resp.status == "success"  # 不降级

    def test_TC_L106_L205_112_entry_field_tampered(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-112 · 候选哈希不匹配 · REJECTED + 严重告警。"""
        cands = make_candidates(5)
        cands[0].entry_summary.title = "TAMPERED"  # 修改后哈希不符
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=cands,
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=3, trace_id="t"))
        assert resp.error_code == "E_L205_IC04_ENTRY_FIELD_TAMPERED"

    def test_TC_L106_L205_113_l2_02_unavailable_empty_injection(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01,
    ) -> None:
        """TC-L106-L205-113 · L2-02 不可达 · 降级 empty_injection。"""
        mock_l2_02.reverse_recall.side_effect = TimeoutError("down")
        from app.l1_06.l2_05.schemas import StageTransitionedEvent
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S3",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        # empty_injection 事件被发出
        mock_l1_01.push_context.assert_not_called()

    def test_TC_L106_L205_114_reverse_recall_empty(
        self, sut, mock_project_id, mock_l2_02,
    ) -> None:
        """TC-L106-L205-114 · 反召 0 条 · 发 kb_injection_empty 事件。"""
        from unittest.mock import MagicMock as MM
        mock_l2_02.reverse_recall.return_value = MM(candidates=[],
                                                     recalled_count=0,
                                                     scope_layers_hit=[],
                                                     duration_ms=5)
        from app.l1_06.l2_05.schemas import ReverseRecallRequest
        resp = sut.reverse_recall(ReverseRecallRequest(
            project_id=mock_project_id, injection_id="i", stage_to="S3",
            kinds=["anti_pattern"],
            scope_priority=["session", "project"], recall_top_k=20,
            trace_id="t"))
        assert resp.recalled_count == 0

    def test_TC_L106_L205_115_reverse_recall_timeout(
        self, sut, mock_project_id, mock_l2_02,
    ) -> None:
        """TC-L106-L205-115 · 反召 > 1s · 放弃本阶段注入。"""
        import time
        def slow(*a, **kw): time.sleep(1.5)
        mock_l2_02.reverse_recall.side_effect = slow
        from app.l1_06.l2_05.schemas import ReverseRecallRequest
        resp = sut.reverse_recall(ReverseRecallRequest(
            project_id=mock_project_id, injection_id="i", stage_to="S3",
            kinds=["anti_pattern"],
            scope_priority=["session", "project"], recall_top_k=20,
            trace_id="t", timeout_ms=1000))
        assert resp.error_code == "E_L205_IC05_TIMEOUT"

    def test_TC_L106_L205_116_stage_unknown(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L205-116 · stage_to=S99 · REJECTED + 严重告警。"""
        from app.l1_06.l2_05.schemas import StageTransitionedEvent
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S99",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        assert any("E_L205_STAGE_UNKNOWN" in str(e)
                    for e in sut._audit_log) \
               or sut._last_error_code == "E_L205_STAGE_UNKNOWN"

    def test_TC_L106_L205_117_strategy_not_found_fallback(
        self, sut, mock_project_id, mock_strategy_repo,
    ) -> None:
        """TC-L106-L205-117 · 策略表损坏 · FALLBACK_NO_INJECTION。"""
        from app.l1_06.l2_05.schemas import StageTransitionedEvent
        mock_strategy_repo.get.side_effect = KeyError("no strategy")
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S3",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        assert sut._fallback_no_injection_count >= 1

    def test_TC_L106_L205_118_stage_inject_timeout(
        self, sut, mock_project_id, mock_l2_02,
    ) -> None:
        """TC-L106-L205-118 · stage_injection 端到端 > 2s · 放弃 + SUGG。"""
        import time
        def slow(*a, **kw): time.sleep(2.5)
        mock_l2_02.reverse_recall.side_effect = slow
        from app.l1_06.l2_05.schemas import StageTransitionedEvent
        t0 = time.perf_counter()
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S3",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"),
            e2e_timeout_s=2.0)
        # 过了 timeout · 应放弃注入
        assert (time.perf_counter() - t0) < 3.0  # 不会超太久

    def test_TC_L106_L205_119_l101_push_fail_retry(
        self, sut, mock_project_id, mock_l1_01,
    ) -> None:
        """TC-L106-L205-119 · L1-01 push 失败 · 重试 1 次。"""
        call = [0]
        def _flaky(*a, **kw):
            call[0] += 1
            if call[0] == 1:
                raise TimeoutError("L1-01")
            from unittest.mock import MagicMock as MM
            return MM(accepted=True, context_id="c", rejection_reason=None)
        mock_l1_01.push_context.side_effect = _flaky
        resp = sut._push_to_l101(project_id=mock_project_id,
                                  injection_id="i", stage="S3",
                                  entries=[], trace_id="t")
        assert resp.accepted is True
        assert call[0] == 2

    def test_TC_L106_L205_120_duplicate_event_idempotent(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L205-120 · 同 event_id 重复消费 · 幂等跳过 + 审计。"""
        from app.l1_06.l2_05.schemas import StageTransitionedEvent
        evt = StageTransitionedEvent(
            event_id="same-evt", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S3",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z", trace_id="t")
        sut.on_stage_transitioned(evt)
        sut.on_stage_transitioned(evt)  # 第二次应跳过
        assert sut._duplicate_event_skipped_count >= 1
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_06/test_l2_05_rerank_ic.py
from __future__ import annotations

import pytest
from app.l1_06.l2_05.schemas import RerankRequest, RerankContext


class TestL2_05_IC_Contracts:

    def test_TC_L106_L205_601_ic_l2_04_fields(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-601 · IC-L2-04 响应字段齐。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r", candidates=make_candidates(3),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=2, trace_id="t"))
        for field in ("project_id", "rerank_id", "status", "entries",
                       "weights_applied", "duration_ms"):
            assert hasattr(resp, field)

    def test_TC_L106_L205_602_ic_l2_05_forwards_to_l2_02(
        self, sut, mock_l2_02, mock_project_id,
    ) -> None:
        """TC-L106-L205-602 · IC-L2-05 调 L2-02。"""
        from app.l1_06.l2_05.schemas import ReverseRecallRequest
        from unittest.mock import MagicMock
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[], recalled_count=0, scope_layers_hit=[],
            duration_ms=1)
        sut.reverse_recall(ReverseRecallRequest(
            project_id=mock_project_id, injection_id="i", stage_to="S3",
            kinds=["anti_pattern"],
            scope_priority=["session"], recall_top_k=5, trace_id="t"))
        mock_l2_02.reverse_recall.assert_called_once()

    def test_TC_L106_L205_603_stage_event_subscription(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L205-603 · stage_transitioned 事件订阅 handler 注册。"""
        assert "L1-02:stage_transitioned" in sut._subscribed_event_types

    def test_TC_L106_L205_604_ic_09_audit_on_rerank(
        self, sut, mock_project_id, mock_audit, make_candidates,
    ) -> None:
        """TC-L106-L205-604 · 每次 rerank 必推 IC-09 audit。"""
        sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r", candidates=make_candidates(3),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=2, trace_id="t"))
        assert mock_audit.append.called

    def test_TC_L106_L205_605_push_to_l101_fields(
        self, sut, mock_l1_01, mock_project_id,
    ) -> None:
        """TC-L106-L205-605 · push_to_l101 请求字段齐。"""
        sut._push_to_l101(project_id=mock_project_id,
                           injection_id="i", stage="S3",
                           entries=[{"entry_id": "e"}], trace_id="t")
        call_args = mock_l1_01.push_context.call_args[0][0]
        for field in ("project_id", "injection_id", "stage", "entries",
                       "context_type"):
            assert hasattr(call_args, field) or field in call_args
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_06/test_l2_05_rerank_perf.py
from __future__ import annotations

import pytest
import time
from app.l1_06.l2_05.schemas import RerankRequest, RerankContext


@pytest.mark.perf
class TestL2_05_SLO:

    def test_TC_L106_L205_501_rerank_100_p50_le_30ms(
        self, sut, mock_project_id, make_candidates, benchmark,
    ) -> None:
        """TC-L106-L205-501 · 100 候选 P50 ≤ 30ms。"""
        ctx = RerankContext(current_stage="S3", task_type="c",
                             tech_stack=["python"])
        counter = [0]
        def _one():
            counter[0] += 1
            sut.rerank(RerankRequest(
                project_id=mock_project_id, rerank_id=f"p-{counter[0]}",
                candidates=make_candidates(100), context=ctx, top_k=5,
                trace_id="t"))
        benchmark.pedantic(_one, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p50"] * 1000 <= 30.0

    def test_TC_L106_L205_502_rerank_100_p99_le_100ms(
        self, sut, mock_project_id, make_candidates, benchmark,
    ) -> None:
        """TC-L106-L205-502 · 100 候选 P99 ≤ 100ms。"""
        ctx = RerankContext(current_stage="S3", task_type="c",
                             tech_stack=["python"])
        counter = [0]
        def _one():
            counter[0] += 1
            sut.rerank(RerankRequest(
                project_id=mock_project_id, rerank_id=f"p99-{counter[0]}",
                candidates=make_candidates(100), context=ctx, top_k=5,
                trace_id="t"))
        benchmark.pedantic(_one, iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 100.0

    def test_TC_L106_L205_503_rerank_1k_p99_le_200ms(
        self, sut, mock_project_id, make_candidates, benchmark,
    ) -> None:
        """TC-L106-L205-503 · 1K 候选 P99 ≤ 200ms。"""
        ctx = RerankContext(current_stage="S3", task_type="c",
                             tech_stack=["python"])
        counter = [0]
        def _one():
            counter[0] += 1
            sut.rerank(RerankRequest(
                project_id=mock_project_id, rerank_id=f"1k-{counter[0]}",
                candidates=make_candidates(1000), context=ctx, top_k=10,
                trace_id="t"))
        benchmark.pedantic(_one, iterations=1, rounds=50)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 200.0

    def test_TC_L106_L205_504_stage_injection_e2e_p95_le_2s(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01,
    ) -> None:
        """TC-L106-L205-504 · stage_injection e2e P95 ≤ 2s。"""
        from unittest.mock import MagicMock
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[{"entry_id": "c"}], recalled_count=1,
            scope_layers_hit=["project"], duration_ms=30)
        from app.l1_06.l2_05.schemas import StageTransitionedEvent
        samples = []
        for i in range(20):
            t0 = time.perf_counter()
            sut.on_stage_transitioned(StageTransitionedEvent(
                event_id=f"e-{i}", event_type="L1-02:stage_transitioned",
                project_id=mock_project_id, stage_from="S2", stage_to="S3",
                transition_reason="gate",
                transition_at="2026-04-22T10:00:00Z", trace_id="t"))
            samples.append(time.perf_counter() - t0)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95) - 1]
        assert p95 <= 2.0

    def test_TC_L106_L205_505_strategy_lookup_p99_le_5ms(
        self, sut, benchmark,
    ) -> None:
        """TC-L106-L205-505 · 策略表查表 P99 ≤ 5ms。"""
        benchmark.pedantic(lambda: sut._strategy_repo.get("S3"),
                            iterations=1, rounds=1000)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 5.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_06/test_l2_05_rerank_e2e.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_06.l2_05.schemas import (
    RerankRequest, RerankContext, StageTransitionedEvent,
)


@pytest.mark.e2e
class TestL2_05_E2E:

    def test_TC_L106_L205_701_l2_02_rerank_to_l1_01_inject_full(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01,
    ) -> None:
        """TC-L106-L205-701 · stage_transitioned → reverse_recall → rerank → push_context e2e。"""
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[{"entry_id": f"c-{i}", "scope": "project",
                          "kind": "anti_pattern",
                          "entry_summary": MagicMock(
                              title=f"t-{i}",
                              applicable_context=MagicMock(
                                  stages=["S3"], task_types=["coding"],
                                  tech_stacks=["python"]),
                              observed_count=10,
                              last_observed_at="2026-04-20T00:00:00Z")}
                         for i in range(10)],
            recalled_count=10, scope_layers_hit=["project"], duration_ms=40)
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e2e-1", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S3",
            transition_reason="gate_approved",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        mock_l1_01.push_context.assert_called_once()

    def test_TC_L106_L205_702_s7_reverse_collect_then_promote_candidates(
        self, sut, mock_project_id, mock_l2_03,
    ) -> None:
        """TC-L106-L205-702 · S7 反向收集 · snapshot 作为 L2-04 候选。"""
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e2e-2", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S6", stage_to="S7",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        mock_l2_03.provide_candidate_snapshot.assert_called()

    def test_TC_L106_L205_703_rerank_idem_cache_across_tick(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-703 · 幂等 · 同 rerank_id 跨 tick 内稳定。"""
        ctx = RerankContext(current_stage="S3", task_type="c",
                             tech_stack=["python"])
        cands = make_candidates(count=10)
        r1 = sut.rerank(RerankRequest(project_id=mock_project_id,
                                        rerank_id="idem-e2e",
                                        candidates=cands, context=ctx,
                                        top_k=5, trace_id="t"))
        r2 = sut.rerank(RerankRequest(project_id=mock_project_id,
                                        rerank_id="idem-e2e",
                                        candidates=cands, context=ctx,
                                        top_k=5, trace_id="t"))
        assert r1.entries[0].entry_id == r2.entries[0].entry_id
```

---

## §7 测试 fixture

```python
# file: tests/l1_06/conftest_l2_05.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_06.l2_05.service import RerankService


@pytest.fixture
def mock_project_id() -> str:
    return "hf-proj-l205"


@pytest.fixture
def mock_l2_02() -> MagicMock:
    """L2-02 KBRead · reverse_recall + rerank callers。"""
    return MagicMock()


@pytest.fixture
def mock_l2_03() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_l1_01() -> MagicMock:
    m = MagicMock()
    m.push_context.return_value = MagicMock(accepted=True,
                                              context_id="ctx",
                                              rejection_reason=None)
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_strategy_repo() -> MagicMock:
    m = MagicMock()
    def _get(stage: str):
        return {"injected_kinds": ["anti_pattern"] if stage == "S3" else [],
                "recall_top_k": 20, "rerank_top_k": 5}
    m.get.side_effect = _get
    return m


@pytest.fixture
def sut(mock_l2_02, mock_l2_03, mock_l1_01, mock_audit,
        mock_strategy_repo, mock_project_id):
    return RerankService(
        l2_02=mock_l2_02,
        l2_03=mock_l2_03,
        l1_01=mock_l1_01,
        audit=mock_audit,
        strategy_repo=mock_strategy_repo,
        project_id=mock_project_id,
    )


@pytest.fixture
def make_candidates():
    """构造 N 个 CandidateSummary."""
    def _make(count: int, project_override: str | None = None) -> list:
        from app.l1_06.l2_05.schemas import CandidateSummary
        result = []
        for i in range(count):
            c = CandidateSummary(
                entry_id=f"kbe-{i:06d}",
                scope="project" if i % 2 else "session",
                kind="anti_pattern" if i % 3 == 0 else "pattern",
                entry_summary=MagicMock(
                    title=f"entry-{i}",
                    applicable_context=MagicMock(
                        stages=["S3", "S4"],
                        task_types=["coding"],
                        tech_stacks=["python", "fastapi"]),
                    observed_count=i + 1,
                    last_observed_at="2026-04-20T00:00:00Z"),
                project_id=project_override or "hf-proj-l205",
            )
            result.append(c)
        return result
    return _make
```

---

## §8 集成点用例

```python
# file: tests/l1_06/test_l2_05_integration.py
from __future__ import annotations

import pytest


class TestL2_05_Integration:

    def test_TC_L106_L205_801_l2_02_driven_rerank_integration(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-801 · L2-02 作为上游驱动 rerank · 无 side-effect。"""
        from app.l1_06.l2_05.schemas import RerankRequest, RerankContext
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="i1",
            candidates=make_candidates(5),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=3, trace_id="t"))
        # rerank 纯函数：不修改候选
        for e in resp.entries:
            assert e.entry_id.startswith("kbe-")

    def test_TC_L106_L205_802_strategy_table_drives_injection(
        self, sut, mock_strategy_repo, mock_project_id, mock_l2_02,
    ) -> None:
        """TC-L106-L205-802 · 策略表 injected_kinds=[] 时 · 不触发 reverse_recall。"""
        mock_strategy_repo.get.side_effect = lambda s: {
            "injected_kinds": [],  # 空 · 不注入
            "recall_top_k": 0, "rerank_top_k": 0,
        }
        from app.l1_06.l2_05.schemas import StageTransitionedEvent
        sut.on_stage_transitioned(StageTransitionedEvent(
            event_id="e", event_type="L1-02:stage_transitioned",
            project_id=mock_project_id, stage_from="S2", stage_to="S3",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z", trace_id="t"))
        mock_l2_02.reverse_recall.assert_not_called()
```

---

## §9 边界 / edge case

```python
# file: tests/l1_06/test_l2_05_edge.py
from __future__ import annotations

import pytest
from app.l1_06.l2_05.schemas import RerankRequest, RerankContext


class TestL2_05_Edge:

    def test_TC_L106_L205_901_single_candidate(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-901 · 仅 1 候选 · top_k=5 · 返回 1 条。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(1),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=5, trace_id="t"))
        assert len(resp.entries) == 1

    def test_TC_L106_L205_902_top_k_equals_candidate_count(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-902 · top_k == 候选数 · 全部返回。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(5),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=5, trace_id="t"))
        assert len(resp.entries) == 5

    def test_TC_L106_L205_903_all_same_score_stable_sort(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-903 · 所有候选 score 相同 · 稳定排序（按 entry_id 确定）。"""
        cands = make_candidates(10)
        # 将所有 applicable_context 调一致
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r", candidates=cands,
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=10, trace_id="t"))
        # 两次调用顺序稳定
        resp2 = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r-2", candidates=cands,
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=10, trace_id="t"))
        assert [e.entry_id for e in resp.entries] == \
               [e.entry_id for e in resp2.entries]

    def test_TC_L106_L205_904_very_large_1k_candidates(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-904 · 1000 候选 · top_k=10 · 成功。"""
        resp = sut.rerank(RerankRequest(
            project_id=mock_project_id, rerank_id="r",
            candidates=make_candidates(1000),
            context=RerankContext(current_stage="S3", task_type="c",
                                   tech_stack=["python"]),
            top_k=10, trace_id="t"))
        assert resp.status == "success"
        assert len(resp.entries) == 10

    def test_TC_L106_L205_905_concurrent_rerank_50(
        self, sut, mock_project_id, make_candidates,
    ) -> None:
        """TC-L106-L205-905 · 50 并发 · 无锁竞争。"""
        import threading
        cands = make_candidates(20)
        ctx = RerankContext(current_stage="S3", task_type="c",
                             tech_stack=["python"])
        errs = []
        def _run(i):
            try:
                sut.rerank(RerankRequest(
                    project_id=mock_project_id, rerank_id=f"c-{i}",
                    candidates=cands, context=ctx, top_k=5, trace_id="t"))
            except Exception as e:
                errs.append(e)
        ts = [threading.Thread(target=_run, args=(i,)) for i in range(50)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert not errs
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
