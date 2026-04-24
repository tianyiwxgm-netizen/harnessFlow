"""L2-01 / L2-05 · review α1 批修复 · TDD 红→绿.

对齐 docs/superpowers/reviews/2026-04-23-Dev-α-α1-review.md
修复清单：B-1 (CRITICAL) · B-2/B-3/B-4/E-1 (HIGH) · A-1/A-2/A-3/A-4 (P2).
"""
from __future__ import annotations

import errno
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.crash_safety.schemas import (
    CrashSafetyError,
    FsyncFailed,
    LineTooLargeError,
)
from app.l1_09.event_bus import (
    BusDiskFull,
    BusFsyncFailed,
    BusHalted,
    BusState,
    Event,
    EventBus,
    iter_events_file,
)
from app.l1_09.event_bus.context import (
    _correlation_id,
    _span_id,
    _trace_id,
    get_correlation_id,
    get_span_id,
    get_trace_id,
    new_correlation_id,
    request_context,
    set_correlation_id,
)


def _make_event(
    *,
    project_id: str = "proj-fix",
    type_: str = "L1-01:tick",
    actor: str = "main_loop",
    payload: dict | None = None,
    event_id: str | None = None,
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
        is_meta=is_meta,
    )


@pytest.fixture
def bus(tmp_fs: Path) -> EventBus:
    return EventBus(root=tmp_fs)


@pytest.fixture(autouse=True)
def _reset_contextvars():
    """每测试独立 · reset L2-01 contextvars · 防跨测试污染."""
    _correlation_id.set(None)
    _trace_id.set(None)
    _span_id.set(None)
    yield
    _correlation_id.set(None)
    _trace_id.set(None)
    _span_id.set(None)


# =========================================================
# B-1 CRITICAL · BusDiskFull 必须调 halt_guard.mark_halt()
# =========================================================

class TestB1DiskFullHalt:
    """IC-09 §3.9.4: E_EVT_DISK_FULL → halt 整个系统."""

    def test_disk_full_triggers_halt_guard_mark_halt(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """disk full · halt_guard 必须标 halted（当前 bug: 缺失）."""

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "ENOSPC")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)
        with pytest.raises(BusDiskFull) as exc:
            bus.append(_make_event())
        assert exc.value.halt_system is True
        # 关键断言（bug 修复要点）
        assert bus.halt_guard.is_halted() is True
        assert bus.state == BusState.HALTED

    def test_disk_full_writes_halt_marker_file(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch, tmp_fs: Path
    ) -> None:
        """disk full · halt.marker 文件必须落盘（跨进程可见）."""

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "ENOSPC")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)
        with pytest.raises(BusDiskFull):
            bus.append(_make_event())

        # marker 文件必须真实存在
        marker_path = tmp_fs / "projects" / "_global" / "halt.marker"
        assert marker_path.exists(), "halt.marker must exist after disk full"

    def test_disk_full_persists_across_bus_instances(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """disk full 触发的 halt · 跨 EventBus 实例可见."""
        bus1 = EventBus(root=tmp_fs)

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "ENOSPC")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)
        with pytest.raises(BusDiskFull):
            bus1.append(_make_event())

        # 还原 write · halt 仍持久（marker 已落盘）
        monkeypatch.undo()
        bus2 = EventBus(root=tmp_fs)
        assert bus2.state == BusState.HALTED
        with pytest.raises(BusHalted):
            bus2.append(_make_event())


# =========================================================
# B-2 HIGH · save_meta 失败必须 halt
# =========================================================

class TestB2SaveMetaFailureHalt:
    """save_meta fsync 失败 · 必须 halt + raise BusFsyncFailed (防 stale meta)."""

    def test_save_meta_fsync_failure_triggers_halt(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """mock save_meta raise FsyncFailed · 必须 halt."""
        from app.l1_09.event_bus import core as _core

        def fake_save_meta(project_dir: Path, meta) -> None:
            raise FsyncFailed(
                "mocked save_meta fsync fail",
                errno=errno.EIO,
                target=str(project_dir / "events.meta.json"),
            )

        monkeypatch.setattr(_core, "save_meta", fake_save_meta)

        with pytest.raises(BusFsyncFailed) as exc:
            bus.append(_make_event())
        # 必须 halt
        assert exc.value.halt_system is True
        assert bus.halt_guard.is_halted() is True

    def test_save_meta_failure_no_seq_reuse(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_meta 失败后 · halt 触发 · 下次 append 直接拒（防 seq reuse）."""
        from app.l1_09.event_bus import core as _core

        call_count = {"n": 0}

        real_save_meta = _core.save_meta

        def flaky_save_meta(project_dir: Path, meta) -> None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise FsyncFailed(
                    "mocked save_meta fsync fail",
                    errno=errno.EIO,
                    target=str(project_dir / "events.meta.json"),
                )
            return real_save_meta(project_dir, meta)

        monkeypatch.setattr(_core, "save_meta", flaky_save_meta)

        with pytest.raises(BusFsyncFailed):
            bus.append(_make_event(project_id="proj-b2"))
        # halt 已触发 · 下次 append 直接拒
        assert bus.halt_guard.is_halted() is True
        with pytest.raises(BusHalted):
            bus.append(_make_event(project_id="proj-b2"))


# =========================================================
# B-3 HIGH · _truncate_jsonl fsync 失败不得吞
# =========================================================

class TestB3TruncateJsonlFsyncNoSuppress:
    """fsync-no-retry 铁律：truncate 后 fsync 失败 · 必须抛 · 不得 suppress."""

    def test_truncate_jsonl_fsync_failure_raises_fsync_failed(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """mock fsync raise · _truncate_jsonl 必须抛 FsyncFailed（当前 bug: suppress）."""
        from app.l1_09.crash_safety import integrity_checker as _ic

        target = tmp_fs / "events.jsonl"
        # 写 2 行合法数据 + 1 行坏尾
        target.write_bytes(b'{"good":1}\n{"bad":half...\n')

        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "fsync EIO (mocked)")

        monkeypatch.setattr(_ic.os, "fsync", fake_fsync)

        with pytest.raises(FsyncFailed):
            _ic._truncate_jsonl(target, 10)


# =========================================================
# B-4 HIGH · LineTooLargeError 取代 AssertionError
# =========================================================

class TestB4LineTooLargeNotAssertion:
    """PIPE_BUF_LIMIT 超出 · 必须 raise LineTooLargeError (CrashSafetyError)."""

    def test_line_over_pipe_buf_raises_line_too_large(
        self, tmp_fs: Path
    ) -> None:
        """line + \\n > PIPE_BUF_LIMIT · 必须 LineTooLargeError（不是 AssertionError）."""
        from app.l1_09 import crash_safety as cs

        target = tmp_fs / "e.jsonl"
        huge = "x" * 4100  # line+\n > 4096

        with pytest.raises(LineTooLargeError):
            cs.append_atomic(target, huge)

    def test_line_too_large_is_crash_safety_error(self, tmp_fs: Path) -> None:
        """LineTooLargeError 必须继承 CrashSafetyError · 便于 catch 集中处理."""
        from app.l1_09 import crash_safety as cs

        target = tmp_fs / "e.jsonl"
        huge = "x" * 4100

        with pytest.raises(CrashSafetyError):
            cs.append_atomic(target, huge)


# =========================================================
# E-1 HIGH · request_context 正确 reset（不擦外层）
# =========================================================

class TestE1RequestContextNested:
    """嵌套 request_context · 退出内层 · 外层 ContextVar 不得被擦除."""

    def test_nested_request_context_preserves_outer_correlation_id(self) -> None:
        """with request_context(outer): with request_context(inner): pass · 外层保留."""
        outer_cid = new_correlation_id()
        inner_cid = new_correlation_id()
        assert outer_cid != inner_cid

        with request_context(correlation_id=outer_cid):
            assert get_correlation_id() == outer_cid
            with request_context(correlation_id=inner_cid):
                assert get_correlation_id() == inner_cid
            # 退出 inner · 必须回到 outer（不是 None）
            assert get_correlation_id() == outer_cid
        # 退出 outer · 回 None
        assert get_correlation_id() is None

    def test_nested_request_context_preserves_trace_and_span(self) -> None:
        """trace_id / span_id 也必须 nested-safe."""
        with request_context(
            correlation_id=new_correlation_id(),
            trace_id="trace-outer",
            span_id="span-outer",
        ):
            assert get_trace_id() == "trace-outer"
            assert get_span_id() == "span-outer"
            with request_context(
                correlation_id=new_correlation_id(),
                trace_id="trace-inner",
                span_id="span-inner",
            ):
                assert get_trace_id() == "trace-inner"
                assert get_span_id() == "span-inner"
            # 外层值复位
            assert get_trace_id() == "trace-outer"
            assert get_span_id() == "span-outer"

    def test_request_context_preserves_pre_existing_correlation_id(self) -> None:
        """若 context 进入前已有 correlation_id · 退出后必须恢复."""
        pre_set = new_correlation_id()
        set_correlation_id(pre_set)
        assert get_correlation_id() == pre_set
        with request_context(correlation_id=new_correlation_id()):
            pass
        # 退出后 · 恢复到 pre_set · 不是 None
        assert get_correlation_id() == pre_set


# =========================================================
# A-1 P2 · AppendEventResult 字段名对齐 IC-09 §3.9.3
# =========================================================

class TestA1AppendEventResultFields:
    """新字段 ts_persisted / storage_path / persisted · 旧字段 deprecation alias."""

    def test_result_has_ts_persisted_and_storage_path(self, bus: EventBus) -> None:
        """新字段名：ts_persisted (ISO-8601 str) + storage_path + persisted=True."""
        r = bus.append(_make_event())
        # 新字段存在
        assert hasattr(r, "ts_persisted")
        assert hasattr(r, "storage_path")
        assert hasattr(r, "persisted")
        # persisted 默认 True
        assert r.persisted is True
        # ts_persisted 是 ISO-8601 str（IC-09 §3.9.3）
        assert isinstance(r.ts_persisted, str)
        # 可解析为 datetime
        datetime.fromisoformat(r.ts_persisted.replace("Z", "+00:00"))
        # storage_path 与旧 file_path 等价
        assert r.storage_path == r.file_path

    def test_old_fields_still_work_as_alias(self, bus: EventBus) -> None:
        """旧字段 persisted_at / file_path 保留 alias（不破坏已 merge 代码）."""
        r = bus.append(_make_event())
        # 旧 getters 仍然可用
        assert r.persisted_at is not None  # datetime alias
        assert r.file_path == r.storage_path


# =========================================================
# A-2 P2 · Event schema 加 trigger_tick
# =========================================================

class TestA2EventTriggerTick:
    """IC-09 §3.9.2: trigger_tick: str | None · optional input · L1-01 调时可填."""

    def test_event_accepts_trigger_tick(self) -> None:
        """Event 构造可传 trigger_tick · 合法 ULID 格式."""
        tick_id = "tick_01HJX9K3M5NQ8BTPWVZYF0GR3K"
        e = Event(
            project_id="proj-a2",
            type="L1-01:tick",
            actor="main_loop",
            timestamp=datetime.now(tz=UTC),
            state="EXEC",
            payload={},
            trigger_tick=tick_id,
        )
        assert e.trigger_tick == tick_id

    def test_event_trigger_tick_default_none(self) -> None:
        """trigger_tick 默认 None · 不传不报错."""
        e = Event(
            project_id="proj-a2",
            type="L1-01:tick",
            actor="main_loop",
            timestamp=datetime.now(tz=UTC),
            state="EXEC",
        )
        assert e.trigger_tick is None

    def test_event_trigger_tick_persisted_in_body(self, bus: EventBus) -> None:
        """append 后 · body 含 trigger_tick（若显式设）."""
        tick_id = "tick_01HJX9K3M5NQ8BTPWVZYF0GR3K"
        evt = Event(
            project_id="proj-a2",
            type="L1-01:tick",
            actor="main_loop",
            timestamp=datetime.now(tz=UTC),
            state="EXEC",
            payload={"n": 1},
            trigger_tick=tick_id,
        )
        r = bus.append(evt)
        lines = iter_events_file(Path(r.file_path))
        assert lines[0].get("trigger_tick") == tick_id


# =========================================================
# A-3 P2 · project_id 支持 "system" 保留值
# =========================================================

class TestA3SystemProjectId:
    """IC-09 §3.9.2: project_id_or_system: 'system' 允许 · 系统级事件.

    halt / startup / crash-recovery 事件用 project_id='system'.
    """

    def test_event_accepts_project_id_system(self) -> None:
        """project_id='system' · Event 构造不报错."""
        e = Event(
            project_id="system",
            type="L1-09:halt_triggered",
            actor="recoverer",
            timestamp=datetime.now(tz=UTC),
            state="HALTED",
        )
        assert e.project_id == "system"

    def test_halt_event_writes_with_system_project(self, bus: EventBus) -> None:
        """halt 类系统事件可用 system project_id 写成功."""
        evt = Event(
            project_id="system",
            type="L1-09:halt_triggered",
            actor="recoverer",
            timestamp=datetime.now(tz=UTC),
            state="HALTED",
            payload={"reason": "fsync_failed"},
        )
        r = bus.append(evt)
        assert r.sequence == 1  # A-4 修复后 · 首个 event sequence=1

    def test_regular_project_id_still_works(self, bus: EventBus) -> None:
        """普通 project_id 仍保留原 pattern."""
        e = Event(
            project_id="proj-normal",
            type="L1-01:tick",
            actor="main_loop",
            timestamp=datetime.now(tz=UTC),
            state="EXEC",
        )
        assert e.project_id == "proj-normal"

    def test_invalid_project_id_still_rejected(self) -> None:
        """非法 project_id 仍被拒（不能开口子）."""
        with pytest.raises(Exception):
            Event(
                project_id="INVALID SPACE",
                type="L1-01:tick",
                actor="main_loop",
                timestamp=datetime.now(tz=UTC),
                state="EXEC",
            )


# =========================================================
# A-4 P2 · sequence 从 1 起（IC-09 §3.9.3 minimum: 1）
# =========================================================

class TestA4SequenceStartsAtOne:
    """IC-09 §3.9.3: sequence: {type: integer, minimum: 1}.

    first event → sequence=1 · last_sequence=0 初值.
    """

    def test_first_event_sequence_is_one(self, bus: EventBus) -> None:
        """首个 append · sequence == 1（不是 0）."""
        r = bus.append(_make_event())
        assert r.sequence == 1

    def test_consecutive_sequence_monotonic_from_one(self, bus: EventBus) -> None:
        """连续 append · 1, 2, 3, ..."""
        r1 = bus.append(_make_event())
        r2 = bus.append(_make_event())
        r3 = bus.append(_make_event())
        assert r1.sequence == 1
        assert r2.sequence == 2
        assert r3.sequence == 3

    def test_multi_project_each_starts_at_one(self, bus: EventBus) -> None:
        """每个 project 独立从 1 起."""
        ra1 = bus.append(_make_event(project_id="proj-a4a"))
        rb1 = bus.append(_make_event(project_id="proj-a4b"))
        assert ra1.sequence == 1
        assert rb1.sequence == 1

    def test_sequence_min_one_in_schema(self) -> None:
        """AppendEventResult.sequence 必 >= 1."""
        from app.l1_09.event_bus.schemas import AppendEventResult

        # sequence=0 非法
        with pytest.raises(Exception):
            AppendEventResult(
                event_id="evt_01HJX9K3M5NQ8BTPWVZYF0GR3K",
                sequence=0,
                hash="a" * 64,
                prev_hash="GENESIS",
                persisted_at=datetime.now(tz=UTC),
                jsonl_offset=0,
                file_path="/tmp/x",
            )

    def test_project_meta_last_sequence_starts_at_zero(self) -> None:
        """ProjectMeta.last_sequence 初值 = 0（首个 event 分配 seq=1）."""
        from app.l1_09.event_bus.schemas import ProjectMeta

        pm = ProjectMeta(project_id="proj-a4")
        assert pm.last_sequence == 0
