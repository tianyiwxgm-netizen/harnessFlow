"""L1-01 L2-02 · Decision Engine (AST 白名单决策).

对齐 docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md §3 + §11.
本 package 聚焦 WP03 范围:AST 白名单决策 + KB boost + history weight + 降级。

公共入口:
    from app.main_loop.decision_engine import decide, DecisionContext

安全红线(同 dod_compiler):
    - 禁 eval / exec / __import__
    - 禁 ast.Import / ast.ImportFrom
    - 禁 ast.Attribute 作为 Call.func
    - 禁 dunder name (__*__)
    - 禁 Lambda / FunctionDef / ClassDef
    - 禁 Comprehensions / Loops / Try / Assign
    - AST 深度 + 节点数上限
"""
from __future__ import annotations

from .engine import decide
from .kb_reader_adapter import KBReaderAdapter
from .schemas import (
    Candidate,
    ChosenAction,
    DecisionContext,
    HistoryEntry,
    KBSnippet,
)

__all__ = [
    "Candidate",
    "ChosenAction",
    "DecisionContext",
    "HistoryEntry",
    "KBReaderAdapter",
    "KBSnippet",
    "decide",
]
