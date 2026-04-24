"""L1-01 L2-02 Decision Engine · KBReaderAdapter 集成测试.

IC-06 真实集成:
    - 调 Dev-β `app.knowledge_base.reader.KBReadService`(已 merged)
    - KBEntry → KBSnippet 映射
    - 降级铁律:reader 抛异常 → 返回空 list(prd §9.6 #2)
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.knowledge_base.reader.schemas import (
    ApplicableContext,
    KBEntry,
    ReadMeta,
    ReadResult,
)
from app.main_loop.decision_engine.kb_reader_adapter import (
    KBReaderAdapter,
    _kb_entry_to_snippet,
)
from app.main_loop.decision_engine.schemas import KBSnippet


class TestKBReaderAdapterMapping:
    """KBEntry → KBSnippet 映射。"""

    def test_TC_W03_AD01_entry_to_snippet_basic(self) -> None:
        """KBEntry 的 kind/tags/rerank/observed 应透传。"""
        entry = KBEntry(
            id="kb-1",
            kind="pattern",
            applicable_context=ApplicableContext(tech_stack=["python", "fastapi"]),
            rerank_score=0.7,
            observed_count=8,
        )
        snip = _kb_entry_to_snippet(entry, fallback_tags=("fallback",))
        assert snip.kind == "pattern"
        assert snip.tags == ("python", "fastapi")
        assert snip.rerank_score == pytest.approx(0.7)
        assert snip.observed_count == 8

    def test_TC_W03_AD02_entry_fallback_tags_when_empty(self) -> None:
        """KBEntry.applicable_context.tech_stack 空 → 用 fallback_tags。"""
        entry = KBEntry(id="kb-2", kind="trap")
        snip = _kb_entry_to_snippet(entry, fallback_tags=("q1", "q2"))
        assert snip.tags == ("q1", "q2")

    def test_TC_W03_AD03_entry_None_rerank_safe(self) -> None:
        """rerank_score 为 None / 0 · 不炸。"""
        entry = KBEntry(id="kb-3", kind="pattern")  # default rerank=0
        snip = _kb_entry_to_snippet(entry, fallback_tags=())
        assert snip.rerank_score == 0.0


class TestKBReaderAdapterFetch:
    """fetch_snippets · 走完整 reader.read 链路。"""

    def test_TC_W03_AD04_fetch_happy_path(self) -> None:
        """reader 返回 2 条 entries · adapter 产 2 条 snippets。"""
        entries = [
            KBEntry(
                id=f"kb-{i}", kind="pattern",
                applicable_context=ApplicableContext(tech_stack=["deepseek"]),
                rerank_score=0.5 + i * 0.1,
                observed_count=i + 1,
            )
            for i in range(2)
        ]
        result = ReadResult(
            entries=entries,
            meta=ReadMeta(project_id="pid-x"),
            trace_id="trace-x",
        )
        reader = MagicMock()
        reader.read.return_value = result
        adapter = KBReaderAdapter(reader=reader)
        snippets = adapter.fetch_snippets(
            project_id="pid-x",
            session_id="sess-x",
            tick_id="tick-x",
            tags=("deepseek",),
            top_k=5,
        )
        assert len(snippets) == 2
        assert all(isinstance(s, KBSnippet) for s in snippets)
        assert snippets[0].tags == ("deepseek",)
        reader.read.assert_called_once()
        # 校验传入 ReadRequest 合法
        req = reader.read.call_args.args[0]
        assert req.project_id == "pid-x"
        assert req.tick_id == "tick-x"
        assert req.top_k == 5

    def test_TC_W03_AD05_fetch_empty_entries(self) -> None:
        """reader 返回 0 条 · adapter 返回空 list。"""
        result = ReadResult(entries=[], meta=ReadMeta(project_id="p"),
                            trace_id="t")
        reader = MagicMock()
        reader.read.return_value = result
        adapter = KBReaderAdapter(reader=reader)
        snippets = adapter.fetch_snippets(
            project_id="p", session_id="s", tick_id="tk",
        )
        assert snippets == []

    def test_TC_W03_AD06_fetch_silent_on_exception(self) -> None:
        """reader.read 抛异常 → 降级静默 · 返回空 list。"""
        reader = MagicMock()
        reader.read.side_effect = RuntimeError("kb down")
        adapter = KBReaderAdapter(reader=reader)
        snippets = adapter.fetch_snippets(
            project_id="p", session_id="s", tick_id="t",
        )
        assert snippets == []

    def test_TC_W03_AD07_fetch_trace_id_default(self) -> None:
        """未传 trace_id · adapter 自动用 'trace-<tick_id>' 构造。"""
        result = ReadResult(entries=[], meta=ReadMeta(project_id="p"),
                            trace_id=None)
        reader = MagicMock()
        reader.read.return_value = result
        adapter = KBReaderAdapter(reader=reader)
        adapter.fetch_snippets(project_id="p", session_id="s", tick_id="tk-abc")
        req = reader.read.call_args.args[0]
        assert req.trace_id == "trace-tk-abc"

    def test_TC_W03_AD08_fetch_with_kind_filter(self) -> None:
        """传 kind_filter='pattern' · 透传到 ReadRequest.kind。"""
        result = ReadResult(entries=[], meta=ReadMeta(project_id="p"),
                            trace_id="t")
        reader = MagicMock()
        reader.read.return_value = result
        adapter = KBReaderAdapter(reader=reader)
        adapter.fetch_snippets(
            project_id="p", session_id="s", tick_id="t",
            kind_filter="pattern",
        )
        req = reader.read.call_args.args[0]
        assert req.kind == "pattern"

    def test_TC_W03_AD09_adapter_uses_dev_beta_schemas(self) -> None:
        """确认本 adapter import 的是 Dev-β merged 的 app.knowledge_base.reader。"""
        # 通过 _resolve_ctors() 懒导入;结果是真实 dataclass
        reader = MagicMock()
        reader.read.return_value = ReadResult(
            entries=[], meta=ReadMeta(project_id="p"), trace_id="t",
        )
        adapter = KBReaderAdapter(reader=reader)
        rr, ac = adapter._resolve_ctors()
        from app.knowledge_base.reader.schemas import (
            ApplicableContext as RealAC,
        )
        from app.knowledge_base.reader.schemas import (
            ReadRequest as RealRR,
        )
        assert rr is RealRR
        assert ac is RealAC


class TestKBReaderAdapterEndToEnd:
    """adapter → engine.decide 端到端。"""

    def test_TC_W03_AD10_adapter_feeds_engine(
        self, make_candidate, make_context,
    ) -> None:
        """adapter 产的 snippets 能被 engine.decide 消费产生 kb_boost。"""
        from app.main_loop.decision_engine import decide

        entry = KBEntry(
            id="kb-1", kind="pattern",
            applicable_context=ApplicableContext(tech_stack=["ast_safe"]),
            rerank_score=0.9,
            observed_count=16,
        )
        result = ReadResult(
            entries=[entry], meta=ReadMeta(project_id="p"), trace_id="t",
        )
        reader = MagicMock()
        reader.read.return_value = result
        adapter = KBReaderAdapter(reader=reader)
        snippets = adapter.fetch_snippets(
            project_id="p", session_id="s", tick_id="t", tags=("ast_safe",),
        )

        c = make_candidate(
            decision_type="invoke_skill",
            base_score=0.5,
            kb_tags=("ast_safe",),
            reason="adapter fed decision",
        )
        ctx = make_context(kb_snippets=tuple(snippets))
        action = decide([c], ctx)
        assert action.kb_boost > 0.0
        assert action.kb_degraded is False
        assert action.final_score > action.base_score
