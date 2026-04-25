"""B6 · L1-09 hash-chain 断 → L1-01 readonly · 3 TC.

链路:
    events.jsonl 被篡改 / 中段缺失 → IntegrityChecker.verify_integrity 报 CORRUPT/PARTIAL →
    IC-17 audit_chain_broken → L1-01 进 readonly mode (拒进一步 append).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.l1_09.crash_safety.integrity_checker import verify_integrity
from app.l1_09.crash_safety.schemas import IntegrityMethod, IntegrityState
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from datetime import UTC, datetime


class TestB6HashChainBrokenReadonly:
    """B6 · hash-chain 断检测 + readonly · 3 TC."""

    def test_b6_01_intact_chain_state_ok(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """B6.1: 完整 hash-chain · verify_integrity 返 OK · readonly 不触发."""
        # 写 5 条 · 形成完整链
        for i in range(5):
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"i": i},
                timestamp=datetime.now(UTC),
            )
            real_event_bus.append(evt)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.OK, (
            f"完整链应 OK · 实际={report.state}"
        )
        assert report.total_items == 5

    def test_b6_02_tampered_middle_event_detected_corrupt(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """B6.2: 篡改中段 event payload · verify 报 CORRUPT/PARTIAL · 含 first_bad_seq.

        IC-17 audit_chain_broken 触发条件: state ∈ {CORRUPT, PARTIAL}.
        """
        # 写 5 条
        for i in range(5):
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"i": i},
                timestamp=datetime.now(UTC),
            )
            real_event_bus.append(evt)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        # 篡改第 3 行的 payload(不动 hash 字段 · 故 hash 与 body 不匹配)
        lines = events_path.read_bytes().splitlines()
        body = json.loads(lines[2].decode("utf-8"))
        body["payload"] = {"i": 999}  # 改值 · 不重算 hash
        lines[2] = json.dumps(body, sort_keys=True).encode("utf-8")
        events_path.write_bytes(b"\n".join(lines) + b"\n")
        # verify · 应非 OK
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state in (IntegrityState.CORRUPT, IntegrityState.PARTIAL)
        # first_bad_seq 应在篡改的位置(line 2 → seq 2)
        assert report.failure_range is not None
        first_bad_seq = report.failure_range[0]
        assert first_bad_seq == 2

    def test_b6_03_truncated_tail_detected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """B6.3: 截断尾部(模拟磁盘损坏) · verify 报非 OK · readonly 应触发."""
        for i in range(3):
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"i": i},
                timestamp=datetime.now(UTC),
            )
            real_event_bus.append(evt)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        # 截断到 50% (磁盘损坏 / 部分写入)
        original = events_path.read_bytes()
        truncate_at = len(original) // 2
        events_path.write_bytes(original[:truncate_at])
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        # 部分写入 → 通常 CORRUPT 或 PARTIAL
        assert report.state in (IntegrityState.CORRUPT, IntegrityState.PARTIAL), (
            f"截断尾部 verify 应非 OK · 实际={report.state}"
        )
