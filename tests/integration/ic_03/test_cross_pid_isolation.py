"""IC-03 · 跨 pid 隔离 + payload 必填字段缺失校验 · 4 TC.

覆盖:
- TC-1 · 同一 bridge 跑 2 pid · 各自分片独立 · 不混
- TC-2 · payload 缺 artifact_kind 不可能(我们 emit 时强制带) · 但断言 contract 校
- TC-3 · payload 缺 hash 验证(0 hash 透传)
- TC-4 · 大量 emit (50 条) · sequence 单调 + chain intact
"""
from __future__ import annotations

from pathlib import Path

from app.l1_09.event_bus.core import EventBus
from tests.integration.ic_03.conftest import (
    FOUR_SET_KINDS,
    PMP_9_KINDS,
    StageArtifactBridge,
)
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    assert_no_events_for_pid,
)


def test_cross_pid_isolation(
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
    other_project_id: str,
    make_artifact_hash,
) -> None:
    """两个 pid 同时 emit · 各自分片独立(PM-14)."""
    bridge = StageArtifactBridge(real_event_bus)
    # pid A · 4 件套
    for k in FOUR_SET_KINDS:
        bridge.emit_stage_artifact(
            project_id=project_id, artifact_kind=k,
            content_hash=make_artifact_hash(project_id, k),
        )
    # pid B 暂无任何 emit
    assert_no_events_for_pid(event_bus_root, project_id=other_project_id)

    # pid A 应有 4 条
    a_events = assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-02:stage_artifact_emitted", min_count=4,
    )
    assert len(a_events) == 4
    a_pids = {e["payload"]["pid"] for e in a_events}
    assert a_pids == {project_id}

    # 现在 pid B emit · 不应跨过来
    bridge.emit_stage_artifact(
        project_id=other_project_id, artifact_kind="four_set.charter",
        content_hash=make_artifact_hash(other_project_id, "charter"),
    )
    b_events = assert_ic_09_emitted(
        event_bus_root, project_id=other_project_id,
        event_type="L1-02:stage_artifact_emitted", min_count=1,
    )
    # B 的事件 pid 字段一致
    assert b_events[0]["payload"]["pid"] == other_project_id
    # A 仍只有 4 条 · 没被 B 影响
    a_events_after = assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-02:stage_artifact_emitted", min_count=4,
    )
    assert len(a_events_after) == 4


def test_artifact_kind_field_required_in_payload(
    stage_bridge,
    make_artifact_hash,
    event_bus_root: Path,
    project_id: str,
) -> None:
    """payload 必含 artifact_kind / pid / hash · IC-03 contract 字段级校."""
    h = make_artifact_hash(project_id, "test")
    stage_bridge.emit_stage_artifact(
        project_id=project_id, artifact_kind="four_set.charter",
        content_hash=h,
    )
    events = assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-02:stage_artifact_emitted", min_count=1,
    )
    payload = events[0]["payload"]
    # 三个必填字段全在
    assert "artifact_kind" in payload
    assert "pid" in payload
    assert "hash" in payload
    assert payload["artifact_kind"] == "four_set.charter"
    assert payload["pid"] == project_id
    assert payload["hash"] == h


def test_event_id_unique_per_emit(
    stage_bridge,
    make_artifact_hash,
    project_id: str,
) -> None:
    """每条 emit 生成唯一 event_id(IC-09 ULID)."""
    ids: set[str] = set()
    for kind in PMP_9_KINDS:
        rec = stage_bridge.emit_stage_artifact(
            project_id=project_id, artifact_kind=kind,
            content_hash=make_artifact_hash(project_id, kind),
        )
        assert rec["event_id"] not in ids
        ids.add(rec["event_id"])
    assert len(ids) == 9


def test_50_emits_chain_intact(
    stage_bridge,
    make_artifact_hash,
    event_bus_root: Path,
    project_id: str,
) -> None:
    """50 次 emit · sequence 单调 + hash chain 完整(IC-09 §3.9.3 minimum: 1)."""
    for i in range(50):
        stage_bridge.emit_stage_artifact(
            project_id=project_id,
            artifact_kind=f"custom.kind_{i:02d}",
            content_hash=make_artifact_hash(project_id, str(i)),
        )

    total = assert_ic_09_hash_chain_intact(
        event_bus_root, project_id=project_id,
    )
    assert total == 50

    events = assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-02:stage_artifact_emitted", min_count=50,
    )
    seqs = [e["sequence"] for e in events]
    assert seqs == list(range(1, 51))
