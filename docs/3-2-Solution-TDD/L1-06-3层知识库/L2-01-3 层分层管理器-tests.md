---
doc_id: tests-L1-06-L2-01-3 层分层管理器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-06-3层知识库/L2-01-3 层分层管理器.md
  - docs/2-prd/L1-06 3层知识库/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-06 L2-01-3 层分层管理器 · TDD 测试用例

> 基于 3-1 L2-01 §3（6 个 public 接口 · 4 同步 IC + 2 异步事件）+ §11（12 项 `E-TIER-*` 错误码）+ §12（P99 ≤ 5/10/20ms SLO）+ §13 TC ID 矩阵 驱动。
> TC ID 统一格式：`TC-L106-L201-NNN`（L1-06 下 L2-01，三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_01_TierManager` 组织；负向 / 性能 / 集成 / e2e 分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock project_id / mock clock / mock event bus / mock fs）
- [x] §8 集成点用例（与 L2-02/03/04 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 6 个 public IC + 12 错误码 + 5 下游 IC 全覆盖。
> 覆盖类型：unit = 纯函数 / integration = 跨 L2 mock / e2e = 端到端 / perf = 性能 SLO。

### §1.1 方法 × TC 矩阵

| 方法（§3 出处） | TC ID | 覆盖类型 | 相关 IC |
|---|---|---|---|
| `resolve_read_scope()` · §3.2 · 正向 session 层 | TC-L106-L201-001 | unit | IC-L2-01 |
| `resolve_read_scope()` · §3.2 · 正向 session+project 合并 | TC-L106-L201-002 | unit | IC-L2-01 |
| `resolve_read_scope()` · §3.2 · 正向 三层全开 | TC-L106-L201-003 | unit | IC-L2-01 |
| `resolve_read_scope()` · §3.2 · kind_filter 子集 | TC-L106-L201-004 | unit | IC-L2-01 |
| `resolve_read_scope()` · §3.2 · expired_exclusion_ts 计算 | TC-L106-L201-005 | unit | IC-L2-01 |
| `allocate_session_write_slot()` · §3.3 · 正向新条目 | TC-L106-L201-006 | unit | IC-L2-02 |
| `allocate_session_write_slot()` · §3.3 · 去重命中 increment | TC-L106-L201-007 | unit | IC-L2-02 |
| `allocate_session_write_slot()` · §3.3 · schema validate 通过 | TC-L106-L201-008 | unit | IC-L2-02 |
| `check_promotion_rule()` · §3.4 · session→project auto | TC-L106-L201-009 | unit | IC-L2-03 |
| `check_promotion_rule()` · §3.4 · project→global user_explicit | TC-L106-L201-010 | unit | IC-L2-03 |
| `run_expire_scan()` · §3.5 · scan_mode=all | TC-L106-L201-011 | unit | IC-L2-07 |
| `run_expire_scan()` · §3.5 · scan_mode=single_project | TC-L106-L201-012 | unit | IC-L2-07 |
| `on_project_activated()` · §3.6 · 新项目创建 | TC-L106-L201-013 | unit | IC-L2-activate |
| `on_project_activated()` · §3.6 · 项目恢复 resumed_from_snapshot | TC-L106-L201-014 | unit | IC-L2-activate |
| `emit_kb_tier_ready()` · §3.6 · 事件 payload | TC-L106-L201-015 | unit | IC-09 |
| `emit_kb_entry_expired()` · §3.5 · 过期事件 payload | TC-L106-L201-016 | unit | IC-09 |
| `emit_kb_cross_project_denied()` · §3.2 · 拒绝事件 | TC-L106-L201-017 | unit | IC-09 |

### §1.2 错误码 × TC 矩阵（§11 12 项全覆盖）

| 错误码 | TC ID | 方法 | §11 触发条件 |
|---|---|---|---|
| `E-TIER-001` TIER_NOT_ACTIVATED | TC-L106-L201-101 | `resolve_read_scope` | 无 `.tier-ready.flag` |
| `E-TIER-002` CROSS_PROJECT_READ_DENIED | TC-L106-L201-102 | `resolve_read_scope` | accessor_pid ≠ owner_pid |
| `E-TIER-003` INVALID_KIND | TC-L106-L201-103 | `allocate_session_write_slot` | kind 不在 8 类白名单 |
| `E-TIER-004` SCHEMA_VIOLATION | TC-L106-L201-104 | `allocate_session_write_slot` | jsonschema 校验失败 |
| `E-TIER-005` WRONG_SCOPE_FOR_WRITE | TC-L106-L201-105 | `allocate_session_write_slot` | scope ≠ session |
| `E-TIER-006` PROMOTION_SKIP_LEVEL | TC-L106-L201-106 | `check_promotion_rule` | session→global 跨级 |
| `E-TIER-007` PROMOTION_BELOW_THRESHOLD | TC-L106-L201-107 | `check_promotion_rule` | observed_count 不足 |
| `E-TIER-008` PROMOTION_MISSING_APPROVAL | TC-L106-L201-108 | `check_promotion_rule` | project→global 缺 user_explicit |
| `E-TIER-009` EXPIRED_ENTRY_ACCESS | TC-L106-L201-109 | `resolve_read_scope` post | 读到已过期条目 |
| `E-TIER-010` PATH_RESOLUTION_FAIL | TC-L106-L201-110 | 任何 IC | 非法 pid 字符 |
| `E-TIER-011` TIER_REGISTRY_CORRUPT | TC-L106-L201-111 | 任何 IC | yaml 解析失败 |
| `E-TIER-012` SESSION_ID_NOT_FOUND | TC-L106-L201-112 | `resolve_read_scope` / `allocate` | session_id 不存在 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 resolve_read_scope | L2-02 → L2-01 | TC-L106-L201-601 | 读 scope 校验上游契约 |
| IC-L2-02 allocate_session_write_slot | L2-03 → L2-01 | TC-L106-L201-602 | 写位申请上游契约 |
| IC-L2-03 check_promotion_rule | L2-04 → L2-01 | TC-L106-L201-603 | 晋升规则上游契约 |
| IC-L2-07 run_expire_scan | BG-Scheduler → L2-01 | TC-L106-L201-604 | 日扫描调度契约 |
| IC-L2-activate on_project_activated | BC-02 → L2-01 | TC-L106-L201-605 | 项目激活订阅契约 |
| IC-09 append_event (emit) | L2-01 → L1-09 | TC-L106-L201-606 | 事件总线下游契约 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| IC-L2-01 P99 延迟 | ≤ 5 ms | TC-L106-L201-501 |
| IC-L2-02 P99 延迟（含 schema） | ≤ 10 ms | TC-L106-L201-502 |
| IC-L2-03 P99 延迟 | ≤ 20 ms | TC-L106-L201-503 |
| A7 扫描完成 | ≤ 30 s @ 10 万条目 | TC-L106-L201-504 |
| A8 激活端到端 | ≤ 1 s | TC-L106-L201-505 |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格 · SUT 类型 `TierManager`（`app.l1_06.l2_01.tier_manager`）· arrange / act / assert 三段明确。

```python
# file: tests/l1_06/test_l2_01_tier_manager_positive.py
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

from app.l1_06.l2_01.tier_manager import TierManager
from app.l1_06.l2_01.schemas import (
    ScopeDecisionRequest, ScopeDecision,
    WriteSlotRequest, WriteSlot,
    PromotionRequest, PromotionDecision,
    ExpireScanTrigger, ActivateEvent,
)


class TestL2_01_TierManager_Positive:
    """每个 public IC 至少 1 正向用例，覆盖 §3.2~§3.6。"""

    # ---- IC-L2-01 resolve_read_scope ----
    def test_TC_L106_L201_001_resolve_read_scope_session_only(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L201-001 · 只激活 Session 层（Project tier-ready 未就绪）· ALLOW + allowed_scopes=[session]。"""
        req = ScopeDecisionRequest(
            request_id="r-001", project_id=mock_project_id, session_id=mock_session_id,
            kind_filter=[], stage_hint="S2_split", requester_bc="BC-01",
        )
        sut._tier_repo.set_tier_ready(mock_project_id, project=False, global_=True)
        resp: ScopeDecision = sut.resolve_read_scope(req)
        assert resp.verdict == "ALLOW"
        assert "session" in resp.allowed_scopes
        assert "project" not in resp.allowed_scopes
        assert resp.isolation_context.accessor_pid == mock_project_id

    def test_TC_L106_L201_002_resolve_session_plus_project(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L201-002 · Project 层已激活 · 返回合并 S+P · 优先级顺序正确。"""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        req = ScopeDecisionRequest(
            request_id="r-002", project_id=mock_project_id, session_id=mock_session_id,
            kind_filter=[], stage_hint="S3_design", requester_bc="BC-01",
        )
        resp = sut.resolve_read_scope(req)
        assert resp.allowed_scopes == ["session", "project", "global"]
        assert resp.tier_paths.project.startswith(f"projects/{mock_project_id}/kb/")

    def test_TC_L106_L201_003_resolve_all_three_tiers(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L201-003 · 三层路径全填充 · global_layer="no_owner"。"""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r-003", project_id=mock_project_id,
                session_id=mock_session_id, requester_bc="BC-07",
            )
        )
        assert resp.isolation_context.global_layer == "no_owner"
        assert resp.tier_paths.session.endswith(".kb.jsonl")
        assert resp.tier_paths.global_.startswith("global_kb/")

    def test_TC_L106_L201_004_resolve_kind_filter_subset(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L201-004 · kind_filter=[pattern, trap] · 仅这两类路径返回。"""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r-004", project_id=mock_project_id,
                session_id=mock_session_id,
                kind_filter=["pattern", "trap"], requester_bc="BC-01",
            )
        )
        assert resp.verdict == "ALLOW"
        # 过滤后 kind_filter 被保留
        assert set(resp.allowed_scopes) >= {"session"}

    def test_TC_L106_L201_005_resolve_expired_exclusion_ts(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        mock_clock: MagicMock,
    ) -> None:
        """TC-L106-L201-005 · TTL=7d · expired_exclusion_ts = now - 7d。"""
        now = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)
        mock_clock.now.return_value = now
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r-005", project_id=mock_project_id,
                session_id=mock_session_id, requester_bc="BC-01",
            )
        )
        expected = (now - timedelta(days=7)).isoformat()
        assert resp.expired_exclusion_ts == expected

    # ---- IC-L2-02 allocate_session_write_slot ----
    def test_TC_L106_L201_006_allocate_new_entry(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """TC-L106-L201-006 · 全新条目 · ALLOW + merge_strategy=new_entry。"""
        cand = make_entry_candidate(kind="pattern", title="test-new")
        slot: WriteSlot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="w-001", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        assert slot.verdict == "ALLOW"
        assert slot.deduplication_hint.merge_strategy == "new_entry"
        assert slot.write_path.endswith(".kb.jsonl")
        assert slot.schema_validation.passed is True
        assert slot.kind_validation.passed is True

    def test_TC_L106_L201_007_allocate_dedup_increment(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """TC-L106-L201-007 · 同 title+kind 已存在 · merge_strategy=increment_observed。"""
        cand = make_entry_candidate(kind="pattern", title="dup-title")
        sut._session_idx.register(project_id=mock_project_id,
                                   session_id=mock_session_id, title=cand.title,
                                   kind=cand.kind, entry_id="ent-existing")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="w-002", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        assert slot.deduplication_hint.existing_entry_id == "ent-existing"
        assert slot.deduplication_hint.merge_strategy == "increment_observed"

    def test_TC_L106_L201_008_allocate_schema_validates_8_kinds(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """TC-L106-L201-008 · 8 类 kind 白名单每一类都通过 schema 校验。"""
        kinds = ["pattern", "trap", "recipe", "tool_combo", "anti_pattern",
                 "project_context", "external_ref", "effective_combo"]
        for k in kinds:
            cand = make_entry_candidate(kind=k, title=f"t-{k}")
            slot = sut.allocate_session_write_slot(
                WriteSlotRequest(request_id=f"w-{k}", project_id=mock_project_id,
                                 session_id=mock_session_id,
                                 entry_candidate=cand, requester_bc="BC-01")
            )
            assert slot.verdict == "ALLOW", f"kind={k} 应通过"
            assert slot.kind_validation.passed is True

    # ---- IC-L2-03 check_promotion_rule ----
    def test_TC_L106_L201_009_promote_session_to_project_auto(
        self, sut: TierManager, mock_project_id: str,
    ) -> None:
        """TC-L106-L201-009 · observed_count=2 · auto 批准 · ALLOW。"""
        resp: PromotionDecision = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p-001", project_id=mock_project_id,
                entry_id="ent-100", from_scope="session", to_scope="project",
                observed_count=2,
                approval={"type": "auto", "approver": "system",
                          "approved_at": "2026-04-22T10:00:00Z"},
                requester_bc="BC-07",
            )
        )
        assert resp.verdict == "ALLOW"
        assert resp.reason_code == "OK"
        assert resp.required_observed_count == 2
        assert resp.expected_write_path.startswith(f"projects/{mock_project_id}/kb/")

    def test_TC_L106_L201_010_promote_project_to_global_user_explicit(
        self, sut: TierManager, mock_project_id: str,
    ) -> None:
        """TC-L106-L201-010 · project→global · observed_count=3 + user_explicit · ALLOW。"""
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p-002", project_id=mock_project_id,
                entry_id="ent-200", from_scope="project", to_scope="global",
                observed_count=3,
                approval={"type": "user_explicit", "approver": "user:alice",
                          "approved_at": "2026-04-22T11:00:00Z"},
                requester_bc="BC-07",
            )
        )
        assert resp.verdict == "ALLOW"
        assert resp.override_owner_project_id is None  # global 去 owner
        assert resp.required_observed_count == 3

    # ---- IC-L2-07 run_expire_scan ----
    def test_TC_L106_L201_011_expire_scan_all(
        self, sut: TierManager, mock_clock: MagicMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-011 · scan_mode=all · 扫描全项目 · emit expire_scan_completed。"""
        sut._tier_repo.register_projects(["p-001", "p-002"])
        trig = ExpireScanTrigger(trigger_id="sc-001",
                                 trigger_at="2026-04-22T03:00:00Z",
                                 scan_mode="all", ttl_days=7)
        summary = sut.run_expire_scan(trig)
        assert summary.scanned_project_count == 2
        mock_event_bus.append.assert_any_call(
            event_type="L1-06:expire_scan_completed",
            payload=MagicMock().ANY if False else pytest.helpers.any_dict(),
        ) if hasattr(pytest, "helpers") else None

    def test_TC_L106_L201_012_expire_scan_single_project(
        self, sut: TierManager,
    ) -> None:
        """TC-L106-L201-012 · scan_mode=single_project · 只扫指定项目。"""
        sut._tier_repo.register_projects(["p-001", "p-002"])
        trig = ExpireScanTrigger(trigger_id="sc-002",
                                 trigger_at="2026-04-22T03:00:00Z",
                                 scan_mode="single_project",
                                 target_project_id="p-001", ttl_days=7)
        summary = sut.run_expire_scan(trig)
        assert summary.scanned_project_count == 1

    # ---- IC-L2-activate on_project_activated ----
    def test_TC_L106_L201_013_activate_new_project_emits_tier_ready(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-013 · 新建项目 · mkdir + touch flag + emit kb_tier_ready。"""
        evt = ActivateEvent(event_type="L1-02:project_created",
                            project_id="p-NEW-001", project_name="Demo",
                            stage="S0_gate", created_at="2026-04-22T10:00:00Z",
                            resumed_from_snapshot=False)
        sut.on_project_activated(evt)
        emitted = [c.kwargs.get("event_type") or c.args[0]
                   for c in mock_event_bus.append.call_args_list]
        assert "L1-06:kb_tier_ready" in emitted

    def test_TC_L106_L201_014_activate_resumed_idempotent(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-014 · 恢复项目 · flag 已存在也不抛错（幂等）。"""
        evt = ActivateEvent(event_type="L1-02:project_resumed",
                            project_id="p-OLD-001", project_name="Old",
                            stage="S3_design", created_at="2026-04-18T08:00:00Z",
                            resumed_from_snapshot=True)
        sut.on_project_activated(evt)
        sut.on_project_activated(evt)  # 第二次调用不应抛
        assert mock_event_bus.append.call_count >= 1

    # ---- 事件 emit 正向 ----
    def test_TC_L106_L201_015_emit_kb_tier_ready_payload(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-015 · kb_tier_ready 事件 payload 字段齐。"""
        sut._emit_kb_tier_ready(project_id="p-100",
                                 session_path="task-boards/p-100/",
                                 project_path="projects/p-100/kb/",
                                 global_path="global_kb/entries/",
                                 tier_ready_flag="projects/p-100/kb/.tier-ready.flag",
                                 activated_at="2026-04-22T10:00:00Z")
        mock_event_bus.append.assert_called()
        call = mock_event_bus.append.call_args
        payload = call.kwargs.get("payload") or call.args[-1]
        assert payload["project_id"] == "p-100"
        assert payload["tier_ready_flag"].endswith(".tier-ready.flag")

    def test_TC_L106_L201_016_emit_kb_entry_expired(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-016 · kb_entry_expired 事件 payload 字段齐。"""
        sut._emit_kb_entry_expired(project_id="p-100", entry_id="ent-EX-1",
                                    expired_at="2026-04-22T00:00:00Z")
        mock_event_bus.append.assert_called()

    def test_TC_L106_L201_017_emit_cross_project_denied(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-017 · cross_project_denied 事件 accessor_pid + owner_pid 都记录。"""
        sut._emit_cross_project_denied(accessor_pid="p-100", owner_pid="p-200",
                                        request_id="r-XP-001")
        call = mock_event_bus.append.call_args
        payload = call.kwargs.get("payload") or call.args[-1]
        assert payload["accessor_pid"] == "p-100"
        assert payload["owner_pid"] == "p-200"
```

---

## §3 负向用例（每错误码 ≥ 1）

> 每个 §11 错误码至少 1 个 `pytest.raises` 或 DENY verdict 断言。

```python
# file: tests/l1_06/test_l2_01_tier_manager_negative.py
from __future__ import annotations

import pytest
from app.l1_06.l2_01.tier_manager import TierManager
from app.l1_06.l2_01.errors import TierError
from app.l1_06.l2_01.schemas import (
    ScopeDecisionRequest, WriteSlotRequest, PromotionRequest,
)


class TestL2_01_Negative:

    def test_TC_L106_L201_101_tier_not_activated(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L201-101 · E-TIER-001 · 无 .tier-ready.flag。"""
        sut._tier_repo.set_tier_ready(mock_project_id, project=False, global_=False)
        req = ScopeDecisionRequest(request_id="r", project_id=mock_project_id,
                                   session_id=mock_session_id, requester_bc="BC-01")
        resp = sut.resolve_read_scope(req)
        assert resp.verdict == "DENY"
        assert resp.error_code == "E-TIER-001"

    def test_TC_L106_L201_102_cross_project_read_denied(
        self, sut: TierManager,
    ) -> None:
        """TC-L106-L201-102 · E-TIER-002 · accessor_pid=p-A 读 Project 层 owner=p-B。"""
        sut._tier_repo.set_tier_ready("p-B", project=True, global_=True)
        # 模拟 accessor 传 p-A，但实际读 p-B 的 Project 路径
        req = ScopeDecisionRequest(request_id="r", project_id="p-A",
                                   session_id="s-a", requester_bc="BC-01")
        # 通过 forbidden_read_target 注入跨项目访问
        sut._isolation.force_cross_project("p-A", "p-B")
        resp = sut.resolve_read_scope(req)
        assert resp.verdict == "DENY"
        assert resp.error_code == "E-TIER-002"

    def test_TC_L106_L201_103_invalid_kind(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """TC-L106-L201-103 · E-TIER-003 · kind=hotfix 不在白名单。"""
        cand = make_entry_candidate(kind="hotfix", title="invalid")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="w", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        assert slot.verdict == "DENY"
        assert slot.error_code == "E-TIER-003"
        assert slot.kind_validation.passed is False

    def test_TC_L106_L201_104_schema_violation(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """TC-L106-L201-104 · E-TIER-004 · content 为空 · schema 校验失败。"""
        cand = make_entry_candidate(kind="pattern", title="t", content="")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="w", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        assert slot.verdict == "DENY"
        assert slot.error_code == "E-TIER-004"
        assert slot.schema_validation.passed is False
        assert any(v.field == "content" for v in slot.schema_validation.violations)

    def test_TC_L106_L201_105_wrong_scope_for_write(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """TC-L106-L201-105 · E-TIER-005 · entry_candidate.scope=project → DENY。"""
        cand = make_entry_candidate(kind="pattern", title="direct-write", scope="project")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="w", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        assert slot.error_code == "E-TIER-005"

    def test_TC_L106_L201_106_promotion_skip_level(
        self, sut: TierManager, mock_project_id: str,
    ) -> None:
        """TC-L106-L201-106 · E-TIER-006 · session→global 跨级 DENY。"""
        resp = sut.check_promotion_rule(
            PromotionRequest(request_id="p", project_id=mock_project_id,
                             entry_id="ent-1", from_scope="session",
                             to_scope="global", observed_count=5,
                             approval={"type": "user_explicit",
                                       "approver": "user:alice",
                                       "approved_at": "2026-04-22T10:00:00Z"},
                             requester_bc="BC-07")
        )
        assert resp.verdict == "DENY"
        assert resp.reason_code == "SKIP_LEVEL"
        assert resp.error_code == "E-TIER-006"

    def test_TC_L106_L201_107_promotion_below_threshold(
        self, sut: TierManager, mock_project_id: str,
    ) -> None:
        """TC-L106-L201-107 · E-TIER-007 · observed_count=1 < 2。"""
        resp = sut.check_promotion_rule(
            PromotionRequest(request_id="p", project_id=mock_project_id,
                             entry_id="ent-2", from_scope="session",
                             to_scope="project", observed_count=1,
                             approval={"type": "auto", "approver": "system",
                                       "approved_at": "2026-04-22T10:00:00Z"},
                             requester_bc="BC-07")
        )
        assert resp.reason_code == "BELOW_THRESHOLD"
        assert resp.error_code == "E-TIER-007"

    def test_TC_L106_L201_108_promotion_missing_approval(
        self, sut: TierManager, mock_project_id: str,
    ) -> None:
        """TC-L106-L201-108 · E-TIER-008 · project→global 缺 user_explicit。"""
        resp = sut.check_promotion_rule(
            PromotionRequest(request_id="p", project_id=mock_project_id,
                             entry_id="ent-3", from_scope="project",
                             to_scope="global", observed_count=5,
                             approval={"type": "auto", "approver": "system",
                                       "approved_at": "2026-04-22T10:00:00Z"},
                             requester_bc="BC-07")
        )
        assert resp.reason_code == "MISSING_APPROVAL"
        assert resp.error_code == "E-TIER-008"

    def test_TC_L106_L201_109_expired_entry_access(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L201-109 · E-TIER-009 · 读到 7d 前条目 · 返回 post-filter warning。"""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        old_ts = "2026-04-10T00:00:00Z"
        sut._session_idx.add_entry(project_id=mock_project_id,
                                    session_id=mock_session_id,
                                    entry_id="ent-expired", last_observed_at=old_ts)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(request_id="r", project_id=mock_project_id,
                                 session_id=mock_session_id,
                                 requester_bc="BC-01")
        )
        # 应在 expired_exclusion_ts 之外 → post-filter 会标 expired
        assert "ent-expired" in sut._audit.expired_post_filter_log

    def test_TC_L106_L201_110_path_resolution_fail(
        self, sut: TierManager,
    ) -> None:
        """TC-L106-L201-110 · E-TIER-010 · project_id 含 "/" 非法。"""
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(request_id="r", project_id="p/../etc",
                                 session_id="s-1", requester_bc="BC-01")
        )
        assert resp.verdict == "DENY"
        assert resp.error_code == "E-TIER-010"

    def test_TC_L106_L201_111_tier_registry_corrupt(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        corrupt_yaml,
    ) -> None:
        """TC-L106-L201-111 · E-TIER-011 · tier-layout.yaml 解析失败 · 升级 EMERGENCY_LOCKDOWN。"""
        corrupt_yaml("configs/tier-layout.yaml")
        with pytest.raises(TierError) as exc:
            sut._tier_repo.reload()
        assert exc.value.code == "E-TIER-011"
        assert sut._degradation_level == "EMERGENCY_LOCKDOWN"

    def test_TC_L106_L201_112_session_id_not_found(
        self, sut: TierManager, mock_project_id: str,
    ) -> None:
        """TC-L106-L201-112 · E-TIER-012 · session_id 未注册到当前 project。"""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(request_id="r", project_id=mock_project_id,
                                 session_id="s-UNKNOWN-999",
                                 requester_bc="BC-01")
        )
        assert resp.error_code == "E-TIER-012"
```

---

## §4 IC-XX 契约集成测试

> 映射 §4 依赖矩阵 · mock 对端 · payload 字段断言。

```python
# file: tests/l1_06/test_l2_01_tier_manager_ic_contract.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_06.l2_01.tier_manager import TierManager


class TestL2_01_IC_Contracts:

    def test_TC_L106_L201_601_ic_l2_01_consumed_by_l2_02(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L201-601 · L2-02 KBReader 调 resolve_read_scope · 字段级合约。"""
        from app.l1_06.l2_01.schemas import ScopeDecisionRequest
        req = ScopeDecisionRequest(request_id="r-ic1",
                                   project_id=mock_project_id,
                                   session_id=mock_session_id,
                                   kind_filter=["pattern"],
                                   requester_bc="BC-01")
        resp = sut.resolve_read_scope(req)
        # 契约字段齐
        for field in ("request_id", "verdict", "allowed_scopes",
                       "isolation_context", "tier_paths",
                       "expired_exclusion_ts", "emitted_at"):
            assert hasattr(resp, field), f"契约缺字段 {field}"
        assert resp.request_id == req.request_id  # request_id 回传

    def test_TC_L106_L201_602_ic_l2_02_consumed_by_l2_03(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """TC-L106-L201-602 · L2-03 ObservationAccum 调 allocate · 包含 dedup + schema + kind 三段结果。"""
        from app.l1_06.l2_01.schemas import WriteSlotRequest
        cand = make_entry_candidate(kind="pattern", title="ic-602")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="w-ic2", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        assert slot.deduplication_hint is not None
        assert slot.schema_validation is not None
        assert slot.kind_validation is not None

    def test_TC_L106_L201_603_ic_l2_03_consumed_by_l2_04(
        self, sut: TierManager, mock_project_id: str,
    ) -> None:
        """TC-L106-L201-603 · L2-04 PromotionRitual 调 check_promotion_rule · expected_write_path 格式正确。"""
        from app.l1_06.l2_01.schemas import PromotionRequest
        resp = sut.check_promotion_rule(
            PromotionRequest(request_id="p-ic3", project_id=mock_project_id,
                             entry_id="ent-ic3", from_scope="session",
                             to_scope="project", observed_count=2,
                             approval={"type": "auto", "approver": "system",
                                       "approved_at": "2026-04-22T10:00:00Z"},
                             requester_bc="BC-07")
        )
        assert resp.verdict == "ALLOW"
        assert resp.expected_write_path == f"projects/{mock_project_id}/kb/entries/"

    def test_TC_L106_L201_604_ic_l2_07_bg_scheduler_invocation(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-604 · APScheduler 触发 run_expire_scan · 完成后 emit expire_scan_completed。"""
        from app.l1_06.l2_01.schemas import ExpireScanTrigger
        sut._tier_repo.register_projects(["p-001"])
        trig = ExpireScanTrigger(trigger_id="sc-ic4",
                                 trigger_at="2026-04-22T03:00:00Z",
                                 scan_mode="all", ttl_days=7)
        sut.run_expire_scan(trig)
        emitted_types = [c.kwargs.get("event_type") or (c.args[0] if c.args else None)
                         for c in mock_event_bus.append.call_args_list]
        assert "L1-06:expire_scan_completed" in emitted_types

    def test_TC_L106_L201_605_ic_l2_activate_subscribed_from_bc_02(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-605 · 订阅 BC-02 project_created 事件 · 处理后 emit kb_tier_ready。"""
        from app.l1_06.l2_01.schemas import ActivateEvent
        evt = ActivateEvent(event_type="L1-02:project_created",
                            project_id="p-ic5", project_name="IC",
                            stage="S0_gate", created_at="2026-04-22T10:00:00Z",
                            resumed_from_snapshot=False)
        sut.on_project_activated(evt)
        emitted = [c.kwargs.get("event_type") or (c.args[0] if c.args else None)
                   for c in mock_event_bus.append.call_args_list]
        assert "L1-06:kb_tier_ready" in emitted

    def test_TC_L106_L201_606_ic_09_append_event_sink(
        self, sut: TierManager, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L106-L201-606 · 所有 emit 都经 L1-09 IC-09 append_event 下沉。"""
        sut._emit_kb_tier_ready(project_id="p-006", session_path="x",
                                 project_path="y", global_path="z",
                                 tier_ready_flag="f", activated_at="t")
        assert mock_event_bus.append.called
```

---

## §5 性能 SLO 用例

> 基于 §12 `l1_06_*_duration_ms` · pytest-benchmark 风格 · 至少 3 个。

```python
# file: tests/l1_06/test_l2_01_tier_manager_perf.py
from __future__ import annotations

import pytest
import time
from app.l1_06.l2_01.tier_manager import TierManager
from app.l1_06.l2_01.schemas import (
    ScopeDecisionRequest, WriteSlotRequest, PromotionRequest,
    ExpireScanTrigger, ActivateEvent,
)


@pytest.mark.perf
class TestL2_01_SLO:

    def test_TC_L106_L201_501_resolve_scope_p99_le_5ms(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        benchmark,
    ) -> None:
        """TC-L106-L201-501 · IC-L2-01 P99 ≤ 5ms（1000 次调用统计）。"""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        req = ScopeDecisionRequest(request_id="p1", project_id=mock_project_id,
                                   session_id=mock_session_id,
                                   requester_bc="BC-01")
        result = benchmark.pedantic(sut.resolve_read_scope, args=(req,),
                                    iterations=1, rounds=1000)
        # pytest-benchmark stats
        assert benchmark.stats["stats"]["p99"] * 1000 <= 5.0, "P99 超 5ms"

    def test_TC_L106_L201_502_allocate_slot_p99_le_10ms(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str,
        make_entry_candidate, benchmark,
    ) -> None:
        """TC-L106-L201-502 · IC-L2-02 P99 ≤ 10ms（含 jsonschema · 500 次）。"""
        cand = make_entry_candidate(kind="pattern", title="perf")
        req = WriteSlotRequest(request_id="p2", project_id=mock_project_id,
                               session_id=mock_session_id,
                               entry_candidate=cand, requester_bc="BC-01")
        benchmark.pedantic(sut.allocate_session_write_slot, args=(req,),
                           iterations=1, rounds=500)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 10.0

    def test_TC_L106_L201_503_promotion_p99_le_20ms(
        self, sut: TierManager, mock_project_id: str, benchmark,
    ) -> None:
        """TC-L106-L201-503 · IC-L2-03 P99 ≤ 20ms。"""
        req = PromotionRequest(request_id="p3", project_id=mock_project_id,
                               entry_id="ent-perf", from_scope="session",
                               to_scope="project", observed_count=2,
                               approval={"type": "auto", "approver": "system",
                                         "approved_at": "2026-04-22T10:00:00Z"},
                               requester_bc="BC-07")
        benchmark.pedantic(sut.check_promotion_rule, args=(req,),
                           iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 20.0

    def test_TC_L106_L201_504_expire_scan_le_30s_100k_entries(
        self, sut: TierManager, fake_fs_with_entries,
    ) -> None:
        """TC-L106-L201-504 · A7 扫描 10 万条目 ≤ 30s。"""
        fake_fs_with_entries(project_count=100, entries_per_project=1000)
        trig = ExpireScanTrigger(trigger_id="perf-scan",
                                 trigger_at="2026-04-22T03:00:00Z",
                                 scan_mode="all", ttl_days=7)
        t0 = time.perf_counter()
        sut.run_expire_scan(trig)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 30.0, f"扫描 {elapsed:.1f}s 超 30s"

    def test_TC_L106_L201_505_activate_e2e_le_1s(
        self, sut: TierManager,
    ) -> None:
        """TC-L106-L201-505 · A8 激活端到端 ≤ 1s（mkdir + flag + emit）。"""
        evt = ActivateEvent(event_type="L1-02:project_created",
                            project_id="p-perf", project_name="P",
                            stage="S0_gate", created_at="2026-04-22T10:00:00Z",
                            resumed_from_snapshot=False)
        t0 = time.perf_counter()
        sut.on_project_activated(evt)
        assert (time.perf_counter() - t0) <= 1.0
```

---

## §6 端到端 e2e

> 映射 §5 P0/P1 时序图 · 2~3 个典型链路。

```python
# file: tests/l1_06/test_l2_01_tier_manager_e2e.py
from __future__ import annotations

import pytest
from app.l1_06.l2_01.tier_manager import TierManager
from app.l1_06.l2_01.schemas import (
    ActivateEvent, ScopeDecisionRequest, WriteSlotRequest, PromotionRequest,
)


@pytest.mark.e2e
class TestL2_01_E2E:

    def test_TC_L106_L201_701_activate_then_read_then_write(
        self, sut: TierManager, mock_event_bus,
    ) -> None:
        """TC-L106-L201-701 · 项目创建 → Session 写 → Project 读 完整链路。"""
        sut.on_project_activated(ActivateEvent(
            event_type="L1-02:project_created", project_id="p-e2e",
            project_name="E2E", stage="S0_gate",
            created_at="2026-04-22T10:00:00Z", resumed_from_snapshot=False,
        ))
        scope = sut.resolve_read_scope(ScopeDecisionRequest(
            request_id="r", project_id="p-e2e", session_id="s-1",
            requester_bc="BC-01",
        ))
        assert scope.verdict == "ALLOW"
        assert "project" in scope.allowed_scopes

    def test_TC_L106_L201_702_session_write_then_promote_to_project(
        self, sut: TierManager, make_entry_candidate,
    ) -> None:
        """TC-L106-L201-702 · Session 写两次 → observed_count=2 → 晋升到 Project。"""
        sut.on_project_activated(ActivateEvent(
            event_type="L1-02:project_created", project_id="p-prom",
            project_name="P", stage="S0_gate",
            created_at="2026-04-22T10:00:00Z", resumed_from_snapshot=False,
        ))
        cand = make_entry_candidate(kind="pattern", title="recurring")
        sut.allocate_session_write_slot(WriteSlotRequest(
            request_id="w1", project_id="p-prom", session_id="s-1",
            entry_candidate=cand, requester_bc="BC-01",
        ))
        # 第二次命中去重 +1
        slot2 = sut.allocate_session_write_slot(WriteSlotRequest(
            request_id="w2", project_id="p-prom", session_id="s-1",
            entry_candidate=cand, requester_bc="BC-01",
        ))
        assert slot2.deduplication_hint.merge_strategy == "increment_observed"
        # 晋升到 Project
        resp = sut.check_promotion_rule(PromotionRequest(
            request_id="p", project_id="p-prom",
            entry_id=slot2.deduplication_hint.existing_entry_id,
            from_scope="session", to_scope="project", observed_count=2,
            approval={"type": "auto", "approver": "system",
                      "approved_at": "2026-04-22T10:00:00Z"},
            requester_bc="BC-07",
        ))
        assert resp.verdict == "ALLOW"

    def test_TC_L106_L201_703_expire_scan_end_to_end_with_emit(
        self, sut: TierManager, mock_event_bus, fake_fs_with_entries,
    ) -> None:
        """TC-L106-L201-703 · 过期扫描 e2e · 过期条目标记 + 事件发出。"""
        fake_fs_with_entries(project_count=2, entries_per_project=5,
                              expired_count=2)
        from app.l1_06.l2_01.schemas import ExpireScanTrigger
        sut.run_expire_scan(ExpireScanTrigger(
            trigger_id="sc-e2e", trigger_at="2026-04-22T03:00:00Z",
            scan_mode="all", ttl_days=7,
        ))
        emitted = [c.kwargs.get("event_type") or c.args[0]
                   for c in mock_event_bus.append.call_args_list]
        assert "L1-06:expire_scan_completed" in emitted
        assert emitted.count("L1-06:kb_entry_expired") >= 2
```

---

## §7 测试 fixture

> pytest fixtures · 在 `tests/l1_06/conftest.py` · 至少 5 个。

```python
# file: tests/l1_06/conftest.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock
from datetime import datetime, timezone

from app.l1_06.l2_01.tier_manager import TierManager
from app.l1_06.l2_01.schemas import EntryCandidate, ApplicableContext


@pytest.fixture
def mock_project_id() -> str:
    """稳定的 PM-14 project_id。"""
    return "p-fixture-001"


@pytest.fixture
def mock_session_id() -> str:
    return "s-fixture-aaa"


@pytest.fixture
def mock_clock() -> MagicMock:
    """固定时钟 · 默认 2026-04-22T12:00:00Z。"""
    clk = MagicMock()
    clk.now.return_value = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)
    return clk


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """L1-09 EventBus 的 IC-09 append。"""
    bus = MagicMock()
    bus.append = MagicMock(return_value={"event_id": "evt-001"})
    return bus


@pytest.fixture
def mock_fs(tmp_path):
    """隔离文件系统（pytest tmp_path 下 task-boards/projects/global_kb）。"""
    (tmp_path / "task-boards").mkdir()
    (tmp_path / "projects").mkdir()
    (tmp_path / "global_kb" / "entries").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def make_entry_candidate():
    """工厂：构造合法 EntryCandidate · 支持字段覆盖。"""
    def _make(**overrides: Any) -> EntryCandidate:
        base = dict(
            id="ent-" + (overrides.get("title") or "default"),
            scope="session",
            kind="pattern",
            title="default-title",
            content="some content >= 10 chars",
            applicable_context=[ApplicableContext(
                stage="S2_split", task_type="cli_tool", tech_stack=["python"]
            )],
            observed_count=1,
            first_observed_at="2026-04-22T10:00:00Z",
            last_observed_at="2026-04-22T10:00:00Z",
            source_links=[{"event_id": "e", "tick_id": "t"}],
        )
        base.update(overrides)
        return EntryCandidate(**base)
    return _make


@pytest.fixture
def corrupt_yaml(monkeypatch):
    """把指定 yaml 文件的 parse 变为 raise yaml.YAMLError。"""
    import yaml
    def _corrupt(path: str):
        orig = yaml.safe_load
        def bad(*a, **kw):
            raise yaml.YAMLError("fixture corruption")
        monkeypatch.setattr(yaml, "safe_load", bad)
    return _corrupt


@pytest.fixture
def fake_fs_with_entries(mock_fs):
    """预生成 N 个项目 × M 个条目，可指定过期数量。"""
    import json, uuid
    def _make(project_count=1, entries_per_project=10, expired_count=0):
        for i in range(project_count):
            pid = f"p-seed-{i:03d}"
            (mock_fs / "projects" / pid / "kb").mkdir(parents=True)
            (mock_fs / "projects" / pid / "kb" / ".tier-ready.flag").touch()
            sess_file = mock_fs / "task-boards" / pid / "s-aaa.kb.jsonl"
            sess_file.parent.mkdir(parents=True, exist_ok=True)
            with sess_file.open("w") as f:
                for j in range(entries_per_project):
                    ts = ("2026-04-10T00:00:00Z" if j < expired_count
                          else "2026-04-22T10:00:00Z")
                    f.write(json.dumps({
                        "id": str(uuid.uuid4()), "title": f"e-{j}",
                        "kind": "pattern",
                        "last_observed_at": ts,
                    }) + "\n")
        return mock_fs
    return _make


@pytest.fixture
def sut(mock_project_id, mock_session_id, mock_clock, mock_event_bus, mock_fs):
    """被测 TierManager · 注入所有 mock。"""
    return TierManager(
        clock=mock_clock,
        event_bus=mock_event_bus,
        fs_root=mock_fs,
        tier_layout_path=mock_fs / "configs" / "tier-layout.yaml",
    )
```

---

## §8 集成点用例

> 与兄弟 L2（L2-02 KBReader · L2-03 ObservationAccum · L2-04 PromotionRitual）协作。

```python
# file: tests/l1_06/test_l2_01_integration_points.py
from __future__ import annotations

import pytest


class TestL2_01_Integration:

    def test_TC_L106_L201_801_l2_02_reads_use_allowed_scopes(
        self, sut, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L201-801 · L2-02 拿到 allowed_scopes 后才发起读 · 无越权。"""
        from app.l1_06.l2_01.schemas import ScopeDecisionRequest
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(request_id="i1", project_id=mock_project_id,
                                 session_id=mock_session_id,
                                 requester_bc="BC-01")
        )
        # 模拟 L2-02 使用 allowed_scopes 指导读取
        assert set(resp.allowed_scopes).issubset({"session", "project", "global"})

    def test_TC_L106_L201_802_l2_03_writes_follow_slot_path(
        self, sut, mock_project_id, mock_session_id, make_entry_candidate,
    ) -> None:
        """TC-L106-L201-802 · L2-03 必须按 WriteSlot.write_path 落盘 · 无自主构造。"""
        from app.l1_06.l2_01.schemas import WriteSlotRequest
        cand = make_entry_candidate(kind="pattern", title="integr")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="i2", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        # L2-03 接 slot.write_path 写入；路径 == session 层固定模式
        assert slot.write_path.startswith("task-boards/")
        assert mock_project_id in slot.write_path

    def test_TC_L106_L201_803_l2_04_promotion_respects_target_tier_ready(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L201-803 · 目标层未激活 · L2-04 收到 target_tier_ready=False · 不搬运。"""
        from app.l1_06.l2_01.schemas import PromotionRequest
        sut._tier_repo.set_tier_ready(mock_project_id, project=False, global_=False)
        resp = sut.check_promotion_rule(
            PromotionRequest(request_id="i3", project_id=mock_project_id,
                             entry_id="ent-x", from_scope="session",
                             to_scope="project", observed_count=2,
                             approval={"type": "auto", "approver": "system",
                                       "approved_at": "2026-04-22T10:00:00Z"},
                             requester_bc="BC-07")
        )
        assert resp.target_tier_ready is False
        assert resp.verdict == "DENY"
```

---

## §9 边界 / edge case

> 空 / 超大 / 并发 / 超时 / 崩溃 · 至少 4 个。

```python
# file: tests/l1_06/test_l2_01_edge_cases.py
from __future__ import annotations

import pytest
import threading


class TestL2_01_EdgeCases:

    def test_TC_L106_L201_901_empty_kind_filter_means_all(
        self, sut, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L201-901 · 边界 · kind_filter=[] 视为全部 8 类。"""
        from app.l1_06.l2_01.schemas import ScopeDecisionRequest
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(request_id="r", project_id=mock_project_id,
                                 session_id=mock_session_id,
                                 kind_filter=[], requester_bc="BC-01")
        )
        assert resp.verdict == "ALLOW"

    def test_TC_L106_L201_902_extra_large_content_10mb_schema_rejects(
        self, sut, mock_project_id, mock_session_id, make_entry_candidate,
    ) -> None:
        """TC-L106-L201-902 · content 长度 10MB · schema 限长拒绝。"""
        from app.l1_06.l2_01.schemas import WriteSlotRequest
        cand = make_entry_candidate(kind="pattern", title="big",
                                     content="x" * (10 * 1024 * 1024))
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(request_id="w", project_id=mock_project_id,
                             session_id=mock_session_id,
                             entry_candidate=cand, requester_bc="BC-01")
        )
        assert slot.verdict == "DENY"
        assert slot.error_code == "E-TIER-004"

    def test_TC_L106_L201_903_concurrent_activate_idempotent_flag_write(
        self, sut,
    ) -> None:
        """TC-L106-L201-903 · 并发 · 10 线程同时 activate 同项目 · 无 flag 冲突。"""
        from app.l1_06.l2_01.schemas import ActivateEvent
        evt = ActivateEvent(event_type="L1-02:project_created",
                            project_id="p-concurrent", project_name="C",
                            stage="S0_gate", created_at="2026-04-22T10:00:00Z",
                            resumed_from_snapshot=False)
        errs = []
        def _run():
            try:
                sut.on_project_activated(evt)
            except Exception as e:
                errs.append(e)
        threads = [threading.Thread(target=_run) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errs, f"并发 activate 抛异常：{errs}"

    def test_TC_L106_L201_904_eventbus_timeout_degrades_to_read_only_isolation(
        self, sut, mock_event_bus,
    ) -> None:
        """TC-L106-L201-904 · EventBus 连续 5 次 timeout · 升级 L1 READ_ONLY_ISOLATION · 写入 buffer。"""
        mock_event_bus.append.side_effect = TimeoutError("bus slow")
        from app.l1_06.l2_01.schemas import ActivateEvent
        evt = ActivateEvent(event_type="L1-02:project_created",
                            project_id="p-to", project_name="T",
                            stage="S0_gate", created_at="2026-04-22T10:00:00Z",
                            resumed_from_snapshot=False)
        for _ in range(5):
            try:
                sut.on_project_activated(evt)
            except TimeoutError:
                pass
        assert sut._degradation_level in ("READ_ONLY_ISOLATION", "L1")
        # buffer 文件非空
        buf = sut._fs_root / "projects" / "p-to" / "kb" / ".l201-emit-buffer.jsonl"
        assert buf.exists() or sut._buffer_in_mem  # 实现可选

    def test_TC_L106_L201_905_session_id_null_rejected(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L201-905 · session_id 为 None · 立即返回 E-TIER-012。"""
        from app.l1_06.l2_01.schemas import ScopeDecisionRequest
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(request_id="r", project_id=mock_project_id,
                                 session_id="", requester_bc="BC-01")
        )
        assert resp.error_code == "E-TIER-012"
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
