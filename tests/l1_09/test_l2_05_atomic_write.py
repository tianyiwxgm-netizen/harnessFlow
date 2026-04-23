"""L2-05 · WP α-WP01 · atomic_write 原子写 · TDD 红→绿.

对齐：
- docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md §3.2 / §6.1 / §11
- docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-05-崩溃安全层-tests.md §2 + §3 + §4

覆盖 TC（WP01 scope = 仅 write_atomic · append / verify / recover 归 WP02/03）：
  正向（§2）：TC-L109-L205-001~005 · 共 5
  负向（§3）：TC-101 / 102 / 103 / 104 / 105 / 106 / 107 / 109 / 110 · 共 9
  契约集成（§4）：TC-201 · 共 1
合计 15 TC。
"""
from __future__ import annotations

import errno
import hashlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.l1_09 import crash_safety as cs
from app.l1_09.crash_safety import (
    ChecksumMismatch,
    DiskFullError,
    FilesystemReadOnly,
    FsyncFailed,
    IOErrorCS,
    RenameFailed,
    WriteResult,
)
from app.l1_09.crash_safety import (
    PermissionError as CSPermissionError,
)

# =========================================================
# §2 正向用例 · 5 TC
# =========================================================

class TestWriteAtomicPositive:
    """§3.2 write_atomic · 5 步 syscall 序."""

    def test_write_atomic_basic_tc001(self, tmp_fs: Path) -> None:
        """TC-L109-L205-001 · snapshot 正常 · 5 步序 · tmp 清零 · WriteResult 完整."""
        target = tmp_fs / "cp.json"
        result = cs.write_atomic(target, b"hello world")

        # 内容 + 字段
        assert target.read_bytes() == b"hello world"
        assert isinstance(result, WriteResult)
        assert result.bytes_written == 11
        assert result.content_hash == hashlib.sha256(b"hello world").hexdigest()
        assert result.retry_count == 0
        assert result.duration_ms >= 0.0
        # ULID 26 字符 · Crockford Base32
        assert len(result.op_id) == 26
        # tmp 清零（成功后无残留）
        assert not list(tmp_fs.glob("*.tmp*"))

    def test_write_atomic_replace_first_time_tc002(self, tmp_fs: Path) -> None:
        """TC-L109-L205-002 · method=replace · 首次创建 · 不走 header 校验."""
        target = tmp_fs / "first.json"
        assert not target.exists()
        result = cs.write_atomic(target, b"v1", method="replace")
        assert result.bytes_written == 2
        assert target.read_bytes() == b"v1"

    def test_write_atomic_checksum_mismatch_raises_tc003(self, tmp_fs: Path) -> None:
        """TC-L109-L205-003 · 传入 checksum · 若不符即抛 ChecksumMismatch."""
        content = b"abc"
        good = hashlib.sha256(content).hexdigest()
        target = tmp_fs / "c.json"
        # 正确 checksum · 通过
        cs.write_atomic(target, content, checksum=good)
        # 错误 checksum · 抛 ChecksumMismatch · 不写入 target（幂等保护）
        with pytest.raises(ChecksumMismatch):
            cs.write_atomic(target, content, checksum="00" * 32)

    def test_write_atomic_fsync_parent_called_tc004(self, tmp_fs: Path) -> None:
        """TC-L109-L205-004 · 第 5 步 fsync(parent_fd) 被调用 · 不同 append · 非性能路径."""
        sub = tmp_fs / "sub"
        sub.mkdir()
        target = sub / "cp.json"
        with patch("app.l1_09.crash_safety.atomic_writer.os.fsync", wraps=os.fsync) as spy:
            cs.write_atomic(target, b"x")
        # 至少两次 fsync：fd + parent_fd
        assert spy.call_count >= 2, f"expected ≥2 fsync calls (fd + parent_fd), got {spy.call_count}"

    def test_write_atomic_tmp_cleanup_on_success_tc005(self, tmp_fs: Path) -> None:
        """TC-L109-L205-005 · 成功后 *.tmp.* 全清 · target 独存."""
        target = tmp_fs / "cp.json"
        cs.write_atomic(target, b"v1")
        tmps = list(tmp_fs.glob("*.tmp*"))
        assert tmps == [], f"orphan tmp files: {tmps}"
        assert target.exists()


# =========================================================
# §3 负向用例 · 9 TC
# =========================================================

class TestWriteAtomicNegative_T2PermanentIO:
    """T2 · 持久 IO · CRITICAL · 硬 halt."""

    def test_disk_full_retries_then_raises_tc101(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TC-L109-L205-101 · ENOSPC 重试 2 次仍失败 · 抛 DiskFullError · retries_exhausted=True."""
        original_write = os.write

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "No space left on device (mocked)")

        monkeypatch.setattr(
            "app.l1_09.crash_safety.atomic_writer.os.write", fake_write
        )

        with pytest.raises(DiskFullError) as exc_info:
            cs.write_atomic(tmp_fs / "x.json", b"xxx")

        assert exc_info.value.errno == errno.ENOSPC
        assert exc_info.value.retries_exhausted is True
        assert exc_info.value.retry_count == 2
        # tmp 必须清理干净（即使失败）
        assert not list(tmp_fs.glob("*.tmp*"))
        # halt 标志
        assert exc_info.value.halt_required is True
        # 未写出 target
        assert not (tmp_fs / "x.json").exists()
        _ = original_write  # 静默未使用

    def test_fsync_failed_first_raise_zero_retry_tc102(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TC-L109-L205-102 · fsync EIO · 首次即抛 · 0 重试（§3.6 fsync 不重试铁律）."""
        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "I/O error (mocked fsync)")

        monkeypatch.setattr(
            "app.l1_09.crash_safety.atomic_writer.os.fsync", fake_fsync
        )

        with pytest.raises(FsyncFailed) as exc_info:
            cs.write_atomic(tmp_fs / "x.json", b"x")

        assert exc_info.value.retry_count == 0
        assert exc_info.value.halt_required is True
        # tmp 清理
        assert not list(tmp_fs.glob("*.tmp*"))

    def test_io_error_retries_twice_tc103(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TC-L109-L205-103 · EIO 重试 2 次 · 耗尽后 CRITICAL IOErrorCS."""

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.EIO, "I/O error (mocked)")

        monkeypatch.setattr(
            "app.l1_09.crash_safety.atomic_writer.os.write", fake_write
        )

        with pytest.raises(IOErrorCS) as exc_info:
            cs.write_atomic(tmp_fs / "x.json", b"x")

        assert exc_info.value.errno == errno.EIO
        assert exc_info.value.retry_count == 2
        assert exc_info.value.retries_exhausted is True
        assert exc_info.value.halt_required is True

    def test_filesystem_readonly_no_retry_tc104(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TC-L109-L205-104 · EROFS · 不重试 · 触发响应面 4."""

        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.EROFS, "Read-only file system (mocked)")

        monkeypatch.setattr(
            "app.l1_09.crash_safety.atomic_writer.os.open", fake_open
        )

        with pytest.raises(FilesystemReadOnly) as exc_info:
            cs.write_atomic(tmp_fs / "x.json", b"x")

        assert exc_info.value.errno == errno.EROFS
        assert exc_info.value.retry_count == 0  # 不重试
        assert exc_info.value.halt_required is True

    def test_rename_failed_exdev_tc110(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TC-L109-L205-110 · EXDEV 跨 FS · 配置错 · retries ≤ 1."""

        def fake_rename(src: str, dst: str) -> None:
            raise OSError(errno.EXDEV, "Invalid cross-device link (mocked)")

        monkeypatch.setattr(
            "app.l1_09.crash_safety.atomic_writer.os.rename", fake_rename
        )

        with pytest.raises(RenameFailed) as exc_info:
            cs.write_atomic(tmp_fs / "x.json", b"x")

        assert exc_info.value.errno == errno.EXDEV
        assert exc_info.value.halt_required is True
        # tmp 清理
        assert not list(tmp_fs.glob("*.tmp*"))


class TestWriteAtomicNegative_T3LogicErrors:
    """T3 · 逻辑错 · ERROR · 不触发 halt."""

    def test_permission_denied_no_retry_tc105(self, tmp_fs: Path) -> None:
        """TC-L109-L205-105 · chmod 555 parent · PermissionError · 不重试."""
        os.chmod(tmp_fs, 0o555)
        try:
            with pytest.raises(CSPermissionError) as exc_info:
                cs.write_atomic(tmp_fs / "x.json", b"x")
            assert exc_info.value.retry_count == 0
            assert exc_info.value.halt_required is False
        finally:
            os.chmod(tmp_fs, 0o755)  # 恢复 · 让 pytest cleanup

    def test_path_not_found_assertion_tc106(self) -> None:
        """TC-L109-L205-106 · 父目录不存在 · AssertionError."""
        with pytest.raises(AssertionError):
            cs.write_atomic(Path("/nonexistent_dir_xyz/a.json"), b"x")

    def test_relative_path_assertion_tc107(self) -> None:
        """TC-L109-L205-107 · 相对路径 · AssertionError."""
        with pytest.raises(AssertionError):
            cs.write_atomic(Path("relative.json"), b"x")


class TestWriteAtomicNegative_T1Transient:
    """T1 · 瞬时 IO · 重试后成功."""

    def test_partial_write_retried_then_success_tc109(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TC-L109-L205-109 · write 返回字节数 < len · 重试后成功."""
        call_count = {"n": 0}
        original_write = os.write

        def fake_write(fd: int, data: bytes) -> int:
            call_count["n"] += 1
            if call_count["n"] == 1:
                # 首次 partial：只写一半
                return original_write(fd, data[: max(1, len(data) // 2)])
            # 后续完整写
            return original_write(fd, data)

        monkeypatch.setattr(
            "app.l1_09.crash_safety.atomic_writer.os.write", fake_write
        )

        target = tmp_fs / "x.json"
        result = cs.write_atomic(target, b"xxxxxx")

        assert result.retry_count >= 1
        assert result.bytes_written == 6
        assert target.read_bytes() == b"xxxxxx"
        # tmp 清零
        assert not list(tmp_fs.glob("*.tmp*"))


# =========================================================
# §4 契约集成 · 1 TC
# =========================================================

class TestWriteAtomicContract:
    """IC schema · 供 L2-04 / L1-02 消费."""

    def test_write_result_schema_stable_tc201(self, tmp_fs: Path) -> None:
        """TC-L109-L205-201 · L2-04 调 write_atomic · WriteResult 字段稳定."""
        target = tmp_fs / "checkpoint.json"
        result = cs.write_atomic(target, b'{"snapshot":1}')

        # 字段存在 + 类型
        assert isinstance(result.op_id, str) and len(result.op_id) == 26
        assert isinstance(result.content_hash, str) and len(result.content_hash) == 64
        assert result.bytes_written == 14
        assert result.retry_count in {0, 1, 2}
        assert isinstance(result.duration_ms, float)

        # pydantic frozen · 不可改
        with pytest.raises(Exception):  # ValidationError 或 AttributeError
            result.bytes_written = 999  # type: ignore[misc]

        # model_dump 可序列化（L2-04 写审计日志用）
        dumped = result.model_dump()
        assert dumped["op_id"] == result.op_id
        assert dumped["content_hash"] == result.content_hash
        assert dumped["bytes_written"] == 14


# =========================================================
# §4 补充边界 TC（内部分支覆盖）
# =========================================================

class TestWriteAtomicBranchCoverage:
    """补齐 _map_oserror_to_cs / method 校验 / rename 重试等分支."""

    def test_invalid_method_raises_invalid_argument(self, tmp_fs: Path) -> None:
        """method 非 'snapshot'|'replace' · runtime 抛 InvalidArgumentError."""
        from app.l1_09.crash_safety import InvalidArgumentError
        with pytest.raises(InvalidArgumentError):
            cs.write_atomic(tmp_fs / "x.json", b"x", method="unknown")  # type: ignore[arg-type]

    def test_einval_mapped_to_invalid_argument(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EINVAL · 不重试 · InvalidArgumentError."""
        from app.l1_09.crash_safety import InvalidArgumentError

        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.EINVAL, "Invalid argument (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.atomic_writer.os.open", fake_open)
        with pytest.raises(InvalidArgumentError) as exc:
            cs.write_atomic(tmp_fs / "x.json", b"x")
        assert exc.value.retry_count == 0

    def test_eaccess_via_open_mapped_to_permission(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EACCES from os.open · PermissionError · 不重试."""
        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.EACCES, "Permission denied (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.atomic_writer.os.open", fake_open)
        with pytest.raises(CSPermissionError) as exc:
            cs.write_atomic(tmp_fs / "x.json", b"x")
        assert exc.value.retry_count == 0

    def test_unexpected_errno_mapped_to_io_error(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """未知 errno · 保守当 IO 处理 · 不可重试路径（EBADF 非可重试列表）."""
        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.EBADF, "Bad file descriptor (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.atomic_writer.os.open", fake_open)
        with pytest.raises(IOErrorCS) as exc:
            cs.write_atomic(tmp_fs / "x.json", b"x")
        # EBADF 非 _is_retryable 集合 · 立即上抛 · retry_count=0
        assert exc.value.retry_count == 0
        assert exc.value.errno == errno.EBADF

    def test_rename_ebusy_retries_once_then_succeeds(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EBUSY · rename 重试 1 次后成功（覆盖 _rename_with_retry backoff 分支）."""
        original_rename = os.rename
        state = {"calls": 0}

        def fake_rename(src: str, dst: str) -> None:
            state["calls"] += 1
            if state["calls"] == 1:
                raise OSError(errno.EBUSY, "Device or resource busy (mocked)")
            original_rename(src, dst)

        monkeypatch.setattr("app.l1_09.crash_safety.atomic_writer.os.rename", fake_rename)
        target = tmp_fs / "x.json"
        result = cs.write_atomic(target, b"ebusy_ok")
        assert target.read_bytes() == b"ebusy_ok"
        assert result.bytes_written == 8
        assert state["calls"] == 2  # 首次 EBUSY · 重试成功


def test_tmp_fs_fixture_isolation(tmp_fs: Path, another_project_id: str) -> None:
    """PM-14 sanity · tmp_fs 与 project_id 独立（非 TC · fixture 冒烟）."""
    assert tmp_fs.exists()
    assert isinstance(another_project_id, str)
    assert another_project_id.startswith("proj-")
