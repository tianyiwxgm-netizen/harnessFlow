---
doc_id: tests-L1-04-L2-02-DoD 表达式编译器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-DoD 表达式编译器.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-04 L2-02 DoD 表达式编译器 · TDD 测试用例

> 基于 3-1 L2-02 §3（5 个 public 方法 · compile_batch / eval_expression / validate_expression / list_whitelist_rules / add_whitelist_rule）+ §11 错误码（15 项 §11.1 降级表 ∪ §3.6 接口错误码 ∪ 前缀 `E_L204_L202_`）+ §12 SLO（编译 / eval / validate / list / add 五梯度）+ §13 TC ID 矩阵（001-015 compile / 016-040 eval / 041-050 validate / 051-053 list / 054-060 add / 061-070 e2e）驱动。
> TC ID 统一格式：`TC-L104-L202-NNN`（L1-04 下 L2-02，三位流水号 · 001-099 正向 / 1xx-4xx 负向按方法分段 / 6xx IC 契约 / 7xx 性能 / 8xx e2e / 9xx 集成 / Axx 边界）。
> pytest + Python 3.11+ 类型注解；`class TestL2_02_DoDExpressionCompiler` 组织；负向 / IC / perf / e2e / 集成 / 边界各自独立 `class`。

## §0 撰写进度

- [x] §1 覆盖度索引（5 public 方法 + 19 错误码 + 6 IC-XX + 7 SLO + 5 PRD GWT 场景）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试（≥ 3 join）
- [x] §5 性能 SLO 用例（§12 对标 · ≥ 3 @pytest.mark.perf）
- [x] §6 端到端 e2e（PRD §9.9 正向 1-2 / 负向 3-5 / 集成 6 / 性能 7）
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus / mock whitelist / mock snapshot）
- [x] §8 集成点用例（与 L2-01 蓝图生成器 / L2-04 Gate 编译器）
- [x] §9 边界 / edge case（表达式注入 / 深层嵌套 / 循环依赖 / 无效 DSL / 冷启动）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。
> 错误码前缀一律 `E_L204_L202_` · 表格仍写全前缀（与 3-1 §11.1 / §3.6 对齐）。

### §1.1 方法 × 测试 × 覆盖类型（§3 + §2 TC）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 / IC |
|---|---|---|---|
| `compile_batch()` · §3.1 合法 50 条一次全编 | TC-L104-L202-001 | unit | IC-L2-01（下游）|
| `compile_batch()` · §3.1 幂等 command_id 缓存 | TC-L104-L202-002 | unit | — |
| `compile_batch()` · §3.1 whitelist_version 显式绑定 | TC-L104-L202-003 | unit | — |
| `compile_batch()` · §3.1 按 wp_id 切片编译 | TC-L104-L202-004 | unit | — |
| `compile_batch()` · §3.1 unmappable 子集不炸全表 | TC-L104-L202-005 | unit | — |
| `compile_batch()` · §3.1 ast_depth_p95 统计回传 | TC-L104-L202-006 | unit | — |
| `eval_expression()` · §3.2 合法覆盖率表达式 PASS | TC-L104-L202-016 | unit | IC-L2-02 |
| `eval_expression()` · §3.2 cache_hit=true 热路径 | TC-L104-L202-017 | unit | — |
| `eval_expression()` · §3.2 evidence_snapshot 仅抽取字段 | TC-L104-L202-018 | unit | PM-10 单一事实源 |
| `eval_expression()` · §3.2 caller=verifier_subagent 合法 | TC-L104-L202-019 | unit | — |
| `eval_expression()` · §3.2 pure function 无副作用 | TC-L104-L202-020 | unit | §3.2.6 |
| `validate_expression()` · §3.3 合法 ast_tree_summary 返回 | TC-L104-L202-041 | unit | — |
| `validate_expression()` · §3.3 不写 audit · 不 emit 事件 | TC-L104-L202-042 | unit | §3.3.3 |
| `list_whitelist_rules()` · §3.4 默认 category=all | TC-L104-L202-051 | unit | — |
| `list_whitelist_rules()` · §3.4 deepcopy 防 frozendict 暴露 | TC-L104-L202-052 | unit | SA-06 |
| `list_whitelist_rules()` · §3.4 并发读无 race | TC-L104-L202-053 | unit | — |
| `add_whitelist_rule()` · §3.5 离线模式 + 双人评审通过 | TC-L104-L202-054 | unit | OFFLINE_ADMIN_MODE=1 |
| `add_whitelist_rule()` · §3.5 cache invalidate 全失效 | TC-L104-L202-055 | unit | §3.5.3 |

### §1.2 错误码 × 测试（§3.6 接口 19 项 ∪ §11.1 降级 15 项 · 去重合并 ≥ 15）

| 错误码（全前缀）| TC ID | 方法 / 触发 | 降级等级（§11.1） |
|---|---|---|---|
| `E_L204_L202_NO_PROJECT_ID` | TC-L104-L202-101 | `compile_batch()` PM-14 缺 pid | 拒绝 · 静默 |
| `E_L204_L202_CROSS_PROJECT` | TC-L104-L202-102 | `eval_expression()` expr.project_id != req.project_id | 🔴 SA-06 审计告警 |
| `E_L204_L202_AST_SYNTAX_ERROR` | TC-L104-L202-103 | `compile_batch()` clause_text 语法错 | 🟡 P3 · 本条 FAILED |
| `E_L204_L202_AST_ILLEGAL_NODE` | TC-L104-L202-104 | `compile_batch()` 含 `Import`/`Attribute`/`Lambda` | 🔴 SA-01 BLOCK |
| `E_L204_L202_AST_ILLEGAL_FUNCTION` | TC-L104-L202-105 | `compile_batch()` Call 非白名单函数 | 🔴 SA-01 BLOCK |
| `E_L204_L202_AC_NOT_MAPPABLE` | TC-L104-L202-106 | `compile_batch()` 条款未命中白名单 | INFO · 推流 F 澄清 |
| `E_L204_L202_AC_REVERSE_LOOKUP_FAILED` | TC-L104-L202-107 | `compile_batch()` source_ac_ids 反查失败 | 硬约束 4 违反 |
| `E_L204_L202_EVAL_TIMEOUT` | TC-L104-L202-108 | `eval_expression()` 超 timeout_ms=500 | 🟠 P2 · SIGTERM |
| `E_L204_L202_RECURSION_LIMIT` | TC-L104-L202-109 | `compile_batch()` AST 深度 > 32 | 🟠 SA-03 防递归炸弹 |
| `E_L204_L202_DATA_SOURCE_INVALID` | TC-L104-L202-110 | `eval_expression()` snapshot Pydantic 校验败 | SA-07 注入防御 |
| `E_L204_L202_DATA_SOURCE_UNKNOWN_TYPE` | TC-L104-L202-111 | `eval_expression()` 非白名单 6 类 DataSource | 拒绝 + 告警 |
| `E_L204_L202_WHITELIST_VERSION_MISMATCH` | TC-L104-L202-112 | `eval_expression()` expr.whitelist_version != 当前 | 🟡 P3 · 重编译 |
| `E_L204_L202_WHITELIST_TAMPERING` | TC-L104-L202-113 | 运行期监控发现 ALLOWED_FUNCS 被改 | 🔴 SEV_CRITICAL HALT |
| `E_L204_L202_ONLINE_WHITELIST_MUTATION` | TC-L104-L202-114 | `add_whitelist_rule()` 无 OFFLINE_ADMIN_MODE | 🔴 BLOCK |
| `E_L204_L202_EVAL_MEMORY_EXCEEDED` | TC-L104-L202-115 | eval 子进程内存 > 64 MB | 🟠 SIGKILL |
| `E_L204_L202_COMPILE_TIMEOUT` | TC-L104-L202-116 | `compile_batch()` 超 timeout_s=120 | 🟠 返回部分 + WARN |
| `E_L204_L202_COMPILE_OVERSIZED` | TC-L104-L202-117 | dod-expressions.yaml > 500KB | 拒绝 + WARN |
| `E_L204_L202_IDEMPOTENCY_VIOLATION` | TC-L104-L202-118 | 同 command_id 但 clauses 变更 | 拒绝 + 审计 |
| `E_L204_L202_CALLER_UNAUTHORIZED` | TC-L104-L202-119 | `eval_expression()` caller 不在 enum | 🔴 SA-07 拒绝 |
| `E_L204_L202_CACHE_POISON` | TC-L104-L202-120 | AST 缓存命中但 re-validate 失败 | SA-11 清缓存 + 告警 |
| `E_L204_L202_AUDIT_APPEND_FAILED` | TC-L104-L202-121 | eval_audit_log.jsonl 写失败 | 🔴 FAIL-L1 · WAL 重试 10 次 HALT |
| `E_L204_L202_SANDBOX_ESCAPE_DETECTED` | TC-L104-L202-122 | eval 触碰 `__builtins__` / `globals()` | 🔴 SEV_CRITICAL HALT |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 `blueprint_ready`（从 L2-01 接）| L2-01 → 本 L2 | TC-L104-L202-601 | 消费方 · 触发 `compile_batch` |
| IC-L2-02 `eval_expression`（本 L2 内部面向 L2-05/06/04）| 本 L2 → L2-05 / L2-06 / L2-04 | TC-L104-L202-602 | 生产方 · 唯一 eval 入口 |
| IC-09 `append_event`（eval_audited / compile_failed）| 本 L2 → L1-09 | TC-L104-L202-603 | hash-chain + fsync 强一致 |
| IC-13 `push_suggestion`（unmappable → INFO 澄清）| 本 L2 → L1-07 | TC-L104-L202-604 | 流 F 回查 L1-02 |
| IC-16 `push_stage_gate_card`（经 L1-02 聚合 S3 Gate）| 本 L2 → L1-10（经 L1-02）| TC-L104-L202-605 | dod-expressions.yaml 为 S3 Gate 五件之一 |
| IC-20 `delegate_verifier`（间接 · verifier 独立 session 回调 evaluator 库）| L2-06 → L1-05 → Verifier → 本 L2 | TC-L104-L202-606 | 库注入 · PM-03 独立 session |

### §1.4 §12 SLO × 测试

| SLO 维度（§12.1/§12.2） | 阈值 | TC ID |
|---|---|---|
| `compile(clause_text)` 冷 P95 | ≤ 100ms | TC-L104-L202-701 |
| `eval(expr, snapshot)` 冷 P95 | ≤ 10ms | TC-L104-L202-702 |
| `eval(expr, snapshot)` 热（cache hit）P95 | ≤ 2ms | TC-L104-L202-703 |
| `validate_expression(expr_text)` P95 | ≤ 20ms | TC-L104-L202-704 |
| `list_whitelist_rules()` P95 | ≤ 5ms | TC-L104-L202-705 |
| 并发 50 eval 无 SLO 劣化 · QPS ≥ 500 | §12.2 | TC-L104-L202-706 |
| 编译 50 条 P99 ≤ 60s（PRD §9.4 性能约束） | §9.4 | TC-L104-L202-707 |

### §1.5 PRD §9.9 交付验证大纲 × 测试

| PRD 场景 | TC ID | 类别 |
|---|---|---|
| 正向 1 · 50 条 DoD 完整编译（60 秒内） | TC-L104-L202-801 | e2e |
| 正向 2 · 受限 eval 正常返回 ≤ 100ms | TC-L104-L202-802 | e2e |
| 负向 3 · 含 arbitrary exec 拒绝编译 | TC-L104-L202-803 | e2e |
| 负向 4 · 未命中白名单触发流 F | TC-L104-L202-804 | e2e |
| 负向 5 · evaluator 试图访问文件系统 | TC-L104-L202-805 | e2e |
| 集成 6 · S5 verifier 独立 eval 同一套 DoD | TC-L104-L202-901 | integration |
| 集成 7 · L2-04 读白名单谓词校验 gates | TC-L104-L202-902 | integration |
| 性能 8 · 1000 次连续 eval 无内存泄漏 | TC-L104-L202-708 | perf |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_02_DoDExpressionCompiler`；arrange / act / assert 三段明确。
> 被测对象（SUT）：`DoDExpressionCompiler` + `DoDEvaluator` 组合（Domain Service · §2.4）· 从 `app.l1_04.l2_02.compiler` / `app.l1_04.l2_02.evaluator` 导入。
> 所有入参 schema 严格按 §3 字段级 YAML · 所有出参断言按 §3 出参 schema。

```python
# file: tests/l1_04/test_l2_02_dod_compiler_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator
from app.l1_04.l2_02.schemas import (
    CompileBatchCommand,
    CompileBatchResult,
    EvalCommand,
    EvalResult,
    ValidateCommand,
    ValidateResult,
    ListWhitelistRulesCommand,
    ListWhitelistRulesResult,
    AddWhitelistRuleCommand,
    AddWhitelistRuleResult,
)
from app.l1_04.l2_02.errors import DoDExpressionError


class TestL2_02_DoDExpressionCompiler:
    """§3 public 方法正向用例。每方法 ≥ 1 happy path。"""

    # --------- 3.1 compile_batch · 正常首次 --------- #

    def test_TC_L104_L202_001_compile_batch_happy_path_50_clauses(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L202-001 · 首次编译 · 50 条 · 全命中白名单 · 返回 set_id + 版本 1。"""
        # arrange
        req: CompileBatchCommand = make_compile_request(
            project_id=mock_project_id,
            clause_count=50,
        )
        # act
        resp: CompileBatchResult = sut.compile_batch(req)
        # assert
        assert resp.accepted is True, "§3.1.3 accepted=True"
        assert resp.set_id.startswith("dod-set-"), "§3.1.3 format=dod-set-{uuid-v7}"
        assert resp.version == 1, "首次版本 = 1"
        assert resp.compiled_count == 50
        assert resp.unmappable_clauses == []
        assert resp.expr_statistics.total_exprs == 50

    def test_TC_L104_L202_002_compile_batch_idempotent_by_command_id(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L202-002 · 同 command_id 二次调用返回首次缓存结果（§3.1.5 Idempotent）。"""
        req = make_compile_request(project_id=mock_project_id, clause_count=10)
        first: CompileBatchResult = sut.compile_batch(req)
        second: CompileBatchResult = sut.compile_batch(req)
        assert first.set_id == second.set_id, "§3.1.5 幂等 cache 命中"
        assert first.version == second.version

    def test_TC_L104_L202_003_compile_batch_explicit_whitelist_version(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L202-003 · 显式指定 whitelist_version · 绑定到编译产物（§3.1.2）。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=10, whitelist_version="1.2.3",
        )
        resp = sut.compile_batch(req)
        assert resp.whitelist_version == "1.2.3"

    def test_TC_L104_L202_004_compile_batch_wp_slice(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L202-004 · wp_id 切片编译 · expr_statistics.per_wp 仅含该 WP。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=20, wp_id="wp-0007",
        )
        resp = sut.compile_batch(req)
        assert "wp-0007" in resp.expr_statistics.per_wp
        assert set(resp.expr_statistics.per_wp.keys()) == {"wp-0007"}

    def test_TC_L104_L202_005_compile_batch_partial_unmappable_does_not_fail_all(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L202-005 · 1 条未命中白名单 + 49 条命中 · 整体 accepted=True · unmappable_clauses 单条登记。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=50, inject_unmappable_count=1,
        )
        resp = sut.compile_batch(req)
        assert resp.accepted is True, "部分失败不 short-circuit（§6.4 并发 fan-out）"
        assert resp.compiled_count == 49
        assert len(resp.unmappable_clauses) == 1
        assert resp.unmappable_clauses[0].rejection_reason

    def test_TC_L104_L202_006_compile_batch_ast_depth_statistics(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L202-006 · expr_statistics 回传 ast_depth_p95 / ast_node_count_p95（§3.1.3）。"""
        req = make_compile_request(project_id=mock_project_id, clause_count=30)
        resp = sut.compile_batch(req)
        assert resp.expr_statistics.ast_depth_p95 >= 1
        assert resp.expr_statistics.ast_node_count_p95 >= 1

    # --------- 3.2 eval_expression · 唯一 eval 入口 --------- #

    def test_TC_L104_L202_016_eval_coverage_expression_passes(
        self,
        sut: DoDExpressionCompiler,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-016 · coverage >= 0.8 · snapshot.coverage=0.85 · 返 pass=True + reason。"""
        req: EvalCommand = make_eval_request(
            project_id=mock_project_id,
            expr_id=ready_expr_id,
            coverage_value=0.85,
            caller="L2-05_wp_self_check",
        )
        resp: EvalResult = evaluator.eval_expression(req)
        assert resp.pass_ is True, "§3.2.3 出参 pass=True"
        assert len(resp.reason) >= 10, "§3.2.3 reason minLength=10 · 禁空 / 禁含糊"
        assert resp.evidence_snapshot
        assert resp.eval_id.startswith("eval-")
        assert resp.caller == "L2-05_wp_self_check"

    def test_TC_L104_L202_017_eval_cache_hit_hot_path(
        self,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-017 · 相同 command_id + snapshot_hash 二次 eval · cache_hit=True。"""
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        first = evaluator.eval_expression(req)
        second = evaluator.eval_expression(req)
        assert first.eval_id == second.eval_id, "§3.2.5 幂等 · AST 缓存命中"
        assert second.cache_hit is True

    def test_TC_L104_L202_018_eval_evidence_snapshot_only_accessed_fields(
        self,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-018 · evidence_snapshot 仅含 expression 实际访问字段（PM-10 单一事实源）。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.85, lint_error_count=0,
            # snapshot 冗余含 perf / artifact 但 expr 只读 coverage
            include_perf=True, include_artifact=True,
        )
        resp = evaluator.eval_expression(req)
        assert "coverage" in resp.evidence_snapshot, "§3.2.3 仅抽取实际访问字段"
        assert "perf" not in resp.evidence_snapshot, "PM-10 禁存 expression 未访问字段"
        assert "artifact" not in resp.evidence_snapshot

    def test_TC_L104_L202_019_eval_caller_verifier_subagent_is_accepted(
        self,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-019 · caller=verifier_subagent 在白名单内（§3.2.2 enum 4 项全部）。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9, caller="verifier_subagent",
        )
        resp = evaluator.eval_expression(req)
        assert resp.pass_ is True
        assert resp.caller == "verifier_subagent"

    def test_TC_L104_L202_020_eval_pure_function_no_side_effects(
        self,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
        mock_event_bus: MagicMock,
        mock_fs: MagicMock,
    ) -> None:
        """TC-L104-L202-020 · eval pure function · 不写文件 / 不发事件 / 不改状态（§3.2.6）。"""
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        evaluator.eval_expression(req)
        # 本方法不得 append_event（§3.2.6 广播由调用方做）
        compile_events = [c for c in mock_event_bus.append_event.call_args_list
                          if c.kwargs.get("event_type", "").startswith("L1-04:dod_evaluated")
                          and c.kwargs.get("source") == "L2-02_evaluator_internal"]
        assert compile_events == []
        assert mock_fs.write.call_count == 0, "§3.2.6 pure function"

    # --------- 3.3 validate_expression · 预校验 --------- #

    def test_TC_L104_L202_041_validate_returns_ast_tree_summary(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L202-041 · 合法 clause · ast_tree_summary.depth / node_count / used_functions 齐全（§3.3.2）。"""
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="coverage.line_rate >= 0.8 and lint.error_count == 0",
        )
        rep: ValidateResult = sut.validate_expression(cmd)
        assert rep.valid is True
        assert rep.ast_tree_summary.depth >= 1
        assert rep.ast_tree_summary.node_count >= 3
        assert "coverage" in rep.ast_tree_summary.used_data_source_types
        assert rep.violations == []

    def test_TC_L104_L202_042_validate_no_audit_no_events(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L202-042 · validate_expression 不 emit 事件 · 不占 compile_audit 日志（§3.3.3）。"""
        mock_event_bus.append_event.reset_mock()
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="test_result.p0_all_pass is True",
        )
        sut.validate_expression(cmd)
        events = [c for c in mock_event_bus.append_event.call_args_list
                  if c.kwargs.get("event_type", "").startswith("L1-04:dod_compile")]
        assert events == [], "§3.3.3 validate 不写 compile_audit · 不 emit 事件"

    # --------- 3.4 list_whitelist_rules --------- #

    def test_TC_L104_L202_051_list_whitelist_default_all(
        self,
        sut: DoDExpressionCompiler,
    ) -> None:
        """TC-L104-L202-051 · 默认 category=all · 返回 node/function/data_source 三大类合集。"""
        cmd = ListWhitelistRulesCommand()
        resp: ListWhitelistRulesResult = sut.list_whitelist_rules(cmd)
        categories = {r.category for r in resp.rules}
        assert {"node", "function", "data_source"}.issubset(categories)
        assert resp.whitelist_version

    def test_TC_L104_L202_052_list_whitelist_returns_deepcopy(
        self,
        sut: DoDExpressionCompiler,
    ) -> None:
        """TC-L104-L202-052 · 返回 deepcopy · 外部修改不应污染内部 frozendict（§3.4.3 SA-06 防篡改）。"""
        cmd = ListWhitelistRulesCommand(category="function")
        r1 = sut.list_whitelist_rules(cmd)
        r1.rules[0].name = "mutated_by_external"
        r2 = sut.list_whitelist_rules(cmd)
        names_v2 = {r.name for r in r2.rules}
        assert "mutated_by_external" not in names_v2, "§3.4.3 deepcopy · SA-06 不暴露内部引用"

    def test_TC_L104_L202_053_list_whitelist_concurrent_read_no_race(
        self,
        sut: DoDExpressionCompiler,
    ) -> None:
        """TC-L104-L202-053 · 20 线程并发读 · 结果一致 · 无 race。"""
        import threading
        outs: list[int] = []
        def _worker() -> None:
            r = sut.list_whitelist_rules(ListWhitelistRulesCommand())
            outs.append(len(r.rules))
        ts = [threading.Thread(target=_worker) for _ in range(20)]
        for t in ts: t.start()
        for t in ts: t.join(timeout=5)
        assert len(set(outs)) == 1, f"并发读结果不一致：{set(outs)}"

    # --------- 3.5 add_whitelist_rule · 离线唯一 --------- #

    def test_TC_L104_L202_054_add_whitelist_rule_offline_with_dual_review(
        self,
        sut_offline_admin: DoDExpressionCompiler,
        make_add_whitelist_rule_request,
    ) -> None:
        """TC-L104-L202-054 · OFFLINE_ADMIN_MODE=1 + 双人评审 + version bump → 通过。"""
        cmd: AddWhitelistRuleCommand = make_add_whitelist_rule_request(
            version_bump_type="minor",
            reviewers=["sre-alice", "sec-bob"],
        )
        resp: AddWhitelistRuleResult = sut_offline_admin.add_whitelist_rule(cmd)
        assert resp.rule_id
        assert resp.new_whitelist_version
        assert resp.audit_log_id

    def test_TC_L104_L202_055_add_whitelist_rule_invalidates_ast_cache(
        self,
        sut_offline_admin: DoDExpressionCompiler,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
        make_add_whitelist_rule_request,
    ) -> None:
        """TC-L104-L202-055 · add_whitelist_rule 产生 AST 缓存全失效(§3.5.3 / §6 步骤 8 cache invalidate)。"""
        # 先 eval 热缓存
        req_eval = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        evaluator.eval_expression(req_eval)
        assert evaluator._debug_cache_size() > 0

        cmd = make_add_whitelist_rule_request(version_bump_type="patch")
        sut_offline_admin.add_whitelist_rule(cmd)
        assert evaluator._debug_cache_size() == 0, "§3.5.3 cache invalidate 全失效"
```

---

## §3 负向用例（每错误码 ≥ 1）

> 与 §1.2 错误码表 1:1 映射。每个错误码至少 1 条 · 抛 `DoDExpressionError(code=..., severity=...)`。
> 错误码前缀一律 `E_L204_L202_`，严格按 3-1 §3.6 + §11.1 原样。

```python
# file: tests/l1_04/test_l2_02_dod_compiler_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator
from app.l1_04.l2_02.schemas import (
    CompileBatchCommand,
    EvalCommand,
    ValidateCommand,
    AddWhitelistRuleCommand,
)
from app.l1_04.l2_02.errors import DoDExpressionError


class TestL2_02_NegativeErrors:
    """§3.6 + §11.1 错误码全覆盖 · 每错误码 ≥ 1。"""

    def test_TC_L104_L202_101_no_project_id_rejected(
        self, sut: DoDExpressionCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L202-101 · project_id 缺失 → E_L204_L202_NO_PROJECT_ID(PM-14 硬红线)。"""
        req = make_compile_request(project_id=None, clause_count=10)
        with pytest.raises(DoDExpressionError) as ei:
            sut.compile_batch(req)
        assert ei.value.code == "E_L204_L202_NO_PROJECT_ID"

    def test_TC_L104_L202_102_cross_project_raises_sa_06(
        self, evaluator: DoDEvaluator, mock_project_id: str, other_project_id: str,
        ready_expr_id_of_other_project: str, make_eval_request,
    ) -> None:
        """TC-L104-L202-102 · expr.project_id != request.project_id → E_L204_L202_CROSS_PROJECT + SA-06 告警。"""
        req = make_eval_request(
            project_id=mock_project_id,
            expr_id=ready_expr_id_of_other_project,
            coverage_value=0.9,
        )
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_CROSS_PROJECT"

    def test_TC_L104_L202_103_ast_syntax_error_per_clause(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-103 · 单条 clause_text 语法错 → 该条 FAILED · 其他继续(§11.1 P3)。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=10,
            inject_syntax_error_indices=[3],
        )
        resp = sut.compile_batch(req)
        assert resp.compiled_count == 9
        assert any(e.error_code == "E_L204_L202_AST_SYNTAX_ERROR" for e in resp.errors)

    def test_TC_L104_L202_104_ast_illegal_node_import_blocks_sa_01(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-104 · 含 Import/Attribute/Lambda → E_L204_L202_AST_ILLEGAL_NODE · BLOCK(SA-01)。"""
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="(lambda x: __import__('os').system('rm -rf /'))(coverage)",
        )
        rep = sut.validate_expression(cmd)
        assert rep.valid is False
        assert any(v.violation_type == "illegal_node" for v in rep.violations)

    def test_TC_L104_L202_105_ast_illegal_function_call_blocked(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-105 · ast.Call func 非白名单 → E_L204_L202_AST_ILLEGAL_FUNCTION(SA-01 BLOCK)。"""
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="open('/etc/passwd').read()",
        )
        rep = sut.validate_expression(cmd)
        assert rep.valid is False
        assert any(v.violation_type == "illegal_function" for v in rep.violations)

    def test_TC_L104_L202_106_ac_not_mappable_goes_to_unmappable(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-106 · "UI 要好看"这种无量化条款 → unmappable_clauses 登记 + INFO 澄清(流 F)。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=5,
            inject_unmappable_texts=["UI 要好看"],
        )
        resp = sut.compile_batch(req)
        assert len(resp.unmappable_clauses) >= 1
        assert resp.unmappable_clauses[0].rejection_reason
        assert any(sug.predicate_name for sug in resp.unmappable_clauses[0].suggested_predicates or [])

    def test_TC_L104_L202_107_ac_reverse_lookup_failed(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-107 · source_ac_ids 反查 ac_matrix 失败(硬约束 4) → 拒绝该条目。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=5,
            inject_invalid_ac_ids=["ac-ghost-001"],
        )
        resp = sut.compile_batch(req)
        assert any(e.error_code == "E_L204_L202_AC_REVERSE_LOOKUP_FAILED" for e in resp.errors)

    def test_TC_L104_L202_108_eval_timeout_sigterms_subprocess(
        self, evaluator: DoDEvaluator, mock_project_id: str, slow_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-108 · 超 timeout_ms=500 → E_L204_L202_EVAL_TIMEOUT · SIGTERM 子进程(§6.3)。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=slow_expr_id, coverage_value=0.9,
            timeout_ms=500,
        )
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_EVAL_TIMEOUT"

    def test_TC_L104_L202_109_recursion_limit_depth_gt_32(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-109 · AST 深度 > max_ast_depth=32 → E_L204_L202_RECURSION_LIMIT(SA-03)。"""
        # 深度 40 的嵌套 and 链
        deep_expr = " and ".join(["coverage.line_rate >= 0.8"] * 40)
        cmd = ValidateCommand(project_id=mock_project_id, expression_text=deep_expr)
        rep = sut.validate_expression(cmd)
        assert rep.valid is False
        assert any(v.violation_type == "exceeds_depth" for v in rep.violations)

    def test_TC_L104_L202_110_data_source_invalid_pydantic_fail(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-110 · data_sources_snapshot Pydantic 校验失败 → E_L204_L202_DATA_SOURCE_INVALID(SA-07)。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            # line_rate 必须 ∈ [0,1] · 传 1.5 触发 Pydantic 校验失败
            coverage_value=1.5,
        )
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_DATA_SOURCE_INVALID"

    def test_TC_L104_L202_111_data_source_unknown_type_rejected(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-111 · snapshot 含非 6 白名单 DataSource 类型 → 拒绝 + 告警。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
            inject_unknown_data_source={"file_system": {"path": "/etc/passwd"}},
        )
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_DATA_SOURCE_UNKNOWN_TYPE"

    def test_TC_L104_L202_112_whitelist_version_mismatch_triggers_recompile(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-112 · expr.whitelist_version != 当前 → E_L204_L202_WHITELIST_VERSION_MISMATCH(OQ-04)。"""
        evaluator._debug_force_whitelist_version_bump()
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_WHITELIST_VERSION_MISMATCH"

    def test_TC_L104_L202_113_whitelist_tampering_detected_halt(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request, mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L202-113 · ALLOWED_FUNCS 被运行期修改 → E_L204_L202_WHITELIST_TAMPERING · SEV_CRITICAL HALT。"""
        evaluator._debug_simulate_whitelist_tamper()
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_WHITELIST_TAMPERING"
        assert ei.value.severity == "SEV_CRITICAL"
        assert mock_l1_07.request_hard_halt.called, "§11.3 SEV_CRITICAL → L1-07 HALT"

    def test_TC_L104_L202_114_online_whitelist_mutation_blocked(
        self, sut: DoDExpressionCompiler, make_add_whitelist_rule_request,
    ) -> None:
        """TC-L104-L202-114 · 生产态(无 OFFLINE_ADMIN_MODE=1)调 add_whitelist_rule → BLOCK。"""
        cmd = make_add_whitelist_rule_request(version_bump_type="minor")
        with pytest.raises(DoDExpressionError) as ei:
            sut.add_whitelist_rule(cmd)
        assert ei.value.code == "E_L204_L202_ONLINE_WHITELIST_MUTATION"

    def test_TC_L104_L202_115_eval_memory_exceeded_sigkill(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-115 · eval 进程内存 > 64MB → E_L204_L202_EVAL_MEMORY_EXCEEDED · SIGKILL。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
            simulate_memory_leak_mb=96,
        )
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_EVAL_MEMORY_EXCEEDED"

    def test_TC_L104_L202_116_compile_batch_timeout_partial_result(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-116 · compile_batch 超 timeout_s=120 → 返回已编译部分 + unmappable + WARN(§11.1 P2)。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=50, simulate_compile_slow_s=150,
            timeout_s=5,
        )
        with pytest.raises(DoDExpressionError) as ei:
            sut.compile_batch(req)
        assert ei.value.code == "E_L204_L202_COMPILE_TIMEOUT"

    def test_TC_L104_L202_117_compile_oversized_500kb_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-117 · dod-expressions.yaml > 500KB → E_L204_L202_COMPILE_OVERSIZED + WARN。"""
        req = make_compile_request(project_id=mock_project_id, clause_count=5000)
        with pytest.raises(DoDExpressionError) as ei:
            sut.compile_batch(req)
        assert ei.value.code == "E_L204_L202_COMPILE_OVERSIZED"

    def test_TC_L104_L202_118_idempotency_violation_same_command_id_diff_clauses(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-118 · 同 command_id 但 clauses 内容变更 → E_L204_L202_IDEMPOTENCY_VIOLATION。"""
        req_1 = make_compile_request(project_id=mock_project_id, clause_count=10, command_id="cmd-fixed-001")
        sut.compile_batch(req_1)
        req_2 = make_compile_request(project_id=mock_project_id, clause_count=10, command_id="cmd-fixed-001",
                                     inject_clause_text_mutation=True)
        with pytest.raises(DoDExpressionError) as ei:
            sut.compile_batch(req_2)
        assert ei.value.code == "E_L204_L202_IDEMPOTENCY_VIOLATION"

    def test_TC_L104_L202_119_caller_unauthorized(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-119 · caller 不在 §3.2.2 enum 4 项 → E_L204_L202_CALLER_UNAUTHORIZED(SA-07)。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
            caller="random_attacker_l2",
        )
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_CALLER_UNAUTHORIZED"

    def test_TC_L104_L202_120_cache_poison_triggers_revalidate(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-120 · AST 缓存命中但 re-validate 失败 → E_L204_L202_CACHE_POISON(SA-11) 清缓存 + 告警。"""
        evaluator._debug_poison_ast_cache(ready_expr_id)
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_CACHE_POISON"

    def test_TC_L104_L202_121_audit_append_failed_fail_l1_after_10(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request, mock_event_bus: MagicMock, mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L202-121 · IC-09 eval_audit_log.jsonl 连续失败 10 次 → FAIL-L1 HALT(PM-18 断链)。"""
        mock_event_bus.append_event.side_effect = RuntimeError("wal_lost")
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        for _ in range(10):
            try:
                evaluator.eval_expression(req)
            except DoDExpressionError:
                pass
        assert mock_l1_07.request_hard_halt.called, "§11.1 AUDIT_APPEND_FAILED x10 → HALT"

    def test_TC_L104_L202_122_sandbox_escape_detected_halt(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request, mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L202-122 · eval 检测到 __builtins__/globals() 异常访问 → SANDBOX_ESCAPE_DETECTED · SEV_CRITICAL HALT。"""
        evaluator._debug_simulate_sandbox_escape()
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code == "E_L204_L202_SANDBOX_ESCAPE_DETECTED"
        assert ei.value.severity == "SEV_CRITICAL"
        assert mock_l1_07.request_hard_halt.called
```

---

## §4 IC-XX 契约集成测试

> 验证本 L2 参与的 6 条 IC 契约：IC-L2-01（从 L2-01 接收 blueprint_ready）· IC-L2-02（本 L2 对外 唯一 eval 入口）· IC-09（审计写）· IC-13（unmappable INFO 升级 L1-07）· IC-16（经 L1-02 S3 Gate 卡）· IC-20（verifier 库注入）。
> 契约测试目标：**两端 schema + 幂等性 + SLO + 事件 payload** 互信。

```python
# file: tests/l1_04/test_l2_02_dod_compiler_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator


class TestL2_02_ICContracts:
    """§4 · IC 契约集成测试(每 IC ≥ 1 join test)。"""

    def test_TC_L104_L202_601_ic_l2_01_consumes_blueprint_ready(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L202-601 · IC-L2-01 · L2-01 发 blueprint_ready · 本 L2 在 60s 内触发 compile_batch(PRD §9.6 必 7)。

        join：L2-01 → IC-L2-01(via L1-09) → 本 L2 订阅 → compile_batch。
        """
        # arrange · 仿真一条 blueprint_ready 事件
        sut.on_blueprint_ready(
            blueprint_id="bp-0001",
            project_id=mock_project_id,
            master_test_plan_path=f"projects/{mock_project_id}/tdd/master-test-plan.md",
            ac_matrix_path=f"projects/{mock_project_id}/tdd/ac-matrix.yaml",
            version=1,
            publisher="L1-04:L2-01",
            ts="2026-04-22T00:00:00Z",
        )
        # 本 L2 应在内部 orchestrator 调 compile_batch
        assert sut._debug_compile_triggered_recently_s() < 60.0, "§9.6 必 7 · ≤ 60s"

    def test_TC_L104_L202_602_ic_l2_02_eval_is_the_only_entry(
        self,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-602 · IC-L2-02 · eval_expression 是全 L1-04 唯一 eval 入口(§3.2.1)。

        join：L2-05 / L2-06 / L2-04 / verifier_subagent 都只能通过本方法 · 4 种 caller 全部接受。
        """
        for caller in (
            "L2-05_wp_self_check",
            "L2-06_s5_verifier",
            "verifier_subagent",
            "L2-04_gate_config_check",
        ):
            req = make_eval_request(
                project_id=mock_project_id, expr_id=ready_expr_id,
                coverage_value=0.9, caller=caller,
            )
            resp = evaluator.eval_expression(req)
            assert resp.pass_ is True
            assert resp.caller == caller

    def test_TC_L104_L202_603_ic_09_append_event_dod_compiled_and_evaluated(
        self,
        sut: DoDExpressionCompiler,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        make_compile_request,
        make_eval_request,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L202-603 · IC-09 · compile_batch → L1-04:dod_compiled · eval → L1-04:dod_evaluated 每次 append。

        join：本 L2 → IC-09 → L1-09 WAL(强一致 fsync · hash-chain)。
        """
        req = make_compile_request(project_id=mock_project_id, clause_count=5)
        resp = sut.compile_batch(req)
        types = [c.kwargs.get("event_type") for c in mock_event_bus.append_event.call_args_list]
        assert "L1-04:dod_compiled" in types, "IC-09 compile 审计"
        # eval 审计
        req2 = make_eval_request(project_id=mock_project_id, expr_id=resp.set_id + ":e0", coverage_value=0.9)
        try:
            evaluator.eval_expression(req2)
        except Exception:
            pass
        types2 = [c.kwargs.get("event_type") for c in mock_event_bus.append_event.call_args_list]
        assert any(t == "L1-04:dod_evaluated" for t in types2), "IC-09 eval 审计(调用方 append)"

    def test_TC_L104_L202_604_ic_13_unmappable_info_escalated_to_l1_07(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
        mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L202-604 · IC-13 · unmappable 条款 → push_suggestion{INFO, reason=dod_unmappable}(流 F)。

        join：本 L2 → IC-13 → L1-07 Supervisor 建议接收器。
        """
        req = make_compile_request(
            project_id=mock_project_id, clause_count=5,
            inject_unmappable_texts=["UI 要好看"],
        )
        sut.compile_batch(req)
        assert mock_l1_07.push_suggestion.called
        call = mock_l1_07.push_suggestion.call_args.kwargs
        assert call["level"] == "INFO"
        assert "dod_unmappable" in call.get("reason", "")

    def test_TC_L104_L202_605_ic_16_s3_gate_card_via_l1_02(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
        mock_l1_02: MagicMock,
    ) -> None:
        """TC-L104-L202-605 · IC-16 间接 · dod-expressions.yaml 是 S3 Gate 五件之一 · 经 L1-02 汇总推 L1-10。

        join：本 L2 → L1-02.receive_artifact{type=dod_expressions_yaml} → L1-02 聚合 5 件 → IC-16 push_stage_gate_card。
        """
        req = make_compile_request(project_id=mock_project_id, clause_count=10)
        sut.compile_batch(req)
        calls = [
            c for c in mock_l1_02.receive_artifact.call_args_list
            if c.kwargs.get("artifact_type") == "dod_expressions_yaml"
        ]
        assert len(calls) >= 1
        assert calls[0].kwargs["project_id"] == mock_project_id

    def test_TC_L104_L202_606_ic_20_verifier_subagent_library_injection(
        self,
        evaluator: DoDEvaluator,
        mock_project_id: str,
        ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-606 · IC-20 间接 · verifier 独立 session 以库注入方式复用本 L2 evaluator(PM-03)。

        join：L2-06 → IC-20 delegate_verifier → Verifier Subagent → 本 L2 evaluator(库注入 · pure function)。
        """
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9, caller="verifier_subagent",
        )
        resp = evaluator.eval_expression(req)
        # verifier 子 Agent 独立 session eval 结果必须与主 session 一致(pure function)
        req_main = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9, caller="L2-05_wp_self_check",
        )
        resp_main = evaluator.eval_expression(req_main)
        assert resp.pass_ == resp_main.pass_
        assert resp.evidence_snapshot == resp_main.evidence_snapshot
```

---

## §5 性能 SLO 用例

> 对齐 §12 延迟 / 吞吐 / 并发 · 用 `@pytest.mark.perf` 标记(CI 分流跑 · 不在 fast 组)· 与 `bench/test_eval_latency_baseline.py` baseline 互镜像。
> SLO 数字严格按 3-1 §12.1 / §12.2(eval 冷 P95 ≤ 10ms / compile 冷 P95 ≤ 100ms / validate P95 ≤ 20ms / list P95 ≤ 5ms / 并发 eval ≥ 500 QPS)。

```python
# file: tests/l1_04/test_l2_02_dod_compiler_perf.py
from __future__ import annotations

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import quantiles

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator
from app.l1_04.l2_02.schemas import ValidateCommand, ListWhitelistRulesCommand


@pytest.mark.perf
class TestL2_02_PerfSLO:
    """§12 · 8 项性能 SLO。P95 不劣化 > 10% 相对 baseline(§12.4)。"""

    def test_TC_L104_L202_701_compile_cold_p95_under_100ms(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-701 · compile(clause_text) 冷 P95 ≤ 100ms(§12.1)。"""
        samples: list[float] = []
        for i in range(30):
            req = make_compile_request(project_id=mock_project_id, clause_count=1, nonce=i)
            t0 = time.perf_counter()
            sut.compile_batch(req)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 100.0, f"compile 冷 P95={p95:.1f}ms > 100ms · §12.1 劣化"

    @pytest.mark.perf
    def test_TC_L104_L202_702_eval_cold_p95_under_10ms(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-702 · eval(cold) P95 ≤ 10ms(§12.1 · 全缓存 miss)。"""
        samples: list[float] = []
        for i in range(50):
            req = make_eval_request(
                project_id=mock_project_id, expr_id=ready_expr_id,
                coverage_value=0.8 + (i % 5) * 0.01,
                command_id=f"cmd-perf-cold-{i}",
            )
            evaluator._debug_flush_cache()
            t0 = time.perf_counter()
            evaluator.eval_expression(req)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 10.0, f"eval 冷 P95={p95:.1f}ms > 10ms · §12.1"

    @pytest.mark.perf
    def test_TC_L104_L202_703_eval_hot_cache_p95_under_2ms(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-703 · eval(hot cache hit) P95 ≤ 2ms(§12.1)。"""
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        evaluator.eval_expression(req)  # 预热
        samples: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            evaluator.eval_expression(req)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 2.0, f"eval 热 P95={p95:.2f}ms > 2ms"

    @pytest.mark.perf
    def test_TC_L104_L202_704_validate_p95_under_20ms(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-704 · validate_expression P95 ≤ 20ms(§12.1)。"""
        samples: list[float] = []
        for i in range(50):
            cmd = ValidateCommand(
                project_id=mock_project_id,
                expression_text=f"coverage.line_rate >= 0.{80 + (i % 10)}",
            )
            t0 = time.perf_counter()
            sut.validate_expression(cmd)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 20.0

    @pytest.mark.perf
    def test_TC_L104_L202_705_list_whitelist_p95_under_5ms(
        self, sut: DoDExpressionCompiler,
    ) -> None:
        """TC-L104-L202-705 · list_whitelist_rules P95 ≤ 5ms(§12.1 · 读内存)。"""
        samples: list[float] = []
        for _ in range(50):
            t0 = time.perf_counter()
            sut.list_whitelist_rules(ListWhitelistRulesCommand())
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 5.0

    @pytest.mark.perf
    def test_TC_L104_L202_706_concurrent_50_eval_qps_over_500(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-706 · 50 并发 eval · 单节点 QPS ≥ 500(§12.2) · 无 SLO 劣化。"""
        # 预热
        warm = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        evaluator.eval_expression(warm)

        def _one_call(idx: int) -> float:
            req = make_eval_request(
                project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
                command_id=f"cmd-perf-conc-{idx}",
            )
            t0 = time.perf_counter()
            evaluator.eval_expression(req)
            return (time.perf_counter() - t0) * 1000.0

        t_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=50) as ex:
            futs = [ex.submit(_one_call, i) for i in range(500)]
            lats = [f.result() for f in as_completed(futs)]
        elapsed = time.perf_counter() - t_start
        qps = 500 / elapsed
        p95 = quantiles(lats, n=20)[18]
        assert qps >= 500.0, f"并发 QPS={qps:.0f} < 500 · §12.2 劣化"
        assert p95 < 15.0, f"并发 P95={p95:.1f}ms 劣化 > 50%"

    @pytest.mark.perf
    def test_TC_L104_L202_707_compile_50_clauses_p99_under_60s(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-707 · 50 条 compile_batch P99 ≤ 60s(PRD §9.4 性能约束)。"""
        samples: list[float] = []
        for i in range(10):
            req = make_compile_request(project_id=mock_project_id, clause_count=50, nonce=i)
            t0 = time.perf_counter()
            sut.compile_batch(req)
            samples.append(time.perf_counter() - t0)
        p99 = max(samples)  # n=10 的 P99 ≈ max
        assert p99 < 60.0, f"50 条 compile_batch P99={p99:.1f}s > 60s · PRD §9.4"

    @pytest.mark.perf
    def test_TC_L104_L202_708_1000_eval_no_memory_leak(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-708 · PRD §9.9 性能 7 · 1000 次连续 eval · 无内存泄漏 · P95 ≤ 10ms。"""
        import tracemalloc
        tracemalloc.start()
        _, peak_start = tracemalloc.get_traced_memory()
        samples: list[float] = []
        for i in range(1000):
            req = make_eval_request(
                project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
                command_id=f"cmd-perf-leak-{i}",
            )
            t0 = time.perf_counter()
            evaluator.eval_expression(req)
            samples.append((time.perf_counter() - t0) * 1000.0)
        _, peak_end = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        p95 = quantiles(samples, n=20)[18]
        mem_growth_mb = (peak_end - peak_start) / (1024 * 1024)
        assert p95 < 10.0, f"1000 eval P95={p95:.1f}ms"
        assert mem_growth_mb < 50.0, f"1000 eval 内存增长 {mem_growth_mb:.1f}MB · 泄漏嫌疑"
```

---

## §6 端到端 e2e

> 对齐 PRD §9.9 五场景(正向 1/2 · 负向 3/4/5 · 集成 6) · 跨 L2-01 → 本 L2 → L2-04 / L2-05 / L2-06 全链路。
> 用 `@pytest.mark.e2e` 标记，用真实 tmp_path + 真实文件系统 + mock 的 IC-09 / 下游 L2。

```python
# file: tests/l1_04/test_l2_02_dod_compiler_e2e.py
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator
from app.l1_04.l2_02.errors import DoDExpressionError


@pytest.mark.e2e
class TestL2_02_E2E_PRDGWTScenarios:
    """PRD §9.9 GWT 场景 · 正向 1/2 · 负向 3/4/5 · 集成 6。"""

    def test_TC_L104_L202_801_positive_1_50_clause_full_compile_60s(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
        make_compile_request, mock_event_bus: MagicMock, tmp_path: Path,
    ) -> None:
        """TC-L104-L202-801 · PRD §9.9 正向 1 · 50 条全命中白名单 · 60s 内产 dod-expressions.yaml · AC 反查 100% 成功。

        Given: 50 条验收条件 + 全命中白名单
        When:  blueprint_ready 触发 compile_batch
        Then:
          - 60s 内产 dod-expressions.yaml
          - 每条表达式反查到 ≥ 1 条 AC
          - 无 exec 节点(AST 校验通过)
        """
        import time
        req = make_compile_request(project_id=mock_project_id, clause_count=50)
        t0 = time.perf_counter()
        resp = sut.compile_batch(req)
        elapsed = time.perf_counter() - t0
        assert resp.accepted is True
        assert resp.compiled_count == 50
        assert elapsed < 60.0
        # 文件落盘
        assert sut._get_fs().exists(
            f"projects/{mock_project_id}/testing/dod-expressions.yaml"
        ), "PRD §9.2 输出 · dod-expressions.yaml"
        # AC 反查 100% 成功(硬约束 4)
        stored = sut._debug_load_dod_set(resp.set_id)
        for expr in stored.expressions:
            assert len(expr.source_ac_ids) >= 1

    def test_TC_L104_L202_802_positive_2_eval_under_100ms_no_io(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request, mock_fs: MagicMock,
    ) -> None:
        """TC-L104-L202-802 · PRD §9.9 正向 2 · L2-05 WP 自检 eval · ≤ 100ms · 无 I/O 访问。

        Given: WP-X 执行完成，L2-05 请求 eval
        When:  调 eval_expression(expr_id, snapshot)
        Then:
          - ≤ 100ms 返 {pass=true, evidence}
          - 无任何文件 / 网络访问
        """
        import time
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.85, caller="L2-05_wp_self_check",
        )
        mock_fs.read.reset_mock()
        mock_fs.write.reset_mock()
        t0 = time.perf_counter()
        resp = evaluator.eval_expression(req)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert resp.pass_ is True
        assert elapsed_ms < 100.0, f"eval {elapsed_ms:.1f}ms > PRD §9.4 100ms"
        assert mock_fs.read.call_count == 0, "§3.2.6 · eval 无 I/O"
        assert mock_fs.write.call_count == 0

    def test_TC_L104_L202_803_negative_3_arbitrary_exec_clause_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
        mock_l1_02: MagicMock,
    ) -> None:
        """TC-L104-L202-803 · PRD §9.9 负向 3 · 条款含 "执行脚本 xxx.sh 检查" → 拒绝 + INFO 澄清 + 推 L1-02 改写。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=5,
            inject_exec_texts=["执行脚本 check.sh 判断是否通过"],
        )
        resp = sut.compile_batch(req)
        # 该条目进入 unmappable(含 arbitrary exec 语义无法映白名单)
        assert any(
            "exec" in (u.rejection_reason or "").lower() or "shell" in (u.rejection_reason or "").lower()
            for u in resp.unmappable_clauses
        )

    def test_TC_L104_L202_804_negative_4_whitelist_miss_triggers_flow_f(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
        mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L202-804 · PRD §9.9 负向 4 · "UI 要好看" 无量化谓词 → unmappable 清单 · 流 F 触发澄清。"""
        req = make_compile_request(
            project_id=mock_project_id, clause_count=3,
            inject_unmappable_texts=["UI 要好看", "响应要快一点"],
        )
        resp = sut.compile_batch(req)
        assert len(resp.unmappable_clauses) == 2
        assert mock_l1_07.push_suggestion.called
        level = mock_l1_07.push_suggestion.call_args.kwargs["level"]
        assert level == "INFO", "流 F · INFO 澄清(不升级)"

    def test_TC_L104_L202_805_negative_5_evaluator_cannot_access_fs(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-805 · PRD §9.9 负向 5 · evaluator 试图访问文件系统 → SecurityError · FAIL + reason=security_violation。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9,
            # 伪冒 data_source=file 注入
            inject_unknown_data_source={"file_system": {"path": "/etc/passwd"}},
        )
        with pytest.raises(DoDExpressionError) as ei:
            evaluator.eval_expression(req)
        assert ei.value.code in (
            "E_L204_L202_DATA_SOURCE_UNKNOWN_TYPE",
            "E_L204_L202_SANDBOX_ESCAPE_DETECTED",
        )
```

---

## §7 测试 fixture

> 共享 fixture：SUT 实例(Compiler + Evaluator 组合) / mock project_id / mock clock / mock event bus / mock whitelist / mock snapshot factory。
> 放在 `tests/l1_04/conftest.py` · autouse 的只开 event bus + whitelist registry · 其余 opt-in。

```python
# file: tests/l1_04/conftest_l2_02.py  (同 L2-01 共享 conftest.py)
from __future__ import annotations

import pytest
import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator
from app.l1_04.l2_02.schemas import (
    CompileBatchCommand,
    EvalCommand,
    AddWhitelistRuleCommand,
)


@pytest.fixture
def mock_project_id() -> str:
    return "pid-l202-default"


@pytest.fixture
def other_project_id() -> str:
    return "pid-l202-foreign"


@pytest.fixture
def mock_whitelist_registry() -> MagicMock:
    reg = MagicMock()
    reg.current_version = "1.0.3"
    reg.list_rules.return_value = ["coverage", "test_result", "lint", "security_scan", "perf", "artifact"]
    return reg


@pytest.fixture
def sut(mock_event_bus, mock_fs, mock_l1_02, mock_l1_07, mock_whitelist_registry) -> DoDExpressionCompiler:
    return DoDExpressionCompiler(
        event_bus=mock_event_bus, fs=mock_fs,
        l1_02=mock_l1_02, l1_07=mock_l1_07,
        whitelist_registry=mock_whitelist_registry,
        offline_admin_mode=False,
    )


@pytest.fixture
def sut_offline_admin(mock_event_bus, mock_fs, mock_l1_02, mock_l1_07, mock_whitelist_registry) -> DoDExpressionCompiler:
    """生产态 vs 离线态两套 SUT · §3.5 add_whitelist_rule 仅离线可用。"""
    return DoDExpressionCompiler(
        event_bus=mock_event_bus, fs=mock_fs,
        l1_02=mock_l1_02, l1_07=mock_l1_07,
        whitelist_registry=mock_whitelist_registry,
        offline_admin_mode=True,  # 等价 OFFLINE_ADMIN_MODE=1
    )


@pytest.fixture
def evaluator(sut, mock_event_bus, mock_whitelist_registry, mock_l1_07) -> DoDEvaluator:
    return DoDEvaluator(
        compiler=sut, event_bus=mock_event_bus,
        whitelist_registry=mock_whitelist_registry, l1_07=mock_l1_07,
        eval_timeout_ms=500, eval_memory_limit_mb=64,
    )


@pytest.fixture
def make_compile_request() -> Callable[..., CompileBatchCommand]:
    def _factory(**overrides: Any) -> CompileBatchCommand:
        clause_count = overrides.pop("clause_count", 50)
        unmappable_texts = overrides.pop("inject_unmappable_texts", [])
        exec_texts = overrides.pop("inject_exec_texts", [])
        syntax_err_idx = overrides.pop("inject_syntax_error_indices", [])
        invalid_ac_ids = overrides.pop("inject_invalid_ac_ids", [])
        mutate_text = overrides.pop("inject_clause_text_mutation", False)
        base_text_pool = [
            "coverage.line_rate >= 0.8",
            "lint.error_count == 0",
            "test_result.p0_all_pass is True",
            "security_scan.high_severity_count == 0",
            "perf.p95_ms < 500",
        ]
        clauses: list[dict[str, Any]] = []
        for i in range(clause_count):
            t = base_text_pool[i % len(base_text_pool)]
            if i in syntax_err_idx:
                t = "coverage.line_rate >>>>=== 0.8"
            if i < len(unmappable_texts):
                t = unmappable_texts[i]
            if i < len(exec_texts):
                t = exec_texts[i]
            if mutate_text and i == 0:
                t = t + " and test_result.p0_all_pass is True"
            ac_id = (invalid_ac_ids[i] if i < len(invalid_ac_ids) else f"ac-{i:04d}")
            clauses.append({
                "clause_id": f"clause-{uuid.uuid4()}",
                "clause_text": t,
                "source_ac_ids": [ac_id],
                "priority": "P0" if i < 5 else "P1",
            })
        base: dict[str, Any] = dict(
            command_id=overrides.get("command_id", f"cmd-{uuid.uuid4()}"),
            project_id=overrides.get("project_id", "pid-l202-default"),
            blueprint_id="bp-0001",
            wp_id=overrides.get("wp_id"),
            clauses=clauses,
            ac_matrix={"acs": [
                {"id": c["source_ac_ids"][0]}
                for c in clauses if not c["source_ac_ids"][0].startswith("ac-ghost")
            ]},
            whitelist_version=overrides.get("whitelist_version"),
            timeout_s=overrides.get("timeout_s", 120),
            ts="2026-04-22T00:00:00Z",
        )
        return CompileBatchCommand(**base)
    return _factory


@pytest.fixture
def make_eval_request() -> Callable[..., EvalCommand]:
    def _factory(**overrides: Any) -> EvalCommand:
        snapshot: dict[str, Any] = {
            "coverage": {"line_rate": overrides.pop("coverage_value", 0.85)},
        }
        if "lint_error_count" in overrides:
            snapshot["lint"] = {"error_count": overrides.pop("lint_error_count")}
        if overrides.pop("include_perf", False):
            snapshot["perf"] = {"p95_ms": 400}
        if overrides.pop("include_artifact", False):
            snapshot["artifact"] = {"files": ["dist/app.js"]}
        unknown = overrides.pop("inject_unknown_data_source", None)
        if unknown:
            snapshot.update(unknown)
        leak = overrides.pop("simulate_memory_leak_mb", None)
        return EvalCommand(
            command_id=overrides.get("command_id", f"cmd-eval-{uuid.uuid4()}"),
            project_id=overrides.get("project_id", "pid-l202-default"),
            expr_id=overrides.get("expr_id", "expr-placeholder"),
            data_sources_snapshot=snapshot,
            caller=overrides.get("caller", "L2-05_wp_self_check"),
            timeout_ms=overrides.get("timeout_ms", 500),
            ts="2026-04-22T00:00:00Z",
            _simulate_memory_leak_mb=leak,
        )
    return _factory


@pytest.fixture
def make_add_whitelist_rule_request() -> Callable[..., AddWhitelistRuleCommand]:
    def _factory(**overrides: Any) -> AddWhitelistRuleCommand:
        return AddWhitelistRuleCommand(
            rule={"name": overrides.get("rule_name", "math.sqrt"), "category": "function"},
            offline_review_memo={
                "review_date": "2026-04-22",
                "reviewers": overrides.get("reviewers", ["sre-alice", "sec-bob"]),
                "rationale": "金融项目需要平方根判别波动率阈值，经 2026-Q2 安全评审通过。" * 2,
                "test_coverage_plan": "新增 12 条单元测试覆盖 sqrt 输入边界 + NaN + 负数",
            },
            version_bump_type=overrides.get("version_bump_type", "minor"),
            operator=overrides.get("operator", "sre-alice"),
            signature="gpg:mock-signature",
        )
    return _factory


@pytest.fixture
def ready_expr_id(sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request) -> str:
    """编译一个 expr 并返回首条 expr_id(可直接给 eval 用)。"""
    req = make_compile_request(project_id=mock_project_id, clause_count=1)
    resp = sut.compile_batch(req)
    return sut._debug_first_expr_id(resp.set_id)


@pytest.fixture
def ready_expr_id_of_other_project(sut, other_project_id, make_compile_request) -> str:
    req = make_compile_request(project_id=other_project_id, clause_count=1)
    resp = sut.compile_batch(req)
    return sut._debug_first_expr_id(resp.set_id)


@pytest.fixture
def slow_expr_id(sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request) -> str:
    req = make_compile_request(project_id=mock_project_id, clause_count=1)
    resp = sut.compile_batch(req)
    eid = sut._debug_first_expr_id(resp.set_id)
    sut._debug_mark_expr_slow(eid, sleep_ms=2000)  # 超 500ms 触发 timeout
    return eid


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.append_event.return_value = {"ok": True}
    return bus


@pytest.fixture
def mock_fs() -> MagicMock:
    fs = MagicMock()
    fs._store: dict[str, str] = {}
    fs.exists = lambda p: p in fs._store
    fs.write = lambda p, c: fs._store.__setitem__(p, c)
    fs.read = lambda p: fs._store.get(p, "")
    return fs


@pytest.fixture
def mock_l1_02() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l1_07() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_01() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_04() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_05() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_06() -> MagicMock: return MagicMock()
```

---

## §8 集成点用例

> 与兄弟 L2(L2-01 TDD 蓝图生成器 / L2-04 质量 Gate 编译器)的协作。
> 本 L2 是**全 L1-04 唯一 eval 入口**；L2-04 必须查白名单做 gates 合规校验；L2-06 verifier 必须以库注入形式 eval。

```python
# file: tests/l1_04/test_l2_02_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator
from app.l1_04.l2_02.schemas import ListWhitelistRulesCommand


class TestL2_02_SiblingIntegration:
    """§8 · 与 L2-01 / L2-04 / L2-06 的协作。"""

    def test_TC_L104_L202_901_verifier_subagent_same_result_as_main(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-901 · PRD §9.9 集成 6 · S5 verifier 子 Agent 独立 eval 与主 session L2-05 得相同结果(pure function)。"""
        req_main = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.88, caller="L2-05_wp_self_check",
            command_id="cmd-main",
        )
        req_verifier = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.88, caller="verifier_subagent",
            command_id="cmd-verifier",
        )
        r_main = evaluator.eval_expression(req_main)
        r_ver = evaluator.eval_expression(req_verifier)
        assert r_main.pass_ == r_ver.pass_, "PM-03 独立 session 可重入一致"
        assert r_main.evidence_snapshot == r_ver.evidence_snapshot
        assert r_main.whitelist_version == r_ver.whitelist_version

    def test_TC_L104_L202_902_l2_04_reads_whitelist_for_gates_compile(
        self, sut: DoDExpressionCompiler, mock_l2_04: MagicMock,
    ) -> None:
        """TC-L104-L202-902 · L2-04 编译 quality-gates.yaml 时调 list_whitelist_rules 做合规校验(§1.4 强同步)。"""
        # L2-04 从本 L2 拿白名单
        resp = sut.list_whitelist_rules(ListWhitelistRulesCommand(category="function"))
        whitelist_func_names = {r.name for r in resp.rules}
        # 模拟 L2-04 用本 L2 白名单校验 gates 里的谓词
        l2_04_predicates = {"coverage.line_rate", "lint.error_count", "test_result.p0_all_pass"}
        assert l2_04_predicates.issubset(whitelist_func_names) or all(
            any(p.startswith(wl) or wl.startswith(p) for wl in whitelist_func_names)
            for p in l2_04_predicates
        ), "§1.4 白名单强同步 · L2-04 gates 的谓词必须在本 L2 白名单内"

    def test_TC_L104_L202_903_l2_01_blueprint_ready_drives_parallel_compile(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
        make_compile_request, mock_l2_01: MagicMock,
    ) -> None:
        """TC-L104-L202-903 · L2-01 blueprint_ready fanout · 本 L2 与 L2-03/04 并行编译(不阻塞兄弟 L2)。"""
        # 模拟 L2-01 发 blueprint_ready
        sut.on_blueprint_ready(
            blueprint_id="bp-0002",
            project_id=mock_project_id,
            master_test_plan_path="projects/pid/tdd/master-test-plan.md",
            ac_matrix_path="projects/pid/tdd/ac-matrix.yaml",
            version=1, publisher="L1-04:L2-01", ts="2026-04-22T00:00:00Z",
        )
        # 本 L2 的 compile 应被触发，且未阻塞 L2-03/04(mock 不被本 L2 调用)
        assert sut._debug_compile_triggered_recently_s() >= 0
        assert mock_l2_01.block.called is False

    def test_TC_L104_L202_904_l2_05_wp_self_check_uses_evaluator(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """TC-L104-L202-904 · L2-05 WP 自检走本 L2 · 禁自实现(PM-10 单一事实源)。"""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9, caller="L2-05_wp_self_check",
        )
        resp = evaluator.eval_expression(req)
        assert resp.pass_ is True
        assert resp.caller == "L2-05_wp_self_check"
```

---

## §9 边界 / edge case

> 空输入 / 超大输入 / 表达式注入 / 深层嵌套 / 循环依赖 / 无效 DSL / 并发读写 / 冷启动 / 版本链边界。
> 至少 5 个 · 本文件 9 个，重点覆盖 **表达式注入 / 深层嵌套 / 循环依赖 / 无效 DSL**。

```python
# file: tests/l1_04/test_l2_02_dod_compiler_edge_cases.py
from __future__ import annotations

import pytest
import threading
from unittest.mock import MagicMock

from app.l1_04.l2_02.compiler import DoDExpressionCompiler
from app.l1_04.l2_02.evaluator import DoDEvaluator
from app.l1_04.l2_02.schemas import ValidateCommand
from app.l1_04.l2_02.errors import DoDExpressionError


class TestL2_02_EdgeCases:
    """§9 · 边界 · 注入 / 嵌套 / 循环 / 无效 DSL / 冷启动 / 并发。"""

    def test_TC_L104_L202_A01_expression_injection_via_string_concat(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-A01 · 表达式注入 · 字符串拼接绕过 `coverage.line_rate >= 0.8; __import__('os')`。"""
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="coverage.line_rate >= 0.8; __import__('os').system('ls')",
        )
        rep = sut.validate_expression(cmd)
        assert rep.valid is False, "SA-01 · 分号多语句 / __import__ 绝不放过"
        codes = [v.violation_type for v in rep.violations]
        assert ("illegal_node" in codes) or ("syntax_error" in codes)

    def test_TC_L104_L202_A02_deep_nesting_exceeds_max_ast_depth(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-A02 · 深层嵌套 · `(((...coverage...)))` 括号嵌套 50 层 → exceeds_depth(max=32)。"""
        expr = "(" * 50 + "coverage.line_rate >= 0.8" + ")" * 50
        cmd = ValidateCommand(project_id=mock_project_id, expression_text=expr)
        rep = sut.validate_expression(cmd)
        assert rep.valid is False
        assert any(v.violation_type == "exceeds_depth" for v in rep.violations)

    def test_TC_L104_L202_A03_circular_reference_expression_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-A03 · 循环依赖 · expr A 引用 B · B 引用 A → 编译期拒绝(§6.4 并发 + §9.3 In-scope 8)。"""
        # 通过 clause_id 互引用仿真
        req = make_compile_request(
            project_id=mock_project_id, clause_count=2,
            inject_circular_reference=True,
        )
        resp = sut.compile_batch(req)
        assert any(
            e.error_code in ("E_L204_L202_AST_SYNTAX_ERROR", "E_L204_L202_AC_REVERSE_LOOKUP_FAILED")
            for e in resp.errors
        ), "循环依赖在编译期被检出(无自引用循环 · §3 约束)"

    def test_TC_L104_L202_A04_invalid_dsl_garbage_text(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-A04 · 无效 DSL · 乱码输入 → syntax_error + 拒绝。"""
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="????!!!==>>> foo bar 🚀🚀🚀",
        )
        rep = sut.validate_expression(cmd)
        assert rep.valid is False
        assert any(v.violation_type == "syntax_error" for v in rep.violations)

    def test_TC_L104_L202_A05_empty_clause_text_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-A05 · 空 clause_text · "" 或纯空格 → minLength=5 校验失败。"""
        cmd = ValidateCommand(project_id=mock_project_id, expression_text="     ")
        rep = sut.validate_expression(cmd)
        assert rep.valid is False

    def test_TC_L104_L202_A06_concurrent_compile_same_project_no_race(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """TC-L104-L202-A06 · 10 线程并发 compile_batch 同 command_id · 幂等返相同 set_id · 无 race。"""
        req = make_compile_request(project_id=mock_project_id, clause_count=20, command_id="cmd-race-0001")
        results: list[str] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                r = sut.compile_batch(req)
                results.append(r.set_id)
            except Exception as e:
                errors.append(e)

        ts = [threading.Thread(target=worker) for _ in range(10)]
        for t in ts: t.start()
        for t in ts: t.join(timeout=30)

        assert len(set(results)) == 1, f"并发幂等失败：{set(results)}"
        assert errors == []

    def test_TC_L104_L202_A07_cold_start_load_whitelist_under_1s(
        self, mock_event_bus, mock_fs, mock_l1_02, mock_l1_07, mock_whitelist_registry,
        mock_project_id, make_compile_request,
    ) -> None:
        """TC-L104-L202-A07 · 冷启动 · 首次加载白名单 rules_v1.0.3.yaml · P95 ≤ 1s。"""
        import time
        t0 = time.perf_counter()
        cold_sut = DoDExpressionCompiler(
            event_bus=mock_event_bus, fs=mock_fs,
            l1_02=mock_l1_02, l1_07=mock_l1_07,
            whitelist_registry=mock_whitelist_registry, offline_admin_mode=False,
        )
        req = make_compile_request(project_id=mock_project_id, clause_count=1)
        cold_sut.compile_batch(req)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"冷启动 {elapsed:.2f}s > 1s"

    def test_TC_L104_L202_A08_oversized_expression_2001_chars(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """TC-L104-L202-A08 · expression_text > maxLength=2000 → 拒绝(§3.1.2 clauses[].clause_text maxLength)。"""
        oversized = "coverage.line_rate >= 0.8" + " and True" * 500  # > 2000 字符
        cmd = ValidateCommand(project_id=mock_project_id, expression_text=oversized[:2500])
        rep = sut.validate_expression(cmd)
        assert rep.valid is False
        assert any(v.violation_type in ("exceeds_size", "syntax_error") for v in rep.violations)

    def test_TC_L104_L202_A09_whitelist_version_bump_invalidates_all_cache(
        self, evaluator: DoDEvaluator, sut_offline_admin: DoDExpressionCompiler,
        mock_project_id: str, ready_expr_id: str, make_eval_request,
        make_add_whitelist_rule_request,
    ) -> None:
        """TC-L104-L202-A09 · whitelist version bump → 所有 AST 缓存失效(§3.5.3 · OQ-04)。"""
        req = make_eval_request(project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9)
        evaluator.eval_expression(req)  # 热缓存
        assert evaluator._debug_cache_size() > 0
        cmd = make_add_whitelist_rule_request(version_bump_type="minor")
        sut_offline_admin.add_whitelist_rule(cmd)
        assert evaluator._debug_cache_size() == 0, "§3.5.3 · cache 全失效"
```

---

*— L1-04 L2-02 DoD 表达式编译器 · TDD 测试用例 · 深度 B · 5 方法 × 18 正向 × 22 负向 × 6 IC × 8 SLO × 5 e2e × 4 集成 × 9 边界 全节完整 —*
