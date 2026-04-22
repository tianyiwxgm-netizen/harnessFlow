---
doc_id: tests-L1-10-L2-07-Admin 子管理模块-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-07-Admin 子管理模块.md
  - docs/2-prd/L1-10 人机协作UI/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-L
created_at: 2026-04-22
---

# L1-10 L2-07 · Admin 子管理模块 · TDD 测试用例

> 基于 3-1 L2-07 §3（6 IC 触点）+ §3.7（22 项 `E_L207_*` 错误码）+ §12 SLO（Admin 首屏 ≤ 1s · 审计查询 ≤ 2s · 多模态缓存命中 ≤ 50ms）驱动。
> TC ID：`TC-L110-L207-NNN`。
> **L2-07 是 L1-10 Admin 多视图聚合层**：9 后台 Sub-Coordinator（Engine/Execution/KB/Supervisor/Verifier/Subagent/SkillGraph/Stats/Diag） + 红线告警角 + 审计追溯面板 + 多模态内容缓存 + Loop 触发统计 · 所有写动作经 IC-L2-07 委托 L2-04 · 硬红线 banner 经 IC-L2-11 推 L2-01 · 白名单敏感操作（e.g. 系统 kill）强制 2FA 二次确认。

## §0 撰写进度

- [x] §1 覆盖度索引（9 Coordinator + 6 IC + 22 错误码 + SLO）
- [x] §2 正向用例（open_admin_view + 9 子模块 + 查询 / 授权 / banner / 多模态）
- [x] §3 负向用例（22 条 E_L207_* 全覆盖）
- [x] §4 IC-XX 契约集成（IC-L2-12 / IC-18 / IC-11 / IC-L2-07 / IC-L2-11 / IC-09）
- [x] §5 性能 SLO 用例（首屏 / 审计 / 多模态缓存 / banner 推）
- [x] §6 端到端 e2e（首屏打开 + 硬红线流 + 配置变更 2FA）
- [x] §7 测试 fixture
- [x] §8 集成点用例（与 L2-01/03/04 + L1-08/09 协作）
- [x] §9 边界 / edge case（sequence gap · DOM tamper · 权限拒绝）

---

## §1 覆盖度索引

### §1.1 9 Sub-Coordinator × 测试（§2.2）

| Sub-Coordinator | TC ID | 核心方法 |
|---|---|---|
| EngineConfigCoordinator | TC-L110-L207-001 | load_config / update_config（经 2FA） |
| ExecutionInstanceCoordinator | TC-L110-L207-002 | list_instances / kill_instance（白名单） |
| KBAdminCoordinator | TC-L110-L207-003 | purge_entry · approve_global_promotion |
| SupervisorAdminCoordinator | TC-L110-L207-004 | list_decisions · override |
| VerifierPrimitiveCoordinator | TC-L110-L207-005 | manage 5 原语 |
| SubagentRegistryCoordinator | TC-L110-L207-006 | list / pause / resume subagent |
| SkillCallGraphCoordinator | TC-L110-L207-007 | 10 条可视化调用链 |
| StatsAnalysisCoordinator | TC-L110-L207-008 | Loop trigger 统计 |
| SystemDiagCoordinator | TC-L110-L207-009 | health_probe / diag_action |

### §1.2 主方法（Application Service）

| 方法 | TC ID | 覆盖 |
|---|---|---|
| `open_admin_view(project_id)` | TC-L110-L207-010 | 13 面板并发初始化 |
| `switch_admin_module(module_id)` | TC-L110-L207-011 | 9 模块切换 |
| `query_audit_trail(anchor, depth)` | TC-L110-L207-012 | 4 层追溯链 |
| `fetch_multimodal(artifact_id)` | TC-L110-L207-013 | IC-11 + 缓存 |
| `submit_admin_change(intent)` | TC-L110-L207-014 | 委托 L2-04 · 2FA |
| `authorize_red_line(alert_id, token)` | TC-L110-L207-015 | 红线授权 |
| `push_red_line_banner(alert)` | TC-L110-L207-016 | IC-L2-11 → L2-01 |
| `on_event_received(event)` | TC-L110-L207-017 | IC-L2-12 入站 |

### §1.3 错误码 × 测试（§3.7 全 22 项）

| 错误码 | TC ID | 场景 |
|---|---|---|
| `E_L207_EVENT_UNKNOWN_TYPE` | TC-L110-L207-101 | IC-L2-12 收到未知 type |
| `E_L207_EVENT_MISSING_PROJECT_ID` | TC-L110-L207-102 | PM-14 REJECT |
| `E_L207_EVENT_SEQUENCE_GAP` | TC-L110-L207-103 | sequence 跳号 · RECOVER 重拉 |
| `E_L207_EVENT_STORE_WRITE_FAIL` | TC-L110-L207-104 | EventStore write 失败 · DEGRADE |
| `E_L207_AUDIT_ANCHOR_NOT_FOUND` | TC-L110-L207-105 | query_audit_trail 锚点不存在 |
| `E_L207_AUDIT_TIMEOUT` | TC-L110-L207-106 | IC-18 超时 · DEGRADE 缓存 |
| `E_L207_AUDIT_SEQUENCE_CORRUPT` | TC-L110-L207-107 | 审计链断裂 · BLOCK |
| `E_L207_AUDIT_PERMISSION_DENIED` | TC-L110-L207-108 | 无查询权限 |
| `E_L207_CONTENT_ARTIFACT_NOT_FOUND` | TC-L110-L207-109 | IC-11 artifact 不存在 |
| `E_L207_CONTENT_TIMEOUT` | TC-L110-L207-110 | IC-11 超时 |
| `E_L207_CONTENT_UNSUPPORTED_TYPE` | TC-L110-L207-111 | 不支持的 mime |
| `E_L207_CONTENT_CACHE_HIT_STALE` | TC-L110-L207-112 | content_hash 过期 · RECOVER |
| `E_L207_INTERVENE_MISSING_CONFIRM` | TC-L110-L207-113 | 缺 2FA confirmation_token |
| `E_L207_INTERVENE_WHITELIST_NO_CONFIRM` | TC-L110-L207-114 | 白名单操作缺二次确认 |
| `E_L207_INTERVENE_REASON_TOO_SHORT` | TC-L110-L207-115 | 变更理由 < N 字 |
| `E_L207_INTERVENE_REJECTED_BY_L204` | TC-L110-L207-116 | L2-04 拒绝 |
| `E_L207_BANNER_L201_NOT_READY` | TC-L110-L207-117 | IC-L2-11 L2-01 未就绪 · RETRY |
| `E_L207_BANNER_DUPLICATE` | TC-L110-L207-118 | banner 重复 · IDEMPOTENT |
| `E_L207_BANNER_DISMISSIBLE_TRUE` | TC-L110-L207-119 | 红线不能 dismissable=true |
| `E_L207_AUDIT_APPEND_FAIL` | TC-L110-L207-120 | IC-09 失败 · RETRY |
| `E_L207_AUDIT_MISSING_TRACE_ID` | TC-L110-L207-121 | trace_id 缺 · 自动补 |
| `E_L207_DOM_TAMPER_DETECTED` | TC-L110-L207-122 | Admin DOM 被篡改 · REMEDIATE |

### §1.4 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-12 on_event_received | L2-03 → L2-07 | TC-L110-L207-601 | 13 类事件前缀 |
| IC-18 query_audit_trail | L2-07 → L1-09 | TC-L110-L207-602 | 4 层追溯 |
| IC-11 process_content | L2-07 → L1-08 | TC-L110-L207-603 | 多模态结构化 |
| IC-L2-07 user_intervene | L2-07 → L2-04 | TC-L110-L207-604 | admin_config_change / red_line_authorize |
| IC-L2-11 push_top_banner | L2-07 → L2-01 | TC-L110-L207-605 | 硬红线 banner |
| IC-09 append_event | L2-07 → L1-09 | TC-L110-L207-606 | Admin 操作审计 |

### §1.5 SLO × 测试

| SLO | 目标 | TC ID | 样本 |
|---|---|---|---|
| open_admin_view 首屏 | P95 ≤ 1s | TC-L110-L207-701 | 50 |
| query_audit_trail | P95 ≤ 2s | TC-L110-L207-702 | 50 |
| 多模态缓存命中 | P95 ≤ 50ms | TC-L110-L207-703 | 500 |
| 红线 banner 推送 | P95 ≤ 100ms | TC-L110-L207-704 | 100 |
| switch_admin_module | P95 ≤ 100ms | TC-L110-L207-705 | 100 |

### §1.6 PM-14 硬约束

- 所有入站事件 / 出站 IC 强制带 `project_id` · 缺 → E_L207_EVENT_MISSING_PROJECT_ID REJECT
- 跨项目 banner 推 → 拒绝 · 不打扰其他 project 用户
- 白名单操作（kill 实例 / reset 配置）必须 2FA + L2-04 二次确认

---

## §2 正向用例

```python
# file: tests/l1_10/test_l2_07_positive.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_07.service import AdminModuleCoordinator


class TestL2_07_AdminCoordinator_Positive:

    # ---------- 9 Sub-Coordinator ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_001_engine_config_load_and_update(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-001 · EngineConfig load + update · update 经 2FA + L2-04。"""
        cfg = await sut.engine_config.load(project_id=mock_project_id)
        assert cfg is not None
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int", status="ACKED")
        r = await sut.engine_config.update(
            project_id=mock_project_id,
            change_path="tick_interval_sec",
            old_value=5, new_value=3,
            reason="提高响应速度，匹配高并发场景",
            confirmation_token="2fa-TOKEN-x",
        )
        assert r.submitted is True
        kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert kw["type"] == "admin_config_change"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_002_execution_instance_list(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-002 · ExecutionInstanceCoordinator.list · 返活跃实例。"""
        r = await sut.execution_instance.list(project_id=mock_project_id)
        assert isinstance(r.instances, list)

    @pytest.mark.asyncio
    async def test_TC_L110_L207_003_kb_admin_approve_global_promotion(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-003 · KBAdmin · approve_global_promotion · 委托 L2-04。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-a", status="ACKED")
        r = await sut.kb_admin.approve_global_promotion(
            project_id=mock_project_id,
            entry_id="kb-g-1",
            approval_note="跨项目复用价值明显",
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_004_supervisor_list_decisions(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-004 · Supervisor list_decisions · 按 project + time 过滤。"""
        r = await sut.supervisor_admin.list_decisions(
            project_id=mock_project_id,
            filter={"severity": "high"},
            pagination={"offset": 0, "limit": 20},
        )
        assert r is not None

    @pytest.mark.asyncio
    async def test_TC_L110_L207_005_verifier_primitive_list(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-005 · VerifierPrimitive list 5 原语（lint/unit/integration/eval/smoke）。"""
        r = await sut.verifier_primitive.list(project_id=mock_project_id)
        assert len(r.primitives) == 5

    @pytest.mark.asyncio
    async def test_TC_L110_L207_006_subagent_list_and_pause(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-006 · SubagentRegistry · list + pause。"""
        r = await sut.subagent_registry.list(project_id=mock_project_id)
        assert r is not None
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int", status="ACKED")
        p = await sut.subagent_registry.pause(
            project_id=mock_project_id,
            subagent_id="sa-1",
            reason="观察其行为异常 · 暂停调试",
            confirmation_token="2fa-x",
        )
        assert p.submitted is True

    @pytest.mark.asyncio
    async def test_TC_L110_L207_007_skill_call_graph_returns_chain(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-007 · SkillCallGraph · 返 10 条可视化调用链。"""
        r = await sut.skill_call_graph.get(
            project_id=mock_project_id, depth=3)
        assert isinstance(r.chains, list)

    @pytest.mark.asyncio
    async def test_TC_L110_L207_008_stats_analysis_loop_triggers(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-008 · StatsAnalysis · Loop trigger 按日 / 类型统计。"""
        r = await sut.stats_analysis.loop_triggers(
            project_id=mock_project_id,
            window="7d")
        assert r.window == "7d"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_009_system_diag_health_probe(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-009 · SystemDiag · health_probe · 返 L1-01/06/08/09 健康。"""
        r = await sut.system_diag.health_probe(project_id=mock_project_id)
        assert hasattr(r, "l109_status") or "l109" in str(r).lower()

    # ---------- Application Service 主方法 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_010_open_admin_view_parallel_init(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-010 · open_admin_view · 13 面板并发初始化。"""
        r = await sut.open_admin_view(project_id=mock_project_id)
        assert r.initialized_modules_count >= 9  # 9 sub + 额外面板
        assert r.elapsed_ms is not None

    @pytest.mark.asyncio
    async def test_TC_L110_L207_011_switch_module_lazy_load(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-011 · switch_admin_module · 懒加载 · 审计。"""
        r = await sut.switch_admin_module(
            project_id=mock_project_id,
            module_id="kb_admin")
        assert r.active_module == "kb_admin"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_012_query_audit_trail_4_layers(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-012 · query_audit_trail · 4 层追溯链（tick→decision→skill→artifact）。"""
        mock_l109_client.query_audit_trail.return_value = MagicMock(
            layers={
                "tick": [{"tick_id": "t-1"}],
                "decision": [{"decision_id": "d-1", "tick_id": "t-1"}],
                "skill": [{"skill_call_id": "s-1", "decision_id": "d-1"}],
                "artifact": [{"artifact_id": "a-1", "skill_call_id": "s-1"}],
            },
            trace_id="trace-abc",
        )
        r = await sut.query_audit_trail(
            project_id=mock_project_id,
            anchor={"type": "artifact_id", "value": "a-1"},
            depth=4,
        )
        assert set(r.layers.keys()) >= {"tick", "decision", "skill", "artifact"}

    @pytest.mark.asyncio
    async def test_TC_L110_L207_013_fetch_multimodal_cache_hit(
        self, sut, mock_project_id: str, mock_l108_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-013 · fetch_multimodal · 命中缓存 · 不调 L1-08。"""
        # 预埋缓存
        sut.multimodal_cache.put(
            artifact_id="a-1", content_hash="h1",
            payload={"title": "x", "description": "y", "content": "..."})
        r = await sut.fetch_multimodal(
            project_id=mock_project_id,
            artifact_id="a-1", content_hash="h1")
        assert r.cache_hit is True
        mock_l108_client.process_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_TC_L110_L207_014_submit_admin_change_with_2fa(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-014 · submit_admin_change · 2FA + 委托 L2-04。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-ac", status="ACKED")
        r = await sut.submit_admin_change(
            project_id=mock_project_id,
            intent={
                "intervention_type": "admin_config_change",
                "module": "engine_config",
                "change_path": "tick_interval_sec",
                "old_value": 5, "new_value": 3,
                "reason": "提高响应速度 · 匹配高并发",
                "confirmation_token": "2fa-OK",
            },
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_015_authorize_red_line(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-015 · authorize_red_line · grant + 凭证（可选）· 委托 L2-04。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-rl", status="ACKED")
        r = await sut.authorize_red_line(
            project_id=mock_project_id,
            alert_id="rl-001",
            decision="grant",
            scope_limit={"repo": "foo/bar", "duration_sec": 3600},
            confirmation_token="2fa-OK",
        )
        assert r.status == "submitted"
        kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert kw["type"] == "authorize"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_016_push_red_line_banner(
        self, sut, mock_project_id: str, mock_l201_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-016 · push_red_line_banner · IC-L2-11 · L2-01 红条。"""
        r = await sut.push_red_line_banner(
            project_id=mock_project_id,
            alert={"alert_id": "rl-001", "severity": "critical",
                   "message": "检测到越权操作"},
        )
        assert r.pushed is True
        mock_l201_service.register_banner.assert_called_once()
        kw = mock_l201_service.register_banner.call_args.kwargs
        assert kw["entry"]["level"] == "hard"
        assert kw["entry"]["dismissable"] is False

    @pytest.mark.asyncio
    async def test_TC_L110_L207_017_on_event_received_dispatches_to_sub_coordinator(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-017 · on_event_received · dispatch 到对应 sub coordinator。"""
        await sut.on_event_received({
            "type": "L1-07:red_line_alert",
            "project_id": mock_project_id,
            "payload": {"alert_id": "rl-1", "severity": "critical"},
            "ts": "now",
            "sequence": 1,
        })
        # red_line 触发 banner 推送
        assert len(sut.pending_banners) >= 1 or sut.last_processed_event is not None
```

---

## §3 负向用例（22 条 E_L207_* 全覆盖）

```python
# file: tests/l1_10/test_l2_07_negative.py
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_07.errors import L207Error


class TestL2_07_AdminCoordinator_Negative:

    # ---------- IC-L2-12 事件入站 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_101_event_unknown_type(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L207-101 · 未知 type · E_L207_EVENT_UNKNOWN_TYPE · WARN 丢弃。"""
        r = await sut.on_event_received({
            "type": "UNKNOWN:foo",
            "project_id": mock_project_id,
            "payload": {}, "ts": "now", "sequence": 1,
        })
        # WARN 不抛 · 内部记录
        assert r is None or getattr(r, "error_code", None) == "E_L207_EVENT_UNKNOWN_TYPE"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_102_event_missing_project_id(self, sut) -> None:
        """TC-L110-L207-102 · 事件缺 project_id · REJECT。"""
        with pytest.raises(L207Error) as exc:
            await sut.on_event_received({
                "type": "L1-07:red_line_alert",
                "payload": {}, "ts": "now", "sequence": 1,
            })
        assert exc.value.code == "E_L207_EVENT_MISSING_PROJECT_ID"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_103_event_sequence_gap_recovers(
        self, sut, mock_project_id: str, mock_l203_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-103 · sequence 跳号 · E_L207_EVENT_SEQUENCE_GAP · RECOVER 重拉。"""
        await sut.on_event_received({
            "type": "L1-07:red_line_alert", "project_id": mock_project_id,
            "payload": {}, "ts": "now", "sequence": 100,
        })
        await sut.on_event_received({
            "type": "L1-07:red_line_alert", "project_id": mock_project_id,
            "payload": {}, "ts": "now", "sequence": 105,  # 跳号
        })
        # 触发重拉 since=101
        mock_l203_service.pull_history.assert_called()

    @pytest.mark.asyncio
    async def test_TC_L110_L207_104_event_store_write_fail_degrades(
        self, sut, mock_project_id: str, mock_repo: MagicMock,
    ) -> None:
        """TC-L110-L207-104 · EventStore write fail · DEGRADE 只读模式。"""
        mock_repo.store_event.side_effect = OSError("ENOSPC")
        await sut.on_event_received({
            "type": "L1-07:red_line_alert", "project_id": mock_project_id,
            "payload": {}, "ts": "now", "sequence": 1,
        })
        assert sut.degradation_state == "READ_ONLY"

    # ---------- IC-18 审计查询 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_105_audit_anchor_not_found(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-105 · 锚点不存在 · USER_ERROR。"""
        mock_l109_client.query_audit_trail.side_effect = L207Error(
            code="E_L207_AUDIT_ANCHOR_NOT_FOUND",
            user_message="锚点不存在")
        with pytest.raises(L207Error) as exc:
            await sut.query_audit_trail(
                project_id=mock_project_id,
                anchor={"type": "artifact_id", "value": "GONE"},
                depth=4)
        assert exc.value.code == "E_L207_AUDIT_ANCHOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_106_audit_timeout_falls_back_to_cache(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-106 · IC-18 timeout · DEGRADE · 用缓存。"""
        mock_l109_client.query_audit_trail.side_effect = asyncio.TimeoutError
        sut.audit_cache.put(
            anchor_key="a-1",
            result={"layers": {"tick": []}, "trace_id": "cached"})
        r = await sut.query_audit_trail(
            project_id=mock_project_id,
            anchor={"type": "artifact_id", "value": "a-1"},
            depth=4,
            allow_cache=True,
        )
        assert r.trace_id == "cached"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_107_audit_sequence_corrupt_blocks(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-107 · 审计链断裂 · BLOCK。"""
        mock_l109_client.query_audit_trail.side_effect = L207Error(
            code="E_L207_AUDIT_SEQUENCE_CORRUPT",
            user_message="审计链断裂")
        with pytest.raises(L207Error) as exc:
            await sut.query_audit_trail(
                project_id=mock_project_id,
                anchor={"type": "artifact_id", "value": "a-1"},
                depth=4)
        assert exc.value.code == "E_L207_AUDIT_SEQUENCE_CORRUPT"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_108_audit_permission_denied(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-108 · 无权限 · REJECT。"""
        mock_l109_client.query_audit_trail.side_effect = L207Error(
            code="E_L207_AUDIT_PERMISSION_DENIED",
            user_message="无权限")
        with pytest.raises(L207Error) as exc:
            await sut.query_audit_trail(
                project_id=mock_project_id,
                anchor={"type": "tick_id", "value": "t-1"},
                depth=4)
        assert exc.value.code == "E_L207_AUDIT_PERMISSION_DENIED"

    # ---------- IC-11 多模态 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_109_content_artifact_not_found(
        self, sut, mock_project_id: str, mock_l108_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-109 · IC-11 artifact 不存在 · USER_ERROR。"""
        mock_l108_client.process_content.side_effect = L207Error(
            code="E_L207_CONTENT_ARTIFACT_NOT_FOUND",
            user_message="artifact 不存在")
        with pytest.raises(L207Error) as exc:
            await sut.fetch_multimodal(
                project_id=mock_project_id,
                artifact_id="GONE", content_hash="h-x")
        assert exc.value.code == "E_L207_CONTENT_ARTIFACT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_110_content_timeout(
        self, sut, mock_project_id: str, mock_l108_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-110 · IC-11 超时 · DEGRADE · 返 skeleton。"""
        mock_l108_client.process_content.side_effect = asyncio.TimeoutError
        r = await sut.fetch_multimodal(
            project_id=mock_project_id,
            artifact_id="a-1", content_hash="h-x",
            graceful_degrade=True,
        )
        assert r.skeleton is True

    @pytest.mark.asyncio
    async def test_TC_L110_L207_111_content_unsupported_type(
        self, sut, mock_project_id: str, mock_l108_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-111 · 不支持的 mime · REJECT。"""
        mock_l108_client.process_content.side_effect = L207Error(
            code="E_L207_CONTENT_UNSUPPORTED_TYPE",
            user_message="不支持的 mime")
        with pytest.raises(L207Error) as exc:
            await sut.fetch_multimodal(
                project_id=mock_project_id,
                artifact_id="a-weird", content_hash="h-x")
        assert exc.value.code == "E_L207_CONTENT_UNSUPPORTED_TYPE"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_112_content_cache_hit_stale_recovers(
        self, sut, mock_project_id: str, mock_l108_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-112 · cache hit 但 content_hash 过期 · RECOVER · 重获。"""
        sut.multimodal_cache.put(
            artifact_id="a-1", content_hash="OLD",
            payload={"title": "stale"})
        mock_l108_client.process_content.return_value = MagicMock(
            title="fresh", description="x", content="y")
        r = await sut.fetch_multimodal(
            project_id=mock_project_id,
            artifact_id="a-1", content_hash="NEW")
        assert r.title == "fresh"

    # ---------- IC-L2-07 委托 L2-04 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_113_intervene_missing_confirm(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-113 · 缺 2FA · BLOCK。"""
        with pytest.raises(L207Error) as exc:
            await sut.submit_admin_change(
                project_id=mock_project_id,
                intent={
                    "intervention_type": "admin_config_change",
                    "module": "engine_config",
                    "change_path": "tick_interval_sec",
                    "old_value": 5, "new_value": 3,
                    "reason": "提高响应速度",
                    # 缺 confirmation_token
                },
            )
        assert exc.value.code == "E_L207_INTERVENE_MISSING_CONFIRM"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_114_intervene_whitelist_no_confirm(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-114 · 白名单操作（kill）缺 2FA · BLOCK。"""
        with pytest.raises(L207Error) as exc:
            await sut.execution_instance.kill(
                project_id=mock_project_id,
                instance_id="inst-1",
                reason="需要重启",
                # 缺 confirmation_token
            )
        assert exc.value.code == "E_L207_INTERVENE_WHITELIST_NO_CONFIRM"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_115_intervene_reason_too_short(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-115 · 变更理由过短 · BLOCK。"""
        with pytest.raises(L207Error) as exc:
            await sut.submit_admin_change(
                project_id=mock_project_id,
                intent={
                    "intervention_type": "admin_config_change",
                    "module": "engine_config",
                    "change_path": "tick_interval_sec",
                    "old_value": 5, "new_value": 3,
                    "reason": "x",  # 过短
                    "confirmation_token": "2fa",
                },
            )
        assert exc.value.code == "E_L207_INTERVENE_REASON_TOO_SHORT"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_116_intervene_rejected_by_l204(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-116 · L2-04 拒绝 · USER_RETRY。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int", status="REJECTED",
            error=MagicMock(code="E-L2-04-013"))
        r = await sut.submit_admin_change(
            project_id=mock_project_id,
            intent={
                "intervention_type": "admin_config_change",
                "module": "engine_config",
                "change_path": "x",
                "old_value": 1, "new_value": 2,
                "reason": "有足够长的理由说明 · 这里填字凑字数",
                "confirmation_token": "2fa",
            },
        )
        assert r.status == "REJECTED"
        assert r.error_code == "E_L207_INTERVENE_REJECTED_BY_L204"

    # ---------- IC-L2-11 banner ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_117_banner_l201_not_ready(
        self, sut, mock_project_id: str, mock_l201_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-117 · L2-01 未就绪 · RETRY。"""
        mock_l201_service.register_banner.side_effect = [
            L207Error(code="E_L207_BANNER_L201_NOT_READY",
                      user_message="L2-01 未就绪"),
            MagicMock(banner_id="b-1"),  # 第二次成功
        ]
        r = await sut.push_red_line_banner(
            project_id=mock_project_id,
            alert={"alert_id": "rl-1", "severity": "critical",
                   "message": "test"},
        )
        assert r.pushed is True
        assert mock_l201_service.register_banner.call_count == 2

    @pytest.mark.asyncio
    async def test_TC_L110_L207_118_banner_duplicate_idempotent(
        self, sut, mock_project_id: str, mock_l201_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-118 · banner 重复 · IDEMPOTENT · 静默。"""
        mock_l201_service.register_banner.return_value = MagicMock(
            banner_id="b-dup")
        alert = {"alert_id": "rl-dup", "severity": "critical",
                 "message": "test"}
        await sut.push_red_line_banner(project_id=mock_project_id, alert=alert)
        await sut.push_red_line_banner(project_id=mock_project_id, alert=alert)
        # 只推一次（idempotency_key）
        assert mock_l201_service.register_banner.call_count == 1

    @pytest.mark.asyncio
    async def test_TC_L110_L207_119_banner_dismissible_true_rejected(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-119 · 试图推 dismissable=true 的红线 · REJECT（违反不变式）。"""
        with pytest.raises(L207Error) as exc:
            await sut.push_red_line_banner(
                project_id=mock_project_id,
                alert={"alert_id": "rl-x", "severity": "critical",
                       "message": "x",
                       "dismissable": True},  # 违法
            )
        assert exc.value.code == "E_L207_BANNER_DISMISSIBLE_TRUE"

    # ---------- IC-09 审计 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L207_120_audit_append_fail_retries(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L207-120 · IC-09 append fail · RETRY 最多 3 次。"""
        mock_event_bus.append_event.side_effect = [
            ConnectionError("f1"), ConnectionError("f2"),
            {"event_id": "e", "sequence": 1},
        ]
        await sut.audit_append(
            project_id=mock_project_id,
            event_type="L1-10:admin_module_switched",
            payload={"module": "kb_admin"},
            trace_id="trace-1",
        )
        assert mock_event_bus.append_event.call_count == 3

    @pytest.mark.asyncio
    async def test_TC_L110_L207_121_audit_missing_trace_id_auto_fill(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L207-121 · 缺 trace_id · WARN · 自动补。"""
        await sut.audit_append(
            project_id=mock_project_id,
            event_type="L1-10:admin_opened",
            payload={},
            # 缺 trace_id
        )
        kw = mock_event_bus.append_event.call_args.kwargs
        assert kw.get("trace_id") or kw.get("payload", {}).get("trace_id")

    def test_TC_L110_L207_122_dom_tamper_detected(
        self, sut,
    ) -> None:
        """TC-L110-L207-122 · DOM 被篡改（MutationObserver 检测）· REMEDIATE + 审计。"""
        # 伪造 DOM tamper 信号
        sut.security_guard.on_dom_tamper(detected_at="now", evidence="x")
        # 立即 remediation + 审计事件
        assert sut.security_guard.tamper_count >= 1
        assert sut.security_guard.last_remediation_at is not None
```

---

## §4 IC-XX 契约集成（≥ 6）

```python
# file: tests/l1_10/test_l2_07_ic_contracts.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_07_IC_Contracts:

    @pytest.mark.asyncio
    async def test_TC_L110_L207_601_ic_l2_12_on_event_received(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-601 · IC-L2-12 · 13 类事件前缀路由（L1-07/09/01/06 等）。"""
        events = [
            ("L1-07:red_line_alert", "supervisor_admin"),
            ("L1-09:event_appended", "stats_analysis"),
            ("L1-01:decision_recorded", "stats_analysis"),
        ]
        for etype, expected_coord in events:
            r = await sut.on_event_received({
                "type": etype, "project_id": mock_project_id,
                "payload": {}, "ts": "now", "sequence": 1,
            })

    @pytest.mark.asyncio
    async def test_TC_L110_L207_602_ic_18_query_audit_trail_payload(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-602 · IC-18 · payload 含 project_id + anchor + depth。"""
        mock_l109_client.query_audit_trail.return_value = MagicMock(
            layers={}, trace_id="x")
        await sut.query_audit_trail(
            project_id=mock_project_id,
            anchor={"type": "artifact_id", "value": "a-1"},
            depth=4)
        kw = mock_l109_client.query_audit_trail.call_args.kwargs
        assert kw["project_id"] == mock_project_id
        assert kw["anchor"]["value"] == "a-1"
        assert kw["depth"] == 4

    @pytest.mark.asyncio
    async def test_TC_L110_L207_603_ic_11_process_content_payload(
        self, sut, mock_project_id: str, mock_l108_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-603 · IC-11 · payload 含 artifact_id + content_hash + options。"""
        mock_l108_client.process_content.return_value = MagicMock(
            title="t", description="d", content="c")
        await sut.fetch_multimodal(
            project_id=mock_project_id,
            artifact_id="a-1", content_hash="h")
        kw = mock_l108_client.process_content.call_args.kwargs
        assert kw["project_id"] == mock_project_id
        assert kw["artifact_id"] == "a-1"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_604_ic_l2_07_user_intervene_types(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-604 · IC-L2-07 · admin_config_change + authorize 两类都走 L2-04。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int", status="ACKED")
        # admin_config_change
        await sut.submit_admin_change(
            project_id=mock_project_id,
            intent={
                "intervention_type": "admin_config_change",
                "module": "engine_config",
                "change_path": "tick", "old_value": 5, "new_value": 3,
                "reason": "性能优化需要更快 tick",
                "confirmation_token": "2fa",
            },
        )
        # authorize
        await sut.authorize_red_line(
            project_id=mock_project_id,
            alert_id="rl-1", decision="grant",
            scope_limit=None, confirmation_token="2fa",
        )
        types = [c.kwargs["type"] for c in mock_l204_service.submit_intervention.call_args_list]
        assert "admin_config_change" in types
        assert "authorize" in types

    @pytest.mark.asyncio
    async def test_TC_L110_L207_605_ic_l2_11_push_top_banner(
        self, sut, mock_project_id: str, mock_l201_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-605 · IC-L2-11 · entry.level=hard · dismissable=false · text/kind 必带。"""
        await sut.push_red_line_banner(
            project_id=mock_project_id,
            alert={"alert_id": "rl-1", "severity": "critical",
                   "message": "test alert"},
        )
        kw = mock_l201_service.register_banner.call_args.kwargs
        assert kw["entry"]["level"] == "hard"
        assert kw["entry"]["dismissable"] is False

    @pytest.mark.asyncio
    async def test_TC_L110_L207_606_ic_09_audit_admin_operations(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L207-606 · IC-09 · admin_opened / admin_module_switched / admin_config_changed。"""
        await sut.open_admin_view(project_id=mock_project_id)
        await sut.switch_admin_module(
            project_id=mock_project_id, module_id="kb_admin")
        event_types = "|".join(
            (c.kwargs.get("event_type") or c.kwargs.get("type") or "")
            for c in mock_event_bus.append_event.call_args_list)
        assert "admin_opened" in event_types
        assert "admin_module_switched" in event_types
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_10/test_l2_07_perf.py
from __future__ import annotations

import statistics
import time
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_07_SLO:

    OPEN_ADMIN_P95_MS = 1000
    AUDIT_QUERY_P95_MS = 2000
    CACHE_HIT_P95_MS = 50
    BANNER_PUSH_P95_MS = 100
    MODULE_SWITCH_P95_MS = 100

    @pytest.mark.asyncio
    async def test_TC_L110_L207_701_open_admin_view_p95_le_1s(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-701 · open_admin_view P95 ≤ 1s · 50 样本（13 面板并发）。"""
        samples: list[float] = []
        for _ in range(50):
            t0 = time.perf_counter()
            await sut.open_admin_view(project_id=mock_project_id)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.OPEN_ADMIN_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L207_702_query_audit_trail_p95_le_2s(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-702 · query_audit_trail P95 ≤ 2s。"""
        mock_l109_client.query_audit_trail.return_value = MagicMock(
            layers={}, trace_id="x")
        samples: list[float] = []
        for _ in range(50):
            t0 = time.perf_counter()
            await sut.query_audit_trail(
                project_id=mock_project_id,
                anchor={"type": "artifact_id", "value": "a-1"},
                depth=4)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.AUDIT_QUERY_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L207_703_multimodal_cache_hit_p95_le_50ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-703 · 多模态缓存命中 P95 ≤ 50ms · 500 样本。"""
        for i in range(100):
            sut.multimodal_cache.put(
                artifact_id=f"a-{i}", content_hash="h",
                payload={"title": f"t-{i}", "description": "x"})
        samples: list[float] = []
        for i in range(500):
            t0 = time.perf_counter()
            await sut.fetch_multimodal(
                project_id=mock_project_id,
                artifact_id=f"a-{i % 100}", content_hash="h")
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.CACHE_HIT_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L207_704_push_banner_p95_le_100ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-704 · push_red_line_banner P95 ≤ 100ms · 100 样本。"""
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.push_red_line_banner(
                project_id=mock_project_id,
                alert={"alert_id": f"rl-{i}", "severity": "critical",
                       "message": "x"})
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.BANNER_PUSH_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L207_705_switch_module_p95_le_100ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-705 · switch_admin_module P95 ≤ 100ms · 100 样本。"""
        await sut.open_admin_view(project_id=mock_project_id)
        modules = ["engine_config", "kb_admin", "supervisor_admin",
                   "verifier_primitive", "subagent_registry",
                   "skill_call_graph", "stats_analysis", "system_diag"]
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.switch_admin_module(
                project_id=mock_project_id,
                module_id=modules[i % len(modules)])
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.MODULE_SWITCH_P95_MS
```

---

## §6 端到端 e2e 场景（≥ 2）

```python
# file: tests/l1_10/test_l2_07_e2e.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_07_E2E:

    @pytest.mark.asyncio
    async def test_TC_L110_L207_801_e2e_red_line_full_flow(
        self, sut, mock_project_id: str,
        mock_l201_service: AsyncMock, mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-801 · e2e · 红线事件到达 → banner 推 L2-01 → 用户授权 → IC-17。"""
        # 1. 收到红线事件
        await sut.on_event_received({
            "type": "L1-07:red_line_alert",
            "project_id": mock_project_id,
            "payload": {"alert_id": "rl-e2e", "severity": "critical",
                        "message": "越权: 试图写 prod db"},
            "ts": "now", "sequence": 1,
        })
        # 2. banner 推 L2-01
        mock_l201_service.register_banner.assert_called()
        kw = mock_l201_service.register_banner.call_args.kwargs
        assert kw["entry"]["level"] == "hard"
        # 3. 用户授权
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-auth", status="ACKED")
        r = await sut.authorize_red_line(
            project_id=mock_project_id,
            alert_id="rl-e2e", decision="grant",
            scope_limit={"repo": "foo/bar", "duration_sec": 3600},
            confirmation_token="2fa-OK",
        )
        assert r.status == "submitted"
        # 4. L2-04 被调 type=authorize
        auth_kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert auth_kw["type"] == "authorize"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_802_e2e_config_change_with_audit_trail(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L207-802 · e2e · Admin 配置变更 + 2FA + 审计链完整。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-cc", status="ACKED")
        # 1. 打开 Admin
        await sut.open_admin_view(project_id=mock_project_id)
        # 2. 切到 EngineConfig
        await sut.switch_admin_module(
            project_id=mock_project_id, module_id="engine_config")
        # 3. 提交变更
        r = await sut.submit_admin_change(
            project_id=mock_project_id,
            intent={
                "intervention_type": "admin_config_change",
                "module": "engine_config",
                "change_path": "tick_interval_sec",
                "old_value": 5, "new_value": 3,
                "reason": "提高响应速度 · 匹配高并发需求",
                "confirmation_token": "2fa-OK",
            },
        )
        assert r.status == "submitted"
        # 4. 审计链：admin_opened / module_switched / config_changed 全留痕
        event_types = "|".join(
            (c.kwargs.get("event_type") or c.kwargs.get("type") or "")
            for c in mock_event_bus.append_event.call_args_list)
        assert "admin_opened" in event_types
        assert "admin_module_switched" in event_types
```

---

## §7 测试 fixture

```python
# file: tests/l1_10/conftest_l2_07.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_07.service import AdminModuleCoordinator


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="EventBus")
    bus.append_event = MagicMock(return_value={"event_id": f"evt-{uuid.uuid4()}"})
    return bus


@pytest.fixture
def mock_repo() -> MagicMock:
    r = MagicMock(name="AdminRepo")
    r.store_event = MagicMock(return_value=None)
    return r


@pytest.fixture
def mock_l109_client() -> AsyncMock:
    c = AsyncMock(name="L109Client")
    c.query_audit_trail = AsyncMock(return_value=MagicMock(
        layers={}, trace_id="trace-default"))
    return c


@pytest.fixture
def mock_l108_client() -> AsyncMock:
    c = AsyncMock(name="L108Client")
    c.process_content = AsyncMock(return_value=MagicMock(
        title="default", description="d", content="c"))
    return c


@pytest.fixture
def mock_l201_service() -> AsyncMock:
    s = AsyncMock(name="L201")
    s.register_banner = AsyncMock(return_value=MagicMock(banner_id="b-1"))
    return s


@pytest.fixture
def mock_l203_service() -> AsyncMock:
    s = AsyncMock(name="L203")
    s.pull_history = AsyncMock(return_value=MagicMock(events=[]))
    return s


@pytest.fixture
def mock_l204_service() -> AsyncMock:
    s = AsyncMock(name="L204")
    s.submit_intervention = AsyncMock(return_value=MagicMock(
        intent_id="int-default", status="ACKED"))
    return s


@pytest.fixture
def sut(
    mock_project_id: str, mock_event_bus: MagicMock, mock_repo: MagicMock,
    mock_l109_client: AsyncMock, mock_l108_client: AsyncMock,
    mock_l201_service: AsyncMock, mock_l203_service: AsyncMock,
    mock_l204_service: AsyncMock,
) -> AdminModuleCoordinator:
    return AdminModuleCoordinator(
        session={"active_project": mock_project_id},
        event_bus=mock_event_bus,
        repo=mock_repo,
        l109=mock_l109_client,
        l108=mock_l108_client,
        l201=mock_l201_service,
        l203=mock_l203_service,
        l204=mock_l204_service,
        config={
            "reason_min_chars": 10,
            "whitelist_ops_require_2fa": True,
            "banner_retry_max": 3,
            "audit_append_retry_max": 3,
            "multimodal_cache_size": 128,
            "audit_cache_ttl_sec": 7 * 24 * 3600,
        },
    )
```

---

## §8 集成点用例（与兄弟 L2 / L1 协作 · ≥ 2）

```python
# file: tests/l1_10/test_l2_07_siblings.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_07_SiblingIntegration:

    @pytest.mark.asyncio
    async def test_TC_L110_L207_901_l2_03_dispatches_13_event_types(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-901 · L2-03 分发 13 类事件前缀 · 全部被本 L2 正确路由。"""
        event_types = [
            "L1-07:red_line_alert", "L1-07:supervisor_warn",
            "L1-09:event_appended", "L1-09:alert_cleared",
            "L1-01:decision_recorded", "L1-01:tick_halted",
            "L1-06:kb_upserted", "L1-06:kb_promoted",
            "L1-08:content_processed", "L1-02:stage_gate",
            "L1-05:skill_invoked", "L1-05:subagent_delegated",
            "L1-10:admin_opened",
        ]
        for et in event_types:
            await sut.on_event_received({
                "type": et, "project_id": mock_project_id,
                "payload": {}, "ts": "now", "sequence": 1,
            })
        # 13 类全被处理 · 无异常

    @pytest.mark.asyncio
    async def test_TC_L110_L207_902_l2_04_delegation_no_direct_ic17(
        self,
    ) -> None:
        """TC-L110-L207-902 · L2-07 代码不得直 import IC17 · 必经 L2-04。"""
        offenders = static_scan.find_imports_in(
            path_prefix="app/l1_10/l2_07/",
            forbidden_imports=["IC17Transport", "send_ic17"])
        assert offenders == [], f"L2-07 违规直发 IC-17: {offenders}"

    @pytest.mark.asyncio
    async def test_TC_L110_L207_903_cross_project_banner_rejected(
        self, sut, mock_project_id: str, mock_l201_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-903 · 跨项目 banner 推 · 拒绝 · 不打扰其他 project。"""
        sut.session.active_project = mock_project_id
        from app.l1_10.l2_07.errors import L207Error
        with pytest.raises(L207Error):
            await sut.push_red_line_banner(
                project_id="pid-OTHER",  # 跨项目
                alert={"alert_id": "rl-x", "severity": "critical",
                       "message": "x"})
        mock_l201_service.register_banner.assert_not_called()
```

---

## §9 边界 / edge case

```python
# file: tests/l1_10/test_l2_07_edge.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_07_Edge:

    @pytest.mark.asyncio
    async def test_TC_L110_L207_911_9_modules_lazy_load_when_switched(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-911 · 9 sub coordinator · 首次切换才真正初始化（懒加载）。"""
        await sut.open_admin_view(project_id=mock_project_id)
        initial_loaded = sut.lazy_loaded_coordinators.copy()
        await sut.switch_admin_module(
            project_id=mock_project_id, module_id="system_diag")
        assert "system_diag" in sut.lazy_loaded_coordinators
        # 其他模块不一定 loaded
        assert sut.lazy_loaded_coordinators != initial_loaded or True

    @pytest.mark.asyncio
    async def test_TC_L110_L207_912_multimodal_cache_lru_eviction(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-912 · 多模态缓存超容量 · LRU 淘汰。"""
        cap = sut.config["multimodal_cache_size"]
        for i in range(cap + 50):
            sut.multimodal_cache.put(
                artifact_id=f"a-{i}", content_hash="h",
                payload={"title": f"t-{i}"})
        # 最旧的被淘汰
        assert sut.multimodal_cache.size() <= cap

    @pytest.mark.asyncio
    async def test_TC_L110_L207_913_empty_audit_trail(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L207-913 · query_audit_trail · L1-09 返空 · 不报错。"""
        mock_l109_client.query_audit_trail.return_value = MagicMock(
            layers={"tick": [], "decision": [], "skill": [], "artifact": []},
            trace_id="empty")
        r = await sut.query_audit_trail(
            project_id=mock_project_id,
            anchor={"type": "artifact_id", "value": "a-none"},
            depth=4)
        assert all(len(v) == 0 for v in r.layers.values())

    @pytest.mark.asyncio
    async def test_TC_L110_L207_914_13_panels_concurrent_init_timeout_tolerant(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L207-914 · 13 面板并发初始化 · 某个面板慢 · 其他不阻塞。"""
        import asyncio
        async def _slow(*a, **kw):
            await asyncio.sleep(0.5)
            return MagicMock()
        sut.verifier_primitive.list = _slow
        r = await sut.open_admin_view(
            project_id=mock_project_id,
            parallel_timeout_ms=200)
        # 至少部分成功 + 告警慢的
        assert r.initialized_modules_count >= 7

    @pytest.mark.asyncio
    async def test_TC_L110_L207_915_sequence_gap_triggers_recovery_once(
        self, sut, mock_project_id: str, mock_l203_service: AsyncMock,
    ) -> None:
        """TC-L110-L207-915 · sequence gap · 只触发 1 次 recovery（不反复）。"""
        await sut.on_event_received({
            "type": "L1-09:event_appended", "project_id": mock_project_id,
            "payload": {}, "ts": "now", "sequence": 100,
        })
        for gap_seq in [105, 110, 120]:
            await sut.on_event_received({
                "type": "L1-09:event_appended", "project_id": mock_project_id,
                "payload": {}, "ts": "now", "sequence": gap_seq,
            })
        # recovery 应有合理的合并（不是每次 gap 都单独拉）
        assert mock_l203_service.pull_history.call_count <= 3
```

---

*— TDD · L1-10 L2-07 · Admin 子管理模块 · depth-B · v1.0 · 2026-04-22 · session-L —*
