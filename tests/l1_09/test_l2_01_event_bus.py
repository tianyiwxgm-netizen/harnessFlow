"""L2-01 · WP α-WP04 · EventBus.append (IC-09 入口) · TDD 红→绿.

对齐：
- 3-1 L2-01 §3.2 append_event · §6.1 核心算法 · §7.1 EventEntry schema
- Dev-α plan §3.4 WP04 DoD

覆盖（~20 TC）：
  正向：
    - 首次 append: seq=0, prev_hash=GENESIS, hash 64hex, meta 持久化
    - 连续 append: seq 单调 · prev == 上一条 hash
    - 多 project 隔离（PM-14）
    - is_meta=True 可 append
    - 跨进程 halt 持久化（marker 生效）
  负向：
    - Event schema 非法（type 前缀错 / actor 非白名单 / project_id 格式错）
    - fsync EIO → BusFsyncFailed + halt marker 写入 + 后续 append raise BusHalted
    - disk full → BusDiskFull
    - I/O error 彻底失败 → BusWriteFailed + halt
  幂等：
    - 同 event_id → idempotent_replay=True · 不重复落盘
    - 同 idempotency_key → idempotent_replay=True
  契约：
    - AppendEventResult 全字段稳定 · hash 链可人工验证
"""
from __future__ import annotations

import errno
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.crash_safety.hash_chain import (
    GENESIS_HASH,
    compute_hash_chain_link,
    verify_chain_link,
)
from app.l1_09.crash_safety.schemas import HashChainLink
from app.l1_09.event_bus import (
    AppendEventResult,
    BusDiskFull,
    BusFsyncFailed,
    BusHalted,
    BusState,
    BusWriteFailed,
    Event,
    EventBus,
    iter_events_file,
)

# =========================================================
# Helpers
# =========================================================

def _make_event(
    *,
    project_id: str = "proj-demo",
    type_: str = "L1-01:tick",
    actor: str = "main_loop",
    payload: dict | None = None,
    event_id: str | None = None,
    idempotency_key: str | None = None,
    is_meta: bool = False,
) -> Event:
    return Event(
        project_id=project_id,
        type=type_,
        actor=actor,
        timestamp=datetime.now(tz=UTC),
        state="EXEC",
        payload=payload or {"n": 1},
        event_id=event_id,
        idempotency_key=idempotency_key,
        is_meta=is_meta,
    )


@pytest.fixture
def bus(tmp_fs: Path) -> EventBus:
    return EventBus(root=tmp_fs)


# =========================================================
# 正向 · append 基础
# =========================================================

class TestAppendPositive:
    def test_first_append_seq_zero_prev_genesis(self, bus: EventBus) -> None:
        """首次 append: sequence=0 · prev_hash=GENESIS · hash 64 hex · 文件落盘."""
        pid = "proj-demo"
        evt = _make_event(project_id=pid)
        result = bus.append(evt)

        assert isinstance(result, AppendEventResult)
        assert result.sequence == 0
        assert result.prev_hash == "GENESIS"
        assert len(result.hash) == 64
        assert all(c in "0123456789abcdef" for c in result.hash)
        assert result.event_id.startswith("evt_")
        assert Path(result.file_path).exists()
        assert result.broadcast_enqueued is False  # WP04 跳过广播
        assert result.idempotent_replay is False

    def test_consecutive_append_seq_monotonic(self, bus: EventBus) -> None:
        """连续 append: sequence 单调 +1 · prev 链接正确."""
        pid = "proj-demo"
        r1 = bus.append(_make_event(project_id=pid))
        r2 = bus.append(_make_event(project_id=pid))
        r3 = bus.append(_make_event(project_id=pid))

        assert r1.sequence == 0
        assert r2.sequence == 1
        assert r3.sequence == 2
        assert r2.prev_hash == r1.hash
        assert r3.prev_hash == r2.hash

    def test_meta_persisted(self, bus: EventBus, tmp_fs: Path) -> None:
        """append 后 meta 持久化 · 重启新 bus 仍可续 seq."""
        pid = "proj-demo"
        bus.append(_make_event(project_id=pid))
        bus.append(_make_event(project_id=pid))
        last_hash_before = bus.append(_make_event(project_id=pid)).hash

        # 新 bus 实例（同 root）读 meta
        bus2 = EventBus(root=tmp_fs)
        r = bus2.append(_make_event(project_id=pid))
        assert r.sequence == 3
        assert r.prev_hash == last_hash_before

    def test_hash_chain_verifiable(self, bus: EventBus) -> None:
        """append 后 · 可用 hash_chain 工具独立验证链完整."""
        pid = "proj-demo"
        bus.append(_make_event(project_id=pid, payload={"n": 1}))
        bus.append(_make_event(project_id=pid, payload={"n": 2}))
        bus.append(_make_event(project_id=pid, payload={"n": 3}))

        events_file = Path(
            bus._events_path(pid)  # type: ignore[attr-defined]
        )
        lines = iter_events_file(events_file)
        assert len(lines) == 3

        prev = GENESIS_HASH
        for body in lines:
            body_for_hash = {k: v for k, v in body.items() if k != "hash"}
            recomputed = compute_hash_chain_link(prev, body_for_hash)
            assert recomputed.curr_hash == body["hash"]
            # verify_chain_link 验 mutation safety
            link = HashChainLink(
                prev_hash=prev,
                curr_hash=recomputed.curr_hash,
                sequence=int(body["sequence"]),
                body_canonical_json=recomputed.body_canonical_json,
            )
            assert verify_chain_link(link, body_for_hash) is True
            prev = recomputed.curr_hash


# =========================================================
# PM-14 · 多 project 隔离
# =========================================================

class TestPM14Isolation:
    def test_multi_project_independent_seq(self, bus: EventBus) -> None:
        """两 project 独立 seq · 无串话."""
        ra1 = bus.append(_make_event(project_id="proj-a"))
        rb1 = bus.append(_make_event(project_id="proj-b"))
        ra2 = bus.append(_make_event(project_id="proj-a"))
        rb2 = bus.append(_make_event(project_id="proj-b"))

        assert ra1.sequence == 0 and ra2.sequence == 1
        assert rb1.sequence == 0 and rb2.sequence == 1
        # hash 链独立
        assert ra2.prev_hash == ra1.hash
        assert rb2.prev_hash == rb1.hash
        # 文件分片物理隔离
        assert ra1.file_path != rb1.file_path

    def test_project_id_format_rejected(self, bus: EventBus) -> None:
        """project_id 不符 PM-14 格式 · Event 构造即 raise."""
        with pytest.raises(Exception):  # pydantic ValidationError
            bus.append(_make_event(project_id="INVALID SPACE"))
        with pytest.raises(Exception):
            bus.append(_make_event(project_id=""))


# =========================================================
# Event schema 校验
# =========================================================

class TestEventSchemaValidation:
    def test_type_prefix_must_be_L1_XX(self) -> None:
        """type 必 ^L1-\\d{2}:.+$ · 非白名单 raise."""
        with pytest.raises(Exception):
            _make_event(type_="Invalid:foo")
        with pytest.raises(Exception):
            _make_event(type_="L1-99:bad_range")  # L1-99 不在 01..10

    def test_actor_whitelist(self) -> None:
        """actor 只能是白名单 · human:* 例外."""
        with pytest.raises(Exception):
            _make_event(actor="unknown_actor")
        # human: 前缀允许
        e = _make_event(actor="human:alice")
        assert e.actor == "human:alice"

    def test_is_meta_flag(self, bus: EventBus) -> None:
        """is_meta=True 可 append · 不触发递归（WP05 广播侧强制）."""
        r = bus.append(_make_event(is_meta=True))
        assert r.sequence == 0


# =========================================================
# 幂等性
# =========================================================

class TestIdempotency:
    def test_same_event_id_idempotent_replay(self, bus: EventBus) -> None:
        """同 event_id · 第二次返 idempotent_replay=True · 不落第二条."""
        eid = "evt_01HJX9K3M5NQ8BTPWVZYF0GR3K"
        r1 = bus.append(_make_event(event_id=eid))
        r2 = bus.append(_make_event(event_id=eid))
        assert r1.event_id == r2.event_id == eid
        assert r2.idempotent_replay is True
        # 物理文件只 1 条
        lines = iter_events_file(Path(r1.file_path))
        assert len(lines) == 1

    def test_same_idempotency_key_replay(self, bus: EventBus) -> None:
        """同 idempotency_key · 第二次返 replay."""
        bus.append(_make_event(idempotency_key="unique-op-123"))
        r2 = bus.append(_make_event(idempotency_key="unique-op-123"))
        assert r2.idempotent_replay is True


# =========================================================
# fsync / halt · 响应面 4
# =========================================================

class TestHaltSemantics:
    def test_fsync_failure_triggers_halt(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """fsync EIO · raise BusFsyncFailed · halt marker 落盘 · state=HALTED."""

        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "fsync EIO (mocked)")

        monkeypatch.setattr(
            "app.l1_09.crash_safety.appender.os.fsync", fake_fsync
        )

        with pytest.raises(BusFsyncFailed) as exc:
            bus.append(_make_event())

        assert exc.value.halt_system is True
        assert bus.halt_guard.is_halted() is True
        assert bus.state == BusState.HALTED

    def test_halt_persists_across_instances(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """halt marker 跨实例可见（模拟跨进程 / 重启）."""
        bus1 = EventBus(root=tmp_fs)

        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "fsync EIO")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.fsync", fake_fsync)
        with pytest.raises(BusFsyncFailed):
            bus1.append(_make_event())

        # 新实例 · 仍 halted
        monkeypatch.undo()  # 不影响 · 因为 marker 已落盘
        bus2 = EventBus(root=tmp_fs)
        assert bus2.state == BusState.HALTED
        with pytest.raises(BusHalted):
            bus2.append(_make_event())

    def test_halt_rejects_all_subsequent_append(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """halt 后 · 任何 append 必 raise BusHalted · 不落盘."""

        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "fsync EIO")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.fsync", fake_fsync)
        with pytest.raises(BusFsyncFailed):
            bus.append(_make_event())

        # 再 append · 即使 fsync 修好也仍 halt（marker 是兜底）
        monkeypatch.undo()
        with pytest.raises(BusHalted):
            bus.append(_make_event())

    def test_clear_halt_unlocks(self, bus: EventBus, monkeypatch: pytest.MonkeyPatch) -> None:
        """clear_halt(admin_token) 解锁 · 可继续 append（WP06 严格校验）."""

        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "fsync EIO")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.fsync", fake_fsync)
        with pytest.raises(BusFsyncFailed):
            bus.append(_make_event())

        monkeypatch.undo()
        assert bus.halt_guard.clear_halt(admin_token="admin") is True
        assert bus.halt_guard.is_halted() is False
        # 再 append 正常
        r = bus.append(_make_event())
        assert r.sequence == 0


# =========================================================
# Disk full / Write failed
# =========================================================

class TestWriteFailure:
    def test_disk_full_raises_bus_disk_full(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """append_atomic ENOSPC 耗尽 · raise BusDiskFull."""

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "ENOSPC")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)
        with pytest.raises(BusDiskFull) as exc:
            bus.append(_make_event())
        assert exc.value.halt_system is True

    def test_io_error_retry_exhausted_bus_write_failed(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """append_atomic EIO 耗尽 · raise BusWriteFailed · 触发 halt."""

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.EIO, "EIO")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)
        with pytest.raises(BusWriteFailed) as exc:
            bus.append(_make_event())
        assert exc.value.halt_system is True
        assert bus.halt_guard.is_halted() is True


# =========================================================
# 契约 · AppendEventResult schema 稳定
# =========================================================

class TestContract:
    def test_append_event_result_schema_stable(self, bus: EventBus) -> None:
        r = bus.append(_make_event())
        dump = r.model_dump()
        required = {
            "event_id",
            "sequence",
            "hash",
            "prev_hash",
            "persisted_at",
            "jsonl_offset",
            "file_path",
            "broadcast_enqueued",
            "idempotent_replay",
        }
        assert required.issubset(dump.keys())
        # pydantic frozen
        with pytest.raises(Exception):
            r.sequence = 999  # type: ignore[misc]

    def test_jsonl_line_schema(self, bus: EventBus) -> None:
        """落盘每行必含 event_id / sequence / prev_hash / hash · §7.1."""
        r = bus.append(_make_event(payload={"k": "v"}))
        lines = iter_events_file(Path(r.file_path))
        assert len(lines) == 1
        body = lines[0]
        for key in (
            "event_id", "project_id", "type", "actor", "timestamp",
            "payload", "sequence", "prev_hash", "hash", "is_meta",
        ):
            assert key in body, f"missing key: {key}"
        # persist_at 也要在（§3.2 response）
        assert "persisted_at" in body
        # json 行可解析
        raw = Path(r.file_path).read_bytes().splitlines()[0]
        assert json.loads(raw) == body
