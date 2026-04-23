# app/skill_dispatch — L1-05 Skill 生态 + 子 Agent 调度

> Dev-γ · Wave 2 · 对应 MASTER-SESSION-DISPATCH 中的 L1-05。

## 定位

skill_dispatch 是 harnessFlow 所有 Skill 调用 + 子 Agent 委托的**唯一**入口。对外提供 4 个全局 IC：

| IC | 方法 | 同步/异步 | 场景 |
|---|---|---|---|
| **IC-04** `invoke_skill` | `SkillExecutor.invoke()` | 同步 | 能力抽象层调 skill（禁硬编码名） |
| **IC-05** `delegate_subagent` | `Delegator.delegate_subagent()` | 异步 | 通用 role 子 Agent |
| **IC-12** `delegate_codebase_onboarding` | `Delegator.delegate_codebase_onboarding()` | 异步 | 代码仓分析专用 |
| **IC-20** `delegate_verifier` | `Delegator.delegate_verifier()` | 异步 | S5 独立验证（PM-03 硬约束） |

## 模块分工

```
app/skill_dispatch/
├── registry/              — L2-01 能力抽象层数据底座
│   ├── schemas.py         SkillSpec / CapabilityPoint (PM-09 ≥2+builtin) / LedgerEntry / RegistrySnapshot
│   ├── loader.py          启动 5 阶段加载 · P99 ≤ 500ms
│   ├── query_api.py       query_candidates / query_subagent / query_tool / query_schema_pointer
│   ├── ledger.py          IC-L2-07 账本回写 (caller='L2-02' only) · P99 ≤ 50ms
│   └── fs_watcher.py      watchdog + throttle 10s 热更新
│
├── intent_selector/       — L2-02 意图选择器
│   ├── schemas.py         SignalScores (6 维) · Chain.advance · ExplanationCard
│   ├── scorer.py          6 信号加权打分 (15/45/25/10/5) · SLO 30ms
│   ├── hard_edge_scan.py  PM-09 启动 crash 护栏 (禁 skill 字面量)
│   ├── kb_boost.py        IC-06 调 + 150ms 超时降级
│   ├── fallback_advancer.py advance + IC-09 capability_fallback_advanced / exhausted
│   └── __init__.py        IntentSelector.select(req) 主入口
│
├── invoker/               — L2-03 IC-04 invoke_skill 调用执行器
│   ├── schemas.py         InvocationRequest / Response (success xor error) / Signature (⊇ Response)
│   ├── context_injector.py 白名单 5 字段 (防 token 泄漏)
│   ├── timeout_manager.py ±100ms 精度 · hard-cap 300s · persistent executor
│   ├── retry_policy.py    idempotent + transient only · MAX_ATTEMPTS=2 · exp backoff
│   ├── audit.py           params_hash SHA-256 + 5 类敏感脱敏 + IC-09 两次写
│   └── executor.py        IC-04 主入口 · 6 阶段流水 · dispatch ≤ 200ms SLO
│
├── subagent/              — L2-04 IC-05/12/20 子 Agent 委托器
│   ├── schemas.py         DelegationRequest (IC-05) / CodebaseOnboardingRequest (IC-12) / VerifierRequest (IC-20) / Lifecycle
│   ├── context_scope.py   COW 只读 + PM-03 白名单 + PM-14 跨 project 拒绝 + SHA-256 checksum
│   ├── resource_limiter.py asyncio Semaphore · max_concurrent=3 + queue=10 · try_reserve API
│   ├── claude_sdk_client.py SDKAdapter protocol + SIGTERM→5s→SIGKILL + spawn retry 1
│   └── delegator.py       IC-05/12/20 路由 + 降级链 · dispatch ≤ 200ms
│
├── async_receiver/        — L2-05 异步结果回收器
│   ├── schemas.py         ValidationResult / PendingEntry / CollectionRecord / idempotency_key
│   ├── validator.py       jsonschema Draft 2020-12 + SCHEMA_UNAVAILABLE 硬失败 + silent_patch E09
│   ├── forwarder.py       DoD gate 转发 L1-04 + IC-14 prev_hash + 10s 超时
│   └── crash_recovery.py  pending.jsonl + TimeoutWatcher asyncio · replay ≤ 5s
│
└── _mocks/                — 跨 L1 mock（波4-5 切真实后删）
    ├── ic09_mock.py       IC-09 event bus (hash chain · 真实: Dev-α L1-09 event_bus)
    ├── ic06_mock.py       IC-06 KB reader (真实: Dev-β L1-06 L2-02)
    ├── lock_mock.py       IC-L2-07 account lock (真实: Dev-α L1-09 lock_manager)
    └── dod_gate_mock.py   L1-04 DoD evaluator (真实: 主-1 L1-04 L2-02)
```

## PM 硬约束兑现

| PM | 规则 | 本 L1 兑现方式 |
|---|---|---|
| **PM-03** | 子 Agent 独立 session · 只读 ctx 副本 | `make_child_context` 白名单 + MappingProxyType + SHA-256 checksum |
| **PM-08** | 可追溯 100% · 每调用完整签名 | `InvocationSignature ⊇ Response + params_hash + attempt + started_at` · IC-09 两次写 |
| **PM-09** | 能力抽象 · 禁硬编码 skill 名 | `HardEdgeScan` 启动 crash · 禁 `superpowers/gstack/ecc/plugin:*` 字面量 |
| **PM-10** | 事件总线单一事实源 | 所有副作用（invoke start/finish · fallback · subagent lifecycle · DoD forward）均走 IC-09 |
| **PM-14** | project_id 根字段 | 所有 Request schema `model_validator` 强制 top/context mirror · 跨 project delegate 拒绝 |

## 契约红线

1. **IC-04 全链失败不 raise** — 返 `success=false + error + fallback_trace[]`。禁止冒泡异常给调用方。
2. **InvocationSignature ⊇ InvocationResponse** — Signature 字段必须覆盖 Response 可落盘字段 + `params_hash` + `attempt` + `started_at_ts_ns`。
3. **SCHEMA_UNAVAILABLE 硬失败** — L2-05 Validator 查不到 schema_pointer → `schema_unavailable` 状态，禁止放行。
4. **silent_patch E09** — skill 返回的 output 若包含 input 未提供且非 schema.required 的字段 → `silent_patch`，视为失败并触发 fallback。
5. **IC-20 verifier 严格白名单** — `allowed_tools` 必须 ⊆ `{Read, Glob, Grep, Bash}`，写类工具禁用。

## SLO

| 指标 | 阈值 | 测试 |
|---|---|---|
| Registry 启动加载 | P99 ≤ 500ms | `test_load_startup_within_500ms_slo` |
| Ledger 写入 | P99 ≤ 50ms | `test_ledger_write_slo_under_50ms_p99` |
| Intent rank 产链 | P99 ≤ 30ms | `test_rank_scoring_latency_p99_under_30ms` |
| KB boost 超时降级 | 150ms 内硬返 `{}` | `test_kb_boost_latency_bounded_even_on_timeout` |
| Timeout 精度 | ±100ms | `test_timeout_precision_within_100ms` |
| IC-04 dispatch | P99 ≤ 200ms | `bench_ic_04_dispatch.py` |
| Subagent spawn | P99 ≤ 1.2s | `bench_subagent_spawn.py` |
| Validator 校验 | P99 ≤ 50ms | `test_validate_latency_p99_under_50ms` |
| CrashRecovery replay 1000 | ≤ 5s | `test_crash_recovery_under_5s_for_1000_entries` |

## Mock 替换清单（波4-5 切真实前）

| Mock | 真实来源 | 切换时机 | 替换动作 |
|---|---|---|---|
| `_mocks/ic09_mock.py` | Dev-α L1-09 `app.l1_09.event_bus` | α WP04 交付后 | 删 mock · import 真实 append_event |
| `_mocks/ic06_mock.py` | Dev-β L1-06 `app.l1_06.l2_02` KB reader | β WP03 交付后 | 删 mock · IntentSelector 换 import |
| `_mocks/lock_mock.py` | Dev-α L1-09 `app.l1_09.lock_manager` | α WP07 交付后 | 删 mock · LedgerWriter 换 import |
| `_mocks/dod_gate_mock.py` | 主-1 L1-04 `app.l1_04.l2_02` DoD evaluator | 主-1 完工后 | 删 mock · DoDForwarder 换 import |

## 使用示例

### IC-04 同步调 skill（能力抽象）

```python
from app.skill_dispatch.intent_selector import IntentSelector
from app.skill_dispatch.invoker.executor import SkillExecutor
from app.skill_dispatch.invoker.schemas import InvocationRequest

executor = SkillExecutor(selector=..., event_bus=..., ledger=..., skill_runner=...)
rsp = executor.invoke(InvocationRequest(
    invocation_id="inv-1",
    project_id="proj_abc",
    capability="write_test",          # 能力名（不是 skill 名）
    params={"spec": "..."},
    caller_l1="L1-04",
    context={"project_id": "proj_abc", "wp_id": "wp-12"},
))
if rsp.success:
    use(rsp.result)
else:
    log(rsp.error["code"], rsp.fallback_trace)
```

### IC-20 委托 verifier（PM-03 独立 session）

```python
from app.skill_dispatch.subagent.delegator import Delegator
from app.skill_dispatch.subagent.schemas import VerifierRequest

ack = await delegator.delegate_verifier(VerifierRequest(
    delegation_id="ver-1",
    project_id="proj_abc",
    wp_id="wp-12",
    blueprint_slice={...},
    s4_snapshot={...},
    acceptance_criteria=["A", "B", "C"],
))
# ack.dispatched == True · 异步 final_report 通过 IC-09 event "subagent_final_report" 回推
```

## 目录约束

- 所有代码只在 `app/skill_dispatch/` 内 · **不跨 L1 写代码**
- `_mocks/` 严格隔离 · 真实 IC 到位后整文件删除
- `schemas.py` 只放 Pydantic 模型 · 业务逻辑在兄弟文件
- 每业务文件 ≤ 280 行（单责约束）

## 组级 DoD

- [x] pytest 全绿 · 总 TC 200+
- [x] coverage ≥ 85%（非 mock / 非 fs_watcher 真 FS 路径）
- [x] IC-04/05/12/20 schema 严格对齐 `ic-contracts.md §3.4/3.5/3.12/3.20`
- [x] 启动硬编码 scan 绿（PM-09）
- [x] PM-14 跨 project 拒绝 + PM-03 独立 session 验证绿
- [x] 降级链 4 路径全测（retry → fallback_advance → exhausted → IC-15 信号）
- [x] 静默 patch 检测（E09）绿
- [x] 所有 SLO TC 绿
- [x] app/skill_dispatch/README.md 已写（本文件）
