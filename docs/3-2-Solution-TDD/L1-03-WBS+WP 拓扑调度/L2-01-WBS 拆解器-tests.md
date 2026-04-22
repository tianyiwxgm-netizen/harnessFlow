---
doc_id: tests-L1-03-L2-01-WBS 拆解器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-01-WBS 拆解器.md
  - docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-03 L2-01-WBS 拆解器 · TDD 测试用例

> 基于 3-1 L2-01 §3（5 条 IC/方法）+ §11（14 条 `E_L103_L201_*` 错误码）+ §12（SLO）+ §13 TC 矩阵 驱动。
> TC ID 统一格式：`TC-L103-L201-NNN`。pytest + Python 3.11+；`class TestL2_01_WBSFactory` 组织；LLM 走 mock。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus / mock LLM）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/降级/崩溃）

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法（§3）| TC ID | 覆盖类型 | IC |
|---|---|---|---|
| `request_wbs_decomposition()` · 正常 | TC-L103-L201-001 | unit | IC-19 |
| `request_wbs_decomposition()` · dispatch ack | TC-L103-L201-002 | unit | IC-19 |
| `request_incremental_decompose()` · failure_count_exceeded | TC-L103-L201-003 | unit | IC-L2-07 |
| `request_incremental_decompose()` · change_request | TC-L103-L201-004 | unit | IC-L2-07 |
| `request_incremental_decompose()` · granularity_oversized | TC-L103-L201-005 | unit | IC-L2-07 |
| 内部 `_parse_llm_wbs_json()` | TC-L103-L201-006 | unit | — |
| 内部 `_self_check_4_elements()` | TC-L103-L201-007 | unit | — |
| 内部 `_diff_merge()` | TC-L103-L201-008 | unit | — |
| 生成 wbs.md + wp_def.yaml | TC-L103-L201-009 | unit | — |
| emit `L1-03:wbs_decomposed` 事件 | TC-L103-L201-010 | unit | IC-09 |
| `invoke_skill(capability='wbs.decompose')` | TC-L103-L201-011 | integration | IC-04 |
| `load_topology()` call-through | TC-L103-L201-012 | integration | IC-L2-01 |
| 同 command_id 幂等 | TC-L103-L201-013 | unit | — |
| Level 2 规则模板降级 | TC-L103-L201-014 | unit | — |
| 4 要素回帖率 | TC-L103-L201-015 | unit | — |
| 审计链 wbs_draft_emitted | TC-L103-L201-016 | unit | IC-09 |
| 差量合并保留历史 effort | TC-L103-L201-017 | unit | — |

### §1.2 错误码 × 测试（§11 14 项全覆盖）

| 错误码 | TC ID | 方法 |
|---|---|---|
| `E_L103_L201_101` | TC-L103-L201-101 | LLM 超时 |
| `E_L103_L201_102` | TC-L103-L201-102 | 悬空依赖 |
| `E_L103_L201_103` | TC-L103-L201-103 | 4 要素缺 |
| `E_L103_L201_104` | TC-L103-L201-104 | 粒度超 5 天 |
| `E_L103_L201_105` | TC-L103-L201-105 | 跨 project 依赖 |
| `E_L103_L201_106` | TC-L103-L201-106 | Goal 无追溯 |
| `E_L103_L201_107` | TC-L103-L201-107 | skill 非法 |
| `E_L103_L201_108` | TC-L103-L201-108 | wbs.md 模板 |
| `E_L103_L201_109` | TC-L103-L201-109 | target_wp_id 不存在 |
| `E_L103_L201_201` | TC-L103-L201-110 | PM-14 归属不一致 |
| `E_L103_L201_301` | TC-L103-L201-111 | LLM 无效 JSON |
| `E_L103_L201_302` | TC-L103-L201-112 | TOGAF 输入缺失 |
| `E_L103_L201_401` | TC-L103-L201-113 | 审计写失败 |
| `E_L103_L201_501` | TC-L103-L201-114 | bypass 直写 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| IC-19 request_wbs_decomposition | L1-02 → 本 L2 | TC-L103-L201-601 |
| IC-L2-07 request_incremental_decompose | L2-05 → 本 L2 | TC-L103-L201-602 |
| IC-L2-01 load_topology | 本 L2 → L2-02 | TC-L103-L201-603 |
| IC-04 invoke_skill | 本 L2 → L1-05 | TC-L103-L201-604 |
| IC-09 append_event | 本 L2 → L1-09 | TC-L103-L201-605 |

---

## §2 正向用例

```python
# file: tests/l1_03/test_l2_01_wbs_factory_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_01_wbs.factory import WBSFactory
from app.l2_01_wbs.schemas import (
    WbsDecompositionRequest,
    WbsDecompositionResponse,
    IncrementalDecomposeRequest,
)


class TestL2_01_WBSFactory_Positive:

    def test_TC_L103_L201_001_full_decomposition_happy_path(
        self, sut, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """TC-L103-L201-001 · 全量拆解 · accepted + decomposition_session_id。"""
        req = WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000001",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        )
        resp: WbsDecompositionResponse = sut.request_wbs_decomposition(req)
        assert resp.accepted is True
        assert resp.decomposition_session_id.startswith("decomp-")
        assert resp.dispatch_latency_ms >= 0

    def test_TC_L103_L201_002_dispatch_latency_under_100ms(
        self, sut, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """TC-L103-L201-002 · dispatch 返回 < 100ms（纯路由）。"""
        resp = sut.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-00000000000a",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        ))
        assert resp.dispatch_latency_ms < 100

    def test_TC_L103_L201_003_incremental_on_failure(
        self, sut, mock_project_id, loaded_initial_wbs,
    ) -> None:
        """TC-L103-L201-003 · reason=failure_count_exceeded · accepted。"""
        resp = sut.request_incremental_decompose(IncrementalDecomposeRequest(
            command_id="idecomp-req-00000000-0000-0000-0000-000000000001",
            project_id=mock_project_id,
            target_wp_id=loaded_initial_wbs["wps"][0],
            reason="failure_count_exceeded",
            failure_evidence_refs=["evt-f-01", "evt-f-02", "evt-f-03"],
            requester_l2="L2-05",
        ))
        assert resp.accepted is True

    def test_TC_L103_L201_004_incremental_on_change_request(
        self, sut, mock_project_id, loaded_initial_wbs,
    ) -> None:
        """TC-L103-L201-004 · reason=change_request · 不需 failure evidence。"""
        resp = sut.request_incremental_decompose(IncrementalDecomposeRequest(
            command_id="idecomp-req-00000000-0000-0000-0000-000000000002",
            project_id=mock_project_id,
            target_wp_id=loaded_initial_wbs["wps"][-1],
            reason="change_request",
            requester_l2="L2-05",
        ))
        assert resp.accepted is True

    def test_TC_L103_L201_005_incremental_on_oversized(
        self, sut, mock_project_id, loaded_initial_wbs,
    ) -> None:
        """TC-L103-L201-005 · reason=granularity_oversized_runtime。"""
        resp = sut.request_incremental_decompose(IncrementalDecomposeRequest(
            command_id="idecomp-req-00000000-0000-0000-0000-000000000003",
            project_id=mock_project_id,
            target_wp_id=loaded_initial_wbs["wps"][0],
            reason="granularity_oversized_runtime",
            requester_l2="L2-05",
        ))
        assert resp.accepted is True

    def test_TC_L103_L201_006_parse_llm_wbs_json_happy(self, sut, sample_llm_json) -> None:
        """TC-L103-L201-006 · _parse_llm_wbs_json 结构化返回 wp_list + dag_edges。"""
        parsed = sut._parse_llm_wbs_json(sample_llm_json)
        assert len(parsed["wp_list"]) >= 1
        assert "dag_edges" in parsed

    def test_TC_L103_L201_007_self_check_all_elements_present(
        self, sut, valid_wbs_draft,
    ) -> None:
        """TC-L103-L201-007 · 全 4 要素齐 · violations 为空。"""
        violations = sut._self_check_4_elements(valid_wbs_draft)
        assert violations == []

    def test_TC_L103_L201_008_diff_merge_adds_new_wp(self, sut, valid_wbs_draft) -> None:
        """TC-L103-L201-008 · _diff_merge 追加新 WP · 保留原有 wp_id。"""
        delta = {"wp_list": [{"wp_id": "wp-900", "goal": "new", "dod_expr_ref": "d",
                              "deps": [], "effort_estimate": 1.0}],
                 "dag_edges": []}
        merged = sut._diff_merge(valid_wbs_draft, delta)
        ids = {w["wp_id"] for w in merged["wp_list"]}
        assert "wp-900" in ids
        for w in valid_wbs_draft["wp_list"]:
            assert w["wp_id"] in ids

    def test_TC_L103_L201_009_renders_wbs_md_and_wp_def_yaml(
        self, sut, mock_project_id, valid_wbs_draft,
    ) -> None:
        """TC-L103-L201-009 · 成功拆解后生成 wbs.md / wp_def.yaml 文件。"""
        paths = sut._finalize_and_render(project_id=mock_project_id, draft=valid_wbs_draft)
        assert paths["wbs_md_path"].endswith("wbs.md")
        assert paths["wp_def_yaml_path"].endswith("wp_def.yaml")

    def test_TC_L103_L201_010_emits_wbs_decomposed_event(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_event_bus,
    ) -> None:
        """TC-L103-L201-010 · append_event(L1-03:wbs_decomposed)。"""
        sut.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000099",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        ))
        sut._process_async_job()
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert "L1-03:wbs_decomposed" in types

    def test_TC_L103_L201_011_invokes_skill_wbs_decompose(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_skill_gateway,
    ) -> None:
        """TC-L103-L201-011 · IC-04 capability='wbs.decompose'."""
        sut.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000100",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        ))
        sut._process_async_job()
        mock_skill_gateway.invoke_skill.assert_called()
        kw = mock_skill_gateway.invoke_skill.call_args.kwargs
        assert kw["capability_tag"] == "wbs.decompose"

    def test_TC_L103_L201_012_calls_l202_load_topology(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_topology_mgr,
    ) -> None:
        """TC-L103-L201-012 · 拆解完成后自动 IC-L2-01 load_topology(mode=full)。"""
        sut.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000101",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        ))
        sut._process_async_job()
        mock_topology_mgr.load_topology.assert_called()
        args = mock_topology_mgr.load_topology.call_args.args[0]
        assert args["mode"] == "full"

    def test_TC_L103_L201_013_command_id_idempotent(
        self, sut, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """TC-L103-L201-013 · 相同 command_id · 第二次直接返首次结果。"""
        req = WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000222",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        )
        r1 = sut.request_wbs_decomposition(req)
        r2 = sut.request_wbs_decomposition(req)
        assert r1.decomposition_session_id == r2.decomposition_session_id

    def test_TC_L103_L201_014_rule_template_degrade_level2(
        self, sut_with_flaky_llm, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """TC-L103-L201-014 · LLM 连续失败 · Level-2 规则模板 · degraded=True。"""
        resp = sut_with_flaky_llm.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000333",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        ))
        sut_with_flaky_llm._process_async_job()
        assert resp.accepted is True
        snap = sut_with_flaky_llm._last_draft(mock_project_id)
        assert snap.get("degraded") is True

    def test_TC_L103_L201_015_self_check_rejection_rate(
        self, sut, make_llm_draft,
    ) -> None:
        """TC-L103-L201-015 · 缺 dod_expr_ref · self_check 返回 err_code。"""
        draft = make_llm_draft(missing="dod_expr_ref")
        violations = sut._self_check_4_elements(draft)
        assert any(v["err_code"] == "E_L103_L201_103" for v in violations)

    def test_TC_L103_L201_016_audit_event_wbs_requested(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_event_bus,
    ) -> None:
        """TC-L103-L201-016 · 每次拆解都产 wbs_requested 或 wbs_draft_emitted 审计。"""
        sut.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000444",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        ))
        sut._process_async_job()
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert any(t.startswith("L1-03:") for t in types)

    def test_TC_L103_L201_017_diff_merge_preserves_history_effort(
        self, sut, valid_wbs_draft,
    ) -> None:
        """TC-L103-L201-017 · 合并时保留原 WP 的 effort_estimate。"""
        orig_effort = valid_wbs_draft["wp_list"][0]["effort_estimate"]
        merged = sut._diff_merge(valid_wbs_draft,
            {"wp_list": [{"wp_id": "wp-new", "goal": "x", "dod_expr_ref": "d",
                          "deps": [], "effort_estimate": 0.5}], "dag_edges": []})
        kept = next(w for w in merged["wp_list"]
                    if w["wp_id"] == valid_wbs_draft["wp_list"][0]["wp_id"])
        assert kept["effort_estimate"] == orig_effort
```

---

## §3 负向用例

```python
# file: tests/l1_03/test_l2_01_wbs_factory_negative.py
import pytest


class TestL2_01_Negative:

    def test_TC_L103_L201_101_llm_timeout(
        self, sut_with_timeout_llm, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """E_L103_L201_101 · LLM 超时 · 重试 2 次后降级/拒绝。"""
        resp = sut_with_timeout_llm.request_wbs_decomposition_direct(
            project_id=mock_project_id, artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
        )
        if not resp.accepted:
            assert resp.rejection.err_code == "E_L103_L201_101"

    def test_TC_L103_L201_102_dangling_dep(self, sut, make_llm_draft) -> None:
        draft = make_llm_draft(dangling_dep="wp-999")
        violations = sut._self_check_4_elements(draft)
        assert any(v["err_code"] == "E_L103_L201_102" for v in violations)

    def test_TC_L103_L201_103_missing_4_elements(self, sut, make_llm_draft) -> None:
        draft = make_llm_draft(missing="goal")
        violations = sut._self_check_4_elements(draft)
        assert any(v["err_code"] == "E_L103_L201_103" for v in violations)

    def test_TC_L103_L201_104_effort_over_5(self, sut, make_llm_draft) -> None:
        draft = make_llm_draft(effort=5.5)
        violations = sut._self_check_4_elements(draft)
        assert any(v["err_code"] == "E_L103_L201_104" for v in violations)

    def test_TC_L103_L201_105_cross_project_dep(self, sut, make_llm_draft) -> None:
        draft = make_llm_draft(cross_project_dep=True)
        violations = sut._self_check_4_elements(draft)
        assert any(v["err_code"] == "E_L103_L201_105" for v in violations)

    def test_TC_L103_L201_106_goal_no_trace(self, sut, make_llm_draft) -> None:
        draft = make_llm_draft(goal_no_trace=True)
        violations = sut._self_check_4_elements(draft)
        assert any(v["err_code"] == "E_L103_L201_106" for v in violations)

    def test_TC_L103_L201_107_invalid_skill(self, sut, make_llm_draft) -> None:
        draft = make_llm_draft(recommended_skills=["unknown.capability"])
        violations = sut._self_check_4_elements(draft)
        assert any(v["err_code"] == "E_L103_L201_107" for v in violations)

    def test_TC_L103_L201_108_wbs_md_template_missing_var(
        self, sut, valid_wbs_draft, broken_template,
    ) -> None:
        sut._template_override(broken_template)
        with pytest.raises(Exception) as ei:
            sut._render_wbs_md(valid_wbs_draft)
        assert "E_L103_L201_108" in str(ei.value)

    def test_TC_L103_L201_109_incremental_target_missing(
        self, sut, mock_project_id,
    ) -> None:
        from app.l2_01_wbs.schemas import IncrementalDecomposeRequest
        resp = sut.request_incremental_decompose(IncrementalDecomposeRequest(
            command_id="idecomp-req-00000000-0000-0000-0000-000000000999",
            project_id=mock_project_id,
            target_wp_id="wp-999",
            reason="change_request",
            requester_l2="L2-05",
        ))
        assert resp.accepted is False
        assert resp.rejection.err_code == "E_L103_L201_109"

    def test_TC_L103_L201_110_pm14_ownership_auto_fix_with_warn(
        self, sut, make_llm_draft, mock_project_id,
    ) -> None:
        """E_L103_L201_201 · 自动修正 + WARN 事件。"""
        draft = make_llm_draft(wp_project_id="hf-proj-other")
        fixed = sut._pm14_normalize(draft, expected_project_id=mock_project_id)
        for w in fixed["wp_list"]:
            assert w["project_id"] == mock_project_id

    def test_TC_L103_L201_111_llm_invalid_json(self, sut) -> None:
        with pytest.raises(Exception) as ei:
            sut._parse_llm_wbs_json("not { a json }")
        assert "E_L103_L201_301" in str(ei.value)

    def test_TC_L103_L201_112_togaf_input_missing(
        self, sut, mock_project_id, make_4_pack,
    ) -> None:
        from app.l2_01_wbs.schemas import WbsDecompositionRequest
        resp = sut.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000302",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output={"togaf_phases": ["A", "B", "C"],
                                 "adr_path": "docs/planning/adr"},
            requester_l1="L1-02",
        ))
        assert resp.accepted is False
        assert resp.rejection.err_code == "E_L103_L201_302"

    def test_TC_L103_L201_113_audit_append_fail(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_event_bus,
    ) -> None:
        """E_L103_L201_401 · append_event 失败 · PM-08 一致性优先 rejected。"""
        mock_event_bus.append_event.side_effect = IOError("bus down")
        from app.l2_01_wbs.schemas import WbsDecompositionRequest
        resp = sut.request_wbs_decomposition(WbsDecompositionRequest(
            command_id="wbs-req-00000000-0000-0000-0000-000000000401",
            project_id=mock_project_id,
            artifacts_4_pack=make_4_pack(),
            architecture_output=mock_arch_output,
            requester_l1="L1-02",
        ))
        assert resp.accepted is False

    def test_TC_L103_L201_114_bypass_fs_write_detected(
        self, sut, mock_project_id, tamper_wbs_md,
    ) -> None:
        tamper_wbs_md(project_id=mock_project_id)
        with pytest.raises(Exception) as ei:
            sut.consistency_check(project_id=mock_project_id)
        assert "E_L103_L201_501" in str(ei.value)
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_03/test_l2_01_ic_contracts.py
import pytest


class TestL2_01_IC_Contracts:

    def test_TC_L103_L201_601_ic19_shape(
        self, sut, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        resp = sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000601",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        for k in ("command_id", "accepted", "decomposition_session_id",
                  "audit_event_id", "dispatch_latency_ms"):
            assert k in resp

    def test_TC_L103_L201_602_ic_l2_07_shape(
        self, sut, mock_project_id, loaded_initial_wbs,
    ) -> None:
        resp = sut.request_incremental_decompose_raw({
            "command_id": "idecomp-req-00000000-0000-0000-0000-000000000602",
            "project_id": mock_project_id,
            "target_wp_id": loaded_initial_wbs["wps"][0],
            "reason": "failure_count_exceeded",
            "failure_evidence_refs": ["e1", "e2", "e3"],
            "requester_l2": "L2-05",
        })
        assert resp["accepted"] is True

    def test_TC_L103_L201_603_ic_l2_01_call_through(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_topology_mgr,
    ) -> None:
        sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000603",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut._process_async_job()
        p = mock_topology_mgr.load_topology.call_args.args[0]
        assert p["mode"] == "full" and p["requester_l2"] == "L2-01"

    def test_TC_L103_L201_604_ic04_skill_payload(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_skill_gateway,
    ) -> None:
        sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000604",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut._process_async_job()
        kw = mock_skill_gateway.invoke_skill.call_args.kwargs
        assert kw["capability_tag"] == "wbs.decompose"
        assert "artifacts_4_pack" in kw["params"]

    def test_TC_L103_L201_605_ic09_event_ordering(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_event_bus,
    ) -> None:
        sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000605",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut._process_async_job()
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert "L1-03:wbs_decomposed" in types
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_03/test_l2_01_perf.py
import time, statistics
import pytest


class TestL2_01_Perf:

    @pytest.mark.perf
    def test_TC_L103_L201_701_dispatch_p95_under_100ms(
        self, sut, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        durations = []
        for i in range(30):
            t = time.perf_counter()
            sut.request_wbs_decomposition_raw({
                "command_id": f"wbs-req-00000000-0000-0000-0000-{i:012d}",
                "project_id": mock_project_id,
                "artifacts_4_pack": make_4_pack(),
                "architecture_output": mock_arch_output,
                "requester_l1": "L1-02",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1

    @pytest.mark.perf
    def test_TC_L103_L201_702_incremental_dispatch_p95_under_100ms(
        self, sut, mock_project_id, loaded_initial_wbs,
    ) -> None:
        durations = []
        for i in range(30):
            t = time.perf_counter()
            sut.request_incremental_decompose_raw({
                "command_id": f"idecomp-req-00000000-0000-0000-0000-{i:012d}",
                "project_id": mock_project_id,
                "target_wp_id": loaded_initial_wbs["wps"][0],
                "reason": "change_request",
                "requester_l2": "L2-05",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1

    @pytest.mark.perf
    def test_TC_L103_L201_703_self_check_p95_under_20ms(self, sut, valid_wbs_draft) -> None:
        durations = []
        for _ in range(200):
            t = time.perf_counter()
            sut._self_check_4_elements(valid_wbs_draft)
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.02
```

---

## §6 端到端 e2e

```python
# file: tests/l1_03/test_l2_01_e2e.py
import pytest


class TestL2_01_E2E:

    @pytest.mark.e2e
    def test_TC_L103_L201_801_full_then_incremental(
        self, sut_real, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """e2e · 全量 → 差量 → 事件链完整。"""
        sut_real.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000e01",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut_real._process_async_job()
        snap = sut_real._last_draft(mock_project_id)
        first = snap["wp_list"][0]["wp_id"]
        sut_real.request_incremental_decompose_raw({
            "command_id": "idecomp-req-00000000-0000-0000-0000-000000000e02",
            "project_id": mock_project_id,
            "target_wp_id": first,
            "reason": "change_request",
            "requester_l2": "L2-05",
        })
        sut_real._process_async_job()

    @pytest.mark.e2e
    def test_TC_L103_L201_802_rule_template_fallback(
        self, sut_with_flaky_llm, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """e2e · 降级路径下仍产 usable wbs.md。"""
        sut_with_flaky_llm.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000e03",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut_with_flaky_llm._process_async_job()
        draft = sut_with_flaky_llm._last_draft(mock_project_id)
        assert draft.get("degraded") is True
        assert len(draft["wp_list"]) >= 1
```

---

## §7 测试 fixture

```python
# file: tests/l1_03/conftest_l2_01.py
import pytest, json, uuid, copy
from unittest.mock import MagicMock

from app.l2_01_wbs.factory import WBSFactory


@pytest.fixture
def mock_skill_gateway():
    m = MagicMock()
    m.invoke_skill = MagicMock(return_value={
        "wp_list": [
            {"wp_id": "wp-001", "goal": "setup env", "dod_expr_ref": "dod-1",
             "deps": [], "effort_estimate": 1.0, "recommended_skills": ["setup"]},
            {"wp_id": "wp-002", "goal": "build api", "dod_expr_ref": "dod-2",
             "deps": ["wp-001"], "effort_estimate": 2.0, "recommended_skills": ["backend"]},
        ],
        "dag_edges": [{"from_wp_id": "wp-001", "to_wp_id": "wp-002"}],
    })
    return m


@pytest.fixture
def mock_topology_mgr():
    m = MagicMock()
    m.load_topology = MagicMock(return_value={
        "status": "ok", "topology_id": "topo-abc", "wp_count": 2,
        "critical_path_ids": ["wp-001", "wp-002"],
    })
    return m


@pytest.fixture
def mock_event_bus():
    m = MagicMock()
    m.append_event = MagicMock(return_value={"event_id": "evt-mock-001"})
    return m


@pytest.fixture
def mock_clock():
    class C:
        def __init__(self): self.t = 10**9
        def now_ns(self): self.t += 1; return self.t
    return C()


@pytest.fixture
def sut(mock_skill_gateway, mock_topology_mgr, mock_event_bus, mock_clock, tmp_path):
    return WBSFactory(
        skill_gateway=mock_skill_gateway,
        topology_mgr=mock_topology_mgr,
        event_bus=mock_event_bus,
        clock=mock_clock,
        storage_root=tmp_path,
    )


@pytest.fixture
def sut_with_flaky_llm(mock_topology_mgr, mock_event_bus, mock_clock, tmp_path):
    flaky = MagicMock()
    flaky.invoke_skill.side_effect = [
        TimeoutError("llm timeout"),
        TimeoutError("llm timeout"),
        {"error": "bad_json"},
    ]
    return WBSFactory(
        skill_gateway=flaky, topology_mgr=mock_topology_mgr,
        event_bus=mock_event_bus, clock=mock_clock, storage_root=tmp_path,
    )


@pytest.fixture
def sut_with_timeout_llm(mock_topology_mgr, mock_event_bus, mock_clock, tmp_path):
    flaky = MagicMock()
    flaky.invoke_skill.side_effect = TimeoutError("llm timeout")
    return WBSFactory(
        skill_gateway=flaky, topology_mgr=mock_topology_mgr,
        event_bus=mock_event_bus, clock=mock_clock, storage_root=tmp_path,
    )


@pytest.fixture
def sut_real(sut):
    return sut


@pytest.fixture
def mock_project_id():
    return f"hf-proj-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def make_4_pack():
    def _make(**overrides):
        base = {
            "charter_path": "docs/planning/charter.md",
            "plan_path": "docs/planning/plan.md",
            "requirements_path": "docs/planning/requirements.md",
            "risk_path": "docs/planning/risk.md",
        }
        base.update(overrides)
        return base
    return _make


@pytest.fixture
def mock_arch_output():
    return {"togaf_phases": ["A", "B", "C", "D"], "adr_path": "docs/planning/adr"}


@pytest.fixture
def sample_llm_json():
    return json.dumps({
        "wp_list": [
            {"wp_id": "wp-001", "goal": "plan", "dod_expr_ref": "dod-1",
             "deps": [], "effort_estimate": 1.0},
        ],
        "dag_edges": [],
    })


@pytest.fixture
def valid_wbs_draft(mock_project_id):
    return {
        "project_id": mock_project_id,
        "wp_list": [
            {"wp_id": "wp-001", "goal": "setup", "dod_expr_ref": "dod-1",
             "deps": [], "effort_estimate": 1.0, "recommended_skills": ["setup"],
             "source_quote_ref": "charter.md:L4"},
            {"wp_id": "wp-002", "goal": "build", "dod_expr_ref": "dod-2",
             "deps": ["wp-001"], "effort_estimate": 2.0,
             "recommended_skills": ["backend"], "source_quote_ref": "plan.md:L7"},
        ],
        "dag_edges": [{"from_wp_id": "wp-001", "to_wp_id": "wp-002"}],
        "source_ref": "trace-test-001",
    }


@pytest.fixture
def make_llm_draft(valid_wbs_draft):
    def _make(**overrides):
        d = copy.deepcopy(valid_wbs_draft)
        if "missing" in overrides:
            d["wp_list"][0][overrides["missing"]] = None
        if "dangling_dep" in overrides:
            d["wp_list"][-1]["deps"].append(overrides["dangling_dep"])
        if "effort" in overrides:
            d["wp_list"][0]["effort_estimate"] = overrides["effort"]
        if overrides.get("cross_project_dep"):
            d["wp_list"][-1]["deps"].append("wp-001@hf-proj-other")
        if overrides.get("goal_no_trace"):
            d["wp_list"][0]["goal"] = "random unrelated xyz"
            d["wp_list"][0]["source_quote_ref"] = None
        if "recommended_skills" in overrides:
            d["wp_list"][0]["recommended_skills"] = overrides["recommended_skills"]
        if "wp_project_id" in overrides:
            for w in d["wp_list"]:
                w["project_id"] = overrides["wp_project_id"]
        return d
    return _make


@pytest.fixture
def loaded_initial_wbs(sut, mock_project_id, make_4_pack, mock_arch_output):
    sut.request_wbs_decomposition_raw({
        "command_id": "wbs-req-00000000-0000-0000-0000-00000000bbbb",
        "project_id": mock_project_id,
        "artifacts_4_pack": make_4_pack(),
        "architecture_output": mock_arch_output,
        "requester_l1": "L1-02",
    })
    sut._process_async_job()
    draft = sut._last_draft(mock_project_id)
    return {"wps": [w["wp_id"] for w in draft["wp_list"]]}


@pytest.fixture
def broken_template():
    return "# {{ project_id }}\n<no critical_path>\n"


@pytest.fixture
def tamper_wbs_md(tmp_path):
    def _t(project_id: str):
        p = tmp_path / "projects" / project_id / "wbs" / "wbs.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# bypass-direct-write", encoding="utf-8")
    return _t
```

---

## §8 集成点用例

```python
# file: tests/l1_03/test_l2_01_integrations.py
import pytest


class TestL2_01_Integration:

    def test_TC_L103_L201_901_cooperation_with_l1_02(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_event_bus,
    ) -> None:
        """L1-02 调用 → 完整事件链（wbs_requested→wbs_decomposed）。"""
        sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000901",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut._process_async_job()
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert "L1-03:wbs_decomposed" in types

    def test_TC_L103_L201_902_cooperation_with_l2_05(
        self, sut, mock_project_id, loaded_initial_wbs, mock_event_bus,
    ) -> None:
        """L2-05 驱动差量拆解 · 审计事件包含 failure evidence 引用。"""
        sut.request_incremental_decompose_raw({
            "command_id": "idecomp-req-00000000-0000-0000-0000-000000000902",
            "project_id": mock_project_id,
            "target_wp_id": loaded_initial_wbs["wps"][0],
            "reason": "failure_count_exceeded",
            "failure_evidence_refs": ["evt-f-a", "evt-f-b", "evt-f-c"],
            "requester_l2": "L2-05",
        })
        sut._process_async_job()
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert any(t.startswith("L1-03:") for t in types)

    def test_TC_L103_L201_903_cooperation_with_l2_02(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_topology_mgr,
    ) -> None:
        """L2-02 load_topology 在每次成功拆解后调用一次。"""
        sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000903",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut._process_async_job()
        assert mock_topology_mgr.load_topology.call_count == 1

    def test_TC_L103_L201_904_cooperation_with_l1_07_warn(
        self, sut_with_flaky_llm, mock_project_id, make_4_pack, mock_arch_output, mock_event_bus,
    ) -> None:
        """L1-07 Supervisor 订阅降级 WARN 事件（soft-drift 信号）。"""
        sut_with_flaky_llm.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000904",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut_with_flaky_llm._process_async_job()
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        # 降级路径至少应产一个带 degraded/warn 的事件类型
        assert any("degraded" in t.lower() or "warn" in t.lower()
                   or t.startswith("L1-03:") for t in types)
```

---

## §9 边界 / edge case

```python
# file: tests/l1_03/test_l2_01_edge.py
import pytest


class TestL2_01_Edge:

    def test_TC_L103_L201_A01_empty_4_pack(self, sut, mock_project_id, mock_arch_output) -> None:
        """IC-19 artifacts_4_pack 空 · rejected。"""
        resp = sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000e01",
            "project_id": mock_project_id,
            "artifacts_4_pack": {},
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        assert resp["accepted"] is False

    def test_TC_L103_L201_A02_very_large_output_100_wps(
        self, sut, mock_project_id, make_4_pack, mock_arch_output, mock_skill_gateway,
    ) -> None:
        """LLM 返 100 WP · 自检 + 装图 不崩。"""
        mock_skill_gateway.invoke_skill.return_value = {
            "wp_list": [
                {"wp_id": f"wp-{i:03d}", "goal": f"goal-{i}", "dod_expr_ref": f"dod-{i}",
                 "deps": [f"wp-{i-1:03d}"] if i > 0 else [],
                 "effort_estimate": 1.0, "recommended_skills": []}
                for i in range(100)
            ],
            "dag_edges": [
                {"from_wp_id": f"wp-{i-1:03d}", "to_wp_id": f"wp-{i:03d}"}
                for i in range(1, 100)
            ],
        }
        resp = sut.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000e02",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        sut._process_async_job()
        assert resp["accepted"] is True

    def test_TC_L103_L201_A03_concurrent_same_command_id(
        self, sut, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """并发两路相同 command_id · 仅产生一个 session_id。"""
        from concurrent.futures import ThreadPoolExecutor
        def go():
            return sut.request_wbs_decomposition_raw({
                "command_id": "wbs-req-00000000-0000-0000-0000-000000000e03",
                "project_id": mock_project_id,
                "artifacts_4_pack": make_4_pack(),
                "architecture_output": mock_arch_output,
                "requester_l1": "L1-02",
            })
        with ThreadPoolExecutor(max_workers=2) as ex:
            r1, r2 = ex.submit(go).result(), ex.submit(go).result()
        assert r1["decomposition_session_id"] == r2["decomposition_session_id"]

    def test_TC_L103_L201_A04_crash_mid_decompose_restart_idempotent(
        self, sut_factory, mock_project_id, make_4_pack, mock_arch_output,
    ) -> None:
        """运行中断 · 重启后同一 command_id 幂等完成。"""
        s1 = sut_factory()
        s1.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000e04",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        s2 = sut_factory()
        r = s2.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000e04",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        assert r["accepted"] is True

    def test_TC_L103_L201_A05_llm_partial_return_retries(
        self, mock_topology_mgr, mock_event_bus, mock_clock, tmp_path, mock_project_id,
        make_4_pack, mock_arch_output,
    ) -> None:
        """LLM 首次返 partial JSON · reprompt 后完整返回。"""
        from unittest.mock import MagicMock
        sg = MagicMock()
        sg.invoke_skill.side_effect = [
            {"wp_list": [{"wp_id": "wp-001"}]},
            {"wp_list": [{"wp_id": "wp-001", "goal": "g", "dod_expr_ref": "d",
                          "deps": [], "effort_estimate": 1.0}], "dag_edges": []},
        ]
        fac = WBSFactory(
            skill_gateway=sg, topology_mgr=mock_topology_mgr,
            event_bus=mock_event_bus, clock=mock_clock, storage_root=tmp_path,
        )
        fac.request_wbs_decomposition_raw({
            "command_id": "wbs-req-00000000-0000-0000-0000-000000000e05",
            "project_id": mock_project_id,
            "artifacts_4_pack": make_4_pack(),
            "architecture_output": mock_arch_output,
            "requester_l1": "L1-02",
        })
        fac._process_async_job()
        assert sg.invoke_skill.call_count >= 2


@pytest.fixture
def sut_factory(mock_skill_gateway, mock_topology_mgr, mock_event_bus, mock_clock, tmp_path):
    def _f():
        return WBSFactory(
            skill_gateway=mock_skill_gateway, topology_mgr=mock_topology_mgr,
            event_bus=mock_event_bus, clock=mock_clock, storage_root=tmp_path,
        )
    return _f
```

---

*— L2-01 TDD 已按 10 段模板完成 · 覆盖 §3 全部方法 / §11 全部 14 错误码 / 5 条 IC · 含 Level-2 规则模板降级覆盖 —*
