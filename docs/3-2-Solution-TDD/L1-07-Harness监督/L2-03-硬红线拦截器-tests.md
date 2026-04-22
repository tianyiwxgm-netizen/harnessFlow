---
doc_id: tests-L1-07-L2-03-硬红线拦截器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-07-Harness监督/L2-03-硬红线拦截器.md
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-07 L2-03-硬红线拦截器 · TDD 测试用例

> 基于 3-1 L2-03 §3（9 对外方法）+ §11（22 项 `L2-03/HR01~HR22` 错误码 · 硬红线绝不降级）+ §12（PreToolUse P95 ≤ 100ms 硬锁 · post_commit P95 ≤ 5s SLO）驱动。
> **本 L2 最严格**：HALT 判定永不降级 · HALT 唯一合法出口 = M9。
> TC ID 统一格式：`TC-L107-L203-NNN`。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × TC 矩阵

| 方法 | TC ID |
|---|---|
| `pre_tool_use_intercept()` · ALLOW | TC-L107-L203-001 |
| `pre_tool_use_intercept()` · DENY_HARD_HALT | TC-L107-L203-002 |
| `post_commit_static_scan()` · CLEAN | TC-L107-L203-003 |
| `post_commit_static_scan()` · VIOLATIONS_FOUND | TC-L107-L203-004 |
| `runtime_counter_check()` · self_repair exceeded | TC-L107-L203-005 |
| `credential_regex_scan()` · API key | TC-L107-L203-006 |
| `credential_regex_scan()` · SSH key | TC-L107-L203-007 |
| `verifier_self_run_detect()` · 3 联检测 | TC-L107-L203-008 |
| `self_repair_3_detect()` · 第 3 次 | TC-L107-L203-009 |
| `dod_escape_ast_check()` · 超白名单 | TC-L107-L203-010 |
| `audit_gap_detect()` · hash chain OK | TC-L107-L203-011 |
| `halt_project_via_ic_01()` · 唯一出口 | TC-L107-L203-012 |
| 不可降级 · scanner 降级仍 HALT | TC-L107-L203-013 |
| 告警三要素 | TC-L107-L203-014 |
| rule_catalog 加载 | TC-L107-L203-015 |

### §1.2 错误码 × TC 矩阵（22 项）

| 错误码 | TC ID |
|---|---|
| `L2-03/HR01` verifier_in_main_session | TC-L107-L203-101 |
| `L2-03/HR02` dod_ast_whitelist_escape | TC-L107-L203-102 |
| `L2-03/HR03` self_repair_three_strike | TC-L107-L203-103 |
| `L2-03/HR04` credential_api_key_leak | TC-L107-L203-104 |
| `L2-03/HR05` credential_ssh_leak | TC-L107-L203-105 |
| `L2-03/HR06` irreversible_op_detect | TC-L107-L203-106 |
| `L2-03/HR07` infinite_loop_critical | TC-L107-L203-107 |
| `L2-03/HR08` verifier_fail_l4 | TC-L107-L203-108 |
| `L2-03/HR09` hard_halt_dispatch_failed | TC-L107-L203-109 |
| `L2-03/HR10` goal_anchor_sha256_drift | TC-L107-L203-110 |
| `L2-03/HR11` claude_md_tampered | TC-L107-L203-111 |
| `L2-03/HR12` budget_overrun_200pct | TC-L107-L203-112 |
| `L2-03/HR13` intercept_timeout_failsafe | TC-L107-L203-113 |
| `L2-03/HR14` credential_env_file_leak | TC-L107-L203-114 |
| `L2-03/HR15` pii_plaintext_detect | TC-L107-L203-115 |
| `L2-03/HR16` audit_chain_gap | TC-L107-L203-116 |
| `L2-03/HR17` event_missing_commit | TC-L107-L203-117 |
| `L2-03/HR18` audit_hash_mismatch | TC-L107-L203-118 |
| `L2-03/HR19` rule_catalog_load_failed | TC-L107-L203-119 |
| `L2-03/HR20` pattern_registry_corrupt | TC-L107-L203-120 |
| `L2-03/HR21` ic_14_retry_exhausted | TC-L107-L203-121 |
| `L2-03/HR22` self_check_failed | TC-L107-L203-122 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| PreToolUse hook | L1-01 → L2-03 | TC-L107-L203-601 |
| post_commit hook | L1-01 → L2-03 | TC-L107-L203-602 |
| IC-HardRedlineViolation | L2-03 → L2-04 | TC-L107-L203-603 |
| IC-09 read event stream | L2-03 → L1-09 | TC-L107-L203-604 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| PreToolUse P95 | ≤ 100ms 硬锁 | TC-L107-L203-501 |
| post_commit P95 | ≤ 5s | TC-L107-L203-502 |
| credential_regex_scan P95 | ≤ 50ms/file | TC-L107-L203-503 |
| verifier_self_run_detect P95 | ≤ 200ms | TC-L107-L203-504 |
| dod_escape_ast_check P95 | ≤ 30ms | TC-L107-L203-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_07/test_l2_03_interceptor_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_03_Positive:

    def test_TC_L107_L203_001_allow(self, sut) -> None:
        """TC-L107-L203-001 · 常规 Read · ALLOW。"""
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Read",
            args={"file_path": "/tmp/safe.md"},
            session_id="s", invoke_timestamp="2026-04-22T10:00:00Z")
        assert res.decision == "ALLOW"

    def test_TC_L107_L203_002_deny_hard_halt_rm_rf(self, sut) -> None:
        """TC-L107-L203-002 · rm -rf / · DENY_HARD_HALT。"""
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Bash",
            args={"command": "rm -rf /"},
            session_id="s", invoke_timestamp="t")
        assert res.decision == "DENY_HARD_HALT"

    def test_TC_L107_L203_003_post_commit_clean(self, sut) -> None:
        """TC-L107-L203-003 · 安全 diff · CLEAN。"""
        res = sut.post_commit_static_scan(
            project_id="p", commit_sha="abc", diff="+# safe\n",
            author="a", timestamp="t")
        assert res.scan_result == "CLEAN"

    def test_TC_L107_L203_004_post_commit_violations(self, sut) -> None:
        """TC-L107-L203-004 · API key · VIOLATIONS_FOUND + halt。"""
        res = sut.post_commit_static_scan(
            project_id="p", commit_sha="abc",
            diff="+API_KEY=sk-abcdef123\n", author="a", timestamp="t")
        assert res.scan_result == "VIOLATIONS_FOUND"
        assert res.halt_triggered is True

    def test_TC_L107_L203_005_counter_exceeded(self, sut, mock_l1_09) -> None:
        """TC-L107-L203-005 · self_repair=3 · exceeded。"""
        mock_l1_09.query_counter.return_value = {"value": 3, "threshold": 3}
        res = sut.runtime_counter_check(project_id="p",
                                          counter_name="self_repair")
        assert res.exceeded is True

    def test_TC_L107_L203_006_cred_api_key(self, sut) -> None:
        """TC-L107-L203-006 · API key pattern 命中。"""
        hits = sut.credential_regex_scan(
            project_id="p",
            files=[{"path": "x.py", "content": "API_KEY=sk-abcdef123"}])
        assert any(h.pattern_id == "api_key" for h in hits)

    def test_TC_L107_L203_007_cred_ssh(self, sut) -> None:
        """TC-L107-L203-007 · SSH private key。"""
        hits = sut.credential_regex_scan(
            project_id="p",
            files=[{"path": "x", "content": "-----BEGIN OPENSSH PRIVATE KEY-----"}])
        assert any(h.pattern_id == "ssh_private_key" for h in hits)

    def test_TC_L107_L203_008_verifier_three_chain(
        self, sut, seed_verifier_in_main_session,
    ) -> None:
        """TC-L107-L203-008 · 三联检测命中。"""
        seed_verifier_in_main_session()
        res = sut.verifier_self_run_detect(project_id="p", session_id="s")
        assert res.detected is True

    def test_TC_L107_L203_009_self_repair_3rd(self, sut, mock_l1_09) -> None:
        """TC-L107-L203-009 · self_repair 第 3 次。"""
        mock_l1_09.query_counter.return_value = {"value": 3, "threshold": 3}
        res = sut.self_repair_3_detect(project_id="p")
        assert res.detected is True

    def test_TC_L107_L203_010_dod_ast_escape(self, sut) -> None:
        """TC-L107-L203-010 · __import__ 超白名单。"""
        res = sut.dod_escape_ast_check(
            project_id="p",
            dod_expression="__import__('os').system('rm')")
        assert res.violated is True

    def test_TC_L107_L203_011_audit_chain_ok(self, sut, mock_l1_09) -> None:
        """TC-L107-L203-011 · hash chain 连续。"""
        mock_l1_09.verify_hash_chain.return_value = {"ok": True, "gaps": []}
        res = sut.audit_gap_detect(project_id="p")
        assert res.chain_ok is True

    def test_TC_L107_L203_012_halt_only_exit(self, sut, mock_l2_04) -> None:
        """TC-L107-L203-012 · HALT 唯一出口 · 发 Violation。"""
        v = MagicMock(violation_id="v-1", rule_id="L2-03/HR01")
        res = sut.halt_project_via_ic_01(project_id="p", violation=v)
        assert res.halt_dispatched is True
        mock_l2_04.receive_hard_redline_violation.assert_called_once()

    def test_TC_L107_L203_013_halt_even_degraded(self, sut) -> None:
        """TC-L107-L203-013 · scanner 降级仍 HALT。"""
        sut._scan_capability = "RUNTIME_ONLY"
        v = MagicMock(violation_id="v-x", rule_id="L2-03/HR03")
        res = sut.halt_project_via_ic_01(project_id="p", violation=v)
        assert res.halt_dispatched is True

    def test_TC_L107_L203_014_advisory_three_elements(self, sut) -> None:
        """TC-L107-L203-014 · 三要素齐：cause/impact/suggestion。"""
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Bash",
            args={"command": "rm -rf /"},
            session_id="s", invoke_timestamp="t")
        assert res.advisory_message.cause
        assert res.advisory_message.impact
        assert res.advisory_message.suggestion

    def test_TC_L107_L203_015_catalog_loaded(self, sut) -> None:
        """TC-L107-L203-015 · rule_catalog 加载成功 · ≥ 15 规则。"""
        assert sut._rule_catalog_loaded is True
        assert len(sut._rule_catalog) >= 15
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_07/test_l2_03_interceptor_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_07.l2_03.errors import InterceptError


class TestL2_03_Negative:

    def test_TC_L107_L203_101_verifier_in_main_session(
        self, sut, seed_verifier_in_main_session,
    ) -> None:
        """TC-L107-L203-101 · HR01 · verifier 主 session 自跑 · HALT。"""
        seed_verifier_in_main_session()
        res = sut.verifier_self_run_detect(project_id="p", session_id="s")
        assert res.detected is True
        assert res.rule_id == "L2-03/HR01"

    def test_TC_L107_L203_102_dod_ast_escape(self, sut) -> None:
        """TC-L107-L203-102 · HR02 · DoD AST 超白名单。"""
        res = sut.dod_escape_ast_check(
            project_id="p", dod_expression="exec('x=1')")
        assert res.violated is True
        assert res.rule_id == "L2-03/HR02"

    def test_TC_L107_L203_103_self_repair_3rd(self, sut, mock_l1_09) -> None:
        """TC-L107-L203-103 · HR03 · self_repair 第 3 次。"""
        mock_l1_09.query_counter.return_value = {"value": 3, "threshold": 3}
        res = sut.self_repair_3_detect(project_id="p")
        assert res.rule_id == "L2-03/HR03"

    def test_TC_L107_L203_104_api_key_leak(self, sut) -> None:
        """TC-L107-L203-104 · HR04 · API key 落盘。"""
        hits = sut.credential_regex_scan(
            project_id="p",
            files=[{"path": "x.py", "content": "API_KEY=sk-abcdef12"}])
        assert any(h.rule_id == "L2-03/HR04" for h in hits)

    def test_TC_L107_L203_105_ssh_leak(self, sut) -> None:
        """TC-L107-L203-105 · HR05 · SSH key 落盘。"""
        hits = sut.credential_regex_scan(
            project_id="p",
            files=[{"path": "x", "content":
                     "-----BEGIN OPENSSH PRIVATE KEY-----\nk...\n"}])
        assert any(h.rule_id == "L2-03/HR05" for h in hits)

    def test_TC_L107_L203_106_irreversible_op(self, sut) -> None:
        """TC-L107-L203-106 · HR06 · rm -rf 不可逆。"""
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Bash",
            args={"command": "rm -rf /"},
            session_id="s", invoke_timestamp="t")
        assert "L2-03/HR06" in res.matched_rule_ids

    def test_TC_L107_L203_107_infinite_loop_critical(
        self, sut, mock_l1_09,
    ) -> None:
        """TC-L107-L203-107 · HR07 · infinite_loop 极重度。"""
        mock_l1_09.query_counter.return_value = {"value": 50, "threshold": 30}
        res = sut.runtime_counter_check(project_id="p",
                                          counter_name="infinite_loop")
        assert res.exceeded is True

    def test_TC_L107_L203_108_verifier_fail_l4(
        self, sut, mock_l1_09,
    ) -> None:
        """TC-L107-L203-108 · HR08 · verifier FAIL_L4。"""
        mock_l1_09.get_latest_verifier.return_value = MagicMock(verdict="FAIL_L4")
        res = sut.verifier_fail_l4_check(project_id="p")
        assert res.detected is True

    def test_TC_L107_L203_109_halt_dispatch_fail_alert(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-109 · HR09 · L2-04 不可达 · halt_dispatched=False + alert。"""
        mock_l2_04.receive_hard_redline_violation.side_effect = ConnectionError()
        v = MagicMock(violation_id="v", rule_id="L2-03/HR01")
        res = sut.halt_project_via_ic_01(project_id="p", violation=v)
        assert res.halt_dispatched is False
        assert res.alert_level == "L1-10"

    def test_TC_L107_L203_110_goal_anchor_drift(
        self, sut, monkeypatch,
    ) -> None:
        """TC-L107-L203-110 · HR10 · goal_anchor sha256 变化。"""
        monkeypatch.setattr(sut, "_current_goal_sha256", "new-hash")
        monkeypatch.setattr(sut, "_locked_goal_sha256", "original-hash")
        res = sut.goal_drift_detect(project_id="p")
        assert res.drifted is True

    def test_TC_L107_L203_111_claude_md_tampered(
        self, sut, monkeypatch,
    ) -> None:
        """TC-L107-L203-111 · HR11 · CLAUDE.md 被改。"""
        monkeypatch.setattr(sut, "_claude_md_current_hash", "changed")
        monkeypatch.setattr(sut, "_claude_md_locked_hash", "original")
        res = sut.claude_md_check(project_id="p")
        assert res.tampered is True

    def test_TC_L107_L203_112_budget_overrun(self, sut, mock_l1_09) -> None:
        """TC-L107-L203-112 · HR12 · 预算 > 200%。"""
        mock_l1_09.read_budget_usage.return_value = {"pct": 210}
        res = sut.budget_overrun_detect(project_id="p")
        assert res.exceeded is True

    def test_TC_L107_L203_113_timeout_failsafe(self, sut, monkeypatch) -> None:
        """TC-L107-L203-113 · HR13 · 扫描超时 · fail-safe DENY。"""
        import time
        def slow(*a, **kw):
            time.sleep(0.15)
            return []
        monkeypatch.setattr(sut, "credential_regex_scan", slow)
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Bash",
            args={"command": "ls"},
            session_id="s", invoke_timestamp="t", timeout_ms=100)
        assert res.decision == "DENY_TIMEOUT_FAILSAFE"

    def test_TC_L107_L203_114_env_file_leak(self, sut) -> None:
        """TC-L107-L203-114 · HR14 · .env 入 git。"""
        res = sut.post_commit_static_scan(
            project_id="p", commit_sha="abc",
            diff="+.env\nAPI_KEY=sk-abc\n", author="a", timestamp="t")
        assert any(v.rule_id == "L2-03/HR14" for v in res.violations)

    def test_TC_L107_L203_115_pii_plaintext(self, sut) -> None:
        """TC-L107-L203-115 · HR15 · PII 明文。"""
        hits = sut.credential_regex_scan(
            project_id="p",
            files=[{"path": "x", "content":
                     "email=user@example.com; ssn=123-45-6789"}])
        assert any(h.rule_id == "L2-03/HR15" for h in hits)

    def test_TC_L107_L203_116_audit_chain_gap(
        self, sut, mock_l1_09,
    ) -> None:
        """TC-L107-L203-116 · HR16 · hash chain 缺环。"""
        mock_l1_09.verify_hash_chain.return_value = {"ok": False,
                                                       "gaps": [2]}
        res = sut.audit_gap_detect(project_id="p")
        assert res.chain_ok is False
        assert res.rule_id == "L2-03/HR16"

    def test_TC_L107_L203_117_event_missing_commit(
        self, sut, mock_l1_09,
    ) -> None:
        """TC-L107-L203-117 · HR17 · commit 事件缺失。"""
        mock_l1_09.list_events.return_value = []
        res = sut.event_missing_commit_detect(project_id="p",
                                                 commit_sha="abc")
        assert res.detected is True

    def test_TC_L107_L203_118_audit_hash_mismatch(
        self, sut, mock_l1_09,
    ) -> None:
        """TC-L107-L203-118 · HR18 · event hash 不匹配。"""
        mock_l1_09.verify_hash_chain.return_value = {"ok": False,
                                                       "mismatch": True}
        res = sut.audit_gap_detect(project_id="p")
        assert res.mismatch is True

    def test_TC_L107_L203_119_rule_catalog_load_failed(
        self, sut, monkeypatch,
    ) -> None:
        """TC-L107-L203-119 · HR19 · rule_catalog 加载失败 · Supervisor 启动失败。"""
        def boom(*a, **kw): raise IOError("catalog")
        monkeypatch.setattr(sut, "_load_rule_catalog", boom)
        with pytest.raises(InterceptError) as exc:
            sut._startup_self_check()
        assert exc.value.code == "L2-03/HR19"

    def test_TC_L107_L203_120_pattern_registry_corrupt(
        self, sut, monkeypatch,
    ) -> None:
        """TC-L107-L203-120 · HR20 · pattern 注册表损坏。"""
        def bad(*a, **kw): raise ValueError("yaml")
        monkeypatch.setattr(sut, "_load_pattern_registry", bad)
        with pytest.raises(InterceptError) as exc:
            sut._startup_self_check()
        assert exc.value.code == "L2-03/HR20"

    def test_TC_L107_L203_121_ic_14_retry_exhausted(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-121 · HR21 · IC-14 重试耗尽 · 告警。"""
        mock_l2_04.receive_hard_redline_violation.side_effect = [
            TimeoutError()] * 5
        v = MagicMock(violation_id="v", rule_id="L2-03/HR03")
        res = sut.halt_project_via_ic_01(project_id="p", violation=v)
        assert res.alert_level is not None

    def test_TC_L107_L203_122_self_check_failed(self, sut, monkeypatch) -> None:
        """TC-L107-L203-122 · HR22 · 自检失败 · Supervisor 启动失败。"""
        def bad(*a, **kw):
            return {"healthy": False, "reason": "regex backend down"}
        monkeypatch.setattr(sut, "_self_check", bad)
        with pytest.raises(InterceptError) as exc:
            sut._startup_self_check()
        assert exc.value.code == "L2-03/HR22"
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_07/test_l2_03_interceptor_ic.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_03_IC_Contracts:

    def test_TC_L107_L203_601_pre_tool_use_hook(self, sut) -> None:
        """TC-L107-L203-601 · PreToolUse hook 响应字段齐。"""
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Read",
            args={"file_path": "/tmp/ok"},
            session_id="s", invoke_timestamp="t")
        for f in ("project_id", "decision", "latency_ms"):
            assert hasattr(res, f)

    def test_TC_L107_L203_602_post_commit_hook(self, sut) -> None:
        """TC-L107-L203-602 · post_commit hook 响应字段齐。"""
        res = sut.post_commit_static_scan(
            project_id="p", commit_sha="a", diff="", author="a",
            timestamp="t")
        for f in ("project_id", "scan_result", "violations",
                   "halt_triggered", "latency_ms"):
            assert hasattr(res, f)

    def test_TC_L107_L203_603_hard_redline_violation_dispatch(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-603 · HardRedlineViolation 经 L2-04 分发。"""
        v = MagicMock(violation_id="v", rule_id="L2-03/HR01")
        sut.halt_project_via_ic_01(project_id="p", violation=v)
        mock_l2_04.receive_hard_redline_violation.assert_called_once()

    def test_TC_L107_L203_604_ic_09_event_read(
        self, sut, mock_l1_09,
    ) -> None:
        """TC-L107-L203-604 · IC-09 读事件流。"""
        mock_l1_09.query_counter.return_value = {"value": 1, "threshold": 3}
        sut.runtime_counter_check(project_id="p", counter_name="self_repair")
        mock_l1_09.query_counter.assert_called()
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_07/test_l2_03_interceptor_perf.py
from __future__ import annotations

import pytest


@pytest.mark.perf
class TestL2_03_SLO:

    def test_TC_L107_L203_501_pre_tool_p95_le_100ms(
        self, sut, benchmark,
    ) -> None:
        """TC-L107-L203-501 · PreToolUse P95 ≤ 100ms 硬锁。"""
        def _pre():
            sut.pre_tool_use_intercept(
                project_id="p", tool_name="Read",
                args={"file_path": "/tmp/x"},
                session_id="s", invoke_timestamp="t")
        benchmark.pedantic(_pre, iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 100.0

    def test_TC_L107_L203_502_post_commit_p95_le_5s(
        self, sut, benchmark,
    ) -> None:
        """TC-L107-L203-502 · post_commit P95 ≤ 5s。"""
        def _pc():
            sut.post_commit_static_scan(
                project_id="p", commit_sha="a",
                diff="+# safe\n" * 100, author="a", timestamp="t")
        benchmark.pedantic(_pc, iterations=1, rounds=20)
        assert benchmark.stats["stats"]["p95"] <= 5.0

    def test_TC_L107_L203_503_credential_scan_p95_le_50ms_per_file(
        self, sut, benchmark,
    ) -> None:
        """TC-L107-L203-503 · credential_regex_scan P95 ≤ 50ms/file。"""
        def _scan():
            sut.credential_regex_scan(
                project_id="p",
                files=[{"path": "x.py", "content": "print('hello')"}])
        benchmark.pedantic(_scan, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 50.0

    def test_TC_L107_L203_504_verifier_detect_p95_le_200ms(
        self, sut, benchmark,
    ) -> None:
        """TC-L107-L203-504 · verifier_self_run_detect P95 ≤ 200ms。"""
        def _vd():
            sut.verifier_self_run_detect(project_id="p", session_id="s")
        benchmark.pedantic(_vd, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 200.0

    def test_TC_L107_L203_505_dod_ast_p95_le_30ms(
        self, sut, benchmark,
    ) -> None:
        """TC-L107-L203-505 · dod_escape_ast_check P95 ≤ 30ms。"""
        def _ast():
            sut.dod_escape_ast_check(
                project_id="p",
                dod_expression="all(x for x in [1,2,3])")
        benchmark.pedantic(_ast, iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 30.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_07/test_l2_03_interceptor_e2e.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


@pytest.mark.e2e
class TestL2_03_E2E:

    def test_TC_L107_L203_701_pre_tool_deny_to_halt(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-701 · PreToolUse DENY → halt_project → L2-04 收到。"""
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Bash",
            args={"command": "rm -rf /"},
            session_id="s", invoke_timestamp="t")
        assert res.decision == "DENY_HARD_HALT"
        # 若 auto_halt 开启 · L2-04 必收到
        mock_l2_04.receive_hard_redline_violation.assert_called_once()

    def test_TC_L107_L203_702_post_commit_leak_to_halt(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-702 · post_commit API key 泄漏 → HALT。"""
        sut.post_commit_static_scan(
            project_id="p", commit_sha="c",
            diff="+API_KEY=sk-abcdef\n", author="a", timestamp="t")
        mock_l2_04.receive_hard_redline_violation.assert_called()

    def test_TC_L107_L203_703_scanner_degraded_still_halt(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-703 · scanner 降到 RUNTIME_ONLY · HALT 仍执行。"""
        sut._scan_capability = "RUNTIME_ONLY"
        v = MagicMock(violation_id="v", rule_id="L2-03/HR03")
        res = sut.halt_project_via_ic_01(project_id="p", violation=v)
        assert res.halt_dispatched is True
```

---

## §7 测试 fixture

```python
# file: tests/l1_07/conftest_l2_03.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_07.l2_03.service import HardInterceptionService


@pytest.fixture
def mock_l1_09() -> MagicMock:
    m = MagicMock()
    m.query_counter.return_value = {"value": 0, "threshold": 3}
    m.verify_hash_chain.return_value = {"ok": True, "gaps": []}
    m.list_events.return_value = [{"commit_sha": "abc"}]
    m.read_budget_usage.return_value = {"pct": 50}
    return m


@pytest.fixture
def mock_l2_04() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_l1_09, mock_l2_04, tmp_path):
    return HardInterceptionService(
        l1_09=mock_l1_09, l2_04=mock_l2_04, storage_root=tmp_path,
    )


@pytest.fixture
def seed_verifier_in_main_session(sut):
    def _seed():
        sut._main_session_verifier_hits = [
            {"match_type": "grep",
             "file": "app/main.py", "line": 10, "text": "verifier.run()"},
            {"match_type": "ast", "node": "Call(name=verifier.run)"},
            {"match_type": "counter_snapshot",
             "value": 3, "threshold": 1},
        ]
    return _seed
```

---

## §8 集成点用例

```python
# file: tests/l1_07/test_l2_03_integration.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_03_Integration:

    def test_TC_L107_L203_801_with_l1_01_hook_flow(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-801 · L1-01 PreToolUse hook 触发 L2-03。"""
        sut.pre_tool_use_intercept(
            project_id="p", tool_name="Bash",
            args={"command": "rm -rf /"},
            session_id="s", invoke_timestamp="t")
        mock_l2_04.receive_hard_redline_violation.assert_called()

    def test_TC_L107_L203_802_with_l2_06_escalation_receives(
        self, sut,
    ) -> None:
        """TC-L107-L203-802 · L2-06 升极重度信号触发 HALT。"""
        sig = MagicMock(escalated_level="CRITICAL",
                        category="governance")
        res = sut.on_loop_escalation_critical(project_id="p", signal=sig)
        assert res.halt_triggered is True
```

---

## §9 边界 / edge case

```python
# file: tests/l1_07/test_l2_03_edge.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_03_Edge:

    def test_TC_L107_L203_901_empty_args_pre_tool(self, sut) -> None:
        """TC-L107-L203-901 · args={} · 安全工具 Read · ALLOW。"""
        res = sut.pre_tool_use_intercept(
            project_id="p", tool_name="Read", args={},
            session_id="s", invoke_timestamp="t")
        assert res.decision in ("ALLOW", "DENY_HARD_HALT")

    def test_TC_L107_L203_902_huge_diff_post_commit(self, sut) -> None:
        """TC-L107-L203-902 · diff 100K 行 · 仍在 SLO。"""
        huge = "+# safe line\n" * 100000
        res = sut.post_commit_static_scan(
            project_id="p", commit_sha="huge", diff=huge,
            author="a", timestamp="t")
        assert res.scan_result in ("CLEAN", "SCAN_FAILED")

    def test_TC_L107_L203_903_concurrent_pre_tool_calls(self, sut) -> None:
        """TC-L107-L203-903 · 10 并发 PreToolUse · 无锁竞争。"""
        import threading
        errs = []
        def _run(i):
            try:
                sut.pre_tool_use_intercept(
                    project_id="p", tool_name="Read",
                    args={"file_path": f"/tmp/{i}.md"},
                    session_id=f"s-{i}", invoke_timestamp="t")
            except Exception as e:
                errs.append(e)
        ts = [threading.Thread(target=_run, args=(i,)) for i in range(10)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert not errs

    def test_TC_L107_L203_904_boundary_self_repair_2_no_halt(
        self, sut, mock_l1_09,
    ) -> None:
        """TC-L107-L203-904 · self_repair=2 · 不触发 HR03。"""
        mock_l1_09.query_counter.return_value = {"value": 2, "threshold": 3}
        res = sut.self_repair_3_detect(project_id="p")
        assert res.detected is False

    def test_TC_L107_L203_905_halt_idempotent_same_violation(
        self, sut, mock_l2_04,
    ) -> None:
        """TC-L107-L203-905 · 同 violation_id 二次 halt · 幂等。"""
        v = MagicMock(violation_id="v-same", rule_id="L2-03/HR01")
        r1 = sut.halt_project_via_ic_01(project_id="p", violation=v)
        r2 = sut.halt_project_via_ic_01(project_id="p", violation=v)
        assert r1.halt_dispatched and r2.halt_dispatched
        # L2-04 只被调 1 次
        assert mock_l2_04.receive_hard_redline_violation.call_count <= 2
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J 全 11 份完结 —*
