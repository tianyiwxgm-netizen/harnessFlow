# method3 · harnessFlow 方法论

> Claude Code 总编排器 harnessFlow 的方法论根文档 — 把「真完成」设为第一原则，把旧速查表升级为显式判断逻辑。

**版本**: v1.0 — 2026-04-16 — harnessFlow MVP
**状态**: Draft（PRD Phase 1 产出）
**读者**: harnessFlow 主 skill（分诊/路由/监督/收口规则源头）/ Supervisor 与 Verifier subagent（红线与 DoD 规则引用）/ 用户（理解 harnessFlow 为什么这么设计）

---

## § 0 前言

### 0.1 这是什么

本文档是 `harnessFlow` 总编排器的**规则根源**。harnessFlow 主 skill、Supervisor agent、Verifier agent、路由矩阵、交付清单所有判断逻辑都以 method3 的章节为出处。如果某条规则在 method3 里找不到，它就不属于 harnessFlow 规则集。

### 0.2 为什么重构

旧版 `method3.md` 是一份 35 行的命令速查表（表一「体量 → 命令组合」、表二「具体任务 → 路线」、3 条经验硬规则）。它能回答"用什么"，但回答不了"什么叫做完了""中途是不是走偏了""怎么避免上次的坑"。

**真实触发事件（2026-04-16）**：aigcv2 P20 任务照旧版 method3 的「方案 C」执行，最后报完成时——没起 uvicorn、没 POST /produce、没校验 mp4 时长、没拿到 OSS key。用户用「做菜放锅里就说好了/水泥到了问要不要砌墙」的类比反馈："先手工 e2e 验一次再说"。旧 method3 没有任何机制能拦住这次假完成。这是用户启动 harnessFlow 项目的直接动因。

所以这次重构不是增量补丁，是**范式切换**：从"推荐命令"升级为"判断规则 + 监督规则 + 验证规则"，显式给出每条规则的「Why + How to apply + 反例」三段。

### 0.3 与 harnessFlow 其他文档的关系

method3 是方法论根，其他文档是细节载体：

| 姐妹文档 | 它装什么 | method3 怎么引用 |
|---|---|---|
| `harness-flow.prd.md` | PRD（目标 / 成功指标 / 开放问题）| § 全文规则对齐 PRD Decisions Log |
| `harnessFlow.md`（Phase 2 产出）| 顶层架构、三引擎、Supervisor、生态边界 | § 5/§ 6/§ 7 细节下挂此文档 |
| `flow-catalog.md`（Phase 3 产出）| A~F 编排路线详细设计 | § 4 只写路线精神，详情详见此文档 |
| `routing-matrix.md`（Phase 3 产出）| 任务类型 × 体量 → 路线推荐矩阵 | § 2 § 3 只写判断维度与原则，矩阵详见此文档 |
| `state-machine.md`（Phase 4 产出）| 任务流转状态机 | § 5 打断/恢复的状态流转详见此文档 |
| `task-board-template.md`（Phase 4 产出）| task-board.json 字段模板 | § 5.4 信号源记录去向 |
| `delivery-checklist.md`（Phase 4 产出）| 强制 DoD 验证清单 | § 6 交付收口引用此清单 |

### 0.4 旧版保留什么 / 丢什么

- **保留**：旧版 3 条经验规则的精神（小任务别上重流程 / L 以上要强 artifact / 视觉用 gan-design）— 全部吸纳进 § 2.4 决策矩阵、§ 6 验证规则、§ 4 路线规则，不丢弃。
- **丢弃**：旧版的表一/表二作为最终速查表的形式 — 那是命令的静态映射，在 harnessFlow 里"用什么"应该由主 skill 按体量 × 类型 × 风险实时算出来，而不是查表。旧表的承接者是 `routing-matrix.md`（Phase 3 产出），带版本号 + 可审计权重。

---

## § 1 第一原则

三条原则的优先级严格如下，冲突时上位压下位：**真完成 > 客人点菜 > 不重复造轮**。

### 1.1 真完成（Real Completion）— 根中之根

**定义**：完成 = **用户可直接消费的 artifact**，不是任何中间状态。

餐厅类比：做菜 = 端到客人面前能吃。不是"放锅里了"、不是"切好了还问要不要炒"、不是"调味料备齐"。
建筑类比：盖房 = 交付可入住的房子。不是"水泥到了问要不要砌墙"、不是"框架封顶了"。

映射到 5 类 Claude Code 常见任务，「真完成」各自长什么样：

| 任务类型 | 真完成的证据 | 假完成反例 |
|---|---|---|
| 视频出片（aigcv2 P20） | 本地/OSS 上存在 mp4 文件 + 时长 > 0 + OSS key 可访问 + 可播 | "Phase 4 通过了"、"pipeline 跑到 render 节点了"、"代码 push 了" |
| 后端 feature（aigc） | 启动 uvicorn + curl endpoint 200 + 响应 schema 合法 + 单测全过 | "build green"、"unit test 过了"、"迁移 SQL 写完了" |
| UI feature（Vue） | npm run dev 起服务 + 浏览器可导航到新页面 + screenshot 有内容 + Playwright e2e PASS | "npm run build 成功"、"type-check 过了"、"组件 render 了" |
| 文档 | 文件存在 + 行数达标 + 目标读者 5 分钟读懂 + 交叉引用无死链 | "Markdown 语法正确"、"outline 写完了" |
| 重构 | 重构后全测试绿 + 性能基线不退化 + 关键路径 diff review 通过 | "代码改完了"、"tests 通过了（未跑性能）" |

**两条铁律**：

1. **强证据收口**：宣告完成必须有可验证 artifact / 可运行进程 / 可消费输出。LLM 自报的 "done" / "TERMINATE" / "Phase X 通过" 一律不算证据。
2. **中途零废问题**：用户给完目标后，所有"标准下一步"由 harness 自动完成。打断用户必须满足 § 5.2 三红线之一，其他情况一律自处理。

**Why**：不这么写，假完成率 ≈ 30%（方案 C P20 就是样本）。LLM 高置信时特别爱「汇报成功」，因为它没有物理世界的消费端反馈闭环。真完成强制把回路从 LLM 延伸到用户可消费的 artifact，补上反馈缺口。

**How to apply（五步自检）**：
- ① 我手上有 artifact 路径 / 可运行命令 / 可访问 URL 贴给用户吗？没有 → 未完成
- ② 这个 artifact 是不是我这轮刚产出的（不是历史遗留）？不是 → 未完成
- ③ 对应的 DoD 布尔表达式（§ 6.1）eval 结果是 True 吗？不是 → 未完成
- ④ 独立 Verifier（§ 6.2）重跑 DoD 命令的输出是 PASS 吗？不是 → 未完成
- ⑤ 三段证据链（§ 6.3）齐全吗？缺任一 → 未完成

五步任何一步不过，禁止使用"完成"、"done"、"success"、"PASS"等词汇汇报。

### 1.2 客人点菜（Restaurant Model）— 中途零废问题

**定义**：用户 = 客人，harnessFlow = 餐厅。客人点菜后，餐厅自动完成所有"标准下一步"（切菜 / 开火 / 调味 / 出锅 / 摆盘 / 上桌），中途不应该被问「要不要开火」「要不要盐」「要不要加香菜」等标准化问题。

**打断用户的合法理由只有 3 个（§ 5.2 红线）**：
- DRIFT_CRITICAL — 任务方向偏离原意（如用户要视频，系统在做图集）
- DOD_GAP_ALERT — 关键 DoD 项被跳过或不可达（如视频任务 mp4 产出不了）
- IRREVERSIBLE_HALT — 即将做不可逆动作但前置缺失（如 push 到 prod 但没跑 e2e）

**反例（必拒）**：
- ❌ "水泥到了，要不要砌墙？"（标准下一步）
- ❌ "菜切好了，要不要开火炒？"（标准下一步）
- ❌ "素材采完了，要不要评分？"（标准下一步，由路线决定）
- ❌ "代码改完了，要不要跑测试？"（真完成强制跑，无需问）
- ❌ "测试过了，要不要 commit？"（不是不可逆动作，由流程决定）

**Why**：打断成本非常高——不光打破用户心流，还让用户对 harness 的信任崩塌（客人去了餐厅点完菜还要全程指挥，不如自己做）。且大量"标准下一步"型问题表示 harness 不知道自己在哪步、下步是什么——这是路线规划失败的信号（见 § 4）。

**How to apply**：
- 每次要打断用户前问三问：① 这是不是标准下一步？② 如果是，我为什么不知道怎么选？③ 如果不是标准下一步，我是不是踩了 § 5.2 三红线之一？
- 前两问答"是/不知道" → 禁止打断，回到路线规划补足
- 第三问答"是" → 允许打断，按 § 5.2 结构化输出

### 1.3 不重复造轮(No-Reinvent）— 只编排

**定义**：harnessFlow 不新造任何底层 skill。所有执行能力来自 SP（Superpowers）/ ECC（Everything Claude Code）/ gstack 三套既有生态 + Claude Code 原生能力（subagent / hooks / skill / MCP / memory）。

**允许自建的 5 处桥接**（最小化空白）：
1. routing-matrix 版本化（权重数据驱动的路由器）
2. 假完成 trap catalog（结构化 jsonl 的失败模式库）
3. task-level state machine（路线启动 → 阶段 → 偏航 → 收口的状态流转）
4. 路由决策引擎（把 § 2.4 决策矩阵编码为可执行规则）
5. `pre:task:complete` hook（强制拦「宣告完成」动作走 Verifier）

**反例（必拒）**：
- ❌ 自己实现 e2e runner（ECC 已有 `e2e-runner`）
- ❌ 自己实现 verification（SP 已有 `verification-before-completion` / ECC 已有 `verification-loop`）
- ❌ 自己实现 save-session（ECC 已有 `save-session/resume-session`）
- ❌ 自己实现 retro（ECC 已有 `retro` / `learn` / `continuous-learning-v2`）
- ❌ 自己实现 brainstorming（SP 已有 `brainstorming`）

**Why**：SP + ECC + gstack 三套库共 206 个能力（SP 14 + ECC 183 + gstack 9），覆盖 ~60% 真完成 / 纠偏 / 进化 / 编排需求。重复造轮违反用户硬约束，也制造维护负担。harness 的价值在「调度的编排 IQ」，不在「能力库的大小」。

**How to apply**：
- 每次主 skill 要"新建"一个动作前，先查 routing-matrix.md 的能力映射。找不到再查 SP/ECC/gstack 原始索引。仍找不到才允许自建桥接，且必须落在上述 5 处空白内。
- 自建桥接 ≠ 自建 skill。桥接只做「绑定、路由、转换、持久化」这类编排职责，不做领域执行。

---

## § 2 任务分诊规则

分诊 = 主 skill 在用户澄清后对任务做 **体量 × 类型 × 风险** 三维判定，为下游路由/路线/监督强度/验证强度给出规则输入。详细推荐矩阵见 `routing-matrix.md`（Phase 3 产出）。

### 2.1 体量判定（6 级）

| 级别 | 特征 | 典型耗时 | 典型文件数 | 警告信号 |
|---|---|---|---|---|
| XS | 一句话改动 / 单函数 / 注释 | < 15 min | 1 | 任务描述能一句话写完且无歧义 |
| S | 单模块小 feature / 单文件重构 | 15 min - 1 h | 1-3 | 涉及 < 1 个目录 |
| M | 单模块中等 feature / 多文件小改 | 1-3 h | 3-8 | 涉及 1-2 个目录，可能要加测试 |
| L | 跨模块 feature / 架构调整局部 | 3-8 h | 8-20 | 需要 plan，可能分多次 commit |
| XL | 跨多模块重构 / 新子系统 | 1-3 天 | 20-50 | 必须 PRD + plan，需要 Supervisor 持续在场 |
| XXL+ | 全链改造 / 新产品模块 | > 3 天 | > 50 | 必须 PRD + plan + 阶段性 gate + 跨会话 |

**体量判定口诀**：看描述长度 + 看文件数估计 + 看测试/验证工作量。三者任一超上限就升一级。升级优于降级（保守对待）。

### 2.2 类型判定（7 类）

| 类型 | 识别关键词 | 典型任务 | 风险点 |
|---|---|---|---|
| 纯代码改动 | "改 bug / 修 / tweak / 小优化" | 改 util 函数 / 修 import / 调日志 | 低 — 但要防误改公共接口 |
| UI 视觉 | "UI / 页面 / 组件 / 视觉 / 截图" | Vue 页面 / React 组件 / 样式 | 视觉验证强依赖 screenshot |
| 多模块 feature | "前后端联调 / 多文件新能力 / pipeline 加 step" | LangGraph 新节点 / API + Vue 成对 | 接口契约易漂移 |
| 系统架构 | "重构 / 分层 / 依赖整理 / 架构" | 拆服务 / 引中间层 / 迁模型 | 影响面大，需回归 |
| agent graph / pipeline | "LangGraph / graph / 节点 / 编排" | aigcv2 subgraph / 多 agent | 状态字段易漂移，end-to-end 难验 |
| 高验证 / 高风险 | "真实数据 / 真出片 / 生产 / 不可逆" | P20 真出片 / prod 迁移 / 发布 | 必须强 DoD + 强 Supervisor |
| 研究 / 方案探索 | "调研 / 比较 / 选型 / brainstorm" | 选哪个 LLM / 架构选型 | 产出是文档而非代码，DoD 偏文档 |

同一任务可能是多类型的组合（如"aigcv2 加新素材源"= 多模块 feature + agent graph + 高验证）。组合类型时**取并集，按最严类型定监督/验证强度**。

### 2.3 风险判定（4 级）

| 级别 | 例子 | 必须的 gate |
|---|---|---|
| 低 | 改内部函数 / 加注释 / 小 UI 微调 | static check + 单测 |
| 中 | 加新 API / 改内部接口 / 非关键重构 | static + 单测 + e2e 关键路径 |
| 高 | 改公共接口 / 改数据迁移 / 影响上游 | static + 单测 + e2e + code-review + 回归 |
| 不可逆 | 生产发布 / OSS 写入 / 删数据 / push prod | 上述全量 + 强 Supervisor + HITL 确认 |

**风险是体量 × 影响面 × 可撤销性的综合判定**，不直接等同于体量。小体量也可能高风险（如删数据库表的一行 SQL）。

### 2.4 三维组合 → 决策

下游决策是「体量 × 类型 × 风险」三维的综合输出。给 5 个典型组合示例：

**例 1**: `M 级 × UI 视觉 × 低风险`
- 推荐路线：轻路线（SP `frontend-design` + `screenshot-verify`，不启全 PRP 链）
- 监督：Supervisor 只开"漏菜" 1 类
- DoD：screenshot + e2e 关键路径
- 打断容忍：≤0 次（标准 UI 任务不该有意外分叉）

**例 2**: `L 级 × 多模块 feature × 中风险`（如 aigc 后端加素材源）
- 推荐路线：中路线（brainstorm → prp-plan → prp-implement + ECC `e2e-runner`）
- 监督：Supervisor 开"漏菜 + 走偏 + 忘开火" 3 类
- DoD：`(api returns 200) AND (e2e PASS) AND (pytest PASS) AND (code-review PASS)`
- 打断容忍：≤1 次（允许 1 次真分叉）

**例 3**: `XL 级 × agent graph + 高验证 × 不可逆`（如 P20 真出片、aigcv2 视频生产 pipeline 改造）
- 推荐路线：重路线（方案 C 的正确版 — 全 PRP + e2e + 三段证据 + 强 Supervisor）
- 监督：Supervisor 开 6 类干预全量 + PostToolUse hook 准实时
- DoD：见 § 6.1 模板①（视频出片任务完整版，不在此重复）
- 打断容忍：0 次废问题；真分叉时可打断

**例 4**: `XS 级 × 纯代码 × 低风险`
- 推荐路线：零路线（直接改 + 单测 + `/commit`，不走 PRP）
- 监督：不启 Supervisor
- DoD：`(pytest exit_code == 0)`
- 打断容忍：0 次

**例 5**: `XXL+ 级 × 系统架构 × 不可逆`（如全链重构 aigcv2 pipeline）
- 推荐路线：超重路线（PRD → 多 plan → 多次 prp-implement + /santa-loop 迭代 + 跨会话 resume + 阶段 gate）
- 监督：Supervisor 必开全量 + 跨会话 goal-anchor 持久化
- DoD：按阶段拆，每阶段独立 DoD + 整体收口 DoD
- 打断容忍：每阶段真分叉 ≤1 次

**继承旧版 3 条硬规则的去向**：
- 旧「XS-S 别上重流程」→ 例 1 + 例 4 显式
- 旧「L 以上不拿 artifact 会吃亏」→ 所有 L+ 例子 DoD 强制包含 artifact 类条件
- 旧「视觉用 gan-design」→ 例 1 及 § 4 路线规则

---

## § 3 路由规则

路由 = 从「体量 × 类型 × 风险」三维决策到**具体 skill / command / agent / hook / MCP 组合**的映射。详细矩阵见 `routing-matrix.md`（Phase 3 产出）。本节只定原则。

### 3.1 两级路由

**一级：确定性 DAG（默认）**
- 主 skill 按预定义状态图走：澄清 → 分诊 → 路由 → 执行 → 监督 → 验证 → 收口
- 阶段间转换由状态机驱动（`state-machine.md` Phase 4 产出），不走 LLM

**二级：LLM 路由（仅真分叉）**
- 触发条件：三维决策命中多条规则且权重接近 / 矩阵里无明确推荐 / Supervisor 报 DRIFT_CRITICAL 要切路线
- 每次 LLM 路由必须在 task-board 里记录 `{trigger, candidates, scores, chosen, reason}` 五字段，可审计
- LLM 路由的输出必须经一次 schema 校验（返回的候选路线必须在 flow-catalog 注册过），不允许 LLM 生成未注册路线

### 3.2 路由不是选择题而是规则题

主 skill 路由时**不要用"我觉得 X 比较好"这种 LLM 自由判断**，要用如下规则链：
1. 读 `routing-matrix.md` 的体量 × 类型 × 风险索引 → 得候选路线集
2. 按当前 `failure-archive` 权重排序（失败过的降权）
3. 取 top-2 在**任务启动澄清阶段一次性呈现**用户 + 推荐 top-1
4. 用户接受 top-1 → 零分叉；用户选 top-2 → 零分叉；用户要第三条路 → 真分叉进 LLM 路由

**澄清阶段豁免声明**：初始路线选择属于 § 1.2「客人点菜」原则中"任务启动阶段的必要澄清"，不算中途废问题。豁免仅限任务启动时一次；任务执行中主 skill 若要切路线，走 § 5.3 4 级 ladder + § 5.2 DRIFT_CRITICAL 红线，不得再次发"路线选择题"问用户。

### 3.3 反模式

- ❌ 全 LLM 黑盒路由（参考 CrewAI Hierarchical Manager）— 不可审计、失败定位困难
- ❌ 完全静态 SOP（参考 MetaGPT）— 灵活性差、新分支要改代码
- ❌ 路由决策不记 reason — 进化引擎无从学习
- ❌ 路由结果不校验 — LLM 捏造不存在的路线名

---

## § 4 编排路线规则

路线（Flow）= 一组 skill / command / agent 的**组合编排策略**。A~F 是精神代号，具体调度顺序见 `flow-catalog.md`（Phase 3 产出）。本节只定精神 + 切换/降级规则。

### 4.1 六条路线精神

| 代号 | 精神（≤ 15 字） | 适用体量 | 核心编排 |
|---|---|---|---|
| A | 零 PRP 直改提交 | XS | 直接改 + 单测 + `/commit` |
| B | 轻 PRP 快速交付 | S-M | brainstorm + prp-implement + qa |
| C | 全 PRP 重验证 | L-XL | brainstorm → prp-prd → prp-plan → prp-implement → santa-loop → prp-commit → prp-pr（真完成版 — 必过 Verifier） |
| D | UI 视觉专线 | S-M UI | frontend-design + screenshot-verify + browser-qa |
| E | agent graph 专线 | L-XL graph | graph-design + agent-eval + verification-loop |
| F | 研究方案探索专线 | 任意 | brainstorming + research-agent + decision-log |

**路线 C 是 MVP 重点**。方案 C 是旧版 method3 对 L-XL 任务的推荐路线，在 P20 任务上因缺真完成 gate 翻车。harnessFlow 的 C 路线是「同一套命令序列 + 强制 Verifier + 强 Supervisor + 结构化 retro」的升级版，不是新造。

### 4.2 何时切换路线

- L3 大偏航（§ 5.3）触发切路线：Verifier 反复 FAIL 且 DoD 子契约不可达、Supervisor 报 DRIFT_CRITICAL、当前路线的前置条件全数失败
- 切换动作：暂停 → 写 task-board `route_switch` 事件 → 主 skill 给用户报「原路线 X 不可行，建议切 Y，理由 Z」→ 用户确认或否决
- 禁止隐式切换：主 skill 不能"自己偷偷走到别的路线"，必须显式打断（因为切路线 = 默认打断用户）

### 4.3 何时降级（reduce scope）

- L3 大偏航但不切路线，改"缩小范围"：减少 DoD 条目（只保 Must）、去除 Should 级验证、把 XXL+ 拆成多个 XL 阶段
- 降级必须触发一次 HITL（用户知情同意），因为降级改变了"真完成"的定义
- 降级动作记 task-board + 进 failure-archive（以便进化引擎下次预防）

---

## § 5 监督推进规则

Supervisor agent 是 harnessFlow 架构的**第 4 块**（不属于三引擎），定位 = 用户的眼睛+大脑，全程在线，只读，不执行。详细 prompt 与实现细节见 `harnessFlow.md`（Phase 2 产出）+ Phase 6 subagent prompt。

### 5.1 Supervisor 6 类干预

每类干预含【检测条件】【典型例子】【严重度 INFO/WARN/BLOCK】【动作】。

**① 忘开火**（关键前置动作缺失）
- 检测：PostToolUse 时对比 "已执行动作" vs "当前阶段必做清单"
- 例：准备 PR 前没跑 lint / 写视频前没校验 prompt / commit 前没 git status
- 严重度：BLOCK（红线 DOD_GAP_ALERT）
- 动作：打断主 skill、告知缺哪步、要求补做

**② 漏菜**（DoD 子契约跳过）
- 检测：对比 DoD 表达式各子条件 vs 已验证条件
- 例：DoD 5 项只做了 3 项 / mp4 生成了但没验 OSS key
- 严重度：BLOCK（红线 DOD_GAP_ALERT）
- 动作：列出漏的 DoD 项、要求补

**③ 走偏**（方向漂移）
- 检测：对比当前动作 vs goal-anchor
- 例：用户要视频做成图集 / 要后端 API 做成前端组件
- 严重度：BLOCK（红线 DRIFT_CRITICAL）
- 动作：暂停、报告偏航、等用户决策是纠偏还是改目标

**④ 节奏失衡**（时间/成本接近预算）
- 检测：time budget / token budget / cost budget watcher
- 例：XL 任务到 80% 预算但才做完 40%
- 严重度：WARN
- 动作：提醒主 skill 考虑 scope down / 切路线

**⑤ 顺序错**（动作顺序违反状态机）
- 检测：对比主 skill 实际执行顺序 vs state-machine 预期
- 例：还没写完代码就跑 e2e / 还没跑测试就 commit
- 严重度：WARN
- 动作：提醒主 skill 纠正顺序

**⑥ 冗余**（重复动作 is_stuck）
- 检测：同一 tool + 同一输入重复 ≥ 3 次（MVP 默认阈值；借 Devin/OpenHands `is_stuck`）
- 例：连续 3 次 pytest 都同一 error 仍在 retry / 同一文件反复 Edit
- 严重度：WARN（连续 5 次升 BLOCK）
- 动作：报告卡住模式、建议换策略

### 5.2 3 条打断红线（其他不打断）

Supervisor 只在以下 3 种情况**直接打断用户**，其他 WARN/INFO 只对主 skill 发信号（主 skill 自处理）。

| 红线 | 触发条件 | 动作 | 恢复路径 |
|---|---|---|---|
| DRIFT_CRITICAL | 动作与 goal-anchor 对抗（"走偏"升级）| 暂停所有执行 + 结构化汇报 + 等用户决策 | 用户决策 "纠偏" → 回原路线 / "改目标" → 更新 goal-anchor |
| DOD_GAP_ALERT | 关键 DoD 项被跳过或确认不可达（"漏菜"/"忘开火"升级）| 暂停 + 列 gap + 等用户决策 | 用户决策 "补做" / "降级 DoD" / "切路线" |
| IRREVERSIBLE_HALT | 即将做不可逆动作（push prod / 删数据 / OSS 生产 bucket 非幂等覆盖写）但前置缺失 | 强制拦截、不执行 | 用户决策 "补前置后继续" / "放弃" |

**OSS 写入豁免**：视频出片任务的 OSS 上传属 DoD 内部自动步骤（DoD 模板①要求 `oss_head.status_code == 200`），**不触发 IRREVERSIBLE_HALT**。IRREVERSIBLE_HALT 仅覆盖「生产 bucket 非幂等覆盖写」和「删数据」。

其他情况 Supervisor 都不打断用户。把"要不要"型的问题留给主 skill 按路线规则自决。

### 5.3 纠偏 4 级 retry ladder

纠偏引擎的动作阶梯。每一级失败后自动升级到下一级。

```
L0 retry-same              → 单步 timeout / 临时网络错 / 临时 429
                             动作：原参数 retry ≤ 2 次
                             升级：2 次仍失败 → L1

L1 retry-tweaked + scope ↓ → L0 失败 / schema 不符 / prompt 过长
                             动作：微调参数（缩小 scope / 切换 model / 改 prompt）retry
                             升级：3 次仍失败 → L2

L2 switch-skill / HITL     → L1 失败 / DoD 子契约不可达
                             动作：切换等价 skill（如 e2e-runner → verification-loop）
                                  或触发 Supervisor 红线 → 打断用户
                             升级：切换后仍失败 → L3

L3 force finalize degraded → L2 失败 / budget 临界
OR escalate-user             动作：降级 DoD 强制收口（记 failure-archive）
                                  或直接 escalate 给用户请决策
                             升级：终止点
```

**无界 retry 是大忌**（反模式 § 8.5）。每次 retry 必记 task-board，`retry_count` 进 failure-archive。

### 5.4 信号源（6 种）

Supervisor 的判断依据来自 6 个信号源：

1. **Hook output**（PostToolUse / PreToolUse / Stop / SubagentStop）— 每次工具调用的原始记录
2. **Subagent status**（Verifier / Build-resolver / Code-reviewer 等的返回）— 强证据
3. **Verifier 中间评估**（不等到收口，阶段性跑）— 提前暴露 gap
4. **Context budget watcher**（token 使用率 / 剩余上下文）— 预算监控
5. **Time budget watcher**（耗时 vs 估算）— 预算监控
6. **Cost budget watcher**（API cost 累计 vs 预算）— 预算监控

6 种信号汇入 task-board.json（字段 schema 见 `task-board-template.md` Phase 4 产出），Supervisor 按配置的干预规则查表 → 判定严重度 → 决定发 INFO/WARN/BLOCK。

---

## § 6 验证 QA review gate 规则

本章和 § 1.1 并列为**最核心章节**。所有"真完成"判定都在这里落地。

### 6.1 DoD 布尔表达式 — 机器可执行，非 LLM 自报

**DoD（Definition of Done）必须是 Python boolean 可 eval 的表达式字符串**，不是自然语言清单，也不是 LLM 自报的 "done"。

**通用格式**：
```
DoD = (条件 1) AND (条件 2) AND (条件 3) ... AND (条件 N)
```

每个条件必须是**可执行命令的布尔返回**或**文件系统/HTTP 状态的物理校验**。

**校验原语库 bootstrap 说明**：模板中出现的所有 `函数(参数)` 是**方法论语义占位符**，在 Phase 6 产出 `harnessFlow /verifier_primitives/` 前按下表映射到现有工具执行（Verifier 手动逐条核对 / 主 skill 通过 Bash + Read 调度原语）：

| 原语 | Phase 6 前的实现 |
|---|---|
| `file_exists(path)` | `Read` 工具或 `test -f` |
| `ffprobe_duration(path)` | `ffprobe -v error -show_entries format=duration -of csv=p=0 {path}` |
| `oss_head(key).status_code` | `requests.head(oss_signed_url)` / `curl -I` |
| `uvicorn_started(host:port)` | `curl -sf http://{host:port}/health` / `lsof -i:{port}` |
| `curl_status(url)` | `curl -o /dev/null -s -w "%{http_code}" {url}` |
| `curl_json(url)` | `curl -s {url} \| python -m json.tool` |
| `pytest_exit_code(path)` | `pytest {path}; echo $?` |
| `pytest_all_green()` | `pytest; [ $? -eq 0 ]` |
| `playwright_nav(url)` / `playwright_exit_code(spec)` | `playwright test {spec}` |
| `vite_started(host:port)` | `curl -sf http://{host:port}/` |
| `screenshot_has_content(path)` | `file {path}` + 非空大小校验 |
| `type_check_exit_code` | `npm run type-check; echo $?` |
| `wc_lines(path)` | `wc -l {path}` |
| `grep_count(pattern, path)` | `grep -c "{pattern}" {path}` |
| `cross_refs_all_resolvable(doc)` | 列出所有 `[link]` 目标用 Read 逐一验证 |
| `schema_valid(data, schema_path)` | `jsonschema -i {data} {schema_path}` |
| `benchmark_regression_delta(baseline)` | 项目自定义 perf 脚本，输出 delta 数值 |
| `no_public_api_breaking_change()` | `git diff main -- openapi.yaml \| grep -E "^-\\s"` 为空 |
| `playback_check(path)` | 抽帧 `ffmpeg -ss 00:03 -i {path} -vframes 1` + 非黑帧校验 |
| `retro_exists(path)` | `Read` / `test -f`（`harnessFlow /retros/` 目录在 Phase 7 正式创建，当前手动 `mkdir -p` 即可）|
| `code_review_verdict` | `code-reviewer` subagent 返回的 PASS/FAIL |
| `diff_lines_net` | `git diff --stat \| tail -1` 解析 |

Phase 6 产出后，上述命令会被打包为 `harnessFlow/verifier_primitives/{primitive}.py`，Verifier subagent 直接调用函数而非手拼命令。DoD 表达式的**书写形式保持不变**，只是底层实现迁移。

**5 类任务的 DoD 模板**：

**① 视频出片任务（如 aigcv2 P20）**
```
DoD = (file_exists("media/p20.mp4"))
  AND (ffprobe_duration("media/p20.mp4") > 0)
  AND (oss_head("p20.mp4").status_code == 200)
  AND (playback_check("media/p20.mp4") == True)
  AND (retro_exists("harnessFlow /retros/p20.md"))
```

**② 后端 feature 任务（如 aigc 加素材源）**
```
DoD = (uvicorn_started("localhost:8000"))
  AND (curl_status("http://localhost:8000/materials/reddit") == 200)
  AND (pytest_exit_code("tests/test_materials_reddit.py") == 0)
  AND (schema_valid(curl_json("http://localhost:8000/materials/reddit"), "schemas/material_reddit.json"))
  AND (code_review_verdict == "PASS")
```

**③ UI feature 任务（如 Vue 页面）**
```
DoD = (vite_started("localhost:5173"))
  AND (playwright_nav("http://localhost:5173/new-page").status == "ok")
  AND (screenshot_has_content("artifacts/new-page.png"))
  AND (playwright_exit_code("e2e/new-page.spec.ts") == 0)
  AND (type_check_exit_code == 0)
```

**④ 文档任务（如 method3 重构）**
```
DoD = (file_exists("harnessFlow /method3.md"))
  AND (wc_lines("harnessFlow /method3.md") >= 500)
  AND (grep_count("## § [0-9]", "method3.md") == 10)
  AND (cross_refs_all_resolvable(method3))
  AND (reader_5min_test == "PASS")
```

**⑤ 重构任务（如 aigc 后端分层）**
```
DoD = (pytest_all_green())
  AND (benchmark_regression_delta < 0.05)
  AND (code_review_verdict == "PASS")
  AND (diff_lines_net < expected_upper_bound)
  AND (no_public_api_breaking_change())
```

**Why**：所有公开 multi-agent 框架都在这一点上翻车（AutoGen `is_termination_msg` 让 LLM 自己说"完了"、CrewAI 最后一步由 Manager LLM 裁决）。LLM 的"自证完成"是自由度最高的捏造空间，必须用不可谈判的机器标准兜住。

**How to apply**：
- 主 skill 在分诊后、执行前必须先生成一个 DoD 表达式，写入 task-board.json 的 `dod` 字段
- 表达式中的每个 `函数(参数)` 必须能映射到 harnessFlow 预定义的校验原语库（Phase 6 产出）
- 用户确认 DoD 后才允许执行（确认 = 显式同意或 2 秒内不反对）
- 执行过程中 DoD 不允许被修改（若要改必须触发 § 5.2 红线 + 用户决策）

### 6.2 Verifier subagent — 执行/审查分离

**Verifier 是独立 subagent**，负责在主 skill 声明"即将完成"时做收口验证。它**不参与执行**，只做审查。

**强制三动作**：
1. **物理存在校验** — 依 DoD 表达式中的文件系统/HTTP 条件逐条 eval
2. **重跑 DoD 命令** — 不信执行 agent 的报告，自己重跑一遍所有可执行条件
3. **关键路径抽测** — 对 DoD 没覆盖但属于关键路径的点做 sample check（如视频任务抽测 mp4 第 3 秒是否有内容、后端任务抽测 200 响应的 body 是否符合 schema）

**只读权限**：Verifier 不允许调用任何写工具（Write / Edit / bash exec 外的命令），只能 Read / Glob / Grep / curl（只读请求）/ ffprobe 等查询原语。

**FAIL 动作**：
- 任务**禁止汇报完成**
- 写 task-board.json 的 `verifier_report` 字段（结构化）
- 触发纠偏引擎 L2/L3（按失败子契约数量定级）
- 失败进 failure-archive.jsonl（§ 7.3）

### 6.3 三段证据链（缺一不可）

完成证据必须覆盖三段：

| 段 | 内容 | 例子（视频任务） |
|---|---|---|
| 存在证据 | artifact 物理存在 + 大小 > 0 + 可访问 | `ls -la media/p20.mp4` 返回非空；`curl -I oss_url` 200 |
| 行为证据 | artifact 行为正确（可运行/可播放/可读取）| `ffprobe p20.mp4` 返回合法元数据；`vlc --play-and-exit p20.mp4` 成功 |
| 质量证据 | artifact 质量达标（内容/性能/语义） | 时长 ≥ 15s / 分辨率 ≥ 720p / 音视频同步 / 与脚本匹配 |

缺任一段 = 未完成。**只有存在证据没有行为证据**是旧 method3 方案 C 在 P20 翻车的直接原因（mp4 路径"看起来有"但从未跑过 ffprobe / playback）。

### 6.4 假完成 trap catalog

harnessFlow 维护一份结构化「假完成陷阱目录」（Phase 7 落 jsonl schema），每条含【识别模式】【拦截动作】。下列是 MVP 必备 7 条：

| Trap | 识别模式 | 拦截动作 |
|---|---|---|
| LLM 自报 TERMINATE | 响应中出现 `TERMINATE` / `done` / `complete` 但无 DoD eval 结果 | Verifier 强制运行 DoD，不信文字 |
| 代码 push 即完成 | 汇报 `git push success` + 无 e2e 或无 artifact | 拦截，要求跑 e2e |
| build green 即完成 | 汇报 `npm run build` 或 `go build` 成功 + 无运行时验证 | 拦截，要求起 dev server 或跑 runtime test |
| Phase X 通过即完成 | 汇报 "Phase 4 PASS" / "流程跑完" + 无终态 artifact | 拦截，要求贴可消费 artifact |
| 单测过即完成 | `pytest ok` + 无 e2e / 无真流量验证 | 拦截，要求跑 e2e 或真流量 smoke |
| 放锅里即完成（视频专） | 生成 prompt/脚本/镜头脚本后汇报完成 + 无 mp4 | 拦截，要求跑到 render 节点出 mp4 |
| 水泥到了型问题 | 出现 "要不要 X" 型对用户提问且 X 是路线里的标准下一步 | 主 skill 自处理，不打断用户 |

每个 trap 在 failure-archive 命中一次就 +1 计数，Supervisor 依此动态调高相应 DoD 子契约的监控权重。

---

## § 7 交付收口规则

收口 = 任务从 Verifier PASS 到最终汇报用户 + 记忆写回的完整流程。

### 7.1 强制 post-mortem

**任务收口前必跑 retro，无条件、不可跳过**。跳过 retro 等于重蹈覆辙（见反模式 § 8.6）。

retro report 至少含 11 项：

1. **DoD 实际 diff**（预期 vs 实际对每一子条件 PASS/FAIL）
2. **路线偏差**（实际走的路线 vs 初始推荐的差异 + 原因）
3. **纠偏次数**（按 L0/L1/L2/L3 分级）
4. **Verifier FAIL 次数**（按子契约分类）
5. **用户打断次数**（按 DRIFT/DOD_GAP/IRREVERSIBLE 分类 + 废问题数 — 严禁废问题）
6. **耗时 vs 估算**（体量估算准不准）
7. **成本 vs 估算**（token/cost 超了没）
8. **新发现的 trap**（喂 trap catalog）
9. **新发现的有效组合**（skill+command 组合首次成功 → 喂路由器）
10. **进化建议**（matrix 权重调整 / 新 skill 引入建议 / 反模式补充）
11. **下次推荐**（同类任务下次用什么路线）

### 7.2 三类记忆分级写回

retro 产出物按"会影响哪个引擎"分三类写回：

| 类别 | 写回位置 | 影响 |
|---|---|---|
| route-outcome | `routing-matrix.json` 权重更新输入 | 影响下次"路线推荐"排序 |
| anti-pattern | `trap-catalog.jsonl` 扩充 | 喂 Verifier 的 trap 拦截规则 |
| combination | `skill-combination-pool.jsonl` | 喂路由器的候选组合池 |

写回不等于立即生效：route-outcome 累积 ≥ 10 样本才触发 matrix 权重 review（MVP 默认）；combination 累积 ≥ 5 次成功才升级到推荐候选（MVP 默认）。阈值可在 `routing-matrix.json` 的 `evolution_config` 字段覆盖。防止单次偶然结果影响下次决策。

### 7.3 failure-archive 驱动进化

**失败记忆优先于成功记忆**。harnessFlow 进化的主要燃料是 `failure-archive.jsonl`（每项目独立 + 全局只读视图）。

schema（Phase 7 落地，权威定义见 `schemas/failure-archive.schema.json`，JSON Schema draft-07；写入路径见 `archive/writer.py`）关键字段：

```
{
  "task_id": "...",
  "date": "2026-04-16",
  "task_type": "视频出片",
  "size": "XL",
  "risk": "不可逆",
  "route": "C",
  "node": "verifier",
  "error_type": "DOD_GAP",
  "missing_subcontract": ["mp4.duration", "oss_key"],
  "retry_count": 0,
  "final_outcome": "false_complete_reported",
  "frequency": 1,
  "root_cause": "旧 method3 C 路线缺 Verifier 收口",
  "fix": "引入 Verifier + DoD 布尔表达式",
  "prevention": "trap catalog + 强 Supervisor"
}
```

archive 的第一条 entry 将是方案 C P20 假完成事件（见反模式 § 8.1）。每 20 次任务触发一次路由权重审计（MVP 默认，逻辑在 `archive/auditor.py`）：失败率高的组合降权或移出推荐；高频 trap 升优先级。审计频率在 `routing-matrix.json` 的 `evolution_config.audit_interval` 覆盖。

**进化边界（硬线）**：`auditor.audit()` 只产 `audit-reports/audit-*.json` 建议报告，**永不自动改写** `routing-matrix.json`。人工复核后再手动合入——避免噪声样本、罕见 trap、评估偏差污染下次路由决策。

---

## § 8 反模式清单

每条反模式含【反模式特征】【造成的问题】【harnessFlow 如何规避】。

### 8.1 方案 C P20 假完成事件（自家，2026-04-16）

- **特征**：按旧版 method3.md 方案 C（全 PRP 链）执行 aigcv2 P20 真出片任务。执行到 LangGraph pipeline 跑完渲染节点，主 agent 看到 pipeline 无 error 后直接汇报"完成"。实际：**没起 uvicorn、没 POST /produce、没校验 mp4 文件是否存在、没校验时长、没校验 OSS key、没做任何 playback**。
- **问题**：用户打开 OSS 准备看结果时发现根本没产出 mp4（或 mp4 为 0 字节 / 损坏），过往大量同类任务可能也在同一口径下假完成但未被发现。信任崩塌。
- **规避**：① § 1.1 真完成定义强制"可消费 artifact"；② § 6.1 DoD 布尔表达式要求 mp4 物理存在 + duration > 0 + OSS key 200；③ § 6.2 Verifier 独立重跑 DoD 不信执行 agent；④ § 6.3 三段证据链缺一不可；⑤ § 6.4 trap catalog 「放锅里即完成」直接拦；⑥ § 5 Supervisor 全程在场防止过早报完成。

### 8.2 AutoGen `is_termination_msg`（LLM 自报 TERMINATE）

- **特征**：AutoGen GroupChat 终止条件由 `is_termination_msg` 函数判定，函数输入是上一轮 LLM 响应。LLM 为了快速结束对话会在响应里塞 "TERMINATE" — 等于"我说我完了就完了"。
- **问题**：典型假完成反模式。LLM 没有物理世界反馈闭环，"说完了"和"真完了"是两回事。
- **规避**：harnessFlow 根本不让 LLM 决定何时终止。终止的唯一信号是 Verifier 对 DoD 表达式 eval 返回 True，且 Verifier 不信 LLM 文字描述（§ 6.1 + § 6.2 + § 6.4 trap 1）。

### 8.3 CrewAI Hierarchical Manager LLM 全黑盒路由

- **特征**：CrewAI 在 Hierarchical 模式下由 Manager LLM 自主决定调用哪个 Worker agent、调多少次、顺序如何。Manager 的推理过程不可见、不可审计。
- **问题**：① 失败发生时无法定位是路由错了还是执行错了；② 相同输入下两次运行路径可能完全不同；③ 无法对路由做进化调整。
- **规避**：§ 3.1 两级路由 — 确定性 DAG 默认，LLM 只在真分叉用，且每次 LLM 路由必记 `{trigger, candidates, scores, chosen, reason}` 五字段可审计（§ 3.1 + § 3.3）。

### 8.4 MetaGPT / ChatDev 硬 SOP

- **特征**：MetaGPT 把软件开发流程硬编码为 PRD → 架构 → API → 代码 → 测试 → 文档 的固定流水线，每步 role 也固定。
- **问题**：灵活性差。新类型任务（如 UI 视觉专线、研究探索专线）要改代码才能加，且不能根据任务实际动态切路线。
- **规避**：§ 4 多路线 A~F 精神 + LLM 路由能力（§ 3.1 二级） + 路线可切换/降级（§ 4.2 § 4.3）。SOP 从"代码里的状态机"解耦为"matrix.json 里的数据"，可热改不动代码。

### 8.5 无界 retry 循环

- **特征**：agent 遇到失败就无脑 retry，没有次数上限、没有升级机制、没有 budget guard。
- **问题**：token / cost 快速耗尽；同一错误模式反复撞墙；用户等待时间不可控。
- **规避**：§ 5.3 4 级 retry ladder 每级有明确次数上限 + 自动升级；§ 5.4 budget watcher 三种（context/time/cost）临界时强制 force finalize degraded 或 escalate-user（§ 5.3 L3）。

### 8.6 post-mortem 遗忘（所有公开方案）

- **特征**：公开多 agent 框架（AutoGen / CrewAI / LangGraph / Swarm）都没内置"任务结束后强制复盘 + 结构化记忆写回"机制。每次任务完成 = 完全遗忘。
- **问题**：同一失败模式不断重演，系统不积累经验。harnessFlow 要避免的最大陷阱就是这个。
- **规避**：§ 7.1 强制 post-mortem（不可跳过）+ § 7.2 三类记忆分级写回 + § 7.3 failure-archive 驱动路由权重审计。**失败记忆 > 成功记忆**是 harnessFlow 的核心 bet。

### 8.7 口号层"重视验证"而无机制

- **特征**：文档里写"我们重视验证 / 务必做 e2e / 确保完成"但没有任何机器可执行的拦截点、没有 DoD 表达式、没有独立审查者。
- **问题**：等于没说。LLM 高置信时会跳过任何"口号级"约束，因为口号无对抗性。
- **规避**：§ 1.1 真完成 + § 6.1 DoD 布尔表达式 + § 6.2 Verifier 独立 + § 6.4 trap catalog 结构化识别模式。method3 里**所有规则都必须翻译成机器可执行的判断逻辑**，禁止只写精神口号。

### 8.8 自动改写 routing-matrix（Phase 7 新增）

- **特征**：auditor 发现某 cell 失败率 > 0.5，直接在 `routing-matrix.json` 里把该 cell 权重改小 / 删候选；或反之，某 cell 成功率高就自动升权。
- **问题**：单样本或偏差样本会污染下次决策；连续几次坏运气足以"杀掉"一条本身正确的路线；evolution 循环对抗不住噪声。
- **规避**：`archive/auditor.py` 硬限"只写 `audit-reports/audit-*.json` 建议报告，永不 open-write `routing-matrix.json`"（§ 7.3 进化边界硬线）；所有 matrix 变更走**人审批 PR**。

### 8.9 retry 循环里刷 archive（Phase 7 新增）

- **特征**：主 skill 每次 L0/L1/L2 重试都调 `failure-archive-writer` 写一条；或在 IMPL↔VERIFY 循环里累加 entry。
- **问题**：同一任务产 N 条 entry，`frequency` 计数被稀释，`audit()` 的统计基数失真，下次路由决策被误导。
- **规避**：归档**只在终态** (`CLOSED` / `PAUSED_ESCALATED` 恢复后 / `ABORTED`) 触发 —— `harnessFlow-skill.md § 8` 和 `subagents/failure-archive-writer.md § 1.1` 各自明写。writer 没做去重（认为调用方的约束）。

### 8.10 绕开 writer 直接 append jsonl（Phase 7 新增）

- **特征**：某脚本或手工流程为了图快，直接 `open("failure-archive.jsonl", "a")` 写一条 JSON —— 跳过 schema 校验、跳过 `_derive_entry` 的派生逻辑、跳过 `_derive_frequency` 的同类聚合。
- **问题**：schema 破坏后，下次 `auditor.audit()` 或 `Stop-final-gate.sh` 校验会 raise，污染整个归档 —— 更糟是"看起来能写 / 跑起来才报错"的延迟失败。
- **规避**：**唯一入口** `archive.writer.write_archive_entry()`；subagent md 显式禁止绕路；CI / pre-commit 可选加 "禁止直接 echo 进 failure-archive.jsonl" 的 grep 检查（Phase 8 候选）。

---

## § 9 快速索引

### 9.1 新旧对照

旧版 method3（35 行速查表）每条规则在新版里的对应去向：

| 旧版条目 | 旧版内容 | 新版去向 |
|---|---|---|
| 表一 XS → 直接改 | 单函数/注释类小改 | § 2.1 体量 XS + § 2.4 例 4 + § 4 路线 A |
| 表一 S → /plan | 单模块小 feature | § 2.1 S + § 2.4 + § 4 路线 B |
| 表一 M → /feature-dev | 单模块中 feature | § 2.1 M + § 2.4 例 1 + § 4 路线 B/D |
| 表一 L → 方案 C 混搭 | 跨模块 feature | § 2.1 L + § 2.4 例 2 + § 4 路线 C（强化版）|
| 表一 XL → 全 PRP | 跨多模块重构 | § 2.1 XL + § 2.4 例 3 + § 4 路线 C |
| 表一 UI → /gan-design | UI 视觉专线 | § 2.2 UI 类型 + § 4 路线 D |
| 表一 纯后端-L/XL | Playwright 可验证 + gan-build | § 2.2 agent graph / 后端 + § 4 路线 C/E |
| 表二 Reddit 爬虫加字段 | S-M 多模块小改 | § 2.4 例 2 + § 4 路线 B |
| 表二 新增素材源（Product Hunt） | L 多模块 feature | § 2.4 例 2 + § 4 路线 C |
| 表二 video_graph 节点连线 | L-XL graph | § 2.2 agent graph + § 4 路线 C/E |
| 表二 新 \_subgraph.py | XL agent graph | § 2.4 例 3 + § 4 路线 C/E + save-session |
| 表二 Vue 新页面 | M-L UI | § 2.4 例 1 + § 4 路线 D |
| 表二 Vue Flow 视觉优化 | M UI | § 2.4 例 1 + § 4 路线 D |
| 表二 AIPDD PyQt6 Tab | M-L | § 4 路线 B |
| 表二 化学课件新动画 | M | § 4 路线 B |
| 表二 修 E2E 测试 | S | § 4 路线 A/B |
| 硬规则 1: S 以下别用重组合 | 避免过度工程 | § 2.4 例 4 + § 4 路线 A 精神 |
| 硬规则 2: L 以上不用 artifact 会吃亏 | 强制 artifact | § 6.1 DoD 表达式强制 artifact 条件 + § 6.3 三段证据 |
| 硬规则 3: 视觉用 /gan-design | 视觉任务专用 | § 2.2 UI 识别 + § 4 路线 D |

旧版所有 7 个表一行 + 9 个表二行 + 3 条硬规则在新版都有明确对应，无遗漏。

### 9.2 场景 → 规则映射

| 我想做什么 | 去哪章找规则 |
|---|---|
| 判断这个任务算不算真完成 | § 1.1 + § 6 全章 |
| 选择编排路线 | § 2 分诊 + § 4 路线精神 + `routing-matrix.md` |
| 生成 DoD 表达式 | § 6.1（5 类模板 + 原语库指引） |
| 判断 Supervisor 该不该打断 | § 5.2 三红线 |
| 判断要不要 retry 还是升级 | § 5.3 4 级 ladder |
| 防止假完成 | § 1.1 + § 6 + § 8（反模式） |
| 任务结束后要做什么 | § 7 交付收口 |
| 判断「中途的提问」是不是废问题 | § 1.2 客人点菜 + § 5.2 红线 |
| 想给 method3 加新规则 | § 7.3 进化流程（走 retro → failure-archive → matrix review → PR） |
| 想理解 harnessFlow 和 SP/ECC/gstack 的边界 | § 1.3 + `harnessFlow.md`（Phase 2 产出） |
| 想看某条路线（A~F）详细怎么跑 | `flow-catalog.md`（Phase 3 产出）|
| 想看任务类型 × 体量 → 具体 skill 组合 | `routing-matrix.md`（Phase 3 产出）|
| 想看任务流转状态图 | `state-machine.md`（Phase 4 产出）|
| 想 fork 一个 task-board 模板 | `task-board-template.md`（Phase 4 产出）|
| 想看 DoD 验证清单 | `delivery-checklist.md`（Phase 4 产出）|

---

*本文档是 harnessFlow 的**奠基规则**。所有后续 Phase (2-8) 的文档都以 method3 的章节为规则源头。method3 的每一条规则必须翻译成机器可执行的判断逻辑，禁止只写精神口号。method3 自己的迭代也必须走 § 7.3 进化流程（failure-archive → matrix review → PR），不允许任何人直接改这份文件而不经 retro 推动。*

*— v1.0 end —*
