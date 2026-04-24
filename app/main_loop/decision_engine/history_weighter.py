"""L1-01 L2-02 · History Weighter · 过往决策的成败对当前候选的加权.

规则:
    - 同 decision_type 在最近 N 步成功 → 正向加权
    - 同 decision_type 在最近 N 步连续失败 → 负向加权(防止重蹈覆辙)
    - tick_delta 越大(越老)权重越衰减(exponential decay)
    - params_fingerprint 匹配给额外加权(策略稳定性)

输出范围: [-MAX_HISTORY_WEIGHT_ABS, +MAX_HISTORY_WEIGHT_ABS]。

对齐:
    - L2-02 §3.1.1 decision_type × params 分表(params 越相似,加权越大)
    - prd §9.5 #4 "重蹈覆辙" → 连续失败负向
"""
from __future__ import annotations

from .schemas import Candidate, HistoryEntry

# ========== 参数 ==========

# 每次历史条目的基础加权(|base| = 0.10)
BASE_WEIGHT_SUCCESS = 0.10
BASE_WEIGHT_FAIL = -0.15   # 失败的绝对值更大(避免重蹈覆辙偏置)
BASE_WEIGHT_SKIP = -0.02

# tick_delta 衰减:factor = 0.8 ^ tick_delta
DECAY_FACTOR = 0.8

# params_fingerprint 精确匹配时的乘数(总加权 = base * decay * match_mult)
PARAMS_EXACT_MATCH_MULT = 1.5

# 只考虑最近 K 条历史
HISTORY_WINDOW = 20

# clamp 输出范围
MAX_HISTORY_WEIGHT_ABS = 0.40

# 连续失败(≥ 3 条连续 fail) → 额外拉低 0.10
CONSEC_FAIL_THRESHOLD = 3
CONSEC_FAIL_EXTRA = -0.10


def compute_history_weight(
    candidate: Candidate,
    history: tuple[HistoryEntry, ...],
) -> float:
    """计算 history_weight ∈ [-MAX_HISTORY_WEIGHT_ABS, +MAX_HISTORY_WEIGHT_ABS]。

    history 降序(最近在前)。空历史 → 0.0。
    """
    if not history:
        return 0.0

    window = history[:HISTORY_WINDOW]
    cand_fp = _params_fingerprint(candidate)

    total = 0.0
    consec_fail = 0
    saw_consec_tracker = True

    for entry in window:
        if entry.decision_type != candidate.decision_type:
            # 不同 type 不直接参与(但破坏连续失败计数)
            saw_consec_tracker = False
            continue

        base = _base_weight(entry.outcome)
        decay = DECAY_FACTOR ** max(0, entry.tick_delta - 1)
        mult = 1.0
        if cand_fp and entry.params_fingerprint == cand_fp:
            mult = PARAMS_EXACT_MATCH_MULT
        total += base * decay * mult

        # 连续失败检测(从最近的一条开始)
        if saw_consec_tracker:
            if entry.outcome == "fail":
                consec_fail += 1
            else:
                saw_consec_tracker = False

    if consec_fail >= CONSEC_FAIL_THRESHOLD:
        total += CONSEC_FAIL_EXTRA

    # clamp
    if total > MAX_HISTORY_WEIGHT_ABS:
        total = MAX_HISTORY_WEIGHT_ABS
    elif total < -MAX_HISTORY_WEIGHT_ABS:
        total = -MAX_HISTORY_WEIGHT_ABS
    return total


def _base_weight(outcome: str) -> float:
    if outcome == "success":
        return BASE_WEIGHT_SUCCESS
    if outcome == "fail":
        return BASE_WEIGHT_FAIL
    if outcome == "skip":
        return BASE_WEIGHT_SKIP
    return 0.0


def _params_fingerprint(candidate: Candidate) -> str:
    """生成候选的稳定指纹字符串;便于与 HistoryEntry.params_fingerprint 比较。

    rule:sorted key-value 串接。空 params → ''。
    """
    if not candidate.decision_params:
        return ""
    items = sorted(
        (str(k), _scalar_str(v)) for k, v in candidate.decision_params.items()
    )
    return "|".join(f"{k}={v}" for k, v in items)


def _scalar_str(v: object) -> str:
    """稳定 scalar 化(dict/list 转 JSON-like 排序字符串,长度封顶)。"""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_scalar_str(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(f"{k}:{_scalar_str(v[k])}" for k in sorted(v)) + "}"
    return str(v)[:64]


__all__ = [
    "BASE_WEIGHT_FAIL",
    "BASE_WEIGHT_SKIP",
    "BASE_WEIGHT_SUCCESS",
    "CONSEC_FAIL_EXTRA",
    "CONSEC_FAIL_THRESHOLD",
    "DECAY_FACTOR",
    "HISTORY_WINDOW",
    "MAX_HISTORY_WEIGHT_ABS",
    "PARAMS_EXACT_MATCH_MULT",
    "compute_history_weight",
]
