---
doc_id: tests-L1-06-L2-03-观察累积器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-06-3层知识库/L2-03-观察累积器.md
  - docs/2-prd/L1-06 3层知识库/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-06 L2-03-观察累积器 · TDD 测试用例

> 基于 3-1 L2-03 §3（`write_session` / `batch_write_session` / `provide_candidate_snapshot` / `crash_recover` 等 public 方法）+ §11（15+ 项 `E_L203_*` 错误码）+ §12（合并/新建 P50/P95/P99 SLO）驱动。
> TC ID 统一格式：`TC-L106-L203-NNN`。

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

| 方法 | TC ID | 覆盖类型 |
|---|---|---|
| `write_session()` · INSERTED | TC-L106-L203-001 | unit |
| `write_session()` · MERGED（dedup 命中）| TC-L106-L203-002 | unit |
| `write_session()` · observed_count 实际累积 | TC-L106-L203-003 | unit |
| `write_session()` · source_links 多条取并集 | TC-L106-L203-004 | unit |
| `write_session()` · promotion_hint 跨阈值 | TC-L106-L203-005 | unit |
| `write_session()` · 幂等重放 | TC-L106-L203-006 | unit |
| `write_session()` · 8 类 kind 白名单 | TC-L106-L203-007 | unit |
| `batch_write_session()` · 10 条混合 | TC-L106-L203-008 | unit |
| `batch_write_session()` · 部分失败不阻塞 | TC-L106-L203-009 | unit |
| `provide_candidate_snapshot()` · 正向 | TC-L106-L203-010 | unit |
| `provide_candidate_snapshot()` · kind_breakdown | TC-L106-L203-011 | unit |
| `provide_candidate_snapshot()` · 超 10000 只返 file_path | TC-L106-L203-012 | unit |
| `crash_recover()` · 1000 WAL 回放 | TC-L106-L203-013 | unit |
| `write_session()` · title 归一化 | TC-L106-L203-014 | unit |
| WAL fsync 次数（WRITE_START + DONE）| TC-L106-L203-015 | unit |

### §1.2 错误码 × TC 矩阵（≥ 15 项全覆盖）

| 错误码 | TC ID | 方法 |
|---|---|---|
| `E_L203_SCHEMA_VALIDATION_FAILED` | TC-L106-L203-101 | `write_session` |
| `E_L203_PM14_PROJECT_ID_MISMATCH` | TC-L106-L203-102 | `write_session` |
| `E_L203_PM14_PROJECT_ID_MISSING` | TC-L106-L203-103 | `write_session` |
| `E_L203_CROSS_LAYER_DENIED` | TC-L106-L203-104 | `write_session` |
| `E_L203_RAW_TEXT_DENIED` | TC-L106-L203-105 | `write_session` |
| `E_L203_COUNT_OVERRIDE_IGNORED` | TC-L106-L203-106 | `write_session` |
| `E_L203_KIND_NOT_WHITELISTED` | TC-L106-L203-107 | `write_session` |
| `E_L203_TITLE_EMPTY_OR_TOO_LONG` | TC-L106-L203-108 | `write_session` |
| `E_L203_SOURCE_LINKS_EMPTY` | TC-L106-L203-109 | `write_session` |
| `E_L203_CAPACITY_SOFT_WARNING` | TC-L106-L203-110 | `write_session` |
| `E_L203_CAPACITY_HARD_REJECTED` | TC-L106-L203-111 | `write_session` |
| `E_L203_IDEMPOTENCY_KEY_CONFLICT` | TC-L106-L203-112 | `write_session` |
| `E_L203_STORAGE_WRITE_FAILED` | TC-L106-L203-113 | `write_session` |
| `E_L203_WAL_WRITE_FAILED` | TC-L106-L203-114 | `write_session` |
| `E_L203_TIER_MANAGER_UNAVAILABLE` | TC-L106-L203-115 | `write_session` |
| `E_L203_SNAPSHOT_PROJECT_NOT_FOUND` | TC-L106-L203-116 | `provide_candidate_snapshot` |
| `E_L203_SNAPSHOT_KIND_EMPTY` | TC-L106-L203-117 | `provide_candidate_snapshot` |
| `E_L203_SNAPSHOT_STORAGE_READ_FAILED` | TC-L106-L203-118 | `provide_candidate_snapshot` |
| `E_L203_L109_UNAVAILABLE` | TC-L106-L203-119 | audit emit |
| `E_L203_L109_BACKPRESSURE` | TC-L106-L203-120 | audit emit |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-07 kb_write_session | caller → L2-03 | TC-L106-L203-601 |
| IC-L2-06 session_candidate_pull | L2-04 → L2-03 | TC-L106-L203-602 |
| IC-L2-02 write_slot_request | L2-03 → L2-01 | TC-L106-L203-603 |
| IC-09 append_event | L2-03 → L1-09 | TC-L106-L203-604 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| write_session 合并 P50 | ≤ 20ms | TC-L106-L203-501 |
| write_session 新建 P50 | ≤ 30ms | TC-L106-L203-502 |
| batch 10 P95 | ≤ 300ms | TC-L106-L203-503 |
| snapshot <100 P99 | ≤ 1s | TC-L106-L203-504 |
| crash_recover 1000 WAL | ≤ 5s | TC-L106-L203-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_06/test_l2_03_obs_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_06.l2_03.service import ObservationAccumulator
from app.l1_06.l2_03.schemas import SnapshotRequest


class TestL2_03_Positive:

    def test_TC_L106_L203_001_inserted_new_entry(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-001 · 首次写 · action=INSERTED · count=1。"""
        res = sut.write_session(make_write_req(kind="trap", title="new-trap-001"))
        assert res.success is True
        assert res.action == "INSERTED"
        assert res.observed_count_after == 1

    def test_TC_L106_L203_002_merged_on_dedup(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-002 · 同 (kind, title_hash) 二次写 · MERGED · count=2。"""
        sut.write_session(make_write_req(kind="pattern", title="same"))
        res = sut.write_session(make_write_req(kind="pattern", title="same"))
        assert res.action == "MERGED"
        assert res.observed_count_after == 2

    def test_TC_L106_L203_003_observed_count_accumulates(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-003 · 连续 5 次 · count 1→5（硬约束 3）。"""
        for _ in range(5):
            res = sut.write_session(make_write_req(kind="recipe", title="acc"))
        assert res.observed_count_after == 5

    def test_TC_L106_L203_004_source_links_union_on_merge(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-004 · 合并时 source_links 并集不去重。"""
        sut.write_session(make_write_req(kind="trap", title="sl",
                                          source_links=["decision:d1"]))
        res = sut.write_session(make_write_req(
            kind="trap", title="sl",
            source_links=["decision:d2", "verifier_report:v1"]))
        stored = sut._repo.get(res.entry_id)
        assert set(stored.source_links) >= {"decision:d1", "decision:d2",
                                             "verifier_report:v1"}

    def test_TC_L106_L203_005_promotion_hint_crosses_threshold(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-005 · 第 2 次达阈值 · promotion_hint.eligible=True。"""
        sut.write_session(make_write_req(kind="pattern", title="ph"))
        res = sut.write_session(make_write_req(kind="pattern", title="ph"))
        assert res.promotion_hint.session_to_project_eligible is True
        assert res.promotion_hint.threshold == 2

    def test_TC_L106_L203_006_idempotent_replay(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-006 · 同 idempotency_key + 同 payload · 不重复累计。"""
        req = make_write_req(kind="trap", title="idem", idempotency_key="k-1")
        r1 = sut.write_session(req)
        r2 = sut.write_session(req)
        assert r1.entry_id == r2.entry_id
        assert r2.observed_count_after == r1.observed_count_after

    def test_TC_L106_L203_007_eight_kinds_all_accepted(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-007 · 8 类 kind 全部通过。"""
        kinds = ["pattern", "trap", "recipe", "tool_combo", "anti_pattern",
                 "project_context", "external_ref", "effective_combo"]
        for k in kinds:
            res = sut.write_session(make_write_req(kind=k, title=f"t-{k}"))
            assert res.success, f"kind={k} 应成功"

    def test_TC_L106_L203_008_batch_write_10(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-008 · batch 10 条混合 · 全部成功。"""
        reqs = [make_write_req(kind="pattern", title=f"b-{i}") for i in range(10)]
        res = sut.batch_write_session(reqs)
        assert res.total == 10
        assert res.success_count == 10

    def test_TC_L106_L203_009_batch_partial_failure(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-009 · batch 第 3 条 schema 错 · 其他 9 条仍成功。"""
        reqs = [make_write_req(kind="pattern", title=f"bp-{i}") for i in range(10)]
        reqs[2] = make_write_req(kind="pattern", title="")
        res = sut.batch_write_session(reqs)
        assert res.success_count == 9
        assert res.failure_count == 1

    def test_TC_L106_L203_010_candidate_snapshot_basic(
        self, sut: ObservationAccumulator, seed_entries, mock_project_id,
    ) -> None:
        """TC-L106-L203-010 · 20 条 Session · snapshot inlined。"""
        seed_entries(project_id=mock_project_id, count=20, kind="pattern")
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="tr",
            kind_filter=["pattern"], min_observed_count=1,
            include_hint=True, snapshot_ttl_s=60))
        assert res.total_entries == 20
        assert len(res.entries) == 20

    def test_TC_L106_L203_011_snapshot_kind_breakdown(
        self, sut: ObservationAccumulator, seed_entries, mock_project_id,
    ) -> None:
        """TC-L106-L203-011 · kind_breakdown 正确。"""
        seed_entries(project_id=mock_project_id, count=5, kind="pattern")
        seed_entries(project_id=mock_project_id, count=3, kind="trap")
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="tr",
            kind_filter=["pattern", "trap"], min_observed_count=1,
            include_hint=True, snapshot_ttl_s=60))
        assert res.kind_breakdown["pattern"] == 5
        assert res.kind_breakdown["trap"] == 3

    def test_TC_L106_L203_012_snapshot_too_large_file_path_only(
        self, sut: ObservationAccumulator, seed_entries, mock_project_id,
    ) -> None:
        """TC-L106-L203-012 · > 10000 条 · 不内联。"""
        seed_entries(project_id=mock_project_id, count=10001, kind="pattern")
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="tr",
            kind_filter=["pattern"], min_observed_count=1,
            include_hint=False, snapshot_ttl_s=60))
        assert res.entries == []
        assert res.snapshot_file_path.endswith(".json")

    def test_TC_L106_L203_013_crash_recover_1000(
        self, sut: ObservationAccumulator, seed_wal, mock_project_id,
    ) -> None:
        """TC-L106-L203-013 · 1000 WAL 回放 · 索引重建完整。"""
        seed_wal(project_id=mock_project_id, count=1000)
        res = sut.crash_recover(project_id=mock_project_id,
                                 last_known_sequence_id=None, trace_id="tr")
        assert res.replay_entries_count == 1000
        assert res.reconstructed_index_entries == 1000

    def test_TC_L106_L203_014_title_normalization(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-014 · "  Space  " 与 "space" 归一化同 key · 合并。"""
        sut.write_session(make_write_req(kind="pattern", title="  Space  "))
        res = sut.write_session(make_write_req(kind="pattern", title="space"))
        assert res.action == "MERGED"
        assert res.was_normalized is True

    def test_TC_L106_L203_015_wal_fsync_twice_per_write(
        self, sut: ObservationAccumulator, mock_wal, make_write_req,
    ) -> None:
        """TC-L106-L203-015 · WAL fsync 次数 = 2（WRITE_START + DONE）。"""
        sut.write_session(make_write_req(kind="trap", title="wal-1"))
        assert mock_wal.fsync.call_count == 2
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_06/test_l2_03_obs_negative.py
from __future__ import annotations

import pytest
from app.l1_06.l2_03.service import ObservationAccumulator
from app.l1_06.l2_03.schemas import SnapshotRequest


class TestL2_03_Negative:

    def test_TC_L106_L203_101_schema_validation_failed(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-101 · trap 缺 trigger 字段 · schema 失败。"""
        req = make_write_req(kind="trap", title="missing-trigger",
                              content={"symptom": "s"})  # 缺 trigger
        res = sut.write_session(req)
        assert res.success is False
        assert res.error.code == "E_L203_SCHEMA_VALIDATION_FAILED"
        assert "trigger" in res.error.detail["missing_fields"]

    def test_TC_L106_L203_102_pm14_project_id_mismatch(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-102 · 顶层 project_id 与 entry 不一致。"""
        req = make_write_req(kind="pattern", title="mismatch",
                              project_id="p-A", entry_project_id="p-B")
        res = sut.write_session(req)
        assert res.error.code == "E_L203_PM14_PROJECT_ID_MISMATCH"

    def test_TC_L106_L203_103_pm14_project_id_missing(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-103 · 顶层 project_id 为空。"""
        req = make_write_req(kind="pattern", title="no-pid", project_id=None)
        res = sut.write_session(req)
        assert res.error.code == "E_L203_PM14_PROJECT_ID_MISSING"

    def test_TC_L106_L203_104_cross_layer_denied(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-104 · scope=project · 越层写拒。"""
        req = make_write_req(kind="pattern", title="xlayer", scope="project")
        res = sut.write_session(req)
        assert res.error.code == "E_L203_CROSS_LAYER_DENIED"

    def test_TC_L106_L203_105_raw_text_denied(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-105 · content 为纯文本字符串 · 拒绝。"""
        req = make_write_req(kind="pattern", title="raw",
                              content="这是一段自由文本")
        res = sut.write_session(req)
        assert res.error.code == "E_L203_RAW_TEXT_DENIED"

    def test_TC_L106_L203_106_count_override_ignored(
        self, sut: ObservationAccumulator, make_write_req, mock_audit,
    ) -> None:
        """TC-L106-L203-106 · 调用方传 observed_count=99 · 被忽略并 audit。"""
        req = make_write_req(kind="pattern", title="co",
                              observed_count_override=99)
        res = sut.write_session(req)
        assert res.observed_count_after == 1  # 不按传入
        events = [c.kwargs.get("event_type") or c.args[0]
                  for c in mock_audit.append.call_args_list]
        # audit 记录 override 被忽略
        assert any("count_override" in (e or "") for e in events) or \
               res.warnings and "E_L203_COUNT_OVERRIDE_IGNORED" in res.warnings

    def test_TC_L106_L203_107_kind_not_whitelisted(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-107 · kind=unknown_kind · 拒。"""
        req = make_write_req(kind="unknown_kind", title="kn")
        res = sut.write_session(req)
        assert res.error.code == "E_L203_KIND_NOT_WHITELISTED"

    def test_TC_L106_L203_108_title_empty_or_too_long(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-108 · title="" · 拒；title > 200 · 拒。"""
        r1 = sut.write_session(make_write_req(kind="pattern", title=""))
        assert r1.error.code == "E_L203_TITLE_EMPTY_OR_TOO_LONG"
        r2 = sut.write_session(make_write_req(kind="pattern", title="x" * 201))
        assert r2.error.code == "E_L203_TITLE_EMPTY_OR_TOO_LONG"

    def test_TC_L106_L203_109_source_links_empty(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-109 · source_links=[] · 拒。"""
        req = make_write_req(kind="pattern", title="no-src", source_links=[])
        res = sut.write_session(req)
        assert res.error.code == "E_L203_SOURCE_LINKS_EMPTY"

    def test_TC_L106_L203_110_capacity_soft_warning(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-110 · 超 soft_cap 仍成功 · warnings 含 SOFT_WARNING。"""
        sut._capacity.set_cap(soft=5, hard=1000)
        for i in range(6):
            res = sut.write_session(make_write_req(kind="pattern", title=f"c-{i}"))
        assert res.success is True
        assert "E_L203_CAPACITY_SOFT_WARNING" in (res.warnings or [])

    def test_TC_L106_L203_111_capacity_hard_rejected(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-111 · 超 hard_cap · 新建拒绝。"""
        sut._capacity.set_cap(soft=5, hard=6)
        for i in range(6):
            sut.write_session(make_write_req(kind="pattern", title=f"h-{i}"))
        res = sut.write_session(make_write_req(kind="pattern", title="h-6"))
        assert res.error.code == "E_L203_CAPACITY_HARD_REJECTED"

    def test_TC_L106_L203_112_idempotency_conflict(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-112 · 同 key 但 payload 不同 · 冲突。"""
        sut.write_session(make_write_req(kind="trap", title="idem-X",
                                          idempotency_key="ik1"))
        res = sut.write_session(make_write_req(kind="pattern", title="idem-Y",
                                                idempotency_key="ik1"))
        assert res.error.code == "E_L203_IDEMPOTENCY_KEY_CONFLICT"

    def test_TC_L106_L203_113_storage_write_failed_degraded(
        self, sut: ObservationAccumulator, make_write_req, mock_storage,
    ) -> None:
        """TC-L106-L203-113 · 底层存储 IOError · 降级写 WAL + INFO。"""
        mock_storage.append.side_effect = IOError("disk")
        res = sut.write_session(make_write_req(kind="pattern", title="sto"))
        # 存储失败但降级 WAL · 不 halt
        assert res.action == "DEGRADED" or res.error.code == "E_L203_STORAGE_WRITE_FAILED"

    def test_TC_L106_L203_114_wal_write_failed_halts(
        self, sut: ObservationAccumulator, make_write_req, mock_wal,
    ) -> None:
        """TC-L106-L203-114 · WAL fsync 失败 · 本次写 halt。"""
        mock_wal.fsync.side_effect = OSError("fsync")
        res = sut.write_session(make_write_req(kind="pattern", title="wal-f"))
        assert res.error.code == "E_L203_WAL_WRITE_FAILED"

    def test_TC_L106_L203_115_tier_manager_unavailable(
        self, sut: ObservationAccumulator, make_write_req, mock_l2_01,
    ) -> None:
        """TC-L106-L203-115 · L2-01 不可达 · 降级绕过 + INFO。"""
        from app.l1_06.l2_01.errors import ScopeCheckError
        mock_l2_01.write_slot_request.side_effect = TimeoutError("L2-01")
        res = sut.write_session(make_write_req(kind="pattern", title="tm-down"))
        # 降级：尽力写 + warnings
        assert "E_L203_TIER_MANAGER_UNAVAILABLE" in (res.warnings or []) \
               or res.error.code == "E_L203_TIER_MANAGER_UNAVAILABLE"

    def test_TC_L106_L203_116_snapshot_project_not_found(
        self, sut: ObservationAccumulator,
    ) -> None:
        """TC-L106-L203-116 · 新项目无条目 · 返回空清单（非 error）。"""
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id="p-empty", trace_id="tr",
            kind_filter=["pattern"], min_observed_count=1,
            include_hint=True, snapshot_ttl_s=60))
        assert res.total_entries == 0

    def test_TC_L106_L203_117_snapshot_kind_empty(
        self, sut: ObservationAccumulator, mock_project_id,
    ) -> None:
        """TC-L106-L203-117 · kind_filter=[] · 拒。"""
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="tr",
            kind_filter=[], min_observed_count=1,
            include_hint=True, snapshot_ttl_s=60))
        assert res.error.code == "E_L203_SNAPSHOT_KIND_EMPTY"

    def test_TC_L106_L203_118_snapshot_storage_read_failed(
        self, sut: ObservationAccumulator, mock_project_id, mock_storage,
    ) -> None:
        """TC-L106-L203-118 · jsonl 读失败 · 重试 3 次。"""
        mock_storage.read_all.side_effect = IOError("jsonl")
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="tr",
            kind_filter=["pattern"], min_observed_count=1,
            include_hint=True, snapshot_ttl_s=60))
        assert res.error.code == "E_L203_SNAPSHOT_STORAGE_READ_FAILED"
        assert mock_storage.read_all.call_count == 3

    def test_TC_L106_L203_119_l109_unavailable_wal_buffer(
        self, sut: ObservationAccumulator, mock_audit, make_write_req,
    ) -> None:
        """TC-L106-L203-119 · L1-09 不可达 · audit 入 WAL buffer。"""
        mock_audit.append.side_effect = ConnectionError("L1-09 down")
        res = sut.write_session(make_write_req(kind="pattern", title="l109"))
        # 写入本身成功，但 audit 入 WAL replay 队列
        assert res.success is True
        assert sut._audit_replay_buffer_size >= 1

    def test_TC_L106_L203_120_l109_backpressure_retry(
        self, sut: ObservationAccumulator, mock_audit, make_write_req,
    ) -> None:
        """TC-L106-L203-120 · L1-09 反压 · jitter 重试成功。"""
        call_count = [0]
        def _flaky(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                from app.l1_09.errors import BackpressureError
                raise BackpressureError()
            return {"event_id": "evt-ok"}
        mock_audit.append.side_effect = _flaky
        res = sut.write_session(make_write_req(kind="pattern", title="bp"))
        assert res.success is True
        assert call_count[0] == 2  # 一次反压 + 一次重试
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_06/test_l2_03_obs_ic.py
from __future__ import annotations

import pytest
from app.l1_06.l2_03.service import ObservationAccumulator
from app.l1_06.l2_03.schemas import SnapshotRequest


class TestL2_03_IC_Contracts:

    def test_TC_L106_L203_601_ic_07_contract_fields(
        self, sut: ObservationAccumulator, make_write_req,
    ) -> None:
        """TC-L106-L203-601 · IC-07 响应字段齐：success/action/entry_id/observed_count_after。"""
        res = sut.write_session(make_write_req(kind="pattern", title="ic07"))
        for field in ("success", "action", "entry_id", "project_id",
                       "observed_count_after", "trace_id"):
            assert hasattr(res, field)

    def test_TC_L106_L203_602_ic_l2_06_snapshot_fields(
        self, sut: ObservationAccumulator, seed_entries, mock_project_id,
    ) -> None:
        """TC-L106-L203-602 · IC-L2-06 响应字段齐。"""
        seed_entries(project_id=mock_project_id, count=5, kind="pattern")
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="tr",
            kind_filter=["pattern"], min_observed_count=1,
            include_hint=True, snapshot_ttl_s=60))
        for field in ("snapshot_id", "total_entries", "kind_breakdown",
                       "entries", "expires_at"):
            assert hasattr(res, field)

    def test_TC_L106_L203_603_ic_l2_02_request_goes_to_l2_01(
        self, sut: ObservationAccumulator, mock_l2_01, make_write_req,
    ) -> None:
        """TC-L106-L203-603 · 本 L2 调 L2-01 write_slot_request 出站。"""
        sut.write_session(make_write_req(kind="pattern", title="out"))
        mock_l2_01.write_slot_request.assert_called_once()

    def test_TC_L106_L203_604_ic_09_append_event_on_every_write(
        self, sut: ObservationAccumulator, mock_audit, make_write_req,
    ) -> None:
        """TC-L106-L203-604 · 每次写入必 audit（硬约束 5）。"""
        sut.write_session(make_write_req(kind="trap", title="audit"))
        assert mock_audit.append.called
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_06/test_l2_03_obs_perf.py
from __future__ import annotations

import pytest
import time
from app.l1_06.l2_03.service import ObservationAccumulator
from app.l1_06.l2_03.schemas import SnapshotRequest


@pytest.mark.perf
class TestL2_03_SLO:

    def test_TC_L106_L203_501_merge_p50_le_20ms(
        self, sut: ObservationAccumulator, make_write_req, benchmark,
    ) -> None:
        """TC-L106-L203-501 · 合并路径 P50 ≤ 20ms。"""
        # 先写入 1 条做合并对象
        sut.write_session(make_write_req(kind="pattern", title="merge-perf"))
        def _merge():
            sut.write_session(make_write_req(kind="pattern", title="merge-perf"))
        benchmark.pedantic(_merge, iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p50"] * 1000 <= 20.0

    def test_TC_L106_L203_502_insert_p50_le_30ms(
        self, sut: ObservationAccumulator, make_write_req, benchmark,
    ) -> None:
        """TC-L106-L203-502 · 新建路径 P50 ≤ 30ms。"""
        counter = [0]
        def _insert():
            counter[0] += 1
            sut.write_session(make_write_req(kind="pattern",
                                              title=f"ins-{counter[0]}"))
        benchmark.pedantic(_insert, iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p50"] * 1000 <= 30.0

    def test_TC_L106_L203_503_batch_10_p95_le_300ms(
        self, sut: ObservationAccumulator, make_write_req, benchmark,
    ) -> None:
        """TC-L106-L203-503 · batch 10 条 P95 ≤ 300ms。"""
        counter = [0]
        def _batch():
            counter[0] += 1
            reqs = [make_write_req(kind="pattern",
                                    title=f"ba-{counter[0]}-{i}")
                    for i in range(10)]
            sut.batch_write_session(reqs)
        benchmark.pedantic(_batch, iterations=1, rounds=50)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 300.0

    def test_TC_L106_L203_504_snapshot_under_100_p99_le_1s(
        self, sut: ObservationAccumulator, seed_entries, mock_project_id,
    ) -> None:
        """TC-L106-L203-504 · snapshot < 100 条 P99 ≤ 1s。"""
        seed_entries(project_id=mock_project_id, count=80, kind="pattern")
        samples = []
        for _ in range(50):
            t0 = time.perf_counter()
            sut.provide_candidate_snapshot(SnapshotRequest(
                project_id=mock_project_id, trace_id="tr",
                kind_filter=["pattern"], min_observed_count=1,
                include_hint=True, snapshot_ttl_s=60))
            samples.append(time.perf_counter() - t0)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99) - 1]
        assert p99 <= 1.0

    def test_TC_L106_L203_505_crash_recover_1000_wal_le_5s(
        self, sut: ObservationAccumulator, seed_wal, mock_project_id,
    ) -> None:
        """TC-L106-L203-505 · 1000 WAL 恢复 ≤ 5s。"""
        seed_wal(project_id=mock_project_id, count=1000)
        t0 = time.perf_counter()
        sut.crash_recover(project_id=mock_project_id,
                           last_known_sequence_id=None, trace_id="tr")
        assert (time.perf_counter() - t0) <= 5.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_06/test_l2_03_obs_e2e.py
from __future__ import annotations

import pytest
from app.l1_06.l2_03.service import ObservationAccumulator
from app.l1_06.l2_03.schemas import SnapshotRequest


@pytest.mark.e2e
class TestL2_03_E2E:

    def test_TC_L106_L203_701_write_to_snapshot_to_promotion_candidate(
        self, sut: ObservationAccumulator, make_write_req, mock_project_id,
    ) -> None:
        """TC-L106-L203-701 · 写 3 次 → snapshot → L2-04 看到 eligible。"""
        for _ in range(3):
            sut.write_session(make_write_req(kind="pattern", title="flow1"))
        snap = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="e2e",
            kind_filter=["pattern"], min_observed_count=2,
            include_hint=True, snapshot_ttl_s=60))
        assert snap.total_entries == 1
        assert snap.entries[0].promotion_hint.session_to_project_eligible

    def test_TC_L106_L203_702_degrade_when_l109_down_still_succeed(
        self, sut: ObservationAccumulator, mock_audit, make_write_req,
    ) -> None:
        """TC-L106-L203-702 · L1-09 不可达 · 写入仍成功（不 halt）· audit 入 replay。"""
        mock_audit.append.side_effect = ConnectionError("L1-09")
        res = sut.write_session(make_write_req(kind="pattern", title="deg"))
        assert res.success is True

    def test_TC_L106_L203_703_crash_mid_write_recovers(
        self, sut: ObservationAccumulator, make_write_req, mock_project_id,
        simulate_crash,
    ) -> None:
        """TC-L106-L203-703 · 写入中途进程死 · 重启 recover 后索引完整。"""
        for i in range(5):
            sut.write_session(make_write_req(kind="pattern", title=f"c-{i}"))
        simulate_crash()  # 不清理 WAL
        res = sut.crash_recover(project_id=mock_project_id,
                                 last_known_sequence_id=None, trace_id="tr")
        assert res.replay_entries_count >= 5
```

---

## §7 测试 fixture

```python
# file: tests/l1_06/conftest_l2_03.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_06.l2_03.service import ObservationAccumulator


@pytest.fixture
def mock_project_id() -> str:
    return "hf-proj-l203"


@pytest.fixture
def mock_l2_01() -> MagicMock:
    """L2-01 TierManager · IC-L2-02 write_slot 默认 ALLOW。"""
    m = MagicMock()
    resp = MagicMock()
    resp.slot_granted = True
    resp.scope_resolved = "session"
    resp.schema_valid = True
    resp.suggested_entry_id = "kbe-auto"
    m.write_slot_request.return_value = resp
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_storage() -> MagicMock:
    """session jsonl storage。"""
    m = MagicMock()
    m.append.return_value = True
    m.read_all.return_value = []
    return m


@pytest.fixture
def mock_wal() -> MagicMock:
    m = MagicMock()
    m.fsync = MagicMock()
    return m


@pytest.fixture
def sut(mock_l2_01, mock_audit, mock_storage, mock_wal, mock_project_id):
    return ObservationAccumulator(
        tier_manager=mock_l2_01,
        audit=mock_audit,
        storage=mock_storage,
        wal=mock_wal,
        project_id=mock_project_id,
    )


@pytest.fixture
def make_write_req(mock_project_id):
    """构造合法 WriteRequest。"""
    from app.l1_06.l2_03.schemas import WriteRequest, EntryCandidate
    def _make(**kw):
        kind = kw.get("kind", "pattern")
        defaults = dict(
            pattern={"situation": "s", "solution": "sol"},
            trap={"trigger": "t", "symptom": "sy", "mitigation": "m",
                  "severity": "low"},
            recipe={"steps": ["a", "b"]},
            tool_combo={"tools": ["t1"]},
            anti_pattern={"reason": "r"},
            project_context={"description": "d"},
            external_ref={"url": "http://x"},
            effective_combo={"combo": ["a"]},
        )
        content = kw.get("content")
        if content is None:
            content = defaults.get(kind, {"desc": "d"})
        entry = EntryCandidate(
            kind=kind,
            title=kw.get("title", "default-title"),
            content=content,
            applicable_context=kw.get("applicable_context",
                                      {"stage": ["S2"], "task_type": ["coding"],
                                       "tech_stack": ["python"]}),
            source_links=kw.get("source_links", ["decision:d-001"]),
            created_by=kw.get("created_by", "L1-04.L2-05"),
            scope=kw.get("scope", "session"),
        )
        return WriteRequest(
            project_id=kw.get("project_id", mock_project_id),
            trace_id=kw.get("trace_id", "tr-default"),
            idempotency_key=kw.get("idempotency_key"),
            entry=entry,
            entry_project_id=kw.get("entry_project_id"),
            observed_count_override=kw.get("observed_count_override"),
        )
    return _make


@pytest.fixture
def seed_entries(sut):
    """批量 seed 若干 session 条目。"""
    from app.l1_06.l2_03.schemas import KBEntry
    def _seed(project_id: str, count: int, kind: str = "pattern"):
        for i in range(count):
            sut._repo.insert(KBEntry(
                id=f"kbe-{kind}-{i:06d}", project_id=project_id,
                scope="session", kind=kind, title=f"{kind}-{i}",
                content={"desc": "x"},
                applicable_context={}, observed_count=1,
                first_observed_at="2026-04-22T10:00:00Z",
                last_observed_at="2026-04-22T10:00:00Z",
                source_links=["decision:auto"],
            ))
    return _seed


@pytest.fixture
def seed_wal(sut, tmp_path):
    """填充 count 条 WAL 记录待恢复。"""
    def _seed(project_id: str, count: int):
        wal_path = tmp_path / "wal" / f"{project_id}.jsonl"
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        with wal_path.open("w") as f:
            for i in range(count):
                f.write(f'{{"seq":{i},"project_id":"{project_id}",'
                        f'"kind":"pattern","title":"w-{i}","action":"WRITE_DONE"}}\n')
        sut._wal_dir = tmp_path / "wal"
    return _seed


@pytest.fixture
def simulate_crash():
    """模拟进程 crash（保留 WAL 不清理）。"""
    def _crash():
        pass  # no-op，WAL 天然保留到 disk
    return _crash
```

---

## §8 集成点用例

```python
# file: tests/l1_06/test_l2_03_obs_integration.py
from __future__ import annotations

import pytest
from app.l1_06.l2_03.service import ObservationAccumulator
from app.l1_06.l2_03.schemas import SnapshotRequest


class TestL2_03_Integration:

    def test_TC_L106_L203_801_l2_01_schema_delegation(
        self, sut: ObservationAccumulator, mock_l2_01, make_write_req,
    ) -> None:
        """TC-L106-L203-801 · schema 校验由 L2-01 执行 · 本 L2 不自行校验。"""
        mock_l2_01.write_slot_request.return_value.schema_valid = False
        mock_l2_01.write_slot_request.return_value.slot_granted = False
        res = sut.write_session(make_write_req(kind="pattern", title="delegate"))
        assert res.success is False
        mock_l2_01.write_slot_request.assert_called_once()

    def test_TC_L106_L203_802_l2_04_pulls_candidate_via_snapshot(
        self, sut: ObservationAccumulator, seed_entries, mock_project_id,
    ) -> None:
        """TC-L106-L203-802 · L2-04 通过 IC-L2-06 拉候选。"""
        seed_entries(project_id=mock_project_id, count=10, kind="pattern")
        res = sut.provide_candidate_snapshot(SnapshotRequest(
            project_id=mock_project_id, trace_id="L204-call",
            kind_filter=["pattern"], min_observed_count=2,
            include_hint=True, snapshot_ttl_s=60))
        assert res.snapshot_file_path or res.entries
```

---

## §9 边界 / edge case

```python
# file: tests/l1_06/test_l2_03_obs_edge.py
from __future__ import annotations

import pytest
import threading


class TestL2_03_Edge:

    def test_TC_L106_L203_901_concurrent_same_kind_title_serialized(
        self, sut, make_write_req,
    ) -> None:
        """TC-L106-L203-901 · 10 并发相同 (kind, title) · 最终 count=10 无丢写。"""
        def _run():
            sut.write_session(make_write_req(kind="pattern", title="race"))
        threads = [threading.Thread(target=_run) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        entry = sut._repo.find_by_title(kind="pattern", title="race")
        assert entry.observed_count == 10

    def test_TC_L106_L203_902_empty_applicable_context(
        self, sut, make_write_req,
    ) -> None:
        """TC-L106-L203-902 · applicable_context 全空 · 允许（非必填字段）。"""
        res = sut.write_session(make_write_req(
            kind="pattern", title="empty-ctx",
            applicable_context={"stage": [], "task_type": [], "tech_stack": []}))
        assert res.success is True

    def test_TC_L106_L203_903_title_200_exactly(
        self, sut, make_write_req,
    ) -> None:
        """TC-L106-L203-903 · title 正好 200 字符 · 通过（边界）。"""
        res = sut.write_session(make_write_req(kind="pattern", title="x" * 200))
        assert res.success is True

    def test_TC_L106_L203_904_content_huge_kb_write_rejected_schema(
        self, sut, make_write_req,
    ) -> None:
        """TC-L106-L203-904 · content 字段超 schema maxLength · schema 拒。"""
        res = sut.write_session(make_write_req(
            kind="pattern", title="huge",
            content={"solution": "x" * 9000}))
        assert res.error.code == "E_L203_SCHEMA_VALIDATION_FAILED"

    def test_TC_L106_L203_905_unknown_stage_in_applicable_context(
        self, sut, make_write_req,
    ) -> None:
        """TC-L106-L203-905 · applicable_context.stage=[S99] · 非法枚举 · schema 拒。"""
        res = sut.write_session(make_write_req(
            kind="pattern", title="bad-stage",
            applicable_context={"stage": ["S99"], "task_type": ["coding"],
                                 "tech_stack": ["python"]}))
        assert res.error.code == "E_L203_SCHEMA_VALIDATION_FAILED"
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
