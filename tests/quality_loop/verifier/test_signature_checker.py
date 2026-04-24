"""TC-L104-L206 · signature_checker · 双签校验（blueprint_alignment + s4_diff_analysis）.

核心 TC：
- blueprint_alignment: happy + dod_expression diff + red_tests set 顺序无关 + red_tests 缺漏
- s4_diff_analysis: happy + passed diff + failed diff + coverage 容忍 + coverage 超阈值
- check_signatures: 组合 · 两签均通 / 单签失败 / 两签均失败
- downgrade_verdict: s4_diff_fail → FAIL_L1 · blueprint_fail → FAIL_L2 · 两签 OK → 沿用 dod
"""
from __future__ import annotations

from typing import Any

from app.quality_loop.verifier.schemas import (
    SignatureCheckResult,
    VerificationRequest,
    VerifierVerdict,
)
from app.quality_loop.verifier.signature_checker import (
    check_blueprint_alignment,
    check_s4_diff_analysis,
    check_signatures,
    downgrade_verdict,
)


def _mk_request(
    *,
    dod: str = "tests_pass AND coverage_ge_80",
    red_tests: tuple[str, ...] = ("t1", "t2"),
    test_report: dict[str, Any] | None = None,
) -> VerificationRequest:
    return VerificationRequest(
        project_id="proj-A",
        wp_id="wp-1",
        blueprint_slice={"dod_expression": dod, "red_tests": list(red_tests)},
        s4_snapshot={
            "artifact_refs": [],
            "git_head": "deadbeef",
            "test_report": test_report or {"passed": 10, "failed": 0, "coverage": 0.85},
        },
        acceptance_criteria={},
        main_session_id="main-sess",
        delegation_id="ver-abc123",
        timeout_s=600,
        ts="2026-04-23T10:00:00Z",
    )


# ==============================================================================
# blueprint_alignment
# ==============================================================================


class TestCheckBlueprintAlignment:
    """TC-L104-L206-200 · blueprint_alignment 签."""

    def test_happy_both_match(self) -> None:
        """TC-200 · dod + red_tests 一致 → ok=True · diff=[]."""
        req = _mk_request()
        observed = {"dod_expression": "tests_pass AND coverage_ge_80", "red_tests": ["t1", "t2"]}
        ok, detail = check_blueprint_alignment(req, observed)
        assert ok is True
        assert detail["diff"] == []
        assert detail["ok"] is True

    def test_dod_expression_mismatch(self) -> None:
        """TC-201 · dod 改写 → ok=False · diff 有 dod_expression."""
        req = _mk_request(dod="tests_pass AND coverage_ge_80")
        observed = {
            "dod_expression": "tests_pass OR coverage_ge_50",  # 被篡改
            "red_tests": ["t1", "t2"],
        }
        ok, detail = check_blueprint_alignment(req, observed)
        assert ok is False
        assert any(d["field"] == "dod_expression" for d in detail["diff"])

    def test_red_tests_set_order_invariant(self) -> None:
        """TC-202 · red_tests 顺序不同 · set 语义应认为一致."""
        req = _mk_request(red_tests=("t1", "t2", "t3"))
        observed = {
            "dod_expression": "tests_pass AND coverage_ge_80",
            "red_tests": ["t3", "t1", "t2"],  # 乱序
        }
        ok, detail = check_blueprint_alignment(req, observed)
        assert ok is True
        assert detail["diff"] == []

    def test_red_tests_missing(self) -> None:
        """TC-203 · verifier 少看了一个 red_test → ok=False."""
        req = _mk_request(red_tests=("t1", "t2", "t3"))
        observed = {
            "dod_expression": "tests_pass AND coverage_ge_80",
            "red_tests": ["t1", "t2"],  # 缺 t3
        }
        ok, detail = check_blueprint_alignment(req, observed)
        assert ok is False
        diff_red = next(d for d in detail["diff"] if d["field"] == "red_tests")
        assert "t3" in diff_red["missing_in_observed"]

    def test_red_tests_extra(self) -> None:
        """TC-204 · verifier 多看了一个 → ok=False."""
        req = _mk_request(red_tests=("t1",))
        observed = {
            "dod_expression": "tests_pass AND coverage_ge_80",
            "red_tests": ["t1", "t99"],  # 多了 t99
        }
        ok, detail = check_blueprint_alignment(req, observed)
        assert ok is False
        diff_red = next(d for d in detail["diff"] if d["field"] == "red_tests")
        assert "t99" in diff_red["extra_in_observed"]

    def test_empty_observed_blueprint_fails(self) -> None:
        """TC-205 · verifier 没汇报 blueprint · 缺字段 → ok=False."""
        req = _mk_request()
        ok, detail = check_blueprint_alignment(req, {})
        assert ok is False


# ==============================================================================
# s4_diff_analysis
# ==============================================================================


class TestCheckS4DiffAnalysis:
    """TC-L104-L206-210 · s4_diff_analysis 签."""

    def test_happy_identical_report(self) -> None:
        """TC-210 · 两份 report 完全一致 → ok=True."""
        req = _mk_request(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        observed = {"passed": 10, "failed": 0, "coverage": 0.85}
        ok, detail = check_s4_diff_analysis(req, observed)
        assert ok is True
        assert detail["diff"] == []

    def test_passed_mismatch_critical(self) -> None:
        """TC-211 · passed 数不同 → ok=False · diff 标 CRITICAL."""
        req = _mk_request(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        observed = {"passed": 9, "failed": 1, "coverage": 0.85}  # 主声称 10 pass · 实测 9
        ok, detail = check_s4_diff_analysis(req, observed)
        assert ok is False
        passed_diff = next(d for d in detail["diff"] if d["field"] == "passed")
        assert passed_diff["main_claimed"] == 10
        assert passed_diff["verifier_actual"] == 9
        assert passed_diff["severity"] == "CRITICAL"

    def test_failed_mismatch(self) -> None:
        """TC-212 · failed 数不同 → CRITICAL."""
        req = _mk_request(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        observed = {"passed": 10, "failed": 2, "coverage": 0.85}
        ok, detail = check_s4_diff_analysis(req, observed)
        assert ok is False
        failed_diff = next(d for d in detail["diff"] if d["field"] == "failed")
        assert failed_diff["severity"] == "CRITICAL"

    def test_coverage_within_tolerance(self) -> None:
        """TC-213 · coverage 在 ±0.05 容忍内 → ok=True."""
        req = _mk_request(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        observed = {"passed": 10, "failed": 0, "coverage": 0.83}  # diff=0.02 < 0.05
        ok, detail = check_s4_diff_analysis(req, observed, coverage_tolerance=0.05)
        assert ok is True

    def test_coverage_over_tolerance_warn(self) -> None:
        """TC-214 · coverage diff 0.06 超 0.05 → ok=False · severity=WARN."""
        req = _mk_request(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        observed = {"passed": 10, "failed": 0, "coverage": 0.79}  # diff=0.06
        ok, detail = check_s4_diff_analysis(req, observed, coverage_tolerance=0.05)
        assert ok is False
        cov_diff = next(d for d in detail["diff"] if d["field"] == "coverage")
        assert cov_diff["severity"] == "WARN"

    def test_coverage_huge_diff_critical(self) -> None:
        """TC-215 · coverage diff > 0.10 → severity=CRITICAL."""
        req = _mk_request(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        observed = {"passed": 10, "failed": 0, "coverage": 0.50}  # diff=0.35
        ok, detail = check_s4_diff_analysis(req, observed, coverage_tolerance=0.05)
        assert ok is False
        cov_diff = next(d for d in detail["diff"] if d["field"] == "coverage")
        assert cov_diff["severity"] == "CRITICAL"

    def test_no_main_claim_no_observed_ok(self) -> None:
        """TC-216 · 两侧都没 test_report 字段 → 无 diff · ok=True."""
        req = VerificationRequest(
            project_id="proj-A",
            wp_id="wp-1",
            blueprint_slice={"dod": "any"},
            s4_snapshot={"artifact_refs": [], "git_head": "dead"},  # 无 test_report
            acceptance_criteria={},
            main_session_id="main",
            delegation_id="ver-none",
            timeout_s=600,
            ts="2026-04-23T00:00:00Z",
        )
        ok, detail = check_s4_diff_analysis(req, {})
        assert ok is True


# ==============================================================================
# check_signatures 组合
# ==============================================================================


class TestCheckSignatures:
    """TC-L104-L206-220 · 组合双签入口."""

    def test_both_signatures_ok(self) -> None:
        """两签均通 → SignatureCheckResult.both_ok=True."""
        req = _mk_request()
        bp = {"dod_expression": "tests_pass AND coverage_ge_80", "red_tests": ["t1", "t2"]}
        tr = {"passed": 10, "failed": 0, "coverage": 0.85}
        sig = check_signatures(req, bp, tr)
        assert sig.both_ok is True
        assert sig.failed_signatures == ()

    def test_blueprint_fail_only(self) -> None:
        """仅 blueprint 失败 → failed_signatures=('blueprint_alignment',)."""
        req = _mk_request()
        bp = {"dod_expression": "CHANGED", "red_tests": ["t1", "t2"]}
        tr = {"passed": 10, "failed": 0, "coverage": 0.85}
        sig = check_signatures(req, bp, tr)
        assert sig.both_ok is False
        assert sig.failed_signatures == ("blueprint_alignment",)

    def test_s4_fail_only(self) -> None:
        """仅 s4 失败 → failed_signatures=('s4_diff_analysis',)."""
        req = _mk_request()
        bp = {"dod_expression": "tests_pass AND coverage_ge_80", "red_tests": ["t1", "t2"]}
        tr = {"passed": 9, "failed": 1, "coverage": 0.85}
        sig = check_signatures(req, bp, tr)
        assert sig.both_ok is False
        assert sig.failed_signatures == ("s4_diff_analysis",)

    def test_both_fail(self) -> None:
        """两签均失败 → failed 含两者."""
        req = _mk_request()
        bp = {"dod_expression": "DIFFERENT"}
        tr = {"passed": 5, "failed": 5, "coverage": 0.1}
        sig = check_signatures(req, bp, tr)
        assert sig.both_ok is False
        assert set(sig.failed_signatures) == {"blueprint_alignment", "s4_diff_analysis"}


# ==============================================================================
# downgrade_verdict
# ==============================================================================


class TestDowngradeVerdict:
    """TC-L104-L206-230 · verdict 降级决策."""

    def _sig(self, *, bp_ok: bool, s4_ok: bool) -> SignatureCheckResult:
        return SignatureCheckResult(
            blueprint_alignment_ok=bp_ok, s4_diff_analysis_ok=s4_ok,
        )

    def test_both_ok_dod_pass_keeps_pass(self) -> None:
        """两签 OK + dod_PASS → PASS."""
        sig = self._sig(bp_ok=True, s4_ok=True)
        assert downgrade_verdict(sig, VerifierVerdict.PASS) == VerifierVerdict.PASS

    def test_both_ok_dod_fail_l3(self) -> None:
        """两签 OK + dod_FAIL_L3 → 沿用 FAIL_L3（质量未过阈值）."""
        sig = self._sig(bp_ok=True, s4_ok=True)
        assert downgrade_verdict(sig, VerifierVerdict.FAIL_L3) == VerifierVerdict.FAIL_L3

    def test_s4_fail_downgrades_to_l1(self) -> None:
        """s4 签失败 → FAIL_L1（信任坍塌最严重 · 优先）."""
        sig = self._sig(bp_ok=True, s4_ok=False)
        assert downgrade_verdict(sig, VerifierVerdict.PASS) == VerifierVerdict.FAIL_L1

    def test_blueprint_fail_downgrades_to_l2(self) -> None:
        """blueprint 签失败 (s4 OK) → FAIL_L2 (INSUFFICIENT)."""
        sig = self._sig(bp_ok=False, s4_ok=True)
        assert downgrade_verdict(sig, VerifierVerdict.PASS) == VerifierVerdict.FAIL_L2

    def test_both_fail_s4_priority_wins(self) -> None:
        """两签均失败 · s4 优先级高于 blueprint → FAIL_L1."""
        sig = self._sig(bp_ok=False, s4_ok=False)
        assert downgrade_verdict(sig, VerifierVerdict.PASS) == VerifierVerdict.FAIL_L1

    def test_s4_fail_overrides_dod_fail_l3(self) -> None:
        """即使 dod 本身 FAIL_L3 · s4 签失败仍升级到 FAIL_L1."""
        sig = self._sig(bp_ok=True, s4_ok=False)
        assert downgrade_verdict(sig, VerifierVerdict.FAIL_L3) == VerifierVerdict.FAIL_L1
