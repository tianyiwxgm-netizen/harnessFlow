"""L2-02 StartupProducer · L2-01 调用入口 · 对齐 tech §3.2。

职责：
  - 接收 KickoffRequest（IC-L2-01）· 校验 stage=='S1' + caller_l2=='L2-01' + user_initial_goal 非空
  - 委托 produce_kickoff 跑 8 步产出
  - 捕获 KickoffError · 包装为 KickoffResponse(status='err', result=KickoffErr)
  - 成功 → KickoffResponse(status='ok', result=KickoffSuccess)
  - 全程 latency_ms 计时
"""
from __future__ import annotations

import time
from typing import Any

from app.project_lifecycle.kickoff.errors import KickoffError
from app.project_lifecycle.kickoff.producer_core import produce_kickoff
from app.project_lifecycle.kickoff.schemas import (
    KickoffErr,
    KickoffRequest,
    KickoffResponse,
)


_INVALID_REQUEST_ERR = "E_L102_L202_TRIGGER_INVALID"


class StartupProducer:
    """L2-02 public API · DI 模式持 brainstorm/template/event_bus/project_root。"""

    def __init__(
        self,
        *,
        brainstorm: Any,
        template: Any,
        event_bus: Any,
        project_root: str,
    ) -> None:
        self._brainstorm = brainstorm
        self._template = template
        self._event_bus = event_bus
        self._project_root = project_root

    def kickoff_create_project(self, req: KickoffRequest) -> KickoffResponse:
        t0 = time.perf_counter()

        # 入参校验（返 err · 不 raise）
        invalid = self._validate_request(req)
        if invalid is not None:
            return KickoffResponse(
                trigger_id=req.trigger_id,
                status="err",
                result=invalid,
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        # 运行 produce_kickoff · 捕获 KickoffError
        try:
            success = produce_kickoff(
                req.user_initial_goal,
                brainstorm=self._brainstorm,
                template=self._template,
                event_bus=self._event_bus,
                project_root=self._project_root,
                trim_level=req.trim_level,
                prior_context=self._prior_context(req),
            )
        except KickoffError as exc:
            return KickoffResponse(
                trigger_id=req.trigger_id,
                status="err",
                result=KickoffErr(
                    err_code=exc.error_code,
                    reason=exc.message,
                    suggested_action=None,
                    partial_project_id=exc.project_id,
                ),
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        # 若 brainstorm 超 3 轮或未收敛 · 标 degraded（仍返章程 · 但 Gate 侧应显 incomplete）
        status = "degraded" if success.clarification_incomplete else "ok"
        return KickoffResponse(
            trigger_id=req.trigger_id,
            status=status,
            result=success,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    # ---- internals ----

    def _validate_request(self, req: KickoffRequest) -> KickoffErr | None:
        if req.stage != "S1":
            return KickoffErr(
                err_code=_INVALID_REQUEST_ERR,
                reason=f"invalid stage {req.stage!r} · this L2 only accepts S1",
            )
        if req.caller_l2 != "L2-01":
            return KickoffErr(
                err_code=_INVALID_REQUEST_ERR,
                reason=f"caller_l2 must be L2-01 · got {req.caller_l2!r}",
            )
        if not req.user_initial_goal or not req.user_initial_goal.strip():
            return KickoffErr(
                err_code=_INVALID_REQUEST_ERR,
                reason="user_initial_goal must be non-empty",
            )
        return None

    def _prior_context(self, req: KickoffRequest) -> str | None:
        """S1 re-open 时从 preexisting_charter_path 读历史作 brainstorm prior_context。"""
        if not req.preexisting_charter_path:
            return None
        from pathlib import Path
        p = Path(req.preexisting_charter_path)
        if p.exists():
            return p.read_text(encoding="utf-8")
        return None
