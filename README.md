# harnessFlow — Claude Code 防假完成元技能

> "真完成"第一原则的落地工具链。
> 把"报了 success 却没真出活"的系统性风险，翻译成 Claude Code 里机器可执行的拦截点。

---

## 这是什么

**harnessFlow** 是一个 Claude Code **元技能（meta-skill）**，负责统一编排 `/`-level skill、subagent、hooks，为任务装上"验证—监督—归档—进化"的链条。

它不是新的工作流，而是一个**总路由器 + 总监督**：

- **总路由器**：接任务 → 2-3 轮澄清 → 识别 `(size, task_type, risk)` 三维 → 查 routing-matrix 推荐 Top-2 路线 → 调度既有 skill（Superpowers / everything-claude-code / gstack）。
- **总监督**：侧挂 Supervisor sidecar 监听 tool call + diff，触发 3 条红线（DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT）→ 收口前独立 spawn Verifier 跑 DoD 布尔表达式 → 强制 retro 11 项 + 写 failure-archive.jsonl。

**一句话**：在 agent 说 "done" 之前，确保它真的 done。

---

## 为什么（P20 事件）

2026-04-16，aigcv2 的 P20 "真出片"任务按旧版 method3（方案 C 全 PRP）跑：pipeline 跑完、agent 报告"出片成功"。实际上：

- 没起 uvicorn
- 没 POST `/api/pipelines`
- 没校验 mp4 文件是否存在
- 没校验时长 / OSS key / playback
- **"pipeline 无 error" ≠ "真出片成功"**

这类"假完成"不是个案——是所有公开 agent 框架（AutoGen / CrewAI / MetaGPT）共有的系统性盲区。harnessFlow 的 bet：**把"真完成"写进机制、写进 Verifier 布尔表达式、写进 Stop hook，而不是写进口号**。

---

## 三大引擎

| 引擎 | 职责 | 核心 artifact |
|---|---|---|
| **路由引擎** | 输入任务 → 查 42-cell matrix → 输出 `(route, plan_skill, impl_skill, verify_skill, supervisor_config)` | `routing-matrix.md` + `flow-catalog.md`（A-F 6 路线）|
| **监督引擎** | Supervisor 实时监听 + Verifier 收口独立验证 + 3 红线即时停机 | `subagents/supervisor.md` + `subagents/verifier.md` + `hooks/*.sh` |
| **进化引擎** | 每任务收口产 retro 11 项 → append failure-archive.jsonl → 每 20 条审计建议 route 权重 | `subagents/retro-generator.md` + `archive/writer.py` + `archive/auditor.py`（**只建议不改 matrix**）|

---

## 快速开始

**2 步上手：**

```bash
# 1. 一键注册（幂等）：软链 skill/subagent + 合并 hooks 到 .claude/settings.local.json
bash "harnessFlow /setup.sh"

# 2. 在 Claude Code 里激活（或用项目内 /harnessFlow 命令）
/harnessFlow 帮我给 Dashboard 加一个 Phase 8 验证入口按钮
```

详见 [QUICKSTART.md](QUICKSTART.md)。

---

## 目录结构

```
harnessFlow /
├── README.md                           ← 本文件
├── QUICKSTART.md                       ← 5 分钟跑通第一个任务
├── setup.sh                            ← 一键安装脚本
│
├── harness-flow.prd.md                 ← Phase 1-8 PRD（路线图）
├── harnessFlow.md                      ← 顶层架构
├── method3.md                          ← 根宪章（真完成 + 42-cell 路由 + 反模式）
│
├── harnessFlow-skill.md                ← 主 skill prompt（~870 行）
├── flow-catalog.md                     ← 6 路线详解（A-F）
├── routing-matrix.md                   ← 42-cell 决策矩阵
├── state-machine.md                    ← 20 状态枚举 + 转移规则
├── task-board-template.md              ← task-board JSON schema
├── delivery-checklist.md               ← 收口 DoD 清单 + Stop gate § 7.2
│
├── subagents/
│   ├── supervisor.md                   ← 6 类干预 + 3 红线
│   ├── verifier.md                     ← DoD eval + 3 段证据链
│   ├── retro-generator.md              ← 11 项 retro markdown 生成
│   └── failure-archive-writer.md       ← 结构化 jsonl 归档 (v2)
│
├── hooks/
│   ├── PostToolUse-goal-drift-check.sh ← CLAUDE.md drift 检测
│   └── Stop-final-gate.sh              ← 收口门卫（Phase 7 加 retro/archive 校验）
│
├── schemas/
│   ├── failure-archive.schema.json     ← JSON Schema draft-07（18 必填 + 8 可选）
│   └── retro-template.md               ← 11 段 retro markdown 模板
│
├── archive/
│   ├── writer.py                       ← write_archive_entry() 结构化写入
│   ├── auditor.py                      ← 每 20 条审计（只建议不改 matrix）
│   ├── retro_renderer.py               ← 11 helpers + Template.safe_substitute
│   └── tests/                          ← 54 pytest（schema + writer + auditor + retro）
│
├── verifier_primitives/                ← 20+ DoD 原语（oss/video/http/fs/pytest/...）
│
├── plans/                              ← 每 Phase 的 PRP plan 文档
├── task-boards/                        ← 任务运行时 state 持久化
├── verifier_reports/                   ← Verifier 独立输出
├── retros/                             ← 11 段 markdown 复盘
├── supervisor-events/                  ← 监督事件日志
├── routing-events/                     ← 路由决策日志
├── sessions/                           ← 跨 session checkpoint
├── audit-reports/                      ← auditor 产出的建议报告（可人审批合入）
└── failure-archive.jsonl               ← 全局结构化失败归档
```

---

## 当前状态

| Phase | 描述 | 状态 |
|---|---|---|
| 1 | method3.md 重构 | ✅ complete |
| 2 | harnessFlow.md 顶层架构 | ✅ complete |
| 3 | flow-catalog + routing-matrix（6 路线 + 42-cell）| ✅ complete |
| 4 | state-machine + task-board-template + delivery-checklist | ✅ complete |
| 5 | harnessFlow-skill.md 主 skill prompt | ✅ complete |
| 6 | Supervisor + Verifier subagent + 20+ verifier_primitives | ✅ complete |
| 7 | failure-archive.jsonl schema + auto-retro 11 项 + 路由审计 | ✅ complete |
| 8 | 端到端验证（3 真任务）| 🔄 in-progress（plan `plans/phase8-e2e-validation.plan.md`）|

**测试**：85 pytest 全绿（31 Phase 6 verifier_primitives + 54 Phase 7 archive）

---

## 核心约束（硬线）

1. **真完成第一原则**：任务完成 ≡ 用户可直接消费的 artifact，而非"pipeline 无 error"（method3 § 1.1）。
2. **3 红线即时停机**：DRIFT_CRITICAL（偏离目标 > 阈值）/ DOD_GAP_ALERT（DoD 缺段）/ IRREVERSIBLE_HALT（不可逆前无 checkpoint）——任一触发进 `PAUSED_ESCALATED`，禁止 COMMIT。
3. **进化边界**：`auditor.audit()` **只产建议报告**（`audit-reports/audit-*.json`），**永不写**（也**不**自动改）`routing-matrix.json`。matrix 变更须人审批（method3 § 7.3）。
4. **RETRO_CLOSE 强制链**（非 A 路线）：收口前必跑 `retro-generator` + `failure-archive-writer`，缺任一 → Stop gate 拒放行。
5. **A 路线豁免**：`route=A` 且 `size=XS` 时跳过 retro + archive（delivery-checklist § 7.2 carve-out）。

---

## 反模式（不要做）

参 `method3.md § 8`（10 条）。高危 3 条：

- **§ 8.1 假完成**：pipeline 跑完 ≠ 任务完成（P20 事件）
- **§ 8.8 自动改 routing-matrix**：auditor 建议 → 必须人审批
- **§ 8.10 绕开 writer 直接 append jsonl**：唯一入口 `archive.writer.write_archive_entry()`

---

## 依赖

- Python 3.10+（archive/ 用 `from __future__ import annotations`）
- `jsonschema`（pip install；setup.sh 自动装）
- `jq`（brew install jq；setup.sh 里 hooks 合并用）
- Claude Code（CLI / VSCode 扩展均可）
- 跑 P20 类任务额外需要：ffmpeg / aliyun OSS credentials / DeepSeek API key（见具体任务的 DoD）

---

## 许可与归属

- 本项目是针对 [aigcv2](../aigc) / 其他内部项目的**内部元技能**，非开源分发。
- 许多 pattern 受 Anthropic Superpowers / everything-claude-code / gstack 启发——边界见 `harnessFlow.md § 2.3`（"不重复造轮"）。

---

## 下一步阅读

- **想用起来**：[QUICKSTART.md](QUICKSTART.md)
- **想理解规则**：[method3.md](method3.md)（根宪章）→ [harnessFlow.md](harnessFlow.md)（架构）→ [state-machine.md](state-machine.md)（状态机）
- **想看怎么验证**：[delivery-checklist.md](delivery-checklist.md) + [verifier_primitives/README.md](verifier_primitives/README.md)
- **想看失败案例 → 进化**：[method3.md § 7.3](method3.md) + [schemas/failure-archive.schema.json](schemas/failure-archive.schema.json)
