---
doc_id: tests-L1-02-L2-02-启动阶段产出器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-02-启动阶段产出器.md
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-H
created_at: 2026-04-22
---

# L1-02 L2-02-启动阶段产出器 · TDD 测试用例

> 基于 3-1 L2-02 §3 对外接口（4 方法：`kickoff_create_project / write_goal_doc / write_scope_doc / activate_project_id` + §6 算法 5 函数：`produce_kickoff / activate_project_id / atomic_write_chart / compute_anchor_hash / recover_draft`）+ §11/§3.6 错误码（14/15 条 · 前缀统一 `E_L102_L202_`）+ §12 性能 SLO + §13 TC ID 矩阵驱动。
> **PM-14 硬定位**：本 L2 是 `project_id` 生成的唯一入口 · 本测试文档对"谁可以生成 · 何时激活 · 跨项目越权"场景零容忍覆盖。
> TC ID 统一格式：`TC-L102-L202-NNN`（L1-02 下 L2-02 · 三位流水号：001-099 正向 · 101-199 负向 · 2xx 集成 · 3xx SLO · 4xx e2e · 5xx 集成点 · 6xx 边界）。
> pytest + Python 3.11+ 类型注解；`class TestL2_02_KickoffProducer` 组织；负向/性能/集成单独分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 × 错误码 × IC-XX × 覆盖类型）
- [x] §2 正向用例（每 public + 每内部算法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1 · 共 15 条）
- [x] §4 IC-XX 契约集成测试（≥ 6 · join ≥ 3）
- [x] §5 性能 SLO 用例（§12 9 指标 ≥ 3 perf mark）
- [x] §6 端到端 e2e 场景（2 张 GWT）
- [x] §7 测试 fixture（≥ 5 mock）
- [x] §8 集成点用例（与 L2-01 / L2-07 / L1-05 / L1-09 协作）
- [x] §9 边界 / edge case（≥ 4 · pid 冲突 / 并发 / draft 恢复 / anchor hash 不一致）

---

## §1 覆盖度索引

> 每个 §3 对外方法 / §6 内部算法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO；edge = 边界/并发/崩溃。

### §1.1 方法 / 算法 × 测试 × 覆盖类型

| 方法 / 算法（出处）                                     | TC ID               | 覆盖类型    | 错误码                       | 对应 IC            |
|---------------------------------------------------------|---------------------|-------------|------------------------------|--------------------|
| `kickoff_create_project()` · §3.2 正向 full             | TC-L102-L202-001    | unit        | —                            | IC-L2-01           |
| `kickoff_create_project()` · §3.2 正向 minimal          | TC-L102-L202-002    | unit        | —                            | IC-L2-01           |
| `kickoff_create_project()` · §3.2 re-open full          | TC-L102-L202-003    | unit        | —                            | IC-L2-01           |
| `produce_kickoff()` · §6.1 主循环                       | TC-L102-L202-004    | unit        | —                            | IC-05 / IC-09      |
| `produce_kickoff()` · 幂等（trigger_id 相同）           | TC-L102-L202-005    | unit        | —                            | IC-L2-01           |
| `write_goal_doc()` · §3.3 正向 8 字段齐                 | TC-L102-L202-006    | unit        | —                            | IC-L2-02           |
| `write_scope_doc()` · §3.4 正向 stakeholder=1           | TC-L102-L202-007    | unit        | —                            | IC-L2-02           |
| `write_scope_doc()` · §3.4 正向 stakeholder=N           | TC-L102-L202-008    | unit        | —                            | IC-L2-02           |
| `activate_project_id()` · §3.5 正向 DRAFT → INITIALIZED | TC-L102-L202-009    | unit        | —                            | IC-09              |
| `activate_project_id()` · §6.2 hash 复核通过            | TC-L102-L202-010    | unit        | —                            | IC-09              |
| `atomic_write_chart()` · §6.3 tempfile + rename         | TC-L102-L202-011    | unit        | —                            | —                  |
| `atomic_write_chart()` · §6.3 post_write hash           | TC-L102-L202-012    | unit        | —                            | —                  |
| `compute_anchor_hash()` · §6.4 正向                     | TC-L102-L202-013    | unit        | —                            | —                  |
| `compute_anchor_hash()` · §6.4 frontmatter 不影响       | TC-L102-L202-014    | unit        | —                            | —                  |
| `compute_anchor_hash()` · §6.4 幂等（同内容同 hash）    | TC-L102-L202-015    | unit        | —                            | —                  |
| `recover_draft()` · §6.5 全齐续传                       | TC-L102-L202-016    | unit        | —                            | IC-09              |
| `recover_draft()` · §6.5 半成品清理                     | TC-L102-L202-017    | unit        | —                            | IC-09              |
| `recover_draft()` · §6.5 no_op（无半成品）              | TC-L102-L202-018    | unit        | —                            | —                  |
| `_publish_s1_events()` · §2.4 顺序 4 事件               | TC-L102-L202-019    | unit        | —                            | IC-09              |
| `_validate_trigger()` · §3.2 入参校验                   | TC-L102-L202-020    | unit        | —                            | —                  |

### §1.2 错误码 × 测试（§11 14 条 + §3.6 `USER_NOT_CONFIRMED` = 15 条全覆盖 · 前缀 `E_L102_L202_`）

| 错误码                                   | TC ID               | 方法                         | 归属 §11 分类          |
|------------------------------------------|---------------------|------------------------------|------------------------|
| `E_L102_L202_001` · PID_DUPLICATE        | TC-L102-L202-101    | `produce_kickoff()`          | PM-14 唯一性           |
| `E_L102_L202_002` · USER_NOT_CONFIRMED   | TC-L102-L202-102    | `activate_project_id()`      | Gate 未通过            |
| `E_L102_L202_003` · GOAL_MISSING_SECTIONS| TC-L102-L202-103    | `write_goal_doc()`           | Charter 8 字段         |
| `E_L102_L202_004` · SCOPE_NOT_LOCKED     | TC-L102-L202-104    | `write_goal_doc()`           | scope.in_scope 空      |
| `E_L102_L202_005` · TEMPLATE_INVALID     | TC-L102-L202-105    | IC-L2-02 返模板损坏          | L2-07 协同             |
| `E_L102_L202_006` · CLARIFICATION_EXCEEDED | TC-L102-L202-106  | `produce_kickoff()`          | 3 轮澄清               |
| `E_L102_L202_007` · STATE_NOT_DRAFT      | TC-L102-L202-107    | `activate_project_id()`      | 状态非 DRAFT           |
| `E_L102_L202_008` · CHART_ALREADY_EXISTS | TC-L102-L202-108    | `atomic_write_chart()`       | O_EXCL 拒覆盖          |
| `E_L102_L202_009` · POST_WRITE_HASH_MISMATCH | TC-L102-L202-109| `atomic_write_chart()`       | 写后 hash 复检         |
| `E_L102_L202_010` · PM14_OWNERSHIP_VIOLATION | TC-L102-L202-110| `activate_project_id()`      | 非 L2-01 越权调用      |
| `E_L102_L202_011` · ANCHOR_HASH_MISMATCH | TC-L102-L202-111    | `activate_project_id()`      | 激活前 hash 对比       |
| `E_L102_L202_012` · CROSS_PROJECT_PATH   | TC-L102-L202-112    | `atomic_write_chart()`       | 路径前缀非 projects/   |
| `E_L102_L202_013` · ATOMIC_WRITE_FAILED  | TC-L102-L202-113    | `atomic_write_chart()`       | I/O 错 + 重试耗尽      |
| `E_L102_L202_014` · GOAL_ANCHOR_TAMPERING| TC-L102-L202-114    | `compute_anchor_hash()`      | 后续回溯校验           |
| `E_L102_L202_015` · BRAINSTORM_SUBAGENT_FAILED | TC-L102-L202-115| `produce_kickoff()`        | L1-05 崩 + 重试        |

### §1.3 IC 契约 × 测试

| IC          | 方向                   | TC ID               | 备注                                    |
|-------------|------------------------|---------------------|-----------------------------------------|
| IC-L2-01    | L2-01 → L2-02（接收）  | TC-L102-L202-201    | trigger_stage_production payload        |
| IC-L2-02    | L2-02 → L2-07（发起）  | TC-L102-L202-202    | request_template · 2 次（goal + scope） |
| IC-05       | L2-02 → L1-05（发起）  | TC-L102-L202-203    | delegate_subagent brainstorming         |
| IC-06       | L2-02 → L1-06（发起）  | TC-L102-L202-204    | kb_read 可选 · trim_level=full          |
| IC-09       | L2-02 → L1-09（发起）  | TC-L102-L202-205    | 4 事件顺序 · project_created 起头        |
| IC-L2-05    | L2-02 → L2-01（回调）  | TC-L102-L202-206    | S1_ready bundle                         |
| IC-17       | 间接接收（via L2-01）  | TC-L102-L202-207    | user_intervene(approve) 触发 activate   |

### §1.4 性能 SLO × 测试

| 指标（§12.1）                             | 目标                 | TC ID               |
|-------------------------------------------|----------------------|---------------------|
| 章程原子落盘（单份 md）· P95 200ms        | 200ms                | TC-L102-L202-301    |
| anchor_hash 计算 · P95 30ms               | 30ms                 | TC-L102-L202-302    |
| IC-09 4 事件组合 · P95 180ms              | 180ms                | TC-L102-L202-303    |
| activate_project_id · P95 60ms            | 60ms                 | TC-L102-L202-304    |

### §1.5 e2e 场景

| 场景                                           | TC ID               |
|------------------------------------------------|---------------------|
| S1 Kickoff 完整链路（用户一句话 → INITIALIZED）| TC-L102-L202-401    |
| S1 回退链路（澄清超 3 轮 → degraded → reject）| TC-L102-L202-402    |

### §1.6 边界 × 测试

| 边界                                           | TC ID               |
|------------------------------------------------|---------------------|
| PID 冲突构造 · 重试 1 次后成功                 | TC-L102-L202-601    |
| 并发双 produce_kickoff 同 project（锁互斥）    | TC-L102-L202-602    |
| recover_draft 从 CHART_WRITING 崩溃恢复        | TC-L102-L202-603    |
| anchor_hash 章程被外部修改 → 后续阶段拒用      | TC-L102-L202-604    |
| DRAFT 超 24h 自动清理                          | TC-L102-L202-605    |

---

## §2 正向用例（每方法 ≥ 1 · 每内部算法 ≥ 1）

> pytest 风格；`class TestL2_02_KickoffProducer`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `StartupProducer`（从 `app.l1_02.l2_02.producer` 导入）。
> §6.1/§6.3/§6.4 辅助算法分别来自 `app.l1_02.l2_02.algo` 的 `produce_kickoff / atomic_write_chart / compute_anchor_hash / recover_draft`。

```python
# file: tests/l1_02/test_l2_02_kickoff_positive.py
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from app.l1_02.l2_02.producer import StartupProducer
from app.l1_02.l2_02.algo import (
    produce_kickoff,
    atomic_write_chart,
    compute_anchor_hash,
    recover_draft,
)
from app.l1_02.l2_02.schemas import (
    KickoffRequest,
    KickoffResponse,
    CharterFields,
    StakeholdersEntry,
    ActivateRequest,
    ActivateResponse,
    RecoveryResult,
)


class TestL2_02_KickoffProducer:
    """每个 public 方法 + 每条内部算法 ≥ 1 正向用例 · 禁 mock SUT 内部私有方法。"""

    # ========= §3.2 方法 1 · kickoff_create_project =========

    def test_TC_L102_L202_001_kickoff_full_trim_success(
        self,
        sut: StartupProducer,
        mock_project_id: str,
        make_kickoff_request,
        mock_template_engine: MagicMock,
        mock_brainstorm_client: MagicMock,
        mock_event_bus: MagicMock,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-001 · full trim + 2 轮澄清收敛 · 完整返回 KickoffSuccess。"""
        req: KickoffRequest = make_kickoff_request(
            user_initial_goal="做一个 todo 应用", trim_level="full", caller_l2="L2-01",
        )
        mock_brainstorm_client.invoke.return_value = {
            "rounds": 2, "is_confirmed": True,
            "slots": {"title": "Todo App", "purpose": "个人任务管理"},
        }
        mock_template_engine.render_template.side_effect = [
            {"template_body": "# {{title}}\n{{purpose}}", "required_fields": 8},
            {"template_body": "# Stakeholders\n- {{who}}", "required_fields": 3},
        ]
        resp: KickoffResponse = sut.kickoff_create_project(req)
        assert resp.status == "ok"
        assert resp.result.project_id.startswith("p_")
        assert resp.result.charter_path.endswith("HarnessFlowGoal.md")
        assert resp.result.stakeholders_path.endswith("HarnessFlowPrdScope.md")
        assert resp.result.goal_anchor_hash.startswith("sha256:")
        assert resp.result.clarification_rounds == 2
        assert resp.result.clarification_incomplete is False
        assert resp.result.events_published == [
            "project_created", "charter_ready",
            "stakeholders_ready", "goal_anchor_hash_locked",
        ]

    def test_TC_L102_L202_002_kickoff_minimal_trim_success(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-002 · minimal trim · 跳过 RACI/多语言 · 仍产 project_id + 2 章程。"""
        req = make_kickoff_request(trim_level="minimal", user_initial_goal="API 原型")
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "tpl goal minimal", "required_fields": 2},
            {"template_body": "tpl scope minimal", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        assert resp.status == "ok"
        assert resp.result.trim_level_applied == "minimal"

    def test_TC_L102_L202_003_kickoff_reopen_with_preexisting_path(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-003 · S1 re-open · preexisting_charter_path 传入 · 带历史重澄清。"""
        preexisting = tmp_project_root / "p_old" / "chart" / "HarnessFlowGoal.md"
        preexisting.parent.mkdir(parents=True, exist_ok=True)
        preexisting.write_text("# Old\n历史 Goal", encoding="utf-8")
        req = make_kickoff_request(preexisting_charter_path=str(preexisting))
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "tpl goal v2", "required_fields": 8},
            {"template_body": "tpl scope v2", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        assert resp.status == "ok"
        # 历史内容作为 prior_context 注入 brainstorming
        call_kw = mock_brainstorm_client.invoke.call_args.kwargs
        assert "prior_context" in call_kw
        assert "历史 Goal" in call_kw["prior_context"]

    # ========= §6.1 算法 · produce_kickoff =========

    def test_TC_L102_L202_004_produce_kickoff_main_loop(
        self, mock_project_id: str, mock_clock, mock_event_bus: MagicMock,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-004 · §6.1 8 步全路径 · 生成 pid → 落 2 章程 → 锁 hash → 发 4 事件。"""
        mock_brainstorm_client.invoke.return_value = {
            "rounds": 2, "is_confirmed": True,
            "slots": {"title": "X", "purpose": "Y", "in_scope": ["A"], "success_criteria": ["B"]},
        }
        mock_template_engine.render_template.side_effect = [
            {"template_body": "# X\nY", "required_fields": 8},
            {"template_body": "# Stakeholders", "required_fields": 1},
        ]
        result = produce_kickoff(
            user_utterance="做个东西",
            brainstorm=mock_brainstorm_client, template=mock_template_engine,
            event_bus=mock_event_bus, clock=mock_clock, project_root=str(tmp_project_root),
        )
        assert result.project_id.startswith("p_")
        assert result.state == "DRAFT"
        assert len(result.chart_paths) == 2
        assert result.emitted_events == [
            "project_created", "chart_written",
            "manifest_written", "s1_ready",
        ]

    def test_TC_L102_L202_005_kickoff_idempotent_by_trigger_id(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-005 · 同 trigger_id 二次调用 · 返回相同 project_id · 不重复落盘。"""
        req = make_kickoff_request(trigger_id="t-same-123")
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8}, {"template_body": "y", "required_fields": 1},
        ] * 2  # 容纳二次调用但不应实际调到
        r1 = sut.kickoff_create_project(req)
        r2 = sut.kickoff_create_project(req)
        assert r1.result.project_id == r2.result.project_id
        assert mock_template_engine.render_template.call_count == 2  # 二次调用不重复拉模板

    # ========= §3.3 方法 2 · write_goal_doc =========

    def test_TC_L102_L202_006_write_goal_doc_8_fields_ok(
        self, sut: StartupProducer, mock_project_id: str,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-006 · Charter 8 字段齐 · 原子落盘成功 · wrote_atomic=True。"""
        charter = CharterFields(
            title="Todo App", purpose="个人任务管理 10 字足够",
            scope={"in_scope": ["a"], "out_of_scope": []},
            success_criteria=["s"], constraints=["c"],
            risks_initial=["r"], stakeholders_initial=["user"],
            authority={"approver": "user", "escalation_path": []},
        )
        res = sut.write_goal_doc(
            project_id=mock_project_id, charter_fields=charter,
            template_body="# {{title}}\n{{purpose}}", trim_level="full",
        )
        assert res.wrote_atomic is True
        assert res.charter_path.endswith("HarnessFlowGoal.md")
        assert res.bytes_written > 0
        assert len(res.checksum_sha256) == 64

    # ========= §3.4 方法 3 · write_scope_doc =========

    def test_TC_L102_L202_007_write_scope_doc_single_owner(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-007 · stakeholders=1（仅 project_owner）· has_owner=True。"""
        holders = [StakeholdersEntry(role="project_owner", who="user", influence="high")]
        res = sut.write_scope_doc(
            project_id=mock_project_id, stakeholders=holders,
            template_body="tpl", trim_level="minimal",
        )
        assert res.count == 1
        assert res.has_owner is True

    def test_TC_L102_L202_008_write_scope_doc_multi_with_raci(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-008 · stakeholders=3 · trim=full 时 RACI 字段生效。"""
        holders = [
            StakeholdersEntry(role="project_owner", who="user", influence="high", raci="A"),
            StakeholdersEntry(role="tech_lead", who="tl", influence="high", raci="R"),
            StakeholdersEntry(role="end_user", who="u", influence="medium", raci="I"),
        ]
        res = sut.write_scope_doc(
            project_id=mock_project_id, stakeholders=holders,
            template_body="tpl", trim_level="full",
        )
        assert res.count == 3
        assert res.has_owner is True

    # ========= §3.5 方法 4 · activate_project_id =========

    def test_TC_L102_L202_009_activate_draft_to_initialized(
        self, sut: StartupProducer, mock_project_id: str,
        mock_event_bus: MagicMock, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-009 · DRAFT → INITIALIZED · 写 meta/created.json · 发 project_activated。"""
        sut._mark_draft_with_hash(mock_project_id, "sha256:" + "a" * 64)
        req = ActivateRequest(
            project_id=mock_project_id,
            goal_anchor_hash="sha256:" + "a" * 64,
            user_confirmed=True,
            charter_path=f"projects/{mock_project_id}/chart/HarnessFlowGoal.md",
            stakeholders_path=f"projects/{mock_project_id}/chart/HarnessFlowPrdScope.md",
        )
        resp: ActivateResponse = sut.activate_project_id(req)
        assert resp.state == "INITIALIZED"
        assert resp.project_id == mock_project_id
        assert resp.meta_path.endswith("meta/created.json")
        mock_event_bus.append_event.assert_any_call(
            project_id=mock_project_id, event_type="project_activated",
            payload={"state": "INITIALIZED"},
        )

    def test_TC_L102_L202_010_activate_rechecks_anchor_hash(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-010 · activate 前必重算 anchor_hash 与 manifest 存储值比对通过。"""
        stored = "sha256:" + "b" * 64
        sut._mark_draft_with_hash(mock_project_id, stored)
        sut._set_recompute_hash_result(stored)  # 测试钩子
        req = ActivateRequest(
            project_id=mock_project_id, goal_anchor_hash=stored,
            user_confirmed=True,
            charter_path="x", stakeholders_path="y",
        )
        resp = sut.activate_project_id(req)
        assert resp.state == "INITIALIZED"

    # ========= §6.3 算法 · atomic_write_chart =========

    def test_TC_L102_L202_011_atomic_write_tempfile_then_rename(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-011 · tempfile + fsync + rename · 写后路径存在且无 .tmp 残留。"""
        path = tmp_project_root / f"projects/{mock_project_id}/chart/HarnessFlowGoal.md"
        atomic_write_chart(str(path), "# hello")
        assert path.exists()
        assert not any(p.name.endswith(".tmp") for p in path.parent.iterdir())

    def test_TC_L102_L202_012_atomic_write_post_hash_matches(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-012 · 写后读回 sha256 与期望 sha256(content) 一致 · 否则 E_L102_L202_009。"""
        path = tmp_project_root / f"projects/{mock_project_id}/chart/HarnessFlowGoal.md"
        content = "# hello\n内容"
        atomic_write_chart(str(path), content)
        import hashlib
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert expected == actual

    # ========= §6.4 算法 · compute_anchor_hash =========

    def test_TC_L102_L202_013_compute_anchor_hash_basic(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-013 · goal + scope 拼接后 sha256 · 返回 64 hex。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        (root / "HarnessFlowGoal.md").write_text("# G\ngoal body", encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# S\nscope body", encoding="utf-8")
        h = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        assert isinstance(h, str) and len(h) == 64

    def test_TC_L102_L202_014_anchor_hash_excludes_frontmatter(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-014 · §7.5 规则 · frontmatter 变 hash 不变（只取正文）。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        body = "# G\ngoal body"
        (root / "HarnessFlowGoal.md").write_text(
            f"---\nupdated_at: 2026-01-01\n---\n{body}", encoding="utf-8",
        )
        (root / "HarnessFlowPrdScope.md").write_text("# S\nscope body", encoding="utf-8")
        h1 = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        # 改 frontmatter
        (root / "HarnessFlowGoal.md").write_text(
            f"---\nupdated_at: 2026-04-22\n---\n{body}", encoding="utf-8",
        )
        h2 = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        assert h1 == h2

    def test_TC_L102_L202_015_anchor_hash_idempotent(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-015 · 同内容连续计算 10 次 · hash 完全一致。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        (root / "HarnessFlowGoal.md").write_text("# G\nbody", encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# S\nbody", encoding="utf-8")
        hashes = {compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root)) for _ in range(10)}
        assert len(hashes) == 1

    # ========= §6.5 算法 · recover_draft =========

    def test_TC_L102_L202_016_recover_draft_resume_when_full(
        self, mock_project_id: str, tmp_project_root: Path, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-016 · 崩溃后两份章程 + manifest 全齐 · resume · 重放 s1_ready。"""
        root = tmp_project_root / f"projects/{mock_project_id}"
        (root / "chart").mkdir(parents=True, exist_ok=True)
        (root / "meta").mkdir(parents=True, exist_ok=True)
        (root / "meta" / "state.json").write_text('{"state":"DRAFT"}', encoding="utf-8")
        (root / "chart" / "HarnessFlowGoal.md").write_text("# g", encoding="utf-8")
        (root / "chart" / "HarnessFlowPrdScope.md").write_text("# s", encoding="utf-8")
        (root / "meta" / "project_manifest.yaml").write_text("project_id: x", encoding="utf-8")
        result: RecoveryResult = recover_draft(
            mock_project_id, root_dir=str(tmp_project_root), event_bus=mock_event_bus,
        )
        assert result.action == "resumed"
        mock_event_bus.append_event.assert_called_with(
            project_id=mock_project_id, event_type="s1_ready",
            payload={"recovered": True},
        )

    def test_TC_L102_L202_017_recover_draft_cleans_partial(
        self, mock_project_id: str, tmp_project_root: Path, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-017 · 半成品（只 goal 无 scope）· 清 rmtree · 发 kickoff_rolled_back。"""
        root = tmp_project_root / f"projects/{mock_project_id}"
        (root / "chart").mkdir(parents=True, exist_ok=True)
        (root / "meta").mkdir(parents=True, exist_ok=True)
        (root / "meta" / "state.json").write_text('{"state":"DRAFT"}', encoding="utf-8")
        (root / "chart" / "HarnessFlowGoal.md").write_text("# g", encoding="utf-8")
        # 故意无 scope / 无 manifest
        result = recover_draft(mock_project_id, root_dir=str(tmp_project_root), event_bus=mock_event_bus)
        assert result.action == "rolled_back"
        assert not root.exists()
        mock_event_bus.append_event.assert_called_with(
            project_id=mock_project_id, event_type="kickoff_rolled_back",
            payload={"reason": "partial_draft_found"},
        )

    def test_TC_L102_L202_018_recover_draft_no_op_when_not_started(
        self, mock_project_id: str, tmp_project_root: Path, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-018 · 根本没开始（无 state.json）· no_op · 不动 · 不发事件。"""
        result = recover_draft(mock_project_id, root_dir=str(tmp_project_root), event_bus=mock_event_bus)
        assert result.action == "no_op"
        mock_event_bus.append_event.assert_not_called()

    # ========= 事件顺序 + 入参校验 =========

    def test_TC_L102_L202_019_publish_4_events_in_order(
        self, sut: StartupProducer, mock_project_id: str,
        mock_event_bus: MagicMock, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-019 · 4 事件按顺序 emit · project_created → charter_ready → stakeholders_ready → goal_anchor_hash_locked。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8}, {"template_body": "y", "required_fields": 1},
        ]
        sut.kickoff_create_project(req)
        emitted = [c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert emitted[:4] == [
            "project_created", "charter_ready",
            "stakeholders_ready", "goal_anchor_hash_locked",
        ]

    def test_TC_L102_L202_020_validate_trigger_stage_s1_only(
        self, sut: StartupProducer, make_kickoff_request,
    ) -> None:
        """TC-L102-L202-020 · stage != S1 立即拒 · 返回 err · 不触发任何下游调用。"""
        req = make_kickoff_request(stage="S2")
        resp = sut.kickoff_create_project(req)
        assert resp.status == "err"
        assert "stage" in resp.result.reason.lower()
```

---

## §3 负向用例（每错误码 ≥ 1 · 共 15 条 · 前缀 `E_L102_L202_`）

> 负向路径：`pytest.raises` 或 `status=err/degraded` 断言。
> 被测对象从 `app.l1_02.l2_02.errors` 导入 `KickoffError`（统一抛出类型 · `err_code` 属性承载具体 `E_L102_L202_NNN`）。

```python
# file: tests/l1_02/test_l2_02_kickoff_negative.py
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.l1_02.l2_02.producer import StartupProducer
from app.l1_02.l2_02.algo import (
    produce_kickoff, atomic_write_chart, compute_anchor_hash,
)
from app.l1_02.l2_02.errors import KickoffError
from app.l1_02.l2_02.schemas import (
    KickoffRequest, ActivateRequest, CharterFields, StakeholdersEntry,
)


class TestL2_02_KickoffProducer_Negative:
    """§11 14 条 + §3.6 USER_NOT_CONFIRMED = 15 条错误码 · 每条 ≥ 1。"""

    # E_L102_L202_001 · PID_DUPLICATE
    def test_TC_L102_L202_101_pid_duplicate_retry_once_then_fail(
        self, mock_project_id: str, tmp_project_root: Path,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_event_bus: MagicMock, mock_clock,
    ) -> None:
        """TC-L102-L202-101 · 构造 FS 目录已占用 · 重试 1 次仍冲突 → 抛 E_L102_L202_001。"""
        # 预占两个 pid 目录（模拟极端 UUIDv7 碰撞 + retry 也碰撞）
        with patch("app.l1_02.l2_02.algo.exists_project", return_value=True):
            with pytest.raises(KickoffError) as exc:
                produce_kickoff(
                    user_utterance="x", brainstorm=mock_brainstorm_client,
                    template=mock_template_engine, event_bus=mock_event_bus,
                    clock=mock_clock, project_root=str(tmp_project_root),
                )
            assert exc.value.err_code == "E_L102_L202_001"

    # E_L102_L202_002 · USER_NOT_CONFIRMED
    def test_TC_L102_L202_102_activate_without_user_confirm_rejected(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-102 · activate 入参 user_confirmed=false → E_L102_L202_002 · 不改 state。"""
        sut._mark_draft_with_hash(mock_project_id, "sha256:" + "a" * 64)
        req = ActivateRequest(
            project_id=mock_project_id, goal_anchor_hash="sha256:" + "a" * 64,
            user_confirmed=False, charter_path="x", stakeholders_path="y",
        )
        with pytest.raises(KickoffError) as exc:
            sut.activate_project_id(req)
        assert exc.value.err_code == "E_L102_L202_002"
        # 状态仍是 DRAFT
        assert sut._read_state(mock_project_id) == "DRAFT"

    # E_L102_L202_003 · GOAL_MISSING_SECTIONS
    def test_TC_L102_L202_103_goal_missing_fields_triggers_degrade(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-103 · 8 字段缺 authority → degrade 补占位 · flag=clarification_incomplete。"""
        charter = CharterFields(
            title="T", purpose="P 够 10 字长够长够长",
            scope={"in_scope": ["a"], "out_of_scope": []},
            success_criteria=["s"], constraints=[], risks_initial=[],
            stakeholders_initial=[], authority=None,  # 缺字段
        )
        res = sut.write_goal_doc(
            project_id=mock_project_id, charter_fields=charter,
            template_body="tpl", trim_level="full",
        )
        assert res.wrote_atomic is True
        assert res.degraded_fields == ["authority"]
        assert res.clarification_incomplete is True

    # E_L102_L202_004 · SCOPE_NOT_LOCKED
    def test_TC_L102_L202_104_scope_in_scope_empty_falls_back(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-104 · scope.in_scope=[] → fallback=[user_initial_goal] · status=degraded。"""
        charter = CharterFields(
            title="T", purpose="purpose 10 字 long enough",
            scope={"in_scope": [], "out_of_scope": []},  # 空
            success_criteria=["s"], constraints=[], risks_initial=[],
            stakeholders_initial=[], authority={"approver": "u"},
        )
        res = sut.write_goal_doc(
            project_id=mock_project_id, charter_fields=charter,
            template_body="tpl", trim_level="full",
            user_initial_goal="fallback here",
        )
        assert res.fallback_in_scope == ["fallback here"]
        assert res.clarification_incomplete is True

    # E_L102_L202_005 · TEMPLATE_INVALID
    def test_TC_L102_L202_105_template_frontmatter_invalid(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-105 · L2-07 返 template 无 frontmatter → 抛 E_L102_L202_005 · ABORTED。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.return_value = {
            "template_body": "no frontmatter body", "required_fields": 8,
        }
        with pytest.raises(KickoffError) as exc:
            sut.kickoff_create_project(req)
        assert exc.value.err_code == "E_L102_L202_005"

    # E_L102_L202_006 · CLARIFICATION_EXCEEDED
    def test_TC_L102_L202_106_clarification_exceeds_3_rounds_degrades(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-106 · brainstorming 3 轮未 confirmed → degrade minimal · status=degraded（非 err）。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.return_value = {
            "rounds": 3, "is_confirmed": False, "slots": {"title": "X"},
        }
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 2}, {"template_body": "y", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        assert resp.status == "degraded"
        assert resp.result.clarification_incomplete is True
        assert resp.result.clarification_rounds == 3

    # E_L102_L202_007 · STATE_NOT_DRAFT
    def test_TC_L102_L202_107_activate_when_state_not_draft(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-107 · 已 INITIALIZED 重复 activate → E_L102_L202_007。"""
        sut._mark_draft_with_hash(mock_project_id, "sha256:" + "a" * 64)
        sut._force_state(mock_project_id, "INITIALIZED")
        req = ActivateRequest(
            project_id=mock_project_id, goal_anchor_hash="sha256:" + "a" * 64,
            user_confirmed=True, charter_path="x", stakeholders_path="y",
        )
        with pytest.raises(KickoffError) as exc:
            sut.activate_project_id(req)
        assert exc.value.err_code == "E_L102_L202_007"

    # E_L102_L202_008 · CHART_ALREADY_EXISTS
    def test_TC_L102_L202_108_atomic_write_refuses_overwrite(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-108 · 目标 chart 路径已存在 · 第二次写 → E_L102_L202_008（O_EXCL）。"""
        path = tmp_project_root / f"projects/{mock_project_id}/chart/HarnessFlowGoal.md"
        atomic_write_chart(str(path), "# v1")
        with pytest.raises(KickoffError) as exc:
            atomic_write_chart(str(path), "# v2")
        assert exc.value.err_code == "E_L102_L202_008"
        assert path.read_text(encoding="utf-8") == "# v1"  # 未被覆盖

    # E_L102_L202_009 · POST_WRITE_HASH_MISMATCH
    def test_TC_L102_L202_109_post_write_hash_mismatch_raises(
        self, mock_project_id: str, tmp_project_root: Path, monkeypatch,
    ) -> None:
        """TC-L102-L202-109 · rename 后读回 sha256 != 预期 → E_L102_L202_009（FS 瞬时篡改）。"""
        path = tmp_project_root / f"projects/{mock_project_id}/chart/HarnessFlowGoal.md"
        # 注入 "读后篡改" 模拟 · 让 post_write 检查不通过
        import app.l1_02.l2_02.algo as algo
        monkeypatch.setattr(algo, "sha256_file", lambda _p: "00" * 32)
        with pytest.raises(KickoffError) as exc:
            atomic_write_chart(str(path), "content")
        assert exc.value.err_code == "E_L102_L202_009"

    # E_L102_L202_010 · PM14_OWNERSHIP_VIOLATION
    def test_TC_L102_L202_110_activate_called_from_non_l2_01(
        self, sut: StartupProducer, mock_project_id: str, monkeypatch,
    ) -> None:
        """TC-L102-L202-110 · 非 L2-01 调 activate（如 L2-03 跨层直调）→ E_L102_L202_010（PM-14 所有权）。"""
        sut._mark_draft_with_hash(mock_project_id, "sha256:" + "a" * 64)
        import app.l1_02.l2_02.algo as algo
        monkeypatch.setattr(algo, "is_called_from_L2_01", lambda: False)
        req = ActivateRequest(
            project_id=mock_project_id, goal_anchor_hash="sha256:" + "a" * 64,
            user_confirmed=True, charter_path="x", stakeholders_path="y",
        )
        with pytest.raises(KickoffError) as exc:
            sut.activate_project_id(req)
        assert exc.value.err_code == "E_L102_L202_010"

    # E_L102_L202_011 · ANCHOR_HASH_MISMATCH
    def test_TC_L102_L202_111_anchor_hash_mismatch_on_activate(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-111 · activate 前重算 hash ≠ manifest 存储 → E_L102_L202_011。"""
        sut._mark_draft_with_hash(mock_project_id, "sha256:" + "a" * 64)
        sut._set_recompute_hash_result("sha256:" + "b" * 64)  # 故意不一致
        req = ActivateRequest(
            project_id=mock_project_id, goal_anchor_hash="sha256:" + "a" * 64,
            user_confirmed=True, charter_path="x", stakeholders_path="y",
        )
        with pytest.raises(KickoffError) as exc:
            sut.activate_project_id(req)
        assert exc.value.err_code == "E_L102_L202_011"

    # E_L102_L202_012 · CROSS_PROJECT_PATH
    def test_TC_L102_L202_112_cross_project_path_refused(
        self, tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-112 · 传入非 projects/<pid>/ 前缀路径 → E_L102_L202_012 · IC-L2-07 广播。"""
        bad = tmp_project_root / "elsewhere" / "HarnessFlowGoal.md"
        with pytest.raises(KickoffError) as exc:
            atomic_write_chart(str(bad), "# x")
        assert exc.value.err_code == "E_L102_L202_012"

    # E_L102_L202_013 · ATOMIC_WRITE_FAILED
    def test_TC_L102_L202_113_atomic_write_io_error_retries_then_fails(
        self, mock_project_id: str, tmp_project_root: Path, monkeypatch,
    ) -> None:
        """TC-L102-L202-113 · os.rename 连续 2 次失败 → 重试耗尽 · E_L102_L202_013。"""
        path = tmp_project_root / f"projects/{mock_project_id}/chart/HarnessFlowGoal.md"
        import app.l1_02.l2_02.algo as algo
        calls = {"n": 0}
        def _bad_rename(a: str, b: str) -> None:
            calls["n"] += 1
            raise OSError("disk full")
        monkeypatch.setattr(algo.os, "rename", _bad_rename)
        with pytest.raises(KickoffError) as exc:
            atomic_write_chart(str(path), "x")
        assert exc.value.err_code == "E_L102_L202_013"
        assert calls["n"] >= 2  # 至少重试 2 次

    # E_L102_L202_014 · GOAL_ANCHOR_TAMPERING
    def test_TC_L102_L202_114_goal_anchor_tampering_on_recheck(
        self, sut: StartupProducer, mock_project_id: str,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-114 · 外部篡改章程后重算 hash 不一致 → E_L102_L202_014（IC-L2-07 critical）。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        (root / "HarnessFlowGoal.md").write_text("# original", encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# s", encoding="utf-8")
        original = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        # 外部篡改
        (root / "HarnessFlowGoal.md").write_text("# tampered", encoding="utf-8")
        with pytest.raises(KickoffError) as exc:
            sut._verify_anchor_not_tampered(mock_project_id, stored_hash=original)
        assert exc.value.err_code == "E_L102_L202_014"

    # E_L102_L202_015 · BRAINSTORM_SUBAGENT_FAILED
    def test_TC_L102_L202_115_brainstorm_crash_retry_then_degrade(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-115 · brainstorm 第一次崩 + 第二次崩 → 记 E_L102_L202_015 · 走 degrade minimal。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.side_effect = [
            TimeoutError("LLM timeout"), TimeoutError("LLM timeout again"),
        ]
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 2}, {"template_body": "y", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        assert resp.status == "degraded"
        assert "E_L102_L202_015" in resp.result.degrade_trace
        assert resp.result.clarification_incomplete is True
```

---

## §4 IC-XX 契约集成测试（join ≥ 3 · PM-14 强验证）

> ≥ 3 个 join test · mock 对端（L2-01 / L2-07 / L1-05 / L1-06 / L1-09）· 断言 IC payload 结构 + 方向契合 `integration/ic-contracts.md` + 本 L2 §3.7 IC 映射。
> **PM-14 核心**：activate 前 IC-17 approve 必已到；project_id 在 IC-09 `project_created` 事件之后其他 IC 才认它存在。

```python
# file: tests/l1_02/test_l2_02_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_02.l2_02.producer import StartupProducer
from app.l1_02.l2_02.schemas import ActivateRequest


class TestL2_02_ICContracts:
    """ic-contracts.md + §3.7 IC 映射的契约级断言。"""

    # IC-L2-01 · 被调（L2-01 → L2-02）
    def test_TC_L102_L202_201_ic_l2_01_trigger_payload(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-201 · IC-L2-01 入参必含 trigger_id / stage=S1 / user_initial_goal / caller_l2=L2-01。"""
        req = make_kickoff_request(
            trigger_id="t-1", stage="S1", caller_l2="L2-01",
            user_initial_goal="一句话需求",
        )
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8},
            {"template_body": "y", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        assert resp.status == "ok"
        assert resp.trigger_id == "t-1"
        assert resp.latency_ms > 0

    # IC-L2-02 · 发起（L2-02 → L2-07） join L2-07
    def test_TC_L102_L202_202_ic_l2_02_request_template_twice(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-202 · IC-L2-02 · 每份章程 1 次 render_template · 共 2 次 · payload 含 doc_type + trim_level。"""
        req = make_kickoff_request(trim_level="full")
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "goal tpl", "required_fields": 8},
            {"template_body": "scope tpl", "required_fields": 1},
        ]
        sut.kickoff_create_project(req)
        assert mock_template_engine.render_template.call_count == 2
        args0 = mock_template_engine.render_template.call_args_list[0].kwargs
        args1 = mock_template_engine.render_template.call_args_list[1].kwargs
        assert args0["doc_type"] == "charter"
        assert args1["doc_type"] == "stakeholders"
        assert args0["trim_level"] == "full"

    # IC-05 · 发起（L2-02 → L1-05） join brainstorming
    def test_TC_L102_L202_203_ic_05_delegate_brainstorming_payload(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-203 · IC-05 · subagent=brainstorming · goal=clarify_intent · max_rounds=3 · timeout。"""
        req = make_kickoff_request(user_initial_goal="one shot")
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8},
            {"template_body": "y", "required_fields": 1},
        ]
        sut.kickoff_create_project(req)
        mock_brainstorm_client.invoke.assert_called_once()
        kw = mock_brainstorm_client.invoke.call_args.kwargs
        assert kw["subagent"] == "brainstorming"
        assert kw["goal"] == "clarify_intent"
        assert kw["max_rounds"] == 3
        assert kw["timeout_s"] >= 120

    # IC-06 · 发起（L2-02 → L1-06 · 可选）
    def test_TC_L102_L202_204_ic_06_kb_read_only_in_full_trim(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_kb_client: MagicMock,
    ) -> None:
        """TC-L102-L202-204 · IC-06 kb_read 仅 trim_level=full 且 KB 非空时调 · minimal 不调。"""
        req_full = make_kickoff_request(trim_level="full")
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8},
            {"template_body": "y", "required_fields": 1},
        ] * 2
        mock_kb_client.kb_read.return_value = {"top_k_examples": []}
        sut.kickoff_create_project(req_full)
        mock_kb_client.kb_read.assert_called_once()
        # minimal 时不调
        mock_kb_client.kb_read.reset_mock()
        req_min = make_kickoff_request(trim_level="minimal", trigger_id="t-min")
        sut.kickoff_create_project(req_min)
        mock_kb_client.kb_read.assert_not_called()

    # IC-09 · 发起（L2-02 → L1-09） PM-14 核心 · project_id 激活主路径
    def test_TC_L102_L202_205_ic_09_4_events_payload_pm14(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-205 · IC-09 · 4 事件 payload 必含 project_id · 顺序严格 · PM-14 首个 project_created 带 state=DRAFT。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8},
            {"template_body": "y", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        pid = resp.result.project_id
        ev_list = mock_event_bus.append_event.call_args_list
        assert len(ev_list) >= 4
        for c in ev_list:
            assert c.kwargs["project_id"] == pid
        # project_created 必带 state=DRAFT + created_by=L2-02（PM-14 硬约束）
        first = ev_list[0].kwargs
        assert first["event_type"] == "project_created"
        assert first["payload"]["state"] == "DRAFT"
        assert first["payload"]["created_by"] == "L2-02"

    # IC-L2-05 · 回调（L2-02 → L2-01）
    def test_TC_L102_L202_206_ic_l2_05_s1_ready_bundle_to_l2_01(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_l2_01_client: MagicMock,
    ) -> None:
        """TC-L102-L202-206 · S1_ready bundle 回 L2-01 · 含 charter_path / stakeholders_path / hash / events_published。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8},
            {"template_body": "y", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        bundle = resp.result
        assert bundle.charter_path and bundle.stakeholders_path
        assert bundle.goal_anchor_hash.startswith("sha256:")
        assert len(bundle.events_published) == 4

    # IC-17 · 间接接收（via L2-01 · user approve）· 驱动 activate
    def test_TC_L102_L202_207_ic_17_user_intervene_approve_unlocks_activate(
        self, sut: StartupProducer, mock_project_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-207 · IC-17 user_intervene(approve) 经 L2-01 中转 · 本 L2 activate 接受 user_confirmed=true。"""
        sut._mark_draft_with_hash(mock_project_id, "sha256:" + "a" * 64)
        # 模拟 L2-01 转发后 · 本 L2 收到 activate
        req = ActivateRequest(
            project_id=mock_project_id, goal_anchor_hash="sha256:" + "a" * 64,
            user_confirmed=True,
            charter_path="x", stakeholders_path="y",
        )
        resp = sut.activate_project_id(req)
        assert resp.state == "INITIALIZED"
        # PM-14 激活事件发出
        mock_event_bus.append_event.assert_any_call(
            project_id=mock_project_id, event_type="project_activated",
            payload={"state": "INITIALIZED"},
        )
```

---

## §5 性能 SLO 用例（§12 对标 · `@pytest.mark.perf` 标记）

> §12.1 9 项 SLO 指标 · 本节覆盖 ≥ 4 项（章程落盘 / anchor_hash 计算 / 4 事件组合 / activate）· 其余由更高层 perf 回归脚本覆盖。
> 采用 100 次采样 · numpy / statistics 计算 P95 · CI 若 P95 超标则 fail。

```python
# file: tests/l1_02/test_l2_02_slo.py
from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest
from unittest.mock import MagicMock

from app.l1_02.l2_02.producer import StartupProducer
from app.l1_02.l2_02.algo import (
    atomic_write_chart, compute_anchor_hash,
)
from app.l1_02.l2_02.schemas import ActivateRequest


@pytest.mark.perf
class TestL2_02_SLO:
    """§12.1 SLO 对齐 · 本地单机基线 · 生产回归须 ≥ P95 通过。"""

    def test_TC_L102_L202_301_atomic_write_p95_le_200ms(
        self, tmp_project_root: Path, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-301 · 单份章程 atomic_write_chart · P95 ≤ 200ms（100 采样）。"""
        durations_ms: list[float] = []
        content = "# title\n" + ("body line\n" * 20)
        for i in range(100):
            path = tmp_project_root / f"projects/{mock_project_id}-{i}/chart/HarnessFlowGoal.md"
            t0 = time.perf_counter_ns()
            atomic_write_chart(str(path), content)
            durations_ms.append((time.perf_counter_ns() - t0) / 1e6)
        p95 = statistics.quantiles(durations_ms, n=20)[18]
        assert p95 <= 200.0, f"atomic_write P95={p95:.1f}ms > 200ms SLO"

    def test_TC_L102_L202_302_anchor_hash_p95_le_30ms(
        self, tmp_project_root: Path, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-302 · compute_anchor_hash · P95 ≤ 30ms（100 采样 · 2 份 2KB md）。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        (root / "HarnessFlowGoal.md").write_text("# G\n" + ("x" * 2048), encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# S\n" + ("y" * 2048), encoding="utf-8")
        durations_ms: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter_ns()
            compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
            durations_ms.append((time.perf_counter_ns() - t0) / 1e6)
        p95 = statistics.quantiles(durations_ms, n=20)[18]
        assert p95 <= 30.0, f"anchor_hash P95={p95:.1f}ms > 30ms SLO"

    def test_TC_L102_L202_303_four_events_bundle_p95_le_180ms(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-303 · 4 事件 IC-09 组合 · P95 ≤ 180ms（20 次组合采样）。"""
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "x", "required_fields": 8},
            {"template_body": "y", "required_fields": 1},
        ] * 20
        durations_ms: list[float] = []
        for i in range(20):
            req = make_kickoff_request(trigger_id=f"t-{i}")
            mock_event_bus.append_event.reset_mock()
            t0 = time.perf_counter_ns()
            sut.kickoff_create_project(req)
            # 采样 4 事件 emit 段（SUT 暴露段计时钩子 · 生产环境由 Prometheus 采）
            seg = sut._last_emit_segment_ms()
            durations_ms.append(seg)
        p95 = statistics.quantiles(durations_ms, n=20)[18]
        assert p95 <= 180.0, f"4-events bundle P95={p95:.1f}ms > 180ms SLO"

    def test_TC_L102_L202_304_activate_p95_le_60ms(
        self, sut: StartupProducer, mock_project_id: str,
    ) -> None:
        """TC-L102-L202-304 · activate_project_id · P95 ≤ 60ms（50 采样 · 构造 DRAFT 池）。"""
        durations_ms: list[float] = []
        for i in range(50):
            pid = f"{mock_project_id}-{i}"
            sut._mark_draft_with_hash(pid, "sha256:" + "a" * 64)
            sut._set_recompute_hash_result("sha256:" + "a" * 64)
            req = ActivateRequest(
                project_id=pid, goal_anchor_hash="sha256:" + "a" * 64,
                user_confirmed=True, charter_path="x", stakeholders_path="y",
            )
            t0 = time.perf_counter_ns()
            sut.activate_project_id(req)
            durations_ms.append((time.perf_counter_ns() - t0) / 1e6)
        p95 = statistics.quantiles(durations_ms, n=20)[18]
        assert p95 <= 60.0, f"activate P95={p95:.1f}ms > 60ms SLO"
```

---

## §6 端到端 e2e 场景（2 张完整 GWT）

> e2e 范围：从用户一句话输入 → 经 L2-01 → 本 L2 → IC-L2-02 模板 + IC-05 brainstorming + IC-09 事件 → S1 Gate → IC-17 approve → activate(`state=INITIALIZED`)。
> 下列两张对应 tech-design §5.1 P0 主干 + §5.2 P1 回退。

### §6.1 E2E GWT · S1 Kickoff 完整成功链路（对标 §5.1 P0）

**Given**：

- 用户输入：`"做一个 todo 应用"`
- `trim_level=full`
- L1-05 brainstorming 2 轮收敛（`is_confirmed=true`）
- L2-07 模板引擎正常返回 2 份章程模板（含 frontmatter）
- IC-09 EventBus 可用 · L1-06 KB 无历史 pattern（kb_read 返 empty）

**When**：

- L2-01 调 `IC-L2-01 trigger_stage_production(stage=S1, user_initial_goal, trim_level=full)`
- 本 L2 依次执行：
  1. `_validate_trigger` → 2. `_invoke_brainstorming` → 3. `generate_project_id` →
  4. `render_template(goal)` + `write_goal_doc` → 5. `render_template(scope)` + `write_scope_doc` →
  6. `compute_anchor_hash` + `write_manifest` → 7. `publish 4 events` → 8. `return KickoffSuccess`
- L2-01 收 `S1_ready` bundle → `IC-16 push_stage_gate_card` → 用户点 Go →
  `IC-17 user_intervene(approve)` → L2-01 调 `activate_project_id(user_confirmed=true)`

**Then**：

- `resp.status == "ok"` · `resp.result.clarification_incomplete is False`
- `projects/<pid>/chart/HarnessFlowGoal.md` + `HarnessFlowPrdScope.md` 两文件存在且不可覆盖
- `projects/<pid>/meta/project_manifest.yaml` 含 `goal_anchor_hash` 且重算一致
- IC-09 4 事件按顺序：`project_created → charter_ready → stakeholders_ready → goal_anchor_hash_locked`
- 最终 `projects/<pid>/meta/state.json.state == "INITIALIZED"`
- `projects/<pid>/meta/created.json` 写入 `activated_at` ISO-8601 时间戳
- `project_activated` 事件发出 · state=INITIALIZED

```python
# file: tests/l1_02/test_l2_02_e2e.py
from __future__ import annotations

from pathlib import Path
import pytest
from unittest.mock import MagicMock

from app.l1_02.l2_02.producer import StartupProducer
from app.l1_02.l2_02.schemas import ActivateRequest


class TestL2_02_E2E:
    """§6 e2e 场景 · 端到端 S1 Kickoff 全链路。"""

    def test_TC_L102_L202_401_e2e_s1_kickoff_full_success_to_initialized(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_event_bus: MagicMock, mock_l2_01_client: MagicMock,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-401 · 对标 §5.1 P0 主干 · 全链路通过。"""
        # Given · 用户一句话 + 2 轮澄清 + 模板正常
        req = make_kickoff_request(
            user_initial_goal="做一个 todo 应用", trim_level="full",
        )
        mock_brainstorm_client.invoke.return_value = {
            "rounds": 2, "is_confirmed": True,
            "slots": {
                "title": "Todo App", "purpose": "个人任务管理 10 字",
                "in_scope": ["增删改查"], "success_criteria": ["7 日留存 30%"],
            },
        }
        mock_template_engine.render_template.side_effect = [
            {"template_body": "---\ndoc_type: harness-flow-goal\n---\n# {{title}}\n{{purpose}}",
             "required_fields": 8},
            {"template_body": "---\ndoc_type: harness-flow-prd-scope\n---\n# Stakeholders\n",
             "required_fields": 3},
        ]

        # When · L2-01 trigger
        resp = sut.kickoff_create_project(req)

        # Then (阶段 1: S1_ready 产出)
        assert resp.status == "ok"
        pid = resp.result.project_id
        assert resp.result.clarification_incomplete is False
        assert resp.result.events_published == [
            "project_created", "charter_ready",
            "stakeholders_ready", "goal_anchor_hash_locked",
        ]

        # 4 事件按顺序发 IC-09
        emitted = [c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list[:4]]
        assert emitted == [
            "project_created", "charter_ready",
            "stakeholders_ready", "goal_anchor_hash_locked",
        ]
        # PM-14 project_id 已硬锁入第一条事件
        assert mock_event_bus.append_event.call_args_list[0].kwargs["payload"]["state"] == "DRAFT"

        # When (阶段 2: 用户 approve 后 activate)
        sut._set_recompute_hash_result(resp.result.goal_anchor_hash)
        activate_req = ActivateRequest(
            project_id=pid, goal_anchor_hash=resp.result.goal_anchor_hash,
            user_confirmed=True,
            charter_path=resp.result.charter_path,
            stakeholders_path=resp.result.stakeholders_path,
        )
        act_resp = sut.activate_project_id(activate_req)

        # Then (阶段 2: INITIALIZED)
        assert act_resp.state == "INITIALIZED"
        assert act_resp.meta_path.endswith("meta/created.json")
        mock_event_bus.append_event.assert_any_call(
            project_id=pid, event_type="project_activated",
            payload={"state": "INITIALIZED"},
        )

    def test_TC_L102_L202_402_e2e_s1_kickoff_degraded_then_reject_then_archive(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-402 · 对标 §5.2 P1 回退 · 澄清 3 轮不收敛 → degraded → 用户 reject → draft_archived。"""
        # Given · 澄清 3 轮未收敛
        req = make_kickoff_request(user_initial_goal="too vague")
        mock_brainstorm_client.invoke.return_value = {
            "rounds": 3, "is_confirmed": False,
            "slots": {"title": "?"},  # 字段严重不全
        }
        mock_template_engine.render_template.side_effect = [
            {"template_body": "---\ndoc_type: harness-flow-goal\n---\n# ?", "required_fields": 2},
            {"template_body": "---\ndoc_type: harness-flow-prd-scope\n---\n# x", "required_fields": 1},
        ]

        # When · 走 produce
        resp = sut.kickoff_create_project(req)

        # Then (阶段 1: status=degraded 且 flag 显式)
        assert resp.status == "degraded"
        assert resp.result.clarification_incomplete is True
        pid = resp.result.project_id
        # charter_ready 事件必带 degraded=true
        charter_evt = next(
            c for c in mock_event_bus.append_event.call_args_list
            if c.kwargs["event_type"] == "charter_ready"
        )
        assert charter_evt.kwargs["payload"].get("degraded") is True

        # When (阶段 2: 用户 Gate reject)
        reject_result = sut.archive_draft(
            project_id=pid, reason="需更清晰目标",
        )

        # Then · 章程目录被移到 .draft-archive · project_id 保持 DRAFT
        assert reject_result.archived is True
        assert sut._read_state(pid) == "DRAFT"
        archive_evt = next(
            c for c in mock_event_bus.append_event.call_args_list
            if c.kwargs["event_type"] == "kickoff_draft_archived"
        )
        assert archive_evt.kwargs["payload"]["reason"] == "需更清晰目标"
```

---

## §7 测试 fixture（≥ 5 · conftest.py）

> 汇总 conftest.py 内置的核心 fixture · 供 §2-§9 复用 · 严格 mock 外部 IC 边界 · 不 mock SUT 内部 state。

```python
# file: tests/l1_02/conftest.py
from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.l1_02.l2_02.producer import StartupProducer
from app.l1_02.l2_02.schemas import KickoffRequest


# ========= fixture 1 · mock_project_id（ULID 占位 · p_{uuid-v7}）=========
@pytest.fixture
def mock_project_id() -> str:
    """PM-14 合法 project_id 占位 · 测试级稳定不变。"""
    return "p_01924a0b-1234-7a89-b012-abcdef012345"


# ========= fixture 2 · mock_clock（冻结时间 · 可 advance）=========
class _FrozenClock:
    def __init__(self, t0_ns: int = 1_700_000_000_000_000_000) -> None:
        self._now_ns = t0_ns

    def now_ns(self) -> int:
        return self._now_ns

    def now_iso(self) -> str:
        return "2026-04-22T00:00:00Z"

    def advance_ms(self, ms: int) -> None:
        self._now_ns += ms * 1_000_000


@pytest.fixture
def mock_clock() -> _FrozenClock:
    """冻结时间时钟 · SUT 注入后时间可控（避免 ISO8601 漂移）。"""
    return _FrozenClock()


# ========= fixture 3 · mock_event_bus（IC-09 sink · append-only）=========
@pytest.fixture
def mock_event_bus() -> MagicMock:
    """L1-09 EventBus mock · 捕获 append_event 调用 · payload 可断言。"""
    bus = MagicMock()
    bus.append_event.return_value = {"event_id": "evt-1", "seq": 1}
    return bus


# ========= fixture 4 · mock_ic_payload（构造 IC-L2-01 / ActivateRequest）=========
@pytest.fixture
def make_kickoff_request():
    """IC-L2-01 trigger payload 工厂 · 允许覆盖部分字段。"""
    def _factory(**overrides: Any) -> KickoffRequest:
        base: dict[str, Any] = {
            "trigger_id": "t-default",
            "stage": "S1",
            "user_initial_goal": "做一个应用",
            "trim_level": "full",
            "caller_l2": "L2-01",
            "preexisting_charter_path": None,
            "trace_ctx": {"ts_dispatched_ns": 0, "session_id": "s-1"},
        }
        base.update(overrides)
        return KickoffRequest(**base)
    return _factory


# ========= fixture 5 · mock_template_engine（IC-L2-02 对端）=========
@pytest.fixture
def mock_template_engine() -> MagicMock:
    """L2-07 模板引擎 mock · render_template 可配 side_effect。"""
    te = MagicMock()
    te.render_template.return_value = {
        "template_body": "---\ndoc_type: harness-flow-goal\n---\n# tpl",
        "required_fields": 8,
    }
    return te


# ========= fixture 6 · mock_brainstorm_client（IC-05 对端）=========
@pytest.fixture
def mock_brainstorm_client() -> MagicMock:
    bs = MagicMock()
    bs.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
    return bs


# ========= fixture 7 · mock_kb_client（IC-06 对端）=========
@pytest.fixture
def mock_kb_client() -> MagicMock:
    kb = MagicMock()
    kb.kb_read.return_value = {"top_k_examples": []}
    return kb


# ========= fixture 8 · mock_l2_01_client / mock_l2_07_client（上下游）=========
@pytest.fixture
def mock_l2_01_client() -> MagicMock:
    return MagicMock()


# ========= fixture 9 · tmp_project_root（PM-14 目录隔离 · 每 test 独立 tmp）=========
@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """每 test 独立 tmp 目录 · 避免 cross-test 污染 · PM-14 沙箱化。"""
    root = tmp_path / "workspace"
    root.mkdir()
    return root


# ========= fixture 10 · sut（StartupProducer 组装 · 注入所有 mock）=========
@pytest.fixture
def sut(
    mock_project_id: str,
    mock_clock: _FrozenClock,
    mock_event_bus: MagicMock,
    mock_template_engine: MagicMock,
    mock_brainstorm_client: MagicMock,
    mock_kb_client: MagicMock,
    tmp_project_root: Path,
) -> StartupProducer:
    """SUT 注入全套 mock · 测试级隔离 · project_root 指向 tmp。"""
    return StartupProducer(
        clock=mock_clock,
        event_bus=mock_event_bus,
        template_engine=mock_template_engine,
        brainstorm_client=mock_brainstorm_client,
        kb_client=mock_kb_client,
        project_root=str(tmp_project_root),
    )
```

---

## §8 集成点用例（与兄弟 L2 协作 · join test）

> 本 L2 不能独立产出 · 必须 join L2-07（模板）+ L2-01（Gate）+ L1-05（brainstorming）+ L1-09（EventBus）。
> 本节 4 join case · 均 real SUT + mocked peer · 断言 call order + payload。

```python
# file: tests/l1_02/test_l2_02_integration.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_02.l2_02.producer import StartupProducer


class TestL2_02_IntegrationWithSiblings:
    """§8 集成点 · 本 L2 + L2-07 / L2-01 / L1-05 / L1-09 协作。"""

    def test_TC_L102_L202_501_join_l2_07_template_before_write(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-501 · L2-07 协作 · render_template 调用必先于 atomic_write。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "---\ndoc_type: harness-flow-goal\n---\n# a", "required_fields": 8},
            {"template_body": "---\ndoc_type: harness-flow-prd-scope\n---\n# b", "required_fields": 1},
        ]
        order_log: list[str] = []
        orig_render = mock_template_engine.render_template.side_effect
        def _tpl(*args, **kwargs):
            order_log.append(f"render:{kwargs.get('doc_type')}")
            return orig_render[len(order_log) - 1]
        mock_template_engine.render_template.side_effect = _tpl
        sut._on_atomic_write_hook = lambda p: order_log.append(f"write:{p.split('/')[-1]}")
        sut.kickoff_create_project(req)
        # render:charter 必早于 write:HarnessFlowGoal.md
        assert order_log.index("render:charter") < order_log.index("write:HarnessFlowGoal.md")
        assert order_log.index("render:stakeholders") < order_log.index("write:HarnessFlowPrdScope.md")

    def test_TC_L102_L202_502_join_l2_01_gate_controls_activate(
        self, sut: StartupProducer, mock_project_id: str,
        mock_l2_01_client: MagicMock,
    ) -> None:
        """TC-L102-L202-502 · L2-01 Gate 协作 · activate 必经 L2-01 中转 + user_confirmed=true。"""
        # 直连 activate 未经 L2-01 标记 · 应被 PM-14 所有权校验拒绝（E_L102_L202_010）
        sut._mark_draft_with_hash(mock_project_id, "sha256:" + "a" * 64)
        sut._set_caller_identity("L2-03")  # 伪造 caller（非 L2-01）
        from app.l1_02.l2_02.schemas import ActivateRequest
        from app.l1_02.l2_02.errors import KickoffError
        req = ActivateRequest(
            project_id=mock_project_id, goal_anchor_hash="sha256:" + "a" * 64,
            user_confirmed=True, charter_path="x", stakeholders_path="y",
        )
        with pytest.raises(KickoffError) as exc:
            sut.activate_project_id(req)
        assert exc.value.err_code == "E_L102_L202_010"

    def test_TC_L102_L202_503_join_l1_05_brainstorming_timeout_retry(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-503 · L1-05 brainstorming 首次 timeout · 重试 1 次成功 · 不 degrade。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.side_effect = [
            TimeoutError("slow LLM"),
            {"rounds": 2, "is_confirmed": True, "slots": {"title": "T"}},
        ]
        mock_template_engine.render_template.side_effect = [
            {"template_body": "---\ndoc_type: harness-flow-goal\n---\n# t", "required_fields": 8},
            {"template_body": "---\ndoc_type: harness-flow-prd-scope\n---\n# s", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(req)
        assert resp.status == "ok"
        assert mock_brainstorm_client.invoke.call_count == 2

    def test_TC_L102_L202_504_join_l1_09_event_bus_degraded_audit_buffers(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-504 · L1-09 协作 · IC-09 首 3 次失败 · 进 DEGRADED_AUDIT buffer · 最终 flush 成功。"""
        req = make_kickoff_request()
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "---\ndoc_type: harness-flow-goal\n---\n# t", "required_fields": 8},
            {"template_body": "---\ndoc_type: harness-flow-prd-scope\n---\n# s", "required_fields": 1},
        ]
        call_n = {"n": 0}
        def _flaky(**kw):
            call_n["n"] += 1
            if call_n["n"] <= 3:
                raise OSError("bus down")
            return {"event_id": "e", "seq": call_n["n"]}
        mock_event_bus.append_event.side_effect = _flaky
        resp = sut.kickoff_create_project(req)
        assert resp.status in ("ok", "degraded")  # 最终能恢复
        assert sut.last_audit_state() in ("DRAFT_READY", "DEGRADED_AUDIT")
```

---

## §9 边界 / edge case（≥ 4 · 并发 / 崩溃 / 冲突 / 篡改 / TTL）

> 覆盖面：PID 冲突重试 / 并发 kickoff 同 pid 锁 / recover_draft 从 CHART_WRITING 崩溃恢复 / 章程被外部修改 / DRAFT TTL 清理。

```python
# file: tests/l1_02/test_l2_02_edge.py
from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.l1_02.l2_02.producer import StartupProducer
from app.l1_02.l2_02.algo import produce_kickoff, recover_draft, compute_anchor_hash
from app.l1_02.l2_02.errors import KickoffError


class TestL2_02_EdgeCases:
    """§9 边界 · PM-14 + 并发 + 崩溃恢复 + 篡改 + TTL。"""

    def test_TC_L102_L202_601_pid_duplicate_retry_once_succeeds(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
        monkeypatch,
    ) -> None:
        """TC-L102-L202-601 · PID 第一次命中已存在 · 重试 1 次成功 · 最终返 KickoffSuccess。"""
        # 第一次 exists_project=True（冲突）· 第二次 False（成功）
        import app.l1_02.l2_02.algo as algo
        calls = {"n": 0}
        def _exists(pid: str) -> bool:
            calls["n"] += 1
            return calls["n"] == 1
        monkeypatch.setattr(algo, "exists_project", _exists)
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "---\ndoc_type: harness-flow-goal\n---\n# a", "required_fields": 8},
            {"template_body": "---\ndoc_type: harness-flow-prd-scope\n---\n# b", "required_fields": 1},
        ]
        resp = sut.kickoff_create_project(make_kickoff_request())
        assert resp.status == "ok"
        assert calls["n"] >= 2

    def test_TC_L102_L202_602_concurrent_kickoff_same_project_lock_blocks(
        self, sut: StartupProducer, make_kickoff_request,
        mock_brainstorm_client: MagicMock, mock_template_engine: MagicMock,
    ) -> None:
        """TC-L102-L202-602 · 并发 2 次 produce_kickoff 同 trigger_id · 仅 1 次落盘 · 另 1 次排队（等结果）。"""
        req = make_kickoff_request(trigger_id="t-concurrent")
        mock_brainstorm_client.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        mock_template_engine.render_template.side_effect = [
            {"template_body": "---\ndoc_type: harness-flow-goal\n---\n# a", "required_fields": 8},
            {"template_body": "---\ndoc_type: harness-flow-prd-scope\n---\n# b", "required_fields": 1},
        ]
        results: list = []
        def _worker():
            results.append(sut.kickoff_create_project(req))
        ts = [threading.Thread(target=_worker) for _ in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert len(results) == 2
        # 两次结果 project_id 相同（幂等 per-trigger_id lock）
        assert results[0].result.project_id == results[1].result.project_id
        # 模板只拉 2 次（非 4 次）· 幂等保证
        assert mock_template_engine.render_template.call_count == 2

    def test_TC_L102_L202_603_recover_draft_from_chart_writing_crash(
        self, mock_project_id: str, tmp_project_root: Path,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L102-L202-603 · CHART_WRITING 中途崩溃 · 残留 .tmp · 启动 recover_draft 扫清 · rolled_back。"""
        root = tmp_project_root / f"projects/{mock_project_id}"
        (root / "chart").mkdir(parents=True, exist_ok=True)
        (root / "meta").mkdir(parents=True, exist_ok=True)
        (root / "meta" / "state.json").write_text('{"state":"DRAFT"}', encoding="utf-8")
        # 模拟 tempfile 残留 + scope 未写
        (root / "chart" / "HarnessFlowGoal.md.tmp.123.abc").write_text("partial", encoding="utf-8")
        result = recover_draft(
            mock_project_id, root_dir=str(tmp_project_root), event_bus=mock_event_bus,
        )
        assert result.action == "rolled_back"
        assert not root.exists()
        mock_event_bus.append_event.assert_called_with(
            project_id=mock_project_id, event_type="kickoff_rolled_back",
            payload={"reason": "partial_draft_found"},
        )

    def test_TC_L102_L202_604_external_chart_edit_detected_on_recheck(
        self, sut: StartupProducer, mock_project_id: str,
        tmp_project_root: Path,
    ) -> None:
        """TC-L102-L202-604 · 章程 md 被外部修改 · 重算 hash 与 manifest 存储不一致 · E_L102_L202_014。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        (root / "HarnessFlowGoal.md").write_text("# original goal", encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# original scope", encoding="utf-8")
        h_before = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        # 外部篡改（比如用户手改章程）
        (root / "HarnessFlowGoal.md").write_text("# tampered goal", encoding="utf-8")
        with pytest.raises(KickoffError) as exc:
            sut._verify_anchor_not_tampered(mock_project_id, stored_hash=h_before)
        assert exc.value.err_code == "E_L102_L202_014"

    def test_TC_L102_L202_605_draft_cleanup_after_24h_ttl(
        self, sut: StartupProducer, mock_project_id: str,
        tmp_project_root: Path, mock_clock,
    ) -> None:
        """TC-L102-L202-605 · DRAFT 超 24h 未 activate · draft_cleanup 任务清 · 目录删 + 事件发。"""
        # 构造 draft_at 24h+ 之前
        root = tmp_project_root / f"projects/{mock_project_id}"
        (root / "meta").mkdir(parents=True, exist_ok=True)
        (root / "meta" / "state.json").write_text(
            '{"state":"DRAFT","draft_at":"2026-04-20T00:00:00Z"}',
            encoding="utf-8",
        )
        # 当前时间：2026-04-22（48h 后）· > 24h TTL
        swept = sut.run_draft_cleanup(ttl_hours=24)
        assert mock_project_id in swept
        assert not root.exists()
```

---

## §10 总结 · 可追溯覆盖

- **§3 方法 4 条** / **§6 算法 5 条** 全部 ≥ 1 正向用例（§2）· 共 20 正向。
- **§11 错误码 15 条**（前缀统一 `E_L102_L202_`）全部 ≥ 1 负向用例（§3）· 共 15 负向。
- **IC 触点 7 条**（IC-L2-01 / IC-L2-02 / IC-05 / IC-06 / IC-09 / IC-L2-05 / IC-17）全部 ≥ 1 契约用例（§4）。
- **SLO 4 指标** 含 `@pytest.mark.perf`（§5）· 对齐 §12.1。
- **e2e 2 张 GWT**（§6）对标 §5.1 P0 + §5.2 P1。
- **fixture 10 项**（§7）· 覆盖 `mock_project_id / mock_clock / mock_event_bus / mock_ic_payload / mock_template_engine / mock_brainstorm_client / mock_kb_client / mock_l2_01_client / tmp_project_root / sut`。
- **集成 4 条**（§8）· PM-14 权属 + Gate + brainstorming + EventBus。
- **边界 5 条**（§9）· PID 重试 / 并发锁 / 崩溃恢复 / 篡改检测 / TTL 清理。

本文档与 3-1 `L2-02-启动阶段产出器.md` §3/§6/§11/§12/§13 双向可追溯 · PM-14 project_id 生成 + 激活唯一入口在负向（§3 TC-110）+ 集成（§8 TC-502）+ e2e（§6 TC-401）三处强校验。

---

*— L1-02 L2-02 启动阶段产出器 · TDD 测试用例 · depth-B (v1.0) · §0-§9 全段完结 —*
