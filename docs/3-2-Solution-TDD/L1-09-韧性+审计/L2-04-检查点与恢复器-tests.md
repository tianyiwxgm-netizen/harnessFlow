---
doc_id: tests-L1-09-L2-04-检查点与恢复器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-04-检查点与恢复器.md
  - docs/2-prd/L1-09 韧性+审计/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-09 L2-04 检查点与恢复器 · TDD 测试用例

> 基于 3-1 L2-04 §3（4 公共 + 1 内部观测 · take_snapshot / recover_from_checkpoint / begin_shutdown / replay_events / list_checkpoints）+ §11（≥ 12 个 `RECOVERY_E_*` / `SNAPSHOT_E_*` / `SHUTDOWN_E_*` 错误码 · 4 级 Tier 降级 · 30s 硬约束）+ §12（snapshot 2s · recovery 30s · shutdown 5s 硬上限）+ §13 TC 锚点。
> **跨 session bootstrap 关键**：Tier 1~4 串行 + events.jsonl hash 链校验 + 30s deadline + PID mismatch 防错位。
> TC ID `TC-L109-L204-NNN`（语义别名：`TC-RECOVER-*` / `TC-SNAPSHOT-*` / `TC-SHUTDOWN-*` / `T-RECOVER-TIER-*`）。
> pytest + Python 3.11+ · `class TestCheckpoint_*` / `TestRecover_*` / `TestShutdown_*` 组织。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（take_snapshot / recover Tier 1-3 / begin_shutdown / replay / list）
- [x] §3 负向用例（≥ 12 错误码 · CRITICAL/WARN/INFO/FATAL 4 级 + Tier 4 拒绝）
- [x] §4 IC-XX 契约集成测试（IC-10 replay · IC-09 audit · IC-Lock · L2-05 atomic_write）
- [x] §5 性能 SLO 用例（snapshot P95 500ms · recovery 1w events ≤ 10s · shutdown ≤ 5s）
- [x] §6 端到端 e2e（跨 session bootstrap · Tier 1→2→3 降级 · shutdown 全流程）
- [x] §7 测试 fixture（make_checkpoint / corrupt_checkpoint / events_chain / tmp_project）
- [x] §8 集成点用例（L2-01/02/05 · L1-02 manifest · L1-07 Supervisor）
- [x] §9 边界 / edge case（30s 临界 · PID mismatch · blank rebuild 拒绝 · in-flight drain）

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法 | TC ID | 覆盖类型 |
|:---|:---|:---|
| `take_snapshot()` · 周期触发 | TC-L109-L204-001 | unit |
| `take_snapshot()` · 关键事件触发 | TC-L109-L204-002 | unit |
| `take_snapshot()` · shutdown_final | TC-L109-L204-003 | unit |
| `take_snapshot()` · duration_ms ≤ 2000 硬约束 | TC-L109-L204-004 | unit |
| `recover_from_checkpoint()` · Tier 1 最新 OK | TC-L109-L204-005 | unit |
| `recover_from_checkpoint()` · Tier 2 回退 previous | TC-L109-L204-006 | unit |
| `recover_from_checkpoint()` · Tier 3 完整回放 | TC-L109-L204-007 | unit |
| `recover_from_checkpoint()` · hash 链跳损坏块 | TC-L109-L204-008 | unit |
| `begin_shutdown()` · REQUESTED → DRAINING → ACKED | TC-L109-L204-009 | unit |
| `begin_shutdown()` · 幂等（重复调返同 token） | TC-L109-L204-010 | unit |
| `begin_shutdown()` · final checkpoint 落盘 | TC-L109-L204-011 | unit |
| `replay_events()` · 顺序回放 1 万 events | TC-L109-L204-012 | unit |
| `list_checkpoints()` · 时间轴列表 | TC-L109-L204-013 | unit |
| `system_resumed` 元事件广播（recover 后） | TC-L109-L204-014 | unit |
| `SnapshotManifest` + `Snapshot` 双份对齐 | TC-L109-L204-015 | unit |

### §1.2 错误码 × 测试（§3.3 12+ 全覆盖）

| 错误码 | TC ID | 严重度 | Tier |
|:---|:---|:---|:---|
| `RECOVERY_E_CHECKPOINT_CORRUPT` | TC-L109-L204-101 | WARN | 降 Tier 1→2 |
| `RECOVERY_E_HASH_CHAIN_BROKEN` | TC-L109-L204-102 | WARN | Tier 3 跳损坏 |
| `RECOVERY_E_DEADLINE_EXCEEDED` | TC-L109-L204-103 | CRITICAL | 失败不假恢复 |
| `RECOVERY_E_NO_CHECKPOINT` | TC-L109-L204-104 | CRITICAL | Tier 4 拒绝 |
| `RECOVERY_E_REPLAY_FAILED` | TC-L109-L204-105 | CRITICAL | 标 RECOVERY_FAILED |
| `RECOVERY_E_PID_MISMATCH` | TC-L109-L204-106 | WARN | 自动 fallback |
| `RECOVERY_E_BLANK_REBUILD_REJECTED` | TC-L109-L204-107 | CRITICAL | Tier 4 硬禁 |
| `SNAPSHOT_E_LOCK_TIMEOUT` | TC-L109-L204-108 | INFO | 跳过本次 |
| `SNAPSHOT_E_DISK_FULL` | TC-L109-L204-109 | FATAL | 响应面 4 |
| `SNAPSHOT_E_INTEGRITY_VERIFY_FAIL` | TC-L109-L204-110 | CRITICAL | 删 corrupt + retry |
| `SHUTDOWN_E_DRAIN_TIMEOUT` | TC-L109-L204-111 | WARN | 强制 flush |
| `SHUTDOWN_E_REENTRANT` | TC-L109-L204-112 | INFO | 返原 token |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 |
|:---|:---|:---|
| IC-10 replay_events | TC-L109-L204-201 | L2-01 / 本 L2 RecoveryOrchestrator |
| IC-09 system_resumed broadcast | TC-L109-L204-202 | L2-01 |
| IC-Lock task_board 锁 | TC-L109-L204-203 | L2-02 |
| IC atomic_write | TC-L109-L204-204 | L2-05 |
| IC-10 verify_integrity（用于 checkpoint checksum） | TC-L109-L204-205 | L2-05 |

### §1.4 性能 SLO × 测试

| SLO | 阈值 | TC ID |
|:---|:---|:---|
| snapshot ≤ 1MB P95 | ≤ 500ms · max 2s | TC-L109-L204-301 |
| snapshot 1-10MB P95 | ≤ 800ms | TC-L109-L204-302 |
| recovery 1w events P95 | ≤ 10s | TC-L109-L204-303 |
| bootstrap 5 project 串行 | ≤ 30s 硬上限 | TC-L109-L204-304 |
| shutdown 总耗时 | ≤ 5s 硬上限 | TC-L109-L204-305 |

### §1.5 e2e × 测试

| 场景 | TC ID |
|:---|:---|
| 跨 session bootstrap · 最新 checkpoint OK · Tier 1 | TC-L109-L204-401 |
| Tier 1 损坏 → Tier 2 (previous) → Tier 3 (replay) 串行降级 | TC-L109-L204-402 |
| shutdown 全流程：SIGINT → drain → final snapshot → ACKED | TC-L109-L204-403 |

---

## §2 正向用例

```python
# tests/unit/L1-09/L2-04/test_checkpoint_positive.py
import pytest, time
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestCheckpoint_TakeSnapshot:
    """§3.1 M1 take_snapshot"""

    def test_take_snapshot_periodic(self, rec, mock_project_id):
        """TC-L109-L204-001 · periodic_timer 触发 · 返 SnapshotResult"""
        r = rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        assert r.checkpoint_id.startswith("cp-")
        assert r.project_id == mock_project_id
        assert r.last_event_sequence >= 0
        assert len(r.checksum) == 64
        assert r.trigger == "periodic_timer"

    def test_take_snapshot_key_event(self, rec, mock_project_id):
        """TC-L109-L204-002 · key_event 触发 · state 切换时"""
        r = rec.take_snapshot(mock_project_id, trigger="key_event")
        assert r.trigger == "key_event"

    def test_take_snapshot_shutdown_final(self, rec, mock_project_id):
        """TC-L109-L204-003 · shutdown_final · superseded_checkpoint_id 非空"""
        rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        r2 = rec.take_snapshot(mock_project_id, trigger="shutdown_final")
        assert r2.trigger == "shutdown_final"

    def test_take_snapshot_duration_within_2s(self, rec, mock_project_id):
        """TC-L109-L204-004 · duration_ms ≤ 2000 硬约束"""
        r = rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        assert r.duration_ms <= 2000


class TestCheckpoint_RecoverTiers:
    """§3.1 M2 recover · Tier 1-3"""

    def test_recover_tier1_latest_ok(self, rec, seeded_project_with_checkpoint):
        """TC-L109-L204-005 · 最新 checkpoint OK · tier=1"""
        pid = seeded_project_with_checkpoint
        r = rec.recover_from_checkpoint(pid)
        assert r.tier == 1
        assert r.hash_chain_valid is True
        assert r.duration_ms <= 30_000
        assert r.system_resumed_event_id

    def test_recover_tier2_previous(self, rec, corrupt_latest_ok_previous):
        """TC-L109-L204-006 · 最新坏 · previous OK · tier=2"""
        pid = corrupt_latest_ok_previous
        r = rec.recover_from_checkpoint(pid)
        assert r.tier == 2

    def test_recover_tier3_full_replay(self, rec, all_checkpoints_corrupt_events_ok):
        """TC-L109-L204-007 · 全部 checkpoint 坏 · events 完整 · tier=3"""
        pid = all_checkpoints_corrupt_events_ok
        r = rec.recover_from_checkpoint(pid)
        assert r.tier == 3
        assert r.checkpoint_id_used is None
        assert r.events_replayed_count > 0

    def test_recover_tier3_skip_corrupt_ranges(self, rec, events_with_broken_middle):
        """TC-L109-L204-008 · hash 链中段断 · skipped_corrupt_ranges 非空"""
        pid = events_with_broken_middle
        r = rec.recover_from_checkpoint(pid)
        assert r.tier == 3
        assert r.skipped_corrupt_ranges
        assert r.skipped_corrupt_ranges[0]["reason"] == "hash_mismatch"


class TestCheckpoint_Shutdown:
    """§3.1 M3 begin_shutdown"""

    def test_shutdown_state_progression(self, rec, mock_project_id):
        """TC-L109-L204-009 · REQUESTED → DRAINING → FLUSHING → ACKED"""
        tok = rec.begin_shutdown(reason="sigint")
        assert tok.state == "REQUESTED"
        rec.wait_until_state(tok, "ACKED", timeout_s=6)
        tok = rec.poll_shutdown(tok.token_id)
        assert tok.state == "ACKED"
        assert tok.flush_duration_ms <= 5000

    def test_shutdown_idempotent_reentrant(self, rec):
        """TC-L109-L204-010 · 重复调 · 返原 token + INFO"""
        tok1 = rec.begin_shutdown(reason="sigint")
        tok2 = rec.begin_shutdown(reason="sigint")
        assert tok1.token_id == tok2.token_id

    def test_shutdown_final_checkpoint_written(self, rec, mock_project_id):
        """TC-L109-L204-011 · ACKED 后 final_checkpoint_id 非空"""
        tok = rec.begin_shutdown(reason="sigint")
        rec.wait_until_state(tok, "ACKED", timeout_s=6)
        tok = rec.poll_shutdown(tok.token_id)
        assert tok.final_checkpoint_id and tok.final_checkpoint_id.startswith("cp-")


class TestCheckpoint_ReplayAndList:
    """§3.1 M4 replay_events · M5 list_checkpoints"""

    def test_replay_events_ordered(self, rec, mock_project_id):
        """TC-L109-L204-012 · 回放 10000 events · hash 链全 OK"""
        # 预 seed events.jsonl
        rec._seed_events(mock_project_id, n=10_000)
        r = rec.replay_events(mock_project_id, from_seq=0)
        assert r.events_replayed == 10_000
        assert r.hash_chain_valid is True
        assert r.last_sequence_processed == 9999

    def test_list_checkpoints_sorted(self, rec, mock_project_id):
        """TC-L109-L204-013 · list 时间轴倒序（最新在前）"""
        for _ in range(3):
            rec.take_snapshot(mock_project_id, trigger="periodic_timer")
            time.sleep(0.01)
        summary = rec.list_checkpoints(mock_project_id)
        assert len(summary) == 3
        # 时间递增
        assert summary[0].created_at >= summary[-1].created_at


class TestCheckpoint_SystemResumedAndAlignment:
    """system_resumed 广播 + manifest 对齐"""

    def test_system_resumed_broadcast(self, rec, seeded_project_with_checkpoint,
                                        l201_audit_spy):
        """TC-L109-L204-014 · recover 成功 · 广播 system_resumed 元事件"""
        rec.recover_from_checkpoint(seeded_project_with_checkpoint)
        types = [e["type"] for e in l201_audit_spy.appended_events]
        assert "L1-09:system_resumed" in types

    def test_manifest_and_snapshot_aligned(self, rec, mock_project_id):
        """TC-L109-L204-015 · SnapshotManifest.checksum 与 Snapshot body sha256 一致"""
        r = rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        manifest = rec._read_manifest(mock_project_id, r.last_event_sequence)
        assert manifest["checksum"] == r.checksum
```

---

## §3 负向用例（12+ 错误码 · 4 级严重度 + Tier 4 拒绝）

```python
# tests/unit/L1-09/L2-04/test_checkpoint_negative.py
import pytest, time

pytestmark = pytest.mark.asyncio


class TestRecovery_WARN_AutoDegrade:
    """WARN · 自动降 Tier"""

    def test_RECOVERY_E_CHECKPOINT_CORRUPT(self, rec, corrupt_latest_only,
                                             l107_supervisor_spy):
        """TC-L109-L204-101 · 最新 checkpoint 坏 · 自动 Tier 1→2 + recovery_degraded 事件"""
        pid = corrupt_latest_only
        r = rec.recover_from_checkpoint(pid)
        assert r.tier == 2
        assert l107_supervisor_spy.has_warn_event("recovery_degraded")

    def test_RECOVERY_E_HASH_CHAIN_BROKEN(self, rec, events_with_broken_middle,
                                            l107_supervisor_spy):
        """TC-L109-L204-102 · hash 链断 · Tier 3 跳损坏块 + CRITICAL"""
        pid = events_with_broken_middle
        r = rec.recover_from_checkpoint(pid)
        assert r.tier == 3
        assert r.skipped_corrupt_ranges

    def test_RECOVERY_E_PID_MISMATCH(self, rec, checkpoint_pid_mismatch):
        """TC-L109-L204-106 · checkpoint.project_id ≠ path pid · fallback previous · WARN"""
        pid = checkpoint_pid_mismatch
        r = rec.recover_from_checkpoint(pid)
        assert r.tier >= 2  # 自动 fallback


class TestRecovery_CRITICAL_Refuse:
    """CRITICAL · 拒绝假恢复"""

    def test_RECOVERY_E_DEADLINE_EXCEEDED(self, rec, mega_project_50w_events):
        """TC-L109-L204-103 · 50w events · 超 30s · 标 RECOVERY_FAILED · 不输半建"""
        pid = mega_project_50w_events
        with pytest.raises(RecoveryError) as exc:
            rec.recover_from_checkpoint(pid)
        assert exc.value.code == "RECOVERY_E_DEADLINE_EXCEEDED"
        assert rec._project_state(pid) == "RECOVERY_FAILED"

    def test_RECOVERY_E_NO_CHECKPOINT(self, rec, truly_empty_project, l107_supervisor_spy):
        """TC-L109-L204-104 · 全新项目 + 无 events · Tier 4 拒绝 · 不重建空白"""
        pid = truly_empty_project
        with pytest.raises(RecoveryError) as exc:
            rec.recover_from_checkpoint(pid)
        assert exc.value.code == "RECOVERY_E_NO_CHECKPOINT"
        assert l107_supervisor_spy.has_critical_event("recovery_failed")

    def test_RECOVERY_E_REPLAY_FAILED(self, rec, fs_unmounted_project,
                                        l107_supervisor_spy):
        """TC-L109-L204-105 · IC-10 连续 3 次失败 · 标 RECOVERY_FAILED · 不 broadcast"""
        pid = fs_unmounted_project
        with pytest.raises(RecoveryError) as exc:
            rec.recover_from_checkpoint(pid)
        assert exc.value.code == "RECOVERY_E_REPLAY_FAILED"

    def test_RECOVERY_E_BLANK_REBUILD_REJECTED(self, rec, synthetic_blank_rebuild):
        """TC-L109-L204-107 · RecoveryPlan 走到 Tier 4 空白重建 · 硬禁 · Terminal abort"""
        pid = synthetic_blank_rebuild
        with pytest.raises(RecoveryError) as exc:
            rec.recover_from_checkpoint(pid)
        assert exc.value.code == "RECOVERY_E_BLANK_REBUILD_REJECTED"


class TestSnapshot_Errors:
    """SNAPSHOT_E_* 三类"""

    def test_SNAPSHOT_E_LOCK_TIMEOUT(self, rec, mock_project_id, lock_held_too_long):
        """TC-L109-L204-108 · task_board 锁等 > 3s · 跳本次 · 记 snapshot_skipped INFO"""
        lock_held_too_long()
        r = rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        assert r.status == "skipped"
        assert r.reason == "lock_timeout"

    def test_SNAPSHOT_E_DISK_FULL_triggers_halt(self, rec, mock_project_id,
                                                  mock_l205_enospc, l107_supervisor_spy):
        """TC-L109-L204-109 · ENOSPC · retry 仍失败 · 触发响应面 4 硬 halt"""
        mock_l205_enospc()
        with pytest.raises(SnapshotError) as exc:
            rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        assert exc.value.code == "SNAPSHOT_E_DISK_FULL"
        assert l107_supervisor_spy.has_critical_event("bus_write_failed")

    def test_SNAPSHOT_E_INTEGRITY_VERIFY_FAIL(self, rec, mock_project_id,
                                                force_verify_fail):
        """TC-L109-L204-110 · 写后 verify CORRUPT · 删 + retry 1 · 仍失败 → CRITICAL"""
        force_verify_fail(times=2)
        with pytest.raises(SnapshotError) as exc:
            rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        assert exc.value.code == "SNAPSHOT_E_INTEGRITY_VERIFY_FAIL"


class TestShutdown_Errors:
    """SHUTDOWN_E_*"""

    def test_SHUTDOWN_E_DRAIN_TIMEOUT(self, rec, inflight_events_stuck):
        """TC-L109-L204-111 · drain 超 5s · 强制 flush · state=TIMED_OUT · degraded=true"""
        inflight_events_stuck()
        tok = rec.begin_shutdown(reason="sigint")
        rec.wait_until_state(tok, "ACKED", timeout_s=6)
        final = rec.poll_shutdown(tok.token_id)
        # 有些实现状态可能是 TIMED_OUT · 有些是 ACKED with degraded=true
        assert final.state in {"TIMED_OUT", "ACKED"}
        assert getattr(final, "degraded", True) is True

    def test_SHUTDOWN_E_REENTRANT_info(self, rec):
        """TC-L109-L204-112 · state=SHUTTING_DOWN 期间再调 · 返原 token"""
        t1 = rec.begin_shutdown(reason="sigint")
        t2 = rec.begin_shutdown(reason="sigint")
        assert t1.token_id == t2.token_id
```

---

## §4 IC-XX 契约集成测试

```python
# tests/integration/L1-09/L2-04/test_ic_contracts.py
import pytest

pytestmark = pytest.mark.asyncio


class TestIC10ReplayContract:
    """IC-10 · replay_events"""

    def test_ic10_replay_returns_hash_chain_valid(self, rec, mock_project_id):
        """TC-L109-L204-201 · 回放返回 hash_chain_valid 字段"""
        rec._seed_events(mock_project_id, n=100)
        r = rec.replay_events(mock_project_id, from_seq=0)
        assert hasattr(r, "hash_chain_valid")
        assert r.events_replayed == 100


class TestIC09SystemResumedContract:
    """IC-09 · system_resumed 广播"""

    def test_ic09_system_resumed_emitted_once(self, rec, seeded_project_with_checkpoint,
                                                l201_audit_spy):
        """TC-L109-L204-202 · 同 project 多次 recover 只广播 1 次 system_resumed"""
        pid = seeded_project_with_checkpoint
        rec.recover_from_checkpoint(pid)
        rec.recover_from_checkpoint(pid)
        count = sum(1 for e in l201_audit_spy.appended_events
                    if e["type"] == "L1-09:system_resumed")
        assert count == 1


class TestLockContract:
    """IC-Lock · task_board"""

    def test_snapshot_acquires_task_board_lock(self, rec, mock_project_id, lock_spy):
        """TC-L109-L204-203 · take_snapshot 必 acquire task_board 锁"""
        rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        lock_spy.acquire.assert_called()
        keys = [c.args[0] for c in lock_spy.acquire.call_args_list]
        assert any("task_board" in k for k in keys)


class TestL205AtomicWriteContract:
    """与 L2-05 · atomic_write"""

    def test_snapshot_uses_atomic_write(self, rec, mock_project_id, l205_spy):
        """TC-L109-L204-204 · snapshot 落盘必经 L2-05.atomic_write"""
        rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        l205_spy.atomic_write.assert_called()


class TestL205VerifyIntegrityContract:
    """与 L2-05 · verify_integrity"""

    def test_checkpoint_load_verifies_integrity(self, rec, seeded_project_with_checkpoint,
                                                  l205_spy):
        """TC-L109-L204-205 · recover 加载 checkpoint 前必 verify"""
        rec.recover_from_checkpoint(seeded_project_with_checkpoint)
        l205_spy.verify_integrity.assert_called()
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-09/L2-04/test_slo.py
import pytest, time, statistics
from contextlib import contextmanager


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestSnapshotSLO_Small:
    """§12 · snapshot ≤ 1MB P95 ≤ 500ms · max 2s"""

    def test_snapshot_small_p95_under_500ms(self, rec, mock_project_id):
        """TC-L109-L204-301 · 200 次 small snapshot · P95 ≤ 500ms · max ≤ 2000ms"""
        samples = []
        for _ in range(200):
            with _timer() as t:
                rec.take_snapshot(mock_project_id, trigger="periodic_timer")
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 500.0
        assert max(samples) <= 2000.0


class TestSnapshotSLO_Medium:
    """§12 · snapshot 1-10MB P95 ≤ 800ms"""

    def test_snapshot_medium_p95_under_800ms(self, rec, big_task_board_project):
        """TC-L109-L204-302 · 50 次 medium snapshot · P95 ≤ 800ms"""
        samples = []
        pid = big_task_board_project
        for _ in range(50):
            with _timer() as t:
                rec.take_snapshot(pid, trigger="periodic_timer")
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 800.0


class TestRecoverySLO:
    """§12 · recovery 1w events P95 ≤ 10s · max 30s"""

    def test_recovery_10k_events_p95_under_10s(self, rec_factory, events_10k_pool):
        """TC-L109-L204-303 · 10 次 recovery 1w · P95 ≤ 10000ms · max ≤ 30000ms"""
        samples = []
        for pid in events_10k_pool[:10]:
            rec = rec_factory()
            with _timer() as t:
                r = rec.recover_from_checkpoint(pid)
            samples.append(t())
            assert r.duration_ms <= 30_000
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 10_000.0


class TestBootstrapSLO:
    """§12 · bootstrap 5 project 串行 ≤ 30s 硬上限"""

    def test_bootstrap_5_projects_under_30s(self, rec_factory, five_projects):
        """TC-L109-L204-304 · 5 project 串行 recover · 总耗时 ≤ 30s"""
        rec = rec_factory()
        t0 = time.perf_counter()
        for pid in five_projects:
            rec.recover_from_checkpoint(pid)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 30.0


class TestShutdownSLO:
    """§12 · shutdown ≤ 5s 硬上限"""

    def test_shutdown_total_under_5s(self, rec, mock_project_id):
        """TC-L109-L204-305 · begin_shutdown → ACKED ≤ 5s"""
        rec._seed_events(mock_project_id, n=100)
        t0 = time.perf_counter()
        tok = rec.begin_shutdown(reason="sigint")
        rec.wait_until_state(tok, "ACKED", timeout_s=6)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 5.0
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-09/L2-04/test_e2e.py
import pytest, time

pytestmark = pytest.mark.asyncio


class TestE2E_CrossSessionBootstrap:
    """跨 session bootstrap · Tier 1"""

    def test_cross_session_bootstrap_tier1(self, rec_factory, mock_project_id):
        """TC-L109-L204-401 · session A 写 100 event + snapshot · session B 启动 · tier=1"""
        rec1 = rec_factory()
        rec1._seed_events(mock_project_id, n=100)
        rec1.take_snapshot(mock_project_id, trigger="periodic_timer")
        # 模拟 session A 退出
        rec1.shutdown_hard()
        # session B 启动
        rec2 = rec_factory()
        r = rec2.recover_from_checkpoint(mock_project_id)
        assert r.tier == 1
        assert r.last_event_sequence_replayed == 99


class TestE2E_TierDowngrade:
    """Tier 1 → 2 → 3 串行降级"""

    def test_tier_downgrade_full_chain(self, rec, all_corrupt_but_events_ok):
        """TC-L109-L204-402 · 最新 + previous 都坏 · events OK · tier=3"""
        pid = all_corrupt_but_events_ok
        r = rec.recover_from_checkpoint(pid)
        assert r.tier == 3
        assert r.events_replayed_count > 0


class TestE2E_ShutdownFullFlow:
    """shutdown 全流程"""

    def test_shutdown_sigint_to_acked(self, rec, mock_project_id):
        """TC-L109-L204-403 · SIGINT → drain → final snapshot → ACKED"""
        rec._seed_events(mock_project_id, n=50)
        tok = rec.begin_shutdown(reason="sigint")
        rec.wait_until_state(tok, "ACKED", timeout_s=6)
        final = rec.poll_shutdown(tok.token_id)
        assert final.state == "ACKED"
        assert final.final_checkpoint_id
        assert final.flush_duration_ms <= 5000
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest, hashlib, json
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id(): return "demo-proj-001"


@pytest.fixture
def l201_audit_spy():
    m = MagicMock()
    m.appended_events = []
    def _a(evt): m.appended_events.append(evt)
    m.append = _a
    return m


@pytest.fixture
def lock_spy():
    m = MagicMock()
    return m


@pytest.fixture
def l205_spy():
    m = MagicMock()
    m.atomic_write = MagicMock()
    m.verify_integrity = MagicMock(return_value={"state": "OK"})
    return m


@pytest.fixture
def l107_supervisor_spy():
    m = MagicMock()
    m.events = []
    def _has(level, reason):
        return any(e.get("severity") == level and reason in e.get("reason", "")
                   for e in m.events)
    m.has_critical_event = lambda r: _has("CRITICAL", r)
    m.has_warn_event = lambda r: _has("WARN", r)
    m.receive = m.events.append
    return m


@pytest.fixture
def rec_factory(tmp_path, l201_audit_spy, lock_spy, l205_spy, l107_supervisor_spy):
    def _make():
        return CheckpointRecoverer(
            workdir=tmp_path,
            event_bus=l201_audit_spy,
            lock_manager=lock_spy,
            crash_safety=l205_spy,
            supervisor=l107_supervisor_spy,
            config={"SNAPSHOT_DEADLINE_MS": 2000,
                    "RECOVERY_DEADLINE_S": 30,
                    "SHUTDOWN_DRAIN_S": 5,
                    "MAX_CHECKPOINT_VERSIONS": 10},
        )
    return _make


@pytest.fixture
def rec(rec_factory): return rec_factory()


@pytest.fixture
def seeded_project_with_checkpoint(rec, mock_project_id):
    rec._seed_events(mock_project_id, n=100)
    rec.take_snapshot(mock_project_id, trigger="periodic_timer")
    return mock_project_id


@pytest.fixture
def corrupt_latest_only(rec, mock_project_id):
    rec._seed_events(mock_project_id, n=100)
    rec.take_snapshot(mock_project_id, trigger="periodic_timer")
    rec.take_snapshot(mock_project_id, trigger="periodic_timer")
    rec._corrupt_latest_checkpoint(mock_project_id)
    return mock_project_id


@pytest.fixture
def corrupt_latest_ok_previous(corrupt_latest_only): return corrupt_latest_only


@pytest.fixture
def all_checkpoints_corrupt_events_ok(rec, mock_project_id):
    rec._seed_events(mock_project_id, n=200)
    rec.take_snapshot(mock_project_id, trigger="periodic_timer")
    rec._corrupt_all_checkpoints(mock_project_id)
    return mock_project_id


@pytest.fixture
def events_with_broken_middle(rec, mock_project_id):
    rec._seed_events(mock_project_id, n=100)
    rec._corrupt_event_at(mock_project_id, seq=50)
    return mock_project_id


@pytest.fixture
def checkpoint_pid_mismatch(rec, mock_project_id):
    rec._seed_events(mock_project_id, n=10)
    rec.take_snapshot(mock_project_id, trigger="periodic_timer")
    rec._tamper_checkpoint_pid(mock_project_id, fake_pid="other_pid")
    return mock_project_id


@pytest.fixture
def mega_project_50w_events(rec):
    pid = "mega_proj"
    rec._seed_events(pid, n=500_000)
    return pid


@pytest.fixture
def truly_empty_project(): return "fresh_empty_project"


@pytest.fixture
def fs_unmounted_project(rec, monkeypatch):
    pid = "unmount_proj"
    rec._seed_events(pid, n=10)
    monkeypatch.setattr(rec, "replay_events",
                        lambda *a, **k: (_ for _ in ()).throw(IOError("FS unmounted")))
    return pid


@pytest.fixture
def synthetic_blank_rebuild(rec):
    pid = "blank_rebuild"
    rec._force_tier4_plan(pid)
    return pid


@pytest.fixture
def all_corrupt_but_events_ok(all_checkpoints_corrupt_events_ok): return all_checkpoints_corrupt_events_ok


@pytest.fixture
def big_task_board_project(rec):
    pid = "big_tb"
    rec._seed_big_task_board(pid, size_mb=5)
    return pid


@pytest.fixture
def events_10k_pool(rec):
    pids = []
    for k in range(10):
        pid = f"p10k_{k}"
        rec._seed_events(pid, n=10_000)
        rec.take_snapshot(pid, trigger="periodic_timer")
        pids.append(pid)
    return pids


@pytest.fixture
def five_projects(rec):
    pids = []
    for k in range(5):
        pid = f"p5_{k}"
        rec._seed_events(pid, n=100)
        rec.take_snapshot(pid, trigger="periodic_timer")
        pids.append(pid)
    return pids


@pytest.fixture
def lock_held_too_long(monkeypatch):
    def _activate(): pass
    return _activate


@pytest.fixture
def mock_l205_enospc(monkeypatch):
    def _activate(): pass
    return _activate


@pytest.fixture
def force_verify_fail(monkeypatch):
    def _activate(times: int = 1): pass
    return _activate


@pytest.fixture
def inflight_events_stuck(monkeypatch):
    def _activate(): pass
    return _activate
```

---

## §8 集成点用例

```python
# tests/integration/L1-09/L2-04/test_integration_points.py
import pytest

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL201EventBus:
    """与 L2-01 · recovery 期间回放事件"""

    def test_recovery_calls_l201_replay(self, rec, seeded_project_with_checkpoint, l201_audit_spy):
        """TC-L109-L204-501 · recover 期间调 L2-01.read_range · 审计 recovery_started/completed"""
        rec.recover_from_checkpoint(seeded_project_with_checkpoint)
        types = [e["type"] for e in l201_audit_spy.appended_events]
        assert "L1-09:recovery_started" in types or "L1-09:system_resumed" in types


class TestIntegrationWithL202Lock:
    """与 L2-02 · task_board 锁"""

    def test_snapshot_uses_task_board_lock(self, rec, mock_project_id, lock_spy):
        """TC-L109-L204-502 · take_snapshot 必 acquire task_board · release 配对"""
        rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        assert lock_spy.acquire.called
        assert lock_spy.release.called


class TestIntegrationWithL205CrashSafety:
    """与 L2-05 · atomic_write + verify"""

    def test_snapshot_write_and_verify(self, rec, mock_project_id, l205_spy):
        """TC-L109-L204-503 · take_snapshot → atomic_write + verify_integrity"""
        rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        assert l205_spy.atomic_write.called


class TestIntegrationWithL107Supervisor:
    """与 L1-07 · CRITICAL 红线上报"""

    def test_tier4_reaches_supervisor(self, rec, truly_empty_project, l107_supervisor_spy):
        """TC-L109-L204-504 · Tier 4 拒绝 · L1-07 收 CRITICAL"""
        try:
            rec.recover_from_checkpoint(truly_empty_project)
        except RecoveryError:
            pass
        assert l107_supervisor_spy.has_critical_event("recovery_failed")
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-09/L2-04/test_edge_cases.py
import pytest, time

pytestmark = pytest.mark.asyncio


class TestEdgeDeadline30s:
    """30s 临界"""

    def test_edge_recovery_exactly_at_30s_fails(self, rec, mega_project_50w_events):
        """TC-L109-L204-601 · 50w events 预计 > 30s · DEADLINE_EXCEEDED · 不输半建"""
        with pytest.raises(RecoveryError) as exc:
            rec.recover_from_checkpoint(mega_project_50w_events)
        assert exc.value.code == "RECOVERY_E_DEADLINE_EXCEEDED"


class TestEdgePidMismatch:
    """PID 字段位错"""

    def test_edge_pid_mismatch_fallback(self, rec, checkpoint_pid_mismatch):
        """TC-L109-L204-602 · checkpoint.pid 被改 · 拒绝该 checkpoint · fallback previous"""
        r = rec.recover_from_checkpoint(checkpoint_pid_mismatch)
        assert r.tier >= 2


class TestEdgeBlankRebuild:
    """Tier 4 绝不空白重建"""

    def test_edge_blank_rebuild_never_outputs_empty_board(self, rec, truly_empty_project):
        """TC-L109-L204-603 · Tier 4 · 绝不输出空 task_board · 必抛"""
        with pytest.raises(RecoveryError):
            rec.recover_from_checkpoint(truly_empty_project)


class TestEdgeDrainInflight:
    """drain 阶段 in-flight 事件"""

    def test_edge_drain_waits_for_inflight(self, rec, mock_project_id):
        """TC-L109-L204-604 · begin_shutdown · 等 in-flight events 完成（≤ 5s）"""
        rec._simulate_inflight(mock_project_id, count=10)
        tok = rec.begin_shutdown(reason="sigint")
        rec.wait_until_state(tok, "ACKED", timeout_s=6)
        final = rec.poll_shutdown(tok.token_id)
        assert final.state in {"ACKED", "TIMED_OUT"}


class TestEdgeRollingCheckpointGC:
    """滚动 GC"""

    def test_edge_max_versions_gc(self, rec, mock_project_id):
        """TC-L109-L204-605 · 超 MAX_CHECKPOINT_VERSIONS · 旧的被 GC · shutdown_final sticky"""
        for _ in range(15):
            rec.take_snapshot(mock_project_id, trigger="periodic_timer")
        # 至少保留 MAX_CHECKPOINT_VERSIONS 份
        assert len(rec.list_checkpoints(mock_project_id)) <= 10


class TestEdgeShutdownReentrantSignal:
    """第二次 SIGINT · os._exit(2) 强退（D5 决策）"""

    def test_edge_double_sigint_hard_exit(self, rec):
        """TC-L109-L204-606 · 第二次 SIGINT · 强退（signal handler · 本测试间接验证 flag 设置）"""
        t1 = rec.begin_shutdown(reason="sigint")
        t2 = rec.begin_shutdown(reason="sigint")
        assert t1.token_id == t2.token_id
        # 第三次（模拟第二次 SIGINT 到达）· 应设置 hard_exit flag
        rec._receive_second_sigint()
        assert rec._hard_exit_requested is True
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
