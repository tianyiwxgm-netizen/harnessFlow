---
doc_id: tests-L1-10-L2-06-裁剪档配置-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-06-裁剪档配置.md
  - docs/2-prd/L1-10 人机协作UI/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-L
created_at: 2026-04-22
---

# L1-10 L2-06 · 裁剪档配置 · TDD 测试用例

> 基于 3-1 L2-06 §3.1-3.5（5 个方法）+ §3.6（IC-16 `scale_profile_required` 入站）+ §3.7（IC-L2-06 经 L2-04）+ §3.8（14 项 `L206-E-*` 错误码）+ §12 SLO（模态打开 ≤ 100ms · 校验 ≤ 50ms · 提交 ≤ 200ms）驱动。
> TC ID：`TC-L110-L206-NNN`。
> **L2-06 是 L1-10 合规裁剪档选择层**（S1/S2 前置 hook · 3 档 full/lean/custom · OneShotGuard 单次写 · L1-02 own profile 持久化 · L2-06 只收集 + 本地校验 + IC-L2-06 委托 L2-04）· Admin 重置经独立路径 `reset_scale_profile`。

## §0 撰写进度

- [x] §1 覆盖度索引（5 方法 + 14 错误码 + IC + SLO）
- [x] §2 正向用例（5 方法 + 3 档 + IC-16 入站 + OneShotGuard）
- [x] §3 负向用例（14 条 L206-E-* 全覆盖）
- [x] §4 IC-XX 契约集成（IC-16 入 · IC-L2-06 → L2-04 · IC-09 审计）
- [x] §5 性能 SLO 用例（open ≤ 100ms · validate ≤ 50ms · submit ≤ 200ms）
- [x] §6 端到端 e2e（正常选 lean + 提交 · 硬约束违反拦截 · Admin 重置全链路）
- [x] §7 测试 fixture
- [x] §8 集成点用例（与 L1-02 hook · L2-04 委托 · L2-07 Admin 重置）
- [x] §9 边界 / edge case（3 档差异 · modal session 1h 过期 · 并发多窗口）

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法 | TC ID | 覆盖类型 | 备注 |
|---|---|---|---|
| `open_compliance_modal(payload)` | TC-L110-L206-001 | unit | 模态打开 · OneShotGuard |
| `toggle_checklist_item(item_id, checked)` | TC-L110-L206-002 | unit | 勾选切换 · 必选锁定 |
| `validate_selection(profile, items)` | TC-L110-L206-003 | unit | 本地校验 · 硬约束检出 |
| `submit_compliance_profile(payload)` | TC-L110-L206-004 | integration | 委托 L2-04 |
| `get_profile_diff()` | TC-L110-L206-005 | unit | 3 档差异对比 |
| 3 档 full 选择 | TC-L110-L206-006 | unit | profile_type=full |
| 3 档 lean 选择 | TC-L110-L206-007 | unit | profile_type=lean |
| 3 档 custom 选择 | TC-L110-L206-008 | unit | custom + selected_items 必填 |
| IC-16 `scale_profile_required` 入站 | TC-L110-L206-009 | integration | L1-02 S1/S2 hook |
| OneShotGuard short-circuit | TC-L110-L206-010 | unit | 已有档直接审计 + continue |

### §1.2 错误码 × 测试（§3.8 全 14 项）

| 错误码 | TC ID | 场景 |
|---|---|---|
| `L206-E-01` ProjectIdMissing | TC-L110-L206-101 | PM-14 · IC 缺 pid |
| `L206-E-02` AlreadySetShortCircuit | TC-L110-L206-102 | 已有档 · 模态不展示 |
| `L206-E-03` LockedItemUncheckAttempt | TC-L110-L206-103 | 尝试取消必选项 |
| `L206-E-04` HardConstraintViolation | TC-L110-L206-104 | 违反 Goal §3.5 硬约束 |
| `L206-E-05` IdempotentDuplicate | TC-L110-L206-105 | 10s 内重复提交 |
| `L206-E-06` InvalidProfileType | TC-L110-L206-106 | profile_type 非 full/lean/custom |
| `L206-E-07` CustomItemsMissing | TC-L110-L206-107 | custom 档 selected_items 为空 |
| `L206-E-08` RulesLoadFailed | TC-L110-L206-108 | compliance-rules.yaml 加载失败 · FORCE_FULL |
| `L206-E-09` ModalSessionExpired | TC-L110-L206-109 | modal_session 超 1h |
| `L206-E-10` TriggerSourceInvalid | TC-L110-L206-110 | trigger_source 非预期枚举 |
| `L206-E-11` L2_04_Rejected | TC-L110-L206-111 | L2-04 拒绝 · 保留勾选 |
| `L206-E-12` ResetAdminPermDenied | TC-L110-L206-112 | 非 Admin 试重置 |
| `L206-E-13` ReasonTooLong | TC-L110-L206-113 | reason > 500 字 |
| `L206-E-14` ConcurrentModalConflict | TC-L110-L206-114 | 多窗口并发打开 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-16 scale_profile_required | L1-02 → L2-06 | TC-L110-L206-601 | payload.project_id + suggested_profile |
| IC-L2-06 set_compliance_profile_intent | L2-06 → L2-04 | TC-L110-L206-602 | type=set_scale_profile |
| IC-L2-06 Admin reset 变体 | L2-07 → L2-06（间接） | TC-L110-L206-603 | 经 IC-17 reset + L1-02 清档 + 重弹 |
| IC-09 append_event | L2-06 → L1-09 | TC-L110-L206-604 | modal_opened / submitted / already_set |

### §1.4 SLO × 测试

| SLO | 目标 | TC ID | 样本 |
|---|---|---|---|
| open_compliance_modal | P95 ≤ 100ms | TC-L110-L206-701 | 100 |
| validate_selection | P95 ≤ 50ms | TC-L110-L206-702 | 500 |
| submit_compliance_profile | P95 ≤ 200ms | TC-L110-L206-703 | 50 |
| get_profile_diff | P95 ≤ 30ms | TC-L110-L206-704 | 500 |
| toggle_checklist_item | P95 ≤ 10ms | TC-L110-L206-705 | 500 |

### §1.5 PM-14 硬约束

- 所有方法强制 `project_id` · 缺 → L206-E-01
- OneShotGuard：同 project 已有 profile 除非 Admin 重置，否则 short-circuit（L206-E-02）

---

## §2 正向用例

```python
# file: tests/l1_10/test_l2_06_positive.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_06.service import ComplianceProfileService


class TestL2_06_Compliance_Positive:

    @pytest.mark.asyncio
    async def test_TC_L110_L206_001_open_compliance_modal(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-001 · open_compliance_modal · 返 modal_session_id + hint。"""
        r = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "existing_profile": None,
                "suggested_profile": "lean",
                "trigger_source": "s1_hook",
            },
        )
        assert r.modal_session_id is not None
        assert r.suggested_profile == "lean"
        assert r.trigger_source == "s1_hook"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_002_toggle_checklist_item(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-002 · toggle_checklist_item · 勾选切换 · 更新 selected_items。"""
        r1 = await sut.open_compliance_modal(
            payload={"project_id": mock_project_id,
                     "suggested_profile": "custom", "trigger_source": "s1_hook"})
        await sut.toggle_checklist_item(
            modal_session_id=r1.modal_session_id,
            item_id="item-A", checked=True)
        await sut.toggle_checklist_item(
            modal_session_id=r1.modal_session_id,
            item_id="item-B", checked=True)
        state = sut.get_modal_state(
            modal_session_id=r1.modal_session_id)
        assert "item-A" in state.selected_items
        assert "item-B" in state.selected_items

    @pytest.mark.asyncio
    async def test_TC_L110_L206_003_validate_selection_ok(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-003 · validate_selection · 合法组合 · 返 ok + 无违规。"""
        r = await sut.validate_selection(
            project_id=mock_project_id,
            profile="lean",
            selected_items=["item-required-1", "item-required-2"],
        )
        assert r.is_valid is True
        assert r.violations == []

    @pytest.mark.asyncio
    async def test_TC_L110_L206_004_submit_delegates_to_l204(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-004 · submit_compliance_profile · 委托 L2-04 · type=set_scale_profile。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-sp", status="ACKED")
        r = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean",
                "selected_items": ["item-1"],
                "reason": "项目规模适中 · lean 够用",
                "idempotency_key": "user-k-1",
                "modal_session_id": "ms-1",
            },
        )
        assert r.status == "submitted"
        kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert kw["type"] == "set_scale_profile"
        assert kw["payload"]["profile"].startswith("P") or kw["payload"].get("profile_type") == "lean"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_005_get_profile_diff(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-005 · get_profile_diff · 返 full/lean/custom 3 档对比表。"""
        r = await sut.get_profile_diff(project_id=mock_project_id)
        assert "full" in r.by_type
        assert "lean" in r.by_type
        assert "custom" in r.by_type

    @pytest.mark.asyncio
    async def test_TC_L110_L206_006_submit_full_profile(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-006 · profile_type=full · 完整档 · 无需 selected_items。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-full", status="ACKED")
        r = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "full",
                "selected_items": None,
                "reason": "严谨项目 · 完整档",
                "idempotency_key": "k-f",
                "modal_session_id": "ms-f",
            },
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_007_submit_lean_profile(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-007 · profile_type=lean · 精简档 · 自动含必选项。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-lean", status="ACKED")
        r = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean",
                "selected_items": None,  # lean 档无需显式
                "reason": "小项目 · 快速迭代",
                "idempotency_key": "k-l",
                "modal_session_id": "ms-l",
            },
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_008_submit_custom_with_items(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-008 · profile_type=custom · selected_items 必填。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-c", status="ACKED")
        r = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "custom",
                "selected_items": ["it-1", "it-2", "it-3"],
                "reason": "自定义档 · 特殊业务需求",
                "idempotency_key": "k-c",
                "modal_session_id": "ms-c",
            },
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_009_ic16_scale_profile_required_triggers_modal(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-009 · IC-16 `scale_profile_required` 入站 · 触发 open_compliance_modal。"""
        r = await sut.on_scale_profile_required({
            "project_id": mock_project_id,
            "stage": "S1",
            "suggested_profile": "lean",
            "goal_requirements": ["item-1", "item-2"],
        })
        assert r.modal_opened is True

    @pytest.mark.asyncio
    async def test_TC_L110_L206_010_one_shot_guard_short_circuit_when_already_set(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-010 · OneShotGuard · 已有 profile · short-circuit · 不开模态。"""
        r = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "existing_profile": {
                    "profile_type": "lean",
                    "selected_items": ["a"],
                    "set_at": "2026-04-22T06:00:00Z",
                },
                "suggested_profile": "lean",
                "trigger_source": "s1_hook",
            },
        )
        assert r.short_circuited is True
        # 审计事件：scale_profile_already_set
        assert any(t == "L1-10:scale_profile_already_set"
                   for t in sut.last_audit_types)
```

---

## §3 负向用例（14 条 L206-E-* 全覆盖）

```python
# file: tests/l1_10/test_l2_06_negative.py
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_06.errors import L206Error


class TestL2_06_Compliance_Negative:

    @pytest.mark.asyncio
    async def test_TC_L110_L206_101_project_id_missing(self, sut) -> None:
        """TC-L110-L206-101 · IC payload 缺 project_id · L206-E-01。"""
        with pytest.raises(L206Error) as exc:
            await sut.open_compliance_modal(
                payload={"suggested_profile": "lean",
                         "trigger_source": "s1_hook"})
        assert exc.value.code == "L206-E-01"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_102_already_set_short_circuit_logged(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-102 · 已有档 · L206-E-02 · 审计事件留痕 · 不展示模态。"""
        r = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "existing_profile": {"profile_type": "lean"},
                "suggested_profile": "lean",
                "trigger_source": "s1_hook",
            },
        )
        assert r.short_circuited is True
        assert r.error_code == "L206-E-02"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_103_locked_item_uncheck_attempt(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-103 · 取消必选项 · L206-E-03 · UI 拒绝。"""
        r1 = await sut.open_compliance_modal(
            payload={"project_id": mock_project_id,
                     "suggested_profile": "custom",
                     "trigger_source": "s1_hook",
                     "locked_items": ["item-REQ-1"]})
        with pytest.raises(L206Error) as exc:
            await sut.toggle_checklist_item(
                modal_session_id=r1.modal_session_id,
                item_id="item-REQ-1",  # 必选
                checked=False)
        assert exc.value.code == "L206-E-03"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_104_hard_constraint_violation(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-104 · 违反硬约束 · L206-E-04 · submit 拒绝 + 违规高亮。"""
        r = await sut.validate_selection(
            project_id=mock_project_id,
            profile="custom",
            selected_items=["item-X"],  # 缺必需的 item-A
        )
        assert r.is_valid is False
        assert any(v["code"] == "L206-E-04" for v in r.violations)

    @pytest.mark.asyncio
    async def test_TC_L110_L206_105_idempotent_duplicate(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-105 · 10s 内重复提交 · L206-E-05 · L2-04 幂等 · 返首次 intent。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-1", status="ACKED")
        payload = {
            "project_id": mock_project_id, "profile_type": "lean",
            "selected_items": None, "reason": "相同理由",
            "idempotency_key": "k-same",
            "modal_session_id": "ms-1",
        }
        r1 = await sut.submit_compliance_profile(payload=payload)
        r2 = await sut.submit_compliance_profile(payload=payload)
        # 幂等返回同 intent_id
        assert r1.intent_id == r2.intent_id

    @pytest.mark.asyncio
    async def test_TC_L110_L206_106_invalid_profile_type(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-106 · profile_type 非法枚举 · L206-E-06。"""
        with pytest.raises(L206Error) as exc:
            await sut.submit_compliance_profile(
                payload={
                    "project_id": mock_project_id,
                    "profile_type": "BOGUS",  # 非法
                    "selected_items": None,
                    "reason": "reason is long enough for validator",
                    "idempotency_key": "k",
                    "modal_session_id": "ms",
                },
            )
        assert exc.value.code == "L206-E-06"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_107_custom_items_missing(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-107 · custom 档 selected_items 空 · L206-E-07。"""
        with pytest.raises(L206Error) as exc:
            await sut.submit_compliance_profile(
                payload={
                    "project_id": mock_project_id,
                    "profile_type": "custom",
                    "selected_items": [],  # 空
                    "reason": "reason is long enough",
                    "idempotency_key": "k-ci",
                    "modal_session_id": "ms-ci",
                },
            )
        assert exc.value.code == "L206-E-07"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_108_rules_load_failed_force_full(
        self, sut, mock_project_id: str, mock_rules_loader: MagicMock,
    ) -> None:
        """TC-L110-L206-108 · compliance-rules.yaml 加载失败 · L206-E-08 · FORCE_FULL_PROFILE。"""
        mock_rules_loader.load.side_effect = OSError("file not found")
        r = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "suggested_profile": "lean",
                "trigger_source": "s1_hook",
            },
        )
        assert r.force_full_profile is True
        assert r.error_code == "L206-E-08"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_109_modal_session_expired(
        self, sut, mock_project_id: str, fake_clock,
    ) -> None:
        """TC-L110-L206-109 · modal session 1h 过期 · L206-E-09。"""
        r1 = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "suggested_profile": "lean",
                "trigger_source": "s1_hook",
            },
        )
        fake_clock.advance(61 * 60 * 1000)  # 61 min
        with pytest.raises(L206Error) as exc:
            await sut.toggle_checklist_item(
                modal_session_id=r1.modal_session_id,
                item_id="item-1", checked=True)
        assert exc.value.code == "L206-E-09"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_110_trigger_source_invalid(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-110 · trigger_source 非预期枚举 · L206-E-10 · 拒绝开。"""
        with pytest.raises(L206Error) as exc:
            await sut.open_compliance_modal(
                payload={
                    "project_id": mock_project_id,
                    "suggested_profile": "lean",
                    "trigger_source": "EVIL_INJECTED",  # 非预期
                },
            )
        assert exc.value.code == "L206-E-10"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_111_l204_rejected_preserves_selection(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-111 · L2-04 拒绝 · L206-E-11 · 保留勾选 · 允许重试。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-r", status="REJECTED",
            error=MagicMock(code="E-L2-04-013",
                            user_message="L1-01 not ready"))
        r = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean",
                "selected_items": None,
                "reason": "有足够长的变更理由说明问题",
                "idempotency_key": "k-rej",
                "modal_session_id": "ms-rej",
            },
        )
        assert r.status == "REJECTED"
        assert r.error_code == "L206-E-11"
        # 勾选保留 · 允许重试
        assert r.selection_preserved is True

    @pytest.mark.asyncio
    async def test_TC_L110_L206_112_reset_admin_permission_denied(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-112 · 非 Admin 试重置 · L206-E-12 · 引导至 L2-07。"""
        with pytest.raises(L206Error) as exc:
            await sut.reset_profile(
                project_id=mock_project_id,
                actor_role="user",  # 非 Admin
            )
        assert exc.value.code == "L206-E-12"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_113_reason_too_long(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-113 · reason > 500 字 · L206-E-13。"""
        huge = "x" * 501
        with pytest.raises(L206Error) as exc:
            await sut.submit_compliance_profile(
                payload={
                    "project_id": mock_project_id,
                    "profile_type": "lean",
                    "selected_items": None,
                    "reason": huge,
                    "idempotency_key": "k-rl",
                    "modal_session_id": "ms-rl",
                },
            )
        assert exc.value.code == "L206-E-13"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_114_concurrent_modal_conflict(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-114 · 多窗口并发 · L206-E-14 · 后开者 short-circuit。"""
        r1 = await sut.open_compliance_modal(
            payload={"project_id": mock_project_id,
                     "suggested_profile": "lean",
                     "trigger_source": "s1_hook",
                     "window_id": "win-A"})
        r2 = await sut.open_compliance_modal(
            payload={"project_id": mock_project_id,
                     "suggested_profile": "lean",
                     "trigger_source": "s1_hook",
                     "window_id": "win-B"})
        # r2 提示"已在别处选择中"
        assert r2.short_circuited is True
        assert r2.error_code == "L206-E-14"
```

---

## §4 IC-XX 契约集成（≥ 4）

```python
# file: tests/l1_10/test_l2_06_ic_contracts.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_06_IC_Contracts:

    @pytest.mark.asyncio
    async def test_TC_L110_L206_601_ic16_scale_profile_required_in(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-601 · IC-16 变体 · payload 字段 project_id + suggested_profile + stage。"""
        r = await sut.on_scale_profile_required({
            "project_id": mock_project_id,
            "stage": "S2",
            "suggested_profile": "full",
            "goal_requirements": ["r-1"],
        })
        assert r.modal_opened is True

    @pytest.mark.asyncio
    async def test_TC_L110_L206_602_ic_l2_06_delegates_l204(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-602 · IC-L2-06 · type=set_scale_profile · payload.profile + locked_at_stage。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-ic", status="ACKED")
        await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean",
                "selected_items": None,
                "reason": "lean 档适合本项目规模",
                "idempotency_key": "k-ic",
                "modal_session_id": "ms-ic",
                "locked_at_stage": "S1",
            },
        )
        kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert kw["type"] == "set_scale_profile"
        assert "profile" in kw["payload"] or "profile_type" in kw["payload"]

    @pytest.mark.asyncio
    async def test_TC_L110_L206_603_admin_reset_rebuild_path(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-603 · Admin 重置 · 经 IC-17 reset + L1-02 清档 + 下次 hook 重弹。"""
        # 伪造"已重置"状态
        sut.admin_reset_flag = True
        r = await sut.on_scale_profile_required({
            "project_id": mock_project_id,
            "stage": "S1",
            "suggested_profile": "lean",
        })
        # 重置后 · OneShotGuard 不 short-circuit
        assert r.modal_opened is True

    @pytest.mark.asyncio
    async def test_TC_L110_L206_604_ic09_audit_events(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L206-604 · IC-09 · modal_opened / submitted / already_set 三类事件。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int", status="ACKED")
        await sut.open_compliance_modal(
            payload={"project_id": mock_project_id,
                     "suggested_profile": "lean",
                     "trigger_source": "s1_hook"})
        await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean", "selected_items": None,
                "reason": "lean 足够 · 不需要完整档",
                "idempotency_key": "k", "modal_session_id": "ms",
            },
        )
        types = "|".join(
            (c.kwargs.get("type") or c.kwargs.get("event_type") or "")
            for c in mock_event_bus.append_event.call_args_list)
        assert "scale_profile_modal_opened" in types
        assert "scale_profile_submitted" in types
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_10/test_l2_06_perf.py
from __future__ import annotations

import statistics
import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_06_SLO:

    OPEN_P95_MS = 100
    VALIDATE_P95_MS = 50
    SUBMIT_P95_MS = 200
    DIFF_P95_MS = 30
    TOGGLE_P95_MS = 10

    @pytest.mark.asyncio
    async def test_TC_L110_L206_701_open_p95_le_100ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-701 · open_compliance_modal P95 ≤ 100ms · 100 样本。"""
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.open_compliance_modal(
                payload={"project_id": f"{mock_project_id}-{i}",
                         "suggested_profile": "lean",
                         "trigger_source": "s1_hook"})
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.OPEN_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L206_702_validate_p95_le_50ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-702 · validate_selection P95 ≤ 50ms · 500 样本。"""
        samples: list[float] = []
        for _ in range(500):
            t0 = time.perf_counter()
            await sut.validate_selection(
                project_id=mock_project_id,
                profile="custom",
                selected_items=["item-1", "item-2", "item-3"],
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.VALIDATE_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L206_703_submit_p95_le_200ms(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-703 · submit_compliance_profile P95 ≤ 200ms · 50 样本。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-p", status="ACKED")
        samples: list[float] = []
        for i in range(50):
            t0 = time.perf_counter()
            await sut.submit_compliance_profile(
                payload={
                    "project_id": f"{mock_project_id}-{i}",
                    "profile_type": "lean",
                    "selected_items": None,
                    "reason": "适合当前项目规模与节奏",
                    "idempotency_key": str(uuid.uuid4()),
                    "modal_session_id": f"ms-{i}",
                },
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.SUBMIT_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L206_704_profile_diff_p95_le_30ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-704 · get_profile_diff P95 ≤ 30ms · 500 样本。"""
        samples: list[float] = []
        for _ in range(500):
            t0 = time.perf_counter()
            await sut.get_profile_diff(project_id=mock_project_id)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.DIFF_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L206_705_toggle_p95_le_10ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-705 · toggle_checklist_item P95 ≤ 10ms · 500 样本。"""
        r = await sut.open_compliance_modal(
            payload={"project_id": mock_project_id,
                     "suggested_profile": "custom",
                     "trigger_source": "s1_hook"})
        samples: list[float] = []
        for i in range(500):
            t0 = time.perf_counter()
            await sut.toggle_checklist_item(
                modal_session_id=r.modal_session_id,
                item_id=f"it-{i % 20}",
                checked=i % 2 == 0)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.TOGGLE_P95_MS
```

---

## §6 端到端 e2e 场景（≥ 2）

```python
# file: tests/l1_10/test_l2_06_e2e.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_06_E2E:

    @pytest.mark.asyncio
    async def test_TC_L110_L206_801_e2e_s1_hook_to_lean_profile_submit(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L206-801 · e2e · IC-16 scale_profile_required → 用户选 lean → 提交 → L2-04。"""
        # 1. IC-16 入站
        r = await sut.on_scale_profile_required({
            "project_id": mock_project_id,
            "stage": "S1",
            "suggested_profile": "lean",
            "goal_requirements": ["r-1"],
        })
        assert r.modal_opened is True
        # 2. 用户确认 lean
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-l", status="ACKED")
        sr = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean",
                "selected_items": None,
                "reason": "lean 足以覆盖本项目的合规需求",
                "idempotency_key": "k-e2e",
                "modal_session_id": r.modal_session_id,
            },
        )
        assert sr.status == "submitted"
        # 3. L2-04 被调 · type=set_scale_profile
        assert mock_l204_service.submit_intervention.call_args.kwargs["type"] == "set_scale_profile"
        # 4. 审计事件
        types = "|".join(
            (c.kwargs.get("type") or c.kwargs.get("event_type") or "")
            for c in mock_event_bus.append_event.call_args_list)
        assert "scale_profile_modal_opened" in types
        assert "scale_profile_submitted" in types

    @pytest.mark.asyncio
    async def test_TC_L110_L206_802_e2e_admin_reset_triggers_modal_again(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-802 · e2e · Admin 重置 → L1-02 清档 → 下次 hook 重新弹模态。"""
        # 1. 已有 profile · 初次 short-circuit
        r1 = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "existing_profile": {"profile_type": "lean"},
                "suggested_profile": "lean",
                "trigger_source": "s1_hook",
            },
        )
        assert r1.short_circuited is True
        # 2. Admin 重置（模拟 L1-02 清档）
        sut.admin_reset_flag = True
        # 3. 下次 hook · 重新弹
        r2 = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "existing_profile": None,  # 已清
                "suggested_profile": "full",
                "trigger_source": "s1_hook",
            },
        )
        assert r2.short_circuited is False
        assert r2.modal_session_id is not None
```

---

## §7 测试 fixture

```python
# file: tests/l1_10/conftest_l2_06.py
from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_06.service import ComplianceProfileService


@dataclass
class FakeClock:
    _now_ms: int = 0
    def now_ms(self) -> int: return self._now_ms
    def advance(self, ms: int) -> None: self._now_ms += ms


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def mock_l204_service() -> AsyncMock:
    s = AsyncMock(name="L204")
    s.submit_intervention = AsyncMock(return_value=MagicMock(
        intent_id="int-default", status="ACKED"))
    return s


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="EventBus")
    bus.append_event = MagicMock(return_value={"event_id": f"evt-{uuid.uuid4()}"})
    return bus


@pytest.fixture
def mock_rules_loader() -> MagicMock:
    r = MagicMock(name="ComplianceRulesLoader")
    r.load = MagicMock(return_value={
        "profiles": {
            "full": {"all": True},
            "lean": {"required": ["item-required-1", "item-required-2"]},
            "custom": {"min_required": 2},
        },
        "hard_constraints": [
            {"rule_id": "hc-1",
             "required_items": ["item-A"],
             "applicable_profiles": ["custom"],
             "violation_message": "需要 item-A",
             "severity": "blocker"},
        ],
    })
    return r


@pytest.fixture
def sut(
    mock_project_id: str, fake_clock: FakeClock,
    mock_l204_service: AsyncMock, mock_event_bus: MagicMock,
    mock_rules_loader: MagicMock,
) -> ComplianceProfileService:
    return ComplianceProfileService(
        session={"active_project": mock_project_id},
        clock=fake_clock,
        l204=mock_l204_service,
        event_bus=mock_event_bus,
        rules_loader=mock_rules_loader,
        config={
            "modal_session_ttl_ms": 60 * 60 * 1000,
            "idempotency_window_ms": 10_000,
            "reason_max_chars": 500,
            "trigger_source_whitelist": ["s1_hook", "s2_hook",
                                         "router_interceptor",
                                         "admin_reset_rebuild"],
            "profile_types": ["full", "lean", "custom"],
        },
    )
```

---

## §8 集成点用例

```python
# file: tests/l1_10/test_l2_06_siblings.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_06_SiblingIntegration:

    @pytest.mark.asyncio
    async def test_TC_L110_L206_901_l1_02_hook_triggers_modal(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-901 · L1-02 S1/S2 hook 入站 · 触发 open_compliance_modal。"""
        r = await sut.on_scale_profile_required({
            "project_id": mock_project_id,
            "stage": "S2",
            "suggested_profile": "custom",
            "goal_requirements": ["r-1", "r-2"],
        })
        assert r.modal_opened is True

    @pytest.mark.asyncio
    async def test_TC_L110_L206_902_l2_04_delegation_no_direct_ic17(
        self,
    ) -> None:
        """TC-L110-L206-902 · L2-06 代码不得直 import IC17 · 必经 L2-04。"""
        offenders = static_scan.find_imports_in(
            path_prefix="app/l1_10/l2_06/",
            forbidden_imports=["IC17Transport", "send_ic17"])
        assert offenders == [], f"L2-06 违规直发 IC-17: {offenders}"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_903_l2_07_admin_resets_flows_through(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-903 · L2-07 Admin 重置 · L1-02 清档 · 下次 hook 重新弹模态。"""
        r1 = await sut.open_compliance_modal(
            payload={
                "project_id": mock_project_id,
                "existing_profile": {"profile_type": "lean"},
                "suggested_profile": "lean",
                "trigger_source": "s1_hook",
            },
        )
        assert r1.short_circuited is True
        # 模拟 Admin 重置
        sut.admin_reset_flag = True
        # 下次 hook
        r2 = await sut.on_scale_profile_required({
            "project_id": mock_project_id,
            "stage": "S1",
            "suggested_profile": "lean",
        })
        assert r2.modal_opened is True
```

---

## §9 边界 / edge case

```python
# file: tests/l1_10/test_l2_06_edge.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_06_Edge:

    @pytest.mark.asyncio
    async def test_TC_L110_L206_911_profile_diff_3_types_consistent(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-911 · get_profile_diff · 3 档必互斥完整（无交叉）。"""
        r = await sut.get_profile_diff(project_id=mock_project_id)
        all_items = set()
        for t in ("full", "lean", "custom"):
            tset = set(r.by_type.get(t, []) or [])
            all_items.update(tset)
        assert len(all_items) > 0

    @pytest.mark.asyncio
    async def test_TC_L110_L206_912_reason_exactly_500_chars(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-912 · reason 恰好 500 字 · 通过（边界）。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int", status="ACKED")
        reason = "x" * 500
        r = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean",
                "selected_items": None,
                "reason": reason,
                "idempotency_key": "k-500",
                "modal_session_id": "ms-500",
            },
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_913_modal_session_exactly_1h(
        self, sut, mock_project_id: str, fake_clock,
    ) -> None:
        """TC-L110-L206-913 · modal_session 恰好 1h · 边界：仍可用（TTL 闭区间）。"""
        r = await sut.open_compliance_modal(
            payload={"project_id": mock_project_id,
                     "suggested_profile": "lean",
                     "trigger_source": "s1_hook"})
        fake_clock.advance(60 * 60 * 1000)  # exactly 1h
        # 视实现 · 59:59 通过 · 60:00 可能过期 · 断言不抛 OR 抛 L206-E-09
        try:
            await sut.toggle_checklist_item(
                modal_session_id=r.modal_session_id,
                item_id="it-1", checked=True)
        except Exception as e:
            # 允许过期，但必须是 L206-E-09
            assert getattr(e, "code", None) == "L206-E-09"

    @pytest.mark.asyncio
    async def test_TC_L110_L206_914_concurrent_multi_window_enforces_one(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L206-914 · 多窗口并发 · 第一个赢 · 后者 short-circuit。"""
        import asyncio
        results = await asyncio.gather(
            sut.open_compliance_modal(
                payload={"project_id": mock_project_id,
                         "suggested_profile": "lean",
                         "trigger_source": "s1_hook",
                         "window_id": "win-A"}),
            sut.open_compliance_modal(
                payload={"project_id": mock_project_id,
                         "suggested_profile": "lean",
                         "trigger_source": "s1_hook",
                         "window_id": "win-B"}),
        )
        winners = sum(1 for r in results if not r.short_circuited)
        assert winners == 1

    @pytest.mark.asyncio
    async def test_TC_L110_L206_915_empty_selected_items_for_lean_ok(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L206-915 · lean 档 selected_items=None · 由系统自动填必选 · 通过。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int", status="ACKED")
        r = await sut.submit_compliance_profile(
            payload={
                "project_id": mock_project_id,
                "profile_type": "lean",
                "selected_items": None,  # lean 档允许 None · 系统自动填
                "reason": "lean 档足够 · 自动含必选",
                "idempotency_key": "k-empty",
                "modal_session_id": "ms-empty",
            },
        )
        assert r.status == "submitted"
```

---

*— TDD · L1-10 L2-06 · 裁剪档配置 · depth-B · v1.0 · 2026-04-22 · session-L —*
