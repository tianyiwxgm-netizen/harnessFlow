---
doc_id: spec-3-solution-design-v1.0
doc_type: design-spec
created_at: 2026-04-20
brainstorming_skill_version: superpowers 5.0.7
approved_by: user
status: approved_for_implementation
---

# 3-Solution 技术方案设计 Spec（Brainstorming 输出）

## 1. 范围

为 HarnessFlow 项目设计 3-Solution 三个子方案（3-1 技术方案 / 3-2 TDD 用例 / 3-3 监督控制规约）的总体结构、内容模板、并行撰写策略。

## 2. 架构决策（5 个）

| # | 决策 | 选项 | 理由 |
|---|---|---|---|
| 1 | 实现底座 | **A · 延续现有 Claude Skill + 可选 FastAPI UI 架构** | 2-prd 多处锚定 Skill/hooks/jsonl；Goal §2 定位开源 Skill 要求最高 portability |
| 2 | 3-1 文档粒度 | **C · L1 级 architecture.md + L2 级 tech-design.md** | 继承 2-prd 分层；L2 级粒度防 subagent 触发 watchdog |
| 3 | 每 L2 tech-design 深度 | **B+ · 完整实现级 + 时序图强调** | 接近工程蓝图，支撑 TDD + 4-exe；含字段级 schema / 伪代码 / 表设计 |
| 4 | 时序图形式 | **Mermaid** | 现代 md 渲染器自动识别；比 ASCII 直观；无需编译 |
| 5 | 开源调研 | **每关键模块必查 GitHub 高星** | 用户强调 "模型最优"，比如 KB / loop / supervisor |

## 3. 每个 L2 tech-design.md 的 13 段模板

1. 定位 + 2-prd 映射
2. DDD 映射（aggregate / service / entity / value object / repository）
3. 对外接口定义（API + 入参 schema + 出参 schema + 错误码）
4. 接口依赖
5. P0/P1 核心时序图（Mermaid）
6. 内部核心算法（伪代码）
7. 底层数据表 / schema 设计
8. 状态机（Mermaid + 转换表）
9. **开源最佳实践调研**（GitHub 高星项目 / 关键库选型）
10. 配置参数清单
11. 错误处理 + 降级策略
12. 性能目标
13. 与 2-prd / 3-2 TDD 的映射表

## 4. 文件清单

### 3-1 Technical Solution（77 份）
- L0 (5)：tech-stack / ddd-context-map / open-source-research / sequence-diagrams-index / architecture-overview
- projectModel (1)
- L1-01~L1-10 (10 × (1 architecture + N L2)) = 67
  - L1-01: 6 L2 · L1-02: 7 L2 · L1-03: 5 L2 · L1-04: 7 L2 · L1-05: 5 L2
  - L1-06: 5 L2 · L1-07: 6 L2 · L1-08: 4 L2 · L1-09: 5 L2 · L1-10: 7 L2
  - 总 L2 = 57
- integration (4)：p0-seq / p1-seq / ic-contracts / cross-l1-integration

### 3-2 Solution TDD（~75 份 · 镜像 3-1）
- L0 (1) / projectModel (1)
- L1-0X (10 × (1 L1-integration + N L2 + optional page)) = ~68
- integration (4) / acceptance (1)

### 3-3 Monitoring & Controlling（10 份）
- L0 (1) / quality-standards (1) / dod-specs (3) / hard-redlines (1) / soft-drift-patterns (1) / monitoring-metrics (2) / acceptance-criteria (1)

**总计 ~162 份文档**

## 5. 6-Phase 并行撰写策略

| Phase | 内容 | agent 数 | 并行度 | 预计时长 |
|---|---|---|---|---|
| **Phase 1** | L0 + projectModel 基础先行 | 6 | 并行 | ~15-20 min |
| **Phase 2** | 10 个 L1 architecture.md | 10 | 并行 | ~15-20 min |
| **Phase 3** | 57 个 L2 tech-design.md | 57 | 分批（6 批 × 10 并行） | ~90-120 min |
| **Phase 4** | integration tech-design | 4 | 并行 | ~15-20 min |
| **Phase 5** | 3-2 TDD（镜像 3-1 ~75 份） | ~75 | 分批并行 | ~120-150 min |
| **Phase 6** | 3-3 监督控制规约 | 10 | 并行 | ~20 min |

**总 agent 数 ~162，总时长 3-5 小时**（含 phase 间串行等待）

## 6. 关键规则

### 6.1 v2 分段 Write 策略（上轮验证有效）

每 subagent 严格：
- Write 1 · 骨架（~400-600 行占位）
- Edit 2~N · 逐段填充（≤ 500 行/次）
- 6-12 次 tool call，避免单次 Write 触发 600s watchdog

### 6.2 串不起来时反向修 PRD

subagent 写 3-1 某 L2 tech-design 发现产品 PRD 有以下问题时，**必须反向改 PRD 后继续**：
- 职责边界不清 / 与其他 L2 重叠
- I/O 定义歧义
- IC 字段描述不足以支撑 schema
- 硬约束矛盾
- DDD 建模发现 aggregate 边界不合理

**改 PRD 规则**：
- 在 tech-design 顶部声明 "修改了 docs/2-prd/L1-XX/prd.md §X.Y（原因）"
- 用 Edit，不用 Write
- 不改 PM-14（project_id as root）骨架

3-2 TDD 同理：发现 PRD + 3-1 串不起来，反向追究。

### 6.3 开源调研硬要求

每个 L2 tech-design 的 **§9 开源最佳实践调研** 必含：
- 至少 3 个 GitHub 高星（> 1k stars）类似项目的 link
- 本方案**学习 / 参考 / 弃用**了什么
- 星数 / commits / 最近活跃度佐证
- 特别关键模块（KB / main loop / supervisor / skill orchestration / event bus）必含性能 benchmark 对比

### 6.4 Mermaid 时序图规范

每份 tech-design 至少 1 张 Mermaid 时序图（P0 或关键流程）。使用 `mermaid` code block：

```
sequenceDiagram
  participant L1-01 as 主 loop
  participant L1-02 as 生命周期
  L1-01->>L1-02: IC-01 request_state_transition
  L1-02-->>L1-01: {accepted: true, new_entry}
```

### 6.5 DDD 映射要求

每 L2 视为一个 bounded context 内的 aggregate 或 service：
- aggregate（有状态实体）：e.g., L1-03 L2-02 拓扑图管理器
- service（无状态函数）：e.g., L1-04 L2-02 DoD 表达式编译器
- repository（持久化）：所有 jsonl / yaml / md 访问走 repository pattern
- entity / value object：字段级 schema 标清

### 6.6 接口驱动设计

每 L2 tech-design 的顺序：
1. 先定义对外接口（入参 schema / 出参 schema）
2. 再定义接口依赖（被谁调 / 调谁）
3. 再画时序图（把接口串起来）
4. 最后才写内部伪代码

## 7. 自审检查

- [x] 架构决策明确（5 项）
- [x] 3-1/3-2/3-3 文件清单精确（对标 2-prd L2 数量）
- [x] 13 段 L2 模板完整
- [x] 6-Phase 并行策略可执行
- [x] 串不起来时处理规则明确
- [x] 开源调研硬要求写入
- [x] Mermaid / DDD / 接口驱动要求明确

---

*— 设计 spec v1.0 · user 已在 Brainstorming Phase 批准 · 进入 Implementation Phase（启动 Phase 1）—*
