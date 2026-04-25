"""IC-12 集成 fixtures · 真实 EightDimensionCollector + 8 维 scanner.

WP04 任务表 IC-12 = emit_metric (L1-07 supervisor 8 维度采集 → IC-09 audit).
"""
from __future__ import annotations

import pytest

from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.common.ids import ProjectId
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.state_cache import StateCache


@pytest.fixture
def project_id() -> str:
    return ProjectId.generate().value


@pytest.fixture
def frozen_clock() -> FrozenClock:
    return FrozenClock()


@pytest.fixture
def event_bus_stub() -> EventBusStub:
    return EventBusStub()


@pytest.fixture
def collector(
    frozen_clock: FrozenClock,
    event_bus_stub: EventBusStub,
) -> EightDimensionCollector:
    """组装真实 collector · 8 维 scanner + cache + bus."""
    scanner = DimScanner(
        l102=L102Stub(),
        l103=L103Stub(),
        l104=L104Stub(),
        event_bus=event_bus_stub,
    )
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    return EightDimensionCollector(
        scanner=scanner,
        cache=cache,
        event_bus=event_bus_stub,
        clock=frozen_clock,
    )


pytest_plugins: list[str] = []
