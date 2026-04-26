"""v1.8 fix defects #3 — routing 决策呈现可被 LLM 跳过.

根因：主 skill § 4.2 仅以 prompt 文字描述"应呈现 top-2 候选 + 分数 +
risk_overlay"，无可执行 enforcement。LLM 在 context 紧 / 自由裁量时
直接说"推荐 C 路线"跳过 § 4.2，路由决策无审计 trace，事后无法
validate 是否真的查表。

修复：引入 `routing_matrix_consultation` 字段 + 写盘前 validator，
ROUTE_SELECT → PLAN 转移前必须落字段，缺则 BLOCK。

对外 API：
- `REQUIRED_FIELDS`：tuple，顶层必填字段名
- `REQUIRED_CANDIDATE_FIELDS`：tuple，每个候选条目必填字段
- `build_consultation(...)`：从 routing-matrix 查表后构造 record
- `validate_consultation_record(record)`：返
  `{"complete": bool, "missing": [...], "reason_code": str|None}`，
  主 skill § 4.2 用它做 BLOCK gate。
"""
from __future__ import annotations

from typing import Any

REQUIRED_FIELDS: tuple[str, ...] = (
    "task_dimensions",
    "top_candidates",
    "decision",
    "rationale",
)

REQUIRED_CANDIDATE_FIELDS: tuple[str, ...] = (
    "route_id",
    "raw_score",
    "adjusted_score",
)

REQUIRED_DIMENSION_FIELDS: tuple[str, ...] = ("size", "task_type", "risk")


def build_consultation(
    *,
    size: str,
    task_type: str,
    risk: str,
    top_candidates: list[dict],
    decision: str,
    rationale: str,
    risk_overlay_applied: bool = False,
    auto_pick_top1: bool = False,
) -> dict:
    """构造 routing_matrix_consultation record。

    `top_candidates` 至少 2 个 dict（top-2），各含 route_id / raw_score /
    adjusted_score。risk overlay 已 apply 时 risk_overlay_applied=True。
    """
    return {
        "task_dimensions": {"size": size, "task_type": task_type, "risk": risk},
        "top_candidates": top_candidates,
        "risk_overlay_applied": risk_overlay_applied,
        "auto_pick_top1": auto_pick_top1,
        "decision": decision,
        "rationale": rationale,
    }


def validate_consultation_record(record: Any) -> dict:
    """校验 routing_matrix_consultation 记录完整性 + 形态.

    返：
      {
        "complete": bool,
        "missing": [<field paths>],
        "reason_code": "ROUTING_CONSULTATION_MISSING" | "ROUTING_CONSULTATION_MALFORMED" | None,
      }

    完整定义：
      - record 是 dict
      - REQUIRED_FIELDS 全有且非 None
      - task_dimensions 含 size/task_type/risk 且都是 str
      - top_candidates 是 list 且 len ≥ 2
      - 每个 candidate 是 dict 含 REQUIRED_CANDIDATE_FIELDS
      - decision 是 str（候选 route_id 或 "halted_irreversible"）
      - rationale 是 str 长度 ≥ 10（防 LLM 写 "ok"）
    """
    if not isinstance(record, dict):
        return {
            "complete": False,
            "missing": ["<root not a dict>"],
            "reason_code": "ROUTING_CONSULTATION_MALFORMED",
        }

    missing: list[str] = []

    for f in REQUIRED_FIELDS:
        if f not in record or record[f] is None:
            missing.append(f)

    dims = record.get("task_dimensions")
    if isinstance(dims, dict):
        for d in REQUIRED_DIMENSION_FIELDS:
            if d not in dims or not isinstance(dims[d], str) or not dims[d]:
                missing.append(f"task_dimensions.{d}")
    else:
        missing.append("task_dimensions.<not a dict>")

    candidates = record.get("top_candidates")
    if isinstance(candidates, list):
        if len(candidates) < 2:
            missing.append("top_candidates[≥2 required]")
        for i, c in enumerate(candidates):
            if not isinstance(c, dict):
                missing.append(f"top_candidates[{i}]<not a dict>")
                continue
            for cf in REQUIRED_CANDIDATE_FIELDS:
                if cf not in c or c[cf] is None:
                    missing.append(f"top_candidates[{i}].{cf}")
    else:
        missing.append("top_candidates<not a list>")

    rationale = record.get("rationale")
    if isinstance(rationale, str) and len(rationale.strip()) < 10:
        missing.append("rationale[<10 chars]")

    if missing:
        # 区分 reason_code：root 不是 dict / 完全缺字段 → MISSING；其他细节 → MALFORMED
        any_top_missing = any(f in missing for f in REQUIRED_FIELDS)
        reason = "ROUTING_CONSULTATION_MISSING" if any_top_missing else "ROUTING_CONSULTATION_MALFORMED"
        return {"complete": False, "missing": missing, "reason_code": reason}
    return {"complete": True, "missing": [], "reason_code": None}
