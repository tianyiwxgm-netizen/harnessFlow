"""L1-01 · L2-05 决策审计记录器 · 主入口.

职责(3-1 §3 6 方法):
    1. `record_audit()` · IC-L2-05/06/07/09 四类入口 · buffer 打包 · 立即返 audit_id
    2. `query_by_tick()` · buffer + index + jsonl_scan 三层反查
    3. `query_by_decision()` · 1:1 反查
    4. `query_by_chain()` · 1:N 反查
    5. `flush_buffer()` · tick 边界强制 flush · 经 IC-09 原子落盘
    6. `replay_from_jsonl()` · 启动期重建反查索引 + hash tip
    7. `get_hash_tip()` · 供 L2-02 打 evidence 链

100% 可追溯硬约束:
    - 每 decision 必发 IC-09 · 未审计的决策 raise E_AUDIT_UNAUDITED_DECISION
    - 通过 TraceabilityGuard 内部台账守护

阻塞/幂等:
    - record_audit 同步但不等 fsync(buffer 入队 + 立即返 audit_id)
    - 同 idempotency_key 重复调用返同一 audit_id
    - flush_buffer 同步阻塞至 IC-09 fsync 完成 · semaphore(1) 防并发重复写
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

from app.main_loop.decision_audit.errors import (
    E_AUDIT_CROSS_PROJECT,
    E_AUDIT_EVENT_TYPE_UNKNOWN,
    E_AUDIT_FLUSH_CONCURRENT,
    E_AUDIT_HALT_ON_FAIL,
    E_AUDIT_HASH_BROKEN,
    E_AUDIT_NO_PROJECT_ID,
    E_AUDIT_NO_REASON,
    E_AUDIT_QUERY_MISS,
    E_AUDIT_QUERY_TIMEOUT,
    E_AUDIT_REPLAY_TIMEOUT,
    E_AUDIT_STALE_BUFFER,
    E_AUDIT_WRITE_FAIL,
    AuditError,
    make_audit_error,
)
from app.main_loop.decision_audit.event_bus_adapter import (
    EventBusAdapter,
    compute_hash,
)
from app.main_loop.decision_audit.schemas import (
    AuditCommand,
    AuditEntry,
    AuditResult,
    FlushResult,
    HashTip,
    QueryResult,
    ReplayResult,
    resolve_event_type,
)
from app.main_loop.decision_audit.traceability_guard import TraceabilityGuard


# =========================================================
# 状态机 · buffering / flushing / flushed
# =========================================================

_STATE_BUFFERING = "buffering"
_STATE_FLUSHING = "flushing"
_STATE_HALTED = "HALTED"

_GENESIS_HASH = "0" * 64


class DecisionAuditRecorder:
    """L2-05 决策审计记录器 · Application Service(半状态 Repository)."""

    def __init__(
        self,
        *,
        session_active_pid: str,
        event_bus: Any,
        l2_01_client: Optional[Any] = None,
        l1_07_client: Optional[Any] = None,
        buffer_max: int = 64,
        reason_min_length: int = 1,
        query_timeout_ms: int = 100,
        replay_timeout_ms: int = 30_000,
        reverse_index_max: int = 100_000,
        jsonl_root: Optional[Path] = None,
    ) -> None:
        self._pid = session_active_pid
        self._bus = EventBusAdapter(event_bus)
        self._raw_bus = event_bus  # 保留原引用 · 测试 `.append_event.call_count` 断言用
        self._l2_01 = l2_01_client
        self._l1_07 = l1_07_client
        self._buffer_max = buffer_max
        self._reason_min = reason_min_length
        self._query_timeout_ms = query_timeout_ms
        self._replay_timeout_ms = replay_timeout_ms
        self._reverse_index_max = reverse_index_max
        self._jsonl_root = jsonl_root

        # buffer + reverse index + hash tip
        self._buffer: list[AuditEntry] = []
        self._buffer_lock = threading.RLock()
        self._flush_sem = threading.Semaphore(1)
        # 反查索引(LRU)· by_tick: tick_id -> list[audit_id] · by_decision: dec_id -> audit_id
        #                 by_chain: ch_id -> list[audit_id] · by_id: audit_id -> AuditEntry
        self._idx_by_tick: OrderedDict[str, list[str]] = OrderedDict()
        self._idx_by_decision: OrderedDict[str, str] = OrderedDict()
        self._idx_by_chain: OrderedDict[str, list[str]] = OrderedDict()
        self._entries_by_id: dict[str, AuditEntry] = {}

        # hash tip per project_id
        self._hash_tips: dict[str, tuple[str, int]] = {}  # pid → (hash, sequence)

        # 幂等缓存 · idempotency_key → audit_id
        self._idempotent: dict[str, str] = {}

        # 状态
        self._state = _STATE_BUFFERING
        self._state_lock = threading.Lock()

        # 元事件池(overflow / stale_buffer / audit_rejected)· 测试 get_recent_audits
        self._recent_meta: list[AuditEntry] = []

        # tick → project_id 映射(支持 _register_tick 测试钩子)
        self._tick_project_map: dict[str, str] = {}

        # jsonl 扫描延迟注入(测试用)
        self._jsonl_scan_latency_ms: int = 0

        # captured events(测试 _captured_events 钩子)
        self._captured_events: list[dict[str, Any]] = []

        # replay 状态
        self._replay_status: str = "not_started"

        # 最近 tick(检测 stale_buffer · §11.1 E_AUDIT_STALE_BUFFER)
        self._last_seen_tick: Optional[str] = None
        self._stale_warned_pairs: dict[tuple[str, str], bool] = {}

        # 可追溯守护(Goal §4.1 硬约束)
        self.traceability = TraceabilityGuard()

    # ======================================================
    # 状态 / 测试钩子
    # ======================================================

    def _force_halted(self) -> None:
        """test-only · 模拟 emit_halt_signal 后状态."""
        with self._state_lock:
            self._state = _STATE_HALTED

    def current_state(self) -> str:
        with self._state_lock:
            return self._state

    def buffer_size(self) -> int:
        with self._buffer_lock:
            return len(self._buffer)

    def peek_buffer(self) -> list[AuditEntry]:
        with self._buffer_lock:
            return list(self._buffer)

    def get_recent_audits(self) -> list[AuditEntry]:
        """返回最近元事件(供测试断言)."""
        return list(self._recent_meta)

    def _register_tick(self, tick_id: str, *, project_id: str) -> None:
        """test-only · 预置 tick → project_id 映射 · 供 cross_project 测试."""
        self._tick_project_map[tick_id] = project_id

    def _inject_jsonl_scan_latency_ms(self, ms: int) -> None:
        """test-only · 模拟 jsonl 扫描慢."""
        self._jsonl_scan_latency_ms = ms

    def _set_reverse_index_max(self, n: int) -> None:
        """test-only · 缩小 LRU 上限."""
        self._reverse_index_max = n

    def reverse_index_size(self) -> int:
        """供测试断言 · 反查索引当前规模(by_tick + by_decision + by_chain sum)."""
        return len(self._idx_by_tick) + len(self._idx_by_decision) + len(self._idx_by_chain)

    def replay_status(self) -> str:
        return self._replay_status

    # ======================================================
    # 3.1 record_audit
    # ======================================================

    def record_audit(self, cmd: AuditCommand) -> AuditResult:
        """IC-L2-05/06/07/09 入口 · 同步入 buffer · 立即返 audit_id."""
        # §11.1 E_AUDIT_HALT_ON_FAIL · halt 后拒绝
        if self.current_state() == _STATE_HALTED:
            raise make_audit_error(E_AUDIT_HALT_ON_FAIL, "recorder halted · rejecting record")

        # 校验 project_id
        if not cmd.project_id:
            raise make_audit_error(E_AUDIT_NO_PROJECT_ID, "project_id missing")
        # 校验 reason
        if not cmd.reason or not cmd.reason.strip():
            # 写元事件 + raise
            self._emit_meta_event(
                action="audit_rejected",
                project_id=cmd.project_id or self._pid,
                reason="reason missing",
                error_code=E_AUDIT_NO_REASON,
                level="WARN",
            )
            raise make_audit_error(E_AUDIT_NO_REASON, "reason is empty")

        # 幂等检查
        if cmd.idempotency_key and cmd.idempotency_key in self._idempotent:
            aid = self._idempotent[cmd.idempotency_key]
            with self._buffer_lock:
                remaining = max(self._buffer_max - len(self._buffer), 0)
            return AuditResult(
                audit_id=aid,
                buffered=True,
                buffer_remaining=remaining,
                event_id=None,
            )

        # 跨 project 检查(通过 linked_tick → project_id 映射)
        if cmd.linked_tick and cmd.linked_tick in self._tick_project_map:
            tick_pid = self._tick_project_map[cmd.linked_tick]
            if tick_pid != cmd.project_id:
                raise make_audit_error(
                    E_AUDIT_CROSS_PROJECT,
                    f"actor.project_id={cmd.project_id} ≠ linked_tick.project_id={tick_pid}",
                )

        # 解析 event_type
        event_type = resolve_event_type(cmd.source_ic, cmd.action)
        if event_type is None:
            raise make_audit_error(
                E_AUDIT_EVENT_TYPE_UNKNOWN,
                f"source_ic={cmd.source_ic} + action={cmd.action} not in whitelist",
            )

        # stale_buffer 检测:本次 tick 与上次不同且 buffer 非空 · 仅 WARN · 不自动 flush.
        # 说明:多 tick 连续入 buffer 是合法的 · L2-01 会在 tick 边界 force_flush_buffer.
        # 真正的 stale 场景(§11.1):调用方忘了 flush · 下 tick 的 tick_id 与上次不同 → WARN.
        # TC-110 期望:仅记 1 条 WARN 元事件 · 不 auto flush(buffer 里条目仍可通过 reverse index 被查到).
        if (
            cmd.linked_tick
            and self._last_seen_tick is not None
            and cmd.linked_tick != self._last_seen_tick
        ):
            # 只在"严格 stale"条件下告警:上次 tick 与本次不同 · 且 buffer 里仍有上次 tick 的条目
            with self._buffer_lock:
                has_stale = any(
                    e.linked_tick == self._last_seen_tick for e in self._buffer
                )
            # 仅每对 (prev_tick, cur_tick) 触发一次 WARN(防连续 WARN)
            if has_stale and not self._stale_warned_pairs.get(
                (self._last_seen_tick, cmd.linked_tick), False
            ):
                self._emit_meta_event(
                    action="stale_buffer",
                    project_id=cmd.project_id,
                    reason=f"tick {self._last_seen_tick} 未 flush · 残留 buffer(WARN 仅记录)",
                    error_code=E_AUDIT_STALE_BUFFER,
                    level="WARN",
                )
                self._stale_warned_pairs[(self._last_seen_tick, cmd.linked_tick)] = True
        if cmd.linked_tick:
            self._last_seen_tick = cmd.linked_tick

        # 打包 AuditEntry
        audit_id = f"audit-{uuid.uuid4()}"
        entry = AuditEntry(
            audit_id=audit_id,
            source_ic=cmd.source_ic,
            actor=dict(cmd.actor),
            action=cmd.action,
            event_type=event_type,
            project_id=cmd.project_id,
            reason=cmd.reason,
            evidence=list(cmd.evidence),
            payload=dict(cmd.payload),
            ts=cmd.ts,
            idempotency_key=cmd.idempotency_key,
            linked_tick=cmd.linked_tick,
            linked_decision=cmd.linked_decision,
            linked_chain=cmd.linked_chain,
            linked_warn=cmd.linked_warn,
        )

        # 自动登记 tick→project_id 映射(供 cross_project 查询校验)
        if cmd.linked_tick and cmd.linked_tick not in self._tick_project_map:
            self._tick_project_map[cmd.linked_tick] = cmd.project_id

        # 先登记 decision 到 traceability(若是 decision_made)
        if cmd.action == "decision_made" and cmd.linked_decision:
            self.traceability.register_decision(
                cmd.linked_decision,
                project_id=cmd.project_id,
                tick_id=cmd.linked_tick,
                reason=cmd.reason,
            )

        # buffer overflow 检查
        with self._buffer_lock:
            if len(self._buffer) >= self._buffer_max:
                # overflow → 降级同步 flush · 本条走 IC-09 直接写
                self._emit_meta_event(
                    action="buffer_overflow",
                    project_id=cmd.project_id,
                    reason=f"buffer 达 {self._buffer_max} · sync flush",
                    error_code="E_AUDIT_BUFFER_OVERFLOW",
                    level="WARN",
                )
                # 先 flush 旧的
            elif len(self._buffer) < self._buffer_max:
                # 正常入队
                self._buffer.append(entry)
                if cmd.idempotency_key:
                    self._idempotent[cmd.idempotency_key] = audit_id
                # 更新反查索引(buffer 内也可查)
                self._update_reverse_index(entry)
                self._entries_by_id[audit_id] = entry
                # 若 action 是 decision_made · mark audited
                if cmd.action == "decision_made" and cmd.linked_decision:
                    self.traceability.mark_audited(cmd.linked_decision)
                remaining = self._buffer_max - len(self._buffer)
                return AuditResult(
                    audit_id=audit_id,
                    buffered=True,
                    buffer_remaining=remaining,
                    event_id=None,
                )

        # 到此说明 overflow 了 · 走同步 flush 路径
        # 1. flush 现有 buffer
        try:
            self.flush_buffer(force=True, reason="buffer_overflow")
        except AuditError:
            raise
        # 2. 同步写本条(独立一次 IC-09)
        event_id = self._sync_append_single(entry)
        if cmd.idempotency_key:
            self._idempotent[cmd.idempotency_key] = audit_id
        self._update_reverse_index(entry)
        self._entries_by_id[audit_id] = entry
        if cmd.action == "decision_made" and cmd.linked_decision:
            self.traceability.mark_audited(cmd.linked_decision)
        with self._buffer_lock:
            remaining = self._buffer_max - len(self._buffer)
        return AuditResult(
            audit_id=audit_id,
            buffered=False,
            buffer_remaining=remaining,
            event_id=event_id,
        )

    # ------------------------------------------------------
    # meta event helper
    # ------------------------------------------------------

    def _emit_meta_event(
        self,
        *,
        action: str,
        project_id: str,
        reason: str,
        error_code: str,
        level: str = "WARN",
    ) -> None:
        """生成元事件(不入 buffer · 进 recent_meta)· 便于测试断言."""
        event_type = resolve_event_type("IC-L2-05", action) or f"L1-01:{action}"
        entry = AuditEntry(
            audit_id=f"audit-meta-{uuid.uuid4()}",
            source_ic="IC-L2-05",
            actor={"l1": "L1-01", "l2": "L2-05"},
            action=action,
            event_type=event_type,
            project_id=project_id,
            reason=reason,
            evidence=[],
            payload={"meta": True},
            ts=self._now_iso(),
            error_code=error_code,
            level=level,
        )
        self._recent_meta.append(entry)

    @staticmethod
    def _now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ------------------------------------------------------
    # reverse index
    # ------------------------------------------------------

    def _update_reverse_index(self, entry: AuditEntry) -> None:
        """更新 by_tick / by_decision / by_chain 索引 · LRU 淘汰."""
        if entry.linked_tick:
            self._touch_tick_index(entry.linked_tick, entry.audit_id)
        if entry.linked_decision:
            self._touch_decision_index(entry.linked_decision, entry.audit_id)
        if entry.linked_chain:
            self._touch_chain_index(entry.linked_chain, entry.audit_id)
        # LRU 淘汰(合并三个索引的条目计数)
        self._maybe_lru_evict()

    def _touch_tick_index(self, tick_id: str, audit_id: str) -> None:
        lst = self._idx_by_tick.get(tick_id, [])
        lst.append(audit_id)
        # OrderedDict move_to_end on access
        self._idx_by_tick[tick_id] = lst
        self._idx_by_tick.move_to_end(tick_id)

    def _touch_decision_index(self, dec_id: str, audit_id: str) -> None:
        self._idx_by_decision[dec_id] = audit_id
        self._idx_by_decision.move_to_end(dec_id)

    def _touch_chain_index(self, chain_id: str, audit_id: str) -> None:
        lst = self._idx_by_chain.get(chain_id, [])
        lst.append(audit_id)
        self._idx_by_chain[chain_id] = lst
        self._idx_by_chain.move_to_end(chain_id)

    def _maybe_lru_evict(self) -> None:
        """总规模超 max 时 · 淘汰最旧 key(跨三类索引·公平淘汰 by_tick 首条)."""
        total = self.reverse_index_size()
        while total > self._reverse_index_max:
            # 优先淘汰最旧的 by_tick · 然后 by_chain · 最后 by_decision
            if self._idx_by_tick:
                tid, aids = self._idx_by_tick.popitem(last=False)
                for aid in aids:
                    self._entries_by_id.pop(aid, None)
            elif self._idx_by_chain:
                cid, aids = self._idx_by_chain.popitem(last=False)
                for aid in aids:
                    self._entries_by_id.pop(aid, None)
            elif self._idx_by_decision:
                did, aid = self._idx_by_decision.popitem(last=False)
                self._entries_by_id.pop(aid, None)
            else:
                break
            total = self.reverse_index_size()

    # ======================================================
    # 3.2 query_by_tick
    # ======================================================

    def query_by_tick(
        self,
        *,
        tick_id: str,
        project_id: str,
        include_buffered: bool = True,
        max_results: int = 100,
    ) -> QueryResult:
        """三层反查:buffer(若 include_buffered) → index → jsonl_scan(超时)."""
        t_start = time.monotonic()
        # 跨 project 校验(若 tick → pid 已登记)
        tick_pid = self._tick_project_map.get(tick_id)
        if tick_pid is not None and tick_pid != project_id:
            raise make_audit_error(
                E_AUDIT_CROSS_PROJECT,
                f"query project_id={project_id} ≠ tick.project_id={tick_pid}",
            )

        entries_from_buffer: list[AuditEntry] = []
        entries_from_index: list[AuditEntry] = []

        # buffer 层
        if include_buffered:
            with self._buffer_lock:
                entries_from_buffer = [e for e in self._buffer if e.linked_tick == tick_id]

        # index 层:已 flushed 的 entries 通过 _idx_by_tick 查 _entries_by_id
        buf_ids = {e.audit_id for e in entries_from_buffer}
        if tick_id in self._idx_by_tick:
            for aid in self._idx_by_tick[tick_id]:
                if aid in buf_ids:
                    continue  # 在 buffer 里已经有了 · 跳过重复
                entry = self._entries_by_id.get(aid)
                if entry is not None and aid not in buf_ids:
                    # 仅取 flushed 的(buffered 的不进 index · 我们靠 buf_ids 过滤)
                    # 此处直接按存在性取 · 不区分是否 flushed
                    if entry.linked_tick == tick_id:
                        # buffer 里有的也在 index · 需更精细区分
                        if entry in entries_from_buffer:
                            continue
                        entries_from_index.append(entry)

        # jsonl_scan 层(当 index + buffer 都 miss · 且配置了 jsonl_root)
        entries_from_jsonl: list[AuditEntry] = []
        partial = False
        if (
            not entries_from_buffer
            and not entries_from_index
            and self._jsonl_root is not None
        ):
            scanned, partial = self._jsonl_scan_by_tick(tick_id, project_id, t_start)
            entries_from_jsonl.extend(scanned)

        all_entries = entries_from_buffer + entries_from_index + entries_from_jsonl
        all_entries = all_entries[:max_results]

        # source 判定
        if entries_from_buffer and entries_from_index:
            source = "mixed"
        elif entries_from_buffer:
            source = "buffer"
        elif entries_from_index:
            source = "index"
        elif entries_from_jsonl:
            source = "jsonl_scan"
        else:
            source = "not_found"

        dur_ms = int((time.monotonic() - t_start) * 1000)
        return QueryResult(
            entries=all_entries,
            source=source,
            count=len(all_entries),
            query_duration_ms=dur_ms,
            partial=partial,
        )

    def _jsonl_scan_by_tick(
        self,
        tick_id: str,
        project_id: str,
        t_start: float,
    ) -> tuple[list[AuditEntry], bool]:
        """扫 projects/<pid>/audit/l1-01/*.jsonl · 超时 → partial=true."""
        if self._jsonl_scan_latency_ms:
            time.sleep(self._jsonl_scan_latency_ms / 1000.0)
        audit_dir = self._jsonl_root / "projects" / project_id / "audit" / "l1-01"
        out: list[AuditEntry] = []
        partial = False
        if not audit_dir.exists():
            return out, False
        for jsonl_path in sorted(audit_dir.glob("*.jsonl")):
            if (time.monotonic() - t_start) * 1000 > self._query_timeout_ms:
                partial = True
                break
            try:
                for raw in jsonl_path.read_text().splitlines():
                    if not raw.strip():
                        continue
                    rec = json.loads(raw)
                    if rec.get("linked_tick") == tick_id:
                        out.append(self._rec_to_entry(rec))
            except Exception:
                continue
        return out, partial

    def _rec_to_entry(self, rec: dict[str, Any]) -> AuditEntry:
        """jsonl 行 → AuditEntry."""
        return AuditEntry(
            audit_id=rec.get("audit_id") or f"audit-replayed-{rec.get('event_id','?')}",
            source_ic=rec.get("source_ic", "IC-L2-05"),
            actor=rec.get("actor", {"l1": "L1-01", "l2": "L2-01"}),
            action=rec.get("action", "tick_scheduled"),
            event_type=rec.get("event_type", "L1-01:tick_scheduled"),
            project_id=rec.get("project_id", ""),
            reason=rec.get("reason", ""),
            evidence=list(rec.get("evidence", [])),
            payload=dict(rec.get("payload", {})),
            ts=rec.get("ts", "1970-01-01T00:00:00Z"),
            linked_tick=rec.get("linked_tick"),
            linked_decision=rec.get("linked_decision"),
            linked_chain=rec.get("linked_chain"),
            linked_warn=rec.get("linked_warn"),
            prev_hash=rec.get("prev_hash"),
            hash=rec.get("hash"),
            sequence=rec.get("sequence"),
            event_id=rec.get("event_id"),
        )

    # ======================================================
    # 3.3 query_by_decision / query_by_chain
    # ======================================================

    def query_by_decision(
        self,
        *,
        decision_id: str,
        project_id: str,
    ) -> Optional[AuditEntry]:
        """1:1 反查 · 未命中返 None · 无异常."""
        aid = self._idx_by_decision.get(decision_id)
        if aid is None:
            return None
        entry = self._entries_by_id.get(aid)
        if entry is None:
            return None
        if entry.project_id != project_id:
            raise make_audit_error(
                E_AUDIT_CROSS_PROJECT,
                f"decision project_id mismatch · got={project_id} entry={entry.project_id}",
            )
        return entry

    def query_by_chain(
        self,
        *,
        chain_id: str,
        project_id: str,
    ) -> list[AuditEntry]:
        """1:N 反查."""
        aids = self._idx_by_chain.get(chain_id, [])
        out: list[AuditEntry] = []
        for aid in aids:
            entry = self._entries_by_id.get(aid)
            if entry is None:
                continue
            if entry.project_id != project_id:
                raise make_audit_error(
                    E_AUDIT_CROSS_PROJECT,
                    f"chain project_id mismatch · got={project_id}",
                )
            out.append(entry)
        return out

    # ======================================================
    # 3.4 flush_buffer
    # ======================================================

    def flush_buffer(self, *, force: bool = False, reason: str = "tick_boundary") -> FlushResult:
        """tick 边界强制 flush · semaphore(1) 防重入."""
        t_start = time.monotonic()
        acquired = self._flush_sem.acquire(blocking=True, timeout=5.0)
        if not acquired:
            raise make_audit_error(
                E_AUDIT_FLUSH_CONCURRENT,
                "flush semaphore acquire timeout · concurrent flush in progress",
            )
        try:
            with self._state_lock:
                if self._state == _STATE_FLUSHING:
                    # 另一线程正在 flush · 等结束(semaphore 已保护 · 此处基本不会达到)
                    pass
                self._state = _STATE_FLUSHING

            with self._buffer_lock:
                to_flush = list(self._buffer)
                self._buffer.clear()

            if not to_flush:
                with self._state_lock:
                    self._state = _STATE_BUFFERING
                dur_ms = int((time.monotonic() - t_start) * 1000)
                return FlushResult(
                    flushed_count=0,
                    last_event_id=None,
                    last_hash=self._get_tip_hash(self._pid),
                    duration_ms=dur_ms,
                )

            last_event_id: Optional[str] = None
            last_hash = _GENESIS_HASH
            hash_broken_seen = False
            for entry in to_flush:
                try:
                    last_event_id, last_hash = self._append_with_hash(entry)
                except AuditError as exc:
                    if exc.error_code == E_AUDIT_HASH_BROKEN and not hash_broken_seen:
                        hash_broken_seen = True
                        # 告警 L1-07 · 不 halt · 用当前 tip 重算 · 续写
                        if self._l1_07:
                            self._l1_07.alert(
                                error_code=E_AUDIT_HASH_BROKEN,
                                source="L2-05",
                                project_id=entry.project_id,
                            )
                        # 再试一次 · bypass hash check · 按本地 tip 重算
                        last_event_id, last_hash = self._append_with_hash(
                            entry, bypass_hash_check=True
                        )
                        continue
                    raise
                except Exception as exc:
                    # IC-09 底层失败 → halt
                    self._halt_on_write_fail(str(exc), entry.project_id)
                    raise make_audit_error(
                        E_AUDIT_WRITE_FAIL,
                        f"IC-09 append_event failed: {exc!r}",
                        cause=repr(exc),
                    ) from exc

            with self._state_lock:
                self._state = _STATE_BUFFERING
            dur_ms = int((time.monotonic() - t_start) * 1000)
            return FlushResult(
                flushed_count=len(to_flush),
                last_event_id=last_event_id,
                last_hash=last_hash,
                duration_ms=dur_ms,
            )
        finally:
            self._flush_sem.release()

    def _append_with_hash(
        self, entry: AuditEntry, *, bypass_hash_check: bool = False
    ) -> tuple[str, str]:
        """hash 链计算 + IC-09 append_event · 返 (event_id, hash).

        bypass_hash_check · retry 路径用 · 告警后按当前本地 tip 重算链 · 不再查 bus.
        """
        prev_hash, seq = self._hash_tips.get(entry.project_id, (_GENESIS_HASH, 0))
        if bypass_hash_check:
            # 跳过 prev_hash 对齐 · 按本地 tip 重算链
            pass
        else:
            self._verify_prev_hash_aligned(entry.project_id, prev_hash)
        return self._do_append(entry, prev_hash, seq)

    def _verify_prev_hash_aligned(self, project_id: str, prev_hash: str) -> None:
        """prev_hash 对齐检查 · bus 告诉我们的 last_hash 必须等于本地 tip.

        (genesis 时两边都 = '0'*64 · 匹配; 后续每条对齐)
        """
        try:
            bus_last = self._bus.get_last_hash(project_id)
        except Exception:
            return
        if (
            isinstance(bus_last, str)
            and bus_last
            and bus_last != _GENESIS_HASH
            and bus_last != prev_hash
        ):
            try:
                bus_last2 = self._bus.get_last_hash(project_id)
            except Exception:
                bus_last2 = bus_last
            if (
                isinstance(bus_last2, str)
                and bus_last2 != _GENESIS_HASH
                and bus_last2 != prev_hash
            ):
                raise make_audit_error(
                    E_AUDIT_HASH_BROKEN,
                    f"prev_hash mismatch · local={prev_hash} bus={bus_last2}",
                    local_prev=prev_hash,
                    bus_last=bus_last2,
                )

    def _do_append(
        self, entry: AuditEntry, prev_hash: str, seq: int
    ) -> tuple[str, str]:
        """真正组 payload + 调 bus.append_event · 返 (event_id, hash)."""
        content_payload = {
            "audit_id": entry.audit_id,
            "source_ic": entry.source_ic,
            "actor": entry.actor,
            "action": entry.action,
            "project_id": entry.project_id,
            "reason": entry.reason,
            "evidence": entry.evidence,
            "ts": entry.ts,
            "payload": entry.payload,
            "linked_tick": entry.linked_tick,
            "linked_decision": entry.linked_decision,
            "linked_chain": entry.linked_chain,
            "linked_warn": entry.linked_warn,
        }
        new_hash = compute_hash(prev_hash, content_payload)
        result = self._bus.append_event(
            event_type=entry.event_type,
            project_id=entry.project_id,
            actor=entry.actor,
            ts=entry.ts,
            payload=content_payload,
            prev_hash=prev_hash,
            hash=new_hash,
            sequence=seq + 1,
            links=[
                {"kind": "audit", "ref": entry.audit_id},
            ],
            idempotency_key=entry.idempotency_key or entry.audit_id,
        )
        event_id = result.get("event_id") or f"evt-{uuid.uuid4()}"
        # 更新 entry 的 hash meta
        entry.prev_hash = prev_hash
        entry.hash = new_hash
        entry.sequence = seq + 1
        entry.event_id = event_id
        # 更新 tip
        self._hash_tips[entry.project_id] = (new_hash, seq + 1)
        # captured events(测试钩子)
        self._captured_events.append({
            "action": entry.action,
            "event_type": entry.event_type,
            "audit_id": entry.audit_id,
            "hash": new_hash,
            "prev_hash": prev_hash,
            "sequence": seq + 1,
        })
        return event_id, new_hash

    def _sync_append_single(self, entry: AuditEntry) -> str:
        """buffer overflow 场景 · 单条直写 IC-09."""
        try:
            event_id, _ = self._append_with_hash(entry)
        except AuditError:
            raise
        except Exception as exc:
            self._halt_on_write_fail(str(exc), entry.project_id)
            raise make_audit_error(
                E_AUDIT_WRITE_FAIL,
                f"IC-09 append_event(overflow) failed: {exc!r}",
                cause=repr(exc),
            ) from exc
        return event_id

    def _halt_on_write_fail(self, reason: str, project_id: str) -> None:
        """响应面 halt · 通知 L2-01."""
        with self._state_lock:
            self._state = _STATE_HALTED
        if self._l2_01 is not None:
            try:
                self._l2_01.on_halt_signal(
                    source="L2-05",
                    reason=E_AUDIT_WRITE_FAIL,
                    project_id=project_id,
                    detail=reason,
                )
            except Exception:
                pass

    # ======================================================
    # 3.5 replay_from_jsonl
    # ======================================================

    def replay_from_jsonl(
        self,
        *,
        project_id: str,
        from_date: Optional[str] = None,
        max_entries: int = 100_000,
    ) -> ReplayResult:
        """启动期重建 · 扫 jsonl · 重建反查索引 + hash tip."""
        if not project_id:
            raise make_audit_error(E_AUDIT_NO_PROJECT_ID, "replay needs project_id")
        t_start = time.monotonic()
        self._replay_status = "in_progress"
        if self._jsonl_root is None:
            self._replay_status = "no_root"
            return ReplayResult(
                replayed_count=0, latest_hash=_GENESIS_HASH, files_scanned=0,
                hash_chain_valid=True, duration_ms=0,
            )
        audit_dir = self._jsonl_root / "projects" / project_id / "audit" / "l1-01"
        if not audit_dir.exists():
            self._replay_status = "no_data"
            return ReplayResult(
                replayed_count=0, latest_hash=_GENESIS_HASH, files_scanned=0,
                hash_chain_valid=True, duration_ms=0,
            )

        replayed = 0
        files_scanned = 0
        prev = _GENESIS_HASH
        seq = 0
        chain_valid = True
        first_broken: Optional[str] = None
        partial = False

        files = sorted(audit_dir.glob("*.jsonl"))
        if from_date:
            files = [f for f in files if f.stem >= from_date]

        for jsonl_path in files:
            if (time.monotonic() - t_start) * 1000 > self._replay_timeout_ms:
                partial = True
                self._replay_status = "partial"
                break
            files_scanned += 1
            try:
                for raw in jsonl_path.read_text().splitlines():
                    if (time.monotonic() - t_start) * 1000 > self._replay_timeout_ms:
                        partial = True
                        break
                    if not raw.strip():
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    rec_prev = rec.get("prev_hash", _GENESIS_HASH)
                    rec_hash = rec.get("hash", "")
                    # hash 链检查
                    expected = compute_hash(rec_prev, rec.get("payload", {}))
                    if rec_hash != expected or rec_prev != prev:
                        chain_valid = False
                        if first_broken is None:
                            first_broken = f"{jsonl_path.name}:seq={rec.get('sequence')}"
                        if self._l1_07:
                            try:
                                self._l1_07.alert(
                                    error_code=E_AUDIT_HASH_BROKEN,
                                    source="L2-05:replay",
                                    at=first_broken,
                                )
                            except Exception:
                                pass
                        # 不阻塞 · 继续
                    # 重建索引
                    entry = self._rec_to_entry(rec)
                    # audit_id 不能重复
                    if entry.audit_id not in self._entries_by_id:
                        self._entries_by_id[entry.audit_id] = entry
                        self._update_reverse_index(entry)
                    replayed += 1
                    prev = rec_hash or prev
                    seq = max(seq, int(rec.get("sequence", 0)))
                    if replayed >= max_entries:
                        partial = True
                        break
                if partial:
                    break
            except Exception:
                continue

        if partial:
            self._replay_status = "partial"
        else:
            self._replay_status = "complete"
        # 更新 hash tip
        self._hash_tips[project_id] = (prev, seq)
        dur_ms = int((time.monotonic() - t_start) * 1000)
        return ReplayResult(
            replayed_count=replayed,
            latest_hash=prev,
            files_scanned=files_scanned,
            hash_chain_valid=chain_valid,
            first_broken_at=first_broken,
            duration_ms=dur_ms,
            partial=partial,
        )

    # ======================================================
    # 3.6 get_hash_tip
    # ======================================================

    def _get_tip_hash(self, project_id: str) -> str:
        return self._hash_tips.get(project_id, (_GENESIS_HASH, 0))[0]

    def get_hash_tip(self, *, project_id: str) -> HashTip:
        h, s = self._hash_tips.get(project_id, (_GENESIS_HASH, 0))
        return HashTip(hash=h, sequence=s)


__all__ = ["DecisionAuditRecorder"]
