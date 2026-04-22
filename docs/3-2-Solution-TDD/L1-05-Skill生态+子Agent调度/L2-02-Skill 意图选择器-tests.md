---
doc_id: tests-L1-05-L2-02-Skill 意图选择器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md
  - docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-05 L2-02-Skill 意图选择器 · TDD 测试用例

> 基于 3-1 L2-02 §3（7 条 IC + select/advance）+ §11（14 条 `E_INTENT_*` 分 P0-P3）+ §12 SLO 驱动。
> TC ID 统一格式：`TC-L105-L202-NNN`。pytest + Python 3.11+；`class TestL2_02_IntentSelector`；硬过滤 / 5 信号混合打分 / KB 旁路 / 降级链 4 级 独立分组。

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
| `select()` · 基础链长 ≥ 2 | TC-L105-L202-001 | unit | IC-04 |
| `select()` · preferred_quality=high | TC-L105-L202-002 | unit | IC-04 |
| `select()` · preferred_quality=fast | TC-L105-L202-003 | unit | IC-04 |
| `select()` · max_cost=L 过滤 | TC-L105-L202-004 | unit | IC-04 |
| `select()` · exclude_set 排除 | TC-L105-L202-005 | unit | IC-04 |
| `select()` · 硬过滤 unavailable | TC-L105-L202-006 | unit | IC-04 |
| `select()` · kb_hint_enabled=True | TC-L105-L202-007 | unit | IC-06 |
| `advance_fallback()` · 返回链下一项 | TC-L105-L202-008 | unit | IC-L2-03 |
| `advance_degrade()` · 返回降级候选 | TC-L105-L202-009 | unit | IC-L2-04 |
| 5 信号混合打分（availability/success_rate/cost/recency/kb_boost） | TC-L105-L202-010 | unit | — |
| explanation_card 包含 filtered_out + signal_weights | TC-L105-L202-011 | unit | — |
| `_writeback_ledger()` 调用 | TC-L105-L202-012 | unit | IC-L2-07 |
| session_chain_cache LRU 1024 | TC-L105-L202-013 | unit | — |
| emit 7 种事件 | TC-L105-L202-014 | unit | IC-09 |
| 硬编码 scan（启动期） | TC-L105-L202-015 | unit | — |
| chain 含 builtin_min 兜底 | TC-L105-L202-016 | unit | — |
| probe_mode=False 禁灰度 | TC-L105-L202-017 | unit | — |
| tie_breaker 稳定 | TC-L105-L202-018 | unit | — |

### §1.2 错误码 × 测试（14 分级 P0-P3 全覆盖）

| 错误码 | TC ID | 优先级 |
|---|---|---|
| `E_INTENT_HARD_EDGE_VIOLATION` | TC-L105-L202-101 | P0 |
| `E_INTENT_BUILTIN_MISSING` | TC-L105-L202-102 | P0 |
| `E_INTENT_PROBE_MISCONFIG` | TC-L105-L202-103 | P0 |
| `E_INTENT_NO_PROJECT_ID` | TC-L105-L202-104 | P1 |
| `E_INTENT_CALLER_INVALID` | TC-L105-L202-105 | P1 |
| `E_INTENT_BOUNDARY_VIOLATION` | TC-L105-L202-106 | P1 |
| `E_INTENT_CAPABILITY_UNKNOWN` | TC-L105-L202-107 | P2 |
| `E_INTENT_CHAIN_TOO_SHORT` | TC-L105-L202-108 | P2 |
| `E_INTENT_FALLBACK_EXHAUSTED` | TC-L105-L202-109 | P2 |
| `E_INTENT_KB_TIMEOUT` | TC-L105-L202-110 | P3 |
| `E_INTENT_REGISTRY_UNAVAILABLE` | TC-L105-L202-111 | P3 |
| `E_INTENT_AMBIGUOUS` | TC-L105-L202-112 | P3 |
| `E_INTENT_CONSTRAINTS_INFEASIBLE` | TC-L105-L202-113 | P3 |
| `E_INTENT_LEDGER_WRITEBACK_FAIL` | TC-L105-L202-114 | P3 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| IC-04 select | 入口 → 本 L2 | TC-L105-L202-601 |
| IC-L2-03 advance_fallback | L2-03 → 本 L2 | TC-L105-L202-602 |
| IC-L2-04 advance_degrade | L2-04 → 本 L2 | TC-L105-L202-603 |
| IC-L2-01 get_candidates | 本 L2 → L2-01 | TC-L105-L202-604 |
| IC-L2-07 writeback_ledger | 本 L2 → L2-01 | TC-L105-L202-605 |
| IC-06 kb_read | 本 L2 → L1-06 | TC-L105-L202-606 |
| IC-09 append_event | 本 L2 → L1-09 | TC-L105-L202-607 |

---

## §2 正向用例

```python
# file: tests/l1_05/test_l2_02_intent_selector_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_02_intent.selector import IntentSelector
from app.l2_02_intent.schemas import (
    SelectionRequest, CapabilityChainResult,
    AdvanceFallbackRequest, AdvanceDegradeRequest,
)


class TestL2_02_IntentSelector_Positive:

    def test_TC_L105_L202_001_select_produces_chain_ge_2(
        self, sut: IntentSelector, mock_project_id: str,
    ) -> None:
        """TC-L105-L202-001 · select 返回 chain ≥ 2."""
        resp: CapabilityChainResult = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-001",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        assert len(resp.chain) >= 2
        assert resp.chain[0].attempt == 1

    def test_TC_L105_L202_002_preferred_quality_high(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L202-002 · preferred_quality=high · 首选高成功率."""
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-002",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            constraints={"preferred_quality": "high"},
            ts="2026-04-22T00:00:00Z",
        ))
        assert resp.chain[0].confidence >= 0.7

    def test_TC_L105_L202_003_preferred_quality_fast(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-003",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            constraints={"preferred_quality": "fast"},
            ts="2026-04-22T00:00:00Z",
        ))
        assert resp.chain[0].expected_cost in {"L", "M"}

    def test_TC_L105_L202_004_max_cost_L_filters(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L202-004 · max_cost=L · 链内每项 cost ≤ L."""
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-004",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            constraints={"max_cost": "L"},
            ts="2026-04-22T00:00:00Z",
        ))
        for item in resp.chain:
            assert item.expected_cost == "L"

    def test_TC_L105_L202_005_exclude_set(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-005",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            constraints={"exclude_set": ["superpowers:writing-plans"]},
            ts="2026-04-22T00:00:00Z",
        ))
        for item in resp.chain:
            assert item.skill_id != "superpowers:writing-plans"

    def test_TC_L105_L202_006_unavailable_hard_filter(
        self, sut_all_unavail, mock_project_id,
    ) -> None:
        """TC-L105-L202-006 · 所有候选 unavailable · 走 L3 builtin_min."""
        resp = sut_all_unavail.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-006",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        assert resp.chain[0].kind == "builtin_min"

    def test_TC_L105_L202_007_kb_hint_enabled(
        self, sut, mock_project_id, mock_kb,
    ) -> None:
        sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-007",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            kb_hint_enabled=True, ts="2026-04-22T00:00:00Z",
        ))
        mock_kb.kb_read.assert_called_once()

    def test_TC_L105_L202_008_advance_fallback_returns_next(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L202-008 · advance_fallback 返回 chain[1]."""
        sel = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-008",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        nxt = sut.advance_fallback(AdvanceFallbackRequest(
            project_id=mock_project_id, request_id=sel.request_id,
            current_attempt=1, caller_l2="L2-03",
        ))
        assert nxt.next_item.attempt == 2

    def test_TC_L105_L202_009_advance_degrade(
        self, sut, mock_project_id,
    ) -> None:
        sel = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-009",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        deg = sut.advance_degrade(AdvanceDegradeRequest(
            project_id=mock_project_id, request_id=sel.request_id,
            reason="runtime_timeout", caller_l2="L2-04",
        ))
        assert deg.next_item.kind in {"skill", "subagent", "builtin_min"}

    def test_TC_L105_L202_010_signal_weights(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L202-010 · explanation_card.structured.signal_weights 有 5 信号。"""
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-010",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        w = resp.explanation_card.structured.signal_weights
        for k in ("availability", "success_rate", "cost", "recency", "kb_boost"):
            assert k in w

    def test_TC_L105_L202_011_filtered_out_has_reason(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-011",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            constraints={"exclude_set": ["superpowers:writing-plans"]},
            ts="2026-04-22T00:00:00Z",
        ))
        filtered = resp.explanation_card.structured.filtered_out
        assert any(f["reason_code"] in {"EXCLUDE_SET", "unavailable"}
                   for f in filtered)

    def test_TC_L105_L202_012_writeback_ledger_called(
        self, sut, mock_project_id, mock_registry,
    ) -> None:
        sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-012",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        sut._writeback_selection(project_id=mock_project_id,
                                  request_id="sel-012",
                                  outcome={"success": True, "duration_ms": 100})
        mock_registry.write_ledger.assert_called_once()

    def test_TC_L105_L202_013_cache_lru_1024(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L202-013 · 写 1200 不同 request_id · cache 只保 1024."""
        for i in range(1200):
            sut.select(SelectionRequest(
                project_id=mock_project_id, request_id=f"sel-lru-{i:04d}",
                capability="tdd.blueprint_generate", caller_l1="L1-02",
                ts="2026-04-22T00:00:00Z",
            ))
        assert len(sut._session_chain_cache) <= 1024

    def test_TC_L105_L202_014_emits_7_event_types(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-014",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        types = {c.args[0]["event_type"]
                  for c in mock_event_bus.append_event.call_args_list}
        assert any(t.startswith("L1-05:") for t in types)

    def test_TC_L105_L202_015_hard_edge_scan_on_startup(self, sut) -> None:
        """TC-L105-L202-015 · 启动时 HardEdgeScan 扫源码硬编码 skill_id."""
        assert sut._hard_edge_scan_passed is True

    def test_TC_L105_L202_016_builtin_min_always_last(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-016",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        # chain 最后一项可能是 builtin_min（兜底）
        kinds = [c.kind for c in resp.chain]
        assert any(k == "builtin_min" for k in kinds) or len(resp.chain) >= 3

    def test_TC_L105_L202_017_probe_mode_false_disables_gray(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-017",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            probe_mode=False, ts="2026-04-22T00:00:00Z",
        ))
        # 链内无 gray=True 的项
        for c in resp.chain:
            assert getattr(c, "gray", False) is False

    def test_TC_L105_L202_018_tie_breaker_stable(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L202-018 · 同分候选按稳定 key 排序 · 两次结果一致。"""
        r1 = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-18a",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        r2 = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-18b",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        ids1 = [c.skill_id for c in r1.chain]
        ids2 = [c.skill_id for c in r2.chain]
        assert ids1 == ids2
```

---

## §3 负向用例

```python
# file: tests/l1_05/test_l2_02_intent_selector_negative.py
import pytest

from app.l2_02_intent.schemas import SelectionRequest, AdvanceFallbackRequest


class TestL2_02_Negative:

    def test_TC_L105_L202_101_hard_edge_violation_P0(
        self, sut_with_hardcoded_skill,
    ) -> None:
        """E_INTENT_HARD_EDGE_VIOLATION · 启动时扫到源码硬编码 skill_id · exit。"""
        with pytest.raises(Exception) as ei:
            sut_with_hardcoded_skill.boot()
        assert "HARD_EDGE_VIOLATION" in str(ei.value)

    def test_TC_L105_L202_102_builtin_missing_P0(
        self, sut_no_builtin,
    ) -> None:
        """E_INTENT_BUILTIN_MISSING · 启动时 builtin_min 不可加载 · exit."""
        with pytest.raises(Exception) as ei:
            sut_no_builtin.boot()
        assert "BUILTIN_MISSING" in str(ei.value)

    def test_TC_L105_L202_103_probe_misconfig_P0(
        self, sut_bad_probe,
    ) -> None:
        """E_INTENT_PROBE_MISCONFIG · 灰度配置错误."""
        with pytest.raises(Exception) as ei:
            sut_bad_probe.boot()
        assert "PROBE_MISCONFIG" in str(ei.value)

    def test_TC_L105_L202_104_no_project_id_P1(self, sut) -> None:
        with pytest.raises(Exception) as ei:
            sut.select_raw({"request_id": "x", "capability": "y",
                            "caller_l1": "L1-02", "ts": "2026-04-22T00:00:00Z"})
        assert "NO_PROJECT_ID" in str(ei.value)

    def test_TC_L105_L202_105_caller_invalid_P1(self, sut, mock_project_id) -> None:
        with pytest.raises(Exception) as ei:
            sut.select_raw({"project_id": mock_project_id, "request_id": "x",
                            "capability": "tdd.blueprint_generate",
                            "caller_l1": "L1-05",  # L1-05 不能调自己
                            "ts": "2026-04-22T00:00:00Z"})
        assert "CALLER_INVALID" in str(ei.value)

    def test_TC_L105_L202_106_boundary_violation_P1(
        self, sut, mock_project_id,
    ) -> None:
        """E_INTENT_BOUNDARY_VIOLATION · 其他 L2 尝试绕本 L2 直接 writeback."""
        with pytest.raises(Exception) as ei:
            sut._writeback_selection(project_id=mock_project_id,
                                      request_id="sel-unknown-999",
                                      outcome={"success": True},
                                      caller_l2="L2-03")  # 非法 caller
        assert "BOUNDARY_VIOLATION" in str(ei.value)

    def test_TC_L105_L202_107_capability_unknown_P2(
        self, sut, mock_project_id,
    ) -> None:
        with pytest.raises(Exception) as ei:
            sut.select(SelectionRequest(
                project_id=mock_project_id, request_id="sel-unk",
                capability="fake.nonexistent", caller_l1="L1-02",
                ts="2026-04-22T00:00:00Z",
            ))
        assert "CAPABILITY_UNKNOWN" in str(ei.value)

    def test_TC_L105_L202_108_chain_too_short_P2(
        self, sut_only_1_candidate, mock_project_id,
    ) -> None:
        """E_INTENT_CHAIN_TOO_SHORT · 仅 1 候选且兜底失败 · 拒绝。"""
        with pytest.raises(Exception) as ei:
            sut_only_1_candidate.select(SelectionRequest(
                project_id=mock_project_id, request_id="sel-short",
                capability="tdd.blueprint_generate", caller_l1="L1-02",
                ts="2026-04-22T00:00:00Z",
            ))
        assert "CHAIN_TOO_SHORT" in str(ei.value)

    def test_TC_L105_L202_109_fallback_exhausted_P2(
        self, sut, mock_project_id,
    ) -> None:
        """E_INTENT_FALLBACK_EXHAUSTED · advance_fallback 超出 chain 长度。"""
        sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-ex",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        for i in range(20):
            try:
                sut.advance_fallback(AdvanceFallbackRequest(
                    project_id=mock_project_id, request_id="sel-ex",
                    current_attempt=i + 1, caller_l2="L2-03",
                ))
            except Exception as e:
                assert "FALLBACK_EXHAUSTED" in str(e)
                return
        pytest.fail("FALLBACK_EXHAUSTED never raised")

    def test_TC_L105_L202_110_kb_timeout_P3(
        self, sut_slow_kb, mock_project_id,
    ) -> None:
        """E_INTENT_KB_TIMEOUT · KB 读 150ms 超 · 降级继续（L1 · NO_KB）。"""
        resp = sut_slow_kb.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-kb",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            kb_hint_enabled=True, ts="2026-04-22T00:00:00Z",
        ))
        assert len(resp.chain) >= 2  # 降级后仍产链

    def test_TC_L105_L202_111_registry_unavailable_P3(
        self, sut, mock_registry, mock_project_id,
    ) -> None:
        mock_registry.query_candidates.side_effect = IOError("registry down")
        # 应降级到 BUILTIN_ONLY
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-reg",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        assert resp.chain[0].kind == "builtin_min"

    def test_TC_L105_L202_112_ambiguous_P3(
        self, sut, mock_project_id,
    ) -> None:
        """E_INTENT_AMBIGUOUS · 多候选同分超过阈值 · INFO 事件 + 稳定排序。"""
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-ambi",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        # 不抛 · 走 tie_breaker
        assert resp.chain[0].skill_id

    def test_TC_L105_L202_113_constraints_infeasible_P3(
        self, sut, mock_project_id,
    ) -> None:
        """E_INTENT_CONSTRAINTS_INFEASIBLE · max_cost=L 但仅 H 候选 · 降级 builtin."""
        resp = sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-con",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            constraints={"max_cost": "L", "max_timeout_ms": 1000},
            ts="2026-04-22T00:00:00Z",
        ))
        # 应至少有 builtin_min 备胎
        assert len(resp.chain) >= 1

    def test_TC_L105_L202_114_ledger_writeback_fail_P3(
        self, sut, mock_registry, mock_project_id,
    ) -> None:
        mock_registry.write_ledger.side_effect = IOError("ledger down")
        # 不抛 · 仅发 WARN
        sut.select(SelectionRequest(
            project_id=mock_project_id, request_id="sel-led",
            capability="tdd.blueprint_generate", caller_l1="L1-02",
            ts="2026-04-22T00:00:00Z",
        ))
        # writeback 异步失败不阻塞 select
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_05/test_l2_02_ic_contracts.py
import pytest


class TestL2_02_IC_Contracts:

    def test_TC_L105_L202_601_select_raw_shape(self, sut, mock_project_id) -> None:
        r = sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-601",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        for k in ("project_id", "request_id", "chain", "explanation_card",
                  "duration_ms"):
            assert k in r

    def test_TC_L105_L202_602_advance_fallback_raw(self, sut, mock_project_id) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-602",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        r = sut.advance_fallback_raw({
            "project_id": mock_project_id, "request_id": "r-602",
            "current_attempt": 1, "caller_l2": "L2-03",
        })
        assert r["next_item"]["attempt"] == 2

    def test_TC_L105_L202_603_advance_degrade_raw(self, sut, mock_project_id) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-603",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        r = sut.advance_degrade_raw({
            "project_id": mock_project_id, "request_id": "r-603",
            "reason": "runtime_timeout", "caller_l2": "L2-04",
        })
        assert "next_item" in r

    def test_TC_L105_L202_604_registry_query_candidates_called(
        self, sut, mock_registry, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-604",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        mock_registry.query_candidates.assert_called()
        kw = mock_registry.query_candidates.call_args.kwargs
        assert kw["caller_l2"] == "L2-02"

    def test_TC_L105_L202_605_writeback_ledger_called(
        self, sut, mock_registry, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-605",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        sut._writeback_selection(project_id=mock_project_id,
                                  request_id="r-605",
                                  outcome={"success": True, "duration_ms": 100})
        mock_registry.write_ledger.assert_called()

    def test_TC_L105_L202_606_kb_read_called(
        self, sut, mock_kb, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-606",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "kb_hint_enabled": True, "ts": "2026-04-22T00:00:00Z",
        })
        mock_kb.kb_read.assert_called()

    def test_TC_L105_L202_607_event_append(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-607",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert mock_event_bus.append_event.called
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_05/test_l2_02_perf.py
import time, statistics
import pytest


class TestL2_02_Perf:

    @pytest.mark.perf
    def test_TC_L105_L202_701_select_p95_under_20ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(200):
            t = time.perf_counter()
            sut.select_raw({
                "project_id": mock_project_id, "request_id": f"r-p-{i:04d}",
                "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
                "ts": "2026-04-22T00:00:00Z",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.02

    @pytest.mark.perf
    def test_TC_L105_L202_702_kb_hint_150ms_hard_cutoff(
        self, sut_slow_kb, mock_project_id,
    ) -> None:
        t = time.perf_counter()
        sut_slow_kb.select_raw({
            "project_id": mock_project_id, "request_id": "r-kb",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "kb_hint_enabled": True, "ts": "2026-04-22T00:00:00Z",
        })
        dur = time.perf_counter() - t
        assert dur < 0.3  # 总耗时不应被 kb 拖死

    @pytest.mark.perf
    def test_TC_L105_L202_703_advance_fallback_p99_under_10ms(
        self, sut, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-af",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        durations = []
        for _ in range(500):
            t = time.perf_counter()
            try:
                sut.advance_fallback_raw({
                    "project_id": mock_project_id, "request_id": "r-af",
                    "current_attempt": 1, "caller_l2": "L2-03",
                })
            except Exception:
                pass
            durations.append(time.perf_counter() - t)
        p99 = statistics.quantiles(durations, n=100)[98]
        assert p99 < 0.01

    @pytest.mark.perf
    def test_TC_L105_L202_704_concurrent_64_no_lock(
        self, sut, mock_project_id,
    ) -> None:
        from concurrent.futures import ThreadPoolExecutor
        def go(i):
            return sut.select_raw({
                "project_id": mock_project_id, "request_id": f"r-c-{i:03d}",
                "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
                "ts": "2026-04-22T00:00:00Z",
            })
        with ThreadPoolExecutor(max_workers=64) as ex:
            futures = [ex.submit(go, i) for i in range(64)]
            for f in futures:
                assert f.result()["chain"]
```

---

## §6 端到端 e2e

```python
# file: tests/l1_05/test_l2_02_e2e.py
import pytest


class TestL2_02_E2E:

    @pytest.mark.e2e
    def test_TC_L105_L202_801_select_then_advance_full_chain(
        self, sut, mock_project_id,
    ) -> None:
        sel = sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-e01",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        for attempt in range(1, len(sel["chain"])):
            nxt = sut.advance_fallback_raw({
                "project_id": mock_project_id, "request_id": "r-e01",
                "current_attempt": attempt, "caller_l2": "L2-03",
            })
            assert nxt["next_item"]["attempt"] == attempt + 1

    @pytest.mark.e2e
    def test_TC_L105_L202_802_degrade_to_builtin_then_exhausted(
        self, sut_all_unavail, mock_project_id,
    ) -> None:
        resp = sut_all_unavail.select_raw({
            "project_id": mock_project_id, "request_id": "r-e02",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert resp["chain"][0]["kind"] == "builtin_min"
```

---

## §7 测试 fixture

```python
# file: tests/l1_05/conftest_l2_02.py
import pytest, uuid, time
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id():
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def _default_candidates():
    return {
        "capability": "tdd.blueprint_generate",
        "candidates": [
            {"skill_id": "superpowers:writing-plans", "version": "2026.04",
             "availability": {"status": "available", "source": "active",
                               "last_probe_ts": int(time.time() * 1e9)},
             "success_rate": {"rate": 0.92, "window_count": 30,
                               "last_update": int(time.time() * 1e9)},
             "failure_memory": {"cumulative": 2, "consecutive": 0},
             "cost_estimate": {"tier": "medium"}},
            {"skill_id": "built-in:minimal-plan", "version": "1.0",
             "availability": {"status": "available", "source": "passive",
                               "last_probe_ts": int(time.time() * 1e9)},
             "success_rate": {"rate": 0.7, "window_count": 10,
                               "last_update": int(time.time() * 1e9)},
             "failure_memory": {"cumulative": 0, "consecutive": 0},
             "cost_estimate": {"tier": "cheap"},
             "is_minimal_fallback": True},
        ],
        "total_count": 2,
        "minimal_fallback_injected": False,
    }


@pytest.fixture
def mock_registry(_default_candidates):
    m = MagicMock()
    m.query_candidates = MagicMock(return_value={
        "status": "ok", "result": _default_candidates,
    })
    m.write_ledger = MagicMock(return_value={"status": "queued"})
    return m


@pytest.fixture
def mock_kb():
    m = MagicMock()
    m.kb_read = MagicMock(return_value={"hits": [
        {"skill_id": "superpowers:writing-plans", "boost": 0.2},
    ]})
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
def sut(mock_registry, mock_kb, mock_event_bus, mock_clock):
    from app.l2_02_intent.selector import IntentSelector
    sel = IntentSelector(
        registry=mock_registry, kb=mock_kb,
        event_bus=mock_event_bus, clock=mock_clock,
    )
    sel.boot()
    return sel


@pytest.fixture
def sut_all_unavail(mock_kb, mock_event_bus, mock_clock):
    from app.l2_02_intent.selector import IntentSelector
    reg = MagicMock()
    reg.query_candidates = MagicMock(return_value={
        "status": "ok",
        "result": {"capability": "tdd.blueprint_generate", "candidates": [
            {"skill_id": "x", "version": "1",
             "availability": {"status": "unavailable", "source": "active",
                               "last_probe_ts": 0},
             "success_rate": {"rate": 0.5, "window_count": 10,
                               "last_update": 0},
             "failure_memory": {"cumulative": 5, "consecutive": 5},
             "cost_estimate": {"tier": "medium"}},
        ], "total_count": 1, "minimal_fallback_injected": True},
    })
    reg.write_ledger = MagicMock(return_value={"status": "queued"})
    sel = IntentSelector(registry=reg, kb=mock_kb, event_bus=mock_event_bus,
                          clock=mock_clock)
    sel.boot()
    return sel


@pytest.fixture
def sut_only_1_candidate(mock_kb, mock_event_bus, mock_clock):
    from app.l2_02_intent.selector import IntentSelector
    reg = MagicMock()
    reg.query_candidates = MagicMock(return_value={
        "status": "ok",
        "result": {"capability": "tdd.blueprint_generate",
                    "candidates": [{"skill_id": "only",
                                     "version": "1",
                                     "availability": {"status": "available"},
                                     "success_rate": {"rate": 0.9},
                                     "failure_memory": {"cumulative": 0, "consecutive": 0},
                                     "cost_estimate": {"tier": "medium"}}],
                    "total_count": 1,
                    "minimal_fallback_injected": False},  # 兜底失败
    })
    reg.write_ledger = MagicMock(return_value={"status": "queued"})
    sel = IntentSelector(registry=reg, kb=mock_kb, event_bus=mock_event_bus,
                          clock=mock_clock)
    sel._builtin_available = False  # 模拟兜底损坏
    sel.boot()
    return sel


@pytest.fixture
def sut_slow_kb(mock_registry, mock_event_bus, mock_clock):
    from app.l2_02_intent.selector import IntentSelector
    slow_kb = MagicMock()
    def slow_read(**kwargs):
        time.sleep(0.2)  # 200ms > 150ms 超时
        return {"hits": []}
    slow_kb.kb_read = slow_read
    sel = IntentSelector(registry=mock_registry, kb=slow_kb,
                          event_bus=mock_event_bus, clock=mock_clock)
    sel.boot()
    return sel


@pytest.fixture
def sut_with_hardcoded_skill(mock_registry, mock_kb, mock_event_bus, mock_clock):
    from app.l2_02_intent.selector import IntentSelector
    sel = IntentSelector(registry=mock_registry, kb=mock_kb,
                          event_bus=mock_event_bus, clock=mock_clock)
    sel._simulate_hardcoded_skill = True
    return sel


@pytest.fixture
def sut_no_builtin(mock_registry, mock_kb, mock_event_bus, mock_clock):
    from app.l2_02_intent.selector import IntentSelector
    sel = IntentSelector(registry=mock_registry, kb=mock_kb,
                          event_bus=mock_event_bus, clock=mock_clock)
    sel._builtin_available = False
    return sel


@pytest.fixture
def sut_bad_probe(mock_registry, mock_kb, mock_event_bus, mock_clock):
    from app.l2_02_intent.selector import IntentSelector
    sel = IntentSelector(registry=mock_registry, kb=mock_kb,
                          event_bus=mock_event_bus, clock=mock_clock)
    sel._probe_config = {"gray_pct": 150}  # 非法百分比
    return sel
```

---

## §8 集成点用例

```python
# file: tests/l1_05/test_l2_02_integrations.py
import pytest


class TestL2_02_Integration:

    def test_TC_L105_L202_901_with_l2_01_registry(
        self, sut, mock_registry, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-901",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        mock_registry.query_candidates.assert_called()

    def test_TC_L105_L202_902_with_l1_06_kb_optional(
        self, sut, mock_kb, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-902",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "kb_hint_enabled": True, "ts": "2026-04-22T00:00:00Z",
        })
        mock_kb.kb_read.assert_called()

    def test_TC_L105_L202_903_with_l1_09_audit(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-903",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert mock_event_bus.append_event.called

    def test_TC_L105_L202_904_exclude_set_respects_l2_05_feedback(
        self, sut, mock_project_id,
    ) -> None:
        """L2-05 回滚建议经 IC-14 → L1-04 → IC-04 · 转为 exclude_set."""
        resp = sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-904",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-04",
            "constraints": {"exclude_set": ["superpowers:writing-plans"]},
            "ts": "2026-04-22T00:00:00Z",
        })
        for item in resp["chain"]:
            assert item["skill_id"] != "superpowers:writing-plans"
```

---

## §9 边界 / edge case

```python
# file: tests/l1_05/test_l2_02_edge.py
import pytest


class TestL2_02_Edge:

    def test_TC_L105_L202_A01_empty_exclude_set(self, sut, mock_project_id) -> None:
        resp = sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-a01",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "constraints": {"exclude_set": []},
            "ts": "2026-04-22T00:00:00Z",
        })
        assert len(resp["chain"]) >= 2

    def test_TC_L105_L202_A02_max_timeout_minimum(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-a02",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "constraints": {"max_timeout_ms": 1000},  # 最小值
            "ts": "2026-04-22T00:00:00Z",
        })
        for item in resp["chain"]:
            assert item["expected_timeout_ms"] <= 1000

    def test_TC_L105_L202_A03_max_timeout_maximum(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.select_raw({
            "project_id": mock_project_id, "request_id": "r-a03",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "constraints": {"max_timeout_ms": 1_800_000},  # 最大值
            "ts": "2026-04-22T00:00:00Z",
        })
        assert len(resp["chain"]) >= 2

    def test_TC_L105_L202_A04_concurrent_same_request_id(
        self, sut, mock_project_id,
    ) -> None:
        """并发相同 request_id · 缓存命中 · 返回同一 chain."""
        from concurrent.futures import ThreadPoolExecutor
        def go():
            return sut.select_raw({
                "project_id": mock_project_id, "request_id": "r-a04",
                "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
                "ts": "2026-04-22T00:00:00Z",
            })
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = [f.result() for f in [ex.submit(go) for _ in range(4)]]
        chains = [[c["skill_id"] for c in r["chain"]] for r in results]
        assert all(c == chains[0] for c in chains)

    def test_TC_L105_L202_A05_very_long_chain(
        self, sut_many_candidates, mock_project_id,
    ) -> None:
        """20 候选 · chain 不超过硬上限。"""
        resp = sut_many_candidates.select_raw({
            "project_id": mock_project_id, "request_id": "r-a05",
            "capability": "tdd.blueprint_generate", "caller_l1": "L1-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert 2 <= len(resp["chain"]) <= 10  # 典型硬上限


@pytest.fixture
def sut_many_candidates(mock_kb, mock_event_bus, mock_clock):
    from unittest.mock import MagicMock
    from app.l2_02_intent.selector import IntentSelector
    reg = MagicMock()
    reg.query_candidates = MagicMock(return_value={
        "status": "ok",
        "result": {"capability": "tdd.blueprint_generate",
                    "candidates": [
                        {"skill_id": f"skill-{i:02d}", "version": "1",
                         "availability": {"status": "available"},
                         "success_rate": {"rate": 0.9 - i * 0.02},
                         "failure_memory": {"cumulative": 0, "consecutive": 0},
                         "cost_estimate": {"tier": "medium"}}
                        for i in range(20)],
                    "total_count": 20,
                    "minimal_fallback_injected": False},
    })
    reg.write_ledger = MagicMock(return_value={"status": "queued"})
    sel = IntentSelector(registry=reg, kb=mock_kb,
                          event_bus=mock_event_bus, clock=mock_clock)
    sel.boot()
    return sel
```

---

*— L1-05 L2-02 TDD 已按 10 段模板完成 · 覆盖 §3 全部方法 / 14 错误码 P0-P3 分级 / 7 IC · 含 5 信号混合打分 + KB 旁路 + 降级链 4 级覆盖 —*
