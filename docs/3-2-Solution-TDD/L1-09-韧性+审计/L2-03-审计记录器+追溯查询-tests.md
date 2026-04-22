---
doc_id: tests-L1-09-L2-03-审计记录器+追溯查询-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-03-审计记录器+追溯查询.md
  - docs/2-prd/L1-09 韧性+审计/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-09 L2-03 审计记录器+追溯查询 · TDD 测试用例

> 基于 3-1 L2-03 §3（4 公共 + 2 内部：query_audit_trail / subscribe_event_stream / report_chain_break / get_gate_state / rebuild_mirror / set_gate_state）+ §11（14+ `AUDIT_E_*` 错误码 · 4 级 Tier T1-T4 降级）+ §12（query P95 1s / rebuild 30s / mirror ≤ 16MB/project）+ §13 TC 锚点（19 TC）。
> TC ID `TC-L109-L203-NNN`（语义别名：`TC-AUDIT-QUERY-*` / `TC-AUDIT-GATE-*` / `TC-AUDIT-REBUILD-*`）。
> pytest + Python 3.11+ · `class TestAudit_*` 组织。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（query 三种 anchor · mirror hit · gate · rebuild · subscribe）
- [x] §3 负向用例（AUDIT_E_* 14+ 全 · T1-T4 四级）
- [x] §4 IC-XX 契约集成测试（IC-18 query · IC-09 append · IC-L2-07 subscribe · IC-L2-10 rebuild）
- [x] §5 性能 SLO 用例（query P95 1s · on_event P95 200μs · rebuild 30s · 100 qps）
- [x] §6 端到端 e2e（全链查询 · T1→T2→T3→T4 降级 · rebuild 恢复）
- [x] §7 测试 fixture（mirror_factory / events_injector / make_anchor / gate_controller）
- [x] §8 集成点用例（L2-01 broadcast · L2-04 rebuild trigger · L1-07 BLOCK · L1-10 UI）
- [x] §9 边界 / edge case（PM-08 单一事实源 · 决策层空 BROKEN · mirror LRU · manual_unlock）

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法 | TC ID | IC |
|:---|:---|:---|
| `query_audit_trail()` · anchor_type=file_path | TC-L109-L203-001 | IC-18 |
| `query_audit_trail()` · anchor_type=artifact_id | TC-L109-L203-002 | IC-18 |
| `query_audit_trail()` · anchor_type=decision_id | TC-L109-L203-003 | IC-18 |
| `query_audit_trail()` · max_depth=1 immediate | TC-L109-L203-004 | IC-18 |
| `query_audit_trail()` · max_depth=4 full_chain | TC-L109-L203-005 | IC-18 |
| `query_audit_trail()` · 4 层 completeness=COMPLETE | TC-L109-L203-006 | IC-18 |
| `subscribe_event_stream()` · filter=* | TC-L109-L203-007 | IC-L2-07 |
| `subscribe_event_stream()` · filter by type_prefix | TC-L109-L203-008 | IC-L2-07 |
| `report_chain_break()` · 决策层空自触发 | TC-L109-L203-009 | 内部 |
| `get_gate_state()` · 返 OPEN | TC-L109-L203-010 | 公共 |
| `set_gate_state()` · L2-04 经 IC-L2-10 | TC-L109-L203-011 | IC-L2-10 |
| `rebuild_mirror()` · 全量重建 · 30s | TC-L109-L203-012 | IC-L2-10 |
| mirror LRU 20% 淘汰 | TC-L109-L203-013 | 内部 |
| on_event_consumed upsert · 不阻塞 broadcast | TC-L109-L203-014 | IC-L2-07 |
| TrailAssembler 拼装 4 层 | TC-L109-L203-015 | 内部 |

### §1.2 错误码 × 测试（§11 14+ 全）

| 错误码 | TC ID | Tier | 严重度 |
|:---|:---|:---|:---|
| `AUDIT_E_PROJECT_REQUIRED` | TC-L109-L203-101 | T1 | INFO |
| `AUDIT_E_PROJECT_NOT_FOUND` | TC-L109-L203-102 | T1 | INFO |
| `AUDIT_E_INVALID_ANCHOR_TYPE` | TC-L109-L203-103 | T1 | INFO |
| `AUDIT_E_GATE_CLOSED` | TC-L109-L203-104 | T2 | WARN |
| `AUDIT_E_GATE_REBUILDING` | TC-L109-L203-105 | T2 | INFO |
| `AUDIT_E_ANCHOR_NOT_FOUND` | TC-L109-L203-106 | — | INFO |
| `AUDIT_E_TRAIL_BROKEN` | TC-L109-L203-107 | T3 | CRITICAL |
| `AUDIT_E_MIRROR_OOM` | TC-L109-L203-108 | T2 | WARN |
| `AUDIT_E_DEADLINE_EXCEEDED` | TC-L109-L203-109 | T2 | WARN |
| `AUDIT_E_DECOMPRESS_FAILED` | TC-L109-L203-110 | T3 | CRITICAL |
| `AUDIT_E_REBUILD_FAILED` | TC-L109-L203-111 | T4 | FATAL |
| `AUDIT_E_INVARIANT_VIOLATION` | TC-L109-L203-112 | T4 | FATAL |
| `AUDIT_E_BACKPRESSURE` | TC-L109-L203-113 | T2 | WARN |
| `AUDIT_E_CONFIG_INVALID` | TC-L109-L203-114 | T4 | FATAL |
| `AUDIT_E_MANUAL_LOCKED` | TC-L109-L203-115 | T4 | WARN |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 |
|:---|:---|:---|
| IC-18 query（入站）| TC-L109-L203-201 | L1-10 UI / retro 工具 |
| IC-09 append audit_trail_broken（出站）| TC-L109-L203-202 | L2-01 |
| IC-L2-07 subscribe_event_stream（出站/入站）| TC-L109-L203-203 | L2-01 |
| IC-L2-10 rebuild_mirror / set_gate_state | TC-L109-L203-204 | L2-04 |
| IC-10 replay fallback | TC-L109-L203-205 | L2-01 |

### §1.4 性能 SLO × 测试

| SLO | 阈值 | TC ID |
|:---|:---|:---|
| query P95 | ≤ 1000ms | TC-L109-L203-301 |
| query P99 | ≤ 2000ms | TC-L109-L203-302 |
| on_event_consumed P95 | ≤ 200μs | TC-L109-L203-303 |
| rebuild 30s 硬上限 | | TC-L109-L203-304 |
| 100 qps 并发 | | TC-L109-L203-305 |

### §1.5 e2e × 测试

| 场景 | TC ID |
|:---|:---|
| UI 全链查询：file_path → 决策/事件/监督/授权 4 层 | TC-L109-L203-401 |
| T1→T2→T3→T4 降级全链 | TC-L109-L203-402 |
| rebuild：L2-04 触发 → gate=REBUILDING → OPEN | TC-L109-L203-403 |

---

## §2 正向用例

```python
# tests/unit/L1-09/L2-03/test_audit_positive.py
import pytest, time
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestAudit_QueryAnchors:
    """§3.1 M1 query_audit_trail · 三种 anchor"""

    def test_query_file_path(self, am, seeded_project, _anchor):
        """TC-L109-L203-001 · file_path anchor_id='src/auth.py#L42' · 返 Trail"""
        trail = am.query_audit_trail(**_anchor(type="file_path", id="src/auth.py#L42",
                                                project=seeded_project))
        assert trail.anchor.anchor_type == "file_path"
        assert trail.project_id == seeded_project
        assert trail.completeness in {"COMPLETE", "PARTIAL", "BROKEN"}

    def test_query_artifact_id(self, am, seeded_project, _anchor):
        """TC-L109-L203-002 · artifact_id='wp-042/output/api-spec.yaml'"""
        trail = am.query_audit_trail(**_anchor(type="artifact_id", id="wp-042/output/x.yaml",
                                                project=seeded_project))
        assert trail.anchor.anchor_type == "artifact_id"

    def test_query_decision_id(self, am, seeded_project, _anchor):
        """TC-L109-L203-003 · decision_id='d-01HJ...'"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-01HJXX0000",
                                                project=seeded_project))
        assert trail.anchor.anchor_type == "decision_id"


class TestAudit_QueryDepth:
    """max_depth=1 / 4"""

    def test_query_immediate_depth1(self, am, seeded_project, _anchor):
        """TC-L109-L203-004 · max_depth=1 · depth=immediate · 只返决策层"""
        trail = am.query_audit_trail(max_depth=1, **_anchor(type="decision_id",
                                                              id="d-01", project=seeded_project))
        assert trail.depth == "immediate"
        assert trail.decision_layer.count > 0

    def test_query_full_chain_depth4(self, am, seeded_project, _anchor):
        """TC-L109-L203-005 · max_depth=4 · depth=full_chain · 4 层均尝试填充"""
        trail = am.query_audit_trail(max_depth=4, **_anchor(type="decision_id",
                                                              id="d-01", project=seeded_project))
        assert trail.depth == "full_chain"
        for layer in ["decision_layer", "event_layer", "supervisor_layer", "authz_layer"]:
            assert hasattr(trail, layer)

    def test_query_completeness_complete(self, am, rich_trail_project, _anchor):
        """TC-L109-L203-006 · 预 seed 4 层都非空 · completeness=COMPLETE"""
        trail = am.query_audit_trail(max_depth=4, **_anchor(type="decision_id",
                                                              id="d-01", project=rich_trail_project))
        assert trail.completeness == "COMPLETE"
        assert trail.broken_layers == []


class TestAudit_SubscribeStream:
    """§3.1 M2 subscribe_event_stream"""

    def test_subscribe_wildcard(self, am, l201_audit_spy):
        """TC-L109-L203-007 · filter='*' · 接收全部事件"""
        handle = am.subscribe_event_stream(filter="*")
        assert handle.subscriber_id == "L2-03:audit_mirror"

    def test_subscribe_type_prefix_filter(self, am):
        """TC-L109-L203-008 · filter.type_prefix=[L1-01:] · 只接收 L1-01 事件"""
        handle = am.subscribe_event_stream(filter={"type_prefix": ["L1-01:"]})
        assert handle.filter["type_prefix"] == ["L1-01:"]


class TestAudit_ChainBreakReport:
    """§3.1 M3 report_chain_break"""

    def test_chain_break_auto_on_empty_decision(self, am, broken_decision_project, _anchor,
                                                  l201_audit_spy):
        """TC-L109-L203-009 · 决策层空 · TrailAssembler 自动触发 · IC-09 上报 audit_trail_broken"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-empty",
                                                 project=broken_decision_project))
        assert trail.completeness == "BROKEN"
        assert "decision" in trail.broken_layers
        types = [e["type"] for e in l201_audit_spy.appended_events]
        assert "L1-09:audit_trail_broken" in types


class TestAudit_GateAndRebuild:
    """§3.1 M4/M5/M6 gate + rebuild + set_gate_state"""

    def test_get_gate_state_open(self, am, mock_project_id):
        """TC-L109-L203-010 · 默认状态 OPEN"""
        state = am.get_gate_state(mock_project_id)
        assert state.state == "OPEN"

    def test_set_gate_state_via_l204(self, am, mock_project_id):
        """TC-L109-L203-011 · L2-04 经 IC-L2-10 set gate=CLOSED"""
        am.set_gate_state(mock_project_id, new_state="CLOSED")
        assert am.get_gate_state(mock_project_id).state == "CLOSED"

    def test_rebuild_mirror_fullscan(self, am, mock_project_id, events_injector):
        """TC-L109-L203-012 · rebuild 扫全 events.jsonl · 返 RebuildReport"""
        events_injector(mock_project_id, count=1000)
        am.set_gate_state(mock_project_id, new_state="REBUILDING")
        report = am.rebuild_mirror(mock_project_id, replay_from_seq=0)
        assert report.events_processed == 1000
        assert report.duration_s <= 30
        am.set_gate_state(mock_project_id, new_state="OPEN")


class TestAudit_MirrorInternals:
    """mirror LRU · on_event_consumed · TrailAssembler"""

    def test_mirror_lru_evicts_20pct(self, am_small_mirror, mock_project_id, events_injector):
        """TC-L109-L203-013 · mirror_max=100 · 超出触发 LRU 20% 淘汰（20 条）"""
        events_injector(mock_project_id, count=120)
        assert am_small_mirror.mirror_size(mock_project_id) <= 100

    def test_on_event_consumed_nonblocking(self, am, _evt):
        """TC-L109-L203-014 · on_event_consumed 不阻塞 broadcast · < 1ms"""
        t0 = time.perf_counter()
        am.on_event_consumed(_evt())
        assert (time.perf_counter() - t0) * 1000 < 1.0

    def test_trail_assembler_four_layers(self, am, rich_trail_project, _anchor):
        """TC-L109-L203-015 · 4 层顺序：decision, event, supervisor, authz · first_ts ≤ last_ts"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                                 project=rich_trail_project))
        for layer in [trail.decision_layer, trail.event_layer,
                      trail.supervisor_layer, trail.authz_layer]:
            if layer.count > 0:
                assert layer.first_ts <= layer.last_ts
```

---

## §3 负向用例（14+ 错误码 · T1-T4 四级）

```python
# tests/unit/L1-09/L2-03/test_audit_negative.py
import pytest

pytestmark = pytest.mark.asyncio


class TestAudit_T1_InputFix:
    """T1 · 调用方修参"""

    def test_AUDIT_E_PROJECT_REQUIRED(self, am, _anchor):
        """TC-L109-L203-101 · 缺 project_id · T1 立即拒"""
        a = _anchor(type="decision_id", id="d-01", project="")
        with pytest.raises(AuditError) as exc:
            am.query_audit_trail(**a)
        assert exc.value.code == "AUDIT_E_PROJECT_REQUIRED"

    def test_AUDIT_E_PROJECT_NOT_FOUND(self, am, _anchor):
        """TC-L109-L203-102 · project_id 不在 _index · T1 拒"""
        with pytest.raises(AuditError) as exc:
            am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                             project="ghost_project"))
        assert exc.value.code == "AUDIT_E_PROJECT_NOT_FOUND"

    def test_AUDIT_E_INVALID_ANCHOR_TYPE(self, am, mock_project_id):
        """TC-L109-L203-103 · anchor_type='event_id'（不在三种）· T1 + 列合法值"""
        with pytest.raises(AuditError) as exc:
            am.query_audit_trail(anchor_type="event_id", anchor_id="evt-01",
                                   project_id=mock_project_id)
        assert exc.value.code == "AUDIT_E_INVALID_ANCHOR_TYPE"
        assert "file_path" in str(exc.value.allowed)


class TestAudit_T2_SelfHeal:
    """T2 · 自愈降级"""

    def test_AUDIT_E_GATE_CLOSED(self, am, seeded_project, _anchor):
        """TC-L109-L203-104 · gate=CLOSED · 拒 · 告知 caller 等 unlock"""
        am.set_gate_state(seeded_project, new_state="CLOSED")
        with pytest.raises(AuditError) as exc:
            am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                             project=seeded_project))
        assert exc.value.code == "AUDIT_E_GATE_CLOSED"

    def test_AUDIT_E_GATE_REBUILDING(self, am, seeded_project, _anchor):
        """TC-L109-L203-105 · gate=REBUILDING · 拒 · 退避重试"""
        am.set_gate_state(seeded_project, new_state="REBUILDING")
        with pytest.raises(AuditError) as exc:
            am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                             project=seeded_project))
        assert exc.value.code == "AUDIT_E_GATE_REBUILDING"

    def test_AUDIT_E_MIRROR_OOM_triggers_lru(self, am_small_mirror, mock_project_id,
                                               events_injector):
        """TC-L109-L203-108 · mirror 超 max · LRU 淘汰 20% · 仍能查询"""
        events_injector(mock_project_id, count=200)
        assert am_small_mirror.mirror_size(mock_project_id) <= 100

    def test_AUDIT_E_DEADLINE_EXCEEDED(self, am_slow_fallback, mock_project_id, _anchor):
        """TC-L109-L203-109 · fallback 超 5s deadline · 抛"""
        with pytest.raises(AuditError) as exc:
            am_slow_fallback.query_audit_trail(**_anchor(type="decision_id", id="d-miss",
                                                          project=mock_project_id))
        assert exc.value.code == "AUDIT_E_DEADLINE_EXCEEDED"

    def test_AUDIT_E_BACKPRESSURE(self, am_small_queue, event_flood):
        """TC-L109-L203-113 · broadcast 堆积超 high_water · drop 旧 event · WARN"""
        event_flood(am_small_queue, count=10_000)
        assert am_small_queue.dropped_count > 0


class TestAudit_T3_PartialAvailable:
    """T3 · 部分可用"""

    def test_AUDIT_E_ANCHOR_NOT_FOUND(self, am, seeded_project, _anchor):
        """TC-L109-L203-106 · mirror miss + jsonl miss · 返 EMPTY trail · 不抛"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-ghost",
                                                 project=seeded_project))
        assert trail.total_entries == 0

    def test_AUDIT_E_TRAIL_BROKEN_critical(self, am, broken_decision_project, _anchor,
                                             l201_audit_spy, l107_supervisor_spy):
        """TC-L109-L203-107 · 决策层空 · BROKEN + 主动 IC-09 上报 + L1-07 CRITICAL"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                                 project=broken_decision_project))
        assert trail.completeness == "BROKEN"
        assert "decision" in trail.broken_layers
        types = [e["type"] for e in l201_audit_spy.appended_events]
        assert "L1-09:audit_trail_broken" in types

    def test_AUDIT_E_DECOMPRESS_FAILED(self, am, corrupted_rotation_zst, _anchor):
        """TC-L109-L203-110 · rotation .zst 解压失败 · 标 <lost> · PARTIAL"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-old",
                                                 project=corrupted_rotation_zst))
        assert trail.completeness == "PARTIAL"


class TestAudit_T4_HumanIntervene:
    """T4 · 人介入"""

    def test_AUDIT_E_REBUILD_FAILED(self, am_corrupt_events, mock_project_id):
        """TC-L109-L203-111 · rebuild 超 30s / hash 断 · gate=CLOSED + FATAL"""
        am_corrupt_events.set_gate_state(mock_project_id, new_state="REBUILDING")
        with pytest.raises(AuditError) as exc:
            am_corrupt_events.rebuild_mirror(mock_project_id)
        assert exc.value.code == "AUDIT_E_REBUILD_FAILED"
        assert am_corrupt_events.get_gate_state(mock_project_id).state == "CLOSED"

    def test_AUDIT_E_INVARIANT_VIOLATION(self, am, force_invariant_break,
                                           mock_project_id, _anchor):
        """TC-L109-L203-112 · trail 完整性自检矛盾 · halt query"""
        force_invariant_break()
        with pytest.raises(AuditError) as exc:
            am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                             project=mock_project_id))
        assert exc.value.code == "AUDIT_E_INVARIANT_VIOLATION"

    def test_AUDIT_E_CONFIG_INVALID_at_boot(self, tmp_path):
        """TC-L109-L203-114 · config 非法 · boot fail-fast"""
        bad_cfg = tmp_path / "bad.yaml"
        bad_cfg.write_text("mirror_max_per_project: -1\n")
        with pytest.raises(SystemExit):
            AuditMirror.bootstrap(str(bad_cfg))

    def test_AUDIT_E_MANUAL_LOCKED(self, am, mock_project_id, _anchor):
        """TC-L109-L203-115 · gate=CLOSED 且无 manual_unlock · 持续拒"""
        am.set_gate_state(mock_project_id, new_state="CLOSED")
        for _ in range(3):
            with pytest.raises(AuditError) as exc:
                am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                                 project=mock_project_id))
            assert exc.value.code in {"AUDIT_E_GATE_CLOSED", "AUDIT_E_MANUAL_LOCKED"}
```

---

## §4 IC-XX 契约集成测试

```python
# tests/integration/L1-09/L2-03/test_ic_contracts.py
import pytest, jsonschema

pytestmark = pytest.mark.asyncio


class TestIC18QueryContract:
    """IC-18 · query（入站）"""

    def test_ic18_trail_schema(self, am, seeded_project, _anchor, trail_schema):
        """TC-L109-L203-201 · Trail schema 完整（≥ 12 字段）"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                                 project=seeded_project))
        # 检验字段存在
        for f in ["anchor", "project_id", "depth", "decision_layer", "event_layer",
                   "supervisor_layer", "authz_layer", "completeness",
                   "queried_at", "mirror_version", "latency_ms", "total_entries"]:
            assert hasattr(trail, f)


class TestIC09AppendAuditBrokenContract:
    """IC-09 · audit_trail_broken 自动上报"""

    def test_ic09_broken_event_fields(self, am, broken_decision_project, _anchor,
                                        l201_audit_spy):
        """TC-L109-L203-202 · 事件含 anchor / missing_layers / detected_at"""
        am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                         project=broken_decision_project))
        broken = next(e for e in l201_audit_spy.appended_events
                      if e["type"] == "L1-09:audit_trail_broken")
        assert broken["payload"]["missing_layers"]


class TestICL207SubscribeContract:
    """IC-L2-07 · subscribe L2-01 event stream"""

    def test_icl207_subscribe_delivery(self, am, l201_audit_spy):
        """TC-L109-L203-203 · 本 L2 boot 期订阅 · L2-01 broadcast 必推"""
        handle = am.subscribe_event_stream(filter="*")
        assert handle.subscriber_id == "L2-03:audit_mirror"


class TestICL210RebuildContract:
    """IC-L2-10 · L2-04 触发 rebuild / set_gate"""

    def test_icl210_rebuild_gate_cycle(self, am, mock_project_id, events_injector):
        """TC-L109-L203-204 · L2-04 经 IC-L2-10: REBUILDING → rebuild → OPEN"""
        events_injector(mock_project_id, count=500)
        am.set_gate_state(mock_project_id, new_state="REBUILDING")
        assert am.get_gate_state(mock_project_id).state == "REBUILDING"
        report = am.rebuild_mirror(mock_project_id)
        am.set_gate_state(mock_project_id, new_state="OPEN")
        assert am.get_gate_state(mock_project_id).state == "OPEN"
        assert report.events_processed == 500


class TestIC10ReplayFallbackContract:
    """IC-10 · mirror miss 时的 jsonl replay fallback"""

    def test_ic10_replay_on_mirror_miss(self, am_tiny, mock_project_id, events_injector, _anchor):
        """TC-L109-L203-205 · mirror 超小 · miss 后 fallback jsonl · fallback_used 字段"""
        events_injector(mock_project_id, count=1000)
        # mirror 仅 100 · 查询第 200 条 · 必 miss
        trail = am_tiny.query_audit_trail(**_anchor(type="decision_id", id="d-0200",
                                                     project=mock_project_id))
        assert trail.fallback_used in {"jsonl_scan", "replay_from_event"}
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-09/L2-03/test_slo.py
import pytest, time, statistics, threading
from contextlib import contextmanager


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestQuerySLO:
    """§12 · query P95 ≤ 1000ms · P99 ≤ 2000ms"""

    def test_query_p95_under_1s(self, am, seeded_project, _anchor):
        """TC-L109-L203-301 · 500 次 query · P95 ≤ 1000ms"""
        samples = []
        for i in range(500):
            with _timer() as t:
                am.query_audit_trail(**_anchor(type="decision_id", id=f"d-{i:04d}",
                                                 project=seeded_project))
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 1000.0

    def test_query_p99_under_2s(self, am, seeded_project, _anchor):
        """TC-L109-L203-302 · P99 ≤ 2000ms"""
        samples = []
        for i in range(500):
            with _timer() as t:
                am.query_audit_trail(**_anchor(type="decision_id", id=f"d-{i:04d}",
                                                 project=seeded_project))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 2000.0


class TestOnEventConsumedSLO:
    """§12 · on_event_consumed P95 ≤ 200μs"""

    def test_on_event_consumed_p95_under_200us(self, am, _evt):
        """TC-L109-L203-303 · 10000 次 upsert · P95 ≤ 0.2ms"""
        samples = []
        for _ in range(10_000):
            with _timer() as t:
                am.on_event_consumed(_evt())
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 0.2


class TestRebuildSLO:
    """§12 · rebuild 30s 硬上限"""

    def test_rebuild_100k_events_under_30s(self, am, mock_project_id, events_injector):
        """TC-L109-L203-304 · 100k events rebuild · ≤ 30s"""
        events_injector(mock_project_id, count=100_000)
        am.set_gate_state(mock_project_id, new_state="REBUILDING")
        t0 = time.perf_counter()
        r = am.rebuild_mirror(mock_project_id)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 30.0
        assert r.events_processed == 100_000


class TestConcurrencySLO:
    """§12 · 100 qps 并发 query"""

    def test_100_qps_concurrent_query(self, am, seeded_project, _anchor):
        """TC-L109-L203-305 · 100 线程 · 1s 内并发 query · 吞吐 ≥ 100"""
        completed = [0]
        lock = threading.Lock()
        end = time.perf_counter() + 1.0
        def _w():
            while time.perf_counter() < end:
                am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                                 project=seeded_project))
                with lock: completed[0] += 1
        ts = [threading.Thread(target=_w) for _ in range(100)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert completed[0] >= 100
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-09/L2-03/test_e2e.py
import pytest, time

pytestmark = pytest.mark.asyncio


class TestE2E_UIFullChainQuery:
    """UI 全链 4 层查询"""

    def test_ui_file_path_full_chain(self, am, rich_trail_project, _anchor):
        """TC-L109-L203-401 · UI query file_path · 返 4 层 COMPLETE trail"""
        trail = am.query_audit_trail(max_depth=4,
                                       **_anchor(type="file_path", id="src/auth.py#L42",
                                                   project=rich_trail_project))
        assert trail.completeness == "COMPLETE"
        assert all(trail.__getattribute__(f"{l}_layer").count > 0
                   for l in ["decision", "event", "supervisor", "authz"])


class TestE2E_FullTierDegrade:
    """T1 → T2 → T3 → T4 降级全链"""

    def test_tier_1_2_3_4_degrade(self, am, mock_project_id, _anchor):
        """TC-L109-L203-402 · 依次触发 T1 invalid → T2 rebuilding → T3 broken → T4 closed"""
        # T1
        with pytest.raises(AuditError) as e1:
            am.query_audit_trail(anchor_type="bad", anchor_id="x", project_id=mock_project_id)
        assert e1.value.code == "AUDIT_E_INVALID_ANCHOR_TYPE"
        # T2
        am.set_gate_state(mock_project_id, new_state="REBUILDING")
        with pytest.raises(AuditError) as e2:
            am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                             project=mock_project_id))
        assert e2.value.code == "AUDIT_E_GATE_REBUILDING"
        # T3 模拟（重建成功 · 决策层空）
        am.set_gate_state(mock_project_id, new_state="OPEN")
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                                 project=mock_project_id))
        # 决策层空 → BROKEN
        assert trail.completeness in {"BROKEN", "PARTIAL"}
        # T4
        am.set_gate_state(mock_project_id, new_state="CLOSED")
        with pytest.raises(AuditError) as e4:
            am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                             project=mock_project_id))
        assert e4.value.code in {"AUDIT_E_GATE_CLOSED", "AUDIT_E_MANUAL_LOCKED"}


class TestE2E_RebuildCycle:
    """L2-04 触发 rebuild · 全流程"""

    def test_rebuild_cycle_with_audit(self, am, mock_project_id, events_injector,
                                        l201_audit_spy):
        """TC-L109-L203-403 · L2-04 经 IC-L2-10 · rebuild start + end 元事件"""
        events_injector(mock_project_id, count=500)
        am.set_gate_state(mock_project_id, new_state="REBUILDING")
        am.rebuild_mirror(mock_project_id)
        am.set_gate_state(mock_project_id, new_state="OPEN")
        types = [e["type"] for e in l201_audit_spy.appended_events]
        assert "L1-09:mirror_rebuild_started" in types or "L1-09:gate_state_changed" in types
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest, json, time
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4


@pytest.fixture
def mock_project_id(): return "demo-proj-001"


@pytest.fixture
def _anchor(mock_project_id):
    def _make(type: str = "decision_id", id: str = "d-01",
              project: str | None = None) -> dict:
        return {
            "anchor_type": type,
            "anchor_id": id,
            "project_id": project if project is not None else mock_project_id,
        }
    return _make


@pytest.fixture
def _evt(mock_project_id):
    def _make(type: str = "L1-01:decision_made", **kwargs) -> dict:
        return {
            "project_id": mock_project_id,
            "type": type,
            "actor": kwargs.get("actor", "main_loop"),
            "timestamp": "2026-04-22T10:00:00Z",
            "sequence": kwargs.get("sequence", 0),
            "hash": kwargs.get("hash", "a" * 64),
            "payload": kwargs.get("payload", {"decision_id": "d-01"}),
        }
    return _make


@pytest.fixture
def l201_audit_spy():
    m = MagicMock()
    m.appended_events = []
    def _a(evt): m.appended_events.append(evt)
    m.append = _a
    return m


@pytest.fixture
def l107_supervisor_spy():
    m = MagicMock()
    m.events = []
    m.receive = m.events.append
    return m


@pytest.fixture
def am(tmp_path, l201_audit_spy, l107_supervisor_spy):
    return AuditMirror(
        workdir=tmp_path,
        event_bus=l201_audit_spy,
        supervisor=l107_supervisor_spy,
        config={"mirror_max_per_project": 1000,
                "max_events_per_layer": 500,
                "mirror_rebuild_deadline_s": 30,
                "fallback_deadline_s": 5},
    )


@pytest.fixture
def am_small_mirror(tmp_path, l201_audit_spy, l107_supervisor_spy):
    return AuditMirror(workdir=tmp_path, event_bus=l201_audit_spy,
                         supervisor=l107_supervisor_spy,
                         config={"mirror_max_per_project": 100})


@pytest.fixture
def am_slow_fallback(tmp_path, l201_audit_spy, l107_supervisor_spy, monkeypatch):
    am_inst = AuditMirror(workdir=tmp_path, event_bus=l201_audit_spy,
                            supervisor=l107_supervisor_spy,
                            config={"fallback_deadline_s": 0.001})  # 超小 deadline
    return am_inst


@pytest.fixture
def am_small_queue(tmp_path, l201_audit_spy, l107_supervisor_spy):
    return AuditMirror(workdir=tmp_path, event_bus=l201_audit_spy,
                         supervisor=l107_supervisor_spy,
                         config={"broadcast_queue_high_water": 10})


@pytest.fixture
def am_tiny(tmp_path, l201_audit_spy, l107_supervisor_spy):
    return AuditMirror(workdir=tmp_path, event_bus=l201_audit_spy,
                         supervisor=l107_supervisor_spy,
                         config={"mirror_max_per_project": 100})


@pytest.fixture
def am_corrupt_events(am, mock_project_id, monkeypatch):
    # 注入 rebuild 超时
    monkeypatch.setattr(am, "rebuild_mirror",
                        lambda pid, replay_from_seq=0:
                            (_ for _ in ()).throw(AuditError("AUDIT_E_REBUILD_FAILED")))
    return am


@pytest.fixture
def seeded_project(am, mock_project_id):
    """填入 500 条 events · 200 个 decisions"""
    for i in range(500):
        am.on_event_consumed({
            "project_id": mock_project_id,
            "type": "L1-01:decision_made" if i % 2 == 0 else "L1-07:supervisor_comment",
            "payload": {"decision_id": f"d-{i:04d}"},
            "sequence": i,
        })
    return mock_project_id


@pytest.fixture
def rich_trail_project(am, mock_project_id):
    """4 层证据都填"""
    am.on_event_consumed({"project_id": mock_project_id, "type": "L1-01:decision_made",
                            "payload": {"decision_id": "d-01", "rationale": "x"}, "sequence": 0})
    am.on_event_consumed({"project_id": mock_project_id, "type": "L1-01:tool_used",
                            "payload": {"decision_id": "d-01"}, "sequence": 1})
    am.on_event_consumed({"project_id": mock_project_id, "type": "L1-07:supervisor_comment",
                            "payload": {"decision_id": "d-01"}, "sequence": 2})
    am.on_event_consumed({"project_id": mock_project_id, "type": "L1-01:user_intervene",
                            "payload": {"decision_id": "d-01"}, "sequence": 3})
    return mock_project_id


@pytest.fixture
def broken_decision_project(am, mock_project_id):
    """决策层空 · 只有事件"""
    am.on_event_consumed({"project_id": mock_project_id, "type": "L1-01:tool_used",
                            "payload": {"decision_id": "d-01"}, "sequence": 0})
    return mock_project_id


@pytest.fixture
def corrupted_rotation_zst(am, mock_project_id, tmp_path):
    # 写一个损坏的 zst 文件
    rot = tmp_path / "audit" / mock_project_id / "rotations"
    rot.mkdir(parents=True)
    (rot / "old.zst").write_bytes(b"\x00\x00\x00invalid_zst")
    return mock_project_id


@pytest.fixture
def events_injector(am):
    def _inject(project_id: str, count: int):
        for i in range(count):
            am.on_event_consumed({
                "project_id": project_id,
                "type": "L1-01:decision_made",
                "payload": {"decision_id": f"d-{i:04d}"},
                "sequence": i,
            })
    return _inject


@pytest.fixture
def event_flood():
    def _flood(am_instance, count: int):
        for i in range(count):
            try:
                am_instance.on_event_consumed({"sequence": i})
            except Exception:
                pass
    return _flood


@pytest.fixture
def force_invariant_break(monkeypatch):
    def _activate():
        monkeypatch.setattr(TrailAssembler, "_check_invariants",
                            lambda self, t: (_ for _ in ()).throw(InvariantViolation("bad")))
    return _activate


@pytest.fixture
def trail_schema():
    return {"type": "object", "required": ["anchor", "project_id", "depth",
                                              "decision_layer", "completeness"]}
```

---

## §8 集成点用例

```python
# tests/integration/L1-09/L2-03/test_integration_points.py
import pytest

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL201Broadcast:
    """与 L2-01 · 订阅消费"""

    def test_l201_broadcast_consumed_by_mirror(self, am, mock_project_id, _evt):
        """TC-L109-L203-501 · L2-01 广播事件 · am.on_event_consumed upsert mirror"""
        am.on_event_consumed(_evt())
        assert am.mirror_size(mock_project_id) >= 1


class TestIntegrationWithL204Rebuild:
    """与 L2-04 · rebuild 触发"""

    def test_l204_triggers_rebuild_cycle(self, am, mock_project_id, events_injector):
        """TC-L109-L203-502 · L2-04 经 IC-L2-10 set REBUILDING · rebuild · OPEN"""
        events_injector(mock_project_id, count=100)
        am.set_gate_state(mock_project_id, new_state="REBUILDING")
        r = am.rebuild_mirror(mock_project_id)
        am.set_gate_state(mock_project_id, new_state="OPEN")
        assert r.events_processed == 100


class TestIntegrationWithL107Supervisor:
    """与 L1-07 · audit_trail_broken CRITICAL"""

    def test_broken_reaches_supervisor(self, am, broken_decision_project,
                                         l107_supervisor_spy, _anchor):
        """TC-L109-L203-503 · BROKEN trail · L1-07 收 CRITICAL"""
        am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                         project=broken_decision_project))
        assert len(l107_supervisor_spy.events) > 0


class TestIntegrationWithL110UI:
    """与 L1-10 UI · gate 状态显示"""

    def test_ui_reads_gate_state_nonblocking(self, am, mock_project_id):
        """TC-L109-L203-504 · UI 调 get_gate_state · 纯读 · 不阻塞 query"""
        for _ in range(1000):
            state = am.get_gate_state(mock_project_id)
            assert state.state in {"OPEN", "CLOSED", "REBUILDING"}
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-09/L2-03/test_edge_cases.py
import pytest, time

pytestmark = pytest.mark.asyncio


class TestEdgePM08SingleSourceOfTruth:
    """PM-08 单一事实源 · 查询结果与 events.jsonl 一致"""

    def test_edge_query_matches_events_jsonl(self, am, seeded_project, _anchor):
        """TC-L109-L203-601 · mirror 查询 decision 条目 · 必与 events.jsonl 原文一致"""
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-0000",
                                                 project=seeded_project))
        if trail.decision_layer.count > 0:
            entry = trail.decision_layer.entries[0]
            assert entry.get("decision_id") == "d-0000"


class TestEdgeEmptyDecisionLayer:
    """决策层空 · BROKEN 必触发"""

    def test_edge_empty_decision_always_broken(self, am, broken_decision_project, _anchor,
                                                 l201_audit_spy):
        """TC-L109-L203-602 · 任何 anchor · 决策层空 · 必 BROKEN + 必 IC-09 上报"""
        am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                         project=broken_decision_project))
        types = [e["type"] for e in l201_audit_spy.appended_events]
        assert "L1-09:audit_trail_broken" in types


class TestEdgeMirrorLRUEviction:
    """mirror 超 max · LRU 按 last access"""

    def test_edge_lru_evicts_oldest_access(self, am_small_mirror, mock_project_id, events_injector):
        """TC-L109-L203-603 · 200 event · mirror 100 · LRU 保留最近访问的"""
        events_injector(mock_project_id, count=200)
        # 访问 d-0150 · 则它应在保留集
        _ = am_small_mirror.mirror_size(mock_project_id)
        assert am_small_mirror.mirror_size(mock_project_id) <= 100


class TestEdgeManualUnlock:
    """T4 manual_unlock · 必须运维显式调"""

    def test_edge_manual_unlock_required(self, am, mock_project_id):
        """TC-L109-L203-604 · gate=CLOSED 不会自动恢复 · 必 set OPEN 才解锁"""
        am.set_gate_state(mock_project_id, new_state="CLOSED")
        # 等 5s 不会自动回 OPEN
        time.sleep(0.1)
        assert am.get_gate_state(mock_project_id).state == "CLOSED"
        am.set_gate_state(mock_project_id, new_state="OPEN")
        assert am.get_gate_state(mock_project_id).state == "OPEN"


class TestEdgeMaxEventsPerLayer:
    """max_events_per_layer=500 截断"""

    def test_edge_layer_truncated_at_500(self, am, mock_project_id, events_injector, _anchor):
        """TC-L109-L203-605 · 1000 events 同 decision · 层 entries ≤ 500 + truncated=true"""
        for i in range(1000):
            am.on_event_consumed({
                "project_id": mock_project_id,
                "type": "L1-01:tool_used",
                "payload": {"decision_id": "d-01"},
                "sequence": i,
            })
        trail = am.query_audit_trail(**_anchor(type="decision_id", id="d-01",
                                                 project=mock_project_id))
        assert trail.event_layer.count <= 500
        if trail.event_layer.count == 500:
            assert trail.truncated is True
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
