"""L2-01 · EventBus 核心 · IC-09 唯一写入口.

对齐 3-1 §3.2 / §5.1 / §6.1 · POSIX append + hash chain + halt guard.

append(event) 14 步（简化版 · WP04 最小可运行）：
    1. 查 halt_guard · 若 halted → raise BusHalted
    2. Pydantic 校验 event（Event schema 强约束）
    3. 幂等检查（idempotency_key / event_id）
    4. 生成 event_id（若缺）
    5. 读 meta (last_seq / last_hash)
    6. 分配 sequence = last_seq + 1
    7. compute_hash_chain_link(prev_hash, body_with_prev_hash_and_meta)
    8. 组装 jsonl line（含 prev_hash + hash + meta）
    9. append_atomic(target=events.jsonl, line=line)
    10. 若 append_atomic fsync 失败 → HaltGuard.mark_halt · raise BusFsyncFailed
    11. 更新 meta（last_seq / last_hash）· save_meta 原子写
    12. （async emit 订阅者 · WP05 实现 · 本 WP 跳过）
    13. 返回 AppendEventResult

WP04 简化版不做：
- L2-02 lock（plan 承接方 · WP04 用进程内 threading.Lock 兜底）
- broadcast async emit（WP05）
- broadcast_enqueued 字段总返 False
- type prefix 跨 L1 授权白名单（WP06 严格校验）
"""
from __future__ import annotations

import errno
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import ulid

from app.l1_09.crash_safety import append_atomic
from app.l1_09.crash_safety.hash_chain import GENESIS_HASH, compute_hash_chain_link
from app.l1_09.crash_safety.schemas import (
    CrashSafetyError,
    DiskFullError,
    FsyncFailed,
)
from app.l1_09.crash_safety.schemas import (
    IOErrorCS as CSIOErrorCS,
)
from app.l1_09.event_bus.context import (
    get_correlation_id,
    get_span_id,
    get_trace_id,
    new_correlation_id,
    set_correlation_id,
)
from app.l1_09.event_bus.halt_guard import HaltGuard
from app.l1_09.event_bus.meta import load_meta, save_meta
from app.l1_09.event_bus.reader import read_range as _read_range_module
from app.l1_09.event_bus.schemas import (
    AppendEventResult,
    BusDiskFull,
    BusFsyncFailed,
    BusHalted,
    BusState,
    BusWriteFailed,
    Event,
    ProjectMeta,
)
from app.l1_09.event_bus.subscriber import (
    Subscriber,
    SubscriberHandle,
    SubscriberRegistry,
    dispatch,
)


class EventBus:
    """IC-09 唯一写入口 · PM-08 单一事实源 · PM-14 按 project 分片."""

    def __init__(self, root: Path) -> None:
        """
        Args:
            root: 系统根目录 · projects 分片在 `<root>/projects/<pid>/`
        """
        self._root = root
        self._projects_dir = root / "projects"
        self._global_dir = self._projects_dir / "_global"
        self._projects_dir.mkdir(parents=True, exist_ok=True)
        self._global_dir.mkdir(parents=True, exist_ok=True)
        self.halt_guard = HaltGuard(self._global_dir)
        # 进程内锁兜底（WP07 L2-02 LockManager 替代）
        self._locks: dict[str, threading.Lock] = {}
        self._locks_registry_lock = threading.Lock()
        # 幂等去重缓存（同进程内 · 跨进程去重依赖 event_id 文件扫描 · WP04 简化只扫 meta）
        self._idempotent_cache: dict[str, AppendEventResult] = {}
        # 订阅注册表（WP05）
        self._subscribers = SubscriberRegistry()
        # 状态
        if self.halt_guard.is_halted():
            self._state = BusState.HALTED
        else:
            self._state = BusState.READY

    @property
    def state(self) -> BusState:
        """当前 bus 状态（若 halt marker 存在 · 转 HALTED）."""
        if self.halt_guard.is_halted():
            self._state = BusState.HALTED
        return self._state

    def _get_project_lock(self, project_id: str) -> threading.Lock:
        """每 project 独立锁 · WP04 进程内兜底（WP07 切 L2-02 flock FIFO）."""
        with self._locks_registry_lock:
            lock = self._locks.get(project_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[project_id] = lock
            return lock

    def _project_dir(self, project_id: str) -> Path:
        return self._projects_dir / project_id

    def _events_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "events.jsonl"

    # =========================================================
    # 订阅者管理 · WP05
    # =========================================================

    def register_subscriber(self, subscriber: Subscriber) -> SubscriberHandle:
        """§3.3 register_subscriber · 幂等（同 subscriber_id 覆盖）.

        WP05 简化：不支持 replay_from_seq（调用方自行先 read_range 再 register）.
        """
        if self.halt_guard.is_halted():
            raise BusHalted(
                f"EventBus halted · marker: {self.halt_guard.marker_path}",
                cause="halt_marker_present",
            )
        return self._subscribers.register(subscriber)

    def unregister_subscriber(
        self,
        *,
        subscriber_id: str,
        registration_token: str,
    ) -> bool:
        """§3.6 unregister_subscriber · token 不符返 False."""
        return self._subscribers.unregister(
            subscriber_id=subscriber_id,
            registration_token=registration_token,
        )

    def subscriber_count(self) -> int:
        return len(self._subscribers)

    # =========================================================
    # 只读扫描 · WP05
    # =========================================================

    def read_range(
        self,
        project_id: str,
        *,
        from_seq: int = 0,
        to_seq: int | None = None,
        include_meta: bool = True,
        verify_hash_on_read: bool = False,
    ):
        """§3.4 流式 iterator · 供 L2-04 checkpoint 扫描."""
        events_path = self._events_path(project_id)
        return _read_range_module(
            events_path,
            from_seq=from_seq,
            to_seq=to_seq,
            include_meta=include_meta,
            verify_hash_on_read=verify_hash_on_read,
        )

    def append(self, event: Event) -> AppendEventResult:
        """IC-09 唯一写入口 · append 一条事件到 `projects/<pid>/events.jsonl`.

        失败分类（详见 §3.2 错误码表）:
            - BusHalted · 已 halt · 拒任何 append · 携带 halt_reason/halt_at
            - BusFsyncFailed · fsync 失败 · halt marker 写入 · 抛 halt
            - BusWriteFailed / BusDiskFull · L2-05 重试耗尽
        """
        # Step 1: halt check（跨进程 · 文件 marker）
        if self.halt_guard.is_halted():
            info = self.halt_guard.load_halt_info() or {}
            raise BusHalted(
                (
                    f"EventBus halted · reason={info.get('reason', 'unknown')} · "
                    f"source={info.get('source', 'unknown')} · "
                    f"halted_at={info.get('timestamp', 'unknown')}"
                ),
                cause="halt_marker_present",
                correlation_id=get_correlation_id(),
            )

        # Step 2: pydantic 已在 Event() 构造时校验
        # （调用方传 Event 实例 · 或传 dict 时由 Event(**dict) 校验 · 不在本层重复）

        # Step 3-4: 幂等 + event_id
        event_id = event.event_id or f"evt_{ulid.new()}"

        # WP06 · 注入 correlation_id（若 context 未设 · 自动生成并落到 body · 保证每事件可追溯）
        correlation_id = get_correlation_id()
        if correlation_id is None:
            correlation_id = new_correlation_id()
            set_correlation_id(correlation_id)
        trace_id = get_trace_id()
        span_id = get_span_id()
        if event.idempotency_key and event.idempotency_key in self._idempotent_cache:
            cached = self._idempotent_cache[event.idempotency_key]
            return cached.model_copy(update={"idempotent_replay": True})
        if event_id in self._idempotent_cache:
            cached = self._idempotent_cache[event_id]
            return cached.model_copy(update={"idempotent_replay": True})

        project_id = event.project_id
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        events_path = self._events_path(project_id)

        lock = self._get_project_lock(project_id)
        with lock:
            # Step 5-6: load meta + allocate seq
            meta = load_meta(project_dir, project_id=project_id)
            sequence = meta.last_sequence + 1
            prev_hash = meta.last_hash if meta.last_hash != "GENESIS" else GENESIS_HASH

            # Step 7-8: compute hash chain + assemble line
            persisted_at = datetime.now(tz=UTC)
            body = _event_to_body(
                event,
                event_id=event_id,
                sequence=sequence,
                prev_hash=prev_hash,
                persisted_at=persisted_at,
                correlation_id=correlation_id,
                trace_id=trace_id,
                span_id=span_id,
            )
            link = compute_hash_chain_link(prev_hash, body)
            line_obj = {**body, "hash": link.curr_hash}
            line = json.dumps(line_obj, sort_keys=True)

            # Step 9-10: append_atomic（L2-05 · 错误映射到 bus 错误码）
            try:
                append_result = append_atomic(events_path, line)
            except FsyncFailed as exc:
                self.halt_guard.mark_halt(
                    reason=f"fsync failed on {events_path}",
                    source="L2-01:append:fsync",
                    correlation_id=event_id,
                )
                self._state = BusState.HALTED
                raise BusFsyncFailed(
                    f"fsync failed · halt · target={events_path}",
                    cause=repr(exc),
                    correlation_id=event_id,
                ) from exc
            except DiskFullError as exc:
                raise BusDiskFull(
                    f"disk full on {events_path}",
                    cause=repr(exc),
                    correlation_id=event_id,
                ) from exc
            except CSIOErrorCS as exc:
                self.halt_guard.mark_halt(
                    reason=f"I/O write failed on {events_path}",
                    source="L2-01:append:io",
                    correlation_id=event_id,
                )
                self._state = BusState.HALTED
                raise BusWriteFailed(
                    f"atomic_append retries exhausted · target={events_path}",
                    cause=repr(exc),
                    correlation_id=event_id,
                ) from exc
            except CrashSafetyError as exc:
                # 其他 L2-05 错误（PathError/Permission 等）直接透传为 BusWriteFailed
                raise BusWriteFailed(
                    f"atomic_append failed: {exc.error_code} · target={events_path}",
                    cause=repr(exc),
                    correlation_id=event_id,
                ) from exc
            except OSError as exc:
                # ENOSPC 的原始捕获兜底
                if exc.errno == errno.ENOSPC:
                    raise BusDiskFull(
                        f"disk full on {events_path}", cause=repr(exc), correlation_id=event_id
                    ) from exc
                raise BusWriteFailed(
                    f"unexpected OSError on {events_path}",
                    cause=repr(exc),
                    correlation_id=event_id,
                ) from exc

            # Step 11: 更新 meta
            meta.last_sequence = sequence
            meta.last_hash = link.curr_hash
            save_meta(project_dir, meta)

            # Step 12: dispatch 给订阅者（fire_and_forget · 同步 · 异常吞）
            subs = self._subscribers.snapshot()
            broadcast_enqueued = False
            if subs:
                body_for_dispatch = {**line_obj}  # 含 hash · 下游消费完整 body
                _delivered, _failures = dispatch(subs, body_for_dispatch)
                broadcast_enqueued = True

            result = AppendEventResult(
                event_id=event_id,
                sequence=sequence,
                hash=link.curr_hash,
                prev_hash=prev_hash if prev_hash != GENESIS_HASH else "GENESIS",
                persisted_at=persisted_at,
                jsonl_offset=append_result.offset,
                file_path=str(events_path),
                broadcast_enqueued=broadcast_enqueued,
                idempotent_replay=False,
            )

            # 幂等缓存登记
            if event.idempotency_key:
                self._idempotent_cache[event.idempotency_key] = result
            self._idempotent_cache[event_id] = result
            return result


def _event_to_body(
    event: Event,
    *,
    event_id: str,
    sequence: int,
    prev_hash: str,
    persisted_at: datetime,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> dict[str, object]:
    """组装 hash 链参与的 body（包含 prev_hash · 不含 hash · 不含 jsonl_offset）.

    WP06 · correlation_id/trace_id/span_id 写入 body · 参与 hash 计算（不可篡改追溯）.
    """
    body: dict[str, object] = {
        "event_id": event_id,
        "project_id": event.project_id,
        "type": event.type,
        "actor": event.actor,
        "timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
        "state": event.state,
        "payload": event.payload,
        "links": event.links,
        "is_meta": event.is_meta,
        "sequence": sequence,
        "prev_hash": prev_hash,
        "persisted_at": persisted_at.isoformat().replace("+00:00", "Z"),
    }
    if correlation_id is not None:
        body["correlation_id"] = correlation_id
    if trace_id is not None:
        body["trace_id"] = trace_id
    if span_id is not None:
        body["span_id"] = span_id
    return body


# 复用给 tests 的工具（供 subscriber / reader / replay 后续 WP 共用）
def iter_events_file(events_path: Path) -> list[dict[str, object]]:
    """读 events.jsonl 为 list · 仅测试用·WP05 提供 read_range 惰性 iterator."""
    if not events_path.exists():
        return []
    out: list[dict[str, object]] = []
    for raw in events_path.read_bytes().splitlines():
        if not raw.strip():
            continue
        out.append(json.loads(raw.decode("utf-8")))
    return out


__all__ = [
    "EventBus",
    "iter_events_file",
    "ProjectMeta",
]
