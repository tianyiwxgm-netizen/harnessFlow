"""IC-14 + IC-15 出口封装 · L2-05 → 主会话 L1-04 / L1-01。

IC-14 `push_rollback_route`：连续 3 次失败时，L2-05 推送 RollbackAdvice 给 L1-07 → L1-01。
IC-15 `request_hard_halt`：死锁等极端情况，L2-05 请求 L1-01 硬停。

本层是"接口占位"：真实 L1-01 / L1-04 / L1-07 未到位时，走注入的 `Emitter` 接口（duck-typed）。
测试期用 `_CapturingEmitter` 即可 assert。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from app.l1_03.rollback.schemas import RollbackAdvice


@dataclass
class RollbackRoute:
    """IC-14 的入参格式（往下游传）。"""

    route_id: str
    project_id: str
    advice: RollbackAdvice
    target_l1: str = "L1-04"  # 默认路由到 Quality Loop，也可切 "L1-01"


PushRollbackEmitter = Callable[[RollbackRoute], None]
HaltEmitter = Callable[[str, str], None]
"""`(project_id, reason) -> None`。"""


@dataclass
class Escalator:
    """IC-14 / IC-15 的 emitter 聚合。

    默认 emitter 为 capturing list（便于测试 assert）· 生产注入真实端点。
    """

    on_push_rollback: PushRollbackEmitter | None = None
    on_request_halt: HaltEmitter | None = None
    captured_routes: list[RollbackRoute] = field(default_factory=list)
    captured_halts: list[tuple[str, str]] = field(default_factory=list)

    def push_rollback_route(self, route: RollbackRoute) -> None:
        self.captured_routes.append(route)
        if self.on_push_rollback is not None:
            self.on_push_rollback(route)

    def request_hard_halt(self, project_id: str, reason: str) -> None:
        self.captured_halts.append((project_id, reason))
        if self.on_request_halt is not None:
            self.on_request_halt(project_id, reason)
