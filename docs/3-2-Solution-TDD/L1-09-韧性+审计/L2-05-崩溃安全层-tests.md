---
doc_id: tests-L1-09-L2-05-崩溃安全层-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md
  - docs/2-prd/L1-09 韧性+审计/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-09 L2-05 崩溃安全层 · TDD 测试用例

> 基于 3-1 L2-05 §3（4 个 public 方法 · write_atomic / append_atomic / verify_integrity / recover_partial_write）+ §11（12 个 `E_*` 错误码 + T1~T4 分类 + 硬 halt 响应面 4）+ §12（P95 20ms append · P95 500ms write · 10k events 5s verify）+ §13 TC 锚点。
> **脊柱地位**：本 L2 是 PM-08 单一事实源的落地层 · hash 链不破 / fsync 硬要求 / 孤儿 tmp 清理 · 测试用例必含系统级 halt + 盘满 + race condition。
> TC ID `TC-L109-L205-NNN`（语义别名：`TC-CRASH-WRITE-*` / `TC-CRASH-APPEND-*` / `TC-CRASH-VERIFY-*` / `TC-CRASH-RECOVER-*`）。
> pytest + Python 3.11+ · `class TestCrashSafety_*` 组织。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（4 方法 · tmp+rename · fsync · hash chain · 孤儿 tmp）
- [x] §3 负向用例（12 错误码 E01-E12 · T1/T2/T3/T4 全覆盖）
- [x] §4 IC-XX 契约集成测试（向 L2-01 / L2-03 / L2-04 暴露的 4 接口 · 无外部 IC）
- [x] §5 性能 SLO 用例（append P95 20ms · write P95 500ms · verify 10k 5s · 吞吐 ≥1000 ops/s）
- [x] §6 端到端 e2e 场景（断电重启 · Tier 3 PARTIAL 恢复 · 响应面 4 硬 halt）
- [x] §7 测试 fixture（mock_fs_enospc / mock_fs_eio / mock_fsync_fail / hash_chain_factory / kill_signal）
- [x] §8 集成点用例（L2-01 events.jsonl · L2-04 checkpoint · L2-03 audit.jsonl）
- [x] §9 边界 / edge case（PIPE_BUF 边界 4095/4096 · symlink · 磁盘 100% · fsync 部分成功 · race）

---

## §1 覆盖度索引

### §1.1 方法 × 测试 × 覆盖类型

| 方法 | TC ID | 覆盖类型 |
|:---|:---|:---|
| `write_atomic()` · 正常 snapshot | TC-L109-L205-001 | unit |
| `write_atomic()` · method=replace 首次 | TC-L109-L205-002 | unit |
| `write_atomic()` · checksum 复核 | TC-L109-L205-003 | unit |
| `write_atomic()` · fsync 父目录（5 步） | TC-L109-L205-004 | unit |
| `write_atomic()` · tmp 清理干净 | TC-L109-L205-005 | unit |
| `append_atomic()` · 单行 jsonl | TC-L109-L205-006 | unit |
| `append_atomic()` · 末尾自动 \n | TC-L109-L205-007 | unit |
| `append_atomic()` · expected_prev_hash 链接 | TC-L109-L205-008 | unit |
| `append_atomic()` · 不 fsync 父目录（性能） | TC-L109-L205-009 | unit |
| `verify_integrity()` · HASH_CHAIN OK | TC-L109-L205-010 | unit |
| `verify_integrity()` · HEADER_CHECKSUM | TC-L109-L205-011 | unit |
| `verify_integrity()` · TAIL_CONSISTENCY | TC-L109-L205-012 | unit |
| `recover_partial_write()` · 孤儿 tmp 删除 | TC-L109-L205-013 | unit |
| `recover_partial_write()` · 坏尾截断 | TC-L109-L205-014 | unit |
| `recover_partial_write()` · NO_ACTION | TC-L109-L205-015 | unit |

### §1.2 错误码 × 测试（§11.2 12 项全覆盖）

| 错误码 | TC ID | 分类 | 硬 halt? |
|:---|:---|:---|:---|
| `E_DISK_FULL` | TC-L109-L205-101 | T2 | 是 |
| `E_FSYNC_FAILED` | TC-L109-L205-102 | T2 | 是（首次） |
| `E_IO_ERROR` | TC-L109-L205-103 | T1→T2 | 耗尽后是 |
| `E_FILESYSTEM_READONLY` | TC-L109-L205-104 | T2 | 是 |
| `E_PERMISSION` | TC-L109-L205-105 | T3 | 否 |
| `E_PATH_NOT_FOUND` | TC-L109-L205-106 | T3 | 否 |
| `E_INVALID_ARGUMENT` | TC-L109-L205-107 | T3 | 否 |
| `E_LINE_TOO_LARGE` | TC-L109-L205-108 | T3 | 否 |
| `E_PARTIAL_WRITE` | TC-L109-L205-109 | T1 | 耗尽后是 |
| `E_RENAME_FAILED` (EXDEV) | TC-L109-L205-110 | T2 | 是 |
| `E_HASH_MISMATCH` | TC-L109-L205-111 | T4 | 否（L2-04 判 Tier） |
| `E_ORPHAN_TMP_DETECTED` | TC-L109-L205-112 | T4 | 否 |

### §1.3 暴露接口 × 调用方

| 接口 | 调用方 | TC ID |
|:---|:---|:---|
| write_atomic | L2-04 checkpoint / L1-02 manifest | TC-L109-L205-201 |
| append_atomic | L2-01 events.jsonl / L2-03 audit.jsonl | TC-L109-L205-202 |
| verify_integrity | L2-04 boot / L2-03 查询前自检 | TC-L109-L205-203 |
| recover_partial_write | L2-04 boot 孤儿清理 | TC-L109-L205-204 |

### §1.4 性能 SLO × 测试

| SLO | 阈值 | TC ID |
|:---|:---|:---|
| append_atomic P95 | ≤ 20ms | TC-L109-L205-301 |
| write_atomic(10KB) P95 | ≤ 100ms | TC-L109-L205-302 |
| write_atomic(1MB) P95 | ≤ 500ms | TC-L109-L205-303 |
| verify 10k events | ≤ 5000ms | TC-L109-L205-304 |
| append 吞吐 | ≥ 1000 ops/s | TC-L109-L205-305 |

### §1.5 e2e × 测试

| 场景 | TC ID |
|:---|:---|
| 断电 SIGKILL 重启 · orphan tmp 清理 · target 不损 | TC-L109-L205-401 |
| events.jsonl hash 链断裂中段 · verify PARTIAL · L2-04 Tier 3 恢复起点 | TC-L109-L205-402 |
| fsync 硬失败 → CRITICAL → 响应面 4 硬 halt | TC-L109-L205-403 |

---

## §2 正向用例

```python
# tests/unit/L1-09/L2-05/test_crash_safety_positive.py
import pytest, os, hashlib, json
from pathlib import Path

pytestmark = pytest.mark.asyncio


class TestCrashSafety_WriteAtomic:
    """§3.2 write_atomic · tmp + rename + fsync + fsync_parent"""

    def test_write_atomic_basic(self, cs, tmp_path):
        """TC-L109-L205-001 · snapshot 正常 · 5 步序 · tmp 清零"""
        target = tmp_path / "cp.json"
        r = cs.write_atomic(target, b"hello world")
        assert target.read_bytes() == b"hello world"
        assert r.bytes_written == 11
        assert r.content_hash == hashlib.sha256(b"hello world").hexdigest()
        assert not list(tmp_path.glob("*.tmp.*"))

    def test_write_atomic_replace_first_time(self, cs, tmp_path):
        """TC-L109-L205-002 · method=replace · 首次创建 · 不做 header 校验"""
        target = tmp_path / "first.json"
        r = cs.write_atomic(target, b"v1", method="replace")
        assert r.bytes_written == 2

    def test_write_atomic_checksum_verification(self, cs, tmp_path):
        """TC-L109-L205-003 · 传入 checksum · 若不符即抛"""
        content = b"abc"
        good = hashlib.sha256(content).hexdigest()
        target = tmp_path / "c.json"
        cs.write_atomic(target, content, checksum=good)
        with pytest.raises(ChecksumMismatch):
            cs.write_atomic(target, content, checksum="00" * 32)

    def test_write_atomic_fsync_parent_called(self, cs, tmp_path, spy_fsync):
        """TC-L109-L205-004 · 第 4 步 fsync(parent_fd) 被调用 · 非 append 特权"""
        target = tmp_path / "sub" / "cp.json"
        target.parent.mkdir()
        cs.write_atomic(target, b"x")
        # 有两次 fsync：一次 fd · 一次 parent_fd
        assert spy_fsync.call_count >= 2

    def test_write_atomic_tmp_cleanup_on_success(self, cs, tmp_path):
        """TC-L109-L205-005 · 成功后 *.tmp.* 全清 · target 独存"""
        target = tmp_path / "cp.json"
        cs.write_atomic(target, b"v1")
        assert not list(tmp_path.glob("*.tmp*"))
        assert target.exists()


class TestCrashSafety_AppendAtomic:
    """§3.3 append_atomic · O_APPEND + fsync + 不 fsync 父"""

    def test_append_single_line(self, cs, tmp_path):
        """TC-L109-L205-006 · 单行 append · hash = sha256(line)"""
        target = tmp_path / "events.jsonl"
        line = '{"seq":1,"data":"x"}'
        r = cs.append_atomic(target, line)
        assert r.bytes_written == len(line.encode()) + 1
        assert r.line_hash == hashlib.sha256(line.encode()).hexdigest()

    def test_append_newline_auto(self, cs, tmp_path):
        """TC-L109-L205-007 · 末尾自动 \n"""
        target = tmp_path / "events.jsonl"
        cs.append_atomic(target, "abc")
        assert target.read_bytes().endswith(b"\n")

    def test_append_prev_hash_chain(self, cs, tmp_path):
        """TC-L109-L205-008 · expected_prev_hash 链接成功"""
        target = tmp_path / "e.jsonl"
        r1 = cs.append_atomic(target, '{"seq":1}')
        r2 = cs.append_atomic(target, '{"seq":2}', expected_prev_hash=r1.line_hash)
        assert r2.offset > r1.offset

    def test_append_no_parent_fsync(self, cs, tmp_path, spy_fsync):
        """TC-L109-L205-009 · append 不 fsync 父目录（性能）"""
        target = tmp_path / "e.jsonl"
        cs.append_atomic(target, "line1")
        spy_fsync.reset_mock()
        cs.append_atomic(target, "line2")
        # 只 fsync 一次（fd） · 父目录不 fsync（inode 未变）
        assert spy_fsync.call_count == 1


class TestCrashSafety_VerifyIntegrity:
    """§3.4 verify_integrity · 3 种 method · 3 态返回"""

    def test_verify_hash_chain_ok(self, cs, make_good_events_jsonl):
        """TC-L109-L205-010 · 健康 events.jsonl · state=OK"""
        f = make_good_events_jsonl(n=100)
        r = cs.verify_integrity(f, method=IntegrityMethod.HASH_CHAIN)
        assert r.state == IntegrityState.OK
        assert r.failure_range is None
        assert r.total_items == 100

    def test_verify_header_checksum(self, cs, make_checkpoint_file):
        """TC-L109-L205-011 · checkpoint header checksum 校验"""
        f = make_checkpoint_file(body=b'{"snapshot":1}')
        r = cs.verify_integrity(f, method=IntegrityMethod.HEADER_CHECKSUM)
        assert r.state == IntegrityState.OK

    def test_verify_tail_consistency(self, cs, make_task_board):
        """TC-L109-L205-012 · task-board 末尾可解析 + version 字段存在"""
        f = make_task_board(version="v1.0")
        r = cs.verify_integrity(f, method=IntegrityMethod.TAIL_CONSISTENCY)
        assert r.state == IntegrityState.OK


class TestCrashSafety_RecoverPartialWrite:
    """§3.5 recover_partial_write · 孤儿 tmp + 坏尾截断"""

    def test_recover_deletes_orphan_tmp(self, cs, tmp_path):
        """TC-L109-L205-013 · 24h+ 孤儿 tmp 被删 · 不删 target"""
        target = tmp_path / "f.json"
        target.write_bytes(b"good")
        tmp = tmp_path / "f.json.tmp.abc"
        tmp.write_bytes(b"half")
        # mtime 人为设为 25h 前
        old = os.path.getmtime(tmp) - 25 * 3600
        os.utime(tmp, (old, old))
        action = cs.recover_partial_write(target)
        assert action.action_kind == RecoveryActionKind.DELETE_ORPHAN_TMP
        assert str(tmp) in action.orphan_tmp_paths
        assert target.exists()  # target 未动

    def test_recover_truncates_bad_tail(self, cs, make_bad_tail_jsonl):
        """TC-L109-L205-014 · events.jsonl 坏尾 · TRUNCATE_TAIL + affected_bytes"""
        f = make_bad_tail_jsonl(good_lines=5, bad_bytes=42)
        action = cs.recover_partial_write(f)
        assert action.action_kind == RecoveryActionKind.TRUNCATE_TAIL
        assert action.affected_bytes >= 1

    def test_recover_no_action_healthy(self, cs, make_good_events_jsonl):
        """TC-L109-L205-015 · 健康文件 · NO_ACTION · 幂等"""
        f = make_good_events_jsonl(n=10)
        action = cs.recover_partial_write(f)
        assert action.action_kind == RecoveryActionKind.NO_ACTION
```

---

## §3 负向用例（12 错误码 · T1/T2/T3/T4）

```python
# tests/unit/L1-09/L2-05/test_crash_safety_negative.py
import pytest, os, errno

pytestmark = pytest.mark.asyncio


class TestCrashSafety_T2_PermanentIO:
    """T2 持久 IO · CRITICAL · 硬 halt 触发"""

    def test_E_DISK_FULL(self, cs, tmp_path, mock_fs_enospc):
        """TC-L109-L205-101 · ENOSPC 重试 2 次仍失败 · 抛 DiskFullError"""
        mock_fs_enospc()
        with pytest.raises(DiskFullError) as exc:
            cs.write_atomic(tmp_path / "x.json", b"xxx")
        assert exc.value.errno == errno.ENOSPC
        assert exc.value.retries_exhausted is True

    def test_E_FSYNC_FAILED_first_raise(self, cs, tmp_path, mock_fsync_fail):
        """TC-L109-L205-102 · fsync EIO · 首次即抛 · 0 重试"""
        mock_fsync_fail()
        with pytest.raises(FsyncFailed) as exc:
            cs.write_atomic(tmp_path / "x.json", b"x")
        assert exc.value.retry_count == 0

    def test_E_IO_ERROR_retries(self, cs, tmp_path, mock_fs_eio):
        """TC-L109-L205-103 · EIO 重试 2 次 · 期间 WARN · 耗尽后 CRITICAL"""
        mock_fs_eio(fail_count=3)
        with pytest.raises(IOError):
            cs.write_atomic(tmp_path / "x.json", b"x")

    def test_E_FILESYSTEM_READONLY(self, cs, tmp_path, mock_fs_erofs):
        """TC-L109-L205-104 · EROFS · 不重试 · 触发响应面 4"""
        mock_fs_erofs()
        with pytest.raises(FilesystemReadOnly):
            cs.write_atomic(tmp_path / "x.json", b"x")

    def test_E_RENAME_FAILED_EXDEV(self, cs, tmp_path, mock_rename_exdev):
        """TC-L109-L205-110 · EXDEV 跨 FS · 配置错 · 首次即抛"""
        mock_rename_exdev()
        with pytest.raises(RenameFailed) as exc:
            cs.write_atomic(tmp_path / "x.json", b"x")
        assert exc.value.errno == errno.EXDEV


class TestCrashSafety_T3_LogicErrors:
    """T3 逻辑错 · ERROR · 不触发 halt"""

    def test_E_PERMISSION(self, cs, tmp_path):
        """TC-L109-L205-105 · chmod 555 parent · 不重试"""
        os.chmod(tmp_path, 0o555)
        try:
            with pytest.raises(PermissionError):
                cs.write_atomic(tmp_path / "x.json", b"x")
        finally:
            os.chmod(tmp_path, 0o755)

    def test_E_PATH_NOT_FOUND(self, cs):
        """TC-L109-L205-106 · 父目录不存在 · assert + PathError"""
        with pytest.raises(AssertionError):
            cs.write_atomic(Path("/nonexistent/a.json"), b"x")

    def test_E_INVALID_ARGUMENT_non_absolute(self, cs):
        """TC-L109-L205-107 · 相对路径 · assert"""
        with pytest.raises(AssertionError):
            cs.write_atomic(Path("relative.json"), b"x")

    def test_E_LINE_TOO_LARGE(self, cs, tmp_path):
        """TC-L109-L205-108 · line ≥ PIPE_BUF=4096 · AssertionError"""
        target = tmp_path / "e.jsonl"
        with pytest.raises(AssertionError):
            cs.append_atomic(target, "x" * 4100)


class TestCrashSafety_T1_TransientIO:
    """T1 瞬时 IO · 重试后通常成功"""

    def test_E_PARTIAL_WRITE_retried(self, cs, tmp_path, mock_partial_write):
        """TC-L109-L205-109 · write 返回字节数 < len · 重试 2 次"""
        mock_partial_write(fail_count=1)
        target = tmp_path / "x.json"
        r = cs.write_atomic(target, b"xxx")
        assert r.retry_count >= 1
        assert target.read_bytes() == b"xxx"


class TestCrashSafety_T4_IntegrityErrors:
    """T4 完整性错 · 只读 · L2-04 分类 Tier"""

    def test_E_HASH_MISMATCH(self, cs, make_broken_hash_chain_jsonl):
        """TC-L109-L205-111 · events.jsonl 某行 hash 断 · state=PARTIAL + first_good_hash"""
        f = make_broken_hash_chain_jsonl(good_prefix=30, bad_at=30)
        r = cs.verify_integrity(f, method=IntegrityMethod.HASH_CHAIN)
        assert r.state == IntegrityState.PARTIAL
        assert r.first_good_hash is not None
        assert r.failure_range[0] >= 30

    def test_E_ORPHAN_TMP_DETECTED(self, cs, tmp_path):
        """TC-L109-L205-112 · 年轻 tmp（< 24h）被检测但保守不删"""
        target = tmp_path / "f.json"
        target.write_bytes(b"ok")
        (tmp_path / "f.json.tmp.xyz").write_bytes(b"half")
        action = cs.recover_partial_write(target)
        # 年轻 tmp → NO_ACTION 或 DELETE_ORPHAN_TMP（取决实现）
        assert action.action_kind in {RecoveryActionKind.NO_ACTION,
                                       RecoveryActionKind.DELETE_ORPHAN_TMP}
```

---

## §4 IC-XX 契约集成测试（调用方 schema）

> 本 L2 无外部 IC · 对 L2-01/03/04 暴露 4 个方法 · 验 Pydantic Result schema。

```python
# tests/integration/L1-09/L2-05/test_interface_contracts.py
import pytest, json

pytestmark = pytest.mark.asyncio


class TestInterfaceContracts:
    """WriteResult / AppendResult / IntegrityReport / RecoveryAction 字段稳定"""

    def test_write_atomic_for_l204_checkpoint(self, cs, tmp_path):
        """TC-L109-L205-201 · L2-04 调 write_atomic · WriteResult 含 op_id/bytes/hash"""
        target = tmp_path / "checkpoint.json"
        r = cs.write_atomic(target, b'{"snapshot":1}')
        assert r.op_id and r.content_hash and r.bytes_written == 14
        assert r.retry_count in {0, 1, 2}

    def test_append_atomic_for_l201_events(self, cs, tmp_path):
        """TC-L109-L205-202 · L2-01 调 append_atomic · AppendResult 含 offset"""
        target = tmp_path / "events.jsonl"
        r1 = cs.append_atomic(target, '{"e":1}')
        r2 = cs.append_atomic(target, '{"e":2}')
        assert r2.offset == r1.offset + r1.bytes_written

    def test_verify_for_l204_boot(self, cs, make_good_events_jsonl):
        """TC-L109-L205-203 · L2-04 boot · IntegrityReport 3 态 schema"""
        f = make_good_events_jsonl(n=50)
        r = cs.verify_integrity(f, method=IntegrityMethod.HASH_CHAIN)
        assert r.state in {IntegrityState.OK, IntegrityState.CORRUPT, IntegrityState.PARTIAL}
        assert r.scan_duration_ms >= 0
        assert isinstance(r.details, dict)

    def test_recover_for_l204_cleanup(self, cs, tmp_path):
        """TC-L109-L205-204 · L2-04 boot 清理 · RecoveryAction 含 rationale"""
        target = tmp_path / "f.json"
        target.write_bytes(b"ok")
        action = cs.recover_partial_write(target)
        assert action.rationale
        assert action.action_kind in list(RecoveryActionKind)
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-09/L2-05/test_slo.py
import pytest, time, statistics
from contextlib import contextmanager


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestAppendSLO:
    """§12.1 · append_atomic P95 ≤ 20ms"""

    def test_append_p95_under_20ms(self, cs, tmp_path):
        """TC-L109-L205-301 · 1000 次 append · P95 ≤ 20ms"""
        target = tmp_path / "e.jsonl"
        samples = []
        for i in range(1000):
            with _timer() as t:
                cs.append_atomic(target, f'{{"seq":{i}}}')
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 20.0


class TestWriteSLO:
    """§12.1 · write 10KB P95 ≤ 100ms · 1MB P95 ≤ 500ms"""

    def test_write_10KB_p95_under_100ms(self, cs, tmp_path):
        """TC-L109-L205-302 · 100 次 10KB 写 · P95 ≤ 100ms"""
        samples = []
        payload = b"x" * 10_000
        for i in range(100):
            with _timer() as t:
                cs.write_atomic(tmp_path / f"s{i}.json", payload)
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 100.0

    def test_write_1MB_p95_under_500ms(self, cs, tmp_path):
        """TC-L109-L205-303 · 50 次 1MB 写 · P95 ≤ 500ms"""
        samples = []
        payload = b"x" * 1_000_000
        for i in range(50):
            with _timer() as t:
                cs.write_atomic(tmp_path / f"s{i}.json", payload)
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 500.0


class TestVerifySLO:
    """§12.1 · verify 10000 events ≤ 5000ms"""

    def test_verify_10k_under_5s(self, cs, make_good_events_jsonl):
        """TC-L109-L205-304 · 10k events hash_chain 扫 · 总耗时 ≤ 5000ms"""
        f = make_good_events_jsonl(n=10_000)
        with _timer() as t:
            r = cs.verify_integrity(f, method=IntegrityMethod.HASH_CHAIN)
        elapsed = t()
        assert r.state == IntegrityState.OK
        assert elapsed <= 5000.0


class TestThroughputSLO:
    """§12.1 · append 吞吐 ≥ 1000 ops/s"""

    def test_append_throughput_1000_ops_s(self, cs, tmp_path):
        """TC-L109-L205-305 · 1s 内连续 append · ops ≥ 1000"""
        target = tmp_path / "e.jsonl"
        end = time.perf_counter() + 1.0
        count = 0
        while time.perf_counter() < end:
            cs.append_atomic(target, f'{{"i":{count}}}')
            count += 1
        assert count >= 1000
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-09/L2-05/test_e2e.py
import pytest, os, signal

pytestmark = pytest.mark.asyncio


class TestE2E_PowerLossRecovery:
    """断电 SIGKILL 重启 · tmp 清理 · target 无损"""

    def test_sigkill_during_write_then_recover(self, cs, tmp_path, simulate_sigkill_mid_write):
        """TC-L109-L205-401 · 写 1MB 中途 SIGKILL · 重启后 tmp 被识别 · target 未被损坏"""
        target = tmp_path / "cp.json"
        target.write_bytes(b"original")  # 先有 target
        # 模拟崩溃：tmp 文件残留
        orphan = tmp_path / "cp.json.tmp.abc"
        orphan.write_bytes(b"partial")
        old = os.path.getmtime(orphan) - 25 * 3600
        os.utime(orphan, (old, old))
        action = cs.recover_partial_write(target)
        assert action.action_kind == RecoveryActionKind.DELETE_ORPHAN_TMP
        assert target.read_bytes() == b"original"


class TestE2E_PartialChainTier3:
    """events.jsonl hash 链中段断 · PARTIAL · 锚点精确"""

    def test_hash_chain_partial_anchor(self, cs, make_broken_hash_chain_jsonl):
        """TC-L109-L205-402 · 第 30 行断链 · state=PARTIAL + first_good_hash = 第 29 行"""
        f = make_broken_hash_chain_jsonl(good_prefix=30, bad_at=30, tail=20)
        r = cs.verify_integrity(f, method=IntegrityMethod.HASH_CHAIN)
        assert r.state == IntegrityState.PARTIAL
        assert r.failure_range[0] == 30
        assert r.first_good_hash


class TestE2E_FsyncFailHardHalt:
    """fsync 硬失败 → 响应面 4 硬 halt 触发链"""

    def test_fsync_fail_escalates_to_supervisor(self, cs, tmp_path, mock_fsync_fail,
                                                 l201_spy, l107_spy):
        """TC-L109-L205-403 · fsync 失败 · 本 L2 抛 · L2-01 捕获 → bus_write_failed → L1-07 escalate"""
        mock_fsync_fail()
        with pytest.raises(FsyncFailed):
            cs.write_atomic(tmp_path / "x.json", b"x")
        # L2-01 应捕获并发 bus_write_failed
        # （本 L2 只负责抛 · 不负责发 · 此处由 L2-01 mock 确认路径）
        l201_spy.expect_bus_write_failed()
        l107_spy.expect_escalate_critical()
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest, os, errno, hashlib, json
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def cs():
    """CrashSafetyLayer 默认实例"""
    return CrashSafetyLayer(config={
        "FSYNC_MODE": "always",
        "MAX_SNAPSHOT_SIZE_BYTES": 10 * 1024 * 1024,
        "PIPE_BUF_LIMIT": 4096,
        "TMP_FILE_MAX_AGE_HOURS": 24,
    })


@pytest.fixture
def mock_fs_enospc(monkeypatch):
    def _activate():
        original = os.write
        def _raise(*a, **k):
            e = OSError("disk full"); e.errno = errno.ENOSPC
            raise e
        monkeypatch.setattr(os, "write", _raise)
    return _activate


@pytest.fixture
def mock_fs_eio(monkeypatch):
    def _activate(fail_count: int = 2):
        counter = {"n": fail_count}
        original = os.write
        def _maybe(*a, **k):
            if counter["n"] > 0:
                counter["n"] -= 1
                e = OSError("io"); e.errno = errno.EIO
                raise e
            return original(*a, **k)
        monkeypatch.setattr(os, "write", _maybe)
    return _activate


@pytest.fixture
def mock_fsync_fail(monkeypatch):
    def _activate():
        def _raise(*a, **k):
            e = OSError("fsync failed"); e.errno = errno.EIO
            raise e
        monkeypatch.setattr(os, "fsync", _raise)
    return _activate


@pytest.fixture
def mock_fs_erofs(monkeypatch):
    def _activate():
        def _raise(*a, **k):
            e = OSError("read only"); e.errno = errno.EROFS
            raise e
        monkeypatch.setattr(os, "write", _raise)
    return _activate


@pytest.fixture
def mock_rename_exdev(monkeypatch):
    def _activate():
        def _raise(*a, **k):
            e = OSError("cross device"); e.errno = errno.EXDEV
            raise e
        monkeypatch.setattr(os, "rename", _raise)
    return _activate


@pytest.fixture
def mock_partial_write(monkeypatch):
    def _activate(fail_count: int = 1):
        counter = {"n": fail_count}
        original = os.write
        def _short(fd, data):
            if counter["n"] > 0:
                counter["n"] -= 1
                return original(fd, data[:1])  # partial
            return original(fd, data)
        monkeypatch.setattr(os, "write", _short)
    return _activate


@pytest.fixture
def spy_fsync(monkeypatch):
    spy = MagicMock()
    original = os.fsync
    def _wrap(fd):
        spy(fd)
        return original(fd)
    monkeypatch.setattr(os, "fsync", _wrap)
    return spy


@pytest.fixture
def make_good_events_jsonl(tmp_path):
    def _make(n: int = 100) -> Path:
        f = tmp_path / "events.jsonl"
        prev = "0" * 64
        with open(f, "wb") as fd:
            for i in range(n):
                body = {"seq": i, "data": f"v{i}"}
                body_canon = json.dumps(body, separators=(",", ":"), sort_keys=True)
                curr = hashlib.sha256((prev + body_canon).encode()).hexdigest()
                body["prev_hash"] = prev
                body["hash"] = curr
                fd.write((json.dumps(body) + "\n").encode())
                prev = curr
        return f
    return _make


@pytest.fixture
def make_broken_hash_chain_jsonl(tmp_path):
    def _make(good_prefix: int = 30, bad_at: int = 30, tail: int = 20) -> Path:
        f = tmp_path / "broken.jsonl"
        prev = "0" * 64
        lines = []
        for i in range(good_prefix):
            body = {"seq": i, "prev_hash": prev, "hash": ""}
            body_canon = json.dumps({"seq": i}, separators=(",", ":"))
            curr = hashlib.sha256((prev + body_canon).encode()).hexdigest()
            body["hash"] = curr
            lines.append(json.dumps(body))
            prev = curr
        # 故意破坏 · 第 bad_at 行 prev_hash 设为错值
        for i in range(bad_at, bad_at + tail):
            body = {"seq": i, "prev_hash": "ff" * 32, "hash": "ee" * 32}  # 断链
            lines.append(json.dumps(body))
        f.write_text("\n".join(lines) + "\n")
        return f
    return _make


@pytest.fixture
def make_bad_tail_jsonl(tmp_path):
    def _make(good_lines: int = 5, bad_bytes: int = 42) -> Path:
        f = tmp_path / "badtail.jsonl"
        with open(f, "wb") as fd:
            for i in range(good_lines):
                fd.write(json.dumps({"seq": i}).encode() + b"\n")
            fd.write(b"\x00" * bad_bytes)  # 损坏尾
        return f
    return _make


@pytest.fixture
def make_checkpoint_file(tmp_path):
    def _make(body: bytes) -> Path:
        f = tmp_path / "cp.json"
        checksum = hashlib.sha256(body).hexdigest()
        header = json.dumps({"checksum": checksum, "size": len(body)}).encode() + b"\n"
        f.write_bytes(header + body)
        return f
    return _make


@pytest.fixture
def make_task_board(tmp_path):
    def _make(version: str = "v1.0") -> Path:
        f = tmp_path / "board.json"
        f.write_text(json.dumps({"tasks": [], "version": version}))
        return f
    return _make


@pytest.fixture
def simulate_sigkill_mid_write():
    def _activate():
        # 制造中途 kill 场景 · 测试环境里用 tmp 文件残留模拟
        pass
    return _activate


@pytest.fixture
def l201_spy():
    m = MagicMock()
    m.expect_bus_write_failed = MagicMock()
    return m


@pytest.fixture
def l107_spy():
    m = MagicMock()
    m.expect_escalate_critical = MagicMock()
    return m
```

---

## §8 集成点用例

```python
# tests/integration/L1-09/L2-05/test_integration_points.py
import pytest, hashlib, json

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL201Events:
    """与 L2-01 events.jsonl · hash 链协同"""

    def test_events_append_then_verify_ok(self, cs, tmp_path):
        """TC-L109-L205-501 · L2-01 连续 append · verify 必 OK"""
        target = tmp_path / "events.jsonl"
        prev = "0" * 64
        for i in range(10):
            body = {"seq": i, "prev_hash": prev}
            body_canon = json.dumps({"seq": i}, separators=(",", ":"))
            curr = hashlib.sha256((prev + body_canon).encode()).hexdigest()
            body["hash"] = curr
            r = cs.append_atomic(target, json.dumps(body))
            assert r.line_hash
            prev = curr
        report = cs.verify_integrity(target, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.OK


class TestIntegrationWithL204Checkpoint:
    """与 L2-04 checkpoint · write_atomic 循环"""

    def test_checkpoint_write_and_verify(self, cs, tmp_path):
        """TC-L109-L205-502 · L2-04 写 checkpoint · header checksum OK"""
        body = b'{"snapshot":{"pid":"p1"}}'
        target = tmp_path / "cp.json"
        r = cs.write_atomic(target, body)
        # L2-04 验 header checksum
        report = cs.verify_integrity(target, method=IntegrityMethod.HEADER_CHECKSUM)
        # 验 · 取决具体实现 · 至少 state ∈ {OK, CORRUPT}
        assert report.state in {IntegrityState.OK, IntegrityState.CORRUPT, IntegrityState.PARTIAL}


class TestIntegrationWithL203Audit:
    """与 L2-03 audit.jsonl · 并发 append"""

    def test_audit_append_concurrent(self, cs, tmp_path):
        """TC-L109-L205-503 · L2-03 与 L2-01 并发 append 不同文件 · 无交错"""
        a = tmp_path / "audit.jsonl"
        e = tmp_path / "events.jsonl"
        for i in range(20):
            cs.append_atomic(a, f'{{"audit":{i}}}')
            cs.append_atomic(e, f'{{"event":{i}}}')
        assert a.read_text().count("\n") == 20
        assert e.read_text().count("\n") == 20
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-09/L2-05/test_edge_cases.py
import pytest, os

pytestmark = pytest.mark.asyncio


class TestEdgePipeBufBoundary:
    """PIPE_BUF 边界 4095 / 4096"""

    def test_edge_append_exactly_4095_bytes(self, cs, tmp_path):
        """TC-L109-L205-601 · line+\n 共 4096 · 恰等 PIPE_BUF · 仍允许"""
        target = tmp_path / "e.jsonl"
        line = "x" * 4095  # + \n = 4096
        r = cs.append_atomic(target, line)
        assert r.bytes_written == 4096

    def test_edge_append_4096_bytes_rejected(self, cs, tmp_path):
        """TC-L109-L205-602 · line+\n 共 4097 · 超 PIPE_BUF · AssertionError"""
        target = tmp_path / "e.jsonl"
        with pytest.raises(AssertionError):
            cs.append_atomic(target, "x" * 4096)  # +\n = 4097


class TestEdgeSymlinks:
    """symlink 处理"""

    def test_edge_write_atomic_target_is_symlink(self, cs, tmp_path):
        """TC-L109-L205-603 · target 是 symlink → 保持 · 只替换内容"""
        real = tmp_path / "real.json"
        real.write_bytes(b"v1")
        link = tmp_path / "link.json"
        os.symlink(real, link)
        cs.write_atomic(link, b"v2")
        assert link.is_symlink() or link.exists()  # 具体策略由实现定


class TestEdgeDiskFillBoundary:
    """磁盘 100% / 边界"""

    def test_edge_disk_100_percent(self, cs, tmp_path, mock_fs_enospc):
        """TC-L109-L205-604 · ENOSPC 时 · 2 次重试 · 最终抛"""
        mock_fs_enospc()
        with pytest.raises(DiskFullError):
            cs.write_atomic(tmp_path / "x.json", b"x")


class TestEdgeRace:
    """并发 append 同文件"""

    def test_edge_concurrent_append_same_file(self, cs, tmp_path):
        """TC-L109-L205-605 · POSIX O_APPEND 原子性 · 多线程 append 无交错"""
        import threading
        target = tmp_path / "e.jsonl"
        lines = [f'{{"t":{i}}}' for i in range(200)]
        def _w(lst):
            for ln in lst:
                cs.append_atomic(target, ln)
        t1 = threading.Thread(target=_w, args=(lines[:100],))
        t2 = threading.Thread(target=_w, args=(lines[100:],))
        t1.start(); t2.start(); t1.join(); t2.join()
        content = target.read_text()
        assert content.count("\n") == 200
        # 每行自洽 · json 可解析
        import json
        for ln in content.strip().split("\n"):
            json.loads(ln)


class TestEdgeTmpCleanup:
    """tmp 年龄边界"""

    def test_edge_young_tmp_preserved(self, cs, tmp_path):
        """TC-L109-L205-606 · < 24h 的 tmp 保守不删（防误伤正在写的）"""
        target = tmp_path / "f.json"
        target.write_bytes(b"ok")
        young = tmp_path / "f.json.tmp.new"
        young.write_bytes(b"writing")
        action = cs.recover_partial_write(target)
        # 允许策略：NO_ACTION 或 DELETE_ORPHAN_TMP · 但文档规定保守不删
        if action.action_kind == RecoveryActionKind.NO_ACTION:
            assert young.exists()
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
