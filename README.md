# harnessFlow

> Claude Code 的 **总编排 / 总监督 / 总路由** 元技能——让 agent 在说 "done" 之前，真的 done。

[![pytest](https://img.shields.io/badge/pytest-100_passed-brightgreen)]()
[![phases](https://img.shields.io/badge/Phase_1--8%20%2B%20v1.1-complete-brightgreen)]()
[![license](https://img.shields.io/badge/license-MIT-blue)]()

---

## 这是什么

**harnessFlow** 是一个 Claude Code **meta-skill（元技能）**——它本身**不造轮子**，只负责**编排**现有生态的 skill，为任务装上 "澄清 → 路由 → 监督 → 验证 → 归档 → 进化" 的完整链条。

一句话定位：**在 agent 说 "done" 之前，确保它真的 done。**

核心逻辑：

```
用户任务
  ↓
2-3 轮澄清 (size × task_type × risk 三维)
  ↓
查 42-cell routing matrix → Top-2 路线（A-F）
  ↓
调度既有 skill (Superpowers / everything-claude-code / gstack)
  ↓
Supervisor sidecar 全程监听 (3 红线即时停机)
  ↓
Verifier 独立收口 (DoD 布尔表达式 + 3 段证据链)
  ↓
retro 11 项 + failure-archive.jsonl (进化引擎)
```

---

## 为什么（P20 事件）

2026-04-16，某个 "AI 视频出片" 流水线跑完、agent 报告 "成功"。实际：

- ✗ 没起后端服务
- ✗ 没 POST 任何 API
- ✗ 没校验 mp4 是否存在
- ✗ 没校验 duration / OSS key / playback
- **"pipeline 无 error" ≠ "真出片成功"**

这类 **假完成** 不是个案——是 **所有公开 agent 框架（AutoGen / CrewAI / MetaGPT / Devin）共有的系统性盲区**。

harnessFlow 的核心 bet：

> **把 "真完成" 写进机制、写进 Verifier 布尔表达式、写进 Stop hook——而不是写进口号。**

---

## 三大引擎

| 引擎 | 职责 | 核心 artifact |
|---|---|---|
| **路由引擎** | 输入任务 → 查 42-cell matrix → 输出 `(route, plan_skill, impl_skill, verify_skill)` | `routing-matrix.md` + `flow-catalog.md`（A-F 6 路线）|
| **监督引擎** | Supervisor 实时监听 + Verifier 收口独立验证 + 3 红线即时停机 | `subagents/supervisor.md` + `subagents/verifier.md` + `hooks/*.sh` |
| **进化引擎** | 每任务收口产 retro 11 项 → append failure-archive.jsonl → 每 20 条审计建议 route 权重（**只建议不改 matrix**） | `subagents/retro-generator.md` + `archive/writer.py` + `archive/auditor.py` |

---

## 六路线（A-F）

| 路线 | 简称 | 适用场景 | 耗时参考 |
|---|---|---|---|
| **A** | 极速路 | XS 任务（改字符串 / 跑一条命令 / 文档单点修正）| < 15 min |
| **B** | 轻 PRP | 单模块小 feature / bug fix | 30-90 min |
| **C** | 全 PRP ⭐ | 跨模块 feature / MVP 主路线 / 重验证 | 3-6 h |
| **D** | UI 优先 | 纯视觉改动 / 前端组件 / screenshot 验证 | 30-90 min |
| **E** | Agent Graph | LangGraph / 多 Agent 节点改动 | 2-4 h |
| **F** | 研究 / 决策 | 需求调研 / 技术选型 / 决策 log | 1-3 h |

完整规则见 [`flow-catalog.md`](flow-catalog.md) + [`routing-matrix.md`](routing-matrix.md)（42-cell 决策矩阵）。

---

## 硬约束（4 条红线）

1. **真完成第一原则**：任务完成 ≡ 用户可直接消费的 artifact，而非 "pipeline 无 error"（method3 § 1.1）
2. **3 条红线即时停机**，任一触发 → `PAUSED_ESCALATED`、禁止 COMMIT：
   - `DRIFT_CRITICAL` — 目标偏离 > 阈值
   - `DOD_GAP_ALERT` — 关键 DoD 项被跳过
   - `IRREVERSIBLE_HALT` — 即将做不可逆动作但前置缺失
3. **进化边界硬线**：`auditor.audit()` **只产建议** (`audit-reports/audit-*.json`)，**永不自动改** `routing-matrix.json`。matrix 变更必须人审批。
4. **RETRO_CLOSE 强制链**（非 A 路线）：收口前必跑 retro-generator + failure-archive-writer，缺任一 → Stop gate 拒放行。

---

## 快速开始

### 前置依赖

- **Claude Code** CLI 或 VSCode/JetBrains 扩展（[官方站](https://claude.com/claude-code)）
- **Python 3.10+**（jsonschema + archive/ 模块）
- **jq**（hooks 合并）
- **3 个 skill 生态**（setup.sh 会自检并尝试自动安装前 2 个）：
  - [Superpowers](https://github.com/obra/superpowers) — `brainstorming` / `executing-plans` / `verification-before-completion`
  - [everything-claude-code](https://github.com/davidvkimball/everything-claude-code) — `prp-prd` / `prp-plan` / `prp-implement` / `code-reviewer` / `retro` / `save-session`
  - [gstack](https://gstack.dev) — `autoplan` / `ship` / `qa` / `review` / `careful` / `browse`

### 安装（3 步）

```bash
# 1. clone
git clone https://github.com/tianyiwxgm-netizen/harnessFlow.git
cd harnessFlow

# 2. 一键注册（幂等；自检 SP/ECC/gstack 依赖，缺的尝试自动装）
bash setup.sh

# 3. 自测
bash scripts/self-test.sh
```

setup.sh 会：

- 装 Python 依赖（`jsonschema`）
- 自检 3 个 skill 生态；Superpowers + everything-claude-code 缺失则 `claude plugin install` 自动装；gstack 缺失则打印手工安装指令
- symlink `harnessFlow.md` → `.claude/skills/harnessFlow.md`
- symlink 4 个 subagent → `.claude/agents/harnessFlow-*.md`
- 合并 2 个 hooks（PostToolUse + Stop）→ `.claude/settings.local.json`

### 激活

重启 Claude Code，输入：

```
/harnessFlow <你的任务描述>
```

首次激活会走 2-3 轮澄清 → 给你 Top-2 路线 → 你 pick → 主 skill 按骨架调度既有 skill 执行 → Verifier 收口。

---

## 使用示例

### 例 1：加一个后端 feature（路线 C）

```
/harnessFlow 给后端加一个 /api/users/{id}/avatar PUT 端点，上传头像到 OSS
```

harness 会：

1. 澄清：体量 M、task_type=后端 feature、risk=中 → 推荐路线 C
2. 拉 `SP:brainstorming` → `ECC:prp-prd` → `ECC:prp-plan` → `ECC:save-session`
3. Supervisor sidecar 上线监听
4. 调 `ECC:prp-implement` + `ECC:code-reviewer`
5. Verifier eval DoD：`(pytest_exit=0) AND (curl_PUT_returns_200) AND (OSS key exists)`
6. PASS → `ECC:prp-commit` → `ECC:prp-pr` → `ECC:retro` + archive.jsonl

### 例 2：一个决策调研（路线 F）

```
/harnessFlow 调研一下用 sqlite vs postgres 对当前项目的 tradeoff
```

harness 走 F 路线：`SP:brainstorming` → 并行 `Explore` + `WebSearch` + `docs-lookup` → 写 `decision_log.md` → Verifier 校验决策完整性 → retro。

### 例 3：极速小修（路线 A）

```
/harnessFlow 把 README 里的 "harnessflow" 统一改成 "harnessFlow"
```

XS + 纯代码 + 低风险 → A 路线豁免：跳过 plan / santa-loop / retro，直接 Read → Edit → Bash pytest → commit。

---

## 目录结构

```
harnessFlow/
├── README.md                           ← 本文件（开源视角）
├── QUICKSTART.md                       ← 5 分钟跑通第一个任务
├── setup.sh                            ← 一键安装（含依赖自检）
│
├── harness-flow.prd.md                 ← PRD（Phase 1-8 路线图 + Success Metrics）
├── harnessFlow.md                      ← 顶层架构（三引擎 + Supervisor）
├── method3.md                          ← 根宪章（真完成第一原则 + 42-cell 路由 + 反模式 10 条）
│
├── harnessFlow-skill.md                ← 主 skill prompt（~740 行）
├── flow-catalog.md                     ← 6 路线详解（A-F）
├── routing-matrix.md                   ← 42-cell 决策矩阵
├── state-machine.md                    ← 20 状态枚举 + 转移规则
├── task-board-template.md              ← task-board JSON schema（运行时状态）
├── delivery-checklist.md               ← 收口 DoD 清单 + Stop gate 规则
│
├── subagents/                          ← 4 个独立 subagent
│   ├── supervisor.md                   ← 6 类干预 + 3 红线监听
│   ├── verifier.md                     ← DoD eval + 3 段证据链
│   ├── retro-generator.md              ← 11 项 retro markdown 生成
│   └── failure-archive-writer.md       ← 结构化 jsonl 归档（schema-validated）
│
├── hooks/
│   ├── PostToolUse-goal-drift-check.sh ← goal-anchor drift 检测
│   └── Stop-final-gate.sh              ← 收口门卫（强制 retro + archive 校验）
│
├── schemas/
│   ├── failure-archive.schema.json     ← JSON Schema draft-07（18 必填 + 8 可选）
│   └── retro-template.md               ← 11 段 retro 模板
│
├── archive/                            ← 进化引擎实现
│   ├── writer.py                       ← schema 校验 + fcntl lock 3×5s retry
│   ├── auditor.py                      ← 每 20 条审计（只建议不改 matrix）
│   ├── retro_renderer.py               ← 11 helpers + Template.safe_substitute
│   ├── __main__.py                     ← python -m archive list|audit|stats CLI
│   └── tests/                          ← 54 pytest
│
├── verifier_primitives/                ← 20+ DoD 原语（oss/video/http/fs/pytest/schema/...）
│
├── scripts/
│   ├── self-test.sh                    ← 6 模块 11 检查一键自测
│   ├── run-p20-validation.sh           ← P20 真出片端到端 handoff 脚手架
│   └── verify-p20-artifacts.py         ← DoD_P20 8 子契约验证器
│
├── plans/                              ← 每 Phase 的 PRP plan 文档
└── commands/harnessFlow.md             ← slash command 入口
```

运行时产物（gitignored）：`task-boards/*.json` / `verifier_reports/*.json` / `retros/*.md` / `failure-archive.jsonl` / `supervisor-events/*.jsonl` / `routing-events/*.jsonl`。

---

## 项目状态

| Phase | 描述 | 状态 |
|---|---|---|
| 1 | method3.md 重构（根宪章）| ✅ complete |
| 2 | harnessFlow.md 顶层架构 | ✅ complete |
| 3 | flow-catalog + routing-matrix（6 路线 + 42-cell）| ✅ complete |
| 4 | state-machine + task-board-template + delivery-checklist | ✅ complete |
| 5 | harnessFlow-skill.md 主 skill prompt | ✅ complete |
| 6 | Supervisor + Verifier subagent + 20+ verifier_primitives | ✅ complete |
| 7 | failure-archive.jsonl schema + auto-retro 11 项 + 路由审计 | ✅ complete |
| 8 | 端到端验证（self-test + archive CLI + P20 handoff）| ✅ complete |
| **v1.1** | **Stage Contract 层**（stage-contracts.md + schema + 4 文档挂接 + 10 pytest） | ✅ complete |

**测试**：100 pytest 全绿（90 Phase 1-8 + 10 v1.1 Stage Contract 自检，0 regression；concurrency test 已加 flaky rerun 标注）
**自举**：8.1 self-test + 8.2 archive CLI 两任务 end-to-end Verifier=PASS、retro 11 段自动生成、archive.jsonl L1+L2 schema-valid
**P20 真出片**：handoff 脚手架就绪（`scripts/run-p20-validation.sh`），按键触发。

---

## 技术原理（深入阅读）

想理解规则层的完整细节，按顺序读：

1. [`method3.md`](method3.md) — 根宪章（真完成第一原则 + 42-cell 路由骨架 + 反模式 10 条）
2. [`harnessFlow.md`](harnessFlow.md) — 顶层架构（三引擎 + Supervisor 设计 + 与 SP/ECC/gstack 边界）
3. [`state-machine.md`](state-machine.md) — 20 状态 + 转移边表 + retry ladder
4. [`delivery-checklist.md`](delivery-checklist.md) — 收口 DoD + Stop gate 证据链要求
5. [`harnessFlow-skill.md`](harnessFlow-skill.md) — 主 skill 的 § 1-13 完整协议

其他参考：

- 想看失败案例 → 进化：[`schemas/failure-archive.schema.json`](schemas/failure-archive.schema.json) + `method3.md § 7.3`（进化边界硬线）
- 想看 DoD 原语怎么实现：[`verifier_primitives/`](verifier_primitives/) 20+ 原语
- 想看 11 段 retro 长什么样：[`schemas/retro-template.md`](schemas/retro-template.md)

---

## 设计决策记录（核心 6 条）

| 决策 | 选择 | 为什么 |
|---|---|---|
| harnessFlow 是什么 | 总编排 + Supervisor 副驾 + 三引擎 | 反对：新 skill 框架（造轮）/ 全 LLM 路由（不可审计）/ 静态 SOP（不灵活） |
| DoD 形式 | 机器可执行布尔表达式 | 反 AutoGen `is_termination_msg` 假完成陷阱 |
| 路由形式 | 确定性 DAG + 真分叉才用 LLM | CrewAI/AutoGen 黑盒不可审计；MetaGPT 全静态太死 |
| Supervisor 权限 | 只读 | 避免和执行 agent 抢手（公开方案 sidecar 模式） |
| 进化边界 | 只输出建议，等用户审批 | harness 自动改自己代码不可控 |
| failure-archive | 每项目独立 + 全局只读视图 | 项目隔离 + 跨项目可学 |

---

## 贡献

本项目欢迎 issue / PR，但请注意：

1. **新 skill 一律去 Superpowers / everything-claude-code / gstack 提**，harnessFlow 只编排不造轮（参 `harnessFlow.md § 2.3` "不重复造轮" 硬约束）
2. **改规则文档**（method3 / flow-catalog / routing-matrix / state-machine）要配对 retro + failure-archive entry，说明触发的历史失败案例
3. **auditor 建议合入 matrix 的 PR** 必须 attach `audit-reports/audit-*.json`，人审批权重调整
4. **新路线** G+ 开放，但要符合 `flow-catalog.md § 8.1` 切换触发矩阵 + 补对应 `routing-matrix.md` cell + 补 `flow-catalog § <新章>` 完整调度序列

---

## 许可

MIT License. See [LICENSE](LICENSE).

---

## FAQ

**Q: harnessFlow 跟 Superpowers 的 `executing-plans` 有什么区别？**
A: `executing-plans` 是 **执行一个既有 plan**；harnessFlow 是 **编排从 "一句话任务" 到 "真完成 artifact" 的全流程**（含 plan 的生成、监督、验证、归档）。harnessFlow 会调用 SP 的 `executing-plans` 作为路线 C 的一个步骤，但不等于它。

**Q: 跟 AutoGen / CrewAI / LangGraph 的关系？**
A: 都是 agent harness。区别：
- AutoGen / CrewAI：通用对话式 multi-agent，LLM 报 `TERMINATE` 就算完（**假完成陷阱**）
- LangGraph：图编排框架，supervisor 模式是参考对象之一
- harnessFlow：**针对 Claude Code 生态**的 meta-skill，DoD 是机器可执行布尔表达式，Verifier 独立重跑命令，专治假完成

**Q: 如果我不装 Superpowers / ECC / gstack 还能用吗？**
A: 部分能用。A 路线（极速路，XS 任务）可 degrade 到纯 Claude Code 原生工具；B-F 路线强依赖 3 个生态里的特定 skill，缺的会 FAIL-LOUD（Verifier 会明确报 "dependency missing"）。

**Q: 数据隐私？harness 会把我的代码发到哪里？**
A: harnessFlow 本身是本地的 markdown + Python + shell，不上传任何数据。它调度的上游 skill（Claude Code 本身 / Anthropic API / 第三方 LLM）的隐私政策由各自负责。

**Q: 跑一个任务要消耗多少 token？**
A: 视路线：A 路线 ~2k tokens、B ~20k、C ~80-200k、XL 可能几 M。Supervisor 本身 token 占比 < 5%（只读、短响应）。完整预算跟踪见 `task-board.cost_budget` 字段。

---

*🤖 Generated with [Claude Code](https://claude.com/claude-code) — harnessFlow 本身就是用 Claude Code + 它自己的雏形迭代出来的*
