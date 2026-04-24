"""WP05 · task_chain.failure_handler BF-E-* 分类用例.

覆盖:
    - classify_exception: CancelledError / TimeoutError / 一般 Exception / TaskChainError 透传
    - TaskChainError.from_cause: 构造 + override_code
    - 错误码枚举完整性 (5 类)
"""
from __future__ import annotations

import asyncio

import pytest

from app.main_loop.task_chain.failure_handler import (
    BF_ERROR_CODES,
    BackwardFailCode,
    TaskChainError,
    classify_exception,
)


class TestClassifyException:
    """classify_exception() 规则."""

    def test_TC_WP05_F01_cancelled_maps_to_downstream_cancelled(self) -> None:
        """asyncio.CancelledError → DOWNSTREAM_CANCELLED."""
        code = classify_exception(asyncio.CancelledError())
        assert code == BackwardFailCode.DOWNSTREAM_CANCELLED

    def test_TC_WP05_F02_timeout_maps_to_downstream_timeout(self) -> None:
        """TimeoutError → DOWNSTREAM_TIMEOUT."""
        code = classify_exception(TimeoutError("boom"))
        assert code == BackwardFailCode.DOWNSTREAM_TIMEOUT
        # asyncio.TimeoutError 在 3.11 是 TimeoutError 别名
        code2 = classify_exception(asyncio.TimeoutError())
        assert code2 == BackwardFailCode.DOWNSTREAM_TIMEOUT

    def test_TC_WP05_F03_value_error_maps_to_downstream_raise(self) -> None:
        """一般 Exception → DOWNSTREAM_RAISE."""
        code = classify_exception(ValueError("bad input"))
        assert code == BackwardFailCode.DOWNSTREAM_RAISE
        code2 = classify_exception(TypeError("wrong type"))
        assert code2 == BackwardFailCode.DOWNSTREAM_RAISE

    def test_TC_WP05_F04_chain_error_passes_through_code(self) -> None:
        """TaskChainError 本身 · 透传已 classify 过的 code (避免双重包装)."""
        exc = TaskChainError(
            code=BackwardFailCode.IC_CONTRACT_VIOLATION,
            message="reply missing task_id",
        )
        assert classify_exception(exc) == BackwardFailCode.IC_CONTRACT_VIOLATION

    def test_TC_WP05_F05_base_exception_maps_to_unknown(self) -> None:
        """非 Exception 的 BaseException (如 KeyboardInterrupt) → UNKNOWN."""
        code = classify_exception(KeyboardInterrupt())
        assert code == BackwardFailCode.UNKNOWN


class TestTaskChainError:
    """TaskChainError 构造 / from_cause."""

    def test_TC_WP05_F10_from_cause_auto_classify(self) -> None:
        """from_cause 自动 classify · 默认 DOWNSTREAM_RAISE."""
        raw = ValueError("boom")
        err = TaskChainError.from_cause(
            raw, project_id="pid-1", task_id="t-1",
        )
        assert err.code == BackwardFailCode.DOWNSTREAM_RAISE
        assert err.project_id == "pid-1"
        assert err.task_id == "t-1"
        assert err.cause is raw

    def test_TC_WP05_F11_from_cause_override_code(self) -> None:
        """override_code 强制指定错误码 (如 IC_CONTRACT_VIOLATION)."""
        raw = ValueError("missing field")
        err = TaskChainError.from_cause(
            raw, override_code=BackwardFailCode.IC_CONTRACT_VIOLATION,
        )
        assert err.code == BackwardFailCode.IC_CONTRACT_VIOLATION

    def test_TC_WP05_F12_error_str_has_prefix(self) -> None:
        """str(err) 以 [BF-E-*] 前缀 · 便于日志 grep."""
        err = TaskChainError(
            code=BackwardFailCode.DOWNSTREAM_TIMEOUT,
            message="timeout after 30s",
        )
        assert "[BF-E-DOWNSTREAM_TIMEOUT]" in str(err)

    def test_TC_WP05_F13_chain_error_raisable(self) -> None:
        """TaskChainError 可 raise / catch."""
        with pytest.raises(TaskChainError) as exc_info:
            raise TaskChainError(
                code=BackwardFailCode.UNKNOWN, message="?",
            )
        assert exc_info.value.code == BackwardFailCode.UNKNOWN


class TestBackwardFailCode:
    """错误码枚举完整性."""

    def test_TC_WP05_F20_five_codes_defined(self) -> None:
        """DOWNSTREAM_RAISE/TIMEOUT/CANCELLED + IC_CONTRACT_VIOLATION + UNKNOWN = 5 类."""
        values = {c.value for c in BackwardFailCode}
        assert values == {
            "BF-E-DOWNSTREAM_RAISE",
            "BF-E-DOWNSTREAM_TIMEOUT",
            "BF-E-DOWNSTREAM_CANCELLED",
            "BF-E-IC_CONTRACT_VIOLATION",
            "BF-E-UNKNOWN",
        }

    def test_TC_WP05_F21_all_codes_have_bf_e_prefix(self) -> None:
        """全部 BF-E-* 前缀约定 · 审计 grep 用."""
        for code in BF_ERROR_CODES:
            assert code.value.startswith("BF-E-")
