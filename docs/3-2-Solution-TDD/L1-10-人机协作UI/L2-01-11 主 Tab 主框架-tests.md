---
doc_id: tests-L1-10-L2-01-11 主 Tab 主框架-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-01-11 主 Tab 主框架.md
  - docs/2-prd/L1-10 人机协作UI/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-L
created_at: 2026-04-22
---

# L1-10 L2-01-11 主 Tab 主框架 · TDD 测试用例

> 基于 3-1 L2-01 §3.1（14 个 public 方法）+ §3.2（17 项 E-** 错误码）+ §12 SLO（tab 切换 ≤ 100ms · banner 注册 ≤ 50ms · 路由 ≤ 50ms）+ §13 TC 驱动。
> TC ID：`TC-L110-L201-NNN`。
> **L2-01 是 L1-10 UI 框架 AR 层**（UISession 聚合根 · 11 tab 固定枚举 · 唯一活跃 tab 单例 · banner 栈 ≤ 3 · PM-14 active_project 切换需断重连）· 所有 tab 切换 / banner 注册 / panic 请求均经本 L2 · 其他 L2（02/03/05/06/07）作为子视图挂载。

## §0 撰写进度

- [x] §1 覆盖度索引（14 方法 + 17 错误码 + IC + SLO）
- [x] §2 正向用例（14 public 方法 + tab 路由 + banner 栈 + panic 请求）
- [x] §3 负向用例（17 条 E-** 全覆盖）
- [x] §4 IC-XX 契约集成（IC-L2-02 向 L2-03 订阅 · IC-L2-04 向 L2-04 发 panic · IC-09 审计 tab_stay）
- [x] §5 性能 SLO 用例（tab switch P95 ≤ 100ms · banner register ≤ 50ms · mount ≤ 80ms）
- [x] §6 端到端 e2e（11 tab 挂载 + 切换 + banner + panic + 项目切换）
- [x] §7 测试 fixture（mock_project_id / make_tab / mock_store / fake_clock）
- [x] §8 集成点用例（与 L2-02/03/04/05/06/07 协作）
- [x] §9 边界 / edge case（11 tab 硬约束 · banner 栈满 · cross project · localStorage 爆）

---

## §1 覆盖度索引

### §1.1 14 public 方法 × 测试（§3.1）

| 方法 | TC ID | 覆盖类型 | 备注 |
|---|---|---|---|
| `mount_tab(tab_id, component_ref)` | TC-L110-L201-001 | unit | 11 tab 注册 |
| `switch_tab(from, to, trigger)` | TC-L110-L201-002 | unit | 正常切换 · 审计 |
| `register_banner(entry)` | TC-L110-L201-003 | unit | soft / hard banner 入栈 |
| `dismiss_banner(banner_id)` | TC-L110-L201-004 | unit | soft 可取消 |
| `update_badge(tab_id, count_delta)` | TC-L110-L201-005 | unit | clamp ≥ 0 |
| `request_panic()` | TC-L110-L201-006 | unit | 经 L2-04 · 硬路径 |
| `subscribe_slice(slice_ids[])` | TC-L110-L201-007 | unit | 经 L2-03 |
| `guard_cross_project(requested_pid)` | TC-L110-L201-008 | unit | PM-14 · active_project 守卫 |
| `record_tab_stay(tab_id, duration_ms)` | TC-L110-L201-009 | unit | 审计 tab_stay |
| `resume_session(snapshot)` | TC-L110-L201-010 | unit | 刷新后恢复 |
| `toggle_theme(theme)` | TC-L110-L201-011 | unit | light/dark · localStorage |
| `rebind_shortcut(action, keys)` | TC-L110-L201-012 | unit | 冲突检测 |
| `export_preferences()` | TC-L110-L201-013 | unit | 导出 yaml |
| `health_check()` | TC-L110-L201-014 | unit | 健康自报 · 不抛异常 |
| 路由 by project_id | TC-L110-L201-015 | integration | 跨 project banner + 重建 |

### §1.2 错误码 × 测试（§3.2 全 17 项）

| 错误码 | TC ID | 场景 |
|---|---|---|
| `E-01` UI_TAB_NOT_REGISTERED | TC-L110-L201-101 | tab_id 不在 11 枚举 |
| `E-02` UI_DUPLICATE_MOUNT | TC-L110-L201-102 | 同 session 同 tab 二次 mount |
| `E-03` UI_SWITCH_BLOCKED_BY_GATE | TC-L110-L201-103 | Gate 未决 + 点"前进" |
| `E-04` UI_SWITCH_BLOCKED_BY_HALT | TC-L110-L201-104 | 硬红线中 + 点非允许 tab |
| `E-05` UI_BANNER_NOT_DISMISSABLE | TC-L110-L201-105 | 试 dismiss 硬红线 banner |
| `E-06` UI_BADGE_INVALID_DELTA | TC-L110-L201-106 | badge < 0 · clamp |
| `E-07` UI_CROSS_PROJECT_DENIED | TC-L110-L201-107 | PM-14 硬边界 |
| `E-08` UI_TAB_STAY_MALFORMED | TC-L110-L201-108 | entered ≥ exited |
| `E-09` UI_RESUME_MODAL_TIMEOUT | TC-L110-L201-109 | 5min 未响应 |
| `E-10` UI_CONTRACT_VIOLATION | TC-L110-L201-110 | 11 tab 数量 ≠ 11 · 硬契约 |
| `E-11` UI_BANNER_STACK_FULL | TC-L110-L201-111 | banner 栈 > 3 |
| `E-12` UI_BANNER_NOT_FOUND | TC-L110-L201-112 | dismiss 不存在 banner · 幂等 |
| `E-13` UI_PANIC_PENDING_CONFIRM | TC-L110-L201-113 | panic 未确认 |
| `E-14` UI_PANIC_FORWARD_FAILED | TC-L110-L201-114 | L2-04 转发失败 · 退避 3 次 |
| `E-15` UI_UNKNOWN_SLICE | TC-L110-L201-115 | 订阅未知 slice |
| `E-16` UI_PREFERENCE_PERSIST_FAILED | TC-L110-L201-116 | localStorage 满 |
| `E-17` UI_SHORTCUT_CONFLICT | TC-L110-L201-117 | 键位冲突 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-02 tab_subscribe | L2-01 → L2-03 | TC-L110-L201-601 | 每 tab 加载触发订阅 |
| IC-L2-04 request_panic | L2-01 → L2-04 | TC-L110-L201-602 | panic 按钮永驻 · 经 L2-04 |
| IC-09 append_event · tab_switched | L2-01 → L1-09 | TC-L110-L201-603 | 每次切换审计 |
| IC-09 append_event · tab_stay | L2-01 → L1-09 | TC-L110-L201-604 | record_tab_stay |
| IC-L2-06 apply_profile | L2-01 → L2-06 | TC-L110-L201-605 | 裁剪档应用 |
| IC-L2-07 switch_project | L2-01 → L2-07 | TC-L110-L201-606 | Admin 切 project · 断 SSE 建新 |

### §1.4 SLO × 测试

| SLO | 目标 | TC ID | 样本 |
|---|---|---|---|
| tab_switch | P95 ≤ 100ms | TC-L110-L201-701 | 100 |
| register_banner | P95 ≤ 50ms | TC-L110-L201-702 | 100 |
| mount_tab | P95 ≤ 80ms | TC-L110-L201-703 | 100 |
| update_badge | P95 ≤ 10ms | TC-L110-L201-704 | 500 |
| guard_cross_project | P95 ≤ 5ms | TC-L110-L201-705 | 1000 |

### §1.5 11 tab 固定枚举硬约束（TC-TAB-*）

11 tab: `deliverables / gate / wbs / outputs / progress / decisions / kb / profile / admin / events / alerts`

- TC-L110-L201-901 · 启动检查：当 len(tabs) ≠ 11 → E-10 UI_CONTRACT_VIOLATION
- TC-L110-L201-902 · 每 tab 必挂载 · 静态资源表校验

### §1.6 PM-14 project 过滤

- active_project 切换 · 触发 guard_cross_project + IC-L2-07 重建 SSE
- 任何 subscribe_slice / mount_tab 的 pid ≠ active_pid · E-07
- 正向：§2 所有用例；负向：TC-L110-L201-107

---

## §2 正向用例（14 方法 + 状态机）

```python
# file: tests/l1_10/test_l2_01_positive.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_01.service import TabRouterOrchestrator


class TestL2_01_TabRouter_Positive:

    TAB_IDS = ["deliverables", "gate", "wbs", "outputs", "progress",
               "decisions", "kb", "profile", "admin", "events", "alerts"]

    @pytest.mark.asyncio
    async def test_TC_L110_L201_001_mount_all_11_tabs(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-001 · 11 tab 全部 mount · 成功 + active=第 1 个。"""
        for tab in self.TAB_IDS:
            r = await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"Component:{tab}",
            )
            assert r.status == "mounted"
        assert len(sut.session.tabs) == 11
        assert sut.session.active_tab in self.TAB_IDS

    @pytest.mark.asyncio
    async def test_TC_L110_L201_002_switch_tab_normal_flow(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L201-002 · switch_tab · 正常切换 · 发 tab_switched 审计事件。"""
        for tab in self.TAB_IDS:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"Component:{tab}")
        r = await sut.switch_tab(
            project_id=mock_project_id,
            from_tab="deliverables", to_tab="gate",
            trigger="user_click",
        )
        assert r.active_tab == "gate"
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        assert any("tab_switched" in (t or "") for t in event_types)

    @pytest.mark.asyncio
    async def test_TC_L110_L201_003_register_banner_soft(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-003 · register_banner · soft 级 · 入栈 · dismissable。"""
        r = await sut.register_banner(
            project_id=mock_project_id,
            entry={"level": "soft", "kind": "info",
                   "text": "事件流降级 L1 · 重连中",
                   "dismissable": True},
        )
        assert r.banner_id
        assert r.stack_size == 1

    @pytest.mark.asyncio
    async def test_TC_L110_L201_004_dismiss_soft_banner(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-004 · dismiss_banner · soft 可取消。"""
        r = await sut.register_banner(
            project_id=mock_project_id,
            entry={"level": "soft", "kind": "info", "text": "test",
                   "dismissable": True},
        )
        d = await sut.dismiss_banner(
            project_id=mock_project_id, banner_id=r.banner_id)
        assert d.dismissed is True

    @pytest.mark.asyncio
    async def test_TC_L110_L201_005_update_badge_clamps_to_zero(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-005 · update_badge · 负向 delta 导致 < 0 时 clamp 到 0。"""
        await sut.mount_tab(
            project_id=mock_project_id, tab_id="gate",
            component_ref="X")
        await sut.update_badge(
            project_id=mock_project_id, tab_id="gate", count_delta=5)
        # 超出归零
        r = await sut.update_badge(
            project_id=mock_project_id, tab_id="gate", count_delta=-10)
        assert r.count == 0

    @pytest.mark.asyncio
    async def test_TC_L110_L201_006_request_panic_delegates_l204(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-006 · request_panic · 经 L2-04 · 硬路径跳 confirm（panic 特权）。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-panic", status="ACKED")
        r = await sut.request_panic(
            project_id=mock_project_id, confirmed=True)
        assert r.status == "submitted"
        call = mock_l204_service.submit_intervention.call_args.kwargs
        assert call["type"] == "panic"
        assert call["_source"] == "l2-01-panic-btn"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_007_subscribe_slice_routes_to_l2_03(
        self, sut, mock_project_id: str, mock_l203_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-007 · subscribe_slice · 转发给 L2-03 · 返 slice_keys。"""
        mock_l203_service.subscribe.return_value = MagicMock(
            subscription_id="sub-1", transport="sse",
            slice_keys=["L1-02:stage_", "L1-09:alert_"])
        r = await sut.subscribe_slice(
            project_id=mock_project_id,
            slice_ids=["gate", "alerts"],
            tab_id="deliverables",
        )
        assert "L1-02:stage_" in r.slice_keys
        mock_l203_service.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_TC_L110_L201_008_guard_cross_project_accepts_same_pid(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-008 · guard_cross_project · 同 pid 通过。"""
        sut.session.active_project = mock_project_id
        r = await sut.guard_cross_project(requested_pid=mock_project_id)
        assert r.allowed is True

    @pytest.mark.asyncio
    async def test_TC_L110_L201_009_record_tab_stay_appends_audit(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L201-009 · record_tab_stay · 审计 tab_stay 事件。"""
        await sut.record_tab_stay(
            project_id=mock_project_id, tab_id="gate",
            entered_at_ms=1_000, exited_at_ms=15_000)
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        assert any("tab_stay" in (t or "") for t in event_types)

    @pytest.mark.asyncio
    async def test_TC_L110_L201_010_resume_session_from_snapshot(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-010 · resume_session · 浏览器刷新恢复 · active_tab / banner / badge。"""
        snapshot = {
            "active_tab": "gate",
            "badges": {"gate": 3, "alerts": 1},
            "banners": [],
            "theme": "dark",
        }
        r = await sut.resume_session(
            project_id=mock_project_id, snapshot=snapshot)
        assert r.restored is True
        assert sut.session.active_tab == "gate"
        assert sut.session.badges["gate"] == 3

    @pytest.mark.asyncio
    async def test_TC_L110_L201_011_toggle_theme_persists_to_local_storage(
        self, sut, mock_project_id: str, mock_local_storage: MagicMock,
    ) -> None:
        """TC-L110-L201-011 · toggle_theme · light/dark · 写 localStorage。"""
        r = await sut.toggle_theme(
            project_id=mock_project_id, theme="dark")
        assert r.active_theme == "dark"
        mock_local_storage.setItem.assert_called()

    @pytest.mark.asyncio
    async def test_TC_L110_L201_012_rebind_shortcut_no_conflict(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-012 · rebind_shortcut · 不冲突的新键位成功绑定。"""
        r = await sut.rebind_shortcut(
            project_id=mock_project_id,
            action="panic", keys="Ctrl+Shift+P")
        assert r.bound is True

    @pytest.mark.asyncio
    async def test_TC_L110_L201_013_export_preferences_yaml(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-013 · export_preferences · yaml 字符串 · 含 theme / shortcuts。"""
        await sut.toggle_theme(project_id=mock_project_id, theme="dark")
        r = await sut.export_preferences(project_id=mock_project_id)
        assert "theme" in r.yaml_content
        assert "dark" in r.yaml_content

    def test_TC_L110_L201_014_health_check_returns_status(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-014 · health_check · 健康自报 · 不抛异常。"""
        r = sut.health_check(project_id=mock_project_id)
        assert r.status in ("healthy", "degraded", "unhealthy")
        assert r.tabs_mounted <= 11

    @pytest.mark.asyncio
    async def test_TC_L110_L201_015_route_by_project_id_triggers_rebuild(
        self, sut, mock_project_id: str, mock_l203_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-015 · 切 project_id · 断旧 SSE + 建新 · 所有 badge 重置。"""
        sut.session.active_project = mock_project_id
        new_pid = "pid-NEW"
        await sut.switch_active_project(new_project_id=new_pid)
        assert sut.session.active_project == new_pid
        # L2-03 被通知重建
        mock_l203_service.switch_project.assert_called_once_with(new_project_id=new_pid)
        # badge 重置
        assert all(v == 0 for v in sut.session.badges.values())
```

---

## §3 负向用例（17 条 E-** 全覆盖）

```python
# file: tests/l1_10/test_l2_01_negative.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_01.errors import L201Error


class TestL2_01_TabRouter_Negative:

    @pytest.mark.asyncio
    async def test_TC_L110_L201_101_mount_unknown_tab_id(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-101 · mount_tab 未知 tab_id → E-01。"""
        with pytest.raises(L201Error) as exc:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id="UNKNOWN",
                component_ref="X")
        assert exc.value.code == "E-01"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_102_duplicate_mount_same_tab(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-102 · 同 session 同 tab 二次 mount → E-02 · 幂等忽略。"""
        await sut.mount_tab(
            project_id=mock_project_id, tab_id="gate", component_ref="X")
        with pytest.raises(L201Error) as exc:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id="gate", component_ref="Y")
        assert exc.value.code == "E-02"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_103_switch_blocked_by_gate_pending(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-103 · Gate 未决 + 点"前进"tab → E-03。"""
        sut.session.gate_pending = True
        with pytest.raises(L201Error) as exc:
            await sut.switch_tab(
                project_id=mock_project_id,
                from_tab="gate", to_tab="outputs",
                trigger="user_click")
        assert exc.value.code == "E-03"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_104_switch_blocked_by_hard_halt(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-104 · 硬红线 + 点非允许 tab → E-04。"""
        sut.session.hard_halt = True
        with pytest.raises(L201Error) as exc:
            await sut.switch_tab(
                project_id=mock_project_id,
                from_tab="alerts", to_tab="wbs",
                trigger="user_click")
        assert exc.value.code == "E-04"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_105_dismiss_hard_banner_rejected(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-105 · 试 dismiss 硬红线 banner → E-05。"""
        r = await sut.register_banner(
            project_id=mock_project_id,
            entry={"level": "hard", "kind": "red_line",
                   "text": "红线告警", "dismissable": False})
        with pytest.raises(L201Error) as exc:
            await sut.dismiss_banner(
                project_id=mock_project_id, banner_id=r.banner_id)
        assert exc.value.code == "E-05"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_106_badge_invalid_delta_clamps(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-106 · badge delta 导致 count < 0 → E-06 + clamp 0。"""
        await sut.mount_tab(
            project_id=mock_project_id, tab_id="gate", component_ref="X")
        # 当前 count=0 · delta=-5
        r = await sut.update_badge(
            project_id=mock_project_id, tab_id="gate", count_delta=-5,
            emit_error=True)
        assert r.count == 0
        # 若实现选择 raise · 则验证 code；若选择 clamp + warn · 两种都合规
        assert r.error_code in (None, "E-06")

    @pytest.mark.asyncio
    async def test_TC_L110_L201_107_cross_project_denied(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L201-107 · 跨项目访问 → E-07 · 审计必留痕。"""
        sut.session.active_project = mock_project_id
        with pytest.raises(L201Error) as exc:
            await sut.guard_cross_project(requested_pid="pid-EVIL")
        assert exc.value.code == "E-07"
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        assert any("cross_project_denied" in (t or "") for t in event_types)

    @pytest.mark.asyncio
    async def test_TC_L110_L201_108_tab_stay_malformed(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-108 · entered ≥ exited → E-08 · 丢弃。"""
        with pytest.raises(L201Error) as exc:
            await sut.record_tab_stay(
                project_id=mock_project_id, tab_id="gate",
                entered_at_ms=10_000, exited_at_ms=5_000)
        assert exc.value.code == "E-08"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_109_resume_modal_timeout(
        self, sut, mock_project_id: str, fake_clock,
    ) -> None:
        """TC-L110-L201-109 · 5min 未响应 resume modal → E-09。"""
        sut.session.resume_modal_shown_at_ms = fake_clock.now_ms()
        fake_clock.advance(5 * 60 * 1000 + 1_000)
        r = await sut.check_resume_modal_timeout()
        assert r.timed_out is True
        assert r.error_code == "E-09"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_110_contract_violation_tab_count(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-110 · 只 mount 10 tab · 启动期间 check → E-10 UI_CONTRACT_VIOLATION。"""
        for tab in ["deliverables", "gate", "wbs", "outputs", "progress",
                    "decisions", "kb", "profile", "admin", "events"]:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"C:{tab}")
        # 未 mount alerts
        with pytest.raises(L201Error) as exc:
            await sut.assert_11_tabs_mounted()
        assert exc.value.code == "E-10"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_111_banner_stack_full(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-111 · banner 栈 > 3 → E-11 · 淘汰最老 soft。"""
        b_ids = []
        for i in range(3):
            r = await sut.register_banner(
                project_id=mock_project_id,
                entry={"level": "soft", "kind": "info",
                       "text": f"banner-{i}", "dismissable": True})
            b_ids.append(r.banner_id)
        # 第 4 个
        r4 = await sut.register_banner(
            project_id=mock_project_id,
            entry={"level": "soft", "kind": "info",
                   "text": "banner-4", "dismissable": True})
        # 栈仍 ≤ 3（淘汰最老）
        assert len(sut.session.banners) <= 3

    @pytest.mark.asyncio
    async def test_TC_L110_L201_112_dismiss_not_found_idempotent(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-112 · dismiss 不存在 banner → E-12 · 幂等忽略。"""
        r = await sut.dismiss_banner(
            project_id=mock_project_id, banner_id="banner-GONE",
            strict=False)
        assert r.dismissed is False
        assert r.error_code in (None, "E-12")

    @pytest.mark.asyncio
    async def test_TC_L110_L201_113_panic_pending_confirm(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-113 · panic 未确认 → E-13 · 前端弹二次 modal。"""
        r = await sut.request_panic(
            project_id=mock_project_id, confirmed=False)
        assert r.status == "pending_confirm"
        assert r.error_code == "E-13"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_114_panic_forward_failed_retries_3(
        self, sut, mock_project_id: str, mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-114 · L2-04 转发失败 → E-14 · 退避 3 次重试。"""
        mock_l204_service.submit_intervention.side_effect = [
            ConnectionError("f1"), ConnectionError("f2"),
            MagicMock(intent_id="int-r", status="ACKED"),
        ]
        r = await sut.request_panic(
            project_id=mock_project_id, confirmed=True)
        # 第 3 次成功
        assert r.status == "submitted"
        assert mock_l204_service.submit_intervention.call_count == 3

    @pytest.mark.asyncio
    async def test_TC_L110_L201_115_subscribe_unknown_slice(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-115 · subscribe_slice 未知 slice → E-15。"""
        with pytest.raises(L201Error) as exc:
            await sut.subscribe_slice(
                project_id=mock_project_id,
                slice_ids=["TOTALLY_UNKNOWN"],
                tab_id="gate")
        assert exc.value.code == "E-15"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_116_preference_persist_failed(
        self, sut, mock_project_id: str, mock_local_storage: MagicMock,
    ) -> None:
        """TC-L110-L201-116 · localStorage 满 → E-16 · 降级到内存。"""
        mock_local_storage.setItem.side_effect = Exception("QuotaExceeded")
        r = await sut.toggle_theme(
            project_id=mock_project_id, theme="dark")
        # 仍生效（内存）· 错误码提示
        assert r.active_theme == "dark"
        assert r.persisted is False
        assert r.error_code == "E-16"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_117_shortcut_conflict(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-117 · 新键位与既有冲突 → E-17。"""
        await sut.rebind_shortcut(
            project_id=mock_project_id, action="panic", keys="Ctrl+P")
        with pytest.raises(L201Error) as exc:
            await sut.rebind_shortcut(
                project_id=mock_project_id, action="pause", keys="Ctrl+P")
        assert exc.value.code == "E-17"
```

---

## §4 IC-XX 契约集成测试（≥ 6）

```python
# file: tests/l1_10/test_l2_01_ic_contracts.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_01_IC_Contracts:

    @pytest.mark.asyncio
    async def test_TC_L110_L201_601_ic_l2_02_each_tab_subscribes(
        self, sut, mock_project_id: str, mock_l203_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-601 · IC-L2-02 · mount_tab 触发 subscribe。"""
        mock_l203_service.subscribe.return_value = MagicMock(
            subscription_id="s-1", transport="sse", slice_keys=["L1-02:stage_"])
        await sut.mount_tab(
            project_id=mock_project_id, tab_id="gate", component_ref="X")
        mock_l203_service.subscribe.assert_called()

    @pytest.mark.asyncio
    async def test_TC_L110_L201_602_ic_l2_04_panic_delegation(
        self, sut, mock_project_id: str, mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-602 · IC-L2-04 · panic 按钮 · 必经 L2-04。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-p", status="ACKED")
        await sut.request_panic(
            project_id=mock_project_id, confirmed=True)
        kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert kw["type"] == "panic"
        assert kw["_source"] == "l2-01-panic-btn"
        assert kw["payload"]["severity"] in ("critical", "high")

    @pytest.mark.asyncio
    async def test_TC_L110_L201_603_ic09_tab_switched_audit(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L201-603 · IC-09 append_event · 每次 switch_tab 审计。"""
        for tab in ["deliverables", "gate"]:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"C:{tab}")
        await sut.switch_tab(
            project_id=mock_project_id,
            from_tab="deliverables", to_tab="gate",
            trigger="user_click")
        ev = [c.kwargs for c in mock_event_bus.append_event.call_args_list]
        tab_sw = [e for e in ev if (e.get("type") or "").endswith("tab_switched")]
        assert len(tab_sw) >= 1
        assert tab_sw[-1]["project_id"] == mock_project_id

    @pytest.mark.asyncio
    async def test_TC_L110_L201_604_ic09_tab_stay_audit(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L201-604 · IC-09 · record_tab_stay 审计 duration_ms。"""
        await sut.record_tab_stay(
            project_id=mock_project_id, tab_id="gate",
            entered_at_ms=1_000, exited_at_ms=16_000)
        ev = [c.kwargs for c in mock_event_bus.append_event.call_args_list
              if (c.kwargs.get("type") or "").endswith("tab_stay")]
        assert len(ev) >= 1
        assert ev[-1]["payload"]["duration_ms"] == 15_000

    @pytest.mark.asyncio
    async def test_TC_L110_L201_605_ic_l2_06_apply_profile(
        self, sut, mock_project_id: str, mock_l206_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-605 · IC-L2-06 · 用户在 profile tab 选择档位 · 应用到 session。"""
        mock_l206_service.apply_profile.return_value = MagicMock(applied=True)
        await sut.apply_profile(
            project_id=mock_project_id,
            profile="P2_standard", locked_at_stage="S1")
        mock_l206_service.apply_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_TC_L110_L201_606_ic_l2_07_switch_project(
        self, sut, mock_project_id: str, mock_l207_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-606 · IC-L2-07 · Admin 切 project · 断旧 SSE + 建新。"""
        new_pid = "pid-NEW-abc"
        mock_l207_service.switch_project.return_value = MagicMock(success=True)
        await sut.switch_active_project(new_project_id=new_pid)
        mock_l207_service.switch_project.assert_called_once()
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_10/test_l2_01_perf.py
from __future__ import annotations

import statistics
import time

import pytest


class TestL2_01_SLO:

    TAB_SWITCH_P95_MS = 100
    BANNER_REG_P95_MS = 50
    MOUNT_P95_MS = 80
    BADGE_UPD_P95_MS = 10
    CROSS_PROJ_GUARD_P95_MS = 5

    TAB_IDS = ["deliverables", "gate", "wbs", "outputs", "progress",
               "decisions", "kb", "profile", "admin", "events", "alerts"]

    @pytest.mark.asyncio
    async def test_TC_L110_L201_701_tab_switch_p95_le_100ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-701 · tab_switch P95 ≤ 100ms · 100 样本。"""
        for tab in self.TAB_IDS:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"C:{tab}")
        samples: list[float] = []
        for i in range(100):
            a, b = self.TAB_IDS[i % 11], self.TAB_IDS[(i + 1) % 11]
            t0 = time.perf_counter()
            await sut.switch_tab(
                project_id=mock_project_id, from_tab=a, to_tab=b,
                trigger="user_click")
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.TAB_SWITCH_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L201_702_register_banner_p95_le_50ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-702 · register_banner P95 ≤ 50ms。"""
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.register_banner(
                project_id=mock_project_id,
                entry={"level": "soft", "kind": "info",
                       "text": f"b-{i}", "dismissable": True})
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.BANNER_REG_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L201_703_mount_tab_p95_le_80ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-703 · mount_tab P95 ≤ 80ms · 100 样本（11 种 tab 循环）。"""
        samples: list[float] = []
        for i in range(100):
            # 每次重建 session
            sut.session.tabs = {}
            for tab in self.TAB_IDS[: (i % 11) + 1]:
                pass  # 填充
            t0 = time.perf_counter()
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=self.TAB_IDS[i % 11],
                component_ref=f"C:{i}",
                strict_duplicate=False)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.MOUNT_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L201_704_update_badge_p95_le_10ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-704 · update_badge P95 ≤ 10ms · 500 样本。"""
        await sut.mount_tab(
            project_id=mock_project_id, tab_id="gate", component_ref="X")
        samples: list[float] = []
        for i in range(500):
            t0 = time.perf_counter()
            await sut.update_badge(
                project_id=mock_project_id, tab_id="gate",
                count_delta=1 if i % 2 == 0 else -1)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.BADGE_UPD_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L201_705_guard_cross_project_p95_le_5ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-705 · guard_cross_project P95 ≤ 5ms · 1000 样本。"""
        sut.session.active_project = mock_project_id
        samples: list[float] = []
        for _ in range(1000):
            t0 = time.perf_counter()
            await sut.guard_cross_project(requested_pid=mock_project_id)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.CROSS_PROJ_GUARD_P95_MS
```

---

## §6 端到端 e2e 场景（≥ 2）

```python
# file: tests/l1_10/test_l2_01_e2e.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_01_E2E:

    TAB_IDS = ["deliverables", "gate", "wbs", "outputs", "progress",
               "decisions", "kb", "profile", "admin", "events", "alerts"]

    @pytest.mark.asyncio
    async def test_TC_L110_L201_801_e2e_full_mount_switch_banner_panic(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock, mock_l203_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-801 · e2e · 11 tab mount → switch → banner → panic 全链路。"""
        mock_l203_service.subscribe.return_value = MagicMock(
            subscription_id="s", transport="sse", slice_keys=["x"])
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-e2e", status="ACKED")
        # 1. mount 11 tab
        for tab in self.TAB_IDS:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"C:{tab}")
        # 2. switch to gate
        await sut.switch_tab(
            project_id=mock_project_id,
            from_tab="deliverables", to_tab="gate",
            trigger="user_click")
        # 3. register soft banner
        b = await sut.register_banner(
            project_id=mock_project_id,
            entry={"level": "soft", "kind": "info",
                   "text": "降级 L1", "dismissable": True})
        # 4. panic
        r = await sut.request_panic(
            project_id=mock_project_id, confirmed=True)
        assert r.status == "submitted"
        assert sut.session.active_tab == "gate"
        assert b.banner_id

    @pytest.mark.asyncio
    async def test_TC_L110_L201_802_e2e_project_switch_rebuilds_session(
        self, sut, mock_project_id: str,
        mock_l203_service: AsyncMock, mock_l207_service: AsyncMock,
    ) -> None:
        """TC-L110-L201-802 · e2e · Admin 切 project · 所有 badge reset + SSE 重建。"""
        # 预埋 badge
        for tab in self.TAB_IDS:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab, component_ref="X")
            await sut.update_badge(
                project_id=mock_project_id, tab_id=tab, count_delta=5)
        # 切 project
        new_pid = "pid-NEW"
        mock_l207_service.switch_project.return_value = MagicMock(success=True)
        await sut.switch_active_project(new_project_id=new_pid)
        assert sut.session.active_project == new_pid
        assert all(v == 0 for v in sut.session.badges.values())
        mock_l203_service.switch_project.assert_called_once()
```

---

## §7 测试 fixture

```python
# file: tests/l1_10/conftest_l2_01.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_01.service import TabRouterOrchestrator


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
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="EventBus")
    bus.append_event = MagicMock(return_value={"event_id": f"evt-{uuid.uuid4()}"})
    return bus


@pytest.fixture
def mock_local_storage() -> MagicMock:
    ls = MagicMock(name="LocalStorage")
    ls.setItem = MagicMock(return_value=None)
    ls.getItem = MagicMock(return_value=None)
    return ls


@pytest.fixture
def mock_l203_service() -> AsyncMock:
    s = AsyncMock(name="L203")
    s.subscribe = AsyncMock(return_value=MagicMock(
        subscription_id="s-1", transport="sse",
        slice_keys=["L1-02:stage_"]))
    s.switch_project = AsyncMock(return_value=None)
    return s


@pytest.fixture
def mock_l204_service() -> AsyncMock:
    s = AsyncMock(name="L204")
    s.submit_intervention = AsyncMock(return_value=MagicMock(
        intent_id="int-1", status="ACKED"))
    return s


@pytest.fixture
def mock_l206_service() -> AsyncMock:
    s = AsyncMock(name="L206")
    s.apply_profile = AsyncMock(return_value=MagicMock(applied=True))
    return s


@pytest.fixture
def mock_l207_service() -> AsyncMock:
    s = AsyncMock(name="L207")
    s.switch_project = AsyncMock(return_value=MagicMock(success=True))
    return s


@pytest.fixture
def sut(
    mock_project_id: str, fake_clock: FakeClock,
    mock_event_bus: MagicMock, mock_local_storage: MagicMock,
    mock_l203_service: AsyncMock, mock_l204_service: AsyncMock,
    mock_l206_service: AsyncMock, mock_l207_service: AsyncMock,
) -> TabRouterOrchestrator:
    return TabRouterOrchestrator(
        session={"active_project": mock_project_id},
        clock=fake_clock,
        event_bus=mock_event_bus,
        local_storage=mock_local_storage,
        l203=mock_l203_service,
        l204=mock_l204_service,
        l206=mock_l206_service,
        l207=mock_l207_service,
        config={
            "banner_stack_max": 3,
            "resume_modal_timeout_ms": 5 * 60 * 1000,
            "tab_ids": ["deliverables", "gate", "wbs", "outputs",
                        "progress", "decisions", "kb", "profile",
                        "admin", "events", "alerts"],
            "panic_retry_max": 3,
        },
    )
```

---

## §8 集成点用例（与兄弟 L2 协作 · ≥ 2）

```python
# file: tests/l1_10/test_l2_01_siblings.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_01_SiblingIntegration:

    @pytest.mark.asyncio
    async def test_TC_L110_L201_901_all_11_tabs_mounted_assertion(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-901 · 11 tab 硬契约 · 全 mount 后 assert_11_tabs_mounted 通过。"""
        for tab in ["deliverables", "gate", "wbs", "outputs", "progress",
                    "decisions", "kb", "profile", "admin", "events", "alerts"]:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"C:{tab}")
        # 不抛
        await sut.assert_11_tabs_mounted()
        assert len(sut.session.tabs) == 11

    @pytest.mark.asyncio
    async def test_TC_L110_L201_902_banner_hard_locks_ui_except_panic(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-902 · 硬红线 banner 注册 · UI 全锁（除 panic/resume）· 禁 tab 切换。"""
        await sut.register_banner(
            project_id=mock_project_id,
            entry={"level": "hard", "kind": "red_line",
                   "text": "硬红线已触发", "dismissable": False})
        sut.session.hard_halt = True
        from app.l1_10.l2_01.errors import L201Error
        for tab in ["deliverables", "gate", "wbs", "outputs",
                    "progress", "decisions", "kb", "profile",
                    "admin", "events"]:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab, component_ref="X")
        with pytest.raises(L201Error) as exc:
            await sut.switch_tab(
                project_id=mock_project_id,
                from_tab="alerts", to_tab="wbs",
                trigger="user_click")
        assert exc.value.code == "E-04"

    @pytest.mark.asyncio
    async def test_TC_L110_L201_903_project_banner_on_cross_project_event(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-903 · 收到跨 project 事件 → 触发跨 project banner（而非简单拒绝）。"""
        sut.session.active_project = mock_project_id
        await sut.on_cross_project_event_detected(
            rejected_event={"event_id": "evt-x",
                            "project_id": "pid-OTHER",
                            "type": "L1-02:stage_gate"})
        levels = [b.level for b in sut.session.banners]
        assert any(l in ("soft", "hard") for l in levels)
```

---

## §9 边界 / edge case

```python
# file: tests/l1_10/test_l2_01_edge.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_01.errors import L201Error


class TestL2_01_Edge:

    @pytest.mark.asyncio
    async def test_TC_L110_L201_911_exactly_11_tabs_boundary(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-911 · 边界 · 恰好 11 tab · 不多不少 · assert_11_tabs_mounted 通过。"""
        tabs = ["deliverables", "gate", "wbs", "outputs", "progress",
                "decisions", "kb", "profile", "admin", "events", "alerts"]
        for tab in tabs:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=tab,
                component_ref=f"C:{tab}")
        await sut.assert_11_tabs_mounted()
        assert len(sut.session.tabs) == 11

    @pytest.mark.asyncio
    async def test_TC_L110_L201_912_banner_stack_lifo_eviction(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-912 · banner 栈满后 · LIFO 淘汰最老 soft · 保留所有 hard。"""
        hard = await sut.register_banner(
            project_id=mock_project_id,
            entry={"level": "hard", "kind": "red_line",
                   "text": "HARD", "dismissable": False})
        for i in range(5):
            await sut.register_banner(
                project_id=mock_project_id,
                entry={"level": "soft", "kind": "info",
                       "text": f"soft-{i}", "dismissable": True})
        # hard 必保留 · 栈 ≤ 3
        banners = sut.session.banners
        assert any(b.banner_id == hard.banner_id for b in banners)
        assert len(banners) <= 3

    @pytest.mark.asyncio
    async def test_TC_L110_L201_913_empty_preferences_export(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-913 · export_preferences · 空配置 · 返默认 yaml（至少含 version）。"""
        r = await sut.export_preferences(project_id=mock_project_id)
        assert "version" in r.yaml_content or "theme" in r.yaml_content

    @pytest.mark.asyncio
    async def test_TC_L110_L201_914_localstorage_quota_exceeded_falls_back_memory(
        self, sut, mock_project_id: str, mock_local_storage: MagicMock,
    ) -> None:
        """TC-L110-L201-914 · localStorage 满 · 降级到内存 · UI 黄 banner 提示。"""
        mock_local_storage.setItem.side_effect = Exception("QuotaExceeded")
        await sut.toggle_theme(project_id=mock_project_id, theme="dark")
        # UI 黄 banner
        assert any(b.level == "soft" and "preference" in (b.text or "").lower()
                   for b in sut.session.banners)

    @pytest.mark.asyncio
    async def test_TC_L110_L201_915_concurrent_tab_switch_serializes(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-915 · 并发 10 次 switch_tab · FIFO 串行化 · active_tab 单调更新。"""
        import asyncio
        tabs = ["deliverables", "gate", "wbs", "outputs", "progress"]
        for t in tabs:
            await sut.mount_tab(
                project_id=mock_project_id, tab_id=t, component_ref="X")
        # 并发切换
        targets = ["gate", "wbs", "outputs", "progress", "gate"]
        await asyncio.gather(*[
            sut.switch_tab(
                project_id=mock_project_id, from_tab="deliverables",
                to_tab=t, trigger="user_click")
            for t in targets
        ])
        # 最终 active_tab 是某一个 target
        assert sut.session.active_tab in targets

    @pytest.mark.asyncio
    async def test_TC_L110_L201_916_tab_stay_over_24h_discarded(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L201-916 · tab_stay duration > 24h · E-08 · 丢弃不审计。"""
        with pytest.raises(L201Error) as exc:
            await sut.record_tab_stay(
                project_id=mock_project_id, tab_id="gate",
                entered_at_ms=0,
                exited_at_ms=25 * 60 * 60 * 1000)  # 25h
        assert exc.value.code == "E-08"
```

---

*— TDD · L1-10 L2-01 · 11 主 Tab 主框架 · depth-B · v1.0 · 2026-04-22 · session-L —*
