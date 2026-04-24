"""TC-L104-L206 · schemas · 字段级 schema 校验 · PM-14 + IC-20 §3.20.

核心 TC：
- PM-14: project_id 非空 · 跨 VO 强制
- IC-20: delegation_id 格式 `ver-{uuid}` · blueprint_slice 必填
- VerifierVerdict 5 档枚举值
- SignatureCheckResult 双签逻辑（both_ok / failed_signatures）
- VerifiedResult.is_pass 便捷 getter
- frozen 不可变（改字段抛 ValidationError）
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    SignatureCheckResult,
    VerificationRequest,
    VerifiedResult,
    VerifierError,
    VerifierVerdict,
)


def _mk_blueprint_slice() -> dict[str, Any]:
    return {
        "dod_expression": "tests_pass AND coverage_ge_80",
        "red_tests": ["tests/test_a.py::test_one"],
        "wp_id": "wp-sample",
    }


def _mk_s4_snapshot() -> dict[str, Any]:
    return {
        "artifact_refs": ["app/feature_x.py"],
        "git_head": "abcdef1234567890",
        "test_report": {"passed": 10, "failed": 0, "coverage": 0.85},
    }


def _mk_request(**overrides: Any) -> VerificationRequest:
    defaults: dict[str, Any] = {
        "project_id": "proj-A",
        "wp_id": "wp-1",
        "blueprint_slice": _mk_blueprint_slice(),
        "s4_snapshot": _mk_s4_snapshot(),
        "acceptance_criteria": {"gate_coverage": 0.80},
        "main_session_id": "main-12345",
        "delegation_id": "ver-abc123def",
        "timeout_s": 1200,
        "ts": "2026-04-23T10:00:00Z",
    }
    defaults.update(overrides)
    return VerificationRequest(**defaults)


class TestVerifierVerdictEnum:
    """TC-L104-L206-001 · VerifierVerdict 5 档枚举 · §3.20.3."""

    def test_verdict_five_values(self) -> None:
        """枚举含 PASS / FAIL_L1 / FAIL_L2 / FAIL_L3 / FAIL_L4 共 5 档."""
        names = {v.name for v in VerifierVerdict}
        assert names == {"PASS", "FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"}

    def test_verdict_pass_is_string(self) -> None:
        """StrEnum · JSON 序列化友好."""
        assert VerifierVerdict.PASS == "PASS"
        assert VerifierVerdict.FAIL_L1.value == "FAIL_L1"


class TestVerificationRequestPM14:
    """TC-L104-L206-002 · VerificationRequest · PM-14 pid 强制."""

    def test_valid_request_accepts(self) -> None:
        """happy · 合法入参构造成功 + frozen."""
        req = _mk_request()
        assert req.project_id == "proj-A"
        assert req.delegation_id == "ver-abc123def"
        assert req.timeout_s == 1200
        with pytest.raises(ValidationError):
            # frozen · 改字段应抛
            req.project_id = "proj-B"  # type: ignore[misc]

    def test_empty_project_id_rejects(self) -> None:
        """TC-L104-L206-003 · PM-14 · project_id 空 → `E_VER_NO_PROJECT_ID`."""
        with pytest.raises(ValidationError) as exc:
            _mk_request(project_id="   ")
        assert "E_VER_NO_PROJECT_ID" in str(exc.value)

    def test_empty_blueprint_slice_rejects(self) -> None:
        """TC-L104-L206-004 · IC-20 §3.20.4 `E_VER_BLUEPRINT_MISSING`."""
        with pytest.raises(ValidationError) as exc:
            _mk_request(blueprint_slice={})
        assert "E_VER_BLUEPRINT_MISSING" in str(exc.value)

    def test_delegation_id_format_enforced(self) -> None:
        """TC-L104-L206-005 · delegation_id 必以 `ver-` 开头."""
        with pytest.raises(ValidationError):
            _mk_request(delegation_id="wp-xyz-bad")
        with pytest.raises(ValidationError):
            _mk_request(delegation_id="ver-ab")  # 太短（< 3 chars after prefix）

    def test_timeout_range_validated(self) -> None:
        """TC-L104-L206-006 · timeout_s 合理范围 1~1800."""
        with pytest.raises(ValidationError):
            _mk_request(timeout_s=0)
        with pytest.raises(ValidationError):
            _mk_request(timeout_s=9999)
        # 1800 上限应通过
        req = _mk_request(timeout_s=1800)
        assert req.timeout_s == 1800


class TestIC20Command:
    """TC-L104-L206-010 · IC-20 Command · §3.20.2 字段级."""

    def test_ic20_command_minimal_ok(self) -> None:
        """happy · IC-20 Command 构造（最小字段 + default allowed_tools）."""
        cmd = IC20Command(
            delegation_id="ver-c0ffee",
            project_id="proj-X",
            wp_id="wp-1",
            blueprint_slice=_mk_blueprint_slice(),
            s4_snapshot=_mk_s4_snapshot(),
            ts="2026-04-23T10:00:00Z",
        )
        assert cmd.timeout_s == 1200  # default
        assert cmd.allowed_tools == ("Read", "Glob", "Grep", "Bash")

    def test_ic20_command_rejects_empty_pid(self) -> None:
        """TC-L104-L206-011 · IC-20 §3.20.4 `E_VER_NO_PROJECT_ID`."""
        with pytest.raises(ValidationError) as exc:
            IC20Command(
                delegation_id="ver-c0ffee",
                project_id=" ",
                wp_id="wp-1",
                blueprint_slice=_mk_blueprint_slice(),
                s4_snapshot=_mk_s4_snapshot(),
                ts="2026-04-23T10:00:00Z",
            )
        assert "E_VER_NO_PROJECT_ID" in str(exc.value)

    def test_ic20_command_rejects_empty_blueprint(self) -> None:
        """IC-20 `E_VER_BLUEPRINT_MISSING` · blueprint_slice 空 dict 拒绝."""
        with pytest.raises(ValidationError) as exc:
            IC20Command(
                delegation_id="ver-c0ffee",
                project_id="proj-X",
                wp_id="wp-1",
                blueprint_slice={},
                s4_snapshot=_mk_s4_snapshot(),
                ts="2026-04-23T10:00:00Z",
            )
        assert "E_VER_BLUEPRINT_MISSING" in str(exc.value)


class TestIC20DispatchResult:
    """TC-L104-L206-020 · IC-20 dispatch 回包 · §3.20.3."""

    def test_dispatch_success_shape(self) -> None:
        """dispatched=True 附 verifier_session_id."""
        r = IC20DispatchResult(
            delegation_id="ver-abc",
            dispatched=True,
            verifier_session_id="sub-xyz-123",
        )
        assert r.dispatched is True
        assert r.verifier_session_id == "sub-xyz-123"

    def test_dispatch_failure_shape(self) -> None:
        """dispatched=False · verifier_session_id 可为 None."""
        r = IC20DispatchResult(delegation_id="ver-abc", dispatched=False)
        assert r.dispatched is False
        assert r.verifier_session_id is None


class TestSignatureCheckResult:
    """TC-L104-L206-030 · SignatureCheckResult · 双签逻辑."""

    def test_both_ok_true_when_both_pass(self) -> None:
        """两签通过 → both_ok=True + failed_signatures=()."""
        sig = SignatureCheckResult(
            blueprint_alignment_ok=True,
            s4_diff_analysis_ok=True,
            blueprint_detail={"matched": 10},
            s4_diff_detail={"diff_count": 0},
        )
        assert sig.both_ok is True
        assert sig.failed_signatures == ()

    def test_blueprint_fail_both_ok_false(self) -> None:
        """blueprint 签名失败 · both_ok=False + failed 含 'blueprint_alignment'."""
        sig = SignatureCheckResult(
            blueprint_alignment_ok=False,
            s4_diff_analysis_ok=True,
        )
        assert sig.both_ok is False
        assert "blueprint_alignment" in sig.failed_signatures

    def test_s4_diff_fail(self) -> None:
        """s4_diff 失败 · failed 含 's4_diff_analysis'."""
        sig = SignatureCheckResult(
            blueprint_alignment_ok=True,
            s4_diff_analysis_ok=False,
        )
        assert sig.both_ok is False
        assert sig.failed_signatures == ("s4_diff_analysis",)

    def test_both_fail(self) -> None:
        """两签均失败 · failed_signatures 包含两者."""
        sig = SignatureCheckResult(
            blueprint_alignment_ok=False,
            s4_diff_analysis_ok=False,
        )
        assert sig.both_ok is False
        assert set(sig.failed_signatures) == {"blueprint_alignment", "s4_diff_analysis"}


class TestVerifiedResult:
    """TC-L104-L206-040 · VerifiedResult 主入口出参."""

    def _sig_ok(self) -> SignatureCheckResult:
        return SignatureCheckResult(
            blueprint_alignment_ok=True, s4_diff_analysis_ok=True,
        )

    def test_verified_result_pass_shape(self) -> None:
        """happy · verdict=PASS · is_pass=True · frozen."""
        r = VerifiedResult(
            project_id="proj-A",
            delegation_id="ver-abc",
            wp_id="wp-1",
            verdict=VerifierVerdict.PASS,
            signatures=self._sig_ok(),
            dod_evaluation={"all_pass": True},
            duration_ms=10500,
        )
        assert r.is_pass is True
        assert r.verdict == VerifierVerdict.PASS

    def test_verified_result_fail_not_pass(self) -> None:
        """FAIL_L1 · is_pass=False."""
        r = VerifiedResult(
            project_id="proj-A",
            delegation_id="ver-abc",
            wp_id="wp-1",
            verdict=VerifierVerdict.FAIL_L1,
            signatures=SignatureCheckResult(
                blueprint_alignment_ok=True,
                s4_diff_analysis_ok=False,
            ),
        )
        assert r.is_pass is False
        assert r.verdict == VerifierVerdict.FAIL_L1

    def test_verified_result_pid_enforced(self) -> None:
        """PM-14 · project_id 空 → ValidationError."""
        with pytest.raises(ValidationError) as exc:
            VerifiedResult(
                project_id=" ",
                delegation_id="ver-abc",
                wp_id="wp-1",
                verdict=VerifierVerdict.PASS,
                signatures=self._sig_ok(),
            )
        assert "E_VER_NO_PROJECT_ID" in str(exc.value)


class TestVerifierErrorBase:
    """TC-L104-L206-050 · 错误基类可继承."""

    def test_verifier_error_is_exception(self) -> None:
        assert issubclass(VerifierError, Exception)

    def test_custom_subclass(self) -> None:
        class MyErr(VerifierError):
            pass
        with pytest.raises(VerifierError):
            raise MyErr("subclass works")
