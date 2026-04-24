"""IC-09 · 10 L1 生产方 × 各 1 TC · 正向 append_event.

每个 L1 都有权限写 IC-09 · L1-09 EventBus 通过 `type` 前缀白名单（^L1-(01..10):...$）
放行合法事件. 本测试直接构造每个 L1 典型 event · 真 bus 写入 · 验证:

    1. AppendEventResult.persisted is True
    2. events.jsonl 物理落盘
    3. sequence 递增
    4. hash-chain 正确链接
    5. project_id (PM-14 根字段) 保留

10 L1 映射:
    L1-01 main_loop    · main-2 WP01-07(decision/tick/state/task/supervisor)
    L1-02 stage_gate   · Dev-δ lifecycle
    L1-03 wbs-wp       · Dev-ε
    L1-04 quality_loop · main-1 WP01-09(verifier/rollback_router)
    L1-05 skill-dispatch · Dev-γ
    L1-06 knowledge_base · Dev-β
    L1-07 supervisor   · Dev-ζ
    L1-08 multimodal   · Dev-η
    L1-09 event_bus / resilience · Dev-α
    L1-10 UI / bff     · Dev-θ
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(raw.decode("utf-8"))
        for raw in path.read_bytes().splitlines()
        if raw.strip()
    ]


# 10 L1 × 典型 event_type + actor 映射 · 作 parametrize 数据源
L1_PRODUCERS = [
    # (L1 id, event_type, actor, payload 示例)
    ("L1-01", "L1-01:decision_made", "main_loop",
     {"decision_id": "d-1", "action": "transition"}),
    ("L1-02", "L1-02:state_transitioned", "main_loop",
     {"transition_id": "trans-0001", "from_state": "PLANNING",
      "to_state": "TDD_PLANNING"}),
    ("L1-03", "L1-03:wp_scheduled", "executor",
     {"wp_id": "wp-1", "seq": 1}),
    ("L1-04", "L1-04:verifier_report_issued", "verifier",
     {"verifier_report_id": "vr-1", "verdict": "PASS"}),
    ("L1-05", "L1-05:skill_invocation_started", "executor",
     {"invocation_id": "inv-1", "capability": "write_test"}),
    ("L1-06", "L1-06:kb_read_completed", "main_loop",
     {"kind": "plan_doc", "scope": "project"}),
    ("L1-07", "L1-07:supervisor_tick_done", "supervisor",
     {"tick_id": "tk-1"}),
    ("L1-08", "L1-08:multimodal_artifact_registered", "executor",
     {"artifact_id": "art-1", "kind": "image"}),
    ("L1-09", "L1-09:meta_event_persisted", "audit_mirror",
     {"self_event_id": "evt_abc123"}),
    ("L1-10", "L1-10:ui_action_recorded", "ui",
     {"user": "admin", "action": "click"}),
]


@pytest.mark.parametrize("l1_id,event_type,actor,payload", L1_PRODUCERS)
def test_l1_producer_can_append_ic09(
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
    l1_id: str,
    event_type: str,
    actor: str,
    payload: dict,
) -> None:
    """每个 L1 都能通过合法 type 前缀写 IC-09 · 真 bus 持久化."""
    evt = Event(
        project_id=project_id,
        type=event_type,
        actor=actor,
        payload=dict(payload),
        timestamp=datetime.now(UTC),
    )
    result = real_event_bus.append(evt)
    # IC-09 契约硬校 · §3.9.3
    assert result.persisted is True
    assert result.sequence >= 1
    assert len(result.hash) == 64
    assert result.event_id.startswith("evt_")

    # 物理落盘 · shard 按 project_id
    events_path = event_bus_root / "projects" / project_id / "events.jsonl"
    raw_events = _read_jsonl(events_path)
    assert len(raw_events) == 1
    persisted = raw_events[0]
    assert persisted["type"] == event_type
    assert persisted["actor"] == actor
    assert persisted["project_id"] == project_id
    assert persisted["payload"] == payload


def test_10_l1_producers_share_single_bus_hash_chain(
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
) -> None:
    """10 L1 producers 写同一个 bus · hash chain 必完整 · sequence 连续."""
    for l1_id, event_type, actor, payload in L1_PRODUCERS:
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            payload=dict(payload),
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)

    events_path = event_bus_root / "projects" / project_id / "events.jsonl"
    persisted = _read_jsonl(events_path)
    assert len(persisted) == 10

    # sequence 1..10 连续
    seqs = [e["sequence"] for e in persisted]
    assert seqs == list(range(1, 11))

    # hash chain 链接无断
    for i in range(1, 10):
        assert persisted[i]["prev_hash"] == persisted[i - 1]["hash"]

    # 10 L1 前缀全命中
    prefixes = [e["type"].split(":")[0] for e in persisted]
    assert prefixes == [
        "L1-01", "L1-02", "L1-03", "L1-04", "L1-05",
        "L1-06", "L1-07", "L1-08", "L1-09", "L1-10",
    ]
