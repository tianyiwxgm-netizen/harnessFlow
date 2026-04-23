---
doc_id: exe-plan-dev-eta-L1-08-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α-L1-09-resilience-audit.md（标杆）
  - docs/2-prd/L1-08 多模态内容处理/prd.md
  - docs/3-1-Solution-Technical/L1-08-多模态内容处理/architecture.md
  - docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-01~L2-04.md（9435 行）
  - docs/3-2-Solution-TDD/L1-08-多模态内容处理/L2-01~L2-04-tests.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.11 IC-11 · §3.12 IC-12
version: v1.0
status: draft
assignee: Dev-η
wave: 2
priority: P0（多 L1 调 IC-11）
estimated_loc: ~17000 行
estimated_duration: 5-7 天
---

# Dev-η · L1-08 多模态内容处理 · Execution Plan

> **组一句话**：4 L2 · 文档 IO + 代码结构 + 图片视觉 + 路径安全 · **IC-11 process_content** 入口 · **IC-12 delegate_codebase_onboarding 发起方**（调 L1-05 子 Agent）。
>
> **依赖**：Dev-α IC-09 mock · Dev-γ IC-12 消费方（mock）· 波 2。
>
> **PM-14**：缓存按 pid 隔离 · 路径安全守门 · ALLOWLIST 白名单。

---

## §0 撰写进度

- [x] §1-§10 全齐

---

## §1 范围

### 4 L2 清单

| L2 | 职责 | 3-1 行 | 估代码 | 估时 |
|:---:|:---|---:|---:|:---:|
| **L2-04** 路径安全与降级编排器 | ALLOWLIST + 沙箱边界 + 符号链接循环检测 + 多级降级（LLM→OCR→规则）| 2240 | ~4000 | 1.5 天 |
| **L2-01** 文档 IO 编排器 | md/py/yaml 读写 · frontmatter · 分页 · atomic_write | 2317 | ~4200 | 1 天 |
| **L2-02** 代码结构理解编排器 | AST 解析（Python/TS/Go 等）· 依赖图 · 符号索引 | 3074 | ~5500 | 1.5 天 |
| **L2-03** 图片视觉理解编排器 | VLM 调用 · 缓存 · 降级 OCR · 批处理 | 1804 | ~3300 | 1 天 |
| 合计 | 4 | 9435 | ~17000 | **5 天** + 0.5 集成 = **5.5 天** |

### 代码目录

```
app/l1_08/
├── path_safety/         # L2-04（最先做 · 所有路径的守门）
├── doc_io/              # L2-01
├── code_structure/      # L2-02（tree-sitter 集成）
├── vision/              # L2-03
└── __init__.py          # 统一入口 process_content
```

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | `2-prd/L1-08 .../prd.md` 4 L2 边界 |
| P0 | `3-1/L1-08/architecture.md` §11 L2 分工 |
| P0 | `3-1/L1-08/L2-04.md` §3 16 错误码（PATH_TRAVERSAL / OUTSIDE_SANDBOX / SYMLINK_LOOP 等）· §6 算法 |
| P0 | `3-1/L1-08/L2-01.md` §3 md 读写接口 · §6 分页 + atomic_write |
| P0 | `3-1/L1-08/L2-02.md` §3 tree-sitter AST · §6 依赖图 · §9 开源（tree-sitter/linguist/ripgrep）|
| P0 | `3-1/L1-08/L2-03.md` §3 VLM 接口 · §6 降级 OCR |
| P0 | `3-2/L1-08/*.md` ~212 TC |
| P0 | `ic-contracts.md §3.11 IC-11 · §3.12 IC-12` |

---

## §3 WP 拆解（5 WP · 5.5 天）

| WP | L2 | 主题 | 前置 | 估时 | TC |
|:---:|:---:|:---|:---|:---:|:---:|
| η-WP01 | L2-04 | 路径安全守门 · ALLOWLIST + 降级链 | α mock | 1.5 天 | ~64 |
| η-WP02 | L2-01 | 文档 IO · md/yaml 读写 · frontmatter · atomic | WP01 | 1 天 | ~54 |
| η-WP03 | L2-02 | 代码结构 · tree-sitter AST · 依赖图 | WP01 | 1.5 天 | ~51 |
| η-WP04 | L2-03 | VLM 图片 · 缓存 · OCR 降级 | WP01 | 1 天 | ~49 |
| η-WP05 | 集成 | IC-11 入口 · 4 L2 联调 · IC-12 发起（mock 消费方）| WP01-04 | 0.5 天 | ≥ 10 |

### 3.1 WP-η-01 · L2-04 路径安全（地基）

**源**：`L2-04.md §3 validate_path · §11 16 错误码 · §6 沙箱 + 降级链`

**L3**：
- `validate_path(path, action) -> ValidationResult`
  - ALLOWLIST：仅允许 `projects/<pid>/` + `templates/` + `tests/` + 预设白名单 base
  - 禁 `../` 逃逸（os.path.realpath + is_relative_to 检测）
  - 符号链接循环检测（最大深度 8）
  - PM-14：跨 pid 拒绝
  - 长度校验（Linux 4096 byte · macOS 1024）
- `fallback_route(request)`
  - 多级降级：LLM 慢（> 15s）→ LLM 降级模型 → OCR（若 image）→ 手写规则 → 拒绝
  - 审计所有降级决策（IC-09 emit）
- 16 错误码全覆盖（PATH_FORBIDDEN / OUTSIDE_SANDBOX / SYMLINK_LOOP / CROSS_PROJECT_READ 等）

**L4**：
```
app/l1_08/path_safety/validator.py         ~250 行
app/l1_08/path_safety/sandbox.py           ~150 行
app/l1_08/path_safety/symlink_detector.py  ~100 行
app/l1_08/path_safety/fallback_router.py   ~200 行
app/l1_08/path_safety/schemas.py           ~150 行
```

**DoD**：
- [ ] ~64 TC 全绿
- [ ] `../../etc/passwd` 等攻击路径全拒
- [ ] 符号链接循环测（人工构造循环 · 8 深度内检出）
- [ ] PM-14 跨 pid 拒绝测
- [ ] 16 错误码全覆盖
- [ ] commit `feat(harnessFlow-code): η-WP01 L2-04 路径安全`

### 3.2 WP-η-02 · L2-01 文档 IO

**L3**：
- `read_md(path, offset, limit) -> MDContent`（分页支持）
  - 调 L2-04 validate_path
  - frontmatter 解析（python-frontmatter）
  - 大 md（> 2000 行）分页读 + MERGING 合并校验
  - PAGED_READING 硬保证（MD_PAGED_ORDER_BROKEN 检测）
- `write_md(path, content)` / `edit_md(path, old, new)`
  - atomic_write（调 L1-09 L2-05）
  - post-write hash 复检
  - frontmatter 校验（write 前）
- `read_yaml` / `write_yaml` 同理
- PM-14：所有 path 经 L2-04 验证

**L4**：
```
app/l1_08/doc_io/md_reader.py           ~220 行
app/l1_08/doc_io/md_writer.py           ~180 行
app/l1_08/doc_io/paginator.py           ~150 行
app/l1_08/doc_io/frontmatter_parser.py  ~120 行
app/l1_08/doc_io/schemas.py             ~150 行
```

**DoD**：
- [ ] ~54 TC 全绿
- [ ] 分页读 3200 行 md · 2 页顺序合并
- [ ] post-write hash mismatch 测
- [ ] edit old_string 0 次 / 多次 · 正确错误码
- [ ] commit `feat(harnessFlow-code): η-WP02 L2-01 文档 IO`

### 3.3 WP-η-03 · L2-02 代码结构理解

**L3**：
- `parse_code(file_path, lang) -> ASTTree`（tree-sitter）
  - 支持 Python / TypeScript / Go / Rust / Java 等（lang 白名单）
  - AST cache（LRU · 基于 file_hash）
- `build_dep_graph(root_dir) -> DepGraph`（依赖图构建）
  - import 解析 · 模块间依赖
  - 环检测
- `build_symbol_index(root_dir) -> SymbolIndex`（符号定义/引用索引）
  - 定义：class / function / const
  - 引用：调用点 · import
- 降级：tree-sitter 失败（未知语言）→ 简单正则扫（粗粒度）· warn

**L4**：
```
app/l1_08/code_structure/ast_parser.py      ~280 行（tree-sitter wrapper）
app/l1_08/code_structure/dep_graph.py       ~220 行
app/l1_08/code_structure/symbol_index.py    ~200 行
app/l1_08/code_structure/cache.py           ~120 行
app/l1_08/code_structure/schemas.py         ~180 行
```

**DoD**：
- [ ] ~51 TC 全绿
- [ ] 5 语言（py/ts/go/rust/java）每语言 ≥ 3 TC
- [ ] 依赖图环检测测
- [ ] AST cache 命中率 > 70%
- [ ] tree-sitter 失败降级测
- [ ] commit `feat(harnessFlow-code): η-WP03 L2-02 代码结构`

### 3.4 WP-η-04 · L2-03 图片视觉理解

**L3**：
- `analyze_image(image_path, task) -> VisionResult`
  - task: `describe` / `extract_text` / `structured_extract`
  - 调 VLM（豆包 Vision · mock 可用 response）
  - LRU cache（基于 image_hash）
  - 降级链：VLM 慢（> 15s）→ VLM 降级（更快小模型）→ OCR（pytesseract）→ 纯规则 
- 批处理：`batch_analyze(images[])` · 并发 ≤ 3
- PM-14：cache 按 pid 隔离（`projects/<pid>/vision_cache/`）

**L4**：
```
app/l1_08/vision/vlm_invoker.py         ~220 行
app/l1_08/vision/ocr_fallback.py        ~150 行
app/l1_08/vision/cache.py               ~120 行
app/l1_08/vision/batch.py               ~120 行
app/l1_08/vision/schemas.py             ~150 行
```

**DoD**：
- [ ] ~49 TC 全绿
- [ ] describe / extract_text / structured_extract 3 task 各 ≥ 3 TC
- [ ] VLM 超时 → OCR 降级测
- [ ] cache 命中率 > 70%
- [ ] PM-14 cache 隔离测
- [ ] commit `feat(harnessFlow-code): η-WP04 L2-03 图片视觉`

### 3.5 WP-η-05 · 集成 · IC-11 入口

**L3**：
- `process_content(content_type, content, pid, ctx) -> ProcessResult`（**IC-11 唯一入口**）
  - content_type: `md` / `yaml` / `code` / `image`
  - 路由到对应 L2：
    - md/yaml → L2-01
    - code → L2-02（小）或 IC-12 委托子 Agent（大 · > 10MB）
    - image → L2-03
  - 所有走 L2-04 path_safety 前置
- IC-12 发起：当代码 > 10MB · `delegate_codebase_onboarding(code_dir)` → Dev-γ L2-04 子 Agent
- 组内 4 L2 e2e 集成测

**L4**：
```
app/l1_08/__init__.py                   ~50 行（process_content 主入口）
app/l1_08/router.py                     ~180 行
app/l1_08/ic_12_delegator.py            ~120 行
```

**DoD**：
- [ ] IC-11 contract 测（4 content_type 全路由）
- [ ] IC-12 发起测（mock L1-05 · assert 子 Agent 被调）
- [ ] 组内 e2e ≥ 10 TC
- [ ] commit `feat(harnessFlow-code): η-WP05 集成 + IC-11/12`

---

## §4 依赖图

```
η-WP01 L2-04 路径安全（地基）
  ├─► η-WP02 L2-01 文档 IO
  ├─► η-WP03 L2-02 代码结构
  └─► η-WP04 L2-03 图片视觉
        ↓
      η-WP05 集成 · IC-11 · IC-12
```

### 跨组 mock

| 外部 | mock |
|:---|:---|
| IC-09 (α) | mock |
| L1-09 L2-05 atomic_write (α) | mock · 直接写文件 |
| IC-12 消费方 (γ L2-04 子 Agent) | mock · 返 dummy report |
| VLM API（豆包） | mock · fixture 返固定 response |

---

## §5 standup + commit

复用 Dev-α §5 · prefix `η-WPNN`。

---

## §6 自修正

- 情形 B · 3-1 不可行：tree-sitter 某语言 grammar 不稳 · 改 L2-02 §9 开源调研（降级到简单正则）
- 情形 D · IC-11 契约：content_type 枚举在消费方（L1-01/04）理解不一 · 仲裁 ic-contracts §3.11

---

## §7 对外契约

| IC | 方法 | 角色 |
|:---|:---|:---|
| IC-11 接收 | `process_content(type, content, pid)` | 多 L1 → 本 L1 · P95 按 content 类型（md 秒 · code 分钟）|
| IC-12 发起 | `delegate_codebase_onboarding(code_dir)` | 本 L1 → L1-05 · dispatch ≤ 200ms · result ≤ 10min |

**替换时机**：WP05 完 · L1-01/04 可切真实 IC-11 · L1-05 验证集成。

---

## §8 DoD（多模态特化）

- 路径安全守门：所有 IO 必经 L2-04（单测验证 · mock L2-04 · 跳过路径校验不允许）
- PM-14 cache 隔离
- tree-sitter 5 语言覆盖
- VLM 降级链 4 级全测
- coverage ≥ 85%

---

## §9 风险

| 风险 | 降级 |
|:---|:---|
| **R-η-01** tree-sitter 语法包大（~50MB）· docker image 膨胀 | docker multi-stage build · 仅保留必要语言 |
| **R-η-02** VLM API 不稳 | OCR 降级 + cache 提高命中率 |
| **R-η-03** 大代码库 > 10MB · AST 内存爆炸 | 分片解析 + 委托 IC-12 子 Agent（独立 session）|

---

## §10 交付清单

### 代码（~17000 行）

```
app/l1_08/
├── path_safety/      (5 · ~870 行)
├── doc_io/           (5 · ~820 行)
├── code_structure/   (5 · ~1000 行)
├── vision/           (5 · ~760 行)
└── __init__.py + router.py + ic_12_delegator.py  (~350 行)
```

### 测试（~5500 行）· 212 TC · coverage ≥ 85%

### commit 7-9 个

---

*— Dev-η · L1-08 多模态 · Execution Plan · v1.0 —*
