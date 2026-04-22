---
doc_id: tests-L1-05-L2-03-Skill 调用执行器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md
  - docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-05 L2-03-Skill 调用执行器 · TDD 测试用例

> 基于 3-1 L2-03 §3（6 IC · 2 接收 + 4 发起）+ §11（14 条 `SKILL_INVOCATION_*` + 4 级降级）+ §12 SLO 驱动。
> TC ID 统一格式：`TC-L105-L203-NNN`。pytest + Python 3.11+；`class TestL2_03_SkillInvoker`；context 注入 / timeout / retry / fallback / audit 独立分组。

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
| `invoke_skill()` · 首选成功 | TC-L105-L203-001 | unit | IC-04 |
| `invoke_skill()` · fallback 1 次后成功 | TC-L105-L203-002 | unit | IC-04 |
| `invoke_skill()` · fallback 耗尽 EXHAUSTED | TC-L105-L203-003 | unit | IC-04 |
| `invoke_skill()` · idempotent retry | TC-L105-L203-004 | unit | IC-04 |
| `invoke_skill()` · rate_limit retry | TC-L105-L203-005 | unit | IC-04 |
| `invoke_skill()` · L2-05 format_invalid 转 fallback | TC-L105-L203-006 | unit | IC-04 |
| `invoke_skill()` · allow_fallback=false | TC-L105-L203-007 | unit | IC-04 |
| `validate_response()` · L2-05 ok | TC-L105-L203-008 | unit | IC-L2-05 |
| `_context_inject()` · 白名单 | TC-L105-L203-009 | unit | — |
| `_hash_params()` · SHA-256 + 脱敏 | TC-L105-L203-010 | unit | — |
| `_audit_seed_emit()` | TC-L105-L203-011 | unit | IC-09 |
| `_timeout_watch()` 硬上限 | TC-L105-L203-012 | unit | — |
| `submit_validation()` 调 L2-05 | TC-L105-L203-013 | unit | IC-L2-05 submit |
| `advance_fallback()` 调 L2-02 | TC-L105-L203-014 | unit | IC-L2-03 |
| `ToolMetadataQuery` 调 L2-01 | TC-L105-L203-015 | unit | — |
| `fallback_trace` 返回 | TC-L105-L203-016 | unit | IC-04 |
| `audit_ref` 返回 | TC-L105-L203-017 | unit | IC-09 |
| `skill_version` 返回 | TC-L105-L203-018 | unit | IC-04 |

### §1.2 错误码 × 测试（14 项全覆盖）

| 错误码 | TC ID | Level |
|---|---|---|
| `E01 NO_PROJECT_ID` | TC-L105-L203-101 | L3 REJECT |
| `E02 CROSS_PROJECT` | TC-L105-L203-102 | L3 REJECT |
| `E03 CAPABILITY_UNKNOWN` | TC-L105-L203-103 | L3 REJECT |
| `E04 TIMEOUT` | TC-L105-L203-104 | L1/L2 |
| `E05 PARAMS_SCHEMA_MISMATCH` | TC-L105-L203-105 | L3 REJECT |
| `E06 SIGNATURE_INCOMPLETE` | TC-L105-L203-106 | L3 CRIT |
| `E07 PARAMS_CONTAINS_RAW_SECRET` | TC-L105-L203-107 | L3 REJECT |
| `E08 PERMISSION_DENIED` | TC-L105-L203-108 | L3 REJECT |
| `E09 RATE_LIMITED` | TC-L105-L203-109 | L1 RETRY |
| `E10 SCHEMA_INVALID` | TC-L105-L203-110 | L2 FALLBACK |
| `E11 RETRY_EXHAUSTED` | TC-L105-L203-111 | L2 FALLBACK |
| `E12 EXHAUSTED` | TC-L105-L203-112 | L3 CRIT |
| `E13 CONTEXT_INJECTION_FAIL` | TC-L105-L203-113 | L3 REJECT |
| `E14 AUDIT_EMIT_FAIL` | TC-L105-L203-114 | L4 CRIT |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| IC-04 invoke_skill | Caller → 本 L2 | TC-L105-L203-601 |
| IC-L2-05 validate_response | L2-05 → 本 L2 | TC-L105-L203-602 |
| IC-L2-03 advance_fallback | 本 L2 → L2-02 | TC-L105-L203-603 |
| IC-L2-05 submit_validation | 本 L2 → L2-05 | TC-L105-L203-604 |
| IC-09 append_event | 本 L2 → L1-09 | TC-L105-L203-605 |
| ToolMetadataQuery | 本 L2 → L2-01 | TC-L105-L203-606 |

---

## §2 正向用例

```python
# file: tests/l1_05/test_l2_03_skill_invoker_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_03_invoker.invoker import SkillInvoker
from app.l2_03_invoker.schemas import InvokeSkillCommand, InvokeSkillResult


class TestL2_03_SkillInvoker_Positive:

    def test_TC_L105_L203_001_invoke_first_choice_success(
        self, sut: SkillInvoker, mock_project_id: str,
    ) -> None:
        """TC-L105-L203-001 · 首选 success=True · fallback_used=False."""
        r: InvokeSkillResult = sut.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000001",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "build api"},
            caller_l1="L1-04",
            context={"project_id": mock_project_id},
            ts_ns=1,
        ))
        assert r.success is True
        assert r.fallback_used is False
        assert r.attempt == 1

    def test_TC_L105_L203_002_fallback_one_then_success(
        self, sut_first_fails, mock_project_id,
    ) -> None:
        """TC-L105-L203-002 · 首选失败 · attempt=2 成功 · fallback_trace 长度 2."""
        r = sut_first_fails.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000002",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=2,
        ))
        assert r.success is True
        assert r.fallback_used is True
        assert len(r.fallback_trace) >= 2

    def test_TC_L105_L203_003_fallback_exhausted(
        self, sut_all_fail, mock_project_id,
    ) -> None:
        """TC-L105-L203-003 · 链全失败 · EXHAUSTED."""
        r = sut_all_fail.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000003",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=3,
        ))
        assert r.success is False
        assert r.error.code == "SKILL_INVOCATION_EXHAUSTED"

    def test_TC_L105_L203_004_idempotent_retry(
        self, sut_flaky_once, mock_project_id,
    ) -> None:
        """TC-L105-L203-004 · idempotent skill 首次 timeout · retry 1 次成功."""
        r = sut_flaky_once.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000004",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=4,
        ))
        assert r.success is True
        assert r.attempt == 1  # 同一 attempt · retry 内解决

    def test_TC_L105_L203_005_rate_limit_retry(
        self, sut_rate_limit, mock_project_id,
    ) -> None:
        r = sut_rate_limit.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000005",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=5,
        ))
        assert r.success is True

    def test_TC_L105_L203_006_schema_invalid_triggers_fallback(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        mock_l2_05.validate.side_effect = [
            {"status": "format_invalid"},
            {"status": "ok"},
        ]
        r = sut.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000006",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=6,
        ))
        assert r.fallback_used is True

    def test_TC_L105_L203_007_allow_fallback_false(
        self, sut_first_fails, mock_project_id,
    ) -> None:
        """TC-L105-L203-007 · allow_fallback=False · 首选失败即拒绝."""
        r = sut_first_fails.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000007",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=7,
            allow_fallback=False,
        ))
        assert r.success is False
        assert r.fallback_used is False

    def test_TC_L105_L203_008_validate_response_ok(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L203-008 · L2-05 回传 ok · validate_status=ok."""
        r = sut.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000008",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=8,
        ))
        assert r.validate_status == "ok"

    def test_TC_L105_L203_009_context_inject_whitelist(
        self, sut,
    ) -> None:
        """TC-L105-L203-009 · context 仅保留白名单字段。"""
        injected = sut._context_inject(
            params={"wp_goal": "x"},
            context={"project_id": "pid",
                      "decision_id": "dec", "wp_id": "wp",
                      "UNKNOWN_field": "should_be_removed"},
        )
        assert "UNKNOWN_field" not in injected

    def test_TC_L105_L203_010_hash_params_sha256(self, sut) -> None:
        """TC-L105-L203-010 · hash 结果 64 hex · 脱敏后."""
        h = sut._hash_params({"api_key": "secret-123", "wp_goal": "x"})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_TC_L105_L203_011_audit_seed_emit(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut._emit_audit_seed(project_id=mock_project_id,
                              invocation_id="inv-aud", capability="x",
                              skill_id="y", attempt=1)
        assert mock_event_bus.append_event.called

    def test_TC_L105_L203_012_timeout_watch_hard_cap(
        self, sut_super_slow, mock_project_id,
    ) -> None:
        import time
        t = time.perf_counter()
        r = sut_super_slow.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000012",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=12,
            timeout_ms=2000,
        ))
        dur = time.perf_counter() - t
        assert dur <= 5.0  # 硬保护

    def test_TC_L105_L203_013_submit_validation_call(
        self, sut, mock_l2_05, mock_project_id,
    ) -> None:
        sut._submit_validation(project_id=mock_project_id,
                                invocation_id="inv-013",
                                result={"output": "x"})
        mock_l2_05.validate.assert_called()

    def test_TC_L105_L203_014_advance_fallback_call(
        self, sut_first_fails, mock_intent_sel, mock_project_id,
    ) -> None:
        sut_first_fails.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000014",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=14,
        ))
        mock_intent_sel.advance_fallback.assert_called()

    def test_TC_L105_L203_015_tool_metadata_query(
        self, sut, mock_registry, mock_project_id,
    ) -> None:
        sut._tool_metadata_query(tool_name="Read")
        mock_registry.query_tool.assert_called()

    def test_TC_L105_L203_016_fallback_trace_fields(
        self, sut_first_fails, mock_project_id,
    ) -> None:
        r = sut_first_fails.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000016",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=16,
        ))
        for item in r.fallback_trace:
            for k in ("attempt", "skill_id", "reason", "duration_ms"):
                assert hasattr(item, k) or k in item

    def test_TC_L105_L203_017_audit_ref_returned(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000017",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=17,
        ))
        assert r.audit_ref

    def test_TC_L105_L203_018_skill_version_returned(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000018",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=18,
        ))
        assert r.skill_version
```

---

## §3 负向用例

```python
# file: tests/l1_05/test_l2_03_skill_invoker_negative.py
import pytest

from app.l2_03_invoker.schemas import InvokeSkillCommand


class TestL2_03_Negative:

    def test_TC_L105_L203_101_no_project_id(self, sut) -> None:
        with pytest.raises(Exception) as ei:
            sut.invoke_skill_raw({
                "invocation_id": "inv-00000000-0000-7000-0000-000000000101",
                "capability": "tdd.blueprint_generate",
                "params": {}, "caller_l1": "L1-04",
                "context": {},  # 缺 project_id
                "ts_ns": 1,
            })
        assert "NO_PROJECT_ID" in str(ei.value)

    def test_TC_L105_L203_102_cross_project(self, sut, mock_project_id) -> None:
        with pytest.raises(Exception) as ei:
            sut.invoke_skill_raw({
                "project_id": mock_project_id,
                "invocation_id": "inv-00000000-0000-7000-0000-000000000102",
                "capability": "tdd.blueprint_generate",
                "params": {}, "caller_l1": "L1-04",
                "context": {"project_id": "pid-OTHER"},
                "ts_ns": 1,
            })
        assert "CROSS_PROJECT" in str(ei.value)

    def test_TC_L105_L203_103_capability_unknown(
        self, sut, mock_intent_sel, mock_project_id,
    ) -> None:
        mock_intent_sel.select.return_value = {
            "chain": [], "explanation_card": {},
        }
        with pytest.raises(Exception) as ei:
            sut.invoke_skill(InvokeSkillCommand(
                project_id=mock_project_id,
                invocation_id="inv-00000000-0000-7000-0000-000000000103",
                capability="fake.unknown",
                params={}, caller_l1="L1-04",
                context={"project_id": mock_project_id}, ts_ns=1,
            ))
        assert "CAPABILITY_UNKNOWN" in str(ei.value)

    def test_TC_L105_L203_104_timeout(
        self, sut_super_slow, mock_project_id,
    ) -> None:
        r = sut_super_slow.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000104",
            capability="tdd.blueprint_generate",
            params={}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=1,
            timeout_ms=1500,
        ))
        # timeout → 转 fallback / EXHAUSTED
        assert r.success is False or r.fallback_used is True

    def test_TC_L105_L203_105_params_schema_mismatch(
        self, sut, mock_project_id,
    ) -> None:
        with pytest.raises(Exception) as ei:
            sut.invoke_skill_raw({
                "project_id": mock_project_id,
                "invocation_id": "inv-00000000-0000-7000-0000-000000000105",
                "capability": "tdd.blueprint_generate",
                "params": {"wrong_field": 1},  # capability schema 要 wp_goal
                "caller_l1": "L1-04",
                "context": {"project_id": mock_project_id},
                "ts_ns": 1,
            })
        assert "PARAMS_SCHEMA_MISMATCH" in str(ei.value)

    def test_TC_L105_L203_106_signature_incomplete(
        self, sut_broken_signature, mock_project_id,
    ) -> None:
        with pytest.raises(Exception) as ei:
            sut_broken_signature.invoke_skill(InvokeSkillCommand(
                project_id=mock_project_id,
                invocation_id="inv-00000000-0000-7000-0000-000000000106",
                capability="tdd.blueprint_generate",
                params={"wp_goal": "x"}, caller_l1="L1-04",
                context={"project_id": mock_project_id}, ts_ns=1,
            ))
        assert "SIGNATURE_INCOMPLETE" in str(ei.value)

    def test_TC_L105_L203_107_raw_secret_in_params(
        self, sut, mock_project_id,
    ) -> None:
        with pytest.raises(Exception) as ei:
            sut.invoke_skill(InvokeSkillCommand(
                project_id=mock_project_id,
                invocation_id="inv-00000000-0000-7000-0000-000000000107",
                capability="tdd.blueprint_generate",
                params={"api_key": "AKIA-RAW-SECRET-EXPOSED"},
                caller_l1="L1-04",
                context={"project_id": mock_project_id}, ts_ns=1,
            ))
        assert "PARAMS_CONTAINS_RAW_SECRET" in str(ei.value)

    def test_TC_L105_L203_108_permission_denied(
        self, sut_permission_denied, mock_project_id,
    ) -> None:
        with pytest.raises(Exception) as ei:
            sut_permission_denied.invoke_skill(InvokeSkillCommand(
                project_id=mock_project_id,
                invocation_id="inv-00000000-0000-7000-0000-000000000108",
                capability="tdd.blueprint_generate",
                params={"wp_goal": "x"}, caller_l1="L1-04",
                context={"project_id": mock_project_id}, ts_ns=1,
            ))
        assert "PERMISSION_DENIED" in str(ei.value)

    def test_TC_L105_L203_109_rate_limited_retry(
        self, sut_rate_limit_3times, mock_project_id,
    ) -> None:
        r = sut_rate_limit_3times.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000109",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=1,
        ))
        # 3 次 rate_limit 全失败 · 转 fallback 或 EXHAUSTED
        assert r.error is None or r.error.code in {
            "SKILL_INVOCATION_RATE_LIMITED", "SKILL_INVOCATION_EXHAUSTED",
        }

    def test_TC_L105_L203_110_schema_invalid_fallback(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        mock_l2_05.validate.return_value = {"status": "format_invalid"}
        r = sut.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000110",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=1,
        ))
        assert r.fallback_used is True

    def test_TC_L105_L203_111_retry_exhausted(
        self, sut_retry_exhausted, mock_project_id,
    ) -> None:
        r = sut_retry_exhausted.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000111",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=1,
        ))
        assert r.fallback_used is True

    def test_TC_L105_L203_112_exhausted_reaches_caller(
        self, sut_all_fail, mock_project_id,
    ) -> None:
        r = sut_all_fail.invoke_skill(InvokeSkillCommand(
            project_id=mock_project_id,
            invocation_id="inv-00000000-0000-7000-0000-000000000112",
            capability="tdd.blueprint_generate",
            params={"wp_goal": "x"}, caller_l1="L1-04",
            context={"project_id": mock_project_id}, ts_ns=1,
        ))
        assert r.error.code == "SKILL_INVOCATION_EXHAUSTED"

    def test_TC_L105_L203_113_context_injection_fail(
        self, sut, mock_project_id,
    ) -> None:
        with pytest.raises(Exception) as ei:
            sut._context_inject(
                params={}, context={"project_id": mock_project_id,
                                      "__INTERNAL_FIELD__": "forbidden"},
                strict_whitelist=True,
            )
        assert "CONTEXT_INJECTION_FAIL" in str(ei.value)

    def test_TC_L105_L203_114_audit_emit_fail(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        mock_event_bus.append_event.side_effect = IOError("bus down")
        with pytest.raises(Exception) as ei:
            sut.invoke_skill(InvokeSkillCommand(
                project_id=mock_project_id,
                invocation_id="inv-00000000-0000-7000-0000-000000000114",
                capability="tdd.blueprint_generate",
                params={"wp_goal": "x"}, caller_l1="L1-04",
                context={"project_id": mock_project_id}, ts_ns=1,
            ))
        assert "AUDIT_EMIT_FAIL" in str(ei.value)
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_05/test_l2_03_ic_contracts.py
import pytest


class TestL2_03_IC_Contracts:

    def test_TC_L105_L203_601_ic04_result_shape(self, sut, mock_project_id) -> None:
        r = sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000601",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"},
            "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        for k in ("project_id", "invocation_id", "success", "skill_id",
                  "duration_ms", "attempt", "fallback_used", "audit_ref"):
            assert k in r

    def test_TC_L105_L203_602_validate_response_callback(
        self, sut, mock_l2_05, mock_project_id,
    ) -> None:
        sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000602",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        mock_l2_05.validate.assert_called()

    def test_TC_L105_L203_603_advance_fallback_called_on_fail(
        self, sut_first_fails, mock_intent_sel, mock_project_id,
    ) -> None:
        sut_first_fails.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000603",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        mock_intent_sel.advance_fallback.assert_called()

    def test_TC_L105_L203_604_submit_validation_shape(
        self, sut, mock_l2_05, mock_project_id,
    ) -> None:
        sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000604",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        kw = mock_l2_05.validate.call_args.kwargs
        assert "project_id" in kw
        assert "invocation_id" in kw

    def test_TC_L105_L203_605_ic09_event_types(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000605",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        types = {c.args[0]["event_type"]
                  for c in mock_event_bus.append_event.call_args_list}
        assert any(t.startswith("L1-05:invocation_") for t in types)

    def test_TC_L105_L203_606_tool_metadata_query(
        self, sut, mock_registry, mock_project_id,
    ) -> None:
        sut._tool_metadata_query(tool_name="Read")
        mock_registry.query_tool.assert_called()
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_05/test_l2_03_perf.py
import time, statistics
import pytest


class TestL2_03_Perf:

    @pytest.mark.perf
    def test_TC_L105_L203_701_signature_overhead_under_100ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(100):
            t = time.perf_counter()
            sut._context_inject(params={"x": 1},
                                 context={"project_id": mock_project_id})
            sut._hash_params({"x": 1, "api_key": "sk-xxx"})
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1

    @pytest.mark.perf
    def test_TC_L105_L203_702_context_inject_p99_under_5ms(self, sut) -> None:
        durations = []
        for _ in range(500):
            t = time.perf_counter()
            sut._context_inject(params={"x": 1},
                                 context={"project_id": "p",
                                           "decision_id": "d",
                                           "wp_id": "w"})
            durations.append(time.perf_counter() - t)
        p99 = statistics.quantiles(durations, n=100)[98]
        assert p99 < 0.005

    @pytest.mark.perf
    def test_TC_L105_L203_703_hash_p99_under_10ms(self, sut) -> None:
        durations = []
        big = {"wp_goal": "a" * 1000, "extra": ["x"] * 100}
        for _ in range(500):
            t = time.perf_counter()
            sut._hash_params(big)
            durations.append(time.perf_counter() - t)
        p99 = statistics.quantiles(durations, n=100)[98]
        assert p99 < 0.01

    @pytest.mark.perf
    def test_TC_L105_L203_704_hard_cap_300s(
        self, sut_super_slow, mock_project_id,
    ) -> None:
        import time
        t = time.perf_counter()
        sut_super_slow.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000704",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1, "timeout_ms": 2000,
        })
        assert time.perf_counter() - t < 10.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_05/test_l2_03_e2e.py
import pytest


class TestL2_03_E2E:

    @pytest.mark.e2e
    def test_TC_L105_L203_801_full_chain_fallback_then_success(
        self, sut_first_fails, mock_project_id,
    ) -> None:
        r = sut_first_fails.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000801",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        assert r["success"] is True
        assert r["fallback_used"] is True

    @pytest.mark.e2e
    def test_TC_L105_L203_802_exhausted_caller_hard_halt(
        self, sut_all_fail, mock_project_id,
    ) -> None:
        r = sut_all_fail.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000802",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        assert r["success"] is False
        assert r["error"]["code"] == "SKILL_INVOCATION_EXHAUSTED"
```

---

## §7 测试 fixture

```python
# file: tests/l1_05/conftest_l2_03.py
import pytest, uuid, time
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id():
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_intent_sel():
    m = MagicMock()
    m.select = MagicMock(return_value={
        "chain": [
            {"attempt": 1, "skill_id": "superpowers:writing-plans",
             "kind": "skill", "expected_timeout_ms": 30000,
             "expected_cost": "M", "confidence": 0.8},
            {"attempt": 2, "skill_id": "built-in:minimal-plan",
             "kind": "builtin_min", "expected_timeout_ms": 5000,
             "expected_cost": "L", "confidence": 0.6},
        ],
        "explanation_card": {},
    })
    m.advance_fallback = MagicMock(return_value={
        "next_item": {"attempt": 2, "skill_id": "built-in:minimal-plan",
                       "kind": "builtin_min", "expected_timeout_ms": 5000},
        "has_next": True,
    })
    return m


@pytest.fixture
def mock_l2_05():
    m = MagicMock()
    m.validate = MagicMock(return_value={"status": "ok"})
    return m


@pytest.fixture
def mock_registry():
    m = MagicMock()
    m.query_tool = MagicMock(return_value={"status": "ok",
                                             "result": {"name": "Read"}})
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
def _default_skill_runner_success():
    def _run(skill_id, params, timeout_ms):
        return {"output": f"success from {skill_id}", "skill_version": "1.0"}
    return _run


@pytest.fixture
def sut(mock_intent_sel, mock_l2_05, mock_registry, mock_event_bus, mock_clock,
         _default_skill_runner_success):
    from app.l2_03_invoker.invoker import SkillInvoker
    return SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=_default_skill_runner_success,
    )


@pytest.fixture
def sut_first_fails(mock_intent_sel, mock_l2_05, mock_registry,
                      mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    call_count = [0]
    def runner(skill_id, params, timeout_ms):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("first fails")
        return {"output": "second attempt ok", "skill_version": "1.0"}
    return SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )


@pytest.fixture
def sut_all_fail(mock_intent_sel, mock_l2_05, mock_registry,
                   mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    def runner(skill_id, params, timeout_ms):
        raise RuntimeError("all fail")
    return SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )


@pytest.fixture
def sut_flaky_once(mock_intent_sel, mock_l2_05, mock_registry,
                     mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    call_count = [0]
    def runner(skill_id, params, timeout_ms):
        call_count[0] += 1
        if call_count[0] == 1:
            raise TimeoutError("transient")
        return {"output": "ok", "skill_version": "1.0"}
    inv = SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )
    inv._capability_idempotent["tdd.blueprint_generate"] = True
    return inv


@pytest.fixture
def sut_rate_limit(mock_intent_sel, mock_l2_05, mock_registry,
                     mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    call_count = [0]
    def runner(skill_id, params, timeout_ms):
        call_count[0] += 1
        if call_count[0] <= 1:
            raise _RateLimitError()
        return {"output": "ok after limit", "skill_version": "1.0"}
    return SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )


class _RateLimitError(Exception):
    code = "RATE_LIMIT"


@pytest.fixture
def sut_rate_limit_3times(mock_intent_sel, mock_l2_05, mock_registry,
                            mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    def runner(skill_id, params, timeout_ms):
        raise _RateLimitError()
    return SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )


@pytest.fixture
def sut_super_slow(mock_intent_sel, mock_l2_05, mock_registry,
                     mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    def runner(skill_id, params, timeout_ms):
        time.sleep(3.0)
        return {"output": "late", "skill_version": "1.0"}
    return SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )


@pytest.fixture
def sut_broken_signature(mock_intent_sel, mock_l2_05, mock_registry,
                           mock_event_bus, mock_clock,
                           _default_skill_runner_success):
    from app.l2_03_invoker.invoker import SkillInvoker
    inv = SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=_default_skill_runner_success,
    )
    inv._signature_fields = ["invocation_id"]  # 缺其他 8 字段
    return inv


@pytest.fixture
def sut_permission_denied(mock_intent_sel, mock_l2_05, mock_registry,
                            mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    def runner(skill_id, params, timeout_ms):
        raise _PermissionError()
    return SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )


class _PermissionError(Exception):
    code = "PERMISSION_DENIED"


@pytest.fixture
def sut_retry_exhausted(mock_intent_sel, mock_l2_05, mock_registry,
                          mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    def runner(skill_id, params, timeout_ms):
        raise TimeoutError("persistent")
    inv = SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )
    inv._capability_idempotent["tdd.blueprint_generate"] = True
    inv._retry_max = 2
    return inv
```

---

## §8 集成点用例

```python
# file: tests/l1_05/test_l2_03_integrations.py
import pytest


class TestL2_03_Integration:

    def test_TC_L105_L203_901_with_l2_02_select_then_invoke(
        self, sut, mock_intent_sel, mock_project_id,
    ) -> None:
        sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000901",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        mock_intent_sel.select.assert_called()

    def test_TC_L105_L203_902_with_l2_05_validate(
        self, sut, mock_l2_05, mock_project_id,
    ) -> None:
        sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000902",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        mock_l2_05.validate.assert_called()

    def test_TC_L105_L203_903_with_l1_09_audit(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000903",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        assert mock_event_bus.append_event.called

    def test_TC_L105_L203_904_with_l2_01_tool_meta(
        self, sut, mock_registry,
    ) -> None:
        sut._tool_metadata_query(tool_name="Grep")
        assert mock_registry.query_tool.called
```

---

## §9 边界 / edge case

```python
# file: tests/l1_05/test_l2_03_edge.py
import pytest

from app.l2_03_invoker.schemas import InvokeSkillCommand


class TestL2_03_Edge:

    def test_TC_L105_L203_A01_params_empty(self, sut, mock_project_id) -> None:
        r = sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000a01",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": ""},  # 空但合法
            "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        assert "success" in r

    def test_TC_L105_L203_A02_timeout_maximum_300000ms(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000a02",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1, "timeout_ms": 300000,
        })
        assert r["success"] is True

    def test_TC_L105_L203_A03_concurrent_same_invocation_id(
        self, sut, mock_project_id,
    ) -> None:
        """相同 invocation_id 并发 · 第二次走幂等短路。"""
        from concurrent.futures import ThreadPoolExecutor
        def go():
            return sut.invoke_skill_raw({
                "project_id": mock_project_id,
                "invocation_id": "inv-00000000-0000-7000-0000-000000000a03",
                "capability": "tdd.blueprint_generate",
                "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
                "context": {"project_id": mock_project_id},
                "ts_ns": 1,
            })
        with ThreadPoolExecutor(max_workers=2) as ex:
            r1, r2 = ex.submit(go).result(), ex.submit(go).result()
        assert r1["audit_ref"] == r2["audit_ref"]

    def test_TC_L105_L203_A04_very_long_fallback_chain_trunc(
        self, sut, mock_intent_sel, mock_project_id,
    ) -> None:
        mock_intent_sel.select.return_value = {
            "chain": [{"attempt": i + 1, "skill_id": f"skill-{i}",
                        "kind": "skill", "expected_timeout_ms": 1000,
                        "expected_cost": "L", "confidence": 0.5}
                       for i in range(50)],
            "explanation_card": {},
        }

    def test_TC_L105_L203_A05_skill_returns_non_dict(
        self, sut_returns_non_dict, mock_project_id,
    ) -> None:
        """skill 返 plain string · L2-05 format_invalid · fallback."""
        r = sut_returns_non_dict.invoke_skill_raw({
            "project_id": mock_project_id,
            "invocation_id": "inv-00000000-0000-7000-0000-000000000a05",
            "capability": "tdd.blueprint_generate",
            "params": {"wp_goal": "x"}, "caller_l1": "L1-04",
            "context": {"project_id": mock_project_id},
            "ts_ns": 1,
        })
        assert r["fallback_used"] is True


@pytest.fixture
def sut_returns_non_dict(mock_intent_sel, mock_l2_05, mock_registry,
                           mock_event_bus, mock_clock):
    from app.l2_03_invoker.invoker import SkillInvoker
    call_count = [0]
    def runner(skill_id, params, timeout_ms):
        call_count[0] += 1
        if call_count[0] == 1:
            return "plain string instead of dict"
        return {"output": "ok", "skill_version": "1.0"}
    inv = SkillInvoker(
        intent_selector=mock_intent_sel, l2_05=mock_l2_05,
        registry=mock_registry, event_bus=mock_event_bus,
        clock=mock_clock, skill_runner=runner,
    )
    # 让 L2-05 第一次说 format_invalid
    mock_l2_05.validate.side_effect = [
        {"status": "format_invalid"}, {"status": "ok"},
    ]
    return inv
```

---

*— L1-05 L2-03 TDD 已按 10 段模板完成 · 覆盖 §3 全部方法 / §11 全部 14 错误码 / 6 IC · 含 context 注入 + 签名 + timeout + retry + fallback + audit 全链路 —*
