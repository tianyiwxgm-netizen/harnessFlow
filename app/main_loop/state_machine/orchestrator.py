"""L2-03 状态机编排器 · 主入口 transition()。

对齐 tech §3.1 request_state_transition + §11 错误处理:
  - 12 合法边硬拒 (frozenset O(1))
  - 字段级校验 (project_id / reason≥20 / evidence_refs≥1 / 7-enum)
  - idempotency (LRU · transition_id)
  - snapshot 版本乐观锁
  - audit_entry_id 透出 (可选挂 L2-05)

本 L2 内部不含 hook 执行 (hook 留给后续 WP);当前 orchestrator 只覆盖:
  §3.1.4 行表中除 HOOK_FAIL / AUDIT_UNAVAILABLE / REPLAY_* 外的硬拒错误码。

Thread-safe 说明:
  使用 threading.Lock 实现 §3.1 "一次一转换"并发语义 (prd §10.4 硬约束 #5):
  第二个并发请求直接 accepted=false + reason=concurrent。
"""
from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.main_loop.state_machine.idempotency_tracker import IdempotencyTracker
from app.main_loop.state_machine.schemas import (
    E_TRANS_CONCURRENT,
    E_TRANS_CROSS_PROJECT,
    E_TRANS_INVALID_NEXT,
    E_TRANS_INVALID_STATE_ENUM,
    E_TRANS_NO_EVIDENCE,
    E_TRANS_NO_PROJECT_ID,
    E_TRANS_REASON_TOO_SHORT,
    E_TRANS_STATE_MISMATCH,
    E_TRANS_TRANSITION_ID_FORMAT,
    MIN_REASON_LENGTH,
    STATES,
    State,
    StateMachineError,
    StateMachineSnapshot,
    TransitionRequest,
    TransitionResult,
)
from app.main_loop.state_machine.transition_table import is_allowed


_TRANSITION_ID_RE = re.compile(r"^trans-[0-9a-fA-F-]{8,}$")
_PROJECT_ID_RE = re.compile(r"^pid-[0-9a-fA-F-]{8,}$")


@dataclass
class _ConcurrencyLock:
    """非阻塞 try-lock · 对齐 §3.1 并发语义 (第二个请求立即拒绝)。"""

    _lock: threading.Lock = field(default_factory=threading.Lock)

    def try_acquire(self) -> bool:
        return self._lock.acquire(blocking=False)

    def release(self) -> None:
        self._lock.release()


class StateMachineOrchestrator:
    """L2-03 主入口 · transition(req) → TransitionResult。

    典型用法:
        orch = StateMachineOrchestrator(project_id="pid-...")
        result = orch.transition(req)

    API:
      - transition(req)          — 核心 (§3.1)
      - allowed_next(from_state) — 只读查询 (§3.2)
      - get_current_state()      — 只读 snapshot (§3.3)
      - snapshot                 — 只读属性 (测试辅助)
    """

    def __init__(
        self,
        *,
        project_id: str,
        clock: Callable[[], datetime] | None = None,
        audit_sink: Callable[[TransitionResult], str] | None = None,
        idempotency_tracker: IdempotencyTracker | None = None,
        initial_state: State = "NOT_EXIST",
    ) -> None:
        if not project_id:
            raise StateMachineError(
                error_code=E_TRANS_NO_PROJECT_ID,
                message="project_id required at construction",
            )
        self._bound_project_id = project_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._audit_sink = audit_sink
        self._tracker = idempotency_tracker or IdempotencyTracker()
        self._lock = _ConcurrencyLock()
        self._snapshot = StateMachineSnapshot(
            project_id=project_id, current_state=initial_state, version=0
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    @property
    def snapshot(self) -> StateMachineSnapshot:
        """只读 snapshot · 测试辅助 (不暴露写入路径)。"""
        return self._snapshot

    @property
    def project_id(self) -> str:
        return self._bound_project_id

    def get_current_state(self) -> State:
        """§3.3 · 纯内存读 · P99 ≤ 5ms。"""
        return self._snapshot.current_state

    def allowed_next(self, from_state: State) -> tuple[State, ...]:
        """§3.2 · 委托 transition_table.allowed_next。"""
        # 直接复用 module 级函数 (避免名称遮蔽 · 局部 import)
        from app.main_loop.state_machine.transition_table import allowed_next as _an

        return _an(from_state)

    def transition(self, req: TransitionRequest) -> TransitionResult:
        """核心主入口 · §3.1 request_state_transition。

        失败语义 (§3.1.4):
          - INVALID_NEXT / STATE_MISMATCH / CONCURRENT → accepted=false
          - NO_PROJECT_ID / CROSS_PROJECT / REASON_TOO_SHORT / NO_EVIDENCE /
            INVALID_STATE_ENUM / TRANSITION_ID_FORMAT → raise StateMachineError
          - IDEMPOTENT_REPLAY → raise (tracker 内部)

        成功:
          - snapshot.current_state ← to · version += 1
          - history.append(result)
          - audit_sink(result) → audit_entry_id (若挂载)
          - tracker.put(req, result)
        """
        # ----- 1. 字段级硬约束校验 (抛异常) -----
        self._validate_request(req)

        # ----- 2. 幂等查询 (可能抛 REPLAY) -----
        cached = self._tracker.lookup(req)
        if cached is not None:
            return cached

        # ----- 3. 并发单锁 (非阻塞) -----
        if not self._lock.try_acquire():
            return self._reject(
                req,
                reason="concurrent transition in progress",
                error_code=E_TRANS_CONCURRENT,
            )
        try:
            # ----- 4. snapshot 一致性 -----
            if self._snapshot.current_state != req.from_state:
                return self._reject(
                    req,
                    reason=(
                        f"state mismatch: snapshot={self._snapshot.current_state!r} "
                        f"req.from={req.from_state!r}"
                    ),
                    error_code=E_TRANS_STATE_MISMATCH,
                )

            # ----- 5. allowed_next 合法性 -----
            if not is_allowed(req.from_state, req.to_state):
                return self._reject(
                    req,
                    reason=(
                        f"{req.from_state} → {req.to_state} not in allowed_next "
                        f"(12 edges table)"
                    ),
                    error_code=E_TRANS_INVALID_NEXT,
                )

            # ----- 6. 提交转换 (原子区间) -----
            ts = _iso_now(self._clock)
            self._snapshot.current_state = req.to_state
            self._snapshot.version += 1

            result = TransitionResult(
                transition_id=req.transition_id,
                accepted=True,
                new_state=req.to_state,
                ts_applied=ts,
                reason=None,
                error_code=None,
                audit_entry_id=None,
            )

            # ----- 7. 审计 (可选) -----
            audit_id = None
            if self._audit_sink is not None:
                try:
                    audit_id = self._audit_sink(result)
                except Exception:
                    # 审计失败不回滚 state;上层 WP 需要时补 E_TRANS_AUDIT_UNAVAILABLE
                    audit_id = None
            # 覆盖 audit_entry_id (frozen dataclass · 重建)
            result = TransitionResult(
                transition_id=result.transition_id,
                accepted=result.accepted,
                new_state=result.new_state,
                ts_applied=result.ts_applied,
                reason=result.reason,
                error_code=result.error_code,
                audit_entry_id=audit_id,
            )

            # ----- 8. history + tracker -----
            self._snapshot.history.append(result)
            self._tracker.put(req, result)

            return result
        finally:
            self._lock.release()

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _validate_request(self, req: TransitionRequest) -> None:
        # project_id 非空 + 格式 + 绑定
        if not req.project_id:
            raise StateMachineError(
                error_code=E_TRANS_NO_PROJECT_ID,
                message="project_id empty",
            )
        if not _PROJECT_ID_RE.match(req.project_id):
            raise StateMachineError(
                error_code=E_TRANS_NO_PROJECT_ID,
                message=f"project_id format invalid: {req.project_id!r}",
                project_id=req.project_id,
            )
        if req.project_id != self._bound_project_id:
            raise StateMachineError(
                error_code=E_TRANS_CROSS_PROJECT,
                message=(
                    f"cross-project: bound={self._bound_project_id!r} "
                    f"req={req.project_id!r}"
                ),
                project_id=req.project_id,
            )

        # transition_id 格式
        if not req.transition_id:
            raise StateMachineError(
                error_code=E_TRANS_TRANSITION_ID_FORMAT,
                message="transition_id empty",
                project_id=req.project_id,
            )
        if not _TRANSITION_ID_RE.match(req.transition_id):
            raise StateMachineError(
                error_code=E_TRANS_TRANSITION_ID_FORMAT,
                message=f"transition_id format invalid: {req.transition_id!r}",
                project_id=req.project_id,
            )

        # 7-enum 校验
        if req.from_state not in STATES:
            raise StateMachineError(
                error_code=E_TRANS_INVALID_STATE_ENUM,
                message=f"from_state {req.from_state!r} not in 7-enum",
                project_id=req.project_id,
            )
        if req.to_state not in STATES:
            raise StateMachineError(
                error_code=E_TRANS_INVALID_STATE_ENUM,
                message=f"to_state {req.to_state!r} not in 7-enum",
                project_id=req.project_id,
            )

        # reason minLength
        if not req.reason or len(req.reason) < MIN_REASON_LENGTH:
            raise StateMachineError(
                error_code=E_TRANS_REASON_TOO_SHORT,
                message=(
                    f"reason length {len(req.reason or '')} < "
                    f"{MIN_REASON_LENGTH}"
                ),
                project_id=req.project_id,
            )

        # evidence_refs minItems=1
        if not req.evidence_refs or len(req.evidence_refs) < 1:
            raise StateMachineError(
                error_code=E_TRANS_NO_EVIDENCE,
                message="evidence_refs minItems=1 violated",
                project_id=req.project_id,
            )

    def _reject(
        self,
        req: TransitionRequest,
        *,
        reason: str,
        error_code: str,
    ) -> TransitionResult:
        """构造 accepted=false 结果 · 走 tracker · history append。"""
        ts = _iso_now(self._clock)
        result = TransitionResult(
            transition_id=req.transition_id,
            accepted=False,
            new_state=self._snapshot.current_state,
            ts_applied=ts,
            reason=reason,
            error_code=error_code,
            audit_entry_id=None,
        )
        self._snapshot.history.append(result)
        # 失败也缓存 (同 transition_id 重放拿同拒绝结果 · 防止重复 side effect)
        self._tracker.put(req, result)
        return result


def _iso_now(clock: Callable[[], datetime]) -> str:
    """ISO-8601 UTC · microsecond · Z 后缀 (对齐 stage_gate controller)。"""
    return (
        clock()
        .astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def generate_transition_id() -> str:
    """辅助 · 给 IC01Producer / 测试生成 trans-{uuid} 字符串。"""
    return f"trans-{uuid.uuid4()}"
