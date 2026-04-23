"""L2-01 · WP α-WP06 · halt_guard 强化 + correlation_id contextvars · TDD 红→绿.

对齐：
- 3-1 L2-01 §3.5 共享元字段 correlation_id / trace_id
- 3-1 L2-01 §8 状态机 · halt 持久化
- Dev-α plan §3.6 WP06 DoD

覆盖（~14 TC）：
  HaltGuard（加强）:
    - admin_token 与 env var 严格匹配（constant-time）
    - env 未设 · 拒任何 token
    - 错 token 拒 · 记 halt_log 审计
    - 正确 token · 解锁 · 记审计
    - halt_info JSON 可解析
    - BusHalted 异常携带 reason / source / halted_at
  Context:
    - new_correlation_id 合法格式
    - set_correlation_id 非法格式 raise
    - request_context 自动生成 + 退出恢复
    - append 自动注入 correlation_id 到 body
    - 多次 append 用同一 correlation_id
    - 手工 set 后 append · body.correlation_id == 手工值
"""
from __future__ import annotations

import errno
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus import (
    BusFsyncFailed,
    BusHalted,
    Event,
    EventBus,
    iter_events_file,
)
from app.l1_09.event_bus.context import (
    _is_valid_correlation_id,
    get_correlation_id,
    new_correlation_id,
    request_context,
    set_correlation_id,
)


def _make_event(*, project_id: str = "proj-ctx", type_: str = "L1-01:tick") -> Event:
    return Event(
        project_id=project_id, type=type_, actor="main_loop",
        timestamp=datetime.now(tz=UTC), state="EXEC", payload={"n": 1},
    )


@pytest.fixture
def bus(tmp_fs: Path) -> EventBus:
    return EventBus(root=tmp_fs)


@pytest.fixture(autouse=True)
def _reset_contextvars():
    """每测试独立 · reset L2-01 contextvars · 防跨测试污染."""
    from app.l1_09.event_bus.context import (
        _correlation_id,
        _span_id,
        _trace_id,
    )
    _correlation_id.set(None)
    _trace_id.set(None)
    _span_id.set(None)
    yield
    _correlation_id.set(None)
    _trace_id.set(None)
    _span_id.set(None)


# =========================================================
# HaltGuard · admin_token 严格校验
# =========================================================

class TestHaltGuardAdminToken:
    def _trigger_halt(self, bus: EventBus, monkeypatch: pytest.MonkeyPatch) -> None:
        """辅助：fsync EIO 触发 halt marker 写入 · 然后恢复 fsync."""
        import os as _os
        real_fsync = _os.fsync

        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "fsync EIO")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.fsync", fake_fsync)
        with pytest.raises(BusFsyncFailed):
            bus.append(_make_event())
        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.fsync", real_fsync)

    def test_clear_halt_env_not_set_rejected(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """env var 未设 · 任何 token 必拒（防止未配置即解锁）."""
        monkeypatch.delenv("HARNESS_ADMIN_TOKEN", raising=False)
        self._trigger_halt(bus, monkeypatch)
        assert bus.halt_guard.clear_halt(admin_token="anything") is False
        assert bus.halt_guard.is_halted() is True

    def test_clear_halt_wrong_token_rejected(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """token 与 env var 不匹配 · 拒."""
        monkeypatch.setenv("HARNESS_ADMIN_TOKEN", "correct-xyz")
        self._trigger_halt(bus, monkeypatch)
        assert bus.halt_guard.clear_halt(admin_token="wrong") is False
        assert bus.halt_guard.is_halted() is True

    def test_clear_halt_empty_token_rejected(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """空 token 直接拒（即使 env 未设也拒）."""
        monkeypatch.setenv("HARNESS_ADMIN_TOKEN", "any")
        self._trigger_halt(bus, monkeypatch)
        assert bus.halt_guard.clear_halt(admin_token="") is False

    def test_clear_halt_matched_token_succeeds(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """token 匹配 · 解锁 · 可继续 append."""
        monkeypatch.setenv("HARNESS_ADMIN_TOKEN", "secret-match")
        self._trigger_halt(bus, monkeypatch)
        assert bus.halt_guard.clear_halt(admin_token="secret-match") is True
        assert bus.halt_guard.is_halted() is False
        r = bus.append(_make_event())
        assert r.sequence == 0

    def test_halt_info_json_parseable(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """marker 内容可解析为 JSON · 含 reason / source / timestamp."""
        self._trigger_halt(bus, monkeypatch)
        info = bus.halt_guard.load_halt_info()
        assert info is not None
        assert "reason" in info
        assert "source" in info
        assert "timestamp" in info

    def test_bus_halted_exception_carries_info(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """触发 halt 后 · 下次 append raise BusHalted · message 含 reason/source/halted_at."""
        bus = EventBus(root=tmp_fs)
        self._trigger_halt(bus, monkeypatch)
        with pytest.raises(BusHalted) as exc:
            bus.append(_make_event())
        msg = str(exc.value)
        assert "reason=" in msg
        assert "source=" in msg
        assert "halted_at=" in msg

    def test_clear_halt_logs_attempt(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch, tmp_fs: Path
    ) -> None:
        """clear_halt 失败 / 成功都记 halt_log.jsonl."""
        monkeypatch.setenv("HARNESS_ADMIN_TOKEN", "correct")
        self._trigger_halt(bus, monkeypatch)

        bus.halt_guard.clear_halt(admin_token="wrong")  # 失败
        bus.halt_guard.clear_halt(admin_token="correct")  # 成功

        log_path = tmp_fs / "projects" / "_global" / "halt_log.jsonl"
        assert log_path.exists()
        content = log_path.read_text()
        assert "halt_clear_attempt" in content
        assert "token_mismatch" in content
        assert "token_matched" in content


# =========================================================
# Context · correlation_id / trace_id
# =========================================================

class TestContextvars:
    def test_new_correlation_id_format(self) -> None:
        """cor_ + 20 lowercase hex."""
        cid = new_correlation_id()
        assert re.match(r"^cor_[0-9a-f]{20}$", cid) is not None
        assert _is_valid_correlation_id(cid) is True

    def test_set_correlation_id_invalid_raises(self) -> None:
        """格式非法 · raise ValueError."""
        with pytest.raises(ValueError):
            set_correlation_id("not_a_valid_format")
        with pytest.raises(ValueError):
            set_correlation_id("cor_TOOSHORT")

    def test_request_context_auto_generates(self) -> None:
        """request_context() 无参 · 自动生成 correlation_id."""
        assert get_correlation_id() is None
        with request_context() as ctx:
            assert ctx["correlation_id"] is not None
            assert _is_valid_correlation_id(ctx["correlation_id"])
            assert get_correlation_id() == ctx["correlation_id"]
        # 退出后 reset
        assert get_correlation_id() is None

    def test_request_context_explicit_correlation(self) -> None:
        explicit = new_correlation_id()
        with request_context(correlation_id=explicit) as ctx:
            assert ctx["correlation_id"] == explicit
            assert get_correlation_id() == explicit


# =========================================================
# EventBus · correlation_id 注入 body
# =========================================================

class TestEventBusContextInjection:
    def test_append_auto_injects_correlation_id(self, bus: EventBus) -> None:
        """无 context 设置 · append 自动生成 correlation_id 并写入 body."""
        r = bus.append(_make_event())
        lines = iter_events_file(Path(r.file_path))
        assert len(lines) == 1
        assert "correlation_id" in lines[0]
        assert _is_valid_correlation_id(str(lines[0]["correlation_id"]))

    def test_request_context_propagates_to_body(self, bus: EventBus) -> None:
        """显式 context · append body.correlation_id == context 值."""
        explicit = new_correlation_id()
        with request_context(correlation_id=explicit):
            r = bus.append(_make_event())
        lines = iter_events_file(Path(r.file_path))
        assert lines[0]["correlation_id"] == explicit

    def test_multi_append_share_correlation_in_context(self, bus: EventBus) -> None:
        """同一 context 内多次 append · 共享 correlation_id."""
        explicit = new_correlation_id()
        with request_context(correlation_id=explicit):
            r1 = bus.append(_make_event())
            r2 = bus.append(_make_event())
        lines = iter_events_file(Path(r1.file_path))
        assert len(lines) == 2
        assert all(line["correlation_id"] == explicit for line in lines)
        # seq 独立 · hash 链独立
        assert r2.sequence == r1.sequence + 1

    def test_trace_id_span_id_also_propagated(self, bus: EventBus) -> None:
        """trace_id / span_id 也写入 body（OTEL 透传）."""
        with request_context(
            trace_id="trace-abc-123",
            span_id="span-xyz-789",
        ):
            r = bus.append(_make_event())
        lines = iter_events_file(Path(r.file_path))
        body = lines[0]
        assert body.get("trace_id") == "trace-abc-123"
        assert body.get("span_id") == "span-xyz-789"

    def test_correlation_id_in_hash_chain(self, bus: EventBus) -> None:
        """correlation_id 参与 hash 链 · 不同 id 导致 hash 不同（不可篡改追溯）."""
        cid_1 = new_correlation_id()
        cid_2 = new_correlation_id()

        # 两个独立 project · 各自 append 一条 · 对比 hash
        with request_context(correlation_id=cid_1):
            r1 = bus.append(_make_event(project_id="proj-trace-a"))
        with request_context(correlation_id=cid_2):
            r2 = bus.append(_make_event(project_id="proj-trace-b"))

        # 相同 payload/type/actor · 不同 correlation_id → hash 不同
        assert r1.hash != r2.hash
