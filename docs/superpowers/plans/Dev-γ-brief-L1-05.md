---
doc_id: dev-gamma-brief-L1-05
doc_type: design-brief
source: Explore subagent 蒸馏自 P0 parent_doc
session: Dev-γ
created_at: 2026-04-23
status: locked-reference
---

# Dev-γ L1-05 Skill生态+子Agent调度 · 必读 Brief

> 源：2-prd L1-05 · 3-1 architecture + L2-01~05 · ic-contracts §3.4/3.5/3.12/3.20 · p0-seq §3
> 保持为 locked 参考 · 实施中如发现与源文档冲突，走 Dev-γ-exe-plan §6 情形 B/D/E 回锤源文档。

---

## §0 快速导航
- **主要输出**：5 个 L2 + 4 个全局 IC（IC-04 / IC-05 / IC-12 / IC-20）
- **关键输入**：能力点 → Skill 候选链 → 执行 + 子 Agent 委托 → 回传校验
- **核心约束**：PM-03（独立 session）+ PM-09（能力抽象层）+ PM-14（project_id）
- **交付物**：Skill 调用路径、子 Agent 生命周期、回传正确性守门

---

## §1 PM 硬约束（影响全 L1-05 的规则）

| 规则 ID | 定义 | 本 L1-05 验证方式 | 触发场景 |
|---|---|---|---|
| **PM-03** | 子 Agent 独立 session · 只读 context 副本 + 结构化回传 · 禁共享状态 | L2-04 启动时：ContextCopy COW 指针 · allowed_tools 白名单 · 禁反向写 task-board | IC-05 / IC-12 / IC-20 委托时 |
| **PM-09** | 能力点绑定 · 每能力 ≥ 2 备选 fallback · Skill 名不暴露上游 | L2-01 启动时：每 capability ≥ 2 候选 + 内建兜底 · 硬编码 skill 名启动拒绝 | 任何 IC-04 invoke_skill 调用 |
| **PM-14** | project_id 全局主键 · 所有 IC payload 根字段必含 · 所有持久化路径按 `projects/<pid>/...` 分片 | 所有 6 IC 触点（IC-04/05/12/20 + IC-L2-01/06/07）首字段验证 project_id · 拒绝跨 project 调用 | 几乎所有请求 |
| **PM-10** | 事件总线单一事实源 · 所有副作用必通过 IC-09 落盘 | L2-01/02/03/04/05 各自独立发 IC-09 · L1-09 汇聚 append-only · 审计查询通过 IC-09 回放 | 每 skill 调用/降级/超时/校验都走 IC-09 |
| **PM-08** | 可追溯 100% · 每次调用产生完整签名（capability + skill_id + params_hash + duration + attempt + result_summary） | L2-03 每次 invoke 产 InvocationSignature · L2-04 每次 delegate 产 DelegationSignature · L2-05 校验通过/失败都记 | 走 IC-09 事件 |

---

## §2 4 个全局 IC 字段级契约

### IC-04 invoke_skill（最高频 IC）

**语义**：多 L1 通过能力抽象层（不硬编码 skill 名）同步调用 skill 或原子工具。

**入参** (ic-contracts.md §3.4.2)：
- 必填：`invocation_id`, `project_id`, `capability`, `params`, `caller_l1`, `context`
- 可选：`timeout_ms` (default 30s), `allow_fallback` (default true), `trigger_tick`

**出参** (§3.4.3)：
- 必填：`invocation_id`, `success`, `skill_id`, `duration_ms`, `fallback_used`
- 可选：`result`（success=true 时）, `error`（success=false 时）, `fallback_trace[]`

**错误码** (§3.4.4)：
- `E_SKILL_NO_CAPABILITY`：capability tag 无注册 → 拒绝
- `E_SKILL_NO_PROJECT_ID`：context 缺 project_id → 拒绝
- `E_SKILL_TIMEOUT`：超 timeout_ms → 强终止 + fallback
- `E_SKILL_ALL_FALLBACK_FAIL`：主 + 全备选失败 → 返回失败 + 完整 fallback_trace
- `E_SKILL_PARAMS_SCHEMA_MISMATCH`：params 不符 schema → 拒绝
- `E_SKILL_PERMISSION_DENIED`：工具权限未授予 → 降级 + 告警

**SLO**：P95 ≤ 按 skill SLO（毫秒级~分钟级）· P99 ≤ skill timeout 5min hard-cap · dispatch ≤ 200ms

**关键约束**：
- 禁硬编码 skill 名（PM-09）
- 调用失败必走 fallback 链
- 结果必过 L2-05 schema 校验

---

### IC-05 delegate_subagent（通用子 Agent 委托）

**语义**：委托独立 session 的通用角色子 Agent（researcher / coder / reviewer 等），区别于 IC-20 特化 verifier。

**入参** (§3.5.2)：
- 必填：`delegation_id`, `project_id`, `role`, `task_brief`, `context_copy`, `caller_l1`
- 可选：`allowed_tools[]`, `timeout_s` (default 1800)

**出参（Dispatch 同步 §3.5.3）**：`delegation_id`, `dispatched`, `[subagent_session_id]`

**出参（Final Report 异步 via IC-09 §3.5.4）**：
- 必填：`subagent_session_id`, `delegation_id`, `status`, `artifacts`
- 可选：`final_message`, `usage{total_tokens, tool_uses, duration_ms}`
- `status ∈ [success, partial, failed, timeout]`

**错误码** (§3.5.5)：
- `E_SUB_NO_PROJECT_ID` → 拒绝
- `E_SUB_ROLE_UNKNOWN` → 拒绝
- `E_SUB_BRIEF_TOO_SHORT`（< 50 字）→ 拒绝
- `E_SUB_SESSION_LIMIT`（并发 ≥ 上限 default 5）→ 延迟 queue
- `E_SUB_TIMEOUT` → 强终止 + partial artifacts
- `E_SUB_TOOL_ERROR` → 内部重试 1 次 + 失败

**SLO**：Dispatch ≤ 200ms · Result ≤ subagent timeout (default 30min)

---

### IC-12 delegate_codebase_onboarding（代码仓分析子 Agent）

**语义**：大代码仓 codebase-onboarding 的特化委托 · IC-05 的特化版本 · 异步 · 结果写回 project KB。

**入参** (§3.12.2)：
- 必填：`delegation_id`, `project_id`, `repo_path`, `kb_write_back`
- 可选：`focus{interfaces[], entry_points[]}`, `timeout_s` (default 600)

**出参（Dispatch 同步）**：`delegation_id`, `dispatched`, `[subagent_session_id]`

**出参（Final Report 异步 via IC-09）**：
- 必填：`delegation_id`, `status`, `[structure_summary]`
- 可选：`kb_entries_written[]`
- `status ∈ [success, partial, failed]`

**错误码** (§3.12.4)：
- `E_OB_REPO_PATH_INVALID` → 拒绝
- `E_OB_REPO_TOO_LARGE`（> 100 万行）→ 拒绝
- `E_OB_TIMEOUT` → 返回 partial + 标记
- `E_OB_KB_WRITE_FAIL` → 继续返回 success + 标记 kb_write_partial

**SLO**：Dispatch ≤ 200ms · Result ≤ 10min

---

### IC-20 delegate_verifier（S5 独立验证）

**语义**：S5 TDD 执行验证的特化委托 · 必走独立 session（PM-03 硬约束）· 三段证据链（blueprint 对齐 + S4 diff + DoD）。

**入参** (§3.20.2)：
- 必填：`delegation_id`, `project_id`, `wp_id`, `blueprint_slice`, `s4_snapshot`, `acceptance_criteria`
- 可选：`timeout_s` (default 1200), `allowed_tools=[Read, Glob, Grep, Bash]`（严格限制）

**出参（Dispatch 同步）**：`delegation_id`, `dispatched`, `verifier_session_id`

**出参（Verdict 异步 via IC-09）**：
- 必填：`delegation_id`, `verdict`, `three_segment_evidence`, `confidence`, `duration_ms`
- `verdict ∈ [PASS, FAIL_L1, FAIL_L2, FAIL_L3, FAIL_L4]`
- `three_segment_evidence{ blueprint_alignment, s4_diff_analysis, dod_evaluation }`

**错误码** (§3.20.4)：
- `E_VER_MUST_BE_INDEPENDENT_SESSION` → 拒绝（PM-03 硬约束）
- `E_VER_TIMEOUT` → verdict=FAIL_L4 + partial evidence + 告警
- `E_VER_EVIDENCE_INCOMPLETE` → verdict=FAIL_L1 + 自动降级
- `E_VER_TOOL_DENIED` → 拦截 + 继续 + 标记证据

**SLO**：Dispatch ≤ 200ms · Result ≤ verifier timeout (default 20min)

---

## §3 5 个 L2 关键算法/协议

### L2-01 Skill 注册表（能力抽象层数据底座）

**启动 5 阶段加载** (tech-design §6)：
1. **Load `registry.yaml`**：从 `projects/<pid>/skills/registry-cache/registry.yaml` 读主映射
2. **Parse capability_points**：每个能力点 → candidates[]（必 ≥ 2 + 内建兜底）
3. **Validate each capability**：缺二级候选 → 注入内建兜底 skill · 无 schema 指针 → assert fail
4. **Load ledger（可用性账本）**：从 `ledger.jsonl` 恢复失败记忆、成功率、版本
5. **Create snapshot**：一次性固化 `snapshot-{ts}.yaml` 防重载期间停服

**热更新协议**（3 源并发抖动合并 · throttle 10s）：
- **File watcher**：`registry.yaml` 变更触发 reload
- **IC-09 订阅**：外部生态事件（skill 升级/弃用）触发 reload
- **显式 API**：`reload_registry()` 运维触发

**读写分离 + 双 buffer**：
- Reading snapshot + Writing shadow · 交换指针原子操作
- 重载 / 账本回写与读查询完全解耦

**账本回写接口**（仅 L2-02 可写 · IC-L2-07）：
- 异步批处理（100ms 合并窗口）· 全局锁（L1-09 提供）
- 字段：capability · skill_id · success_count · failure_count · last_attempt · failure_reason

**SLO**：capability 查询 P99 ≤ 2ms · 重载 P99 ≤ 500ms · 账本回写 P99 ≤ 50ms

---

### L2-02 Skill 意图选择器（多信号混合排序）

**排序算法骨架** (tech-design §6)：

```
input: capability + constraints{max_cost, max_timeout, preferred_quality} + failure_memory
output: [首选, 备选1, 备选2, 内建兜底] 链 + explanation_card

Step 1: 硬约束过滤
  - 移除 unavailable 的候选（不降权 · 直接剔）
  - 按 cost / timeout 上限过滤
  - 按 preferred_quality 过滤

Step 2: 多信号打分（6 维）
  signal[0] = availability（硬）— 最近 N=30 次调用可用率
  signal[1] = cost（权重 15%）— $ 单位
  signal[2] = success_rate（权重 45%）— 历史成功率（90 天滑动窗）
  signal[3] = failure_memory（权重 25%）— 近 N 次失败的衰减记忆（指数衰减）
  signal[4] = recency（权重 10%）— 最近调用时间（新鲜度）
  signal[5] = kb_boost（权重 5%）— KB Recipe/Trap 历史经验 boost

Step 3: 可选灰度探测（V1 关闭）
  - 5% 概率让次优成为首选（防先发者赢者通吃）
  - 事件显式标注 `probe_attempt=true`

Step 4: 生成 explanation_card
  - 自然语言：为什么选了这个？
  - 结构化：各信号得分 + 权重
```

**硬编码扫描**（§10 startup assert）：
- 启动时 grep 本 L2 代码 · 禁 `superpowers:*` / `gstack:*` / `ecc:*` 字面量
- 发现 → reject startup + log 黑名单位置

**SLO**：产链 P99 ≤ 30ms · fallback 前进 ≤ 10ms · KB 读 P95 ≤ 150ms（否则丢弃）

---

### L2-03 Skill 调用执行器（context 注入 + retry + timeout + 签名）

**调用 6 阶段流水**：
1. **Resolve fallback chain**：IC-L2-01 查候选 → L2-02 排序 → 输出链
2. **ContextInjector 白名单**：从上游 context 注入 `project_id / wp_id / loop_session_id / decision_id`（防泄漏）
3. **TimeoutWatcher**：per-skill default (30s) + per-call override + hard-cap 5min
4. **RetryPolicy**：skill 声明 `idempotent: true` 允许最多 2 次重试（网络闪断恢复）· false 直接 fallback
5. **InvocationSignature 准备**：调用前生成 `invocation_id + params_hash + started_at`（防崩溃丢签名）
6. **Fallback 前进**：首选失败 → IC-L2-03 请 L2-02 取下一候选（不能自行决策）

**params_hash 脱敏**：
- SHA-256 over canonical JSON
- 敏感字段（token / key / password 后缀匹配）先脱敏再 hash
- 配置 `sensitive_field_patterns: [.*_token, .*_key, .*_password]`

**审计种子生成时机**：
- **调用前** append InvocationSignature 初始形态
- **调用后** update 补齐 duration / result_summary / validate_status
- 启动即 append 防崩溃丢事件（IC-09 两次写）

**SLO**：签名准备 P99 ≤ 100ms · 原子工具 ≤ 10ms · fallback 前进 ≤ 1s

---

### L2-04 子 Agent 委托器（独立 session 生命周期 + PM-03 隔离）

**Spawn 协议**（Claude Agent SDK）：
```
1. 分配 subagent_session_id
2. ContextCopy: COW 指针（非深拷贝）
   - 显式允许列表：project_id, wp_id, related_artifacts[], dod_exprs
   - 禁访问：task_board(主 session), KB 写入, 文件系统全局
3. 工具白名单：allowed_tools = [Read, Glob, Grep, Bash]（子 Agent verifier 严格限制）
4. 启动独立 Claude session（与主 session 完全隔离）
```

**Lifecycle 状态机**（5 状态）：
```
provisioning ─► running ─► completed
               │          ├─ success (normal exit)
               │          ├─ partial (timeout but partial artifacts)
               │          └─ failed (error / crash)
               └─ killed (超时 SIGTERM+SIGKILL / 资源超限)
```

**心跳监控**（default 5min 无进展即超时）：
```
设置 deadline_ts = now + timeout_s
后台心跳 ticker（interval = timeout_s / 10）
  if elapsed > deadline_ts:
    → SIGTERM（优雅退出）
    → wait 10s
    if still running:
      → SIGKILL（强制杀死）
      → 回收临时目录 + context 副本
```

**降级链**（BF-E-09 · 2 次失败自动降级）：
```
attempt 1 失败 → 新 session 重试（attempt 2）
attempt 2 失败 → 标记 "degraded" · 走降级路径：
  Level 1：简化版本（缩小 goal scope）
  Level 2：跳过（缺省行为）
  Level 3：硬暂停
```

**max_concurrent_subagents = 3**（default · 防 Claude API rate-limit）

**SLO**：Dispatch ≤ 200ms · 心跳精度 ≤ 1min · 资源上限执行时间 ≤ 5s

---

### L2-05 异步结果回收器（schema 校验 + DoD 网关 + 幂等）

**三段校验流程**：
```
Step 1: SchemaValidation（jsonschema Draft 2020-12）
  - IC-L2-06 查 L2-01 取回传 schema 指针
  - 校验失败 → status=format_invalid + error{kind, path, expected, actual}
  - schema_unavailable → 自动 FAIL（硬约束 · 禁放行）

Step 2: DoDGate 转发（不自己求值）
  - 格式通过 → 转发 L1-04 L2-02 DoD 表达式编译器
  - L1-04 求值后通过 IC-14 回推 verdict{PASS / FAIL_L1~L4}
  - 两层事件（L2-05 + L1-04 各落一次）· via verdict_id 关联

Step 3: ResultAssembler
  - 装配统一 CollectionRecord VO：
    {status, result, dod_verdict, validation_errors[], assembled_at}
```

**幂等 result_id**：
```
result_id = hash(invocation_id + skill_id + started_at)
同 result_id 的重复请求返回缓存 CollectionRecord（窗口 5min）
```

**超时识别与恢复**：
```
维护 pending.jsonl（append-only）：
  {result_id, deadline_ts_ns, status, capability}
后台 TimeoutWatcher 协程（asyncio）：
  每 60s tick 扫 pending · 超时 → status=timeout + move to rejected
崩溃恢复：
  启动时 replay pending.jsonl · 重建内存表
  Finalized 记录通过 compaction 清理（日维护 cron）
```

**静默 patch 检测 E09**（PRD §12.5 禁止 8）：
- 若发现回传包含"默认字段"（caller 未提供但现在有了）
- 日志标注 `N5_SILENT_PATCH_DETECTED` · 视为失败触发 fallback

**SLO**：校验 P99 ≤ 50ms · 大报告 ≤ 500ms · 超时精度 ≤ 60s · 崩溃恢复 ≤ 5s

---

## §4 5 个 L2 全部错误码清单

| L2 | 错误码 | 触发条件 | 处理 |
|---|---|---|---|
| **L2-01** | `E_REG_MISSING_CAPABILITY` | capability tag 无注册 | 拒绝 + assert |
| | `E_REG_SINGLE_CANDIDATE` | capability 候选 < 2 | startup fail + INFO 注入兜底 |
| | `E_REG_NO_SCHEMA_POINTER` | skill 注册缺 schema 指针 | assert fail |
| | `E_REG_RELOAD_CONFLICT` | reload 期间读取冲突 | 返回 last_known_good snapshot |
| | `E_REG_FILE_NOT_FOUND` | registry.yaml 文件缺 | degraded 返回快照 + WARN |
| **L2-02** | `E_INTENT_BOUNDARY_VIOLATION` | 越界查询（如超越 cost 上限） | 拒绝 · assert |
| | `E_INTENT_NO_AVAILABLE` | 所有候选都 unavailable | chain=[内建兜底] |
| | `E_INTENT_KB_TIMEOUT` | IC-06 KB 读超 150ms | 丢弃 KB 信号 · 继续排序 |
| | `E_INTENT_EXPLANATION_TRUNCATED` | explanation_card 超大 | 截断 + 标注 |
| | `E_INTENT_CHAIN_EXHAUSTED` | fallback 链全失败 | 返回 exhausted + 调用方决定暂停 |
| **L2-03** | `E_SKILL_INVOCATION_NO_PROJECT_ID` | context 缺 project_id | 拒绝 |
| | `E_SKILL_INVOCATION_CROSS_PROJECT` | invocation_id 与 pid 不匹配 | 拒绝 + 告警 |
| | `E_SKILL_INVOCATION_TIMEOUT` | 超 timeout_ms | 强终止 + fallback 前进 |
| | `E_SKILL_INVOCATION_RETRY_EXHAUSTED` | 重试 2 次仍失败（idempotent） | fallback 前进 |
| | `E_SKILL_INVOCATION_CONTEXT_INJECTION_FAILED` | ContextInjector 白名单过滤失败 | 拒绝（上游 bug） |
| | `E_SKILL_INVOCATION_AUDIT_SEED_FAILED` | IC-09 append 失败 | 继续（L1-09 应该不会失败） |
| **L2-04** | `E_SUB_NO_PROJECT_ID` | context_copy 缺 project_id | 拒绝 |
| | `E_SUB_SPAWN_FAILED` | Claude Agent SDK spawn 失败 | 降级 + 重试 1 次 |
| | `E_SUB_CONTEXT_ISOLATION_VIOLATION` | 子 Agent 访问禁区 | 拦截 + 继续 + 标注 trace |
| | `E_SUB_TOOL_NOT_ALLOWED` | 工具白名单检查失败 | 拦截 + fallback |
| | `E_SUB_TIMEOUT` | 超 timeout_s（default 30min） | SIGKILL + 收集 partial artifacts |
| | `E_SUB_RESOURCE_QUOTA_EXCEEDED` | token / 工具调用数超限 | 强终止 + fallback |
| **L2-05** | `E_COLLECT_SCHEMA_UNAVAILABLE` | capability 无 schema 指针 | 返回 SCHEMA_UNAVAILABLE · 视为失败 |
| | `E_COLLECT_FORMAT_INVALID` | schema 校验不过 | 返回 validation_errors[] + fallback 触发 |
| | `E_COLLECT_DOD_GATE_TIMEOUT` | 转发 L1-04 超时 | 返回 timeout + 告警 |
| | `E_COLLECT_SILENT_PATCH_DETECTED` | 静默补默认字段 | N5 违规 · 标注 + 视为失败 |
| | `E_COLLECT_RESULT_TIMEOUT` | 超时表中记录超期 | status=timeout · move to rejected |
| | `E_COLLECT_IDEMPOTENCY_KEY_CONFLICT` | 同 result_id 重复请求 | 返回缓存 + 事件重放 |

---

## §5 TC 分类统计（来自 Dev-γ exe-plan §3 + 3-2 tests 扫描）

| L2 | 功能 TC | 边界 TC | 失败 TC | 性能 TC | 总数（exe-plan 声明） |
|---|---|---|---|---|---|
| **L2-01** | 加载/查询/热更新 | 边界容量/快照 | 异常降级 | 并发 | ~40 |
| **L2-02** | 排序/信号融合 | KB 缺失/超时 | 无候选/链耗尽 | 并发/缓存 | ~40 |
| **L2-03** | 调用/重试/fallback | 超时/权限 | 审计失败/脱敏 | 并发/管道 | ~39 |
| **L2-04** | spawn/心跳/kill | 资源上限/隔离 | timeout/crash | 并发数/ctx 大小 | ~39 |
| **L2-05** | 校验/DoD/装配 | 超时表/崩溃恢复 | schema 缺失/patch | 并发/大报告 | ~38 |
| **合计** | - | - | - | - | **196** L2 + **≥ 8** 集成 = **≥ 204** |

> 注：exe-plan §3.0 合计声明 ~249 TC · 差值来自集成 WP06 额外 TC 与 tests.md 细粒度。以 exe-plan 总数 **249** 作 DoD 基线。

---

## §6 P0 风险 + 降级矩阵

| 失败路径 | 触发条件 | 降级行为 | 恢复机制 |
|---|---|---|---|
| **Skill 全链失败** | 主 + 2 个备选 + 内建兜底都失败 | 返回 `capability_exhausted` · 调用方硬暂停 | 等运维修复或注册新备选 |
| **Subagent 超时 × 2** | attempt 1 → 新 session attempt 2 → 仍超时 | 降权至 "degraded" · 下次 L2-02 排序降低 · 走备选 | 子 Agent 修复后下次新调用重评 |
| **Schema 指针缺失** | L2-05 查不到 schema → `SCHEMA_UNAVAILABLE` | 自动失败 + fallback · 禁放行 | 新 capability 注册时补提供 schema pointer |
| **DoD 表达式转发失败** | L1-04 编译/求值超时 | 返回 timeout + 告警升级 · verdict=FAIL_L4 | L1-04 修复 · 重跑验证 |
| **超时表崩溃丢记录** | L2-05 进程崩溃且 pending.jsonl 未 flush | 启动时 replay pending.jsonl 重建表 · 标 `TIMEOUT_RECOVERY` | 定期 compaction + fsync |
| **Context 快照超大** | COW 指针内容 > memory 预算 | 降级到 `CONTEXT_OVERFLOW` · L2-04 返回失败 + 告警 | 上游减少 context 信息量 |
| **Skill 不可用被误剔** | L2-01 probe 失败判定 unavailable | L2-02 直接剔除 → 可能误掉某个备选 | L2-01 探测间隔调短 · 或强制重载 |
| **PM-09 violation 逃脱** | 硬编码 skill 名被 grep miss | 运行时 assert fail 拒绝调用 | 代码审查 + 启动时扫描覆盖 |

---

## §7 设计陷阱（⚠️ 标）

### ⚠️ 1. IC-04 出参与 L2-03 InvocationSignature 字段不完全对齐
- **现象**：ic-contracts.md §3.4.3 出参字段是 L2-03 tech-design §7 InvocationSignature 的子集
- **解决**：L2-03 的 InvocationSignature 必须是 IC-04 出参的**超集**（多出 attempt + params_hash），不能反过来

### ⚠️ 2. L2-04 COW 指针在主 session 被修改后的脏读
- **现象**：COW 指针避免深拷贝延迟（< 5ms）但主 session 对快照区域的 append-only 是"约定" · 运行时未强制
- **解决**：子 Agent 启动时生成 `context_checksum` · 启动后任何时点验证（可选告警但继续）· 或强制深拷贝（+ ~200ms）— 本次选 checksum 方案

### ⚠️ 3. L2-02 权重调优后难回溯
- **现象**：权重硬写会掩盖之前已发生的错误排序 · 改权重要做离线 replay 对比
- **解决**：权重写配置表 `signal_weights` · 灰度探测前先离线 replay · 再上线

### ⚠️ 4. L2-05 的 DoD 转发与 L1-04 的时序竞态
- **现象**：L2-05 和 L1-04 各自落 IC-09 事件 · 时序日志可能显示"顺序混乱"
- **解决**：IC-14 转发体包含 `prev_hash` · 或 L2-05 ↔ L1-04 走同步调用（不经事件总线）— 本次选 IC-14 prev_hash

### ⚠️ 5. L2-01 快照文件无清理策略
- **现象**：频繁重载产生大量 snapshot 文件
- **解决**：配置 cleanup 策略 — 保留最近 N=5 或 mtime > 7 天删

---

## §8 关键参考路径

| 内容 | 路径 | 优先级 |
|---|---|---|
| PM-14 项目上下文模式 | docs/3-1-Solution-Technical/projectModel/tech-design.md §9 | P0 |
| IC 契约全文 | docs/3-1-Solution-Technical/integration/ic-contracts.md | P0 |
| 时序图参考（IC-04） | docs/3-1-Solution-Technical/integration/p0-seq.md §3 | P1 |
| L1-04 DoD evaluator | docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-*.md | P1 |
| TDD 测试清单 | docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/L2-*-tests.md | P0（写测试时精读） |

---

*— Dev-γ L1-05 Brief · v1.0 · 2026-04-23 · 蒸馏自 ~18800 行源文档 —*
