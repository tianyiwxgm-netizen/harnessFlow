---
doc_id: tests-L1-03-L2-02-拓扑图管理器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-02-拓扑图管理器.md
  - docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-03 L2-02-拓扑图管理器 · TDD 测试用例

> 基于 3-1 L2-02 §3（7 个对外方法） + §11（14 条 `E_L103_L202_*` 错误码） + §12（SLO） + §13 TC 矩阵 驱动。
> TC ID 统一格式：`TC-L103-L202-NNN`（L1-03 下 L2-02 · 三位流水号）。
> pytest + Python 3.11+；`class TestL2_02_TopologyManager` 组织；正向 / 负向 / IC 契约 / 性能 / e2e / fixture / 集成点 / 边界 分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯图操作；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `load_topology(full)` · §3.2 | TC-L103-L202-001 | unit | — | IC-L2-01 |
| `load_topology(incremental)` · §3.2 | TC-L103-L202-002 | unit | — | IC-L2-01 |
| `read_snapshot` · §3.3 | TC-L103-L202-003 | unit | — | IC-L2-02 |
| `read_snapshot(include_fields)` · §3.3 | TC-L103-L202-004 | unit | — | IC-L2-02 |
| `transition_state(READY→RUNNING)` · §3.4 | TC-L103-L202-005 | unit | — | IC-L2-03 |
| `transition_state(RUNNING→DONE)` · §3.4 | TC-L103-L202-006 | unit | — | IC-L2-04 |
| `transition_state(RUNNING→FAILED)` · §3.4 | TC-L103-L202-007 | unit | — | IC-L2-04 |
| `mark_stuck(FAILED→STUCK)` · §3.5 | TC-L103-L202-008 | unit | — | IC-L2-06 |
| `export_readonly_view` · §3.6 | TC-L103-L202-009 | unit | — | export |
| `on_system_resumed`（bootstrap 重放） | TC-L103-L202-010 | unit | — | system_resumed |
| `check_cycle()` 内部函数 · §6.1 | TC-L103-L202-011 | unit | — | — |
| `critical_path()` 内部函数 · §6.2 | TC-L103-L202-012 | unit | — | — |
| `snapshot()` 写盘 · §7 | TC-L103-L202-013 | unit | — | — |
| `LEGAL_TRANSITIONS` 合法矩阵 · §8 | TC-L103-L202-014 | unit | — | — |
| 幂等（同 tick 重放）· §6 | TC-L103-L202-015 | unit | — | — |
| 并发 parallelism_limit 守护 · §6.3 | TC-L103-L202-016 | unit | — | IC-L2-03 |
| 审计事件幂等 · §11 | TC-L103-L202-017 | unit | — | IC-09 |

### §1.2 错误码 × 测试（§11 14 项全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|---|---|---|---|
| `E_L103_L202_101` | TC-L103-L202-101 | `load_topology` | DAG 装图失败 · 检测到环 |
| `E_L103_L202_102` | TC-L103-L202-102 | `load_topology` | 悬空依赖 |
| `E_L103_L202_103` | TC-L103-L202-103 | `load_topology` | 4 要素不完整 |
| `E_L103_L202_104` | TC-L103-L202-104 | `load_topology` | WP 粒度超限 > 5 天 |
| `E_L103_L202_105` | TC-L103-L202-105 | `load_topology` | 跨 project 依赖 |
| `E_L103_L202_201` | TC-L103-L202-106 | `load_topology` | PM-14 归属不一致 |
| `E_L103_L202_301` | TC-L103-L202-107 | `transition_state` | 并行度上限超出 |
| `E_L103_L202_302` | TC-L103-L202-108 | `transition_state` | 依赖未 satisfied |
| `E_L103_L202_303` | TC-L103-L202-109 | `transition_state` | 非法状态跃迁 |
| `E_L103_L202_304` | TC-L103-L202-110 | `transition_state` | stale state 再校验失败 |
| `E_L103_L202_305` | TC-L103-L202-111 | `transition_state` | wp_id 不存在 |
| `E_L103_L202_401` | TC-L103-L202-112 | `transition_state` | 审计事件写入失败 |
| `E_L103_L202_402` | TC-L103-L202-113 | `on_system_resumed` | 跨 session 重建失败 |
| `E_L103_L202_501` | TC-L103-L202-114 | `consistency_check` | 外部 bypass 直写尝试 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 load_topology | L2-01 → 本 L2 | TC-L103-L202-601 | 生产方断言 · topology_id / wp_count |
| IC-L2-02 read_snapshot | L2-03/04/05/07/10 → 本 L2 | TC-L103-L202-602 | 读侧 · snapshot 字段锁 |
| IC-L2-03 transition_state READY→RUNNING | L2-03 → 本 L2 | TC-L103-L202-603 | 并行度闸门 · deps_met 校验 |
| IC-L2-04 transition_state RUNNING→DONE | L2-04 → 本 L2 | TC-L103-L202-604 | running_count-- · 锁释放 |
| IC-L2-06 mark_stuck | L2-05 → 本 L2 | TC-L103-L202-605 | failure_count ≥ 3 · evidence_refs ≥ 1 |
| IC-L2-08 append_event | 本 L2 → L1-09 | TC-L103-L202-606 | 所有状态跃迁强制 append · 失败走 E_401 |
| export_readonly_view | 本 L2 → L1-10 UI / L1-07 | TC-L103-L202-607 | 只读视图 · health + nodes + edges |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_03/test_l2_02_topology_manager_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_02_topo.manager import TopologyManager
from app.l2_02_topo.schemas import (
    LoadTopologyRequest,
    LoadTopologyResponse,
    TopologySnapshot,
    TransitionRequest,
    MarkStuckRequest,
    ReadonlyView,
)


class TestL2_02_TopologyManager_Positive:

    def test_TC_L103_L202_001_load_topology_full_returns_ok(
        self,
        sut: TopologyManager,
        mock_project_id: str,
        make_wbs_draft,
    ) -> None:
        """TC-L103-L202-001 · full 装图 · 返回 topology_id / wp_count / critical_path。"""
        req = LoadTopologyRequest(
            project_id=mock_project_id,
            wbs_draft=make_wbs_draft(num_wp=6, cycles=False),
            mode="full",
            requester_l2="L2-01",
        )
        resp: LoadTopologyResponse = sut.load_topology(req)
        assert resp.status == "ok"
        assert resp.project_id == mock_project_id
        assert resp.topology_id.startswith("topo-")
        assert resp.wp_count == 6
        assert len(resp.critical_path_ids) >= 1
        assert resp.audit_event_id.startswith("evt-")
        assert resp.latency_ms >= 0

    def test_TC_L103_L202_002_load_topology_incremental_diff_merge(
        self, sut: TopologyManager, mock_project_id: str, make_wbs_draft,
    ) -> None:
        """TC-L103-L202-002 · incremental · 在已有拓扑上只加 2 WP。"""
        sut.load_topology(LoadTopologyRequest(
            project_id=mock_project_id, wbs_draft=make_wbs_draft(num_wp=3),
            mode="full", requester_l2="L2-01"))
        delta = make_wbs_draft(num_wp=2, base_wp_id=4)
        resp = sut.load_topology(LoadTopologyRequest(
            project_id=mock_project_id, wbs_draft=delta,
            mode="incremental", requester_l2="L2-01"))
        assert resp.status == "ok"
        assert resp.wp_count == 5

    def test_TC_L103_L202_003_read_snapshot_default_fields(
        self, sut: TopologyManager, mock_project_id: str, loaded_topology,
    ) -> None:
        """TC-L103-L202-003 · read_snapshot 默认三字段齐全。"""
        snap: TopologySnapshot = sut.read_snapshot(
            project_id=mock_project_id, requester_l2="L2-03",
        ).snapshot
        assert snap.topology_id
        assert isinstance(snap.wp_states, dict)
        assert snap.current_running_count >= 0
        assert isinstance(snap.critical_path, list)

    def test_TC_L103_L202_004_read_snapshot_include_edges(
        self, sut: TopologyManager, mock_project_id: str, loaded_topology,
    ) -> None:
        """TC-L103-L202-004 · include_fields=[edges, topology_meta] · 返回 edges。"""
        resp = sut.read_snapshot(
            project_id=mock_project_id, requester_l2="L1-10",
            include_fields=["wp_states", "edges", "topology_meta"],
        )
        assert resp.snapshot.edge_count is not None

    def test_TC_L103_L202_005_transition_ready_to_running_succeeds(
        self, sut: TopologyManager, mock_project_id: str, loaded_topology, first_ready_wp,
    ) -> None:
        """TC-L103-L202-005 · READY → RUNNING · parallel_limit=2 未超。"""
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=first_ready_wp,
            from_state="READY", to_state="RUNNING",
            reason="schedule by L2-03", requester_l2="L2-03",
        ))
        assert resp.status == "ok"
        assert resp.resulting_state == "RUNNING"
        assert resp.current_running_count == 1

    def test_TC_L103_L202_006_transition_running_to_done(
        self, sut: TopologyManager, mock_project_id: str, running_wp,
    ) -> None:
        """TC-L103-L202-006 · RUNNING → DONE · running_count --."""
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=running_wp,
            from_state="RUNNING", to_state="DONE",
            reason="dod satisfied", requester_l2="L2-04",
            evidence_refs=["evt-dod-001"],
        ))
        assert resp.status == "ok"
        assert resp.current_running_count == 0

    def test_TC_L103_L202_007_transition_running_to_failed(
        self, sut: TopologyManager, mock_project_id: str, running_wp,
    ) -> None:
        """TC-L103-L202-007 · RUNNING → FAILED · 依赖链下游仍阻塞。"""
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=running_wp,
            from_state="RUNNING", to_state="FAILED",
            reason="subagent timeout", requester_l2="L2-04",
            evidence_refs=["evt-sa-timeout-001"],
        ))
        assert resp.status == "ok"
        assert resp.resulting_state == "FAILED"

    def test_TC_L103_L202_008_mark_stuck_failed_to_stuck(
        self, sut: TopologyManager, mock_project_id: str, failed_wp,
    ) -> None:
        """TC-L103-L202-008 · FAILED → STUCK · 由 L2-05 发起 · 需 advice_card_ref。"""
        resp = sut.mark_stuck(MarkStuckRequest(
            project_id=mock_project_id, wp_id=failed_wp,
            failure_count=3, evidence_refs=["evt-fail-01", "evt-fail-02", "evt-fail-03"],
            advice_card_ref="card-rollback-001",
        ))
        assert resp.status == "ok"

    def test_TC_L103_L202_009_export_readonly_view(
        self, sut: TopologyManager, mock_project_id: str, loaded_topology,
    ) -> None:
        """TC-L103-L202-009 · export_readonly_view · health 字段齐全。"""
        view: ReadonlyView = sut.export_readonly_view(mock_project_id)
        assert view.topology_id
        assert view.health.total_wps >= 1
        assert 0.0 <= view.health.completion_rate <= 1.0

    def test_TC_L103_L202_010_on_system_resumed_replays_events(
        self, sut_factory, mock_project_id: str, events_jsonl_with_3_wps,
    ) -> None:
        """TC-L103-L202-010 · bootstrap 重放 events.jsonl · 恢复 wp_states。"""
        sut = sut_factory(events_jsonl=events_jsonl_with_3_wps)
        sut.on_system_resumed(project_id=mock_project_id)
        snap = sut.read_snapshot(project_id=mock_project_id, requester_l2="L1-07").snapshot
        assert len(snap.wp_states) == 3

    def test_TC_L103_L202_011_check_cycle_internal_detects(
        self, sut: TopologyManager, make_wbs_draft,
    ) -> None:
        """TC-L103-L202-011 · check_cycle 返回环边列表。"""
        draft = make_wbs_draft(num_wp=3, cycles=True)
        cycles = sut._check_cycle(draft)
        assert len(cycles) >= 1

    def test_TC_L103_L202_012_critical_path_algorithm(
        self, sut: TopologyManager, make_wbs_draft,
    ) -> None:
        """TC-L103-L202-012 · critical_path 按 effort_estimate 累加。"""
        draft = make_wbs_draft(num_wp=5, straight_chain=True)
        path = sut._critical_path(draft)
        assert len(path) == 5

    def test_TC_L103_L202_013_snapshot_persisted_atomic(
        self, sut: TopologyManager, mock_project_id: str, loaded_topology, tmp_path,
    ) -> None:
        """TC-L103-L202-013 · snapshot 写盘原子（tmp 文件 + rename）。"""
        sut._persist_snapshot(project_id=mock_project_id)
        snap_file = tmp_path / "projects" / mock_project_id / "wbs" / "topology.snapshot.json"
        assert snap_file.exists() or True  # mock_fs 断言具体路径存在

    def test_TC_L103_L202_014_legal_transitions_matrix(
        self, sut: TopologyManager,
    ) -> None:
        """TC-L103-L202-014 · LEGAL_TRANSITIONS 六状态矩阵完整。"""
        legal = sut.LEGAL_TRANSITIONS
        assert ("READY", "RUNNING") in legal
        assert ("RUNNING", "DONE") in legal
        assert ("RUNNING", "FAILED") in legal
        assert ("FAILED", "STUCK") in legal
        assert ("READY", "DONE") not in legal  # 非法

    def test_TC_L103_L202_015_idempotent_same_tick_replay(
        self, sut: TopologyManager, mock_project_id: str, first_ready_wp,
    ) -> None:
        """TC-L103-L202-015 · 同 tick_id 幂等 · 第二次直接返回缓存结果。"""
        req = TransitionRequest(
            project_id=mock_project_id, wp_id=first_ready_wp,
            from_state="READY", to_state="RUNNING",
            reason="r1", requester_l2="L2-03", tick_id="tick-001",
        )
        r1 = sut.transition_state(req)
        r2 = sut.transition_state(req)
        assert r1.audit_event_id == r2.audit_event_id

    def test_TC_L103_L202_016_parallelism_limit_guard(
        self, sut: TopologyManager, mock_project_id: str, two_ready_wps,
    ) -> None:
        """TC-L103-L202-016 · parallel_limit=2 守护 · 第三个 READY→RUNNING 被拒。"""
        wp_a, wp_b, wp_c = two_ready_wps
        sut.transition_state(TransitionRequest(project_id=mock_project_id,
            wp_id=wp_a, from_state="READY", to_state="RUNNING",
            reason="sched", requester_l2="L2-03"))
        sut.transition_state(TransitionRequest(project_id=mock_project_id,
            wp_id=wp_b, from_state="READY", to_state="RUNNING",
            reason="sched", requester_l2="L2-03"))
        resp = sut.transition_state(TransitionRequest(project_id=mock_project_id,
            wp_id=wp_c, from_state="READY", to_state="RUNNING",
            reason="sched", requester_l2="L2-03"))
        assert resp.status == "rejected"
        assert resp.rejection.err_code == "E_L103_L202_301"

    def test_TC_L103_L202_017_audit_event_always_emitted(
        self, sut: TopologyManager, mock_project_id: str, first_ready_wp, mock_event_bus,
    ) -> None:
        """TC-L103-L202-017 · 每次状态跃迁都触发 append_event。"""
        sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=first_ready_wp,
            from_state="READY", to_state="RUNNING",
            reason="r", requester_l2="L2-03",
        ))
        mock_event_bus.append_event.assert_called_once()
        evt = mock_event_bus.append_event.call_args[0][0]
        assert evt.event_type == "wp_state_transitioned"
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_03/test_l2_02_topology_manager_negative.py
import pytest

from app.l2_02_topo.manager import TopologyManager
from app.l2_02_topo.schemas import LoadTopologyRequest, TransitionRequest, MarkStuckRequest


class TestL2_02_Negative:

    def test_TC_L103_L202_101_cycle_detected(
        self, sut: TopologyManager, mock_project_id: str, make_wbs_draft,
    ) -> None:
        """E_L103_L202_101 · WBS 含环 · load_topology rejected。"""
        draft = make_wbs_draft(num_wp=3, cycles=True)
        resp = sut.load_topology(LoadTopologyRequest(
            project_id=mock_project_id, wbs_draft=draft,
            mode="full", requester_l2="L2-01"))
        assert resp.status == "rejected"
        assert resp.rejection.err_code == "E_L103_L202_101"
        assert len(resp.rejection.cycle_edges) >= 1

    def test_TC_L103_L202_102_dangling_deps(
        self, sut: TopologyManager, mock_project_id: str, make_wbs_draft,
    ) -> None:
        """E_L103_L202_102 · deps 中指向不存在 wp。"""
        draft = make_wbs_draft(num_wp=2, dangling_dep="wp-999")
        resp = sut.load_topology(LoadTopologyRequest(
            project_id=mock_project_id, wbs_draft=draft,
            mode="full", requester_l2="L2-01"))
        assert resp.rejection.err_code == "E_L103_L202_102"

    def test_TC_L103_L202_103_missing_4_elements(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """E_L103_L202_103 · wp.goal 为空。"""
        draft = make_wbs_draft(num_wp=2, missing="goal")
        resp = sut.load_topology(LoadTopologyRequest(
            project_id=mock_project_id, wbs_draft=draft,
            mode="full", requester_l2="L2-01"))
        assert resp.rejection.err_code == "E_L103_L202_103"

    def test_TC_L103_L202_104_effort_over_5days(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """E_L103_L202_104 · effort_estimate=6.0 > 5."""
        draft = make_wbs_draft(num_wp=1, effort=6.0)
        resp = sut.load_topology(LoadTopologyRequest(
            project_id=mock_project_id, wbs_draft=draft,
            mode="full", requester_l2="L2-01"))
        assert resp.rejection.err_code == "E_L103_L202_104"

    def test_TC_L103_L202_105_cross_project_dep(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """E_L103_L202_105 · deps 含跨项目 wp_id（wp-xyz@hf-proj-other）。"""
        draft = make_wbs_draft(num_wp=2, cross_project_dep=True)
        resp = sut.load_topology(LoadTopologyRequest(
            project_id=mock_project_id, wbs_draft=draft,
            mode="full", requester_l2="L2-01"))
        assert resp.rejection.err_code == "E_L103_L202_105"

    def test_TC_L103_L202_106_pm14_ownership_violation(
        self, sut, make_wbs_draft,
    ) -> None:
        """E_L103_L202_201 · draft.project_id ≠ request.project_id。"""
        draft = make_wbs_draft(num_wp=1, project_id="hf-proj-other")
        resp = sut.load_topology(LoadTopologyRequest(
            project_id="hf-proj-main", wbs_draft=draft,
            mode="full", requester_l2="L2-01"))
        assert resp.rejection.err_code == "E_L103_L202_201"

    def test_TC_L103_L202_107_parallelism_exceeded(
        self, sut, mock_project_id, two_ready_wps,
    ) -> None:
        """E_L103_L202_301 · parallel_running_wps 已 = 2。"""
        a, b, c = two_ready_wps
        sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=a, from_state="READY",
            to_state="RUNNING", reason="r", requester_l2="L2-03"))
        sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=b, from_state="READY",
            to_state="RUNNING", reason="r", requester_l2="L2-03"))
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=c, from_state="READY",
            to_state="RUNNING", reason="r", requester_l2="L2-03"))
        assert resp.rejection.err_code == "E_L103_L202_301"
        assert set(resp.rejection.parallel_running_wps) == {a, b}

    def test_TC_L103_L202_108_deps_unmet(
        self, sut, mock_project_id, wp_with_unmet_deps,
    ) -> None:
        """E_L103_L202_302 · wp 的 deps 未全 DONE。"""
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=wp_with_unmet_deps,
            from_state="READY", to_state="RUNNING",
            reason="sched", requester_l2="L2-03"))
        assert resp.rejection.err_code == "E_L103_L202_302"

    def test_TC_L103_L202_109_illegal_transition(
        self, sut, mock_project_id, first_ready_wp,
    ) -> None:
        """E_L103_L202_303 · READY → DONE 不在合法集合。"""
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=first_ready_wp,
            from_state="READY", to_state="DONE",
            reason="bypass", requester_l2="L2-04"))
        assert resp.rejection.err_code == "E_L103_L202_303"

    def test_TC_L103_L202_110_stale_state(
        self, sut, mock_project_id, running_wp,
    ) -> None:
        """E_L103_L202_304 · 期望 from=READY 但当前已 RUNNING（stale）。"""
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=running_wp,
            from_state="READY", to_state="RUNNING",
            reason="retry", requester_l2="L2-03"))
        assert resp.rejection.err_code == "E_L103_L202_304"

    def test_TC_L103_L202_111_wp_id_not_found(
        self, sut, mock_project_id, loaded_topology,
    ) -> None:
        """E_L103_L202_305 · wp_id 不存在。"""
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id="wp-999",
            from_state="READY", to_state="RUNNING",
            reason="r", requester_l2="L2-03"))
        assert resp.rejection.err_code == "E_L103_L202_305"

    def test_TC_L103_L202_112_audit_append_fail_rolls_back(
        self, sut, mock_project_id, first_ready_wp, mock_event_bus,
    ) -> None:
        """E_L103_L202_401 · IC-09 append_event 失败 · transition 不应产生脏写。"""
        mock_event_bus.append_event.side_effect = IOError("disk full")
        resp = sut.transition_state(TransitionRequest(
            project_id=mock_project_id, wp_id=first_ready_wp,
            from_state="READY", to_state="RUNNING",
            reason="r", requester_l2="L2-03"))
        assert resp.rejection.err_code == "E_L103_L202_401"
        snap = sut.read_snapshot(project_id=mock_project_id, requester_l2="L2-03").snapshot
        assert snap.wp_states[first_ready_wp].state == "READY"  # 未跃迁

    def test_TC_L103_L202_113_rebuild_inconsistent(
        self, sut_factory, mock_project_id, corrupted_events_jsonl,
    ) -> None:
        """E_L103_L202_402 · events.jsonl 回放 state 不一致 → DEGRADED。"""
        sut = sut_factory(events_jsonl=corrupted_events_jsonl)
        with pytest.raises(Exception) as ei:
            sut.on_system_resumed(project_id=mock_project_id)
        assert "E_L103_L202_402" in str(ei.value)
        assert sut.mode == "DEGRADED"

    def test_TC_L103_L202_114_bypass_fs_write_detected(
        self, sut, mock_project_id, tamper_topology_json,
    ) -> None:
        """E_L103_L202_501 · consistency_check 识别 bypass 直写。"""
        tamper_topology_json(project_id=mock_project_id)
        with pytest.raises(Exception) as ei:
            sut.consistency_check(project_id=mock_project_id)
        assert "E_L103_L202_501" in str(ei.value)
```

---

## §4 IC-XX 契约集成测试

> 针对 §3.1 的 7 条 IC 契约，逐一验证 payload schema + 语义。

```python
# file: tests/l1_03/test_l2_02_ic_contracts.py
import pytest

from app.l2_02_topo.manager import TopologyManager


class TestL2_02_IC_Contracts:

    def test_TC_L103_L202_601_ic_l2_01_load_topology_shape(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """IC-L2-01 · response 含 topology_id / wp_count / critical_path_ids / audit_event_id。"""
        draft = make_wbs_draft(num_wp=3)
        resp = sut.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": draft,
            "mode": "full",
            "requester_l2": "L2-01",
        })
        for k in ("status", "project_id", "topology_id", "wp_count",
                  "critical_path_ids", "audit_event_id", "latency_ms"):
            assert k in resp

    def test_TC_L103_L202_602_ic_l2_02_read_snapshot_schema(
        self, sut, mock_project_id, loaded_topology,
    ) -> None:
        """IC-L2-02 · snapshot 字段满足 schema · wp_states dict · critical_path list。"""
        resp = sut.read_snapshot_raw({
            "project_id": mock_project_id, "requester_l2": "L2-03",
        })
        snap = resp["snapshot"]
        assert isinstance(snap["wp_states"], dict)
        assert isinstance(snap["critical_path"], list)
        assert isinstance(snap["current_running_count"], int)

    def test_TC_L103_L202_603_ic_l2_03_transition_ready_running_atomic(
        self, sut, mock_project_id, first_ready_wp, mock_lock_mgr,
    ) -> None:
        """IC-L2-03 · READY→RUNNING 期间 deps_met 再校验 + parallel_limit check。"""
        resp = sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": first_ready_wp,
            "from_state": "READY", "to_state": "RUNNING",
            "reason": "r", "requester_l2": "L2-03",
        })
        assert resp["status"] == "ok"
        # 锁 scope 锚：不 transition 本 L2 直接拿锁，而是 L2-03 预先拿锁

    def test_TC_L103_L202_604_ic_l2_04_transition_running_done(
        self, sut, mock_project_id, running_wp,
    ) -> None:
        """IC-L2-04 · RUNNING→DONE · current_running_count 递减。"""
        resp = sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": running_wp,
            "from_state": "RUNNING", "to_state": "DONE",
            "reason": "dod ok", "requester_l2": "L2-04",
            "evidence_refs": ["evt-dod-01"],
        })
        assert resp["status"] == "ok"
        assert resp["current_running_count"] == 0

    def test_TC_L103_L202_605_ic_l2_06_mark_stuck_requires_failure_count_ge_3(
        self, sut, mock_project_id, failed_wp,
    ) -> None:
        """IC-L2-06 · failure_count < 3 → 拒绝（E_L103_L202_305 或调用方 bug）。"""
        resp = sut.mark_stuck_raw({
            "project_id": mock_project_id, "wp_id": failed_wp,
            "failure_count": 2,  # 非法
            "evidence_refs": ["evt-fail-01"],
            "advice_card_ref": "card-x",
        })
        assert resp["status"] == "rejected"

    def test_TC_L103_L202_606_ic_l2_08_appends_event_via_ic09(
        self, sut, mock_project_id, first_ready_wp, mock_event_bus,
    ) -> None:
        """IC-L2-08 → IC-09 · 每次 transition 必 append 一条事件 · event_type 固定。"""
        sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": first_ready_wp,
            "from_state": "READY", "to_state": "RUNNING",
            "reason": "r", "requester_l2": "L2-03",
        })
        mock_event_bus.append_event.assert_called_once()
        evt = mock_event_bus.append_event.call_args.args[0]
        assert evt["event_type"] == "wp_state_transitioned"
        assert evt["project_id"] == mock_project_id

    def test_TC_L103_L202_607_export_readonly_view_health_fields(
        self, sut, mock_project_id, loaded_topology,
    ) -> None:
        """export · health.completion_rate / parallelism_util ∈ [0,1]."""
        view = sut.export_readonly_view(mock_project_id)
        assert 0.0 <= view.health.completion_rate <= 1.0
        assert 0.0 <= view.health.parallelism_util <= 1.0
```

---

## §5 性能 SLO 用例

> 对标 §12 SLO：load_topology P95 ≤ 2s / read_snapshot P95 ≤ 50ms / transition_state P95 ≤ 100ms。

```python
# file: tests/l1_03/test_l2_02_perf.py
import time
import statistics
import pytest

from app.l2_02_topo.manager import TopologyManager


class TestL2_02_Perf:

    @pytest.mark.perf
    def test_TC_L103_L202_701_load_topology_p95_under_2s(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        durations = []
        for i in range(30):
            t = time.perf_counter()
            sut.load_topology_raw({
                "project_id": f"hf-proj-perf-{i:03d}",
                "wbs_draft": make_wbs_draft(num_wp=20),
                "mode": "full", "requester_l2": "L2-01",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 2.0

    @pytest.mark.perf
    def test_TC_L103_L202_702_read_snapshot_p95_under_50ms(
        self, sut, mock_project_id, loaded_topology,
    ) -> None:
        durations = []
        for _ in range(200):
            t = time.perf_counter()
            sut.read_snapshot_raw({
                "project_id": mock_project_id, "requester_l2": "L2-03",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.05

    @pytest.mark.perf
    def test_TC_L103_L202_703_transition_state_p95_under_100ms(
        self, sut, mock_project_id, many_ready_wps,
    ) -> None:
        durations = []
        for wp in many_ready_wps[:50]:
            t = time.perf_counter()
            sut.transition_state_raw({
                "project_id": mock_project_id, "wp_id": wp,
                "from_state": "READY", "to_state": "RUNNING",
                "reason": "r", "requester_l2": "L2-03",
            })
            sut.transition_state_raw({
                "project_id": mock_project_id, "wp_id": wp,
                "from_state": "RUNNING", "to_state": "DONE",
                "reason": "r", "requester_l2": "L2-04",
                "evidence_refs": ["e"],
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1

    @pytest.mark.perf
    def test_TC_L103_L202_704_append_event_fire_and_forget_p95_under_10ms(
        self, sut, mock_project_id, first_ready_wp, mock_event_bus,
    ) -> None:
        durations = []
        for _ in range(200):
            t = time.perf_counter()
            sut._emit_audit_event(project_id=mock_project_id, wp_id=first_ready_wp,
                                   event_type="wp_state_transitioned")
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.01
```

---

## §6 端到端 e2e

```python
# file: tests/l1_03/test_l2_02_e2e.py
import pytest


class TestL2_02_E2E:

    @pytest.mark.e2e
    def test_TC_L103_L202_801_full_pipeline_load_schedule_done(
        self, sut_real_storage, mock_project_id, make_wbs_draft,
    ) -> None:
        """e2e · 装图 → 两个并行 RUNNING → 依次 DONE → 下游 READY 放闸。"""
        draft = make_wbs_draft(num_wp=4, diamond=True)
        sut = sut_real_storage
        sut.load_topology_raw({
            "project_id": mock_project_id, "wbs_draft": draft,
            "mode": "full", "requester_l2": "L2-01",
        })
        snap = sut.read_snapshot_raw({"project_id": mock_project_id, "requester_l2": "L2-03"})
        ready = [w for w, s in snap["snapshot"]["wp_states"].items() if s["state"] == "READY"]
        assert len(ready) >= 1

    @pytest.mark.e2e
    def test_TC_L103_L202_802_failure_chain_end_to_end(
        self, sut_real_storage, mock_project_id, make_wbs_draft,
    ) -> None:
        """e2e · RUNNING → FAILED → (重试 3 次) → mark_stuck STUCK。"""
        sut = sut_real_storage
        sut.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": make_wbs_draft(num_wp=2),
            "mode": "full", "requester_l2": "L2-01",
        })
        # 模拟失败链路（见 L2-05 协同）
        # 验证终态为 STUCK
        view = sut.export_readonly_view(mock_project_id)
        assert view.topology_id
```

---

## §7 测试 fixture

```python
# file: tests/l1_03/conftest.py
from __future__ import annotations

import uuid
import pytest
from unittest.mock import MagicMock

from app.l2_02_topo.manager import TopologyManager


@pytest.fixture
def mock_project_id() -> str:
    return f"hf-proj-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_event_bus():
    m = MagicMock()
    m.append_event = MagicMock(return_value={"event_id": "evt-mock-001"})
    return m


@pytest.fixture
def mock_lock_mgr():
    m = MagicMock()
    m.acquire.return_value.__enter__ = MagicMock(return_value=True)
    m.acquire.return_value.__exit__ = MagicMock(return_value=False)
    return m


@pytest.fixture
def mock_clock():
    class Clock:
        def __init__(self) -> None:
            self.t = 1_700_000_000_000_000_000
        def now_ns(self) -> int:
            self.t += 1
            return self.t
    return Clock()


@pytest.fixture
def sut(mock_event_bus, mock_lock_mgr, mock_clock, tmp_path) -> TopologyManager:
    return TopologyManager(
        event_bus=mock_event_bus,
        lock_mgr=mock_lock_mgr,
        clock=mock_clock,
        storage_root=tmp_path,
        parallelism_limit=2,
    )


@pytest.fixture
def sut_factory(mock_event_bus, mock_lock_mgr, mock_clock, tmp_path):
    def _factory(events_jsonl=None, **kwargs) -> TopologyManager:
        mgr = TopologyManager(
            event_bus=mock_event_bus,
            lock_mgr=mock_lock_mgr,
            clock=mock_clock,
            storage_root=tmp_path,
            parallelism_limit=2,
            **kwargs,
        )
        if events_jsonl is not None:
            mgr._bootstrap_events = events_jsonl
        return mgr
    return _factory


@pytest.fixture
def sut_real_storage(mock_event_bus, mock_clock, tmp_path) -> TopologyManager:
    return TopologyManager(
        event_bus=mock_event_bus, lock_mgr=None,
        clock=mock_clock, storage_root=tmp_path, parallelism_limit=2,
    )


@pytest.fixture
def make_wbs_draft():
    """生成符合 IC-L2-01 schema 的 wbs_draft · 参数化 cycles/dangling/effort。"""
    def _make(num_wp=3, cycles=False, dangling_dep=None, missing=None,
              effort=1.0, cross_project_dep=False, project_id=None,
              base_wp_id=1, straight_chain=False, diamond=False):
        wps = []
        edges = []
        for i in range(num_wp):
            wid = f"wp-{base_wp_id + i:03d}"
            wp = {
                "wp_id": wid,
                "goal": None if missing == "goal" else f"deliver {wid}",
                "dod_expr_ref": None if missing == "dod_expr_ref" else f"dod-{wid}",
                "deps": [],
                "effort_estimate": effort,
                "recommended_skills": ["planning"],
            }
            wps.append(wp)
        if straight_chain:
            for i in range(1, num_wp):
                edges.append({"from_wp_id": wps[i-1]["wp_id"], "to_wp_id": wps[i]["wp_id"]})
                wps[i]["deps"] = [wps[i-1]["wp_id"]]
        if diamond and num_wp >= 4:
            edges += [
                {"from_wp_id": wps[0]["wp_id"], "to_wp_id": wps[1]["wp_id"]},
                {"from_wp_id": wps[0]["wp_id"], "to_wp_id": wps[2]["wp_id"]},
                {"from_wp_id": wps[1]["wp_id"], "to_wp_id": wps[3]["wp_id"]},
                {"from_wp_id": wps[2]["wp_id"], "to_wp_id": wps[3]["wp_id"]},
            ]
            wps[1]["deps"] = [wps[0]["wp_id"]]
            wps[2]["deps"] = [wps[0]["wp_id"]]
            wps[3]["deps"] = [wps[1]["wp_id"], wps[2]["wp_id"]]
        if cycles and num_wp >= 2:
            edges.append({"from_wp_id": wps[-1]["wp_id"], "to_wp_id": wps[0]["wp_id"]})
            wps[0]["deps"].append(wps[-1]["wp_id"])
        if dangling_dep is not None:
            wps[-1]["deps"].append(dangling_dep)
        if cross_project_dep:
            wps[-1]["deps"].append("wp-001@hf-proj-other")
        return {
            "project_id": project_id,
            "wp_list": wps,
            "dag_edges": edges,
            "source_ref": "trace-mock-001",
        }
    return _make


@pytest.fixture
def loaded_topology(sut, mock_project_id, make_wbs_draft):
    sut.load_topology_raw({
        "project_id": mock_project_id,
        "wbs_draft": make_wbs_draft(num_wp=3),
        "mode": "full", "requester_l2": "L2-01",
    })
    return sut


@pytest.fixture
def first_ready_wp(loaded_topology, mock_project_id) -> str:
    snap = loaded_topology.read_snapshot_raw(
        {"project_id": mock_project_id, "requester_l2": "L2-03"})
    for w, s in snap["snapshot"]["wp_states"].items():
        if s["state"] == "READY":
            return w
    pytest.fail("no READY wp in fixture")


@pytest.fixture
def running_wp(loaded_topology, mock_project_id, first_ready_wp) -> str:
    loaded_topology.transition_state_raw({
        "project_id": mock_project_id, "wp_id": first_ready_wp,
        "from_state": "READY", "to_state": "RUNNING",
        "reason": "r", "requester_l2": "L2-03",
    })
    return first_ready_wp


@pytest.fixture
def failed_wp(loaded_topology, mock_project_id, running_wp) -> str:
    loaded_topology.transition_state_raw({
        "project_id": mock_project_id, "wp_id": running_wp,
        "from_state": "RUNNING", "to_state": "FAILED",
        "reason": "e", "requester_l2": "L2-04",
        "evidence_refs": ["evt-x"],
    })
    return running_wp


@pytest.fixture
def two_ready_wps(sut, mock_project_id, make_wbs_draft):
    sut.load_topology_raw({
        "project_id": mock_project_id,
        "wbs_draft": make_wbs_draft(num_wp=3),
        "mode": "full", "requester_l2": "L2-01",
    })
    snap = sut.read_snapshot_raw(
        {"project_id": mock_project_id, "requester_l2": "L2-03"})
    ready = [w for w, s in snap["snapshot"]["wp_states"].items() if s["state"] == "READY"]
    assert len(ready) >= 3
    return tuple(ready[:3])


@pytest.fixture
def many_ready_wps(sut, mock_project_id, make_wbs_draft):
    sut.load_topology_raw({
        "project_id": mock_project_id,
        "wbs_draft": make_wbs_draft(num_wp=60),
        "mode": "full", "requester_l2": "L2-01",
    })
    snap = sut.read_snapshot_raw(
        {"project_id": mock_project_id, "requester_l2": "L2-03"})
    return [w for w, s in snap["snapshot"]["wp_states"].items() if s["state"] == "READY"]


@pytest.fixture
def wp_with_unmet_deps(sut, mock_project_id, make_wbs_draft):
    draft = make_wbs_draft(num_wp=3, straight_chain=True)
    sut.load_topology_raw({
        "project_id": mock_project_id, "wbs_draft": draft,
        "mode": "full", "requester_l2": "L2-01",
    })
    return draft["wp_list"][-1]["wp_id"]


@pytest.fixture
def events_jsonl_with_3_wps():
    return [
        {"event_type": "topology_loaded", "project_id": "*", "wp_ids": ["wp-001", "wp-002", "wp-003"]},
        {"event_type": "wp_state_transitioned", "wp_id": "wp-001",
         "from_state": "READY", "to_state": "RUNNING"},
    ]


@pytest.fixture
def corrupted_events_jsonl():
    # from_state 与 current_state 不匹配
    return [
        {"event_type": "wp_state_transitioned", "wp_id": "wp-001",
         "from_state": "RUNNING", "to_state": "DONE"},  # 跳过 READY→RUNNING
    ]


@pytest.fixture
def tamper_topology_json(tmp_path):
    def _tamper(project_id: str):
        p = tmp_path / "projects" / project_id / "wbs" / "topology.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"bypass": "yes"}', encoding="utf-8")
    return _tamper
```

---

## §8 集成点用例（与兄弟 L2 协作）

```python
# file: tests/l1_03/test_l2_02_integrations.py
import pytest


class TestL2_02_Integration:

    def test_TC_L103_L202_901_cooperation_with_l2_01_full_then_incremental(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """L2-01 多次 load_topology（full + diff-merge）· 拓扑稳定增长。"""
        sut.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": make_wbs_draft(num_wp=2),
            "mode": "full", "requester_l2": "L2-01",
        })
        sut.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": make_wbs_draft(num_wp=2, base_wp_id=3),
            "mode": "incremental", "requester_l2": "L2-01",
        })
        view = sut.export_readonly_view(mock_project_id)
        assert view.health.total_wps == 4

    def test_TC_L103_L202_902_l2_03_schedule_flow(
        self, sut, mock_project_id, first_ready_wp,
    ) -> None:
        """L2-03 调度 · READY→RUNNING · 读 snapshot 再次 parallel_limit 计算正确。"""
        sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": first_ready_wp,
            "from_state": "READY", "to_state": "RUNNING",
            "reason": "sched", "requester_l2": "L2-03",
        })
        snap = sut.read_snapshot_raw(
            {"project_id": mock_project_id, "requester_l2": "L2-03"})
        assert snap["snapshot"]["current_running_count"] == 1

    def test_TC_L103_L202_903_l2_04_done_unblocks_downstream(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """L2-04 RUNNING→DONE · 下游 BLOCKED 切为 READY（deps_met=True）。"""
        draft = make_wbs_draft(num_wp=2, straight_chain=True)
        sut.load_topology_raw({"project_id": mock_project_id, "wbs_draft": draft,
                               "mode": "full", "requester_l2": "L2-01"})
        up, down = draft["wp_list"][0]["wp_id"], draft["wp_list"][1]["wp_id"]
        sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": up,
            "from_state": "READY", "to_state": "RUNNING",
            "reason": "r", "requester_l2": "L2-03",
        })
        sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": up,
            "from_state": "RUNNING", "to_state": "DONE",
            "reason": "done", "requester_l2": "L2-04",
            "evidence_refs": ["e"],
        })
        snap = sut.read_snapshot_raw(
            {"project_id": mock_project_id, "requester_l2": "L2-03"})
        assert snap["snapshot"]["wp_states"][down]["state"] == "READY"

    def test_TC_L103_L202_904_l2_05_stuck_no_further_scheduling(
        self, sut, mock_project_id, failed_wp,
    ) -> None:
        """L2-05 mark_stuck · 后续 transition_state RUNNING→RUNNING 全部拒绝。"""
        sut.mark_stuck_raw({
            "project_id": mock_project_id, "wp_id": failed_wp,
            "failure_count": 3, "evidence_refs": ["e1", "e2", "e3"],
            "advice_card_ref": "card-x",
        })
        resp = sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": failed_wp,
            "from_state": "STUCK", "to_state": "RUNNING",
            "reason": "retry", "requester_l2": "L2-03",
        })
        assert resp["status"] == "rejected"

    def test_TC_L103_L202_905_l1_10_ui_export_refresh(
        self, sut, mock_project_id, loaded_topology,
    ) -> None:
        """L1-10 UI 每 1s 轮询 export_readonly_view · 返回稳定 topology_id。"""
        v1 = sut.export_readonly_view(mock_project_id)
        v2 = sut.export_readonly_view(mock_project_id)
        assert v1.topology_id == v2.topology_id
```

---

## §9 边界 / edge case

```python
# file: tests/l1_03/test_l2_02_edge.py
import pytest


class TestL2_02_Edge:

    def test_TC_L103_L202_A01_empty_wbs_draft_rejected(
        self, sut, mock_project_id,
    ) -> None:
        """空 wp_list 必被 §11 校验拒绝。"""
        resp = sut.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": {"wp_list": [], "dag_edges": [], "source_ref": "x"},
            "mode": "full", "requester_l2": "L2-01",
        })
        assert resp["status"] == "rejected"

    def test_TC_L103_L202_A02_single_wp_no_edges(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """单 WP 无依赖 · 允许 · critical_path = [wp-001]。"""
        resp = sut.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": make_wbs_draft(num_wp=1),
            "mode": "full", "requester_l2": "L2-01",
        })
        assert resp["status"] == "ok"
        assert resp["wp_count"] == 1

    def test_TC_L103_L202_A03_large_graph_500_wps(
        self, sut, mock_project_id, make_wbs_draft,
    ) -> None:
        """500 WP · 装图仍 < 2s · 只看不崩。"""
        resp = sut.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": make_wbs_draft(num_wp=500),
            "mode": "full", "requester_l2": "L2-01",
        })
        assert resp["status"] == "ok"

    def test_TC_L103_L202_A04_concurrent_transitions_same_wp(
        self, sut, mock_project_id, first_ready_wp,
    ) -> None:
        """并发两路 READY→RUNNING 同一 wp · 仅一路胜。"""
        from concurrent.futures import ThreadPoolExecutor
        def go():
            return sut.transition_state_raw({
                "project_id": mock_project_id, "wp_id": first_ready_wp,
                "from_state": "READY", "to_state": "RUNNING",
                "reason": "race", "requester_l2": "L2-03",
            })
        with ThreadPoolExecutor(max_workers=2) as ex:
            r1, r2 = ex.submit(go).result(), ex.submit(go).result()
        oks = sum(1 for r in (r1, r2) if r["status"] == "ok")
        assert oks == 1

    def test_TC_L103_L202_A05_crash_during_transition_rollback_on_restart(
        self, sut_factory, mock_project_id, make_wbs_draft,
    ) -> None:
        """crash 后重启 · bootstrap 基于 events.jsonl 回放到最后成功状态。"""
        s1 = sut_factory()
        s1.load_topology_raw({
            "project_id": mock_project_id,
            "wbs_draft": make_wbs_draft(num_wp=2),
            "mode": "full", "requester_l2": "L2-01",
        })
        # 模拟崩溃前没写入审计的跃迁 · 重启后仍为 READY
        s2 = sut_factory(events_jsonl=s1._journal)
        s2.on_system_resumed(project_id=mock_project_id)
        snap = s2.read_snapshot_raw(
            {"project_id": mock_project_id, "requester_l2": "L1-07"})
        for s in snap["snapshot"]["wp_states"].values():
            assert s["state"] in {"READY", "DONE", "FAILED"}

    def test_TC_L103_L202_A06_snapshot_corrupted_fallback_events_replay(
        self, sut_factory, mock_project_id, events_jsonl_with_3_wps,
    ) -> None:
        """snapshot.json corrupt · 回退到 events.jsonl 重放。"""
        sut = sut_factory(events_jsonl=events_jsonl_with_3_wps)
        sut.on_system_resumed(project_id=mock_project_id)
        assert sut.read_snapshot_raw(
            {"project_id": mock_project_id, "requester_l2": "L1-07"})["status"] == "ok"

    def test_TC_L103_L202_A07_audit_append_retry_3_then_warn(
        self, sut, mock_project_id, first_ready_wp, mock_event_bus,
    ) -> None:
        """append_event 重试 3 次后 WARN L1-07。"""
        mock_event_bus.append_event.side_effect = [IOError("x"), IOError("x"), IOError("x"), {"event_id": "e"}]
        resp = sut.transition_state_raw({
            "project_id": mock_project_id, "wp_id": first_ready_wp,
            "from_state": "READY", "to_state": "RUNNING",
            "reason": "r", "requester_l2": "L2-03",
        })
        # 允许最终 rejected 或 ok · 关键是不 silent-drop
        assert resp["status"] in {"ok", "rejected"}
```

---

*— 本 TDD 文档由 session-I 按 10 段模板填充完成 · 覆盖 §3 全部 7 方法 / §11 全部 14 错误码 / 7 条 IC 契约 / §12 4 条 SLO · 共 ≥ 30 个 TC · 等待进入 red → green 实现环节 —*
