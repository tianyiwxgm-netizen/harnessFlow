"""D2 · 篡改检测(中间篡改一条) · 3 TC.

audit_chain_verify 应检测到任意位置的事件被篡改 · state ∈ {CORRUPT, PARTIAL}.
篡改方式:
    - payload 改值不重算 hash
    - hash 字段直接覆写
    - prev_hash 字段直接覆写
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.crash_safety.integrity_checker import verify_integrity
from app.l1_09.crash_safety.schemas import IntegrityMethod, IntegrityState
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


def _write_events(bus: EventBus, project_id: str, n: int) -> None:
    for i in range(n):
        evt = Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={"i": i, "verdict": "PASS"},
            timestamp=datetime.now(UTC),
        )
        bus.append(evt)


def _read_jsonl_lines(path: Path) -> list[bytes]:
    return [l for l in path.read_bytes().splitlines() if l.strip()]


def _write_jsonl_lines(path: Path, lines: list[bytes]) -> None:
    path.write_bytes(b"\n".join(lines) + b"\n")


class TestD2TamperDetection:
    """D2 · audit-chain 篡改检测 · 3 TC."""

    def test_d2_01_payload_tamper_detected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D2.1: 中段事件 payload 改 · verify 报 CORRUPT/PARTIAL · failure_range 指向篡改位."""
        _write_events(real_event_bus, project_id, 5)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        # 篡改第 2 条(index 1) 的 payload
        lines = _read_jsonl_lines(events_path)
        body = json.loads(lines[1].decode("utf-8"))
        body["payload"] = {"i": 999, "verdict": "FAIL_L4"}  # 改值不动 hash
        lines[1] = json.dumps(body, sort_keys=True).encode("utf-8")
        _write_jsonl_lines(events_path, lines)
        # verify
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state in (IntegrityState.CORRUPT, IntegrityState.PARTIAL)
        # failure_range 第一坏 seq
        assert report.failure_range is not None
        assert report.failure_range[0] == 1

    def test_d2_02_hash_field_overwrite_detected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D2.2: 中段事件直接覆写 hash 字段 · verify 立即检测."""
        _write_events(real_event_bus, project_id, 4)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        lines = _read_jsonl_lines(events_path)
        body = json.loads(lines[2].decode("utf-8"))
        body["hash"] = "0" * 64  # 写假 hash
        lines[2] = json.dumps(body, sort_keys=True).encode("utf-8")
        _write_jsonl_lines(events_path, lines)
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state in (IntegrityState.CORRUPT, IntegrityState.PARTIAL)
        # 第 3 条(index 2) bad
        assert report.failure_range is not None
        assert report.failure_range[0] == 2

    def test_d2_03_prev_hash_chain_break_detected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D2.3: 篡改 prev_hash · verify 报错 first_bad_seq 在篡改位."""
        _write_events(real_event_bus, project_id, 5)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        lines = _read_jsonl_lines(events_path)
        body = json.loads(lines[3].decode("utf-8"))
        body["prev_hash"] = "f" * 64  # 假 prev_hash · 不再链
        lines[3] = json.dumps(body, sort_keys=True).encode("utf-8")
        _write_jsonl_lines(events_path, lines)
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state in (IntegrityState.CORRUPT, IntegrityState.PARTIAL)
        # 第 4 条(index 3) prev_hash 不匹配 · 链断
        assert report.failure_range is not None
        assert report.failure_range[0] == 3
