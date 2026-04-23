---
doc_id: exe-plan-main-4-final-integration-v1.0
doc_type: final-integration-execution-plan
layer: 4-exe-plan（根级 · 集成顶层）
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α ~ Dev-θ + main-1 + main-2 + main-3（全 11 份子 exe-plan）
  - docs/4-exe-plan/4-3-exe-monitoring&controlling/4-3-monitoring-impl-plan.md
  - docs/5-exe-test-plan/5-1 ~ 5-5（测试）
  - docs/6-finalQualityAcceptance/6-1 ~ 6-4（签收）
  - docs/3-1-Solution-Technical/L1集成/architecture.md
  - docs/3-3-Monitoring-Controlling/acceptance-criteria.md
version: v1.0
status: draft
assignee: **主会话（不分派 · 顶层协调）**
wave: 6-7
priority: P0（最终交付）
---

# main-4 · 最终集成 + 交付 Execution Plan（主会话集成顶层）

> **本 md 定位**：**所有其他 exe-plan 会话（11 Dev 组 + 主-1 + 主-2 + 主-3 + QA + Sign）执行完成后** · **主会话根据本 md 完成最终集成 + 集成测试 + 交付**。
>
> **本组与 main-3 的区别**：
> - main-3 · 写**集成层代码 + tests**（integration/ + acceptance/ 测试用例落地）
> - **main-4 · 做最终 e2e 集成 + 跨层验收 + bug fix loop + 交付打包 + release**（本 md）
>
> **前置（必须全绿）**：
> - ✅ 所有 4-1 Dev-α ~ Dev-θ 交付（11 L1 · 57 L2 代码 + TDD 全绿）
> - ✅ main-1 L1-04 Quality Loop 交付
> - ✅ main-2 L1-01 主循环 交付
> - ✅ main-3 集成测试 + acceptance 落地
> - ✅ 4-3 监督落地
> - ✅ QA-1/2/3/4/5 五测试组全绿
>
> **产出**：可交付的 harnessFlow v1.0 · tar.zst 交付包 · release notes · 签收。

---

## §0 撰写进度

- [x] §1-§10 全齐

---

## §1 组定位

### 本组做什么

1. **全系统端到端集成**（5-7 天）：把 11 Dev 组产出的所有 L1 代码 + main-1/2 + main-3 整成一个**可完整运行的 harnessFlow**
2. **跨层 bug fix loop**（3-5 天）：QA-1/2/3/4/5 发现的问题 · 本组主会话负责 fix
3. **最终集成验收**（2-3 天）：scenario-02 S1→S7 真实场景（非 mock）· 性能 SLO 真实达标验证
4. **交付打包**（1 天）：调 Sign-1 写的脚本打 tar.zst + manifest
5. **release**（1 天）：调 Sign-2 写的 release 流程 · 发公告

**合计**：12-17 天墙钟 · 主会话连续投入。

### 本组不做

- ❌ 不新增 feature（在各组 exe-plan 已完成）
- ❌ 不独立写测试（在 main-3 已完成）
- ❌ 不改源文档（若需改 · 走 4-0 §6 自修正）
- ❌ V2+ 功能（延后）

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | 所有 4-exe-plan 子 md（11 份）· 了解每组交付物 |
| P0 | `3-1/L1集成/architecture.md` §12 M1-M6 里程碑 |
| P0 | `3-3/acceptance-criteria.md`（O 产出 · 最终验收标准）|
| P0 | `5-exe-test-plan/*` 5 份测试报告 |
| P0 | `6-finalQualityAcceptance/6-1 ~ 6-4`（签收模板）|

---

## §3 WP 拆解（8 WP · 12-17 天）

### 3.0 总表

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| M4-WP01 | 全系统启动验证（bootstrap · all L1 alive）| 11 Dev + 主-1/2/3 + QA 全绿 | 1 天 |
| M4-WP02 | IC 契约真实集成（替换最后的 mock）| WP01 | 1-2 天 |
| M4-WP03 | S1→S7 真实 e2e（mock LLM · 真实流程）· scenario-02 跑通 | WP02 | 2 天 |
| M4-WP04 | 跨 session 恢复真实 e2e（kill -9 + 重启 · Tier 1-4）· scenario-08 | WP03 | 1-2 天 |
| M4-WP05 | 性能 SLO 真实达标（调优）| WP03 + QA-3 报告 | 2-3 天 |
| M4-WP06 | bug fix loop（QA-1/2/3/4/5 发现的全部 P0/P1 问题）| QA 全完 | 3-5 天 |
| M4-WP07 | 交付包打包（tar.zst + manifest + sha256）| WP06 全清 | 1 天 |
| M4-WP08 | release · 签收 · 发公告 | WP07 + 6-1/2/3 | 1 天 |

### 3.1 M4-WP01 · 全系统启动验证

**L3**：
- 启动 harnessFlow 进程（`python -m harnessflow.main` 假设入口）
- 验证 10 L1 + L1 集成 全部 alive：
  - L1-09 事件总线 listening
  - L1-06 KB 三层可读
  - L1-07 supervisor 订阅 IC-09
  - L1-02 S1 可创建 pid
  - L1-10 UI 可访问（`npm run dev` + `uvicorn bff:main`）
  - ...
- 跑 `pytest tests/smoke/` · 冒烟测试全绿

**DoD**：启动 ≤ 10s · 10 L1 全 alive · smoke tests 全绿

### 3.2 M4-WP02 · IC 契约真实集成

**L3**：
- 清掉所有 mock_*（从 conftest.py 删）
- 全链走真实 IC · 再跑 integration 24 + acceptance 12
- 修复集成期发现的模糊契约（走 §6 情形 D）
- integration_gate.sh 绿

**DoD**：tests/integration + tests/acceptance 全绿 · 0 mock

### 3.3 M4-WP03 · S1→S7 真实 e2e

**L3**：
- 用真实 mock LLM（豆包 mock · 返固定 response）· 但流程真实
- 输入：用户一句话 "做一个 TODO App"
- 跑：S1 kickoff → S2 Planning → S3 TDD Gate → S4 Executing × N WP → S5 Integration → S6 Closing → S7 Archive
- 期望：pid 创建 → 激活 → 4 件套产出 → PMP/TOGAF 产出 → WBS 拆解 → WP 执行 → quality loop → verifier → 归档 tar.zst
- 全链耗时预估 20-60 分钟（mock LLM 加速）
- 审计链完整 100%

**DoD**：scenario-02 真实跑通 · state=ARCHIVED · 审计可追溯 100%

### 3.4 M4-WP04 · 跨 session 恢复真实 e2e

**L3**：
- 启动 harnessFlow · 创建 2 pid · S3 期间
- `kill -9` 进程
- 重启
- 验证 Tier 1 恢复（latest checkpoint）· 状态与 kill 前一致
- 破坏 checkpoint · 验证 Tier 2 fallback
- 破坏 events.jsonl · 验证 Tier 3 跳跃
- 全坏 · 验证 Tier 4 拒绝假恢复

**DoD**：scenario-08 Tier 1-4 全绿

### 3.5 M4-WP05 · 性能 SLO 真实达标

**L3**：
- 跑 QA-3 performance-test-run 的 7 SLO benchmark
- 不达标项 · 优化热路径：
  - L1-09 fsync 如瓶颈 · 批量 fsync
  - L1-06 KB read 如 > 500ms · 加 cache
  - L1-01 tick drift 如 > 100ms · 优化 loop 算法
- 迭代直到 7/7 SLO 绿

**DoD**：7 SLO 100% 达标 · 有 benchmark 报告

### 3.6 M4-WP06 · bug fix loop

**L3**：
- 主会话接 QA-1/2/3/4/5 bug report
- 分级：
  - P0 · 阻塞发布（halt / 数据丢失 / PM-14 违规）· 必修
  - P1 · 严重（SLO 不达 · UI 关键 bug）· 必修
  - P2 · 次要（UI 小 bug · warning）· 可延
- 修完 · 回归 · 再 QA

**DoD**：所有 P0 + P1 clear · P2 < 10 个

### 3.7 M4-WP07 · 交付包打包

**L3**：
- 调 Sign-1 `6-1-delivery-checklist.md` 的打包脚本
- 产出 `releases/harnessflow-v1.0.tar.zst`
- 含：代码 + 测试 + 文档 + 示例 project · 排除 secrets · .git · node_modules · __pycache__
- 计算 sha256 + 写 manifest.json
- 验证可 `tar -xf` 解压 + `pip install -e .` + `pytest` 绿

**DoD**：tar.zst + sha256 + manifest · 解压可跑

### 3.8 M4-WP08 · release + 签收

**L3**：
- 按 Sign-2 `6-2-release-process.md`：
  - git tag `v1.0.0` + push
  - GitHub release · 上传 tar.zst + manifest
  - 发 release notes（Sign-4 产出）
- 按 Sign-3 `6-3-signoff-templates.md`：
  - 签收清单勾全（5 维度验收 · 全绿）
  - 权责人签字
  - 存档 `releases/signoff-v1.0.yaml`

**DoD**：v1.0.0 发布 · 签收完成 · 所有验收 checklist 绿

---

## §4 依赖图

```
全 Dev/主-1/2/3/QA 全绿
  ↓
M4-WP01 启动验证
  ↓
M4-WP02 IC 真实集成
  ↓
M4-WP03 S1→S7 真实 e2e
M4-WP04 跨 session 恢复
M4-WP05 性能 SLO 达标
  ↓（并行）
M4-WP06 bug fix loop
  ↓
M4-WP07 交付包打包
  ↓
M4-WP08 release + 签收 → 交付完成 🎉
```

---

## §5-§10 简版

- §5 standup · prefix `M4-WPNN` · 主会话每天 report 进度
- §6 自修正：最后兜底期 · 发现源文档错仍走 4-0 §6（但要谨慎 · 接近发布）
- §7 无对外契约（本组是集成顶层）
- §8 最终 DoD：
  - 所有前置组 DoD 绿
  - 7 SLO 100% 达标
  - scenario-02 + scenario-08 真实跑通
  - 0 P0/P1 bug · P2 < 10
  - tar.zst + sha256 + 签收齐
- §9 风险：
  - R-M4-01 QA 发现大量 P0（集成期难免）· 主会话全力 fix
  - R-M4-02 性能 SLO 个别不达 · 走 §6 改 3-1 §12 SLO（降预期 · 但需 justification）
  - R-M4-03 scenario-02 全链超时 · 优化热路径或降 mock LLM 参数
- §10 交付：release v1.0.0 · 签收 · 结束 harnessFlow M0→M8 全程

---

## 附录 · 交付里程碑 (M1-M8 完整路径)

```
M0 · 项目启动（scope 冻结）             已完成 ✅
M1 · 20 IC 契约锁定                    已完成 ✅
M2 · L1-01 主循环原型                  已完成 ✅（tech-design）
M3 · L1-04/07 质量环+监督              已完成 ✅（tech-design）
M4 · 57 L2 全 depth-B+                 已完成 ✅（M4 达成）
M5 · 3-2 TDD 全覆盖                    已完成 ✅（57/57）
M6 · 3-3 Monitoring 规约               🟡 O 会话中
M7 · 代码开发完成（4-exe-plan 全绿）    ← 本 main-4 前置
M8 · 交付 · release v1.0.0             ← 本 main-4 产出 🎯
```

---

*— main-4 · 最终集成 + 交付 · Execution Plan · v1.0 · 主会话终末集成 —*
