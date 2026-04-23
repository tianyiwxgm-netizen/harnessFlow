"""L2-01 · HaltGuard · 响应面 4 硬 halt 守护.

当 L2-05 fsync 失败或 atomic_append 彻底失败时 · L2-01 必须：
1. 写 `_halt.marker` 文件（系统级 · 跨进程可见）
2. 记 `_halt_log.jsonl`（审计）
3. 拒绝所有后续 append · 返 `E_BUS_HALTED`

marker 文件位置：`<root>/projects/_global/halt.marker`（全系统共享）.

启动时必读 marker · 若存在 · EventBus 直接进 HALTED 状态 · 只有运维手工
`clear_halt(admin_token=...)` 可解锁（WP06 实现 · 本 WP 仅最小骨架）.
"""
from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path


class HaltGuard:
    """跨进程 halt 状态守护 · 最小实现（WP06 扩展 clear_halt admin_token）."""

    def __init__(self, global_dir: Path) -> None:
        """
        Args:
            global_dir: `<root>/projects/_global/` · halt marker 所在目录.
        """
        self._global_dir = global_dir
        self._marker_path = global_dir / "halt.marker"
        self._log_path = global_dir / "halt_log.jsonl"
        self._global_dir.mkdir(parents=True, exist_ok=True)

    @property
    def marker_path(self) -> Path:
        return self._marker_path

    def is_halted(self) -> bool:
        """跨进程可见 · 只读检查."""
        return self._marker_path.exists()

    def mark_halt(self, *, reason: str, source: str, correlation_id: str | None = None) -> None:
        """写 marker + append log.

        幂等：若已 halted · 仍追加 log（记录二次 halt 原因）· marker 不重写.
        """
        now_iso = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
        record = {
            "timestamp": now_iso,
            "reason": reason,
            "source": source,
            "correlation_id": correlation_id,
            "pid": os.getpid(),
            "monotonic_ms": time.monotonic() * 1000.0,
        }
        # append 审计 log（best-effort）
        try:
            with open(self._log_path, "ab") as f:
                f.write((json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
                os.fsync(f.fileno())
        except OSError:
            # halt 期间 log 写失败不阻止 marker 写（marker 是兜底）
            pass

        # 写 marker（若不存在）· best-effort · 盘满也尽量留痕
        if not self._marker_path.exists():
            try:
                with open(self._marker_path, "xb") as f:
                    f.write(json.dumps(record, sort_keys=True).encode("utf-8"))
                    os.fsync(f.fileno())
            except FileExistsError:
                pass  # 竞态 · 另一进程已 halt · OK
            except OSError:
                # 极端情况（盘满）· 不抛 · halt 状态由 log 间接表达
                pass

    def clear_halt(self, *, admin_token: str) -> bool:
        """仅运维 CLI 可调 · WP06 补 admin_token 严格校验.

        当前 WP04 最小实现：admin_token 非空即可（用于测试复用 fixture）.
        生产安全：WP06 从 config 读 hashed token · 只允许手工 CLI 调.
        """
        if not admin_token:
            return False
        try:
            if self._marker_path.exists():
                self._marker_path.unlink()
                return True
        except OSError:
            return False
        return False
