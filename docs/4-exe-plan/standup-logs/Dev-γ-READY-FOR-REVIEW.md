# Dev-γ · L1-05 · READY FOR MAIN-SESSION REVIEW

**Date**: 2026-04-23
**Branch**: `feat/dev-gamma-l1-05`
**Worktree**: `/Users/zhongtianyi/work/code/harnessFlow/.worktrees/dev-gamma-l1-05/`
**Status**: ✅ 开发完成 · 待主会话 review

---

## 一句话交付

**L1-05 Skill 生态 + 子 Agent 调度** · 5 L2 · 4 全局 IC · **212 TC 全绿** · coverage **89.21%**（>85% 阈值）· 34 commits · 领域独立（零跨 L1 代码改动）。

## 验证证据（刚刚执行 · fresh）

### 测试
```
$ pytest tests/skill_dispatch/ --cov=app.skill_dispatch --cov-fail-under=85
============================= 212 passed in 4.98s ==============================
TOTAL    807    81   138   15   89.2%
Required test coverage of 85% reached. Total coverage: 89.21%
```

### Perf SLO
```
IC-04 dispatch latency:   p50=0.44ms  p95=0.67ms  p99=0.78ms   (SLO ≤ 200ms  ✓)
subagent spawn latency:   p50=0.06ms  p95=0.09ms  p99=0.15ms   (SLO ≤ 1200ms ✓)
```

### 分模块 Coverage
| 模块 | Stmts | Cover | 核心未 cover 原因 |
|---|---|---|---|
| async_receiver/validator | 42 | 100% | — |
| async_receiver/forwarder | 25 | 92.0% | _safe_emit 异常分支 |
| async_receiver/crash_recovery | 66 | 87.2% | TimeoutWatcher 内部 try/except |
| intent_selector/hard_edge_scan | 31 | 95.6% | 非 utf-8 文件 fallback |
| intent_selector/scorer | 68 | 87.8% | MAX_COST_REF=0 边界 |
| intent_selector/kb_boost | 34 | 76.3% | __del__ finalizer · KB 异常路径 |
| intent_selector/fallback_advancer | 22 | 83.3% | audit_safe except 分支 |
| invoker/context_injector | 9 | 100% | — |
| invoker/timeout_manager | 18 | 100% | — |
| invoker/retry_policy | 16 | 91.7% | attempt<1 defensive |
| invoker/audit | 35 | 89.7% | IC-09 失败降级分支 |
| invoker/executor | 72 | 93.4% | allow_fallback=False 分支 |
| subagent/context_scope | 26 | 100% | — |
| subagent/resource_limiter | 36 | 89.1% | ValueError init 分支 |
| subagent/claude_sdk_client | 52 | 85.2% | kill 错误分支 |
| subagent/delegator | 65 | 86.3% | async except 分支 |
| registry/loader | 78 | 88.9% | snapshot write edge |
| registry/query_api | 35 | 100% | — |
| registry/ledger | 24 | 100% | — |
| registry/fs_watcher | 53 | 66.1% | watchdog Observer 真 FS 路径 pragma no cover（预期） |

### 14 个错误码全覆盖（grep 命中）
```
E_SKILL_NO_CAPABILITY              :  8 refs
E_SKILL_ALL_FALLBACK_FAIL          :  7 refs
E_SKILL_INVOCATION_TIMEOUT         :  3 refs
E_INTENT_HARDCODED_SKILL           :  2 refs
E_INTENT_CHAIN_EXHAUSTED           :  4 refs
E_INTENT_KB_TIMEOUT                :  2 refs
E_REG_MISSING_CAPABILITY           :  6 refs
E_REG_NO_SCHEMA_POINTER            :  4 refs
E_SUB_SPAWN_FAILED                 :  6 refs
E_SUB_TIMEOUT                      :  4 refs
E_SUB_CONTEXT_ISOLATION_VIOLATION  :  2 refs
E_SUB_SESSION_LIMIT                :  3 refs
E_COLLECT_SCHEMA_UNAVAILABLE       :  1 refs
E_COLLECT_DOD_GATE_TIMEOUT         :  3 refs
```

---

## PM 硬约束兑现（所有均有独立 TC）

| PM | 测试 |
|---|---|
| **PM-03** 子 Agent 独立 session · 只读 ctx | `test_pm03_child_cannot_read_main_task_board` / `test_pm03_child_context_is_read_only` |
| **PM-08** 可追溯 100% · Signature 种子 | `test_invocation_signature_is_superset_of_response_fields` / `test_audit_emits_started_and_finished_events` |
| **PM-09** 能力抽象 · 禁硬编码 skill | `test_scan_crashes_on_superpowers_literal` / `test_scan_catches_gstack_and_ecc_patterns` |
| **PM-10** 事件总线单一事实源 | `test_ic09_audit_trail_is_complete` |
| **PM-14** project_id 根字段 | `test_pm14_all_ic_writes_require_project_id` / `test_pm14_cross_project_delegate_rejected` |

## IC 契约对齐（vs `ic-contracts.md`）

| IC | 出处章节 | 测试 |
|---|---|---|
| **IC-04** invoke_skill | §3.4.2/3/4 | `test_ic_04_request_matches_contract` + 11 executor TCs |
| **IC-05** delegate_subagent | §3.5.2/3/4/5 | `test_ic_05_delegation_request_matches_contract` + delegator TCs |
| **IC-12** delegate_codebase_onboarding | §3.12.2/4 | `test_ic_12_codebase_onboarding_matches_contract` + delegator TCs |
| **IC-20** delegate_verifier | §3.20.2/4 | `test_ic_20_verifier_matches_contract` + `test_ic20_verifier_dispatch_with_strict_whitelist` |

## 契约红线兑现

1. ✅ **IC-04 全链失败不 raise** — `test_all_candidates_fail_returns_success_false_not_raises` + `test_all_candidates_fail_yields_success_false`
2. ✅ **Signature ⊇ Response** — `test_invocation_signature_is_superset_of_response_fields`
3. ✅ **SCHEMA_UNAVAILABLE 硬失败** — `test_schema_unavailable_returns_hard_fail` / `test_schema_pointer_none_returns_schema_unavailable`
4. ✅ **silent_patch E09 检测** — `test_silent_patch_detected_when_output_has_unexpected_fields`
5. ✅ **IC-20 严格 allowed_tools** — `test_ic20_rejects_extra_tool_in_whitelist`

---

## Commit 总表（34 个）

主线顺序（自 Dev-δ `ce8fd51` 起）：
```
00.1+00.3  bootstrap: pyproject amend + app/skill_dispatch/ + tests/skill_dispatch/ 骨架
00.4+00.5  4 IC 本地 mocks (IC-09/IC-06/L2-07 lock/L1-04 DoD gate)
00.6       tests conftest + registry_valid.yaml fixture
00.docs    Dev-γ-brief + Dev-γ-impl plan + Day 1 standup
01.1       L2-01 Registry schemas (Pydantic v2 · PM-09)
01.2       Loader Stage 1-3 (SLO 500ms)
01.3       Loader Stage 4-5 + query_api 4 接口
01.4       Ledger writer IC-L2-07 (P99 50ms)
01.5       fs_watcher + watchdog + throttle 10s
01.6       WP-γ-01 close (41 TC · 86.4% cov)
refactor   l1_05 → skill_dispatch 语义命名（只改自己领域）
02.1       Intent schemas (SignalScores 6 维)
02.2       hard_edge_scan (PM-09 启动 crash)
02.3       6 信号打分器 + rank (SLO 30ms)
02.4       KB boost 150ms 超时降级 + persistent executor 修 bug
02.5       FallbackAdvancer + IntentSelector.select 主入口
02.6       WP-γ-02 close (40 TC · 86.8% cov)
03.1       IC-04 schemas (对齐 §3.4)
03.2       ContextInjector 白名单
03.3       TimeoutManager (±100ms · hard-cap 300s)
03.4       RetryPolicy (idempotent · MAX_ATTEMPTS=2)
03.5       Audit (SHA-256 + 脱敏 + IC-09 双写)
03.6+03.7  SkillExecutor 6 阶段 + close (45 TC)
04.1       Subagent schemas (IC-05/12/20 + Lifecycle)
04.2       context_scope (PM-03 + PM-14 + checksum)
04.3       ResourceLimiter (asyncio Semaphore)
04.3-fix   ResourceLimiter max_queue 语义修正
04.4       ClaudeSDKClient (SDKAdapter + SIGTERM→5s→SIGKILL)
04.5+04.6  Delegator IC-05/12/20 + try_reserve + close (41 TC)
05.1+05.2  Receiver schemas + Validator
05.3+05.4+05.5  Forwarder + CrashRecovery + close (30 TC)
06         集成 (13 TC) + perf benches (2) + README
06-fix     perf 文件 rename test_bench_* 以便 pytest 收集
```

---

## 主会话 review 建议关注点

### 必审（契约红线）
1. `app/skill_dispatch/invoker/schemas.py` — IC-04 schema 是否字段级对齐 `ic-contracts.md §3.4`
2. `app/skill_dispatch/subagent/schemas.py` — IC-05/12/20 schema 对齐 §3.5/3.12/3.20
3. `app/skill_dispatch/invoker/executor.py` 6 阶段流水 — 全链失败返 `success=false` 是否 watertight
4. `app/skill_dispatch/intent_selector/hard_edge_scan.py` — 硬编码 scan 覆盖面（是否漏掉某些前缀）
5. `app/skill_dispatch/subagent/context_scope.py` — PUBLIC_CONTEXT_KEYS 白名单是否合理

### 次审（设计权衡）
6. `intent_selector/scorer.py` — 默认权重 15/45/25/10/5 · 配置项命名 · 衰减半衰期 24h/7d
7. `intent_selector/kb_boost.py` — persistent executor 是否有泄漏（atexit + finalizer 已加）
8. `async_receiver/validator.py` — lru_cache(64) 是否合适 · silent_patch 定义是否过严
9. `subagent/delegator.py` — try_reserve API 是否应替代 slot() ctx-manager（两种模式共存）

### 替换前置（波4-5）
`app/skill_dispatch/_mocks/*.py` 4 个 mock 需在波4/波5 切真实：
- `ic09_mock.py` → Dev-α L1-09 event_bus（α WP04 后）
- `ic06_mock.py` → Dev-β L1-06 L2-02（β WP03 后）
- `lock_mock.py` → Dev-α L1-09 lock_manager（α WP07 后）
- `dod_gate_mock.py` → 主-1 L1-04 L2-02（主-1 完工后）

### 已知风险 / 后续 follow-up
- **R-γ-01**（Claude Agent SDK 真集成延后）：当前用本地 `SDKAdapter` protocol + fake adapter 测试 · 真实 `anthropic` 接入留到 WP-4 Adapter 实现（pyproject `[sdk]` optional 已预留）
- **fs_watcher 真 FS 路径 coverage 66%**：watchdog Observer 事件路径 pragma no cover · 需集成期由 main-3 手工触发真实 fs 变更验证
- **scorer 权重**：PRD 给的 15/45/25/10/5 · 若生产发现不合适需离线 replay 历史 · 不建议热切

---

## 主会话 review 命令速查

```bash
# 进入 worktree
cd /Users/zhongtianyi/work/code/harnessFlow/.worktrees/dev-gamma-l1-05

# 跑全量测试
.venv/bin/pytest tests/skill_dispatch/ --cov=app.skill_dispatch --cov-report=term

# 跑 perf only
.venv/bin/pytest tests/skill_dispatch/perf/ -v -s

# 审 diff
git log --oneline ce8fd51..HEAD
git diff ce8fd51..HEAD --stat

# 审 schema 对齐
diff <(grep -oE "^\s+\w+:" app/skill_dispatch/invoker/schemas.py) \
     <(grep -A 30 "§3.4.2" ../../docs/3-1-Solution-Technical/integration/ic-contracts.md | grep -oE "^\s*- \w+")

# 审 PM-14 根字段强制
grep -rn "project_id" app/skill_dispatch/ --include="schemas.py"
```

---

## 后续未跑环节（由主会话决定）

- [ ] `superpowers:requesting-code-review` — 主会话决定是否派 python-reviewer subagent 二审
- [ ] `superpowers:finishing-a-development-branch` — 主会话决定 push + PR 时机
- [ ] Sync 到 remote `origin/feat/dev-gamma-l1-05`（当前仅本地 · 未 push · CLAUDE.md 约束需显式批准）

---

## 附：L1-05 代码树概览

```
app/skill_dispatch/
├── README.md                            # 组级文档
├── _mocks/                              # 4 mocks (待波4-5 替换)
├── registry/                            # L2-01 (5 files)
├── intent_selector/                     # L2-02 (6 files incl. __init__)
├── invoker/                             # L2-03 (6 files)
├── subagent/                            # L2-04 (5 files)
└── async_receiver/                      # L2-05 (4 files)

tests/skill_dispatch/
├── conftest.py
├── fixtures/ (registry_valid.yaml + ledger_sample.jsonl)
├── test_l2_01_registry.py               (41 TC)
├── test_l2_02_intent.py                 (40 TC)
├── test_l2_03_invoker.py                (45 TC)
├── test_l2_04_subagent.py               (41 TC)
├── test_l2_05_receiver.py               (30 TC)
├── integration/                         (13 TC)
│   ├── test_l1_05_e2e.py
│   ├── test_ic_04_05_12_20.py
│   └── test_pm14_subagent_isolation.py
└── perf/                                (2 TC)
    ├── test_bench_ic_04_dispatch.py
    └── test_bench_subagent_spawn.py

Total: 212 TC · 2-3 seconds (full suite) · 89.21% coverage
```

---

**Dev-γ out. 等主会话 review.**
