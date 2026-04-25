"""Scenario 01 · happy-path fixtures · 真实 WBSTopologyManager + L1-09 EventBus.

干净 project_id · 6 stage · pid 严格 ^[a-z0-9_-]{1,40}$ (L1-09 校验).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import DAGEdge, WorkPackage
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    """Scenario 01 happy-path 默认 pid · L1-09 严格 ^[a-z0-9_-]{1,40}$."""
    return "proj-acc01-happy"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 真实 event bus 根目录."""
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """L1-09 真实 EventBus · happy-path audit 闭环."""
    return EventBus(event_bus_root)


@pytest.fixture
def topo_manager(project_id: str) -> WBSTopologyManager:
    """L1-03 WBSTopologyManager · 干净初态 · parallelism=2."""
    return WBSTopologyManager(project_id=project_id, parallelism_limit=2)


@pytest.fixture
def make_wp(project_id: str):
    """工厂 · 标准 WP (4 要素齐 · effort ≤ 5)."""

    def _mk(
        wp_id: str,
        *,
        deps: list[str] | None = None,
        effort: float = 1.0,
        goal: str | None = None,
    ) -> WorkPackage:
        return WorkPackage(
            wp_id=wp_id,
            project_id=project_id,
            goal=goal or f"happy goal · {wp_id}",
            dod_expr_ref=f"dod-{wp_id}",
            deps=deps or [],
            effort_estimate=effort,
        )

    return _mk


@pytest.fixture
def emit_audit(real_event_bus: EventBus, project_id: str):
    """工厂 · 给 happy-path 模拟 stage 推进事件 · 直接 append L1-09."""

    def _emit(event_type: str, payload: dict, actor: str = "main_loop") -> str:
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            timestamp=datetime.now(UTC),
            payload=payload,
        )
        return real_event_bus.append(evt).event_id

    return _emit


# =============================================================================
# 14 verdict + 7 IC-XX (per-stage stub list, supports T9)
# =============================================================================

# 7 stages: S0 init / S1 chart / S2 plan / S3 tdd / S4 exec / S5 verify / S6 close
HAPPY_STAGES: tuple[str, ...] = ("S0", "S1", "S2", "S3", "S4", "S5", "S6")

# 14 verdict (DoD 7 · acceptance 7) - 每 stage 1 verdict (覆盖 1-14 编号)
HAPPY_VERDICTS: tuple[tuple[int, str, str], ...] = (
    (1, "S0", "init_clean_root"),
    (2, "S1", "charter_ready"),
    (3, "S1", "stakeholders_ready"),
    (4, "S2", "4_pieces_ready"),
    (5, "S2", "9_plans_ready"),
    (6, "S2", "togaf_ready"),
    (7, "S2", "wbs_ready"),
    (8, "S3", "tdd_blueprint_ready"),
    (9, "S4", "wp_chain_complete"),
    (10, "S4", "test_green"),
    (11, "S5", "verifier_pass"),
    (12, "S5", "audit_chain_intact"),
    (13, "S6", "delivery_bundled"),
    (14, "S6", "retro_ready"),
)
