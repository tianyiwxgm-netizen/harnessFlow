# routing-matrix.md

**版本**: v1.0 (2026-04-16)
**Status**: DRAFT（Phase 3 产出）
**Readers**: 主 skill (Phase 5) / Supervisor (Phase 6) / 贡献者

> 本文档把 method3.md § 2-3（分诊 + 路由规则）落实为**可查表的决策矩阵**。给主 skill 一个 `(size, type, risk)` 三维向量，它查本文档 § 2 主表立刻拿到 `candidates[]`，再经 § 3 风险修正 + § 4 算法排序，输出 top-2 推荐路线交给用户（详见 method3 § 3.2 澄清阶段豁免）。路线完整调度序列见 `flow-catalog.md`。

---

## § 1 三维决策维度

主 skill 分诊后对任务打三个标签：

### 1.1 size（体量）

| 代号 | 判定规则 | 典型例子 |
|---|---|---|
| **XS** | < 50 行改动 / 单文件 / < 30 分钟预估 | typo / docstring 修 / 单函数 bug |
| **S** | 50-200 行 / 1-3 文件 / 0.5-2 小时 | 单模块小 feature / bug fix |
| **M** | 200-500 行 / 3-10 文件 / 0.5-1 天 | 单模块中 feature / Vue 新页面 |
| **L** | 500-2000 行 / 10-30 文件 / 1-3 天 | 跨模块 feature / subgraph 节点改 |
| **XL** | 2000-5000 行 / 30+ 文件 / 3-7 天 | 视频出片 / 大重构 / graph 新增 |
| **XXL+** | > 5000 行 / 跨会话 / > 1 周 | 架构级重构 / 全链路 pipeline 改造 |

**判定原则**：
- 宁大勿小（路线重可降级，反之禁回退 — flow-catalog § 8.3）
- 首次分诊不确定时取**上界**；执行中发现体量爆炸，按 § 2.3 切换
- 体量 ≥ L 且涉及 graph / 视频 / 不可逆 → 直接进 XL 通道

### 1.2 type（类型）

| 代号 | 判定规则 |
|---|---|
| **纯代码** | 单文件或多文件函数级改动，不涉及 API / schema / UI / agent graph |
| **后端 feature** | 新增或修改 FastAPI 路由 / 服务层 / DB schema / controller |
| **UI** | Vue 模板 / Element Plus / Vue Flow / 组件视觉 / CSS 改动 |
| **agent graph** | LangGraph 节点 / subgraph / TypedDict state / LangChain chain 编排 |
| **文档** | .md / docstring / README / 架构文档 |
| **重构** | 行为不变的代码结构调整 / 分层 / 命名重构 |
| **研究** | 选型 / 调研 / 方案对比 / 决策前置，产出是决策 log |

**交叉情况**：
- UI + 后端 → 按**后端**主类型 + UI 辅标签；路线走 C（见 § 3.1 修正）
- 视频出片 → 归 **agent graph**（LangGraph pipeline）+ 触发风险 **不可逆**（OSS 写入）
- 研究 → **无论体量都走 F**（§ 4.3 特殊规则）

### 1.3 risk（风险）

| 代号 | 判定规则 |
|---|---|
| **低** | 可本地回滚 / 无 prod 影响 / 无 DB 迁移 / 无 OSS 生产 bucket 写入 |
| **中** | 改动触及公开 API 兼容性 / 多用户影响 / 可回滚但成本较高 |
| **高** | DB schema 变更 / 影响多项目 / 回滚复杂 / 涉及定时任务 |
| **不可逆** | prod push / OSS 生产 bucket 非幂等覆盖写 / 删数据 / DB migration（非 reversible） |

**注意**（见 method3 § 5.2 OSS 豁免）：
- 视频出片任务的 OSS 上传**属于 DoD 内自动步骤**，不触发 IRREVERSIBLE_HALT 红线，仍按**不可逆**风险走路线 C（强制 Verifier）
- DB migration 若是 additive + nullable + backfill，可降到**高**；destructive migration 强制**不可逆**

---

## § 2 矩阵主表

### 2.1 表结构

每个 cell 格式：`路线 (权重) / 备选路线 (权重)`
- 权重范围 0.0 - 1.0（非百分比），值越高越推荐
- `-` 表示该组合在实践中罕见或不存在（若出现走 LLM 真分叉路由）
- 主表仅含 size × type 二维；risk 通过 § 3 修正器叠加

### 2.2 主表（6 行 × 7 列 = 42 cell）

| 体量＼类型 | 纯代码 | 后端 feature | UI | agent graph | 文档 | 重构 | 研究 |
|---|---|---|---|---|---|---|---|
| **XS** | A (1.0) / B (0.3) | B (0.9) / A (0.7) | A (0.5) / D (0.8) | - | A (1.0) | A (0.6) / B (0.7) | F (1.0) |
| **S** | B (0.9) / A (0.6) | B (1.0) | D (1.0) / B (0.6) | B (0.7) / E (0.4) | B (0.8) | B (0.9) / C (0.4) | F (1.0) |
| **M** | B (1.0) / C (0.5) | B (0.7) / C (0.9) | D (1.0) / B (0.4) | E (0.9) / B (0.5) | B (1.0) | C (1.0) / B (0.6) | F (1.0) |
| **L** | C (1.0) / B (0.4) | C (1.0) | D (0.8) / C (0.7) | E (1.0) / C (0.6) | C (0.8) | C (1.0) | F (0.8) +flag:convert_to_C |
| **XL** | C (1.0) | C (1.0) | C (1.0) | E (1.0) / C (0.9) | C (1.0) | C (1.0) | F (0.8) +flag:convert_to_C |
| **XXL+** | C (1.0) +flag:split_required | C (1.0) +flag:split_required | C (1.0) +flag:split_required | E (1.0) +flag:split_required | C (1.0) +flag:split_required | C (1.0) +flag:split_required | F (0.8) +flag:convert_to_C |

**cell 格式规范化说明**（供算法 parse）：
- 标准 cell: `路线1 (权重1) / 路线2 (权重2)` — 逗号分隔两候选
- 单候选 cell: `路线 (权重)` — 仅一个候选
- 带 flag 的 cell: `路线 (权重) +flag:<flag_name>` — `flag_name` 由主 skill 查 `FLAG_HANDLERS` 字典后续处理（见 § 4.1 伪码 step 6）
- `-` 表示罕见组合，走 LLM 真分叉路由
- XXL+ 行所有 cell 必带 `+flag:split_required`，主 skill 自动触发分拆流程（见 § 2.3）

### 2.3 矩阵读法示例（简化版）

> 本节仅演示 cell 解析 + 风险修正。**完整演算**（含 failure-archive 降权、特殊规则触发、top-2 输出）见 § 6 示例 1-5。

任务向量 `(M, UI, 低)`：
1. 查表 cell = `D (1.0) / B (0.4)`
2. 风险低 → 无修正（见 § 3.1）
3. top-2 = `[D (1.0), B (0.4)]` → 推荐 D

任务向量 `(XL, agent graph, 不可逆)`：
1. 查表 cell = `E (1.0) / C (0.9)`
2. 风险不可逆 → § 3 修正 `C 权重 +0.3` = `C 0.9 + 0.3 = 1.2` → 封顶 1.0
3. 风险不可逆 → **禁 A** + 强制 Verifier + IRREVERSIBLE_HALT 前置检查
4. top-2（不含 failure-archive）= `[E (1.0), C (1.0)]`
5. **注意**：含 failure-archive 降权的完整演算见 § 6.1（考虑 P20 历史失败后 C 降权为 0.8）

**XXL+ 分阶段规则**（`flag:split_required` 处理器）：
- 任何 XXL+ 任务主 skill 读到 `+flag:split_required` 后，必须在 plan 阶段调用分拆子流程
- 拆为多个 L/XL 子任务，每子任务独立走路线 C（或 E），独立 DoD + checkpoint
- 整体收口 DoD = 各子任务 DoD `AND` 聚合
- 禁止一次性走单条 C 路线完成 XXL+ 任务

**研究 L/XL 处理**（`flag:convert_to_C` 处理器）：
- L/XL 研究读到 `+flag:convert_to_C` 后，F 路线输出决策 log 即刻触发 C 实施路线
- 决策 log 作为 C 路线的 Mandatory Reading 输入
- 本行 cell 的权重 0.8 意指 F 仅作为"前置阶段"，收口必过 C

---

## § 3 风险修正器

### 3.1 风险 → 路线权重调整

| 风险 | 修正规则 | 附加硬约束 |
|---|---|---|
| **低** | 无修正 | 无 |
| **中** | C 权重 +0.1 | 无 |
| **高** | C 权重 +0.2 / A 权重 -0.3 | 若当前 top-1 是 A 且权重跌到 < 0.5，自动提升 B 为 top-1 |
| **不可逆** | C 权重 +0.3（封顶 1.0） / E 权重 +0.2 | **禁 A**（从 candidates 移除） + 强制 `harnessFlow:verifier` gate + IRREVERSIBLE_HALT 前置检查 |

**修正计算公式**：
```
new_weight(route) = min(1.0, old_weight(route) + risk_adjustment(route, risk))
```

**RISK_ADJUSTMENT 数据字典**（算法查表时使用，key = `(route, risk)`）：
```python
RISK_ADJUSTMENT = {
    # 低风险 — 无修正
    ("A", "低"): 0.0, ("B", "低"): 0.0, ("C", "低"): 0.0,
    ("D", "低"): 0.0, ("E", "低"): 0.0, ("F", "低"): 0.0,
    # 中风险 — C +0.1
    ("A", "中"): 0.0, ("B", "中"): 0.0, ("C", "中"): +0.1,
    ("D", "中"): 0.0, ("E", "中"): 0.0, ("F", "中"): 0.0,
    # 高风险 — C +0.2, A -0.3
    ("A", "高"): -0.3, ("B", "高"): 0.0, ("C", "高"): +0.2,
    ("D", "高"): 0.0, ("E", "高"): 0.0, ("F", "高"): 0.0,
    # 不可逆 — C +0.3, E +0.2, A 移除（由算法 step 3 显式处理）
    ("A", "不可逆"): -1.0,  # 哨兵值，实际由 candidates filter 移除
    ("B", "不可逆"): 0.0, ("C", "不可逆"): +0.3,
    ("D", "不可逆"): 0.0, ("E", "不可逆"): +0.2, ("F", "不可逆"): 0.0,
}
```

### 3.2 不可逆风险的 IRREVERSIBLE_HALT 前置检查

对 `risk == 不可逆` 任务，**主 skill 在启动执行前**必须 Supervisor 前置检查：

| 动作类别 | 前置条件 | 检查方式 |
|---|---|---|
| OSS 非幂等覆盖写（生产 bucket） | DoD 明示 OSS key 验证 | Verifier DoD 含 `oss_head.status_code == 200` |
| DB migration（destructive） | 有 reversible migration 或备份 | 查 migration 脚本含 downgrade 或备份命令 |
| prod push | PR 已过 review + CI 绿 | 查 `gh pr view` 状态 |
| 删数据 / `rm -rf` 生产路径 | 用户显式授权（文字确认） | 主 skill 等待明确确认动作 |

前置不满足 → Supervisor 报 `IRREVERSIBLE_HALT` 红线（harnessFlow.md § 4.3 + method3 § 5.2），强制拦截。

**OSS 豁免**（与 method3 § 5.2 一致）：视频出片的 OSS 上传是 DoD 内部自动步骤，不触发 IRREVERSIBLE_HALT，仍满足"风险=不可逆"修正规则。

---

## § 4 决策规则

### 4.1 查表算法（Python 伪码）

**数据源声明**（主 skill 启动时从本文档 + failure-archive 加载）：
- `MATRIX`：主 skill 启动时解析本文档 § 2.2 表格生成 `dict[Size, dict[Type, list[tuple[Route, weight, flags]]]]`，持久化为 `harnessFlow /routing-matrix.json`（每次 matrix 变更自动 regen + diff 审计）
- `RISK_ADJUSTMENT`：主 skill 启动时加载本文档 § 3.1 Python 字典字面量
- `FAILURE_ARCHIVE`：主 skill 启动时加载 `harnessFlow /failure-archive.jsonl`（Phase 7 产出），MVP 空文件时所有查询返回 `failure_rate=0`
- `FLAG_HANDLERS`：主 skill 内置处理器，支持 `split_required`（XXL+ 分拆）/ `convert_to_C`（研究转实施）

```python
def route_decide(size: Size, task_type: Type, risk: Risk) -> list[Candidate]:
    # 1. 查主表 cell
    raw_cell = MATRIX[size][task_type]  # e.g. [("E", 1.0, []), ("C", 0.9, [])]
    if raw_cell is None or raw_cell == "-":
        # 罕见组合 → LLM 真分叉路由（method3 § 3.1 二级路由）
        return llm_real_branch_route(size, task_type, risk)

    candidates = [Candidate(route=r, weight=w, flags=f) for r, w, f in raw_cell]

    # 2. 风险修正
    for c in candidates:
        adj = RISK_ADJUSTMENT.get((c.route, risk), 0.0)
        c.weight = min(1.0, max(0.0, c.weight + adj))

    # 3. 不可逆强制移除 A + 强制 Verifier 标注
    if risk == "不可逆":
        candidates = [c for c in candidates if c.route != "A"]
        for c in candidates:
            c.force_verifier_gate = True
            c.force_irreversible_halt_precheck = True

    # 4. failure-archive 降权
    for c in candidates:
        archive_stats = FAILURE_ARCHIVE.query(route=c.route, type=task_type)
        if archive_stats.failure_rate > 0.3:
            c.weight *= 0.8
            c.warning = f"历史失败率 {archive_stats.failure_rate:.0%}"

    # 5. 排序 + top-2
    #   注：研究 type 不需特殊插入 F —— § 2.2 表所有研究 cell 已经 F 主推
    candidates.sort(key=lambda x: -x.weight)
    top = candidates[:2]

    # 6. flags 后处理（XXL+ 分拆 / L-XL 研究转 C）
    for c in top:
        for flag in c.flags:
            FLAG_HANDLERS[flag](c)  # 例如 split_required 触发分拆预提示

    return top
```

**step 5 去除 "特殊规则 研究插入 F" 死代码说明**：§ 2.2 表所有 `研究` 列 cell 已主推 F，候选列表必已含 F，无需额外 insert。研究 L/XL 的 `convert_to_C` 由 step 6 flag handler 处理，不在 step 5。

### 4.2 failure-archive 降权详规

- 降权触发条件：同一 `(route, task_type)` 组合在 `failure-archive.jsonl` 中最近 20 条 entry 里失败率 > 30%（MVP 默认，见 § 5）
- 降权幅度：`weight *= 0.8`
- 降权后仍进入候选列表，但附带 `warning` 字段，主 skill 呈现给用户
- 降权不会导致候选数量减少（除非降到 weight < 0.2 才移出）

### 4.3 特殊规则

1. **研究 type 默认 F**：由 § 2.2 主表直接实现（所有研究列主推 F），无需算法 step 额外处理
2. **不可逆禁 A**：风险不可逆时 A 直接从候选移除（§ 4.1 step 3）
3. **XXL+ 强制分阶段**：主表 XXL+ 行所有 cell 带 `+flag:split_required`，主 skill 读到后触发分拆预提示，不允许一次性走单条 C
4. **研究 L/XL 收口转 C**：主表 L/XL 研究 cell 带 `+flag:convert_to_C`，F 路线产出决策 log 后立即触发 C 实施
5. **视频出片专属规则**：任务描述含"出片 / 视频 / media" + `type == agent graph` → 自动标注 `video_output=True`，DoD 必含 method3 § 6.1 模板①全部条件
6. **无 cell 的真分叉**：`cell == "-"` 或 `cell is None` → 走 `llm_real_branch_route()`（method3 § 3.1 二级 LLM 路由），结果必记 `routing_events[]`

---

## § 5 evolution_config（MVP 默认 + 覆盖方式）

### 5.1 MVP 默认阈值

```json
{
  "route_outcome_min_samples": 10,
  "combination_min_success": 5,
  "audit_interval_tasks": 20,
  "failure_penalty_threshold": 0.3,
  "failure_penalty_factor": 0.8,
  "weight_cap": 1.0,
  "is_stuck_repeat_threshold": 3,
  "warn_downgrade_threshold_per_task": 10,
  "warn_dedup_window_seconds": 300
}
```

- `route_outcome_min_samples`：matrix 权重 review 触发最小样本数（method3 § 7.2）
- `combination_min_success`：新组合晋升推荐候选的成功次数阈值（method3 § 7.2）
- `audit_interval_tasks`：每 20 次任务触发一次路由权重审计（method3 § 7.3）
- `failure_penalty_threshold` / `factor`：历史失败降权触发点和幅度（§ 4.2）
- `weight_cap`：修正后权重封顶（§ 3.1 修正计算）
- `is_stuck_repeat_threshold`：Supervisor 冗余干预触发阈值（method3 § 5.1⑥）
- `warn_downgrade_threshold_per_task`：**严格大于（`>`）**该值的第 N+1 条 WARN 自动降 INFO。MVP 默认 10，即任务内前 10 条 WARN 正常呈现，第 11 条起降 INFO（harnessFlow.md § 7.7）
- `warn_dedup_window_seconds`：同类 WARN 去重窗口，窗口内重复 WARN（同 `signal_source + code`）合并为单条（harnessFlow.md § 7.7）

### 5.2 覆盖方式

1. 编辑本文件 § 5.1 JSON 块 → 提交 PR → 同时 bump 本文档和 flow-catalog.md 版本号
2. 或在 `harnessFlow /routing-matrix.json`（Phase 5 主 skill 启动时从本文档生成）的 `evolution_config` 字段覆盖，该 JSON 文件每次 commit 自动校验与本文档一致
3. 进化引擎（harnessFlow.md § 3.3）每 audit_interval_tasks 次任务自动产出 `权重 review 建议 diff`，走 PR 审批合入

---

## § 6 查表示例

### 示例 1：aigcv2 P20 视频出片任务

**任务向量**：`(XL, agent graph, 不可逆)` + `video_output=True`

**查表演算**：
1. cell `MATRIX[XL][agent graph]` = `[("E", 1.0), ("C", 0.9)]`
2. 风险不可逆：
   - E 权重 +0.2 → `min(1.0, 1.0+0.2) = 1.0`
   - C 权重 +0.3 → `min(1.0, 0.9+0.3) = 1.0`
3. 禁 A（不在候选中，无影响）；E 和 C 均标注 `force_verifier_gate=True` + `force_irreversible_halt_precheck=True`
4. failure-archive 查询：旧 C 路线曾在 `(XL, agent graph)` 组合下失败（P20 事故） → C 权重 `* 0.8 = 0.8`，附 `warning="历史失败率 100%（旧 C 版 P20 翻车）"`
5. 特殊规则 4：`video_output=True` → DoD 必含 method3 § 6.1 模板① 全部条件
6. 排序 + top-2：`[E (1.0), C (0.8, warning)]`

**输出给用户**：
```
推荐 top-1: 路线 E — agent graph 专线 (权重 1.0)
推荐 top-2: 路线 C — 全 PRP 重验证 (权重 0.8, 警告: 旧版 C 在 P20 翻车，新 C 已补 Verifier 门)
附加约束: 强制 harnessFlow:verifier gate + IRREVERSIBLE_HALT 前置检查 + DoD 模板①全条件
```

### 示例 2：aigc 后端加 Product Hunt 素材源

**任务向量**：`(L, 后端 feature, 中)`

**查表演算**：
1. cell `MATRIX[L][后端 feature]` = `[("C", 1.0)]`
2. 风险中：C 权重 +0.1 → `min(1.0, 1.0+0.1) = 1.0`
3. failure-archive 无历史失败
4. 无特殊规则触发
5. top-2：`[C (1.0)]`（cell 只一条候选）

**输出**：
```
推荐 top-1: 路线 C — 全 PRP 重验证 (权重 1.0)
推荐 top-2: 无（cell 单候选）；允许用户选"真分叉 LLM 路由"产生 top-2
```

### 示例 3：Vue 新页面（AIGC 素材详情页）

**任务向量**：`(M, UI, 低)`

**查表演算**：
1. cell `MATRIX[M][UI]` = `[("D", 1.0), ("B", 0.4)]`
2. 风险低：无修正
3. failure-archive 无历史失败
4. 无特殊规则
5. top-2：`[D (1.0), B (0.4)]`

**输出**：
```
推荐 top-1: 路线 D — UI 视觉专线 (权重 1.0)
推荐 top-2: 路线 B — 轻 PRP (权重 0.4)
```

### 示例 4：修 docstring typo

**任务向量**：`(XS, 文档, 低)`

**查表演算**：
1. cell `MATRIX[XS][文档]` = `[("A", 1.0)]`
2. 风险低：无修正
3. failure-archive 无
4. 无特殊规则
5. top-2：`[A (1.0)]`

**输出**：
```
推荐 top-1: 路线 A — 零 PRP 直改 (权重 1.0)
推荐 top-2: 无
```

### 示例 5：LangChain 选型调研

**任务向量**：`(M, 研究, 低)`

**查表演算**：
1. cell `MATRIX[M][研究]` = `[("F", 1.0)]`
2. 风险低：无修正
3. failure-archive 无
4. 特殊规则 1 触发：研究 type 默认 F（已在候选中，无动作）
5. top-2：`[F (1.0)]`

**输出**：
```
推荐 top-1: 路线 F — 研究方案探索 (权重 1.0)
推荐 top-2: 无；决策敲定后自动提示"转 B/C 实施"
```

---

*本文档把 method3.md § 2-3（分诊 + 路由）转化为可查表的决策矩阵。路线完整调度序列见 flow-catalog.md；决策执行由 Phase 5 主 skill 落地；权重审计由进化引擎（harnessFlow.md § 3.3）驱动。*

*— v1.0 end —*
