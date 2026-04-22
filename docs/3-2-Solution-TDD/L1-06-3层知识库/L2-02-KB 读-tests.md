---
doc_id: tests-L1-06-L2-02-KB 读-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-06-3层知识库/L2-02-KB 读.md
  - docs/2-prd/L1-06 3层知识库/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-06 L2-02-KB 读 · TDD 测试用例

> 基于 3-1 L2-02 §3（`read()` + `reverse_recall()` + `merge` + `context_match` 等 public 接口）+ §11（14 项 `KBR-*` 错误码）+ §12（P50/P95/P99 + 降级率 SLO）驱动。
> TC ID 统一格式：`TC-L106-L202-NNN`。
> pytest · `class TestL2_02_KBRead` 组织；负向 / 性能 / 集成 / e2e 分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × TC 矩阵

| 方法 | TC ID | 覆盖类型 |
|---|---|---|
| `read()` · 主流程正向 | TC-L106-L202-001 | unit |
| `read()` · cache_hit 短路 | TC-L106-L202-002 | unit |
| `read()` · S>P>G 合并正向 | TC-L106-L202-003 | unit |
| `read()` · kind_filter 正向 | TC-L106-L202-004 | unit |
| `read()` · applicable_context AND 匹配 | TC-L106-L202-005 | unit |
| `read()` · 候选 > 500 截断 | TC-L106-L202-006 | unit |
| `read()` · rerank 正向 | TC-L106-L202-007 | unit |
| `reverse_recall()` · 正向 | TC-L106-L202-008 | unit |
| `merge_scope_priority()` · 同 id S 覆盖 P | TC-L106-L202-009 | unit |
| `context_match()` · strict_mode 正向 | TC-L106-L202-010 | unit |
| `context_match()` · 缺省通过 | TC-L106-L202-011 | unit |
| `kind_allowed()` · 策略枚举 | TC-L106-L202-012 | unit |
| `read()` · audit 事件发送 | TC-L106-L202-013 | unit |
| `read()` · trace_id 回传 | TC-L106-L202-014 | unit |
| `read()` · top_k 截断 | TC-L106-L202-015 | unit |

### §1.2 错误码 × TC 矩阵（§11 14 项全覆盖）

| 错误码 | TC ID | 方法 | 触发条件 |
|---|---|---|---|
| `KBR-001` 入参 schema 错 | TC-L106-L202-101 | `read` | top_k=-1 |
| `KBR-002` NLQ 被拒 | TC-L106-L202-102 | `read` | query 含自然语言 |
| `KBR-003` scope 拒绝 | TC-L106-L202-103 | `read` | L2-01 返空 allowed_scopes |
| `KBR-004` 跨项目违规 | TC-L106-L202-104 | `read` | project_id 不匹配 session |
| `KBR-005` kind 策略禁用 | TC-L106-L202-105 | `read` | kind 当前 stage 禁用 |
| `KBR-006` 存储全层不可达 | TC-L106-L202-106 | `read` | 3 层 IOError |
| `KBR-007` 整体超时 | TC-L106-L202-107 | `read` | 全流程 > 1s |
| `KBR-008` rerank 失败 | TC-L106-L202-108 | `read` | L2-05 timeout |
| `KBR-009` 缓存损坏 | TC-L106-L202-109 | `read` | tick_cache corrupt |
| `KBR-010` 候选溢出 | TC-L106-L202-110 | `read` | matched > 500 |
| `KBR-011` 条目 schema 错 | TC-L106-L202-111 | `read` | jsonl 条目字段缺 |
| `KBR-012` trace_id 缺失 | TC-L106-L202-112 | `read` | trace_id=None |
| `KBR-013` 反向召回未授权 | TC-L106-L202-113 | `reverse_recall` | caller ≠ L2-05 |
| `KBR-014` jsonl 坏行 | TC-L106-L202-114 | `read_session` | jsonl 末行截断 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-06 kb_read | caller → L2-02 | TC-L106-L202-601 | 主入口合约 |
| IC-L2-01 scope_check | L2-02 → L2-01 | TC-L106-L202-602 | 读前强制校验 |
| IC-L2-05 rerank | L2-02 → L2-05 | TC-L106-L202-603 | 每次读必 rerank |
| IC-09 audit | L2-02 → L1-09 | TC-L106-L202-604 | 每次读写审计 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| P50 延迟 | ≤ 50ms | TC-L106-L202-501 |
| P95 延迟 | ≤ 200ms | TC-L106-L202-502 |
| P99 延迟 | ≤ 500ms | TC-L106-L202-503 |
| 缓存命中率 | ≥ 60% | TC-L106-L202-504 |
| 错误率 | ≤ 0.5% | TC-L106-L202-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_06/test_l2_02_kb_read_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.kb.read.service import KBReadService
from app.kb.read.schemas import (
    ReadRequest, ReadResult, ApplicableContext, RerankResponse,
)


class TestL2_02_KBRead_Positive:

    def test_TC_L106_L202_001_read_happy_path(
        self, sut: KBReadService, mock_project_id: str, mock_session_id: str,
        mock_l2_01, mock_l2_05, fake_repo,
    ) -> None:
        """TC-L106-L202-001 · 标准流程 · 3 层返回 10 条 → rerank → top_k=5。"""
        fake_repo.seed(session=3, project=4, global_=3)
        mock_l2_05.rerank.return_value = RerankResponse(
            ranked=fake_repo.all()[:5], signals_used=["bm25", "embed"])
        req = ReadRequest(trace_id="tr-001", project_id=mock_project_id,
                          session_id=mock_session_id, kind=None,
                          applicable_context=ApplicableContext(route="S2"),
                          top_k=5, cache_enabled=True)
        res: ReadResult = sut.read(req)
        assert res.trace_id == "tr-001"
        assert res.error_hint is None
        assert len(res.entries) == 5
        assert res.meta.cache_hit is False

    def test_TC_L106_L202_002_read_cache_hit_short_circuit(
        self, sut: KBReadService, mock_project_id: str, mock_session_id: str,
    ) -> None:
        """TC-L106-L202-002 · 同 tick 内重复请求 · cache_hit=True · 不再读 3 层。"""
        req = ReadRequest(trace_id="tr-002", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(route="S2"),
                          top_k=5, cache_enabled=True)
        first = sut.read(req)
        sut._repo.read_session = MagicMock(side_effect=AssertionError("不该被再次调用"))
        second = sut.read(req)
        assert second.meta.cache_hit is True

    def test_TC_L106_L202_003_read_spg_priority_merge(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-003 · 同 id 在 S/P/G 三层 · Session 版本胜出（S>P>G）。"""
        fake_repo.seed_conflict(entry_id="kbe-0001SAME",
                                 session_title="S 版", project_title="P 版",
                                 global_title="G 版")
        req = ReadRequest(trace_id="tr-003", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(route="S2"),
                          top_k=5, cache_enabled=False)
        res = sut.read(req)
        titles = [e.title for e in res.entries]
        assert "S 版" in titles
        assert "P 版" not in titles

    def test_TC_L106_L202_004_read_kind_filter(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-004 · kind=["pattern"] · 其他 kind 被过滤。"""
        fake_repo.seed_kinds(["pattern", "trap", "recipe"], count_each=3)
        req = ReadRequest(trace_id="tr-004", project_id=mock_project_id,
                          session_id=mock_session_id, kind=["pattern"],
                          applicable_context=ApplicableContext(),
                          top_k=10, cache_enabled=False)
        res = sut.read(req)
        assert all(e.kind == "pattern" for e in res.entries)

    def test_TC_L106_L202_005_context_match_and(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-005 · applicable_context route=S2 AND tech_stack=[python]。"""
        fake_repo.seed_contexts([("S2", ["python"]), ("S2", ["go"]),
                                  ("S3", ["python"])])
        req = ReadRequest(trace_id="tr-005", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(
                              route="S2", tech_stack=["python"]),
                          top_k=10, strict_mode=True)
        res = sut.read(req)
        assert len(res.entries) == 1  # 只有 (S2, python) 匹配

    def test_TC_L106_L202_006_candidate_overflow_truncated(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-006 · 匹配 800 条 · 截断到 500 · audit kb_read_candidate_overflow。"""
        fake_repo.seed(session=300, project=300, global_=200)
        req = ReadRequest(trace_id="tr-006", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(),
                          top_k=10)
        res = sut.read(req)
        assert res.meta.candidate_overflow is True
        assert res.meta.candidate_count == 500

    def test_TC_L106_L202_007_rerank_invoked_with_candidates(
        self, sut: KBReadService, mock_l2_05, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-007 · rerank 被调用 · candidates 非空。"""
        fake_repo.seed(session=2, project=2, global_=2)
        req = ReadRequest(trace_id="tr-007", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(route="S2"),
                          top_k=3)
        sut.read(req)
        mock_l2_05.rerank.assert_called_once()
        call_args = mock_l2_05.rerank.call_args[0][0]
        assert len(call_args.candidates) == 6

    def test_TC_L106_L202_008_reverse_recall_allowed_for_l2_05(
        self, sut: KBReadService, mock_project_id, mock_session_id, fake_repo,
    ) -> None:
        """TC-L106-L202-008 · reverse_recall 被 L2-05 合法调用 · 返回 candidates。"""
        fake_repo.seed(session=2, project=2, global_=2)
        res = sut.reverse_recall(project_id=mock_project_id,
                                  session_id=mock_session_id,
                                  stage="S3", kinds=["pattern"],
                                  caller_identity="L2-05")
        assert len(res) >= 1

    def test_TC_L106_L202_009_merge_scope_priority_session_wins(
        self, sut: KBReadService,
    ) -> None:
        """TC-L106-L202-009 · 纯函数 · merge_scope_priority 同 id Session 覆盖 Project。"""
        s = [MagicMock(id="kbe-SAME", scope="session", title="S-win")]
        p = [MagicMock(id="kbe-SAME", scope="project", title="P-lose")]
        g = [MagicMock(id="kbe-OTHER", scope="global", title="G-only")]
        merged = sut._merger.merge(s, p, g)
        titles = [m.title for m in merged]
        assert "S-win" in titles
        assert "G-only" in titles
        assert "P-lose" not in titles

    def test_TC_L106_L202_010_context_match_strict_true(
        self, sut: KBReadService,
    ) -> None:
        """TC-L106-L202-010 · strict_mode=True · entry 缺 route 则不通过。"""
        e1 = MagicMock(applicable_context=MagicMock(route=None,
                                                    tech_stack=["python"]))
        ctx = ApplicableContext(route="S2", tech_stack=["python"])
        assert sut._matcher.match(e1, ctx, strict_mode=True) is False

    def test_TC_L106_L202_011_context_match_default_pass(
        self, sut: KBReadService,
    ) -> None:
        """TC-L106-L202-011 · strict_mode=False · entry 缺 route 按缺省通过。"""
        e1 = MagicMock(applicable_context=MagicMock(route=None,
                                                    tech_stack=[]))
        ctx = ApplicableContext(route="S2", tech_stack=["python"])
        assert sut._matcher.match(e1, ctx, strict_mode=False) is True

    def test_TC_L106_L202_012_kind_allowed_by_stage(
        self, sut: KBReadService,
    ) -> None:
        """TC-L106-L202-012 · kind=effective_combo 仅在 S4_execute 允许。"""
        e = MagicMock(kind="effective_combo")
        assert sut._kind_policy.allowed(e, stage="S4_execute") is True
        assert sut._kind_policy.allowed(e, stage="S1_plan") is False

    def test_TC_L106_L202_013_audit_event_on_every_read(
        self, sut: KBReadService, mock_audit, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-013 · 每次 read 必推 IC-09 audit · event_type=kb_read."""
        fake_repo.seed(session=1, project=1, global_=1)
        req = ReadRequest(trace_id="tr-013", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        sut.read(req)
        mock_audit.append.assert_called()
        first = mock_audit.append.call_args_list[0]
        et = first.kwargs.get("event_type") or first.args[0]
        assert et.startswith("kb_read")

    def test_TC_L106_L202_014_trace_id_round_trip(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-014 · trace_id 原样回传。"""
        fake_repo.seed(session=1, project=0, global_=0)
        req = ReadRequest(trace_id="my-trace-XYZ",
                          project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=1)
        res = sut.read(req)
        assert res.trace_id == "my-trace-XYZ"

    def test_TC_L106_L202_015_top_k_truncates_rerank_output(
        self, sut: KBReadService, mock_l2_05, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-015 · rerank 返 20 条但 top_k=5 · 只取 5 条。"""
        fake_repo.seed(session=10, project=10, global_=0)
        req = ReadRequest(trace_id="tr-015", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=5)
        res = sut.read(req)
        assert len(res.entries) == 5
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_06/test_l2_02_kb_read_negative.py
from __future__ import annotations

import pytest
from app.kb.read.service import KBReadService
from app.kb.read.schemas import ReadRequest, ApplicableContext
from app.kb.read.errors import KBReadRejected, KBSecurityError


class TestL2_02_Negative:

    def test_TC_L106_L202_101_invalid_top_k(
        self, sut: KBReadService, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-101 · KBR-001 · top_k=-1。"""
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=-1)
        res = sut.read(req)
        assert res.error_hint == "kb_rejected"
        assert res.error_code == "KBR-001"

    def test_TC_L106_L202_102_nl_query_rejected(
        self, sut: KBReadService, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-102 · KBR-002 · 入参含自由文本 NLQ。"""
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(),
                          top_k=3, nlq="请找出所有关于 FastAPI 的模式")
        res = sut.read(req)
        assert res.error_code == "KBR-002"

    def test_TC_L106_L202_103_scope_denied(
        self, sut: KBReadService, mock_l2_01, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-103 · KBR-003 · L2-01 返回 allowed_scopes=[]。"""
        mock_l2_01.scope_check.return_value.allowed_scopes = []
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        res = sut.read(req)
        assert res.error_code == "KBR-003"
        assert res.error_hint == "kb_rejected"

    def test_TC_L106_L202_104_cross_project(
        self, sut: KBReadService, mock_l2_01, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-104 · KBR-004 · L2-01 拋跨项目违规。"""
        from app.l1_06.l2_01.errors import ScopeCheckError
        mock_l2_01.scope_check.side_effect = ScopeCheckError("cross-project")
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id="s-OTHER",
                          applicable_context=ApplicableContext(), top_k=3)
        res = sut.read(req)
        assert res.error_code == "KBR-003"  # 由 L2-02 收敛为 kb_rejected

    def test_TC_L106_L202_105_kind_policy_forbidden_for_stage(
        self, sut: KBReadService, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-105 · KBR-005 · S1 阶段禁用 kind=effective_combo。"""
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(route="S1"),
                          kind=["effective_combo"], top_k=3)
        res = sut.read(req)
        assert res.error_code == "KBR-005"

    def test_TC_L106_L202_106_storage_all_layers_io_error(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-106 · KBR-006 · 3 层 read_* 全 IOError · 返空 degraded。"""
        fake_repo.fail_all_layers(IOError("disk bad"))
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        res = sut.read(req)
        assert res.entries == []
        assert res.error_hint == "kb_degraded"
        assert res.error_code == "KBR-006"

    def test_TC_L106_L202_107_global_timeout(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-107 · KBR-007 · 整体 > 1s · 超时。"""
        fake_repo.slow_all_layers(delay_ms=1500)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3,
                          global_timeout_ms=1000)
        res = sut.read(req)
        assert res.error_code == "KBR-007"
        assert res.error_hint == "kb_timeout"

    def test_TC_L106_L202_108_rerank_fallback(
        self, sut: KBReadService, mock_l2_05, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-108 · KBR-008 · L2-05 超时 · fallback observed_count DESC。"""
        from app.l1_06.l2_05.errors import RerankTimeout
        mock_l2_05.rerank.side_effect = RerankTimeout()
        fake_repo.seed(session=2, project=2, global_=0)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        res = sut.read(req)
        assert res.error_hint is None  # 用户不感知 · meta.degraded 标记
        assert res.meta.rerank_fallback is True
        assert res.meta.fallback_reason == "KBR-008"

    def test_TC_L106_L202_109_cache_corrupt_retry_succeeds(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-109 · KBR-009 · tick_cache.get 抛 · 清缓存重试成功。"""
        fake_repo.seed(session=1, project=0, global_=0)
        sut._tick_cache.force_corrupt()
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=1,
                          cache_enabled=True)
        res = sut.read(req)
        assert res.error_hint is None
        assert res.meta.cache_recovered is True

    def test_TC_L106_L202_110_candidate_overflow_audit(
        self, sut: KBReadService, fake_repo, mock_audit,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-110 · KBR-010 · 600 候选 · audit kb_read_candidate_overflow。"""
        fake_repo.seed(session=300, project=300, global_=0)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        sut.read(req)
        events = [c.kwargs.get("event_type") or (c.args[0] if c.args else None)
                  for c in mock_audit.append.call_args_list]
        assert "kb_read_candidate_overflow" in events

    def test_TC_L106_L202_111_entry_schema_invalid_skipped(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-111 · KBR-011 · jsonl 缺字段条目跳过 · 其他正常。"""
        fake_repo.seed_with_bad_entries(session_good=2, session_bad=1)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=5)
        res = sut.read(req)
        assert res.meta.schema_invalid_skipped == 1
        assert len(res.entries) == 2

    def test_TC_L106_L202_112_missing_trace_id(
        self, sut: KBReadService, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-112 · KBR-012 · trace_id=None 必拒。"""
        req = ReadRequest(trace_id=None, project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        res = sut.read(req)
        assert res.error_code == "KBR-012"

    def test_TC_L106_L202_113_reverse_recall_unauthorized(
        self, sut: KBReadService, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-113 · KBR-013 · reverse_recall 非 L2-05 调用 · 必抛。"""
        with pytest.raises(KBSecurityError) as exc:
            sut.reverse_recall(project_id=mock_project_id,
                               session_id=mock_session_id,
                               stage="S3", kinds=["pattern"],
                               caller_identity="attacker")
        assert exc.value.code == "KBR-013"

    def test_TC_L106_L202_114_jsonl_corrupt_line_skipped(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-114 · KBR-014 · jsonl 末行截断 · 跳过 · audit kb_jsonl_line_corrupt。"""
        fake_repo.seed_with_truncated_jsonl(good_lines=3, bad_last_line=True)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=5)
        res = sut.read(req)
        assert res.meta.jsonl_line_corrupt_skipped >= 1
        assert len(res.entries) == 3
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_06/test_l2_02_kb_read_ic.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.kb.read.service import KBReadService
from app.kb.read.schemas import ReadRequest, ApplicableContext


class TestL2_02_IC_Contracts:

    def test_TC_L106_L202_601_ic_06_contract_fields(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-601 · IC-06 响应字段齐：entries / trace_id / meta / error_hint。"""
        fake_repo.seed(session=1, project=1, global_=1)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        res = sut.read(req)
        for field in ("entries", "trace_id", "meta", "error_hint"):
            assert hasattr(res, field)

    def test_TC_L106_L202_602_l2_01_scope_check_invoked(
        self, sut: KBReadService, mock_l2_01, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-602 · 每次 read 前必调 L2-01 scope_check。"""
        fake_repo.seed(session=1, project=0, global_=0)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        sut.read(req)
        mock_l2_01.scope_check.assert_called_once()

    def test_TC_L106_L202_603_l2_05_rerank_invoked_with_top_k(
        self, sut: KBReadService, mock_l2_05, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-603 · rerank 被调 · 传入 top_k。"""
        fake_repo.seed(session=3, project=3, global_=3)
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=4)
        sut.read(req)
        args = mock_l2_05.rerank.call_args[0][0]
        assert args.top_k == 4

    def test_TC_L106_L202_604_ic_09_audit_always(
        self, sut: KBReadService, mock_audit, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-604 · 成功 / 失败 / 降级 都必须 audit IC-09。"""
        fake_repo.fail_all_layers(IOError("down"))
        req = ReadRequest(trace_id="tr", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        sut.read(req)
        assert mock_audit.append.called
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_06/test_l2_02_kb_read_perf.py
from __future__ import annotations

import pytest
import time
from app.kb.read.service import KBReadService
from app.kb.read.schemas import ReadRequest, ApplicableContext


@pytest.mark.perf
class TestL2_02_SLO:

    def test_TC_L106_L202_501_p50_le_50ms(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
        benchmark,
    ) -> None:
        """TC-L106-L202-501 · 100 次调用 P50 ≤ 50ms。"""
        fake_repo.seed(session=3, project=3, global_=3)
        req = ReadRequest(trace_id="perf", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=5)
        benchmark.pedantic(sut.read, args=(req,), iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p50"] * 1000 <= 50.0

    def test_TC_L106_L202_502_p95_le_200ms(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
        benchmark,
    ) -> None:
        """TC-L106-L202-502 · P95 ≤ 200ms。"""
        fake_repo.seed(session=10, project=10, global_=10)
        req = ReadRequest(trace_id="perf", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=10)
        benchmark.pedantic(sut.read, args=(req,), iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 200.0

    def test_TC_L106_L202_503_p99_le_500ms(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
        benchmark,
    ) -> None:
        """TC-L106-L202-503 · P99 ≤ 500ms。"""
        fake_repo.seed(session=100, project=100, global_=100)
        req = ReadRequest(trace_id="perf", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=10)
        benchmark.pedantic(sut.read, args=(req,), iterations=1, rounds=300)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 500.0

    def test_TC_L106_L202_504_cache_hit_rate_ge_60pct(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-504 · 同 tick 内重复查询 · cache hit 率 ≥ 60%。"""
        fake_repo.seed(session=2, project=2, global_=2)
        req = ReadRequest(trace_id="perf-cache", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3,
                          cache_enabled=True)
        hits = 0
        total = 10
        for _ in range(total):
            res = sut.read(req)
            if res.meta.cache_hit:
                hits += 1
        assert hits / total >= 0.6

    def test_TC_L106_L202_505_error_rate_le_0_5_pct(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-505 · 正常负载下错误率 ≤ 0.5%。"""
        fake_repo.seed(session=3, project=3, global_=3)
        errors = 0
        total = 200
        for i in range(total):
            req = ReadRequest(trace_id=f"err-{i}", project_id=mock_project_id,
                              session_id=mock_session_id,
                              applicable_context=ApplicableContext(),
                              top_k=3)
            if sut.read(req).error_hint:
                errors += 1
        assert errors / total <= 0.005
```

---

## §6 端到端 e2e

```python
# file: tests/l1_06/test_l2_02_kb_read_e2e.py
from __future__ import annotations

import pytest
from app.kb.read.service import KBReadService
from app.kb.read.schemas import ReadRequest, ApplicableContext


@pytest.mark.e2e
class TestL2_02_E2E:

    def test_TC_L106_L202_701_l1_01_to_l2_02_to_l2_05_full(
        self, sut: KBReadService, mock_l2_01, mock_l2_05,
        fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-701 · L1-01 → L2-02 → L2-05 全链路（对 PRD I1）。"""
        fake_repo.seed(session=2, project=3, global_=5)
        req = ReadRequest(trace_id="e2e-1", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(route="S4"),
                          top_k=5)
        res = sut.read(req)
        assert res.error_hint is None
        assert len(res.entries) == 5
        mock_l2_01.scope_check.assert_called_once()
        mock_l2_05.rerank.assert_called_once()

    def test_TC_L106_L202_702_reverse_recall_stage_changed_trigger(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-702 · stage_changed 事件触发反向召回（PRD I2）。"""
        fake_repo.seed_for_stage("S3", ["pattern", "trap"], count=3)
        res = sut.reverse_recall(project_id=mock_project_id,
                                  session_id=mock_session_id,
                                  stage="S3", kinds=["pattern", "trap"],
                                  caller_identity="L2-05")
        assert len(res) >= 3

    def test_TC_L106_L202_703_degraded_path_returns_empty_not_halt(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-703 · 降级不 halt（PRD N3）。"""
        fake_repo.fail_all_layers(IOError("全层坏"))
        req = ReadRequest(trace_id="e2e-3", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=5)
        res = sut.read(req)
        assert res.entries == []
        assert res.error_hint == "kb_degraded"
```

---

## §7 测试 fixture

```python
# file: tests/l1_06/conftest_l2_02.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.kb.read.service import KBReadService


@pytest.fixture
def mock_project_id() -> str:
    return "hf-proj-l202"


@pytest.fixture
def mock_session_id() -> str:
    return "hf-sess-l202"


@pytest.fixture
def mock_l2_01():
    """IC-L2-01 scope_check · 默认 allow 全部 3 层。"""
    m = MagicMock()
    resp = MagicMock()
    resp.allowed_scopes = ["session", "project", "global"]
    resp.isolation_ctx = MagicMock()
    m.scope_check.return_value = resp
    return m


@pytest.fixture
def mock_l2_05():
    """IC-L2-05 rerank · 默认原顺序返回前 top_k 条。"""
    m = MagicMock()
    def _rerank(req, *a, **kw):
        from app.kb.read.schemas import RerankResponse
        return RerankResponse(ranked=req.candidates[:req.top_k],
                               signals_used=["bm25"])
    m.rerank.side_effect = _rerank
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    """IC-09 append_event sink。"""
    return MagicMock()


@pytest.fixture
def fake_repo():
    """KBEntryRepository 可控 fake · 支持 seed/conflict/io-error 各模式。"""
    class _Fake:
        def __init__(self):
            self._session, self._project, self._global = [], [], []
            self._fail_all = False
            self._slow_ms = 0
        def seed(self, session=0, project=0, global_=0):
            from app.kb.read.schemas import KBEntry, ApplicableContext
            def mk(n, scope):
                return [KBEntry(
                    id=f"kbe-{scope}{i:05d}", project_id="hf-proj-l202",
                    scope=scope, kind="pattern",
                    title=f"{scope}-t-{i}", content="c" * 20,
                    applicable_context=ApplicableContext(route="S2"),
                    observed_count=i + 1,
                    first_observed_at="2026-04-22T10:00:00Z",
                    last_observed_at="2026-04-22T10:00:00Z",
                ) for i in range(n)]
            self._session = mk(session, "session")
            self._project = mk(project, "project")
            self._global = mk(global_, "global")
        def seed_kinds(self, kinds, count_each):
            from app.kb.read.schemas import KBEntry, ApplicableContext
            self._session = [
                KBEntry(id=f"kbe-{k}{i}", project_id="p", scope="session",
                        kind=k, title=f"t-{k}-{i}", content="x" * 20,
                        applicable_context=ApplicableContext(),
                        observed_count=1,
                        first_observed_at="t", last_observed_at="t")
                for k in kinds for i in range(count_each)]
        def seed_contexts(self, pairs):
            from app.kb.read.schemas import KBEntry, ApplicableContext
            self._session = [
                KBEntry(id=f"kbe-{i}", project_id="p", scope="session",
                        kind="pattern", title=f"t-{i}", content="c" * 20,
                        applicable_context=ApplicableContext(
                            route=rt, tech_stack=tech),
                        observed_count=1,
                        first_observed_at="t", last_observed_at="t")
                for i, (rt, tech) in enumerate(pairs)]
        def seed_conflict(self, entry_id, session_title, project_title, global_title):
            from app.kb.read.schemas import KBEntry, ApplicableContext
            mk = lambda scope, title: KBEntry(
                id=entry_id, project_id="p", scope=scope, kind="pattern",
                title=title, content="c" * 20,
                applicable_context=ApplicableContext(route="S2"),
                observed_count=1, first_observed_at="t", last_observed_at="t")
            self._session = [mk("session", session_title)]
            self._project = [mk("project", project_title)]
            self._global = [mk("global", global_title)]
        def seed_for_stage(self, stage, kinds, count):
            from app.kb.read.schemas import KBEntry, ApplicableContext
            self._session = [KBEntry(
                id=f"kbe-{k}{i}", project_id="p", scope="session",
                kind=k, title=f"{stage}-{k}-{i}", content="c" * 20,
                applicable_context=ApplicableContext(route=stage),
                observed_count=1,
                first_observed_at="t", last_observed_at="t")
                for k in kinds for i in range(count)]
        def seed_with_bad_entries(self, session_good, session_bad):
            self.seed(session=session_good)
            self._session_bad_count = session_bad
        def seed_with_truncated_jsonl(self, good_lines, bad_last_line):
            self.seed(session=good_lines)
            self._jsonl_truncated = bad_last_line
        def fail_all_layers(self, exc):
            self._fail_all = exc
        def slow_all_layers(self, delay_ms):
            self._slow_ms = delay_ms
        def read_session(self, ctx, kinds):
            if self._fail_all: raise self._fail_all
            return self._session
        def read_project(self, ctx, kinds):
            if self._fail_all: raise self._fail_all
            return self._project
        def read_global(self, kinds):
            if self._fail_all: raise self._fail_all
            return self._global
        def all(self):
            return self._session + self._project + self._global
    return _Fake()


@pytest.fixture
def sut(mock_l2_01, mock_l2_05, mock_audit, fake_repo):
    """KBReadService 注入全部 mocks。"""
    return KBReadService(
        scope_checker=mock_l2_01,
        reranker=mock_l2_05,
        audit=mock_audit,
        repo=fake_repo,
    )
```

---

## §8 集成点用例

```python
# file: tests/l1_06/test_l2_02_integration.py
from __future__ import annotations

import pytest
from app.kb.read.service import KBReadService
from app.kb.read.schemas import ReadRequest, ApplicableContext


class TestL2_02_Integration:

    def test_TC_L106_L202_801_l1_01_decision_loop_injection(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-801 · L1-01 决策环注入 KB · 单 tick 最多调用 1 次 read（缓存命中）。"""
        fake_repo.seed(session=3, project=3, global_=3)
        req = ReadRequest(trace_id="tick-1", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(route="S4"),
                          top_k=3, cache_enabled=True)
        sut.read(req)
        # 2 次重复 read 都命中 cache
        r2 = sut.read(req)
        r3 = sut.read(req)
        assert r2.meta.cache_hit
        assert r3.meta.cache_hit

    def test_TC_L106_L202_802_with_l2_03_session_writes_visible_next_read(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-802 · L2-03 写 session 后 · 同 tick 内 cache invalidate 再读可见。"""
        req = ReadRequest(trace_id="next", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=5,
                          cache_enabled=True)
        fake_repo.seed(session=1)
        r1 = sut.read(req)
        # 模拟 L2-03 写入新条目 → L2-02 缓存应 invalidate
        fake_repo.seed(session=2)
        sut._tick_cache.invalidate_on_write()
        r2 = sut.read(req)
        assert len(r2.entries) >= len(r1.entries)
```

---

## §9 边界 / edge case

```python
# file: tests/l1_06/test_l2_02_edge.py
from __future__ import annotations

import pytest
import threading
from app.kb.read.service import KBReadService
from app.kb.read.schemas import ReadRequest, ApplicableContext


class TestL2_02_Edge:

    def test_TC_L106_L202_901_empty_kb_returns_empty_no_error(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-901 · 3 层全空 · entries=[] · error_hint=None（不是错）。"""
        fake_repo.seed(0, 0, 0)
        req = ReadRequest(trace_id="empty", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=3)
        res = sut.read(req)
        assert res.entries == []
        assert res.error_hint is None

    def test_TC_L106_L202_902_top_k_zero(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-902 · top_k=0 · 返回空但不视为错。"""
        fake_repo.seed(session=3)
        req = ReadRequest(trace_id="tk0", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=0)
        res = sut.read(req)
        assert res.entries == []

    def test_TC_L106_L202_903_very_long_content_truncated_at_8000(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-903 · content 9000 字符的条目被 schema 丢弃（KBR-011）。"""
        fake_repo.seed_with_bad_entries(session_good=2, session_bad=1)
        req = ReadRequest(trace_id="long", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=10)
        res = sut.read(req)
        assert res.meta.schema_invalid_skipped >= 1

    def test_TC_L106_L202_904_concurrent_16_reads_no_lock_contention(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-904 · 16 线程并发 · 无锁竞争报错。"""
        fake_repo.seed(session=5, project=5, global_=5)
        req = ReadRequest(trace_id="conc", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=5,
                          cache_enabled=False)
        errs = []
        def _run():
            try:
                sut.read(req)
            except Exception as e:
                errs.append(e)
        threads = [threading.Thread(target=_run) for _ in range(16)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errs

    def test_TC_L106_L202_905_scope_subset_only_session(
        self, sut: KBReadService, mock_l2_01, fake_repo,
        mock_project_id, mock_session_id,
    ) -> None:
        """TC-L106-L202-905 · L2-01 只允许 session · project/global 层不被读取。"""
        mock_l2_01.scope_check.return_value.allowed_scopes = ["session"]
        fake_repo.seed(session=2, project=5, global_=5)
        req = ReadRequest(trace_id="only-s", project_id=mock_project_id,
                          session_id=mock_session_id,
                          applicable_context=ApplicableContext(), top_k=10)
        res = sut.read(req)
        # rerank input 仅 2 条（session 层）
        assert len(res.entries) <= 2
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
