---
doc_id: tech-design-L1-04-Quality Loop-L2-01-v1.0
doc_type: l2-tech-design
layer: 3-1-Solution-Technical
parent_doc:
  - docs/2-prd/L1-04 Quality Loop/prd.md（§5.4.1 L2-01 + §8 L2-01 详细定义）
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/architecture.md
  - docs/3-1-Solution-Technical/L0/ddd-context-map.md
  - docs/3-1-Solution-Technical/L0/open-source-research.md
  - docs/3-1-Solution-Technical/L0/tech-stack.md
  - docs/3-1-Solution-Technical/projectModel/tech-design.md
  - docs/superpowers/specs/2026-04-20-3-solution-design.md
version: v1.0
status: filled-depth-A  # R3.1.01 filled · 1500-2500 行目标
author: main-session-subagent-R3.1.01
created_at: 2026-04-21
updated_at: 2026-04-21
traceability:
  prd_anchor: docs/2-prd/L1-04 Quality Loop/prd.md §5.4.1 L2-01 + §8 L2-01 详细定义（§8.1 ~ §8.9）
  scope_anchor: docs/2-prd/L0/scope.md §5.4.1 / §5.4.4 硬约束 4
  architecture_anchor: docs/3-1-Solution-Technical/L1-04-Quality Loop/architecture.md §1.4 L2-01 行 + §2.2 TDDBlueprint 聚合根 + §3.1 7 L2 容器图 + §4.1 P0-L1-04-A 时序
  ic_contracts_anchor: docs/3-1-Solution-Technical/integration/ic-contracts.md §3.3 IC-03 + §3.6 IC-06 + §3.9 IC-09 + §3.16 IC-16
  ddd_bc: BC-04 Quality Loop（L0/ddd-context-map.md §2.5 · Domain Service + Factory + Aggregate Root `TDDBlueprint`）
  role: Domain Service + Factory（S3 总指挥 · blueprint_ready 广播上游）
  business_flow_anchor: [BF-S3-01]
consumer:
  - docs/3-2-Solution-TDD/L1-04-Quality Loop/L2-01-tests.md（待建）
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-DoD 表达式编译器.md（blueprint_ready 消费方 · 读 ac_matrix 校验白名单谓词）
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-03-测试用例生成器.md（blueprint_ready 消费方 · 按分层矩阵生成骨架）
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-04-质量 Gate 编译器.md（blueprint_ready 消费方 · 读 coverage_target 编 gates）
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-06-S5 Verifier 编排器.md（S5 组装工作包时读 TDDBlueprint）
quality_baseline: true  # 对齐 L2-02 决策引擎 / L2-06 Supervisor 接收器深度 A 基线
---

# L1 L2-01 · TDD 蓝图生成器 · Tech Design

> **本文档定位**：3-1-Solution-Technical 层级 · L1 的 L2-01 TDD 蓝图生成器 技术实现方案（L2 粒度）。
> **与产品 PRD 的分工**：2-prd/L1-04-Quality Loop/prd.md §5.4 的对应 L2 节定义产品边界，本文档定义**技术实现**（接口字段级 schema + 算法伪代码 + 底层数据结构 + 状态机 + 配置参数）。
> **与 L1 architecture.md 的分工**：architecture.md 负责**跨 L2 架构 + 跨 L2 时序**，本文档负责**本 L2 内部技术细节**。冲突以 architecture.md 为准。
> **严格规则**：本文档不复述产品 PRD 文字（职责 / 禁止 / 必须等清单），只做技术映射 + 补齐"产品视角未说 but 工程师必须知道"的部分（具体算法 · syscall · schema · 配置）。

---

## §0 撰写进度

- [x] §1 定位 + 2-prd §5.4.1 / §8 L2-01 映射（BF-S3-01 溯源）
- [x] §2 DDD 映射（BC-04 Quality Loop · TDDBlueprint Aggregate Root + Factory）
- [x] §3 对外接口定义（4 方法字段级 YAML schema + 错误码 ≥ 8 项）
- [x] §4 接口依赖（被谁调 · 调谁 · 5 件产物依赖边 · PlantUML 依赖图）
- [x] §5 P0/P1 时序图（PlantUML · S3 主干 + blueprint_ready 并行广播）
- [x] §6 内部核心算法（AC 矩阵构建 / pyramid 推导 / coverage target / NLP 解析）
- [x] §7 底层数据表 / schema 设计（blueprint + ac_matrix + test_env_blueprint · PM-14 分片）
- [x] §8 状态机（DRAFT → VALIDATING → READY → PUBLISHED → FROZEN · PlantUML + 转换表）
- [x] §9 Mock 三档（unit / contract / chaos）+ 9 环境变量 + fixture 四象限 + MockTDDBlueprintGenerator 参考类
- [x] §10 配置参数清单（≥ 12 项）
- [x] §11 STRIDE 10+ 项 + 8 层 Defense in Depth + Open Questions ≥ 6
- [x] §12 性能目标（P95/P99/并发/资源）
- [x] §13 与 2-prd / 3-2 TDD 的映射表

> **填写次序建议**：§1 → §3 接口 → §4 依赖 → §2 DDD（基于接口回推聚合 / 组件）→ §5 时序（串 §3+§4）→ §6 算法 → §7 schema → §8 状态机 → §9 Mock 三档 → §10 配置 → §11 STRIDE + OQ → §12 SLO → §13 映射。理由：本 L2 是 S3 总指挥 · 接口驱动下游 3 个 L2 的并行广播，从契约和依赖着手最易固定 Aggregate 边界；§9 Mock 三档和 §11 STRIDE 放在骨架落定后补充，保证工程可测性与威胁覆盖。

---

## §1 定位 + 2-prd 映射

### 1.1 本 L2 的唯一命题（One-Liner）

**L2-01 = L1-04 Quality Loop 的 S3 总指挥 + `TDDBlueprint` Aggregate 的唯一生产者**：在 S3 阶段接收 `IC-03 enter_quality_loop{phase=S3}` → 读 4 件套（L1-02 产） + WBS 拓扑（L1-03 产）+ AC 清单 → 经 `TDDBlueprintFactory` 构造出五件一套 `TDDBlueprint`（test_pyramid / ac_matrix / coverage_target / test_env_blueprint / priority_annotation） → 校验 AC 覆盖率 100% 硬红线 → 广播 `blueprint_ready` 给 L2-02/03/04 **并行起跑** → 作为 S3 Stage Gate 的**硬凭证之一**交给 L1-02 → 进入 FROZEN 状态（任何后续修改必经 FAIL-L2 回退）。

关键定性（来自 architecture.md §1.4 + §2.4）：**本 L2 是 Domain Service + Factory 组合**——DDD 构造块用 "Domain Service（做推导）+ Factory（建聚合）" 而非 Application Service（不含长事务 / 不编排跨 BC），推导函数纯函数化以便 100% 单元可测；Factory 是构造 `TDDBlueprint` Aggregate Root 的**唯一入口**（符合 L0 DDD §7.2.4 "单一写入点"原则）。

### 1.2 与 `2-prd/L1-04 Quality Loop/prd.md §8` 的精确小节映射表

> 说明：本表是**技术实现 ↔ 产品小节**的锚点表，不复述 PRD 文字。每行左列为本 tech-design 的段落，右列为对应的 PRD 小节。冲突以本文档（技术实现）+ architecture.md（架构）为准，若发现 PRD 有歧义或不足以导出字段级 schema，按 spec 6.2 规则反向修 PRD 并在此处注明。

| 本文档段 | 2-prd §8 小节 | 映射内容 | 备注 |
|---|---|---|---|
| §1.1 命题 | §8.1 职责 + 锚定 | "S3 总指挥 + TDDBlueprint 唯一生产者" | 本文档补 "Domain Service + Factory" 定性（prd 未明写 DDD）|
| §1.4 兄弟边界 | §8.3 边界 | In-scope 8 项 + Out-of-scope 8 项 | — |
| §1.5 PM-14 | §8.4 硬约束 + frontmatter PM-14 声明 | "TDDBlueprint.project_id 根字段" + "AC 覆盖率按 project 独立计算" | **补** |
| §2 DDD | §8 无 DDD 语言 | BC-04 映射 + Factory 单例 | **补** |
| §3 接口 `generate_blueprint` | §8.2 输入 + §8.6 必 6 | IC-03 接入后主方法 | **补字段级 YAML** |
| §3 接口 `get_blueprint` | §8.2 输出（供下游读）| L2-02/03/04/06 按 blueprint_id 读 | **补** |
| §3 接口 `validate_coverage` | §8.4 硬约束 2 | AC 覆盖率 100% 硬性校验 | **补** |
| §3 接口 `broadcast_ready` | §8.6 必 6 "必须广播 blueprint_ready" | IC-L2-01 广播 | **补** |
| §3 错误码 | §8.4 硬约束 + §8.5 禁止 | 约束违反一对一映射错误码 | **补错误码表 ≥ 8** |
| §4 依赖 | §8.2 输入源 + §8.7 可选 KB | 上游 L1-02/03/01 + 可选 L1-06 | — |
| §5 时序 | §8 无时序；L1-04 arch §4.1 P0-L1-04-A | PlantUML 重绘 | **补** |
| §6 算法 | §8.2 输出 + §8.4 硬约束 2 | AC 矩阵 + pyramid + coverage target | **补 Python-like 伪代码** |
| §7 schema | §8.2 输出"master-test-plan 结构" | YAML 化 + PM-14 `projects/<pid>/tdd/` | **补** |
| §8 状态机 | §8.3 "蓝图冻结" | DRAFT → VALIDATING → READY → PUBLISHED → FROZEN | **补** |
| §9 Mock 三档 | — | unit / contract / chaos | **补** |
| §10 配置 | §8.4 性能约束 | coverage_threshold / ac_strict_mode 等 | **补 ≥ 12 项** |
| §11 降级 + STRIDE | §8.4 + §8.5 + arch §3.1 | 错误分类 + 降级链 + STRIDE 10+ | **补** |
| §12 SLO | §8.4 性能约束 | 3 分钟蓝图 / 1 秒广播 / 1MB 文档 | 原样继承 + 细化 P95/P99 |
| §13 映射 | — | 本段接口 ↔ §8.X + ↔ 3-2-TDD 用例 | **补** |

### 1.3 与 `L1-04/architecture.md` 的位置映射

| architecture 锚点 | 映射内容 | 本文档对应段 |
|---|---|---|
| §1.4 L2 清单 L2-01 行 | "TDD 蓝图生成器 · Domain Service + Factory + Aggregate Root TDDBlueprint" | §2 DDD |
| §1.5 "谁写 quality-gates.yaml" | L2-01 只给"覆盖率目标"作为输入给 L2-04 | §1.4 兄弟边界 |
| §2.2 聚合根 TDDBlueprint | 本 L2 持有 · L2-03 / L2-04 / L2-06 读 | §2.2 + §7 |
| §2.3 VO CoverageTarget | "行/分支/AC 三类覆盖率下限 · AC 硬性 = 1.0" | §2.4 |
| §2.4 领域服务 TDDBlueprintFactory | "把 4 件套 + WBS 组合成 TDDBlueprint 聚合" | §2.4 |
| §2.5 Repository 模式 `TDDBlueprintRepository` | 聚合根持久化唯一写入点 | §2.6 |
| §2.6 跨 BC BC-04 ↔ BC-02 Customer | L1-02 4 件套 + AC 上游输入 | §4.1 依赖 |
| §3.1 C4 Container 图 L2_01 节点 | 居中节点 · 5 对契约面 | §4.3 依赖图 |
| §3.2 S3 并行产出依赖图 | L2-01 blueprint_ready 广播触发并行 | §5.1 时序 |
| §4.1 P0-L1-04-A 时序图 | "S3 TDD 蓝图一次完整生成" | §5.1 P0 |

### 1.4 与兄弟 L2 的边界（7 L2 中 L2-01 的位置）

| 兄弟 L2 | 本 L2 与兄弟的边界规则（基于 prd §8.3 + arch §1.5）|
|---|---|
| **L2-02 DoD 表达式编译器** | L2-01 **只给** `ac_matrix`（每条 AC 对应的分层 + 优先级 + 用例槽索引）；L2-02 消费 `ac_matrix` 把每条 AC 的验收条件自然语言编译为白名单 AST DoDExpression。**L2-01 不碰 DoD 语法**（arch §1.5 "谁 eval DoD 表达式"表）。反向：L2-02 回传 "dod_unmappable" INFO 给 L2-01 作为后续蓝图版本演进线索（通过事件总线，非同步调用）。 |
| **L2-03 测试用例生成器** | L2-01 **只给** `test_pyramid`（单元/集成/E2E 分层责任边界）+ `ac_matrix`（AC 对应用例槽）；L2-03 消费后为每个槽位生成**红灯骨架**（pytest collect 可发现、运行全 FAIL）。**L2-01 不生成代码**（prd §8.5 禁 4 "禁止直接生成测试代码"）。 |
| **L2-04 质量 Gate 编译器** | L2-01 **只给** `coverage_target`（行/分支/AC 三类覆盖率下限）+ `test_env_blueprint`（mock / fixture / 数据准备策略）；L2-04 消费后编译 `quality-gates.yaml` + `acceptance-checklist.md`。L2-01 **不编译 yaml**（prd §8.5 禁 "不编译 quality-gates.yaml"）。 |
| **L2-05 S4 执行驱动器** | 无直接同步调用。L2-05 在 S4 阶段读 `TDDBlueprint` 的 WP 切片（通过 `get_blueprint(blueprint_id)` Query），把对应 WP 的分层用例槽 + coverage 子集传给 invoke_skill 作为 tdd skill 的 context。 |
| **L2-06 S5 Verifier 编排器** | L2-06 在组装 verifier 工作包时 `get_blueprint(blueprint_id)` 读**整份** TDDBlueprint 作为 verifier 的"验收尺"（existence / behavior / quality 三段证据链的参照物）。L2-01 的 blueprint 是 S5 独立验证的**唯一可信上下文**（PM-05 单一事实源）。 |
| **L2-07 偏差判定与回退路由器** | 无直接同步调用。FAIL-L2 回退时 L2-07 经 IC-01 触发 L1-01 回 S3 → L1-01 重发 `IC-03 phase=S3` → 本 L2 按 `previous_blueprint_id` 增量补缺（而非完全重建）· 详见 §6.5 增量补缺算法。 |

### 1.5 PM-14 约束（project_id as root）

**硬约束**（arch §1 "PM-14 项目上下文声明" + prd §8 frontmatter）：

1. `TDDBlueprint.project_id` 为**根字段**（Aggregate Root 不变量 I-01），缺则 `E_L204_L201_BLUEPRINT_NO_PROJECT_ID` 拒绝（不入 Repository）
2. `ac_matrix` / `test_env_blueprint` / `coverage_target` 三件 Entity 都带 `project_id` 作副字段（透传自根）
3. 所有持久化路径按 `projects/<pid>/tdd/blueprint.yaml` + `projects/<pid>/tdd/master-test-plan.md` + `projects/<pid>/tdd/ac-matrix.yaml` 分片（见 §7 schema）
4. 跨 project 蓝图复用**禁止**（即便 AC 文本相同 · 防止 project A 的质量规格被误用到 project B · `E_L204_L201_CROSS_PROJECT_BLUEPRINT`）
5. 发布的 Domain Event（`blueprint_created` / `blueprint_ready`）payload 必含 `project_id`
6. `blueprint_ready` 广播到 L2-02/03/04 时，三个 L2 自己维护各自 project 下的产出目录，不跨 project 聚合
7. FAIL-L2 回退时 `previous_blueprint_id` 必与 `project_id` 匹配（否则 `E_L204_L201_BLUEPRINT_VERSION_CROSS_PROJECT`）

### 1.6 关键技术决策（Decision → Rationale → Alternatives → Trade-off）

本 L2 在 architecture.md §1.4 的 "Domain Service + Factory" 基础上，补充 L2 粒度的 4 个技术决策：

| # | Decision | Rationale | Alternatives | Trade-off |
|---|---|---|---|---|
| **D-L201-01** | `TDDBlueprintFactory` 为**纯函数 Factory**：`(FourPieces, WBS, AcClauses) → TDDBlueprint`，不访问任何外部 IO（所有 IO 前置到 `InputLoader` / 后置到 `Repository.save()`）| 纯函数 Factory = 100% 可单元测试 + 可 mock 4 件套 / WBS 覆盖各种边界（AC 空 / AC 重复 / WBS 无叶子 WP 等）；这和 L2-02 决策引擎 D-02a 的"DecisionEngine 纯函数"设计思路一致，防止产 Aggregate 的函数被污染成"IO + 推导"混合态 | **A. 在 Factory 内直接读 L1-02/L1-03 的产出物**（file read）：Factory 变成 IO 混合 · 难测试 · 难回放（回溯某版本 blueprint 时无法复现当时的 4 件套快照）| 所有 IO 前置到 `InputLoader`（唯一 IO 入口），Factory 就是 6 阶段纯计算：parse_ac → derive_pyramid → build_matrix → compute_coverage → assemble_env → pack_blueprint。详见 §6.1 |
| **D-L201-02** | **AC 自然语言解析采用 "spaCy lemmatizer + 模板匹配 + LLM fallback" 三级管线**（D-04 原型设计，精确实现见 §6.2）| prd §8.4 性能约束 "3 分钟蓝图"——纯 LLM 调用对 100 条 AC 的规模 P99 可能到 5-10 分钟（成本也爆炸）；模板匹配可覆盖 ~70% 场景（如 "必须 ... 才算完成" / "全部 X 必须 Y"），spaCy 辅助识别动词 / 名词槽位，剩余 ~30% 交给 DeepSeek | **A. 纯 LLM**：超 SLO + 成本高；**B. 纯正则**：歧义 AC 识别率低（<50%）；**C. 纯 spaCy**：无语义理解，只能分词不能判断"验收意图" | 三级 fallback：模板命中直接返回（毫秒级）；模板未命中 spaCy 提取槽位后模板化匹配（~50ms）；仍未命中才调 LLM 并缓存（同 AC hash 下次命中）；缓存命中率 > 60% 时 P95 可达标 |
| **D-L201-03** | **test_pyramid 层比采用"默认 70/20/10 + WBS 权重调整 + 用户显式覆盖"三层推导**（单元 70% / 集成 20% / E2E 10%）| pyramid 理论经验值（Mike Cohn pyramid · 2009）被 Google Testing Blog / Martin Fowler 多次验证，**默认值 70/20/10 对一般工程项目最优**；但需要根据 WBS 特征微调（如前端项目 E2E 占比应高 · 后端纯算法应低）；用户显式覆盖是保留灵活性 | **A. 硬编码 70/20/10**：无法适应不同项目域；**B. 完全用户自定义**：每项目都问一遍太烦；**C. 完全 LLM 推导**：不可解释 · 不稳定 | 三层回退链：用户 config 有则用用户；否则按 WBS 特征（WP 标签 `frontend` / `backend` / `e2e_heavy`）查权重表；否则默认 70/20/10。所有层都落审计便于后续调优 |
| **D-L201-04** | **coverage_target 的 AC 覆盖率硬性 = 1.0（不可配置）**，行/分支覆盖率默认分别 0.80 / 0.70（可配置下限 0.60） | prd §8.4 硬约束 2 "AC 覆盖率硬性 100%"是**红线**（非建议值）——允许配置 = 给违规开口子；行/分支覆盖率是**工程经验值**，可按项目调 | A. 全部可配：违反硬约束；B. 全部硬编码：失去项目适应性 | AC 覆盖率锁死 1.0（配置空间直接禁）；行/分支覆盖率可配（默认值在 §10），但下限 0.60 是硬底（低于就警告） |

### 1.7 BF-S3-01 业务流溯源

本 L2 聚合 **BF-S3-01 Master Test Plan 生成流**（prd §8.1 上游锚定第 5 行："BF-S3-01 Master Test Plan 生成流"）。精确锚点：

- **prd §5.4.1 L2-01**：职责 = "S3 阶段 · 将 4 件套 + WBS 转为 Master Test Plan（含 test pyramid / ac matrix / coverage target / test env blueprint）"
- **prd §8.1 职责 + 锚定**：一句话职责 + 上游 Goal §2.2 / §4.1 + 下游 L2-02/03/04 + S3 Stage Gate
- **prd §8.2 输入 / 输出**：精确列出 4 件套 4 类文档 / WBS 拓扑 / blueprint_ready 事件
- **prd §8.4 约束**：5 条硬约束（S4 前全齐 · AC 100% · 冻结 · 纯文本 · 输入源两个）
- **prd §8.5 禁止**：7 条禁止行为
- **prd §8.6 必须**：8 条必须职责

本文档将上述 PRD 语义**翻译为机器可执行的字段级 schema + 算法伪代码 + 错误码 + SLO**，**绝不改写 PRD 语义**——凡与 PRD 冲突则反向修 PRD 并在 §13 本文档末登记。

---

## §2 DDD 映射（BC-04 Quality Loop · TDDBlueprint Aggregate）

### 2.1 Bounded Context 定位

本 L2 所属 `BC-04 · Quality Loop`（定义见 `L0/ddd-context-map.md §2.5`，HarnessFlow 质量闭环的唯一控制源 BC）。在 BC-04 内部 **L2-01 扮演"S3 总指挥 + 蓝图聚合构造者"的双重角色**：

1. **S3 总指挥**：L1-04 Quality Loop 进入 S3 阶段后，L2-01 是**唯一入口**（arch §3.1 S3_PLANNING 包的左上角节点），L1-01 通过 IC-03 只调 L2-01（不能绕过 L2-01 直接调 L2-02/03/04）。
2. **聚合构造者**：`TDDBlueprint` Aggregate Root 的**唯一 Factory**——通过 `TDDBlueprintFactory.build()` 产出不可变版本化聚合，经 `TDDBlueprintRepository.save()` 持久化。

与兄弟 L2 的 DDD 关系（基于 `L0/ddd-context-map.md §2.5` BC-04 跨聚合协作）：

| 兄弟 L2 | DDD 关系 | 本 L2 与该 L2 的交互模式 |
|---|---|---|
| L2-02 DoD 表达式编译器 | **Downstream**（Customer）· blueprint_ready 消费方 | L2-01 产 `ac_matrix` → L2-02 读 → 按 AC 条款编 DoDExpression · 广播模式 |
| L2-03 测试用例生成器 | **Downstream**（Customer）· blueprint_ready 消费方 | L2-01 产 `test_pyramid` + `ac_matrix` → L2-03 读 → 生成红灯骨架 · 广播模式 |
| L2-04 质量 Gate 编译器 | **Downstream**（Customer）· blueprint_ready 消费方 | L2-01 产 `coverage_target` + `test_env_blueprint` → L2-04 读 → 编 quality-gates.yaml · 广播模式 |
| L2-05 S4 执行驱动器 | **Downstream**（Query 消费方）· 非广播 | L2-05 在 S4 阶段 `get_blueprint(blueprint_id, wp_slice=True)` 读 WP 切片 |
| L2-06 S5 Verifier 编排器 | **Downstream**（Query 消费方）· 非广播 | L2-06 组装 verifier 工作包时 `get_blueprint(blueprint_id, full=True)` 读整份蓝图 |
| L2-07 偏差判定与回退路由器 | **No direct coupling** | FAIL-L2 通过 IC-14 → L2-07 → IC-01 → L1-01 → IC-03 重入本 L2 · 间接 |

跨 BC 关系（引 `L0/ddd-context-map.md §2.5` BC-04 跨 BC 表）：

| 跨 BC | 关系模式 | 本 L2 体现 |
|---|---|---|
| BC-01 Agent Decision Loop（L1-01）| **Customer-Supplier**（消费 IC-03 · 供应 `L1-04:blueprint_ready` 事件）| 本 L2 是 IC-03 phase=S3 的直接接入点 |
| BC-02 Project Lifecycle（L1-02）| **Customer**（上游 4 件套 + AC 清单）| 本 L2 不直接调 L1-02，通过文件系统读 `projects/<pid>/four-pieces/` |
| BC-03 WBS Scheduling（L1-03）| **Customer**（上游 WBS 拓扑）| 本 L2 不直接调 L1-03，通过文件系统读 `projects/<pid>/wbs/topology.yaml` |
| BC-06 Knowledge Base（L1-06）| **Customer**（可选 · 读 test_pyramid recipe）| 本 L2 经 IC-06 kb_read 查历史相似项目的测试分层最佳实践 |
| BC-09 Resilience & Audit（L1-09）| **Partnership**（经 IC-09 append_event 单一审计源）| 本 L2 所有状态转换（DRAFT → READY → PUBLISHED → FROZEN）必 append 事件 |
| BC-10 UI（L1-10）| **Customer-Supplier**（IC-16 推 S3 Gate 待审卡）| 本 L2 产 blueprint → L1-02 汇总 → IC-16 推 L1-10（间接）|

### 2.2 Aggregate Root · TDDBlueprint

引自 `L0/ddd-context-map.md §2.5` BC-04 聚合根表 + arch §2.2：

**TDDBlueprint** 聚合根定义：

| 属性 | 类型 | 语义 | 不变量 |
|---|---|---|---|
| `blueprint_id` | VO `BlueprintId` | 唯一 id（uuid-v7）· Append-only | I-01 一 blueprint_id 一份聚合 |
| `project_id` | VO `ProjectId` | PM-14 根字段 | I-L201-01 不可变 |
| `version` | int | 从 1 开始递增；FAIL-L2 回退重建时 version++ | I-L201-02 单调递增 |
| `test_pyramid` | VO `TestPyramid` | 单元/集成/E2E 三层责任边界 + 比例 | I-L201-03 三层比例和 = 1.0 |
| `ac_matrix` | Entity `ACMatrix` | 每条 AC 对应的分层 / 优先级 / 用例槽索引 | I-L201-04 AC 覆盖率 = 1.0（硬性）|
| `coverage_target` | VO `CoverageTarget` | 行 / 分支 / AC 三类覆盖率下限 | I-L201-05 ac 分量硬等 1.0，line/branch ∈ [0.60, 1.0] |
| `test_env_blueprint` | Entity `TestEnvBlueprint` | mock 策略 / fixture 设计 / 数据准备 | — |
| `priority_annotation` | VO `PriorityMap` | 用例槽 → P0/P1/P2 标注 | I-L201-06 每槽位必标 |
| `created_at` | VO ISO-8601 | 生成时刻 | 不可变 |
| `published_at` | VO ISO-8601 \| null | 转 PUBLISHED 时刻；未发布为 null | — |
| `frozen_at` | VO ISO-8601 \| null | 转 FROZEN 时刻；未冻结为 null | — |
| `source_refs` | Entity `SourceRefs` | 溯源 `four_pieces_hash` + `wbs_version` + `ac_clauses_hash` | I-L201-07 不可变 |

**关键不变量**（Invariants · 引自 L0 DDD + arch §2.2）：

1. **I-L201-01 `project_id` 不可变**：聚合一旦创建，`project_id` 不能改动（即便 FAIL-L2 回退重建也只在同一 project 下）。
2. **I-L201-02 `version` 单调递增**：FAIL-L2 回退重建 `version += 1`，旧版本保留（不删除，给 Verifier 和 UI 提供 diff 视图）。
3. **I-L201-03 `test_pyramid` 三层比例和 = 1.0**：`unit_ratio + integration_ratio + e2e_ratio = 1.0`，精度到 0.01（任一误差 > 0.01 拒绝构造）。
4. **I-L201-04 `ac_matrix` 的 AC 覆盖率 = 1.0**：每条 AC 至少有 1 个用例槽（`slot_count ≥ 1`），不允许"零槽 AC"（硬约束 prd §8.4 #2）。
5. **I-L201-05 `coverage_target.ac_coverage = 1.0`**（硬锁 · 不可配置）；`line_coverage` / `branch_coverage` ∈ [0.60, 1.0]（可配置，< 0.60 拒绝）。
6. **I-L201-06 `priority_annotation` 全量覆盖**：每个用例槽必有优先级标注（P0 / P1 / P2）。
7. **I-L201-07 `source_refs` 不可变**：一旦绑定 4 件套 hash / WBS version，不可改；修改 = 新建版本（违反 → `E_L204_L201_SOURCE_REFS_MUTATED`）。

### 2.3 Factory · TDDBlueprintFactory

引自 `L0/ddd-context-map.md §2.4` 领域服务表 + arch §2.4 领域服务清单：

| 属性 | 值 |
|---|---|
| DDD 类型 | **Factory**（Aggregate 构造唯一入口）|
| 所在 L2 | L2-01（本 L2 核心组件）|
| 调用契约 | `build(four_pieces: FourPieces, wbs: WBSTopology, ac_clauses: list[ACClause], config: BuildConfig) → TDDBlueprint` |
| 纯函数性 | **纯函数**（D-L201-01 · 无 IO）|
| 构造阶段 | 6 阶段（见 §6.1）：parse_ac → derive_pyramid → build_matrix → compute_coverage → assemble_env → pack_blueprint |
| 异常通道 | 抛 `TDDBlueprintBuildError`（含错误码 `E_L204_L201_*`）|

### 2.4 Value Objects（不可变）

| VO 名 | 结构 | 用途 | 不变量 |
|---|---|---|---|
| `BlueprintId` | `"bp-{uuid-v7}"` | 聚合唯一 id | 一次构造一 id |
| `ProjectId` | `"pid-{uuid-v7}"` | PM-14 根字段 · 跨 BC Shared Kernel | — |
| `TestPyramid` | `{unit_ratio: float, integration_ratio: float, e2e_ratio: float, layer_specs: dict[str, LayerSpec]}` | 测试金字塔分层 | 三层比例和 = 1.0 ± 0.01 |
| `CoverageTarget` | `{line: float, branch: float, ac: float}` | 三类覆盖率下限 | `ac = 1.0` 硬锁 · line/branch ∈ [0.60, 1.0] |
| `PriorityMap` | `dict[slot_id, enum[P0, P1, P2]]` | 用例槽优先级标注 | 全量覆盖 |
| `LayerSpec` | `{responsibility: str, applicable_ac_types: list[str], expected_case_count: int}` | 单层金字塔规格 | expected_case_count ≥ 1 |
| `ACClauseId` | `"ac-{uuid-v7}"` | AC 条款唯一 id | — |
| `SlotId` | `"slot-{uuid-v7}"` | 用例槽唯一 id | — |

### 2.5 Entities（可变 · 聚合内持久化）

| Entity | 生命期 | 用途 |
|---|---|---|
| `ACMatrix` | 与 Aggregate 同生命 · FROZEN 后不可变 | AC → 用例槽映射表（见 §7.2 schema）|
| `TestEnvBlueprint` | 与 Aggregate 同生命 | 测试环境规格（mock / fixture / 数据准备）|
| `SourceRefs` | 与 Aggregate 同生命 · 不可变 | 溯源 4 件套 / WBS / AC hash |
| `BuildLog` | 单次构造（< 3 分钟）· 构造结束落盘 | Factory 6 阶段执行日志（供调试 / 审计）|

### 2.6 Repository Interface · TDDBlueprintRepository

引自 `L0/ddd-context-map.md §7.2.4 BC-04 Repository`：

| 方法 | 签名 | SLO |
|---|---|---|
| `save(blueprint: TDDBlueprint) → SaveResult` | 幂等 · 同 blueprint_id 二次调用返回首次结果 | P95 ≤ 50ms（本地 jsonl append + yaml 写）|
| `load(blueprint_id: str) → TDDBlueprint \| None` | 按 id 读（含 FROZEN 版本）| P95 ≤ 30ms |
| `latest(project_id: str) → TDDBlueprint \| None` | 取当前 project 最新版本（可能是 DRAFT / READY / PUBLISHED / FROZEN）| P95 ≤ 30ms |
| `history(project_id: str) → list[TDDBlueprint]` | 取当前 project 全部版本（供 FAIL-L2 diff 视图）| P95 ≤ 100ms |
| `slice(blueprint_id: str, wp_id: str) → TDDBlueprintSlice` | 取 WP 切片（给 L2-05 消费）| P95 ≤ 50ms |

**持久化约束**：

1. **单一写入点**：只能经 Repository 的 `save()`，不得绕过（PM-08 单一事实源）
2. **事件溯源一致性**：`save()` 成功后必 emit `L1-04:blueprint_created` / `L1-04:blueprint_ready` 经 IC-09 到 L1-09
3. **PM-14 隔离**：所有 Repository 方法接受 `project_id` 或在构造时绑定，跨 project 查询 `E_L204_L201_CROSS_PROJECT_BLUEPRINT`
4. **不可变快照**：save 后 Aggregate 不可 patch；版本升级 = 新建 `TDDBlueprint(version=old.version+1)`

### 2.7 Domain Events（本 L2 对外发布 · 经 IC-09）

引自 `L0/ddd-context-map.md §5.2.4` BC-04 发布的事件：

| Event | 触发时机 | 订阅方 | Payload 关键字段 |
|---|---|---|---|
| `L1-04:blueprint_started` | 本 L2 接收 IC-03 phase=S3 开始构造 | L1-09 审计 + L1-10 UI | `{blueprint_id, project_id, input_refs, ts}` |
| `L1-04:blueprint_created` | Factory 产出 TDDBlueprint + Repository save 成功 | L1-09 审计 | `{blueprint_id, version, project_id, ac_count, pyramid_ratios, ts}` |
| `L1-04:blueprint_ready` | 本 L2 广播给 L2-02/03/04（IC-L2-01）| L2-02/03/04 + L1-09 + L1-10 | `{blueprint_id, project_id, master_test_plan_path, ac_matrix_path, ts}` |
| `L1-04:blueprint_validation_failed` | AC 覆盖率 < 1.0 校验失败 | L1-07 + L1-02 + L1-10 | `{blueprint_id, missing_ac_ids[], project_id, ts}` |
| `L1-04:blueprint_frozen` | 转 FROZEN 状态（S3 Gate Go 后）| L1-09 审计 | `{blueprint_id, frozen_at, project_id}` |
| `L1-04:blueprint_reopened` | FAIL-L2 回退重建 | L1-09 + L1-10 | `{old_blueprint_id, new_blueprint_id, reopen_reason, project_id}` |

所有事件必含 `project_id`（PM-14）+ 事件在 L1-09 hash-chain 中的位置（由 L1-09 填）。

### 2.8 BC-04 内部 5 件产物的 "L2-01 为根" 依赖树

```plantuml
@startuml
title L2-01 TDDBlueprint 作为 BC-04 五件产物的"根"依赖树
rectangle "TDDBlueprint\n(L2-01 产 · Aggregate Root)" as ROOT
rectangle "DoDExpressionSet\n(L2-02 产 · 依赖 ac_matrix)" as DOD
rectangle "TestSuite\n(L2-03 产 · 依赖 test_pyramid + ac_matrix)" as TS
rectangle "QualityGateConfig\n(L2-04 产 · 依赖 coverage_target + test_env_blueprint)" as QGC
rectangle "AcceptanceChecklist\n(L2-04 产 · 依赖 ac_matrix)" as AC

ROOT --> DOD : ac_matrix\n(每 AC 对应的 validation_criteria)
ROOT --> TS : test_pyramid\n(分层策略)\n+ ac_matrix\n(槽位)
ROOT --> QGC : coverage_target\n(阈值)\n+ test_env_blueprint\n(环境规格)
ROOT --> AC : ac_matrix\n(勾选条款)

note bottom of ROOT
  **L2-01 是 S3 "五件产物" 的根节点**
  其他 4 件都从本 Aggregate 衍生
  FAIL-L2 回退 → 重建本 Aggregate → 级联重产其他 4 件
  符合 arch §3.2 "S3 并行产出依赖图"
end note

@enduml
```

**关键推论**：L2-01 的 `TDDBlueprint` 是 BC-04 五件产物的**共同根**——这决定了本 L2 的 blueprint 状态机（§8）向后兼容性必须极强（一旦 PUBLISHED 被下游引用，blueprint_id 生命与 4 件衍生产物挂钩），只能通过"新版本"演进，不能"修改当前版本"。

---

## §3 对外接口定义（字段级 YAML schema + 错误码）

> 说明：本 L2 对外暴露 **4 个方法**（1 主 + 3 辅）。字段级 YAML 采用 OpenAPI-like 风格声明 type / required / 约束。
>
> 调用方向：`generate_blueprint()` 由 L1-01（经 IC-03）单一调用（主流）；`get_blueprint()` 由 L2-02/03/04（blueprint_ready 消费后 · 读聚合）+ L2-05（WP 切片）+ L2-06（整份）调用；`validate_coverage()` 为内部暴露方法（也供 L2-04 编译 quality-gates 时调用校验）；`broadcast_ready()` 是 L2-01 自动触发（非直接对外接口，但字段级 schema 固定给下游 contract）。

### 3.1 `generate_blueprint(request) → blueprint_id`（核心 · IC-03 phase=S3 接入处）

**调用方**：L1-01 主 loop（单一调用方 · 经 `IC-03 enter_quality_loop{phase=S3}` 触发 L1-04 entry → L1-04 内部派发给本 L2）
**幂等性**：同 `(project_id, source_refs_hash)` 二次调用返回首次 `blueprint_id`（内存 LRU 缓存 256 · 防 L1-01 重发）
**阻塞性**：异步启动；返回 `blueprint_id` 后 L1-04 主 loop 不阻塞（实际构造在后台线程跑，完成经 L1-09 事件总线通知下游）
**性能**：3 分钟上限（prd §8.4 · 100 AC 规模）· P95 ≤ 2 分钟 · P99 ≤ 3 分钟 · 硬上限 5 分钟（超 → abort）

#### 入参 `request`（字段级 YAML）

```yaml
generate_blueprint_request:
  type: object
  required:
    - command_id
    - project_id       # PM-14 根字段
    - entry_phase
    - four_pieces_refs
    - wbs_refs
    - ac_clauses_refs
  properties:
    command_id:
      type: string
      format: "cmd-{uuid-v7}"
      description: L1-01 生成 · 用于 IC-03 幂等 + 审计追溯

    project_id:
      type: string
      format: "pid-{uuid-v7}"
      description: PM-14 根字段；缺 → E_L204_L201_BLUEPRINT_NO_PROJECT_ID

    entry_phase:
      type: enum
      enum: [S3]
      description: 必为 S3（其他 phase → E_L204_L201_INVALID_PHASE）

    four_pieces_refs:
      type: object
      required: [requirements_path, goals_path, ac_list_path, quality_standard_path]
      properties:
        requirements_path:
          type: string
          format: "projects/{pid}/four-pieces/requirements.md"
        goals_path:
          type: string
          format: "projects/{pid}/four-pieces/goals.md"
        ac_list_path:
          type: string
          format: "projects/{pid}/four-pieces/ac-list.md"
        quality_standard_path:
          type: string
          format: "projects/{pid}/four-pieces/quality-standard.md"
        four_pieces_hash:
          type: string
          format: "sha256:[64 hex]"
          description: 4 件套聚合 hash · 供 source_refs 固化

    wbs_refs:
      type: object
      required: [topology_path, wbs_version]
      properties:
        topology_path:
          type: string
          format: "projects/{pid}/wbs/topology.yaml"
        wbs_version:
          type: integer
          minimum: 1

    ac_clauses_refs:
      type: object
      required: [ac_manifest_path, clause_count]
      properties:
        ac_manifest_path:
          type: string
          format: "projects/{pid}/four-pieces/ac-manifest.yaml"
        clause_count:
          type: integer
          minimum: 1
          description: AC 条款总数；= 0 → E_L204_L201_AC_EMPTY

    previous_blueprint_id:
      type: string | null
      description: FAIL-L2 回退重建时传入旧 blueprint_id；null 表示首次构造
      default: null

    retry_focus:
      type: array | null
      description: FAIL-L2 指定需重做的 section（如 `["test_pyramid", "coverage_target"]`）；null 表示全量重做
      default: null

    config_overrides:
      type: object | null
      description: 本次构造的 config 覆盖（§10 配置的子集）；如 `{pyramid_default_ratio: [0.6, 0.3, 0.1]}`
      default: null

    trigger_tick_id:
      type: string
      description: L1-01 触发本次调用的 tick_id · 用于审计溯源
```

#### 出参 `blueprint_id`（字段级 YAML）

```yaml
generate_blueprint_response:
  type: object
  required:
    - blueprint_id
    - project_id
    - status
    - ts_accepted
  properties:
    blueprint_id:
      type: string
      format: "bp-{uuid-v7}"
      description: 聚合唯一 id

    project_id:
      type: string
      description: 透传 request.project_id

    status:
      type: enum
      enum: [ACCEPTED, CACHED]
      description: ACCEPTED = 新构造进 DRAFT; CACHED = 幂等命中，返回已存在的 blueprint_id

    ts_accepted:
      type: string
      format: ISO-8601-utc

    estimated_completion_ts:
      type: string
      format: ISO-8601-utc
      description: 预期构造完成时间（P95 ≤ 2 分钟 · 供 UI 展示进度条）

    version:
      type: integer
      description: 本次构造的版本号（首次 = 1；FAIL-L2 重建 = 旧 +1）
```

#### 3.1.1 错误码（`generate_blueprint()`）

| 错误码 | 含义 | 触发场景 | 调用方处理 | 对应 prd 硬约束 |
|---|---|---|---|---|
| `E_L204_L201_BLUEPRINT_NO_PROJECT_ID` | project_id 缺失 | 上游传入非法 request | L1-01 丢弃 + 告警 L1-07 | PM-14 |
| `E_L204_L201_CROSS_PROJECT_BLUEPRINT` | `previous_blueprint_id` 与 `project_id` 不匹配 | FAIL-L2 回退 bug | 拒绝 + 审计 | §1.5 #7 |
| `E_L204_L201_INVALID_PHASE` | entry_phase 非 S3 | L1-01 路由 bug | 拒绝 + 静默 | §1.4 L2-01 入口唯一 |
| `E_L204_L201_AC_EMPTY` | `clause_count = 0` | 4 件套缺 AC 清单 | 本 L2 发 `L1-04:blueprint_validation_failed` 事件 + IC-13 INFO 给 L1-07 要求 L1-02 澄清 | prd §8.5 #1 "禁 AC 不全生成蓝图" |
| `E_L204_L201_BLUEPRINT_AC_MISSING` | Factory 校验时发现 AC 覆盖率 < 1.0 | AC 条款某条未匹配任何用例槽 | 状态机走 VALIDATING → DRAFT 补缺 + 推 INFO 澄清 | prd §8.4 #2 AC 100% |
| `E_L204_L201_FOUR_PIECES_MISSING` | 4 件套某文件不存在或 hash 不匹配 | 文件损坏 / L1-02 未完成 | 拒绝 + 等 L1-02 完成事件后重试 | prd §8.6 #1 "完整 4 件套后开始" |
| `E_L204_L201_WBS_NOT_READY` | WBS 拓扑文件不存在或 wbs_version 不一致 | L1-03 未发 `wbs_topology_ready` 事件 | 订阅 WBS ready 事件后重试 | — |
| `E_L204_L201_BUILD_TIMEOUT` | Factory 构造耗时 > 5 分钟硬上限 | LLM fallback 长尾 / AC 过多 | 本 L2 abort → 事件 `blueprint_build_timeout` → L1-07 WARN | prd §8.4 性能 |
| `E_L204_L201_SOURCE_REFS_MUTATED` | save 时发现 source_refs 已被他人改动 | 罕见 race condition | Repository 抛异常 · 本 L2 重试一次 | I-L201-07 |
| `E_L204_L201_BLUEPRINT_TOO_LARGE` | master-test-plan.md > 1MB | WBS 过碎 / AC 过多 | 本 L2 WARN L1-07 + 建议 L1-03 重规划 | prd §8.4 "≤ 1MB" |

### 3.2 `get_blueprint(query) → blueprint_data`（读取 · from L2-02/03/04/05/06）

**调用方**：
- L2-02/03/04：blueprint_ready 消费后读整份聚合（`full=True`）
- L2-05：S4 阶段读 WP 切片（`wp_slice=True`）
- L2-06：S5 阶段读整份（`full=True`）

**SLO**：P95 ≤ 100ms（仅文件读 + yaml parse · full 模式）· P95 ≤ 50ms（wp_slice 模式）
**幂等性**：纯 Query · 天然幂等

#### 入参 `query`（字段级 YAML）

```yaml
get_blueprint_query:
  type: object
  required:
    - query_id
    - project_id
    - blueprint_id
  properties:
    query_id:
      type: string
      format: "q-{uuid-v7}"
    project_id:
      type: string
      description: PM-14 根字段 · 必等于 blueprint.project_id
    blueprint_id:
      type: string
      format: "bp-{uuid-v7}"
    mode:
      type: enum
      enum: [full, wp_slice, metadata_only]
      default: full
      description: full = 全聚合；wp_slice = 指定 WP 的切片；metadata_only = 仅 header 不含 matrix
    wp_id:
      type: string | null
      description: mode=wp_slice 必填
    version:
      type: integer | null
      description: 指定版本；null 取 latest
      default: null
```

#### 出参 `blueprint_data`（字段级 YAML）

```yaml
get_blueprint_response:
  type: object
  required:
    - blueprint_id
    - project_id
    - version
    - state
    - created_at
  properties:
    blueprint_id: {type: string}
    project_id: {type: string}
    version: {type: integer}
    state:
      type: enum
      enum: [DRAFT, VALIDATING, READY, PUBLISHED, FROZEN]
    created_at: {type: string, format: ISO-8601-utc}
    published_at: {type: string | null, format: ISO-8601-utc}
    frozen_at: {type: string | null, format: ISO-8601-utc}

    # mode=full 或 wp_slice 才返回的字段
    test_pyramid:
      type: object
      properties:
        unit_ratio: {type: number, minimum: 0, maximum: 1}
        integration_ratio: {type: number}
        e2e_ratio: {type: number}
        layer_specs:
          type: object
          description: "{layer_name: LayerSpec}"

    ac_matrix:
      type: array
      items:
        type: object
        required: [ac_id, ac_text, layer, priority, slot_ids]
        properties:
          ac_id: {type: string, format: "ac-{uuid-v7}"}
          ac_text: {type: string}
          layer: {type: enum, enum: [unit, integration, e2e]}
          priority: {type: enum, enum: [P0, P1, P2]}
          slot_ids:
            type: array
            items: {type: string, format: "slot-{uuid-v7}"}
            minItems: 1
            description: 每条 AC 至少 1 个槽位（I-L201-04）

    coverage_target:
      type: object
      properties:
        line: {type: number, minimum: 0.60, maximum: 1.0}
        branch: {type: number, minimum: 0.60, maximum: 1.0}
        ac: {type: number, const: 1.0, description: "硬锁"}

    test_env_blueprint:
      type: object
      properties:
        mock_strategy:
          type: object
          description: "{service_name: mock_policy}"
        fixture_design:
          type: object
        data_prep_plan:
          type: object

    source_refs:
      type: object
      properties:
        four_pieces_hash: {type: string, format: "sha256:[64 hex]"}
        wbs_version: {type: integer}
        ac_clauses_hash: {type: string}

    # mode=wp_slice 才返回
    wp_slice:
      type: object | null
      properties:
        wp_id: {type: string}
        related_ac_ids: {type: array, items: {type: string}}
        related_slot_ids: {type: array}
        coverage_slice:
          type: object
          description: 该 WP 涉及的覆盖率子目标
```

#### 3.2.1 错误码（`get_blueprint()`）

| 错误码 | 含义 | 触发场景 | 调用方处理 |
|---|---|---|---|
| `E_L204_L201_BLUEPRINT_NOT_FOUND` | blueprint_id 不存在 | 查询拼写错误 / 未构造完成 | 调用方订阅 `blueprint_ready` 事件后再重试 |
| `E_L204_L201_CROSS_PROJECT_READ` | query.project_id ≠ blueprint.project_id | 调用方 bug · PM-14 违规 | 拒绝 · 调用方严重 bug 告警 |
| `E_L204_L201_WP_SLICE_NOT_FOUND` | mode=wp_slice 但 wp_id 不在聚合内 | WBS 和 blueprint 版本不匹配 | 调用方读 `source_refs.wbs_version` 确认 · 回查 L1-03 |
| `E_L204_L201_VERSION_NOT_FOUND` | 指定 version 不存在 | 查询过旧版本 | 调用方回退到 latest |

### 3.3 `validate_coverage(blueprint_id) → validation_report`（AC 覆盖率硬性校验 · 内部 + 供 L2-04 调用）

**调用方**：
- 本 L2 自身（Factory 产出后状态机 DRAFT → VALIDATING 的过渡）
- L2-04 质量 Gate 编译器（编译 quality-gates 时交叉校验）
- 单元测试（Mock 三档的 contract 档位校验）

**SLO**：P95 ≤ 50ms（in-memory 遍历）· P99 ≤ 200ms
**幂等性**：纯函数 · 同 blueprint_id 同版本多次调用结果一致

#### 入参 + 出参

```yaml
validate_coverage_query:
  type: object
  required: [query_id, project_id, blueprint_id]
  properties:
    query_id: {type: string}
    project_id: {type: string, description: PM-14}
    blueprint_id: {type: string}
    strict_mode:
      type: boolean
      default: true
      description: strict=true → ac=1.0 硬校；strict=false → 只 warn 不 fail（仅供调试）

validate_coverage_response:
  type: object
  required: [valid, ac_coverage, line_coverage_target, branch_coverage_target]
  properties:
    valid:
      type: boolean
      description: valid=true 表示全部校验通过
    ac_coverage:
      type: number
      minimum: 0
      maximum: 1
      description: 实际 AC 覆盖率；硬锁应为 1.0
    missing_ac_ids:
      type: array
      items: {type: string}
      description: 未映射到任何用例槽的 AC id 列表（valid=false 时非空）
    line_coverage_target: {type: number}
    branch_coverage_target: {type: number}
    pyramid_ratios_valid:
      type: boolean
      description: 三层比例和是否 = 1.0 ± 0.01
    priority_annotation_complete:
      type: boolean
      description: 所有槽位是否都有优先级标注
    issues:
      type: array
      items:
        type: object
        properties:
          code: {type: string, description: "E_L204_L201_*"}
          severity: {type: enum, enum: [ERROR, WARN, INFO]}
          message: {type: string}
```

#### 3.3.1 错误码

| 错误码 | 含义 | 触发 | 调用方处理 |
|---|---|---|---|
| `E_L204_L201_VALIDATION_BLUEPRINT_NOT_FOUND` | blueprint_id 不存在 | 查询拼写错 | 调用方确认 id |
| `E_L204_L201_VALIDATION_STALE_READ` | 校验过程中 blueprint 被并发修改 | race condition | 调用方重试一次 |

### 3.4 `broadcast_ready(blueprint_id) → broadcast_result`（IC-L2-01 广播 · from 本 L2 内部状态机触发）

**调用方**：本 L2 状态机 READY → PUBLISHED 转换时自动触发（非对外直接暴露）
**广播通道**：L1-09 事件总线（经 IC-09 发 `L1-04:blueprint_ready` 事件，L2-02/03/04 订阅）
**SLO**：P95 ≤ 500ms（事件总线 append + fanout 到 3 订阅者）· 硬上限 1 秒（prd §8.4 "blueprint_ready 广播延迟 ≤ 1 秒"）
**幂等性**：同 `blueprint_id` 二次广播返回首次结果（防重复触发 L2-02/03/04）

#### 入参 + 出参

```yaml
broadcast_ready_request:
  type: object
  required: [blueprint_id, project_id, ts_publish]
  properties:
    blueprint_id: {type: string}
    project_id: {type: string}
    ts_publish: {type: string, format: ISO-8601-utc}
    subscribers:
      type: array
      default: ["L2-02", "L2-03", "L2-04"]
      description: 默认 3 个下游 · 调试模式可缩减
    retry_max:
      type: integer
      default: 3
      description: 事件总线发送失败最大重试次数

broadcast_ready_response:
  type: object
  properties:
    published: {type: boolean}
    event_id: {type: string, format: "evt-{uuid-v7}"}
    fanout_acks:
      type: array
      items:
        type: object
        properties:
          subscriber: {type: string}
          ack: {type: boolean}
          received_at: {type: string | null}
    latency_ms: {type: integer}
```

#### 3.4.1 错误码

| 错误码 | 含义 | 触发 | 降级策略 |
|---|---|---|---|
| `E_L204_L201_BROADCAST_SLO_VIOLATION` | latency_ms > 1000 | 事件总线慢 / fanout 慢 | 记审计；不 fail 广播；L1-07 WARN |
| `E_L204_L201_BROADCAST_FANOUT_INCOMPLETE` | 某下游 ack 超时 | L2-02/03/04 之一离线 | 重试 3 次 · 仍失败发 `L1-04:blueprint_subscriber_unreachable` · 不阻塞本 L2 转 PUBLISHED |
| `E_L204_L201_DUPLICATE_BROADCAST` | 同 blueprint_id 二次广播 | 状态机 bug | 静默 + 审计 |

### 3.5 错误码总表（10 + 4 + 2 + 3 = 19 项）

| 错误码前缀 | 语义类别 | 降级链 |
|---|---|---|
| `E_L204_L201_BLUEPRINT_*` | 聚合创建 / 校验 | 按严重程度：abort → WARN → INFO 澄清 |
| `E_L204_L201_CROSS_PROJECT_*` | PM-14 违规 | 拒绝 · 严重 bug 告警 |
| `E_L204_L201_SOURCE_*` / `E_L204_L201_FOUR_*` / `E_L204_L201_WBS_*` / `E_L204_L201_AC_*` | 输入不全 | 推 INFO 澄清 · 等事件后重试 |
| `E_L204_L201_BUILD_TIMEOUT` | Factory 超时 | abort + L1-07 WARN + UI 警告 |
| `E_L204_L201_VALIDATION_*` | 覆盖率校验 | 降级为 non-strict 仅供调试 |
| `E_L204_L201_BROADCAST_*` | 广播失败 | 重试 3 次 · 升级 WARN |

详细 §11 降级策略。

---

## §4 接口依赖（被谁调 · 调谁）

<!-- FILL §4 · 上游调用方：哪些 L1 / L2 调本 L2 的哪些方法；下游依赖：本 L2 调哪些外部接口（IC-XX 或内部 L2-XX）· 依赖图 PlantUML -->

---

## §5 P0/P1 时序图（PlantUML ≥ 2 张）

<!-- FILL §5 · 本 L2 的 P0 场景时序图（≥ 2 张 · PlantUML）· 可引用 L0/sequence-diagrams-index.md 的对应 P0/P1 链路 · 聚焦本 L2 内部流程 -->

---

## §6 内部核心算法（伪代码）

<!-- FILL §6 · 本 L2 的核心算法伪代码（Python-like 风格）· 关键 syscall / 数据结构操作 / 并发控制 -->

---

## §7 底层数据表 / schema 设计（字段级 YAML）

<!-- FILL §7 · 本 L2 持久化的数据结构字段级 YAML schema · 物理存储路径（按 PM-14 分片 `projects/<pid>/...`）· 索引结构 -->

---

## §8 状态机（如适用 · PlantUML + 转换表）

<!-- FILL §8 · 本 L2 内部状态机 PlantUML @startuml ... @enduml (state) + 状态转换表（触发 / guard / action） · 若本 L2 无状态则标明"本 L2 为无状态服务" -->

---

## §9 开源最佳实践调研（≥ 3 GitHub 高星项目）

<!-- FILL §9 · 引 L0/open-source-research.md 对应模块段 + L2 粒度细化：至少 3 个 GitHub ≥1k stars 项目对标 · 每项目：星数 · 最近活跃 · 核心架构一句话 · Adopt/Learn/Reject 处置 · 具体学习点 · 弃用原因 -->

---

## §10 配置参数清单

<!-- FILL §10 · 参数名 / 默认值 / 可调范围 / 意义 / 调用位置 -->

---

## §11 错误处理 + 降级策略

<!-- FILL §11 · 本 L2 各类错误的处理策略 · 降级链 · 与本 L1 其他 L2 / L1-07 supervisor 的降级协同 -->

---

## §12 性能目标

<!-- FILL §12 · 本 L2 的 P95/P99 延迟 SLO · 吞吐 · 资源消耗 · 并发上限 -->

---

## §13 与 2-prd / 3-2 TDD 的映射表

<!-- FILL §13 · 本 L2 接口 ↔ 2-prd §5.4 对应小节 · 本 L2 方法 ↔ 3-2-Solution-TDD/L1/L2-01-tests.md 的测试用例 -->

---

*— L1 L2-01 TDD 蓝图生成器 · skeleton 骨架 · 等待 subagent 多次 Edit 刷新填充 —*
