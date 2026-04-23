"""IC-09 事件订阅 · 把 L1-04 的 wp_done / wp_failed 事件解码成 domain 对象。

事件类型（来自 `architecture.md §7.5`）：
- `L1-04:wp_executed` · PASS 后广播
- `L1-04:wp_verified_pass` · S5 Verifier PASS
- `L1-04:wp_failed` · 任一级 FAIL

本订阅器把 raw event dict 解码成 `WPCompletionEvent` / `WPFailureEvent`，
再转给 `ProgressTracker` 处理。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WPCompletionEvent:
    wp_id: str
    project_id: str
    event_id: str
    commit_sha: str | None = None
    duration_ms: int | None = None
    verifier_verdict: str = "PASS"


@dataclass(frozen=True)
class WPFailureEvent:
    wp_id: str
    project_id: str
    event_id: str
    fail_level: str = "L2"
    reason_summary: str = ""
    failure_artifacts_ref: str | None = None


CompletionHandler = Callable[[WPCompletionEvent], None]
FailureHandler = Callable[[WPFailureEvent], None]


class ProgressEventSubscriber:
    """将 event_bus subscribe 回调解码成 domain 事件并分发。

    典型用法：
        sub = ProgressEventSubscriber(on_done=tracker.on_wp_done, on_failed=tracker.on_wp_failed)
        event_bus.subscribe(sub)
    """

    COMPLETION_TYPES: frozenset[str] = frozenset({
        "L1-04:wp_executed",
        "L1-04:wp_verified_pass",
    })
    FAILURE_TYPES: frozenset[str] = frozenset({
        "L1-04:wp_failed",
    })

    def __init__(
        self,
        on_done: CompletionHandler | None = None,
        on_failed: FailureHandler | None = None,
    ) -> None:
        self._on_done = on_done
        self._on_failed = on_failed

    def __call__(self, payload: dict[str, Any]) -> None:
        """event_bus.subscribe 回调入口。"""
        event_type = payload.get("type", "")
        if event_type in self.COMPLETION_TYPES:
            if self._on_done is None:
                return
            done_ev = self._decode_completion(payload)
            if done_ev is not None:
                self._on_done(done_ev)
        elif event_type in self.FAILURE_TYPES:
            if self._on_failed is None:
                return
            fail_ev = self._decode_failure(payload)
            if fail_ev is not None:
                self._on_failed(fail_ev)
        # 其他类型事件 · 忽略

    @staticmethod
    def _decode_completion(payload: dict[str, Any]) -> WPCompletionEvent | None:
        content = payload.get("content", {})
        wp_id = content.get("wp_id")
        pid = payload.get("project_id")
        if not wp_id or not pid:
            return None
        return WPCompletionEvent(
            wp_id=wp_id,
            project_id=pid,
            event_id=payload.get("event_id", ""),
            commit_sha=content.get("commit_sha"),
            duration_ms=content.get("duration_ms"),
            verifier_verdict=content.get("verifier_verdict", "PASS"),
        )

    @staticmethod
    def _decode_failure(payload: dict[str, Any]) -> WPFailureEvent | None:
        content = payload.get("content", {})
        wp_id = content.get("wp_id")
        pid = payload.get("project_id")
        if not wp_id or not pid:
            return None
        return WPFailureEvent(
            wp_id=wp_id,
            project_id=pid,
            event_id=payload.get("event_id", ""),
            fail_level=content.get("fail_level", "L2"),
            reason_summary=content.get("reason_summary", ""),
            failure_artifacts_ref=content.get("failure_artifacts_ref"),
        )
