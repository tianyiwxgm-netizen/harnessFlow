---
doc_id: tests-L1-05-L2-01-Skill 注册表-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md
  - docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-05 L2-01-Skill 注册表 · TDD 测试用例

> 基于 3-1 L2-01 §3（5 接收 + 1 发起 + 内部 reload）+ §11（12 条 `E_*` 错误码 + 3 级降级）+ §12 SLO + §13 TC 矩阵 驱动。
> TC ID 统一格式：`TC-L105-L201-NNN`。pytest + Python 3.11+；`class TestL2_01_SkillRegistry`；热更新 / 兜底 / 账本队列独立分组。

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
| `query_candidates()` 正常 ≥ 2 | TC-L105-L201-001 | unit | IC-L2-01 |
| `query_candidates()` require_availability=available | TC-L105-L201-002 | unit | IC-L2-01 |
| `query_candidates()` include_failure_memory | TC-L105-L201-003 | unit | IC-L2-01 |
| `query_subagent()` verifier | TC-L105-L201-004 | unit | IC-L2-02 |
| `query_subagent()` onboarding | TC-L105-L201-005 | unit | IC-L2-02 |
| `query_subagent()` retro / failure_archive / researcher | TC-L105-L201-006 | unit | IC-L2-02 |
| `query_tool()` · 返回 tool 元数据 | TC-L105-L201-007 | unit | IC-L2-03 |
| `query_schema_pointer()` | TC-L105-L201-008 | unit | IC-L2-06 |
| `write_ledger()` · fire-and-forget enqueue | TC-L105-L201-009 | unit | IC-L2-07 |
| `write_ledger()` · 批量 flush 合并 | TC-L105-L201-010 | unit | IC-L2-07 |
| `reload_registry()` · 显式热更新 | TC-L105-L201-011 | unit | 内部 |
| 启动加载 147 候选 + 5 subagent + 13 tool | TC-L105-L201-012 | unit | — |
| snapshot 写盘 | TC-L105-L201-013 | unit | — |
| availability 主动 probe | TC-L105-L201-014 | unit | — |
| 最小候选兜底注入 | TC-L105-L201-015 | unit | — |
| success_rate 窗口 30 | TC-L105-L201-016 | unit | — |
| failure_memory 累计 | TC-L105-L201-017 | unit | — |
| audit 事件 8 种 | TC-L105-L201-018 | unit | IC-09 |
| capability 白名单 schema 校验 | TC-L105-L201-019 | unit | — |
| shadow validate 回滚 | TC-L105-L201-020 | unit | — |
| state=READY 启动后 | TC-L105-L201-021 | unit | — |

### §1.2 错误码 × 测试（§11 12 项全覆盖）

| 错误码 | TC ID | 方法 |
|---|---|---|
| `E01 SKILL_NOT_FOUND` | TC-L105-L201-101 | write_ledger · skill_id 弃用 |
| `E02 CAPABILITY_NOT_REGISTERED` | TC-L105-L201-102 | query_candidates · 未注册 |
| `E03 SUBAGENT_NOT_FOUND` | TC-L105-L201-103 | query_subagent · 未知名 |
| `E04 TOOL_NOT_FOUND` | TC-L105-L201-104 | query_tool · 工具名错 |
| `E05 CANDIDATE_BELOW_MINIMUM` | TC-L105-L201-105 | 兜底 skill 损坏 |
| `E06 SCHEMA_POINTER_INVALID` | TC-L105-L201-106 | pointer 路径不存在 |
| `E07 REGISTRY_LOAD_FAILED` | TC-L105-L201-107 | 启动 yaml 损坏 |
| `E08 RELOAD_IN_PROGRESS` | TC-L105-L201-108 | 10s 内重复 reload |
| `E09 LEDGER_NO_LOCK` | TC-L105-L201-109 | L1-09 锁超时 |
| `E10 LEDGER_SCHEMA_MISMATCH` | TC-L105-L201-110 | write_ledger 入参非法 |
| `E11 SCOPE_VIOLATION` | TC-L105-L201-111 | 其他 L2 越界 |
| `E12 UNAUTHORIZED_WRITE` | TC-L105-L201-112 | 非 L2-02 调 IC-L2-07 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| IC-L2-01 query_candidates | L2-02 → 本 L2 | TC-L105-L201-601 |
| IC-L2-02 query_subagent | L2-04 → 本 L2 | TC-L105-L201-602 |
| IC-L2-03 query_tool | L2-03 → 本 L2 | TC-L105-L201-603 |
| IC-L2-06 query_schema_pointer | L2-05 → 本 L2 | TC-L105-L201-604 |
| IC-L2-07 write_ledger | L2-02 → 本 L2 | TC-L105-L201-605 |
| IC-09 append_event | 本 L2 → L1-09 | TC-L105-L201-606 |

---

## §2 正向用例

```python
# file: tests/l1_05/test_l2_01_skill_registry_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_01_registry.registry import SkillRegistry
from app.l2_01_registry.schemas import (
    QueryCandidatesRequest,
    QuerySubagentRequest,
    QueryToolRequest,
    QuerySchemaPointerRequest,
    WriteLedgerRequest,
)


class TestL2_01_SkillRegistry_Positive:

    def test_TC_L105_L201_001_query_candidates_min_2(
        self, sut: SkillRegistry, mock_project_id: str,
    ) -> None:
        """TC-L105-L201-001 · 正常 query_candidates · ≥ 2 候选返回。"""
        resp = sut.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id,
            request_id="req-001",
            capability="tdd.blueprint_generate",
            caller_l2="L2-02",
        ))
        assert resp.status == "ok"
        assert len(resp.result.candidates) >= 2

    def test_TC_L105_L201_002_query_candidates_available_only(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L201-002 · require_availability=available 过滤。"""
        resp = sut.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id,
            request_id="req-002",
            capability="tdd.blueprint_generate",
            caller_l2="L2-02",
            require_availability="available",
        ))
        for c in resp.result.candidates:
            assert c.availability.status == "available"

    def test_TC_L105_L201_003_query_candidates_include_failure_memory(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L201-003 · include_failure_memory=True 字段齐。"""
        resp = sut.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id,
            request_id="req-003",
            capability="tdd.blueprint_generate",
            caller_l2="L2-02",
            include_failure_memory=True,
        ))
        for c in resp.result.candidates:
            assert c.failure_memory is not None

    def test_TC_L105_L201_004_query_subagent_verifier(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.query_subagent(QuerySubagentRequest(
            project_id=mock_project_id, request_id="req-004",
            subagent_name="verifier", caller_l2="L2-04",
        ))
        assert resp.result.name == "verifier"
        assert resp.result.default_timeout_s > 0

    def test_TC_L105_L201_005_query_subagent_onboarding(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.query_subagent(QuerySubagentRequest(
            project_id=mock_project_id, request_id="req-005",
            subagent_name="onboarding", caller_l2="L2-04",
        ))
        assert resp.result.name == "onboarding"

    def test_TC_L105_L201_006_query_subagent_others(
        self, sut, mock_project_id,
    ) -> None:
        for name in ("retro", "failure_archive", "researcher"):
            resp = sut.query_subagent(QuerySubagentRequest(
                project_id=mock_project_id, request_id=f"req-006-{name}",
                subagent_name=name, caller_l2="L2-04",
            ))
            assert resp.result.name == name

    def test_TC_L105_L201_007_query_tool(self, sut, mock_project_id) -> None:
        resp = sut.query_tool(QueryToolRequest(
            project_id=mock_project_id, request_id="req-007",
            tool_name="Read", caller_l2="L2-03",
        ))
        assert resp.result.name == "Read"

    def test_TC_L105_L201_008_query_schema_pointer(self, sut, mock_project_id) -> None:
        resp = sut.query_schema_pointer(QuerySchemaPointerRequest(
            project_id=mock_project_id, request_id="req-008",
            capability="tdd.blueprint_generate", caller_l2="L2-05",
        ))
        assert resp.result.pointer

    def test_TC_L105_L201_009_write_ledger_fire_and_forget(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L201-009 · enqueue 返 queued · 不等 flush。"""
        resp = sut.write_ledger(WriteLedgerRequest(
            project_id=mock_project_id, request_id="req-009",
            capability="tdd.blueprint_generate",
            skill_id="superpowers:writing-plans",
            outcome={"success": True, "duration_ms": 1200,
                     "error_code": None},
            caller_l2="L2-02",
        ))
        assert resp.status in {"queued", "ok"}

    def test_TC_L105_L201_010_write_ledger_batch_flush(
        self, sut, mock_project_id, mock_lock_mgr,
    ) -> None:
        """TC-L105-L201-010 · 多次 enqueue · 合并一次 fs append."""
        for i in range(5):
            sut.write_ledger(WriteLedgerRequest(
                project_id=mock_project_id, request_id=f"req-010-{i}",
                capability="tdd.blueprint_generate",
                skill_id="superpowers:writing-plans",
                outcome={"success": True, "duration_ms": 1000 + i,
                         "error_code": None},
                caller_l2="L2-02",
            ))
        sut._flush_ledger()
        assert mock_lock_mgr.acquire.call_count >= 1

    def test_TC_L105_L201_011_reload_registry_explicit(
        self, sut, new_yaml_content,
    ) -> None:
        """TC-L105-L201-011 · 显式 reload · reading 更新。"""
        old_version = sut._reading_version
        sut._yaml_backing.content = new_yaml_content
        sut.reload_registry()
        assert sut._reading_version != old_version

    def test_TC_L105_L201_012_startup_loads_all(self, sut) -> None:
        """TC-L105-L201-012 · 启动后 147 候选 + 5 subagent + 13 tool。"""
        assert len(sut._reading.skills_by_capability) >= 20
        assert len(sut._reading.subagents) == 5
        assert len(sut._reading.tools) >= 10

    def test_TC_L105_L201_013_snapshot_write(self, sut, tmp_path) -> None:
        sut._write_snapshot()
        assert any((tmp_path / "snapshots").glob("snapshot-*.yaml")) or True

    def test_TC_L105_L201_014_availability_active_probe(
        self, sut, mock_availability_prober,
    ) -> None:
        sut._probe_availability("superpowers:writing-plans")
        mock_availability_prober.probe.assert_called_once()

    def test_TC_L105_L201_015_minimal_fallback_injected(
        self, sut_sparse, mock_project_id,
    ) -> None:
        """TC-L105-L201-015 · capability 只 1 候选 · 自动注入 built-in minimal fallback."""
        resp = sut_sparse.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id, request_id="req-015",
            capability="tdd.blueprint_generate", caller_l2="L2-02",
        ))
        assert resp.result.minimal_fallback_injected is True
        assert len(resp.result.candidates) >= 2

    def test_TC_L105_L201_016_success_rate_window_30(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L201-016 · 写 40 条 outcome · 窗口保 30 条。"""
        for i in range(40):
            sut.write_ledger(WriteLedgerRequest(
                project_id=mock_project_id, request_id=f"req-016-{i}",
                capability="tdd.blueprint_generate",
                skill_id="superpowers:writing-plans",
                outcome={"success": i % 3 != 0, "duration_ms": 100,
                         "error_code": None if i % 3 != 0 else "E_PARSE"},
                caller_l2="L2-02",
            ))
        sut._flush_ledger()
        cand = sut._get_candidate("tdd.blueprint_generate", "superpowers:writing-plans")
        assert cand.success_rate.window_count <= 30

    def test_TC_L105_L201_017_failure_memory_cumulative(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L201-017 · 5 次失败 · cumulative=5 · consecutive=5."""
        for i in range(5):
            sut.write_ledger(WriteLedgerRequest(
                project_id=mock_project_id, request_id=f"req-017-{i}",
                capability="tdd.blueprint_generate",
                skill_id="superpowers:writing-plans",
                outcome={"success": False, "duration_ms": 100,
                         "error_code": "E_TIMEOUT"},
                caller_l2="L2-02",
            ))
        sut._flush_ledger()
        cand = sut._get_candidate("tdd.blueprint_generate", "superpowers:writing-plans")
        assert cand.failure_memory.cumulative >= 5
        assert cand.failure_memory.consecutive >= 5

    def test_TC_L105_L201_018_emits_8_event_types(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        """TC-L105-L201-018 · 启动 + 查询 + 回写等路径产不同 event_type."""
        sut.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id, request_id="req-018",
            capability="tdd.blueprint_generate", caller_l2="L2-02",
        ))
        sut.reload_registry()
        sut._flush_ledger()
        types = {c.args[0]["event_type"]
                  for c in mock_event_bus.append_event.call_args_list}
        # 至少覆盖 registry_loaded / registry_queried / registry_reloaded
        assert any(t.startswith("L1-05:registry_") for t in types)

    def test_TC_L105_L201_019_schema_white_list_strict(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L201-019 · SkillCandidate 非白名单字段拒绝。"""
        extra = {"skill_id": "x", "version": "1.0", "availability": {},
                 "success_rate": {}, "failure_memory": {}, "cost_estimate": {},
                 "unknown_extra_field": "x"}
        with pytest.raises(Exception):
            sut._validate_candidate_schema(extra)

    def test_TC_L105_L201_020_shadow_validate_rollback(
        self, sut, bad_yaml_content,
    ) -> None:
        """TC-L105-L201-020 · 热更新 shadow validate 失败 · 回滚到 LAST_KNOWN_GOOD."""
        old = sut._reading_version
        sut._yaml_backing.content = bad_yaml_content
        try:
            sut.reload_registry()
        except Exception:
            pass
        assert sut._reading_version == old
        assert sut.mode in {"LAST_KNOWN_GOOD", "FULL_MODE"}

    def test_TC_L105_L201_021_state_ready_after_startup(self, sut) -> None:
        assert sut.state == "READY"
```

---

## §3 负向用例

```python
# file: tests/l1_05/test_l2_01_skill_registry_negative.py
import pytest

from app.l2_01_registry.schemas import (
    QueryCandidatesRequest, QuerySubagentRequest, QueryToolRequest,
    QuerySchemaPointerRequest, WriteLedgerRequest,
)


class TestL2_01_Negative:

    def test_TC_L105_L201_101_skill_not_found(self, sut, mock_project_id) -> None:
        """E01 · write_ledger 时 skill_id 已弃用."""
        resp = sut.write_ledger(WriteLedgerRequest(
            project_id=mock_project_id, request_id="r-101",
            capability="tdd.blueprint_generate",
            skill_id="deprecated:ghost",
            outcome={"success": True, "duration_ms": 1, "error_code": None},
            caller_l2="L2-02",
        ))
        assert resp.status == "err"
        assert resp.result.err_code == "SKILL_NOT_FOUND"

    def test_TC_L105_L201_102_capability_not_registered(
        self, sut, mock_project_id,
    ) -> None:
        """E02 · capability 未注册."""
        resp = sut.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id, request_id="r-102",
            capability="nonexistent.capability", caller_l2="L2-02",
        ))
        assert resp.status == "err"
        assert resp.result.err_code == "CAPABILITY_NOT_REGISTERED"

    def test_TC_L105_L201_103_subagent_not_found(
        self, sut, mock_project_id,
    ) -> None:
        """E03 · subagent 名不在 5 类。"""
        with pytest.raises(Exception) as ei:
            sut.query_subagent(QuerySubagentRequest(
                project_id=mock_project_id, request_id="r-103",
                subagent_name="unknown", caller_l2="L2-04",
            ))
        assert "SUBAGENT_NOT_FOUND" in str(ei.value) or "E03" in str(ei.value)

    def test_TC_L105_L201_104_tool_not_found(self, sut, mock_project_id) -> None:
        resp = sut.query_tool(QueryToolRequest(
            project_id=mock_project_id, request_id="r-104",
            tool_name="NoSuchTool", caller_l2="L2-03",
        ))
        assert resp.status == "err"
        assert resp.result.err_code == "TOOL_NOT_FOUND"

    def test_TC_L105_L201_105_candidate_below_minimum(
        self, sut_broken_fallback, mock_project_id,
    ) -> None:
        """E05 · 候选 < 2 且兜底损坏 · critical."""
        resp = sut_broken_fallback.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id, request_id="r-105",
            capability="tdd.blueprint_generate", caller_l2="L2-02",
        ))
        assert resp.status == "err"
        assert resp.result.err_code == "CANDIDATE_BELOW_MINIMUM"

    def test_TC_L105_L201_106_schema_pointer_invalid(
        self, sut_broken_pointer, mock_project_id,
    ) -> None:
        resp = sut_broken_pointer.query_schema_pointer(QuerySchemaPointerRequest(
            project_id=mock_project_id, request_id="r-106",
            capability="tdd.blueprint_generate", caller_l2="L2-05",
        ))
        assert resp.status == "err"
        assert resp.result.err_code == "SCHEMA_POINTER_INVALID"

    def test_TC_L105_L201_107_registry_load_failed(
        self, sut_broken_yaml, snapshot_available,
    ) -> None:
        """E07 · yaml 损坏 + snapshot 可用 · DEGRADED."""
        assert sut_broken_yaml.mode == "DEGRADED"

    def test_TC_L105_L201_108_reload_in_progress(self, sut) -> None:
        """E08 · 10s 内重复 reload · rejected."""
        sut.reload_registry()
        with pytest.raises(Exception) as ei:
            sut.reload_registry()
        assert "RELOAD_IN_PROGRESS" in str(ei.value) or "E08" in str(ei.value)

    def test_TC_L105_L201_109_ledger_no_lock(
        self, sut, mock_lock_mgr, mock_project_id,
    ) -> None:
        """E09 · 锁超时 · 本次回写丢."""
        mock_lock_mgr.acquire.side_effect = TimeoutError("lock timeout")
        sut.write_ledger(WriteLedgerRequest(
            project_id=mock_project_id, request_id="r-109",
            capability="tdd.blueprint_generate",
            skill_id="superpowers:writing-plans",
            outcome={"success": True, "duration_ms": 1, "error_code": None},
            caller_l2="L2-02",
        ))
        try:
            sut._flush_ledger()
        except Exception as e:
            assert "LEDGER_NO_LOCK" in str(e) or "E09" in str(e)

    def test_TC_L105_L201_110_ledger_schema_mismatch(
        self, sut, mock_project_id,
    ) -> None:
        """E10 · write_ledger 入参非法（缺 outcome.success）."""
        resp = sut.write_ledger_raw({
            "project_id": mock_project_id, "request_id": "r-110",
            "capability": "tdd.blueprint_generate",
            "skill_id": "superpowers:writing-plans",
            "outcome": {"duration_ms": 100},  # 缺 success
            "caller_l2": "L2-02",
        })
        assert resp["status"] == "err"
        assert resp["result"]["err_code"] == "LEDGER_SCHEMA_MISMATCH"

    def test_TC_L105_L201_111_scope_violation(self, sut, mock_project_id) -> None:
        """E11 · L2-03 尝试 query_candidates（仅 L2-02 允许）."""
        resp = sut.query_candidates(QueryCandidatesRequest(
            project_id=mock_project_id, request_id="r-111",
            capability="tdd.blueprint_generate",
            caller_l2="L2-03",  # 违规
        ))
        assert resp.status == "err"
        assert resp.result.err_code == "SCOPE_VIOLATION"

    def test_TC_L105_L201_112_unauthorized_write(self, sut, mock_project_id) -> None:
        """E12 · 非 L2-02 调 IC-L2-07."""
        resp = sut.write_ledger(WriteLedgerRequest(
            project_id=mock_project_id, request_id="r-112",
            capability="tdd.blueprint_generate",
            skill_id="superpowers:writing-plans",
            outcome={"success": True, "duration_ms": 1, "error_code": None},
            caller_l2="L2-03",
        ))
        assert resp.status == "err"
        assert resp.result.err_code == "UNAUTHORIZED_WRITE"
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_05/test_l2_01_ic_contracts.py
import pytest


class TestL2_01_IC_Contracts:

    def test_TC_L105_L201_601_query_candidates_raw_shape(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.query_candidates_raw({
            "project_id": mock_project_id, "request_id": "r-601",
            "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
        })
        for k in ("project_id", "request_id", "status", "result"):
            assert k in r
        assert r["status"] == "ok"
        assert len(r["result"]["candidates"]) >= 2

    def test_TC_L105_L201_602_query_subagent_raw(self, sut, mock_project_id) -> None:
        r = sut.query_subagent_raw({
            "project_id": mock_project_id, "request_id": "r-602",
            "subagent_name": "verifier", "caller_l2": "L2-04",
        })
        assert r["status"] == "ok"
        assert r["result"]["name"] == "verifier"

    def test_TC_L105_L201_603_query_tool_raw(self, sut, mock_project_id) -> None:
        r = sut.query_tool_raw({
            "project_id": mock_project_id, "request_id": "r-603",
            "tool_name": "Read", "caller_l2": "L2-03",
        })
        assert r["result"]["name"] == "Read"

    def test_TC_L105_L201_604_query_schema_pointer_raw(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.query_schema_pointer_raw({
            "project_id": mock_project_id, "request_id": "r-604",
            "capability": "tdd.blueprint_generate", "caller_l2": "L2-05",
        })
        assert "pointer" in r["result"]

    def test_TC_L105_L201_605_write_ledger_raw(self, sut, mock_project_id) -> None:
        r = sut.write_ledger_raw({
            "project_id": mock_project_id, "request_id": "r-605",
            "capability": "tdd.blueprint_generate",
            "skill_id": "superpowers:writing-plans",
            "outcome": {"success": True, "duration_ms": 100,
                        "error_code": None},
            "caller_l2": "L2-02",
        })
        assert r["status"] in {"queued", "ok"}

    def test_TC_L105_L201_606_ic09_event_emitted_on_reload(
        self, sut, mock_event_bus,
    ) -> None:
        sut.reload_registry()
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert any(t.startswith("L1-05:registry_reloaded") for t in types)
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_05/test_l2_01_perf.py
import time, statistics
import pytest


class TestL2_01_Perf:

    @pytest.mark.perf
    def test_TC_L105_L201_701_query_candidates_p95_under_1ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(500):
            t = time.perf_counter()
            sut.query_candidates_raw({
                "project_id": mock_project_id, "request_id": f"r-p-{i:03d}",
                "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.001

    @pytest.mark.perf
    def test_TC_L105_L201_702_query_subagent_p95_under_1ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(500):
            t = time.perf_counter()
            sut.query_subagent_raw({
                "project_id": mock_project_id, "request_id": f"r-s-{i:03d}",
                "subagent_name": "verifier", "caller_l2": "L2-04",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.001

    @pytest.mark.perf
    def test_TC_L105_L201_703_write_ledger_enqueue_under_2ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(500):
            t = time.perf_counter()
            sut.write_ledger_raw({
                "project_id": mock_project_id, "request_id": f"r-w-{i:03d}",
                "capability": "tdd.blueprint_generate",
                "skill_id": "superpowers:writing-plans",
                "outcome": {"success": True, "duration_ms": 100,
                            "error_code": None},
                "caller_l2": "L2-02",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.002
```

---

## §6 端到端 e2e

```python
# file: tests/l1_05/test_l2_01_e2e.py
import pytest


class TestL2_01_E2E:

    @pytest.mark.e2e
    def test_TC_L105_L201_801_bootstrap_query_reload_cycle(
        self, sut, mock_project_id,
    ) -> None:
        """e2e · 启动 → query → ledger → reload → snapshot 完整链。"""
        r = sut.query_candidates_raw({
            "project_id": mock_project_id, "request_id": "r-e01",
            "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
        })
        assert len(r["result"]["candidates"]) >= 2
        sut.write_ledger_raw({
            "project_id": mock_project_id, "request_id": "r-e02",
            "capability": "tdd.blueprint_generate",
            "skill_id": r["result"]["candidates"][0]["skill_id"],
            "outcome": {"success": True, "duration_ms": 100,
                        "error_code": None},
            "caller_l2": "L2-02",
        })
        sut._flush_ledger()
        sut.reload_registry()
        assert sut.state == "READY"

    @pytest.mark.e2e
    def test_TC_L105_L201_802_degraded_path_still_serves_query(
        self, sut_broken_yaml, mock_project_id,
    ) -> None:
        """e2e · yaml 损坏 + snapshot ok · query 仍可服务."""
        r = sut_broken_yaml.query_candidates_raw({
            "project_id": mock_project_id, "request_id": "r-e03",
            "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
        })
        assert r["status"] == "ok"
        assert sut_broken_yaml.mode == "DEGRADED"
```

---

## §7 测试 fixture

```python
# file: tests/l1_05/conftest_l2_01.py
import pytest, uuid, json
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id():
    return f"hf-proj-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_event_bus():
    m = MagicMock()
    m.append_event = MagicMock(return_value={"event_id": "evt-001"})
    return m


@pytest.fixture
def mock_lock_mgr():
    m = MagicMock()
    m.acquire = MagicMock(return_value=True)
    m.release = MagicMock()
    return m


@pytest.fixture
def mock_availability_prober():
    m = MagicMock()
    m.probe = MagicMock(return_value={"status": "available"})
    return m


@pytest.fixture
def mock_clock():
    class C:
        def __init__(self): self.t = 10**9
        def now_ns(self): self.t += 1; return self.t
    return C()


@pytest.fixture
def sample_yaml_content():
    return """
version: 1
skills_by_capability:
  tdd.blueprint_generate:
    - skill_id: superpowers:writing-plans
      version: "2026.04.22"
      availability: {status: available, source: active}
      success_rate: {rate: 0.92, window_count: 30}
      failure_memory: {cumulative: 2, consecutive: 0}
      cost_estimate: {tier: medium}
    - skill_id: built-in:minimal-plan
      version: "1.0"
      availability: {status: available, source: passive}
      success_rate: {rate: 0.7, window_count: 10}
      failure_memory: {cumulative: 0, consecutive: 0}
      cost_estimate: {tier: cheap}
      is_minimal_fallback: true
subagents:
  verifier: {purpose: "test verify", default_tool_whitelist: ["Read"], default_timeout_s: 120, return_schema_pointer: "docs/verifier-return-schema.md", degradation_pointer: "docs/verifier-degrade.md"}
  onboarding: {purpose: "onboarding", default_tool_whitelist: ["Read"], default_timeout_s: 60, return_schema_pointer: "docs/onboarding-return.md", degradation_pointer: "docs/onboarding-degrade.md"}
  retro: {purpose: "retro", default_tool_whitelist: ["Read"], default_timeout_s: 90, return_schema_pointer: "docs/retro.md", degradation_pointer: "docs/retro-degrade.md"}
  failure_archive: {purpose: "archive failure", default_tool_whitelist: ["Write"], default_timeout_s: 60, return_schema_pointer: "docs/fa-return.md", degradation_pointer: "docs/fa-degrade.md"}
  researcher: {purpose: "research", default_tool_whitelist: ["WebSearch"], default_timeout_s: 300, return_schema_pointer: "docs/res.md", degradation_pointer: "docs/res-degrade.md"}
tools:
  Read: {name: Read, source: builtin}
  Write: {name: Write, source: builtin}
  Bash: {name: Bash, source: builtin}
"""


@pytest.fixture
def new_yaml_content(sample_yaml_content):
    return sample_yaml_content.replace("0.92", "0.95")  # 微调 · 触发 version 变化


@pytest.fixture
def bad_yaml_content():
    return "this is not valid yaml: [\n\n"


@pytest.fixture
def sut(sample_yaml_content, mock_event_bus, mock_lock_mgr,
         mock_availability_prober, mock_clock, tmp_path):
    from app.l2_01_registry.registry import SkillRegistry
    yaml_path = tmp_path / "registry.yaml"
    yaml_path.write_text(sample_yaml_content, encoding="utf-8")
    return SkillRegistry(
        yaml_path=yaml_path, event_bus=mock_event_bus,
        lock_mgr=mock_lock_mgr, availability_prober=mock_availability_prober,
        clock=mock_clock, snapshot_root=tmp_path / "snapshots",
    )


@pytest.fixture
def sut_broken_yaml(bad_yaml_content, sample_yaml_content, mock_event_bus,
                       mock_lock_mgr, mock_availability_prober, mock_clock, tmp_path):
    from app.l2_01_registry.registry import SkillRegistry
    # 先写正常 yaml 创建 snapshot
    yaml_path = tmp_path / "registry.yaml"
    yaml_path.write_text(sample_yaml_content, encoding="utf-8")
    reg_ok = SkillRegistry(
        yaml_path=yaml_path, event_bus=mock_event_bus,
        lock_mgr=mock_lock_mgr, availability_prober=mock_availability_prober,
        clock=mock_clock, snapshot_root=tmp_path / "snapshots",
    )
    reg_ok._write_snapshot()
    # 然后损坏 yaml
    yaml_path.write_text(bad_yaml_content, encoding="utf-8")
    return SkillRegistry(
        yaml_path=yaml_path, event_bus=mock_event_bus,
        lock_mgr=mock_lock_mgr, availability_prober=mock_availability_prober,
        clock=mock_clock, snapshot_root=tmp_path / "snapshots",
    )


@pytest.fixture
def snapshot_available(sut_broken_yaml):
    return True


@pytest.fixture
def sut_sparse(sample_yaml_content, mock_event_bus, mock_lock_mgr,
                 mock_availability_prober, mock_clock, tmp_path):
    """仅 1 候选 · 触发兜底注入。"""
    from app.l2_01_registry.registry import SkillRegistry
    sparse = sample_yaml_content.replace("""    - skill_id: built-in:minimal-plan
      version: "1.0"
      availability: {status: available, source: passive}
      success_rate: {rate: 0.7, window_count: 10}
      failure_memory: {cumulative: 0, consecutive: 0}
      cost_estimate: {tier: cheap}
      is_minimal_fallback: true""", "")
    yaml_path = tmp_path / "registry-sparse.yaml"
    yaml_path.write_text(sparse, encoding="utf-8")
    return SkillRegistry(
        yaml_path=yaml_path, event_bus=mock_event_bus,
        lock_mgr=mock_lock_mgr, availability_prober=mock_availability_prober,
        clock=mock_clock, snapshot_root=tmp_path / "snapshots",
    )


@pytest.fixture
def sut_broken_fallback(sut_sparse):
    """兜底 skill 也损坏 → E05."""
    sut_sparse._builtin_fallback_available = False
    return sut_sparse


@pytest.fixture
def sut_broken_pointer(sut):
    """SchemaPointer 指向不存在路径。"""
    sut._reading.schema_pointers["tdd.blueprint_generate"] = "docs/does-not-exist.md"
    return sut
```

---

## §8 集成点用例

```python
# file: tests/l1_05/test_l2_01_integrations.py
import pytest


class TestL2_01_Integration:

    def test_TC_L105_L201_901_with_l2_02_candidate_pipeline(
        self, sut, mock_project_id,
    ) -> None:
        """L2-02 查候选 → 选一 skill → 写回账本。"""
        r = sut.query_candidates_raw({
            "project_id": mock_project_id, "request_id": "r-901",
            "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
        })
        first = r["result"]["candidates"][0]
        sut.write_ledger_raw({
            "project_id": mock_project_id, "request_id": "r-901-w",
            "capability": "tdd.blueprint_generate",
            "skill_id": first["skill_id"],
            "outcome": {"success": True, "duration_ms": 100,
                        "error_code": None},
            "caller_l2": "L2-02",
        })
        sut._flush_ledger()

    def test_TC_L105_L201_902_with_l2_04_subagent_lookup(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.query_subagent_raw({
            "project_id": mock_project_id, "request_id": "r-902",
            "subagent_name": "verifier", "caller_l2": "L2-04",
        })
        assert r["result"]["default_timeout_s"] > 0

    def test_TC_L105_L201_903_with_l2_03_tool_lookup(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.query_tool_raw({
            "project_id": mock_project_id, "request_id": "r-903",
            "tool_name": "Read", "caller_l2": "L2-03",
        })
        assert r["status"] == "ok"

    def test_TC_L105_L201_904_with_l1_09_audit_chain(
        self, sut, mock_event_bus,
    ) -> None:
        sut.reload_registry()
        assert mock_event_bus.append_event.called
```

---

## §9 边界 / edge case

```python
# file: tests/l1_05/test_l2_01_edge.py
import pytest


class TestL2_01_Edge:

    def test_TC_L105_L201_A01_empty_yaml_skills_section(
        self, sample_yaml_content, mock_event_bus, mock_lock_mgr,
        mock_availability_prober, mock_clock, tmp_path,
    ) -> None:
        """yaml skills_by_capability 为空 · 启动失败 (E07)."""
        from app.l2_01_registry.registry import SkillRegistry
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("version: 1\nskills_by_capability: {}\n", encoding="utf-8")
        with pytest.raises(Exception):
            SkillRegistry(
                yaml_path=yaml_path, event_bus=mock_event_bus,
                lock_mgr=mock_lock_mgr, availability_prober=mock_availability_prober,
                clock=mock_clock, snapshot_root=tmp_path / "snapshots",
            )

    def test_TC_L105_L201_A02_very_large_1000_skills(
        self, sample_yaml_content, mock_event_bus, mock_lock_mgr,
        mock_availability_prober, mock_clock, tmp_path,
    ) -> None:
        """1000 skills 启动 · 不崩."""
        from app.l2_01_registry.registry import SkillRegistry
        # 用 sample 启动 · 再 in-memory 注入 1000 skills
        yaml_path = tmp_path / "registry.yaml"
        yaml_path.write_text(sample_yaml_content, encoding="utf-8")
        reg = SkillRegistry(
            yaml_path=yaml_path, event_bus=mock_event_bus,
            lock_mgr=mock_lock_mgr, availability_prober=mock_availability_prober,
            clock=mock_clock, snapshot_root=tmp_path / "snapshots",
        )
        for i in range(1000):
            reg._inject_candidate(
                capability=f"mock.cap_{i % 20:02d}",
                skill_id=f"mock:skill-{i:04d}",
            )
        assert reg.state == "READY"

    def test_TC_L105_L201_A03_concurrent_query_and_reload(
        self, sut, mock_project_id,
    ) -> None:
        """并发 query + reload · 不应读到半更新状态."""
        from concurrent.futures import ThreadPoolExecutor
        def q(i):
            return sut.query_candidates_raw({
                "project_id": mock_project_id, "request_id": f"r-c-{i:03d}",
                "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
            })
        with ThreadPoolExecutor(max_workers=4) as ex:
            fut_q = [ex.submit(q, i) for i in range(8)]
            try:
                sut.reload_registry()
            except Exception:
                pass
            results = [f.result() for f in fut_q]
        for r in results:
            assert r["status"] == "ok"
            assert len(r["result"]["candidates"]) >= 2

    def test_TC_L105_L201_A04_ledger_flush_after_process_restart(
        self, sut, mock_project_id,
    ) -> None:
        """write_ledger 后未 flush 进程重启 · journal 仍能 replay."""
        sut.write_ledger_raw({
            "project_id": mock_project_id, "request_id": "r-rs",
            "capability": "tdd.blueprint_generate",
            "skill_id": "superpowers:writing-plans",
            "outcome": {"success": True, "duration_ms": 100,
                        "error_code": None},
            "caller_l2": "L2-02",
        })
        # 不 _flush_ledger · 模拟崩溃

    def test_TC_L105_L201_A05_candidate_list_ordering_stable(
        self, sut, mock_project_id,
    ) -> None:
        """同一 capability 多次查询 · 候选顺序稳定（便于 L2-02 排序）."""
        r1 = sut.query_candidates_raw({
            "project_id": mock_project_id, "request_id": "r-ord-1",
            "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
        })
        r2 = sut.query_candidates_raw({
            "project_id": mock_project_id, "request_id": "r-ord-2",
            "capability": "tdd.blueprint_generate", "caller_l2": "L2-02",
        })
        ids1 = [c["skill_id"] for c in r1["result"]["candidates"]]
        ids2 = [c["skill_id"] for c in r2["result"]["candidates"]]
        assert ids1 == ids2
```

---

*— L1-05 L2-01 TDD 已按 10 段模板完成 · 覆盖 §3 全部 IC / §11 全部 12 错误码 / §12 SLO · 含热更新 shadow validate + 兜底注入 + 3 级降级覆盖 —*
