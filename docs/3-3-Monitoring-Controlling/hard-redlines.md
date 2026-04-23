---
doc_id: monitor-control-hard-redlines-v1.0
doc_type: monitoring-controlling-spec
layer: 3-3-Monitoring-Controlling
parent_doc:
  - docs/2-prd/L0/scope.md（范围 · 硬红线 / 软漂移 / DoD 定义源）
  - docs/2-prd/HarnessFlowGoal.md
  - docs/3-1-Solution-Technical/L1集成/architecture.md §7 失败传播 · §8 性能
  - docs/3-1-Solution-Technical/integration/ic-contracts.md（IC-09/13/14/15 与红线/建议/审计）
version: v1.0
status: skeleton
author: main-session-r6-init
created_at: 2026-04-23
updated_at: 2026-04-23
---

# 硬红线规约（5 类 · 不可失真）

> **本文档定位**：3-3 Monitoring & Controlling 层 · 5 类硬红线清单 · 触发条件 · 响应 SLO ≤100ms · 拦截机制 · 用户文字授权唯一放行
> **与 3-1/3-2 的分工**：3-1 定义"系统如何实现" · 3-2 定义"如何测" · **3-3 定义"如何监督与判通过"**（质量 Gate 规约 · 硬红线清单 · DoD 契约 · 验收标准）
> **消费方**：L1-04 质量环（读 DoD 编译 Gate）· L1-07 监督（读红线/软漂移清单触发）· 交付验收（读 acceptance-criteria）

---

## §0 撰写进度

- [ ] §1 定位 + 与上游 PRD/scope 的映射
- [ ] §2 核心清单 / 规约内容
- [ ] §3 触发与响应机制
- [ ] §4 与 L1-04 / L1-07 / L1-09 的契约对接
- [ ] §5 证据要求 + 审计 schema
- [ ] §6 与 2-prd 的反向追溯表

---

## §1 定位 + 映射

<!-- FILL §1 · 引 docs/2-prd/L0/scope.md 对应小节（红线/软漂移/DoD 均在 scope §8-§10）· 引 HarnessFlowGoal.md 对应原则 · 在 3-3 层的确切位置 -->

## §2 核心清单 / 规约内容

<!-- FILL §2 · 本文档的主体内容（如硬红线 5 类清单 · DoD 表达式语法 · 指标项清单 · 验收标准矩阵）-->

## §3 触发与响应机制

<!-- FILL §3 · 何时生效（启动/运行时/Gate 前）· 响应 SLO · 响应链路 · 降级策略 -->

## §4 与 L1-04/L1-07/L1-09 的契约对接

<!-- FILL §4 · 本规约如何被 L1-04 质量 Gate 编译器消费 · 如何被 L1-07 监督订阅 · 如何经 IC-09 审计 -->

## §5 证据要求 + 审计 schema

<!-- FILL §5 · 规约成立必提供的证据（字段级 YAML）· 审计事件 schema(IC-09) -->

## §6 与 2-prd 的反向追溯表

<!-- FILL §6 · 本文档每条规约反向追溯到 docs/2-prd/L0/scope.md §X.Y 或 docs/2-prd/L1-NN/prd.md §X.Y -->

---

*— 3-3 硬红线规约（5 类 · 不可失真） · skeleton · v1.0 · 2026-04-23 · 等待填充 —*
