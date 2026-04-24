"""main-1 WP05 · L2-05 S4 Driver · SubagentDispatcher unit tests。

对齐 3-2 §2 正向 · §3 负向 · §4 IC-04 契约（IC-05 对 L1-05 · WP05 mock）:
  - TC-L104-L205-045    · SkillInvoker.invoke 成功路径
  - TC-L104-L205-107    · 错误码 SKILL_INVOKE_FAIL
  - TC-L104-L205-120    · 错误码 SKILL_NOT_FOUND
  - TC-L104-L205-121    · 错误码 SKILL_BUDGET_EXHAUSTED
  - TC-L104-L205-122    · 错误码 SKILL_TIMEOUT
  - TC-L104-L205-404    · IC-04 主动调 red/green/self_repair intent
"""
from __future__ import annotations

import pytest

from app.quality_loop.s4_driver.schemas import (
    INTERNAL_ASSERT,
    SKILL_BUDGET_EXHAUSTED,
    SKILL_INVOKE_FAIL,
    SKILL_NOT_FOUND,
    SKILL_TIMEOUT,
    DriverError,
    SubagentInvokeResult,
)
from app.quality_loop.s4_driver.subagent_dispatcher import (
    MockSkillBridge,
    SubagentDispatcher,
)


class TestSubagentDispatcherHappy:
    """§2 正向 · invoke 成功路径（TC-045 / TC-404）。"""

    def test_TC_L104_L205_045_invoke_success_returns_success_result(self) -> None:
        """TC-L104-L205-045 · SkillInvoker.invoke 成功 · status=success + invoke_id 有值。"""
        disp = SubagentDispatcher()
        r = disp.invoke(intent="red_test_creation")
        assert isinstance(r, SubagentInvokeResult)
        assert r.status == "success"
        assert r.invoke_id.startswith("iv-"), "§2.2 invoke_id uuid7 前缀"
        assert r.skill_intent == "red_test_creation"
        assert r.error_code is None

    def test_TC_L104_L205_045b_invoke_count_increments(self) -> None:
        """TC-L104-L205-045b · invoke_count 每次 +1（driver 观测用）。"""
        disp = SubagentDispatcher()
        disp.invoke(intent="red_test_creation")
        disp.invoke(intent="green_test_implementation")
        assert disp.invoke_count == 2

    def test_TC_L104_L205_404_ic04_intents_triple_pattern(self) -> None:
        """TC-L104-L205-404 · IC-04 驱动 red/green/self_repair 三态 · 都返 success（mock 默认）。"""
        disp = SubagentDispatcher()
        for intent in ("red_test_creation", "green_test_implementation", "code_fix_attempt"):
            r = disp.invoke(intent=intent)
            assert r.status == "success"
            assert r.skill_intent == intent

    def test_TC_L104_L205_404b_stub_plan_consumed_in_order(self) -> None:
        """TC-L104-L205-404b · stub_plan 优先 · 按序弹。"""
        plan = [
            SubagentInvokeResult(invoke_id="iv-a", skill_intent="x", status="success"),
            SubagentInvokeResult(invoke_id="iv-b", skill_intent="x", status="partial"),
        ]
        disp = SubagentDispatcher(bridge=MockSkillBridge(stub_plan=list(plan)))
        r1 = disp.invoke(intent="x")
        r2 = disp.invoke(intent="x")
        assert r1.invoke_id == "iv-a"
        assert r2.invoke_id == "iv-b"
        assert r2.status == "partial"


class TestSubagentDispatcherNegative:
    """§3 负向 · 4 类 Skill 错误码 + INTERNAL_ASSERT。"""

    def test_TC_L104_L205_107_skill_invoke_fail_wraps_status_fail(self) -> None:
        """TC-L104-L205-107 · SKILL_INVOKE_FAIL · status=fail · error_code 对齐。"""
        disp = SubagentDispatcher(bridge=MockSkillBridge(fail_after_n=1))
        r = disp.invoke(intent="red_test_creation")
        assert r.status == "fail"
        assert r.error_code == SKILL_INVOKE_FAIL

    def test_TC_L104_L205_120_skill_not_found(self) -> None:
        """TC-L104-L205-120 · 未注册 intent → SKILL_NOT_FOUND。"""
        disp = SubagentDispatcher(bridge=MockSkillBridge(not_found_after_n=1))
        r = disp.invoke(intent="unknown_intent")
        assert r.status == "fail"
        assert r.error_code == SKILL_NOT_FOUND
        assert "unknown_intent" in r.error_message

    def test_TC_L104_L205_121_skill_budget_exhausted(self) -> None:
        """TC-L104-L205-121 · 预算耗尽 → SKILL_BUDGET_EXHAUSTED · token_cost 追平预算。"""
        disp = SubagentDispatcher(bridge=MockSkillBridge(budget_exhausted_after_n=1))
        r = disp.invoke(intent="green_test_implementation", budget_tokens=5000)
        assert r.status == "fail"
        assert r.error_code == SKILL_BUDGET_EXHAUSTED
        assert r.token_cost == 5000

    def test_TC_L104_L205_122_skill_timeout(self) -> None:
        """TC-L104-L205-122 · 超时 → SKILL_TIMEOUT · duration_ms 等于 timeout_ms。"""
        disp = SubagentDispatcher(bridge=MockSkillBridge(timeout_after_n=1))
        r = disp.invoke(intent="red_test_creation", timeout_ms=3000)
        assert r.status == "fail"
        assert r.error_code == SKILL_TIMEOUT
        assert r.duration_ms == 3000

    def test_TC_L104_L205_135_internal_assert_on_empty_intent(self) -> None:
        """TC-L104-L205-135 · 内部 bug · 空 intent → INTERNAL_ASSERT。"""
        disp = SubagentDispatcher()
        with pytest.raises(DriverError) as exc:
            disp.invoke(intent="")
        assert exc.value.code == INTERNAL_ASSERT

    def test_TC_L104_L205_135b_internal_assert_on_non_str_intent(self) -> None:
        """TC-L104-L205-135b · 非 str intent → INTERNAL_ASSERT。"""
        disp = SubagentDispatcher()
        with pytest.raises(DriverError) as exc:
            disp.invoke(intent=None)  # type: ignore[arg-type]
        assert exc.value.code == INTERNAL_ASSERT


class TestSubagentDispatcherFlakyCombos:
    """§9 边界 · flaky · N 次成功 + 之后全 fail 的模式。"""

    def test_flaky_first_success_then_fail(self) -> None:
        """flaky 模式 · fail_after_n=2 · 第 1 次 success · 第 2 次 起 fail。"""
        disp = SubagentDispatcher(bridge=MockSkillBridge(fail_after_n=2))
        r1 = disp.invoke(intent="x")
        r2 = disp.invoke(intent="x")
        assert r1.status == "success"
        assert r2.status == "fail"
        assert r2.error_code == SKILL_INVOKE_FAIL
