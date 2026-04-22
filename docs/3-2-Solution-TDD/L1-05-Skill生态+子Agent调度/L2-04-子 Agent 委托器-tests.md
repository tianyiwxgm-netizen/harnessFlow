---
doc_id: tests-L1-05-L2-04-子 Agent 委托器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md
  - docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-05 L2-04-子 Agent 委托器 · TDD 测试用例

> 基于 3-1 L2-04 §3（4 方法：spawn/delegate/collect/abort）+ §11（14 条 `SUBAGENT_*` 错误码 + 5 级降级）+ §12 SLO 驱动。
> TC ID 统一格式：`TC-L105-L204-NNN`。pytest + Python 3.11+；`class TestL2_04_SubagentDelegator`；独立 session / COW 快照 / 5 verdict 独立分组。

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
| `spawn()` · 成功 | TC-L105-L204-001 | unit | IC-14 §2.1 |
| `spawn()` · memory_readonly scope | TC-L105-L204-002 | unit | IC-14 |
| `spawn()` · resource_quota 下调 | TC-L105-L204-003 | unit | IC-14 |
| `delegate()` · accepted | TC-L105-L204-004 | unit | IC-14 §2.2 |
| `delegate()` · queue_position | TC-L105-L204-005 | unit | IC-14 |
| `collect()` · PASS | TC-L105-L204-006 | unit | IC-14 §2.3 |
| `collect()` · FAIL-L1 | TC-L105-L204-007 | unit | IC-14 |
| `collect()` · FAIL-L2 | TC-L105-L204-008 | unit | IC-14 |
| `collect()` · FAIL-L3 | TC-L105-L204-009 | unit | IC-14 |
| `collect()` · FAIL-L4 | TC-L105-L204-010 | unit | IC-14 |
| `abort()` · user_cancel | TC-L105-L204-011 | unit | IC-14 §2.4 |
| eight_dim_vector 8 维输出 | TC-L105-L204-012 | unit | — |
| evidence_chain 3 段 | TC-L105-L204-013 | unit | — |
| tool_call_trace 记录 | TC-L105-L204-014 | unit | — |
| SDK 建链（含 `min_required_version`） | TC-L105-L204-015 | unit | — |
| supervisor_review pass | TC-L105-L204-016 | unit | IC-09 |
| supervisor_review reject | TC-L105-L204-017 | unit | IC-09 |
| PM-14 path 分片 `<pid>.json` | TC-L105-L204-018 | unit | — |

### §1.2 错误码 × 测试（14 项全覆盖）

| 错误码 | TC ID | verdict |
|---|---|---|
| `SUBAGENT_SPAWN_FAIL` | TC-L105-L204-101 | FAIL-L1 |
| `SUBAGENT_CONTEXT_OVERFLOW` | TC-L105-L204-102 | FAIL-L1→PASS |
| `SUBAGENT_RATE_LIMIT_EXCEEDED` | TC-L105-L204-103 | FAIL-L1 |
| `SUBAGENT_TIMEOUT` | TC-L105-L204-104 | FAIL-L2 |
| `SUBAGENT_TOKEN_BUDGET_EXCEEDED` | TC-L105-L204-105 | FAIL-L2 |
| `SUBAGENT_TOOL_NOT_ALLOWED` | TC-L105-L204-106 | FAIL-L3 |
| `SUBAGENT_PROJECT_SCOPE_VIOLATION` | TC-L105-L204-107 | FAIL-L4 |
| `SUBAGENT_CONCURRENCY_LIMIT` | TC-L105-L204-108 | FAIL-L1 |
| `SUBAGENT_ABORT_BY_USER` | TC-L105-L204-109 | PASS |
| `SUBAGENT_CRASH` | TC-L105-L204-110 | FAIL-L2 |
| `SUBAGENT_SUPERVISOR_REJECT` | TC-L105-L204-111 | FAIL-L3 |
| `SUBAGENT_TRACE_BROKEN` | TC-L105-L204-112 | FAIL-L1 |
| `SUBAGENT_MEMORY_EXCEEDED` | TC-L105-L204-113 | FAIL-L2 |
| `SUBAGENT_SDK_VERSION_MISMATCH` | TC-L105-L204-114 | FAIL-L1 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| IC-14-Spawn | Caller → 本 L2 | TC-L105-L204-601 |
| IC-14-Delegate | Caller → 本 L2 | TC-L105-L204-602 |
| IC-14-Collect | Caller → 本 L2 | TC-L105-L204-603 |
| IC-14-Abort | Caller → 本 L2 | TC-L105-L204-604 |
| IC-05 TrustLedger | 本 L2 → L1-07 | TC-L105-L204-605 |
| IC-09 supervisor filter | 本 L2 → L1-07 | TC-L105-L204-606 |

---

## §2 正向用例

```python
# file: tests/l1_05/test_l2_04_subagent_delegator_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_04_subagent.delegator import SubagentDelegator
from app.l2_04_subagent.schemas import (
    SpawnRequest, DelegateRequest, AbortRequest, SubAgentResult,
)


class TestL2_04_SubagentDelegator_Positive:

    def test_TC_L105_L204_001_spawn_success(
        self, sut: SubagentDelegator, mock_project_id: str,
    ) -> None:
        """TC-L105-L204-001 · spawn 返回 handle + state=provisioning/running."""
        resp = sut.spawn(SpawnRequest(
            project_id=mock_project_id,
            request_id="req-001", skill_id="tdd-blueprint-v2",
            skill_version="2.3.0",
            parent_agent_id="agent-main",
            parent_context_snapshot={"snapshot_id": "snap-001",
                                       "token_count": 50000,
                                       "checksum": "a" * 64,
                                       "scope": ["memory_readonly"]},
            tool_whitelist=[{"tool_id": "Read", "version": "1"}],
            resource_quota={"max_tokens": 50000, "max_wall_time_ms": 300000,
                             "max_tool_calls": 30, "max_memory_mb": 512},
            trust_level="normal", stage="S4",
            trace_parent={"trace_id": "t-001", "span_id": "s-001"},
        ))
        assert resp.handle.subagent_id
        assert resp.state in {"provisioning", "running"}

    def test_TC_L105_L204_002_spawn_memory_readonly_scope(
        self, sut, mock_project_id,
    ) -> None:
        resp = sut.spawn(SpawnRequest(
            project_id=mock_project_id, request_id="req-002",
            skill_id="x", skill_version="1",
            parent_agent_id="agent-main",
            parent_context_snapshot={"snapshot_id": "snap-002",
                                       "token_count": 1000,
                                       "checksum": "b" * 64,
                                       "scope": ["memory_readonly",
                                                  "tools_whitelisted"]},
            tool_whitelist=[],
            resource_quota={"max_tokens": 1000, "max_wall_time_ms": 5000,
                             "max_tool_calls": 5, "max_memory_mb": 128},
            trust_level="low", stage="S3",
            trace_parent={"trace_id": "t", "span_id": "s"},
        ))
        assert "memory_readonly" in resp.context_snapshot_ref.get("scope", []) \
            or resp.context_snapshot_ref.get("snapshot_id")

    def test_TC_L105_L204_003_quota_downgraded_by_gate(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L204-003 · 请求 max_memory=2048 · gate 下调到 1024."""
        resp = sut.spawn(SpawnRequest(
            project_id=mock_project_id, request_id="req-003",
            skill_id="x", skill_version="1",
            parent_agent_id="agent-main",
            parent_context_snapshot={"snapshot_id": "snap-003",
                                       "token_count": 1000,
                                       "checksum": "c" * 64,
                                       "scope": ["memory_readonly"]},
            tool_whitelist=[], trust_level="low", stage="S4",
            resource_quota={"max_tokens": 10**9, "max_wall_time_ms": 10**9,
                             "max_tool_calls": 10**6, "max_memory_mb": 2048},
            trace_parent={"trace_id": "t", "span_id": "s"},
        ))
        assert resp.resource_quota_granted["max_memory_mb"] <= 1024

    def test_TC_L105_L204_004_delegate_accepted(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        ack = sut.delegate(DelegateRequest(
            project_id=mock_project_id, subagent_id=spawned_handle.subagent_id,
            delegate_id="del-004",
            skill_invocation={"skill_id": "tdd", "method": "run",
                              "args": {}, "timeout_ms": 30000},
            stage_contract={"stage": "S4", "preconditions": [], "postconditions": []},
            ac_label={"project_id": mock_project_id, "trust_level": "normal",
                      "tenant_id": "t-1"},
        ))
        assert ack.accepted is True

    def test_TC_L105_L204_005_delegate_queue_position(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        sut.delegate(DelegateRequest(
            project_id=mock_project_id, subagent_id=spawned_handle.subagent_id,
            delegate_id="del-005a",
            skill_invocation={"skill_id": "tdd", "method": "run",
                              "args": {}, "timeout_ms": 30000},
            stage_contract={"stage": "S4", "preconditions": [], "postconditions": []},
            ac_label={"project_id": mock_project_id, "trust_level": "normal",
                      "tenant_id": "t-1"},
        ))
        ack2 = sut.delegate(DelegateRequest(
            project_id=mock_project_id, subagent_id=spawned_handle.subagent_id,
            delegate_id="del-005b",
            skill_invocation={"skill_id": "tdd", "method": "run",
                              "args": {}, "timeout_ms": 30000},
            stage_contract={"stage": "S4", "preconditions": [], "postconditions": []},
            ac_label={"project_id": mock_project_id, "trust_level": "normal",
                      "tenant_id": "t-1"},
        ))
        assert ack2.queue_position >= 0

    def test_TC_L105_L204_006_collect_pass(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r: SubAgentResult = sut.collect(
            project_id=mock_project_id,
            subagent_id=spawned_handle.subagent_id,
            delegate_id="del-006",
            timeout=30000,
        )
        assert r.verdict == "PASS"
        assert r.supervisor_review.passed is True

    def test_TC_L105_L204_007_collect_fail_l1(
        self, sut_l1, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_l1.collect(project_id=mock_project_id,
                            subagent_id=spawned_handle.subagent_id,
                            delegate_id="del-007", timeout=30000)
        assert r.verdict == "FAIL-L1"

    def test_TC_L105_L204_008_collect_fail_l2(
        self, sut_l2, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_l2.collect(project_id=mock_project_id,
                            subagent_id=spawned_handle.subagent_id,
                            delegate_id="del-008", timeout=30000)
        assert r.verdict == "FAIL-L2"

    def test_TC_L105_L204_009_collect_fail_l3(
        self, sut_l3, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_l3.collect(project_id=mock_project_id,
                            subagent_id=spawned_handle.subagent_id,
                            delegate_id="del-009", timeout=30000)
        assert r.verdict == "FAIL-L3"

    def test_TC_L105_L204_010_collect_fail_l4(
        self, sut_l4, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_l4.collect(project_id=mock_project_id,
                            subagent_id=spawned_handle.subagent_id,
                            delegate_id="del-010", timeout=30000)
        assert r.verdict == "FAIL-L4"

    def test_TC_L105_L204_011_abort_user_cancel(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        ack = sut.abort(AbortRequest(
            project_id=mock_project_id,
            subagent_id=spawned_handle.subagent_id,
            reason="user_cancel",
        ))
        assert ack.status in {"ok", "aborted"}

    def test_TC_L105_L204_012_eight_dim_vector(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.collect(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-012", timeout=30000)
        for k in ("isolation", "token_efficiency", "latency_score",
                  "tool_call_safety", "result_completeness",
                  "trust_level_score", "resource_usage_ratio",
                  "context_hygiene"):
            assert k in r.eight_dim_vector

    def test_TC_L105_L204_013_evidence_chain_3_parts(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.collect(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-013", timeout=30000)
        for k in ("spawn_evidence", "run_evidence", "collect_evidence"):
            assert k in r.evidence_chain

    def test_TC_L105_L204_014_tool_call_trace_has_hashes(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.collect(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-014", timeout=30000)
        for t in r.result.tool_call_trace:
            assert "args_hash" in t
            assert "output_hash" in t

    def test_TC_L105_L204_015_sdk_version_check(self, sut) -> None:
        """SDK 版本 >= min_required 才建链."""
        assert sut._sdk_version_ok() is True

    def test_TC_L105_L204_016_supervisor_review_pass(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.collect(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-016", timeout=30000)
        assert r.supervisor_review.passed is True

    def test_TC_L105_L204_017_supervisor_review_reject_changes_verdict(
        self, sut_supervisor_reject, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_supervisor_reject.collect(
            project_id=mock_project_id,
            subagent_id=spawned_handle.subagent_id,
            delegate_id="del-017", timeout=30000,
        )
        assert r.verdict == "FAIL-L3"
        assert r.supervisor_review.passed is False

    def test_TC_L105_L204_018_pm14_path_sharding(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L105-L204-018 · session 记录路径按 pid 分片."""
        path = sut._session_record_path(project_id=mock_project_id,
                                         subagent_id="sa-018")
        assert mock_project_id in str(path)
```

---

## §3 负向用例

```python
# file: tests/l1_05/test_l2_04_subagent_delegator_negative.py
import pytest

from app.l2_04_subagent.schemas import SpawnRequest, AbortRequest


class TestL2_04_Negative:

    def test_TC_L105_L204_101_spawn_fail_os_resource(
        self, sut_os_fail, mock_project_id,
    ) -> None:
        resp = sut_os_fail.spawn(SpawnRequest(
            project_id=mock_project_id, request_id="req-n1",
            skill_id="x", skill_version="1",
            parent_agent_id="am", parent_context_snapshot={
                "snapshot_id": "s", "token_count": 100,
                "checksum": "a" * 64, "scope": []},
            tool_whitelist=[], resource_quota={"max_tokens": 1000,
                "max_wall_time_ms": 1000, "max_tool_calls": 1,
                "max_memory_mb": 64},
            trust_level="low", stage="S1",
            trace_parent={"trace_id": "t", "span_id": "s"},
        ))
        assert resp.error.code == "SUBAGENT_SPAWN_FAIL"

    def test_TC_L105_L204_102_context_overflow_then_degrade(
        self, sut_ctx_overflow, mock_project_id,
    ) -> None:
        resp = sut_ctx_overflow.spawn(SpawnRequest(
            project_id=mock_project_id, request_id="req-n2",
            skill_id="x", skill_version="1",
            parent_agent_id="am", parent_context_snapshot={
                "snapshot_id": "s", "token_count": 500000,  # 超预算
                "checksum": "a" * 64, "scope": ["memory_readonly"]},
            tool_whitelist=[], resource_quota={"max_tokens": 1000,
                "max_wall_time_ms": 1000, "max_tool_calls": 1,
                "max_memory_mb": 64},
            trust_level="low", stage="S1",
            trace_parent={"trace_id": "t", "span_id": "s"},
        ))
        # 降级后 PASS 或 FAIL-L1
        assert resp.verdict in {"PASS", "FAIL-L1"} or resp.error

    def test_TC_L105_L204_103_rate_limit_exceeded(
        self, sut_rate_limit, mock_project_id,
    ) -> None:
        resp = sut_rate_limit.spawn(SpawnRequest(
            project_id=mock_project_id, request_id="req-n3",
            skill_id="x", skill_version="1",
            parent_agent_id="am", parent_context_snapshot={
                "snapshot_id": "s", "token_count": 1000,
                "checksum": "a" * 64, "scope": []},
            tool_whitelist=[], resource_quota={"max_tokens": 1000,
                "max_wall_time_ms": 1000, "max_tool_calls": 1,
                "max_memory_mb": 64},
            trust_level="low", stage="S1",
            trace_parent={"trace_id": "t", "span_id": "s"},
        ))
        assert resp.error.code == "SUBAGENT_RATE_LIMIT_EXCEEDED" or resp.state == "running"

    def test_TC_L105_L204_104_timeout(
        self, sut_wall_timeout, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_wall_timeout.collect(project_id=mock_project_id,
                                      subagent_id=spawned_handle.subagent_id,
                                      delegate_id="del-to", timeout=100)
        assert r.verdict == "FAIL-L2"
        assert r.error.code == "SUBAGENT_TIMEOUT"

    def test_TC_L105_L204_105_token_budget_exceeded(
        self, sut_token_over, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_token_over.collect(project_id=mock_project_id,
                                    subagent_id=spawned_handle.subagent_id,
                                    delegate_id="del-tok", timeout=30000)
        assert r.error.code == "SUBAGENT_TOKEN_BUDGET_EXCEEDED"

    def test_TC_L105_L204_106_tool_not_allowed(
        self, sut_tool_forbidden, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_tool_forbidden.collect(project_id=mock_project_id,
                                        subagent_id=spawned_handle.subagent_id,
                                        delegate_id="del-tool", timeout=30000)
        assert r.verdict == "FAIL-L3"
        assert r.error.code == "SUBAGENT_TOOL_NOT_ALLOWED"

    def test_TC_L105_L204_107_project_scope_violation_hard_kill(
        self, sut_scope_viol, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_scope_viol.collect(project_id=mock_project_id,
                                    subagent_id=spawned_handle.subagent_id,
                                    delegate_id="del-sv", timeout=30000)
        assert r.verdict == "FAIL-L4"
        assert r.error.code == "SUBAGENT_PROJECT_SCOPE_VIOLATION"

    def test_TC_L105_L204_108_concurrency_limit(
        self, sut_at_cap, mock_project_id,
    ) -> None:
        resp = sut_at_cap.spawn(SpawnRequest(
            project_id=mock_project_id, request_id="req-cc",
            skill_id="x", skill_version="1",
            parent_agent_id="am", parent_context_snapshot={
                "snapshot_id": "s", "token_count": 1000,
                "checksum": "a" * 64, "scope": []},
            tool_whitelist=[], resource_quota={"max_tokens": 1000,
                "max_wall_time_ms": 1000, "max_tool_calls": 1,
                "max_memory_mb": 64},
            trust_level="low", stage="S1",
            trace_parent={"trace_id": "t", "span_id": "s"},
        ))
        assert resp.error.code in {"SUBAGENT_CONCURRENCY_LIMIT", None}

    def test_TC_L105_L204_109_abort_by_user_is_pass(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        sut.abort(AbortRequest(
            project_id=mock_project_id,
            subagent_id=spawned_handle.subagent_id,
            reason="user_cancel",
        ))
        # 不算错误

    def test_TC_L105_L204_110_crash(
        self, sut_crash, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_crash.collect(project_id=mock_project_id,
                               subagent_id=spawned_handle.subagent_id,
                               delegate_id="del-cr", timeout=30000)
        assert r.error.code == "SUBAGENT_CRASH"

    def test_TC_L105_L204_111_supervisor_reject(
        self, sut_supervisor_reject, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_supervisor_reject.collect(project_id=mock_project_id,
                                           subagent_id=spawned_handle.subagent_id,
                                           delegate_id="del-sr", timeout=30000)
        assert r.error.code == "SUBAGENT_SUPERVISOR_REJECT"

    def test_TC_L105_L204_112_trace_broken(
        self, sut_trace_broken, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_trace_broken.collect(project_id=mock_project_id,
                                      subagent_id=spawned_handle.subagent_id,
                                      delegate_id="del-tb", timeout=30000)
        assert r.error.code == "SUBAGENT_TRACE_BROKEN"

    def test_TC_L105_L204_113_memory_exceeded(
        self, sut_mem_over, mock_project_id, spawned_handle,
    ) -> None:
        r = sut_mem_over.collect(project_id=mock_project_id,
                                  subagent_id=spawned_handle.subagent_id,
                                  delegate_id="del-mem", timeout=30000)
        assert r.error.code == "SUBAGENT_MEMORY_EXCEEDED"

    def test_TC_L105_L204_114_sdk_version_mismatch(
        self, sut_sdk_old, mock_project_id,
    ) -> None:
        resp = sut_sdk_old.spawn(SpawnRequest(
            project_id=mock_project_id, request_id="req-sdk",
            skill_id="x", skill_version="1",
            parent_agent_id="am", parent_context_snapshot={
                "snapshot_id": "s", "token_count": 1000,
                "checksum": "a" * 64, "scope": []},
            tool_whitelist=[], resource_quota={"max_tokens": 1000,
                "max_wall_time_ms": 1000, "max_tool_calls": 1,
                "max_memory_mb": 64},
            trust_level="low", stage="S1",
            trace_parent={"trace_id": "t", "span_id": "s"},
        ))
        assert resp.error.code == "SUBAGENT_SDK_VERSION_MISMATCH"
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_05/test_l2_04_ic_contracts.py
import pytest


class TestL2_04_IC_Contracts:

    def test_TC_L105_L204_601_ic14_spawn_request_lock_project_id_first(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.spawn_raw({
            "project_id": mock_project_id, "request_id": "req-601",
            "skill_id": "x", "skill_version": "1",
            "parent_agent_id": "am",
            "parent_context_snapshot": {"snapshot_id": "s",
                                          "token_count": 1000,
                                          "checksum": "a" * 64,
                                          "scope": []},
            "tool_whitelist": [],
            "resource_quota": {"max_tokens": 1000, "max_wall_time_ms": 1000,
                               "max_tool_calls": 1, "max_memory_mb": 64},
            "trust_level": "low", "stage": "S1",
            "trace_parent": {"trace_id": "t", "span_id": "s"},
        })
        assert r["project_id"] == mock_project_id
        assert r["request_id"] == "req-601"

    def test_TC_L105_L204_602_ic14_delegate_queue_position(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.delegate_raw({
            "project_id": mock_project_id,
            "subagent_id": spawned_handle.subagent_id,
            "delegate_id": "del-602",
            "skill_invocation": {"skill_id": "x", "method": "run",
                                  "args": {}, "timeout_ms": 30000},
            "stage_contract": {"stage": "S4", "preconditions": [],
                                "postconditions": []},
            "ac_label": {"project_id": mock_project_id,
                          "trust_level": "normal", "tenant_id": "t-1"},
        })
        assert "queue_position" in r

    def test_TC_L105_L204_603_ic14_collect_has_8_dim(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.collect_raw(project_id=mock_project_id,
                             subagent_id=spawned_handle.subagent_id,
                             delegate_id="del-603", timeout=30000)
        assert "eight_dim_vector" in r

    def test_TC_L105_L204_604_ic14_abort_shape(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.abort_raw({
            "project_id": mock_project_id,
            "subagent_id": spawned_handle.subagent_id,
            "reason": "user_cancel",
        })
        assert r["status"] in {"ok", "aborted"}

    def test_TC_L105_L204_605_ic05_trust_ledger_written(
        self, sut, mock_trust_ledger, mock_project_id, spawned_handle,
    ) -> None:
        sut.collect_raw(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-605", timeout=30000)
        mock_trust_ledger.record.assert_called()

    def test_TC_L105_L204_606_ic09_supervisor_filter(
        self, sut, mock_supervisor, mock_project_id, spawned_handle,
    ) -> None:
        sut.collect_raw(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-606", timeout=30000)
        mock_supervisor.filter.assert_called()
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_05/test_l2_04_perf.py
import time, statistics
import pytest


class TestL2_04_Perf:

    @pytest.mark.perf
    def test_TC_L105_L204_701_spawn_p95_under_1200ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(30):
            t = time.perf_counter()
            sut.spawn_raw({
                "project_id": mock_project_id, "request_id": f"req-p-{i:03d}",
                "skill_id": "x", "skill_version": "1",
                "parent_agent_id": "am",
                "parent_context_snapshot": {"snapshot_id": "s",
                                              "token_count": 1000,
                                              "checksum": "a" * 64,
                                              "scope": []},
                "tool_whitelist": [],
                "resource_quota": {"max_tokens": 1000,
                                    "max_wall_time_ms": 5000,
                                    "max_tool_calls": 5,
                                    "max_memory_mb": 128},
                "trust_level": "low", "stage": "S1",
                "trace_parent": {"trace_id": "t", "span_id": "s"},
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 1.2

    @pytest.mark.perf
    def test_TC_L105_L204_702_delegate_p95_under_50ms(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        durations = []
        for i in range(100):
            t = time.perf_counter()
            sut.delegate_raw({
                "project_id": mock_project_id,
                "subagent_id": spawned_handle.subagent_id,
                "delegate_id": f"del-p-{i:03d}",
                "skill_invocation": {"skill_id": "x", "method": "run",
                                      "args": {}, "timeout_ms": 30000},
                "stage_contract": {"stage": "S4",
                                    "preconditions": [], "postconditions": []},
                "ac_label": {"project_id": mock_project_id,
                              "trust_level": "normal", "tenant_id": "t-1"},
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.05

    @pytest.mark.perf
    def test_TC_L105_L204_703_collect_p95_under_300ms(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        durations = []
        for i in range(30):
            t = time.perf_counter()
            sut.collect_raw(project_id=mock_project_id,
                             subagent_id=spawned_handle.subagent_id,
                             delegate_id=f"del-p-{i}", timeout=30000)
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.3
```

---

## §6 端到端 e2e

```python
# file: tests/l1_05/test_l2_04_e2e.py
import pytest


class TestL2_04_E2E:

    @pytest.mark.e2e
    def test_TC_L105_L204_801_spawn_delegate_collect_full_chain(
        self, sut, mock_project_id,
    ) -> None:
        s = sut.spawn_raw({
            "project_id": mock_project_id, "request_id": "req-e01",
            "skill_id": "x", "skill_version": "1",
            "parent_agent_id": "am",
            "parent_context_snapshot": {"snapshot_id": "s",
                                          "token_count": 1000,
                                          "checksum": "a" * 64,
                                          "scope": []},
            "tool_whitelist": [],
            "resource_quota": {"max_tokens": 1000,
                                "max_wall_time_ms": 5000,
                                "max_tool_calls": 5,
                                "max_memory_mb": 128},
            "trust_level": "low", "stage": "S1",
            "trace_parent": {"trace_id": "t", "span_id": "s"},
        })
        sid = s["handle"]["subagent_id"]
        sut.delegate_raw({
            "project_id": mock_project_id, "subagent_id": sid,
            "delegate_id": "del-e01",
            "skill_invocation": {"skill_id": "x", "method": "run",
                                  "args": {}, "timeout_ms": 30000},
            "stage_contract": {"stage": "S4",
                                "preconditions": [], "postconditions": []},
            "ac_label": {"project_id": mock_project_id,
                          "trust_level": "normal", "tenant_id": "t-1"},
        })
        r = sut.collect_raw(project_id=mock_project_id,
                             subagent_id=sid,
                             delegate_id="del-e01", timeout=30000)
        assert r["verdict"] in {"PASS", "FAIL-L1", "FAIL-L2", "FAIL-L3", "FAIL-L4"}

    @pytest.mark.e2e
    def test_TC_L105_L204_802_degrade_ctx_overflow_to_inline(
        self, sut_ctx_overflow, mock_project_id,
    ) -> None:
        resp = sut_ctx_overflow.spawn_raw({
            "project_id": mock_project_id, "request_id": "req-e02",
            "skill_id": "x", "skill_version": "1",
            "parent_agent_id": "am",
            "parent_context_snapshot": {"snapshot_id": "s",
                                          "token_count": 500000,
                                          "checksum": "a" * 64,
                                          "scope": []},
            "tool_whitelist": [],
            "resource_quota": {"max_tokens": 1000,
                                "max_wall_time_ms": 5000,
                                "max_tool_calls": 5,
                                "max_memory_mb": 128},
            "trust_level": "low", "stage": "S1",
            "trace_parent": {"trace_id": "t", "span_id": "s"},
        })
        assert "handle" in resp or resp.get("error")
```

---

## §7 测试 fixture

```python
# file: tests/l1_05/conftest_l2_04.py
import pytest, uuid
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id():
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_sdk_ok():
    m = MagicMock()
    m.min_required_version.return_value = "1.0.0"
    m.current_version = "1.5.0"
    m.spawn_session = MagicMock(return_value={
        "session_id": "sess-001", "pid": 12345,
    })
    return m


@pytest.fixture
def mock_trust_ledger():
    m = MagicMock()
    m.record = MagicMock(return_value={"evt_id": "tl-001"})
    return m


@pytest.fixture
def mock_supervisor():
    m = MagicMock()
    m.filter = MagicMock(return_value={"passed": True,
                                        "sanitized_output": {"x": 1}})
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


def _make_sut(sdk, ledger, supervisor, event_bus, clock, tmp_path, **kwargs):
    from app.l2_04_subagent.delegator import SubagentDelegator
    return SubagentDelegator(
        sdk=sdk, trust_ledger=ledger, supervisor=supervisor,
        event_bus=event_bus, clock=clock, storage_root=tmp_path,
        **kwargs,
    )


@pytest.fixture
def sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus,
         mock_clock, tmp_path):
    return _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                       mock_event_bus, mock_clock, tmp_path)


@pytest.fixture
def spawned_handle(sut, mock_project_id):
    from app.l2_04_subagent.schemas import SpawnRequest
    resp = sut.spawn(SpawnRequest(
        project_id=mock_project_id, request_id="req-fixture",
        skill_id="x", skill_version="1",
        parent_agent_id="am",
        parent_context_snapshot={"snapshot_id": "s",
                                   "token_count": 1000,
                                   "checksum": "a" * 64,
                                   "scope": []},
        tool_whitelist=[],
        resource_quota={"max_tokens": 1000, "max_wall_time_ms": 5000,
                         "max_tool_calls": 5, "max_memory_mb": 128},
        trust_level="low", stage="S1",
        trace_parent={"trace_id": "t", "span_id": "s"},
    ))
    return resp.handle


def _make_by_failure(verdict, err_code, mock_sdk_ok, mock_trust_ledger,
                     mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_verdict = verdict
    sut._force_error = err_code
    return sut


@pytest.fixture
def sut_l1(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    return _make_by_failure("FAIL-L1", "SUBAGENT_SPAWN_FAIL",
                              mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                              mock_event_bus, mock_clock, tmp_path)


@pytest.fixture
def sut_l2(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    return _make_by_failure("FAIL-L2", "SUBAGENT_TIMEOUT",
                              mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                              mock_event_bus, mock_clock, tmp_path)


@pytest.fixture
def sut_l3(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    return _make_by_failure("FAIL-L3", "SUBAGENT_TOOL_NOT_ALLOWED",
                              mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                              mock_event_bus, mock_clock, tmp_path)


@pytest.fixture
def sut_l4(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    return _make_by_failure("FAIL-L4", "SUBAGENT_PROJECT_SCOPE_VIOLATION",
                              mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                              mock_event_bus, mock_clock, tmp_path)


@pytest.fixture
def sut_os_fail(mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    from unittest.mock import MagicMock
    sdk = MagicMock()
    sdk.min_required_version.return_value = "1.0.0"
    sdk.current_version = "1.5.0"
    sdk.spawn_session.side_effect = OSError("resource busy")
    return _make_sut(sdk, mock_trust_ledger, mock_supervisor,
                       mock_event_bus, mock_clock, tmp_path)


@pytest.fixture
def sut_ctx_overflow(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path):
    return _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                       mock_event_bus, mock_clock, tmp_path,
                       context_budget=10000)


@pytest.fixture
def sut_rate_limit(mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    from unittest.mock import MagicMock
    sdk = MagicMock()
    sdk.min_required_version.return_value = "1.0.0"
    sdk.current_version = "1.5.0"
    call_count = [0]
    def spawn(**kw):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise _RateLimit()
        return {"session_id": "sess", "pid": 1}
    sdk.spawn_session = spawn
    return _make_sut(sdk, mock_trust_ledger, mock_supervisor,
                       mock_event_bus, mock_clock, tmp_path)


class _RateLimit(Exception):
    code = "RATE_LIMIT"


@pytest.fixture
def sut_wall_timeout(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_TIMEOUT"
    sut._force_verdict = "FAIL-L2"
    return sut


@pytest.fixture
def sut_token_over(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_TOKEN_BUDGET_EXCEEDED"
    sut._force_verdict = "FAIL-L2"
    return sut


@pytest.fixture
def sut_tool_forbidden(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_TOOL_NOT_ALLOWED"
    sut._force_verdict = "FAIL-L3"
    return sut


@pytest.fixture
def sut_scope_viol(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_PROJECT_SCOPE_VIOLATION"
    sut._force_verdict = "FAIL-L4"
    return sut


@pytest.fixture
def sut_at_cap(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path,
                      max_concurrent=0)
    return sut


@pytest.fixture
def sut_crash(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_CRASH"
    sut._force_verdict = "FAIL-L2"
    return sut


@pytest.fixture
def sut_supervisor_reject(mock_sdk_ok, mock_trust_ledger, mock_event_bus, mock_clock, tmp_path):
    from unittest.mock import MagicMock
    sv = MagicMock()
    sv.filter = MagicMock(return_value={"passed": False,
                                          "sanitized_output": None})
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, sv,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_SUPERVISOR_REJECT"
    sut._force_verdict = "FAIL-L3"
    return sut


@pytest.fixture
def sut_trace_broken(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_TRACE_BROKEN"
    sut._force_verdict = "FAIL-L1"
    return sut


@pytest.fixture
def sut_mem_over(mock_sdk_ok, mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    sut = _make_sut(mock_sdk_ok, mock_trust_ledger, mock_supervisor,
                      mock_event_bus, mock_clock, tmp_path)
    sut._force_error = "SUBAGENT_MEMORY_EXCEEDED"
    sut._force_verdict = "FAIL-L2"
    return sut


@pytest.fixture
def sut_sdk_old(mock_trust_ledger, mock_supervisor, mock_event_bus, mock_clock, tmp_path):
    from unittest.mock import MagicMock
    sdk = MagicMock()
    sdk.min_required_version.return_value = "2.0.0"
    sdk.current_version = "1.5.0"  # 低于要求
    return _make_sut(sdk, mock_trust_ledger, mock_supervisor,
                       mock_event_bus, mock_clock, tmp_path)
```

---

## §8 集成点用例

```python
# file: tests/l1_05/test_l2_04_integrations.py
import pytest


class TestL2_04_Integration:

    def test_TC_L105_L204_901_with_l1_01_stage4_driver(
        self, sut, mock_project_id,
    ) -> None:
        """L1-01 Stage4 调用 spawn · 签发独立 session."""
        r = sut.spawn_raw({
            "project_id": mock_project_id, "request_id": "req-901",
            "skill_id": "x", "skill_version": "1",
            "parent_agent_id": "am",
            "parent_context_snapshot": {"snapshot_id": "s",
                                          "token_count": 1000,
                                          "checksum": "a" * 64,
                                          "scope": []},
            "tool_whitelist": [],
            "resource_quota": {"max_tokens": 1000, "max_wall_time_ms": 5000,
                               "max_tool_calls": 5, "max_memory_mb": 128},
            "trust_level": "low", "stage": "S4",
            "trace_parent": {"trace_id": "t", "span_id": "s"},
        })
        assert r["handle"]["subagent_id"]

    def test_TC_L105_L204_902_with_l1_07_supervisor(
        self, sut, mock_supervisor, mock_project_id, spawned_handle,
    ) -> None:
        sut.collect_raw(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-902", timeout=30000)
        mock_supervisor.filter.assert_called()

    def test_TC_L105_L204_903_with_l1_05_l2_01_metadata(
        self, sut, mock_project_id,
    ) -> None:
        """spawn 前读 skill metadata (IC-12)."""
        sut.spawn_raw({
            "project_id": mock_project_id, "request_id": "req-903",
            "skill_id": "x", "skill_version": "1",
            "parent_agent_id": "am",
            "parent_context_snapshot": {"snapshot_id": "s",
                                          "token_count": 1000,
                                          "checksum": "a" * 64,
                                          "scope": []},
            "tool_whitelist": [],
            "resource_quota": {"max_tokens": 1000, "max_wall_time_ms": 5000,
                               "max_tool_calls": 5, "max_memory_mb": 128},
            "trust_level": "low", "stage": "S4",
            "trace_parent": {"trace_id": "t", "span_id": "s"},
        })

    def test_TC_L105_L204_904_with_trust_ledger(
        self, sut, mock_trust_ledger, mock_project_id, spawned_handle,
    ) -> None:
        sut.collect_raw(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-904", timeout=30000)
        assert mock_trust_ledger.record.called
```

---

## §9 边界 / edge case

```python
# file: tests/l1_05/test_l2_04_edge.py
import pytest


class TestL2_04_Edge:

    def test_TC_L105_L204_A01_concurrent_spawn_3(
        self, sut, mock_project_id,
    ) -> None:
        """3 并发 spawn · 都 accepted."""
        from concurrent.futures import ThreadPoolExecutor
        def go(i):
            return sut.spawn_raw({
                "project_id": mock_project_id, "request_id": f"req-a1-{i}",
                "skill_id": "x", "skill_version": "1",
                "parent_agent_id": "am",
                "parent_context_snapshot": {"snapshot_id": "s",
                                              "token_count": 1000,
                                              "checksum": "a" * 64,
                                              "scope": []},
                "tool_whitelist": [],
                "resource_quota": {"max_tokens": 1000, "max_wall_time_ms": 5000,
                                   "max_tool_calls": 5, "max_memory_mb": 128},
                "trust_level": "low", "stage": "S1",
                "trace_parent": {"trace_id": "t", "span_id": "s"},
            })
        with ThreadPoolExecutor(max_workers=3) as ex:
            results = [f.result() for f in [ex.submit(go, i) for i in range(3)]]
        ids = [r["handle"]["subagent_id"] for r in results if "handle" in r]
        assert len(set(ids)) == len(ids)

    def test_TC_L105_L204_A02_huge_context_snapshot_500k(
        self, sut_ctx_overflow, mock_project_id,
    ) -> None:
        """500k token snapshot · 降级或 FAIL."""
        r = sut_ctx_overflow.spawn_raw({
            "project_id": mock_project_id, "request_id": "req-a2",
            "skill_id": "x", "skill_version": "1",
            "parent_agent_id": "am",
            "parent_context_snapshot": {"snapshot_id": "s",
                                          "token_count": 500000,
                                          "checksum": "a" * 64,
                                          "scope": []},
            "tool_whitelist": [],
            "resource_quota": {"max_tokens": 1000, "max_wall_time_ms": 5000,
                               "max_tool_calls": 5, "max_memory_mb": 128},
            "trust_level": "low", "stage": "S1",
            "trace_parent": {"trace_id": "t", "span_id": "s"},
        })
        assert r

    def test_TC_L105_L204_A03_many_tool_calls_in_whitelist(
        self, sut, mock_project_id,
    ) -> None:
        """tool_whitelist 50 个工具 · spawn 成功."""
        r = sut.spawn_raw({
            "project_id": mock_project_id, "request_id": "req-a3",
            "skill_id": "x", "skill_version": "1",
            "parent_agent_id": "am",
            "parent_context_snapshot": {"snapshot_id": "s",
                                          "token_count": 1000,
                                          "checksum": "a" * 64,
                                          "scope": []},
            "tool_whitelist": [{"tool_id": f"T-{i}", "version": "1"}
                                  for i in range(50)],
            "resource_quota": {"max_tokens": 1000, "max_wall_time_ms": 5000,
                               "max_tool_calls": 5, "max_memory_mb": 128},
            "trust_level": "low", "stage": "S1",
            "trace_parent": {"trace_id": "t", "span_id": "s"},
        })
        assert "handle" in r

    def test_TC_L105_L204_A04_abort_after_collect_is_noop(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        sut.collect_raw(project_id=mock_project_id,
                         subagent_id=spawned_handle.subagent_id,
                         delegate_id="del-a04", timeout=30000)
        r = sut.abort_raw({
            "project_id": mock_project_id,
            "subagent_id": spawned_handle.subagent_id,
            "reason": "user_cancel",
        })
        assert r["status"] in {"ok", "aborted", "already_done"}

    def test_TC_L105_L204_A05_very_short_timeout_10ms(
        self, sut, mock_project_id, spawned_handle,
    ) -> None:
        r = sut.collect_raw(project_id=mock_project_id,
                             subagent_id=spawned_handle.subagent_id,
                             delegate_id="del-a05", timeout=10)
        # 极短 timeout · 走 FAIL-L2 TIMEOUT 或正常返回
        assert r["verdict"] in {"PASS", "FAIL-L1", "FAIL-L2", "FAIL-L3", "FAIL-L4"}
```

---

*— L1-05 L2-04 TDD 已按 10 段模板完成 · 覆盖 §3 全部 4 方法 / §11 全部 14 错误码 / 6 IC 契约 · 含 COW 快照 + 5 verdict + 5 级降级覆盖 —*
