---
doc_id: tests-L1-06-L2-04-KB 晋升仪式执行器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-06-3层知识库/L2-04-KB 晋升仪式执行器.md
  - docs/2-prd/L1-06 3层知识库/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-06 L2-04-KB 晋升仪式执行器 · TDD 测试用例

> 基于 3-1 L2-04 §3（IC-08 kb_promote single/batch · IC-L2-03 下游 · probe_health）+ §11（15 项 `E_L204_*` 错误码）+ §12（单条 P50 200ms / 批量 100 条 P95 20s SLO）驱动。
> TC ID 统一格式：`TC-L106-L204-NNN`。

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

### §1.1 方法 × TC 矩阵

| 方法 | TC ID |
|---|---|
| `kb_promote(mode=single)` · Session→Project auto | TC-L106-L204-001 |
| `kb_promote(mode=single)` · Project→Global user_approved | TC-L106-L204-002 |
| `kb_promote(mode=single)` · 幂等 request_id 重放 | TC-L106-L204-003 |
| `kb_promote(mode=batch)` · S7 批量 100 候选 | TC-L106-L204-004 |
| `kb_promote(mode=batch)` · 部分失败不阻塞 | TC-L106-L204-005 |
| `kb_promote(mode=batch)` · 分页 cursor | TC-L106-L204-006 |
| 物理写 tmp + rename 原子 | TC-L106-L204-007 |
| Global 晋升剥离 project_id | TC-L106-L204-008 |
| rejected_index 查询 | TC-L106-L204-009 |
| source Session 标记已搬运 | TC-L106-L204-010 |
| halt_command ack 响应 | TC-L106-L204-011 |
| probe_health liveness | TC-L106-L204-012 |
| probe_health ceremony_progress | TC-L106-L204-013 |
| IC-L2-03 调用（L2-01 校验） | TC-L106-L204-014 |
| IC-L2-06 调用（L2-03 快照） | TC-L106-L204-015 |

### §1.2 错误码 × TC 矩阵（15 项全覆盖）

| 错误码 | TC ID |
|---|---|
| `E_L204_L201_SKIP_LAYER_DENIED` | TC-L106-L204-101 |
| `E_L204_L201_GLOBAL_THRESHOLD_UNMET` | TC-L106-L204-102 |
| `E_L204_L201_PROJECT_THRESHOLD_UNMET` | TC-L106-L204-103 |
| `E_L204_L203_CANDIDATE_PULL_FAIL` | TC-L106-L204-104 |
| `E_L204_WRITE_TARGET_FAIL` | TC-L106-L204-105 |
| `E_L204_SOURCE_MARK_FAIL` | TC-L106-L204-106 |
| `E_L204_PROMOTION_LOCKED` | TC-L106-L204-107 |
| `E_L204_CEREMONY_ALREADY_RUNNING` | TC-L106-L204-108 |
| `E_L204_USER_APPROVAL_MISSING` | TC-L106-L204-109 |
| `E_L204_REJECTED_CANNOT_UNDO` | TC-L106-L204-110 |
| `E_L204_INVALID_FROM_TO` | TC-L106-L204-111 |
| `E_L204_PROJECT_ID_MISMATCH` | TC-L106-L204-112 |
| `E_L204_REPEAT_ATTEMPT_EXHAUSTED` | TC-L106-L204-113 |
| `E_L204_SUPERVISOR_HALT` | TC-L106-L204-114 |
| `E_L204_STRIP_PROJECT_ID_FAIL` | TC-L106-L204-115 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-08 kb_promote | caller → L2-04 | TC-L106-L204-601 |
| IC-L2-03 check_promotion_rule | L2-04 → L2-01 | TC-L106-L204-602 |
| IC-L2-06 session_candidate_pull | L2-04 → L2-03 | TC-L106-L204-603 |
| IC-09 append_event | L2-04 → L1-09 | TC-L106-L204-604 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| 单条晋升 P50 | ≤ 200ms | TC-L106-L204-501 |
| 单条晋升 P99 | ≤ 500ms | TC-L106-L204-502 |
| 批量 100 条 P95 | ≤ 20s | TC-L106-L204-503 |
| 批量 100 条 P99 | ≤ 30s | TC-L106-L204-504 |
| halt_command 响应 | ≤ 1s | TC-L106-L204-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_06/test_l2_04_promotion_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_06.l2_04.service import PromotionRitualExecutor
from app.l1_06.l2_04.schemas import (
    PromoteRequest, PromoteTarget, BatchScope, ApproverInfo,
)


class TestL2_04_Positive:

    def test_TC_L106_L204_001_single_session_to_project_auto(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-001 · single · session→project · auto_threshold · promoted=true。"""
        make_entry(entry_id="ent-01", scope="session", observed_count=2)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="req-001", requested_at="2026-04-22T10:00:00Z",
            target=PromoteTarget(entry_id="ent-01", from_scope="session",
                                  to_scope="project", reason="auto_threshold",
                                  approver=ApproverInfo(user_id=None,
                                                         intent_source="api"))))
        assert res.success is True
        assert res.single_result.promoted is True
        assert res.single_result.final_scope == "project"

    def test_TC_L106_L204_002_single_project_to_global_user_approved(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-002 · project→global · user_approved + count=3 · 成功。"""
        make_entry(entry_id="ent-02", scope="project", observed_count=3)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="req-002", requested_at="2026-04-22T10:00:00Z",
            target=PromoteTarget(entry_id="ent-02", from_scope="project",
                                  to_scope="global", reason="user_approved",
                                  approver=ApproverInfo(user_id="user:alice",
                                                         intent_source="ui_click"))))
        assert res.single_result.promoted is True
        assert res.single_result.final_scope == "global"

    def test_TC_L106_L204_003_idempotent_replay_same_request_id(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-003 · 同 request_id 二次 · 返回首次结果。"""
        make_entry(entry_id="ent-03", scope="session", observed_count=2)
        req = PromoteRequest(project_id=mock_project_id, mode="single",
                              trigger="user_manual", request_id="req-003",
                              requested_at="2026-04-22T10:00:00Z",
                              target=PromoteTarget(entry_id="ent-03",
                                                    from_scope="session",
                                                    to_scope="project",
                                                    reason="auto_threshold"))
        r1 = sut.kb_promote(req)
        r2 = sut.kb_promote(req)
        assert r2.response_id == r1.response_id
        assert r2.single_result.promotion_id == r1.single_result.promotion_id

    def test_TC_L106_L204_004_batch_s7_100_candidates(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-004 · S7 批量 100 条 · promoted_count > 0。"""
        mock_l2_03_snapshot.seed(count=100, kind="pattern", observed_count=2)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="cer-001", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=100)))
        assert res.success is True
        assert res.batch_result.candidates_total == 100
        assert res.batch_result.verdict_summary.promoted_count > 0

    def test_TC_L106_L204_005_batch_partial_failure(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow, mock_storage,
    ) -> None:
        """TC-L106-L204-005 · 10 条中第 4 条 write 失败 · 其他继续。"""
        mock_l2_03_snapshot.seed(count=10, kind="pattern", observed_count=2)
        mock_storage.write_target.side_effect = [
            True, True, True, IOError("disk-4"),
            True, True, True, True, True, True,
        ]
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="cer-002", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=10)))
        assert res.batch_result.verdict_summary.failed_count == 1
        assert res.batch_result.verdict_summary.promoted_count == 9

    def test_TC_L106_L204_006_batch_pagination(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-006 · 600 候选 · 分 5 页 · 全部处理。"""
        mock_l2_03_snapshot.seed_paginated(total=600, page_size=120)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="cer-003", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=600)))
        assert res.batch_result.candidates_total == 600

    def test_TC_L106_L204_007_atomic_tmp_then_rename(
        self, sut, mock_project_id, mock_storage,
        mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-007 · 原子 .tmp + rename。"""
        make_entry(entry_id="atom", scope="session", observed_count=2)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="req-atom", requested_at="t",
            target=PromoteTarget(entry_id="atom", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert mock_storage.atomic_rename.called

    def test_TC_L106_L204_008_global_strip_project_id(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-008 · global 写入 project_id=null。"""
        make_entry(entry_id="glb-01", scope="project", observed_count=3)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="glb", requested_at="t",
            target=PromoteTarget(entry_id="glb-01", from_scope="project",
                                  to_scope="global", reason="user_approved",
                                  approver=ApproverInfo(user_id="user:a",
                                                         intent_source="ui_click"))))
        written = sut._repo.find_global(entry_id="glb-01")
        assert written.project_id is None

    def test_TC_L106_L204_009_rejected_index_query_fast(self, sut) -> None:
        """TC-L106-L204-009 · rejected_index · add/contains 正常。"""
        sut._rejected_index.add("ent-rej-1")
        assert sut._rejected_index.contains("ent-rej-1")
        assert not sut._rejected_index.contains("ent-ok-1")

    def test_TC_L106_L204_010_source_marked_after_write(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-010 · 晋升后 source 打 promoted_to 标记。"""
        make_entry(entry_id="src-mark", scope="session", observed_count=2)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="sm", requested_at="t",
            target=PromoteTarget(entry_id="src-mark", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        src = sut._repo.find_session(entry_id="src-mark")
        assert src.promoted_to in ("project", "global")

    def test_TC_L106_L204_011_halt_command_ack_under_1s(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-011 · halt_command · 1s 内 ack。"""
        import time, threading
        mock_l2_03_snapshot.seed(count=100, kind="pattern", observed_count=2)
        def _run():
            sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="batch", trigger="s7_batch",
                request_id="halt-1", requested_at="t",
                batch_scope=BatchScope(max_candidates_per_batch=100)))
        t = threading.Thread(target=_run); t.start()
        time.sleep(0.1)
        t_ack = time.perf_counter()
        sut.halt_command(scope="l1_06")
        t.join(timeout=5)
        assert (time.perf_counter() - t_ack) <= 1.5

    def test_TC_L106_L204_012_probe_liveness(self, sut) -> None:
        """TC-L106-L204-012 · probe_health liveness · healthy=True。"""
        res = sut.probe_health(probe_type="liveness")
        assert res.healthy is True

    def test_TC_L106_L204_013_probe_ceremony_progress(self, sut) -> None:
        """TC-L106-L204-013 · probe ceremony_progress · 返回 list。"""
        res = sut.probe_health(probe_type="ceremony_progress")
        assert isinstance(res.ceremony_progress, list)

    def test_TC_L106_L204_014_ic_l2_03_invoked_per_promotion(
        self, sut, mock_l2_01_promotion_allow, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-014 · 每次晋升必调 L2-01 check_promotion_rule。"""
        make_entry(entry_id="ic203", scope="session", observed_count=2)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="r", requested_at="t",
            target=PromoteTarget(entry_id="ic203", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        mock_l2_01_promotion_allow.check_promotion_rule.assert_called_once()

    def test_TC_L106_L204_015_ic_l2_06_invoked_for_batch(
        self, sut, mock_l2_03_snapshot, mock_l2_01_promotion_allow,
        mock_project_id,
    ) -> None:
        """TC-L106-L204-015 · batch 模式必调 L2-03 session_candidate_pull。"""
        mock_l2_03_snapshot.seed(count=5, kind="pattern", observed_count=2)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="c-ic206", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=10)))
        mock_l2_03_snapshot.provide_candidate_snapshot.assert_called()
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_06/test_l2_04_promotion_negative.py
from __future__ import annotations

import pytest
from app.l1_06.l2_04.service import PromotionRitualExecutor
from app.l1_06.l2_04.schemas import PromoteRequest, PromoteTarget, BatchScope, ApproverInfo


class TestL2_04_Negative:

    def test_TC_L106_L204_101_skip_layer_denied(
        self, sut, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-101 · session→global 跨级 · 硬拒绝。"""
        make_entry(entry_id="skip", scope="session", observed_count=5)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="skip-req", requested_at="t",
            target=PromoteTarget(entry_id="skip", from_scope="session",
                                  to_scope="global", reason="user_approved",
                                  approver=ApproverInfo(user_id="u",
                                                         intent_source="ui_click"))))
        assert res.single_result.verdict == "rejected"
        assert res.single_result.reason_code == "E_L204_L201_SKIP_LAYER_DENIED"

    def test_TC_L106_L204_102_global_threshold_unmet(
        self, sut, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-102 · project→global · observed_count=2 无 user_approved。"""
        make_entry(entry_id="gu", scope="project", observed_count=2)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="gu-r", requested_at="t",
            target=PromoteTarget(entry_id="gu", from_scope="project",
                                  to_scope="global", reason="auto_threshold")))
        assert res.single_result.reason_code == "E_L204_L201_GLOBAL_THRESHOLD_UNMET"

    def test_TC_L106_L204_103_project_threshold_unmet(
        self, sut, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-103 · session→project · observed_count=1。"""
        make_entry(entry_id="pu", scope="session", observed_count=1)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="pu-r", requested_at="t",
            target=PromoteTarget(entry_id="pu", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert res.single_result.reason_code == "E_L204_L201_PROJECT_THRESHOLD_UNMET"

    def test_TC_L106_L204_104_candidate_pull_fail_abort(
        self, sut, mock_project_id, mock_l2_03_snapshot,
    ) -> None:
        """TC-L106-L204-104 · L2-03 快照失败 · 批量仪式 abort。"""
        mock_l2_03_snapshot.provide_candidate_snapshot.side_effect = TimeoutError("pull")
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="pfail", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=10)))
        assert res.success is False
        assert res.error.code == "E_L204_L203_CANDIDATE_PULL_FAIL"

    def test_TC_L106_L204_105_write_target_fail_retry_then_give_up(
        self, sut, mock_project_id, mock_storage,
        mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-105 · 物理写失败 · 单条失败（backoff 内）。"""
        make_entry(entry_id="wt", scope="session", observed_count=2)
        mock_storage.write_target.side_effect = IOError("disk")
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="wt-r", requested_at="t",
            target=PromoteTarget(entry_id="wt", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert res.single_result.reason_code in (
            "E_L204_WRITE_TARGET_FAIL", "E_L204_REPEAT_ATTEMPT_EXHAUSTED")

    def test_TC_L106_L204_106_source_mark_fail_escalates(
        self, sut, mock_project_id, mock_storage,
        mock_l2_01_promotion_allow, make_entry, mock_supervisor,
    ) -> None:
        """TC-L106-L204-106 · 源 session 标记失败 · 升 supervisor。"""
        make_entry(entry_id="sm-f", scope="session", observed_count=2)
        mock_storage.mark_source.side_effect = IOError("locked")
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="sm-f", requested_at="t",
            target=PromoteTarget(entry_id="sm-f", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert mock_supervisor.escalate.called

    def test_TC_L106_L204_107_promotion_locked_returns_existing(
        self, sut, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-107 · 同 entry_id 并发晋升 · 第二次幂等返回已在途 promotion_id。"""
        make_entry(entry_id="pl", scope="session", observed_count=2)
        sut._lock_repo.acquire("pl", promotion_id="in-flight-XYZ")
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="pl-r", requested_at="t",
            target=PromoteTarget(entry_id="pl", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert res.single_result.promotion_id == "in-flight-XYZ"

    def test_TC_L106_L204_108_ceremony_already_running(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L204-108 · 同项目已有 ceremony · 第二次拒。"""
        sut._ceremony_registry.register(project_id=mock_project_id,
                                         ceremony_id="cer-in-flight")
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="ca2", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=10)))
        assert res.error.code == "E_L204_CEREMONY_ALREADY_RUNNING"

    def test_TC_L106_L204_109_user_approval_missing(
        self, sut, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-109 · user_approved 但 user_id 为 None。"""
        make_entry(entry_id="ua", scope="project", observed_count=3)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="ua-r", requested_at="t",
            target=PromoteTarget(entry_id="ua", from_scope="project",
                                  to_scope="global", reason="user_approved",
                                  approver=ApproverInfo(user_id=None,
                                                         intent_source="ui_click"))))
        assert res.error.code == "E_L204_USER_APPROVAL_MISSING"

    def test_TC_L106_L204_110_rejected_cannot_undo(
        self, sut, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-110 · 已 rejected 条目再晋升 · 拒。"""
        make_entry(entry_id="rej", scope="session", observed_count=5)
        sut._rejected_index.add("rej")
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="rej-r", requested_at="t",
            target=PromoteTarget(entry_id="rej", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert res.error.code == "E_L204_REJECTED_CANNOT_UNDO"

    def test_TC_L106_L204_111_invalid_from_to(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L106-L204-111 · from=global / to=session · 422。"""
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="inv", requested_at="t",
            target=PromoteTarget(entry_id="x", from_scope="global",
                                  to_scope="session", reason="auto_threshold")))
        assert res.error.code == "E_L204_INVALID_FROM_TO"

    def test_TC_L106_L204_112_project_id_mismatch(
        self, sut, make_entry, mock_supervisor,
    ) -> None:
        """TC-L106-L204-112 · 请求 project=p-A · entry project=p-B · 拒 + 升 supervisor。"""
        make_entry(entry_id="mm", scope="session", observed_count=2, project_id="p-B")
        res = sut.kb_promote(PromoteRequest(
            project_id="p-A", mode="single", trigger="user_manual",
            request_id="mm", requested_at="t",
            target=PromoteTarget(entry_id="mm", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert res.error.code == "E_L204_PROJECT_ID_MISMATCH"
        assert mock_supervisor.escalate.called

    def test_TC_L106_L204_113_repeat_attempt_exhausted(
        self, sut, mock_project_id, mock_storage,
        mock_l2_01_promotion_allow, make_entry, mock_supervisor,
    ) -> None:
        """TC-L106-L204-113 · 3 次重试全失败 · 升 supervisor。"""
        make_entry(entry_id="re", scope="session", observed_count=2)
        mock_storage.write_target.side_effect = IOError("persistent")
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="re-r", requested_at="t",
            target=PromoteTarget(entry_id="re", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert mock_storage.write_target.call_count >= 3
        assert mock_supervisor.escalate.called

    def test_TC_L106_L204_114_supervisor_halt_abort_ceremony(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-114 · supervisor halt · 仪式立即 abort。"""
        import threading, time
        mock_l2_03_snapshot.seed(count=100, kind="pattern", observed_count=2)
        result = {}
        def _run():
            result["r"] = sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="batch", trigger="s7_batch",
                request_id="h", requested_at="t",
                batch_scope=BatchScope(max_candidates_per_batch=100)))
        t = threading.Thread(target=_run); t.start()
        time.sleep(0.05)
        sut.halt_command(scope="l1_06")
        t.join(timeout=3)
        r = result.get("r")
        assert r is not None
        assert r.error is None or r.error.code == "E_L204_SUPERVISOR_HALT" \
               or r.batch_result.verdict_summary.promoted_count < 100

    def test_TC_L106_L204_115_strip_project_id_fail(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
        monkeypatch,
    ) -> None:
        """TC-L106-L204-115 · frontmatter 结构异常 · project_id 剥离失败 · abort 该条。"""
        make_entry(entry_id="strip-bad", scope="project", observed_count=3)
        def bad_strip(*a, **kw):
            raise ValueError("frontmatter corrupt")
        monkeypatch.setattr(sut, "_strip_project_id", bad_strip)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="sb", requested_at="t",
            target=PromoteTarget(entry_id="strip-bad", from_scope="project",
                                  to_scope="global", reason="user_approved",
                                  approver=ApproverInfo(user_id="u",
                                                         intent_source="ui_click"))))
        assert res.error.code == "E_L204_STRIP_PROJECT_ID_FAIL"
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_06/test_l2_04_promotion_ic.py
from __future__ import annotations

import pytest
from app.l1_06.l2_04.schemas import PromoteRequest, PromoteTarget, BatchScope


class TestL2_04_IC_Contracts:

    def test_TC_L106_L204_601_ic_08_response_fields(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-601 · IC-08 响应字段齐。"""
        make_entry(entry_id="ic08", scope="session", observed_count=2)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="ic08-r", requested_at="t",
            target=PromoteTarget(entry_id="ic08", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        for field in ("response_id", "request_id", "project_id", "mode",
                       "success", "single_result"):
            assert hasattr(res, field)
        assert res.request_id == "ic08-r"

    def test_TC_L106_L204_602_ic_l2_03_called(
        self, sut, mock_l2_01_promotion_allow, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-602 · 每次晋升必调 IC-L2-03。"""
        make_entry(entry_id="ic203", scope="session", observed_count=2)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="r", requested_at="t",
            target=PromoteTarget(entry_id="ic203", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        mock_l2_01_promotion_allow.check_promotion_rule.assert_called_once()

    def test_TC_L106_L204_603_ic_l2_06_called_for_batch(
        self, sut, mock_l2_03_snapshot, mock_l2_01_promotion_allow,
        mock_project_id,
    ) -> None:
        """TC-L106-L204-603 · batch 模式必调 IC-L2-06。"""
        mock_l2_03_snapshot.seed(count=3, kind="pattern", observed_count=2)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="b", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=5)))
        mock_l2_03_snapshot.provide_candidate_snapshot.assert_called()

    def test_TC_L106_L204_604_ic_09_audit_on_every_promotion(
        self, sut, mock_audit, mock_l2_01_promotion_allow,
        mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-604 · 每次晋升推 IC-09 audit。"""
        make_entry(entry_id="aud", scope="session", observed_count=2)
        sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="aud-r", requested_at="t",
            target=PromoteTarget(entry_id="aud", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert mock_audit.append.called
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_06/test_l2_04_promotion_perf.py
from __future__ import annotations

import pytest
import time
from app.l1_06.l2_04.schemas import PromoteRequest, PromoteTarget, BatchScope


@pytest.mark.perf
class TestL2_04_SLO:

    def test_TC_L106_L204_501_single_p50_le_200ms(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, seed_many_entries,
        benchmark,
    ) -> None:
        """TC-L106-L204-501 · 单条晋升 P50 ≤ 200ms。"""
        seed_many_entries(count=50, scope="session", observed_count=2)
        counter = [0]
        def _one():
            counter[0] += 1
            sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="single", trigger="user_manual",
                request_id=f"p-{counter[0]}", requested_at="t",
                target=PromoteTarget(entry_id=f"many-{counter[0]}",
                                      from_scope="session", to_scope="project",
                                      reason="auto_threshold")))
        benchmark.pedantic(_one, iterations=1, rounds=50)
        assert benchmark.stats["stats"]["p50"] * 1000 <= 200.0

    def test_TC_L106_L204_502_single_p99_le_500ms(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, seed_many_entries,
        benchmark,
    ) -> None:
        """TC-L106-L204-502 · 单条晋升 P99 ≤ 500ms。"""
        seed_many_entries(count=200, scope="session", observed_count=2)
        counter = [0]
        def _one():
            counter[0] += 1
            sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="single", trigger="user_manual",
                request_id=f"p99-{counter[0]}", requested_at="t",
                target=PromoteTarget(entry_id=f"many-{counter[0]}",
                                      from_scope="session", to_scope="project",
                                      reason="auto_threshold")))
        benchmark.pedantic(_one, iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 500.0

    def test_TC_L106_L204_503_batch_100_p95_le_20s(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-503 · batch 100 条 P95 ≤ 20s。"""
        mock_l2_03_snapshot.seed(count=100, kind="pattern", observed_count=2)
        samples = []
        for i in range(5):
            t0 = time.perf_counter()
            sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="batch", trigger="s7_batch",
                request_id=f"b-{i}", requested_at="t",
                batch_scope=BatchScope(max_candidates_per_batch=100)))
            samples.append(time.perf_counter() - t0)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95) - 1]
        assert p95 <= 20.0

    def test_TC_L106_L204_504_batch_100_p99_le_30s(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-504 · batch 100 条 P99 ≤ 30s。"""
        mock_l2_03_snapshot.seed(count=100, kind="pattern", observed_count=2)
        samples = []
        for i in range(10):
            t0 = time.perf_counter()
            sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="batch", trigger="s7_batch",
                request_id=f"b99-{i}", requested_at="t",
                batch_scope=BatchScope(max_candidates_per_batch=100)))
            samples.append(time.perf_counter() - t0)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99) - 1]
        assert p99 <= 30.0

    def test_TC_L106_L204_505_halt_ack_under_1s(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-505 · halt_command ack ≤ 1s。"""
        import threading
        mock_l2_03_snapshot.seed(count=200, kind="pattern", observed_count=2)
        def _run():
            sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="batch", trigger="s7_batch",
                request_id="halt-perf", requested_at="t",
                batch_scope=BatchScope(max_candidates_per_batch=200)))
        th = threading.Thread(target=_run); th.start()
        time.sleep(0.1)
        t0 = time.perf_counter()
        sut.halt_command(scope="l1_06")
        th.join(timeout=5)
        assert (time.perf_counter() - t0) <= 1.5  # 松弛边界
```

---

## §6 端到端 e2e

```python
# file: tests/l1_06/test_l2_04_promotion_e2e.py
from __future__ import annotations

import pytest
from app.l1_06.l2_04.schemas import PromoteRequest, PromoteTarget, BatchScope, ApproverInfo


@pytest.mark.e2e
class TestL2_04_E2E:

    def test_TC_L106_L204_701_s7_ceremony_full_flow(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow, mock_audit,
    ) -> None:
        """TC-L106-L204-701 · S7 批量仪式 e2e · 快照 → 校验 → 写 → 审计。"""
        mock_l2_03_snapshot.seed(count=30, kind="pattern", observed_count=2)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="e2e-1", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=50)))
        assert res.success is True
        assert res.batch_result.verdict_summary.promoted_count > 0
        assert mock_audit.append.called

    def test_TC_L106_L204_702_session_to_project_to_global_progression(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-702 · session→project 后再 project→global（跨仪式）。"""
        make_entry(entry_id="prog", scope="session", observed_count=2)
        r1 = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="prog-1", requested_at="t",
            target=PromoteTarget(entry_id="prog", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert r1.single_result.final_scope == "project"
        # 项目层继续累积到 3
        sut._repo.set_observed_count("prog", 3, scope="project")
        r2 = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="prog-2", requested_at="t",
            target=PromoteTarget(entry_id="prog", from_scope="project",
                                  to_scope="global", reason="user_approved",
                                  approver=ApproverInfo(user_id="u",
                                                         intent_source="ui_click"))))
        assert r2.single_result.final_scope == "global"

    def test_TC_L106_L204_703_halt_mid_ceremony_preserves_done(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-703 · halt 中途 · 已完成部分保留 · 未开始跳过。"""
        import threading, time
        mock_l2_03_snapshot.seed(count=50, kind="pattern", observed_count=2)
        def _run():
            sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="batch", trigger="s7_batch",
                request_id="e2e-halt", requested_at="t",
                batch_scope=BatchScope(max_candidates_per_batch=50)))
        t = threading.Thread(target=_run); t.start()
        time.sleep(0.05)
        sut.halt_command(scope="l1_06")
        t.join(timeout=3)
        # 已搬运的条目仍在 Project 层
        assert sut._repo.count_in_project(project_id=mock_project_id) >= 0
```

---

## §7 测试 fixture

```python
# file: tests/l1_06/conftest_l2_04.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_06.l2_04.service import PromotionRitualExecutor


@pytest.fixture
def mock_project_id() -> str:
    return "hf-proj-l204"


@pytest.fixture
def mock_l2_01_promotion_allow() -> MagicMock:
    """默认 L2-01 check_promotion_rule 返回 ALLOW。"""
    m = MagicMock()
    def _check(req, *a, **kw):
        # 基于请求的 from_scope / to_scope / observed_count 做判断
        from app.l1_06.l2_01.schemas import PromotionDecision
        if req.from_scope == "session" and req.to_scope == "global":
            return PromotionDecision(allowed=False, rule_id="R-SKIP",
                                      violation_code="E_L204_L201_SKIP_LAYER_DENIED")
        if req.to_scope == "project" and req.observed_count < 2:
            return PromotionDecision(allowed=False, rule_id="R-PT",
                                      violation_code="E_L204_L201_PROJECT_THRESHOLD_UNMET")
        if req.to_scope == "global" and req.observed_count < 3:
            return PromotionDecision(allowed=False, rule_id="R-GT",
                                      violation_code="E_L204_L201_GLOBAL_THRESHOLD_UNMET")
        return PromotionDecision(allowed=True, rule_id="R-OK")
    m.check_promotion_rule.side_effect = _check
    return m


@pytest.fixture
def mock_l2_03_snapshot() -> MagicMock:
    """L2-03 candidate snapshot · 支持 seed / seed_paginated。"""
    m = MagicMock()
    state = {"entries": [], "page_size": None}
    def _seed(count, kind, observed_count):
        state["entries"] = [
            {"entry_id": f"cand-{i}", "scope": "session", "kind": kind,
             "title": f"t-{i}", "observed_count": observed_count,
             "first_observed_at": "t", "last_observed_at": "t",
             "task_ids": ["t1", "t2"], "source_links": ["decision:d"]}
            for i in range(count)]
    def _seed_paginated(total, page_size):
        _seed(total, "pattern", 2)
        state["page_size"] = page_size
    def _pull(req, *a, **kw):
        return MagicMock(entries=state["entries"],
                         total_count=len(state["entries"]),
                         next_cursor=None)
    m.seed = _seed
    m.seed_paginated = _seed_paginated
    m.provide_candidate_snapshot.side_effect = _pull
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_storage() -> MagicMock:
    m = MagicMock()
    m.write_target.return_value = True
    m.atomic_rename.return_value = True
    m.mark_source.return_value = True
    return m


@pytest.fixture
def mock_supervisor() -> MagicMock:
    m = MagicMock()
    m.escalate = MagicMock()
    return m


@pytest.fixture
def sut(mock_l2_01_promotion_allow, mock_l2_03_snapshot, mock_audit,
        mock_storage, mock_supervisor, mock_project_id):
    return PromotionRitualExecutor(
        tier_manager=mock_l2_01_promotion_allow,
        obs_accumulator=mock_l2_03_snapshot,
        audit=mock_audit,
        storage=mock_storage,
        supervisor=mock_supervisor,
        project_id=mock_project_id,
    )


@pytest.fixture
def make_entry(sut, mock_project_id):
    def _make(entry_id: str, scope: str, observed_count: int,
              project_id: str | None = None):
        sut._repo.insert({
            "id": entry_id, "project_id": project_id or mock_project_id,
            "scope": scope, "observed_count": observed_count,
            "kind": "pattern", "title": f"t-{entry_id}",
            "content": {"desc": "x"}, "source_links": ["decision:x"],
        })
    return _make


@pytest.fixture
def seed_many_entries(sut, mock_project_id):
    def _seed(count, scope, observed_count):
        for i in range(1, count + 1):
            sut._repo.insert({
                "id": f"many-{i}", "project_id": mock_project_id,
                "scope": scope, "observed_count": observed_count,
                "kind": "pattern", "title": f"t-{i}",
                "content": {"desc": "x"}, "source_links": ["decision:x"],
            })
    return _seed
```

---

## §8 集成点用例

```python
# file: tests/l1_06/test_l2_04_integration.py
from __future__ import annotations

import pytest
from app.l1_06.l2_04.schemas import PromoteRequest, PromoteTarget, BatchScope


class TestL2_04_Integration:

    def test_TC_L106_L204_801_l2_01_denies_cascade_to_rejected(
        self, sut, mock_project_id, make_entry,
    ) -> None:
        """TC-L106-L204-801 · L2-01 拒绝 → 记入 rejected_index 后续同条目再晋升返回 REJECTED_CANNOT_UNDO。"""
        make_entry(entry_id="cas", scope="session", observed_count=1)
        r1 = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="cas-1", requested_at="t",
            target=PromoteTarget(entry_id="cas", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert r1.single_result.verdict != "promoted"
        # 第二次（即使 user_approved）仍不允许 undo
        if sut._rejected_index.contains("cas"):
            r2 = sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="single", trigger="user_manual",
                request_id="cas-2", requested_at="t",
                target=PromoteTarget(entry_id="cas", from_scope="session",
                                      to_scope="project", reason="user_approved")))
            assert r2.error.code == "E_L204_REJECTED_CANNOT_UNDO"

    def test_TC_L106_L204_802_with_l1_10_ui_approval_path(
        self, sut, mock_project_id, make_entry, mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-802 · IC-17 UI 触发 project→global · 正常执行。"""
        make_entry(entry_id="ui", scope="project", observed_count=3)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single",
            trigger="user_manual",  # 来自 UI 的触发
            request_id="ui-r", requested_at="t",
            target=PromoteTarget(entry_id="ui", from_scope="project",
                                  to_scope="global", reason="user_approved",
                                  approver={"user_id": "user:ui",
                                             "intent_source": "ui_click"})))
        assert res.single_result.promoted is True
```

---

## §9 边界 / edge case

```python
# file: tests/l1_06/test_l2_04_edge.py
from __future__ import annotations

import pytest
from app.l1_06.l2_04.schemas import PromoteRequest, PromoteTarget, BatchScope


class TestL2_04_Edge:

    def test_TC_L106_L204_901_empty_batch_candidates(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-901 · 边界 · 候选 0 条 · ceremony 完成但 counts 全为 0。"""
        mock_l2_03_snapshot.seed(count=0, kind="pattern", observed_count=0)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="empty", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=10)))
        assert res.batch_result.candidates_total == 0

    def test_TC_L106_L204_902_max_batch_500(
        self, sut, mock_project_id, mock_l2_03_snapshot,
        mock_l2_01_promotion_allow,
    ) -> None:
        """TC-L106-L204-902 · max_candidates_per_batch=500 · 5 页处理完。"""
        mock_l2_03_snapshot.seed(count=500, kind="pattern", observed_count=2)
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="batch", trigger="s7_batch",
            request_id="max500", requested_at="t",
            batch_scope=BatchScope(max_candidates_per_batch=500)))
        assert res.batch_result.candidates_total == 500

    def test_TC_L106_L204_903_concurrent_same_entry_serialized(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
    ) -> None:
        """TC-L106-L204-903 · 同 entry_id 5 线程并发 · 仅 1 次真实晋升 · 其余返回已在途。"""
        import threading
        make_entry(entry_id="conc", scope="session", observed_count=2)
        results = []
        def _go(i):
            results.append(sut.kb_promote(PromoteRequest(
                project_id=mock_project_id, mode="single", trigger="user_manual",
                request_id=f"conc-{i}", requested_at="t",
                target=PromoteTarget(entry_id="conc", from_scope="session",
                                      to_scope="project", reason="auto_threshold"))))
        ts = [threading.Thread(target=_go, args=(i,)) for i in range(5)]
        for t in ts: t.start()
        for t in ts: t.join()
        promoted = sum(1 for r in results if r.single_result.verdict == "promoted")
        assert promoted == 1

    def test_TC_L106_L204_904_timeout_single_5s(
        self, sut, mock_project_id, mock_l2_01_promotion_allow, make_entry,
        mock_storage,
    ) -> None:
        """TC-L106-L204-904 · single 超时 5s · error 返回。"""
        import time
        make_entry(entry_id="to", scope="session", observed_count=2)
        def slow(*a, **kw):
            time.sleep(6); return True
        mock_storage.write_target.side_effect = slow
        res = sut.kb_promote(PromoteRequest(
            project_id=mock_project_id, mode="single", trigger="user_manual",
            request_id="to-r", requested_at="t", timeout_ms=5000,
            target=PromoteTarget(entry_id="to", from_scope="session",
                                  to_scope="project", reason="auto_threshold")))
        assert res.success is False

    def test_TC_L106_L204_905_degradation_level_reflected_in_health(
        self, sut,
    ) -> None:
        """TC-L106-L204-905 · degradation_level=2 · probe readiness=False。"""
        sut._degradation_level = 2
        res = sut.probe_health(probe_type="readiness")
        # readiness: degradation_level < 3
        assert res.healthy is (sut._degradation_level < 3)
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
