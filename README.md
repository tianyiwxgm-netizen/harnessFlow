# harnessFlow

> **防"假完成"AI 编排引擎** —— 给 Claude 当 PM + 架构师 + 质检员 · 一句话需求到完整项目交付 · 每步有监督 + 审计 + 质量 Gate 兜底 · 永不宣称"完成"直到有真凭据。

[![version](https://img.shields.io/badge/version-1.0.0-blue)]()
[![pytest](https://img.shields.io/badge/E2E_pytest-753%20passed-brightgreen)]()
[![halt](https://img.shields.io/badge/halt_P99-0.04ms-brightgreen)]()
[![panic](https://img.shields.io/badge/panic_P99-0.02ms-brightgreen)]()
[![docs](https://img.shields.io/badge/docs-154%20files%20%E2%80%A2%20165kL-brightgreen)]()
[![license](https://img.shields.io/badge/license-MIT-blue)]()

---

## 🎯 是什么 · 解决什么问题

**harnessFlow** 是一个开源 **Claude Code Skill**，专门解决 AI 编程的最大痛点：

> *AI 说"完成了"——但代码跑不起来、测试没写、需求没对上。*

harnessFlow 的核心机制：**任务完成 ≡ 用户可直接消费的 artifact**，而非"pipeline 无 error"。
通过 **路由矩阵 → 三引擎监督 → Verifier 独立收口 → 结构化归档** 四道关卡，让 AI 真正完成任务。

---

## ✨ 核心功能

| 功能 | 描述 |
|:---|:---|
| **42-cell 路由矩阵** | 按 `(size, task_type, risk)` 三维自动选最优执行路线(A-F 6 种)，避免大炮打蚊子 |
| **Supervisor 侧挂监听** | 任务全程后台运行，检测 8 维偏移 + 5 硬红线，触发自动回滚或暂停升级 |
| **Verifier 独立收口** | 任务"完成"时由独立 subagent 用 DoD 布尔表达式验证——不是 AI 自评，是独立评审 |
| **结构化失败归档** | 每次失败写 `failure-archive.jsonl`，11 段 retro 复盘，知识持续积累 |
| **硬红线 ≤100ms** | halt / panic / IC-15 硬约束实测 P99 = 0.04ms，余量 970×，随时可急停 |
| **100% 审计可追溯** | 每次决策写 `events.jsonl`，hash chain 确保不可篡改 |
| **跨 session 恢复** | 4 层恢复机制，Claude crash / 重启后从 checkpoint 继续，不丢进度 |
| **任务看板 UI** | `/harnessFlow-ui` 一键启动 Web 界面，查看任务时间轴 + KB + 产出物 |

---

## ⚙️ 工作机制

### 三引擎架构

```
用户输入一句话需求
       ↓
  ┌─────────────────────────────────────────┐
  │          harnessFlow 主编排器            │
  │  CLARIFY(2-3轮) → ROUTE → PLAN → IMPL  │
  └──────────┬──────────────────────────────┘
             │ 全程
    ┌─────────┴──────────┐
    │  Supervisor sidecar │  ← 侧挂监听，检测偏移，发 WARN/BLOCK
    └─────────────────────┘
             │ 任务"完成"时
    ┌─────────┴──────────┐
    │  Verifier subagent  │  ← 独立 spawn，DoD 布尔表达式验证
    └─────────────────────┘
             │ 通过后
    ┌─────────┴──────────┐
    │  failure-archive +  │  ← 11段retro + JSONL归档 + 知识积累
    │  retro-generator    │
    └─────────────────────┘
```

### 7 Stage 自动流水线

| Stage | 名称 | 产出 |
|:---:|:---|:---|
| S1 | **Kickoff** | 4 件套：需求(REQ)/ 目标(GOAL)/ 验收标准(AC)/ 质检清单(QS) |
| S2 | **Planning** | PMP 9 计划 + TOGAF 架构 → Gate 卡（等用户 Go/Reject） |
| S3 | **TDD Plan** | TDD blueprint + pytest 骨架 → Gate 卡 |
| S4 | **Executing** | 多 WP 并发：代码 → 单元测试 → 质量 Gate 5 基线 |
| S5 | **Verifier** | Verifier 独立双签验证 + IC-20 invoke_verifier |
| S6 | **Closing** | 11 段 retro + artifacts 整理 |
| S7 | **Archive** | `tar.zst` 压缩 + PM-14 归档，`projects/<pid>/artifacts/` |

### 6 条执行路线（自动选）

| 路线 | 适用场景 | 特点 |
|:---:|:---|:---|
| **A** | XS 任务（改个字符串、读文件） | 极简，跳过重 skill |
| **B** | S/M 标准功能开发 | brainstorm→plan→implement→review |
| **C** | L/XL 复杂项目 | 加 Supervisor + 全量 Gate |
| **D** | 重构 / 架构迁移 | 分析优先，渐进式 |
| **E** | 纯文档 / 研究 | 知识库驱动 |
| **F** | 高风险 / 不可逆操作 | 强制暂停确认，双签 |

---

## 🚀 快速上手

### 方式一：作为 Claude Code Slash Command（推荐）

```bash
git clone https://github.com/tianyiwxgm-netizen/harnessFlow.git
cd harnessFlow
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# 自动注册到 Claude（全局可用）
bash scripts/register.sh

# 验证安装
bash scripts/self-test.sh    # 期望：12/12 PASS
```

在 **任意项目** 的 Claude Code 里：
```
/harnessFlow 做一个 FastAPI + Vue TODO App，含用户认证
```

查看任务看板：
```
/harnessFlow-ui
```

### 方式二：仅在 harnessFlow 目录下使用

直接 clone 后在 Claude Code 里打开该目录，`/harnessFlow` 和 `/harnessFlow-ui` 自动可用（无需运行注册脚本）。

---

## ✅ 当前状态：v1.0.0 stable · 2026-04-25

10 L1 全交付 · 753 E2E 测试 0 flake / 41.72s · 7 SLO 全实测（halt P99=0.04ms · 余量 970×）· 12 acceptance scenario 端到端绿 · 154 份 3-Solution 文档 ~165k 行 · 20 IC 契约锁定 · 30/30 跨 L1 矩阵 cell。详见 [CHANGELOG.md](CHANGELOG.md)。

## 📋 环境要求

| 依赖 | 版本 | 说明 |
|:---|:---:|:---|
| Python | 3.11+ | 必须 |
| Claude Code | 任意 | Skill / slash command 载体 |
| LLM 凭据 | - | Anthropic / DeepSeek / 豆包 · 详 `.env` |
| 磁盘 | ≥ 500MB | 含依赖 |
| Node 20+ | 可选 | 仅贡献者 build frontend 时需要，普通用户零 Node |

---

## 💡 典型使用

### 场景 1:做一个新项目(最常用)

```
UI 点"新项目" → 输入需求一句话:
   "做一个 TODO App · FastAPI + Vue · 含用户认证 + 标签分类"

↓ harnessFlow 自动推进 7 Stage:
S1 Kickoff    · 4 件套(REQ / GOAL / AC / QS)
S2 Planning   · PMP 9 计划 + TOGAF → Gate 卡(等你 Go)
S3 TDD Plan   · TDD blueprint + pytest 骨架 → Gate 卡
S4 Executing  · 多 WP 并发(每 WP:代码 → test → 质量 Gate 5 基线)
S5 Verifier   · 双签验证 + IC-20 invoke_verifier
S6 Closing    · retro + artifacts 整理
S7 Archive    · tar.zst + PM-14 归档

↓ 产出:
app/           源代码(FastAPI + Vue)
tests/         TDD 测试(覆盖率 ≥85%)
docs/          设计文档 + Gate cards
projects/<pid>/artifacts/  4 件套 + PMP + TOGAF + 审计链
```

### 场景 2:失控兜底(Supervisor 自动)

AI 卡死时(连续 3 次 rework · 硬红线命中 · tick drift 超阈):
- **L1-07 Supervisor** 自动发 IC-14 rollback 路由
- 严重时 IC-15 `request_hard_halt` · **≤100ms 硬约束**
- UI panic 按钮:随时叫停

### 场景 3:跨 session 恢复

Claude crash / 机器重启后 · L1-09 提供 4 层恢复机制:
- Tier 1:latest checkpoint 正常恢复(≤60s)
- Tier 2:checkpoint 坏 · fallback 上一个 + 告警
- Tier 3:events.jsonl 中间破损 · 跳恢复 + 告警
- Tier 4:全坏 · **拒绝假恢复** · halt 告警

恢复通过 `app.l1_09` Python API 或 Claude Code Skill 触发 · v1.1 补 CLI 入口。

---

## 🧠 10 L1 能力清单

| L1 | 职责 | 核心 |
|:---:|:---|:---|
| **L1-01 主决策循环** | tick 调度全局 | 100ms tick · AST 白名单决策 · S1-S7 状态机 |
| **L1-02 项目生命周期** | pid 唯一入口 | PM-14 根字段硬约束 · Stage Gate · TOGAF ADM |
| **L1-03 WBS+WP** | 任务拓扑调度 | 6 态机 · DAG 循环检测 · 失败升级 |
| **L1-04 Quality Loop** | 质量判官 | DoD AST 编译 · TDD 蓝图 · Gate 5 基线 · 4 级回退 |
| **L1-05 Skill+子Agent** | 能力抽象 | Claude Agent SDK · 4 全局 IC(invoke_skill/delegate_*)|
| **L1-06 3 层 KB** | 知识库 | session/project/global · 5 信号 rerank · 晋升仪式 |
| **L1-07 Harness 监督** | 审慎兜底 | 8 维监控 · 5 硬红线 · 8 soft-drift · IC-13/14/15 |
| **L1-08 多模态** | 内容处理 | tree-sitter 5 语言 · VLM · OCR · 白名单路径 |
| **L1-09 韧性审计** | 脊柱 | fsync 铁律 · hash chain · JCS · PM-08 单事实源 |
| **L1-10 人机协作 UI** | 交互面 | Vue 3 + Vite · 11 Tab + Admin 8 子 Tab · SSE |

---

## 📊 硬约束(release gate 必 PASS)

| 约束 | 阈值 | 实测 P99 | 富余 |
|:---|:---:|:---:|:---:|
| IC-15 halt | ≤ 100ms | **103μs** | 970× |
| L1-10 panic | ≤ 100ms | < 1ms | 100× |
| L1-01 tick drift | ≤ 100ms | < 1ms | 100× |
| L1-04 IC-12 dispatch | ≤ 200ms | 0.29ms | 697× |
| L1-07 L2-03 HRL scan | ≤ 500ms | 1.08ms | 462× |
| **审计可追溯** | **100%** | **100%** | - |

---

## 🖥️ UI 总览(11 主 Tab + Admin 8 子 Tab)

**主 Tab**:
1. **项目总览** — state machine 进度 · 关键 metric
2. **WBS** — 任务拓扑 · 可视化 · 切换
3. **Gate 卡片** — S1-S7 Gate 裁决历史
4. **决策流** — AI 每次决策可追溯(审计 100%)
5. **质量面板** — DoD 实时 + 5 基线统计
6. **进度流(SSE)** — 实时事件滚动
7. **Retro** — 项目回顾 + 失败档案
8. **事件总线** — audit 查询 + filter
9. **KB 浏览器** — 3 层 · 晋升审核
10. **裁剪档** — full / lean / custom
11. **Admin** — users / permissions / audit / health / metrics / config / extensions / diagnostics

**panic 按钮**(顶栏):≤100ms 硬约束中断主循环。

---

## 🔧 扩展点

| 想做什么 | 改哪里 |
|:---|:---|
| 加新 Skill | `skills/<my_skill>.md` + register · L1-05 自动发现 |
| 调 DoD 基线阈值 | DoD YAML(`docs/3-3-Solution-Monitoring&Controlling/dod-specs/`) |
| 换 LLM 后端 | `.env`:`LLM_PROVIDER=deepseek/claude/doubao/local` |
| 加新 L1 能力 | 参考 `docs/3-1-Solution-Technical/` 内各 L1 Tech Design |
| 加新 IC 契约 | `docs/3-1-Solution-Technical/integration/ic-contracts.md` + register |

---

## 📁 项目结构(end user 视角)

```
harnessflow/
├── app/                       后端核心(10 L1 代码)
│   ├── l1_09/                 韧性+审计(脊柱)
│   ├── project_lifecycle/     L1-02
│   ├── knowledge_base/        L1-06
│   ├── skill_dispatch/        L1-05
│   ├── l1_03/                 WBS+WP
│   ├── supervisor/            L1-07
│   ├── multimodal/            L1-08
│   ├── quality_loop/          L1-04(Quality Loop)
│   └── main_loop/             L1-01(心脏)
├── frontend/                  Vue 3 源码(开发者 build · End User 用 Skill)
├── tests/                     753 E2E TC · 覆盖率 ≥85%
├── docs/                      设计文档 + 用户/开发者手册
├── projects/                  你的 project 数据(PM-14 分片)
│   └── <pid>/
│       ├── artifacts/         4 件套 + PMP + TOGAF
│       ├── events.jsonl       审计链(IC-09 单事实源)
│       ├── wbs/               任务拓扑
│       └── kb/                session/project 层 KB
└── global_kb/                 跨 project 共享层
```

---

## 📚 完整文档

- **[CHANGELOG.md](CHANGELOG.md)** — v1.0.0 变更清单
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — 贡献指南(PR 规范 + 架构约束)
- **[harnessFlow-skill.md](harnessFlow-skill.md)** — Claude Code Skill 入口说明
- **[docs/3-1-Solution-Technical/](docs/3-1-Solution-Technical/)** — 10 L1 技术设计文档(154 份)
- **[docs/3-3-Monitoring-Controlling/](docs/3-3-Monitoring-Controlling/)** — DoD + 硬红线 + 质量规范

---

## 🎓 设计哲学

1. **审慎 > 速度** — AI 每决策可追溯 · 硬红线 + 软飘移双重监督
2. **code + TDD 同会话** — Q-04 铁律 · 避免"写完没测"
3. **PM-14 物理分片** — 每 project 数据 `projects/<pid>/` 严格隔离
4. **PM-08 单一事实源** — L1-09 `events.jsonl` 是**唯一**审计真相
5. **V-model 严格** — 设计文档(3-1) → TDD(3-2) → 代码 → 验证(3-3)
6. **语义命名** — `supervisor/` > `l1_07/` · `quality_loop/` > `l1_04/`

---

## 🏗️ 适用人群

- **AI 驱动开发先锋** — 想让 Claude 当 PM+架构师+码农 · 做完整软件项目
- **软件工程研究者** — V-model / PM-14 / 审慎监督等实践案例
- **Claude Code 深度用户** — 扩展 skill 生态 · 做领域定制

---

## 🏆 v1.0 交付指标(最终目标)

- **10 L1 + 集成层 + UI** · ~195,000 行代码
- **~4080 TC 全绿** · 覆盖率 ≥ 85%(部分模块 ≥ 95%)
- **4 硬约束** 100-970× 富余
- **审计链完整 100%**
- **跨 session 恢复** Tier 1-4
- **7 篇文档** + 25 份设计 md
- **MIT License** · 完全开源

## 📍 v1.0.0 已交付(2026-04-25)

**全部 merged main** · tag `v1.0.0`:
- ✅ **753 E2E TC + 47 perf TC 全绿** · 0 flake / 41.72s
- ✅ 8 Dev 代码全完(α-θ)· L1-01~10 全交付
- ✅ main-1 L1-04 Quality Loop 100%(9 WP · 719 TC · DoD AST + Gate + Verifier + 4 级回退)
- ✅ main-2 L1-01 心脏 100%(7 WP · 521 TC · halt P99=0.04ms / panic P99=0.02ms)
- ✅ main-3 集成 + acceptance + perf(波 6 · 10 WP · 753 E2E TC · 12 acceptance scenarios + 7 SLO 全实测 · 30/30 跨 L1 矩阵 cell · 20 IC 契约 + PM-14 + cross-session 全 covered)
- ✅ main-4 release(波 7 · CHANGELOG.md / LICENSE / CI workflow / CONTRIBUTING.md / ISSUE_TEMPLATE 全到位)
- ✅ 3-Solution 文档体系 154 份 / ~165k 行 / 298 PlantUML / 0 Mermaid / 0 FILL

**v1.1 roadmap**:multi-tenant deployment / 全 Vue 3 + Vite production frontend / runtime LLM provider switching / 扩展 tree-sitter 多语言包 / cloud audit-ledger sink。

## 🚧 已知限制(v1.0 scope)

- **V1 单 project 激活**(同时刻仅 1 个 active)· V2+ 多 project 切换
- **无 CLI 包装**(`harnessflow serve` 需 pyproject.toml `[project.scripts]` 注册 · v1.0 release 前补)
- **无 Docker 镜像**(V2+ 可选)
- **LLM 只支持 4 个**(Claude / DeepSeek / 豆包 / local)· 接其他需改 adapter
- **PM-14 严格**:同时刻只能一 project 写 · 跨 project 任何写操作 raise(安全兜底)
- **UI 只有 Web**(无 TUI / 无原生 app · V2+ Electron)
- **仅支持 Python 3.11+**(3.10 缺 asyncio improvements · 3.12 未测)
- **Multimodal V1 只读 5 种代码语言**(py/ts/go/rust/java · tree-sitter)

---

## 💡 实际例子(v1.0 release 后)

**输入**:UI 的"新项目"框输入
```
做一个简单 TODO App · FastAPI + Vue · 用户注册登录 + 标签分类
```

**20-60 分钟后 · 产出**:
```
projects/<pid>/
├── artifacts/
│   ├── REQ-001.md   需求文档(自动生成)
│   ├── GOAL-001.md
│   ├── AC-001.md    验收标准
│   ├── QS-001.md    质量标准
│   ├── PMP-9-plans/ 9 个子计划(范围/进度/成本/质量/资源/风险/沟通/采购/相关方)
│   └── TOGAF-ADM/   架构 4 件套(business/data/application/technology)
├── code/
│   ├── backend/main.py  FastAPI + SQLAlchemy
│   ├── backend/auth.py  JWT
│   ├── frontend/        Vue 3 + Pinia
│   └── tests/           TDD 测试(覆盖率 ≥ 85%)
├── events.jsonl     所有 AI 决策审计(hash 链不断)
└── wbs/             任务拓扑
```

全程在 UI 可见 · Gate 卡时推通知等你 approve。

---

## 📞 反馈 / 贡献

- **Issues**: https://github.com/tianyiwxgm-netizen/harnessFlow/issues
- **Discussions**: GitHub Discussions
- **Security**: `security@harnessflow.dev`(可选)

欢迎 fork · PR · 贡献新 Skill / 新 L1 / 新 IC!

---

**License**: MIT · © 2026 harnessFlow contributors

*本质:harnessFlow 让"用 AI 做一个完整软件项目"**不再失控**。你给方向 · 它把产品全流程走完 · 每一步有审计 + 监督 + 质量 Gate 兜底。*
