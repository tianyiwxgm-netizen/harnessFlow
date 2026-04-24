"""L1-01 L2-02 · KB Reader Adapter.

L2-02 decision_engine 与 L1-06 KBReadService 之间的 **只读 adapter**。
将 `app.knowledge_base.reader.schemas.KBEntry` → 本包 `KBSnippet` 精简投影。

设计铁律(对齐 prd §9.6 #2):
    - KB 读失败 → adapter 返回空列表(不抛);
      让 engine.decide 走 kb_degraded=True 路径。
    - 不绑定具体的 reader 实现(依赖倒置):
      调用方传入 ``reader.read(req) -> ReadResult`` 的 duck-typed 对象。

使用:

    from app.knowledge_base.reader.service import KBReadService
    from app.knowledge_base.reader.schemas import ReadRequest, ApplicableContext

    svc = KBReadService(scope_checker=..., reranker=..., audit=..., repo=...)
    adapter = KBReaderAdapter(reader=svc)
    snippets = adapter.fetch_snippets(
        project_id="pid-xxx",
        session_id="sess-yyy",
        tick_id="tick-zzz",
        tags=("deepseek", "oss"),
        top_k=5,
    )
"""
from __future__ import annotations

from typing import Any, Protocol

from .schemas import KBSnippet


class _ReaderProtocol(Protocol):
    """KBReadService.read() 的 duck-typed 签名(避免强依赖)。"""

    def read(self, req: Any) -> Any:  # ReadResult-shaped
        ...


class KBReaderAdapter:
    """L2-02 → L1-06 只读 adapter。

    Attributes:
        _reader: 任何实现 `read(req) -> ReadResult` 的对象(典型:KBReadService)。
        _read_request_cls: ReadRequest 构造器(DI · 默认从 knowledge_base 懒导入)。
        _applicable_ctx_cls: ApplicableContext 构造器(DI)。
    """

    def __init__(
        self,
        reader: _ReaderProtocol,
        *,
        read_request_cls: Any = None,
        applicable_context_cls: Any = None,
    ) -> None:
        self._reader = reader
        self._read_request_cls = read_request_cls
        self._applicable_context_cls = applicable_context_cls

    def fetch_snippets(
        self,
        *,
        project_id: str,
        session_id: str,
        tick_id: str,
        trace_id: str | None = None,
        tags: tuple[str, ...] = (),
        top_k: int = 5,
        kind_filter: str | list[str] | None = None,
        route: str | None = None,
        timeout_ms: int = 1000,
    ) -> list[KBSnippet]:
        """按 tags 查询 KB · 返回 KBSnippet 列表。

        失败 / 异常 → 返回空列表(降级静默)。
        """
        try:
            ReadRequest, ApplicableContext = self._resolve_ctors()
            applicable_context = ApplicableContext(
                route=route,
                tech_stack=list(tags),
            )
            req = ReadRequest(
                trace_id=trace_id or f"trace-{tick_id}",
                project_id=project_id,
                session_id=session_id,
                applicable_context=applicable_context,
                kind=kind_filter,
                top_k=top_k,
                tick_id=tick_id,
                global_timeout_ms=timeout_ms,
            )
            result = self._reader.read(req)
        except Exception:
            return []

        entries = getattr(result, "entries", None)
        if not entries:
            return []

        snippets: list[KBSnippet] = []
        for entry in entries:
            snippets.append(_kb_entry_to_snippet(entry, fallback_tags=tags))
        return snippets

    # ---------- 内部 ----------

    def _resolve_ctors(self) -> tuple[Any, Any]:
        """懒导入 ReadRequest / ApplicableContext(避免强依赖)。"""
        rr = self._read_request_cls
        ac = self._applicable_context_cls
        if rr is None or ac is None:
            from app.knowledge_base.reader.schemas import (
                ApplicableContext as _AC,
            )
            from app.knowledge_base.reader.schemas import (
                ReadRequest as _RR,
            )
            if rr is None:
                rr = _RR
            if ac is None:
                ac = _AC
        return rr, ac


def _kb_entry_to_snippet(entry: Any, *, fallback_tags: tuple[str, ...]) -> KBSnippet:
    """KBEntry → KBSnippet。

    映射规则:
        - kind: 透传(pattern / trap / anti_pattern / ...)
        - tags: 优先用 entry.applicable_context.tech_stack;空则回退调用方 tags。
        - rerank_score / observed_count: 透传。
    """
    kind = getattr(entry, "kind", "pattern")
    rerank = float(getattr(entry, "rerank_score", 0.0) or 0.0)
    observed = int(getattr(entry, "observed_count", 1) or 1)

    tags: tuple[str, ...] = ()
    ac = getattr(entry, "applicable_context", None)
    if ac is not None:
        tech = getattr(ac, "tech_stack", None)
        if isinstance(tech, (list, tuple)) and tech:
            tags = tuple(str(t) for t in tech)
    if not tags:
        tags = fallback_tags

    return KBSnippet(
        kind=str(kind),
        tags=tags,
        rerank_score=rerank,
        observed_count=observed,
    )


__all__ = [
    "KBReaderAdapter",
]
