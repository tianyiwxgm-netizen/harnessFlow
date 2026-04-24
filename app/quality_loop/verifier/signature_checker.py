"""L1-04 · L2-06 · signature_checker · 双签验证（blueprint_alignment + s4_diff_analysis）.

**职责**：对 verifier 返回的三段证据链前两段做**字段级一致性校验**，产出 SignatureCheckResult。

**两签规则**：

1. **blueprint_alignment**（蓝图对齐签）
   - verifier 看到的 dod_expression / red_tests 是否与 VerificationRequest.blueprint_slice 一致
   - 核心防御：防 verifier 被污染（用了错的蓝图）或 prompt 注入改写 DoD

2. **s4_diff_analysis**（S4 快照 diff 签）
   - verifier 独立跑的测试结果 vs 主 session 声称的 s4_snapshot.test_report
   - 核心防御：信任坍塌 · 主 session 声称 pass 但实际 fail
   - 任意 diff（含 coverage 差 > 阈值） → 签名失败

**verdict 降级链**：
- blueprint_alignment 失败 → FAIL_L2 (INSUFFICIENT)
- s4_diff_analysis 失败    → FAIL_L1 (信任坍塌)
- 两签均失败              → 取更严重的 FAIL_L1

**锚点**：
- IC-20 §3.20.3 three_segment_evidence (blueprint_alignment + s4_diff_analysis + dod_evaluation)
- L2-06 §2.4 ThreeEvidenceChain + §6.11 diff_with_main_claim
"""
from __future__ import annotations

from typing import Any

from app.quality_loop.verifier.schemas import (
    SignatureCheckResult,
    VerificationRequest,
    VerifierError,
    VerifierVerdict,
)


class SignatureCheckError(VerifierError):
    """双签校验失败（非 verdict 级 · 仅表示校验本身无法进行）.

    **区别于 verdict 降级**：
    - 本异常 = 输入数据根本无法校验（schema 破损等）
    - verdict 降级 = 校验出结果 · 签名不通过 · 归 verdict=FAIL_Lx
    """


# ==============================================================================
# Blueprint alignment 签
# ==============================================================================


def check_blueprint_alignment(
    request: VerificationRequest,
    verifier_observed_blueprint: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """校验 verifier 实际看到的蓝图与 request 里传入的蓝图一致.

    Args:
        request: 原始 VerificationRequest（含 authoritative blueprint_slice）
        verifier_observed_blueprint: verifier 回调里报告的 blueprint（含它实际消费的 dod / red_tests）

    Returns:
        (ok, detail)
        - ok        · True 表示对齐
        - detail    · 详细 diff（存入 SignatureCheckResult.blueprint_detail）

    **核心字段对比**：
    - `dod_expression`
    - `red_tests` (list / tuple · 顺序无关 · set 比较)

    任一字段不一致 → ok=False · detail 含 diff 信息。
    """
    auth = request.blueprint_slice
    obs = verifier_observed_blueprint or {}

    detail: dict[str, Any] = {
        "authoritative": _summary(auth),
        "observed": _summary(obs),
        "diff": [],
    }

    # 1. dod_expression 完全一致
    auth_dod = auth.get("dod_expression")
    obs_dod = obs.get("dod_expression")
    if auth_dod != obs_dod:
        detail["diff"].append({
            "field": "dod_expression",
            "authoritative": auth_dod,
            "observed": obs_dod,
        })

    # 2. red_tests 顺序无关比较（set 语义）
    auth_red = _to_set(auth.get("red_tests"))
    obs_red = _to_set(obs.get("red_tests"))
    if auth_red != obs_red:
        detail["diff"].append({
            "field": "red_tests",
            "missing_in_observed": sorted(auth_red - obs_red),
            "extra_in_observed": sorted(obs_red - auth_red),
        })

    ok = len(detail["diff"]) == 0
    detail["ok"] = ok
    return ok, detail


# ==============================================================================
# S4 diff analysis 签
# ==============================================================================


def check_s4_diff_analysis(
    request: VerificationRequest,
    verifier_test_report: dict[str, Any],
    *,
    coverage_tolerance: float = 0.05,
) -> tuple[bool, dict[str, Any]]:
    """校验 verifier 独立跑测试结果 vs 主 session 声称的 s4_snapshot.test_report.

    Args:
        request: 原始 VerificationRequest（含主 session 声称的 s4_snapshot.test_report）
        verifier_test_report: verifier 独立跑产出的 report
        coverage_tolerance: coverage diff 容忍（默认 ±0.05 = ±5 pp）

    Returns:
        (ok, detail)
        - ok     · True 表示两份 report 字段级一致（在容忍内）
        - detail · 详细 diff（存入 SignatureCheckResult.s4_diff_detail）

    **核心字段对比**：
    - `passed` / `failed` · 整数严格一致
    - `coverage`          · 浮点数 ±coverage_tolerance 容忍
    - 任一差异 → ok=False
    """
    main_claim = request.s4_snapshot.get("test_report", {}) or {}
    observed = verifier_test_report or {}

    detail: dict[str, Any] = {
        "main_claim": _summary(main_claim),
        "observed": _summary(observed),
        "diff": [],
    }

    # 1. passed 严格一致（若 main 声称值存在）
    if "passed" in main_claim or "passed" in observed:
        mp = main_claim.get("passed", 0)
        op = observed.get("passed", 0)
        if mp != op:
            detail["diff"].append({
                "field": "passed",
                "main_claimed": mp,
                "verifier_actual": op,
                "severity": "CRITICAL",
            })

    # 2. failed 严格一致
    if "failed" in main_claim or "failed" in observed:
        mf = main_claim.get("failed", 0)
        of = observed.get("failed", 0)
        if mf != of:
            detail["diff"].append({
                "field": "failed",
                "main_claimed": mf,
                "verifier_actual": of,
                "severity": "CRITICAL",
            })

    # 3. coverage 阈值内容忍
    if "coverage" in main_claim or "coverage" in observed:
        mc = float(main_claim.get("coverage", 0.0))
        oc = float(observed.get("coverage", 0.0))
        diff_abs = abs(mc - oc)
        if diff_abs > coverage_tolerance:
            detail["diff"].append({
                "field": "coverage",
                "main_claimed": mc,
                "verifier_actual": oc,
                "diff_abs": round(diff_abs, 4),
                "tolerance": coverage_tolerance,
                "severity": "WARN" if diff_abs < 0.10 else "CRITICAL",
            })

    ok = len(detail["diff"]) == 0
    detail["ok"] = ok
    return ok, detail


# ==============================================================================
# 组合双签 → SignatureCheckResult
# ==============================================================================


def check_signatures(
    request: VerificationRequest,
    verifier_observed_blueprint: dict[str, Any],
    verifier_test_report: dict[str, Any],
    *,
    coverage_tolerance: float = 0.05,
) -> SignatureCheckResult:
    """组合两签 · 返回 SignatureCheckResult VO.

    **调用约定**：orchestrator 在 verifier 回调后调用此函数生成 signatures · 喂给 downgrade_verdict。
    """
    bp_ok, bp_detail = check_blueprint_alignment(request, verifier_observed_blueprint)
    s4_ok, s4_detail = check_s4_diff_analysis(
        request, verifier_test_report, coverage_tolerance=coverage_tolerance,
    )
    return SignatureCheckResult(
        blueprint_alignment_ok=bp_ok,
        s4_diff_analysis_ok=s4_ok,
        blueprint_detail=bp_detail,
        s4_diff_detail=s4_detail,
    )


def downgrade_verdict(
    signatures: SignatureCheckResult,
    dod_verdict: VerifierVerdict,
) -> VerifierVerdict:
    """根据双签 + dod_evaluation 综合决定最终 verdict.

    **降级优先级**（从严到松）：
    1. `s4_diff_analysis` 失败     → FAIL_L1（信任坍塌最严重）
    2. `blueprint_alignment` 失败  → FAIL_L2（INSUFFICIENT · 蓝图对不齐无法证明）
    3. 两签均 OK → 沿用 dod_verdict（PASS / FAIL_L3 / FAIL_L4）

    **规则理由**（L2-06 §1.5 决策 D1 + IC-20 §3.20.1）：
    - 信任坍塌 > 证据不足 > DoD 未达标
    - verifier 超时等 FAIL_L4 由 orchestrator 在 dispatch 阶段直接定（不来这里）
    """
    if not signatures.s4_diff_analysis_ok:
        return VerifierVerdict.FAIL_L1
    if not signatures.blueprint_alignment_ok:
        return VerifierVerdict.FAIL_L2
    # 两签均 OK · 沿用 dod
    return dod_verdict


# ==============================================================================
# 辅助
# ==============================================================================


def _to_set(value: Any) -> frozenset[str]:
    """把 list / tuple / None / 其他 → frozenset[str] · 用于顺序无关比较."""
    if value is None:
        return frozenset()
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(x) for x in value)
    # 单值（少见）· 包成 set
    return frozenset([str(value)])


def _summary(d: dict[str, Any] | Any) -> dict[str, Any]:
    """防 detail dict 过大 · 只取关键字段 summary."""
    if not isinstance(d, dict):
        return {"_type": type(d).__name__}
    keys = ("dod_expression", "red_tests", "passed", "failed", "coverage")
    return {k: d[k] for k in keys if k in d}
