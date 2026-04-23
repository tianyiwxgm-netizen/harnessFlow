---
doc_id: exe-test-plan-5-4-failure-injection-v1.0
doc_type: test-execution-plan
layer: 5-exe-test-plan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/3-1-Solution-Technical/L1集成/architecture.md §9 失败传播模型
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md（本 L1 失败专项）
  - docs/3-3-Solution-Monitoring&Controlling/hard-redlines/（5 硬红线触发）
version: v1.0
status: draft
assignee: **QA-4 · 独立会话**
wave: 6（与 QA-1/2/3 并行）
priority: P1（韧性验证 · 但不阻塞 release）
estimated_duration: 2-3 天
---

# QA-4 · 失败注入测试 Test Run Execution Plan

> **本 md 定位**：**独立会话** · 读本 md 即知如何做失败注入（chaos engineering 轻量版）· 验证 harnessFlow 韧性。
>
> **本组做什么**：
> 1. 10 L1 各自注入失败 · 验证 PM-14 隔离（foo 失败不影响 bar）
> 2. 系统级失败注入（唯独 L1-09 可触 halt）· 验证 halt 路径
> 3. fsync / 磁盘满 / OOM / 网络中断 · 韧性专项
> 4. 20 IC 消费方异常 · 生产方应如何（IC 契约 §4.3 失败处理）
> 5. 产韧性报告
>
> **本组不做**：
> - ❌ 不做混沌工程全套（V2+ 延后）
> - ❌ 不做 DDoS / 安全攻击（超出 scope）
> - ❌ 不 fix bug

---

## §1 5 类失败注入清单

### 1.1 L1 自身失败（10 L1 × 1 用例 · PM-14 隔离专项）

| L1 | 注入方式 | 期望 |
|:---:|:---|:---|
| L1-01 | tick 卡住（模拟死锁）| L1-07 SDP 发现 · IC-15 halt |
| L1-02 | 创建 pid 时漏 pid | HRL-01 halt |
| L1-03 | WBS 拆解返空 | L1-01 捕获 · rework |
| L1-04 | DoD 编译抛异常 | L1-01 catch · WP failed |
| L1-05 | Skill 调用超时 | IC-04 timeout · fallback |
| L1-06 | KB read I/O error | IC-06 降级无 KB · 继续 |
| L1-07 | Supervisor 订阅断 | L1-09 警告 · 但不 halt |
| L1-08 | VLM 返 error | L1-05 catch · skip |
| L1-09 | fsync 失败 | **halt**（PM-08 触底）|
| L1-10 | UI 连接断 | L1-10 本地缓冲 · 不影响其他 L1 |

**PM-14 隔离验证**：注入 L1-X 失败时 · 其他 pid 的 L1-X 应正常（本 L1 不通过 root pid 串用）。

### 1.2 系统级失败（5 用例）

| ID | 场景 | 期望 |
|:---:|:---|:---|
| SYS-01 | kill -9 harnessFlow 进程 | 重启后 Tier 1 恢复 |
| SYS-02 | /tmp 磁盘满 | event_bus 写失败 · halt |
| SYS-03 | OOM（模拟 RAM 满）| 进程退出 · 重启 |
| SYS-04 | network down（L1-05 外部 API）| skill fallback · 降级 |
| SYS-05 | 文件系统 readonly | halt |

### 1.3 IC 消费方失败（20 IC × 1 · 共 20）

每 IC：生产方发送 · 消费方返错 / 超时 / 抛异常 → 生产方应按 IC §4.3 失败处理。

### 1.4 跨 L1 级联失败（5 用例）

| ID | 场景 | 期望 |
|:---:|:---|:---|
| CAS-01 | L1-09 死 → 全 L1 halt | 正确（PM-08 唯一事实）|
| CAS-02 | L1-02 死 → pid 创建停 | L1-01 暂停新 project · 老继续 |
| CAS-03 | L1-04 死 → Gate 裁决停 | WP queue 堆积 · 不 halt |
| CAS-04 | L1-07 死 → 监督缺位 | 降级无监督 · 但不 halt |
| CAS-05 | L1-10 死 → UI 断 | 用户不可见但系统继续 |

### 1.5 审计链破坏（2 用例）

| ID | 场景 | 期望 |
|:---:|:---|:---|
| AUD-01 | 手动改 events.jsonl 中间行 | **HRL-02 halt** |
| AUD-02 | 删除一个 checkpoint 文件 | Tier 2 fallback + 告警 |

**合计 ~42 用例 · 2-3 天跑完**

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | architecture.md §9 失败传播 |
| P0 | L1-09 architecture.md §6-§8（韧性 tier）|
| P0 | hard-redlines/ 5 条（触发点）|
| P1 | ic-contracts.md §4.3 每 IC 的失败处理 |

---

## §3 WP 拆解（4 WP · 2.5 天）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| QA4-WP01 | 注入工具 + 环境 | main-3 ready + Dev/主-1/2 ready | 0.5 天 |
| QA4-WP02 | L1 自身失败 10 用例 + PM-14 隔离 | WP01 | 1 天 |
| QA4-WP03 | 系统级 + IC 消费方 + 跨 L1 级联（5+20+5 = 30）| WP01 | 0.75 天 |
| QA4-WP04 | 审计链破坏 + 报告 | 全 WP | 0.25 天 |

### 关键 WP 细节

**QA4-WP01 工具**：
- 用 `pytest-mock` + `monkeypatch` 注入
- 系统级：`subprocess` kill / `resource` limits / chaos-python（可选）
- 审计链：直接写脏数据到 events.jsonl

**QA4-WP02 L1 自身 + PM-14 隔离**：
- 每用例：建 2 pid（A/B）· 注入 A 失败 · 验证 B 正常
- 写报告：`failure_l1_01.md` ~ `failure_l1_10.md`

**QA4-WP03 系统级 + IC**：
- 系统级 5 用例（重点 SYS-01 pid 进程重启）
- IC 消费方：pytest-mock 让消费方 raise · 看生产方是否按 IC §4.3 处理

**QA4-WP04 审计链**：
- 硬红线 HRL-02 触发 · 验证 100% halt
- 报告 `reports/QA4-resilience-matrix.yaml`

---

## §4 依赖图

```
main-3 + Dev/主-1/2 ready
  ↓
QA4-WP01 工具
  ↓
QA4-WP02 ──┬── QA4-WP03（并行）
           ↓
QA4-WP04 → main-4 消费
```

---

## §5-§10

- §5 standup · prefix `QA4-WPNN`
- §6 自修正：若失败处理与 IC §4.3 不符 · 走 §6 情形 D（IC 契约矛盾）· 回锤 ic-contracts.md
- §7 无对外契约
- §8 DoD：
  - 42 用例全跑
  - PM-14 隔离 100% 验证
  - 5 硬红线 100% 触发正确
  - Tier 1-4 恢复全验证
- §9 风险：
  - R-QA4-01 失败注入路径遗漏 · V2+ 补
  - R-QA4-02 系统级失败难在 CI 稳定 · 局部跑
- §10 交付：`reports/QA4-resilience-matrix.yaml` + ~42 用例子报告

---

*— QA-4 · 失败注入测试 Test Run · Execution Plan · v1.0 —*
