"""L1-01 L2-05 决策审计记录器 · 测试 fixtures.

对齐 TDD(3-2 L2-05-tests.md §7):
    - mock_project_id · PM-14 pid-{uuid} 合法
    - mock_event_bus · L1-09 事件总线 stub · append_event / get_last_hash / query
    - mock_l2_01_client · halt_signal 回调
    - mock_l1_07_client · HASH_BROKEN 告警
    - make_audit_cmd · AuditCommand 工厂
    - jsonl_fixture_file / pre_populated_jsonl_dir · replay 用
    - real_event_bus_stub · e2e 半真实
    - make_recorder · 参数化工厂
    - corrupted_jsonl_dir / large_jsonl_dir · 边界 case
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from app.main_loop.decision_audit.recorder import DecisionAuditRecorder
from app.main_loop.decision_audit.schemas import AuditCommand


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_project_id() -> str:
    """PM-14 · 合法 pid-{uuid} · 每测试独立."""
    return f"pid-{uuid.uuid4()}"


# ---------------------------------------------------------------------------
# L1-09 event bus stub
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """L1-09 事件总线 stub · append_event / get_last_hash / query.

    TDD 用 `mock_event_bus.append_event.call_count / call_args_list` 断言.
    本 stub 模拟 sequence + hash 自增 · 并维持 last_hash 状态.
    """
    bus = MagicMock(name="L1-09-event-bus")
    counter = {"seq": 0, "last_hash": "0" * 64}

    def _append(**kwargs: Any) -> dict[str, Any]:
        counter["seq"] += 1
        # 若调用方传了 hash · 尊重之(用于 hash chain 测试)· 否则自动推进
        new_hash = kwargs.get("hash")
        if not new_hash:
            new_hash = hashlib.sha256(
                (counter["last_hash"] + json.dumps(kwargs.get("payload", {}),
                                                   sort_keys=True)).encode()
            ).hexdigest()
        counter["last_hash"] = new_hash
        return {
            "event_id": f"evt-{uuid.uuid4()}",
            "sequence": counter["seq"],
            "hash": new_hash,
            "persisted": True,
        }

    bus.append_event = MagicMock(side_effect=_append)
    bus.get_last_hash = MagicMock(side_effect=lambda project_id: counter["last_hash"])
    bus.query = MagicMock(return_value=[])
    return bus


# ---------------------------------------------------------------------------
# L2-01 / L1-07 clients
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_l2_01_client() -> MagicMock:
    """L2-01 Tick 调度器 stub · on_halt_signal 回调断言."""
    client = MagicMock(name="L2-01-tick-scheduler")
    client.on_halt_signal = MagicMock(return_value={"halted": True})
    return client


@pytest.fixture
def mock_l1_07_client() -> MagicMock:
    """L1-07 Supervisor stub · alert 回调断言."""
    client = MagicMock(name="L1-07-supervisor")
    client.alert = MagicMock(return_value={"alert_id": f"alert-{uuid.uuid4()}"})
    return client


# ---------------------------------------------------------------------------
# SUT
# ---------------------------------------------------------------------------


@pytest.fixture
def sut(
    mock_project_id: str,
    mock_event_bus: MagicMock,
    mock_l2_01_client: MagicMock,
    mock_l1_07_client: MagicMock,
) -> DecisionAuditRecorder:
    """默认 SUT · buffer=64 · reason_min=1 · 供 unit/integration 复用."""
    return DecisionAuditRecorder(
        session_active_pid=mock_project_id,
        event_bus=mock_event_bus,
        l2_01_client=mock_l2_01_client,
        l1_07_client=mock_l1_07_client,
        buffer_max=64,
        reason_min_length=1,
        query_timeout_ms=100,
        replay_timeout_ms=30_000,
    )


@pytest.fixture
def make_recorder(
    mock_event_bus: MagicMock,
    mock_l2_01_client: MagicMock,
    mock_l1_07_client: MagicMock,
) -> Callable[..., DecisionAuditRecorder]:
    """工厂 · 注入参数自定义(session_active_pid / jsonl_root / buffer_max / ...)."""

    def _factory(**overrides: Any) -> DecisionAuditRecorder:
        kwargs: dict[str, Any] = dict(
            session_active_pid=overrides.pop("session_active_pid", f"pid-{uuid.uuid4()}"),
            event_bus=overrides.pop("event_bus", mock_event_bus),
            l2_01_client=overrides.pop("l2_01_client", mock_l2_01_client),
            l1_07_client=overrides.pop("l1_07_client", mock_l1_07_client),
            buffer_max=overrides.pop("buffer_max", 64),
            reason_min_length=overrides.pop("reason_min_length", 1),
            query_timeout_ms=overrides.pop("query_timeout_ms", 100),
            replay_timeout_ms=overrides.pop("replay_timeout_ms", 30_000),
        )
        for k, v in overrides.items():
            kwargs[k] = v
        return DecisionAuditRecorder(**kwargs)

    return _factory


# ---------------------------------------------------------------------------
# AuditCommand factory
# ---------------------------------------------------------------------------


@pytest.fixture
def make_audit_cmd() -> Callable[..., AuditCommand]:
    """AuditCommand 工厂 · 覆盖默认字段."""

    def _factory(**overrides: Any) -> AuditCommand:
        base: dict[str, Any] = dict(
            source_ic="IC-L2-05",
            actor={"l1": "L1-01", "l2": "L2-01"},
            action="tick_scheduled",
            project_id="pid-default",
            reason="default reason (>=1 char)",
            evidence=[],
            linked_tick=None,
            linked_decision=None,
            linked_chain=None,
            linked_warn=None,
            payload={},
            ts=f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            idempotency_key=None,
        )
        base.update(overrides)
        return AuditCommand(**base)

    return _factory


# ---------------------------------------------------------------------------
# jsonl fixtures · replay 用
# ---------------------------------------------------------------------------


def _write_jsonl(
    path: Path,
    project_id: str,
    count: int,
    date_label: str = "2026-04-15",
    prev: str = "0" * 64,
    corrupt_at: int | None = None,
) -> Path:
    """内部工具 · 写 count 条 jsonl 到 `path/audit/l1-01/<date>.jsonl`.

    corrupt_at · 若设 · 在该 index 处故意写错 hash(模拟链断).
    """
    audit_root = path / "projects" / project_id / "audit" / "l1-01"
    audit_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = audit_root / f"{date_label}.jsonl"
    cur = prev
    lines: list[str] = []
    for i in range(count):
        tick_id = f"tick-historical-{i:03d}"
        payload = {"tick_id": tick_id, "action": "tick_scheduled"}
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256((cur + content).encode()).hexdigest()
        stored_h = h if corrupt_at != i else ("0" * 64)
        rec = {
            "event_id": f"evt-hist-{i:03d}",
            "event_type": "L1-01:tick_scheduled",
            "project_id": project_id,
            "payload": payload,
            "action": "tick_scheduled",
            "source_ic": "IC-L2-05",
            "actor": {"l1": "L1-01", "l2": "L2-01"},
            "reason": f"historical entry {i}",
            "evidence": [f"evt-src-{i}"],
            "linked_tick": tick_id,
            "prev_hash": cur,
            "hash": stored_h,
            "sequence": i + 1,
            "ts": f"{date_label}T00:00:00Z",
        }
        lines.append(json.dumps(rec))
        cur = h
    jsonl_path.write_text("\n".join(lines) + "\n")
    return jsonl_path


@pytest.fixture
def jsonl_fixture_file(tmp_path: Path, mock_project_id: str) -> Path:
    """3 条合法 hash 链 jsonl · 返 jsonl 路径."""
    return _write_jsonl(tmp_path, mock_project_id, count=3, date_label="2026-04-15")


@pytest.fixture
def pre_populated_jsonl_dir(tmp_path: Path, mock_project_id: str) -> Path:
    """10 条合法 hash 链 jsonl · 返 root 目录(供 make_recorder 注 jsonl_root)."""
    _write_jsonl(tmp_path, mock_project_id, count=10, date_label="2026-04-20")
    return tmp_path


@pytest.fixture
def corrupted_jsonl_dir(tmp_path: Path, mock_project_id: str) -> Path:
    """5 条 jsonl 其中第 3 条 hash 故意坏 · 返 root."""
    _write_jsonl(tmp_path, mock_project_id, count=5, date_label="2026-04-15", corrupt_at=2)
    return tmp_path


@pytest.fixture
def large_jsonl_dir(tmp_path: Path, mock_project_id: str) -> Path:
    """100K 条 jsonl 模拟超时场景 · 为速度取 2_000 条足够让 replay_timeout_ms 生效."""
    _write_jsonl(tmp_path, mock_project_id, count=2_000, date_label="2026-04-01")
    return tmp_path


# ---------------------------------------------------------------------------
# real_event_bus_stub · e2e 半真实
# ---------------------------------------------------------------------------


@pytest.fixture
def real_event_bus_stub(tmp_path: Path) -> Any:
    """半真实 event_bus · 内存存储 · 按 project_id 分组查询 · 用于 e2e."""

    class _Event:
        def __init__(self, **kw: Any) -> None:
            self.__dict__.update(kw)

    class _Stub:
        def __init__(self) -> None:
            self._events: list[_Event] = []
            self._hash = "0" * 64
            self._seq = 0

        def append_event(self, **kwargs: Any) -> dict[str, Any]:
            self._seq += 1
            # 取调用方计算的 hash · 或自动推进
            self._hash = kwargs.get("hash") or hashlib.sha256(
                (self._hash + json.dumps(kwargs.get("payload", {}), sort_keys=True)).encode()
            ).hexdigest()
            ev = _Event(**kwargs, sequence=self._seq)
            self._events.append(ev)
            return {"event_id": f"evt-{uuid.uuid4()}", "sequence": self._seq,
                    "hash": self._hash, "persisted": True}

        def get_last_hash(self, project_id: str) -> str:
            return self._hash

        def get_events_by_project(self, project_id: str) -> list[_Event]:
            return [e for e in self._events if getattr(e, "project_id", None) == project_id]

        def query(self, **kwargs: Any) -> list[_Event]:
            return []

    return _Stub()
