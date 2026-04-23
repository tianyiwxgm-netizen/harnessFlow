"""L2-01 账本回写 · IC-L2-07.

契约:
  - 只允许 caller='L2-02'（L2-02 意图选择器 · 打分后回写 success/fail 记忆）· 其他拒
  - 所有写操作必持 (project_id, capability) 级别的 L1-09 锁
  - PM-14: project_id 非空 · 否则 raise ValueError
  - 每次调用追加一行到 `projects/<pid>/skills/registry-cache/ledger.jsonl`

SLO:
  - P99 ≤ 50ms（见 tests/l1_05/test_l2_01_registry.py::test_ledger_write_slo_under_50ms_p99）

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md IC-L2-07
  - docs/superpowers/plans/Dev-γ-impl.md §3 Task 01.4
"""
from __future__ import annotations

import json
import pathlib
import time
from typing import Any


class LedgerPermissionError(PermissionError):
    """IC-L2-07: 非 L2-02 调用者被拒."""


class LedgerWriter:
    ALLOWED_CALLER = "L2-02"

    def __init__(self, project_root: pathlib.Path, lock: Any) -> None:
        self.project_root = pathlib.Path(project_root)
        self.path = self.project_root / "skills" / "registry-cache" / "ledger.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = lock

    def record(
        self,
        *,
        project_id: str,
        capability: str,
        skill_id: str,
        success: bool,
        failure_reason: str | None = None,
        caller: str = "L2-02",
    ) -> None:
        if not project_id:
            raise ValueError("LedgerWriter.record: project_id required (PM-14)")
        if caller != self.ALLOWED_CALLER:
            raise LedgerPermissionError(
                f"IC-L2-07: caller must be {self.ALLOWED_CALLER!r} · got {caller!r}"
            )
        rec = {
            "project_id": project_id,
            "capability": capability,
            "skill_id": skill_id,
            "success_count": 1 if success else 0,
            "failure_count": 0 if success else 1,
            "last_attempt_ts": int(time.time()),
            "failure_reason": failure_reason,
        }
        line = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        with self._lock.acquire(project_id=project_id, capability=capability):
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
