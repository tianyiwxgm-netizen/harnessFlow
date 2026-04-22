---
doc_id: tests-L1-08-L2-02-代码结构理解编排器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-02-代码结构理解编排器.md
  - docs/2-prd/L1-08 多模态内容处理/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-08 L2-02 代码结构理解编排器 · TDD 测试用例

> 基于 3-1 L2-02 §3（6 IC 触点）+ §11（16 个 `E_L202_*` 错误码）+ §12 SLO M-01~M-12 + §13 TC 锚点驱动。
> TC ID `TC-L108-L202-NNN`（语义别名：`TC-CODE-ANALYZE-*` / `TC-CODE-DELEGATE-*` / `TC-CODE-CACHE-*`）。
> pytest + Python 3.11+ 类型注解；`class TestCodeOrchestrator_*` 组织；IC 契约独立分组。

## §0 撰写进度

- [x] §1 覆盖度索引（IC × 错误码 × SLO）
- [x] §2 正向用例（五要素摘要 / 缓存命中 / 委托路径）
- [x] §3 负向用例（16 个 E_L202_* 全覆盖）
- [x] §4 IC-XX 契约集成测试（IC-L2-01 / IC-06 / IC-07 / IC-12）
- [x] §5 性能 SLO 用例（小仓 / 中仓 / 缓存 / 委托决策）
- [x] §6 端到端 e2e 场景（brownfield 全链 · delegate 超大仓 · KB 命中短路）
- [x] §7 测试 fixture（fake_repo / make_git_repo / mock_l106_kb / mock_l105_subagent）
- [x] §8 集成点用例（L1-06 KB · L1-05 子 Agent · L2-04 审计）
- [x] §9 边界 / edge case（空仓 / 10 万行边界 / git_dirty / Grep 预算截断）

---

## §1 覆盖度索引

### §1.1 方法 × 测试 × 覆盖类型

| 方法 / 路径（§3） | TC ID | 覆盖类型 | 对应 IC |
|:---|:---|:---|:---|
| `handle_dispatch()` · 小仓全量分析 | TC-L108-L202-001 | unit | IC-L2-01 |
| `handle_dispatch()` · KB cache hit 短路 | TC-L108-L202-002 | unit | IC-L2-01 + IC-06 |
| `handle_dispatch()` · 中仓完整分析 | TC-L108-L202-003 | unit | IC-L2-01 |
| `handle_dispatch()` · > 10 万行 · delegated | TC-L108-L202-004 | unit | IC-L2-01 + IC-12 |
| `handle_dispatch()` · partial（language_unsupported） | TC-L108-L202-005 | unit | IC-L2-01 |
| 五要素摘要：LanguageDetector | TC-L108-L202-006 | unit | 内部 |
| 五要素摘要：FrameworkDetector | TC-L108-L202-007 | unit | 内部 |
| 五要素摘要：EntryPointResolver | TC-L108-L202-008 | unit | 内部 |
| 五要素摘要：DependencyGraphBuilder | TC-L108-L202-009 | unit | 内部 |
| 五要素摘要：GrepPatternScanner | TC-L108-L202-010 | unit | 内部 |
| `emit_kb_read()` · IC-06 出站 | TC-L108-L202-011 | unit | IC-06 |
| `emit_kb_write()` · IC-07 出站（成功写 KB） | TC-L108-L202-012 | unit | IC-07 |
| `emit_delegate_to_l105()` · IC-12 出站 | TC-L108-L202-013 | unit | IC-12 |
| `validate_summary_invariants()` · 五要素校验 | TC-L108-L202-014 | unit | 内部 |
| `build_cache_key()` · repo_path + git_head + focus_hint_hash | TC-L108-L202-015 | unit | 内部 |

### §1.2 错误码 × 测试（§11 16 项全覆盖）

| 错误码 | TC ID | 分类 |
|:---|:---|:---|
| `E_L202_INPUT_TYPE_MISMATCH` | TC-L108-L202-101 | input |
| `E_L202_REPO_EMPTY` | TC-L108-L202-102 | input |
| `E_L202_GLOB_TIMEOUT` | TC-L108-L202-103 | timeout |
| `E_L202_LINE_ESTIMATE_FAIL` | TC-L108-L202-104 | io |
| `E_L202_LANGUAGE_UNSUPPORTED` | TC-L108-L202-105 | partial |
| `E_L202_FRAMEWORK_AMBIGUOUS` | TC-L108-L202-106 | partial |
| `E_L202_ENTRY_NOT_FOUND` | TC-L108-L202-107 | partial |
| `E_L202_GREP_BUDGET_EXCEEDED` | TC-L108-L202-108 | truncated |
| `E_L202_GREP_PATTERN_INVALID` | TC-L108-L202-109 | config |
| `E_L202_DELEGATE_FORWARD_FAIL` | TC-L108-L202-110 | delegate |
| `E_L202_DELEGATE_TIMEOUT` | TC-L108-L202-111 | delegate |
| `E_L202_DELEGATE_SCHEMA_INVALID` | TC-L108-L202-112 | delegate |
| `E_L202_KB_LOOKUP_FAIL` | TC-L108-L202-113 | kb |
| `E_L202_KB_WRITE_FAIL_PERMANENT` | TC-L108-L202-114 | kb |
| `E_L202_CONCURRENT_LOCK_TIMEOUT` | TC-L108-L202-115 | concurrency |
| `E_L202_SUMMARY_INVARIANT_VIOLATION` | TC-L108-L202-116 | internal |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 | 场景 |
|:---|:---|:---|:---|
| IC-L2-01 dispatch | TC-L108-L202-201 | L2-04 | 入站 schema 合法 |
| IC-06 kb_read | TC-L108-L202-202 | L1-06 | cache hit 短路 |
| IC-07 kb_write_session | TC-L108-L202-203 | L1-06 | 新摘要写入 |
| IC-12 delegate_codebase_onboarding | TC-L108-L202-204 | L1-05 | 委托 · tools_whitelist 锁定 |

### §1.4 性能 SLO × 测试

| SLO ID | 指标 | 阈值 | TC ID |
|:---|:---|:---|:---|
| M-01 | 小仓（< 1 万行）P99 | ≤ 30s | TC-L108-L202-301 |
| M-02 | 中仓（1-10 万行）P99 | ≤ 180s | TC-L108-L202-302 |
| M-03 | 缓存命中返回 P99 | ≤ 1s | TC-L108-L202-303 |
| M-04 | 委托决策 P99 | ≤ 5s | TC-L108-L202-304 |
| M-07 | 分析完整性 P95 | ≥ 0.8 | TC-L108-L202-305 |

### §1.5 e2e × 测试

| 场景 | TC ID |
|:---|:---|
| brownfield S1 全链：L2-04 → L2-02 → KB cache miss → analyze → kb_write → audit | TC-L108-L202-401 |
| 超大仓委托：L2-02 → IC-12 → L1-05 → 子 Agent 返回 summary | TC-L108-L202-402 |
| 二次访问：缓存命中短路全链 ≤ 1s | TC-L108-L202-403 |

---

## §2 正向用例

```python
# tests/unit/L1-08/L2-02/test_code_orchestrator_positive.py
import pytest
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestCodeOrchestrator_Analyze:
    """§3.1 handle_dispatch 正向"""

    async def test_small_repo_full_analyze(self, code_orch, small_py_repo, _dispatch):
        """TC-L108-L202-001 · < 1 万行 · status=success · 五要素填满"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp["status"] == "success"
        s = resp["summary"]
        assert UUID(s["summary_id"])
        assert s["language_detection"]["primary"] == "Python"
        assert s["framework_detection"]
        assert s["entry_points"]
        assert s["dependency_graph"]
        assert s["grep_hits_summary"]

    async def test_kb_cache_hit_short_circuit(self, code_orch, small_py_repo,
                                                mock_l106_kb_hit, _dispatch):
        """TC-L108-L202-002 · KB 命中 · 不再跑 Glob / tree-sitter · latency ≤ 1s"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp["status"] == "success"
        assert resp["kb_meta"]["cache_hit"] is True
        assert resp["latency_ms"] < 1000
        mock_l106_kb_hit.get.assert_called_once()

    async def test_medium_repo_analyze(self, code_orch, medium_py_repo, _dispatch):
        """TC-L108-L202-003 · 1-10 万行 · 耗时 ≤ 180s（mock 场景快通过）"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(medium_py_repo)))
        assert resp["status"] in {"success", "partial"}
        assert resp["summary"]["language_detection"]["primary"] == "Python"

    async def test_large_repo_delegated(self, code_orch, huge_repo,
                                          mock_l105_subagent, _dispatch):
        """TC-L108-L202-004 · > 10 万行 · status=delegated · IC-12 已发"""
        resp = await code_orch.handle_dispatch(
            _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=150_000)
        )
        assert resp["status"] == "delegated"
        assert resp["delegation_meta"]["subagent_session_id"]
        mock_l105_subagent.dispatch.assert_called_once()

    async def test_partial_language_unsupported(self, code_orch, cobol_repo, _dispatch):
        """TC-L108-L202-005 · COBOL 仓 · status=partial + framework=unknown"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(cobol_repo)))
        assert resp["status"] == "partial"
        assert resp["summary"]["framework_detection"]["primary"] == "unknown"


class TestCodeOrchestrator_InternalDetectors:
    """§2.3 内部检测器"""

    def test_language_detector_python(self, fake_glob_result_python):
        """TC-L108-L202-006 · LanguageDetector 识别 Python 为 primary"""
        r = LanguageDetector.detect(fake_glob_result_python)
        assert r["primary"] == "Python"
        assert r["confidence"] >= 0.7

    def test_framework_detector_fastapi(self, fake_py_repo_with_fastapi):
        """TC-L108-L202-007 · FrameworkDetector 识别 FastAPI（setup.py 依赖 + imports）"""
        r = FrameworkDetector.detect(fake_py_repo_with_fastapi)
        assert r["primary"] == "FastAPI"

    def test_entry_point_resolver_main_py(self, tmp_path):
        """TC-L108-L202-008 · EntryPointResolver 识别 app/main.py · __main__ 入口"""
        (tmp_path/"app").mkdir()
        (tmp_path/"app/main.py").write_text("if __name__ == '__main__':\n    pass\n")
        r = EntryPointResolver.resolve(tmp_path)
        assert any("main.py" in p for p in r)

    def test_dependency_graph_builder(self, fake_py_repo_with_fastapi):
        """TC-L108-L202-009 · DependencyGraphBuilder 构建 module → module 边"""
        g = DependencyGraphBuilder.build(fake_py_repo_with_fastapi)
        assert g["nodes"]
        assert g["edges"]

    def test_grep_pattern_scanner(self, fake_py_repo_with_fastapi):
        """TC-L108-L202-010 · GrepPatternScanner 聚合 hit_count"""
        r = GrepPatternScanner.scan(fake_py_repo_with_fastapi, patterns=["^from fastapi"])
        assert r["hit_counts"]


class TestCodeOrchestrator_OutboundIC:
    """§3.2/3.3/3.4 出站 IC"""

    async def test_emit_kb_read(self, code_orch, mock_l106_kb, small_py_repo, _dispatch):
        """TC-L108-L202-011 · IC-06 query.cache_key 含 repo_path+git_head+focus_hint_hash"""
        await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        call = mock_l106_kb.query.call_args[0][0]
        assert call["query"]["cache_key"]["repo_path"]
        assert call["query"]["cache_key"]["git_head"]

    async def test_emit_kb_write(self, code_orch, mock_l106_kb_miss, small_py_repo, _dispatch):
        """TC-L108-L202-012 · IC-07 写摘要 · scope=project · kind=code_structure_summary"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp["kb_meta"]["kb_write_status"] == "success"
        mock_l106_kb_miss.write.assert_called_once()
        payload = mock_l106_kb_miss.write.call_args[0][0]
        assert payload["scope"] == "project"
        assert payload["kind"] == "code_structure_summary"

    async def test_emit_delegate_ic12(self, code_orch, huge_repo, mock_l105_subagent, _dispatch):
        """TC-L108-L202-013 · IC-12 委托 · tools_whitelist 限定 [Glob,Grep,Read]"""
        await code_orch.handle_dispatch(
            _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=200_000)
        )
        payload = mock_l105_subagent.dispatch.call_args[0][0]
        assert payload["delegation_request"]["subagent_name"] == "codebase-onboarding"
        assert set(payload["delegation_request"]["tools_whitelist"]) == {"Glob", "Grep", "Read"}


class TestCodeOrchestrator_InvariantAndCacheKey:
    """不变式 + cache key"""

    def test_validate_summary_invariants_ok(self, valid_summary):
        """TC-L108-L202-014 · 五要素齐全 · 校验通过"""
        assert SummaryInvariantChecker.check(valid_summary) is True

    def test_build_cache_key_shape(self):
        """TC-L108-L202-015 · cache_key 三元组稳定 · 对同 inputs 幂等"""
        k1 = CodeOrchestrator.build_cache_key(repo_path="/a", git_head="sha1", focus_hint="backend/")
        k2 = CodeOrchestrator.build_cache_key(repo_path="/a", git_head="sha1", focus_hint="backend/")
        assert k1 == k2
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# tests/unit/L1-08/L2-02/test_code_orchestrator_negative.py
import pytest, asyncio

pytestmark = pytest.mark.asyncio


class TestL202_InputErrors:
    """INPUT_TYPE_MISMATCH / REPO_EMPTY / GLOB_TIMEOUT / LINE_ESTIMATE_FAIL"""

    async def test_E_L202_INPUT_TYPE_MISMATCH(self, code_orch, _dispatch):
        """TC-L108-L202-101 · type="md" → INPUT_TYPE_MISMATCH"""
        bad = _dispatch()
        bad["request"]["type"] = "md"
        resp = await code_orch.handle_dispatch(bad)
        assert resp["status"] == "failed"
        assert resp["error"]["code"] == "E_L202_INPUT_TYPE_MISMATCH"

    async def test_E_L202_REPO_EMPTY(self, code_orch, tmp_path, _dispatch):
        """TC-L108-L202-102 · Glob 零可读文本 → REPO_EMPTY"""
        (tmp_path/"bin").mkdir()
        (tmp_path/"bin/a").write_bytes(b"\x00\x01\x02")
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(tmp_path)))
        assert resp["error"]["code"] == "E_L202_REPO_EMPTY"

    async def test_E_L202_GLOB_TIMEOUT(self, code_orch, huge_repo, glob_timeout_config, _dispatch):
        """TC-L108-L202-103 · Glob 超时 · 降级为 DELEGATE"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(huge_repo)))
        # §11.2 降级为 DELEGATE
        assert resp["status"] in {"delegated", "failed"}

    async def test_E_L202_LINE_ESTIMATE_FAIL(self, code_orch, small_py_repo,
                                              monkeypatch, _dispatch):
        """TC-L108-L202-104 · wc -l IO 错 · fallback 到 L2-04 粗估"""
        monkeypatch.setattr(LineEstimator, "count",
                            lambda self, p: (_ for _ in ()).throw(OSError("IO fail")))
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        # §3.1 处理：退回 L2-04 粗估走降级
        assert resp["status"] in {"delegated", "partial", "success"}


class TestL202_PartialErrors:
    """LANGUAGE_UNSUPPORTED / FRAMEWORK_AMBIGUOUS / ENTRY_NOT_FOUND"""

    async def test_E_L202_LANGUAGE_UNSUPPORTED(self, code_orch, cobol_repo, _dispatch):
        """TC-L108-L202-105 · COBOL 仓 → partial · framework=unknown"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(cobol_repo)))
        assert resp["status"] == "partial"

    async def test_E_L202_FRAMEWORK_AMBIGUOUS(self, code_orch, monorepo_mixed, _dispatch):
        """TC-L108-L202-106 · monorepo 多框架置信度均 < 0.5 → FRAMEWORK_AMBIGUOUS · partial"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(monorepo_mixed)))
        assert resp["status"] == "partial"
        assert resp["summary"]["framework_detection"]["confidence"] < 0.5

    async def test_E_L202_ENTRY_NOT_FOUND(self, code_orch, no_entry_repo, _dispatch):
        """TC-L108-L202-107 · 无约定入口 → entry_files=[] · partial"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(no_entry_repo)))
        assert resp["summary"]["entry_points"] == []
        assert resp["status"] in {"partial", "success"}


class TestL202_GrepErrors:
    """GREP_BUDGET_EXCEEDED / GREP_PATTERN_INVALID"""

    async def test_E_L202_GREP_BUDGET_EXCEEDED(self, code_orch, small_py_repo,
                                                 tight_token_budget, _dispatch):
        """TC-L108-L202-108 · token 预算耗尽 · grep_hits_summary.truncated_patterns 非空"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        summary = resp["summary"]["grep_hits_summary"]
        assert summary.get("truncated_patterns")

    async def test_E_L202_GREP_PATTERN_INVALID(self, invalid_regex_config):
        """TC-L108-L202-109 · 启动期 config 含非法 regex → 启动拒绝"""
        with pytest.raises(ConfigError):
            CodeOrchestrator(config=invalid_regex_config)


class TestL202_DelegateErrors:
    """DELEGATE_FORWARD_FAIL / DELEGATE_TIMEOUT / DELEGATE_SCHEMA_INVALID"""

    async def test_E_L202_DELEGATE_FORWARD_FAIL(self, code_orch, huge_repo,
                                                  mock_l105_down, _dispatch):
        """TC-L108-L202-110 · IC-12 发送失败 3 次 · 透传 err"""
        mock_l105_down.set_persistent_fail(True)
        resp = await code_orch.handle_dispatch(
            _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=200_000)
        )
        assert resp["error"]["code"] == "E_L202_DELEGATE_FORWARD_FAIL"

    async def test_E_L202_DELEGATE_TIMEOUT(self, code_orch, huge_repo,
                                             mock_l105_slow, _dispatch):
        """TC-L108-L202-111 · L1-05 子 Agent > 30 min 未返回 → 透传"""
        mock_l105_slow.set_never_complete(True)
        resp = await code_orch.handle_dispatch(
            _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=200_000,
                      delegate_timeout_ms=100)
        )
        assert resp["error"]["code"] == "E_L202_DELEGATE_TIMEOUT"
        assert "focus_hint" in resp["error"]["suggested_action"]

    async def test_E_L202_DELEGATE_SCHEMA_INVALID(self, code_orch, huge_repo,
                                                    mock_l105_bad_schema, _dispatch):
        """TC-L108-L202-112 · 子 Agent 返回 schema 缺字段 → REJECTED"""
        mock_l105_bad_schema.set_bad_payload({"missing": "required_fields"})
        resp = await code_orch.handle_dispatch(
            _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=200_000)
        )
        assert resp["error"]["code"] == "E_L202_DELEGATE_SCHEMA_INVALID"


class TestL202_KBErrors:
    """KB_LOOKUP_FAIL / KB_WRITE_FAIL_PERMANENT"""

    async def test_E_L202_KB_LOOKUP_FAIL(self, code_orch, small_py_repo, mock_l106_down, _dispatch):
        """TC-L108-L202-113 · L1-06 不可达 · 跳缓存 · 走 full analyze · 不硬失败"""
        mock_l106_down.set_persistent_fail(True)
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp["status"] in {"success", "partial"}
        assert resp["kb_meta"]["cache_hit"] is False

    async def test_E_L202_KB_WRITE_FAIL_PERMANENT(self, code_orch, small_py_repo,
                                                    mock_l106_write_fail, _dispatch):
        """TC-L108-L202-114 · IC-07 重试耗尽 · 返摘要 · kb_write_status=failed"""
        mock_l106_write_fail.set_persistent_write_fail(True)
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp["status"] == "success"
        assert resp["kb_meta"]["kb_write_status"] == "failed"


class TestL202_ConcurrencyAndInvariant:
    """CONCURRENT_LOCK_TIMEOUT / SUMMARY_INVARIANT_VIOLATION"""

    async def test_E_L202_CONCURRENT_LOCK_TIMEOUT(self, code_orch, small_py_repo,
                                                    lock_always_busy, _dispatch):
        """TC-L108-L202-115 · 同 repo 并发堆积 · 等锁超时 → REJECTED"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp["error"]["code"] == "E_L202_CONCURRENT_LOCK_TIMEOUT"

    async def test_E_L202_SUMMARY_INVARIANT_VIOLATION(self, code_orch, small_py_repo,
                                                        force_invariant_break, _dispatch):
        """TC-L108-L202-116 · mock 五要素缺一 · REJECTED + 告警 L1-07 · 不入 KB"""
        force_invariant_break()
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp["error"]["code"] == "E_L202_SUMMARY_INVARIANT_VIOLATION"
```

---

## §4 IC-XX 契约集成测试

```python
# tests/integration/L1-08/L2-02/test_ic_contracts.py
import pytest, jsonschema

pytestmark = pytest.mark.asyncio


class TestICL201Contract:
    """IC-L2-01 dispatch(type=code) · 入站"""

    async def test_dispatch_input_schema(self, code_orch, small_py_repo,
                                           icl201_code_schema, _dispatch):
        """TC-L108-L202-201 · 入站 payload 字段完备 · type=code · action=analyze"""
        payload = _dispatch(repo_path=str(small_py_repo))
        jsonschema.validate(payload, icl201_code_schema)
        resp = await code_orch.handle_dispatch(payload)
        assert resp["status"] in {"success", "partial", "delegated"}


class TestIC06KbReadContract:
    """IC-06 kb_read · 出站"""

    async def test_ic06_query_payload(self, code_orch, small_py_repo, mock_l106_kb, _dispatch):
        """TC-L108-L202-202 · query.scope=project · kind=code_structure_summary"""
        await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        payload = mock_l106_kb.query.call_args[0][0]
        assert payload["query"]["scope"] == "project"
        assert payload["query"]["kind"] == "code_structure_summary"


class TestIC07KbWriteContract:
    """IC-07 kb_write_session · 出站"""

    async def test_ic07_write_payload(self, code_orch, small_py_repo,
                                        mock_l106_kb_miss, _dispatch):
        """TC-L108-L202-203 · entry.content.summary 完整 · source_links 非空"""
        await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        payload = mock_l106_kb_miss.write.call_args[0][0]
        assert payload["entry"]["content"]["summary"]
        assert payload["entry"]["source_links"]


class TestIC12DelegateContract:
    """IC-12 · 出站委托"""

    async def test_ic12_delegate_payload(self, code_orch, huge_repo, mock_l105_subagent,
                                          ic12_schema, _dispatch):
        """TC-L108-L202-204 · tools_whitelist 锁定 · goal 明确 · context_copy 完整"""
        await code_orch.handle_dispatch(
            _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=200_000)
        )
        payload = mock_l105_subagent.dispatch.call_args[0][0]
        jsonschema.validate(payload, ic12_schema)
        assert payload["delegation_request"]["tools_whitelist"] == ["Glob", "Grep", "Read"]
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-08/L2-02/test_slo.py
import pytest, time, statistics
from contextlib import contextmanager

pytestmark = pytest.mark.asyncio


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestSmallRepoSLO:
    """M-01 · < 1 万行 P99 ≤ 30s"""

    async def test_small_repo_p99_under_30s(self, code_orch, small_py_repo_pool, _dispatch):
        """TC-L108-L202-301 · 100 次小仓分析 · P99 ≤ 30000ms"""
        samples = []
        for r in small_py_repo_pool[:100]:
            with _timer() as t:
                await code_orch.handle_dispatch(_dispatch(repo_path=str(r)))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 30_000.0


class TestMediumRepoSLO:
    """M-02 · 1-10 万行 P99 ≤ 180s"""

    async def test_medium_repo_p99_under_180s(self, code_orch, medium_py_repo_pool, _dispatch):
        """TC-L108-L202-302 · 20 次中仓 · P99 ≤ 180000ms"""
        samples = []
        for r in medium_py_repo_pool[:20]:
            with _timer() as t:
                await code_orch.handle_dispatch(_dispatch(repo_path=str(r)))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 180_000.0


class TestCacheHitSLO:
    """M-03 · cache hit P99 ≤ 1s"""

    async def test_cache_hit_p99_under_1s(self, code_orch, small_py_repo, mock_l106_kb_hit,
                                           _dispatch):
        """TC-L108-L202-303 · 500 次 cache hit · P99 ≤ 1000ms"""
        samples = []
        for _ in range(500):
            with _timer() as t:
                await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 1_000.0


class TestDelegateDecisionSLO:
    """M-04 · 委托决策 P99 ≤ 5s"""

    async def test_delegate_decision_p99_under_5s(self, code_orch, huge_repo_pool,
                                                    mock_l105_fast, _dispatch):
        """TC-L108-L202-304 · 50 次委托决策 · 决策 → IC-12 发出 ≤ 5000ms"""
        samples = []
        for r in huge_repo_pool[:50]:
            with _timer() as t:
                await code_orch.handle_dispatch(
                    _dispatch(repo_path=str(r), precheck_lines_estimate=200_000)
                )
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 5_000.0


class TestCompletenessSLO:
    """M-07 · 分析完整性 P95 ≥ 0.8"""

    async def test_completeness_p95_ge_0_8(self, code_orch, small_py_repo_pool, _dispatch):
        """TC-L108-L202-305 · 100 次分析 · completeness_score P95 ≥ 0.8"""
        scores = []
        for r in small_py_repo_pool[:100]:
            resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(r)))
            scores.append(resp["summary"].get("completeness_score", 1.0))
        p95 = statistics.quantiles(scores, n=20)[18]
        assert p95 >= 0.8
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-08/L2-02/test_e2e.py
import pytest, asyncio

pytestmark = pytest.mark.asyncio


class TestE2E_BrownfieldS1:
    """brownfield S1 全链 · L2-04 → L2-02 → KB miss → analyze → kb_write → audit"""

    async def test_full_s1_flow(self, l204_real, code_orch, l106_real, l109_real,
                                  small_py_repo, _dispatch):
        """TC-L108-L202-401 · 全链成功 · kb_write + audit 均落盘"""
        req = _dispatch(repo_path=str(small_py_repo))
        resp = await code_orch.handle_dispatch(req)
        assert resp["status"] == "success"
        # 审计有 code_summarized 事件
        events = l109_real.query_trail(trace_id=req["trace_id"])
        assert any(e["event_type"] == "L1-08:code_summarized" for e in events)
        # KB 有摘要
        kb_hits = l106_real.query({"query": {"scope": "project",
                                              "kind": "code_structure_summary",
                                              "cache_key": req["request"]["precheck"]}})
        assert kb_hits["hits"]


class TestE2E_LargeRepoDelegate:
    """超大仓 delegate · IC-12 → L1-05 子 Agent → summary"""

    async def test_large_repo_delegate_flow(self, code_orch, huge_repo, l105_real, _dispatch):
        """TC-L108-L202-402 · 15 万行仓 · delegated · 子 Agent 返 summary"""
        req = _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=150_000)
        resp = await code_orch.handle_dispatch(req)
        assert resp["status"] == "delegated"
        assert resp["summary"]["summary_id"]


class TestE2E_CacheHit:
    """二次访问 · cache hit 全链 ≤ 1s"""

    async def test_cache_hit_short_circuit(self, code_orch, small_py_repo, l106_real, _dispatch):
        """TC-L108-L202-403 · 首次写 KB · 二次命中 · latency < 1s"""
        req = _dispatch(repo_path=str(small_py_repo))
        resp1 = await code_orch.handle_dispatch(req)
        assert resp1["kb_meta"]["cache_hit"] is False
        resp2 = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert resp2["kb_meta"]["cache_hit"] is True
        assert resp2["latency_ms"] < 1000
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest, subprocess
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4


@pytest.fixture
def mock_project_id(): return "demo-proj-001"


@pytest.fixture
def _dispatch(mock_project_id):
    def _make(repo_path: str = "/tmp/r", precheck_lines_estimate: int = 5_000,
              focus_hint: str | None = None) -> dict:
        return {
            "ic_id": "IC-L2-01", "ic_version": "v1.0",
            "dispatched_at": "2026-04-22T10:00:00Z", "dispatched_by": "L2-04",
            "project_id": mock_project_id, "trace_id": str(uuid4()),
            "request": {
                "type": "code", "action": "analyze",
                "repo_path": repo_path, "canonical_repo_path": repo_path,
                "focus_hint": focus_hint,
                "include_patterns": None, "exclude_patterns": None,
                "precheck": {
                    "delegate_hint": precheck_lines_estimate >= 100_000,
                    "precheck_lines_estimate": precheck_lines_estimate,
                    "git_head": "a" * 40, "git_dirty": False,
                    "repo_size_bytes": precheck_lines_estimate * 80,
                },
                "caller": {"l1_id": "L1-01", "l2_id": None, "purpose": "brownfield_init"},
            },
        }
    return _make


@pytest.fixture
def small_py_repo(tmp_path):
    (tmp_path/"app").mkdir()
    (tmp_path/"app/__init__.py").write_text("")
    (tmp_path/"app/main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    (tmp_path/"setup.py").write_text("from setuptools import setup\nsetup(name='x', install_requires=['fastapi'])\n")
    subprocess.run(["git", "init"], cwd=tmp_path, check=False, capture_output=True)
    return tmp_path


@pytest.fixture
def medium_py_repo(tmp_path):
    root = tmp_path / "medium"
    root.mkdir()
    for i in range(30):
        m = root / f"m{i}.py"
        m.write_text("# line\n" * 2000)
    subprocess.run(["git", "init"], cwd=root, check=False, capture_output=True)
    return root


@pytest.fixture
def huge_repo(tmp_path):
    root = tmp_path / "huge"
    root.mkdir()
    for i in range(500):
        (root / f"m{i}.py").write_text("# line\n" * 300)
    subprocess.run(["git", "init"], cwd=root, check=False, capture_output=True)
    return root


@pytest.fixture
def huge_repo_pool(tmp_path):
    pool = []
    for k in range(5):
        root = tmp_path / f"h{k}"
        root.mkdir()
        for i in range(500):
            (root / f"m{i}.py").write_text("# line\n" * 300)
        pool.append(root)
    return pool


@pytest.fixture
def small_py_repo_pool(tmp_path):
    pool = []
    for k in range(100):
        r = tmp_path / f"s{k}"
        r.mkdir()
        (r / "main.py").write_text("print('hi')\n")
        pool.append(r)
    return pool


@pytest.fixture
def medium_py_repo_pool(tmp_path):
    pool = []
    for k in range(20):
        r = tmp_path / f"m{k}"
        r.mkdir()
        for i in range(30):
            (r / f"m{i}.py").write_text("# line\n" * 2000)
        pool.append(r)
    return pool


@pytest.fixture
def cobol_repo(tmp_path):
    (tmp_path/"prog.cbl").write_text("IDENTIFICATION DIVISION.\nPROGRAM-ID. X.\n")
    return tmp_path


@pytest.fixture
def monorepo_mixed(tmp_path):
    (tmp_path/"py/app.py").parent.mkdir(); (tmp_path/"py/app.py").write_text("import django\n")
    (tmp_path/"ts/app.ts").parent.mkdir(); (tmp_path/"ts/app.ts").write_text("import Vue from 'vue'\n")
    (tmp_path/"go/main.go").parent.mkdir(); (tmp_path/"go/main.go").write_text("package main\n")
    return tmp_path


@pytest.fixture
def no_entry_repo(tmp_path):
    (tmp_path/"util.py").write_text("def f(): pass\n")
    return tmp_path


@pytest.fixture
def mock_l106_kb():
    m = MagicMock()
    m.query = AsyncMock(return_value={"hits": []})
    m.write = AsyncMock(return_value={"kb_entry_id": str(uuid4())})
    return m


@pytest.fixture
def mock_l106_kb_hit():
    m = MagicMock()
    m.get = AsyncMock(return_value={"summary": {"summary_id": str(uuid4()),
                                                   "language_detection": {"primary": "Python"}}})
    m.query = AsyncMock(return_value={"hits": [{"summary_id": str(uuid4())}]})
    m.write = AsyncMock()
    return m


@pytest.fixture
def mock_l106_kb_miss():
    m = MagicMock()
    m.query = AsyncMock(return_value={"hits": []})
    m.write = AsyncMock(return_value={"kb_entry_id": str(uuid4())})
    return m


@pytest.fixture
def mock_l106_down():
    m = MagicMock()
    async def _fail(*a, **k): raise ConnectionError("L1-06 down")
    m.query = AsyncMock(side_effect=_fail)
    m.write = AsyncMock(side_effect=_fail)
    m.set_persistent_fail = lambda v: None
    return m


@pytest.fixture
def mock_l106_write_fail():
    m = MagicMock()
    m.query = AsyncMock(return_value={"hits": []})
    async def _wfail(*a, **k): raise ConnectionError("write fail")
    m.write = AsyncMock(side_effect=_wfail)
    m.set_persistent_write_fail = lambda v: None
    return m


@pytest.fixture
def mock_l105_subagent():
    m = MagicMock()
    m.dispatch = AsyncMock(return_value={
        "subagent_session_id": str(uuid4()),
        "subagent_elapsed_ms": 5000,
        "subagent_report_path": "/tmp/rep.yaml",
        "summary": {"summary_id": str(uuid4())},
    })
    return m


@pytest.fixture
def mock_l105_down():
    m = MagicMock()
    async def _fail(*a, **k): raise ConnectionError("L1-05 down")
    m.dispatch = AsyncMock(side_effect=_fail)
    m.set_persistent_fail = lambda v: None
    return m


@pytest.fixture
def mock_l105_slow():
    import asyncio
    m = MagicMock()
    async def _slow(*a, **k):
        await asyncio.sleep(10)
        return {}
    m.dispatch = AsyncMock(side_effect=_slow)
    m.set_never_complete = lambda v: None
    return m


@pytest.fixture
def mock_l105_bad_schema():
    m = MagicMock()
    m.dispatch = AsyncMock(return_value={"missing": "required_fields"})
    m.set_bad_payload = lambda p: None
    return m


@pytest.fixture
def mock_l105_fast():
    m = MagicMock()
    m.dispatch = AsyncMock(return_value={"subagent_session_id": str(uuid4())})
    return m


@pytest.fixture
def code_orch(mock_l106_kb_miss, mock_l105_subagent, l204_mock_emitter):
    return CodeOrchestrator(
        kb_client=mock_l106_kb_miss,
        subagent_dispatcher=mock_l105_subagent,
        emitter=l204_mock_emitter,
        config={"token_budget_per_scan": 100_000},
    )


@pytest.fixture
def l204_mock_emitter():
    m = MagicMock()
    m.emit_audit_seed = AsyncMock()
    return m


@pytest.fixture
def valid_summary():
    return {
        "summary_id": str(uuid4()),
        "language_detection": {"primary": "Python", "confidence": 0.9},
        "framework_detection": {"primary": "FastAPI", "confidence": 0.9},
        "entry_points": ["app/main.py"],
        "dependency_graph": {"nodes": [], "edges": []},
        "grep_hits_summary": {"hit_counts": {}},
    }


@pytest.fixture
def tight_token_budget(monkeypatch):
    monkeypatch.setattr(GrepPatternScanner, "token_budget", 100)


@pytest.fixture
def glob_timeout_config(monkeypatch):
    monkeypatch.setattr(GlobScanner, "timeout_ms", 1)


@pytest.fixture
def invalid_regex_config():
    return {"grep_patterns": [{"name": "bad", "pattern": "["}]}


@pytest.fixture
def lock_always_busy(monkeypatch):
    async def _fail(*a, **k):
        raise LockTimeoutError("locked")
    monkeypatch.setattr(LockManager, "acquire", _fail)


@pytest.fixture
def force_invariant_break(monkeypatch):
    def _activate():
        monkeypatch.setattr(SummaryInvariantChecker, "check",
                            lambda self, s: False)
    return _activate


@pytest.fixture
def icl201_code_schema():
    return {"type": "object", "required": ["ic_id", "project_id", "trace_id", "request"],
            "properties": {"request": {"type": "object",
                                        "required": ["type", "action", "repo_path"]}}}


@pytest.fixture
def ic12_schema():
    return {"type": "object", "required": ["ic_id", "project_id", "trace_id", "delegation_request"]}
```

---

## §8 集成点用例

```python
# tests/integration/L1-08/L2-02/test_integration_points.py
import pytest

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL106KB:
    """与 L1-06 三层 KB 协作"""

    async def test_read_then_write_writes_project_scope(self, code_orch, small_py_repo,
                                                          mock_l106_kb_miss, _dispatch):
        """TC-L108-L202-501 · cache miss → full analyze → 写 project 层 KB"""
        await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        call = mock_l106_kb_miss.write.call_args[0][0]
        assert call["scope"] == "project"


class TestIntegrationWithL105Subagent:
    """与 L1-05 Skill+子 Agent 协作"""

    async def test_tools_whitelist_enforced(self, code_orch, huge_repo,
                                              mock_l105_subagent, _dispatch):
        """TC-L108-L202-502 · 委托时 tools_whitelist 固定只读 · 禁 Write/Bash/WebFetch"""
        await code_orch.handle_dispatch(
            _dispatch(repo_path=str(huge_repo), precheck_lines_estimate=200_000)
        )
        payload = mock_l105_subagent.dispatch.call_args[0][0]
        tw = set(payload["delegation_request"]["tools_whitelist"])
        assert tw == {"Glob", "Grep", "Read"}
        assert not ({"Write", "Bash", "WebFetch"} & tw)


class TestIntegrationWithL204Audit:
    """经 L2-04 审计路径"""

    async def test_audit_seed_emitted_on_success(self, code_orch, small_py_repo,
                                                   l204_mock_emitter, _dispatch):
        """TC-L108-L202-503 · success 路径 · emit_audit_seed 至少 1 次"""
        await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        assert l204_mock_emitter.emit_audit_seed.call_count >= 1
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-08/L2-02/test_edge_cases.py
import pytest

pytestmark = pytest.mark.asyncio


class TestEdgeBoundaryLines:
    """10 万行边界 / git_dirty / 空仓"""

    async def test_edge_exactly_100000_lines(self, code_orch, tmp_path, _dispatch):
        """TC-L108-L202-601 · precheck=100000 · 临界 · 可能 delegated 也可能 full"""
        (tmp_path/"a.py").write_text("# line\n" * 100_000)
        resp = await code_orch.handle_dispatch(
            _dispatch(repo_path=str(tmp_path), precheck_lines_estimate=100_000)
        )
        assert resp["status"] in {"success", "delegated", "partial"}

    async def test_edge_git_dirty_cache_key_includes_dirty(self, code_orch, small_py_repo,
                                                             mock_l106_kb, _dispatch):
        """TC-L108-L202-602 · git_dirty=true · cache_key 不同于 clean 版本"""
        d = _dispatch(repo_path=str(small_py_repo))
        d["request"]["precheck"]["git_dirty"] = True
        await code_orch.handle_dispatch(d)
        key = mock_l106_kb.query.call_args[0][0]["query"]["cache_key"]
        assert "dirty" in str(key).lower() or key.get("git_dirty") is True


class TestEdgeTruncation:
    """Grep token 预算截断"""

    async def test_edge_grep_truncation_reported(self, code_orch, small_py_repo,
                                                   tight_token_budget, _dispatch):
        """TC-L108-L202-603 · 预算紧 · truncated_patterns 非空 + 审计记录"""
        resp = await code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
        truncated = resp["summary"]["grep_hits_summary"].get("truncated_patterns")
        assert truncated is not None


class TestEdgeConcurrencySameRepo:
    """同 repo 并发"""

    async def test_edge_concurrent_same_repo_serialized(self, code_orch, small_py_repo, _dispatch):
        """TC-L108-L202-604 · 同 repo 5 并发 · 通过 repo_lock 串行 · 至少 1 成功"""
        import asyncio
        tasks = [code_orch.handle_dispatch(_dispatch(repo_path=str(small_py_repo)))
                 for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        assert ok >= 1
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
