---
doc_id: exe-plan-dev-alpha-L1-09-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md（总索引）
  - docs/1-goal/HarnessFlowGoal.md（顶层目标 · PM-08 单一事实源 · 可追溯率 100%）
  - docs/2-prd/L0/scope.md（§8 整合 · §11 PM-14 · §12-§14 业务流）
  - docs/2-prd/L1-09 韧性+审计/prd.md（L1-09 产品边界 · 硬约束 · GWT）
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md（本 L1 顶层架构 · 1733 行 · §11 L2 分工 · §5 时序 · §6 按 project 分片）
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-01-事件总线核心.md（2078 行 · 14 错误码）
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md（1538 行）
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-03-审计记录器+追溯查询.md（1782 行 · 22 错误码）
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-04-检查点与恢复器.md（2223 行 · 40 错误码）
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md（2057 行 · 20 错误码）
  - docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-01-事件总线核心-tests.md（862 行 · 56 TC）
  - docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-02-锁管理器-tests.md（844 行 · 50 TC）
  - docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-03-审计记录器+追溯查询-tests.md（935 行 · 56 TC）
  - docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-04-检查点与恢复器-tests.md（900 行 · 54 TC）
  - docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-05-崩溃安全层-tests.md（889 行 · 53 TC）
  - docs/3-1-Solution-Technical/integration/ic-contracts.md（§3.9 IC-09 · §3.10 IC-10 · §3.18 IC-18）
  - docs/3-3-Monitoring-Controlling/hard-redlines.md（待 O 会话完 · fallback 用 3-1 §11）
  - docs/3-3-Monitoring-Controlling/dod-specs/general-dod.md（DoD 规约 fallback）
version: v1.0
status: draft
author: main-session
assignee: Dev-α（独立 AI 会话 · 代码 + TDD 同会话）
created_at: 2026-04-23
updated_at: 2026-04-23
wave: 1（底座 · 脊柱先行）
priority: P0（所有其他组依赖 IC-09）
estimated_loc: ~17400 行 Python
estimated_duration: 5-7 天（含 TDD + debug）
---

# Dev-α · L1-09 韧性+审计 · Execution Plan

> **本 md 定位**：4-0 master plan §3.2 定义的 Dev-α 独立开发组的**详细执行计划**。独立 AI 会话读本 md 开工 · 代码 + TDD 必须同会话完成（4-0 §1.4 约束 Q-02）。
>
> **组一句话**：**把 3-1 L1-09 韧性+审计 5 L2 tech-design（9678 行）和 3-2 L1-09 5 tests（4435 行 · 269 TC · 248 test_fn）** → **落地成可运行 Python 代码**（预估 ~17400 行） · **IC-09 事件总线是整个 harnessFlow 的脊柱**（所有其他 L1 通过 IC-09 写事件） · **本组先行于所有其他 Dev 组**。
>
> **硬性原则**（对应 4-0 master 4 硬约束）：
> - Q-01 **质量不妥协**：本组作为脊柱 · 必须完工且稳定 · 否则后续所有组 IC-09 集成失败
> - Q-02 **代码+TDD 同会话**：严格 TDD 红→绿→重构 · 先写失败的测试 · 再写实现
> - Q-03 **自修正机制**：执行中发现源文档错 · 回 4-0 §6 协议修 2-prd/3-1/3-2
> - Q-04 **本组不跨 L1**：只动 `app/l1_09/` 和 `tests/l1_09/` · 不碰其他 L1 代码
>
> **PM-08 + PM-14 双锁**：L1-09 是 PM-08（单一事实源）的唯一落实方 + PM-14 物理分片的核心执行者。所有产出必严格按 `projects/<pid>/events.jsonl · audit.jsonl · checkpoints/` 分片。

---

## §0 撰写进度

- [x] §1 组定位 + L2 清单（5 L2）
- [x] §2 源文档导读（P0-P2 清单 · 20 份必读 · 每份怎么用）
- [ ] §3 WP 拆解（5 L2 × 13 WP · 天级粒度 · L3/L4 代码文件清单）
- [ ] §4 WP 依赖图（组内 + 跨组 mock）
- [ ] §5 每日 standup + commit 规范
- [ ] §6 自修正触发点（5 情形映射到 L1-09 特有场景）
- [ ] §7 本组对外契约（IC mock + 真实替换时机）
- [ ] §8 验收 DoD（脊柱特化 · fsync/hash_chain/halt 强覆盖）
- [ ] §9 风险 + 降级（R-01 脊柱稳定性是全局 P0）
- [ ] §10 交付清单 + commit 工作流

---

## §1 组定位 + 范围

### 1.1 本组在 harnessFlow 整个开发阶段的位置

```
波 1 · 底座（Dev-α + Dev-β + Dev-θ1）        ← 本组在此
  ↓ 脊柱 IC-09 ready · 事件总线可写可查
波 2 · 业务层（Dev-γ/δ1/ε/η）
  ↓ 业务 L1 ready · 各自发 IC-09 事件到 L1-09
波 3 · 监督+扩展（Dev-ζ/δ2/θ2）
  ↓ 监督 L1-07 订阅 IC-09 · 完整审计链成型
波 4+ · 核心集成（主-1 主-2 主-3）
```

**本组的战略重要性**：**唯一"其他组无法 mock 久"的底座组**。其他组在开发期可 mock IC-09 · 但集成期必须真实替换 · 若本组晚到或不稳 · 其他组集成会 cascade 失败。

### 1.2 本组范围（L1/L2 清单）

| L2 | 简介 | 3-1 tech-design 行数 | 预估代码量 | 估时 | 对外 IC |
|:---:|:---|---:|---:|:---:|:---|
| **L2-05** 崩溃安全层 | WAL + atomic_write + sha256 链 + fsync 硬约束 | 2057 | ~3700 | 1.5 天 | 内部 · 被 L2-01/L2-04 调 |
| **L2-01** 事件总线核心 | IC-09 `append(event)` 唯一写入口 · 每事件必 fsync · halt on fail | 2078 | ~3700 | 1.5 天 | **IC-09**（全 L1 写）· IC-L2-02（订阅）· IC-L2-04（只读 iterator）|
| **L2-02** 锁管理器 | flock + FIFO ticket + 死锁检测 + TTL 泄漏回收 | 1538 | ~2800 | 1 天 | 内部 · 被 L2-04 调（force_release_all）|
| **L2-03** 审计记录器+追溯查询 | IC-18 `query_audit_trail` · 按 pid/time/actor/type 追溯 · append-only jsonl + rotation | 1782 | ~3200 | 1 天 | **IC-18**（L1-10 UI 查）· IC-09 落盘延续 |
| **L2-04** 检查点与恢复器 | snapshot + bootstrap + Tier 1-4 恢复 · 30s 硬约束 | 2223 | ~4000 | 1.5 天 | **IC-10** replay_from_event · 内部 recovery |
| **合计** | 5 | **9678** | **~17400** | **5-7 天** | 3 全局 IC + 2 内部 IC |

### 1.3 Out-of-scope（本组不做）

- ❌ 分布式 event bus（V2+ 考虑 · 本版本单机 jsonl）
- ❌ 跨 project 事件总线（每 project 独立分片 · PM-14 硬约束）
- ❌ 二进制事件编码（本版本 JSON · 性能够 · protobuf 留 V3+）
- ❌ 外部审计系统对接（Grafana / ELK 等 · 3-3 metrics 对接留给后续）
- ❌ snapshot 增量模式（全量先 · 增量留 V2+ OQ-L209-04-02）

### 1.4 本组产出清单（What）

**代码**（约 17400 行）：
```
app/l1_09/
├── event_bus/                       （L2-01 · 事件总线核心）
│   ├── core.py                      核心 append 逻辑
│   ├── emitter.py                   出口 API
│   ├── subscriber.py                订阅者注册
│   ├── reader.py                    read_range iterator
│   ├── halt_guard.py                fsync 失败的硬 halt 守护
│   └── schemas.py                   Event / Subscriber Pydantic
├── lock_manager/                    （L2-02 · 锁管理器）
│   ├── manager.py                   acquire/release/is_locked
│   ├── fifo_queue.py                FIFO ticket 队列
│   ├── deadlock_detector.py         环检测
│   ├── janitor.py                   TTL 泄漏回收
│   └── schemas.py                   LeaseToken / LockError
├── audit/                           （L2-03 · 审计记录器+追溯查询）
│   ├── writer.py                    IC-09 落盘延续
│   ├── query.py                     IC-18 追溯 query_audit_trail
│   ├── rotation.py                  文件滚动
│   ├── gate.py                      rebuilding/open/closed gate 三态
│   └── schemas.py                   Trail / Anchor / EvidenceLayer
├── checkpoint/                      （L2-04 · 检查点与恢复）
│   ├── snapshot.py                  周期 + 关键事件触发
│   ├── recovery.py                  bootstrap 主路径
│   ├── tier_fallback.py             Tier 1→4 降级
│   ├── shutdown.py                  drain + final snapshot
│   └── schemas.py                   SnapshotResult / RecoveryResult
└── crash_safety/                    （L2-05 · 崩溃安全层）
    ├── atomic_writer.py             write_atomic · tmpfile+rename+fsync
    ├── appender.py                  append_atomic · O_APPEND+fsync
    ├── hash_chain.py                sha256 链 · canonical_json + JCS
    ├── integrity_checker.py         verify_integrity 三态
    └── schemas.py                   AppendResult / WriteResult / IntegrityReport
```

**测试**（约 5500 行 · 对应 3-2 tests × 1.2 倍实际 pytest）：
```
tests/l1_09/
├── test_l2_01_event_bus.py          对齐 3-2 L2-01-tests.md · 52 test_fn · 56 TC
├── test_l2_02_lock_manager.py       · 46 test_fn · 50 TC
├── test_l2_03_audit.py              · 52 test_fn · 56 TC
├── test_l2_04_checkpoint.py         · 50 test_fn · 54 TC
├── test_l2_05_crash_safety.py       · 48 test_fn · 53 TC
├── conftest.py                      共享 fixture · mock_project_id · fake_clock · tmp_fs
├── integration/
│   ├── test_ic_09_contract.py       IC-09 契约集成（暂给 QA-1 预留）
│   └── test_tier_recovery.py        Tier 1-4 崩溃恢复端到端
└── perf/
    ├── bench_append_qps.py           事件总线 ≥ 200 QPS
    ├── bench_lock_acquire.py         无竞争 P95 ≤ 5ms
    └── bench_recovery.py             bootstrap ≤ 30s
```

### 1.5 本组 DoD 概要（详见 §8）

完工 = 以下全达标：

1. 5 L2 代码全落地 · 跑 `pytest tests/l1_09/` 全绿
2. 每 L2 对应 3-2 tests 的 TC 全覆盖 · coverage ≥ 80%
3. ruff + mypy 全绿
4. fsync/halt/hash_chain 关键路径有专项 perf + chaos 测试
5. PM-14 物理分片验证（多 pid 隔离 · 单 pid 数据完整）
6. IC-09 作为生产方 · 提供可供其他组 mock 替换的真实接口
7. IC-18 / IC-10 可单独调通
8. 每 WP 独立 commit · 消息规范（§5）
9. 所有自修正触发走 4-0 §6 协议 · 记 `_correction_log.jsonl`

---

## §2 源文档导读（必读清单 · 按优先级）

### 2.1 P0 必读（开工前必读 · 不读等于开工前基线缺失）

| 优先级 | 文档 | 关键章节 | 为何必读 | 本组怎么用 |
|:---:|:---|:---|:---|:---|
| P0-1 | `docs/1-goal/HarnessFlowGoal.md` | 全文 | 顶层目标 · PM 清单 | 对齐 PM-08 单一事实源 + PM-14 分片 + 100% 可追溯 |
| P0-2 | `docs/2-prd/L0/scope.md` | §8 整合 · §11 PM-14 · §12.9 硬红线 | 产品范围 + 集成边界 | 确认 L1-09 不越界（不做 L1-07 监督工作）|
| P0-3 | `docs/2-prd/L1-09 韧性+审计/prd.md` | 全文 | 本 L1 产品视角（5 L2 各自职责 + GWT 场景）| 定义 DoD + 负向用例 + 硬约束（每事件必 fsync 等） |
| P0-4 | `docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md` | §11 L2 分工 · §5 核心 P0 时序 · §6 按 project 分片 · §7 锁 · §8 崩溃安全 | L1 内部 L2 协作图 · 跨 L2 时序 | WP 拆解的依据（§3 本 md） |
| P0-5 | `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md` | §3 4 方法 + §5 时序 + §6 核心算法 + §11 错误码 20 条 | **最底层 · 必最先实现** | L2-05 代码（WP α-01/02/03） |
| P0-6 | `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-01-事件总线核心.md` | §3 5 方法 + §5 时序 + §6 核心算法 + §11 错误码 14 条 | 脊柱入口 | L2-01 代码（WP α-04/05/06） |
| P0-7 | `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md` | §3 6 方法（4 公共 + 2 内部）+ §11 死锁检测 | 并发基础 | L2-02 代码（WP α-07/08） |
| P0-8 | `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-03-审计记录器+追溯查询.md` | §3 5 方法 + §11 错误码 22 条 | 审计查询 | L2-03 代码（WP α-09/10） |
| P0-9 | `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-04-检查点与恢复器.md` | §3 5 方法 + §8 Tier 1-4 恢复 + §11 错误码 40 条 | 崩溃恢复脊柱 | L2-04 代码（WP α-11/12/13） |
| P0-10 | `docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-01 ~ L2-05 tests.md` | 5 份 · 共 4435 行 · 269 TC · 248 test_fn | TDD 用例源 | 复制伪代码到 `tests/l1_09/test_l2_0X_*.py` 作红灯 |
| P0-11 | `docs/3-1-Solution-Technical/integration/ic-contracts.md` | §3.9 IC-09 · §3.10 IC-10 · §3.18 IC-18 | 全局 IC 契约字段级 schema | 实现时严格对齐 payload 字段 + 错误码 |
| P0-12 | `docs/3-1-Solution-Technical/L1集成/architecture.md` | §7 失败传播（L1-09 halt 唯一入口）· §10 跨 session 恢复 | 跨 L1 视角下的 L1-09 角色 | 确认 halt 协议 + bootstrap 协议 |

### 2.2 P1 推荐（边开工边参考 · 不读会影响集成质量）

| 优先级 | 文档 | 关键章节 | 用途 |
|:---:|:---|:---|:---|
| P1-1 | `docs/2-prd/L0/projectModel.md` | 全文 | PM-14 全集 · 定义 `projects/<pid>/` 分片布局 |
| P1-2 | `docs/3-1-Solution-Technical/projectModel/tech-design.md` | §4-§8 | PM-14 技术规范 · 字段级 schema · 分片验证脚本 |
| P1-3 | `docs/3-1-Solution-Technical/integration/p0-seq.md` | 12 条 P0 时序 | 看 IC-09 / IC-18 在主干时序的位置 |
| P1-4 | `docs/3-1-Solution-Technical/integration/p1-seq.md` | 11 条 P1 异常 | Tier 恢复时序 + halt 时序 |
| P1-5 | `docs/3-1-Solution-Technical/L0/open-source-research.md` | §6 事件总线对标 · §10 audit chain 对标 | 选型依据（Kafka / etcd / Raft / PG WAL / zstd + tar）|
| P1-6 | `docs/3-3-Monitoring-Controlling/dod-specs/general-dod.md` | 待 O 完 · fallback 用 3-1 §12 | DoD 评估规约 |
| P1-7 | `docs/3-3-Monitoring-Controlling/hard-redlines.md` | 待 O 完 | 本组产出是否触发硬红线（系统级 halt）|
| P1-8 | `docs/3-3-Monitoring-Controlling/monitoring-metrics/system-metrics.md` | 待 O 完 | Prometheus 指标命名规范 |

### 2.3 P2 选读（遇到具体问题再查）

| 优先级 | 文档 | 场景 |
|:---:|:---|:---|
| P2-1 | `docs/3-1-Solution-Technical/L0/tech-stack.md` | 确认技术栈版本（Python 3.11+ · pytest · ruff · mypy） |
| P2-2 | `docs/3-1-Solution-Technical/L0/ddd-context-map.md` | 确认 BC-09 DDD 边界（本 L1 不跨 BC） |
| P2-3 | `docs/3-1-Solution-Technical/integration/cross-l1-integration.md` | 本 L1 与哪些 L1 有 IC 依赖（核对 IC mock 覆盖完整）|
| P2-4 | `docs/superpowers/reviews/2026-04-22-F-session-polish-prompt.md` | F 会话做 L1-09 3-1 文档的经验 · 参考（不是源） |
| P2-5 | `docs/superpowers/reviews/2026-04-22-J-K-session-review.md` | K 会话做 L1-09 3-2 tests 的经验 · 参考 fsync/halt 覆盖密度 |

### 2.4 读法建议（Dev-α 开工前 1-2 小时的读源计划）

**第 1 小时（P0-1 ~ P0-4）· 对齐顶层锚点**：
- Read HarnessFlowGoal.md（全文 · 约 20 分钟）
- Read scope.md §8 + §11 + §12.9（约 15 分钟）
- Read 2-prd/L1-09 prd.md（全文 · 约 20 分钟）
- Read 3-1/L1-09 architecture.md §11 + §5 + §6 + §7 + §8（约 25 分钟）

**第 2 小时（P0-5 ~ P0-9）· 5 L2 接口速览**：
- 每份 L2 tech-design Read `§3 + §11 + §12` 约 10 分钟 · 5 份 = 50 分钟
- 跳过 §1/§2/§13（与实现关联弱）

**开工后边做边读**：
- 写某 L2 时 · 深读该 L2 的 §5 时序 · §6 算法 · §7 schema · §8 状态机
- 写测试时 · 深读对应 3-2 tests.md 的伪代码

**禁区**：**不要一次读完所有 ~15800 行源文档** · 按需读 · 避免上下文爆炸 + 分心。

---

**§1+§2 完结** · 下接 §3 WP 拆解。

---

## §3 WP 拆解（天级 L3/L4 粒度）

### 3.0 WP 总表

13 WP · 5-7 天 · 按依赖顺序执行（底层先行）：

| 顺序 | WP ID | L2 | 主题 | 前置 | 估时 | 对应 3-2 TC 数 |
|:---:|:---|:---:|:---|:---|:---:|:---:|
| 1 | α-WP01 | L2-05 | atomic_write 原子写（tmp+rename+fsync）| 无 | 0.5 天 | ~15 TC |
| 2 | α-WP02 | L2-05 | append_atomic + hash chain（sha256 + JCS）| WP01 | 0.5 天 | ~20 TC |
| 3 | α-WP03 | L2-05 | verify_integrity + recover_partial_write | WP01+02 | 0.5 天 | ~18 TC |
| 4 | α-WP04 | L2-01 | EventBus.append（IC-09 入口 · halt on fsync_fail）| WP01-03 | 1 天 | ~20 TC |
| 5 | α-WP05 | L2-01 | register_subscriber + read_range | WP04 | 0.5 天 | ~18 TC |
| 6 | α-WP06 | L2-01 | halt_guard + correlation_id 链路 | WP04 | 0.5 天 | ~18 TC |
| 7 | α-WP07 | L2-02 | acquire/release/is_locked（flock + FIFO）| 无（独立）| 0.75 天 | ~30 TC |
| 8 | α-WP08 | L2-02 | 死锁检测 + janitor 泄漏回收 + force_release_all | WP07 | 0.5 天 | ~20 TC |
| 9 | α-WP09 | L2-03 | query_audit_trail（IC-18）+ Anchor 三态 | WP04 | 0.5 天 | ~28 TC |
| 10 | α-WP10 | L2-03 | rotation + gate（rebuilding/open/closed）| WP09 | 0.5 天 | ~28 TC |
| 11 | α-WP11 | L2-04 | take_snapshot（周期 + 关键事件触发）| WP04+07 | 0.75 天 | ~18 TC |
| 12 | α-WP12 | L2-04 | recover_from_checkpoint · Tier 1-4 | WP11 | 1 天 | ~20 TC |
| 13 | α-WP13 | L2-04 | begin_shutdown（drain + final snapshot）+ replay_events | WP11+12 | 0.5 天 | ~16 TC |

**关键路径**（若延期最致命）：WP01→WP02→WP03→WP04（L2-05 基础 + L2-01 入口 · 4 个 WP · 2.5 天）· 这 4 WP 若延 · 全组后续 WP 都 block。

### 3.1 WP-α-01 · L2-05 崩溃安全层 · atomic_write 原子写

**源文档锚点**：
- 3-1 `L2-05-崩溃安全层.md §3.2 方法 1 write_atomic`
- 3-1 `L2-05 §6 核心算法（write_atomic 5 步 syscall 序）`
- 3-1 `L2-05 §11 错误码（`E_WRITE_TMP_FAIL` / `E_WRITE_FSYNC_FAIL` / `E_WRITE_RENAME_FAIL`）
- 3-2 `L2-05-崩溃安全层-tests.md §2 正向`（原子写正常路径）

**工作内容（L3）**：

- 实现 `AtomicWriter` 类 · 单入口 `write_atomic(path, bytes_data)` → `WriteResult`
- 5 步 syscall 序：
  1. 打开 tmp 文件（`O_CREAT | O_WRONLY | O_EXCL`）· tmp 命名 `<path>.tmp.<pid>.<uuid>`
  2. 全量写（处理部分写 · 分块循环至完整）
  3. `fsync(tmp_fd)`（关键 · 失败即 raise · 无重试）
  4. `close(tmp_fd)`
  5. `os.rename(tmp, path)`（POSIX 原子）
  6. （可选）`fsync` 父目录（Linux durability · config 开关）
- 错误分类与错误码映射：
  - `ENOSPC` → `E_WRITE_TMP_FAIL` · 含 `disk_avail_bytes`
  - `EIO` / fsync fail → `E_WRITE_FSYNC_FAIL` · 触发上层 halt
  - rename 失败 → `E_WRITE_RENAME_FAIL` + 清理 tmp
- 确保所有异常路径清理 tmp（try/finally）

**代码文件（L4）**：

```
app/l1_09/crash_safety/atomic_writer.py              # 主实现 ~180 行
app/l1_09/crash_safety/schemas.py                    # WriteResult / CrashSafetyDiskFullError / CrashSafetyFSyncError ~60 行
app/l1_09/crash_safety/__init__.py                   # 导出 ~10 行
```

**TDD 流程**：

1. Read `docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-05-崩溃安全层-tests.md` · 摘 §2 正向 5 个 + §3 负向 10 个 TC 伪代码
2. 写 `tests/l1_09/test_l2_05_atomic_write.py`（~15 test_fn · 对齐 TC-CRASH-WRITE-*）
3. `pytest tests/l1_09/test_l2_05_atomic_write.py` → **全红**（期望 15 fail）
4. 实现 `atomic_writer.py` · 分段：
   - 先 `_open_tmp()` + `_write_all()` + `_fsync_fd()` 三私函数
   - 再组合成 `write_atomic()` 主方法
5. `pytest` → 逐个转绿（期望 15/15）
6. 检查 coverage ≥ 85%
7. Refactor：提炼 `_tmp_name()` 工具函数 · 保持测试绿
8. `ruff check && mypy app/l1_09/crash_safety/`
9. `git add + git commit -m "feat(harnessFlow-code): α-WP01 L2-05 atomic_write 原子写"`

**DoD（WP 完工判据）**：

- [ ] `tests/l1_09/test_l2_05_atomic_write.py` 15/15 全绿
- [ ] coverage ≥ 85%
- [ ] 3 错误码全覆盖（`E_WRITE_TMP_FAIL` / `E_WRITE_FSYNC_FAIL` / `E_WRITE_RENAME_FAIL` 各 ≥ 1 负向 TC）
- [ ] mock disk full（`errno=ENOSPC`）可触发正确错误码 + 清理 tmp
- [ ] `ruff + mypy` 绿
- [ ] commit SHA 记录
- [ ] **硬断言**：fsync 失败不得吞异常（必 raise · 让上层 halt）

### 3.2 WP-α-02 · L2-05 崩溃安全层 · append_atomic + hash chain

**源文档锚点**：
- 3-1 `L2-05 §3.3 方法 2 append_atomic`
- 3-1 `L2-05 §6.2 append 模式 + PIPE_BUF 硬约束`
- 3-1 `L2-05 §6.3 hash 链算法（JCS + sha256 + GENESIS）`
- 3-1 `L2-05 §7.5 HashChainLink schema`
- 3-2 tests §2 正向 5 个 + §3 负向 8 个 + §4 hash chain 完整性测试

**工作内容（L3）**：

- 实现 `Appender.append_atomic(path, line_bytes) -> AppendResult`
  - `O_APPEND | O_WRONLY`（append 原子保证 · POSIX · size < PIPE_BUF = 4096 bytes 下写入不会交错）
  - 硬断言 `len(line_bytes) < PIPE_BUF`（超则 raise `E_LINE_TOO_LARGE`）
  - 写后 `fsync` · 失败即 halt
  - 无 tmp 文件（append 语义不需要）
- 实现 `HashChain.compute_next(prev_hash, payload_dict) -> HashChainLink`
  - JCS (JSON Canonicalization Scheme · RFC 8785) canonicalize payload
  - `sha256(prev_hash + canonical_json)` → 64 char hex
  - GENESIS 特例：prev_hash = `"0" * 64`
  - 返回 `HashChainLink(seq, prev_hash, hash, timestamp, canonical_payload)`
- 每 append 前必先 compute_next（上层 L2-01 保证 · 本 WP 提供工具）

**代码文件（L4）**：

```
app/l1_09/crash_safety/appender.py          # append_atomic ~120 行
app/l1_09/crash_safety/hash_chain.py        # compute_next + verify_link ~150 行
app/l1_09/crash_safety/canonical_json.py    # JCS 规范化 ~80 行（可复用 rfc8785 库 · pip install rfc8785）
```

**TDD 流程**（同 WP01）：
- tests/l1_09/test_l2_05_append_atomic.py · ~20 test_fn
- hash chain 测试重点：
  - GENESIS 创世块生成（prev="0"*64）
  - 连续 3 链：每链的 prev = 上链的 hash
  - 篡改 N-1 条 payload · 第 N 条验证失败
  - JCS 规范化边界（unicode · 浮点 · 空对象）

**DoD**：
- [ ] ~20 TC 全绿
- [ ] PIPE_BUF 硬限断言（line > 4096 时必 raise · 不截断）
- [ ] hash chain 篡改检测 100%（mutation testing 验证）
- [ ] JCS canonical 符合 RFC 8785（至少 5 个 edge case 覆盖）
- [ ] coverage ≥ 85%

### 3.3 WP-α-03 · L2-05 崩溃安全层 · verify_integrity + recover_partial_write

**源文档锚点**：
- 3-1 `L2-05 §3.4 方法 3 verify_integrity`
- 3-1 `L2-05 §3.5 方法 4 recover_partial_write`
- 3-1 `L2-05 §6.4 verify 3 态（OK / PARTIAL / CORRUPT）`
- 3-1 `L2-05 §7.4 IntegrityReport schema`

**工作内容（L3）**：

- 实现 `IntegrityChecker.verify_integrity(path) -> IntegrityReport`
  - 按行扫 jsonl · 每行 parse + 检查 hash chain
  - 3 态分类：
    - `OK`：全链完整
    - `PARTIAL`：末尾 1 条损坏（可能 crash 中途）· 可截断恢复
    - `CORRUPT`：中段损坏（hash 断裂）· 不可恢复 · 返回 `failure_range`
- 实现 `recover_partial_write(path) -> RecoveryResult`
  - 仅 `PARTIAL` 状态下调用
  - 截断至最后完整的 N-1 条 · 保留 `path.corrupt.<ts>` 备份
  - 返回 `RecoveryResult(recovered_count, truncated_bytes)`

**代码文件（L4）**：

```
app/l1_09/crash_safety/integrity_checker.py   # verify + recover ~200 行
```

**DoD**：
- [ ] verify 3 态测试全绿（~18 TC · §6 正向 + 每态边界）
- [ ] CORRUPT 情况下 `failure_range` 精确到 byte offset
- [ ] PARTIAL recover 后 · 再 verify 必返 `OK`
- [ ] coverage ≥ 85%

**3 个 WP 小结（L2-05 完工）**：崩溃安全层 3 WP 约 1.5 天 · ~3700 行代码 · 53 TC · 提供 L2-01 所需的底层 atomic write + append + hash chain + verify 工具 · **其他 L2 开发可启动**。

### 3.4 WP-α-04 · L2-01 事件总线核心 · EventBus.append（IC-09 入口）

**源文档锚点**：
- 3-1 `L2-01-事件总线核心.md §3.2 append(event) — IC-09 唯一写入口`
- 3-1 `L2-01 §5.1 P0 时序`（append 主路径 · 14 步骤）
- 3-1 `L2-01 §6 核心算法（event_id 生成 + payload 校验 + hash chain + fsync + emit 到订阅者）`
- 3-1 `L2-01 §11 错误码 14 条`
- 3-2 `L2-01-事件总线核心-tests.md` 完整 56 TC

**工作内容（L3）**：

- 实现 `EventBus.append(event: Event) -> AppendEventResult`
  - Step 1 · 入参校验：PM-14 `project_id` 根字段必存（或 `project_scope="system"`）
  - Step 2 · event schema 校验（pydantic）· 失败返 `E_EVT_SCHEMA_INVALID`
  - Step 3 · 幂等检查：同 `event_id` 已存在 · 返回原记录（PM-08 幂等）
  - Step 4 · 生成 seq（project 内单调递增 · 从 meta 读）
  - Step 5 · 读前一 hash · compute_next（调 WP02 HashChain）
  - Step 6 · 组装 jsonl line（含 event + hash_link）
  - Step 7 · 调 WP02 `append_atomic(path, line)`
  - Step 8 · 成功后更新 meta seq / last_hash
  - Step 9 · 异步 emit 到订阅者（不阻塞主路径）
  - Step 10 · 返回 `AppendEventResult(event_id, seq, hash, ts)`
- **硬约束 · halt on fsync_fail**：Step 7 抛 `CrashSafetyFSyncError` → 本层 catch · 标系统级 halt · 写 `_halt.marker` · 拒绝所有后续 append · raise `E_BUS_SYSTEM_HALTED`

**代码文件（L4）**：

```
app/l1_09/event_bus/core.py                   # EventBus 主类 ~250 行
app/l1_09/event_bus/emitter.py                # append 出口 API ~80 行
app/l1_09/event_bus/schemas.py                # Event / AppendEventResult / EventBusError ~150 行
app/l1_09/event_bus/halt_guard.py             # halt 守护（_halt.marker · reject 新请求）~80 行
app/l1_09/event_bus/meta.py                   # project meta（seq + last_hash 持久化）~120 行
```

**特别关注**：
- **幂等性**：同 `event_id` 第二次 append 必返回第一次的结果（含原 seq · 原 hash）· 不重复落盘
- **PM-14 root field**：所有 event.payload 必含 project_id（除 system 级）· schema 强制
- **订阅者 emit 异步**：subscriber.call 失败不得影响 append 成功
- **meta 持久化**：meta 也要 `write_atomic`（复用 WP01）
- **halt 持久化**：`_halt.marker` 跨进程可读 · 重启后仍 halt · 只有运维手工清除才解锁

**DoD**：
- [ ] ~20 TC 全绿（对齐 3-2 L2-01 §2+§3）
- [ ] fsync_fail 触发 halt 测试（mock fsync 抛 EIO · 验证 halt 行为）
- [ ] 同 event_id 幂等测试（第二次 append 不落盘 · 返回原结果）
- [ ] PM-14 违规（缺 project_id）· 返 `E_EVT_NO_PROJECT_OR_SYSTEM`
- [ ] 并发 append 10 × 100 次 · seq 严格单调 · hash chain 不破
- [ ] coverage ≥ 85%
- [ ] **硬断言**：fsync 失败 halt 后 · 任何后续 append 必 raise（不得成功）

### 3.5 WP-α-05 · L2-01 事件总线核心 · register_subscriber + read_range

**源文档锚点**：
- 3-1 `L2-01 §3.3 register_subscriber · §3.4 read_range`
- 3-1 `L2-01 §6.3 订阅者模型 + §6.4 read_range iterator`

**工作内容（L3）**：

- 实现 `register_subscriber(sub: Subscriber) -> SubscriberHandle`
  - 注册时记录：filter（event_type/scope/project_id）+ call_site（async callback）
  - 订阅者按 project 隔离：global 订阅者（订阅所有 project）vs project-scoped
  - 启动时 replay 机制：可选 `replay_from_seq=0` · append 新事件前先重放历史
- 实现 `read_range(pid, from_seq, to_seq) -> Iterator[Event]`
  - IC-L2-04 · 为 L2-04 checkpoint 提供只读扫描
  - 按 project 分片读 · 支持 seq range
  - 惰性 iterator（大 project 不一次性加载内存）

**代码文件（L4）**：

```
app/l1_09/event_bus/subscriber.py             # 订阅者注册 + dispatch ~180 行
app/l1_09/event_bus/reader.py                 # read_range iterator ~120 行
```

**DoD**：
- [ ] ~18 TC 全绿
- [ ] 订阅者 filter 准确（跨 project 无串话）
- [ ] read_range 对 10 万 event 不 OOM（内存 < 50MB · 验证）
- [ ] replay 后新 append 可正常订阅到
- [ ] coverage ≥ 85%

### 3.6 WP-α-06 · L2-01 事件总线核心 · halt_guard + correlation_id

**源文档锚点**：
- 3-1 `L2-01 §3.5 共享元字段 · correlation_id / trace_id`
- 3-1 `L2-01 §8 状态机（NORMAL / HALTED / ...）`

**工作内容（L3）**：

- 实现 `HaltGuard`（独立类 · 被 EventBus 持有）
  - `_halt.marker` 文件位置：`projects/_global/halt.marker`（全系统共享）
  - 启动时读 marker · 若存在 · EventBus 直接进 HALTED 状态
  - `mark_halt(reason)` · 写 marker + 记 `_halt_log.jsonl`
  - `clear_halt()` · 仅 CLI 工具可调 · 运维手动解锁
- correlation_id / trace_id / span_id 自动注入：
  - 每 `append` 请求：若 event 无 correlation_id · 复用当前 task context 的 id（contextvars）
  - trace_id 链路：上游传入 · 本层透传
- halt 期间的错误消息清晰：返回 `E_BUS_SYSTEM_HALTED` + `halt_reason` + `halt_at`

**代码文件（L4）**：

```
app/l1_09/event_bus/halt_guard.py             # HaltGuard（在 WP04 已建基础上完善）
app/l1_09/event_bus/context.py                # correlation_id / trace_id contextvars ~60 行
```

**DoD**：
- [ ] ~18 TC 全绿
- [ ] halt 持久化：halt 后重启进程 · 仍 HALTED
- [ ] clear_halt 需 `admin_token` 认证（CLI 工具 · 不对代码暴露）
- [ ] correlation_id 跨 append 传递测试（同一请求链所有 event 共 correlation_id）
- [ ] coverage ≥ 85%

**L2-05 + L2-01 共 6 WP 小结（第 1 阶段收尾）**：
- **总 WP**：6（α-WP01 ~ α-WP06）· 4 天 · ~7400 行代码 · ~109 TC
- **里程碑 · Dev-α-M1**：IC-09 入口可用 · 其他组开始可通过 mock → 真实替换
- **外部可见**：`from app.l1_09 import EventBus` 可 import · `event_bus.append(event)` 可调

---

**§3（L2-05 + L2-01）完结 · 批 2 结束** · 下批写 §3（L2-02 + L2-03 + L2-04）+ §4 依赖图。
