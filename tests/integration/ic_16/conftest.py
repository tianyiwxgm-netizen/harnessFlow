"""IC-16 集成 fixtures · 真实 TaskChainExecutor + 配置化 ic_resolver.

WP04 任务表 IC-16 = task_chain_step (main-2 L1-01 / L2-04 任务链推进).
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.main_loop.decision_engine.schemas import ChosenAction
from app.main_loop.task_chain.executor import (
    ExecutorConfig,
    TaskChainExecutor,
    build_noop_resolver,
)
from app.main_loop.task_chain.schemas import RouteDecision
from app.main_loop.task_chain.task_spawner import ICCallable


@pytest.fixture
def project_id() -> str:
    return "proj-ic16"


def make_action(
    dt: str,
    params: dict[str, Any] | None = None,
    *,
    score: float = 0.8,
) -> ChosenAction:
    return ChosenAction(
        decision_type=dt,
        decision_params=params or {},
        final_score=score,
        kb_boost=0.0,
        history_weight=0.0,
        base_score=score,
        reason="synthesized chosen action for ic-16 integration tests",
    )


def make_echo_config(reply: dict[str, Any] | None = None) -> ExecutorConfig:
    """ic_resolver 永远返预置 reply."""
    return ExecutorConfig(ic_resolver=build_noop_resolver(reply or {"ok": True}))


def make_raising_config(exc: Exception) -> ExecutorConfig:
    """ic_resolver 抛异常 (模拟下游 L1 失败)."""
    def _resolver(_r: RouteDecision) -> ICCallable:
        async def _call(_route: RouteDecision) -> dict:
            raise exc
        return _call

    return ExecutorConfig(ic_resolver=_resolver)


@pytest.fixture
def executor():
    """默认 echo executor."""
    return TaskChainExecutor(config=make_echo_config())


@pytest.fixture
def executor_factory():
    """工厂 · 按 config 造 executor."""

    def _make(config: ExecutorConfig) -> TaskChainExecutor:
        return TaskChainExecutor(config=config)

    return _make


# 暴露 helper · 测试 import
__all__ = [
    "make_action",
    "make_echo_config",
    "make_raising_config",
]
