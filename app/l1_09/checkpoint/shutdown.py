"""L2-04 · begin_shutdown · 对齐 3-1 §6.3.

流程：
- 通知所有 SnapshotJob · state = SHUTTING_DOWN
- drain: 等 in-flight snapshot 完 · 超 3s timeout
- 每 ACTIVE pid 做 final snapshot
- ack · 总耗时 ≤ 5s · 返 ShutdownToken

第二次 SIGINT:
- signal_handler 捕获 · os._exit(2)
- 下次启动走 Tier 2 recovery
"""
from __future__ import annotations

import os
import signal
import threading
import time
from datetime import UTC, datetime, timedelta

import ulid

from app.l1_09.checkpoint.schemas import (
    ShutdownDrainTimeout,
    ShutdownReentrant,
    ShutdownState,
    ShutdownToken,
    Trigger,
)


SHUTDOWN_DRAIN_S = 3
SHUTDOWN_TOTAL_DEADLINE_S = 5


class ShutdownOrchestrator:
    """单例 · graceful shutdown coordinator."""

    def __init__(
        self,
        *,
        snapshot_job=None,
        event_bus=None,
        lock_manager=None,
        subscriber_notifier=None,
    ) -> None:
        self._snapshot_job = snapshot_job
        self._bus = event_bus
        self._lm = lock_manager
        self._subscriber_notifier = subscriber_notifier

        self._token: ShutdownToken | None = None
        self._lock = threading.Lock()
        self._sigint_count = 0
        self._registered_signal = False

    def register_signal_handler(self) -> None:
        """SIGTERM / SIGINT 捕获."""
        if self._registered_signal:
            return
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        self._registered_signal = True

    def _handle_signal(self, signum, frame) -> None:
        self._sigint_count += 1
        if self._sigint_count >= 2:
            # 第二次 · 强退
            os._exit(2)
        # 第一次 · 触发 graceful shutdown（同步）
        try:
            self.begin_shutdown(reason="sigint")
        except Exception:
            os._exit(1)

    def begin_shutdown(
        self,
        *,
        reason: str = "manual_quit",
        active_projects: list[str] | None = None,
    ) -> ShutdownToken:
        """§3.2.3 begin_shutdown."""
        with self._lock:
            if self._token is not None:
                # REENTRANT · 返原 token
                return self._token

            now = datetime.now(UTC)
            token_id = f"sd-{ulid.new()}"
            drain_deadline = (now + timedelta(seconds=SHUTDOWN_DRAIN_S)).isoformat()
            self._token = ShutdownToken(
                token_id=token_id,
                requested_at=now.isoformat(),
                reason=reason,
                drain_deadline=drain_deadline,
                state=ShutdownState.REQUESTED,
            )

        start_s = time.time()

        # Drain phase
        self._drain(start_s)

        # Final snapshot phase
        snapshotted: list[str] = []
        final_cp_id = None
        pids = active_projects or []
        if self._snapshot_job is not None and pids:
            for pid in pids:
                if time.time() - start_s > SHUTDOWN_TOTAL_DEADLINE_S:
                    break
                try:
                    result = self._snapshot_job.take_snapshot(
                        pid, trigger=Trigger.SHUTDOWN_FINAL
                    )
                    snapshotted.append(pid)
                    final_cp_id = result.checkpoint_id
                except Exception:
                    # 单个 pid fail 不阻断其他 pid
                    pass

        # Force release all locks (L2-02)
        if self._lm is not None:
            try:
                self._lm.force_release_all(
                    reason="shutdown", caller="L2-04-shutdown"
                )
            except Exception:
                pass

        flush_duration_ms = int((time.time() - start_s) * 1000)

        # Notify subscribers
        if self._subscriber_notifier is not None:
            try:
                self._subscriber_notifier({
                    "event": "L1-09:shutdown_clean",
                    "token_id": token_id,
                    "reason": reason,
                    "projects_snapshotted": snapshotted,
                })
            except Exception:
                pass

        with self._lock:
            # 更新为 ACKED
            self._token = ShutdownToken(
                token_id=token_id,
                requested_at=self._token.requested_at,
                reason=reason,
                drain_deadline=drain_deadline,
                state=ShutdownState.ACKED,
                final_checkpoint_id=final_cp_id,
                flush_duration_ms=flush_duration_ms,
                projects_snapshotted=snapshotted,
            )
            return self._token

    def _drain(self, start_s: float) -> None:
        """drain in-flight events · 超 3s 时间窗."""
        # 简化：等 drain timeout（真实 bus 应提供 in_flight_count API）
        deadline = start_s + SHUTDOWN_DRAIN_S
        # 允许 bus / subscriber 自行 flush
        while time.time() < deadline:
            # 询问 bus 是否 clear · 若接口不在 · 短暂等即可
            if self._bus is None:
                break
            in_flight = getattr(self._bus, "in_flight_count", lambda: 0)()
            if in_flight == 0:
                break
            time.sleep(0.05)

    def is_shutting_down(self) -> bool:
        with self._lock:
            return self._token is not None and self._token.state != ShutdownState.ACKED


__all__ = ["ShutdownOrchestrator", "SHUTDOWN_DRAIN_S", "SHUTDOWN_TOTAL_DEADLINE_S"]
