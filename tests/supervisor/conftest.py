"""supervisor root conftest. 共用 fixtures：frozen_clock / pid。"""
from __future__ import annotations

import pytest

from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.ids import ProjectId


@pytest.fixture
def frozen_clock() -> FrozenClock:
    return FrozenClock()


@pytest.fixture
def pid() -> ProjectId:
    return ProjectId.generate()
