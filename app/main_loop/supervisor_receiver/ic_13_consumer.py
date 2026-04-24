"""`IC13Consumer` · IC-13 push_suggestion 消费端 · 分级入 INFO/SUGG/WARN 内存队列。

端到端链路（对齐 3-1 L2-06 §3.1 "receive_suggestion"）：

1. PM-14 校验（跨 project_id → `E_SUGG_CROSS_PROJECT`）
2. schema 已由 `PushSuggestionCommand` pydantic 强校验（content ≥ 10 / obs refs ≥ 1 / level != BLOCK）
3. 幂等 by `suggestion_id`（已入队直接返回 cached ack）
4. 按 `level` 分派：
   - INFO：仅审计 · 不入 queue（§3.1 "INFO 级不入 queue · queue_len 仍为 0"）
   - SUGG：入 `sugg_queue`（FIFO · bounded）
   - WARN：入 `warn_queue`（FIFO · bounded · 非静默 evict 最旧 WARN）
5. IC-09 审计 `L1-01:suggestion_received`

**独立性**：消费 Dev-ζ `SuggestionPusher` 产出的 `PushSuggestionCommand` · 不改 producer。

后续 WP 扩展：priority 排序 / WARN deadline watchdog / counter_after 返 queue snapshot。
WP06 范围 = 分级队列 + 幂等 + 非静默 evict · 满足 §3.1 最小合约。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    SuggestionAck,
    SuggestionInbox,
)
from app.supervisor.event_sender.schemas import (
    PushSuggestionCommand,
)


class EventBusProtocol(Protocol):
    """L1-09 IC-09 append_event 协议（与 rollback_router.executor 对齐）。"""

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str: ...


@dataclass
class IC13Consumer:
    """IC-13 消费端主类 · 分级队列 + 幂等 + 非静默 evict。

    - `session_pid`: 本 session 绑定的 project_id · PM-14 跨 pid 拒绝
    - `event_bus`: L1-09 IC-09 审计
    - `max_warn_queue_len` / `max_sugg_queue_len`: 背压上限（默认 1000 对齐 Dev-ζ pusher）
    """

    session_pid: str
    event_bus: EventBusProtocol
    max_warn_queue_len: int = 1000
    max_sugg_queue_len: int = 1000

    _warn_queue: deque[SuggestionInbox] = field(default_factory=deque)
    _sugg_queue: deque[SuggestionInbox] = field(default_factory=deque)
    # 幂等缓存 · key=suggestion_id · val=首次 ack
    _idem_cache: dict[str, SuggestionAck] = field(default_factory=dict)
    # counter 只增（对齐 I-L2-06-04）
    _counter_info: int = 0
    _counter_sugg: int = 0
    _counter_warn: int = 0

    def __post_init__(self) -> None:
        if not self.session_pid or not self.session_pid.strip():
            raise ValueError("E_SUGG_NO_PROJECT_ID: session_pid 必带（PM-14）")

    async def consume(self, inbox: SuggestionInbox) -> SuggestionAck:
        """端到端消费一次 IC-13 inbox · 返回 ack（幂等 · 分级入队）。"""
        cmd: PushSuggestionCommand = inbox.command

        # Step 1: 幂等检查
        cached = self._idem_cache.get(cmd.suggestion_id)
        if cached is not None:
            return cached

        # Step 2: PM-14 校验
        if cmd.project_id != self.session_pid:
            raise ValueError(
                f"E_SUGG_CROSS_PROJECT: {cmd.project_id} != {self.session_pid}"
            )

        # Step 3: level schema 已由 pydantic `SuggestionLevel` enum 强校验（不会出现 BLOCK · 走 IC-15）

        # Step 4: 分级入队
        evicted: str | None = None
        if inbox.level == AdviceLevel.INFO:
            # INFO 仅审计 · 不入 queue（§3.1）
            self._counter_info += 1
            depth_after = 0
        elif inbox.level == AdviceLevel.SUGG:
            if len(self._sugg_queue) >= self.max_sugg_queue_len:
                evicted = self._sugg_queue.popleft().command.suggestion_id
            self._sugg_queue.append(inbox)
            self._counter_sugg += 1
            depth_after = len(self._sugg_queue)
        else:  # WARN
            if len(self._warn_queue) >= self.max_warn_queue_len:
                evicted = self._warn_queue.popleft().command.suggestion_id
            self._warn_queue.append(inbox)
            self._counter_warn += 1
            depth_after = len(self._warn_queue)

        # Step 5: IC-09 审计 · suggestion_received
        await self.event_bus.append_event(
            project_id=self.session_pid,
            type="L1-01:suggestion_received",
            payload={
                "suggestion_id": cmd.suggestion_id,
                "level": cmd.level.value,
                "routed_to": inbox.level.value,
                "queue_depth_after": depth_after,
                "evicted_suggestion_id": evicted,
            },
            evidence_refs=tuple(cmd.observation_refs),
        )
        # 非静默 evict · 附加一条告警事件（§3.1 "evicted 非静默：审计 + L1-07 告警"）
        if evicted is not None:
            await self.event_bus.append_event(
                project_id=self.session_pid,
                type="L1-01:suggestion_evicted",
                payload={
                    "evicted_suggestion_id": evicted,
                    "reason": "queue_overflow",
                    "routed_to": inbox.level.value,
                },
            )

        # Step 6: ack + 缓存
        ack = SuggestionAck(
            suggestion_id=cmd.suggestion_id,
            accepted=True,
            routed_to=inbox.level,
            queue_depth_after=depth_after,
        )
        self._idem_cache[cmd.suggestion_id] = ack
        return ack

    # --- 审计 / 调试辅助 ---

    def is_processed(self, suggestion_id: str) -> bool:
        """判断某 suggestion_id 是否已被消费过（幂等命中检测）。"""
        return suggestion_id in self._idem_cache

    def queue_depth(self, level: AdviceLevel) -> int:
        """返回指定 level 队列当前深度（INFO 恒为 0）。"""
        if level == AdviceLevel.WARN:
            return len(self._warn_queue)
        if level == AdviceLevel.SUGG:
            return len(self._sugg_queue)
        return 0

    def counter_snapshot(self) -> dict[str, int]:
        """导出 3 级 counter（单调递增 · I-L2-06-04）。"""
        return {
            "info": self._counter_info,
            "sugg": self._counter_sugg,
            "warn": self._counter_warn,
        }

    def peek_queue(self, level: AdviceLevel) -> tuple[SuggestionInbox, ...]:
        """返回队列浅拷贝（read-only · 供 L2-02 pull 语义 · §3.3）。"""
        if level == AdviceLevel.WARN:
            return tuple(self._warn_queue)
        if level == AdviceLevel.SUGG:
            return tuple(self._sugg_queue)
        return ()


# 便捷构造：兼容直接传 `PushSuggestionCommand` 的调用方
def wrap_cmd_into_inbox(
    cmd: PushSuggestionCommand, *, received_at_ms: int = 0
) -> SuggestionInbox:
    """helper · cmd → inbox · 多数 test 场景直接传 cmd 更简洁。"""
    return SuggestionInbox.from_command(cmd, received_at_ms=received_at_ms)
