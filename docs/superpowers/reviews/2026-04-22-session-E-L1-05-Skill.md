# 【并发会话 E】3-1/L1-05 Skill 生态+子 Agent 调度 × 5 份 L2 填充

> ## ✅ **已完成 · 2026-04-22**
>
> - 交付 5/5 份 depth-B（~7737 行 · 14 节齐 · FILL=0 · Mermaid=0）
> - commits：6a2d570（L2-01）/ b0b8067（L2-02）/ e5d224b（L2-03）/ d1164be（L2-04）/ 4cd938e（L2-05）
> - P2 微调 commit fb05e86（§13 反向 prd 路径统一）
> - 主会话审查报告：`docs/superpowers/reviews/2026-04-22-E-session-polish-prompt.md`
> - **质量评分：9/10 优秀** · 14 节齐 · PlantUML 全配对 · TDD 路径全部带 L1 编号 · IC-XX 500+ 处

## 背景

harnessFlow 3-1-Solution-Technical 已完成 39/57 份 L2（L1-01/04/06/07/08/10 全 done + L1-02 部分）。
你负责 **L1-05 Skill 生态+子 Agent 调度** 的 5 份 L2，全是 131 行骨架。其他会话并发做 L1-02/03/09，彼此不冲突。

## 任务文件（只动 L1-05 目录）

1. `docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md`
2. `docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md`
3. `docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md`
4. `docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md`
5. `docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-05-异步结果回收器.md`

## 各 L2 定位（硬必填 §1 里要精确引用）

- **L2-01 Skill 注册表**：所有可用 Skill（frontmatter + 能力声明 + invocation 协议）的 in-memory + 落盘索引 · 启动时加载 · 运行时热更新 · BC-05 Aggregate Root = SkillRegistry
- **L2-02 Skill 意图选择器**：用户/Agent 的意图 → Skill 匹配（向量相似度 + 规则 + 历史经验 KB 混合）· 返回 top-N 排序 + 置信度
- **L2-03 Skill 调用执行器**：Skill 的 invoke 编排（context injection + timeout + retry + audit seed）· 单 session 内执行（非子 Agent）
- **L2-04 子 Agent 委托器**：把 Skill 调用派发给独立 Claude session（subagent）· 隔离 context · 管理生命周期 · 资源上限 · 对接 Anthropic Claude Agent SDK
- **L2-05 异步结果回收器**：子 Agent 完成事件的订阅 + 结果装配 + 超时处理 · 对接 L1-04 质量环做 DoD 校验

## 必读参考

1. **质量标杆**：`docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md` §1/§3/§11/§13（学深度节奏）
2. **精简 B 范本**：`docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-03-图片视觉理解编排器.md`（1804 行 depth-B+）
3. **L1-05 架构**：`docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/architecture.md`
4. **PRD**：`docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md`（路径含空格）
5. **契约锚点**：`docs/3-1-Solution-Technical/integration/ic-contracts.md`（查 IC-04/IC-05/IC-08/IC-14）
6. **消费方参考（L1-04 会调你的调用执行器）**：`docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-01-TDD 蓝图生成器.md` §4（它对 L1-05 的依赖描述）
7. **L1-06 KB 读（意图选择会读历史）**：`docs/3-1-Solution-Technical/L1-06-3层知识库/L2-02-KB 读.md`

## 模板 · 精简 B（500-800 行/份）

硬必填 5 段深度：§1 / §3 / §5 / §11 / §13
精简 8 段（每段 30-50 行 bullet）：§2 / §4 / §6-§10 / §12

### 各段硬约束

- **§1**：精确映射 prd 小节 · 关键决策 3-5 条 · 50-100 行
- **§3**：字段级 YAML schema ≥ 3 blocks + 错误码 ≥ 8 条四列表 · 80-150 行
- **§5**：PlantUML ≥ 2 张（P0 主干 + P1 异常/降级）· 50-100 行
- **§7**：PM-14 分片 · 推荐路径 `projects/<pid>/skills/{registry-cache|invocations|subagent-sessions|results}/*` · 字段级 YAML · 30-60 行
- **§8**：状态机（SkillRegistry 是有状态 · SkillInvoker/SubagentDelegator 有状态 · IntentSelector 无状态）
- **§9**：≥ 3 开源对标 · Adopt/Learn/Reject 三段俱全
  - 建议对标（任选 3-4）：LangChain / LangGraph / AutoGen / CrewAI / OpenAI Swarm / Anthropic Claude Agent SDK / Temporal
- **§11**：≥ 12 错误码四列表 + 3-4 级降级链 · 60-100 行
  - 典型错误码建议：SKILL_NOT_FOUND / SKILL_INVOCATION_TIMEOUT / SKILL_INVALID_FRONTMATTER / INTENT_AMBIGUOUS / SUBAGENT_SPAWN_FAIL / SUBAGENT_CONTEXT_OVERFLOW / RESULT_SCHEMA_MISMATCH / RETRY_EXHAUSTED / RATE_LIMIT_EXCEEDED 等
- **§13**：反向映射到 `docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md §X.X` + 前向占位 `docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/L2-0N-tests.md`（待建）· **必须带 L1 完整目录名** · ≥ 15 TC ID 矩阵 + 2-3 ADR + 2-3 OQ
- **IC-XX 引用**：每份 ≥ 5 处

## 硬约束（禁区红线）

- 图一律 PlantUML · **禁止 Mermaid**
- 所有 `@startuml` 必配 `@enduml`
- 无 `<!-- FILL`、无 `TBD`、无 `TODO`、无 `待填`
- TDD 占位路径**必带 L1 完整目录名**：`docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/L2-0N-tests.md`（不要只写 `L1/L2-...` · 这是 A 会话踩过的坑）
- §13 反向 + 前向**都要有**
- 同一 L2 文件内错误码命名风格保持一致

## 执行节奏（每份 L2 · 7 步）

1. **Read 骨架** + **标杆 L2-02 §3/§11/§13** + **L1-08/L2-03 节奏** + **prd 对应小节** + **architecture**（并行 4-5 call）
2. **Read ic-contracts.md** 找本 L2 相关的 IC-XX
3. **Edit §1 + §3**（≤ 400 行 patch）
4. **Edit §5 + §11**（≤ 400 行 patch）
5. **Edit §13 + 剩余 8 段 bullet**（≤ 300 行 patch）
6. **Bash 验证**：
   ```bash
   fp="docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-0N-XXX.md"
   echo "行数=$(wc -l < "$fp")"
   echo "§数=$(grep -c '^## §' "$fp")"              # 期望 14（含 §0）
   echo "FILL=$(grep -c '<!-- FILL' "$fp")"         # 期望 0
   echo "Mermaid=$(grep -c '```mermaid' "$fp")"     # 期望 0
   echo "@start/end=$(grep -c '^@startuml' "$fp")/$(grep -c '^@enduml' "$fp")"  # 必相等
   echo "IC-XX=$(grep -cE 'IC-[A-Z0-9-]+' "$fp")"   # 期望 ≥ 5
   ```
7. **Commit**（每份独立 commit）：
   ```bash
   git add "docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-0N-XXX.md"
   git commit -m "feat(harnessFlow): R4.3-E · L1-05/L2-0N XXX depth-B 完成"
   ```

## 推进顺序建议

**L2-01（注册表 · 地基）→ L2-02（意图选择 · 读注册表）→ L2-03（调用执行 · 依赖意图选择）→ L2-04（子 Agent 委托 · L2-03 的独立 session 特化分支）→ L2-05（异步回收 · 订阅 L2-04 事件）**

理由：L2-01 Registry 是所有其他 L2 的查询源；依次按依赖方向推进减少返工。

## 最终验收

5 份全绿后：

```bash
# 全局 Gate
./scripts/quality_gate.sh

# 本批自检
for f in "docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度"/L2-*.md; do
    lines=$(wc -l < "$f")
    fill=$(grep -c '<!-- FILL' "$f")
    secs=$(grep -c '^## §' "$f")
    bad_tdd=$(grep -c "docs/3-2-Solution-TDD/L1/L2-" "$f")  # 必须 0
    echo "$(basename "$f"): lines=$lines §=$secs FILL=$fill bad_tdd_path=$bad_tdd"
done

# Push
git push
```

完成后回主会话报告：**5 份全部 depth-B 完成 + 最后 commit SHA + 总行数**。

## 禁区（不要碰）

- `docs/3-1-Solution-Technical/L1-02/`、`L1-03/`、`L1-09/` —— 其他会话在做
- `docs/3-1-Solution-Technical/integration/` —— 契约已锁定
- `docs/3-2-Solution-TDD/` —— G 会话在建
- `scripts/quality_gate.sh` —— 主会话维护
- 任何 `L1-01/04/06/07/08/10` 已完工 L2 —— 只读参考

## 开工前检查

```bash
git pull origin main
git status
ls "docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/"   # 确认 5 份骨架在
```

准备好后开始 L2-01（Skill 注册表）。
