---
doc_id: tests-L1-04-L2-05-S4 执行驱动器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-05-S4 执行驱动器.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-04 L2-05 S4 执行驱动器 · TDD 测试用例

> 基于 3-1 L2-05 §3（10 个 IC 触点 + `execute_wp` 主方法 + 8 个 orchestrator 方法 + 6 个 domain service）+ §11 错误码（24 项 · 跨 L204/L205/L105/L106/L108 前缀）+ §12 SLO（延迟 / 吞吐 / 资源）+ §13 TC ID 矩阵（60+ 占位）驱动。
> TC ID 统一格式：`TC-L104-L205-NNN`（L1-04 下 L2-05，三位流水号 · 001-099 正向按方法分段 / 1xx-3xx 负向按错误码前缀 / 4xx IC 契约 / 5xx SLO / 6xx e2e / 7xx fixture 自检 / 8xx 集成点 / 9xx 边界）。
> pytest + Python 3.11+ 类型注解；`class TestL2_05_S4ExecutionDriver` 组织正向；负向 / IC / perf / e2e / 集成 / 边界各自独立 `class`；错误码前缀按 3-1 §11.1 原样保留 `E_L205_L204_` / `E_L205_L205_` / `E_L205_L105_` / `E_L205_L106_` / `E_L205_L108_` / `E_L205_SUPERVISOR_` / `E_L205_INTERNAL_`。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus / mock worktree / mock wal / mock skill invoker）
- [x] §8 集成点用例（与兄弟 L2 协作 · L2-03 / L2-04 / L2-06 / L2-07）
- [x] §9 边界 / edge case（空/超大/并发/崩溃/超时/资源耗尽）

---

## §1 覆盖度索引

> 每个 §3 IC 触点 / §2.1 orchestrator 方法 / §2.6 domain service 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型（§2.1 + §2.6 + §3）

| 方法（3-1 出处） | TC ID | 覆盖类型 | 错误码 / IC |
|---|---|---|---|
| `on_artifacts_ready()` · §2.1 + §6.1 · 入口 event handler | TC-L104-L205-001 | integration | IC-L2-04 / IC-09 |
| `on_artifacts_ready()` · §6.1 · 多 WP 扇出并发 | TC-L104-L205-002 | integration | IC-L2-04 |
| `execute_wp()` · §2.1 + §6.2 · attempt=0 首跑绿 | TC-L104-L205-003 | integration | IC-09 / IC-16 |
| `execute_wp()` · §6.2 · 本地 coherence 正确 | TC-L104-L205-011 | unit | — |
| `execute_wp()` · §6.2 · self-repair 1 次即绿 | TC-L104-L205-012 | integration | IC-04 / IC-09 |
| `execute_wp()` · §6.2 · 幂等 · 已完成 WP 直接返回 | TC-L104-L205-039 | unit | — |
| `run_red_green_loop()` · §2.1 + §6.3 · 首次直接绿（skeletons 为空） | TC-L104-L205-013 | unit | — |
| `run_red_green_loop()` · §6.3 · 1 次 fix 后绿 | TC-L104-L205-014 | unit | — |
| `invoke_self_repair()` · §2.1 + §6.3 · attempt=1 成功 | TC-L104-L205-015 | unit | IC-06 |
| `invoke_self_repair()` · §6.3 · attempt=3 硬锁耗尽 | TC-L104-L205-016 | unit | — |
| `run_predicates()` · §2.1 + §6.5 · 全 pass | TC-L104-L205-020 | unit | — |
| `run_predicates()` · §6.5 · 部分 fail 仍继续 | TC-L104-L205-021 | unit | — |
| `run_predicates()` · §6.5 · whitelist 校验（拒非白名单类型） | TC-L104-L205-022 | unit | — |
| `build_candidate_report()` · §2.1 + §6.7 · 成功路径 | TC-L104-L205-025 | unit | — |
| `build_candidate_report()` · §6.7 · verdict_hint 不是 verdict（no-self-verdict） | TC-L104-L205-026 | unit | — |
| `build_candidate_report()` · §6.7 · exhausted candidate 仍可构建 | TC-L104-L205-027 | unit | — |
| `delegate_verdict()` · §2.1 + §6.6 · 一次成功 | TC-L104-L205-030 | integration | IC-L2-06 |
| `delegate_verdict()` · §6.6 · 3 次重试后降级 standalone | TC-L104-L205-031 | integration | IC-L2-06 |
| `crash_recovery()` · §2.1 + §6.10 · WAL 完整重放 | TC-L104-L205-035 | integration | IC-09 |
| `crash_recovery()` · §6.10 · hash-chain 损坏检测 | TC-L104-L205-036 | unit | — |
| `WorkspaceIsolator.create()` · §2.6.3 + §6.4 | TC-L104-L205-040 | unit | — |
| `WorkspaceIsolator.destroy()` · §6.4 · 资源清理 | TC-L104-L205-041 | unit | — |
| `SkillInvoker.invoke()` · §2.6.4 + §6.9 · 成功 | TC-L104-L205-045 | unit | IC-04 |
| `WALBuffer.append()` + `fsync()` · §2.6.5 + §6.8 | TC-L104-L205-050 | unit | — |
| `WALBuffer.replay_on_crash()` · §6.8 · hash-chain 完整 | TC-L104-L205-051 | unit | — |
| `handle_halt_command()` · §6.12 · scope=wp | TC-L104-L205-055 | integration | IC-14 |
| `handle_halt_command()` · §6.12 · scope=l1_04 | TC-L104-L205-056 | integration | IC-14 |
| `handle_halt_command()` · §6.12 · scope=project | TC-L104-L205-057 | integration | IC-14 |
| `handle_rollback_hint()` · §6.13 · retry_wp | TC-L104-L205-060 | integration | IC-L2-07 |
| `handle_rollback_hint()` · §6.13 · retry_blueprint | TC-L104-L205-061 | integration | IC-L2-07 |
| `handle_rollback_hint()` · §6.13 · escalate_supervisor | TC-L104-L205-062 | integration | IC-L2-07 |
| `handle_probe_health()` · §6.14 · liveness | TC-L104-L205-065 | unit | IC-11 |
| `handle_probe_health()` · §6.14 · wp_progress | TC-L104-L205-066 | unit | IC-11 |
| `detect_stuck_wps()` · §6.15 · stuck 检测 | TC-L104-L205-070 | unit | — |

### §1.2 错误码 × 测试（§3 + §11.1 · 24 项完整枚举）

| 错误码（按 §11.1 原样 · 保留前缀） | TC ID | 方法 / 触发 | 降级等级 |
|---|---|---|---|
| `E_L205_L204_YAML_NOT_FOUND` | TC-L104-L205-101 | `on_artifacts_ready()` · yaml_path 不存在 | REJECTED · 告警上游 |
| `E_L205_L204_YAML_PARSE_FAIL` | TC-L104-L205-102 | `on_artifacts_ready()` · 语法错 | REJECTED |
| `E_L205_L204_MD_NOT_FOUND` | TC-L104-L205-103 | `on_artifacts_ready()` · md_path 不存在 | REJECTED |
| `E_L205_L204_COHERENCE_CHECK_FAIL` | TC-L104-L205-104 | `on_artifacts_ready()` · 本地再校验不一致 | REJECTED + 告警 |
| `E_L205_L205_WP_NOT_FOUND` | TC-L104-L205-105 | `execute_wp()` · wp_id 非法 | 返回 + 上报 |
| `E_L205_L205_WORKSPACE_CREATE_FAIL` | TC-L104-L205-106 | `execute_wp()` · git worktree 错 | 重试 3 次 · HALT_WP |
| `E_L205_L205_SKILL_INVOKE_FAIL` | TC-L104-L205-107 | `execute_wp()` · L1-05 回错 | 算 red · self-repair |
| `E_L205_L205_TEST_RUN_CRASH` | TC-L104-L205-108 | `run_red_green_loop()` · 子进程错 | self-repair |
| `E_L205_L205_SELF_REPAIR_EXHAUSTED` | TC-L104-L205-109 | `invoke_self_repair()` · ≥ 3 次 | candidate 标 exhausted · 委托 L2-06 |
| `E_L205_L205_PREDICATE_RUN_FAIL` | TC-L104-L205-110 | `run_predicates()` · runtime 错 | 标记 · 继续其他 |
| `E_L205_L205_COHERENCE_LOCAL_FAIL` | TC-L104-L205-111 | `execute_wp()` · 本地 coherence 再校验失败 | REJECTED + 告警 |
| `E_L205_L205_WAL_WRITE_FAIL` | TC-L104-L205-112 | `WALBuffer.append()` · 磁盘/权限 | 重试 3 次 · HALT |
| `E_L205_L205_WAL_REPLAY_FAIL` | TC-L104-L205-113 | `crash_recovery()` · WAL 损坏 | HALT · 人工 |
| `E_L205_L205_WP_TIMEOUT` | TC-L104-L205-114 | `execute_wp()` · > 3 min | HALT_WP |
| `E_L205_L205_DELEGATE_VERIFIER_FAIL` | TC-L104-L205-115 | `delegate_verdict()` · L2-06 不可达 | 3 次重试 · 降级 standalone |
| `E_L205_L205_ROLLBACK_PROMPTED` | TC-L104-L205-116 | `handle_rollback_hint()` · verify 失败路由 | 重启 WP（新 attempt） |
| `E_L205_L205_WP_LOCK_TIMEOUT` | TC-L104-L205-117 | `acquire_wp_lock()` · 并发冲突 | 重试或拒绝 |
| `E_L205_L105_SKILL_NOT_FOUND` | TC-L104-L205-120 | `SkillInvoker.invoke()` · 未知 intent | REJECTED |
| `E_L205_L105_SKILL_BUDGET_EXHAUSTED` | TC-L104-L205-121 | `SkillInvoker.invoke()` · 预算耗尽 | self-repair |
| `E_L205_L105_SKILL_TIMEOUT` | TC-L104-L205-122 | `SkillInvoker.invoke()` · 超时 | self-repair |
| `E_L205_L106_KB_UNAVAILABLE` | TC-L104-L205-125 | `kb_recipe_reader.read()` · KB 不可达 | 降级 fallback playbook |
| `E_L205_L108_EVENT_BUS_DOWN` | TC-L104-L205-128 | `event_bus.append_event()` · 故障 | WAL 缓冲 |
| `E_L205_SUPERVISOR_HALT` | TC-L104-L205-130 | `handle_halt_command()` · L1-07 强制 | partial candidate · 委托 |
| `E_L205_INTERNAL_ASSERT_FAILED` | TC-L104-L205-135 | 任意方法 · 内部 bug | 告警 + HALT |

### §1.3 IC 契约 × 测试（§3.1–3.10 · 10 触点）

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-04 `dual_artifact_ready` | L2-04 → L2-05（入站）| TC-L104-L205-401 | 消费方 · payload schema + 驱动触发 |
| `execute_wp` 内部主方法（§3.2）| L2-05 内部 | TC-L104-L205-402 | 覆盖在 §2 正向 |
| IC-09 `append_event` · 10 种事件类型 | L2-05 → L1-09（出站）| TC-L104-L205-403 | 状态转换必写审计 · hash-chain |
| IC-04 `invoke_skill`（§3.4 对 L1-05）| L2-05 → L1-05（出站）| TC-L104-L205-404 | 主动调 · red/green/self_repair intent |
| IC-06 `kb_read`（§3.5 对 L1-06）| L2-05 → L1-06（出站 · 可选）| TC-L104-L205-405 | miss 不 fail · fallback playbook |
| IC-11 `probe_health`（§3.6）| L1-07 → L2-05（入站）| TC-L104-L205-406 | 消费方 · 响应 P95 ≤ 100ms |
| IC-14 `receive_halt_command`（§3.7）| L1-07 → L2-05（入站）| TC-L104-L205-407 | 3 scope 全覆盖 |
| IC-16 `push_stage_gate_card`（§3.8）| L2-05 → L1-05（出站）| TC-L104-L205-408 | UI 展示 · enqueue ≤ 50ms |
| IC-L2-06 `delegate_verify`（§3.9）| L2-05 → L2-06（出站）| TC-L104-L205-409 | 驱动测试用例执行 → 结果回流 · no-self-verdict |
| IC-L2-07 `receive_rollback_hint`（§3.10）| L2-07 → L2-05（入站）| TC-L104-L205-410 | 4 种 rollback_decision |

### §1.4 §12 SLO × 测试

| SLO 维度（§12.1 / §12.2 / §12.3） | 阈值 | TC ID |
|---|---|---|
| 单 WP 总执行 P95（典型 · 50 测试 · 3 predicates）| ≤ 3 min | TC-L104-L205-501 |
| 单 Skill 调用 P95 | ≤ 2 min | TC-L104-L205-502 |
| WAL append + fsync P95 | ≤ 5 ms | TC-L104-L205-503 |
| Worktree 创建 P95 | ≤ 500 ms | TC-L104-L205-504 |
| Predicate 批量执行（20 个）P95 | ≤ 5 s | TC-L104-L205-505 |
| Candidate report 构建 P95 | ≤ 1 s | TC-L104-L205-506 |
| 委托 L2-06 P95 | ≤ 2 s | TC-L104-L205-507 |
| Crash recovery（WAL 重放）P95 | ≤ 10 s | TC-L104-L205-508 |
| Probe health 响应 P95 | ≤ 100 ms | TC-L104-L205-509 |
| Halt command 响应 P95 | ≤ 500 ms | TC-L104-L205-510 |
| 单机并发 WP × 5（吞吐） | WP/min ~ 20 | TC-L104-L205-511 |
| 单 WP 内存峰值 | ≤ 500 MB | TC-L104-L205-512 |

### §1.5 PRD §5.5 GWT 场景 × 测试（prd.md L1-04 §5.5 L2-05）

| PRD 场景 | TC ID | 类别 |
|---|---|---|
| 正向 · S4 阶段从 artifacts_ready 到 candidate_built（WP 绿+自检 PASS+commit） | TC-L104-L205-601 | e2e |
| 负向 · self-repair 3 次耗尽 · 委托 L2-06 exhausted candidate | TC-L104-L205-602 | e2e |
| 回滚 · 崩溃重启 · WAL 重放恢复到最后 attempt | TC-L104-L205-603 | e2e |
| 监督 · L1-07 halt scope=l1_04 · 所有活跃 WP 停止 · 导出 partial candidates | TC-L104-L205-604 | e2e |

### §1.6 集成点 × 测试（§2.9 与兄弟 L2 / 跨 BC）

| 协作方 | 关系 | TC ID | 备注 |
|---|---|---|---|
| L2-03 测试用例生成器 | 读 TestSuite（间接经 blueprint_id） | TC-L104-L205-801 | skeleton 从 L2-03 读 |
| L2-04 QualityGateConfig | 读 qgc + acl | TC-L104-L205-802 | 入站触发源 |
| L2-06 S5 Verifier 编排器 | 出站 delegate | TC-L104-L205-803 | no-self-verdict 强制 |
| L2-07 回退路由器 | 入站 receive_rollback_hint | TC-L104-L205-804 | 4 种决策路由 |

### §1.7 边界 × 测试（§9）

| 边界类型 | TC ID | 备注 |
|---|---|---|
| 空 WP（无测试）| TC-L104-L205-901 | red_count=0 · green_count=0 · 直接 candidate |
| 超大 WP（1000 测试）| TC-L104-L205-902 | 内存 / 吞吐边界 |
| WP 执行超时（3 min 边界） | TC-L104-L205-903 | HALT_WP |
| 资源耗尽 · disk full | TC-L104-L205-904 | WAL 写失败 · HALT |
| 用例崩溃 · 子进程 OOM | TC-L104-L205-905 | self-repair · 再失败 exhausted |
| 并发 > 5（上限排队）| TC-L104-L205-906 | FIFO 队列语义 |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_05_S4ExecutionDriver`；arrange / act / assert 三段明确。
> 被测对象（SUT）：`WPExecutionOrchestrator`（Application Service）· 从 `app.l1_04.l2_05.orchestrator` 导入。
> 所有入参 schema 严格按 §3 字段级 YAML · 所有出参断言按 §3 出参 schema。

```python
# file: tests/l1_04/test_l2_05_s4_execution_driver_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_05.orchestrator import WPExecutionOrchestrator
from app.l1_04.l2_05.schemas import (
    ArtifactsReadyEvent,
    ExecuteWPRequest,
    ExecuteWPResponse,
    ProbeHealthQuery,
    ProbeHealthResponse,
    HaltCommand,
    HaltResponse,
    RollbackHint,
    RollbackAck,
)
from app.l1_04.l2_05.vo import (
    WPExecutionSnapshot,
    WPRunState,
    CandidateReport,
)
from app.l1_04.l2_05.errors import L205ExecutionError


class TestL2_05_S4ExecutionDriver:
    """§2.1 + §2.6 orchestrator / domain service 方法正向用例。每方法 ≥ 1 happy path。"""

    # --------- §3.1 + §6.1 · on_artifacts_ready 入口 --------- #

    def test_TC_L104_L205_001_on_artifacts_ready_single_wp_happy_path(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
        make_artifacts_ready_event,
    ) -> None:
        """TC-L104-L205-001 · 收 dual_artifact_ready 事件 · 启 1 WP · 正常返回。"""
        # arrange
        evt: ArtifactsReadyEvent = make_artifacts_ready_event(
            project_id=mock_project_id,
            wp_ids=["wp-001"],
        )
        # act
        resp = sut.on_artifacts_ready(evt)
        # assert
        assert resp.accepted is True, "§3.1 接收方动作 · 校验 qgc+acl 可读"
        assert resp.started_wp_count == 1
        assert resp.trace_id == evt.trace_id, "透传 trace_id"

    def test_TC_L104_L205_002_on_artifacts_ready_multi_wp_fanout(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
        make_artifacts_ready_event,
    ) -> None:
        """TC-L104-L205-002 · 多 WP 并发扇出（≤ concurrent_limit=5）。"""
        evt = make_artifacts_ready_event(
            project_id=mock_project_id,
            wp_ids=[f"wp-{i:03d}" for i in range(5)],
        )
        resp = sut.on_artifacts_ready(evt)
        assert resp.started_wp_count == 5, "§12.2 单机并发 WP 上限 5"

    # --------- §3.2 + §6.2 · execute_wp 主方法 --------- #

    def test_TC_L104_L205_003_execute_wp_attempt_0_all_green(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
        make_execute_request,
    ) -> None:
        """TC-L104-L205-003 · attempt=0 首跑 · 所有测试绿 · 所有 predicate pass · 构建 candidate。"""
        # arrange
        req: ExecuteWPRequest = make_execute_request(
            project_id=mock_project_id, wp_id="wp-happy", attempt=0
        )
        # act
        resp: ExecuteWPResponse = sut.execute_wp(req)
        # assert
        assert resp.success is True
        assert resp.candidate_report_id is not None, "§6.7 必构 candidate"
        assert resp.attempt_count == 1, "只跑了 attempt=0 一次"
        assert resp.final_state["test_outcomes"]["red_count"] == 0
        assert resp.delegation["delegated_to"] == "L2-06", "§6.6 no-self-verdict 强委托"

    def test_TC_L104_L205_011_execute_wp_coherence_local_ok(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
        make_execute_request,
    ) -> None:
        """TC-L104-L205-011 · 本地 coherence 再校验通过 · is_coherent=true。"""
        req = make_execute_request(project_id=mock_project_id, wp_id="wp-coh")
        resp = sut.execute_wp(req)
        assert resp.final_state["coherence"]["is_coherent"] is True

    def test_TC_L104_L205_012_execute_wp_self_repair_once_recovers(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
        make_execute_request,
        flaky_skill_invoker,
    ) -> None:
        """TC-L104-L205-012 · attempt=0 红 · self-repair attempt=1 绿 · 构 candidate 标 repaired。"""
        req = make_execute_request(project_id=mock_project_id, wp_id="wp-fix1")
        flaky_skill_invoker.set_fail_count(1)
        resp = sut.execute_wp(req)
        assert resp.success is True
        assert resp.attempt_count == 2, "attempt_count = 0 跑 + 1 次 self-repair = 2"

    def test_TC_L104_L205_039_execute_wp_idempotent_already_completed(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
        make_execute_request,
    ) -> None:
        """TC-L104-L205-039 · §6.16 幂等 · 已 GREEN_AND_PASSING 的 WP 二次调用直接返回原 snapshot。"""
        req = make_execute_request(project_id=mock_project_id, wp_id="wp-idem")
        first = sut.execute_wp(req)
        second = sut.execute_wp(req)
        assert first.snapshot_id == second.snapshot_id, "§6.16 幂等键 = (project_id, wp_id, blueprint_id)"

    # --------- §2.1 + §6.3 · run_red_green_loop --------- #

    def test_TC_L104_L205_013_run_red_green_loop_empty_skeleton_direct_green(
        self,
        sut: WPExecutionOrchestrator,
        make_wp_ctx,
    ) -> None:
        """TC-L104-L205-013 · skeleton 为空 · 直接返回绿（边界）。"""
        ctx = make_wp_ctx(skeletons=[])
        result = sut._red_green_strategy.run(ctx)
        assert result.all_green is True
        assert result.attempts_used == 0

    def test_TC_L104_L205_014_run_red_green_loop_one_fix_green(
        self,
        sut: WPExecutionOrchestrator,
        make_wp_ctx,
        flaky_skill_invoker,
    ) -> None:
        """TC-L104-L205-014 · 1 次 fix 后绿 · attempts_used=1。"""
        ctx = make_wp_ctx(skeletons=[{"test_id": "t1", "status": "red"}])
        flaky_skill_invoker.set_fail_count(1)
        result = sut._red_green_strategy.run(ctx)
        assert result.all_green is True
        assert result.attempts_used == 1

    # --------- §2.1 + §6.3 · invoke_self_repair（≤ 3 硬锁） --------- #

    def test_TC_L104_L205_015_invoke_self_repair_attempt_1_success(
        self,
        sut: WPExecutionOrchestrator,
        make_wp_ctx,
    ) -> None:
        """TC-L104-L205-015 · self-repair attempt=1 · strategy=import_missing_deps 成功。"""
        ctx = make_wp_ctx()
        outcome = sut.invoke_self_repair(ctx, attempt=1)
        assert outcome.success is True
        assert outcome.strategy == "import_missing_deps", "§11.3 fallback playbook"

    def test_TC_L104_L205_016_invoke_self_repair_attempt_3_exhausted(
        self,
        sut: WPExecutionOrchestrator,
        make_wp_ctx,
        flaky_skill_invoker,
    ) -> None:
        """TC-L104-L205-016 · §2.1 self_repair_max_attempts=3 硬锁 · attempt 4 抛 EXHAUSTED。"""
        ctx = make_wp_ctx()
        flaky_skill_invoker.set_fail_count(999)
        with pytest.raises(L205ExecutionError) as exc:
            sut.invoke_self_repair(ctx, attempt=4)
        assert exc.value.code == "E_L205_L205_SELF_REPAIR_EXHAUSTED"

    # --------- §2.1 + §6.5 · run_predicates（PredicateRunner） --------- #

    def test_TC_L104_L205_020_run_predicates_all_pass(
        self,
        sut: WPExecutionOrchestrator,
        make_qgc,
        make_actual_state,
    ) -> None:
        """TC-L104-L205-020 · 3 个 predicates 全 pass。"""
        qgc = make_qgc(predicate_count=3)
        state = make_actual_state(all_pass=True)
        results = sut.run_predicates(qgc, state)
        assert all(r.status == "pass" for r in results)

    def test_TC_L104_L205_021_run_predicates_partial_fail_continues(
        self,
        sut: WPExecutionOrchestrator,
        make_qgc,
        make_actual_state,
    ) -> None:
        """TC-L104-L205-021 · §6.5 部分 fail · 继续执行其他（不抛异常短路）。"""
        qgc = make_qgc(predicate_count=5)
        state = make_actual_state(fail_indices=[1, 3])
        results = sut.run_predicates(qgc, state)
        assert len(results) == 5, "即使有 fail 也跑完所有"
        assert sum(1 for r in results if r.status == "fail") == 2

    def test_TC_L104_L205_022_run_predicates_whitelist_enforced(
        self,
        sut: WPExecutionOrchestrator,
        make_qgc_with_banned_type,
    ) -> None:
        """TC-L104-L205-022 · §6.5 + D6 决策 · whitelist 只允许 Numeric/Boolean/String/TestStatus。"""
        qgc = make_qgc_with_banned_type(type_name="arbitrary_exec")
        with pytest.raises(L205ExecutionError) as exc:
            sut.run_predicates(qgc, actual_state={})
        assert exc.value.code == "E_L205_L205_PREDICATE_RUN_FAIL"

    # --------- §2.1 + §6.7 · build_candidate_report（no-self-verdict） --------- #

    def test_TC_L104_L205_025_build_candidate_report_happy(
        self,
        sut: WPExecutionOrchestrator,
        make_final_snapshot,
        make_qgc,
        make_acl,
    ) -> None:
        """TC-L104-L205-025 · §6.7 正常构 candidate · 含 markdown_summary。"""
        snap = make_final_snapshot(all_green=True)
        qgc = make_qgc()
        acl = make_acl()
        cr: CandidateReport = sut.build_candidate_report([snap], qgc, acl)
        assert cr.candidate_id.startswith("cr-"), "§2.4 format=cr-{uuid-v7}"
        assert cr.markdown_summary, "§3.9 给人类审计"

    def test_TC_L104_L205_026_candidate_verdict_hint_is_not_verdict(
        self,
        sut: WPExecutionOrchestrator,
        make_final_snapshot,
        make_qgc,
        make_acl,
    ) -> None:
        """TC-L104-L205-026 · §6.7 关键不变式 · candidate_verdict_hint 是 hint · 不是 verdict（no-self-verdict）。"""
        snap = make_final_snapshot(all_green=True, all_predicates_pass=True)
        cr = sut.build_candidate_report([snap], make_qgc(), make_acl())
        # 明确区分：hint 结构存在但没有 "verdict" 字段
        assert "candidate_verdict_hint" in cr.to_dict()
        assert "verdict" not in cr.to_dict(), "§1.9 DDD 一句话 · 只裁 candidate，不下 verdict"
        assert cr.candidate_verdict_hint["all_tests_green"] is True

    def test_TC_L104_L205_027_candidate_report_exhausted_path(
        self,
        sut: WPExecutionOrchestrator,
        make_final_snapshot,
        make_qgc,
        make_acl,
    ) -> None:
        """TC-L104-L205-027 · self-repair 耗尽也能构 exhausted candidate（§5.3 P1-1 链路）。"""
        snap = make_final_snapshot(exhausted=True)
        cr = sut.build_candidate_report([snap], make_qgc(), make_acl())
        assert cr.candidate_verdict_hint["no_self_repair_exhausted"] is False
        assert cr.self_repair_summary["attempts"] == 3

    # --------- §2.1 + §6.6 · delegate_verdict（IC-L2-06） --------- #

    def test_TC_L104_L205_030_delegate_verdict_first_try_accepted(
        self,
        sut: WPExecutionOrchestrator,
        make_candidate_report,
        mock_l2_06_verifier,
    ) -> None:
        """TC-L104-L205-030 · IC-L2-06 首次委托被接受 · 返回 verdict_session_id。"""
        cr = make_candidate_report()
        mock_l2_06_verifier.set_response(accepted=True, estimated_verdict_ms=1500)
        resp = sut.delegate_verdict(cr)
        assert resp.accepted is True
        assert resp.verdict_session_id, "§3.9 出参必含 verdict_session_id"

    def test_TC_L104_L205_031_delegate_verdict_3_retries_then_standalone(
        self,
        sut: WPExecutionOrchestrator,
        make_candidate_report,
        mock_l2_06_verifier,
    ) -> None:
        """TC-L104-L205-031 · 3 次重试后降级 standalone（§11.1 E_L205_L205_DELEGATE_VERIFIER_FAIL 恢复）。"""
        cr = make_candidate_report()
        mock_l2_06_verifier.set_unavailable(fail_count=3)
        resp = sut.delegate_verdict(cr)
        assert resp.accepted is False
        assert resp.fallback_mode == "standalone", "§11.1 降级路径"

    # --------- §2.1 + §6.10 · crash_recovery --------- #

    def test_TC_L104_L205_035_crash_recovery_full_wal_replay(
        self,
        sut: WPExecutionOrchestrator,
        seeded_wal_buffer,
    ) -> None:
        """TC-L104-L205-035 · §6.10 崩溃重启 · WAL 完整重放 · 恢复到最后 snapshot。"""
        seeded_wal_buffer.seed_entries(wp_id="wp-crash", count=12)
        snap = sut.crash_recovery(wp_id="wp-crash")
        assert snap is not None
        assert snap.wal_sequence_id == 12

    def test_TC_L104_L205_036_crash_recovery_hash_chain_detect_corruption(
        self,
        sut: WPExecutionOrchestrator,
        seeded_wal_buffer,
    ) -> None:
        """TC-L104-L205-036 · §6.10 hash-chain 校验 · 损坏时抛 WAL_REPLAY_FAIL。"""
        seeded_wal_buffer.seed_entries(wp_id="wp-corrupt", count=10)
        seeded_wal_buffer.corrupt_entry_hash(wp_id="wp-corrupt", seq=5)
        with pytest.raises(L205ExecutionError) as exc:
            sut.crash_recovery(wp_id="wp-corrupt")
        assert exc.value.code == "E_L205_L205_WAL_REPLAY_FAIL"

    # --------- §2.6.3 · WorkspaceIsolator（§6.4） --------- #

    def test_TC_L104_L205_040_workspace_create_git_worktree(
        self,
        workspace_isolator,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L205-040 · §6.4 git worktree add · 返回绝对路径。"""
        path = workspace_isolator.create(project_id=mock_project_id, wp_id="wp-iso")
        assert path.startswith(f"projects/{mock_project_id}/workspaces/")

    def test_TC_L104_L205_041_workspace_destroy_cleans_up(
        self,
        workspace_isolator,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L205-041 · §6.4 + §6.18 destroy · git worktree remove + 文件清零。"""
        p = workspace_isolator.create(project_id=mock_project_id, wp_id="wp-del")
        workspace_isolator.destroy(p)
        assert not workspace_isolator.exists(p)

    # --------- §2.6.4 · SkillInvoker（§6.9 · IC-04） --------- #

    def test_TC_L104_L205_045_skill_invoke_success_returns_invoke_id(
        self,
        skill_invoker,
        mock_workspace_path: str,
    ) -> None:
        """TC-L104-L205-045 · §3.4 + §6.9 IC-04 invoke_skill · 返回 invoke_id + duration_ms。"""
        result = skill_invoker.invoke(
            skill_intent="red_test_creation",
            skill_context={"workspace_path": mock_workspace_path, "budget_ms": 120000, "budget_tokens": 50000},
            workspace_path=mock_workspace_path,
        )
        assert result.status == "success"
        assert result.invoke_id is not None
        assert result.duration_ms >= 0

    # --------- §2.6.5 · WALBuffer（§6.8） --------- #

    def test_TC_L104_L205_050_wal_append_then_fsync(
        self,
        wal_buffer,
        make_wal_entry,
    ) -> None:
        """TC-L104-L205-050 · §6.8 append + fsync · sequence_id 单调递增。"""
        e1 = make_wal_entry(wp_id="wp-w1", entry_type="SNAPSHOT_START")
        e2 = make_wal_entry(wp_id="wp-w1", entry_type="SKILL_INVOKE")
        wal_buffer.append(e1)
        wal_buffer.append(e2)
        wal_buffer.fsync()
        assert wal_buffer.get_latest_sequence("wp-w1") == 2

    def test_TC_L104_L205_051_wal_replay_on_crash_reconstructs_snapshot(
        self,
        wal_buffer,
        make_wal_entry,
    ) -> None:
        """TC-L104-L205-051 · §6.8 replay_on_crash · hash-chain 正确 · 重建 snapshot。"""
        for i in range(5):
            wal_buffer.append(make_wal_entry(wp_id="wp-rp", sequence_id=i + 1))
        snap = wal_buffer.replay_on_crash("wp-rp")
        assert snap is not None
        assert snap.wp_id == "wp-rp"

    # --------- §6.12 · handle_halt_command（IC-14） --------- #

    def test_TC_L104_L205_055_halt_scope_wp(
        self,
        sut: WPExecutionOrchestrator,
        running_wp_fixture,
    ) -> None:
        """TC-L104-L205-055 · §3.7 IC-14 scope=wp · 单 WP halt。"""
        cmd = HaltCommand(halt_scope="wp", target={"wp_id": running_wp_fixture}, reason="supervisor_intervention")
        resp: HaltResponse = sut.handle_halt_command(cmd)
        assert resp.halted is True
        assert running_wp_fixture in resp.affected_wps

    def test_TC_L104_L205_056_halt_scope_l1_04_all_active(
        self,
        sut: WPExecutionOrchestrator,
        multi_running_wps,
    ) -> None:
        """TC-L104-L205-056 · §3.7 scope=l1_04 · 所有活跃 WP 都 halt。"""
        cmd = HaltCommand(halt_scope="l1_04", target={}, reason="catastrophic_divergence")
        resp = sut.handle_halt_command(cmd)
        assert set(resp.affected_wps) == set(multi_running_wps)

    def test_TC_L104_L205_057_halt_scope_project(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
        multi_running_wps,
    ) -> None:
        """TC-L104-L205-057 · §3.7 scope=project · 目标 project 全部 halt。"""
        cmd = HaltCommand(halt_scope="project", target={"project_id": mock_project_id}, reason="resource_exhaustion")
        resp = sut.handle_halt_command(cmd)
        assert resp.halted is True

    # --------- §6.13 · handle_rollback_hint（IC-L2-07） --------- #

    def test_TC_L104_L205_060_rollback_retry_wp(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L205-060 · §3.10 retry_wp · 重启 WP（新 attempt）。"""
        hint = RollbackHint(rollback_decision="retry_wp", wp_id="wp-rb", project_id=mock_project_id, candidate_id_triggering="cr-x")
        ack: RollbackAck = sut.handle_rollback_hint(hint)
        assert ack.acknowledged is True
        assert ack.next_action == "restart_wp"

    def test_TC_L104_L205_061_rollback_retry_blueprint(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L205-061 · §3.10 retry_blueprint · 请 L2-01 重编 · 本 L2 停当前 wp。"""
        hint = RollbackHint(rollback_decision="retry_blueprint", wp_id="wp-rb2", project_id=mock_project_id, candidate_id_triggering="cr-y")
        ack = sut.handle_rollback_hint(hint)
        assert ack.acknowledged is True
        assert ack.next_action == "stop_and_escalate_to_l2_01"

    def test_TC_L104_L205_062_rollback_escalate_supervisor(
        self,
        sut: WPExecutionOrchestrator,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L205-062 · §3.10 escalate_supervisor · 升给 L1-07。"""
        hint = RollbackHint(rollback_decision="escalate_supervisor", wp_id="wp-rb3", project_id=mock_project_id, candidate_id_triggering="cr-z")
        ack = sut.handle_rollback_hint(hint)
        assert ack.next_action == "escalate_to_l1_07"

    # --------- §6.14 · handle_probe_health（IC-11） --------- #

    def test_TC_L104_L205_065_probe_health_liveness(
        self,
        sut: WPExecutionOrchestrator,
    ) -> None:
        """TC-L104-L205-065 · §3.6 probe_type=liveness · healthy=true。"""
        q = ProbeHealthQuery(probe_type="liveness")
        r: ProbeHealthResponse = sut.handle_probe_health(q)
        assert r.healthy is True

    def test_TC_L104_L205_066_probe_health_wp_progress(
        self,
        sut: WPExecutionOrchestrator,
        running_wp_fixture,
    ) -> None:
        """TC-L104-L205-066 · §3.6 probe_type=wp_progress · 返回 current_phase + elapsed_ms。"""
        q = ProbeHealthQuery(probe_type="wp_progress", wp_id=running_wp_fixture)
        r = sut.handle_probe_health(q)
        assert r.healthy is True
        assert any(p.wp_id == running_wp_fixture and p.current_phase in {"RED", "GREEN", "REPAIRING", "EVALUATING"} for p in r.in_progress)

    # --------- §6.15 · detect_stuck_wps --------- #

    def test_TC_L104_L205_070_detect_stuck_wps_returns_stale(
        self,
        sut: WPExecutionOrchestrator,
        stale_wp_fixture,
    ) -> None:
        """TC-L104-L205-070 · §6.15 last_event_at > wp_execution_timeout_ms 的 WP 被标 stuck。"""
        stuck = sut.detect_stuck_wps()
        assert stale_wp_fixture in {s.wp_id for s in stuck}
```

---

## §3 负向用例（每错误码 ≥ 1）

> 按 §11.1 24 项错误码 · 每类各 ≥ 1 用例 · 错误码前缀按 3-1 原样保留。

```python
# file: tests/l1_04/test_l2_05_s4_execution_driver_negative.py
from __future__ import annotations

import pytest

from app.l1_04.l2_05.errors import L205ExecutionError


class TestL2_05_NegativePath:
    """§11.1 全 24 项错误码；每类 ≥ 1 用例。"""

    # --------- E_L205_L204_* （上游 L2-04 入参错） --------- #

    def test_TC_L104_L205_101_yaml_not_found(self, sut, make_artifacts_ready_event) -> None:
        """TC-L104-L205-101 · yaml_path 不存在 · REJECTED + 告警。"""
        evt = make_artifacts_ready_event(yaml_path="projects/x/none.yaml")
        with pytest.raises(L205ExecutionError) as exc:
            sut.on_artifacts_ready(evt)
        assert exc.value.code == "E_L205_L204_YAML_NOT_FOUND"
        assert exc.value.severity == "REJECTED"

    def test_TC_L104_L205_102_yaml_parse_fail(self, sut, make_artifacts_ready_event, broken_yaml_path) -> None:
        """TC-L104-L205-102 · yaml 语法污染 · REJECTED。"""
        evt = make_artifacts_ready_event(yaml_path=broken_yaml_path)
        with pytest.raises(L205ExecutionError) as exc:
            sut.on_artifacts_ready(evt)
        assert exc.value.code == "E_L205_L204_YAML_PARSE_FAIL"

    def test_TC_L104_L205_103_md_not_found(self, sut, make_artifacts_ready_event) -> None:
        """TC-L104-L205-103 · md_path 不存在 · REJECTED。"""
        evt = make_artifacts_ready_event(md_path="projects/x/none.md")
        with pytest.raises(L205ExecutionError) as exc:
            sut.on_artifacts_ready(evt)
        assert exc.value.code == "E_L205_L204_MD_NOT_FOUND"

    def test_TC_L104_L205_104_coherence_check_fail(self, sut, make_artifacts_ready_event, tainted_pair) -> None:
        """TC-L104-L205-104 · yaml 和 md 不一致（疑似污染）· REJECTED + 告警。"""
        evt = make_artifacts_ready_event(yaml_path=tainted_pair.yaml, md_path=tainted_pair.md)
        with pytest.raises(L205ExecutionError) as exc:
            sut.on_artifacts_ready(evt)
        assert exc.value.code == "E_L205_L204_COHERENCE_CHECK_FAIL"

    # --------- E_L205_L205_* （本 L2 执行侧错） --------- #

    def test_TC_L104_L205_105_wp_not_found(self, sut, make_execute_request) -> None:
        """TC-L104-L205-105 · execute_wp(wp_id 非法) · 返回 + 上报。"""
        req = make_execute_request(wp_id="wp-does-not-exist")
        with pytest.raises(L205ExecutionError) as exc:
            sut.execute_wp(req)
        assert exc.value.code == "E_L205_L205_WP_NOT_FOUND"

    def test_TC_L104_L205_106_workspace_create_fail_retries_3x_then_halt(
        self, sut, make_execute_request, broken_git_fixture
    ) -> None:
        """TC-L104-L205-106 · §6.4 worktree 创建失败 · 重试 3 次 · HALT_WP。"""
        req = make_execute_request(wp_id="wp-wc-fail")
        broken_git_fixture.break_worktree_add()
        with pytest.raises(L205ExecutionError) as exc:
            sut.execute_wp(req)
        assert exc.value.code == "E_L205_L205_WORKSPACE_CREATE_FAIL"
        assert broken_git_fixture.call_count == 3, "§11.1 恢复 = 重试 3 次"

    def test_TC_L104_L205_107_skill_invoke_fail_triggers_self_repair(
        self, sut, make_execute_request, flaky_skill_invoker
    ) -> None:
        """TC-L104-L205-107 · skill 回错 · 算 red · 触发 self-repair。"""
        flaky_skill_invoker.set_fail_count(1)
        req = make_execute_request(wp_id="wp-skill-err")
        resp = sut.execute_wp(req)
        # 不抛异常：§11.1 恢复 = 算作 red · 触发 self-repair
        assert resp.attempt_count >= 2
        assert "E_L205_L205_SKILL_INVOKE_FAIL" in resp.error_codes_seen

    def test_TC_L104_L205_108_test_run_crash_triggers_self_repair(
        self, sut, make_execute_request, crashing_test_runner
    ) -> None:
        """TC-L104-L205-108 · 测试子进程崩溃 · self-repair。"""
        crashing_test_runner.crash_on_first_run()
        req = make_execute_request(wp_id="wp-crash-test")
        resp = sut.execute_wp(req)
        assert "E_L205_L205_TEST_RUN_CRASH" in resp.error_codes_seen

    def test_TC_L104_L205_109_self_repair_exhausted_delegates_exhausted_candidate(
        self, sut, make_execute_request, flaky_skill_invoker
    ) -> None:
        """TC-L104-L205-109 · §6.3 hard-lock 3 · candidate.verdict_hint.no_self_repair_exhausted=False。"""
        flaky_skill_invoker.set_fail_count(999)
        req = make_execute_request(wp_id="wp-exh")
        resp = sut.execute_wp(req)
        assert resp.success is False
        assert resp.candidate_report_id is not None, "仍必须产 exhausted candidate"
        assert "E_L205_L205_SELF_REPAIR_EXHAUSTED" in resp.error_codes_seen

    def test_TC_L104_L205_110_predicate_run_fail_continues_others(
        self, sut, make_qgc_with_broken_predicate
    ) -> None:
        """TC-L104-L205-110 · 某 predicate runtime 错 · 标记 · 继续其他（不短路）。"""
        qgc = make_qgc_with_broken_predicate(broken_index=2, total=5)
        results = sut.run_predicates(qgc, actual_state={})
        assert len(results) == 5
        assert results[2].status == "error"
        assert results[2].error_code == "E_L205_L205_PREDICATE_RUN_FAIL"

    def test_TC_L104_L205_111_coherence_local_fail_rejected(
        self, sut, make_execute_request, force_coherence_drift
    ) -> None:
        """TC-L104-L205-111 · 本地再校验 coherence fail · REJECTED + 告警。"""
        force_coherence_drift()
        req = make_execute_request(wp_id="wp-cohfail")
        with pytest.raises(L205ExecutionError) as exc:
            sut.execute_wp(req)
        assert exc.value.code == "E_L205_L205_COHERENCE_LOCAL_FAIL"

    def test_TC_L104_L205_112_wal_write_fail_retries_3x_then_halt(
        self, sut, wal_buffer, make_wal_entry, wal_disk_full
    ) -> None:
        """TC-L104-L205-112 · §6.8 WAL 写盘失败 · 重试 3 · HALT。"""
        wal_disk_full()
        with pytest.raises(L205ExecutionError) as exc:
            wal_buffer.append(make_wal_entry(wp_id="wp-wfail"))
        assert exc.value.code == "E_L205_L205_WAL_WRITE_FAIL"

    def test_TC_L104_L205_113_wal_replay_fail_manual(
        self, sut, seeded_wal_buffer
    ) -> None:
        """TC-L104-L205-113 · §6.10 WAL 损坏无法重放 · HALT · 人工介入。"""
        seeded_wal_buffer.seed_entries(wp_id="wp-wrepfail", count=5)
        seeded_wal_buffer.corrupt_entry_hash(wp_id="wp-wrepfail", seq=3)
        with pytest.raises(L205ExecutionError) as exc:
            sut.crash_recovery(wp_id="wp-wrepfail")
        assert exc.value.code == "E_L205_L205_WAL_REPLAY_FAIL"
        assert exc.value.severity == "HALT_MANUAL"

    def test_TC_L104_L205_114_wp_timeout_exceeds_3min(
        self, sut, make_execute_request, slow_skill_invoker
    ) -> None:
        """TC-L104-L205-114 · §12.1 + §2.1 wp_execution_timeout_ms=180000 · HALT_WP。"""
        slow_skill_invoker.set_sleep_ms(190_000)
        req = make_execute_request(wp_id="wp-tmo")
        with pytest.raises(L205ExecutionError) as exc:
            sut.execute_wp(req)
        assert exc.value.code == "E_L205_L205_WP_TIMEOUT"

    def test_TC_L104_L205_115_delegate_verifier_fail_3x_fallback_standalone(
        self, sut, make_candidate_report, mock_l2_06_verifier
    ) -> None:
        """TC-L104-L205-115 · §3.9 L2-06 不可达 · 3 次重试失败 · 降级 candidate-standalone。"""
        mock_l2_06_verifier.set_unavailable(fail_count=3)
        cr = make_candidate_report()
        resp = sut.delegate_verdict(cr)
        assert resp.accepted is False
        assert "E_L205_L205_DELEGATE_VERIFIER_FAIL" in resp.error_codes_seen
        assert resp.fallback_mode == "standalone"

    def test_TC_L104_L205_116_rollback_prompted_restarts_wp(
        self, sut, mock_project_id
    ) -> None:
        """TC-L104-L205-116 · §3.10 + §11.1 ROLLBACK_PROMPTED · 重启 WP · 新 attempt。"""
        hint = {"rollback_decision": "retry_wp", "wp_id": "wp-roll", "project_id": mock_project_id}
        ack = sut.handle_rollback_hint(hint)
        assert ack.next_action_started is True
        assert "E_L205_L205_ROLLBACK_PROMPTED" in ack.error_codes_seen

    def test_TC_L104_L205_117_wp_lock_timeout_conflict(
        self, sut, make_execute_request, already_locked_wp
    ) -> None:
        """TC-L104-L205-117 · §6.17 分布式锁冲突 · 超时抛错。"""
        already_locked_wp("wp-lock-clash")
        req = make_execute_request(wp_id="wp-lock-clash")
        with pytest.raises(L205ExecutionError) as exc:
            sut.execute_wp(req)
        assert exc.value.code == "E_L205_L205_WP_LOCK_TIMEOUT"

    # --------- E_L205_L105_* （Skill L1-05 侧错） --------- #

    def test_TC_L104_L205_120_skill_not_found(self, skill_invoker) -> None:
        """TC-L104-L205-120 · §3.4 未知 skill_intent · REJECTED。"""
        with pytest.raises(L205ExecutionError) as exc:
            skill_invoker.invoke(skill_intent="unknown_xxx_skill", skill_context={}, workspace_path="/tmp")
        assert exc.value.code == "E_L205_L105_SKILL_NOT_FOUND"

    def test_TC_L104_L205_121_skill_budget_exhausted(self, skill_invoker, over_budget_context) -> None:
        """TC-L104-L205-121 · §3.4 预算耗尽 · self-repair 路径。"""
        with pytest.raises(L205ExecutionError) as exc:
            skill_invoker.invoke(skill_intent="red_test_creation", skill_context=over_budget_context, workspace_path="/tmp")
        assert exc.value.code == "E_L205_L105_SKILL_BUDGET_EXHAUSTED"

    def test_TC_L104_L205_122_skill_timeout(self, skill_invoker, slow_skill_backend) -> None:
        """TC-L104-L205-122 · §3.4 skill 超时 · self-repair。"""
        slow_skill_backend.set_sleep_ms(150_000)
        with pytest.raises(L205ExecutionError) as exc:
            skill_invoker.invoke(skill_intent="code_fix_attempt", skill_context={"budget_ms": 120_000}, workspace_path="/tmp")
        assert exc.value.code == "E_L205_L105_SKILL_TIMEOUT"

    # --------- E_L205_L106_* （KB L1-06 侧） --------- #

    def test_TC_L104_L205_125_kb_unavailable_falls_back_to_playbook(
        self, sut, kb_unavailable_fixture, make_execute_request
    ) -> None:
        """TC-L104-L205-125 · §11.3 · KB 不可达 · 走内建 fallback playbook · 不 fail。"""
        kb_unavailable_fixture()
        req = make_execute_request(wp_id="wp-kbna")
        resp = sut.execute_wp(req)
        # 必须仍能正常跑（走内建 playbook）
        assert resp.success is True
        assert "E_L205_L106_KB_UNAVAILABLE" in resp.warnings

    # --------- E_L205_L108_* （Event Bus 侧） --------- #

    def test_TC_L104_L205_128_event_bus_down_buffers_in_wal(
        self, sut, event_bus_down_fixture, make_execute_request
    ) -> None:
        """TC-L104-L205-128 · §11.1 · Event Bus 故障 · 写 WAL 缓冲 · 不阻塞。"""
        event_bus_down_fixture()
        req = make_execute_request(wp_id="wp-ebdown")
        resp = sut.execute_wp(req)
        assert resp.success is True
        assert "E_L205_L108_EVENT_BUS_DOWN" in resp.warnings

    # --------- E_L205_SUPERVISOR_* --------- #

    def test_TC_L104_L205_130_supervisor_halt_builds_partial_candidate(
        self, sut, running_wp_fixture
    ) -> None:
        """TC-L104-L205-130 · §3.7 L1-07 强制 halt · 仍构建 partial candidate 委托 L2-06（§5.5 P1-3）。"""
        cmd = {"halt_scope": "wp", "target": {"wp_id": running_wp_fixture}, "reason": "supervisor_intervention"}
        resp = sut.handle_halt_command(cmd)
        assert resp.halted is True
        assert len(resp.active_candidates_at_halt) >= 1, "§6.11 halt 仍委托 partial candidate"

    # --------- E_L205_INTERNAL_* --------- #

    def test_TC_L104_L205_135_internal_assert_failed_alerts_and_halts(
        self, sut, make_execute_request, induce_internal_bug
    ) -> None:
        """TC-L104-L205-135 · 内部断言失败（bug）· 告警 + HALT。"""
        induce_internal_bug()
        req = make_execute_request(wp_id="wp-assert")
        with pytest.raises(L205ExecutionError) as exc:
            sut.execute_wp(req)
        assert exc.value.code == "E_L205_INTERNAL_ASSERT_FAILED"
        assert exc.value.severity == "HALT"
```

---

## §4 IC-XX 契约集成测试

> §3 的 10 个 IC 触点 · 每个 ≥ 1 join test；重点覆盖"驱动测试用例执行 / 结果回流"的契约边界：
> - 入站（触发执行）：IC-L2-04 dual_artifact_ready、IC-11 probe_health、IC-14 halt_command、IC-L2-07 rollback_hint
> - 出站（结果回流）：IC-09 append_event、IC-04 invoke_skill、IC-06 kb_read、IC-16 push_stage_gate_card、IC-L2-06 delegate_verify

```python
# file: tests/l1_04/test_l2_05_s4_ic_contracts.py
from __future__ import annotations

import pytest


class TestL2_05_ICContracts:
    """IC-XX 契约粒度集成测试 · Schema/方向/幂等 断言。"""

    # --------- IC-L2-04 入站 · 触发执行（dual_artifact_ready） --------- #

    def test_TC_L104_L205_401_ic_l2_04_artifacts_ready_schema_and_trigger(
        self, sut, make_artifacts_ready_event, mock_project_id
    ) -> None:
        """TC-L104-L205-401 · §3.1 schema 校验 + 触发 execute_wp 扇出。"""
        evt = make_artifacts_ready_event(
            project_id=mock_project_id,
            wp_ids=["wp-a", "wp-b"],
        )
        # 字段级 schema 断言（§3.1）
        assert evt.event_type == "dual_artifact_ready"
        assert evt.event_version == "v1.0"
        assert evt.emitted_by == "L2-04"
        assert evt.payload.get("ac_count") is not None
        # 行为：驱动执行
        resp = sut.on_artifacts_ready(evt)
        assert resp.started_wp_count == 2

    # --------- execute_wp 内部主方法 schema --------- #

    def test_TC_L104_L205_402_execute_wp_schema_in_out(
        self, sut, make_execute_request, mock_project_id
    ) -> None:
        """TC-L104-L205-402 · §3.2 入参/出参 schema 断言。"""
        req = make_execute_request(project_id=mock_project_id, wp_id="wp-sch", resume_from_wal=False)
        resp = sut.execute_wp(req)
        # §3.2 出参结构
        for key in ("success", "snapshot_id", "candidate_report_id", "attempt_count", "total_duration_ms", "final_state"):
            assert hasattr(resp, key), f"§3.2 出参 schema 缺字段 {key}"

    # --------- IC-09 append_event 出站 · 10 种事件类型 --------- #

    def test_TC_L104_L205_403_ic_09_append_event_10_types_and_fsync(
        self, sut, mock_event_bus, make_execute_request
    ) -> None:
        """TC-L104-L205-403 · §3.3 stream=L1-04.L2-05.exec · 每状态转换写审计 · 强一致 fsync。"""
        req = make_execute_request(wp_id="wp-evt")
        sut.execute_wp(req)
        types = [e.event_type for e in mock_event_bus.captured]
        # 正常链路必含：wp_exec_started → redgreen_loop_start → predicates_ran → candidate_built → delegated_to_verifier
        must_contain = {"wp_exec_started", "redgreen_loop_start", "predicates_ran", "candidate_built", "delegated_to_verifier"}
        assert must_contain.issubset(set(types))
        # payload 字段级
        for e in mock_event_bus.captured:
            assert e.stream == "L1-04.L2-05.exec"
            assert e.trace_id is not None

    # --------- IC-04 invoke_skill 出站 · red/green/self_repair intent --------- #

    def test_TC_L104_L205_404_ic_04_invoke_skill_intent_mapping(
        self, sut, skill_invoker_recorder, make_execute_request
    ) -> None:
        """TC-L104-L205-404 · §3.4 skill_intent 白名单 · 必含 red_test_creation/green_test_implementation。"""
        req = make_execute_request(wp_id="wp-sk-intent")
        sut.execute_wp(req)
        intents = [c.skill_intent for c in skill_invoker_recorder.calls]
        assert "red_test_creation" in intents or "green_test_implementation" in intents

    # --------- IC-06 kb_read 出站 · 可选 recipe miss 不 fail --------- #

    def test_TC_L104_L205_405_ic_06_kb_read_miss_does_not_fail(
        self, sut, kb_reader_recorder, make_execute_request
    ) -> None:
        """TC-L104-L205-405 · §3.5 recipe 查询 · cache_hit=False 不阻塞（降级 playbook）。"""
        kb_reader_recorder.set_miss()
        req = make_execute_request(wp_id="wp-kb-miss")
        resp = sut.execute_wp(req)
        assert resp.success is True, "§3.5 降级：KB 不可用 → 内建 fallback playbook"

    # --------- IC-11 probe_health 入站 · 响应契约 --------- #

    def test_TC_L104_L205_406_ic_11_probe_health_response_contract(
        self, sut
    ) -> None:
        """TC-L104-L205-406 · §3.6 响应 schema · healthy + active_wp_count + last_event_at。"""
        q = {"probe_type": "readiness"}
        r = sut.handle_probe_health(q)
        assert hasattr(r, "healthy")
        assert hasattr(r, "active_wp_count")
        assert hasattr(r, "last_event_at")

    # --------- IC-14 receive_halt_command 入站 · 3 scope --------- #

    def test_TC_L104_L205_407_ic_14_halt_command_idempotent_same_wp(
        self, sut, running_wp_fixture
    ) -> None:
        """TC-L104-L205-407 · §3.7 + ic-contracts.md · IC-14 幂等（同 wp_id + verdict_id 多次 halt 返回同结果）。"""
        cmd = {"halt_scope": "wp", "target": {"wp_id": running_wp_fixture}, "reason": "supervisor_intervention"}
        r1 = sut.handle_halt_command(cmd)
        r2 = sut.handle_halt_command(cmd)
        assert r1.halted == r2.halted
        assert r1.affected_wps == r2.affected_wps

    # --------- IC-16 push_stage_gate_card 出站 · UI 展示 --------- #

    def test_TC_L104_L205_408_ic_16_push_stage_gate_card_emits_on_transition(
        self, sut, stage_gate_card_recorder, make_execute_request
    ) -> None:
        """TC-L104-L205-408 · §3.8 · 每 card_type 状态转换都推（wp_exec_started / wp_self_repair_triggered / wp_candidate_built / wp_exec_halted）。"""
        req = make_execute_request(wp_id="wp-card")
        sut.execute_wp(req)
        types = [c.card_type for c in stage_gate_card_recorder.cards]
        assert "wp_exec_started" in types
        assert "wp_candidate_built" in types

    # --------- IC-L2-06 delegate_verify 出站 · no-self-verdict --------- #

    def test_TC_L104_L205_409_ic_l2_06_delegate_verify_result_flow_back(
        self, sut, mock_l2_06_verifier, make_candidate_report
    ) -> None:
        """TC-L104-L205-409 · §3.9 + D4 no-self-verdict · 必经 L2-06 · 接收 verdict_session_id 回流。"""
        mock_l2_06_verifier.set_response(accepted=True, estimated_verdict_ms=1500)
        cr = make_candidate_report()
        resp = sut.delegate_verdict(cr)
        # 关键契约：驱动测试用例执行 → 结果必回流 L2-06 裁决
        assert resp.accepted is True
        assert resp.verdict_session_id is not None
        assert mock_l2_06_verifier.last_request.full_candidate_report is not None
        assert mock_l2_06_verifier.last_request.delegation_request["priority"] in {"normal", "urgent"}

    # --------- IC-L2-07 receive_rollback_hint 入站 · 4 种决策 --------- #

    def test_TC_L104_L205_410_ic_l2_07_rollback_hint_all_4_decisions(
        self, sut, mock_project_id
    ) -> None:
        """TC-L104-L205-410 · §3.10 · 4 种 rollback_decision 全覆盖。"""
        for decision, expected in [
            ("retry_wp", "restart_wp"),
            ("retry_blueprint", "stop_and_escalate_to_l2_01"),
            ("escalate_supervisor", "escalate_to_l1_07"),
            ("reject_wp", "abandon_wp"),
        ]:
            hint = {
                "rollback_decision": decision,
                "wp_id": f"wp-rb-{decision}",
                "project_id": mock_project_id,
                "candidate_id_triggering": "cr-x",
            }
            ack = sut.handle_rollback_hint(hint)
            assert ack.acknowledged is True
            assert ack.next_action == expected
```

---

## §5 性能 SLO 用例（§12 对标）

> `@pytest.mark.perf` 标记；P95 对标 §12.1；吞吐 对标 §12.2；资源 对标 §12.3。

```python
# file: tests/l1_04/test_l2_05_s4_perf.py
from __future__ import annotations

import time
import pytest


@pytest.mark.perf
class TestL2_05_PerformanceSLO:
    """§12 SLO · P95 / 吞吐 / 并发 / 资源。"""

    def test_TC_L104_L205_501_single_wp_total_execution_p95_le_3min(
        self, sut, make_execute_request, perf_sampler
    ) -> None:
        """TC-L104-L205-501 · §12.1 · 单 WP 总执行（典型 50 测试 + 3 predicates）P95 ≤ 3 min。"""
        for _ in range(50):
            t0 = time.perf_counter()
            sut.execute_wp(make_execute_request(wp_id=f"wp-p-{_}"))
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 180_000

    def test_TC_L104_L205_502_single_skill_invoke_p95_le_2min(
        self, skill_invoker, perf_sampler, mock_workspace_path
    ) -> None:
        """TC-L104-L205-502 · §12.1 · 单 Skill 调用 P95 ≤ 2 min。"""
        for i in range(30):
            t0 = time.perf_counter()
            skill_invoker.invoke(skill_intent="red_test_creation", skill_context={"budget_ms": 120_000}, workspace_path=mock_workspace_path)
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 120_000

    def test_TC_L104_L205_503_wal_append_fsync_p95_le_5ms(
        self, wal_buffer, make_wal_entry, perf_sampler
    ) -> None:
        """TC-L104-L205-503 · §12.1 · WAL append + fsync P95 ≤ 5 ms。"""
        for i in range(500):
            t0 = time.perf_counter()
            wal_buffer.append(make_wal_entry(wp_id="wp-wperf", sequence_id=i + 1))
            wal_buffer.fsync()
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 5

    def test_TC_L104_L205_504_worktree_create_p95_le_500ms(
        self, workspace_isolator, perf_sampler, mock_project_id
    ) -> None:
        """TC-L104-L205-504 · §12.1 · Worktree 创建 P95 ≤ 500 ms。"""
        for i in range(50):
            t0 = time.perf_counter()
            workspace_isolator.create(project_id=mock_project_id, wp_id=f"wp-wt-{i}")
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 500

    def test_TC_L104_L205_505_predicate_batch_20_p95_le_5s(
        self, sut, make_qgc, make_actual_state, perf_sampler
    ) -> None:
        """TC-L104-L205-505 · §12.1 · 20 predicates 批量执行 P95 ≤ 5 s。"""
        qgc = make_qgc(predicate_count=20)
        state = make_actual_state(all_pass=True)
        for _ in range(30):
            t0 = time.perf_counter()
            sut.run_predicates(qgc, state)
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 5000

    def test_TC_L104_L205_506_candidate_build_p95_le_1s(
        self, sut, make_final_snapshot, make_qgc, make_acl, perf_sampler
    ) -> None:
        """TC-L104-L205-506 · §12.1 · CandidateReport 构建 P95 ≤ 1 s。"""
        for _ in range(50):
            t0 = time.perf_counter()
            sut.build_candidate_report([make_final_snapshot()], make_qgc(), make_acl())
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 1000

    def test_TC_L104_L205_507_delegate_l2_06_p95_le_2s(
        self, sut, make_candidate_report, mock_l2_06_verifier, perf_sampler
    ) -> None:
        """TC-L104-L205-507 · §12.1 · 委托 L2-06 P95 ≤ 2 s。"""
        mock_l2_06_verifier.set_response(accepted=True)
        for _ in range(30):
            t0 = time.perf_counter()
            sut.delegate_verdict(make_candidate_report())
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 2000

    def test_TC_L104_L205_508_crash_recovery_replay_p95_le_10s(
        self, sut, seeded_wal_buffer, perf_sampler
    ) -> None:
        """TC-L104-L205-508 · §12.1 · Crash recovery 重放 P95 ≤ 10 s。"""
        for i in range(20):
            seeded_wal_buffer.seed_entries(wp_id=f"wp-crp-{i}", count=100)
            t0 = time.perf_counter()
            sut.crash_recovery(wp_id=f"wp-crp-{i}")
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 10_000

    def test_TC_L104_L205_509_probe_health_p95_le_100ms(
        self, sut, perf_sampler
    ) -> None:
        """TC-L104-L205-509 · §12.1 · Probe health 响应 P95 ≤ 100 ms。"""
        for _ in range(100):
            t0 = time.perf_counter()
            sut.handle_probe_health({"probe_type": "liveness"})
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 100

    def test_TC_L104_L205_510_halt_command_p95_le_500ms(
        self, sut, running_wp_fixture, perf_sampler
    ) -> None:
        """TC-L104-L205-510 · §12.1 · Halt command 响应 P95 ≤ 500 ms。"""
        for _ in range(50):
            cmd = {"halt_scope": "wp", "target": {"wp_id": running_wp_fixture}, "reason": "supervisor_intervention"}
            t0 = time.perf_counter()
            sut.handle_halt_command(cmd)
            perf_sampler.record((time.perf_counter() - t0) * 1000)
        assert perf_sampler.p95_ms() <= 500

    def test_TC_L104_L205_511_concurrent_5_wp_throughput_20_per_min(
        self, sut, make_execute_request, perf_sampler
    ) -> None:
        """TC-L104-L205-511 · §12.2 · 单机并发 WP=5 · 吞吐 ~ 20 WP/min。"""
        import concurrent.futures
        wp_ids = [f"wp-th-{i}" for i in range(20)]
        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            list(ex.map(lambda wp: sut.execute_wp(make_execute_request(wp_id=wp)), wp_ids))
        elapsed_s = time.perf_counter() - t0
        throughput_per_min = (len(wp_ids) / elapsed_s) * 60
        assert throughput_per_min >= 15, "§12.2 WP/min ~ 20 · 允许 25% 波动"

    def test_TC_L104_L205_512_single_wp_memory_peak_le_500mb(
        self, sut, make_execute_request, memory_sampler
    ) -> None:
        """TC-L104-L205-512 · §12.3 · 单 WP 内存峰值 ≤ 500 MB（含测试运行时峰值）。"""
        req = make_execute_request(wp_id="wp-mem")
        with memory_sampler.track() as s:
            sut.execute_wp(req)
        assert s.peak_mb <= 500
```

---

## §6 端到端 e2e 场景

> 真实链路 · 少量 mock 只替换外部 L2-06 / L1-05 / L1-09 · `@pytest.mark.e2e` · GWT 结构。

```python
# file: tests/l1_04/test_l2_05_s4_e2e.py
from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestL2_05_EndToEnd:
    """§5 P0/P1 时序图 + §13.2 TC-L204-L205-049~052 对标。"""

    def test_TC_L104_L205_601_e2e_from_artifacts_ready_to_delegated(
        self, e2e_harness, mock_project_id
    ) -> None:
        """TC-L104-L205-601 · e2e · §5.1 P0-1 · artifacts_ready → wp_exec → candidate_built → delegated_to_verifier。
        GIVEN L2-04 发出 dual_artifact_ready（1 WP · 50 测试 · 3 predicates）
        WHEN  L2-05 接收并执行
        THEN  产出 candidate_report + 委托 L2-06 + WAL 含 hash-chain
        """
        # GIVEN
        evt = e2e_harness.emit_artifacts_ready(project_id=mock_project_id, wp_ids=["wp-e2e-happy"], test_count=50, predicate_count=3)
        # WHEN
        e2e_harness.wait_for_delegation(wp_id="wp-e2e-happy", timeout_s=30)
        # THEN
        snap = e2e_harness.load_last_snapshot("wp-e2e-happy")
        assert snap.status == "DELEGATED_TO_VERIFIER"
        candidate = e2e_harness.load_candidate_by_wp("wp-e2e-happy")
        assert candidate.candidate_verdict_hint["all_tests_green"] is True
        # WAL + event
        assert e2e_harness.event_bus.has_event(stream="L1-04.L2-05.exec", event_type="delegated_to_verifier")

    def test_TC_L104_L205_602_e2e_self_repair_exhausted_delegates_exhausted(
        self, e2e_harness, mock_project_id
    ) -> None:
        """TC-L104-L205-602 · e2e · §5.3 P1-1 · self-repair 3 次全失败 · 委托 exhausted candidate。
        GIVEN skill 持续失败
        WHEN  L2-05 3 次 self-repair 均失败
        THEN  产 exhausted candidate · 仍委托 L2-06（no-self-verdict）
        """
        e2e_harness.force_skill_always_fail()
        e2e_harness.emit_artifacts_ready(project_id=mock_project_id, wp_ids=["wp-e2e-exh"])
        e2e_harness.wait_for_delegation(wp_id="wp-e2e-exh", timeout_s=60)
        cr = e2e_harness.load_candidate_by_wp("wp-e2e-exh")
        assert cr.candidate_verdict_hint["no_self_repair_exhausted"] is False
        assert cr.self_repair_summary["attempts"] == 3

    def test_TC_L104_L205_603_e2e_crash_recovery_resumes_from_wal(
        self, e2e_harness, mock_project_id
    ) -> None:
        """TC-L104-L205-603 · e2e · §5.4 P1-2 · 崩溃恢复 · WAL 重放 · 从最后 attempt 续跑。
        GIVEN attempt=1 进行中 · 模拟 crash
        WHEN  重启 L2-05
        THEN  crash_recovery 读 WAL · 重建 snapshot · resume_from_wal=True 继续
        """
        e2e_harness.start_wp(wp_id="wp-e2e-crash", project_id=mock_project_id)
        e2e_harness.wait_for_phase("wp-e2e-crash", phase="REPAIRING")
        e2e_harness.simulate_process_crash()
        # 重启
        e2e_harness.restart()
        e2e_harness.wait_for_delegation(wp_id="wp-e2e-crash", timeout_s=60)
        snap = e2e_harness.load_last_snapshot("wp-e2e-crash")
        assert snap.status in {"DELEGATED_TO_VERIFIER", "EXHAUSTED"}
        assert e2e_harness.event_bus.has_event(event_type="crash_detected")

    def test_TC_L104_L205_604_e2e_supervisor_halt_scope_l1_04(
        self, e2e_harness, mock_project_id
    ) -> None:
        """TC-L104-L205-604 · e2e · §5.5 P1-3 · L1-07 halt scope=l1_04 · 所有活跃 WP stop + 导 partial candidates。
        GIVEN 3 WP 在跑
        WHEN  L1-07 发 IC-14 halt(scope=l1_04)
        THEN  3 WP 全部 halt + 各自产 partial candidate 委托 L2-06
        """
        e2e_harness.start_wps(wp_ids=[f"wp-e2e-h-{i}" for i in range(3)], project_id=mock_project_id)
        e2e_harness.wait_all_in_progress(timeout_s=15)
        e2e_harness.supervisor_send_halt(scope="l1_04", reason="catastrophic_divergence")
        e2e_harness.wait_all_halted(timeout_s=30)
        for i in range(3):
            cr = e2e_harness.load_candidate_by_wp(f"wp-e2e-h-{i}")
            assert cr is not None, "§6.11 halt 仍构 partial candidate"
```

---

## §7 测试 fixture（mock pid / mock clock / mock event bus / mock worktree / mock wal / mock skill invoker）

> 放 `tests/l1_04/conftest.py`；session / function scope 按表述。

```python
# file: tests/l1_04/conftest.py
from __future__ import annotations

import uuid
import pytest
from typing import Callable, Any
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id() -> str:
    """生成 PM-14 合法 project_id（uuid-v7 simulated）。"""
    return f"proj-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def mock_clock() -> Callable[[], int]:
    """可步进的单调时钟（ms）。"""
    t = {"now": 0}
    def _now() -> int: return t["now"]
    def _advance(ms: int) -> None: t["now"] += ms
    _now.advance = _advance  # type: ignore[attr-defined]
    return _now


@pytest.fixture
def mock_event_bus():
    """记录 L1-08 event · 支持 has_event / captured。"""
    bus = MagicMock()
    bus.captured = []
    def _append(evt): bus.captured.append(evt)
    bus.append_event = _append
    bus.has_event = lambda stream=None, event_type=None: any(
        (stream is None or e.stream == stream) and (event_type is None or e.event_type == event_type)
        for e in bus.captured
    )
    return bus


@pytest.fixture
def wal_buffer(tmp_path):
    """真实 WALBuffer（文件后端 · 但目录用 tmp）。"""
    from app.l1_04.l2_05.wal import WALBuffer
    return WALBuffer(base_dir=str(tmp_path / "wal"), fsync_every_n=1)


@pytest.fixture
def seeded_wal_buffer(wal_buffer, make_wal_entry):
    """预置 WAL 条目 + 可注入 hash 损坏的辅助 fixture。"""
    class _Seeded:
        def __init__(self, buf): self.buf = buf
        def seed_entries(self, wp_id: str, count: int) -> None:
            for i in range(count):
                self.buf.append(make_wal_entry(wp_id=wp_id, sequence_id=i + 1))
        def corrupt_entry_hash(self, wp_id: str, seq: int) -> None:
            self.buf.corrupt(wp_id=wp_id, sequence_id=seq)
    return _Seeded(wal_buffer)


@pytest.fixture
def skill_invoker(mock_clock):
    """Mock L1-05 SkillInvoker · 默认成功 · 可切换 flaky / slow。"""
    inv = MagicMock()
    def _invoke(skill_intent, skill_context, workspace_path):
        return MagicMock(status="success", invoke_id=str(uuid.uuid4()), duration_ms=100, token_cost=1000, output_summary="", artifacts_written=[])
    inv.invoke = _invoke
    return inv


@pytest.fixture
def flaky_skill_invoker(skill_invoker):
    """计数失败 N 次后转成功。"""
    state = {"fail_left": 0}
    orig = skill_invoker.invoke
    def _invoke(*args, **kwargs):
        if state["fail_left"] > 0:
            state["fail_left"] -= 1
            raise Exception("E_L205_L205_SKILL_INVOKE_FAIL")
        return orig(*args, **kwargs)
    skill_invoker.invoke = _invoke
    skill_invoker.set_fail_count = lambda n: state.update(fail_left=n)
    return skill_invoker


@pytest.fixture
def workspace_isolator(tmp_path):
    from app.l1_04.l2_05.workspace import WorkspaceIsolator
    return WorkspaceIsolator(base_path=str(tmp_path / "workspaces"))


@pytest.fixture
def mock_l2_06_verifier():
    """Mock IC-L2-06 端 · 控制 accept / unavailable。"""
    v = MagicMock()
    v.last_request = None
    v.set_response = lambda accepted, estimated_verdict_ms=1000: setattr(v, "_resp", (accepted, estimated_verdict_ms))
    v.set_unavailable = lambda fail_count: setattr(v, "_unavailable", fail_count)
    return v


@pytest.fixture
def perf_sampler():
    """收集耗时 + P95 统计。"""
    class _S:
        def __init__(self): self._xs: list[float] = []
        def record(self, ms: float) -> None: self._xs.append(ms)
        def p95_ms(self) -> float:
            xs = sorted(self._xs)
            return xs[int(len(xs) * 0.95) - 1] if xs else 0.0
    return _S()
```

---

## §8 集成点用例（与兄弟 L2 协作 · L2-03 / L2-04 / L2-06 / L2-07）

> §2.9 与兄弟 L2 的边界断言 · mock 其他 L2 但真实跑 L2-05。

```python
# file: tests/l1_04/test_l2_05_s4_integration.py
from __future__ import annotations

import pytest


class TestL2_05_CrossL2Integration:
    """与 L2-03 / L2-04 / L2-06 / L2-07 的集成。"""

    def test_TC_L104_L205_801_integrate_with_l2_03_testsuite_read(
        self, sut, mock_l2_03_repo, make_execute_request
    ) -> None:
        """TC-L104-L205-801 · §2.9 · 本 L2 通过 blueprint_id 间接读 L2-03 的 TestSuite skeleton。"""
        mock_l2_03_repo.seed_skeleton(blueprint_id="bp-int-03", skeleton_count=5)
        req = make_execute_request(wp_id="wp-int-03", blueprint_id="bp-int-03")
        resp = sut.execute_wp(req)
        assert resp.final_state["test_outcomes"]["total_tests"] == 5

    def test_TC_L104_L205_802_integrate_with_l2_04_qgc_read(
        self, sut, mock_l2_04_qgc_repo, make_artifacts_ready_event
    ) -> None:
        """TC-L104-L205-802 · §3.1 · L2-04 是入站触发源 · 读 qgc + acl。"""
        mock_l2_04_qgc_repo.seed(qgc_id="qgc-int-04", acl_id="acl-int-04")
        evt = make_artifacts_ready_event(qgc_id="qgc-int-04", acl_id="acl-int-04")
        resp = sut.on_artifacts_ready(evt)
        assert resp.accepted is True

    def test_TC_L104_L205_803_integrate_with_l2_06_no_self_verdict_enforced(
        self, sut, make_candidate_report, mock_l2_06_verifier
    ) -> None:
        """TC-L104-L205-803 · §2.9 + D4 · no-self-verdict 强制 · 任何 candidate 必经 L2-06。"""
        mock_l2_06_verifier.set_response(accepted=True)
        cr = make_candidate_report()
        sut.delegate_verdict(cr)
        assert mock_l2_06_verifier.last_request is not None, "L2-05 绝不自给 verdict"

    def test_TC_L104_L205_804_integrate_with_l2_07_rollback_routing(
        self, sut, mock_project_id
    ) -> None:
        """TC-L104-L205-804 · §3.10 · 接收 L2-07 的 4 种 rollback 决策 · 路由正确。"""
        for d in ("retry_wp", "retry_blueprint", "escalate_supervisor", "reject_wp"):
            ack = sut.handle_rollback_hint({
                "rollback_decision": d, "wp_id": f"wp-int-{d}",
                "project_id": mock_project_id, "candidate_id_triggering": "cr-x",
            })
            assert ack.acknowledged is True
```

---

## §9 边界 / edge case（空/超大/并发/崩溃/超时/资源耗尽）

> §13.2 TC-060~065 + §11.2 降级状态机 + §12.4 退化边界 · 不少于 5 条。

```python
# file: tests/l1_04/test_l2_05_s4_boundary.py
from __future__ import annotations

import pytest


class TestL2_05_Boundary:
    """边界 · ≥ 5 条 · 覆盖 §12.4 退化边界 + §11.2 降级状态机 + §13.2 060~065。"""

    def test_TC_L104_L205_901_empty_wp_no_tests_still_produces_candidate(
        self, sut, make_execute_request_no_tests
    ) -> None:
        """TC-L104-L205-901 · §13.2 TC-060 · 空 WP（无测试）· red_count=0 · green_count=0 · 仍构 candidate。"""
        req = make_execute_request_no_tests(wp_id="wp-empty")
        resp = sut.execute_wp(req)
        assert resp.success is True
        assert resp.final_state["test_outcomes"]["total_tests"] == 0
        assert resp.candidate_report_id is not None

    def test_TC_L104_L205_902_huge_wp_1000_tests_still_completes(
        self, sut, make_execute_request_with_count
    ) -> None:
        """TC-L104-L205-902 · §13.2 TC-061 · 超大 WP（1000 测试）· 不超时 · 吞吐退化可接受。"""
        req = make_execute_request_with_count(wp_id="wp-huge", test_count=1000)
        resp = sut.execute_wp(req)
        assert resp.success is True
        assert resp.final_state["test_outcomes"]["total_tests"] == 1000

    def test_TC_L104_L205_903_wp_execution_timeout_3min_halt(
        self, sut, make_execute_request, slow_skill_invoker
    ) -> None:
        """TC-L104-L205-903 · §12.1 + §12.4 · 执行超时 3 min 边界 · HALT_WP。"""
        slow_skill_invoker.set_sleep_ms(185_000)
        req = make_execute_request(wp_id="wp-edge-tmo")
        from app.l1_04.l2_05.errors import L205ExecutionError
        with pytest.raises(L205ExecutionError) as exc:
            sut.execute_wp(req)
        assert exc.value.code == "E_L205_L205_WP_TIMEOUT"

    def test_TC_L104_L205_904_disk_full_wal_write_fail_halts(
        self, wal_buffer, make_wal_entry, wal_disk_full
    ) -> None:
        """TC-L104-L205-904 · §13.2 TC-065 · 磁盘满 · WAL 写失败 · 重试 3 次 · HALT。"""
        wal_disk_full()
        from app.l1_04.l2_05.errors import L205ExecutionError
        with pytest.raises(L205ExecutionError) as exc:
            wal_buffer.append(make_wal_entry(wp_id="wp-edge-disk"))
        assert exc.value.code == "E_L205_L205_WAL_WRITE_FAIL"

    def test_TC_L104_L205_905_test_process_oom_crash_self_repair_then_exhausted(
        self, sut, make_execute_request, oom_test_runner
    ) -> None:
        """TC-L104-L205-905 · §13.2 TC-063 · 测试子进程 OOM 崩溃 · self-repair · 再失败 exhausted。"""
        oom_test_runner.crash_always()
        req = make_execute_request(wp_id="wp-oom")
        resp = sut.execute_wp(req)
        assert resp.success is False
        assert "E_L205_L205_TEST_RUN_CRASH" in resp.error_codes_seen
        assert "E_L205_L205_SELF_REPAIR_EXHAUSTED" in resp.error_codes_seen

    def test_TC_L104_L205_906_concurrent_exceeds_limit_queues_fifo(
        self, sut, make_execute_request, concurrency_monitor
    ) -> None:
        """TC-L104-L205-906 · §12.2 + §4.4 · 并发 > 上限 5 · 后续 WP FIFO 排队。"""
        wp_ids = [f"wp-cc-{i:02d}" for i in range(8)]
        started_order = concurrency_monitor.record_starts_for(sut, wp_ids, max_inflight=5)
        # 前 5 个立刻开始；第 6-8 在有 slot 后按 FIFO 顺序开始
        assert started_order[:5] == wp_ids[:5]
        assert concurrency_monitor.max_inflight_observed <= 5
```

---

*— 填充完成 · 30+ 覆盖度表 · 90+ TC · 24 错误码全覆盖 · 10 IC 契约 · 12 SLO · 4 e2e · 4 集成 · 6 边界 —*
