"""archive.sequence_verifier.verifier — 解析 flow-catalog.md + 比对 planned_steps.

主 skill § 5.1 execute_route() 在调度任何 ECC/SP skill 前调用本模块，
确保 planned_steps 与 flow-catalog 对应路线 § 的 expected sequence 一致。
不一致 → 返 mismatch 报告，主 skill 应转 PAUSED_ESCALATED + Supervisor BLOCK + 红线。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence

# flow-catalog 序列行 pattern：
#   "1.  SP:brainstorming (@clarify) [3 轮]"      # 路线 C/D/E/F 用 numbered
#   "  → ECC:code-reviewer (@impl) [parallel]"    # 嵌套并发/补充调用
#   "native:Read (@clarify)"                      # 路线 A 用 bare 行（无前缀）
# 编号 / 箭头前缀都做成可选 — 行首之后只要是 namespace:skill_name 就算一步。
SEQ_LINE_RE = re.compile(
    r"^\s*(?:(?:\d+\.|→)\s+)?([\w][\w\-]*:[\w][\w\-]*)\b"
)

# 路线 § 标题 pattern，e.g. "## § 4 路线 C — 全 PRP 重验证（L-XL）"
ROUTE_HEADING_RE = re.compile(
    r"^##\s+§\s*\d+\s+路线\s+([A-Z](?:-lite)?)\b"
)


def parse_flow_catalog_route(
    flow_catalog_path: Path,
    route_id: str,
) -> List[str]:
    """从 flow-catalog.md 解析指定路线的 expected sequence.

    解析规则：
      1. 找 "## § N 路线 <route_id> ..." 标题（routes A/B/C/D/E/F + C-lite）
      2. 在该 § 内找首个 ``` 围栏代码块（"调度序列" 块）
      3. 块内每行匹配 SEQ_LINE_RE，提取 namespace:skill 部分
      4. 同名连续重复（e.g. ECC:save-session 出现多次）保留全部，序列敏感

    Args:
        flow_catalog_path: flow-catalog.md 路径。
        route_id: 路线字母（"A"/"B"/"C"/"C-lite"/"D"/"E"/"F"）。

    Returns:
        list of skill names（namespace:name）按出现顺序排列。
        路线未找到 / 无代码块 → 空 list。

    Raises:
        FileNotFoundError: flow_catalog_path 不存在。
    """
    flow_catalog_path = Path(flow_catalog_path)
    if not flow_catalog_path.is_file():
        raise FileNotFoundError(f"flow_catalog not found: {flow_catalog_path}")

    lines = flow_catalog_path.read_text(encoding="utf-8").splitlines()

    # 找路线 § 起止
    start = None
    end = None
    for i, ln in enumerate(lines):
        m = ROUTE_HEADING_RE.match(ln)
        if m:
            if m.group(1) == route_id and start is None:
                start = i
            elif start is not None:
                end = i
                break
    if start is None:
        return []
    if end is None:
        end = len(lines)

    # 在 § 内找首个 ``` 代码块
    in_block = False
    seq: List[str] = []
    for ln in lines[start:end]:
        if ln.strip().startswith("```"):
            if in_block:
                # 块结束 → 已取首个块内容
                break
            in_block = True
            continue
        if in_block:
            m = SEQ_LINE_RE.match(ln)
            if m:
                seq.append(m.group(1))
    return seq


def verify_route_sequence(
    route_id: str,
    planned_steps: Sequence[str],
    flow_catalog_path: Path,
    *,
    allow_missing_steps: Optional[List[str]] = None,
) -> Dict:
    """比对 planned_steps 与 flow-catalog expected sequence.

    Args:
        route_id: 路线字母。
        planned_steps: 主 skill 在 execute_route 准备执行的 skill 序列
                       （namespace:name 格式，e.g. "SP:brainstorming"）。
        flow_catalog_path: flow-catalog.md 路径。
        allow_missing_steps: 已知合法可省略的 step（e.g. C-lite 省 prp-prd / mid-retro / santa-loop）。
                             这些 step 出现在 expected 但不在 planned 时不算 missing。

    Returns:
        dict {
            "match": bool,
            "expected": [...],          # flow-catalog 解析出的序列
            "actual": [...],            # planned_steps
            "missing": [...],           # 应有但缺（已扣除 allow_missing_steps）
            "extra": [...],             # 不在 expected 中却出现的
            "reordered": bool,          # 共有 step 是否乱序（仅当 missing/extra 都为 [] 时才有意义）
            "reason_code": str,         # 主 skill 写 supervisor BLOCK 时用
            "reason_msg": str,          # 人可读说明
        }
    """
    expected = parse_flow_catalog_route(flow_catalog_path, route_id)
    actual = list(planned_steps)
    allow = set(allow_missing_steps or [])

    expected_set = [s for s in expected if s not in allow]
    expected_unique = list(dict.fromkeys(expected_set))  # 保序去重，便于集合差
    actual_unique = list(dict.fromkeys(actual))

    missing = [s for s in expected_unique if s not in set(actual_unique)]
    extra = [s for s in actual_unique if s not in set(expected_unique)]

    # 序判断：仅在 missing/extra 都为 [] 时才有意义；否则 reordered 不可靠
    reordered = False
    if not missing and not extra:
        # 比较 expected 在 actual 里的相对顺序
        actual_index = {s: i for i, s in enumerate(actual)}
        prev = -1
        for s in expected:
            if s in allow:
                continue
            idx = actual_index.get(s, -1)
            if idx == -1:
                continue
            if idx < prev:
                reordered = True
                break
            prev = idx

    if not expected:
        return {
            "match": False,
            "expected": [],
            "actual": actual,
            "missing": [],
            "extra": [],
            "reordered": False,
            "reason_code": "ROUTE_NOT_FOUND",
            "reason_msg": f"route {route_id} not found in flow-catalog or has no code block",
        }

    if missing or extra or reordered:
        codes = []
        if missing:
            codes.append("missing")
        if extra:
            codes.append("extra")
        if reordered:
            codes.append("reordered")
        msg_parts = []
        if missing:
            msg_parts.append(f"missing={missing}")
        if extra:
            msg_parts.append(f"extra={extra}")
        if reordered:
            msg_parts.append("reordered")
        return {
            "match": False,
            "expected": expected,
            "actual": actual,
            "missing": missing,
            "extra": extra,
            "reordered": reordered,
            "reason_code": "SEQUENCE_MISMATCH:" + "+".join(codes),
            "reason_msg": (
                f"route {route_id} planned_steps deviate from flow-catalog: "
                + ", ".join(msg_parts)
            ),
        }

    return {
        "match": True,
        "expected": expected,
        "actual": actual,
        "missing": [],
        "extra": [],
        "reordered": False,
        "reason_code": "OK",
        "reason_msg": f"route {route_id} planned_steps match flow-catalog expected sequence",
    }
