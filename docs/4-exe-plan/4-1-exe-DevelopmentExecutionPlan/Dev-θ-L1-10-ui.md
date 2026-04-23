---
doc_id: exe-plan-dev-theta-L1-10-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α-L1-09-resilience-audit.md（标杆）
  - docs/2-prd/L1-10 人机协作UI/prd.md
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/architecture.md
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-01~L2-07.md（15477 行）
  - docs/3-2-Solution-TDD/L1-10-人机协作UI/L2-01~L2-07-tests.md（9243 行 · 392 TC）
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.16 IC-16 · §3.17 IC-17 · §3.18 IC-18
version: v1.0
status: draft
assignee: Dev-θ（拆 θ1 前端骨架 + θ2 业务完整 · 2 会话接力）
wave: 1-3
priority: P0（用户入口）
estimated_loc: ~27800 行（前端 Vue + 后端 FastAPI BFF）
estimated_duration: 8-10 天（θ1 · 3 天 + θ2 · 5 天）
---

# Dev-θ · L1-10 人机协作 UI · Execution Plan

> **组一句话**：7 L2 前端 · Vue 3 + Element Plus + Pinia + vue-router · 11 tab 主框架 + Gate 卡片 + 进度流（SSE）+ 用户干预（panic ≤ 100ms）+ KB 浏览器 + 裁剪档 + Admin · 发起 **IC-17** · 消费 **IC-16** · 查询 **IC-18**。
>
> **拆批**：θ1 前端骨架（L2-01/06/07 · 3 L2 · 3 天 · 波 1 与 Dev-α 并行）· θ2 业务完整（L2-02/03/04/05 · 4 L2 · 5 天 · 波 3 后端 ready 后集成）。
>
> **PM-14**：所有视图按 pid 过滤 · 跨 project 访问拒绝 · banner 标注当前 project。

---

## §0 撰写进度

- [x] §1-§10 全齐

---

## §1 范围

### 7 L2 · θ1/θ2 拆批

**θ1 批**（3 天 · 3 L2 · 后端 mock · 前端骨架）：
| L2 | 职责 | 估时 |
|:---:|:---|:---:|
| L2-01 11 主 Tab 主框架 | Vue3 + vue-router · 11 tab 路由 · 跨 project banner | 1.5 天 |
| L2-06 裁剪档配置 | full/lean/custom 切换 · localStorage | 0.75 天 |
| L2-07 Admin 子管理 | 8 子 tab（users/permissions/audit/health/...）| 0.75 天 |

**θ2 批**（5 天 · 4 L2 · 后端真实集成）：
| L2 | 职责 | 估时 |
|:---:|:---|:---:|
| L2-04 用户干预入口 | 5 类（panic/resume/pause/kill_wp/rework/change_request/switch_project）· **panic ≤ 100ms 硬约束** | 1.5 天 |
| L2-03 进度实时流 | SSE 长连接 · heartbeat · 断线重连 · 降级 polling | 1.5 天 |
| L2-02 Gate 决策卡片 | S1-S7 Gate 卡片展示 + 决策（pass/reject/need_input）| 1 天 |
| L2-05 KB 浏览器+候选晋升 | 3 层 KB 浏览 · IndexedDB 缓存 · 晋升审核 | 1 天 |

合计 **7 L2 · 8 天** + 0.5 集成 = **8.5 天** · ~27800 行代码。

### 代码目录

```
frontend/                # Vue 3 项目根
├── src/
│   ├── views/
│   │   ├── MainTab/         # L2-01
│   │   ├── GateCard/        # L2-02
│   │   ├── ProgressStream/  # L2-03
│   │   ├── UserIntervene/   # L2-04
│   │   ├── KbBrowser/       # L2-05
│   │   ├── TrimConfig/      # L2-06
│   │   └── Admin/           # L2-07
│   ├── stores/              # Pinia state stores
│   ├── router/
│   ├── composables/
│   ├── api/                 # 后端 API client
│   └── utils/
├── tests/
│   ├── unit/
│   └── e2e/                 # Playwright（可选）
└── package.json

backend/bff/                 # FastAPI BFF for UI
├── routes/
│   ├── gate_cards.py
│   ├── progress_stream.py   # SSE endpoint
│   ├── user_intervene.py
│   ├── kb_browse.py
│   └── admin.py
└── main.py
```

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | `2-prd/L1-10 .../prd.md §5.10` 7 L2 边界 |
| P0 | `3-1/L1-10/architecture.md` L1 内部 L2 协作 + SSE 架构 |
| P0 | `3-1/L1-10/L2-01~L2-07.md` 每份 §3 接口 · §11 错误码 |
| P0 | `3-2/L1-10/*.md` 392 TC |
| P0 | `ic-contracts.md §3.16 IC-16 · §3.17 IC-17 · §3.18 IC-18` |

---

## §3 WP 拆解（8 WP · 8.5 天）

| WP | 批 | L2 | 主题 | 估时 | TC |
|:---:|:---:|:---:|:---|:---:|:---:|
| θ-WP01 | θ1 | 基建 | Vue3 项目脚手架 + Pinia + router + API mock | 0.5 天 | - |
| θ-WP02 | θ1 | L2-01 | 11 主 Tab 主框架（vue-router + banner）| 1.5 天 | 55 |
| θ-WP03 | θ1 | L2-06 | 裁剪档 full/lean/custom 切换 | 0.75 天 | 44 |
| θ-WP04 | θ1 | L2-07 | Admin 8 子 tab | 0.75 天 | 61 |
| θ-WP05 | θ2 | L2-04 | 用户干预 5 类 · panic ≤ 100ms | 1.5 天 | 75 |
| θ-WP06 | θ2 | L2-03 | 进度流 SSE + heartbeat + 降级 | 1.5 天 | 60 |
| θ-WP07 | θ2 | L2-02 | Gate 决策卡片 S1-S7 | 1 天 | 53 |
| θ-WP08 | θ2 | L2-05 | KB 浏览器 + IndexedDB + 晋升审核 | 1 天 | 44 |
| θ-WP09 | - | 集成 | 前后端联调 · e2e | 0.5 天 | ≥ 10 |

### 3.1 WP-θ-01 · 基建

- Vue 3 + Vite 项目脚手架
- Pinia stores（decision_store · wbs_store · progress_store · kb_store）
- vue-router 配置（11 tab）
- API client（axios + 拦截器）· Dev-θ1 阶段用 mock
- CI：`npm run build` + type-check + lint

### 3.2 WP-θ-02 · L2-01 11 主 Tab 主框架

**L3**：
- 11 tab：overview / gate / artifacts / progress / wbs / decision_flow / quality / kb / retro / events / admin_entry
- vue-router 路由 · 每 tab 一个组件
- project 切换 banner（当前 pid · 警告跨 project 误操作）
- localStorage 持久化当前 tab
- 硬约束：tab 数量 = 11（E-10 TAB_COUNT_MISMATCH）

**DoD**：~55 TC（vitest + vue-test-utils）· 路由 · banner · 持久化 · commit `θ-WP02`

### 3.3 WP-θ-03 · L2-06 裁剪档

- full/lean/custom 3 档切换
- 存 localStorage + 同步到后端（PATCH /config/profile）
- 动态切换影响：某些 tab 在 LIGHT 下隐藏

**DoD**：~44 TC · commit `θ-WP03`

### 3.4 WP-θ-04 · L2-07 Admin 8 子 tab

- 8 子 tab：users / permissions / audit / backup / config / health / metrics / red_line_alerts
- 权限守护（非 admin 拒绝）
- 调后端 BFF `/admin/*` endpoints（mock）

**DoD**：~61 TC · commit `θ-WP04`

### 3.5 WP-θ-05 · L2-04 用户干预（panic 100ms 硬约束）

**L3**：
- 5 类干预：
  - `panic` · 全局红按钮 · 点击后 ≤ 100ms 触发 IC-17 state=PAUSED
  - `resume` · PAUSED → RUNNING
  - `pause` · RUNNING → PAUSED（软暂停）
  - `kill_wp` · 指定 wp_id 强杀
  - `rework` · 4 件套部分重做
  - `change_request` · TOGAF H 变更请求
  - `switch_project`（V2+）
- panic 硬路径：UI click → WebSocket 即发 IC-17 · 不经 axios request/response（避免额外 ~50ms RTT）
- 乐观 UI：点击后立即变 PAUSED 样式 · 不等 ack（后端失败再回滚）

**DoD**：~75 TC（L1-10 最重 L2）· panic e2e ≤ 100ms 硬约束测（Playwright + 后端 perf）· commit `θ-WP05`

### 3.6 WP-θ-06 · L2-03 进度实时流（SSE）

**L3**：
- SSE 订阅 `/progress/stream?pid=<pid>`
- heartbeat 10s · 超 30s 断线判定
- 断线重连（指数退避 · 最大 3 次）
- 降级链：SSE → polling（5s interval）→ 手动刷新
- 增量应用到 Pinia progress_store
- 超长事件流 · 虚拟滚动（vue-virtual-scroller）

**DoD**：~60 TC · SSE e2e + 降级链测 · commit `θ-WP06`

### 3.7 WP-θ-07 · L2-02 Gate 决策卡片

**L3**：
- S1/S2/S3/S5/S6 Gate 卡片
- 展示 evidence（引 4 件套 + PMP + TOGAF）· 展开查看
- 用户决策（pass / reject / need_input）· 触发 IC-17
- 幂等（同 gate_id 重复决策忽略）
- reject 必填 reason + fix_advice

**DoD**：~53 TC · commit `θ-WP07`

### 3.8 WP-θ-08 · L2-05 KB 浏览器 + IndexedDB

**L3**：
- 3 层 KB 浏览（session/project/global 分别 tab）
- 搜索 + 过滤（kind / tag）
- IndexedDB 本地缓存（500MB 上限）· 大 KB 首次加载后离线可用
- 晋升审核 UI（pending 列表 · one-click approve/reject）
- 调后端 BFF `/kb/*` endpoints

**DoD**：~44 TC · commit `θ-WP08`

### 3.9 WP-θ-09 · 前后端联调

- 所有 mock 替换为真实后端
- E2E（Playwright · 可选）：
  - 登录 → 选 project → 查看 Gate → 决策 → 看进度 → panic → resume
- PM-14 跨 project 隔离 e2e

**DoD**：e2e ≥ 10 TC · commit `θ-WP09`

---

## §4 依赖图

```
θ1（波 1 · 与 α 并行）
  WP01 基建 → WP02 主框架 → WP03 裁剪档 → WP04 Admin
                ↓
θ2（波 3 · 后端 ready 后）
  WP05 panic → WP06 SSE → WP07 Gate → WP08 KB
                              ↓
                          WP09 联调
```

### 跨组 mock（θ1 阶段）

| 后端 API | mock（θ1）| 真实（θ2）|
|:---|:---|:---|
| GET /projects/list | 固定 2 项目 | Dev-δ + Dev-α 真实 |
| GET /progress/stream (SSE) | 固定 fixture 事件 | Dev-ε 真实 |
| POST /user/intervene | mock ack | Dev-δ L2-01 + L1-01 主-2 真实 |
| GET /kb/browse | 固定 fixture | Dev-β L2-02 真实 |
| GET /audit/trail | 固定 | Dev-α L2-03 真实 |
| GET /gate/:id/card | 固定 | Dev-δ L2-01 真实 |

---

## §5 standup + commit

复用 Dev-α · prefix `θ-WPNN`。θ1 会话做 WP01-04 · 交接 θ2 会话做 WP05-09。

### commit 规范（前端）

```
feat(harnessFlow-ui): θ-WP02 L2-01 11 主 Tab 主框架（Vue 3 + vue-router + Pinia）
- tests: vitest 55 passed
- vue-tsc --noEmit 绿
- eslint 绿
```

---

## §6 自修正

- 情形 A · 11 tab 业务调整（某 tab 不需要）· 改 PRD §5.10.1 · 改代码同步
- 情形 D · IC-17 panic 字段语义 · 仲裁

---

## §7 对外契约

| IC | 角色 |
|:---|:---|
| IC-16 消费 | 接收 push_stage_gate_card（来自 L1-02 L2-01） |
| IC-17 发起 | 用户 panic/resume/intervene → L1-01 · **panic 100ms 硬约束** |
| IC-18 发起 | query_audit_trail → L1-09 L2-03 |

---

## §8 DoD（UI 特化）

- PM-14：所有视图按 pid 过滤 · 跨 project 拒绝 e2e
- panic 100ms 硬约束（benchmark 3 次均值）
- SSE 降级链 4 级全绿
- IndexedDB 限额（超则 warn）
- vue-tsc + eslint 全绿
- 392 TC（unit + e2e）· coverage ≥ 80%

---

## §9 风险

- **R-θ-01** panic 100ms 实测不达 · WebSocket 直发（跳 axios）
- **R-θ-02** SSE 在高并发下丢包 · polling 降级兜底
- **R-θ-03** IndexedDB 跨浏览器兼容 · 测 Chrome/Firefox/Safari
- **R-θ-04** 前后端 API schema 分歧 · 集成期冻结后再开工

---

## §10 交付清单

### 代码（~27800 行）

```
frontend/src/
├── views/           (7 模块 · ~15000 行 Vue + TS)
├── stores/          (~3000 行)
├── composables/     (~2000 行)
├── api/             (~2500 行)
├── router/ utils/   (~1500 行)

backend/bff/
├── routes/          (~3000 行 FastAPI)
└── main.py          (~800 行)
```

### 测试（~10000 行）· 392 unit TC + 10+ e2e · coverage ≥ 80%

### commit 15-18 个（θ1 · 5-6 · θ2 · 10-12）

---

*— Dev-θ · L1-10 UI · Execution Plan · v1.0 —*
