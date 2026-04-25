"""D4 · cross-pid verify reject · 2 TC.

audit_chain_verify 是按 pid 分片做的 · 跨 pid 不能"借用"另一 pid 的 events 来 verify.
本测确认:
    - 各 pid 各自的 events.jsonl 物理隔离 verify
    - 给 pid_b 路径但实际被 pid_a 写入 → 是 PM-14 反模式 · verify 仍按物理路径 verify
      (verify_integrity 不知 pid · 但路径分片确保不可能误用)
"""
from __future__ import annotations

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
            payload={"i": i},
            timestamp=datetime.now(UTC),
        )
        bus.append(evt)


class TestD4CrossPidVerifyReject:
    """D4 · 跨 pid verify 隔离 · 2 TC."""

    def test_d4_01_each_pid_has_independent_chain_verify(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
    ) -> None:
        """D4.1: A/B 各自写事件 · 各自 verify · 各自的 chain 互独立.

        PM-14 切片下 audit_chain 各自独立 · A 链坏不影响 B 链 verify.
        """
        pid_a = "proj-d4-a"
        pid_b = "proj-d4-b"
        _write_events(real_event_bus, pid_a, 3)
        _write_events(real_event_bus, pid_b, 4)
        # 各自 verify · OK
        path_a = event_bus_root / "projects" / pid_a / "events.jsonl"
        path_b = event_bus_root / "projects" / pid_b / "events.jsonl"
        report_a = verify_integrity(path_a, method=IntegrityMethod.HASH_CHAIN)
        report_b = verify_integrity(path_b, method=IntegrityMethod.HASH_CHAIN)
        assert report_a.state == IntegrityState.OK
        assert report_b.state == IntegrityState.OK
        assert report_a.total_items == 3
        assert report_b.total_items == 4
        # 篡改 A · 不影响 B
        # 直接读 A · 改一条 hash
        import json
        lines = path_a.read_bytes().splitlines()
        body = json.loads(lines[1].decode("utf-8"))
        body["hash"] = "0" * 64
        lines[1] = json.dumps(body, sort_keys=True).encode("utf-8")
        path_a.write_bytes(b"\n".join(lines) + b"\n")
        # A 现在坏 · B 仍 OK
        report_a2 = verify_integrity(path_a, method=IntegrityMethod.HASH_CHAIN)
        report_b2 = verify_integrity(path_b, method=IntegrityMethod.HASH_CHAIN)
        assert report_a2.state in (IntegrityState.CORRUPT, IntegrityState.PARTIAL)
        # B 不受影响
        assert report_b2.state == IntegrityState.OK
        assert report_b2.total_items == 4

    def test_d4_02_pid_path_must_match_pid_in_events(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
    ) -> None:
        """D4.2: 物理路径 PM-14 切片确保 pid 一致 · events 内 project_id 字段必 = 路径中 pid.

        反模式: 把 pid_b 的事件写到 pid_a 的物理路径下(手工伪造) · audit-trail 跨 pid 反向链
        无法成立 · pid 与路径不一致即为审计违规.
        """
        pid_a = "proj-d4-real"
        pid_b = "proj-d4-fake"
        _write_events(real_event_bus, pid_a, 2)
        # 验证: pid_a 路径下所有 event 的 project_id 字段 = pid_a
        import json
        path_a = event_bus_root / "projects" / pid_a / "events.jsonl"
        for raw in path_a.read_bytes().splitlines():
            if raw.strip():
                body = json.loads(raw.decode("utf-8"))
                assert body["project_id"] == pid_a, (
                    f"PM-14 反模式: 路径 {pid_a} 下 event project_id={body['project_id']}"
                )
        # 反向: 真给 pid_b 写一条 · 物理上路径就是 pid_b 的目录
        _write_events(real_event_bus, pid_b, 1)
        path_b = event_bus_root / "projects" / pid_b / "events.jsonl"
        # b 路径下的 events 必带 pid_b
        for raw in path_b.read_bytes().splitlines():
            if raw.strip():
                body = json.loads(raw.decode("utf-8"))
                assert body["project_id"] == pid_b
        # 各自 verify 各自 OK
        report_a = verify_integrity(path_a, method=IntegrityMethod.HASH_CHAIN)
        report_b = verify_integrity(path_b, method=IntegrityMethod.HASH_CHAIN)
        assert report_a.state == IntegrityState.OK
        assert report_b.state == IntegrityState.OK
