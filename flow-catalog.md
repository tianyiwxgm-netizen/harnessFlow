# flow-catalog.md

**版本**: v1.0 (2026-04-16)
**Status**: DRAFT（Phase 3 产出）
**Readers**: 主 skill (Phase 5) / Supervisor (Phase 6) / 贡献者

> 本文档落实 `method3.md § 4` 六条路线精神到**完整调度序列**。method3 定"用什么精神 + 何时切换"，本文档定"具体按什么顺序调哪些 skill/command/agent/hook"。主 skill 路由决策由 `routing-matrix.md` 查表得到 `route_id`，然后查本文档对应章节拿调度序列。

---

## § 1 路线设计框架

### 1.1 七字段 schema

每条路线按如下 7 字段描述：

| 字段 | 含义 |
|---|---|
| **精神** | ≤ 20 字的编排哲学口号 |
| **定位** | 路线解决什么问题、服务哪类任务 |
| **适用场景** | 体量 × 类型 × 风险 的匹配画像（具体到可查表） |
| **调度序列** | 有序列表：`[skill/command/agent/hook/MCP]`，含并行/条件/强制门 |
| **切换条件** | 什么情况下要切出（升级 / 降级 / 转线） |
| **降级路径** | 当前路线失败时降到哪条（可能为"无"） |
| **风险点** | 该路线典型失败模式 + 对应缓解 |

### 1.2 调度序列写法约定

路线调度序列条目格式：`[来源]:[名字] (@[阶段]) [:可选标注]`

- **来源前缀**：
  - `SP:`（Superpowers skill）— 如 `SP:brainstorming`
  - `ECC:`（Everything Claude Code command / agent）— 如 `ECC:prp-plan` / `ECC:code-reviewer`
  - `gstack:`（gstack skill）— 如 `gstack:review`
  - `native:`（Claude Code 内建 tool / hook）— 如 `native:Edit` / `native:Stop-hook`
  - `harnessFlow:`（harnessFlow 自产 subagent / skill，**Phase 5-6 落地**）— 如 `harnessFlow:verifier`。本文档所有 `harnessFlow:*` 条目统一标注 `(Phase 5/6)` 后缀，提示读者这些组件尚未构建。
- **阶段标注**（可选）：`@clarify / @plan / @impl / @verify / @commit / @retro`
- **强制门标注**：`[gate]` 表示不通过则阻断后续步骤；`[optional]` 表示可跳过
- **并行标注**：`[parallel: A, B]` 表示 A、B 两步并发

示例：
```
ECC:prp-implement (@impl)
  → ECC:code-reviewer (@impl) [parallel]
  → harnessFlow:verifier (@verify) [gate]
  → ECC:prp-commit (@commit)
```

### 1.3 DAG vs LLM 路由边界

- **默认路线都是确定性 DAG**：调度序列的阶段顺序由状态机（Phase 4 `state-machine.md`）驱动，不走 LLM。
- **仅在"真分叉"时走 LLM 路由**：触发条件详见 `method3.md § 3.1` 二级路由。真分叉事件记入 `task-board.json.routing_events[]`，可审计。
- **路线本身不允许中途自动切换**：切换由主 skill 或 Supervisor 根据 § 8 切换规则显式发起，必须记入 task-board。

---

## § 2 路线 A — 零 PRP 直改提交（XS）

**精神**：最快路径，无中间仪式。

**定位**：单函数 / 单行改动 / typo / docstring 修复。启动成本低于 harnessFlow 自身开销时默认走 A。

**适用场景**：
- 体量：XS（< 50 行改动，单文件）
- 类型：纯代码 / 文档 / typo
- 风险：低（不触碰 API 边界、不可逆操作、对外行为不变）
- 反例：任何跨文件改动、任何后端路由改动、任何 schema 变更都不走 A

**调度序列**：
```
native:Read (@clarify)                       # 快速定位问题文件
native:Edit / native:Write (@impl)           # 直接改
native:Bash "pytest <focus>" (@verify) [gate]    # 小范围回归
ECC:prp-commit (@commit)                     # 或 gstack:ship（若配置了 ship 守则）
```

**切换条件**：
- 改动中途发现涉及多文件 / 改动 > 50 行 → **升级到 B**（重启澄清）
- 发现涉及不可逆动作（DB migration / OSS 覆盖写 / prod push）→ **强制升级到 C**，中止 A
- 改动涉及 UI 视觉细节（Vue 模板、样式）→ **转 D**

**降级路径**：无（A 已是最轻路线）。

**风险点**：
- 面积评估错：用户报"小改动"实际是跨模块 → Supervisor 6 干预中的"走偏" 监测
- 缺 DoD：A 路线 DoD 固定为 `pytest_exit_code == 0`（method3 § 6.1 无专用模板）→ 风险是漏 artifact-level 验证
- 无 code review：靠 `prp-commit` 内置预检 hook（`pre:bash:commit-quality`）兜底

**DoD（默认模板）**：
```
DoD = (pytest_exit_code(<focused_test>) == 0)
  AND (diff_lines_net < 50)
  AND (no_public_api_breaking_change())
```

---

## § 3 路线 B — 轻 PRP 快速交付（S-M）

**精神**：小仪式，快闭环。

**定位**：单模块小 feature / 中等 bug fix / 文档补全。适用于跨 3-10 个文件但不涉及架构决策的场景。

**适用场景**：
- 体量：S-M（50-500 行改动，1-10 文件）
- 类型：后端 feature（单模块）/ 纯代码 / 文档 / 小重构
- 风险：低-中（可回滚、非不可逆）

**调度序列**：
```
SP:brainstorming (@clarify) [≤ 2 轮]         # 轻澄清，不走完整 PRD
ECC:prp-plan (@plan)                         # 生成轻 plan（不做 prp-prd）
ECC:save-session (@plan) [checkpoint]        # 跨会话兜底
ECC:prp-implement (@impl)
  → ECC:code-reviewer (@impl) [parallel]
harnessFlow:verifier (@verify) [gate] (Phase 5/6)   # DoD eval 强制
ECC:prp-commit (@commit)
ECC:retro (@retro)                           # 轻量 retro（B 路线不强制 11 项全填）
```

**切换条件**：
- 分解 plan 时发现跨模块 / 涉及 agent graph → **升级到 C**
- 纯视觉改动 → **转 D**
- LangGraph 节点改造 → **转 E**
- code-reviewer 返回 critical → **纠偏 L1**（method3 § 5.3），重跑 prp-implement；连续 3 次 FAIL → **升级到 C**

**降级路径**：
- 澄清阶段发现改动 < 50 行且单文件 → **降 A**（B 未启动 plan 前允许降级；plan 产出后禁止降）

**风险点**：
- prp-plan 过轻导致实施中爆 scope：用 Supervisor "节奏失衡" 干预检测（method3 § 5.1④）
- verifier gate 不严：B 路线 DoD 必须包含 pytest + schema_valid 至少 2 条硬条件
- 跨会话目标漂移：save-session checkpoint 后续 resume 必过 goal-anchor 校验

**DoD（参考 method3 § 6.1 模板②）**：
```
DoD = (pytest_exit_code("<module>") == 0)
  AND (code_review_verdict == "PASS")
  AND (diff_lines_net < 500)
```

**DoD 三条件的 justification**（与方案 C 对比）：
- 仅要求 `pytest + code_review + diff_lines` 三条：S-M 任务不必含 uvicorn/curl/oss 等 artifact 级证据（无服务启动无外部依赖）；轻 PRP 不需要跨会话 checkpoint 验证
- 加第 3 条 `diff_lines_net < 500`：防 B 路线 scope 爆炸（超 500 行自动触发切换到 C，见 § 8.1 切换矩阵）
- 明确不够 → 切 C：若实施中发现需要 curl/oss artifact 验证（如引入新后端路由），由主 skill 主动升级到路线 C（见 § 8.1 矩阵 `B → C`）

---

## § 4 路线 C — 全 PRP 重验证（L-XL）

**精神**：端到端真完成，一步不少。对标方案 C 真完成升级版。

**定位**：harnessFlow **MVP 主路线**。L-XL 体量跨模块 feature / graph 改造 / 视频出片 / 任何触碰不可逆动作的任务。

**适用场景**：
- 体量：L-XL（500-5000 行 / 10+ 文件 / 可能跨会话）
- 类型：跨模块 feature / 视频出片 / 重大重构 / 不可逆操作
- 风险：中-高-不可逆（含 OSS 写入、DB migration、prod push 等）

**背景 — 为什么叫"C 真完成升级版"**：
旧版 method3 的方案 C = `brainstorm→prp-prd→prp-plan→prp-implement→prp-commit→prp-pr`，**没有强制 Verifier 门**、**没有 DoD 布尔表达式**、**没有 Supervisor 全程跟进**。aigcv2 P20 任务在旧 C 路线下翻车（无 mp4 / 无 OSS key / 没 uvicorn 起就报完成）。新 C 路线在同一命令序列基础上**强制插入**：`save-session` checkpoint、`harnessFlow:supervisor` 全程、`harnessFlow:verifier` 收口 gate、`ECC:santa-loop` 在 FAIL 时迭代、`ECC:retro` 强制 11 项。

**调度序列**（完整 15 步）：
```
1.  SP:brainstorming (@clarify) [3 轮]            # 深度澄清
2.  ECC:prp-prd (@clarify)                        # PRD 产出
3.  ECC:prp-plan (@plan)                          # 详细 plan
4.  ECC:save-session (@plan) [checkpoint-1]       # 计划阶段快照
5.  harnessFlow:supervisor (@startup) [sidecar] (Phase 5/6)   # 拉起旁观，PostToolUse hook 注册
6.  ECC:prp-implement (@impl)                     # 按 plan 实施
      → ECC:code-reviewer (@impl) [parallel, 中途检查]
      → Supervisor 6 干预持续监测 → INFO/WARN/BLOCK
7.  ECC:save-session (@impl) [checkpoint-2]       # 实施中快照（L 任务强制；XL 任务每阶段一次）
8.  ECC:retro (@impl) [mid-retro]                 # 阶段反思（仅 XL 强制）
9.  harnessFlow:verifier (@verify) [gate] (Phase 5/6)         # DoD 表达式 eval → PASS/FAIL
10. ECC:santa-loop (@verify) [仅 FAIL 时]         # 迭代修复 → 回 step 6 重跑（≤ 4 级 ladder）
11. ECC:prp-commit (@commit)                      # 过 quality-gate
12. ECC:prp-pr (@commit)                          # PR 创建
13. ECC:retro (@retro) [强制 11 项]                # 收口强制 retro
14. harnessFlow:failure-archive-writer (@retro) (Phase 5/6)   # 写回 failure-archive.jsonl（如有失败）
15. native:Stop-hook (@close) [bootstrap gate] (Phase 6)      # 兜底检测 verifier_report 是否存在
```

**Verifier 门位置说明**（对应 harnessFlow.md § 5.3 桥接 ⑤）：step 9 是主 skill 内部状态转换 gate（"即将进入收口状态"前同步调 Verifier）；step 15 是 Stop hook 兜底（若主 skill 绕过 gate，hook 检测 `task-board.verifier_report` 未写入则 force escalate）。**两层防线缺一不可**。

**切换条件**：
- Verifier 连续 FAIL ≥ 3 次且 santa-loop 未收敛 → **升级 L3 纠偏**（method3 § 5.3），暂停等用户决策
- Supervisor 报 **DRIFT_CRITICAL**（目标走偏）→ 暂停 + 等用户决策切目标 / 纠偏
- Supervisor 报 **IRREVERSIBLE_HALT**（不可逆前置缺失）→ 强制拦截
- 任务实际体量重估为 M → **降级到 C-lite**（见降级路径）
- 发现是纯 agent graph 改造 → **转 E**（graph 专线）

**降级路径**：
- **C-lite**：省 step 2（prp-prd）+ step 8（mid-retro）+ step 10（santa-loop 封顶 2 轮）。仅在任务启动后**发现体量重估为 M**且 Supervisor 确认无不可逆风险时允许。明确标记 `route_id = C-lite`。
- **禁止回退到 B / A**：C 路线已启动即不许回退到更轻路线；要重开任务才能换。

**风险点**：
- **主 skill prompt 过长**：路线 C 调度序列最长，但 prompt 中只存 skill 名；具体规则查 `state-machine.md` / `routing-matrix.md`（Phase 4 产出）。
- **跨会话目标漂移**：step 4、7 强制 save-session + goal-anchor 不可变（method3 § 5.2 DRIFT_CRITICAL 兜底）。
- **假完成**：step 9 DoD eval + step 15 Stop hook 兜底 + trap catalog（harnessFlow.md § 5.3 桥接 ②）三层防。
- **santa-loop 无界**：step 10 封顶 4 级 ladder（method3 § 5.3），超时强制 escalate，不允许无限 retry。

**DoD（参考 method3 § 6.1 模板①或②）**：按任务类型选模板。视频出片任务必含 `(mp4 exists) AND (ffprobe_duration > 0) AND (oss_head.status_code == 200) AND (playback_check) AND (retro_exists)`。

**P20 事故修复映射**：
| P20 原方案 C 缺的 | 新 C 路线在哪一步补上 |
|---|---|
| 没起 uvicorn 就报完成 | step 9 Verifier DoD 模板②含 `uvicorn_started`（method3 § 6.1） |
| 没 POST /produce 验证（接口未 smoke 跑） | step 9 Verifier DoD 模板②含 `curl_status("POST /produce") == 200` + `schema_valid(curl_json(...), "schemas/produce_response.json")`（method3 § 6.2 模板②） |
| 没校验 mp4 存在 | step 9 Verifier DoD 模板①含 `file_exists("media/p20.mp4")` |
| 没查 OSS key | step 9 Verifier DoD 模板①含 `oss_head.status_code == 200` |
| 没 playback | step 9 Verifier DoD 模板①含 `playback_check` |
| 没结构化 retro | step 13 强制 `ECC:retro` 11 项 |
| 假完成后无记录 | step 14 `failure-archive-writer` 写失败条目 |
| 绕过 Verifier 直接 commit | step 15 Stop hook 兜底检测 |

---

## § 5 路线 D — UI 视觉专线（S-M UI）

**精神**：像素级验证 + screenshot 做硬证据。

**定位**：Vue 页面 / Vue Flow 视觉优化 / 组件视觉调整 / UI bug 修复。视觉任务传统上最容易假完成（"我觉得好看了"），必须 screenshot + browser 导航做硬证据。

**适用场景**：
- 体量：S-M
- 类型：UI（Vue / Element Plus / Vue Flow / 组件视觉）
- 风险：低-中（一般不触及 backend）

**调度序列**：
```
SP:brainstorming (@clarify) [1-2 轮]              # 视觉目标 + 交互预期
ECC:gan-design (@plan)                            # 视觉设计（gan-design 命令对应 frontend-design 意图）
native:Edit (@impl)                               # 改 .vue / .ts / .css
gstack:browse (@verify) [parallel]                # 浏览器导航抓 DOM
gstack:design-review (@verify)                    # 视觉审查
native:Bash playwright-screenshot (@verify) [gate]     # screenshot 硬证据（playwright CLI 封装）
harnessFlow:verifier (@verify) [gate] (Phase 5/6) # DoD eval（method3 § 6.1 模板③）
ECC:prp-commit (@commit)
ECC:retro (@retro) [轻量]
```

**切换条件**：
- 视觉改动涉及后端 API / schema 变更 → **升级到 C**（不是 B，因为 UI+后端组合风险已非 M）
- 纯 CSS 微调 < 10 行 → **降级到 A**（启动澄清阶段可降；impl 后禁降）
- 涉及复杂 state 管理 / Pinia store 改造 → **转 B/C**（依体量）

**降级路径**：
- D-mini：省 `SP:brainstorming` + `gan-design`，直接 Edit + browse + screenshot（视觉微调场景）。

**风险点**：
- **screenshot 作假**：Verifier 必须用 `screenshot_has_content()` 原语（method3 § 6.1 bootstrap 表）确认 screenshot 非空非纯色
- **浏览器 cache 污染**：`gstack:browse` 启动强制 cache-bust
- **异步渲染漏验**：screenshot 前强制等 `playwright_wait_for` 或 3s 延迟

**DoD（method3 § 6.1 模板③）**：
```
DoD = (vite_started("localhost:5173"))
  AND (playwright_nav("http://localhost:5173/<new-page>").status == "ok")
  AND (screenshot_has_content("artifacts/<page>.png"))
  AND (playwright_exit_code("e2e/<page>.spec.ts") == 0)
  AND (type_check_exit_code == 0)
```

---

## § 6 路线 E — agent graph 专线（L-XL graph）

**精神**：节点隔离测试 + 图级回归。

**定位**：LangGraph subgraph 新增 / 节点改造 / agent 编排调整。aigcv2 视频生产 pipeline、`supervisor_graph.py`、`video_graph_v2.py` 等场景。

**适用场景**：
- 体量：L-XL
- 类型：agent graph（LangGraph node / subgraph / orchestration）
- 风险：中-高（graph 改错会破坏整个 pipeline，但通常非不可逆）

**调度序列**：
```
SP:brainstorming (@clarify) [2-3 轮]              # graph 目标 + 输入/输出 schema
native:Read (@plan)                                # 读取现有 graph 实现
native:Write (@plan) "graph_diff.md"              # 产出 before/after graph diff 文档（ASCII 流程 + 节点 schema diff）
ECC:prp-plan (@plan)                              # 带节点清单的 plan
ECC:save-session (@plan) [checkpoint]
ECC:prp-implement (@impl)                         # 节点级 TDD（每节点独立单测）
  → ECC:tdd-guide (@impl) [agent]
ECC:eval (@verify) / ECC:gan-evaluator (@verify)  # 节点输出回归
harnessFlow:verifier (@verify) [gate] (Phase 5/6) # DoD eval（含 graph 级端到端）
ECC:prp-commit (@commit)
ECC:prp-pr (@commit)
ECC:retro (@retro)
```

**切换条件**：
- graph 稳定，只改节点内部实现 → **转 C**（agent graph 精神不再，走普通跨模块 feature）
- 超大重构跨多个 graph → **升级到 C-重**（分阶段 XXL+ 模式）
- 涉及真出片 / OSS 写入 → **附加 C 路线的 Verifier DoD 模板①**（E 的 DoD 加上视频模板）

**降级路径**：
- E-lite：单节点改造且不涉及 graph topology 变更 → 可省 `手工画图` + `ECC:eval`，走 B 变体（但保留节点级 TDD）。

**风险点**：
- **节点输出 schema 漂移**：`ECC:eval` 必须回归所有下游节点的 input schema 兼容性
- **graph 环路**：节点改造引入环路 → Supervisor 顺序错检测
- **共享 state 污染**：TypedDict state 字段新增但未迁移历史数据 → prp-plan 必列 migration step

**DoD（E 路线专用）**：
```
DoD = (pytest_exit_code("tests/test_graph_<name>.py") == 0)
  AND (pytest_exit_code("tests/test_<node>_unit.py") == 0)
  AND (eval_regression_delta("<downstream_nodes>") < 0.05)
  AND (graph_compile_success("app.graphs.<graph_name>") == True)
  AND (code_review_verdict == "PASS")
```

---

## § 7 路线 F — 研究方案探索专线

**精神**：多轮 brainstorm + 外部资料 + 决策 log，不写代码。

**定位**：选型 / 架构决策前置 / 新技术评估 / 方案对比。产出是**决策文档**（不是代码）。

**适用场景**：
- 体量：任意（但通常 M-L）
- 类型：研究 / 调研
- 风险：低（不触及代码仓库，除非最后转 B/C 实施）

**调度序列**：
```
SP:brainstorming (@clarify) [多轮]                # 问题定义 + 约束条件
native:Agent (@research) [subagent_type=Explore]  # 代码库调研（现状分析）
native:WebSearch / native:WebFetch (@research)    # 外部资料
ECC:docs-lookup (@research) [agent]               # 库文档查询（context7 MCP）
gstack:investigate (@research)                    # 调研汇总
native:Write (@decision)                          # 决策 log 文档（.md）
ECC:retro (@retro) [决策型 retro]
```

**切换条件**：
- 决策敲定 → **转 B/C 实施**（F 产出的决策 log 作为下游路线的 Mandatory Reading）
- 发现需代码实验验证 → **转 B 做 POC**，POC 完再回 F 完善决策

**降级路径**：无（F 本身是最轻的研究模式；不需进一步降级）。

**风险点**：
- **决策漂移**：决策 log 不持久化 → 必须 Write 成 .md 进仓库，或进 memory `project_*.md`
- **外部资料过时**：WebSearch 结果带日期戳，决策 log 注明 Retrieved 时间
- **不写代码但过度澄清**：`SP:brainstorming` 封顶 5 轮，超出转 B 做 POC

**DoD（F 路线专用）**：
```
DoD = (file_exists("<decision_log>.md"))
  AND (wc_lines("<decision_log>.md") >= 200)
  AND (grep_count("^## 选项", "<decision_log>.md") >= 2)
  AND (grep_count("^## 决策", "<decision_log>.md") == 1)
  AND (retro_exists("harnessFlow /retros/<task_id>.md"))
```

---

## § 8 路线切换 / 降级规则

### 8.1 切换触发矩阵

| 当前路线 | 触发条件 | 建议切换目标 | 切换时机 | 何处记录 |
|---|---|---|---|---|
| A | 改动扩大 > 50 行 / 跨文件 | B | impl 阶段任何时刻 | task-board.route_changes[] |
| A | 发现不可逆动作 | C | 立即 | task-board + Supervisor BLOCK |
| A | UI 视觉改动 | D | clarify 阶段 | task-board |
| B | 跨模块 / agent graph | C 或 E | plan 阶段（晚于 impl 禁切） | task-board + routing_events |
| B | 纯视觉改动 / 只改 .vue 和样式 | D | clarify 阶段（impl 后禁切） | task-board |
| B | code-reviewer 连续 3 次 FAIL | C | verify 阶段 | task-board + L3 纠偏 |
| C | Verifier 连续 FAIL ≥ 3 且 santa-loop 未收敛 | L3 纠偏（暂停） | verify 阶段 | task-board + Supervisor BLOCK |
| C | Supervisor DRIFT_CRITICAL | 暂停等用户切目标 | 任何阶段 | task-board + red_line |
| C | 发现是纯 graph 改造 | E | plan 阶段 | task-board |
| D | 涉及后端 schema 变更 | C | 任何阶段 | task-board |
| E | graph topology 稳定，改节点内部 | C | plan 阶段 | task-board |
| F | 决策敲定 | B / C | 任意，F 不 impl | 决策 log 明确下一步路线 |

### 8.2 降级路径

| 原路线 | 降级目标 | 允许条件 |
|---|---|---|
| C | C-lite | 体量重估为 M 且无不可逆风险 + 已 `save-session` checkpoint 后（Supervisor 确认） |
| D | D-mini | 视觉微调 / 单文件 CSS 改动 |
| E | E-lite | 单节点改造，无 graph topology 变更 |
| A / B / F | 无降级路径 | A 已是最轻；B/F 降就回到 A 模式，不作为正式降级 |

降级必须满足**三条件**：
1. 原路线已启动但未进 `@verify` 阶段（已过 gate 禁止降）
2. Supervisor 明确 **非** IRREVERSIBLE_HALT / DRIFT_CRITICAL 状态
3. task-board 记录 `route_id` 变更 + reason + 审批 agent（主 skill 或 Supervisor）

### 8.3 禁止回退

- **回退 = 从重路线切到轻路线**（如 C → A）。除 § 8.2 降级白名单外，一律禁止。
- 若确实体量重估为 XS-S，需**关闭当前任务 + 重开新任务**（`task_id` 变更），不允许原地回退。
- Why：中途回退会丢失已产出的澄清 / plan / checkpoint，违反真完成「强证据收口」原则。

---

## § 9 扩展位（G+ 预留）

### 9.1 新路线引入流程

1. `failure-archive.jsonl` 累积同类成功组合 ≥ 3 次（MVP 默认，见 `routing-matrix.md` § 5）
2. 用户或主 skill retro 发起新路线提案 → 写入 `harnessFlow /proposals/route-G-xxx.md`
3. 提案含 7 字段（§ 1.1）+ 现有路线无法覆盖的反例
4. 走 PR 审批合入 flow-catalog.md 新章节 + bump 版本号（v1.0 → v1.1）
5. `routing-matrix.md` § 2 主表同步更新相关 cell

### 9.2 版本化与 PR 审批

- flow-catalog 改动 = routing-matrix 可能改动 = **两份文档必须同版本号 bump**
- 版本号语义：major（新路线 / 删路线）/ minor（路线字段调整）/ patch（typo / 文字精修）
- 每次 bump 附 `CHANGELOG.md` entry，说明动机 + 反例 + 审批人
- 进化引擎（harnessFlow.md § 3.3）每 20 次任务触发一次权重 review，可能建议 bump

---

*本文档定义 6 条编排路线的完整调度序列。规则决策锚点见 method3.md § 4；三维查表见 routing-matrix.md；状态机流转见 state-machine.md（Phase 4 产出）；主 skill 如何按本文档序列调度见 Phase 5 产出。*

*— v1.0 end —*
