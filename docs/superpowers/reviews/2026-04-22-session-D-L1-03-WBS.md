# 【并发会话 D】3-1/L1-03 WBS+WP 拓扑调度 × 5 份 L2 填充

> ## ✅ **已完成 · 2026-04-22**
>
> - 交付 5/5 份 depth-B+（6584 行 · 14 节齐 · FILL=0 · Mermaid=0 · PlantUML 25 对全配对）
> - TC ID 93 条 · 错误码表 22-45 行/份 · IC-XX 100-187 处/份
> - commits：b891485（L2-01）/ da48eab（L2-02）/ 8696ab0（L2-03）/ 5adf630（L2-04）/ 3b62b66（L2-05）
> - 执行方式：L2-02 主写（基线）+ 4 subagent 并行做 L2-01/03/04/05
> - 跨 L2 一致性：错误码命名 `E_L103_L20N_NNN` / IC-L2-01~08 / 六状态机 `LEGAL_TRANSITIONS` L2-02 §8 单点定义
> - **质量评分：9.5/10 优秀** · 无 A 会话坑 · TDD 路径全带 L1 完整目录
> - 主会话审查报告 + P2 微调 prompt：`docs/superpowers/reviews/2026-04-22-D-session-polish-prompt.md`（§13 反向 prd 路径统一化 · 与 E 会话 fb05e86 同类）

## 背景

harnessFlow 3-1-Solution-Technical 已完成 39/57 份 L2（L1-01/04/06/07/08/10 全 done + L1-02 部分）。
你负责 **L1-03 WBS+WP 拓扑调度** 的 5 份 L2，当前全是 131 行骨架。其他会话并发做 L1-02/05/09，彼此不冲突。

## 任务文件（只动 L1-03 目录）

1. `docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-01-WBS 拆解器.md`
2. `docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-02-拓扑图管理器.md`
3. `docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-03-WP 调度器.md`
4. `docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-04-WP 完成度追踪器.md`
5. `docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-05-失败回退协调器.md`

## 各 L2 定位（硬必填 §1 里要精确引用这些）

- **L2-01 WBS 拆解器**：S2 Planning 后把 4 件套中的 Plan 拆成 Work Package 层级树（PMP WBS 工具）· BC-03 Aggregate Root = WBS · 产出 WBSItemTree 数据结构
- **L2-02 拓扑图管理器**：WP 之间的依赖 DAG 管理（无环校验 · 关键路径计算 · 前驱/后继查询）· 供 L1-02/L2-01 S3 TDD Gate 调用做环检测
- **L2-03 WP 调度器**：基于拓扑序 + 并发度 + 资源池向 L1-05 Skill 派发 WP 执行请求 · 含 backpressure + priority queue + timeout
- **L2-04 WP 完成度追踪器**：订阅 L1-09 事件（IC-09）· 聚合 WP 状态（pending/running/done/failed/blocked）+ Burndown · 供 L1-10/L2-03 进度实时流消费
- **L2-05 失败回退协调器**：WP 失败时的回退协议（retry with backoff / skip-and-mark / rollback-to-checkpoint / escalate-to-supervisor）· 与 L1-07 supervisor 协同 IC-06

## 必读参考（强制 Read · 每 L2 都要读）

1. **质量标杆（学深度节奏）**：`docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md` §1/§3/§11/§13
2. **精简 B 范本（1804 行 depth-B+）**：`docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-03-图片视觉理解编排器.md`
3. **L1-03 架构**：`docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/architecture.md`
4. **PRD**：`docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md`（路径含空格）
5. **契约锚点**：`docs/3-1-Solution-Technical/integration/ic-contracts.md`（查 IC-02/IC-03/IC-08/IC-11/IC-15）
6. **依赖上游**：`docs/3-1-Solution-Technical/L1-02-项目生命周期编排/architecture.md`（PMP×TOGAF 交织矩阵 · WBS 来源）
7. **事件订阅源**：`docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-01-事件总线核心.md`（L2-04 会订阅它）

## 模板 · 精简 B（500-800 行/份）

硬必填 5 段深度：§1 / §3 / §5 / §11 / §13
精简 8 段（每段 30-50 行 bullet）：§2 / §4 / §6-§10 / §12

### 各段硬约束

- **§1**：精确映射 prd 小节 · 含关键决策 3-5 条 · 50-100 行
- **§3**：字段级 YAML schema（≥ 3 个 yaml code block · 请求/响应/错误对象）· 错误码表 ≥ 8 条四列（errorCode/meaning/trigger/callerAction · 或中文等价列名）· 80-150 行
- **§5**：PlantUML 时序图 ≥ 2 张（P0 主干 + P1 异常）· `@startuml/@enduml` 必配对 · 50-100 行
- **§7**：PM-14 分片 · 推荐路径 `projects/<pid>/wbs/*`、`projects/<pid>/wp-queue/*`、`projects/<pid>/wp-progress/*` · 字段级 YAML · 30-60 行
- **§8**：状态机（有状态就画 PlantUML · 无状态就明确标注"本 L2 为无状态服务"）
- **§9**：≥ 3 个 GitHub ≥ 1k stars 项目对标 · 每项 Adopt/Learn/Reject 三段俱全
  - 建议对标（任选 3）：Airflow / Prefect / Temporal / Luigi / Celery / Dagster / Kueue
- **§11**：≥ 12 错误码四列表 + 3-4 级降级链（含 PlantUML 降级状态图）· 60-100 行
- **§13**：反向映射到 `docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md §X.X` + 前向占位 `docs/3-2-Solution-TDD/L1-03-WBS+WP 拓扑调度/L2-0N-tests.md`（待建）· **必须带 L1 完整目录名** · ≥ 15 TC ID 矩阵 + 2-3 ADR + 2-3 OQ
- **IC-XX 引用**：每份 ≥ 5 处

## 硬约束（禁区红线）

- 图一律 PlantUML（`@startuml...@enduml`）· **禁止 Mermaid**
- 所有 `@startuml` 必配 `@enduml`
- 无 `<!-- FILL`、无 `TBD`、无 `TODO`、无 `待填`
- TDD 占位路径**必带 L1 完整目录名**：`docs/3-2-Solution-TDD/L1-03-WBS+WP 拓扑调度/L2-0N-tests.md`（不要只写 `L1/L2-...` · 这是 A 会话踩过的坑）
- §13 反向 + 前向**都要有**
- 同一 L2 文件内错误码命名风格保持一致（推荐 `E_L103_L20N_NNN` 或 `WBS_XXX_YYY` 风格 · 择一并贯彻）

## 执行节奏（每份 L2 · 7 步）

1. **Read 骨架** + **标杆 L2-02 §3/§11/§13** + **L1-08/L2-03 节奏** + **prd 对应小节** + **architecture**（并行 4-5 call）
2. **Read ic-contracts.md** 找本 L2 相关的 IC-XX
3. **Edit §1 + §3**（≤ 400 行 patch）
4. **Edit §5 + §11**（≤ 400 行 patch）
5. **Edit §13 + 剩余 8 段 bullet**（≤ 300 行 patch）
6. **Bash 验证**：
   ```bash
   fp="docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-0N-XXX.md"
   echo "行数=$(wc -l < "$fp")"
   echo "§数=$(grep -c '^## §' "$fp")"              # 期望 14（含 §0）
   echo "FILL=$(grep -c '<!-- FILL' "$fp")"         # 期望 0
   echo "Mermaid=$(grep -c '```mermaid' "$fp")"     # 期望 0
   echo "@start/end=$(grep -c '^@startuml' "$fp")/$(grep -c '^@enduml' "$fp")"  # 必相等
   echo "IC-XX=$(grep -cE 'IC-[A-Z0-9-]+' "$fp")"   # 期望 ≥ 5
   ```
7. **Commit**（每份独立 commit · 不要 bundle）：
   ```bash
   git add "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-0N-XXX.md"
   git commit -m "feat(harnessFlow): R4.2-D · L1-03/L2-0N XXX depth-B 完成"
   ```

## 推进顺序建议

**L2-02（拓扑图管理器）→ L2-01（WBS 拆解器）→ L2-03（WP 调度器）→ L2-04（完成度追踪器）→ L2-05（失败回退）**

理由：L2-02 拓扑是地基（其他 4 个都用 DAG 概念）· 先定义拓扑 schema 再写其他 L2 的调度/追踪/回退逻辑更顺。

## 最终验收

5 份全绿后：

```bash
# 全局 Gate（应全 PASS 或仅其他 L1 的 FILL WARN）
./scripts/quality_gate.sh

# 本批 5 份自检
for f in "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度"/L2-*.md; do
    lines=$(wc -l < "$f")
    fill=$(grep -c '<!-- FILL' "$f")
    secs=$(grep -c '^## §' "$f")
    bad_tdd=$(grep -c "docs/3-2-Solution-TDD/L1/L2-" "$f")  # 必须 0
    echo "$(basename "$f"): lines=$lines §=$secs FILL=$fill bad_tdd_path=$bad_tdd"
done

# Push
git push
```

完成后回主会话报告：**5 份全部 depth-B 完成 + 最后 commit SHA + 总行数统计**。

## 禁区（不要碰）

- `docs/3-1-Solution-Technical/L1-02/`、`L1-05/`、`L1-09/` —— 其他会话在做
- `docs/3-1-Solution-Technical/integration/` —— 契约已锁定
- `docs/3-2-Solution-TDD/` —— G 会话在建
- `scripts/quality_gate.sh` —— 主会话维护
- 任何 `L1-01/04/06/07/08/10` 已完工 L2 —— 只读参考

## 开工前检查

```bash
git pull origin main                                  # 同步最新
git status                                            # 应干净或只含本会话的 WIP
ls "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/"  # 确认 5 份骨架在
```

准备好后开始 L2-02（拓扑图管理器）。
