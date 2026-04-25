"""IC-03 集成 fixtures · 真实 L1-09 EventBus + stage_artifact emit 直接通道.

铁律:
- 真实 L1-09 EventBus(IC-09 唯一写入口) · events.jsonl 落盘
- emit 走 EventBusBridge · 把 stage producer 的
  `append_event(project_id, event_type, payload)` 适配到 L1-09 Event schema
- artifact emit 用统一 type=`L1-02:stage_artifact_emitted` · payload 含 artifact_kind
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


@pytest.fixture
def project_id() -> str:
    return "proj-ic03"


@pytest.fixture
def other_project_id() -> str:
    return "proj-ic03-other"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    return tmp_path / "bus_root"


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    return EventBus(event_bus_root)


class StageArtifactBridge:
    """L1-02 stage_artifact_emitted 桥 · 给 producer-style 直接 emit.

    模拟 L1-02/L2-02 在 stage 产物落盘后调用 IC-03 emit 的契约:
        bridge.emit_stage_artifact(
            project_id=pid,
            artifact_kind="four_set.charter",
            content_hash="abc...",
            extra={"path": "..."},
        )
    """

    EVENT_TYPE = "L1-02:stage_artifact_emitted"

    def __init__(self, real_bus: EventBus) -> None:
        self._real = real_bus
        self._emitted: list[dict[str, Any]] = []

    def emit_stage_artifact(
        self,
        *,
        project_id: str,
        artifact_kind: str,
        content_hash: str,
        actor: str = "main_loop",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """emit 一条 IC-03 stage_artifact_emitted 事件 · 真实落盘 IC-09.

        Returns:
            落盘后 AppendEventResult 字段(event_id/sequence/hash/...)
        """
        payload = {
            "artifact_kind": artifact_kind,
            "pid": project_id,
            "hash": content_hash,
        }
        if extra:
            payload.update(extra)

        evt = Event(
            project_id=project_id,
            type=self.EVENT_TYPE,
            actor=actor,
            payload=payload,
            timestamp=datetime.now(UTC),
        )
        result = self._real.append(evt)
        # payload 里补 event_id 字段(契约要求 payload 里也含)
        record = {
            "event_id": result.event_id,
            "sequence": result.sequence,
            "artifact_kind": artifact_kind,
            "pid": project_id,
            "hash": content_hash,
        }
        self._emitted.append(record)
        return record

    @property
    def emitted(self) -> list[dict[str, Any]]:
        return list(self._emitted)


@pytest.fixture
def stage_bridge(real_event_bus: EventBus) -> StageArtifactBridge:
    return StageArtifactBridge(real_event_bus)


@pytest.fixture
def make_artifact_hash():
    """工厂: 给定 stage 名 / kind 生成稳定 sha256."""
    def _mk(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(p.encode("utf-8"))
        return h.hexdigest()
    return _mk


# ---------- 已知 artifact kind 集合 (供 parametrize) ----------

FOUR_SET_KINDS = (
    "four_set.charter",
    "four_set.plan",
    "four_set.requirements",
    "four_set.team",
)

PMP_9_KINDS = tuple(
    f"pmp.{kda}" for kda in (
        "integration", "scope", "schedule", "cost", "quality",
        "resource", "communication", "risk", "procurement",
    )
)

TOGAF_PHASES = (
    "togaf.preliminary",
    "togaf.phase_a",
    "togaf.phase_b",
    "togaf.phase_c_data",
    "togaf.phase_c_application",
    "togaf.phase_d",
    "togaf.phase_e",
    "togaf.phase_f",
    "togaf.phase_g",
    "togaf.phase_h",
)
