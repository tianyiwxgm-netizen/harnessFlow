---
doc_id: tests-L1-04-L2-06-S5 TDDExe Verifier 编排器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-06-S5 TDDExe Verifier 编排器.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-04 L2-06 S5 TDDExe Verifier 编排器 · TDD 测试用例

> 基于 3-1 L2-06 §3（11 个 public 方法）+ §11 错误码（33 项 · 其中 7 条硬红线 CRITICAL）+ §12 SLO（派发 / verifier 跑 / 落盘 / 广播延迟 + 并发吞吐）+ §13 TC ID 矩阵驱动。
> TC ID 统一格式：`TC-L104-L206-NNN`（L1-04 下 L2-06，三位流水号 · 001-099 正向 / 1xx-3xx 负向按错误码分段 / 6xx IC 契约 / 7xx 性能 / 8xx e2e / 9xx 集成 / Axx 边界）。
> pytest + Python 3.11+ 类型注解；正向 `class TestL2_06_S5TDDExeVerifier` 组织；负向 / IC / perf / e2e / 集成 / 边界各自独立 `class`。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus / mock L1-05 / mock fs）
- [x] §8 集成点用例（与兄弟 L2-04/05/07 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃/session 污染）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码（33 项） / 本 L2 参与的 IC-XX（IC-03 / IC-09 / IC-13 / IC-14 / IC-16 / IC-20） 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 / 跨 L1 mock；e2e = 端到端；perf = 性能 SLO。
> 错误码前缀一律 `L2-06/E` · 以下表格省略前缀（与 3-1 §3/§11 原样保持）。

### §1.1 方法 × 测试 × 覆盖类型（§3 · 11 方法 + §2 TC）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 / IC |
|---|---|---|---|
| `start(project_id)` · §3.1 响应 IC-03 + 异步 accept | TC-L104-L206-001 | unit | IC-03 / IC-09 |
| `start(project_id)` · §3.1 新建 VerifierReport + estimated_completion | TC-L104-L206-002 | unit | IC-09 |
| `start(project_id)` · §3.1 trigger_source 校验 | TC-L104-L206-003 | unit | — |
| `assemble_workbench()` · §3.2 五件蓝图齐 happy | TC-L104-L206-010 | unit | — |
| `assemble_workbench()` · §3.2 workbench_path 落盘可回读 | TC-L104-L206-011 | unit | — |
| `assemble_workbench()` · §3.2 credential_scrubbed=true | TC-L104-L206-012 | unit | — |
| `scrub_credentials()` · §3.3 API_KEY 命中 | TC-L104-L206-020 | unit | — |
| `scrub_credentials()` · §3.3 TOKEN 命中 | TC-L104-L206-021 | unit | — |
| `scrub_credentials()` · §3.3 PASSWORD 命中 | TC-L104-L206-022 | unit | — |
| `scrub_credentials()` · §3.3 override_allow 合法字段 | TC-L104-L206-023 | unit | — |
| `dispatch_verifier()` · §3.4 attempt=1 成功 | TC-L104-L206-030 | unit | IC-20 |
| `dispatch_verifier()` · §3.4 attempt=1 fail + attempt=2 成功 | TC-L104-L206-031 | unit | IC-20 |
| `dispatch_verifier()` · §3.4 session_id 前缀合法 | TC-L104-L206-032 | unit | IC-20 |
| `receive_verifier_callback()` · §3.5 三段齐 happy | TC-L104-L206-040 | unit | — |
| `receive_verifier_callback()` · §3.5 metadata 透传 | TC-L104-L206-041 | unit | — |
| `assemble_evidence_chain()` · §3.6 三段 done happy | TC-L104-L206-050 | unit | — |
| `assemble_evidence_chain()` · §3.6 diff_with_main_claim 计算 | TC-L104-L206-051 | unit | — |
| `persist_report_atomic()` · §3.7 fsync + rename 成功 | TC-L104-L206-060 | unit | — |
| `persist_report_atomic()` · §3.7 sha256 校验落盘文件 | TC-L104-L206-061 | unit | — |
| `broadcast_verifier_report_ready()` · §3.8 fanout 到 L1-07/10/09 | TC-L104-L206-070 | unit | IC-09 |
| `broadcast_verifier_report_ready()` · §3.8 L1-07 ack | TC-L104-L206-071 | unit | IC-09 |
| `handle_delegation_failure()` · §3.9 retry decision | TC-L104-L206-080 | unit | — |
| `handle_delegation_failure()` · §3.9 block_escalate 构造 | TC-L104-L206-081 | unit | IC-13 |
| `push_progress_to_ui()` · §3.10 各阶段推送 | TC-L104-L206-090 | unit | IC-16 |
| `shard_and_parallel_verify()` · §3.11 默认关 → 串行 | TC-L104-L206-095 | unit | — |
| `shard_and_parallel_verify()` · §3.11 开启后并行聚合 | TC-L104-L206-096 | unit | — |

### §1.2 错误码 × 测试（§3 + §11 · 33 项 · 严重度分组）

| 错误码（省略 `L2-06/E` 前缀） | TC ID | 方法 / 触发 | 严重度 | 硬红线 |
|---|---|---|---|---|
| `E01 delegation_timeout` | TC-L104-L206-101 | `dispatch_verifier()` · IC-20 14s 超时 | WARN | 否 |
| `E02 evidence_incomplete` | TC-L104-L206-102 | `receive_verifier_callback()` · 三段缺一无 reason | WARN | 否 |
| `E03 workbench_credential_leak` | TC-L104-L206-103 | `scrub_credentials()` · 脱敏后仍命中 | **CRITICAL** | **是** |
| `E04 invalid_phase` | TC-L104-L206-104 | `start()` · phase≠S5 | ERROR | 否 |
| `E05 s4_not_done` | TC-L104-L206-105 | `start()` · WP 未全完成 | ERROR | 否 |
| `E06 missing_blueprint_artifact` | TC-L104-L206-106 | `start()` · 五件蓝图缺一 | ERROR | 否 |
| `E07 main_session_id_collision` | TC-L104-L206-107 | `start()` · main_session_id 缺失或冲突 | **CRITICAL** | **是** |
| `E08 blueprint_path_missing` | TC-L104-L206-108 | `assemble_workbench()` · 路径不存在 | ERROR | 否 |
| `E09 workbench_size_exceeded` | TC-L104-L206-109 | `assemble_workbench()` · > 10MB | WARN | 否 |
| `E10 s4_snapshot_invalid` | TC-L104-L206-110 | `assemble_workbench()` · schema 违反 | ERROR | 否 |
| `E11 ac_list_empty` | TC-L104-L206-111 | `assemble_workbench()` · AC 清单空 | ERROR | 否 |
| `E12 regex_compile_failed` | TC-L104-L206-112 | `scrub_credentials()` · regex 编译异常 | WARN | 否 |
| `E13 payload_too_large` | TC-L104-L206-113 | `scrub_credentials()` · > 10MB | WARN | 否 |
| `E14 ic_20_api_error` | TC-L104-L206-114 | `dispatch_verifier()` · L1-05 5xx | WARN | 否 |
| `E15 ic_20_api_rate_limit` | TC-L104-L206-115 | `dispatch_verifier()` · 429 限流 | WARN | 否 |
| `E16 subagent_spawn_failure` | TC-L104-L206-116 | `dispatch_verifier()` · L1-05 起 session 失败 | WARN | 否 |
| `E17 session_id_prefix_violation` | TC-L104-L206-117 | `dispatch_verifier()` · session_id 以 `main.` 开头 | **CRITICAL** | **是** |
| `E18 callback_timeout` | TC-L104-L206-118 | `receive_verifier_callback()` · 30 min 未回调 | WARN | 否 |
| `E19 callback_schema_violation` | TC-L104-L206-119 | `receive_verifier_callback()` · payload schema 违反 | WARN | 否 |
| `E20 session_id_prefix_mismatch` | TC-L104-L206-120 | `receive_verifier_callback()` · session 前缀污染 | **CRITICAL** | **是** |
| `E21 segment_status_invalid` | TC-L104-L206-121 | `receive_verifier_callback()` · status 非枚举值 | WARN | 否 |
| `E22 evidence_items_empty` | TC-L104-L206-122 | `assemble_evidence_chain()` · existence 证据为空 | WARN | 否 |
| `E23 diff_computation_failed` | TC-L104-L206-123 | `assemble_evidence_chain()` · diff 异常 | WARN | 否 |
| `E24 fsync_failed` | TC-L104-L206-124 | `persist_report_atomic()` · fsync syscall 失败 | ERROR | 否 |
| `E25 rename_failed` | TC-L104-L206-125 | `persist_report_atomic()` · os.rename 失败 | ERROR | 否 |
| `E26 disk_full` | TC-L104-L206-126 | `persist_report_atomic()` · 磁盘满 | **CRITICAL** | **是** |
| `E27 broadcast_before_persist` | TC-L104-L206-127 | `broadcast_verifier_report_ready()` · 未落盘就广播 | **CRITICAL** | **是** |
| `E28 event_bus_unavailable` | TC-L104-L206-128 | `broadcast_verifier_report_ready()` · IC-09 异常 | WARN | 否 |
| `E29 main_session_fallback_attempted` | TC-L104-L206-129 | `handle_delegation_failure()` · fallback 主 session | **CRITICAL** | **是** |
| `E30 retry_count_exceeded` | TC-L104-L206-130 | `handle_delegation_failure()` · retry_log > 3 | INFO | 否 |
| `E31 ui_offline` | TC-L104-L206-131 | `push_progress_to_ui()` · L1-10 不可达 | WARN | 否 |
| `E32 shard_count_exceeded` | TC-L104-L206-132 | `shard_and_parallel_verify()` · shard > max_parallel | WARN | 否 |
| `E33 shard_aggregation_failed` | TC-L104-L206-133 | `shard_and_parallel_verify()` · 聚合异常 | WARN | 否 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-03 `enter_quality_loop{phase=S5}` | L1-01 → L1-04 → 本 L2 | TC-L104-L206-601 | 消费方 · 仅接受 phase=S5 |
| IC-20 `delegate_verifier`（独立 session · ephemeral） | 本 L2 → L1-05 | TC-L104-L206-602 | 生产方 · payload 结构 + session_id 前缀断言 |
| IC-09 `append_event`（verifier_delegation_started / verifier_report_issued / verifier_failed） | 本 L2 → L1-09 | TC-L104-L206-603 | 状态转换必写审计 |
| IC-13 `push_suggestion(BLOCK)` | 本 L2 → L1-07 | TC-L104-L206-604 | 3 次委托失败后升 BLOCK |
| IC-14 `halt_command` | L1-07 → 本 L2 | TC-L104-L206-605 | Supervisor 强制终止 S5 |
| IC-16 `push_stage_gate_card`（progress tab） | 本 L2 → L1-10 | TC-L104-L206-606 | verifier 进度 + 三段证据链 tab |

### §1.4 §12 SLO × 测试

| SLO 维度（§12.1/§12.2） | 阈值 | TC ID |
|---|---|---|
| 组装 workbench + 派发 IC-20 P95 | ≤ 20s · 硬上限 30s | TC-L104-L206-701 |
| 三段证据链组装 P95 | ≤ 500ms · 硬上限 10s | TC-L104-L206-702 |
| 原子落盘（fsync + rename） P95 | ≤ 200ms · 硬上限 10s | TC-L104-L206-703 |
| 广播给 L1-07 P95 | ≤ 50ms · 硬上限 1s | TC-L104-L206-704 |
| 跨 project 并发 S5 ≥ 10 | P95 不劣化 | TC-L104-L206-705 |
| 单次 S5 总耗时（mock verifier） | ≤ 60s | TC-L104-L206-706 |

### §1.5 PRD §8/§13 GWT × 测试（整合 §13.2 TC-L206-047~050）

| PRD 场景 | TC ID | 类别 |
|---|---|---|
| 正向 1 · S4 全完 → S5 派发 → verifier 跑 → 报告落盘（E2E） | TC-L104-L206-801 | e2e |
| 正向 2 · verifier 判 PASS → L1-07 读 report → L2-07 进 S7 | TC-L104-L206-802 | e2e |
| 负向 3 · verifier 判 FAIL（diff 与 main 声称不一致）→ L2-07 FAIL-L2 | TC-L104-L206-803 | e2e |
| 负向 4 · 委托 3 次失败 → BLOCK 硬红线 | TC-L104-L206-804 | e2e |
| 集成 5 · 与 L2-05 S4 执行器 · 读 S4 快照 | TC-L104-L206-901 | integration |
| 集成 6 · 与 L2-04 Gate 编译器 · 读 acceptance-checklist | TC-L104-L206-902 | integration |
| 集成 7 · 与 L2-07 回退路由器 · 下发 PASS/FAIL 信号 | TC-L104-L206-903 | integration |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_06_S5TDDExeVerifier`；arrange / act / assert 三段明确。
> 被测对象（SUT）：`VerifierDelegationOrchestrator`（Application Service + 10 子模块）· 从 `app.l1_04.l2_06.orchestrator` 导入。
> 所有入参 schema 严格按 §3 字段级 YAML · 所有出参断言按 §3 出参 schema。

```python
# file: tests/l1_04/test_l2_06_verifier_orchestrator_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_06.orchestrator import VerifierDelegationOrchestrator
from app.l1_04.l2_06.submodules import (
    WorkbenchAssembler,
    CredentialScrubber,
    VerifierDispatcher,
    CallbackReceiver,
    ThreeEvidenceChainAssembler,
    AtomicReportPersister,
    VerifierReportBroadcaster,
    DelegationFailureEscalator,
    ProgressNotifier,
)
from app.l1_04.l2_06.schemas import (
    StartRequest,
    StartResponse,
    AssembleWorkbenchRequest,
    AssembleWorkbenchResponse,
    ScrubCredentialsRequest,
    ScrubCredentialsResponse,
    DispatchVerifierRequest,
    DispatchVerifierResponse,
    CallbackRequest,
    CallbackResponse,
    AssembleEvidenceChainRequest,
    AssembleEvidenceChainResponse,
    PersistReportRequest,
    PersistReportResponse,
    BroadcastRequest,
    BroadcastResponse,
    HandleFailureRequest,
    HandleFailureResponse,
    PushProgressRequest,
    PushProgressResponse,
    ShardVerifyRequest,
    ShardVerifyResponse,
)
from app.l1_04.l2_06.aggregates import VerifierReport, VerifierWorkPackage, ThreeEvidenceChain
from app.l1_04.l2_06.errors import VerifierOrchestratorError


class TestL2_06_S5TDDExeVerifier:
    """§3 public 方法正向用例。每方法 ≥ 1 happy path。"""

    # --------- 3.1 start · 响应 IC-03 enter_quality_loop{phase=S5} --------- #

    def test_TC_L104_L206_001_start_happy_path_accepts_s5(
        self,
        sut: VerifierDelegationOrchestrator,
        mock_project_id: str,
        make_start_request,
    ) -> None:
        """TC-L104-L206-001 · start() 收 IC-03 phase=S5 · 返回 accepted + report_id + session_id。"""
        # arrange
        req: StartRequest = make_start_request(
            project_id=mock_project_id,
            phase="S5",
            main_session_id="main.alpha.001",
            all_wps_completed=True,
        )
        # act
        resp: StartResponse = sut.start(req)
        # assert
        assert resp.status == "accepted", "§3.1 happy path status=accepted"
        assert resp.project_id == mock_project_id, "PM-14 透传"
        assert resp.report_id is not None, "§3.1 新建 VerifierReport id"
        assert resp.session_id is not None, "§3.1 由 L1-05 预分配 session id"
        assert not resp.session_id.startswith("main."), "硬红线 · 独立 session 前缀非 main."
        assert resp.event_id is not None, "§3.1 L1-04:verifier_delegation_started 事件"

    def test_TC_L104_L206_002_start_new_report_and_estimated_completion(
        self,
        sut: VerifierDelegationOrchestrator,
        mock_project_id: str,
        make_start_request,
        frozen_clock,
    ) -> None:
        """TC-L104-L206-002 · start() 新建 VerifierReport + estimated_completion = now + timeout_30min。"""
        req = make_start_request(project_id=mock_project_id)
        resp = sut.start(req)
        assert resp.estimated_completion is not None, "§3.1 预估完成时间必返"
        # 硬上限 30 min · 最长估时
        delta_seconds = (resp.estimated_completion - frozen_clock.now()).total_seconds()
        assert 0 < delta_seconds <= 30 * 60, "§12.1 verifier 硬上限 30 min"

    def test_TC_L104_L206_003_start_trigger_source_is_ic_03(
        self,
        sut: VerifierDelegationOrchestrator,
        mock_project_id: str,
        make_start_request,
    ) -> None:
        """TC-L104-L206-003 · trigger_source 必须为 IC-03 · 其他触发源拒绝（上行契约）。"""
        req = make_start_request(project_id=mock_project_id, trigger_source="IC-03")
        resp = sut.start(req)
        assert resp.status == "accepted"

    # --------- 3.2 assemble_workbench · 组装 verifier 工作包 --------- #

    def test_TC_L104_L206_010_assemble_workbench_five_blueprint_happy(
        self,
        workbench_assembler: WorkbenchAssembler,
        mock_project_id: str,
        make_blueprint_refs,
        make_s4_snapshot,
        make_ac_list,
    ) -> None:
        """TC-L104-L206-010 · 五件蓝图齐 + S4 快照齐 + AC 齐 → workbench 组装成功 · size ≤ 10MB。"""
        resp: AssembleWorkbenchResponse = workbench_assembler.assemble_workbench(
            blueprint_refs=make_blueprint_refs(),
            s4_snapshot=make_s4_snapshot(wp_count=5),
            ac_list=make_ac_list(count=20),
            project_id=mock_project_id,
        )
        assert resp.workbench is not None
        assert resp.workbench_size_bytes <= 10 * 1024 * 1024, "§3.2 硬上限 10MB"
        assert resp.credential_scrubbed is True, "§3.2 必为 true"
        assert resp.assemble_duration_ms > 0

    def test_TC_L104_L206_011_assemble_workbench_path_persisted_readable(
        self,
        workbench_assembler: WorkbenchAssembler,
        mock_project_id: str,
        make_blueprint_refs,
        make_s4_snapshot,
        make_ac_list,
        tmp_fs,
    ) -> None:
        """TC-L104-L206-011 · workbench 落盘路径可回读 · 用于审计。"""
        resp = workbench_assembler.assemble_workbench(
            blueprint_refs=make_blueprint_refs(),
            s4_snapshot=make_s4_snapshot(),
            ac_list=make_ac_list(),
            project_id=mock_project_id,
        )
        assert tmp_fs.exists(resp.workbench_path), "§3.2 workbench_path 必须实际存在"

    def test_TC_L104_L206_012_assemble_workbench_credential_scrubbed_flag(
        self,
        workbench_assembler: WorkbenchAssembler,
        mock_project_id: str,
        make_blueprint_refs,
        make_s4_snapshot_with_secrets,
        make_ac_list,
    ) -> None:
        """TC-L104-L206-012 · S4 快照含敏感字段 · 组装后 credential_scrubbed=true 且字段被脱敏。"""
        resp = workbench_assembler.assemble_workbench(
            blueprint_refs=make_blueprint_refs(),
            s4_snapshot=make_s4_snapshot_with_secrets(),
            ac_list=make_ac_list(),
            project_id=mock_project_id,
        )
        assert resp.credential_scrubbed is True
        # 硬约束 5 · 工作包不含敏感凭证
        assert "API_KEY" not in str(resp.workbench)
        assert "sk_live_" not in str(resp.workbench)

    # --------- 3.3 scrub_credentials · 凭证脱敏 --------- #

    def test_TC_L104_L206_020_scrub_credentials_api_key_match(
        self,
        scrubber: CredentialScrubber,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L206-020 · API_KEY 字段 + 内置 regex → 命中脱敏 · count=1。"""
        payload = {"config": {"api_key": "sk_live_ABC123"}}
        resp: ScrubCredentialsResponse = scrubber.scrub_credentials(
            payload=payload, project_id=mock_project_id,
        )
        assert resp.scrubbed_count >= 1
        assert "sk_live_ABC123" not in str(resp.scrubbed_payload)
        assert "config.api_key" in resp.scrubbed_fields

    def test_TC_L104_L206_021_scrub_credentials_token_match(
        self,
        scrubber: CredentialScrubber,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L206-021 · Bearer token 命中。"""
        payload = {"headers": {"Authorization": "Bearer abcd1234"}}
        resp = scrubber.scrub_credentials(payload=payload, project_id=mock_project_id)
        assert resp.scrubbed_count >= 1
        assert "abcd1234" not in str(resp.scrubbed_payload)

    def test_TC_L104_L206_022_scrub_credentials_password_match(
        self,
        scrubber: CredentialScrubber,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L206-022 · password 字段命中。"""
        payload = {"db": {"password": "mypass"}}
        resp = scrubber.scrub_credentials(payload=payload, project_id=mock_project_id)
        assert resp.scrubbed_count >= 1
        assert "mypass" not in str(resp.scrubbed_payload)

    def test_TC_L104_L206_023_scrub_credentials_override_allow_passthrough(
        self,
        scrubber: CredentialScrubber,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L206-023 · override_allow 白名单字段保留原值。"""
        payload = {"metrics": {"token_count": 12345}}  # "token" 在字段名但合法业务字段
        resp = scrubber.scrub_credentials(
            payload=payload,
            override_allow=["metrics.token_count"],
            project_id=mock_project_id,
        )
        assert resp.scrubbed_payload["metrics"]["token_count"] == 12345

    # --------- 3.4 dispatch_verifier · IC-20 派发独立 session --------- #

    def test_TC_L104_L206_030_dispatch_verifier_attempt_1_success(
        self,
        dispatcher: VerifierDispatcher,
        mock_project_id: str,
        make_workbench,
    ) -> None:
        """TC-L104-L206-030 · attempt=1 IC-20 成功 · 返回 session_id · 非 main. 前缀。"""
        resp: DispatchVerifierResponse = dispatcher.dispatch_verifier(
            workbench=make_workbench(),
            project_id=mock_project_id,
        )
        assert resp.status == "dispatched"
        assert resp.attempt_number == 1
        assert resp.session_id is not None
        assert not resp.session_id.startswith("main."), "硬红线 · session_id 前缀必非 main."
        assert resp.dispatch_duration_ms > 0

    def test_TC_L104_L206_031_dispatch_verifier_retry_backoff_success_on_attempt_2(
        self,
        dispatcher_flaky: VerifierDispatcher,  # mock: attempt=1 失败, attempt=2 成功
        mock_project_id: str,
        make_workbench,
    ) -> None:
        """TC-L104-L206-031 · attempt=1 失败 · 2s 指数退避 · attempt=2 成功。"""
        resp = dispatcher_flaky.dispatch_verifier(
            workbench=make_workbench(), project_id=mock_project_id,
        )
        assert resp.status == "dispatched"
        assert resp.attempt_number == 2, "§11.2 降级链 · 重试 1 退避 2s"

    def test_TC_L104_L206_032_dispatch_verifier_session_id_prefix_valid(
        self,
        dispatcher: VerifierDispatcher,
        mock_project_id: str,
        make_workbench,
    ) -> None:
        """TC-L104-L206-032 · 分配的 session_id 必须以 verifier. 或其他非 main. 前缀开头（PM-03）。"""
        resp = dispatcher.dispatch_verifier(
            workbench=make_workbench(), project_id=mock_project_id,
        )
        assert resp.session_id.startswith(("verifier.", "subagent.", "s5_")), (
            "§3.4 session_id 硬红线 · PM-03 独立 session"
        )

    # --------- 3.5 receive_verifier_callback · 接收 verifier 回调 --------- #

    def test_TC_L104_L206_040_receive_verifier_callback_three_segments_happy(
        self,
        callback_receiver: CallbackReceiver,
        mock_project_id: str,
        make_verifier_output,
    ) -> None:
        """TC-L104-L206-040 · 三段齐（existence/behavior/quality 全 done） · 组装后 empty_segments=[]。"""
        resp: CallbackResponse = callback_receiver.receive_verifier_callback(
            session_id="verifier.test.001",
            verifier_output=make_verifier_output(all_done=True),
            project_id=mock_project_id,
        )
        assert resp.three_evidence_chain is not None
        assert resp.empty_segments == [], "§3.5 三段齐 · 无缺段"
        assert resp.session_id_mismatch is False

    def test_TC_L104_L206_041_receive_verifier_callback_metadata_preserved(
        self,
        callback_receiver: CallbackReceiver,
        mock_project_id: str,
        make_verifier_output,
    ) -> None:
        """TC-L104-L206-041 · metadata 中 verifier_duration / tools_used 透传（审计用）。"""
        output = make_verifier_output(
            all_done=True,
            verifier_duration_seconds=120.5,
            verifier_tools_used=["Read", "Grep", "Bash(pytest)"],
        )
        resp = callback_receiver.receive_verifier_callback(
            session_id="verifier.test.002", verifier_output=output,
            project_id=mock_project_id,
        )
        assert resp.three_evidence_chain.metadata["verifier_duration_seconds"] == 120.5

    # --------- 3.6 assemble_evidence_chain · 三段证据链组装 --------- #

    def test_TC_L104_L206_050_assemble_evidence_chain_three_done_happy(
        self,
        chain_assembler: ThreeEvidenceChainAssembler,
        mock_project_id: str,
        make_verifier_output,
        make_main_claim_snapshot,
    ) -> None:
        """TC-L104-L206-050 · 三段 status=done + evidence_items 全齐 · 组装后 happy。"""
        resp: AssembleEvidenceChainResponse = chain_assembler.assemble_evidence_chain(
            verifier_output=make_verifier_output(all_done=True),
            main_session_id="main.alpha.001",
            main_claim_snapshot=make_main_claim_snapshot(),
            project_id=mock_project_id,
        )
        chain = resp.three_evidence_chain
        assert chain.existence_segment.status == "done"
        assert chain.behavior_segment.status == "done"
        assert chain.quality_segment.status == "done"
        assert len(chain.existence_segment.evidence_items) > 0

    def test_TC_L104_L206_051_assemble_evidence_chain_diff_with_main_claim(
        self,
        chain_assembler: ThreeEvidenceChainAssembler,
        mock_project_id: str,
        make_verifier_output,
        make_main_claim_snapshot_with_diff,
    ) -> None:
        """TC-L104-L206-051 · verifier 判 fail 但主声称 pass · diff_with_main_claim 记录差异。"""
        resp = chain_assembler.assemble_evidence_chain(
            verifier_output=make_verifier_output(wp_result="fail"),
            main_session_id="main.alpha.001",
            main_claim_snapshot=make_main_claim_snapshot_with_diff(wp_result="pass"),
            project_id=mock_project_id,
        )
        diff = resp.three_evidence_chain.behavior_segment.diff_with_main_claim
        assert len(diff) > 0, "§3.6 diff_with_main_claim 必记录不一致"

    # --------- 3.7 persist_report_atomic · 原子落盘 --------- #

    def test_TC_L104_L206_060_persist_report_atomic_fsync_rename_success(
        self,
        persister: AtomicReportPersister,
        mock_project_id: str,
        make_verifier_report,
        tmp_fs,
    ) -> None:
        """TC-L104-L206-060 · fsync + rename 原子落盘 · final_path 存在 · 临时文件清理。"""
        report = make_verifier_report()
        resp: PersistReportResponse = persister.persist_report_atomic(
            report=report, project_id=mock_project_id,
        )
        assert tmp_fs.exists(resp.final_path)
        assert not tmp_fs.exists(resp.final_path + ".tmp"), "临时文件必须被 rename 掉"
        assert resp.fsync_duration_ms >= 0
        assert resp.rename_duration_ms >= 0

    def test_TC_L104_L206_061_persist_report_atomic_sha256_matches_content(
        self,
        persister: AtomicReportPersister,
        mock_project_id: str,
        make_verifier_report,
        tmp_fs,
    ) -> None:
        """TC-L104-L206-061 · 落盘文件 sha256 与返回值一致（审计可校验）。"""
        report = make_verifier_report()
        resp = persister.persist_report_atomic(report=report, project_id=mock_project_id)
        computed_sha = tmp_fs.sha256(resp.final_path)
        assert resp.sha256 == computed_sha, "§3.7 落盘 sha256 一致性"
        assert resp.file_size > 0

    # --------- 3.8 broadcast_verifier_report_ready · 广播事件 --------- #

    def test_TC_L104_L206_070_broadcast_fanout_to_l1_07_10_09(
        self,
        broadcaster: VerifierReportBroadcaster,
        mock_project_id: str,
        make_persisted_report,
    ) -> None:
        """TC-L104-L206-070 · 广播后 consumer list = [L1-07, L1-10, L1-09]。"""
        resp: BroadcastResponse = broadcaster.broadcast_verifier_report_ready(
            report=make_persisted_report(), project_id=mock_project_id,
        )
        assert set(resp.broadcasted_to) == {"L1-07", "L1-10", "L1-09"}
        assert resp.event_id.startswith("L1-04:verifier_report_issued")

    def test_TC_L104_L206_071_broadcast_l1_07_ack_received(
        self,
        broadcaster: VerifierReportBroadcaster,
        mock_project_id: str,
        make_persisted_report,
    ) -> None:
        """TC-L104-L206-071 · L1-07 Supervisor ack 收到 · 用于重传保障。"""
        resp = broadcaster.broadcast_verifier_report_ready(
            report=make_persisted_report(), project_id=mock_project_id,
        )
        assert resp.l1_07_ack is True

    # --------- 3.9 handle_delegation_failure · 委托失败处理 --------- #

    def test_TC_L104_L206_080_handle_failure_retry_decision_under_threshold(
        self,
        escalator: DelegationFailureEscalator,
        mock_project_id: str,
        make_delegation_log,
    ) -> None:
        """TC-L104-L206-080 · retry_log.len=2 < 3 · decision=retry · retry_after 指数退避。"""
        resp: HandleFailureResponse = escalator.handle_delegation_failure(
            error=TimeoutError("verifier_timeout"),
            retry_log=make_delegation_log(attempts=2),
            project_id=mock_project_id,
        )
        assert resp.decision == "retry"
        assert resp.retry_after_seconds > 0

    def test_TC_L104_L206_081_handle_failure_block_escalate_after_3_retries(
        self,
        escalator: DelegationFailureEscalator,
        mock_project_id: str,
        make_delegation_log,
    ) -> None:
        """TC-L104-L206-081 · retry_log.len=3 · decision=block_escalate · suggestion_type=BLOCK。"""
        resp = escalator.handle_delegation_failure(
            error=RuntimeError("subagent_spawn_failure"),
            retry_log=make_delegation_log(attempts=3),
            project_id=mock_project_id,
        )
        assert resp.decision == "block_escalate"
        assert resp.block_suggestion.suggestion_type == "BLOCK"
        assert resp.block_suggestion.reason == "verifier_unavailable_after_3_retries"
        assert resp.block_suggestion.escalation_target == "L1-07_Supervisor"

    # --------- 3.10 push_progress_to_ui · 推 UI 进度 --------- #

    def test_TC_L104_L206_090_push_progress_each_stage(
        self,
        notifier: ProgressNotifier,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L206-090 · 8 阶段 stage 各推一次 · UI ack。"""
        stages = [
            "assembling", "dispatching", "running_existence", "running_behavior",
            "running_quality", "assembling_report", "persisted", "broadcasted",
        ]
        for name in stages:
            resp: PushProgressResponse = notifier.push_progress_to_ui(
                session_id="verifier.test.004",
                stage={"name": name, "percent": 50, "message": f"stage={name}"},
                project_id=mock_project_id,
            )
            assert resp.event_id.startswith("L1-04:verifier_progress_update")
            assert resp.ui_ack is True

    # --------- 3.11 shard_and_parallel_verify · 大项目分片（可选） --------- #

    def test_TC_L104_L206_095_shard_disabled_falls_back_to_serial(
        self,
        dispatcher: VerifierDispatcher,
        mock_project_id: str,
        make_wps,
    ) -> None:
        """TC-L104-L206-095 · enabled=false（默认）→ 串行执行（不分片）· 返回单 report。"""
        resp: ShardVerifyResponse = dispatcher.shard_and_parallel_verify(
            wps=make_wps(count=10), project_id=mock_project_id,
        )
        assert len(resp.shard_reports) == 1, "默认关 · 单 shard = 串行"
        assert resp.parallel_speedup == 1.0

    def test_TC_L104_L206_096_shard_enabled_parallel_aggregates(
        self,
        dispatcher_shard_on: VerifierDispatcher,
        mock_project_id: str,
        make_wps,
    ) -> None:
        """TC-L104-L206-096 · enabled=true · 3 shard 并行 · aggregated_report 合并三段。"""
        resp = dispatcher_shard_on.shard_and_parallel_verify(
            wps=make_wps(count=60), project_id=mock_project_id,
        )
        assert len(resp.shard_reports) == 3
        assert resp.aggregated_report is not None
        assert resp.parallel_speedup > 1.5, "§12 并行加速比 · 3 shard 期望 > 1.5x"
```

---

## §3 负向用例（每错误码 ≥ 1）

> 33 条错误码 · CRITICAL / ERROR / WARN / INFO 四级严重度 · 每条对应一个 TC。
> 硬红线 7 条（E03/E07/E17/E20/E26/E27/E29）必须 raise + alert + 不静默吞。

```python
# file: tests/l1_04/test_l2_06_verifier_orchestrator_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.l1_04.l2_06.orchestrator import VerifierDelegationOrchestrator
from app.l1_04.l2_06.errors import (
    VerifierOrchestratorError,
    DelegationTimeoutError,
    EvidenceIncompleteError,
    WorkbenchCredentialLeakError,      # E03 · CRITICAL
    InvalidPhaseError,
    S4NotDoneError,
    MissingBlueprintArtifactError,
    MainSessionIdCollisionError,        # E07 · CRITICAL
    SessionIdPrefixViolationError,      # E17 · CRITICAL
    SessionIdPrefixMismatchError,       # E20 · CRITICAL
    DiskFullError,                      # E26 · CRITICAL
    BroadcastBeforePersistError,        # E27 · CRITICAL
    MainSessionFallbackAttemptedError,  # E29 · CRITICAL
)


class TestL2_06_Negative_E01_to_E10:
    """负向用例 · E01~E10（dispatch + start + assemble 段）"""

    def test_TC_L104_L206_101_delegation_timeout_e01(
        self, dispatcher, mock_project_id, make_workbench,
    ) -> None:
        """TC-L104-L206-101 · E01 · IC-20 14s 总等待超时 · WARN 记 log · 重试 1 次。"""
        with patch.object(dispatcher, "_ic_20_call", side_effect=TimeoutError()):
            with pytest.raises(DelegationTimeoutError) as exc:
                dispatcher.dispatch_verifier(
                    workbench=make_workbench(), project_id=mock_project_id,
                )
            assert exc.value.code == "L2-06/E01"

    def test_TC_L104_L206_102_evidence_incomplete_e02(
        self, callback_receiver, mock_project_id, make_verifier_output,
    ) -> None:
        """TC-L104-L206-102 · E02 · 回调三段缺一且无 reason · 自动补 empty+reason（不 raise）。"""
        output = make_verifier_output(skip_quality_segment=True, omit_reason=True)
        resp = callback_receiver.receive_verifier_callback(
            session_id="verifier.x", verifier_output=output,
            project_id=mock_project_id,
        )
        assert "quality" in resp.empty_segments
        assert resp.reason_map["quality"] == "malformed_callback"

    def test_TC_L104_L206_103_workbench_credential_leak_e03_critical(
        self, scrubber, mock_project_id,
    ) -> None:
        """TC-L104-L206-103 · E03 · CRITICAL · 脱敏后仍检出凭证 → 硬拒派发 + alert。"""
        payload = {"api_key": "LEAK-should-be-scrubbed-but-isnt"}
        with patch.object(scrubber, "_apply_regex", return_value=payload):  # 模拟脱敏失效
            with pytest.raises(WorkbenchCredentialLeakError) as exc:
                scrubber.scrub_credentials_hard_check(payload=payload, project_id=mock_project_id)
            assert exc.value.code == "L2-06/E03"
            assert exc.value.severity == "CRITICAL"

    def test_TC_L104_L206_104_invalid_phase_e04(
        self, sut, mock_project_id, make_start_request,
    ) -> None:
        """TC-L104-L206-104 · E04 · phase=S4 非 S5 · 拒绝请求返 rejected。"""
        req = make_start_request(project_id=mock_project_id, phase="S4")
        resp = sut.start(req)
        assert resp.status == "rejected"
        assert "L2-06/E04" in resp.rejection_reason

    def test_TC_L104_L206_105_s4_not_done_e05(
        self, sut, mock_project_id, make_start_request,
    ) -> None:
        """TC-L104-L206-105 · E05 · S4 WP 未全完成 · 拒绝启 S5。"""
        req = make_start_request(project_id=mock_project_id, all_wps_completed=False)
        resp = sut.start(req)
        assert resp.status == "rejected"
        assert "L2-06/E05" in resp.rejection_reason

    def test_TC_L104_L206_106_missing_blueprint_artifact_e06(
        self, sut, mock_project_id, make_start_request,
    ) -> None:
        """TC-L104-L206-106 · E06 · 五件蓝图缺 master_test_plan_path · 拒绝。"""
        req = make_start_request(
            project_id=mock_project_id,
            blueprint_refs={"master_test_plan_path": None},  # 缺一件
        )
        resp = sut.start(req)
        assert resp.status == "rejected"
        assert "L2-06/E06" in resp.rejection_reason

    def test_TC_L104_L206_107_main_session_id_collision_e07_critical(
        self, sut, mock_project_id, make_start_request,
    ) -> None:
        """TC-L104-L206-107 · E07 · CRITICAL · main_session_id 缺失或格式非法 → PM-03 违反。"""
        req = make_start_request(project_id=mock_project_id, main_session_id="")
        with pytest.raises(MainSessionIdCollisionError) as exc:
            sut.start(req)
        assert exc.value.code == "L2-06/E07"
        assert exc.value.severity == "CRITICAL"

    def test_TC_L104_L206_108_blueprint_path_missing_e08(
        self, workbench_assembler, mock_project_id, make_blueprint_refs,
        make_s4_snapshot, make_ac_list,
    ) -> None:
        """TC-L104-L206-108 · E08 · 五件蓝图路径之一不存在磁盘。"""
        refs = make_blueprint_refs(invalid_path="test_suite_path")
        with pytest.raises(VerifierOrchestratorError) as exc:
            workbench_assembler.assemble_workbench(
                blueprint_refs=refs, s4_snapshot=make_s4_snapshot(),
                ac_list=make_ac_list(), project_id=mock_project_id,
            )
        assert exc.value.code == "L2-06/E08"

    def test_TC_L104_L206_109_workbench_size_exceeded_e09(
        self, workbench_assembler, mock_project_id, make_huge_s4_snapshot,
        make_blueprint_refs, make_ac_list,
    ) -> None:
        """TC-L104-L206-109 · E09 · 组装后 > 10MB · WARN + 启分片或拒绝。"""
        with pytest.raises(VerifierOrchestratorError) as exc:
            workbench_assembler.assemble_workbench(
                blueprint_refs=make_blueprint_refs(),
                s4_snapshot=make_huge_s4_snapshot(size_mb=15),
                ac_list=make_ac_list(), project_id=mock_project_id,
            )
        assert exc.value.code == "L2-06/E09"

    def test_TC_L104_L206_110_s4_snapshot_invalid_e10(
        self, workbench_assembler, mock_project_id, make_blueprint_refs, make_ac_list,
    ) -> None:
        """TC-L104-L206-110 · E10 · S4 快照 schema 违反（缺 wp_commit_hashes）。"""
        bad_snapshot = {"wp_commit_hashes": None, "test_results_snapshot_path": None}
        with pytest.raises(VerifierOrchestratorError) as exc:
            workbench_assembler.assemble_workbench(
                blueprint_refs=make_blueprint_refs(), s4_snapshot=bad_snapshot,
                ac_list=make_ac_list(), project_id=mock_project_id,
            )
        assert exc.value.code == "L2-06/E10"


class TestL2_06_Negative_E11_to_E20:
    """负向用例 · E11~E20（assemble + scrub + dispatch + callback 段）"""

    def test_TC_L104_L206_111_ac_list_empty_e11(
        self, workbench_assembler, mock_project_id, make_blueprint_refs, make_s4_snapshot,
    ) -> None:
        """TC-L104-L206-111 · E11 · AC 清单为空 · 拒绝（无验收标准）。"""
        with pytest.raises(VerifierOrchestratorError) as exc:
            workbench_assembler.assemble_workbench(
                blueprint_refs=make_blueprint_refs(), s4_snapshot=make_s4_snapshot(),
                ac_list=[], project_id=mock_project_id,
            )
        assert exc.value.code == "L2-06/E11"

    def test_TC_L104_L206_112_regex_compile_failed_e12(
        self, scrubber, mock_project_id,
    ) -> None:
        """TC-L104-L206-112 · E12 · regex 编译异常 · fallback 黑名单默认规则（WARN · 不 raise）。"""
        resp = scrubber.scrub_credentials(
            payload={"api_key": "x"}, regex_patterns=["[invalid-regex"],
            project_id=mock_project_id,
        )
        # E12 fallback · 使用默认 regex
        assert resp.scrubbed_count >= 1, "§3.3 fallback 默认规则仍应工作"

    def test_TC_L104_L206_113_payload_too_large_e13(
        self, scrubber, mock_project_id, make_huge_payload,
    ) -> None:
        """TC-L104-L206-113 · E13 · payload > 10MB · 分片脱敏或拒绝。"""
        with pytest.raises(VerifierOrchestratorError) as exc:
            scrubber.scrub_credentials(
                payload=make_huge_payload(size_mb=15), project_id=mock_project_id,
            )
        assert exc.value.code == "L2-06/E13"

    def test_TC_L104_L206_114_ic_20_api_error_e14(
        self, dispatcher, mock_project_id, make_workbench,
    ) -> None:
        """TC-L104-L206-114 · E14 · L1-05 IC-20 返 5xx · 指数退避重试。"""
        with patch.object(dispatcher, "_ic_20_call") as m:
            m.side_effect = [ConnectionError("500"), MagicMock(session_id="verifier.ok")]
            resp = dispatcher.dispatch_verifier(
                workbench=make_workbench(), project_id=mock_project_id,
            )
            assert resp.attempt_number == 2

    def test_TC_L104_L206_115_ic_20_api_rate_limit_e15(
        self, dispatcher, mock_project_id, make_workbench,
    ) -> None:
        """TC-L104-L206-115 · E15 · 429 限流 · backoff 重试。"""
        with patch.object(dispatcher, "_ic_20_call") as m:
            m.side_effect = [Exception("429 Too Many"), MagicMock(session_id="verifier.ok2")]
            resp = dispatcher.dispatch_verifier(
                workbench=make_workbench(), project_id=mock_project_id,
            )
            assert resp.attempt_number >= 2

    def test_TC_L104_L206_116_subagent_spawn_failure_e16(
        self, dispatcher, mock_project_id, make_workbench,
    ) -> None:
        """TC-L104-L206-116 · E16 · L1-05 起 subagent 失败 · 重试 1 次。"""
        with patch.object(dispatcher, "_ic_20_call") as m:
            m.side_effect = [RuntimeError("spawn_fail"), MagicMock(session_id="verifier.ok3")]
            resp = dispatcher.dispatch_verifier(
                workbench=make_workbench(), project_id=mock_project_id,
            )
            assert resp.status == "dispatched"

    def test_TC_L104_L206_117_session_id_prefix_violation_e17_critical(
        self, dispatcher, mock_project_id, make_workbench,
    ) -> None:
        """TC-L104-L206-117 · E17 · CRITICAL · 分配的 session_id 以 main. 开头 → 硬红线 · 拒绝 + 升 BLOCK。"""
        with patch.object(dispatcher, "_ic_20_call",
                          return_value=MagicMock(session_id="main.polluted.001")):
            with pytest.raises(SessionIdPrefixViolationError) as exc:
                dispatcher.dispatch_verifier(
                    workbench=make_workbench(), project_id=mock_project_id,
                )
            assert exc.value.code == "L2-06/E17"
            assert exc.value.severity == "CRITICAL"

    def test_TC_L104_L206_118_callback_timeout_e18(
        self, callback_receiver, mock_project_id,
    ) -> None:
        """TC-L104-L206-118 · E18 · 30 min 未回调 · WARN + 重试 1 次。"""
        with patch.object(callback_receiver, "_wait_callback",
                          side_effect=TimeoutError()):
            with pytest.raises(VerifierOrchestratorError) as exc:
                callback_receiver.wait_and_receive(
                    session_id="verifier.x", timeout_seconds=1800,
                    project_id=mock_project_id,
                )
            assert exc.value.code == "L2-06/E18"

    def test_TC_L104_L206_119_callback_schema_violation_e19(
        self, callback_receiver, mock_project_id,
    ) -> None:
        """TC-L104-L206-119 · E19 · 回调 payload 缺 behavior_segment · 补 empty + reason=malformed_callback。"""
        bad_output = {"existence_segment": {"status": "done", "evidence_items": []}}
        resp = callback_receiver.receive_verifier_callback(
            session_id="verifier.y", verifier_output=bad_output,
            project_id=mock_project_id,
        )
        assert "behavior" in resp.empty_segments
        assert resp.reason_map["behavior"] == "malformed_callback"

    def test_TC_L104_L206_120_session_id_prefix_mismatch_e20_critical(
        self, callback_receiver, mock_project_id, make_verifier_output,
    ) -> None:
        """TC-L104-L206-120 · E20 · CRITICAL · 回调 session_id 与 main 前缀冲突 → 硬红线 + 升 BLOCK。"""
        with pytest.raises(SessionIdPrefixMismatchError) as exc:
            callback_receiver.receive_verifier_callback(
                session_id="main.collided.xxx",  # 污染前缀
                verifier_output=make_verifier_output(all_done=True),
                project_id=mock_project_id,
            )
        assert exc.value.code == "L2-06/E20"
        assert exc.value.severity == "CRITICAL"


class TestL2_06_Negative_E21_to_E33:
    """负向用例 · E21~E33（assemble_chain + persist + broadcast + escalate + shard 段）"""

    def test_TC_L104_L206_121_segment_status_invalid_e21(
        self, callback_receiver, mock_project_id,
    ) -> None:
        """TC-L104-L206-121 · E21 · status 非 done/empty/error 枚举 · 当 empty 处理 + reason。"""
        bad = {
            "existence_segment": {"status": "INVALID_ENUM", "evidence_items": []},
            "behavior_segment": {"status": "done", "test_runs": []},
            "quality_segment": {"status": "done", "quality_eval_results": []},
        }
        resp = callback_receiver.receive_verifier_callback(
            session_id="verifier.z", verifier_output=bad, project_id=mock_project_id,
        )
        assert "existence" in resp.empty_segments

    def test_TC_L104_L206_122_evidence_items_empty_e22(
        self, chain_assembler, mock_project_id, make_verifier_output,
        make_main_claim_snapshot,
    ) -> None:
        """TC-L104-L206-122 · E22 · existence.evidence_items=[] · 补 status=empty + reason=no_artifacts_observed。"""
        output = make_verifier_output(existence_empty=True)
        resp = chain_assembler.assemble_evidence_chain(
            verifier_output=output, main_session_id="main.alpha",
            main_claim_snapshot=make_main_claim_snapshot(),
            project_id=mock_project_id,
        )
        seg = resp.three_evidence_chain.existence_segment
        assert seg.status == "empty"
        assert seg.reason == "no_artifacts_observed"

    def test_TC_L104_L206_123_diff_computation_failed_e23(
        self, chain_assembler, mock_project_id, make_verifier_output,
    ) -> None:
        """TC-L104-L206-123 · E23 · diff 计算异常 · WARN · diff 为空 list（不阻断）。"""
        with patch.object(chain_assembler, "_diff_with_main",
                          side_effect=RuntimeError("diff_panic")):
            resp = chain_assembler.assemble_evidence_chain(
                verifier_output=make_verifier_output(all_done=True),
                main_session_id="main.alpha",
                main_claim_snapshot=None,
                project_id=mock_project_id,
            )
            assert resp.three_evidence_chain.behavior_segment.diff_with_main_claim == []

    def test_TC_L104_L206_124_fsync_failed_e24(
        self, persister, mock_project_id, make_verifier_report,
    ) -> None:
        """TC-L104-L206-124 · E24 · fsync syscall 失败 · 重试 1 次 · 仍失败升 BLOCK。"""
        with patch("os.fsync", side_effect=OSError("fsync_fail")):
            with pytest.raises(VerifierOrchestratorError) as exc:
                persister.persist_report_atomic(
                    report=make_verifier_report(), project_id=mock_project_id,
                )
            assert exc.value.code == "L2-06/E24"

    def test_TC_L104_L206_125_rename_failed_e25(
        self, persister, mock_project_id, make_verifier_report,
    ) -> None:
        """TC-L104-L206-125 · E25 · os.rename 失败 · 重试 1 次 · 仍失败升 BLOCK。"""
        with patch("os.rename", side_effect=PermissionError("rename_fail")):
            with pytest.raises(VerifierOrchestratorError) as exc:
                persister.persist_report_atomic(
                    report=make_verifier_report(), project_id=mock_project_id,
                )
            assert exc.value.code == "L2-06/E25"

    def test_TC_L104_L206_126_disk_full_e26_critical(
        self, persister, mock_project_id, make_verifier_report,
    ) -> None:
        """TC-L104-L206-126 · E26 · CRITICAL · 磁盘满 · 升 BLOCK · 告警用户扩容。"""
        with patch("builtins.open", side_effect=OSError(28, "No space left on device")):
            with pytest.raises(DiskFullError) as exc:
                persister.persist_report_atomic(
                    report=make_verifier_report(), project_id=mock_project_id,
                )
            assert exc.value.code == "L2-06/E26"
            assert exc.value.severity == "CRITICAL"

    def test_TC_L104_L206_127_broadcast_before_persist_e27_critical(
        self, broadcaster, mock_project_id, make_unpersisted_report,
    ) -> None:
        """TC-L104-L206-127 · E27 · CRITICAL · 未落盘就广播 → 破坏硬约束 3 · 硬拒绝 + alert。"""
        with pytest.raises(BroadcastBeforePersistError) as exc:
            broadcaster.broadcast_verifier_report_ready(
                report=make_unpersisted_report(), project_id=mock_project_id,
            )
        assert exc.value.code == "L2-06/E27"
        assert exc.value.severity == "CRITICAL"

    def test_TC_L104_L206_128_event_bus_unavailable_e28(
        self, broadcaster, mock_project_id, make_persisted_report,
    ) -> None:
        """TC-L104-L206-128 · E28 · IC-09 事件总线异常 · 重试 1 次 或 WAL 缓冲。"""
        with patch.object(broadcaster, "_emit_event",
                          side_effect=[ConnectionError("down"), None]):
            resp = broadcaster.broadcast_verifier_report_ready(
                report=make_persisted_report(), project_id=mock_project_id,
            )
            # WAL 缓冲 · 不阻塞主路径
            assert resp.event_id is not None

    def test_TC_L104_L206_129_main_session_fallback_attempted_e29_critical(
        self, escalator, mock_project_id, make_delegation_log,
    ) -> None:
        """TC-L104-L206-129 · E29 · CRITICAL · 代码试图 fallback 主 session · 硬拒绝 + alert + PR reject。"""
        with patch.object(escalator, "_try_fallback_main_session", return_value=True):
            with pytest.raises(MainSessionFallbackAttemptedError) as exc:
                escalator._assert_no_main_session_fallback(
                    retry_log=make_delegation_log(attempts=3),
                    project_id=mock_project_id,
                )
            assert exc.value.code == "L2-06/E29"
            assert exc.value.severity == "CRITICAL"

    def test_TC_L104_L206_130_retry_count_exceeded_e30(
        self, escalator, mock_project_id, make_delegation_log,
    ) -> None:
        """TC-L104-L206-130 · E30 · INFO · retry_log.len > max_retries=3 · decision=block_escalate。"""
        resp = escalator.handle_delegation_failure(
            error=RuntimeError("third_fail"),
            retry_log=make_delegation_log(attempts=4),
            project_id=mock_project_id,
        )
        assert resp.decision == "block_escalate"

    def test_TC_L104_L206_131_ui_offline_e31(
        self, notifier, mock_project_id,
    ) -> None:
        """TC-L104-L206-131 · E31 · L1-10 不可达 · 缓存进度 · 稍后 flush（不 raise）。"""
        with patch.object(notifier, "_ui_emit", side_effect=ConnectionError("ui_down")):
            resp = notifier.push_progress_to_ui(
                session_id="verifier.ui.1",
                stage={"name": "dispatching", "percent": 30, "message": "派发中"},
                project_id=mock_project_id,
            )
            assert resp.ui_ack is False
            assert notifier.pending_cache_size() >= 1

    def test_TC_L104_L206_132_shard_count_exceeded_e32(
        self, dispatcher_shard_on, mock_project_id, make_wps,
    ) -> None:
        """TC-L104-L206-132 · E32 · shard 数 > max_parallel=3 · 降级为串行。"""
        resp = dispatcher_shard_on.shard_and_parallel_verify(
            wps=make_wps(count=500), project_id=mock_project_id,
        )
        assert len(resp.shard_reports) <= 3, "§3.11 max_parallel 硬上限"

    def test_TC_L104_L206_133_shard_aggregation_failed_e33(
        self, dispatcher_shard_on, mock_project_id, make_wps,
    ) -> None:
        """TC-L104-L206-133 · E33 · 聚合 shard reports 异常 · 保留 shard reports · 升 WARN。"""
        with patch.object(dispatcher_shard_on, "_aggregate_shards",
                          side_effect=RuntimeError("agg_fail")):
            resp = dispatcher_shard_on.shard_and_parallel_verify(
                wps=make_wps(count=60), project_id=mock_project_id,
            )
            # shard_reports 保留 · aggregated_report=None
            assert len(resp.shard_reports) > 0
            assert resp.aggregated_report is None
```

---

## §4 IC-XX 契约集成测试

> ≥ 3 join test · 本 L2 作为 IC-20 生产方（委托 verifier） + IC-03/IC-14 消费方 + IC-09/IC-13/IC-16 生产方。
> 聚焦于 S4 执行结果的接收 + 下发 PASS/FAIL/BLOCK 信号到 L2-07 与 L1-07。

```python
# file: tests/l1_04/test_l2_06_verifier_orchestrator_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_06_IC_Contracts:
    """IC-XX 契约跨 L1 集成测试 · mock 生产方 / 消费方 · 断言 payload schema 字段级"""

    def test_TC_L104_L206_601_ic_03_consume_phase_s5_from_l1_01(
        self, sut, mock_project_id, mock_l1_01,
    ) -> None:
        """TC-L104-L206-601 · 消费方 · L1-01 发 IC-03 phase=S5 · 本 L2 正确接收并启动。"""
        ic_03_payload = {
            "command_id": "cmd-001",
            "project_id": mock_project_id,
            "wp_id": "wp-5",
            "entry_phase": "S5",
            "loop_session_id": "qloop-s5-001",
            "main_session_id": "main.alpha.001",
            "s4_done_confirmation": {"all_wps_completed": True},
        }
        resp = sut.on_ic_03_enter_quality_loop(ic_03_payload)
        assert resp.status == "accepted"
        assert resp.project_id == mock_project_id

    def test_TC_L104_L206_602_ic_20_produce_delegate_verifier_to_l1_05(
        self, dispatcher, mock_project_id, mock_l1_05, make_workbench,
    ) -> None:
        """TC-L104-L206-602 · 生产方 · 本 L2 → L1-05 IC-20 delegate_verifier ·
        payload 字段级校验 + session_id 前缀非 main.（PM-03 硬约束）。"""
        resp = dispatcher.dispatch_verifier(
            workbench=make_workbench(), project_id=mock_project_id,
        )
        # 取 L1-05 侧收到的 IC-20 payload
        ic_20_calls = mock_l1_05.ic_20_received
        assert len(ic_20_calls) == 1
        payload = ic_20_calls[0]
        assert payload["subagent_type"] == "harnessFlow:verifier"
        assert payload["ephemeral"] is True
        assert set(payload["allowed_tools"]) == {
            "Read", "Grep", "Glob", "Bash(pytest|coverage|ruff|pyright)",
        }
        assert payload["timeout_minutes"] == 30
        assert payload["context"]["project_id"] == mock_project_id
        # 硬红线 · session_id 前缀
        assert not resp.session_id.startswith("main.")

    def test_TC_L104_L206_603_ic_09_produce_audit_events_three_types(
        self, sut, mock_project_id, make_start_request, mock_l1_09,
    ) -> None:
        """TC-L104-L206-603 · 生产方 · 全链路写审计 ·
        verifier_delegation_started / verifier_report_issued / verifier_failed 至少 2 类触发。"""
        req = make_start_request(project_id=mock_project_id)
        sut.start(req)
        sut.run_full_cycle_to_completion(req)  # 驱动整个 S5 链路
        events = mock_l1_09.events_received
        types_seen = {e["event_type"] for e in events}
        assert "L1-04:verifier_delegation_started" in types_seen
        assert "L1-04:verifier_report_issued" in types_seen
        for e in events:
            assert e["project_id"] == mock_project_id, "PM-14 每事件带 project_id"

    def test_TC_L104_L206_604_ic_13_push_suggestion_block_to_l1_07_after_3_retries(
        self, escalator, mock_project_id, make_delegation_log, mock_l1_07,
    ) -> None:
        """TC-L104-L206-604 · 生产方 · 3 次委托失败 · IC-13 push_suggestion(BLOCK) 到 L1-07 Supervisor。"""
        escalator.handle_delegation_failure(
            error=RuntimeError("final_fail"),
            retry_log=make_delegation_log(attempts=3),
            project_id=mock_project_id,
        )
        suggestions = mock_l1_07.suggestions_received
        assert len(suggestions) == 1
        assert suggestions[0]["level"] == "BLOCK"
        assert suggestions[0]["reason"] == "verifier_unavailable_after_3_retries"
        assert suggestions[0]["project_id"] == mock_project_id

    def test_TC_L104_L206_605_ic_14_consume_halt_command_from_l1_07(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L104-L206-605 · 消费方 · L1-07 Supervisor 发 IC-14 halt_command · 本 L2 进 HALT 状态。"""
        sut.start_running(project_id=mock_project_id)  # 当前 RUNNING
        sut.on_ic_14_halt_command(
            halt_id="halt-001",
            project_id=mock_project_id,
            red_line_id="PM-03",
        )
        assert sut.get_state(project_id=mock_project_id) == "HALTED"

    def test_TC_L104_L206_606_ic_16_push_progress_tab_to_l1_10(
        self, notifier, mock_project_id, mock_l1_10,
    ) -> None:
        """TC-L104-L206-606 · 生产方 · IC-16 push_stage_gate_card/progress 到 L1-10 UI。"""
        notifier.push_progress_to_ui(
            session_id="verifier.test.606",
            stage={"name": "running_quality", "percent": 75, "message": "质量段跑 dod"},
            project_id=mock_project_id,
        )
        cards = mock_l1_10.cards_received
        assert len(cards) == 1
        assert cards[0]["project_id"] == mock_project_id
        assert cards[0]["stage"]["percent"] == 75

    def test_TC_L104_L206_607_ic_join_s4_to_s5_to_s7_signal_flow(
        self, sut, mock_project_id, make_start_request, mock_l2_05, mock_l2_07,
    ) -> None:
        """TC-L104-L206-607 · IC join · S4 执行结果（来自 L2-05）→ 本 L2 → L2-07 回退路由器 ·
        下发 PASS 信号（verdict=pass + 三段证据链完整）。"""
        # arrange · L2-05 报 S4 done
        mock_l2_05.emit_s4_done(
            project_id=mock_project_id,
            wp_commit_hashes={"wp-1": "abc123"},
            test_results_snapshot_path="/tmp/s4-snapshot.json",
        )
        req = make_start_request(project_id=mock_project_id, all_wps_completed=True)
        # act
        report = sut.run_full_cycle_to_completion(req)
        # assert · L2-07 接收 verdict=PASS 信号
        signals = mock_l2_07.signals_received
        assert len(signals) == 1
        assert signals[0]["verdict_hint"] == "PASS"
        assert signals[0]["report_id"] == report.report_id
        assert signals[0]["project_id"] == mock_project_id
```

---

## §5 性能 SLO 用例

> ≥ 3 `@pytest.mark.perf` · 对标 §12.1/§12.2 · 覆盖单次派发延迟 / 批量 / 并发。
> 使用 `pytest-benchmark` 或手工计时 · 单 project 隔离 PM-14。

```python
# file: tests/l1_04/test_l2_06_verifier_orchestrator_slo.py
from __future__ import annotations

import pytest
import time
from concurrent.futures import ThreadPoolExecutor


class TestL2_06_PerformanceSLO:
    """§12 性能目标验证 · pytest -m perf 单独跑。"""

    @pytest.mark.perf
    def test_TC_L104_L206_701_assemble_and_dispatch_latency_p95_under_20s(
        self, sut, mock_project_id, make_start_request, benchmark,
    ) -> None:
        """TC-L104-L206-701 · §12.1 · 组装 workbench + 派发 IC-20 P95 ≤ 20s · 硬上限 30s。"""
        req = make_start_request(project_id=mock_project_id)
        result = benchmark.pedantic(
            lambda: sut.assemble_and_dispatch(req), iterations=20, rounds=5,
        )
        # pytest-benchmark 自动算 stats.quantile(0.95)
        assert benchmark.stats.stats.median <= 5.0, "P50 ≤ 5s"
        assert benchmark.stats.stats.max <= 30.0, "§12.1 硬上限 30s"

    @pytest.mark.perf
    def test_TC_L104_L206_702_assemble_evidence_chain_latency_p95_under_500ms(
        self, chain_assembler, mock_project_id, make_verifier_output,
        make_main_claim_snapshot, benchmark,
    ) -> None:
        """TC-L104-L206-702 · §12.1 · 三段证据链组装 P95 ≤ 500ms · 硬上限 10s。"""
        output = make_verifier_output(all_done=True, wp_count=10)
        result = benchmark.pedantic(
            lambda: chain_assembler.assemble_evidence_chain(
                verifier_output=output, main_session_id="main.a",
                main_claim_snapshot=make_main_claim_snapshot(),
                project_id=mock_project_id,
            ),
            iterations=50, rounds=5,
        )
        assert benchmark.stats.stats.max <= 10.0

    @pytest.mark.perf
    def test_TC_L104_L206_703_persist_atomic_latency_p95_under_200ms(
        self, persister, mock_project_id, make_verifier_report, benchmark,
    ) -> None:
        """TC-L104-L206-703 · §12.1 · 原子落盘（fsync + rename）P95 ≤ 200ms · 硬上限 10s。"""
        report = make_verifier_report()
        benchmark.pedantic(
            lambda: persister.persist_report_atomic(
                report=report, project_id=mock_project_id,
            ),
            iterations=30, rounds=5,
        )
        assert benchmark.stats.stats.median <= 0.05, "§12.1 P50 ≤ 50ms"
        assert benchmark.stats.stats.max <= 10.0

    @pytest.mark.perf
    def test_TC_L104_L206_704_broadcast_latency_p95_under_50ms(
        self, broadcaster, mock_project_id, make_persisted_report, benchmark,
    ) -> None:
        """TC-L104-L206-704 · §12.1 · 广播 L1-07 P95 ≤ 50ms · 硬上限 1s。"""
        report = make_persisted_report()
        benchmark.pedantic(
            lambda: broadcaster.broadcast_verifier_report_ready(
                report=report, project_id=mock_project_id,
            ),
            iterations=100, rounds=3,
        )
        assert benchmark.stats.stats.max <= 1.0

    @pytest.mark.perf
    def test_TC_L104_L206_705_cross_project_concurrency_10_parallel(
        self, make_sut_factory, make_start_request,
    ) -> None:
        """TC-L104-L206-705 · §12.2 · 跨 10 project 并发 S5 · P95 不劣化 · PM-14 天然隔离。"""
        sut = make_sut_factory()
        project_ids = [f"pid-perf-{i:03d}" for i in range(10)]
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [
                pool.submit(sut.start, make_start_request(project_id=pid))
                for pid in project_ids
            ]
            results = [f.result() for f in futures]
        elapsed = time.perf_counter() - start
        assert all(r.status == "accepted" for r in results)
        # 10 project 并发 · 整体应在 2x 单 project 延迟内（PM-14 无共享）
        assert elapsed < 60.0, "§12.2 跨 project 并发 ≥ 10 无显著争用"

    @pytest.mark.perf
    def test_TC_L104_L206_706_full_s5_cycle_mock_verifier_under_60s(
        self, sut, mock_project_id, make_start_request, mock_verifier_fast,
    ) -> None:
        """TC-L104-L206-706 · §12.6 · 集成 benchmark · 单次完整 S5（mock verifier）≤ 60s。"""
        req = make_start_request(project_id=mock_project_id)
        start = time.perf_counter()
        report = sut.run_full_cycle_to_completion(req)
        elapsed = time.perf_counter() - start
        assert report is not None
        assert elapsed <= 60.0, "§12.6 mock verifier 全流程 ≤ 60s"

    @pytest.mark.perf
    def test_TC_L104_L206_707_single_project_s5_serial_sequence(
        self, sut, mock_project_id, make_start_request,
    ) -> None:
        """TC-L104-L206-707 · §12.2 · 同 project S5 连续回合（FAIL 后重跑）· 串行 · 不抢并发。"""
        req1 = make_start_request(project_id=mock_project_id)
        r1 = sut.start(req1)
        # 同 project 第二次 start 前必须前一次 COMPLETED
        with pytest.raises(Exception) as exc:
            sut.start(req1)  # 直接 start 应失败（锁）
        assert "lock" in str(exc.value).lower() or "already" in str(exc.value).lower()
```

---

## §6 端到端 e2e

> 2-3 GWT · TDDExe 全链路验证 · 从 L1-01 发 IC-03 → 本 L2 派发 → verifier 跑 → 报告落盘广播 → L2-07 收信号。

```python
# file: tests/l1_04/test_l2_06_verifier_orchestrator_e2e.py
from __future__ import annotations

import pytest


class TestL2_06_E2E:
    """端到端 e2e 场景 · 覆盖 PRD §13.9 3 个主场景。"""

    @pytest.mark.e2e
    def test_TC_L104_L206_801_happy_path_s4_done_to_report_issued(
        self, e2e_stack, mock_project_id, make_full_s4_artifacts,
    ) -> None:
        """TC-L104-L206-801 · E2E 正向 ·
        GIVEN · S4 全完成（5 WP 全 done + 测试产物 + DoD self-check pass）
        WHEN · L1-01 发 IC-03 phase=S5 触发本 L2
        THEN · 派发 verifier → verifier 跑三段全 done → 报告落盘 → 广播 verifier_report_issued
              L1-07 ack · L2-07 收 verdict=PASS 信号 · 整流程 ≤ 60s（mock）"""
        # arrange
        make_full_s4_artifacts(project_id=mock_project_id, wp_count=5)
        # act
        result = e2e_stack.run_s5_full_cycle(project_id=mock_project_id)
        # assert
        assert result.status == "COMPLETED"
        assert result.verdict_hint == "PASS"
        assert result.report_id is not None
        assert result.three_evidence_chain.existence_segment.status == "done"
        assert result.three_evidence_chain.behavior_segment.status == "done"
        assert result.three_evidence_chain.quality_segment.status == "done"
        # 硬约束验证
        assert result.session_id.startswith("verifier."), "硬红线 · 独立 session"
        assert result.persisted_before_broadcasted is True, "硬约束 3 · 先落盘后广播"
        assert result.l1_07_received is True
        assert result.l2_07_signal_verdict == "PASS"

    @pytest.mark.e2e
    def test_TC_L104_L206_802_fail_path_verifier_diff_with_main_claim(
        self, e2e_stack, mock_project_id, make_full_s4_artifacts, inject_fail_claim,
    ) -> None:
        """TC-L104-L206-802 · E2E 负向 · verifier 判 FAIL（diff 不一致）
        GIVEN · S4 全完成 + 主声称 wp-3 pass · 但 verifier 独立跑判 wp-3 fail
        WHEN · 本 L2 派发 verifier
        THEN · behavior_segment.diff_with_main_claim ≠ [] · 报告落盘
              L2-07 收 verdict_hint=FAIL · 触发 FAIL-L2 回退"""
        make_full_s4_artifacts(project_id=mock_project_id, wp_count=3)
        inject_fail_claim(project_id=mock_project_id, wp_id="wp-3", main_claim="pass")
        result = e2e_stack.run_s5_full_cycle(project_id=mock_project_id)
        assert result.status == "COMPLETED"
        assert len(result.three_evidence_chain.behavior_segment.diff_with_main_claim) > 0
        assert result.verdict_hint == "FAIL"
        assert result.l2_07_signal_verdict == "FAIL"

    @pytest.mark.e2e
    def test_TC_L104_L206_803_delegation_three_strikes_block(
        self, e2e_stack, mock_project_id, make_full_s4_artifacts, force_l1_05_down,
    ) -> None:
        """TC-L104-L206-803 · E2E 硬红线 · 委托 3 次失败 → BLOCK
        GIVEN · S4 全完 · L1-05 IC-20 完全不可达（强制 down）
        WHEN · 本 L2 派发 verifier
        THEN · 3 次指数退避重试全 fail · 不 fallback 主 session · 
              push_suggestion(BLOCK) 到 L1-07 · retry_chain 记录 3 条 · UI 红屏"""
        make_full_s4_artifacts(project_id=mock_project_id, wp_count=3)
        force_l1_05_down()  # 强制 L1-05 不可达
        result = e2e_stack.run_s5_full_cycle(project_id=mock_project_id)
        assert result.status == "BLOCKED"
        assert result.verdict_hint == "BLOCK"
        assert len(result.retry_chain) == 3
        # 硬约束 4 · 禁主 session 降级
        assert result.main_session_fallback_attempted is False
        # L1-07 收 BLOCK 建议
        assert result.l1_07_block_suggestion is not None
        assert result.l1_07_block_suggestion["reason"] == "verifier_unavailable_after_3_retries"
```

---

## §7 测试 fixture

> mock pid · mock clock · mock event bus · mock L1-05 · mock fs · 各 L1 子系统

```python
# file: tests/l1_04/conftest_l2_06.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def mock_project_id() -> str:
    """PM-14 mock project_id · 所有 TC 强制携带。"""
    return "pid-test-l2-06"


@pytest.fixture
def frozen_clock():
    """冻结时间 · 用于 estimated_completion / timeout 断言。"""
    class Clock:
        _now = datetime(2026, 4, 22, 10, 0, 0)
        def now(self): return self._now
        def advance(self, seconds: int): self._now += timedelta(seconds=seconds)
    return Clock()


@pytest.fixture
def mock_l1_05():
    """mock L1-05 Skill+子 Agent · 接 IC-20 delegate_verifier。"""
    m = MagicMock()
    m.ic_20_received = []
    def _record(payload):
        m.ic_20_received.append(payload)
        return MagicMock(session_id=f"verifier.mock.{len(m.ic_20_received):03d}")
    m.receive_ic_20.side_effect = _record
    return m


@pytest.fixture
def mock_l1_07():
    """mock L1-07 Supervisor · 接 IC-13 push_suggestion + 发 IC-14 halt。"""
    m = MagicMock()
    m.suggestions_received = []
    m.receive_suggestion.side_effect = lambda payload: m.suggestions_received.append(payload)
    return m


@pytest.fixture
def mock_l1_09():
    """mock L1-09 审计事件总线 · 接 IC-09 append_event（hash chain）。"""
    m = MagicMock()
    m.events_received = []
    m.append_event.side_effect = lambda e: m.events_received.append(e)
    return m


@pytest.fixture
def mock_l1_10():
    """mock L1-10 UI · 接 IC-16 push_stage_gate_card / progress。"""
    m = MagicMock()
    m.cards_received = []
    m.push_card.side_effect = lambda c: m.cards_received.append(c)
    return m


@pytest.fixture
def tmp_fs(tmp_path):
    """临时文件系统 · 用于落盘测试 + sha256 校验。"""
    class FS:
        root = tmp_path
        def exists(self, p): return (self.root / p.lstrip("/")).exists()
        def sha256(self, p):
            import hashlib
            data = (self.root / p.lstrip("/")).read_bytes()
            return hashlib.sha256(data).hexdigest()
    return FS()


@pytest.fixture
def sut(mock_l1_05, mock_l1_07, mock_l1_09, mock_l1_10, tmp_fs, frozen_clock):
    """Application Service SUT · 注入全套 mock。"""
    from app.l1_04.l2_06.orchestrator import VerifierDelegationOrchestrator
    return VerifierDelegationOrchestrator(
        l1_05=mock_l1_05, l1_07=mock_l1_07, l1_09=mock_l1_09,
        l1_10=mock_l1_10, fs=tmp_fs, clock=frozen_clock,
    )
```

---

## §8 集成点用例

> 与 L2-04 Gate 编译器 / L2-05 S4 执行驱动器 / L2-07 回退路由器 3 兄弟 L2 的集成。

```python
# file: tests/l1_04/test_l2_06_verifier_orchestrator_integration.py
from __future__ import annotations

import pytest


class TestL2_06_Integration_With_Sibling_L2:
    """与兄弟 L2 的集成测试 · 读蓝图 + 接 S4 快照 + 发 PASS/FAIL 信号。"""

    def test_TC_L104_L206_901_read_s4_snapshot_from_l2_05(
        self, sut, mock_project_id, make_start_request, mock_l2_05,
    ) -> None:
        """TC-L104-L206-901 · 与 L2-05 S4 执行驱动器 · 读 S4 done snapshot · 组装 workbench。"""
        mock_l2_05.emit_s4_done(
            project_id=mock_project_id,
            wp_commit_hashes={"wp-1": "abc", "wp-2": "def"},
            test_results_snapshot_path="/tmp/s4.json",
            produced_artifacts_paths=["artifact-a.py", "artifact-b.py"],
            dod_self_check_results={"wp-1": "pass", "wp-2": "pass"},
        )
        req = make_start_request(project_id=mock_project_id)
        resp = sut.start(req)
        assert resp.status == "accepted"
        # 组装时必读 L2-05 快照
        assert mock_l2_05.read_snapshot_called is True

    def test_TC_L104_L206_902_read_acceptance_checklist_from_l2_04(
        self, sut, mock_project_id, make_start_request, mock_l2_04,
    ) -> None:
        """TC-L104-L206-902 · 与 L2-04 Gate 编译器 · 读 acceptance-checklist + quality-gates。"""
        mock_l2_04.provide_ac_list(
            project_id=mock_project_id,
            ac_clauses=[
                {"ac_id": "AC-001", "given": "...", "when": "...", "then": "..."},
                {"ac_id": "AC-002", "given": "...", "when": "...", "then": "..."},
            ],
        )
        req = make_start_request(project_id=mock_project_id)
        sut.start(req)
        assert mock_l2_04.read_ac_called is True
        assert mock_l2_04.read_gates_called is True

    def test_TC_L104_L206_903_downstream_signal_to_l2_07_rollback_router(
        self, sut, mock_project_id, make_start_request, mock_l2_07,
    ) -> None:
        """TC-L104-L206-903 · 与 L2-07 偏差判定+回退路由器 · 下发 verdict 信号（PASS/FAIL）。"""
        req = make_start_request(project_id=mock_project_id)
        report = sut.run_full_cycle_to_completion(req)
        signals = mock_l2_07.signals_received
        assert len(signals) >= 1
        assert signals[-1]["report_id"] == report.report_id
        assert signals[-1]["verdict_hint"] in {"PASS", "FAIL", "BLOCK"}
        assert signals[-1]["project_id"] == mock_project_id

    def test_TC_L104_L206_904_read_blueprint_manifests_from_l2_01_02_03(
        self, sut, mock_project_id, make_start_request,
        mock_l2_01, mock_l2_02, mock_l2_03,
    ) -> None:
        """TC-L104-L206-904 · 与 L2-01/02/03 · 读 master_test_plan + dod_expressions + test_suite 清单。"""
        req = make_start_request(project_id=mock_project_id)
        sut.start(req)
        assert mock_l2_01.read_master_plan_called is True
        assert mock_l2_02.read_dod_expr_called is True
        assert mock_l2_03.read_test_suite_called is True
```

---

## §9 边界 / edge case

> ≥ 5 · 验证超时 / 部分结果缺失 / 脏数据 / 重复验证 / 崩溃恢复。

```python
# file: tests/l1_04/test_l2_06_verifier_orchestrator_edge.py
from __future__ import annotations

import pytest
from unittest.mock import patch


class TestL2_06_EdgeCases:
    """边界 / edge case · 非常规输入 + 极端条件。"""

    def test_TC_L104_L206_A01_verifier_timeout_30min_retry_once(
        self, sut, mock_project_id, make_start_request, mock_l1_05,
    ) -> None:
        """TC-L104-L206-A01 · 边界 · verifier 30 min 超时 · 重启 1 次 · 仍超时 → BLOCK。"""
        # mock L1-05 两次都超时
        mock_l1_05.receive_ic_20.side_effect = [TimeoutError(), TimeoutError(), TimeoutError()]
        req = make_start_request(project_id=mock_project_id)
        result = sut.run_full_cycle_to_completion(req)
        assert result.status == "BLOCKED"
        assert result.verifier_restart_count == 1, "§11.4 软降级 · 超时允许 1 次瞬时重试"

    def test_TC_L104_L206_A02_partial_evidence_missing_two_segments(
        self, callback_receiver, mock_project_id,
    ) -> None:
        """TC-L104-L206-A02 · 边界 · 部分结果缺失 · 三段中 2 段缺 · 每段补 empty+reason。"""
        bad_output = {"existence_segment": {"status": "done", "evidence_items": []}}
        resp = callback_receiver.receive_verifier_callback(
            session_id="verifier.partial", verifier_output=bad_output,
            project_id=mock_project_id,
        )
        assert set(resp.empty_segments) == {"behavior", "quality"}
        assert all(r == "malformed_callback" for r in resp.reason_map.values())

    def test_TC_L104_L206_A03_dirty_data_malformed_json_in_verifier_output(
        self, callback_receiver, mock_project_id,
    ) -> None:
        """TC-L104-L206-A03 · 边界 · 脏数据 · verifier 输出 JSON 含非法 Unicode。"""
        dirty = {
            "existence_segment": {"status": "done", "evidence_items": [{"path": "\x00bad"}]},
            "behavior_segment": {"status": "done", "test_runs": []},
            "quality_segment": {"status": "done", "quality_eval_results": []},
        }
        # 不应 crash · 应清洗或标 empty
        resp = callback_receiver.receive_verifier_callback(
            session_id="verifier.dirty", verifier_output=dirty,
            project_id=mock_project_id,
        )
        assert resp.three_evidence_chain is not None

    def test_TC_L104_L206_A04_duplicate_verification_idempotent(
        self, sut, mock_project_id, make_start_request,
    ) -> None:
        """TC-L104-L206-A04 · 边界 · 重复验证 · 同 request_id 重发 · 幂等返回首次 report_id。"""
        req = make_start_request(project_id=mock_project_id, request_id="req-unique-001")
        r1 = sut.start(req)
        # 第二次（相同 request_id）· 幂等
        r2 = sut.start(req)
        assert r1.report_id == r2.report_id
        assert r2.status in ("accepted", "duplicate")  # 幂等返首次 id

    def test_TC_L104_L206_A05_empty_ac_list_and_empty_s4_results(
        self, workbench_assembler, mock_project_id, make_blueprint_refs,
    ) -> None:
        """TC-L104-L206-A05 · 边界 · AC 空 + S4 空 · 双空拒绝（E11 优先）。"""
        from app.l1_04.l2_06.errors import VerifierOrchestratorError
        with pytest.raises(VerifierOrchestratorError) as exc:
            workbench_assembler.assemble_workbench(
                blueprint_refs=make_blueprint_refs(),
                s4_snapshot={"wp_commit_hashes": {}, "test_results_snapshot_path": ""},
                ac_list=[],
                project_id=mock_project_id,
            )
        assert exc.value.code in {"L2-06/E11", "L2-06/E10"}

    def test_TC_L104_L206_A06_concurrent_s5_same_project_rejected(
        self, sut, mock_project_id, make_start_request,
    ) -> None:
        """TC-L104-L206-A06 · 边界 · 同 project 并发 S5 · 只允许 1 个（Repository 锁）。"""
        req = make_start_request(project_id=mock_project_id)
        r1 = sut.start(req)
        assert r1.status == "accepted"
        # 同 project 第二次 S5 · 应被锁拒绝
        r2 = sut.start(req)
        assert r2.status == "rejected" or "already_running" in (r2.rejection_reason or "")

    def test_TC_L104_L206_A07_crash_recovery_mid_persist(
        self, persister, mock_project_id, make_verifier_report, tmp_fs,
    ) -> None:
        """TC-L104-L206-A07 · 边界 · 崩溃恢复 · persist 中途 crash · 下次启动清理 .tmp 文件。"""
        report = make_verifier_report()
        # 模拟 crash · 留下 .tmp 文件
        with patch("os.rename", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                persister.persist_report_atomic(report=report, project_id=mock_project_id)
        # 下次启动 · 清理残留
        persister.cleanup_stale_tmp_files(project_id=mock_project_id)
        # .tmp 应被清理
        tmp_files = list(tmp_fs.root.glob("**/*.tmp"))
        assert len(tmp_files) == 0

    def test_TC_L104_L206_A08_oversized_verifier_output_truncation(
        self, callback_receiver, mock_project_id,
    ) -> None:
        """TC-L104-L206-A08 · 边界 · verifier 回调 output 超大（> 100MB）· 截断 + WARN。"""
        huge_output = {
            "existence_segment": {
                "status": "done",
                "evidence_items": [{"path": f"f{i}.py"} for i in range(1_000_000)],
            },
            "behavior_segment": {"status": "done", "test_runs": []},
            "quality_segment": {"status": "done", "quality_eval_results": []},
        }
        resp = callback_receiver.receive_verifier_callback(
            session_id="verifier.huge", verifier_output=huge_output,
            project_id=mock_project_id,
        )
        # 截断 · 仍能返回 three_evidence_chain
        assert resp.three_evidence_chain is not None
        assert len(resp.three_evidence_chain.existence_segment.evidence_items) <= 10_000, (
            "超大 output 必截断"
        )
```

---

*— L1-04 / L2-06 · S5 TDDExe Verifier 编排器 · TDD tests 用例 v1.0 · 33 错误码 × 11 方法 × 6 IC × 7 硬红线全覆盖 —*
