# HarnessFlow — 项目目标（Goal）

> 版本：v1.0 · 更新时间：2026-04-19
> 本文件定义 HarnessFlow 项目的**方向和意图**。每一条后续产出（PrdScope / PRD / Plan / 代码 / UI）都必须可追溯回本文件。

---

## 一、一句话目标

**HarnessFlow 是一个 Claude Code Skill 生态下的 "AI 技术项目经理 + 架构师"——以 PMP + TOGAF 双主干方法论为骨架，辅以 "规划 / 质量 / 拆解 / 检验 / 交付" 五大贯穿纪律，从 "项目目标 + 资源约束" 出发，以 methodology-paced 方式（规划协同 / 执行自走 / 交付强 Gate）端到端自治推进一个超大型复杂软件项目，最终产出可运行、可交付、可审计的软件产品 + 完整项目文档。**

---

## 二、产品定位

### 2.1 是什么 / 不是什么

**是**：
- 把 PMP + TOGAF 方法论硬编进决策骨架的单路线 meta-orchestrator
- 以主 Skill Agent loop 为执行核心、监督 Agent 为旁路审计的双 Agent 协作系统
- 调度整个 Claude Code Skill 生态（superpowers / gstack / everything-claude-code / 自定义）的高阶调度器
- 产出完整 PMP 产出物包 + TOGAF 架构产出物包的方法论落地机器

**不是**：
- ❌ 不是 AI 工程师（不替代 Devin / Cursor / Claude Code 写代码）
- ❌ 不是 AI 助理（不做 ChatGPT 式闲聊 / 问答）
- ❌ 不是 PM 工具（不做 Jira / Linear 看板替代）
- ❌ 不是通用 Agent 框架（不做 LangGraph / CrewAI 替代）
- ❌ 不是 Scrum / 敏捷 Agent（专注 PMP + TOGAF 细分）
- ❌ 不是商业 SaaS（产品形态锁定为开源 Claude Code Skill）

### 2.2 方法论骨架：双层结构

**第一层 · 主骨架（结构维度）**

PMP 5 过程组 × TOGAF 9 ADM 阶段 = 双主干编织矩阵：
- PMP 过程组：启动 → 规划 → 执行 → 监控（贯穿）→ 收尾
- TOGAF ADM：预备 → A 愿景 → B 业务 → C 信息系统 → D 技术 → E 机会方案 → F 迁移 → G 实施治理 → H 变更管理 + 需求管理贯穿
- 两条线在每个阶段交叉点定义必须产出的 PMP 工件 + TOGAF 工件，形成可审计的二维推进表

**第二层 · 五大纪律（品质维度）**

无论走到哪个 PMP 过程组、哪个 TOGAF 阶段，以下五件事必须被反复拷问、贯穿始终：

| 纪律 | 一句话定义 |
|---|---|
| **规划** | 当前阶段有没有清晰可执行的计划 + DoD |
| **质量** | 当前产出物是否满足质量标准，有无 TDD / 审查 / 证据链 |
| **拆解** | 当前 Work Package 是否被拆到可执行粒度（WBS） |
| **检验** | 有没有独立 verifier 对 DoD 逐条判定 + 三段证据链 |
| **交付** | 每个阶段是否产出可消费、可验收、可审计的交付物 |

主骨架保证结构正统，五大纪律保证每步都有品质。两者不可偏废。

### 2.3 超大项目的消化方式：WP 拓扑

超大型项目不是一次跑完的。主 Agent 按业务模块 / 架构边界把项目拆成若干 Work Package（WP）：

- 每个 WP 有独立 Goal、独立 DoD、独立工时预估、依赖关系（拓扑序）
- 主 Agent loop 每次只调度 1-2 个 WP 并行推进，避免认知爆炸
- 每个 WP 内部都走完整的小号 PMP 过程组 + 所需 TOGAF 阶段
- WP 级失败不污染整个项目，只回本 WP 重跑或 replan
- 全部 WP 完成 = 整个项目交付

### 2.4 全局灵魂：harnessFlowProjectId

HarnessFlow 每承接一个超大软件项目时，在 S1 启动阶段生成一个**全局唯一、不可变**的 `harnessFlowProjectId` 作为项目"灵魂"：

- **归属根键**：所有运行数据 / 决策 / 产出物 / 任务 / 测试 / 监督事件 / KB 条目都归属到这个 ID
- **隔离边界**：多会话恢复、多项目并发（V2+）按此 ID 做强隔离——不同 project 的数据物理 + 逻辑都不互通
- **生命周期锚**：ID 与项目主状态机（INITIALIZED → PLANNING → TDD_PLANNING → EXECUTING → CLOSING → CLOSED）1:1 对齐
- **可审计根**：retro / archive / failure-archive / 跨 session 恢复全部以此 ID 为主键

若缺失此概念，系统的"可追溯 / 可恢复 / 可审计 / 可分享"四大能力全部坍塌。**详见 `docs/2-prd/L0/projectModel.md`**。

---

## 三、输入 / 输出 / 过程

### 3.1 输入

- **项目目标**：一句话到若干段落的自然语言描述
- **资源约束**：预算、时间窗、技术栈偏好、可用团队、现有仓库、合规要求
- **启动模式**：全新项目（Greenfield）/ 改造已有代码库（Brownfield）/ 多仓库协调

### 3.2 输出

**A. 可运行的软件产品**
- 完整代码仓库（git commit + optional PR / push）
- 配置文件 + 环境说明
- 部署脚本或部署指南
- README + 使用文档

**B. 完整 PMP 产出物包**
- 项目章程
- 9 大计划（范围 / 进度 / 成本 / 质量 / 资源 / 沟通 / 风险 / 采购 / 干系人整合）
- WBS 工作分解结构
- 风险登记册
- 阶段状态报告
- 变更请求记录
- 交付物清单 + 验收文档
- 项目收尾报告 + 复盘（retro）

**C. 完整 TOGAF 架构产出物包**
- 架构愿景（A）/ 业务架构（B）/ 数据 + 应用架构（C）/ 技术架构（D）
- 候选方案对比 + 选型理由（E）
- 迁移路线图（F）
- 实施治理文档（G）
- 架构变更管理记录（H）
- ADR（架构决策记录）≥ 10 条

**D. 可审计的决策链 + 知识沉淀**
- 主 Agent 每次决策 + 理由
- 监督 Agent 每条建议 + 用户回应
- Verifier 每次 DoD 判定 + 三段证据链
- 用户每次介入 + 授权记录
- 项目结束后，有价值的 pattern / trap / tool_combo 自动晋升到 Project 或 Global 知识库

### 3.3 过程：Methodology-Paced Autonomy

不是匀速自治，而是按方法论阶段变速：

| 阶段 | PMP 过程组 | TOGAF ADM | 自治程度 | 人机互动 |
|---|---|---|---|---|
| **规划 / 架构** | 启动 + 规划 | 预备 + A-D | **强协同** | 主 Agent 主动请求澄清、章程确认、WBS + 架构评审 |
| **执行** | 执行 + 监控 | E + F + G（贯穿） | **执行自走** | 只在触碰红线 / 需要凭证 / 不可逆授权时打断 |
| **交付验收** | 收尾 | H | **强制 Stage Gate** | 用户 Go / No-Go 才能关闭 |

---

## 四、成功判定

### 4.1 V1 量化指标

- ✅ 至少跑通 1 个真实中等复杂度项目（1-3 周墙钟）从立项到交付
- ✅ PMP 产出物完整度 ≥ 85%
- ✅ TOGAF 产出物完整度 ≥ 75%
- ✅ 规划 / 架构阶段澄清轮次 ≤ 20 轮
- ✅ 执行阶段主动打断用户 ≤ 5 次 / 周
- ✅ 监督 Agent 3 红线准确率 100%（0 漏报）
- ✅ 可跨 session 无损恢复
- ✅ 决策可追溯率 100%（任一交付物可追到某次 Agent 决策）
- ✅ 用户主观打分 "这像真人 PMP + TOGAF 技术经理" ≥ 7/10

### 4.2 里程碑

| 里程碑 | 时间窗 | 判定 |
|---|---|---|
| **V1 MVP** | 6 月内 | 跑通 1 个中等复杂度项目全生命周期 |
| **V2 稳定** | 12 月内 | 跑通 1 个超大型项目；沉淀 50+ 有效 pattern 到 Global KB |
| **V3 扩展** | 18 月内 | 多项目并行；跨项目知识迁移 |

### 4.3 反向失败判定（任一命中即 Goal 未达成）

- ❌ 用户评价 "还不如自己拿 Claude Code 写快"
- ❌ PMP 完整度 < 60% 或 TOGAF < 40%
- ❌ 决策不可追溯
- ❌ 监督 Agent 漏过一次红线酿成不可逆事故
- ❌ 超大项目跑不起来，沦为 Devin 同质品

---

## 五、非目标（明确不做）

1. 不替代 AI 工程师（写代码交给下层 skill）
2. 不替代 PM 工具（不做 Jira / Linear 看板）
3. 不做通用 Agent 框架
4. 不追求"零人工介入"（三阶段必须人类参与是 feature）
5. 不做 Scrum / 敏捷 Master Agent
6. 不做非软件类项目
7. 不做商业 SaaS
8. 不自研 LLM
9. 不做 CI/CD 流水线
10. 不做移动端 / 桌面端 App
11. V1-V2 不做跨项目并行，同时只管一个项目

---

## 六、目标锚定声明

- **Goal（本文件）** = 方向 = "去哪里"
- **PrdScope（配套文件）** = 实体 = "建什么"
- **PRD / Plan / 代码 / UI** = 实施 = "怎么建"

**追溯关系**：
- 每条 PrdScope 功能 → 必须追溯回 Goal 某条目
- 每行 PRD / Plan / 代码 → 必须追溯回 PrdScope 某功能
- Goal 每条目 → 必须在 PrdScope 有对应实现

**按 PrdScope 把"房子"建成，Goal 即自动实现。**

---

## 附录 · 术语速查表

| 术语 | 含义 |
|---|---|
| **主 Skill Agent** | 在 loop 里持续决策、执行的 AI 智能体 |
| **监督 Agent（Supervisor）** | 旁路常驻、只读观察、8 维度 + 3 红线告警的独立 AI 智能体 |
| **WP（Work Package）** | 工作包。超大项目拆解后的可执行单元 |
| **Stage Gate** | 阶段门。PMP 过程组切换点的强制 Go/No-Go 检查 |
| **Methodology-Paced Autonomy** | 按方法论阶段变速的自治 |
| **DoD** | Definition of Done。可机器校验的完成谓词 |
| **Verifier** | 独立验证子 Agent。DoD 逐条 eval + 三段证据链 |
| **3 红线** | DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT |
| **KB 三层** | Global / Project / Session 知识库 |
| **ADR** | Architecture Decision Record |
| **五大纪律** | 规划 / 质量 / 拆解 / 检验 / 交付 |
| **harnessFlowProjectId** | 项目全局灵魂 ID。所有数据归属根键 + 多会话 / 多项目隔离键。详见 `docs/2-prd/L0/projectModel.md` |

---

*— Goal 文档完 —*
