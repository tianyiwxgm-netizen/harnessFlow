"""L2-01 · HaltGuard · 响应面 4 硬 halt 守护.

当 L2-05 fsync 失败或 atomic_append 彻底失败时 · L2-01 必须：
1. 写 `_halt.marker` 文件（系统级 · 跨进程可见）
2. 记 `_halt_log.jsonl`（审计）
3. 拒绝所有后续 append · 返 `E_BUS_HALTED`

marker 文件位置：`<root>/projects/_global/halt.marker`（全系统共享）.

启动时必读 marker · 若存在 · EventBus 直接进 HALTED 状态 · 只有运维手工
`clear_halt(admin_token=...)` 可解锁.

WP06 强化：
- admin_token 校验走 constant-time compare（防 timing attack）
- 从 env `HARNESS_ADMIN_TOKEN` 读期望值（未设则全拒）
- marker 内容可解析（JSON）· halt_reason / halt_at 可被 BusHalted 异常带出
"""
from __future__ import annotations

import hmac
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ADMIN_TOKEN_ENV_VAR: str = "HARNESS_ADMIN_TOKEN"


class HaltGuard:
    """跨进程 halt 状态守护 · 支持跨进程持久 + admin_token 解锁."""

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

    def load_halt_info(self) -> dict[str, Any] | None:
        """读 marker 内容 · 用于 BusHalted 异常 · 返 None 未 halt."""
        if not self._marker_path.exists():
            return None
        try:
            content = self._marker_path.read_bytes().decode("utf-8")
            data = json.loads(content)
            return data if isinstance(data, dict) else None
        except (OSError, ValueError, UnicodeDecodeError):
            # marker 存在但不可解析 · 仍视为 halted · 返最小信息
            return {"reason": "unknown", "source": "marker_unreadable"}

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
        """运维解锁 · 需与环境变量 `HARNESS_ADMIN_TOKEN` 匹配.

        安全性：
        - 使用 `hmac.compare_digest` 做 constant-time 比较（防 timing attack）
        - 环境变量未设置 · 返 False（安全兜底 · 防测试污染生产）
        - 空 token 拒
        - 匹配成功 · 删 marker · append log（记录解锁）
        """
        if not admin_token:
            return False

        expected = os.environ.get(ADMIN_TOKEN_ENV_VAR, "")
        if not expected:
            return False  # 未配置 admin token · 无人可解锁

        if not hmac.compare_digest(admin_token.encode(), expected.encode()):
            # 记录失败尝试（审计 · 可选后续报警）
            self._log_clear_attempt(success=False, reason="token_mismatch")
            return False

        try:
            if self._marker_path.exists():
                self._marker_path.unlink()
            self._log_clear_attempt(success=True, reason="token_matched")
            return True
        except OSError:
            self._log_clear_attempt(success=False, reason="unlink_oserror")
            return False

    def _log_clear_attempt(self, *, success: bool, reason: str) -> None:
        """内部：记录 clear_halt 尝试 · 审计用（best-effort）."""
        now_iso = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
        record = {
            "timestamp": now_iso,
            "event": "halt_clear_attempt",
            "success": success,
            "reason": reason,
            "pid": os.getpid(),
        }
        try:
            with open(self._log_path, "ab") as f:
                f.write((json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
                os.fsync(f.fileno())
        except OSError:
            pass
