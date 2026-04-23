---
doc_id: dev-theta-impl-plan
doc_type: superpowers-implementation-plan
source_exe_plan: docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-θ-L1-10-ui.md
session: Dev-θ
version: v1.0
status: active
updated_at: 2026-04-23
---

# Dev-θ · L1-10 人机协作 UI · Implementation Plan（Index + WP01）

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 harnessFlow L1-10 人机协作 UI 完整栈（Vue 3 SPA + FastAPI BFF · 7 L2 · 11 主 Tab + Gate 卡片 + SSE 进度流 + 用户干预 panic ≤100ms + KB 浏览器 + 裁剪档 + Admin）· 发起 IC-17 · 消费 IC-16 · 查询 IC-18 · 满足 PM-14（pid 过滤）。

**Architecture:** 前端 Vue 3 + Vite + TypeScript + Pinia + vue-router · 7 个 views 模块对应 7 L2 · Pinia stores 承接 BC-10 3 个聚合根（UISession / GateCard / InterventionIntent）· composables 封装 SSE / WebSocket / IndexedDB · api/ 层封装 axios（通过 BFF 转发到各 L1）。后端 FastAPI BFF 承载 UI 专属 endpoints（/projects/*, /progress/stream SSE, /user/intervene, /kb/browse, /admin/*, /audit/trail），内部消费其他 L1 的 IC。

**Tech Stack:**
- Frontend: Vue 3.4 + Vite 5 + TypeScript 5 + Pinia 2 + vue-router 4 + Element Plus 2.5 + axios + vue-virtual-scroller
- Testing (FE): vitest + @vue/test-utils + @testing-library/vue + jsdom + Playwright（e2e）
- Backend BFF: FastAPI 0.110+ + uvicorn + pydantic v2 + sse-starlette + httpx（转发到 L1-*）
- Testing (BE): pytest + pytest-asyncio + httpx.AsyncClient

---

## §0 前置与依赖状态（2026-04-23）

**技术栈决议（锁定）：**
- arch.md §4 原文"Vue 3 **CDN** + 零 npm"与 Dev-θ exe-plan §3"Vue 3 + Vite + Pinia + vue-router + vue-tsc + eslint + vitest + Playwright + IndexedDB + vue-virtual-scroller"冲突。
- 以 **exe-plan 为准**（依据：exe-plan DoD §8 明确 vue-tsc + eslint + 392 TC + vue-virtual-scroller · 这些均需 npm 生态；CDN 方案无法满足 392 TC 单元测试与 IndexedDB + 虚拟滚动工程化要求）。
- 自修正登记：需写入 `projects/_correction_log.jsonl`（会话尾）并在 Dev-θ 合并时提请主会话更新 arch.md §4 tech_stack 从 "Vue 3 CDN" 改为 "Vue 3 + Vite"（§6 情形 A）。

**代码所有权（CODE-OWNERSHIP-MATRIX.md 3 铁律）：**
- 本 session 只写 `frontend/**` + `backend/bff/**` + `tests/bff/**`
- `pyproject.toml` / `tests/conftest.py` / 共享 scripts — **冻结 · 合并时找主会话**
- 跨 L1 消费只通过 IC（本 session 阶段用 mock）

**现状盘点：**
- `ui/` 目录下有早期 toy prototype（单 HTML + mock_data.py + server.py）· **保留不动 · 视为 archive**
- 真正 Dev-θ 产出在仓库根的 `frontend/` + `backend/bff/`
- 当前 `app/` 只有 l1_02 / l1_06 / l1_09（波 1-2 交付），其他 L1 未 ready → BFF 全用本地 mock
- `pyproject.toml` 已存在（主会话管） · 本 session 不改，但追加 BFF 依赖由主会话合并

**Mock 替换清单（θ2 阶段切真实）：**

| Mock | 位置 | 真实来源 | 切换时机 |
|---|---|---|---|
| `GET /api/projects/list` | `backend/bff/_mocks/projects.py` | Dev-δ L2-02 | δ 交付后 |
| `GET /api/progress/stream` (SSE) | `backend/bff/_mocks/progress.py` | L1-09 events.jsonl 订阅（Dev-α） | α WP04 后 |
| `POST /api/user/intervene` (IC-17) | `backend/bff/_mocks/intervene.py` | L1-01 主会话 main-2 | main-2 后 |
| `GET /api/kb/browse` (IC-06) | `backend/bff/_mocks/kb.py` | Dev-β L1-06 L2-02 | β WP03 后 |
| `GET /api/audit/trail` (IC-18) | `backend/bff/_mocks/audit.py` | Dev-α L2-03 | α 后 |
| `GET /api/gate/:id/card` (IC-16) | `backend/bff/_mocks/gate.py` | Dev-δ L2-01 | δ 后 |

---

## §1 File Structure（锁定单责）

```
harnessFlow/
├── frontend/                              # Vue 3 SPA 根（新建）
│   ├── package.json                       # npm 依赖 + scripts（dev/build/test/lint/type-check）
│   ├── tsconfig.json                      # TS 配置
│   ├── tsconfig.node.json                 # vite.config.ts 用
│   ├── vite.config.ts                     # Vite 配置（代理 /api → :8001）
│   ├── vitest.config.ts                   # vitest 配置
│   ├── .eslintrc.cjs                      # ESLint + Vue 规则
│   ├── .prettierrc.json                   # Prettier
│   ├── index.html                         # Vite 入口
│   ├── playwright.config.ts               # Playwright e2e 配置（WP09 激活）
│   ├── public/                            # 静态资源
│   │   └── favicon.svg
│   ├── src/
│   │   ├── main.ts                        # Vue 启动入口（createApp + router + pinia + Element Plus）
│   │   ├── App.vue                        # 根组件（<router-view />）
│   │   ├── env.d.ts                       # import.meta.env 类型
│   │   ├── router/
│   │   │   └── index.ts                   # vue-router 配置（WP01 占位 / WP02 完善）
│   │   ├── stores/                        # Pinia stores（WP01 骨架 / 各 WP 填充）
│   │   │   ├── index.ts                   # pinia instance
│   │   │   ├── ui_session.ts              # UISession 聚合根（WP02）
│   │   │   ├── gate_card.ts               # GateCard 聚合根（WP07）
│   │   │   ├── progress.ts                # 进度流（WP06）
│   │   │   ├── kb.ts                      # KB 浏览（WP08）
│   │   │   └── trim_profile.ts            # 裁剪档（WP03）
│   │   ├── api/                           # axios client + typed endpoints
│   │   │   ├── client.ts                  # axios instance + 拦截器（添加 pid header）
│   │   │   ├── projects.ts                # /api/projects/*
│   │   │   ├── progress.ts                # /api/progress/*
│   │   │   ├── intervene.ts               # /api/user/intervene
│   │   │   ├── gate.ts                    # /api/gate/*
│   │   │   ├── kb.ts                      # /api/kb/*
│   │   │   ├── audit.ts                   # /api/audit/*
│   │   │   └── admin.ts                   # /api/admin/*
│   │   ├── composables/                   # 可复用 composition hooks
│   │   │   ├── useSSE.ts                  # WP06
│   │   │   ├── useWebSocket.ts            # WP05 panic
│   │   │   ├── useIndexedDB.ts            # WP08
│   │   │   └── useLocalStorage.ts         # WP03 裁剪档持久化
│   │   ├── views/                         # 7 L2 对应 7 模块
│   │   │   ├── MainTab/                   # L2-01（WP02）
│   │   │   ├── GateCard/                  # L2-02（WP07）
│   │   │   ├── ProgressStream/            # L2-03（WP06）
│   │   │   ├── UserIntervene/             # L2-04（WP05）
│   │   │   ├── KbBrowser/                 # L2-05（WP08）
│   │   │   ├── TrimConfig/                # L2-06（WP03）
│   │   │   └── Admin/                     # L2-07（WP04）
│   │   └── utils/
│   │       ├── pid.ts                     # PM-14 pid 上下文工具（读 localStorage）
│   │       └── logger.ts                  # 前端日志
│   └── tests/
│       ├── setup.ts                       # vitest setup
│       ├── smoke/                         # WP01 冒烟
│       │   └── app.test.ts
│       ├── unit/                          # 各 WP 单测
│       │   └── .gitkeep
│       └── e2e/                           # Playwright（WP09）
│           └── .gitkeep
│
├── backend/
│   └── bff/                               # FastAPI BFF for UI（新建）
│       ├── __init__.py
│       ├── main.py                        # FastAPI app + CORS + 路由注册
│       ├── config.py                      # pydantic Settings（端口 / L1 endpoint url）
│       ├── deps.py                        # FastAPI Depends（pid 验证 / 权限守护）
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── health.py                  # GET /api/health（WP01）
│       │   ├── projects.py                # GET /api/projects/list（WP02）
│       │   ├── gate_cards.py              # WP07
│       │   ├── progress_stream.py         # SSE（WP06）
│       │   ├── user_intervene.py          # WP05 · IC-17 入口
│       │   ├── kb_browse.py               # WP08
│       │   ├── audit_trail.py             # IC-18 转发
│       │   └── admin.py                   # WP04
│       └── _mocks/                        # 依赖未 ready 期本地桩
│           ├── __init__.py
│           ├── projects.py
│           ├── progress.py
│           ├── intervene.py
│           ├── gate.py
│           ├── kb.py
│           └── audit.py
│
└── tests/
    └── bff/                               # 后端 BFF pytest（镜像 backend/bff/）
        ├── __init__.py
        ├── conftest.py                    # AsyncClient fixture
        └── smoke/
            └── test_health.py             # WP01
```

---

## §2 WP 进度跟踪（9 WP · 8.5 天）

| WP | 批 | L2 | 主题 | TC | 状态 | 详细计划 |
|:---:|:---:|:---:|:---|:---:|:---:|:---|
| **WP01** | θ1 | 基建 | Vue3 + BFF 脚手架 + Pinia + router + mock API | 冒烟 ≥ 4 | **本会话** | §3 本文档内 |
| WP02 | θ1 | L2-01 | 11 主 Tab + pid banner | 55 | pending | 下一 session · 单独 plan |
| WP03 | θ1 | L2-06 | 裁剪档 LIGHT/STANDARD/HEAVY | 44 | pending | 同上 |
| WP04 | θ1 | L2-07 | Admin 8 子 tab | 61 | pending | 同上 |
| WP05 | θ2 | L2-04 | panic ≤100ms + 干预 5 类 | 75 | pending | 同上（θ2 关键 WP）|
| WP06 | θ2 | L2-03 | SSE 进度流 + 降级链 | 60 | pending | 同上 |
| WP07 | θ2 | L2-02 | Gate 卡片 S1-S7 | 53 | pending | 同上 |
| WP08 | θ2 | L2-05 | KB 浏览 + IndexedDB + 晋升 | 44 | pending | 同上 |
| WP09 | - | 集成 | 前后端联调 + Playwright e2e | ≥ 10 | pending | 同上 |

**合计**：9 WP · 392 单元 TC + 10 e2e TC · ~27,800 LoC · 8.5 天墙钟。

---

## §3 WP-θ-01 · 基建脚手架（0.5 天 · 本会话）

### §3.0 目标 / DoD

**目标**：搭起 Vue 3 + Vite + TypeScript + Pinia + vue-router 前端骨架 + FastAPI BFF 骨架，并跑通最小端到端回路（前端 App 挂载 + 调 BFF /api/health + 返 `{status: "ok", pid: null}`）。

**DoD（必须全绿才能 commit θ-WP01）：**
1. `cd frontend && npm install` 成功
2. `cd frontend && npm run build` 绿（vite build + vue-tsc --noEmit 零错误）
3. `cd frontend && npm run lint` 绿
4. `cd frontend && npm run test:unit` 绿（≥ 4 冒烟 TC 通过）
5. `cd frontend && npm run dev` 起得来（启后 curl http://localhost:5173 返 200）
6. `cd backend/bff && uvicorn backend.bff.main:app --port 8001` 起得来 · `curl http://localhost:8001/api/health` 返 `{"status": "ok", "pid": null, "version": "0.1.0"}`
7. `pytest tests/bff/smoke -v` 绿（BFF 冒烟 ≥ 2 TC）
8. Vite 代理配置：`/api` → `http://localhost:8001`（前端 dev server `fetch('/api/health')` 应返同样 JSON）

---

### §3.1 Task 01-01 · Frontend `package.json` + `tsconfig` + `vite.config.ts` 骨架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/.eslintrc.cjs`
- Create: `frontend/.prettierrc.json`
- Create: `frontend/.gitignore`
- Create: `frontend/env.d.ts`

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "harnessflow-ui",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview",
    "test:unit": "vitest run",
    "test:unit:watch": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint . --ext .vue,.ts,.tsx --max-warnings 0",
    "format": "prettier --write src/ tests/",
    "type-check": "vue-tsc --noEmit"
  },
  "dependencies": {
    "vue": "^3.4.21",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7",
    "element-plus": "^2.6.1",
    "@element-plus/icons-vue": "^2.3.1",
    "axios": "^1.6.8"
  },
  "devDependencies": {
    "@playwright/test": "^1.42.1",
    "@vitejs/plugin-vue": "^5.0.4",
    "@vue/test-utils": "^2.4.5",
    "@testing-library/vue": "^8.0.2",
    "@types/node": "^20.11.30",
    "@typescript-eslint/eslint-plugin": "^7.3.1",
    "@typescript-eslint/parser": "^7.3.1",
    "eslint": "^8.57.0",
    "eslint-plugin-vue": "^9.23.0",
    "jsdom": "^24.0.0",
    "prettier": "^3.2.5",
    "typescript": "^5.4.3",
    "vite": "^5.2.6",
    "vitest": "^1.4.0",
    "vue-tsc": "^2.0.7"
  }
}
```

- [ ] **Step 2: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["vite/client", "vitest/globals"]
  },
  "include": ["src/**/*", "src/**/*.vue", "tests/**/*", "env.d.ts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Write `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts", "vitest.config.ts", "playwright.config.ts"]
}
```

- [ ] **Step 4: Write `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'es2022',
    sourcemap: true,
  },
});
```

- [ ] **Step 5: Write `frontend/vitest.config.ts`**

```typescript
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,vue}'],
    },
  },
});
```

- [ ] **Step 6: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HarnessFlow UI</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 7: Write `frontend/.eslintrc.cjs`**

```javascript
module.exports = {
  root: true,
  env: { browser: true, node: true, es2022: true },
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 2022,
    sourceType: 'module',
    extraFileExtensions: ['.vue'],
  },
  plugins: ['@typescript-eslint', 'vue'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:vue/vue3-recommended',
  ],
  rules: {
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'vue/multi-word-component-names': 'off',
  },
  ignorePatterns: ['dist', 'node_modules', 'coverage'],
};
```

- [ ] **Step 8: Write `frontend/.prettierrc.json`**

```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "endOfLine": "lf"
}
```

- [ ] **Step 9: Write `frontend/.gitignore`**

```
node_modules/
dist/
coverage/
.vitest-cache/
*.log
.DS_Store
playwright-report/
test-results/
```

- [ ] **Step 10: Write `frontend/env.d.ts`**

```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 11: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/tsconfig.node.json \
        frontend/vite.config.ts frontend/vitest.config.ts frontend/index.html \
        frontend/.eslintrc.cjs frontend/.prettierrc.json frontend/.gitignore \
        frontend/env.d.ts
git commit -m "chore(harnessFlow-ui): θ-WP01-1 Vue3+Vite+TS 骨架配置

- package.json · scripts: dev/build/test:unit/lint/type-check
- tsconfig + vite.config + vitest.config（proxy /api→:8001）
- ESLint + Prettier + gitignore"
```

---

### §3.2 Task 01-02 · Frontend 最小运行时（main.ts + App.vue + router + stores + smoke test）

**Files:**
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/utils/pid.ts`
- Create: `frontend/tests/setup.ts`
- Create: `frontend/tests/smoke/app.test.ts`
- Create: `frontend/tests/smoke/pid.test.ts`
- Create: `frontend/tests/smoke/client.test.ts`
- Create: `frontend/tests/smoke/router.test.ts`
- Create: `frontend/public/favicon.svg`

- [ ] **Step 1: Write failing smoke test `frontend/tests/smoke/app.test.ts`**

```typescript
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import App from '@/App.vue';
import { createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes } from '@/router/index';

describe('App.vue smoke', () => {
  it('mounts with router + pinia and renders <router-view />', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes });
    const pinia = createPinia();
    await router.push('/');
    await router.isReady();
    const wrapper = mount(App, { global: { plugins: [router, pinia] } });
    expect(wrapper.html()).toContain('data-test="app-root"');
  });
});
```

- [ ] **Step 2: Write failing smoke test `frontend/tests/smoke/pid.test.ts`**

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { getActivePid, setActivePid, clearActivePid, PID_STORAGE_KEY } from '@/utils/pid';

describe('pid utils (PM-14)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when no pid is set', () => {
    expect(getActivePid()).toBeNull();
  });

  it('persists and reads pid from localStorage', () => {
    setActivePid('pj-abc123');
    expect(localStorage.getItem(PID_STORAGE_KEY)).toBe('pj-abc123');
    expect(getActivePid()).toBe('pj-abc123');
  });

  it('clears pid', () => {
    setActivePid('pj-abc123');
    clearActivePid();
    expect(getActivePid()).toBeNull();
    expect(localStorage.getItem(PID_STORAGE_KEY)).toBeNull();
  });

  it('rejects empty string pid', () => {
    expect(() => setActivePid('')).toThrow(/pid must be non-empty/);
  });
});
```

- [ ] **Step 3: Write failing smoke test `frontend/tests/smoke/client.test.ts`**

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { apiClient, PID_HEADER } from '@/api/client';
import { setActivePid, clearActivePid } from '@/utils/pid';

describe('apiClient', () => {
  beforeEach(() => {
    clearActivePid();
  });

  it('has /api as baseURL', () => {
    expect(apiClient.defaults.baseURL).toBe('/api');
  });

  it('omits pid header when no active pid', () => {
    const headers = (apiClient.defaults.headers.common ?? {}) as Record<string, string>;
    expect(headers[PID_HEADER]).toBeUndefined();
  });

  it('adds X-Harness-Pid header via interceptor when pid is active', async () => {
    setActivePid('pj-xyz');
    const config = { headers: {} as Record<string, string> };
    // @ts-expect-error private API — interceptor[0] is our injector
    const handler = apiClient.interceptors.request.handlers[0].fulfilled;
    const result = await handler(config);
    expect(result.headers[PID_HEADER]).toBe('pj-xyz');
  });
});
```

- [ ] **Step 4: Write failing smoke test `frontend/tests/smoke/router.test.ts`**

```typescript
import { describe, it, expect } from 'vitest';
import { routes } from '@/router/index';

describe('router routes (WP01 placeholder)', () => {
  it('has a root route "/" named "home"', () => {
    const root = routes.find((r) => r.path === '/');
    expect(root).toBeDefined();
    expect(root?.name).toBe('home');
  });

  it('has 404 fallback', () => {
    const fallback = routes.find((r) => r.path === '/:pathMatch(.*)*');
    expect(fallback).toBeDefined();
  });
});
```

- [ ] **Step 5: Run tests to verify they all fail**

Run: `cd frontend && npm install && npm run test:unit`
Expected: 4 tests FAIL with "cannot find module '@/App.vue'" / "'@/utils/pid'" / "'@/api/client'" / "'@/router/index'"

- [ ] **Step 6: Write `frontend/tests/setup.ts`**

```typescript
import { afterEach } from 'vitest';

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
```

- [ ] **Step 7: Write `frontend/src/utils/pid.ts`**

```typescript
export const PID_STORAGE_KEY = 'harnessflow.active_pid';

export function getActivePid(): string | null {
  return localStorage.getItem(PID_STORAGE_KEY);
}

export function setActivePid(pid: string): void {
  if (!pid) {
    throw new Error('pid must be non-empty');
  }
  localStorage.setItem(PID_STORAGE_KEY, pid);
}

export function clearActivePid(): void {
  localStorage.removeItem(PID_STORAGE_KEY);
}
```

- [ ] **Step 8: Write `frontend/src/api/client.ts`**

```typescript
import axios, { type InternalAxiosRequestConfig } from 'axios';
import { getActivePid } from '@/utils/pid';

export const PID_HEADER = 'X-Harness-Pid';

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const pid = getActivePid();
  if (pid) {
    config.headers.set(PID_HEADER, pid);
  }
  return config;
});
```

- [ ] **Step 9: Write `frontend/src/router/index.ts`**

```typescript
import type { RouteRecordRaw } from 'vue-router';
import { createRouter, createWebHistory } from 'vue-router';

// WP01 骨架 · WP02 会替换为 11 tab 完整路由
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/App.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    redirect: '/',
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
```

- [ ] **Step 10: Write `frontend/src/stores/index.ts`**

```typescript
import { createPinia } from 'pinia';

export const pinia = createPinia();
```

- [ ] **Step 11: Write `frontend/src/App.vue`**

```vue
<template>
  <div data-test="app-root" class="harness-app">
    <header class="harness-header">
      <h1>HarnessFlow</h1>
      <span class="pid-indicator" data-test="pid-indicator">
        {{ activePid ?? '无活动项目' }}
      </span>
    </header>
    <main class="harness-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getActivePid } from '@/utils/pid';

const activePid = ref<string | null>(null);

onMounted(() => {
  activePid.value = getActivePid();
});
</script>

<style scoped>
.harness-app {
  font-family: system-ui, -apple-system, sans-serif;
  min-height: 100vh;
}
.harness-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: #1e293b;
  color: white;
}
.pid-indicator {
  font-size: 0.875rem;
  opacity: 0.85;
}
</style>
```

- [ ] **Step 12: Write `frontend/src/main.ts`**

```typescript
import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import App from './App.vue';
import { router } from './router';
import { pinia } from './stores';

const app = createApp(App);
app.use(pinia);
app.use(router);
app.use(ElementPlus);
app.mount('#app');
```

- [ ] **Step 13: Write `frontend/public/favicon.svg`**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#1e293b"/><text x="16" y="22" font-family="system-ui" font-size="18" font-weight="700" fill="#fff" text-anchor="middle">H</text></svg>
```

- [ ] **Step 14: Re-run unit tests**

Run: `cd frontend && npm run test:unit`
Expected: 4 tests PASS (app.test.ts · pid.test.ts · client.test.ts · router.test.ts)

- [ ] **Step 15: Verify build + lint + type-check**

Run: `cd frontend && npm run lint && npm run build`
Expected: lint PASS · vue-tsc --noEmit PASS · vite build writes `dist/` with no errors

- [ ] **Step 16: Commit**

```bash
git add frontend/src frontend/tests frontend/public
git commit -m "feat(harnessFlow-ui): θ-WP01-2 Vue3 最小运行时 + 4 冒烟 TC

- App.vue 根组件 + pid indicator（PM-14 占位）
- main.ts · router/index.ts · stores/index.ts · api/client.ts
- utils/pid.ts（localStorage 持久化 PM-14 active pid）
- 4 smoke TC: App mount / pid utils / apiClient / router routes
- npm run test:unit PASS · npm run build PASS · npm run lint PASS"
```

---

### §3.3 Task 01-03 · Backend BFF 骨架 + health + CORS + pytest smoke

**Files:**
- Create: `backend/__init__.py` (if not exists)
- Create: `backend/bff/__init__.py`
- Create: `backend/bff/main.py`
- Create: `backend/bff/config.py`
- Create: `backend/bff/deps.py`
- Create: `backend/bff/routes/__init__.py`
- Create: `backend/bff/routes/health.py`
- Create: `backend/bff/_mocks/__init__.py`
- Create: `tests/bff/__init__.py`
- Create: `tests/bff/conftest.py`
- Create: `tests/bff/smoke/__init__.py`
- Create: `tests/bff/smoke/test_health.py`

- [ ] **Step 1: Write failing test `tests/bff/smoke/test_health.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport

from backend.bff.main import app


@pytest.mark.asyncio
async def test_health_returns_200_and_status_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["pid"] is None


@pytest.mark.asyncio
async def test_health_echoes_pid_header_when_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health", headers={"X-Harness-Pid": "pj-abc"})
    assert response.status_code == 200
    assert response.json()["pid"] == "pj-abc"


@pytest.mark.asyncio
async def test_cors_allows_vite_dev_origin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
```

- [ ] **Step 2: Write `tests/bff/conftest.py`**

```python
import pytest


@pytest.fixture
def pid_header() -> dict[str, str]:
    return {"X-Harness-Pid": "pj-test-001"}
```

- [ ] **Step 3: Create empty `__init__.py` files**

Run:
```bash
touch tests/bff/__init__.py tests/bff/smoke/__init__.py
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/bff/smoke -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.bff'"

- [ ] **Step 5: Write `backend/__init__.py` (if missing) and `backend/bff/__init__.py`**

Both files empty (or `backend/__init__.py` should exist — check first; do not overwrite).

Run:
```bash
[ -f backend/__init__.py ] || touch backend/__init__.py
touch backend/bff/__init__.py
touch backend/bff/routes/__init__.py
touch backend/bff/_mocks/__init__.py
```

- [ ] **Step 6: Write `backend/bff/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bff_version: str = "0.1.0"
    bff_port: int = 8001
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    pid_header_name: str = "X-Harness-Pid"

    model_config = SettingsConfigDict(env_prefix="HARNESS_", env_file=".env", extra="ignore")


settings = Settings()
```

- [ ] **Step 7: Write `backend/bff/deps.py`**

```python
from typing import Annotated

from fastapi import Header

from backend.bff.config import settings


def get_active_pid(
    x_harness_pid: Annotated[str | None, Header(alias=settings.pid_header_name)] = None,
) -> str | None:
    """
    PM-14 · 从请求头 X-Harness-Pid 读取当前 project id。
    WP01 阶段允许为 None（表示无活动项目）。
    后续 WP 的 write 类 endpoint 会把 None 升为 422。
    """
    return x_harness_pid
```

- [ ] **Step 8: Write `backend/bff/routes/health.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.bff.config import settings
from backend.bff.deps import get_active_pid

router = APIRouter()


@router.get("/health", tags=["system"])
async def health(
    pid: Annotated[str | None, Depends(get_active_pid)],
) -> dict[str, str | None]:
    return {
        "status": "ok",
        "version": settings.bff_version,
        "pid": pid,
    }
```

- [ ] **Step 9: Write `backend/bff/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.bff.config import settings
from backend.bff.routes import health

app = FastAPI(
    title="HarnessFlow BFF",
    version=settings.bff_version,
    description="Backend-for-Frontend for L1-10 Human-Agent Collaboration UI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[settings.pid_header_name],
)

app.include_router(health.router, prefix="/api")
```

- [ ] **Step 10: Install deps (if missing)**

Check if `fastapi`, `httpx`, `pydantic-settings`, `sse-starlette` are in the root `pyproject.toml`. If not — **STOP** and flag to main session (per CODE-OWNERSHIP-MATRIX: `pyproject.toml` is frozen). For WP01 we only need `fastapi` + `uvicorn` + `httpx` + `pydantic-settings` + `pytest-asyncio`.

Run: `pip install fastapi 'uvicorn[standard]' httpx pydantic-settings pytest-asyncio`

(Note in standup log: "BFF 依赖临时 pip install · 待主会话合并进 pyproject.toml dev-group")

- [ ] **Step 11: Re-run pytest**

Run: `pytest tests/bff/smoke -v`
Expected: 3 tests PASS

- [ ] **Step 12: Start BFF and smoke-test with curl**

Run:
```bash
uvicorn backend.bff.main:app --port 8001 &
BFF_PID=$!
sleep 2
curl -s http://localhost:8001/api/health
# Expected: {"status":"ok","version":"0.1.0","pid":null}
curl -s -H "X-Harness-Pid: pj-smoke" http://localhost:8001/api/health
# Expected: {"status":"ok","version":"0.1.0","pid":"pj-smoke"}
kill $BFF_PID
```

- [ ] **Step 13: Commit**

```bash
git add backend/bff backend/__init__.py tests/bff
git commit -m "feat(harnessFlow-ui): θ-WP01-3 FastAPI BFF 骨架 + /api/health + 3 smoke TC

- backend/bff: main.py · config.py · deps.py · routes/health.py
- CORS 允许 vite dev (localhost:5173)
- X-Harness-Pid header 透传 (PM-14 占位)
- tests/bff/smoke/test_health.py · 3 TC pass
- pytest + uvicorn + curl 全链路验证 OK"
```

---

### §3.4 Task 01-04 · Vite → BFF 代理 E2E 冒烟 + standup log

**Files:**
- Create: `docs/4-exe-plan/standup-logs/Dev-θ-2026-04-23.md`
- Create: `projects/_correction_log.jsonl`（追加一行）

- [ ] **Step 1: Start BFF + frontend dev server in background**

Run:
```bash
(uvicorn backend.bff.main:app --port 8001 >/tmp/harnessflow-bff.log 2>&1 &)
(cd frontend && npm run dev -- --port 5173 >/tmp/harnessflow-fe.log 2>&1 &)
sleep 5
```

- [ ] **Step 2: Verify proxied call through Vite**

Run:
```bash
curl -s http://localhost:5173/api/health
# Expected: {"status":"ok","version":"0.1.0","pid":null}
```

Expected: matches BFF direct response (Vite proxy forwards /api → :8001).

- [ ] **Step 3: Teardown dev servers**

Run:
```bash
pkill -f 'uvicorn backend.bff.main'
pkill -f 'vite'
```

- [ ] **Step 4: Append self-correction log entry**

If `projects/` dir does not exist yet, create it:
```bash
mkdir -p projects
```

Then append to `projects/_correction_log.jsonl`:

```json
{"ts":"2026-04-23T00:00:00+08:00","session":"Dev-θ","pid":"root","type":"doc-inconsistency","target":"docs/3-1-Solution-Technical/L1-10-人机协作UI/architecture.md §4","from":"Vue 3 CDN + 零 npm","to":"Vue 3 + Vite + Pinia + vue-router（exe-plan §3 WP01 实际采纳）","reason":"exe-plan DoD §8 要求 vue-tsc + eslint + 392 单元 TC + vue-virtual-scroller + IndexedDB 工程化，CDN 方案无法满足。决议以 exe-plan 为准；arch.md §4 需主会话在合并 Dev-θ 时同步更新（§6 情形 A）。","scope":"L1-10","requires_master_session":true}
```

- [ ] **Step 5: Write standup log `docs/4-exe-plan/standup-logs/Dev-θ-2026-04-23.md`**

```markdown
---
session: Dev-θ
date: 2026-04-23
wp_range: θ-WP01（基建）
status: done
---

# Dev-θ standup · 2026-04-23 · WP01 基建

## 完成

- **θ-WP01-1** Vue3 + Vite + TS 骨架配置（10 文件）
- **θ-WP01-2** Vue3 最小运行时 + 4 smoke TC（全绿）
  - App.vue · router/stores · api/client · utils/pid
- **θ-WP01-3** FastAPI BFF 骨架 + /api/health + 3 smoke TC（全绿）
- **θ-WP01-4** Vite→BFF 代理冒烟 OK（curl http://localhost:5173/api/health 正常）

## DoD 自检

| DoD | 状态 |
|---|:---:|
| npm install | ✅ |
| npm run build（含 vue-tsc） | ✅ |
| npm run lint | ✅ |
| npm run test:unit（4 TC） | ✅ |
| npm run dev 起得来 | ✅ |
| uvicorn backend.bff.main:app 起得来 | ✅ |
| curl /api/health 返 status=ok + pid 透传 | ✅ |
| pytest tests/bff/smoke（3 TC） | ✅ |
| Vite 代理 /api→:8001 | ✅ |

## 待决策 / 风险

- **arch.md §4 tech_stack 与 exe-plan 分歧** · 已登记到 `projects/_correction_log.jsonl` · 待主会话合并 Dev-θ 时同步改 arch.md（§6 情形 A）。
- **BFF 依赖临时 pip install**（fastapi / uvicorn / httpx / pydantic-settings / pytest-asyncio）· 需主会话合并到 `pyproject.toml` dev-group（本 session 不动 `pyproject.toml`，遵守 CODE-OWNERSHIP-MATRIX）。

## 下一步（WP02 · L2-01 11 主 Tab 主框架 · 1.5 天）

- 独立计划文档：`docs/superpowers/plans/Dev-θ-WP02-main-tab.md`（下一会话生成）
- 依赖：WP01 ✅
- 关键 DoD：11 tab 路由 · pid banner · localStorage 持久化 · E-10 TAB_COUNT_MISMATCH 硬约束 · 55 unit TC
```

- [ ] **Step 6: Commit standup + correction log**

```bash
git add docs/4-exe-plan/standup-logs/Dev-θ-2026-04-23.md projects/_correction_log.jsonl
git commit -m "docs(harnessFlow-ui): θ-WP01 完成 · standup + arch 分歧登记

- standup: 3 tasks / 9 DoD / 7 TC 全绿
- correction log: arch.md §4 CDN→Vite 分歧 · 待主会话同步"
```

---

## §4 WP02-WP09 · 高层路线（详细计划留给后续 session）

每个 WP 单独一份 plan，遵循本 impl 的相同结构：

- `docs/superpowers/plans/Dev-θ-WP02-L2-01-main-tab.md`（1.5 天 · 55 TC）
- `docs/superpowers/plans/Dev-θ-WP03-L2-06-trim-profile.md`（0.75 天 · 44 TC）
- `docs/superpowers/plans/Dev-θ-WP04-L2-07-admin.md`（0.75 天 · 61 TC）
- `docs/superpowers/plans/Dev-θ-WP05-L2-04-intervene.md`（1.5 天 · 75 TC · **panic ≤ 100ms 硬约束**）
- `docs/superpowers/plans/Dev-θ-WP06-L2-03-sse-progress.md`（1.5 天 · 60 TC · 降级链 4 级）
- `docs/superpowers/plans/Dev-θ-WP07-L2-02-gate-card.md`（1 天 · 53 TC）
- `docs/superpowers/plans/Dev-θ-WP08-L2-05-kb-browser.md`（1 天 · 44 TC · IndexedDB）
- `docs/superpowers/plans/Dev-θ-WP09-integration-e2e.md`（0.5 天 · ≥10 e2e TC · Playwright）

**提示给下一会话的 agent**：读 exe-plan `Dev-θ-L1-10-ui.md §3.N` + 对应 L2 tech-design + L2 tests.md 即可生成 detailed plan，沿用本 impl 的 file structure、命名、测试组织。

---

## §5 Self-review（writing-plans 要求）

- ✅ **Spec coverage（WP01 部分）**：exe-plan §3.1 WP01 的 5 项（Vue 3 + Vite 脚手架 / Pinia stores / vue-router 配置 / axios client / CI build+type-check+lint）100% 映射到 §3.1-§3.4 的 4 个 task。
- ✅ **Placeholder scan**：搜过 TBD / TODO / implement later — 无。所有 code blocks 为完整可运行内容。
- ✅ **Type consistency**：`PID_STORAGE_KEY` / `PID_HEADER` / `getActivePid` / `setActivePid` / `clearActivePid` / `apiClient` / `routes` 等跨 task 使用的符号命名一致。
- ✅ **测试完整性**：4 前端 TC + 3 后端 TC = 7 冒烟 TC，覆盖 App mount / pid utils 4 分支 / apiClient baseURL + header 注入 / router 路由 / health endpoint 3 分支（默认 / pid 透传 / CORS）。
- ⚠️ **WP02-09 高层 only**：刻意不展开，每 WP 独立 plan 文档（§4），符合「每 Package 独立 brainstorm → plan → implement」的会话模式。

---

*— Dev-θ · L1-10 UI · Implementation Plan · v1.0 · updated 2026-04-23 —*
