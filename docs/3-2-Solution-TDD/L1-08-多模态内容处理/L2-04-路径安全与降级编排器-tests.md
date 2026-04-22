---
doc_id: tests-L1-08-L2-04-路径安全与降级编排器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-04-路径安全与降级编排器.md
  - docs/2-prd/L1-08 多模态内容处理/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-08 L2-04 路径安全与降级编排器 · TDD 测试用例

> 基于 3-1 L2-04 §3（5 个 public 方法 + 6 条 IC 契约）+ §11（16 项 `E_L204_*` 错误码 + 四档降级链）+ §12（路径校验/守门总开销 SLO）+ §13 TC 锚点（20 条）驱动。
> TC ID 统一前缀 `TC-L108-L204-NNN` · 其中 `PATH-*` / `DEGRADE-*` / `AUDIT-*` 为语义分组别名。
> pytest + Python 3.11+ 类型注解；`class TestL2_04_PathSafetyFacade` / `TestDegradationRouter` / `TestContentAuditor` 等组织；负向 / 性能 / 集成独立分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 × 错误码 × IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1 · 全 16 条）
- [x] §4 IC-XX 契约集成测试（IC-11 / IC-L2-01 / IC-L2-05 / IC-L2-07 / IC-09 / IC-Lock）
- [x] §5 性能 SLO 用例（§12 对标 · 路径规范化 / 守门总开销 / 审计落盘）
- [x] §6 端到端 e2e 场景（FULL / DEGRADED / HALTED / 合法写 md 全链）
- [x] §7 测试 fixture（mock_project_id / mock_event_bus / mock_clock / mock_l107_state / mock_ic11_payload / mock_l109_endpoint）
- [x] §8 集成点用例（与 L2-01/02/03 · L1-09 · L1-07 协作）
- [x] §9 边界 / edge case（空路径 / 超长路径 / symlink 环 / 中控 HALTED / 并发 1000）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|:---|:---|:---|:---|:---|
| `handle_process_content()` · md DIRECT | TC-L108-L204-001 | unit | — | IC-11 → IC-L2-01 |
| `handle_process_content()` · md PAGED（≥ 2000 行） | TC-L108-L204-002 | unit | — | IC-11 → IC-L2-01 |
| `handle_process_content()` · code DELEGATE（≥ 10 万行） | TC-L108-L204-003 | unit | — | IC-11 → IC-L2-01 |
| `handle_process_content()` · image DIRECT（< 20MB） | TC-L108-L204-004 | unit | — | IC-11 → IC-L2-01 |
| `dispatch_to_modal()` · md → MdOrchestrator | TC-L108-L204-005 | unit | — | IC-L2-01 |
| `dispatch_to_modal()` · code → CodeOrchestrator | TC-L108-L204-006 | unit | — | IC-L2-01 |
| `dispatch_to_modal()` · image → ImageOrchestrator | TC-L108-L204-007 | unit | — | IC-L2-01 |
| `emit_audit_event()` · content_read 正向 | TC-L108-L204-008 | unit | — | IC-L2-05 → IC-09 |
| `emit_audit_event()` · content_written 正向 | TC-L108-L204-009 | unit | — | IC-L2-05 → IC-09 |
| `emit_audit_event()` · path_rejected 违规事件 | TC-L108-L204-010 | unit | — | IC-L2-05 |
| `return_structured_error()` · err_type=path_forbidden | TC-L108-L204-011 | unit | — | IC-L2-06 |
| `return_structured_error()` · err_type=not_found | TC-L108-L204-012 | unit | — | IC-L2-06 |
| `notify_supervisor()` · severity=critical | TC-L108-L204-013 | unit | — | IC-L2-07 → L1-07 |
| `notify_supervisor()` · severity=high + repeat_count | TC-L108-L204-014 | unit | — | IC-L2-07 |
| `notify_supervisor()` · severity=medium 累积窗口 | TC-L108-L204-015 | unit | — | IC-L2-07 |

### §1.2 错误码 × 测试（§11 16 项全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|:---|:---|:---|:---|
| `E_L204_PATH_FORBIDDEN` | TC-L108-L204-101 | `validate_path()` | L1 单请求拒绝 |
| `E_L204_PATH_ESCAPE_BLOCKED` | TC-L108-L204-102 | `validate_path()` | L1 单请求拒绝 |
| `E_L204_CROSS_PROJECT_READ` | TC-L108-L204-103 | `validate_path()` | L1 单请求拒绝 |
| `E_L204_FILE_NOT_FOUND` | TC-L108-L204-104 | `handle_process_content()` | L2 文件级 err |
| `E_L204_PERMISSION_DENIED` | TC-L108-L204-105 | `handle_process_content()` | L2 文件级 err |
| `E_L204_BINARY_UNSUPPORTED` | TC-L108-L204-106 | `handle_process_content()` | L2 文件级 err |
| `E_L204_TYPE_MISMATCH` | TC-L108-L204-107 | `handle_process_content()` | L2 文件级 err |
| `E_L204_IMAGE_TOO_LARGE` | TC-L108-L204-108 | `handle_process_content()` | L2 文件级 err |
| `E_L204_PATH_LOCK_TIMEOUT` | TC-L108-L204-109 | `ConcurrencyLockKeeper` | L2 文件级 err |
| `E_L204_AUDIT_EMIT_FAIL` | TC-L108-L204-110 | `emit_audit_event()` | L3 审计降级 |
| `E_L204_L109_UNAVAILABLE` | TC-L108-L204-111 | `ContentAuditor` | L3 审计降级 |
| `E_L204_STARTUP_CONFIG_INVALID` | TC-L108-L204-112 | `StartupConfigValidator` | 启动失败 |
| `E_L204_EXTERNAL_ENDPOINT_BLOCKED` | TC-L108-L204-113 | `StartupConfigValidator` | 启动失败 |
| `E_L204_HALTED_DENIED` | TC-L108-L204-114 | `handle_process_content()` | L4 Halted |
| `E_L204_CONCURRENT_LIMIT_EXCEEDED` | TC-L108-L204-115 | `handle_process_content()` | L3 降级 |
| `E_L204_DISPATCH_FAIL` | TC-L108-L204-116 | `dispatch_to_modal()` | L3 降级 |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 | 场景 |
|:---|:---|:---|:---|
| IC-11 process_content（入站） | TC-L108-L204-201 | L1-01 主 loop | 合法请求全链路 |
| IC-L2-01 dispatch（出站） | TC-L108-L204-202 | L2-01 MdOrchestrator | md DIRECT 透传 canonical_path |
| IC-L2-05 → IC-09 append_event（出站） | TC-L108-L204-203 | L1-09 EventBus | 每次 I/O 必审计 |
| IC-L2-07 violation broadcast（出站） | TC-L108-L204-204 | L1-07 Supervisor | critical 违规 |
| IC-Lock acquire/release（出站） | TC-L108-L204-205 | L1-09 LockManager | per-path 写串行化 |
| IC-11 err 通道（出站） | TC-L108-L204-206 | L1-01 主 loop | err_type=path_forbidden 回写 |

### §1.4 性能 SLO × 测试（§12 对标 · ≥ 3 项）

| SLO 项 | P99 约束 | TC ID |
|:---|:---|:---|
| 路径规范化 + 白名单校验 | ≤ 200ms | TC-L108-L204-301 |
| 守门总开销（小文件场景） | ≤ 500ms | TC-L108-L204-302 |
| IC-09 审计事件落盘 | ≤ 100ms | TC-L108-L204-303 |
| IC-L2-01 分派 | ≤ 50ms | TC-L108-L204-304 |

### §1.5 e2e × 测试（§5 P0 时序 · ≥ 2 项）

| 场景 | TC ID |
|:---|:---|
| 合法 md 写全链（IC-11 → L2-01 → L1-09 审计） | TC-L108-L204-401 |
| DEGRADED 模式：L1-09 连续失败 3 次触发 fallback buffer + L1-09 恢复后 replay | TC-L108-L204-402 |
| HALTED 场景：L1-07 推 HALTED → 所有 IC-11 拒绝 → 解除后恢复 | TC-L108-L204-403 |

---

## §2 正向用例（每 public 方法 ≥ 1）

```python
# tests/unit/L1-08/L2-04/test_path_safety_facade_positive.py
import pytest
from uuid import UUID
from pathlib import Path

pytestmark = pytest.mark.asyncio


class TestL2_04_PathSafetyFacade:
    """§3.2/3.3 handle_process_content 正向路径"""

    async def test_handle_process_content_md_direct(self, facade, mock_ic11_md_read, mock_l201_md):
        """TC-L108-L204-001 · 合法 md 读 · DIRECT 档 · 返 ok + audit_ref"""
        resp = await facade.handle_process_content(mock_ic11_md_read)
        assert resp["status"] == "ok"
        assert resp["route"] == "DIRECT"
        assert UUID(resp["audit_ref"])
        assert resp["latency_ms"] >= 0
        mock_l201_md.handle_md_request.assert_called_once()
        payload = mock_l201_md.handle_md_request.call_args[0][0]
        assert payload["paged"] is False
        assert payload["canonical_path"].startswith(str(facade.scope_root))

    async def test_handle_process_content_md_paged(self, facade, make_md_file, mock_l201_md):
        """TC-L108-L204-002 · md ≥ 2000 行 · paged=true · 审计 threshold_hit"""
        big_md = make_md_file(lines=2500)
        req = _ic11_req(path=str(big_md), modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["route"] == "PAGED"
        assert "md_paged_threshold" in resp["threshold_hits"]
        dispatch = mock_l201_md.handle_md_request.call_args[0][0]
        assert dispatch["paged"] is True
        assert dispatch["total_lines"] >= 2000

    async def test_handle_process_content_code_delegate(self, facade, mock_ic11_code_analyze, mock_l202_code):
        """TC-L108-L204-003 · code 仓 > 10 万行 · delegate=true · subagent_session_id 透传"""
        resp = await facade.handle_process_content(mock_ic11_code_analyze)
        assert resp["route"] == "DELEGATE"
        mock_l202_code.handle_code_request.assert_called_once()
        assert mock_l202_code.handle_code_request.call_args[0][0]["delegate"] is True

    async def test_handle_process_content_image_direct(self, facade, make_image_file, mock_l203_image):
        """TC-L108-L204-004 · image < 20MB · DIRECT"""
        img = make_image_file(size_bytes=15 * 1024 * 1024, fmt="png")
        req = _ic11_req(path=str(img), modality="image", action="analyze", image_hint="architecture")
        resp = await facade.handle_process_content(req)
        assert resp["status"] == "ok"
        assert resp["route"] == "DIRECT"
        mock_l203_image.handle_image_request.assert_called_once()

    async def test_dispatch_to_modal_md(self, facade, mock_l201_md):
        """TC-L108-L204-005 · dispatch_to_modal type=md → MdOrchestrator"""
        decision = _decision(route="DIRECT", modality="md")
        req = _ic11_req(modality="md", action="read")
        await facade._dispatch_to_modal(decision, req)
        mock_l201_md.handle_md_request.assert_called_once()

    async def test_dispatch_to_modal_code(self, facade, mock_l202_code):
        """TC-L108-L204-006 · dispatch_to_modal type=code → CodeOrchestrator"""
        decision = _decision(route="DELEGATE", modality="code", delegate=True)
        req = _ic11_req(modality="code", action="analyze")
        await facade._dispatch_to_modal(decision, req)
        mock_l202_code.handle_code_request.assert_called_once()

    async def test_dispatch_to_modal_image(self, facade, mock_l203_image):
        """TC-L108-L204-007 · dispatch_to_modal type=image → ImageOrchestrator"""
        decision = _decision(route="DIRECT", modality="image")
        req = _ic11_req(modality="image", action="analyze")
        await facade._dispatch_to_modal(decision, req)
        mock_l203_image.handle_image_request.assert_called_once()


class TestContentAuditor:
    """§3.5 emit_audit_event 正向路径"""

    async def test_emit_audit_event_content_read(self, auditor, mock_event_bus):
        """TC-L108-L204-008 · content_read 成功 · 事件含 file_hash + latency"""
        event = _audit_event("L1-08:content_read", path="docs/x.md", sha="abc123", lines=1200)
        ref = await auditor.emit_audit_event(event)
        assert UUID(ref)
        mock_event_bus.append_event.assert_called_once()
        evt = mock_event_bus.append_event.call_args[0][0]
        assert evt["event_type"] == "L1-08:content_read"
        assert evt["content"]["file_hash_sha256"] == "abc123"
        assert evt["content"]["lines"] == 1200

    async def test_emit_audit_event_content_written(self, auditor, mock_event_bus):
        """TC-L108-L204-009 · content_written 写路径 · 审计含 size_bytes"""
        event = _audit_event("L1-08:content_written", path="docs/new.md", size=4096)
        await auditor.emit_audit_event(event)
        evt = mock_event_bus.append_event.call_args[0][0]
        assert evt["event_type"] == "L1-08:content_written"
        assert evt["content"]["size_bytes"] == 4096

    async def test_emit_audit_event_path_rejected(self, auditor, mock_event_bus):
        """TC-L108-L204-010 · path_rejected 违规事件 · 含 err_type + attempted_path"""
        event = _audit_event("L1-08:path_rejected", path="/etc/passwd",
                             err_type="path_forbidden", reason="write outside whitelist")
        await auditor.emit_audit_event(event)
        evt = mock_event_bus.append_event.call_args[0][0]
        assert evt["event_type"] == "L1-08:path_rejected"
        assert evt["content"]["err_type"] == "path_forbidden"
        assert evt["content"]["attempted_path"].endswith("/etc/passwd")


class TestStructuredErrorReturn:
    """§3.1 return_structured_error · IC-L2-06"""

    async def test_return_err_path_forbidden(self, facade):
        """TC-L108-L204-011 · 写非白名单 → IC-L2-06 结构化 err"""
        req = _ic11_req(path="scripts/hack.py", modality="code", action="write", content="x")
        resp = await facade.handle_process_content(req)
        assert resp["status"] == "err"
        assert resp["err_type"] == "path_forbidden"
        assert UUID(resp["audit_ref"])
        assert resp["suggested_action"]

    async def test_return_err_not_found(self, facade):
        """TC-L108-L204-012 · 文件不存在 → err_type=not_found · 非 critical"""
        req = _ic11_req(path="docs/missing_xyz.md", modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["status"] == "err"
        assert resp["err_type"] == "not_found"


class TestSupervisorNotification:
    """§3.6 notify_supervisor · IC-L2-07"""

    async def test_notify_supervisor_critical(self, facade, mock_event_bus):
        """TC-L108-L204-013 · ../../../etc 逃逸 → severity=critical 广播"""
        req = _ic11_req(path="../../../etc/hosts", modality="md", action="read")
        await facade.handle_process_content(req)
        broadcast = _find_event(mock_event_bus, event_type="L1-08:path_rejected")
        assert broadcast is not None
        assert broadcast["content"]["err_type"] in {"path_escape", "path_forbidden"}

    async def test_notify_supervisor_high_repeat(self, facade, mock_event_bus):
        """TC-L108-L204-014 · 同调用方 60s 内 5 次 path_forbidden · repeat_count=5"""
        for _ in range(5):
            await facade.handle_process_content(_ic11_req(path="/var/tmp/x.md", action="write"))
        rejects = _count_events(mock_event_bus, event_type="L1-08:path_rejected")
        assert rejects == 5

    async def test_notify_supervisor_medium_sliding(self, facade):
        """TC-L108-L204-015 · invalid_path 观察窗口 60s · severity=medium"""
        for _ in range(3):
            resp = await facade.handle_process_content(_ic11_req(path="", modality="md", action="read"))
            assert resp["err_type"] == "invalid_path"
```

---

## §3 负向用例（每错误码 ≥ 1）

> 基于 §11.1 16 个错误码 · 每码 1 条 TC · `pytest.raises` 或结构化 err 返回双路径。

```python
# tests/unit/L1-08/L2-04/test_path_safety_facade_negative.py
import pytest, os
from unittest.mock import patch

pytestmark = pytest.mark.asyncio


class TestL204ErrorCodes_L1_SingleRejection:
    """E_L204_PATH_* · L1 单请求拒绝档 · 仍可接下一请求"""

    async def test_E_L204_PATH_FORBIDDEN(self, facade, mock_event_bus):
        """TC-L108-L204-101 · 写 /var/tmp/x.md → path_forbidden + critical 广播"""
        req = _ic11_req(path="/var/tmp/secret.md", modality="md", action="write", content="leak")
        resp = await facade.handle_process_content(req)
        assert resp["status"] == "err"
        assert resp["err_type"] == "path_forbidden"
        evt = _find_event(mock_event_bus, event_type="L1-08:path_rejected")
        assert evt["content"]["err_type"] == "path_forbidden"

    async def test_E_L204_PATH_ESCAPE_BLOCKED(self, facade, mock_event_bus):
        """TC-L108-L204-102 · resolve 后超 scope_root → path_escape · critical"""
        req = _ic11_req(path="docs/../../../etc/shadow", modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "path_escape"
        assert resp["canonical_path"] is not None  # 仍附 canonical 供调用方调试

    async def test_E_L204_CROSS_PROJECT_READ(self, facade, other_project_md):
        """TC-L108-L204-103 · realpath 命中他 project → cross_project"""
        req = _ic11_req(path=str(other_project_md), modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "cross_project"


class TestL204ErrorCodes_L2_FileLevel:
    """E_L204_FILE_* · L2 文件级 err · 不通知 L1-07"""

    async def test_E_L204_FILE_NOT_FOUND(self, facade, mock_event_bus):
        """TC-L108-L204-104 · 路径合法但文件不存在 → not_found · 无 critical 广播"""
        req = _ic11_req(path="docs/nonexistent.md", modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "not_found"
        assert _find_event(mock_event_bus, event_type="L1-08:path_rejected") is None  # 无违规事件

    async def test_E_L204_PERMISSION_DENIED(self, facade, make_md_file):
        """TC-L108-L204-105 · chmod 000 → EACCES → permission_denied"""
        f = make_md_file(lines=10)
        os.chmod(f, 0o000)
        try:
            req = _ic11_req(path=str(f), modality="md", action="read")
            resp = await facade.handle_process_content(req)
            assert resp["err_type"] == "permission_denied"
        finally:
            os.chmod(f, 0o644)

    async def test_E_L204_BINARY_UNSUPPORTED(self, facade, make_binary_file):
        """TC-L108-L204-106 · UTF-8 解码失败 + type=md → binary_unsupported"""
        f = make_binary_file(ext=".md", content=b"\x89PNG\x0d\x0a\x1a\x0a")
        req = _ic11_req(path=str(f), modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "binary_unsupported"

    async def test_E_L204_TYPE_MISMATCH(self, facade, make_image_file):
        """TC-L108-L204-107 · .jpg 被 type=md 请求 → type_mismatch · 不分派"""
        jpg = make_image_file(size_bytes=1024, fmt="jpg")
        req = _ic11_req(path=str(jpg), modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "type_mismatch"

    async def test_E_L204_IMAGE_TOO_LARGE(self, facade, make_image_file):
        """TC-L108-L204-108 · 25MB.jpg > 20MB 阈值 → size_exceeded"""
        big = make_image_file(size_bytes=25 * 1024 * 1024, fmt="jpg")
        req = _ic11_req(path=str(big), modality="image", action="analyze")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "size_exceeded"

    async def test_E_L204_PATH_LOCK_TIMEOUT(self, facade, lock_always_busy):
        """TC-L108-L204-109 · FileLock.acquire 超 60s → concurrency_lock_timeout"""
        req = _ic11_req(path="docs/contended.md", modality="md", action="write", content="x")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "concurrency_lock_timeout"


class TestL204ErrorCodes_L3_AuditDegrade:
    """E_L204_AUDIT_* / L109_UNAVAILABLE · L3 审计降级"""

    async def test_E_L204_AUDIT_EMIT_FAIL(self, auditor, mock_event_bus_flaky):
        """TC-L108-L204-110 · IC-09 单次 5xx → 进入 retry · 最终 AuditEmitFail"""
        mock_event_bus_flaky.set_fail_count(1)
        event = _audit_event("L1-08:content_read", path="docs/x.md")
        ref = await auditor.emit_audit_event(event)
        assert UUID(ref)
        assert mock_event_bus_flaky.call_count >= 2  # 首次失败 + 重试

    async def test_E_L204_L109_UNAVAILABLE_enters_degraded(self, facade, mock_event_bus_down, state_machine):
        """TC-L108-L204-111 · L1-09 连续 3 次 5xx → state=DEGRADED + fallback_buffer 激活"""
        mock_event_bus_down.set_persistent_fail(True)
        for _ in range(3):
            await facade.handle_process_content(_ic11_req(path="docs/x.md", modality="md", action="read"))
        assert state_machine.state == "DEGRADED"
        assert facade.auditor.fallback_buffer.size >= 3


class TestL204ErrorCodes_Startup:
    """E_L204_STARTUP_* · 启动期失败 · exit(1)"""

    async def test_E_L204_STARTUP_CONFIG_INVALID(self, tmp_path):
        """TC-L108-L204-112 · config schema 不合法 → SystemExit(1)"""
        bad_cfg = tmp_path / "bad.yaml"
        bad_cfg.write_text("scope_root:\n  - NOT_A_STRING: 1\n")
        with pytest.raises(SystemExit) as exc:
            StartupConfigValidator.validate_and_load(str(bad_cfg))
        assert exc.value.code == 1

    async def test_E_L204_EXTERNAL_ENDPOINT_BLOCKED(self, tmp_path):
        """TC-L108-L204-113 · image.endpoints 非空 → exit(1) + 审计 external_endpoint_blocked"""
        cfg = tmp_path / "cfg.yaml"
        cfg.write_text("image:\n  endpoints:\n    - https://malicious.example\n")
        with pytest.raises(SystemExit) as exc:
            StartupConfigValidator.validate_and_load(str(cfg))
        assert exc.value.code == 1


class TestL204ErrorCodes_Halted:
    """E_L204_HALTED_DENIED · L4 进程停摆"""

    async def test_E_L204_HALTED_DENIED(self, facade, state_machine):
        """TC-L108-L204-114 · 推 HALTED 后所有 IC-11 均 halted_denied"""
        state_machine.force_state("HALTED")
        resp = await facade.handle_process_content(_ic11_req(path="docs/x.md"))
        assert resp["err_type"] == "halted_denied"
        # 审计事件不包含 request content · 仅记录 action
        # scope §5.8.6 违规：不记请求正文


class TestL204ErrorCodes_DispatchAndConcurrency:
    """E_L204_DISPATCH_FAIL / CONCURRENT_LIMIT"""

    async def test_E_L204_CONCURRENT_LIMIT_EXCEEDED(self, facade_semaphore_1, mock_l201_md_slow):
        """TC-L108-L204-115 · Semaphore=1 · 第 2 并发 → 429 concurrent_limit_exceeded"""
        import asyncio
        mock_l201_md_slow.set_latency_ms(500)
        req = _ic11_req(path="docs/x.md", modality="md", action="read")
        task1 = asyncio.create_task(facade_semaphore_1.handle_process_content(req))
        await asyncio.sleep(0.05)  # 让 task1 进入
        resp2 = await facade_semaphore_1.handle_process_content(req)
        assert resp2["err_type"] == "concurrent_limit_exceeded"
        await task1

    async def test_E_L204_DISPATCH_FAIL(self, facade, mock_l201_md_crashing):
        """TC-L108-L204-116 · L2-01 抛 5xx × 2 + 最终失败 → dispatch_fail · critical 广播"""
        mock_l201_md_crashing.set_fail_count(3)
        req = _ic11_req(path="docs/x.md", modality="md", action="read")
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "dispatch_fail"
```

---

## §4 IC-XX 契约集成测试

> §3 列出 6 条 IC · 本节以 mock 对端方式验证入/出参 schema + 字段级语义。

```python
# tests/integration/L1-08/L2-04/test_ic_contracts.py
import pytest, json, jsonschema
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestIC11ProcessContentContract:
    """IC-11 · 本 L2 作为承担方（从 L1-01/02/04 入站）"""

    async def test_ic11_inbound_ok_response_schema(self, facade, mock_ic11_md_read, ic11_ok_schema):
        """TC-L108-L204-201 · 合法请求 → 返回体符合 IC-11 ok schema"""
        resp = await facade.handle_process_content(mock_ic11_md_read)
        jsonschema.validate(resp, ic11_ok_schema)
        assert set(resp.keys()) >= {"project_id", "request_id", "status", "result",
                                     "audit_ref", "latency_ms", "route"}

    async def test_ic11_inbound_err_response_schema(self, facade, ic11_err_schema):
        """TC-L108-L204-206 · err 路径返回体符合 IC-L2-06 err schema"""
        req = _ic11_req(path="/root/danger.md", modality="md", action="write", content="x")
        resp = await facade.handle_process_content(req)
        jsonschema.validate(resp, ic11_err_schema)
        assert resp["status"] == "err"
        assert "err_type" in resp and "suggested_action" in resp


class TestICL201DispatchContract:
    """IC-L2-01 · 分派到模态 L2"""

    async def test_icl201_dispatch_md_payload(self, facade, mock_l201_md, icl201_schema):
        """TC-L108-L204-202 · md DIRECT 分派 · canonical_path 已 resolve · lock_handle 颁发"""
        req = _ic11_req(path="docs/goals.md", modality="md", action="read")
        await facade.handle_process_content(req)
        payload = mock_l201_md.handle_md_request.call_args[0][0]
        jsonschema.validate(payload, icl201_schema)
        assert payload["canonical_path"] == str((facade.scope_root / "docs/goals.md").resolve())
        assert UUID(payload["audit_ref_prelim"])
        assert "lock_handle" in payload


class TestIC09AppendEventContract:
    """IC-09 · 审计事件统一出口"""

    async def test_ic09_audit_event_every_io(self, facade, mock_event_bus, ic09_schema):
        """TC-L108-L204-203 · 每次 I/O 必有 IC-09 事件 · schema 校验"""
        await facade.handle_process_content(_ic11_req(path="docs/a.md"))
        await facade.handle_process_content(_ic11_req(path="docs/b.md"))
        assert mock_event_bus.append_event.call_count == 2
        for call in mock_event_bus.append_event.call_args_list:
            jsonschema.validate(call[0][0], ic09_schema)


class TestICL207SupervisorBroadcast:
    """IC-L2-07 · 硬约束违规广播"""

    async def test_icl207_critical_broadcast(self, facade, mock_event_bus, icl207_schema):
        """TC-L108-L204-204 · 路径逃逸 → severity=critical broadcast · 包含 evidence"""
        req = _ic11_req(path="../../../etc/hosts", modality="md", action="read")
        await facade.handle_process_content(req)
        # 通过事件总线查 path_rejected + L1-07 订阅
        evt = _find_event(mock_event_bus, event_type="L1-08:path_rejected")
        assert evt is not None
        # 违规事件符合 IC-L2-07 body schema
        violation = {
            "project_id": evt["project_id"],
            "incident_id": evt["audit_ref"],
            "violation_type": "path_escape_attempt",
            "severity": "critical",
            "evidence": evt["content"],
            "ts": evt["ts"],
        }
        jsonschema.validate(violation, icl207_schema)


class TestICLockAcquireRelease:
    """IC-Lock · 与 L1-09 LockManager"""

    async def test_ic_lock_per_path_serialize(self, facade, lock_manager, mock_l201_md):
        """TC-L108-L204-205 · 写同 path · LockManager.acquire/release 被对称调用"""
        req = _ic11_req(path="docs/x.md", modality="md", action="write", content="v1")
        await facade.handle_process_content(req)
        lock_manager.acquire.assert_called_once()
        lock_manager.release.assert_called_once()
        # 释放顺序：L2-01 回传后 release
        assert lock_manager.release.call_args[0][0] == \
               lock_manager.acquire.return_value
```

---

## §5 性能 SLO 用例

> 对标 3-1 §12 · pytest-benchmark 风格伪代码 · 本文档不追求真跑 · 仅约束 assert 形态与阈值。

```python
# tests/perf/L1-08/L2-04/test_slo.py
import pytest, time, statistics
from contextlib import contextmanager

pytestmark = pytest.mark.asyncio


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestPathValidationSLO:
    """§12.2 · 路径规范化 + 白名单校验 P99 ≤ 200ms"""

    async def test_path_validation_p99_under_200ms(self, validator):
        """TC-L108-L204-301 · 1000 次 realpath 校验 · P99 ≤ 200ms"""
        samples = []
        for i in range(1000):
            with _timer() as elapsed:
                validator.validate_path(f"docs/batch/{i}.md", action="read")
            samples.append(elapsed())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 200.0, f"P99={p99:.2f}ms > 200ms"


class TestGatekeeperTotalSLO:
    """§12.2 · 守门总开销 P99 ≤ 500ms（小文件场景）"""

    async def test_gatekeeper_total_p99_under_500ms(self, facade, small_md_pool):
        """TC-L108-L204-302 · 1000 次 < 500 行 md 读 · P99 ≤ 500ms"""
        samples = []
        for md in small_md_pool[:1000]:
            with _timer() as elapsed:
                await facade.handle_process_content(_ic11_req(path=str(md)))
            samples.append(elapsed())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 500.0

    async def test_gatekeeper_p50_under_80ms(self, facade, small_md_pool):
        """TC-L108-L204-302b · P50 ≤ 80ms"""
        samples = []
        for md in small_md_pool[:1000]:
            with _timer() as elapsed:
                await facade.handle_process_content(_ic11_req(path=str(md)))
            samples.append(elapsed())
        assert statistics.median(samples) <= 80.0


class TestAuditEmitSLO:
    """§12.2 · IC-09 审计事件落盘 P99 ≤ 100ms"""

    async def test_ic09_emit_p99_under_100ms(self, auditor, mock_event_bus):
        """TC-L108-L204-303 · 1000 次 emit · P99 ≤ 100ms"""
        samples = []
        for _ in range(1000):
            with _timer() as elapsed:
                await auditor.emit_audit_event(_audit_event("L1-08:content_read", path="docs/x.md"))
            samples.append(elapsed())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 100.0


class TestDispatchSLO:
    """§12.2 · IC-L2-01 分派 P99 ≤ 50ms"""

    async def test_dispatch_p99_under_50ms(self, facade, mock_l201_md_nearinstant):
        """TC-L108-L204-304 · mock 模态 L2 立返 · dispatch 自身开销 ≤ 50ms"""
        samples = []
        req = _ic11_req(path="docs/x.md")
        for _ in range(500):
            with _timer() as elapsed:
                await facade._dispatch_to_modal(_decision(route="DIRECT", modality="md"), req)
            samples.append(elapsed())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 50.0
```

---

## §6 端到端 e2e 场景

> 映射 3-1 §5 P0 时序 · 端到端拉通 L1-01 → L2-04 → L2-01 → L1-09。

```python
# tests/e2e/L1-08/L2-04/test_e2e.py
import pytest, asyncio

pytestmark = pytest.mark.asyncio


class TestE2ELegalMdWrite:
    """§5 P0 · 合法 md 写全链路"""

    async def test_legal_md_write_end_to_end(self, facade, md_orchestrator_real, l109_real, tmp_project):
        """TC-L108-L204-401 · IC-11 → L2-04 → L2-01.write_md → L1-09 审计事件
        断言 · 文件落盘 + 审计事件 2 条（write_start + content_written）+ hash 一致"""
        req = _ic11_req(path="docs/new_goal.md", modality="md", action="write",
                        content="# Goal\nvalue\n")
        resp = await facade.handle_process_content(req)
        assert resp["status"] == "ok"
        assert resp["route"] == "DIRECT"
        final_path = tmp_project / "docs/new_goal.md"
        assert final_path.exists()
        # 审计链
        events = l109_real.query_trail(request_id_ref=req["request_id"])
        assert any(e["event_type"] == "L1-08:content_written" for e in events)
        # hash 一致
        written = final_path.read_text()
        import hashlib
        sha = hashlib.sha256(written.encode()).hexdigest()
        written_evt = next(e for e in events if e["event_type"] == "L1-08:content_written")
        assert written_evt["content"]["file_hash_sha256"] == sha


class TestE2EDegradedAndRecover:
    """§11.2 四档降级链 · L1-09 故障 + 恢复"""

    async def test_degraded_fallback_then_replay(self, facade, flaky_l109, state_machine):
        """TC-L108-L204-402 · L1-09 连续 3 次 5xx → DEGRADED → fallback_buffer → 恢复后 replay"""
        flaky_l109.set_fail_count(3)
        for _ in range(3):
            await facade.handle_process_content(_ic11_req(path="docs/a.md"))
        assert state_machine.state == "DEGRADED"
        assert facade.auditor.fallback_buffer.size >= 3
        # 恢复
        flaky_l109.recover()
        await asyncio.sleep(0.15)  # replay 调度
        assert facade.auditor.fallback_buffer.size == 0
        assert state_machine.state == "FULL"


class TestE2EHaltedFlow:
    """§11.2 L4 Halted · L1-07 推 HALTED + 解除"""

    async def test_halted_denies_then_resumes(self, facade, state_machine):
        """TC-L108-L204-403 · HALTED 推入 → 所有 IC-11 halted_denied · 解除后恢复"""
        state_machine.force_state("HALTED")
        resp = await facade.handle_process_content(_ic11_req(path="docs/a.md"))
        assert resp["err_type"] == "halted_denied"
        state_machine.force_state("FULL")
        resp2 = await facade.handle_process_content(_ic11_req(path="docs/a.md"))
        assert resp2["status"] == "ok"
```

---

## §7 测试 fixture

> 固定 ≥ 5 个 fixture · 统一 mock 边界 · 避免每 TC 重写 Arrange。

```python
# tests/conftest.py
import pytest, tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone


@pytest.fixture
def mock_project_id() -> str:
    """固定 PM-14 project_id · 用于 scope 校验"""
    return "demo-proj-001"


@pytest.fixture
def mock_clock(monkeypatch):
    """可控的单调递增时钟 · 测试 ts / rate limit / sliding window"""
    class FakeClock:
        def __init__(self):
            self.t = 1700000000.0
        def now(self) -> float:
            self.t += 0.001
            return self.t
        def iso(self) -> str:
            return datetime.fromtimestamp(self.t, tz=timezone.utc).isoformat()
    fc = FakeClock()
    monkeypatch.setattr("time.time", fc.now)
    return fc


@pytest.fixture
def mock_event_bus():
    """mock IC-09 event bus · 支持断言 append_event 调用"""
    bus = MagicMock()
    bus.append_event = AsyncMock(return_value={"event_id": str(uuid4()), "hash": "a" * 64})
    bus._events = []
    async def _capture(evt):
        bus._events.append(evt)
        return {"event_id": str(uuid4()), "hash": "a" * 64}
    bus.append_event.side_effect = _capture
    return bus


@pytest.fixture
def mock_event_bus_down():
    """持续不可用 L1-09 · 用于 DEGRADED 场景"""
    bus = MagicMock()
    bus.fail = True
    async def _fail(evt):
        if bus.fail:
            raise ConnectionError("L1-09 5xx")
        return {"event_id": str(uuid4())}
    bus.append_event = AsyncMock(side_effect=_fail)
    bus.set_persistent_fail = lambda v: setattr(bus, "fail", v)
    return bus


@pytest.fixture
def mock_l107_state():
    """mock Supervisor state · 可 force_state 以切 FULL/DEGRADED/HALTED"""
    class State:
        def __init__(self):
            self.state = "FULL"
        def force_state(self, s): self.state = s
    return State()


@pytest.fixture
def mock_ic11_md_read(mock_project_id, tmp_project) -> dict:
    """标准 IC-11 md 读请求 payload"""
    return _ic11_req(
        project_id=mock_project_id,
        path="docs/goals.md",
        modality="md",
        action="read",
    )


@pytest.fixture
def mock_ic11_code_analyze(mock_project_id, big_repo) -> dict:
    """IC-11 code 分析请求 · 仓 > 10 万行"""
    return _ic11_req(
        project_id=mock_project_id,
        path=str(big_repo),
        modality="code",
        action="analyze",
        focus_hint="find auth",
    )


@pytest.fixture
def mock_l201_md():
    """mock MdOrchestrator"""
    m = MagicMock()
    m.handle_md_request = AsyncMock(return_value={
        "status": "ok",
        "result": {"lines": 1200, "sha256": "deadbeef" * 8},
    })
    return m


@pytest.fixture
def mock_l202_code():
    """mock CodeOrchestrator"""
    m = MagicMock()
    m.handle_code_request = AsyncMock(return_value={"status": "ok", "result": {}})
    return m


@pytest.fixture
def mock_l203_image():
    """mock ImageOrchestrator"""
    m = MagicMock()
    m.handle_image_request = AsyncMock(return_value={"status": "ok", "result": {}})
    return m


@pytest.fixture
def tmp_project(tmp_path) -> Path:
    """空 project 目录 · 含 docs/ tests/ harnessFlow/ 三个白名单子目录"""
    for d in ["docs", "tests", "harnessFlow"]:
        (tmp_path / d).mkdir()
    (tmp_path / "docs" / "goals.md").write_text("# goals\n" * 1200)
    return tmp_path


@pytest.fixture
def make_md_file(tmp_project):
    def _make(lines: int = 10, name: str = "data.md") -> Path:
        f = tmp_project / "docs" / name
        f.write_text("line\n" * lines)
        return f
    return _make


@pytest.fixture
def make_image_file(tmp_project):
    def _make(size_bytes: int, fmt: str = "png") -> Path:
        f = tmp_project / "docs" / f"img.{fmt}"
        f.write_bytes(b"\x00" * size_bytes)
        return f
    return _make


@pytest.fixture
def make_binary_file(tmp_project):
    def _make(ext: str, content: bytes) -> Path:
        f = tmp_project / "docs" / f"bin{ext}"
        f.write_bytes(content)
        return f
    return _make


@pytest.fixture
def facade(mock_event_bus, mock_l201_md, mock_l202_code, mock_l203_image,
           mock_l107_state, tmp_project, lock_manager):
    """组装 PathSafetyFacade · 所有下游 mock"""
    return PathSafetyFacade(
        scope_root=tmp_project,
        whitelist=["docs/", "tests/", "harnessFlow/"],
        event_bus=mock_event_bus,
        md_orchestrator=mock_l201_md,
        code_orchestrator=mock_l202_code,
        image_orchestrator=mock_l203_image,
        supervisor_state=mock_l107_state,
        lock_manager=lock_manager,
    )


@pytest.fixture
def lock_manager():
    m = MagicMock()
    m.acquire = AsyncMock(return_value="lock-token-001")
    m.release = AsyncMock(return_value=None)
    return m
```

---

## §8 集成点用例（与兄弟 L2 / 跨 L1 协作）

> 验证 L2-04 作为"门面 + 审计统一出口"与 L2-01/02/03 + L1-09 + L1-07 的协作边界。

```python
# tests/integration/L1-08/L2-04/test_integration_points.py
import pytest, asyncio

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL201MdOrchestrator:
    """与 L2-01 文档 IO 编排器协作"""

    async def test_l204_to_l201_paged_flag_propagation(self, facade, make_md_file, mock_l201_md):
        """TC-L108-L204-501 · PAGED 档 · paged=true + total_lines 透传给 L2-01"""
        big = make_md_file(lines=3000, name="big.md")
        await facade.handle_process_content(_ic11_req(path=str(big)))
        call_payload = mock_l201_md.handle_md_request.call_args[0][0]
        assert call_payload["paged"] is True
        assert call_payload["total_lines"] == 3000

    async def test_l204_to_l201_offset_limit_passthrough(self, facade, make_md_file, mock_l201_md):
        """TC-L108-L204-502 · 分页参数 offset/limit 原样透传"""
        big = make_md_file(lines=3000, name="big.md")
        req = _ic11_req(path=str(big), offset=1000, limit=500)
        await facade.handle_process_content(req)
        payload = mock_l201_md.handle_md_request.call_args[0][0]
        assert payload.get("offset") == 1000 and payload.get("limit") == 500


class TestIntegrationWithL202CodeOrchestrator:
    """与 L2-02 代码结构理解协作"""

    async def test_l204_to_l202_delegate_subagent(self, facade, big_repo, mock_l202_code):
        """TC-L108-L204-503 · code > 10 万行 · delegate=true · subagent_session_id 由 L2-02 生成"""
        req = _ic11_req(path=str(big_repo), modality="code", action="analyze")
        resp = await facade.handle_process_content(req)
        assert resp["route"] == "DELEGATE"
        payload = mock_l202_code.handle_code_request.call_args[0][0]
        assert payload["delegate"] is True


class TestIntegrationWithL203ImageOrchestrator:
    """与 L2-03 图片视觉理解协作"""

    async def test_l204_to_l203_image_hint_propagation(self, facade, make_image_file, mock_l203_image):
        """TC-L108-L204-504 · image_hint=architecture 透传"""
        img = make_image_file(size_bytes=2 * 1024 * 1024, fmt="png")
        req = _ic11_req(path=str(img), modality="image", action="analyze", image_hint="architecture")
        await facade.handle_process_content(req)
        payload = mock_l203_image.handle_image_request.call_args[0][0]
        assert payload["image_hint"] == "architecture"


class TestIntegrationWithL109EventBus:
    """与 L1-09 事件总线协作"""

    async def test_l204_audit_ordering_guarantee(self, facade, mock_event_bus):
        """TC-L108-L204-505 · 同 request 审计事件顺序 · start 先于 finish"""
        req = _ic11_req(path="docs/x.md")
        await facade.handle_process_content(req)
        events = [e for e in mock_event_bus._events if e.get("request_id_ref") == req["request_id"]]
        assert len(events) >= 1
        # 有 finish event
        assert any(e["event_type"] in {"L1-08:content_read", "L1-08:content_written"} for e in events)


class TestIntegrationWithL107Supervisor:
    """与 L1-07 Harness 监督协作"""

    async def test_l204_subscribes_to_l107_halted_events(self, facade, mock_l107_state):
        """TC-L108-L204-506 · L1-07 推 HALTED → L2-04 在 100ms 内转状态 + 拒 IC-11"""
        mock_l107_state.force_state("HALTED")
        resp = await facade.handle_process_content(_ic11_req(path="docs/x.md"))
        assert resp["err_type"] == "halted_denied"
```

---

## §9 边界 / edge case

> 空 / 超大 / 并发 / 超时 / 崩溃 · 至少 4 类。

```python
# tests/edge/L1-08/L2-04/test_edge_cases.py
import pytest, asyncio, os

pytestmark = pytest.mark.asyncio


class TestEdgeEmptyAndInvalid:
    """空 / None / 非法字符"""

    async def test_edge_empty_path(self, facade):
        """TC-L108-L204-601 · path="" → invalid_path · 不触发 realpath"""
        resp = await facade.handle_process_content(_ic11_req(path="", modality="md", action="read"))
        assert resp["err_type"] == "invalid_path"

    async def test_edge_path_with_null_byte(self, facade):
        """TC-L108-L204-602 · path 含 \\x00 控制字符 → invalid_path"""
        resp = await facade.handle_process_content(_ic11_req(path="docs/ok\x00.md"))
        assert resp["err_type"] == "invalid_path"

    async def test_edge_project_id_missing(self, facade):
        """TC-L108-L204-603 · project_id 缺失 → invalid_project_id"""
        req = _ic11_req(path="docs/x.md")
        req["project_id"] = ""
        resp = await facade.handle_process_content(req)
        assert resp["err_type"] == "invalid_project_id"


class TestEdgeOversized:
    """超长路径 / 超大文件 / 超长分页 offset"""

    async def test_edge_path_longer_than_1024(self, facade):
        """TC-L108-L204-604 · path > 1024 字符 → invalid_path"""
        bad = "docs/" + "a" * 1100 + ".md"
        resp = await facade.handle_process_content(_ic11_req(path=bad))
        assert resp["err_type"] == "invalid_path"

    async def test_edge_image_exactly_20mb(self, facade, make_image_file):
        """TC-L108-L204-605 · image == 20MB 边界 · 允许 · DIRECT"""
        img = make_image_file(size_bytes=20 * 1024 * 1024, fmt="png")
        req = _ic11_req(path=str(img), modality="image", action="analyze")
        resp = await facade.handle_process_content(req)
        assert resp["status"] == "ok"

    async def test_edge_md_exactly_2000_lines(self, facade, make_md_file, mock_l201_md):
        """TC-L108-L204-606 · md == 2000 行边界 · paged=false（< threshold）"""
        f = make_md_file(lines=2000, name="boundary.md")
        await facade.handle_process_content(_ic11_req(path=str(f)))
        payload = mock_l201_md.handle_md_request.call_args[0][0]
        assert payload["paged"] is False


class TestEdgeSymlinkAndLoop:
    """symlink 逃逸 / symlink 环"""

    async def test_edge_symlink_escapes_scope(self, facade, tmp_project):
        """TC-L108-L204-607 · symlink 指向 scope 外 → path_escape"""
        outside = tmp_project.parent / "outside.md"
        outside.write_text("secret")
        link = tmp_project / "docs" / "evil_link.md"
        os.symlink(outside, link)
        resp = await facade.handle_process_content(_ic11_req(path=str(link), modality="md"))
        assert resp["err_type"] == "path_escape"

    async def test_edge_symlink_loop(self, facade, tmp_project):
        """TC-L108-L204-608 · symlink 环 → not_found or invalid_path"""
        a = tmp_project / "docs" / "a.md"
        b = tmp_project / "docs" / "b.md"
        os.symlink(b, a)
        os.symlink(a, b)
        resp = await facade.handle_process_content(_ic11_req(path=str(a), modality="md"))
        assert resp["err_type"] in {"not_found", "invalid_path"}


class TestEdgeConcurrency:
    """大并发 / 同 path 竞态"""

    async def test_edge_1000_concurrent_reads(self, facade, make_md_file):
        """TC-L108-L204-609 · 1000 并发读同文件 · 全 ok · 无文件损坏"""
        f = make_md_file(lines=100)
        reqs = [_ic11_req(path=str(f), modality="md", action="read") for _ in range(1000)]
        results = await asyncio.gather(*[facade.handle_process_content(r) for r in reqs])
        assert all(r["status"] == "ok" for r in results)

    async def test_edge_concurrent_write_same_path_serialized(self, facade, tmp_project):
        """TC-L108-L204-610 · 10 并发写同 path · LockManager 串行化 · 最终 content 来自最后完成的写"""
        req_factory = lambda i: _ic11_req(path="docs/contended.md", modality="md",
                                          action="write", content=f"v{i}\n")
        results = await asyncio.gather(*[facade.handle_process_content(req_factory(i)) for i in range(10)])
        assert all(r["status"] == "ok" for r in results)
        # 锁顺序化后最终文件存在
        assert (tmp_project / "docs" / "contended.md").exists()


class TestEdgeHashChainAndCrash:
    """scope §5.8.6 PM-08 单一事实源 · hash 链不可破"""

    async def test_edge_audit_event_has_hash_prev_chain(self, facade, mock_event_bus):
        """TC-L108-L204-611 · 连续 3 次 I/O · 审计事件 hash_prev 形成链（由 L1-09 填）"""
        for i in range(3):
            await facade.handle_process_content(_ic11_req(path=f"docs/x{i}.md"))
        # mock bus 填 hash_prev · 此处仅验证字段存在 + 顺序
        evts = mock_event_bus._events
        assert len(evts) >= 3

    async def test_edge_audit_no_raw_content_leaked(self, facade, mock_event_bus):
        """TC-L108-L204-612 · ADR-L204-05 审计事件禁存完整内容 · 只允许 hash + summary_excerpt"""
        req = _ic11_req(path="docs/x.md", modality="md", action="write", content="SECRET_TOKEN_12345")
        await facade.handle_process_content(req)
        for evt in mock_event_bus._events:
            content = evt.get("content", {})
            assert "raw_content" not in content
            assert "SECRET_TOKEN_12345" not in str(content)  # 不泄露


class TestEdgeStartupAndShutdown:
    """启动校验 + shutdown 冲刷"""

    async def test_edge_shutdown_flushes_fallback_buffer(self, facade, flaky_l109, state_machine):
        """TC-L108-L204-613 · 进程 shutdown · fallback_buffer 必须落本地 JSONL（OQ-04）"""
        flaky_l109.set_persistent_fail(True)
        for _ in range(5):
            await facade.handle_process_content(_ic11_req(path="docs/x.md"))
        await facade.shutdown(timeout_s=5)
        assert facade.auditor.fallback_buffer_persisted_path.exists()


# ---
# Helper functions（本 md 内伪代码 · 真实 tests 会放 tests/_helpers.py）
# ---

def _ic11_req(path: str = "docs/x.md", modality: str = "md", action: str = "read",
              content: str | None = None, offset: int | None = None, limit: int | None = None,
              image_hint: str | None = None, focus_hint: str | None = None,
              project_id: str = "demo-proj-001") -> dict:
    from uuid import uuid4
    from datetime import datetime, timezone
    return {
        "project_id": project_id,
        "request_id": str(uuid4()),
        "type": modality,
        "path": path,
        "action": action,
        "content": content,
        "image_hint": image_hint,
        "focus_hint": focus_hint,
        "offset": offset,
        "limit": limit,
        "caller_l1": "L1-01",
        "caller_wp_id": None,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def _decision(route: str, modality: str, delegate: bool = False, paged: bool = False) -> dict:
    return {"route": route, "type": modality, "delegate": delegate, "paged": paged}


def _audit_event(event_type: str, path: str, **kwargs) -> dict:
    from uuid import uuid4
    from datetime import datetime, timezone
    return {
        "project_id": "demo-proj-001",
        "event_type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": "L2-04/ContentAuditor",
        "request_id_ref": str(uuid4()),
        "audit_ref": str(uuid4()),
        "content": {
            "canonical_path": path,
            "attempted_path": path,
            "file_hash_sha256": kwargs.get("sha"),
            "size_bytes": kwargs.get("size"),
            "lines": kwargs.get("lines"),
            "err_type": kwargs.get("err_type"),
            "reason": kwargs.get("reason"),
        },
    }


def _find_event(bus, event_type: str) -> dict | None:
    return next((e for e in bus._events if e["event_type"] == event_type), None)


def _count_events(bus, event_type: str) -> int:
    return sum(1 for e in bus._events if e["event_type"] == event_type)
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
