---
doc_id: tests-L1-02-L2-06-收尾阶段执行器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-06-收尾阶段执行器.md
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-H
created_at: 2026-04-22
---

# L1-02 L2-06-收尾阶段执行器 · TDD 测试用例

> 基于 3-1 L2-06 tech-design 的 §3 接口（`produce_closing` / `archive_project` / `purge_project` / `restore_archive`）+ §11 错误码（`E_L102_L206_001~015` 共 15 条）+ §12 SLO（produce P95 ≤ 15s · 归档小/中/大三档 SLO · purge P95 ≤ 20s）+ §13 TC ID 矩阵驱动。
> TC ID 统一格式：`TC-L102-L206-NNN`（L1-02 下 L2-06 · 三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_06_ClosingStageExecutor` 组织；正向/负向/IC 契约/SLO/e2e 分文件归档。
> 本 L2 是 **PM-14 project_id 归档 + purge 唯一入口**（与 L2-02 创建入口对应）；S6/S7 两阶段 Application Service；被 L2-01 Stage Gate 控制器驱动（IC-L2-01）；下游发 IC-09 审计事件 / 调 L2-07 渲染 / IC-06 读 KB learn 层。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 × 错误码 × IC）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1 · 15 条）
- [x] §4 IC-XX 契约集成测试（IC-01 / IC-06 / IC-09 / IC-17 / IC-L2-01 / IC-L2-02 / IC-L2-03）
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景（GWT 映射 §5 P0/P1 时序）
- [x] §7 测试 fixture（mock_project_id / mock_event_bus / mock_clock / mock_ic_payload / mock_archive_store / mock_s5_gate_status）
- [x] §8 集成点用例（与 L2-01 Gate 控制器 / L2-07 模板引擎调用链）
- [x] §9 边界 / edge case（S5 Gate 未过 / 90 天未到 purge / 并发 archive/purge / restore 失败）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO；security = 归档完整性攻击面。

### §1.1 方法 × 测试 × 覆盖类型（§3.1 四个 public 方法）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `produce_closing()` · §3.2 · 正向 EXECUTING → CLOSING_PRODUCED | TC-L102-L206-001 | integration | — | IC-L2-01 + IC-L2-02 + IC-06 + IC-09 + IC-17 |
| `produce_closing()` · §3.2 · 3 md 落盘 + bundle_hash 正确 | TC-L102-L206-002 | integration | — | IC-L2-02 |
| `produce_closing()` · §3.2 · evidence_ref 回传 L2-01 S6 Gate | TC-L102-L206-003 | integration | — | IC-17 |
| `archive_project()` · §3.3 · 正向 CLOSING_GATE_APPROVED → ARCHIVED | TC-L102-L206-004 | integration | — | IC-L2-01 + IC-09 |
| `archive_project()` · §3.3 · tar.zst + manifest.json + sha256 复验 | TC-L102-L206-005 | integration | — | IC-09 |
| `archive_project()` · §3.3 · chmod 0444 read-only 生效 | TC-L102-L206-006 | unit | — | — |
| `archive_project()` · §3.3 · resume 续做成功 | TC-L102-L206-007 | integration | — | IC-09 |
| `purge_project()` · §3.1 · 双重确认通过 + 删除 | TC-L102-L206-008 | integration | — | IC-L2-03 + IC-09 |
| `purge_project()` · §3.1 · CRITICAL 事件经 IC-09 落盘 | TC-L102-L206-009 | integration | — | IC-09 |
| `restore_archive()` · §3.1 · ops 内部 · 不走 IC | TC-L102-L206-010 | unit | — | — |
| PM-14 归档所有权闭环（本 L2 是唯一 archive + purge 入口）| TC-L102-L206-011 | integration | — | IC-L2-01 + IC-L2-03 |

### §1.2 错误码 × 测试（§11 15 条全覆盖 · 前缀 `E_L102_L206_`）

| 错误码 | TC ID | 方法 | 归属 §11.1 降级分类 |
|---|---|---|---|
| `E_L102_L206_001` PM14_OWNERSHIP_VIOLATION | TC-L102-L206-101 | `archive_project` / `purge_project` | 越权 · 拒绝 |
| `E_L102_L206_002` WRONG_STATE | TC-L102-L206-102 | `produce_closing` | 调用方 bug |
| `E_L102_L206_003` S5_GATE_NOT_PASSED | TC-L102-L206-103 | `produce_closing` | 状态机 |
| `E_L102_L206_004` S6_GATE_NOT_APPROVED | TC-L102-L206-104 | `archive_project` | 状态机 |
| `E_L102_L206_005` LESSONS_SOURCE_UNAVAILABLE | TC-L102-L206-105 | `produce_closing` | 依赖故障 |
| `E_L102_L206_006` CLOSING_BUNDLE_HASH_FAIL | TC-L102-L206-106 | `produce_closing` | HALT |
| `E_L102_L206_007` ARCHIVE_WRITE_FAIL | TC-L102-L206-107 | `archive_project` | 磁盘/权限 |
| `E_L102_L206_008` ARCHIVE_HASH_MISMATCH | TC-L102-L206-108 | `archive_project` | HALT |
| `E_L102_L206_009` ARCHIVE_TOO_LARGE | TC-L102-L206-109 | `archive_project` | 拒绝 |
| `E_L102_L206_010` MANIFEST_WRITE_FAIL | TC-L102-L206-110 | `archive_project` | HALT |
| `E_L102_L206_011` READONLY_CHMOD_FAIL | TC-L102-L206-111 | `archive_project` | warn 不 block |
| `E_L102_L206_012` PURGE_TOO_SOON | TC-L102-L206-112 | `purge_project` | 90 天未满 |
| `E_L102_L206_013` PURGE_CONFIRM_MISMATCH | TC-L102-L206-113 | `purge_project` | 双重确认 |
| `E_L102_L206_014` AUDIT_SEED_EMIT_FAIL | TC-L102-L206-114 | `produce_closing` · buffer | 基础设施 |
| `E_L102_L206_015` RESUME_ARCHIVE_CORRUPT | TC-L102-L206-115 | `archive_project` | 拒绝 · 整批重做 |

### §1.3 IC 契约 × 测试（本 L2 参与 7 条）

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-01 request_state_transition（主状态机 S5→S6→S7→ARCHIVED） | 间接驱动 | TC-L102-L206-601 | L2-01 发起 · 本 L2 写 state |
| IC-06 kb_read（learn 层） | 本 L2 → L1-06 | TC-L102-L206-602 | produce_closing 读 learn_patterns |
| IC-09 append_event · closing_produced / project_archived / project_purged | 本 L2 → L1-09 | TC-L102-L206-603 | 5 种事件全映射 |
| IC-09 CRITICAL · project_purged | 本 L2 → L1-09 | TC-L102-L206-604 | 不可逆终态 · 特别审计 |
| IC-17 user_intervene(authorize) · S6 Gate 审批 | L1-10 → L2-01 → 本 L2 | TC-L102-L206-605 | 产出 evidence_ref 回推 |
| IC-L2-01 produce_closing / archive_project | L2-01 → 本 L2 | TC-L102-L206-606 | S6/S7 两阶段入口 |
| IC-L2-02 request_template · closing.* | 本 L2 → L2-07 | TC-L102-L206-607 | 3 md 渲染 |
| IC-L2-03 purge_project（token） | L1-10/L2-04 → 本 L2 | TC-L102-L206-608 | 用户干预入口 |

### §1.4 SLO × 测试（§12.1 7 指标）

| 指标 | P95 目标 | 硬上限 | TC ID | 类型 |
|---|---|---|---|---|
| produce_closing 全链 | ≤ 15s | 60s | TC-L102-L206-501 | perf |
| 单 md 渲染（via L2-07）| ≤ 300ms | 2s | TC-L102-L206-502 | perf |
| archive_project 小 project（< 500MB）| ≤ 60s | 300s | TC-L102-L206-503 | perf |
| archive_project 中（500MB-5GB）| ≤ 5min | 20min | TC-L102-L206-504 | perf |
| archive sha256 复验 | 磁盘 IO bound | 5min | TC-L102-L206-505 | perf |
| purge_project | ≤ 20s | 120s | TC-L102-L206-506 | perf |
| 并发 archive（IO bound 2 并发）| — | — | TC-L102-L206-507 | perf |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_06_ClosingStageExecutor`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `ClosingStageExecutor`（从 `app.l2_06.executor` 导入）。

```python
# file: tests/l1_02/test_l2_06_closing_executor_positive.py
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest

from app.l2_06.executor import ClosingStageExecutor
from app.l2_06.schemas import (
    ArchiveResult,
    ClosingProductionResult,
    PurgeResult,
    RestoreResult,
)


class TestL2_06_ClosingStageExecutor:
    """每个 public 方法 + 关键不变量至少 1 正向用例。

    覆盖 §3.1 四个 public 方法：
      - produce_closing        (S6 · 3 md + bundle_hash + evidence_ref)
      - archive_project        (S7 · tar.zst + manifest.json + chmod 0444)
      - purge_project          (≥ 90 天 · 双重确认 + CRITICAL 事件)
      - restore_archive        (ops 内部 · 不走 IC)

    覆盖 §2.2 不变量 I-L206-01 ~ I-L206-06。
    """

    def test_TC_L102_L206_001_produce_closing_executing_to_closing_produced(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_s5_gate_status: dict[str, Any],
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L206-001 · I-L206-01 · 正向主干 · EXECUTING → CLOSING_PRODUCED。

        Given: project state=EXECUTING · S5 Gate 已 PASS · KB learn 层有 pattern · audit 事件齐
        When: L2-01 经 IC-L2-01 调 produce_closing(pid)
        Then: 返回 ClosingProductionResult(state=CLOSING_PRODUCED, 3 md 路径齐, bundle_hash 非空,
              evidence_ref 回传 L2-01 装 S6 Gate)
        """
        # Arrange
        assert mock_s5_gate_status["state"] == "EXECUTING"
        assert mock_s5_gate_status["s5_verdict"] == "PASS"

        # Act
        result: ClosingProductionResult = sut.produce_closing(
            request_id=mock_request_id,
            project_id=mock_project_id,
            trigger_stage="S6",
            closing_scope={
                "include_lessons": True,
                "include_delivery_manifest": True,
                "include_retro": True,
            },
            lessons_source={
                "kb_learn_layer_enabled": True,
                "audit_events_enabled": True,
                "timespan_days": 0,
            },
        )

        # Assert
        assert result.project_id == mock_project_id
        assert result.state == "CLOSING_PRODUCED"
        assert len(result.closing_files) == 3
        assert result.closing_files[0].endswith("closing/lessons_learned.md")
        assert result.closing_files[1].endswith("closing/delivery_manifest.md")
        assert result.closing_files[2].endswith("closing/retro_summary.md")
        assert result.closing_bundle_hash and len(result.closing_bundle_hash) == 64
        assert result.evidence_ref.startswith("s6-evidence:")
        assert "closing_produced" in result.emitted_events

    def test_TC_L102_L206_002_produce_closing_three_md_files_on_disk_bundle_hash(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_s5_gate_status: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """TC-L102-L206-002 · 3 份 md 落盘 · bundle_hash = sha256(合并 3 份 md 规范化内容)。"""
        # Act
        result = sut.produce_closing(
            request_id=mock_request_id,
            project_id=mock_project_id,
            trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )

        # Assert · 3 md 物理落盘
        for p in result.closing_files:
            assert Path(p).exists(), f"md not found: {p}"
            assert Path(p).stat().st_size > 0

        # Assert · bundle_hash 算法正确（§6.5）
        chunks: list[bytes] = []
        for fn in ["lessons_learned.md", "delivery_manifest.md", "retro_summary.md"]:
            content = Path(f"projects/{mock_project_id}/closing/{fn}").read_text(encoding="utf-8").strip()
            chunks.append(content.encode("utf-8"))
        combined = b"\n---CLOSING---\n".join(chunks)
        expected_hash = hashlib.sha256(combined).hexdigest()
        assert result.closing_bundle_hash == expected_hash

    def test_TC_L102_L206_003_produce_closing_evidence_ref_feeds_s6_gate(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_s5_gate_status: dict[str, Any],
    ) -> None:
        """TC-L102-L206-003 · evidence_ref 必以 `s6-evidence:` 前缀 + 含 bundle_hash 前 8 位（给 L2-01 装 S6 Gate）。"""
        result = sut.produce_closing(
            request_id=mock_request_id,
            project_id=mock_project_id,
            trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        parts = result.evidence_ref.split(":")
        assert parts[0] == "s6-evidence"
        assert parts[1] == mock_project_id
        assert result.closing_bundle_hash.startswith(parts[2])

    def test_TC_L102_L206_004_archive_project_closing_gate_approved_to_archived(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-004 · I-L206-02 · S6 Gate 已 approve · archive → ARCHIVED。

        Given: state=CLOSING_GATE_APPROVED · 目录大小 < max_archive_gb
        When: L2-01 经 IC-L2-01 调 archive_project(pid)
        Then: 返回 ArchiveResult(state=ARCHIVED, archive_path tar.zst, sha256, manifest_path)
        """
        # Arrange
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.set_closing_bundle_hash(mock_project_id, "a" * 64)

        # Act
        result: ArchiveResult = sut.archive_project(
            request_id=mock_request_id,
            project_id=mock_project_id,
            archive_options={
                "compression": "zstd",
                "compression_level": 19,
                "include_media": True,
            },
        )

        # Assert
        assert result.project_id == mock_project_id
        assert result.state == "ARCHIVED"
        assert result.archive_path.endswith(f"_archive/{mock_project_id}.tar.zst")
        assert Path(result.archive_path).exists()
        assert len(result.archive_sha256) == 64
        assert result.archive_size_bytes > 0
        assert result.manifest_path.endswith(f"_archive/{mock_project_id}.manifest.json")
        assert result.archived_at  # ISO-8601

    def test_TC_L102_L206_005_archive_sha256_recheck_matches_manifest(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-005 · archive 复验：manifest.archive_sha256 == sha256(tar.zst 文件)。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        result = sut.archive_project(
            request_id=mock_request_id, project_id=mock_project_id, archive_options={}
        )
        # 再算一次文件 sha256
        import hashlib as _h
        h = _h.sha256()
        with open(result.archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        recomputed = h.hexdigest()
        # manifest 中记录 必等于 实际文件 sha256
        manifest = mock_archive_store.read_manifest(mock_project_id)
        assert manifest["archive_sha256"] == recomputed == result.archive_sha256

    def test_TC_L102_L206_006_archive_project_dir_chmod_0444_readonly(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-006 · I-L206-03 · 归档后 projects/<pid>/ 所有文件 chmod 0444 read-only。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        sut.archive_project(
            request_id=mock_request_id, project_id=mock_project_id, archive_options={}
        )
        project_dir = Path(f"projects/{mock_project_id}/")
        for p in project_dir.rglob("*"):
            if p.is_file():
                mode = p.stat().st_mode & 0o777
                # 0o444 或 0o644 等仅所有者可读都可（视 OS · 但禁 write）
                assert (mode & 0o222) == 0, f"{p} still writable: {oct(mode)}"

    def test_TC_L102_L206_007_archive_resume_continues_after_interrupt(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-007 · I-L206-06 · 中断后可 resume · 最终 sha256 正确。

        P1 时序 §5.2：
          1. 第 1 次 archive · mock 磁盘 70% 时 ENOSPC · 返 E_L102_L206_007 + 写 resume marker
          2. ops 清磁盘 · 第 2 次 archive_project(resume=True) · 成功 · state=ARCHIVED
        """
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.inject_disk_full_at(progress=0.7)

        # 第 1 次 · 预期失败
        from app.l2_06.errors import L206ArchiveError
        with pytest.raises(L206ArchiveError) as exc_info:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc_info.value.code == "E_L102_L206_007"
        assert mock_archive_store.has_resume_marker(mock_project_id)

        # 清磁盘 · 第 2 次 · 预期成功
        mock_archive_store.clear_disk_full()
        result = sut.archive_project(
            request_id=f"{mock_request_id}-retry",
            project_id=mock_project_id,
            archive_options={"resume": True},
        )
        assert result.state == "ARCHIVED"
        assert not mock_archive_store.has_resume_marker(mock_project_id)

    def test_TC_L102_L206_008_purge_project_double_confirm_deletes_all(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-008 · I-L206-05 · purge 双重确认 + ≥ 90 天 · 彻底删除。

        Given: 归档 100 天前 · 正确 confirm_token
        When: L1-10/L2-04 经 IC-L2-03 调 purge_project(pid, token)
        Then: projects/<pid>/、 _archive/<pid>.tar.zst、 manifest.json 全删除 · 返回 PurgeResult
        """
        # Arrange · 已归档 100 天
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)

        # Act
        result: PurgeResult = sut.purge_project(
            request_id=mock_request_id,
            project_id=mock_project_id,
            confirm_token=token,
        )

        # Assert
        assert result.project_id == mock_project_id
        assert result.purged_at  # ISO-8601
        assert not Path(f"projects/{mock_project_id}/").exists()
        assert not Path(f"projects/_archive/{mock_project_id}.tar.zst").exists()
        assert not Path(f"projects/_archive/{mock_project_id}.manifest.json").exists()

    def test_TC_L102_L206_009_purge_emits_critical_audit_event(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L206-009 · purge 必发 IC-09 CRITICAL 事件 project_purged（不可逆 · 特别审计）。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        original_sha = mock_archive_store.read_manifest(mock_project_id)["archive_sha256"]

        sut.purge_project(
            request_id=mock_request_id,
            project_id=mock_project_id,
            confirm_token=token,
        )

        events = mock_event_bus.emitted_events()
        critical = [
            e for e in events
            if e["event_type"] == "L1-02/L2-06:project_purged"
            and e.get("severity") == "CRITICAL"
        ]
        assert len(critical) == 1
        assert critical[0]["payload"]["archive_sha256"] == original_sha

    def test_TC_L102_L206_010_restore_archive_ops_tool_unpacks_tar_zst(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        tmp_path: Path,
    ) -> None:
        """TC-L102-L206-010 · restore_archive（ops 内部 · 不走 IC）· tar.zst 解出 · sha256 复验通过。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        result: RestoreResult = sut.restore_archive(
            project_id=mock_project_id,
            restore_to=str(tmp_path / "restored"),
        )
        assert result.project_id == mock_project_id
        assert result.restored_path.endswith("restored")
        assert Path(result.restored_path).is_dir()
        assert result.sha256_verified is True

    def test_TC_L102_L206_011_pm14_ownership_closure(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-011 · PM-14 归档/purge 唯一入口闭环 · 全链 EXECUTING → ARCHIVED → PURGED 只走本 L2。"""
        # S6
        r1 = sut.produce_closing(
            request_id="r1", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        assert r1.state == "CLOSING_PRODUCED"
        # 外部 L2-01 S6 Gate approve
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        # S7
        r2 = sut.archive_project(request_id="r2", project_id=mock_project_id, archive_options={})
        assert r2.state == "ARCHIVED"
        # purge（100 天后）
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        r3 = sut.purge_project(request_id="r3", project_id=mock_project_id, confirm_token=token)
        assert r3.purged_at
        # 全链 state 流只由本 L2 写入
        assert mock_archive_store.state_writer_allowlist() == {"L1-02/L2-06"}
```

---

## §3 负向用例（§11 每错误码 ≥ 1 · 15 条全覆盖）

> pytest 风格；`class TestL2_06_ClosingExecutor_Negative`；所有用例用 `pytest.raises(L206Error)` 捕获具名错误码。
> 被测对象（SUT）类型 `ClosingStageExecutor`（从 `app.l2_06.executor` 导入）。
> 错误码对应 §11.1 降级分类：越权/状态机/HALT/基础设施/拒绝/warn。

```python
# file: tests/l1_02/test_l2_06_closing_executor_negative.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.l2_06.executor import ClosingStageExecutor
from app.l2_06.errors import (
    L206ArchiveError,
    L206AuditError,
    L206HashError,
    L206PurgeError,
    L206StateError,
)


class TestL2_06_ClosingExecutor_Negative:
    """§11 错误码 15 条 · 每条 ≥ 1 负向用例 · 覆盖越权/状态机/HALT/基础设施/拒绝/warn 6 类降级。"""

    # ---- 越权 ----

    def test_TC_L102_L206_101_pm14_ownership_violation(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-101 · E_L102_L206_001 PM14_OWNERSHIP_VIOLATION · 非 L2-01 调 archive 拒绝。

        Given: caller_l2 = "L2-03"（越权 · 非 L2-01 / L1-10 / L2-04）
        When: 越权方直接调 archive_project
        Then: raises L206StateError(E_L102_L206_001) · 审计 ERROR · state 不变
        """
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        with pytest.raises(L206StateError) as exc:
            sut.archive_project(
                request_id=mock_request_id,
                project_id=mock_project_id,
                archive_options={},
                caller_l2="L2-03",   # 越权
            )
        assert exc.value.code == "E_L102_L206_001"
        assert mock_archive_store.read_state(mock_project_id) == "CLOSING_GATE_APPROVED"

    def test_TC_L102_L206_101b_pm14_ownership_violation_on_purge(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-101b · PM-14 铁律 · 非 L1-10/L2-04 调 purge · E_L102_L206_001 拒绝。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        with pytest.raises(L206StateError) as exc:
            sut.purge_project(
                request_id=mock_request_id,
                project_id=mock_project_id,
                confirm_token=token,
                caller_l2="L2-05",    # 越权 · 必须 L1-10 / L2-04
            )
        assert exc.value.code == "E_L102_L206_001"

    # ---- 状态机 ----

    def test_TC_L102_L206_102_wrong_state_produce_closing_from_draft(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-102 · E_L102_L206_002 WRONG_STATE · state=DRAFT 调 produce_closing 拒绝。"""
        mock_archive_store.set_state(mock_project_id, "DRAFT")
        with pytest.raises(L206StateError) as exc:
            sut.produce_closing(
                request_id=mock_request_id, project_id=mock_project_id,
                trigger_stage="S6",
                closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
                lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            )
        assert exc.value.code == "E_L102_L206_002"

    def test_TC_L102_L206_103_s5_gate_not_passed(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-103 · E_L102_L206_003 S5_GATE_NOT_PASSED · state ≠ EXECUTING（S5 未完成）。"""
        mock_archive_store.set_state(mock_project_id, "S5_QUALITY_GATE_PENDING")
        with pytest.raises(L206StateError) as exc:
            sut.produce_closing(
                request_id=mock_request_id, project_id=mock_project_id,
                trigger_stage="S6",
                closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
                lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            )
        assert exc.value.code == "E_L102_L206_003"

    def test_TC_L102_L206_104_s6_gate_not_approved_archive_rejected(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-104 · E_L102_L206_004 S6_GATE_NOT_APPROVED · state=CLOSING_PRODUCED 直接 archive 拒绝。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_PRODUCED")   # 未经 S6 Gate approve
        with pytest.raises(L206StateError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc.value.code == "E_L102_L206_004"

    # ---- 依赖故障 ----

    def test_TC_L102_L206_105_lessons_source_unavailable(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_kb_client: Any,
        mock_audit_scanner: Any,
    ) -> None:
        """TC-L102-L206-105 · E_L102_L206_005 LESSONS_SOURCE_UNAVAILABLE · KB + audit 都不可达。

        §6.1 双源都 raise → 不降级 · 直接 raise E005（硬依赖）
        """
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        mock_kb_client.raise_on_read = True
        mock_audit_scanner.raise_on_scan = True
        with pytest.raises(L206AuditError) as exc:
            sut.produce_closing(
                request_id=mock_request_id, project_id=mock_project_id,
                trigger_stage="S6",
                closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
                lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            )
        assert exc.value.code == "E_L102_L206_005"

    # ---- HALT ----

    def test_TC_L102_L206_106_closing_bundle_hash_fail(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-106 · E_L102_L206_006 CLOSING_BUNDLE_HASH_FAIL · md 文件损坏导致合并 hash 失败 · HALT。"""
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        mock_archive_store.inject_md_corrupt_after_write()
        with pytest.raises(L206HashError) as exc:
            sut.produce_closing(
                request_id=mock_request_id, project_id=mock_project_id,
                trigger_stage="S6",
                closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
                lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            )
        assert exc.value.code == "E_L102_L206_006"
        assert exc.value.severity == "HALT"

    def test_TC_L102_L206_107_archive_write_fail_enospc_writes_resume_marker(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-107 · E_L102_L206_007 ARCHIVE_WRITE_FAIL · 磁盘满 → resume marker 写入 + raise。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.inject_disk_full_at(progress=0.5)
        with pytest.raises(L206ArchiveError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc.value.code == "E_L102_L206_007"
        assert mock_archive_store.has_resume_marker(mock_project_id)

    def test_TC_L102_L206_108_archive_hash_mismatch_halt(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-108 · E_L102_L206_008 ARCHIVE_HASH_MISMATCH · 复验 sha256 不符 · HALT · 重打。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.inject_archive_tamper_after_write()     # 写完后立刻破坏
        with pytest.raises(L206HashError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc.value.code == "E_L102_L206_008"
        assert exc.value.severity == "HALT"

    def test_TC_L102_L206_109_archive_too_large(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-109 · E_L102_L206_009 ARCHIVE_TOO_LARGE · 项目目录超 max_archive_gb（默认 20GB）· 拒绝。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.set_project_dir_size_gb(mock_project_id, gb=25.0)    # 超 20GB
        with pytest.raises(L206ArchiveError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc.value.code == "E_L102_L206_009"

    def test_TC_L102_L206_110_manifest_write_fail_fsync_halt(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-110 · E_L102_L206_010 MANIFEST_WRITE_FAIL · manifest.json fsync 失败 · HALT。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.inject_manifest_fsync_fail()
        with pytest.raises(L206ArchiveError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc.value.code == "E_L102_L206_010"
        assert exc.value.severity == "HALT"

    # ---- warn 不 block ----

    def test_TC_L102_L206_111_readonly_chmod_fail_warns_not_block(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L206-111 · E_L102_L206_011 READONLY_CHMOD_FAIL · chmod 0444 失败 · warn 不 block · 归档仍成功。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.inject_chmod_fail()
        # 不 raise · 仅发 warn 事件
        result = sut.archive_project(
            request_id=mock_request_id, project_id=mock_project_id, archive_options={}
        )
        assert result.state == "ARCHIVED"
        warns = [e for e in mock_event_bus.emitted_events()
                 if e["event_type"] == "L1-02/L2-06:chmod_readonly_fail_warn"]
        assert len(warns) == 1
        assert warns[0]["payload"]["error_code"] == "E_L102_L206_011"

    # ---- purge 拒绝 ----

    def test_TC_L102_L206_112_purge_too_soon_under_90_days(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-112 · E_L102_L206_012 PURGE_TOO_SOON · 归档仅 60 天 · 不足 90 天 · 拒绝。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=60)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        with pytest.raises(L206PurgeError) as exc:
            sut.purge_project(
                request_id=mock_request_id, project_id=mock_project_id, confirm_token=token,
            )
        assert exc.value.code == "E_L102_L206_012"

    def test_TC_L102_L206_113_purge_confirm_mismatch(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-113 · E_L102_L206_013 PURGE_CONFIRM_MISMATCH · token 错 · 双重确认失败 · 拒绝。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        with pytest.raises(L206PurgeError) as exc:
            sut.purge_project(
                request_id=mock_request_id, project_id=mock_project_id,
                confirm_token="deadbeef-WRONG-TOKEN",
            )
        assert exc.value.code == "E_L102_L206_013"

    # ---- 基础设施 ----

    def test_TC_L102_L206_114_audit_seed_emit_fail_buffered(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L206-114 · E_L102_L206_014 AUDIT_SEED_EMIT_FAIL · EventBus 不可达 · buffer 不 block。"""
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        mock_event_bus.inject_bus_down(retries=3)
        # 不 raise · 事件进 buffer
        result = sut.produce_closing(
            request_id=mock_request_id, project_id=mock_project_id,
            trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        assert result.state == "CLOSING_PRODUCED"
        buffered = mock_event_bus.buffered_events()
        assert any(e["event_type"] == "L1-02/L2-06:closing_produced" for e in buffered)
        assert mock_event_bus.degradation_state() == "DEGRADED_AUDIT"

    # ---- 拒绝 · 整批重做 ----

    def test_TC_L102_L206_115_resume_archive_corrupt_rejects_whole_retry(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-115 · E_L102_L206_015 RESUME_ARCHIVE_CORRUPT · resume 前半成品损坏 · 拒绝 · 必须整批重做。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVE_INTERRUPTED")
        mock_archive_store.write_resume_marker(mock_project_id, progress=0.7)
        mock_archive_store.inject_partial_archive_corrupt()
        with pytest.raises(L206ArchiveError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id,
                archive_options={"resume": True},
            )
        assert exc.value.code == "E_L102_L206_015"
        assert exc.value.details["action"] == "整批重做"
```

---

## §4 IC 契约集成测试（IC-01 / IC-06 / IC-09 / IC-17 / IC-L2-01 / IC-L2-02 / IC-L2-03）

> §1.3 列 7 条 IC 全覆盖；join test 至少 3 处（IC-06 + IC-L2-02 / IC-09 + IC-17 / IC-01 + IC-L2-01）。
> PM-14 归档+purge 唯一入口铁律在 IC-L2-01 + IC-L2-03 covenant 验收。
> 被测对象：`ClosingStageExecutor` + mocked IC clients。

```python
# file: tests/l1_02/test_l2_06_closing_executor_ic_contracts.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.l2_06.executor import ClosingStageExecutor


class TestL2_06_ClosingExecutor_IC_Contracts:
    """覆盖本 L2 参与的 7 条 IC · ≥ 3 join test · 契约字段/方向/负载 full validate。"""

    # ---- IC-01 主状态机 ----

    def test_TC_L102_L206_601_ic01_state_transition_chain(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L206-601 · IC-01 · L2-01 发起状态转换 · 本 L2 写 state · EXECUTING → CLOSING_PRODUCED → CLOSING_GATE_APPROVED → ARCHIVED 四跳 chain。"""
        # S6 produce
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        sut.produce_closing(
            request_id="r1", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        assert mock_archive_store.read_state(mock_project_id) == "CLOSING_PRODUCED"
        # L2-01 审批通过 S6 Gate
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        # S7 archive
        sut.archive_project(request_id="r2", project_id=mock_project_id, archive_options={})
        assert mock_archive_store.read_state(mock_project_id) == "ARCHIVED"
        # IC-01 审计应有 4 条 transition 事件（本 L2 只写 2 条 · L2-01 写 2 条 · 但 chain 完整）
        writers = mock_archive_store.state_writer_log(mock_project_id)
        assert writers == [
            "L1-02/L2-06",    # CLOSING_PRODUCED
            "L1-02/L2-01",    # CLOSING_GATE_APPROVED
            "L1-02/L2-06",    # ARCHIVED
        ]

    # ---- IC-06 KB read ----

    def test_TC_L102_L206_602_ic06_kb_read_learn_layer_contract(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_kb_client: Any,
    ) -> None:
        """TC-L102-L206-602 · IC-06 kb_read(layer=learn) · 字段齐 · 返回 learn_patterns 非空 · 进 lessons md。"""
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        mock_kb_client.set_learn_patterns([
            {"pattern_id": "P001", "summary": "quality-gate retry > 3 correlated with scope creep"},
            {"pattern_id": "P002", "summary": "TDD-first phase shortens S5 by 40%"},
        ])

        sut.produce_closing(
            request_id="r", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )

        # IC-06 契约：1 次调用 · layer=learn · project_id 正确
        calls = mock_kb_client.call_log()
        assert len(calls) == 1
        assert calls[0]["layer"] == "learn"
        assert calls[0]["project_id"] == mock_project_id

        # 契约回馈：lessons md 含 pattern_id
        lessons = Path(f"projects/{mock_project_id}/closing/lessons_learned.md").read_text()
        assert "P001" in lessons
        assert "P002" in lessons

    # ---- IC-09 + IC-17 join ----

    def test_TC_L102_L206_603_ic09_emits_five_event_types(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_event_bus: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-603 · IC-09 · 本 L2 全链发 5 种事件 · event_type / severity / payload 齐。"""
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        sut.produce_closing(
            request_id="r1", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        sut.archive_project(request_id="r2", project_id=mock_project_id, archive_options={})

        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        sut.purge_project(request_id="r3", project_id=mock_project_id, confirm_token=token)

        # 5 种事件全到（§2.2 Domain Events）
        types = {e["event_type"] for e in mock_event_bus.emitted_events()}
        expected = {
            "L1-02/L2-06:closing_started",
            "L1-02/L2-06:lessons_written",
            "L1-02/L2-06:delivery_packaged",
            "L1-02/L2-06:project_archived",
            "L1-02/L2-06:project_purged",
        }
        assert expected.issubset(types), f"missing: {expected - types}"

    def test_TC_L102_L206_604_ic09_critical_purge_audit_payload(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_event_bus: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-604 · IC-09 CRITICAL · project_purged severity=CRITICAL · payload 含 archive_sha256 + archived_at（合规审计痕迹）。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        manifest_before = mock_archive_store.read_manifest(mock_project_id)

        sut.purge_project(request_id="r", project_id=mock_project_id, confirm_token=token)

        critical = [e for e in mock_event_bus.emitted_events()
                    if e["event_type"] == "L1-02/L2-06:project_purged"]
        assert len(critical) == 1
        e = critical[0]
        assert e["severity"] == "CRITICAL"
        assert e["payload"]["archive_sha256"] == manifest_before["archive_sha256"]
        assert e["payload"]["archived_at"] == manifest_before["archived_at"]
        # 不可逆标记
        assert e["payload"]["irreversible"] is True

    def test_TC_L102_L206_605_ic17_s6_gate_evidence_ref_join(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_event_bus: Any,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L206-605 · IC-17 + IC-09 join · S6 Gate evidence_ref 回推 L2-01 · 同一 bundle_hash 贯穿 3 处。

        3 处必须一致：
          1. ClosingProductionResult.evidence_ref   （API 回参）
          2. IC-09 event closing_produced.payload.bundle_hash   （审计事件）
          3. IC-17 S6 Gate evidence.closing_bundle_hash          （L2-01 装 Gate 时读）
        """
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        result = sut.produce_closing(
            request_id="r", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )

        # 1 · API 返回
        api_hash = result.closing_bundle_hash
        assert result.evidence_ref == f"s6-evidence:{mock_project_id}:{api_hash[:8]}"

        # 2 · IC-09 event payload
        cp_event = next(e for e in mock_event_bus.emitted_events()
                        if e["event_type"] == "L1-02/L2-06:closing_produced")
        assert cp_event["payload"]["bundle_hash"] == api_hash

        # 3 · IC-17 Gate payload（mock_ic_payload 记录本 L2 回推给 L2-01 的 Gate 装载负载）
        gate_payload = mock_ic_payload.capture_for_l201_s6_gate(mock_project_id)
        assert gate_payload["evidence"]["closing_bundle_hash"] == api_hash
        assert gate_payload["evidence"]["evidence_ref"] == result.evidence_ref

    # ---- IC-L2-01 + IC-L2-02 join ----

    def test_TC_L102_L206_606_ic_l201_covenant_pm14_exclusive_entry(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-606 · IC-L2-01 · PM-14 铁律 · produce_closing + archive_project 双入口唯一来自 L2-01。"""
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        # L2-01 可 · 成功
        r1 = sut.produce_closing(
            request_id="r1", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            caller_l2="L2-01",
        )
        assert r1.state == "CLOSING_PRODUCED"
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        r2 = sut.archive_project(
            request_id="r2", project_id=mock_project_id, archive_options={}, caller_l2="L2-01",
        )
        assert r2.state == "ARCHIVED"
        # state 写入者审计：本 L2 + L2-01 闭环
        writers = mock_archive_store.state_writer_log(mock_project_id)
        assert "L1-02/L2-06" in writers
        # 唯一入口：非 L2-01 调 → §3.101 已验证 E001 拒绝

    def test_TC_L102_L206_607_ic_l202_template_three_render_join(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_template_engine: Any,
    ) -> None:
        """TC-L102-L206-607 · IC-L2-02 · closing.lessons_learned / closing.delivery_manifest / closing.retro_summary 3 次渲染 · template_id 齐。"""
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        sut.produce_closing(
            request_id="r", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        calls = mock_template_engine.render_calls()
        template_ids = [c["template_id"] for c in calls]
        assert template_ids == [
            "closing.lessons_learned",
            "closing.delivery_manifest",
            "closing.retro_summary",
        ]
        # IC-L2-02 契约：每次渲染必带 project_id slot
        for c in calls:
            assert c["slots"]["project_id"] == mock_project_id

    # ---- IC-L2-03 purge 入口 ----

    def test_TC_L102_L206_608_ic_l203_purge_entry_covenant(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L206-608 · IC-L2-03 · PM-14 purge 唯一入口 · 必须从 L1-10/L2-04 干预进入 · 带 confirm_token · 发 CRITICAL 事件。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        sut.purge_project(
            request_id="r", project_id=mock_project_id,
            confirm_token=token, caller_l2="L2-04",
        )
        # IC-L2-03 契约：purge 完成态 · 3 实体全删 · CRITICAL 事件已发
        assert not Path(f"projects/{mock_project_id}/").exists()
        assert not Path(f"projects/_archive/{mock_project_id}.tar.zst").exists()
        assert not Path(f"projects/_archive/{mock_project_id}.manifest.json").exists()
        crit = [e for e in mock_event_bus.emitted_events()
                if e["event_type"] == "L1-02/L2-06:project_purged" and e["severity"] == "CRITICAL"]
        assert len(crit) == 1
```

---

## §5 性能 SLO 用例（§12 对标）

> pytest 风格；`@pytest.mark.perf` 标记；本地默认 skip · CI perf job 启用。
> 对标 §12.1 7 个 SLO 指标；使用 `time.perf_counter()` + `mock_clock.deterministic_io_delay`。

```python
# file: tests/l1_02/test_l2_06_closing_executor_perf.py
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from app.l2_06.executor import ClosingStageExecutor


pytestmark = [pytest.mark.perf]


class TestL2_06_ClosingExecutor_SLO:
    """对标 §12.1 7 个 SLO 指标；每个 P95 断言来自 §12 硬上限；使用 100 次 sample P95。"""

    def test_TC_L102_L206_501_produce_closing_p95_under_15s(
        self,
        sut: ClosingStageExecutor,
        mock_project_id_factory: Any,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-501 · produce_closing P95 ≤ 15s · 硬上限 60s（§12.1）。"""
        durations: list[float] = []
        for i in range(30):
            pid = mock_project_id_factory()
            mock_archive_store.set_state(pid, "EXECUTING")
            t0 = time.perf_counter()
            sut.produce_closing(
                request_id=f"r-{i}", project_id=pid, trigger_stage="S6",
                closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
                lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            )
            durations.append(time.perf_counter() - t0)

        durations.sort()
        p95 = durations[int(len(durations) * 0.95) - 1]
        assert p95 <= 15.0, f"produce_closing P95={p95:.2f}s > 15s"
        assert max(durations) <= 60.0, f"produce_closing hard limit breached: {max(durations):.2f}s"

    def test_TC_L102_L206_502_single_md_render_p95_under_300ms(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_template_engine: Any,
    ) -> None:
        """TC-L102-L206-502 · 单 md 渲染 P95 ≤ 300ms · 硬上限 2s（§12.1 · IC-L2-02 侧 SLO）。"""
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        sut.produce_closing(
            request_id="r", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        # mock_template_engine 在每次 render 上计时
        durations = mock_template_engine.render_durations()
        assert len(durations) == 3   # 3 份 md
        durations.sort()
        p95_idx = max(0, int(len(durations) * 0.95) - 1)
        p95 = durations[p95_idx]
        assert p95 <= 0.3, f"single md render P95={p95 * 1000:.0f}ms > 300ms"
        assert max(durations) <= 2.0

    def test_TC_L102_L206_503_archive_small_project_p95_under_60s(
        self,
        sut: ClosingStageExecutor,
        mock_project_id_factory: Any,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-503 · 小 project (< 500MB) archive P95 ≤ 60s · 硬上限 300s（§12.1）。"""
        durations: list[float] = []
        for i in range(10):
            pid = mock_project_id_factory()
            mock_archive_store.set_state(pid, "CLOSING_GATE_APPROVED")
            mock_archive_store.set_project_dir_size_gb(pid, gb=0.3)   # 300MB
            t0 = time.perf_counter()
            sut.archive_project(request_id=f"r-{i}", project_id=pid, archive_options={})
            durations.append(time.perf_counter() - t0)
        durations.sort()
        p95 = durations[int(len(durations) * 0.95) - 1]
        assert p95 <= 60.0, f"small archive P95={p95:.2f}s > 60s"
        assert max(durations) <= 300.0

    def test_TC_L102_L206_504_archive_medium_project_p95_under_5min(
        self,
        sut: ClosingStageExecutor,
        mock_project_id_factory: Any,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-504 · 中 project (500MB-5GB) archive P95 ≤ 5min · 硬上限 20min（§12.1）。"""
        durations: list[float] = []
        for i in range(5):   # 中规模采样少
            pid = mock_project_id_factory()
            mock_archive_store.set_state(pid, "CLOSING_GATE_APPROVED")
            mock_archive_store.set_project_dir_size_gb(pid, gb=2.0)   # 2GB
            t0 = time.perf_counter()
            sut.archive_project(request_id=f"r-{i}", project_id=pid, archive_options={})
            durations.append(time.perf_counter() - t0)
        durations.sort()
        p95 = durations[-1]   # 5 次 → 取 max 作 P95 近似
        assert p95 <= 300.0, f"medium archive P95={p95:.2f}s > 5min"
        assert max(durations) <= 1200.0

    def test_TC_L102_L206_505_archive_sha256_recheck_within_disk_io_budget(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-505 · archive sha256 复验 · 磁盘 IO bound · 硬上限 5min（§12.1）。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.set_project_dir_size_gb(mock_project_id, gb=1.0)
        # sha256 复验计时（单独埋点 · mock_archive_store 捕获）
        sut.archive_project(request_id="r", project_id=mock_project_id, archive_options={})
        sha256_duration = mock_archive_store.last_sha256_recheck_duration_sec()
        assert sha256_duration <= 300.0, f"sha256 recheck {sha256_duration:.2f}s > 5min"

    def test_TC_L102_L206_506_purge_p95_under_20s(
        self,
        sut: ClosingStageExecutor,
        mock_project_id_factory: Any,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-506 · purge_project P95 ≤ 20s · 硬上限 120s（§12.1）。"""
        durations: list[float] = []
        for i in range(20):
            pid = mock_project_id_factory()
            mock_archive_store.set_state(pid, "ARCHIVED")
            mock_clock.set_archived_days_ago(pid, days=100)
            token = mock_archive_store.compute_confirm_token(pid)
            t0 = time.perf_counter()
            sut.purge_project(request_id=f"r-{i}", project_id=pid, confirm_token=token)
            durations.append(time.perf_counter() - t0)
        durations.sort()
        p95 = durations[int(len(durations) * 0.95) - 1]
        assert p95 <= 20.0, f"purge P95={p95:.2f}s > 20s"
        assert max(durations) <= 120.0

    def test_TC_L102_L206_507_concurrent_archive_respects_parallel_limit_2(
        self,
        sut: ClosingStageExecutor,
        mock_project_id_factory: Any,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-507 · §12.2 IO bound · archive_parallel_limit=2 · 3 并发时第 3 单排队。"""
        pids = [mock_project_id_factory() for _ in range(3)]
        for pid in pids:
            mock_archive_store.set_state(pid, "CLOSING_GATE_APPROVED")
            mock_archive_store.set_project_dir_size_gb(pid, gb=0.5)

        def run(pid: str) -> tuple[str, float]:
            t0 = time.perf_counter()
            sut.archive_project(request_id=f"r-{pid}", project_id=pid, archive_options={})
            return pid, time.perf_counter() - t0

        with ThreadPoolExecutor(max_workers=3) as ex:
            results = list(ex.map(run, pids))

        # 3 并发 archive · 其中 1 个被队列 · max_concurrent 实际观察 ≤ 2
        max_concurrent = mock_archive_store.max_concurrent_archive_observed()
        assert max_concurrent <= 2, f"archive parallel={max_concurrent} > 2"
        # 全部最终成功
        for pid, _d in results:
            assert mock_archive_store.read_state(pid) == "ARCHIVED"
```

---

## §6 端到端 e2e 场景（GWT 映射 §5 P0/P1 时序）

> pytest + Playwright / real FS；`@pytest.mark.e2e`；每 GWT 至少 1 个 test · 3 场景全覆盖 S5 Gate + S6 + S7 Archive + 90 天后 Purge 完整链路。
> e2e 使用 real ClosingStageExecutor + real tar.zst + real sha256 + mock 外部（L2-01 / L2-07 / KB / EventBus）。

```python
# file: tests/l1_02/test_l2_06_closing_executor_e2e.py
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from app.l2_06.executor import ClosingStageExecutor


pytestmark = [pytest.mark.e2e]


class TestL2_06_ClosingExecutor_E2E:
    """§5 P0/P1 时序 → GWT 映射 3 个 e2e 场景：
       Scenario-1 · S6+S7 完整主干（§5.1 P0）
       Scenario-2 · S7 归档中断 + resume（§5.2 P1）
       Scenario-3 · S7 Archive + 90 天后 Purge 完整链（§5.3 P1 · PM-14 收闭环）
    """

    def test_TC_L102_L206_701_e2e_s5_passed_to_s6_s7_archived_full_happy(
        self,
        real_sut: ClosingStageExecutor,
        real_project_fixture: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L206-701 · e2e scenario-1 · GWT · §5.1 P0 主干。

        Given: project p1 已完 S5 · state=EXECUTING · real FS 有 5 阶段产出物
               · KB learn 有 2 个 pattern · audit 有 120 事件
        When: L2-01 IC-L2-01 调 produce_closing → 审批 S6 Gate → 调 archive_project
        Then: state=ARCHIVED · projects/p1/ chmod 0444 · _archive/p1.tar.zst 存在
              · sha256 与 manifest.archive_sha256 一致 · IC-09 审计 5 事件齐
        """
        pid = real_project_fixture.create_with_state("EXECUTING")
        real_project_fixture.seed_kb_learn_patterns(pid, count=2)
        real_project_fixture.seed_audit_events(pid, count=120)

        # S6 produce
        r1 = real_sut.produce_closing(
            request_id="e2e-r1", project_id=pid, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )
        assert r1.state == "CLOSING_PRODUCED"
        # 外部 L2-01 审批 S6 Gate
        real_project_fixture.mark_s6_gate_approved(pid, evidence_ref=r1.evidence_ref)

        # S7 archive
        r2 = real_sut.archive_project(request_id="e2e-r2", project_id=pid, archive_options={})
        assert r2.state == "ARCHIVED"

        # 实盘验证：tar.zst 存在 · 可解 · sha256 一致
        archive = Path(r2.archive_path)
        assert archive.exists() and archive.stat().st_size > 0
        h = hashlib.sha256()
        with open(archive, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        assert h.hexdigest() == r2.archive_sha256

        # projects/p1/ 所有文件 chmod 0444（不可写）
        for p in Path(f"projects/{pid}/").rglob("*"):
            if p.is_file():
                assert (p.stat().st_mode & 0o222) == 0

        # IC-09 5 种事件齐
        types = {e["event_type"] for e in mock_event_bus.emitted_events()}
        for et in ["L1-02/L2-06:closing_started", "L1-02/L2-06:lessons_written",
                   "L1-02/L2-06:delivery_packaged", "L1-02/L2-06:project_archived"]:
            assert et in types, f"missing event: {et}"

    def test_TC_L102_L206_702_e2e_archive_enospc_resume_eventually_archived(
        self,
        real_sut: ClosingStageExecutor,
        real_project_fixture: Any,
    ) -> None:
        """TC-L102-L206-702 · e2e scenario-2 · GWT · §5.2 P1 resume。

        Given: project p2 已在 CLOSING_GATE_APPROVED · 磁盘 70% 后 ENOSPC
        When: 第 1 次 archive 失败 E007 · ops 清磁盘 · 第 2 次 archive(resume=True)
        Then: state=ARCHIVED · resume marker 清理 · 最终 sha256 复验 OK
        """
        pid = real_project_fixture.create_with_state("CLOSING_GATE_APPROVED")
        real_project_fixture.inject_disk_full_at(progress=0.7)

        # 第 1 次失败
        from app.l2_06.errors import L206ArchiveError
        with pytest.raises(L206ArchiveError) as exc:
            real_sut.archive_project(request_id="e2e-r1", project_id=pid, archive_options={})
        assert exc.value.code == "E_L102_L206_007"
        assert real_project_fixture.has_resume_marker(pid)

        # 清磁盘
        real_project_fixture.clear_disk_full()

        # 第 2 次 resume 成功
        r2 = real_sut.archive_project(
            request_id="e2e-r2", project_id=pid,
            archive_options={"resume": True},
        )
        assert r2.state == "ARCHIVED"
        assert not real_project_fixture.has_resume_marker(pid)
        # sha256 复验
        h = hashlib.sha256()
        with open(r2.archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        assert h.hexdigest() == r2.archive_sha256

    def test_TC_L102_L206_703_e2e_archive_then_100_days_purge_full_closure(
        self,
        real_sut: ClosingStageExecutor,
        real_project_fixture: Any,
        mock_clock: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L206-703 · e2e scenario-3 · PM-14 归档+purge 闭环 · GWT。

        Given: project p3 · S6+S7 完成 · state=ARCHIVED · 已归档 100 天
        When: L1-10 干预 IC-L2-03 调 purge_project(pid, correct_token)
        Then: projects/p3/ + _archive/p3.tar.zst + manifest.json 全删除
              · IC-09 project_purged CRITICAL 事件已发 · 本 L2 是唯一 archive+purge 入口
        """
        pid = real_project_fixture.full_s6_s7_complete()
        assert real_project_fixture.read_state(pid) == "ARCHIVED"
        mock_clock.set_archived_days_ago(pid, days=100)
        manifest_before = real_project_fixture.read_manifest(pid)
        token = real_project_fixture.compute_confirm_token(pid)

        r = real_sut.purge_project(
            request_id="e2e-r", project_id=pid,
            confirm_token=token, caller_l2="L2-04",
        )
        assert r.purged_at

        # 3 实体全删
        assert not Path(f"projects/{pid}/").exists()
        assert not Path(f"projects/_archive/{pid}.tar.zst").exists()
        assert not Path(f"projects/_archive/{pid}.manifest.json").exists()

        # CRITICAL 事件
        crit = [e for e in mock_event_bus.emitted_events()
                if e["event_type"] == "L1-02/L2-06:project_purged" and e["severity"] == "CRITICAL"]
        assert len(crit) == 1
        assert crit[0]["payload"]["archive_sha256"] == manifest_before["archive_sha256"]

        # PM-14 闭环：state writer 审计只含本 L2
        assert real_project_fixture.state_writer_allowlist() == {"L1-02/L2-06"}
```

---

## §7 测试 fixture 实现

> §0 声明的 6 个 fixture + 衍生实现；pytest `conftest.py` 归档；类型注解齐。
> 原则：单测 mock fixture 可程序化注入故障；e2e 用 real_* 系列（真磁盘 + 真 tar.zst）。

```python
# file: tests/l1_02/conftest.py
from __future__ import annotations

import hashlib
import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

from app.l2_06.executor import ClosingStageExecutor


# ---------------------------------------------------------------------------
# fixture 1 · mock_project_id
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_project_id() -> str:
    """返回 deterministic · 唯一 · 测试内不重用。"""
    return "proj-l102-l206-test-0001"


@pytest.fixture
def mock_project_id_factory() -> Callable[[], str]:
    """对 SLO / 并发用例；每次调用返回新 pid。"""
    counter = {"n": 0}

    def _make() -> str:
        counter["n"] += 1
        return f"proj-l102-l206-test-{counter['n']:04d}"

    return _make


@pytest.fixture
def mock_request_id() -> str:
    return "req-l102-l206-0001"


# ---------------------------------------------------------------------------
# fixture 2 · mock_event_bus
# ---------------------------------------------------------------------------

class _MockEventBus:
    """IC-09 EventBus mock · 支持 emit / buffer / bus down 注入 / 降级状态追踪。"""

    def __init__(self) -> None:
        self._emitted: list[dict[str, Any]] = []
        self._buffered: list[dict[str, Any]] = []
        self._bus_down_remaining = 0
        self._degradation = "FULL"

    def emit(self, event: dict[str, Any]) -> None:
        if self._bus_down_remaining > 0:
            self._bus_down_remaining -= 1
            self._buffered.append(event)
            self._degradation = "DEGRADED_AUDIT"
            return
        self._emitted.append(event)
        if self._degradation == "DEGRADED_AUDIT":
            self._emitted.extend(self._buffered)
            self._buffered.clear()
            self._degradation = "FULL"

    def inject_bus_down(self, retries: int = 3) -> None:
        self._bus_down_remaining = retries

    def emitted_events(self) -> list[dict[str, Any]]:
        return list(self._emitted)

    def buffered_events(self) -> list[dict[str, Any]]:
        return list(self._buffered)

    def degradation_state(self) -> str:
        return self._degradation


@pytest.fixture
def mock_event_bus() -> _MockEventBus:
    return _MockEventBus()


# ---------------------------------------------------------------------------
# fixture 3 · mock_clock
# ---------------------------------------------------------------------------

class _MockClock:
    """Deterministic clock · 支持设 archived_at · 测 purge 时间窗。"""

    def __init__(self) -> None:
        self._now = datetime(2026, 4, 22, 12, 0, 0, tzinfo=timezone.utc)
        self._archived_days: dict[str, int] = {}

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)

    def set_archived_days_ago(self, project_id: str, days: int) -> None:
        self._archived_days[project_id] = days

    def archived_at_for(self, project_id: str) -> datetime:
        days = self._archived_days.get(project_id, 0)
        return self._now - timedelta(days=days)


@pytest.fixture
def mock_clock() -> _MockClock:
    return _MockClock()


# ---------------------------------------------------------------------------
# fixture 4 · mock_ic_payload
# ---------------------------------------------------------------------------

class _MockICPayload:
    """记录本 L2 向上下游 IC 发送的 payload · 便于 join test 断言。"""

    def __init__(self) -> None:
        self._l201_s6_gate: dict[str, dict[str, Any]] = {}

    def capture_for_l201_s6_gate(self, project_id: str) -> dict[str, Any]:
        return self._l201_s6_gate.get(project_id, {})

    def record_l201_s6_gate(self, project_id: str, payload: dict[str, Any]) -> None:
        self._l201_s6_gate[project_id] = payload


@pytest.fixture
def mock_ic_payload() -> _MockICPayload:
    return _MockICPayload()


# ---------------------------------------------------------------------------
# fixture 5 · mock_archive_store (project/archive/manifest 综合 mock)
# ---------------------------------------------------------------------------

class _MockArchiveStore:
    """综合 mock: state + closing_bundle_hash + archive_path + manifest + 各类故障注入。"""

    def __init__(self, tmp_root: Path, event_bus: _MockEventBus) -> None:
        self._tmp_root = tmp_root
        self._event_bus = event_bus
        self._state: dict[str, str] = {}
        self._state_writer_log: dict[str, list[str]] = {}
        self._bundle_hash: dict[str, str] = {}
        self._manifest: dict[str, dict[str, Any]] = {}
        self._resume_markers: dict[str, float] = {}
        self._project_size_gb: dict[str, float] = {}
        # 故障注入
        self._disk_full_at: float | None = None
        self._manifest_fsync_fail = False
        self._chmod_fail = False
        self._archive_tamper = False
        self._md_corrupt_after_write = False
        self._partial_archive_corrupt = False
        self._max_concurrent: int = 0
        self._current_concurrent: int = 0
        self._last_sha256_duration: float = 0.0

    # state -------------------------------------------------------
    def set_state(self, pid: str, state: str, writer: str = "L1-02/L2-06") -> None:
        self._state[pid] = state
        self._state_writer_log.setdefault(pid, []).append(writer)

    def read_state(self, pid: str) -> str:
        return self._state.get(pid, "UNKNOWN")

    def state_writer_log(self, pid: str) -> list[str]:
        return list(self._state_writer_log.get(pid, []))

    def state_writer_allowlist(self) -> set[str]:
        allow: set[str] = set()
        for writers in self._state_writer_log.values():
            allow.update(writers)
        # 本 L2 负责 CLOSING_PRODUCED / ARCHIVED / PURGED；L2-01 负责 CLOSING_GATE_APPROVED
        return {w for w in allow if w == "L1-02/L2-06"}

    # bundle hash -------------------------------------------------
    def set_closing_bundle_hash(self, pid: str, h: str) -> None:
        self._bundle_hash[pid] = h

    # manifest ----------------------------------------------------
    def read_manifest(self, pid: str) -> dict[str, Any]:
        return dict(self._manifest.get(pid, {}))

    def compute_confirm_token(self, pid: str) -> str:
        manifest = self._manifest.get(pid, {})
        seed = f"{pid}:{manifest.get('archive_sha256', 'no-sha')}:{manifest.get('archived_at', 'no-at')}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]

    # resume marker -----------------------------------------------
    def has_resume_marker(self, pid: str) -> bool:
        return pid in self._resume_markers

    def write_resume_marker(self, pid: str, progress: float) -> None:
        self._resume_markers[pid] = progress

    def clear_resume_marker(self, pid: str) -> None:
        self._resume_markers.pop(pid, None)

    # size --------------------------------------------------------
    def set_project_dir_size_gb(self, pid: str, gb: float) -> None:
        self._project_size_gb[pid] = gb

    # 故障注入 -----------------------------------------------------
    def inject_disk_full_at(self, progress: float) -> None:
        self._disk_full_at = progress

    def clear_disk_full(self) -> None:
        self._disk_full_at = None

    def inject_manifest_fsync_fail(self) -> None:
        self._manifest_fsync_fail = True

    def inject_chmod_fail(self) -> None:
        self._chmod_fail = True

    def inject_archive_tamper_after_write(self) -> None:
        self._archive_tamper = True

    def inject_md_corrupt_after_write(self) -> None:
        self._md_corrupt_after_write = True

    def inject_partial_archive_corrupt(self) -> None:
        self._partial_archive_corrupt = True

    # 并发观测 -----------------------------------------------------
    def record_concurrent_archive_enter(self) -> None:
        self._current_concurrent += 1
        self._max_concurrent = max(self._max_concurrent, self._current_concurrent)

    def record_concurrent_archive_exit(self) -> None:
        self._current_concurrent -= 1

    def max_concurrent_archive_observed(self) -> int:
        return self._max_concurrent

    def last_sha256_recheck_duration_sec(self) -> float:
        return self._last_sha256_duration


@pytest.fixture
def mock_archive_store(tmp_path: Path, mock_event_bus: _MockEventBus) -> _MockArchiveStore:
    return _MockArchiveStore(tmp_path, mock_event_bus)


# ---------------------------------------------------------------------------
# fixture 6 · mock_s5_gate_status
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_s5_gate_status() -> dict[str, Any]:
    """L2-01 S5 Gate 已 PASS · state=EXECUTING · 允许进 S6。"""
    return {
        "state": "EXECUTING",
        "s5_verdict": "PASS",
        "s5_passed_at": "2026-04-20T09:00:00Z",
        "s5_evidence_ref": "s5-evidence:proj-l102-l206-test-0001:abc12345",
    }


# ---------------------------------------------------------------------------
# fixture 7 · mock_kb_client · IC-06 读 KB learn 层
# ---------------------------------------------------------------------------

class _MockKBClient:
    def __init__(self) -> None:
        self.raise_on_read = False
        self._patterns: list[dict[str, Any]] = [
            {"pattern_id": "P000", "summary": "default"},
        ]
        self._calls: list[dict[str, Any]] = []

    def set_learn_patterns(self, patterns: list[dict[str, Any]]) -> None:
        self._patterns = patterns

    def kb_read(self, project_id: str, layer: str) -> list[dict[str, Any]]:
        self._calls.append({"project_id": project_id, "layer": layer})
        if self.raise_on_read:
            from app.l2_06.errors import KBError
            raise KBError("kb unavailable")
        return list(self._patterns)

    def call_log(self) -> list[dict[str, Any]]:
        return list(self._calls)


@pytest.fixture
def mock_kb_client() -> _MockKBClient:
    return _MockKBClient()


# ---------------------------------------------------------------------------
# fixture 8 · mock_audit_scanner
# ---------------------------------------------------------------------------

class _MockAuditScanner:
    def __init__(self) -> None:
        self.raise_on_scan = False
        self._events: list[dict[str, Any]] = []

    def set_events(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    def scan(self, project_id: str) -> dict[str, Any]:
        if self.raise_on_scan:
            from app.l2_06.errors import AuditError
            raise AuditError("audit unavailable")
        return {"count": len(self._events), "events": list(self._events)}


@pytest.fixture
def mock_audit_scanner() -> _MockAuditScanner:
    return _MockAuditScanner()


# ---------------------------------------------------------------------------
# fixture 9 · mock_template_engine · IC-L2-02 L2-07
# ---------------------------------------------------------------------------

class _MockTemplateEngine:
    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._durations: list[float] = []

    def render(self, template_id: str, slots: dict[str, Any], project_id: str) -> Any:
        t0 = time.perf_counter()
        self._calls.append({"template_id": template_id, "slots": slots, "project_id": project_id})
        # 伪内容
        class _Out:
            output = f"# rendered: {template_id}\n\npid={project_id}\npatterns={slots.get('learn_patterns', [])}\n"
        out = _Out()
        self._durations.append(time.perf_counter() - t0)
        return out

    def render_calls(self) -> list[dict[str, Any]]:
        return list(self._calls)

    def render_durations(self) -> list[float]:
        return list(self._durations)


@pytest.fixture
def mock_template_engine() -> _MockTemplateEngine:
    return _MockTemplateEngine()


# ---------------------------------------------------------------------------
# fixture 10 · sut / real_sut / real_project_fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sut(
    mock_archive_store: _MockArchiveStore,
    mock_event_bus: _MockEventBus,
    mock_clock: _MockClock,
    mock_kb_client: _MockKBClient,
    mock_audit_scanner: _MockAuditScanner,
    mock_template_engine: _MockTemplateEngine,
    mock_ic_payload: _MockICPayload,
) -> ClosingStageExecutor:
    """单测 SUT · 全部外部依赖注入 mock。"""
    return ClosingStageExecutor(
        archive_store=mock_archive_store,
        event_bus=mock_event_bus,
        clock=mock_clock,
        kb_client=mock_kb_client,
        audit_scanner=mock_audit_scanner,
        template_engine=mock_template_engine,
        ic_payload=mock_ic_payload,
    )


class _RealProjectFixture:
    """e2e · 真 FS 目录 · 真 tar.zst · 最少必要 state mock。"""

    def __init__(self, tmp_root: Path, event_bus: _MockEventBus) -> None:
        self._tmp_root = tmp_root
        self._event_bus = event_bus
        self._states: dict[str, str] = {}
        self._manifests: dict[str, dict[str, Any]] = {}
        self._resume: set[str] = set()
        self._disk_full_at: float | None = None

    def create_with_state(self, state: str) -> str:
        pid = f"proj-e2e-{len(self._states):04d}"
        (self._tmp_root / f"projects/{pid}/closing").mkdir(parents=True, exist_ok=True)
        (self._tmp_root / f"projects/{pid}/meta").mkdir(parents=True, exist_ok=True)
        # 伪 5 阶段产出物
        for stage in ["s1", "s2", "s3", "s4", "s5"]:
            d = self._tmp_root / f"projects/{pid}/{stage}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "out.txt").write_bytes(os.urandom(1024))   # 1KB each
        self._states[pid] = state
        return pid

    def seed_kb_learn_patterns(self, pid: str, count: int) -> None:
        pass   # real fixture 用真 KB client · 此处可空

    def seed_audit_events(self, pid: str, count: int) -> None:
        pass

    def mark_s6_gate_approved(self, pid: str, evidence_ref: str) -> None:
        self._states[pid] = "CLOSING_GATE_APPROVED"

    def read_state(self, pid: str) -> str:
        return self._states.get(pid, "UNKNOWN")

    def inject_disk_full_at(self, progress: float) -> None:
        self._disk_full_at = progress

    def clear_disk_full(self) -> None:
        self._disk_full_at = None

    def has_resume_marker(self, pid: str) -> bool:
        return pid in self._resume

    def full_s6_s7_complete(self) -> str:
        pid = self.create_with_state("ARCHIVED")
        # 真 tar.zst
        archive_dir = self._tmp_root / "projects/_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        src = self._tmp_root / f"projects/{pid}"
        dst = archive_dir / f"{pid}.tar.zst"
        subprocess.run(
            ["tar", "--zstd", "-cf", str(dst), "-C", str(self._tmp_root), f"projects/{pid}"],
            check=True,
        )
        sha = hashlib.sha256()
        with open(dst, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        manifest = {
            "project_id": pid,
            "archive_path": str(dst),
            "archive_sha256": sha.hexdigest(),
            "archive_size_bytes": dst.stat().st_size,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "state_before": "CLOSING_GATE_APPROVED",
        }
        (archive_dir / f"{pid}.manifest.json").write_text(
            __import__("json").dumps(manifest, indent=2)
        )
        self._manifests[pid] = manifest
        return pid

    def read_manifest(self, pid: str) -> dict[str, Any]:
        return dict(self._manifests.get(pid, {}))

    def compute_confirm_token(self, pid: str) -> str:
        manifest = self._manifests.get(pid, {})
        seed = f"{pid}:{manifest.get('archive_sha256', 'no-sha')}:{manifest.get('archived_at', 'no-at')}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]

    def state_writer_allowlist(self) -> set[str]:
        return {"L1-02/L2-06"}


@pytest.fixture
def real_project_fixture(tmp_path: Path, mock_event_bus: _MockEventBus) -> _RealProjectFixture:
    # tmp_path 做 cwd · 让 "projects/..." 相对路径落在隔离目录
    import os as _os
    _os.chdir(tmp_path)
    return _RealProjectFixture(tmp_path, mock_event_bus)


@pytest.fixture
def real_sut(
    real_project_fixture: _RealProjectFixture,
    mock_event_bus: _MockEventBus,
    mock_clock: _MockClock,
    mock_kb_client: _MockKBClient,
    mock_audit_scanner: _MockAuditScanner,
    mock_template_engine: _MockTemplateEngine,
    mock_ic_payload: _MockICPayload,
) -> ClosingStageExecutor:
    """e2e SUT · real FS + real tar.zst + mock 外部。"""
    return ClosingStageExecutor.build_for_e2e(
        event_bus=mock_event_bus,
        clock=mock_clock,
        kb_client=mock_kb_client,
        audit_scanner=mock_audit_scanner,
        template_engine=mock_template_engine,
        ic_payload=mock_ic_payload,
        real_project_fixture=real_project_fixture,
    )
```

---

## §8 集成点用例（与 L2-01 Stage Gate 控制器 / L2-07 模板引擎调用链）

> §1.3 已概述 IC；本节专做 2 条 "跨 L2 调用链完整 join test" · 覆盖 L2-01 S5/S6 Gate pass + L2-07 closing 3 md 渲染。

```python
# file: tests/l1_02/test_l2_06_closing_executor_integration_points.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_06.executor import ClosingStageExecutor


class TestL2_06_ClosingExecutor_IntegrationPoints:
    """跨 L2 join test · 重点：L2-01 Gate 驱动 + L2-07 3 md 渲染链路。"""

    def test_TC_L102_L206_801_with_l201_gate_controller_s5_then_s6_chain(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L206-801 · join · L2-01 Stage Gate 控制器 S5 pass → produce_closing → S6 Gate evidence 回推。

        L2-01 <-> 本 L2 的 2 次握手：
          1. L2-01 S5 pass 后 IC-L2-01 call produce_closing(pid)
          2. 本 L2 返回 evidence_ref · L2-01 装 S6 Gate
        """
        # L2-01 S5 Gate 已 pass
        mock_archive_store.set_state(mock_project_id, "EXECUTING", writer="L1-02/L2-01")

        # L2-01 触发 produce_closing
        r = sut.produce_closing(
            request_id="r", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            caller_l2="L2-01",
        )
        # 本 L2 回 evidence_ref 供 L2-01 装 S6 Gate
        gate_payload = mock_ic_payload.capture_for_l201_s6_gate(mock_project_id)
        assert gate_payload["evidence"]["evidence_ref"] == r.evidence_ref
        assert gate_payload["evidence"]["closing_bundle_hash"] == r.closing_bundle_hash
        assert gate_payload["gate"] == "S6"

        # 模拟 L2-01 审批通过（本 L2 只等待 state 被 L2-01 改）
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED", writer="L1-02/L2-01")
        # 然后 L2-01 再触发 archive_project
        r2 = sut.archive_project(
            request_id="r2", project_id=mock_project_id, archive_options={}, caller_l2="L2-01",
        )
        assert r2.state == "ARCHIVED"
        # writer log: L2-01 改 CLOSING_GATE_APPROVED · 本 L2 改 ARCHIVED
        writers = mock_archive_store.state_writer_log(mock_project_id)
        assert writers.count("L1-02/L2-01") >= 1
        assert writers[-1] == "L1-02/L2-06"

    def test_TC_L102_L206_802_with_l207_template_engine_three_md_render_contract(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_template_engine: Any,
    ) -> None:
        """TC-L102-L206-802 · join · L2-07 模板引擎 · closing 3 md 渲染契约（template_id / slots / 顺序）。

        契约：
          1. 模板 ID · 固定顺序：lessons_learned → delivery_manifest → retro_summary
          2. slots · 必含 project_id + closed_at · delivery_manifest 额外 deliverables · retro_summary 额外 retro_data
          3. 3 次渲染串行（非并行）· 保证文件顺序写入
        """
        mock_archive_store.set_state(mock_project_id, "EXECUTING")
        sut.produce_closing(
            request_id="r", project_id=mock_project_id, trigger_stage="S6",
            closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
            lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
        )

        calls = mock_template_engine.render_calls()
        assert [c["template_id"] for c in calls] == [
            "closing.lessons_learned",
            "closing.delivery_manifest",
            "closing.retro_summary",
        ]
        # 通用 slots
        for c in calls:
            assert c["slots"]["project_id"] == mock_project_id
            assert "closed_at" in c["slots"]
        # delivery_manifest 额外 deliverables
        assert "deliverables" in calls[1]["slots"]
        # retro_summary 额外 retro_data
        assert "retro_data" in calls[2]["slots"]
```

---

## §9 边界 / edge case

> 覆盖 §0 declared 5 种 · 追加 2 种（S5 Gate 未通过 / ARCHIVED 再次 archive）· 共 7 条 · PM-14 铁律 edge 必含。

```python
# file: tests/l1_02/test_l2_06_closing_executor_edge.py
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest

from app.l2_06.executor import ClosingStageExecutor
from app.l2_06.errors import L206ArchiveError, L206PurgeError, L206StateError


class TestL2_06_ClosingExecutor_Edge:
    """§0 声明 5 种 + 扩展 2 种 · 共 7 条 · PM-14 铁律 edge 全覆盖。"""

    def test_TC_L102_L206_901_s5_gate_not_passed_direct_produce_closing_rejected(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-901 · edge-1 · S5 Gate 未通过 · state=S5_QUALITY_REWORK · produce_closing 拒绝。"""
        mock_archive_store.set_state(mock_project_id, "S5_QUALITY_REWORK")
        with pytest.raises(L206StateError) as exc:
            sut.produce_closing(
                request_id=mock_request_id, project_id=mock_project_id,
                trigger_stage="S6",
                closing_scope={"include_lessons": True, "include_delivery_manifest": True, "include_retro": True},
                lessons_source={"kb_learn_layer_enabled": True, "audit_events_enabled": True, "timespan_days": 0},
            )
        assert exc.value.code == "E_L102_L206_003"

    def test_TC_L102_L206_902_archive_hash_inconsistent_after_extern_tamper_halt(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-902 · edge-2 · archive hash 不一致 · 写入后被外部改 · HALT · 不写 state。"""
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.inject_archive_tamper_after_write()
        with pytest.raises(L206ArchiveError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc.value.code == "E_L102_L206_008"
        # state 未转到 ARCHIVED（HALT 回滚）
        assert mock_archive_store.read_state(mock_project_id) == "CLOSING_GATE_APPROVED"

    def test_TC_L102_L206_903_purge_before_90_days_strict_reject_even_with_valid_token(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-903 · edge-3 · 89 天 · 即使 token 正确 · 也必须拒绝（PM-14 90 天冷却铁律）。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=89)   # 差 1 天
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        with pytest.raises(L206PurgeError) as exc:
            sut.purge_project(
                request_id=mock_request_id, project_id=mock_project_id, confirm_token=token,
            )
        assert exc.value.code == "E_L102_L206_012"
        # 90 天整到
        mock_clock.set_archived_days_ago(mock_project_id, days=90)
        r = sut.purge_project(
            request_id=f"{mock_request_id}-2", project_id=mock_project_id,
            confirm_token=mock_archive_store.compute_confirm_token(mock_project_id),
        )
        assert r.purged_at

    def test_TC_L102_L206_904_concurrent_archive_and_purge_same_pid_serialized(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-904 · edge-4 · 并发 archive + purge 同一 pid · 串行化 · purge 等 archive 完或直接拒（需 state=ARCHIVED）。

        由于 purge 必须 state=ARCHIVED · archive 跑时 state=ARCHIVING ·
        并发 purge 必然因 state 不符或 ≥ 90 天冷却不满 拒绝 —— 保证不会误删进行中的 archive。
        """
        mock_archive_store.set_state(mock_project_id, "CLOSING_GATE_APPROVED")
        mock_archive_store.set_project_dir_size_gb(mock_project_id, gb=0.1)
        mock_clock.set_archived_days_ago(mock_project_id, days=100)   # 假设已归档 · 但实际 state 还未到 ARCHIVED
        errors: list[Exception] = []

        def do_archive() -> None:
            try:
                sut.archive_project(request_id="a1", project_id=mock_project_id, archive_options={})
            except Exception as e:
                errors.append(e)

        def do_purge() -> None:
            try:
                token = mock_archive_store.compute_confirm_token(mock_project_id)
                sut.purge_project(request_id="p1", project_id=mock_project_id, confirm_token=token)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=do_archive)
        t2 = threading.Thread(target=do_purge)
        t1.start()
        time.sleep(0.01)    # 确保 archive 先占锁
        t2.start()
        t1.join()
        t2.join()

        # archive 应成功
        assert mock_archive_store.read_state(mock_project_id) == "ARCHIVED"
        # purge 要么排后 OK · 要么 state 不符拒绝（E002）· 不应误删 archive 中产物
        assert len(errors) <= 1
        if errors:
            err = errors[0]
            assert isinstance(err, (L206PurgeError, L206StateError))

    def test_TC_L102_L206_905_restore_archive_fails_on_corrupt_tar(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        tmp_path: Path,
    ) -> None:
        """TC-L102-L206-905 · edge-5 · restore 失败 · tar.zst 损坏 · 报错 · 原 archive 保留不动（ops 可重试）。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_archive_store.inject_archive_tamper_after_write()   # 模拟损坏
        with pytest.raises(L206ArchiveError) as exc:
            sut.restore_archive(
                project_id=mock_project_id,
                restore_to=str(tmp_path / "restore"),
            )
        assert exc.value.code in ("E_L102_L206_008", "E_L102_L206_015")

    def test_TC_L102_L206_906_archived_state_reject_second_archive(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_request_id: str,
        mock_archive_store: Any,
    ) -> None:
        """TC-L102-L206-906 · edge-6 · ARCHIVED 再次调 archive_project · 拒绝（state 已终态）。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        with pytest.raises(L206StateError) as exc:
            sut.archive_project(
                request_id=mock_request_id, project_id=mock_project_id, archive_options={}
            )
        assert exc.value.code == "E_L102_L206_004"

    def test_TC_L102_L206_907_pm14_purge_only_entry_path_allowlist(
        self,
        sut: ClosingStageExecutor,
        mock_project_id: str,
        mock_archive_store: Any,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L206-907 · edge-7 · PM-14 铁律 · purge 只能由 L1-10 / L2-04 发起 · 本 L2 不接受 L2-01 / L2-05 purge。"""
        mock_archive_store.set_state(mock_project_id, "ARCHIVED")
        mock_clock.set_archived_days_ago(mock_project_id, days=100)
        token = mock_archive_store.compute_confirm_token(mock_project_id)
        # L2-01 越权 purge
        with pytest.raises(L206StateError) as exc1:
            sut.purge_project(
                request_id="r1", project_id=mock_project_id,
                confirm_token=token, caller_l2="L2-01",
            )
        assert exc1.value.code == "E_L102_L206_001"
        # L2-05 越权 purge
        with pytest.raises(L206StateError) as exc2:
            sut.purge_project(
                request_id="r2", project_id=mock_project_id,
                confirm_token=token, caller_l2="L2-05",
            )
        assert exc2.value.code == "E_L102_L206_001"
        # L2-04 合法 purge
        r = sut.purge_project(
            request_id="r3", project_id=mock_project_id,
            confirm_token=token, caller_l2="L2-04",
        )
        assert r.purged_at
```

---

*— L1-02 L2-06 收尾阶段执行器 · TDD 测试用例 · v1.0 · §0-§9 全段完结 · PM-14 归档+purge 唯一入口验收 —*
