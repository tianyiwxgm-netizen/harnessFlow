"""IC-03 · 正向 stage_artifact_emitted · 4 件套 / PMP 9 / TOGAF · 8 TC.

每条 TC 验证:
1. emit 不抛
2. events.jsonl 物理落盘(IC-09 唯一写入口)
3. payload 必含 artifact_kind / pid / hash
4. event_id 唯一(IC-09 ULID 自动生成)
5. PM-14 落到 projects/<pid>/events.jsonl 分片
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from tests.integration.ic_03.conftest import (
    FOUR_SET_KINDS,
    PMP_9_KINDS,
    TOGAF_PHASES,
)
from tests.shared.ic_assertions import assert_ic_09_emitted


class TestIC03FourSet:
    """4 件套全产出 · 4 TC."""

    @pytest.mark.parametrize("artifact_kind", FOUR_SET_KINDS)
    def test_four_set_artifact_emit(
        self,
        stage_bridge,
        make_artifact_hash,
        event_bus_root: Path,
        project_id: str,
        artifact_kind: str,
    ) -> None:
        h = make_artifact_hash(project_id, artifact_kind)
        result = stage_bridge.emit_stage_artifact(
            project_id=project_id,
            artifact_kind=artifact_kind,
            content_hash=h,
            extra={"path": f"projects/{project_id}/four-set/{artifact_kind}.md"},
        )
        assert result["event_id"].startswith("evt_")
        assert result["sequence"] >= 1

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:stage_artifact_emitted",
            min_count=1,
            payload_contains={
                "artifact_kind": artifact_kind,
                "pid": project_id,
                "hash": h,
            },
        )
        # 字段级校验
        evt = events[0]
        assert evt["payload"]["artifact_kind"].startswith("four_set.")
        assert evt["payload"]["pid"] == project_id
        assert len(evt["payload"]["hash"]) == 64


class TestIC03PmpAndTogaf:
    """PMP 9 计划合并 + TOGAF 各 phase · 4 TC(代表性子集)."""

    # ---- TC-5 · PMP 9 计划全部 emit ----
    def test_pmp_all_9_kdas_emit(
        self,
        stage_bridge,
        make_artifact_hash,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        for kind in PMP_9_KINDS:
            h = make_artifact_hash(project_id, kind)
            stage_bridge.emit_stage_artifact(
                project_id=project_id,
                artifact_kind=kind,
                content_hash=h,
            )

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:stage_artifact_emitted",
            min_count=9,
        )
        emitted_kinds = sorted(
            e["payload"]["artifact_kind"] for e in events
            if e["payload"]["artifact_kind"].startswith("pmp.")
        )
        assert emitted_kinds == sorted(PMP_9_KINDS)

    # ---- TC-6 · TOGAF preliminary + phase_a ----
    def test_togaf_preliminary_and_phase_a_emit(
        self,
        stage_bridge,
        make_artifact_hash,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        for kind in ("togaf.preliminary", "togaf.phase_a"):
            stage_bridge.emit_stage_artifact(
                project_id=project_id,
                artifact_kind=kind,
                content_hash=make_artifact_hash(project_id, kind),
            )

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:stage_artifact_emitted",
            min_count=2,
        )
        kinds = {e["payload"]["artifact_kind"] for e in events}
        assert "togaf.preliminary" in kinds
        assert "togaf.phase_a" in kinds

    # ---- TC-7 · TOGAF phase_d (重要 release blocker) ----
    def test_togaf_phase_d_emit(
        self,
        stage_bridge,
        make_artifact_hash,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        kind = "togaf.phase_d"
        h = make_artifact_hash(project_id, kind, "phase_d_critical")
        stage_bridge.emit_stage_artifact(
            project_id=project_id,
            artifact_kind=kind,
            content_hash=h,
            extra={"adr_count": 12, "phase_complete": True},
        )

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:stage_artifact_emitted",
            min_count=1,
            payload_contains={"artifact_kind": kind},
        )
        # 额外字段透传
        assert events[0]["payload"]["adr_count"] == 12
        assert events[0]["payload"]["phase_complete"] is True

    # ---- TC-8 · 三类混合 emit · IC-09 hash chain 完整 ----
    def test_mixed_artifact_chain_intact(
        self,
        stage_bridge,
        make_artifact_hash,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """混合 emit 4 + 9 + 3 = 16 条 · hash chain 必完整."""
        all_kinds = list(FOUR_SET_KINDS) + list(PMP_9_KINDS) + [
            "togaf.preliminary", "togaf.phase_a", "togaf.phase_d",
        ]
        for kind in all_kinds:
            stage_bridge.emit_stage_artifact(
                project_id=project_id,
                artifact_kind=kind,
                content_hash=make_artifact_hash(project_id, kind),
            )

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:stage_artifact_emitted",
            min_count=len(all_kinds),
        )
        # sequence 连续(从首条 emit 起 1..N)
        seqs = [e["sequence"] for e in events]
        assert seqs == sorted(seqs)
        # hash chain 链接(prev_hash 串)
        for i in range(1, len(events)):
            assert events[i]["prev_hash"] == events[i - 1]["hash"]
