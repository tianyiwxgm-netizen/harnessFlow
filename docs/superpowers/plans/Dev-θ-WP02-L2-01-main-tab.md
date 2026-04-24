---
doc_id: dev-theta-wp02-plan
doc_type: superpowers-implementation-plan
source_exe_plan: docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-θ-L1-10-ui.md §3.2
source_tech_design: docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-01-11 主 Tab 主框架.md
parent_plan: docs/superpowers/plans/Dev-θ-impl.md
wp: θ-WP02
l2: L2-01
version: v1.0
status: active
updated_at: 2026-04-23
---

# Dev-θ · θ-WP02 · L2-01 11 主 Tab 主框架 · Plan

**Goal**: 搭 11 主 Tab 主框架（vue-router 懒加载每 tab 一个组件）+ pid banner（project 切换 + 跨 project 拦截）+ UISession pinia store + active_tab localStorage 持久化 + **11-tab 数量硬不变量（E-10）** · ≥ 55 unit TC · 全绿。

**Architecture**：
- 11 tab 用 `TAB_IDS` 常量数组 + TypeScript `readonly [11]` 元组固化编译期长度
- `src/domain/tabs.ts` · tab VO 定义 + 11 tab registry + runtime assert（E-10）
- `src/stores/ui_session.ts` · UISession Pinia store（active_project_id / active_tab / preferences）
- `src/router/index.ts` · vue-router 11 routes + lazy `import()` + `beforeEach` guard（pid 缺失→home）
- `src/views/MainTab/MainLayout.vue` · 顶部 pid banner + 侧栏 / 顶栏 tab 导航 + `<router-view />` · 读 ui_session store
- `src/views/MainTab/<TabId>View.vue` × 11 · 最小占位组件（tab title + current pid）
- localStorage 键：`harnessflow.active_tab`
- 跨 project 拦截：router.beforeEach 比较 URL query `?pid=` 与 ui_session.active_project_id

**Tech Stack**: 复用 WP01 · Vue3 + Vite + TS + Pinia + vue-router + vitest + happy-dom。

---

## §0 decision log（L2-01 spec 分歧）

L2-01 §1.5 D1/D2 声称「不用 vue-router / 不用 Pinia」(AD-05 `el-tabs + v-model`)，但 Dev-θ exe-plan §3.2 WP02 明写「vue-router 路由 · 每 tab 一个组件」+ WP01 已采 Pinia。

**决议**：以 exe-plan 为准（理由：WP01 基座已建；L2-01 spec 更早、未反映 exe-plan 的 Vite 栈决策）。追加一条 `projects/_correction_log.jsonl` 条目，待主会话合并时同步更新 L2-01 tech-design §1.5 D1/D2。

---

## §1 File Structure（本 WP 新建 / 修改）

```
frontend/src/
├── domain/
│   └── tabs.ts                          # 【新】TAB_IDS 常量 + TabRoute VO + 11-tab registry + E-10 assert
├── stores/
│   └── ui_session.ts                    # 【新】UISession Pinia store
├── router/
│   └── index.ts                         # 【改】11 routes + guard
├── views/
│   └── MainTab/
│       ├── MainLayout.vue               # 【新】顶层 shell: pid banner + tab nav + <router-view>
│       ├── OverviewView.vue             # 【新】tab 1 · 占位
│       ├── GateView.vue                 # 【新】tab 2 · 占位
│       ├── ArtifactsView.vue            # 【新】tab 3 · 占位
│       ├── ProgressView.vue             # 【新】tab 4 · 占位
│       ├── WbsView.vue                  # 【新】tab 5 · 占位
│       ├── DecisionFlowView.vue         # 【新】tab 6 · 占位
│       ├── QualityView.vue              # 【新】tab 7 · 占位
│       ├── KbView.vue                   # 【新】tab 8 · 占位
│       ├── RetroView.vue                # 【新】tab 9 · 占位
│       ├── EventsView.vue               # 【新】tab 10 · 占位
│       └── AdminEntryView.vue           # 【新】tab 11 · 占位
├── App.vue                              # 【改】去 pid indicator（搬 MainLayout）· 只保留 <router-view />
└── utils/
    └── last_tab.ts                      # 【新】active_tab localStorage 持久化

frontend/tests/unit/
└── main_tab/
    ├── tabs.registry.test.ts            # 11-tab 契约（长度/唯一/枚举）· ~15 TC
    ├── ui_session.store.test.ts         # UISession Pinia store · ~12 TC
    ├── router.guards.test.ts            # router guard（pid 缺失/跨 pid/重定向）· ~10 TC
    ├── main_layout.test.ts              # MainLayout 组件渲染 · ~8 TC
    ├── last_tab.test.ts                 # localStorage 持久化 · ~6 TC
    └── tab_views.test.ts                # 11 placeholder views 参数化测 · ~11 TC
```

**总计新增 TC ≥ 55**（目标 62，留余量）。

---

## §2 Task Breakdown（6 任务 · TDD）

| Task | 主题 | 文件 | TC | 状态 |
|:---:|---|---|:---:|:---:|
| WP02-1 | 11-tab domain 常量 + registry + E-10 | `src/domain/tabs.ts` + test | 15 | pending |
| WP02-2 | `last_tab` localStorage utils | `src/utils/last_tab.ts` + test | 6 | pending |
| WP02-3 | UISession Pinia store | `src/stores/ui_session.ts` + test | 12 | pending |
| WP02-4 | vue-router 11 routes + guard | `src/router/index.ts`（改）+ test | 10 | pending |
| WP02-5 | MainLayout + 11 placeholder views | `src/views/MainTab/*.vue` + tests | 19 | pending |
| WP02-6 | App.vue 精简 + E2E smoke + commit | `src/App.vue`（改） | — | pending |

---

## §3 关键契约速查

**11 tab enum（固定顺序 · CFG-01/02）**：
```typescript
export const TAB_IDS = [
  'overview',
  'gate',
  'artifacts',
  'progress',
  'wbs',
  'decision_flow',
  'quality',
  'kb',
  'retro',
  'events',
  'admin_entry',
] as const;
export type TabId = typeof TAB_IDS[number];
```

**TabRoute VO**：`{ id: TabId, title: string, order: number, path: string, componentLoader: () => Promise<Component> }`

**UISession state**：`{ activeProjectId: string | null, activeTabId: TabId, preferences: { tabOrder: TabId[], theme: 'light'|'dark'|'auto' } }`

**Router guard 规则**：
1. 路径 `/` → 重定向到 `/tabs/:activeTabId`（从 localStorage 读，默认 `overview`）
2. 路径 `/tabs/<未知>` → 重定向 `/tabs/overview` + console.warn
3. 路径 `?pid=<x>` 且 `x !== ui_session.activeProjectId`（两者皆非 null）→ 拒绝 + emit `cross_project_access_denied` + 重定向 home
4. 路径 `?pid=<x>` 且 activeProjectId 为 null → 作为激活动作，写 store
5. 合法路径 → 更新 `ui_session.activeTabId` + 持久化 localStorage

**E-10 TAB_COUNT_MISMATCH 断言**：`src/domain/tabs.ts` 模块加载期 `console.assert(TAB_IDS.length === 11)` + 导出 `assertTabContract()` 函数可运行期调用。

---

## §4 DoD

- [ ] `npm run test:unit` · ≥ 55 TC 全绿（目标 62）
- [ ] `npm run build` 绿（vue-tsc 零错）
- [ ] `npm run lint` 绿（0 warning）
- [ ] `npm run dev` 起得来 · 浏览器打开 `/` 自动跳 `/tabs/overview` · 11 tab 点击切换正常
- [ ] pid banner 显示 `无活动项目` 或当前 pid · 跨 pid URL 被拦
- [ ] localStorage 持久化当前 tab（刷新后保持）

---

## §5 commit 规划

1. `WP02-1~2`：domain/tabs + utils/last_tab（基础构件）
2. `WP02-3`：UISession store
3. `WP02-4`：router 11 routes + guard
4. `WP02-5`：MainLayout + 11 views + tests
5. `WP02-6`：App.vue + standup + correction log

---

*— Dev-θ · WP02 · L2-01 plan · v1.0 —*
