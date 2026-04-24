"""L2-05 · replay_from_jsonl + hash 链 · TC-013 + hash 补充.

§3.5 replay · §6.2 hash 链 · §9 replay 边界.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.main_loop.decision_audit import (
    AuditError,
    DecisionAuditRecorder,
    E_AUDIT_NO_PROJECT_ID,
    ReplayResult,
)


class TestL2_05_Replay:
    """§3.5 replay_from_jsonl()."""

    def test_TC_L101_L205_013_replay_rebuilds_reverse_index(
        self,
        make_recorder,
        mock_project_id: str,
        jsonl_fixture_file: Path,
    ) -> None:
        """TC-013 · replay 从 fixture 重建索引 + hash tip."""
        # jsonl 路径:<tmp>/projects/<pid>/audit/l1-01/2026-04-15.jsonl · parents[4] = <tmp>
        fresh = make_recorder(
            session_active_pid=mock_project_id,
            jsonl_root=jsonl_fixture_file.parents[4],
        )
        rr: ReplayResult = fresh.replay_from_jsonl(
            project_id=mock_project_id,
            from_date="2026-04-15",
            max_entries=100_000,
        )
        assert rr.replayed_count >= 3
        assert rr.hash_chain_valid is True
        assert rr.latest_hash and len(rr.latest_hash) == 64
        tip = fresh.get_hash_tip(project_id=mock_project_id)
        assert tip.hash == rr.latest_hash
        assert tip.sequence == rr.replayed_count

    def test_TC_L101_L205_013b_replay_from_query_hits_after_replay(
        self,
        make_recorder,
        mock_project_id: str,
        jsonl_fixture_file: Path,
    ) -> None:
        """TC-013b · replay 后 · query_by_tick 能命中 historical tick · source='index'."""
        fresh = make_recorder(
            session_active_pid=mock_project_id,
            jsonl_root=jsonl_fixture_file.parents[4],
        )
        fresh.replay_from_jsonl(project_id=mock_project_id, from_date="2026-04-15")
        r = fresh.query_by_tick(
            tick_id="tick-historical-001",
            project_id=mock_project_id,
            include_buffered=False,
        )
        assert r.count >= 1
        assert r.source in ("index", "jsonl_scan", "mixed")

    def test_TC_L101_L205_013c_replay_without_jsonl_root_returns_zero(
        self,
        make_recorder,
        mock_project_id: str,
    ) -> None:
        """TC-013c · 无 jsonl_root · replay 返回 replayed_count=0 · 不 raise."""
        fresh = make_recorder(session_active_pid=mock_project_id)
        rr = fresh.replay_from_jsonl(project_id=mock_project_id)
        assert rr.replayed_count == 0
        assert rr.latest_hash == "0" * 64

    def test_TC_L101_L205_013d_replay_without_project_id_raises(
        self,
        make_recorder,
    ) -> None:
        """TC-013d · project_id 缺失 · raise E_AUDIT_NO_PROJECT_ID."""
        fresh = make_recorder()
        with pytest.raises(AuditError) as exc:
            fresh.replay_from_jsonl(project_id="")
        assert exc.value.error_code == E_AUDIT_NO_PROJECT_ID


class TestL2_05_HashChain:
    """§6.2 hash 链 · compute_hash(prev + canonical(content)) · monotonic sequence."""

    def test_TC_L101_L205_H01_hash_chain_monotonic_across_flushes(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-H01 · 连续 flush · sequence 严格递增 · prev_hash = 上条 hash."""
        hashes = []
        seqs = []
        for batch in range(3):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-h-{batch}",
                reason=f"batch {batch}", evidence=[f"evt-{batch}"],
            ))
            fr = sut.flush_buffer(force=True, reason="tick_boundary")
            hashes.append(fr.last_hash)
            tip = sut.get_hash_tip(project_id=mock_project_id)
            seqs.append(tip.sequence)
        assert seqs == [1, 2, 3]
        # hash 链不等(单调 · 各不同)
        assert len(set(hashes)) == 3

    def test_TC_L101_L205_H02_hash_chain_per_project_independent(
        self,
        make_recorder,
        make_audit_cmd,
    ) -> None:
        """TC-H02 · 每 project_id 独立 hash tip · 互不影响(§D-05c per-project)."""
        fresh = make_recorder()
        pid_a = "pid-aaaaaaaa"
        pid_b = "pid-bbbbbbbb"
        fresh.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=pid_a, linked_tick="tick-a-1",
            reason="project A", evidence=["evt-a-1"],
        ))
        fresh.flush_buffer(force=True, reason="tick_boundary")
        tip_a = fresh.get_hash_tip(project_id=pid_a)
        tip_b_before = fresh.get_hash_tip(project_id=pid_b)
        fresh.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=pid_b, linked_tick="tick-b-1",
            reason="project B", evidence=["evt-b-1"],
        ))
        fresh.flush_buffer(force=True, reason="tick_boundary")
        tip_b = fresh.get_hash_tip(project_id=pid_b)
        assert tip_a.sequence == 1
        assert tip_b_before.sequence == 0
        assert tip_b.sequence == 1
        assert tip_a.hash != tip_b.hash

    def test_TC_L101_L205_H03_flush_writes_prev_hash_and_hash(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus,
        make_audit_cmd,
    ) -> None:
        """TC-H03 · IC-09 kwargs 含 prev_hash / hash / sequence 字段."""
        for i in range(2):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-h3-{i}",
                reason=f"h3 {i}", evidence=[f"evt-{i}"],
            ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        calls = mock_event_bus.append_event.call_args_list
        assert len(calls) == 2
        # 第 1 条 prev = GENESIS(0*64)
        assert calls[0].kwargs["prev_hash"] == "0" * 64
        # 第 2 条 prev = 第 1 条 hash
        assert calls[1].kwargs["prev_hash"] == calls[0].kwargs["hash"]
        assert calls[0].kwargs["sequence"] == 1
        assert calls[1].kwargs["sequence"] == 2
        # event_type 必以 L1-01: 前缀
        for c in calls:
            assert c.kwargs["event_type"].startswith("L1-01:")
            assert c.kwargs["project_id"] == mock_project_id
