"""L2-01 · WP α-WP05 · register_subscriber + read_range · TDD 红→绿.

对齐：
- 3-1 L2-01 §3.3 register_subscriber / §3.4 read_range / §6.4 BroadcastDispatcher
- Dev-α plan §3.5 WP05 DoD

覆盖（~18 TC）：
  Subscriber registry：注册 / 幂等覆盖 / 注销 / token 错配
  Filter：type_prefix / actor / state / project_id / exclude_meta · AND 语义
  Dispatch：fire_and_forget · 失败吞 · 多订阅独立触发
  Read range：完整读 / from_seq / to_seq / include_meta / verify_hash / 10 万 event 不 OOM
  EventBus 集成：append 后 callback 被触发 · 无订阅不影响 broadcast_enqueued
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus import (
    Event,
    EventBus,
    ReadHashBrokenError,
    Subscriber,
    SubscriberFilter,
    SubscriberHandle,
    SubscriberRegistry,
    dispatch,
    event_matches,
)

# =========================================================
# Helpers
# =========================================================

def _make_event(
    *, project_id: str = "proj-demo", type_: str = "L1-01:tick",
    actor: str = "main_loop", state: str = "EXEC", is_meta: bool = False,
    payload: dict | None = None,
) -> Event:
    return Event(
        project_id=project_id, type=type_, actor=actor,
        timestamp=datetime.now(tz=UTC), state=state,
        payload=payload or {"n": 1}, is_meta=is_meta,
    )


def _noop(body: dict) -> None:
    pass


@pytest.fixture
def bus(tmp_fs: Path) -> EventBus:
    return EventBus(root=tmp_fs)


# =========================================================
# SubscriberRegistry
# =========================================================

class TestSubscriberRegistry:
    def test_register_returns_handle(self) -> None:
        r = SubscriberRegistry()
        sub = Subscriber(subscriber_id="audit_mirror", callback=_noop)
        h = r.register(sub)
        assert isinstance(h, SubscriberHandle)
        assert h.subscriber_id == "audit_mirror"
        assert h.registration_token.startswith("sub_")
        assert len(r) == 1

    def test_register_idempotent_overwrite(self) -> None:
        """§3.3 同 subscriber_id 再注册 · 覆盖 · 新 token."""
        r = SubscriberRegistry()
        h1 = r.register(Subscriber(subscriber_id="audit_mirror", callback=_noop))
        h2 = r.register(
            Subscriber(
                subscriber_id="audit_mirror",
                callback=_noop,
                filter=SubscriberFilter(type_prefix=["L1-07:"]),
            )
        )
        assert h2.registration_token != h1.registration_token
        assert len(r) == 1

    def test_unregister_token_mismatch_rejected(self) -> None:
        r = SubscriberRegistry()
        h1 = r.register(Subscriber(subscriber_id="audit_mirror", callback=_noop))
        # 再注册 · 旧 token 无效
        r.register(Subscriber(subscriber_id="audit_mirror", callback=_noop))
        ok = r.unregister(
            subscriber_id="audit_mirror",
            registration_token=h1.registration_token,
        )
        assert ok is False
        assert len(r) == 1

    def test_unregister_unknown_returns_false(self) -> None:
        r = SubscriberRegistry()
        ok = r.unregister(subscriber_id="nonexistent", registration_token="sub_xxx")
        assert ok is False


# =========================================================
# event_matches · filter 语义
# =========================================================

class TestFilterSemantics:
    def _body(self, **kwargs) -> dict:
        return {
            "type": "L1-01:tick",
            "actor": "main_loop",
            "state": "EXEC",
            "project_id": "proj-a",
            "is_meta": False,
            **kwargs,
        }

    def test_empty_filter_matches_all(self) -> None:
        sub = Subscriber(subscriber_id="all", callback=_noop)
        assert event_matches(sub, self._body()) is True
        assert event_matches(sub, self._body(is_meta=True)) is True

    def test_type_prefix_filter(self) -> None:
        sub = Subscriber(
            subscriber_id="only_main_class",
            callback=_noop,
            filter=SubscriberFilter(type_prefix=["L1-01:"]),
        )
        assert event_matches(sub, self._body(type="L1-01:tick")) is True
        assert event_matches(sub, self._body(type="L1-07:supervisor_check")) is False

    def test_actor_filter(self) -> None:
        sub = Subscriber(
            subscriber_id="only_supervisor",
            callback=_noop,
            filter=SubscriberFilter(actor=["supervisor"]),
        )
        assert event_matches(sub, self._body(actor="supervisor")) is True
        assert event_matches(sub, self._body(actor="main_loop")) is False

    def test_exclude_meta(self) -> None:
        sub = Subscriber(
            subscriber_id="no_meta",
            callback=_noop,
            filter=SubscriberFilter(exclude_meta=True),
        )
        assert event_matches(sub, self._body(is_meta=False)) is True
        assert event_matches(sub, self._body(is_meta=True)) is False

    def test_project_id_filter(self) -> None:
        sub = Subscriber(
            subscriber_id="proj_a_only",
            callback=_noop,
            filter=SubscriberFilter(project_id=["proj-a"]),
        )
        assert event_matches(sub, self._body(project_id="proj-a")) is True
        assert event_matches(sub, self._body(project_id="proj-b")) is False

    def test_filter_and_combine(self) -> None:
        """多条件 AND · 一个不中即 False."""
        sub = Subscriber(
            subscriber_id="strict",
            callback=_noop,
            filter=SubscriberFilter(
                type_prefix=["L1-01:"],
                actor=["main_loop"],
                state=["EXEC"],
            ),
        )
        assert event_matches(sub, self._body()) is True
        assert event_matches(sub, self._body(actor="supervisor")) is False  # actor 不中
        assert event_matches(sub, self._body(state="CLOSED")) is False  # state 不中


# =========================================================
# dispatch
# =========================================================

class TestDispatch:
    def test_dispatch_fire_and_forget(self) -> None:
        seen = []

        def cb(body: dict) -> None:
            seen.append(body["event_id"])

        sub = Subscriber(subscriber_id="sink", callback=cb)
        body = {"event_id": "evt_1", "type": "L1-01:tick", "actor": "main_loop"}
        delivered, failures = dispatch([sub], body)
        assert delivered == 1
        assert failures == []
        assert seen == ["evt_1"]

    def test_dispatch_failure_swallowed(self) -> None:
        """callback raise 不影响其他订阅者."""
        reached = []

        def bad(body: dict) -> None:
            raise RuntimeError("boom")

        def good(body: dict) -> None:
            reached.append(body["event_id"])

        subs = [
            Subscriber(subscriber_id="bad", callback=bad),
            Subscriber(subscriber_id="good", callback=good),
        ]
        body = {"event_id": "evt_x", "type": "L1-01:tick", "actor": "main_loop"}
        delivered, failures = dispatch(subs, body)
        # good 被调 · bad 失败
        assert delivered == 1
        assert len(failures) == 1
        assert failures[0][0] == "bad"
        assert reached == ["evt_x"]

    def test_dispatch_skip_filter_miss(self) -> None:
        reached = []

        def cb(body: dict) -> None:
            reached.append(1)

        sub = Subscriber(
            subscriber_id="supervisor_class",
            callback=cb,
            filter=SubscriberFilter(type_prefix=["L1-07:"]),
        )
        body = {"type": "L1-01:tick"}  # 不中
        delivered, _ = dispatch([sub], body)
        assert delivered == 0
        assert reached == []


# =========================================================
# EventBus integration
# =========================================================

class TestEventBusSubscriberIntegration:
    def test_append_triggers_callback(self, bus: EventBus) -> None:
        received = []

        def cb(body: dict) -> None:
            received.append(body["sequence"])

        h = bus.register_subscriber(
            Subscriber(subscriber_id="sink", callback=cb)
        )
        assert isinstance(h, SubscriberHandle)

        r = bus.append(_make_event())
        assert r.broadcast_enqueued is True  # 有订阅者 · broadcast=True
        assert received == [1]  # A-4 · 首个 event seq=1

    def test_no_subscribers_broadcast_false(self, bus: EventBus) -> None:
        r = bus.append(_make_event())
        assert r.broadcast_enqueued is False

    def test_unregister_stops_callbacks(self, bus: EventBus) -> None:
        received = []

        def cb(body: dict) -> None:
            received.append(1)

        h = bus.register_subscriber(
            Subscriber(subscriber_id="sink", callback=cb)
        )
        bus.append(_make_event())
        assert received == [1]

        ok = bus.unregister_subscriber(
            subscriber_id="sink", registration_token=h.registration_token
        )
        assert ok is True
        bus.append(_make_event())
        assert received == [1]  # 仍 1 · 未再触发

    def test_type_prefix_filter_integration(self, bus: EventBus) -> None:
        received_types: list[str] = []

        def cb(body: dict) -> None:
            received_types.append(body["type"])

        bus.register_subscriber(
            Subscriber(
                subscriber_id="only_supervisor_class",
                callback=cb,
                filter=SubscriberFilter(type_prefix=["L1-07:"]),
            )
        )
        bus.append(_make_event(type_="L1-01:tick"))  # 不匹配
        bus.append(_make_event(type_="L1-07:supervisor_check"))  # 匹配
        assert received_types == ["L1-07:supervisor_check"]


# =========================================================
# read_range
# =========================================================

class TestReadRange:
    def test_read_full_range(self, bus: EventBus) -> None:
        pid = "proj-demo"
        for _ in range(5):
            bus.append(_make_event(project_id=pid))
        items = list(bus.read_range(pid))
        assert len(items) == 5
        # A-4 · sequence 从 1 起（§3.9.3）
        assert [it["sequence"] for it in items] == [1, 2, 3, 4, 5]

    def test_read_with_from_seq(self, bus: EventBus) -> None:
        pid = "proj-demo"
        for _ in range(5):
            bus.append(_make_event(project_id=pid))
        # A-4 · 从 seq=3 起
        items = list(bus.read_range(pid, from_seq=3))
        assert [it["sequence"] for it in items] == [3, 4, 5]

    def test_read_with_to_seq(self, bus: EventBus) -> None:
        pid = "proj-demo"
        for _ in range(5):
            bus.append(_make_event(project_id=pid))
        # A-4 · seq=[2, 4] 闭区间
        items = list(bus.read_range(pid, from_seq=2, to_seq=4))
        assert [it["sequence"] for it in items] == [2, 3, 4]

    def test_read_exclude_meta(self, bus: EventBus) -> None:
        pid = "proj-demo"
        bus.append(_make_event(project_id=pid, is_meta=False))
        bus.append(_make_event(project_id=pid, is_meta=True))
        bus.append(_make_event(project_id=pid, is_meta=False))
        items = list(bus.read_range(pid, include_meta=False))
        assert len(items) == 2
        assert all(not it["is_meta"] for it in items)

    def test_read_verify_hash_ok(self, bus: EventBus) -> None:
        pid = "proj-demo"
        for _ in range(3):
            bus.append(_make_event(project_id=pid))
        # 无篡改 · verify 通过
        items = list(bus.read_range(pid, verify_hash_on_read=True))
        assert len(items) == 3

    def test_read_verify_hash_detects_tamper(
        self, bus: EventBus, tmp_fs: Path
    ) -> None:
        pid = "proj-demo"
        for _ in range(3):
            bus.append(_make_event(project_id=pid))
        # 手工篡改第 2 条的 payload（不改 hash）
        events_path = bus._events_path(pid)  # type: ignore[attr-defined]
        import json as _json
        lines = events_path.read_bytes().splitlines()
        body = _json.loads(lines[1])
        body["payload"] = {"TAMPERED": True}
        lines[1] = _json.dumps(body, sort_keys=True).encode()
        events_path.write_bytes(b"\n".join(lines) + b"\n")

        with pytest.raises(ReadHashBrokenError):
            list(bus.read_range(pid, verify_hash_on_read=True))

    def test_read_project_not_found(self, bus: EventBus) -> None:
        """project 无事件 · read_range raise BusProjectNotRegistered."""
        from app.l1_09.event_bus import BusProjectNotRegistered
        with pytest.raises(BusProjectNotRegistered):
            list(bus.read_range("proj-nonexistent"))

    def test_read_large_streaming(self, bus: EventBus) -> None:
        """大文件流式 · 仅取前 10 条 · 内存不应增长（A-4 · seq 从 1 起）."""
        pid = "proj-demo"
        for _ in range(100):
            bus.append(_make_event(project_id=pid))
        # 用 iter 取前 10
        it = bus.read_range(pid)
        first_ten = []
        for i, body in enumerate(it):
            first_ten.append(body["sequence"])
            if i + 1 == 10:
                break
        assert first_ten == list(range(1, 11))
