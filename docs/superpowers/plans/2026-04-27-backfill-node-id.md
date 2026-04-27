# Backfill stage_artifacts.node_id Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) — single-session B-route lite execution.

**Goal:** 写 `scripts/backfill_node_id_in_stage_artifacts.py` + 测试，把 21 个历史 task-board 的 stage_artifacts[] 升级为 `node_id`-tagged，让 dashboard 的 23 个任务卡片都能显示真实 outputs_actual > 0。

**Architecture:** 单文件脚本 + 单文件测试。从 task-board 的 `state_history` / `verifier_report` / `supervisor_interventions` / `retro_link` / `commit_sha` / `artifacts[]` / `goal_anchor` 等已有字段推导 N1-N13 的 outputs，写回 `stage_artifacts[]`。Idempotent：再跑不重复加 entry。e2e-migration 已 13/13 直接 skip。

**Tech Stack:** Python 3.11+ stdlib (json, pathlib, argparse, hashlib)，pytest，no external deps。

---

## File Structure

- **Create**: `scripts/backfill_node_id_in_stage_artifacts.py` (~180 行)
  - `derive_per_node_artifacts(tb: dict) -> list[dict]` — 推导 13 节点 outputs
  - `apply_backfill(tb: dict) -> tuple[dict, int]` — 合并到 stage_artifacts，返回 (new_tb, n_added)
  - `is_already_backfilled(tb: dict) -> bool` — 判幂等
  - `main()` — argparse: --dry-run / --task-id / --all
- **Create**: `tests/unit/__init__.py`（如果不存在）+ `tests/unit/test_backfill_node_id.py` (~120 行)
  - `test_derive_per_node_artifacts_min_fields` — 给最少字段（task_id + state_history）能跑出 13 entries
  - `test_apply_backfill_skips_already_tagged` — e2e-migration shape 不被改
  - `test_apply_backfill_appends_n11_when_commit_sha_exists`
  - `test_idempotent_second_run_no_change`
  - `test_main_dry_run_doesnt_write`
- **Modify**: 无（不动 main skill / pipeline_catalog / mock_data）

---

## Task 1: 测试先行 + 框架函数空 stub

**Files:**
- Create: `tests/unit/__init__.py`（空）
- Create: `tests/unit/test_backfill_node_id.py`
- Create: `scripts/backfill_node_id_in_stage_artifacts.py`（仅签名 + 空体）

- [ ] **Step 1: 写 5 个测试（红状态）**

```python
# tests/unit/test_backfill_node_id.py
import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from backfill_node_id_in_stage_artifacts import (
    derive_per_node_artifacts,
    apply_backfill,
    is_already_backfilled,
)


MIN_TB = {
    "task_id": "test-min-20260427T0000Z",
    "current_state": "CLOSED",
    "goal_anchor": {"text": "demo goal", "hash": "deadbeef"},
    "state_history": [
        {"state": "INIT", "timestamp": "2026-04-27T05:00:00Z"},
        {"state": "CLARIFY", "timestamp": "2026-04-27T05:01:00Z"},
        {"state": "PLAN", "timestamp": "2026-04-27T05:02:00Z"},
        {"state": "IMPL", "timestamp": "2026-04-27T05:03:00Z"},
        {"state": "VERIFY", "timestamp": "2026-04-27T05:04:00Z"},
        {"state": "COMMIT", "timestamp": "2026-04-27T05:05:00Z"},
        {"state": "CLOSED", "timestamp": "2026-04-27T05:06:00Z"},
    ],
    "stage_artifacts": [],
    "verifier_report": {"overall": "PASS"},
    "supervisor_interventions": [{"level": "INFO", "code": "X"}],
    "commit_sha": "abc1234",
    "retro_link": "retros/test-min-20260427T0000Z.md",
    "size": "S",
    "task_type": "重构",
    "risk": "低",
}


def test_derive_per_node_artifacts_returns_13():
    out = derive_per_node_artifacts(MIN_TB)
    assert len(out) == 13
    assert [a["node_id"] for a in out] == [f"N{i}" for i in range(1, 14)]


def test_apply_backfill_appends_when_empty():
    tb = json.loads(json.dumps(MIN_TB))
    new_tb, n_added = apply_backfill(tb)
    assert n_added == 13
    assert len(new_tb["stage_artifacts"]) == 13
    node_ids = [sa["node_id"] for sa in new_tb["stage_artifacts"]]
    assert "N11" in node_ids  # commit_sha exists → N11 must emit


def test_apply_backfill_skips_already_tagged():
    tb = json.loads(json.dumps(MIN_TB))
    tb["stage_artifacts"] = [
        {"node_id": "N1", "outputs": {"x": 1}},
        {"node_id": "N3", "outputs": {"x": 1}},
    ]
    assert is_already_backfilled(tb) is False  # 只 2 个，不算 done
    # full 13-tagged
    tb["stage_artifacts"] = [{"node_id": f"N{i}", "outputs": {}} for i in range(1, 14)]
    assert is_already_backfilled(tb) is True


def test_idempotent_second_run_no_change():
    tb = json.loads(json.dumps(MIN_TB))
    tb1, n1 = apply_backfill(tb)
    tb2, n2 = apply_backfill(tb1)
    assert n2 == 0  # 第二次 0 改动


def test_n11_outputs_includes_commit_sha():
    out = derive_per_node_artifacts(MIN_TB)
    n11 = next(a for a in out if a["node_id"] == "N11")
    assert "commit_sha" in n11["outputs"]
    assert n11["outputs"]["commit_sha"] == "abc1234"
```

- [ ] **Step 2: 写空 stub（红测试）**

```python
# scripts/backfill_node_id_in_stage_artifacts.py
"""Backfill stage_artifacts[].node_id for historical task-boards.

Derives 13-node outputs from existing task-board fields (state_history,
verifier_report, supervisor_interventions, commit_sha, retro_link, etc).
"""
from __future__ import annotations

def derive_per_node_artifacts(tb: dict) -> list[dict]:
    raise NotImplementedError

def apply_backfill(tb: dict) -> tuple[dict, int]:
    raise NotImplementedError

def is_already_backfilled(tb: dict) -> bool:
    raise NotImplementedError

def main() -> int:
    raise NotImplementedError

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 3: 跑测试看红**

`pytest tests/unit/test_backfill_node_id.py -v` → 5 FAIL（NotImplementedError）

---

## Task 2: 实现 derive_per_node_artifacts + apply_backfill + is_already_backfilled

- [ ] **Step 1: 实现 13 节点推导**

  - N1：从 `task_id` + `initial_user_input` / `task_description_initial`
  - N2：从 `goal_anchor.text` 推断"已 read 文档"（保守列固定）
  - N3：从 `goal_anchor` 字段（hash + text + claude_md_path）
  - N4：B/D 路 skipped；C/E 路写"charter_lite"
  - N5：从 `dod_expression` 或 `goal_anchor.text` 摘 PRD-lite
  - N6：从 `verifier_report.evidence_checks[]` 或 default
  - N7：从 `route_decision.rationale` + `dod_expression`
  - N8：从 `dod_expression`
  - N9：从 `state_history` 长度 + size 推 WBS 数量
  - N10：从 `verifier_report.overall` + `evidence_checks[]`
  - N11：从 `commit_sha` + `artifacts[]`
  - N12：从 `supervisor_interventions[]`
  - N13：从 `retro_link` + `failure_archive_refs` + `final_outcome`

- [ ] **Step 2: 实现 idempotent + skip 逻辑**

  ```python
  def is_already_backfilled(tb: dict) -> bool:
      sas = tb.get("stage_artifacts") or []
      tagged = [s for s in sas if s.get("node_id") in {f"N{i}" for i in range(1, 14)}]
      return len(set(s["node_id"] for s in tagged)) == 13
  ```

  ```python
  def apply_backfill(tb: dict) -> tuple[dict, int]:
      if is_already_backfilled(tb):
          return tb, 0
      existing = {s.get("node_id") for s in (tb.get("stage_artifacts") or []) if s.get("node_id")}
      new_entries = [a for a in derive_per_node_artifacts(tb) if a["node_id"] not in existing]
      tb.setdefault("stage_artifacts", []).extend(new_entries)
      return tb, len(new_entries)
  ```

- [ ] **Step 3: 跑测试到绿**

  `pytest tests/unit/test_backfill_node_id.py -v` → 5 PASS

---

## Task 3: 实现 main() + dry-run + 跑全 21 个 task-board

- [ ] **Step 1: argparse + main**

  ```python
  def main() -> int:
      ap = argparse.ArgumentParser(description="Backfill stage_artifacts.node_id for task-boards")
      ap.add_argument("--dry-run", action="store_true")
      ap.add_argument("--task-id", help="Only one task")
      ap.add_argument("--task-boards-dir", default="task-boards")
      args = ap.parse_args()
      tb_dir = Path(args.task_boards_dir)
      patterns = [tb_dir.glob("*.json"), tb_dir.glob("legacy/*.json"), tb_dir.glob("cross-project/*.json")]
      total_changed = 0
      for paths in patterns:
          for p in paths:
              if args.task_id and p.stem != args.task_id: continue
              tb = json.loads(p.read_text(encoding="utf-8"))
              new_tb, n = apply_backfill(tb)
              if n > 0:
                  total_changed += 1
                  if not args.dry_run:
                      p.write_text(json.dumps(new_tb, ensure_ascii=False, indent=2), encoding="utf-8")
                  print(f"{'DRY ' if args.dry_run else ''}{p.name}: +{n} nodes")
              else:
                  print(f"{p.name}: skip (already complete)")
      print(f"\ntotal changed: {total_changed}")
      return 0
  ```

- [ ] **Step 2: 跑 dry-run 看输出**

  `python scripts/backfill_node_id_in_stage_artifacts.py --dry-run` → 21 个 changed，1 skip

- [ ] **Step 3: 真跑写盘**

  `python scripts/backfill_node_id_in_stage_artifacts.py` → 21 task-boards 改动

- [ ] **Step 4: curl /api/tasks/<id> 抽样验证**

  抽 5 个：`tank-battle / hf-mobterm / e2e-hello-walkthrough / p-harness-v1.4 / p8-1-self-test` → 每个的 pipeline.nodes 至少 50% outputs_actual > 0

- [ ] **Step 5: pytest default suite 不破**

  `pytest -m 'not e2e'` → 49+/N PASS

- [ ] **Step 6: commit**

  `git add scripts/backfill_node_id_in_stage_artifacts.py tests/unit/ && git commit -m "feat(harnessFlow): backfill stage_artifacts.node_id for 21 historical task-boards"`

---
