"""L1-01 L2-06 Supervisor 建议接收器 · 主入口 shim（WP06 最小）。

完整 AdviceQueue / watchdog / 4 级 counter / clear_block 留给后续 WP。
本 WP 只需：
1. 暴露 3 个 consume 方法（suggestion / rollback / halt）
2. 内部组装对应 consumer
3. 统一 session_pid + clock + event_bus 注入

实现在后续 commit 中逐步补齐 · 此处先给最小骨架占位 · 便于 __init__ 导入。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SupervisorReceiver:
    """L2-06 主入口占位 · impl 在后续 commit 随 consumer 落地。"""

    session_pid: str = ""

