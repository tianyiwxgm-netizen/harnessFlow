"""L2-01 FS watcher · registry.yaml 热更新 · throttle 10s · 原子 swap.

职责:
  - 监听 `projects/<pid>/skills/registry-cache/registry.yaml` 的 modify 事件
  - 防抖：10s 内多次变更只触发一次 reload
  - reload 失败时保留当前 snapshot 不崩（E_REG_RELOAD_CONFLICT / E_REG_YAML_PARSE）
  - reload 成功调 RegistryQueryAPI.swap(new_snapshot) 原子替换

SLO:
  - fs_watch 触发到 swap 完成 P99 ≤ 500ms

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §3 Task 01.5
"""
from __future__ import annotations

import logging
import pathlib
import time
from typing import TYPE_CHECKING

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer as _Observer

    _HAS_WATCHDOG = True
except ImportError:  # pragma: no cover
    _HAS_WATCHDOG = False
    FileSystemEventHandler = object  # type: ignore[misc,assignment]
    _Observer = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .loader import RegistryLoader
    from .query_api import RegistryQueryAPI

_log = logging.getLogger(__name__)


class FsWatcher:
    """Registry.yaml 监听器 · 使用 watchdog · 防抖 + 原子 swap.

    典型生命周期:
        watcher = FsWatcher(loader, api, throttle_s=10.0)
        watcher.start()
        ...
        watcher.stop()

    测试直接路径（无文件系统）:
        watcher._on_change()   # 由 FileSystemEventHandler 调
        watcher.trigger_reload()   # 跳过 throttle 的显式 API (运维 reload)
    """

    def __init__(
        self,
        loader: "RegistryLoader",
        api: "RegistryQueryAPI",
        throttle_s: float = 10.0,
    ) -> None:
        self._loader = loader
        self._api = api
        self._throttle_s = float(throttle_s)
        self._last_reload_monotonic: float = -float("inf")
        self._observer = None
        self.reload_count: int = 0

    def start(self) -> None:
        if not _HAS_WATCHDOG:
            _log.warning("watchdog unavailable · fs_watcher disabled (trigger_reload only)")
            return
        handler = _RegistryChangeHandler(self)
        self._observer = _Observer()
        watch_dir = self._loader.yaml_path.parent
        watch_dir.mkdir(parents=True, exist_ok=True)
        self._observer.schedule(handler, str(watch_dir), recursive=False)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None

    def _on_change(self) -> bool:
        """文件系统变更回调 · 受 throttle 保护."""
        now = time.monotonic()
        if now - self._last_reload_monotonic < self._throttle_s:
            return False   # coalesce · 在 throttle 窗口内
        self._last_reload_monotonic = now
        return self.trigger_reload()

    def trigger_reload(self) -> bool:
        """显式 reload（跳 throttle · 运维 API）· True = 成功 + swap 完成."""
        try:
            new_snapshot = self._loader.load()
        except Exception as e:     # RegistryLoadError or unexpected
            _log.warning("E_REG_RELOAD_CONFLICT: reload failed · kept old snapshot: %s", e)
            return False
        self._api.swap(new_snapshot)
        self.reload_count += 1
        return True


class _RegistryChangeHandler(FileSystemEventHandler):
    """watchdog event handler → 转调 FsWatcher._on_change()."""

    def __init__(self, watcher: FsWatcher) -> None:
        super().__init__()
        self._watcher = watcher
        self._target = pathlib.Path(watcher._loader.yaml_path).name

    def on_modified(self, event) -> None:  # pragma: no cover - FS integration
        if event.is_directory:
            return
        if pathlib.Path(event.src_path).name == self._target:
            self._watcher._on_change()

    def on_created(self, event) -> None:  # pragma: no cover
        if event.is_directory:
            return
        if pathlib.Path(event.src_path).name == self._target:
            self._watcher._on_change()
