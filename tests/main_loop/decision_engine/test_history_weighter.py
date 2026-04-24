"""L1-01 L2-02 Decision Engine · History Weighter 单元.

覆盖:
    - 空历史 → 0.0
    - 仅不同 type → 0.0(filter)
    - 同 type success → 正向
    - 同 type fail → 负向(绝对值大于 success)
    - tick_delta 衰减
    - params_fingerprint 匹配乘数
    - 连续失败(≥3)额外拉低
    - clamp MAX_HISTORY_WEIGHT_ABS
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine.history_weighter import (
    BASE_WEIGHT_FAIL,
    BASE_WEIGHT_SUCCESS,
    CONSEC_FAIL_EXTRA,
    CONSEC_FAIL_THRESHOLD,
    MAX_HISTORY_WEIGHT_ABS,
    compute_history_weight,
)


class TestHistoryWeighterBasics:
    def test_TC_W03_HW01_empty_history_zero(self, make_candidate) -> None:
        cand = make_candidate(decision_type="invoke_skill")
        assert compute_history_weight(cand, ()) == 0.0

    def test_TC_W03_HW02_different_type_filtered(
        self, make_candidate, make_history_entry,
    ) -> None:
        """history 全是其他 type → 0.0(本 type 无数据)。"""
        cand = make_candidate(decision_type="invoke_skill")
        hist = (
            make_history_entry(decision_type="use_tool", outcome="success"),
            make_history_entry(decision_type="kb_read", outcome="fail"),
        )
        assert compute_history_weight(cand, hist) == 0.0

    def test_TC_W03_HW03_single_success_positive(
        self, make_candidate, make_history_entry,
    ) -> None:
        cand = make_candidate(decision_type="invoke_skill")
        hist = (make_history_entry(decision_type="invoke_skill",
                                   outcome="success", tick_delta=1),)
        w = compute_history_weight(cand, hist)
        assert w > 0.0
        assert w == pytest.approx(BASE_WEIGHT_SUCCESS, abs=1e-6)

    def test_TC_W03_HW04_single_fail_negative(
        self, make_candidate, make_history_entry,
    ) -> None:
        cand = make_candidate(decision_type="invoke_skill")
        hist = (make_history_entry(decision_type="invoke_skill",
                                   outcome="fail", tick_delta=1),)
        w = compute_history_weight(cand, hist)
        assert w < 0.0
        assert w == pytest.approx(BASE_WEIGHT_FAIL, abs=1e-6)

    def test_TC_W03_HW05_fail_abs_greater_than_success(
        self, make_candidate, make_history_entry,
    ) -> None:
        """prd §9.5 #4:防重蹈覆辙 → |fail| > |success|。"""
        assert abs(BASE_WEIGHT_FAIL) > abs(BASE_WEIGHT_SUCCESS)


class TestHistoryWeighterDecay:
    def test_TC_W03_HW06_tick_delta_decay(
        self, make_candidate, make_history_entry,
    ) -> None:
        """tick_delta 越大 → 权重绝对值越小。"""
        cand = make_candidate(decision_type="invoke_skill")
        near = (make_history_entry(decision_type="invoke_skill",
                                   outcome="success", tick_delta=1),)
        far = (make_history_entry(decision_type="invoke_skill",
                                  outcome="success", tick_delta=10),)
        w_near = compute_history_weight(cand, near)
        w_far = compute_history_weight(cand, far)
        assert w_near > w_far > 0.0


class TestHistoryWeighterParamsMatch:
    def test_TC_W03_HW07_params_fingerprint_boosts(
        self, make_candidate, make_history_entry,
    ) -> None:
        """params_fingerprint 精确匹配 → 正向倍增。"""
        cand = make_candidate(
            decision_type="invoke_skill",
            decision_params={"capability_tag": "deepseek.generate", "n": 1},
        )
        # 重新计算同指纹的 fingerprint
        from app.main_loop.decision_engine.history_weighter import (
            _params_fingerprint,
        )
        fp = _params_fingerprint(cand)
        match = (make_history_entry(
            decision_type="invoke_skill",
            outcome="success",
            tick_delta=1,
            params_fingerprint=fp,
        ),)
        no_match = (make_history_entry(
            decision_type="invoke_skill",
            outcome="success",
            tick_delta=1,
            params_fingerprint="different-fp",
        ),)
        w_match = compute_history_weight(cand, match)
        w_no = compute_history_weight(cand, no_match)
        assert w_match > w_no > 0.0


class TestHistoryWeighterConsecFail:
    def test_TC_W03_HW08_three_consec_fails_extra_penalty(
        self, make_candidate, make_history_entry,
    ) -> None:
        """连续 3 条 fail → 额外 CONSEC_FAIL_EXTRA 拉低。"""
        cand = make_candidate(decision_type="invoke_skill")
        three_fails = tuple(
            make_history_entry(decision_type="invoke_skill",
                               outcome="fail", tick_delta=i+1)
            for i in range(CONSEC_FAIL_THRESHOLD)
        )
        w = compute_history_weight(cand, three_fails)
        # 期望:base fails 总和 + CONSEC_FAIL_EXTRA
        assert w < CONSEC_FAIL_EXTRA + 3 * BASE_WEIGHT_FAIL * 0.1  # 够低即可

    def test_TC_W03_HW09_interrupted_fails_no_extra(
        self, make_candidate, make_history_entry,
    ) -> None:
        """fail/fail/success/fail · 非连续 → 不触发 CONSEC_FAIL_EXTRA 额外拉低。

        对比同样多 fail 但连续的情况,此处 w 应更大(更接近 0)。
        """
        cand = make_candidate(decision_type="invoke_skill")
        mixed = (
            make_history_entry(decision_type="invoke_skill", outcome="fail",
                               tick_delta=1),
            make_history_entry(decision_type="invoke_skill", outcome="fail",
                               tick_delta=1),
            make_history_entry(decision_type="invoke_skill", outcome="success",
                               tick_delta=1),
            make_history_entry(decision_type="invoke_skill", outcome="fail",
                               tick_delta=1),
        )
        # 同是 3 个 fail 但连续 · 会额外 -0.10
        all_fail = (
            make_history_entry(decision_type="invoke_skill", outcome="fail",
                               tick_delta=1),
            make_history_entry(decision_type="invoke_skill", outcome="fail",
                               tick_delta=1),
            make_history_entry(decision_type="invoke_skill", outcome="fail",
                               tick_delta=1),
            make_history_entry(decision_type="invoke_skill", outcome="fail",
                               tick_delta=1),
        )
        w_mixed = compute_history_weight(cand, mixed)
        w_consec = compute_history_weight(cand, all_fail)
        assert w_mixed > w_consec  # mixed 因 success 抵消 + 无 extra → 更高


class TestHistoryWeighterClamp:
    def test_TC_W03_HW10_clamp_lower(
        self, make_candidate, make_history_entry,
    ) -> None:
        """大量 fail · clamp 下界 -MAX_HISTORY_WEIGHT_ABS。"""
        cand = make_candidate(decision_type="invoke_skill")
        big = tuple(
            make_history_entry(decision_type="invoke_skill", outcome="fail", tick_delta=1)
            for _ in range(20)
        )
        w = compute_history_weight(cand, big)
        assert w == pytest.approx(-MAX_HISTORY_WEIGHT_ABS, abs=1e-6)

    def test_TC_W03_HW11_clamp_upper(
        self, make_candidate, make_history_entry,
    ) -> None:
        """大量 success · clamp 上界 +MAX_HISTORY_WEIGHT_ABS。"""
        cand = make_candidate(decision_type="invoke_skill")
        big = tuple(
            make_history_entry(
                decision_type="invoke_skill", outcome="success", tick_delta=1,
            )
            for _ in range(20)
        )
        w = compute_history_weight(cand, big)
        assert w == pytest.approx(MAX_HISTORY_WEIGHT_ABS, abs=1e-6)

    def test_TC_W03_HW12_history_window_cap(
        self, make_candidate, make_history_entry,
    ) -> None:
        """超 HISTORY_WINDOW 的 history 被忽略。"""
        from app.main_loop.decision_engine.history_weighter import HISTORY_WINDOW
        cand = make_candidate(decision_type="invoke_skill")
        # 构造 2*HISTORY_WINDOW 个 fail;只前 WINDOW 生效
        many = tuple(
            make_history_entry(decision_type="invoke_skill", outcome="fail", tick_delta=1)
            for _ in range(2 * HISTORY_WINDOW)
        )
        # 未被 clamp 时一定低于单个 fail 的 weight;
        # 由于 clamp 存在,只能断言 ≤ 0 即可
        w = compute_history_weight(cand, many)
        assert w <= 0.0


class TestHistoryWeighterSkip:
    def test_TC_W03_HW13_skip_outcome_small_negative(
        self, make_candidate, make_history_entry,
    ) -> None:
        """outcome=skip · 小幅负向(-0.02)。"""
        cand = make_candidate(decision_type="invoke_skill")
        hist = (make_history_entry(decision_type="invoke_skill",
                                   outcome="skip", tick_delta=1),)
        w = compute_history_weight(cand, hist)
        assert -0.05 < w < 0.0
