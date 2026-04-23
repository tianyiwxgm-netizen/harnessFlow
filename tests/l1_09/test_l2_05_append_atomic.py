"""L2-05 · WP α-WP02 · append_atomic jsonl 行原子追加 · TDD 红→绿.

对齐：
- 3-1 L2-05 §3.3 / §6.2 / §3.6（错误码）
- 3-2 L2-05-tests §2 正向 TC-006~009 + §3 负向 TC-108 + §4 契约 TC-202

覆盖 TC：
  正向：TC-006 single line · TC-007 auto \\n · TC-008 prev_hash chain · TC-009 no parent fsync
  负向：TC-108 line ≥ PIPE_BUF · TC-PARTIAL append partial write retry · TC-FSYNC EIO
        TC-DISK_FULL append ENOSPC · TC-IO EIO retry 2× · TC-PERMISSION EACCES
        TC-EMPTY line · TC-NEWLINE line 含 \\n
  契约：TC-202 AppendResult schema
  合计 ~14 TC。
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
    AppendResult,
    DiskFullError,
    FsyncFailed,
    IOErrorCS,
    LineTooLargeError,
)
from app.l1_09.crash_safety import (
    PermissionError as CSPermissionError,
)

# =========================================================
# §2 正向用例 · 4 TC
# =========================================================

class TestAppendAtomicPositive:
    """§3.3 append_atomic · O_APPEND + fsync · 不 fsync 父目录."""

    def test_append_single_line_tc006(self, tmp_fs: Path) -> None:
        """TC-L109-L205-006 · 单行 append · line_hash = sha256(line) · bytes_written 含 \\n."""
        target = tmp_fs / "events.jsonl"
        line = '{"seq":1,"data":"x"}'
        result = cs.append_atomic(target, line)

        assert isinstance(result, AppendResult)
        # bytes_written = len(line.encode) + 1 (for \n)
        assert result.bytes_written == len(line.encode("utf-8")) + 1
        # line_hash 是原 line（不含 \n）
        assert result.line_hash == hashlib.sha256(line.encode("utf-8")).hexdigest()
        # 首次 append · offset = 0
        assert result.offset == 0
        # ULID
        assert len(result.op_id) == 26
        # 落盘内容 = line + \n
        assert target.read_bytes() == (line + "\n").encode("utf-8")

    def test_append_newline_auto_tc007(self, tmp_fs: Path) -> None:
        """TC-L109-L205-007 · 末尾自动 \\n · 调用方 line 不带 \\n."""
        target = tmp_fs / "events.jsonl"
        cs.append_atomic(target, "abc")
        cs.append_atomic(target, "def")
        # 每行末尾 \n
        assert target.read_bytes() == b"abc\ndef\n"

    def test_append_prev_hash_chain_tc008(self, tmp_fs: Path) -> None:
        """TC-L109-L205-008 · expected_prev_hash 链接 · offset 单调递增."""
        target = tmp_fs / "e.jsonl"
        r1 = cs.append_atomic(target, '{"seq":1}')
        r2 = cs.append_atomic(target, '{"seq":2}', expected_prev_hash=r1.line_hash)
        assert r2.offset > r1.offset
        # 两条都落盘
        lines = target.read_bytes().splitlines()
        assert len(lines) == 2

    def test_append_no_parent_fsync_tc009(self, tmp_fs: Path) -> None:
        """TC-L109-L205-009 · append 不 fsync 父目录（inode 未变 · 性能优化）."""
        target = tmp_fs / "e.jsonl"
        # 首次 append · 创建文件 · 可能会有 parent 变化 → 不做断言
        cs.append_atomic(target, "line1")
        # 第二次 append · 文件已存在 · inode 不变 · 只 fsync fd 一次
        with patch(
            "app.l1_09.crash_safety.appender.os.fsync", wraps=os.fsync
        ) as spy:
            cs.append_atomic(target, "line2")
        # 恰好 1 次 fsync（fd · 不做 parent fsync）
        assert spy.call_count == 1, f"expected exactly 1 fsync (fd only), got {spy.call_count}"


# =========================================================
# §3 负向用例 · T3 逻辑错（断言）
# =========================================================

class TestAppendAtomicAssertions:
    """§3.3 输入不变量断言."""

    def test_line_too_large_tc108(self, tmp_fs: Path) -> None:
        """TC-L109-L205-108 · line + \\n ≥ PIPE_BUF(4096) · AssertionError（或 LineTooLargeError）."""
        target = tmp_fs / "e.jsonl"
        huge = "x" * 4100  # line+\n > 4096
        # 按 §3.3 输入不变量 · assert 抛（pytest AssertionError 或 LineTooLargeError 都可）
        with pytest.raises((AssertionError, LineTooLargeError)):
            cs.append_atomic(target, huge)

    def test_line_contains_newline_raises(self, tmp_fs: Path) -> None:
        """§3.3 · line 不得含 \\n（调用方用 canonical_json 保证单行）."""
        target = tmp_fs / "e.jsonl"
        with pytest.raises(AssertionError):
            cs.append_atomic(target, "a\nb")

    def test_non_str_line_raises(self, tmp_fs: Path) -> None:
        """§3.3 · line 必 str（不是 bytes）."""
        target = tmp_fs / "e.jsonl"
        with pytest.raises(AssertionError):
            cs.append_atomic(target, b"bytes")  # type: ignore[arg-type]

    def test_line_just_below_pipe_buf_passes(self, tmp_fs: Path) -> None:
        """PIPE_BUF 边界 · len(line+\\n) = 4095 必过（严格小于 PIPE_BUF_LIMIT=4096）."""
        target = tmp_fs / "e.jsonl"
        line = "x" * 4094  # +\n = 4095 < 4096 OK
        result = cs.append_atomic(target, line)
        assert result.bytes_written == 4095


class TestAppendAtomicRetries:
    """持久/瞬时 IO 错误的重试策略."""

    def test_disk_full_retries_then_raises(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """append ENOSPC · 重试 2× · 抛 DiskFullError(halt)."""

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "ENOSPC (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)

        with pytest.raises(DiskFullError) as exc:
            cs.append_atomic(tmp_fs / "e.jsonl", "line")
        assert exc.value.retries_exhausted is True
        assert exc.value.retry_count == 2
        assert exc.value.halt_required is True

    def test_io_error_retries_twice(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """append EIO · 重试 2× · 抛 IOErrorCS(halt)."""

        def fake_write(fd: int, data: bytes) -> int:
            raise OSError(errno.EIO, "EIO (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)

        with pytest.raises(IOErrorCS) as exc:
            cs.append_atomic(tmp_fs / "e.jsonl", "line")
        assert exc.value.retry_count == 2
        assert exc.value.halt_required is True

    def test_fsync_failed_no_retry(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """append fsync EIO · 首次即抛 · 0 重试（§3.6 铁律）."""

        def fake_fsync(fd: int) -> None:
            raise OSError(errno.EIO, "fsync EIO (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.fsync", fake_fsync)

        with pytest.raises(FsyncFailed) as exc:
            cs.append_atomic(tmp_fs / "e.jsonl", "line")
        assert exc.value.retry_count == 0
        assert exc.value.halt_required is True

    def test_permission_denied_no_retry(self, tmp_fs: Path) -> None:
        """chmod 555 parent · PermissionError · 不重试."""
        os.chmod(tmp_fs, 0o555)
        try:
            with pytest.raises(CSPermissionError) as exc:
                cs.append_atomic(tmp_fs / "e.jsonl", "line")
            assert exc.value.retry_count == 0
        finally:
            os.chmod(tmp_fs, 0o755)


class TestAppendAtomicBranchCoverage:
    """补齐 _map_oserror 分支覆盖（EROFS / ENOENT / EINVAL / unexpected errno）."""

    def test_readonly_fs_mapped(self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.l1_09.crash_safety import FilesystemReadOnly

        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.EROFS, "EROFS (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.open", fake_open)
        with pytest.raises(FilesystemReadOnly) as exc:
            cs.append_atomic(tmp_fs / "e.jsonl", "line")
        assert exc.value.retry_count == 0

    def test_enoent_mapped_to_path_error(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.l1_09.crash_safety import PathError

        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.ENOENT, "ENOENT (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.open", fake_open)
        with pytest.raises(PathError) as exc:
            cs.append_atomic(tmp_fs / "e.jsonl", "line")
        assert exc.value.retry_count == 0

    def test_einval_mapped_to_invalid_argument(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.l1_09.crash_safety import InvalidArgumentError

        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.EINVAL, "EINVAL (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.open", fake_open)
        with pytest.raises(InvalidArgumentError) as exc:
            cs.append_atomic(tmp_fs / "e.jsonl", "line")
        assert exc.value.retry_count == 0

    def test_unexpected_errno_mapped_to_io(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_open(*args, **kwargs) -> int:
            raise OSError(errno.EBADF, "EBADF (mocked)")

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.open", fake_open)
        with pytest.raises(IOErrorCS) as exc:
            cs.append_atomic(tmp_fs / "e.jsonl", "line")
        assert exc.value.errno == errno.EBADF

    def test_partial_write_retried_then_succeeds(
        self, tmp_fs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """partial write · 重试成功."""
        state = {"n": 0}
        original_write = os.write

        def fake_write(fd: int, data: bytes) -> int:
            state["n"] += 1
            if state["n"] == 1:
                # 首次 partial：只写一半
                return original_write(fd, data[: max(1, len(data) // 2)])
            return original_write(fd, data)

        monkeypatch.setattr("app.l1_09.crash_safety.appender.os.write", fake_write)
        target = tmp_fs / "e.jsonl"
        result = cs.append_atomic(target, "hello")
        assert result.retry_count >= 1
        assert b"hello\n" in target.read_bytes()


class TestAppendAtomicContract:
    """§4 契约 · AppendResult schema."""

    def test_append_result_schema_tc202(self, tmp_fs: Path) -> None:
        """TC-L109-L205-202 · L2-01 调 append_atomic · AppendResult 含 offset."""
        target = tmp_fs / "events.jsonl"
        result = cs.append_atomic(target, '{"seq":1}')

        assert isinstance(result.op_id, str) and len(result.op_id) == 26
        assert isinstance(result.line_hash, str) and len(result.line_hash) == 64
        assert result.bytes_written > 0
        assert result.offset == 0  # 首次
        assert result.retry_count in {0, 1, 2}

        dumped = result.model_dump()
        assert dumped["offset"] == 0
        assert dumped["line_hash"] == result.line_hash

    def test_multi_append_offset_monotonic(self, tmp_fs: Path) -> None:
        """多次 append · offset 单调递增（可能 > 期望但不回退）."""
        target = tmp_fs / "e.jsonl"
        r1 = cs.append_atomic(target, "a")
        r2 = cs.append_atomic(target, "b")
        r3 = cs.append_atomic(target, "c")
        assert r1.offset < r2.offset < r3.offset
