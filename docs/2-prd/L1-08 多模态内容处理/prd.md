---
doc_id: prd-l1-08-multimodal-v0.1
doc_type: l1-prd
parent_doc:
  - HarnessFlowGoal.md
  - docs/2-prd/L0/businessFlow.md
  - docs/2-prd/L0/scope.md#5.8
version: v0.1
status: draft
author: mixed
created_at: 2026-04-20
updated_at: 2026-04-20
traceability:
  goal_anchor: HarnessFlowGoal.md#3.1 输入（Brownfield · 多仓库 · 架构图 · 现有代码库）
  business_flow: [BF-L3-06, BF-L3-07, BF-L3-08, BF-X-03, BF-X-05]
  scope: [L1-08]
consumer:
  - docs/2-prd/L0/flowOutInput.md（待回填）
  - docs/2-prd/L1集成/prd.md（待撰写）
  - docs/3-1-Solution-Technical/L1-08/tech-design.md（待 M9 启动）
---

# L1-08 · 多模态内容处理能力 · PRD

> **版本**：v0.1（骨架 + 4 个 L2 产品级详细定义一轮合一）
> **定位**：L1-08 的独立 PRD · 为 L1-01 决策与 L1-02 规划提供"多模态内容理解"能力 · 读写 md / 读懂代码结构 / 读懂图片
> **产品级 PRD 硬边界**：本 PRD **不含** 算法 / 伪码 / 代码块 / YAML schema 字段级 / 状态机代码 / 配置参数表 / 数据结构字段定义。实现细节统一迁到 `docs/3-1-Solution-Technical/L1-08/tech-design.md`。
> **严格遵循**：本 PRD **不得与** `docs/2-prd/L0/scope.md §5.8` 冲突。如冲突以 scope 为准。
> **PM-14 项目上下文声明**：**所有多模态素材（图片 / 代码结构摘要 / md 文档）按 `harnessFlowProjectId` 隔离缓存**。避免跨项目素材污染：project-foo 的图片识别结果不进入 project-bar 的 KB；代码结构摘要按 project_id + git_head 作 cache key；md 读写路径受 project 根目录限定。详见 `docs/2-prd/L0/projectModel.md` §9.1（L1-08 使用方式）。

---

## 0. 撰写进度

- [x] §1 L1-08 范围锚定（引用 scope §5.8）
- [x] §2 L2 清单（4 个）
- [x] §3 L2 整体架构 · 图 A 主干内容流
- [x] §4 L2 整体架构 · 图 B 横切响应面
- [x] §5 L2 间业务流程（6 条）
- [x] §6 IC-L2 契约清单（7 条 · 一句话 + 方向）
- [x] §7 L2 定义模板（9 小节标准 · 严禁 §X.10）
- [x] §8 L2-01 · 文档 I/O 编排器（md 读写）
- [x] §9 L2-02 · 代码结构理解编排器
- [x] §10 L2-03 · 图片视觉理解编排器
- [x] §11 L2-04 · 路径安全与降级编排器（横切）
- [x] §12 对外 scope §8 IC 契约映射
- [x] §13 本 L1 retro 位点
- [x] 附录 A · 术语（L1-08 本地）
- [x] 附录 B · businessFlow BF 映射

---

## 1. L1-08 范围锚定（引自 scope §5.8，不重复写）

| scope §5.8 子节 | 内容摘要 | 锚点 |
|---|---|---|
| §5.8.1 职责 | 为 L1-01 / L1-02 提供"多模态内容理解"（读写 md / 读懂代码结构 / 读懂图片） | scope#5.8.1 |
| §5.8.2 输入/输出 | 输入"读/写/分析"请求 + 用户上传图片；输出结构化 sections / 模板 md / 代码结构摘要 / 图片结构化描述 | scope#5.8.2 |
| §5.8.3 边界 | In：md I/O / 大文件分页 / 代码结构扫描 / 图片视觉理解 / > 10 万行委托；Out：代码生成 / AST 深度 / 图片生成 / PDF Excel 二进制 / OCR / 代码重构 | scope#5.8.3 |
| §5.8.4 约束 | PM-08 可审计全链追溯；硬约束：> 2000 行分页 / > 10 万行委托 / 路径白名单 | scope#5.8.4 |
| §5.8.5 🚫 禁止行为 | 6 条（禁改用户源代码 / 禁写非 docs/tests/harnessFlow / 禁上传外部 / 禁执行用户代码 / 禁原始图片二进制外抛 / 禁跨项目） | scope#5.8.5 |
| §5.8.6 ✅ 必须义务 | 6 条（每次读写落事件 / > 2000 行必分页 / 图片必结构化 / 代码分析必入 KB / 不可读必告警 / > 10 万行必委托） | scope#5.8.6 |
| §5.8.7 与其他 L1 交互 | L1-01 / L1-02 / L1-04 / L1-05 / L1-06 / L1-09 / L1-10 | scope#5.8.7 |
| 对外 IC 契约 | IC-11 process_content（scope §8.2 主入口）+ IC-12 delegate_codebase_onboarding + IC-09 record_event | scope#8.2 |

**本 PRD 的职责**：把 L1-08 内部拆成 **4 个 L2** + 画清楚它们之间的 **架构 / 业务流 / 契约**，仅产品级，不涉实现。

**L1-08 的定位**（简单 L1）：
- **不承担生成**：不做图片生成 / 代码生成 / 视频生成 / 音频生成；本 L1 只做"理解 + 读写"
- **不承担深分析**：不做 AST / 符号表 / 全文索引；深度分析委托 `codebase-onboarding` 子 Agent
- **只是"薄编排层"**：把底层工具柜（Read/Write/Edit/Glob/Grep + Claude 多模态视觉）按场景编排成"内容理解服务"

---

## 2. L2 清单（4 个）

| L2 ID | 名称 | 一句话职责 | 聚合自 BF | 核心问题 |
|---|---|---|---|---|
| **L2-01** | 文档 I/O 编排器 | md 文档的 Read / Write / Edit 编排 + frontmatter 解析 + headings 结构化 + > 2000 行分页 + 只写 `docs/` `tests/` `harnessFlow/` 白名单路径 | BF-L3-06 | md 怎么读写 |
| **L2-02** | 代码结构理解编排器 | Glob 扫目录 + Read 入口文件 + Grep 关键模式 → 产出"语言 + 框架 + 入口 + 依赖图 + 关键模式"结构摘要 + > 10 万行自动委托 `codebase-onboarding` + 结果必入 Project KB | BF-L3-07 | 代码仓库怎么读懂 |
| **L2-03** | 图片视觉理解编排器 | Read 工具加载图片 → Claude 多模态视觉理解 → 按图片类型产结构化描述（架构图 · UI mock · 截图）+ 图片不上传外部 + 禁止原始二进制外抛 | BF-L3-08 | 图片怎么读懂 |
| **L2-04** | 路径安全与降级编排器（横切） | 路径白名单校验 + 文件大小 / 行数阈值判定 + 不可读告警（权限 / 不存在 / 二进制未支持）+ 降级路由（直读 / 分页 / 委托子 Agent / 拒绝）+ 每次读写必走审计（IC-09） | 横切于 BF-L3-06 / 07 / 08 + BF-X-03 | 怎么安全地读写 |

**4 个 L2 的切分理由**：
- **三种内容类型各一个 L2**（md / 代码 / 图片）——内容模态差异大、编排逻辑独立、边界清晰
- **一个横切 L2**（L2-04 路径安全与降级）——承担所有"跨模态都要做"的守门 + 降级职责（类似 L1-02 的 L2-07 模板引擎地位）
- 未来若扩展 PDF / OCR / 音视频，按需再开 L2-05+，不影响前 4 个 L2

---

## 3. L2 整体架构 · 图 A 主干内容流

```
              L1-08 多模态内容处理（4 个 L2）
              ═════════════════════════════════

    L1-01 / L1-02 / L1-04 的"读/写/分析"请求
    （IC-11 process_content: {type, path, action}）
                     │
                     ▼
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃  L2-04 路径安全与降级编排器（横切 · 守门）   ┃
  ┃   · 路径白名单校验                           ┃
  ┃   · 文件大小 / 行数阈值判定                  ┃
  ┃   · 不可读告警（权限 / 二进制 / 不存在）       ┃
  ┃   · 降级路由（直读 / 分页 / 委托 / 拒绝）      ┃
  ┃   · 每次读写走 IC-09 审计                    ┃
  ┗━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
              │ 通过校验 + 降级决策
              │ IC-L2-01 dispatch_to_modality（按 type 路由）
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 ┏━━━━━━┓ ┏━━━━━━┓ ┏━━━━━━┓
 ┃ L2-01┃ ┃ L2-02┃ ┃ L2-03┃
 ┃ md   ┃ ┃ code ┃ ┃image ┃
 ┃ I/O  ┃ ┃结构  ┃ ┃视觉  ┃
 ┃      ┃ ┃理解  ┃ ┃理解  ┃
 ┃      ┃ ┃      ┃ ┃      ┃
 ┃Read  ┃ ┃Glob  ┃ ┃Read  ┃
 ┃Write ┃ ┃+Grep ┃ ┃image ┃
 ┃Edit  ┃ ┃+Read ┃ ┃→视觉 ┃
 ┃fm+   ┃ ┃入口  ┃ ┃→结构 ┃
 ┃head  ┃ ┃摘要  ┃ ┃化描述┃
 ┃ings  ┃ ┃      ┃ ┃      ┃
 ┗━━━┳━━┛ ┗━━━┳━━┛ ┗━━━┳━━┛
      │        │        │
      │        │        │
      │   IC-L2-02 (大仓委托)
      │        │        │
      │        ▼        │
      │  ┏━━━━━━━━━━━━┓  │
      │  ┃  L1-05     ┃  │ （外部：委托 codebase-onboarding · IC-12）
      │  ┃ 子 Agent   ┃  │
      │  ┗━━━━━━━━━━━━┛  │
      │                  │
      ▼                  ▼
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃  结构化产物输出（供调用方消费）            ┃
  ┃   · md → sections + frontmatter          ┃
  ┃   · code → 结构摘要 + 依赖图（写 L1-06 KB）┃
  ┃   · image → 结构化描述（架构图/UI/截图）  ┃
  ┗━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
              │
              │ 返回给调用方（IC-11 响应）
              │ + 落盘事件总线（IC-09）
              ▼
       L1-01 / L1-02 / L1-04 消费
       + L1-09 事件总线（审计）
       + L1-06 Project KB（仅代码结构摘要）
```

**关键规则**：
- **L2-04 是唯一入口**（所有 IC-11 请求必先经守门 → 降级决策 → 路由到 L2-01/02/03）
- **L2-01/02/03 不直接对外**（主入口走 L2-04；内部才按模态分派）
- **L2-02 是唯一写 L1-06 Project KB 的 L2**（代码结构摘要写 KB；md/image 不写 KB）
- **委托子 Agent 只发生在 L2-02**（仅代码仓库 > 10 万行触发 IC-12）
- **禁止绕过 L2-04 直接调模态 L2**（所有守门 + 审计必经 L2-04）

---

## 4. L2 整体架构 · 图 B 横切响应面

```
 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 1 · 大文件分页读（> 2000 行触发）                         ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ (调用方) → IC-11 process_content(type=md, path=big.md, read)     ║
 ║   → L2-04 判定：行数 > 2000 → 标记 paged=true                    ║
 ║   → IC-L2-01 dispatch_to_modality(L2-01, paged=true)             ║
 ║   → L2-01 按分页策略循环 Read（每页 ≤ 2000 行）                   ║
 ║   → 逐页结构化 → 拼接 sections                                    ║
 ║   → 审计每页读取事件（IC-09）                                     ║
 ║   → 返回完整 sections 给调用方                                    ║
 ║                                                                  ║
 ║ 禁止：一次性全量读（违反 scope §5.8.4 硬约束 1）                  ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 2 · 大仓委托（> 10 万行触发）                              ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ (调用方) → IC-11 process_content(type=code, path=bigRepo, analyze)║
 ║   → L2-04 经 L2-02 初步 Glob 估算 → 行数 > 10 万                 ║
 ║   → L2-04 触发降级：标记 delegate=true                           ║
 ║   → L2-02 经 IC-L2-02 → L1-05（IC-12 delegate_codebase_onboarding）║
 ║   → L1-05 独立 session 子 Agent 跑                               ║
 ║   → 返回 structure_summary + kb_entries                          ║
 ║   → L2-02 把 kb_entries 写 L1-06 Project KB                      ║
 ║   → 返回 structure_summary 给调用方                               ║
 ║                                                                  ║
 ║ 禁止：单体 Agent 硬扛 > 10 万行（违反 scope §5.8.4 硬约束 2）     ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 3 · 路径白名单拦截（写入不允许路径 → 拒绝）                 ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ (调用方) → IC-11 process_content(type=md, path=/etc/xxx, write)   ║
 ║   → L2-04 路径校验：不在 `docs/` / `tests/` / `harnessFlow/`       ║
 ║   → 拒绝 + 结构化 err 返回                                        ║
 ║   → 审计"路径越权拒绝"事件                                         ║
 ║                                                                  ║
 ║ 允许白名单：docs/ / tests/ / harnessFlow/（合规可配置 · 见 L2-04） ║
 ║ 读路径更宽：允许整个项目 scope 内的任何路径（只禁跨项目）          ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 4 · 不可读告警（明确失败 · 禁止静默）                       ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ (调用方) → IC-11 process_content(type=md, path=missing, read)     ║
 ║   → L2-04 判定：文件不存在 / 权限拒绝 / 二进制不支持               ║
 ║   → 结构化 err（错误码 + 原因 + 建议动作）                         ║
 ║   → 审计"不可读告警"事件                                           ║
 ║   → 禁止降级为"假装成功返回空"（违反 scope §5.8.6 必须义务 5）     ║
 ║                                                                  ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 5 · 图片隐私保护（禁止上传外部）                            ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ (调用方) → IC-11 process_content(type=image, path=local.png, analyze)║
 ║   → L2-04 → L2-03                                                 ║
 ║   → L2-03 本地 Read（Claude 多模态原生）                           ║
 ║   → Claude 视觉理解（走主 Agent 上下文，不出模型边界）             ║
 ║   → 产结构化描述                                                   ║
 ║   → 禁止原始二进制外抛 / 禁止上传任何外部服务                       ║
 ║                                                                  ║
 ║ 禁止：L2-03 调任何外部 image hosting / CDN / OCR API               ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 6 · 代码分析必入 KB（session / project 分层）              ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-02 产出代码结构摘要                                            ║
 ║   → 默认写 Project KB（IC-06/07 经 L1-06）                        ║
 ║   → 等后续 L1-01 决策 / L1-02 规划可查                             ║
 ║   → 不重复分析：同 repo_path + 同 git_head 命中 KB 则直接返回缓存 ║
 ║                                                                  ║
 ║ md / image 不入 KB（短寿命 · 当次使用完即止）                     ║
 ╚══════════════════════════════════════════════════════════════════╝
```

**横切响应面小结**：
- 响应面 1-2 是"大体量降级"路径（分页 / 委托）
- 响应面 3-5 是"安全守门"路径（路径 / 不可读 / 隐私）
- 响应面 6 是"KB 持久化"路径（仅代码）

---

## 5. L2 间业务流程（6 条）

### 流 A · md 文档读（正常 ≤ 2000 行）

```
[调用方 L1-01/02/04] → IC-11 process_content(type=md, path=X, read)
     ↓
L2-04 路径白名单校验（项目 scope 内）→ 通过
     ↓
L2-04 行数探测 → ≤ 2000 行 → paged=false
     ↓
L2-04 IC-L2-01 dispatch_to_modality(L2-01)
     ↓
L2-01 Read 工具拉整份
     ↓
L2-01 结构化：解析 frontmatter + headings 层次 + 正文段落
     ↓
L2-01 返回 sections
     ↓
L2-04 记录 IC-09 审计（path + size + hash + 结果摘要）
     ↓
返回调用方
```

### 流 B · md 文档写（白名单路径内）

```
[调用方 L1-02] → IC-11 process_content(type=md, path=docs/planning/xxx, write, content)
     ↓
L2-04 路径白名单校验 → path 在 `docs/` → 通过
     ↓
L2-04 IC-L2-01 dispatch_to_modality(L2-01, action=write)
     ↓
L2-01 Write 工具落盘
     ↓
L2-01 写完后复检（Read 一次验证内容对齐）
     ↓
L2-04 记录 IC-09 审计（path + size + hash + write 结果）
     ↓
返回调用方 ok
     ↓
[若 path 不在白名单] L2-04 拒绝 + 结构化 err + 审计"路径越权"
```

### 流 C · md 文档大文件读（> 2000 行 · 分页）

```
[调用方] → IC-11 process_content(type=md, path=big.md, read)
     ↓
L2-04 路径校验通过 + 行数探测 → > 2000 行 → paged=true
     ↓
L2-04 IC-L2-01 dispatch_to_modality(L2-01, paged=true)
     ↓
L2-01 分页循环：
   Page 1: Read(offset=0, limit=2000)
   Page 2: Read(offset=2000, limit=2000)
   ... 直到读完
     ↓
L2-01 按页累积结构化 sections
     ↓
L2-01 返回合并后的 sections + total_pages
     ↓
L2-04 记录 IC-09 审计（每页一条事件 · 方便追溯）
     ↓
返回调用方
```

### 流 D · 代码结构理解（≤ 10 万行 · 自体扫描）

```
[调用方 L1-01/02 · Brownfield 接入] → IC-11 process_content(type=code, path=repo, analyze)
     ↓
L2-04 路径校验（项目 scope 内）+ 估算行数（Glob 快速数行）
     ↓
≤ 10 万行 → delegate=false
     ↓
L2-04 IC-L2-01 dispatch_to_modality(L2-02)
     ↓
L2-02 流程：
  Step 1: Glob 扫目录结构 → 识别语言 / 框架
  Step 2: Read 关键入口（main.py / index.ts / pom.xml / package.json / go.mod / Cargo.toml）
  Step 3: Grep 关键模式（类 / 函数 / API 端点 / DB 访问）
  Step 4: 组装结构摘要（语言 + 框架 + 入口 + 依赖图 + 关键模式）
     ↓
L2-02 写 L1-06 Project KB（IC-06/07 经 L1-06 · 带 repo_path + git_head 作缓存 key）
     ↓
L2-04 记录 IC-09 审计
     ↓
返回 structure_summary 给调用方
```

### 流 E · 大仓委托（> 10 万行 · 委托 codebase-onboarding）

```
[调用方] → IC-11 process_content(type=code, path=bigRepo, analyze)
     ↓
L2-04 → L2-02 初步 Glob → 估算行数 > 10 万
     ↓
L2-04 触发降级：delegate=true
     ↓
L2-02 IC-L2-02 delegate_onboarding → 经 L1-05 IC-12 delegate_codebase_onboarding
     ↓
L1-05 独立 session 跑 codebase-onboarding 子 Agent
   （本 L1-08 不参与子 Agent 内部过程 · 只等 report）
     ↓
L1-05 返回 {structure_summary, kb_entries}
     ↓
L2-02 把 kb_entries 批量写 L1-06 Project KB
     ↓
L2-04 记录 IC-09 审计（含"委托决策 + 子 Agent 耗时"）
     ↓
返回 structure_summary 给调用方
```

### 流 F · 图片视觉理解

```
[调用方 L1-01（用户上传架构图）/ L1-04（Playwright 截图）] → IC-11 process_content(type=image, path=local.png, analyze, image_hint?: architecture/ui_mock/screenshot)
     ↓
L2-04 路径校验（项目 scope 或显式允许的外部上传目录）
     ↓
L2-04 文件大小 / 格式校验（支持：png / jpg / webp · V1 范围）
     ↓
L2-04 IC-L2-01 dispatch_to_modality(L2-03)
     ↓
L2-03 流程：
  Step 1: Read 工具加载图片（Claude 多模态原生）
  Step 2: 根据 image_hint 选结构化描述模板：
     · architecture → 节点列表 + 关系 + 技术栈推断
     · ui_mock → 布局 + 组件清单 + 交互点
     · screenshot → 页面状态 + 可见文本 + 错误迹象
  Step 3: 主 Agent 视觉理解并填入模板
  Step 4: 产出结构化描述（禁止返回原始二进制）
     ↓
L2-04 记录 IC-09 审计（路径 + 图片类型 + 描述摘要 · 不记原始像素数据）
     ↓
返回结构化描述给调用方
     ↓
[禁止] 上传到任何外部 hosting / OCR API / CDN
```

---

## 6. IC-L2 契约清单（7 条 · 一句话 + 方向）

| ID | 调用方 | 被调方 | 意义（一句话） |
|---|---|---|---|
| **IC-L2-01** | L2-04 | L2-01 / L2-02 / L2-03 | 守门通过后按模态分派：告诉对应模态 L2 本次请求的 `{type, path, action, paged?, delegate?, image_hint?}` |
| **IC-L2-02** | L2-02 | L1-05（经 IC-12 外部） | 大仓委托：> 10 万行触发 `delegate_codebase_onboarding`，由 L1-05 开独立 session 子 Agent |
| **IC-L2-03** | L2-01 | L1-02（内部 KB read）/ L2-02 | 查询模板库（L2-02 产出时可选查 KB 已有结构摘要作模式参考）· 可选 |
| **IC-L2-04** | L2-02 | L1-06（经 IC-06/07 外部） | 代码结构摘要写 Project KB：默认持久化所有 analyze 产出 |
| **IC-L2-05** | 全 L2 | L1-09（经 IC-09 外部） | 审计事件：每次 Read / Write / analyze / 降级 / 拒绝 / 错误都落事件总线 |
| **IC-L2-06** | L2-04 | 调用方（IC-11 响应路径） | 结构化错误返回：不可读 / 路径越权 / 二进制未支持 等明确告警（禁静默失败） |
| **IC-L2-07** | L2-04 | L1-07（经 BF-X-02 广播） | 硬约束违规上报：调用方尝试触碰 🚫（如写非白名单 / 强制不分页大文件）时通知监督 |

**契约版本规则**：同 L1-02 规则（scope §8.2 契约版本约定）：
- 每条 IC 有 `version` 字段（v1 起）
- L1-08 升级必须保 backward compat 至少 1 个 minor 版本
- 升级点在本 PRD §12 对外 IC 契约映射章节记录

**注**：字段级 schema（`{type, path, action, paged, ...}` 具体字段类型、取值范围、必选可选）迁到 `docs/3-1-Solution-Technical/L1-08/tech-design.md`，本 PRD 只给一句话 + 方向。

---

## 7. L2 定义模板（每 L2 必含 9 小节）

每个 L2 详细定义（§8-§11）严格按以下模板（复用 L1-01 / L1-02 §7 · 产品级版本）：

| # | 小节 | 内容 |
|---|---|---|
| 1 | 职责 + 锚定 | 一句话职责 + Goal / BF / scope §5.8 锚点 |
| 2 | 输入 / 输出（概念级） | 输入事件 / 请求 + 产出类型；**不写 YAML schema** |
| 3 | 边界 | In-scope / Out-of-scope / 边界规则 |
| 4 | 约束 | 业务模式 + 硬约束（文字描述）+ 性能约束（阈值文字）|
| 5 | 🚫 禁止行为 | 明确清单（4-7 条） |
| 6 | ✅ 必须职责 | 明确清单（4-7 条） |
| 7 | 🔧 可选功能职责 | 2-4 条 |
| 8 | 与其他 L2 / L1 交互 | IC-L2 一句话 + 方向（**不含字段 schema**） |
| 9 | 🎯 交付验证大纲 | Given-When-Then（正向 / 负向 / 集成 / 性能）|

**严禁**：§X.10 L3 实现设计（算法伪码 / 状态机代码图 / YAML schema / 配置参数表）→ 迁到 `docs/3-1-Solution-Technical/L1-08/tech-design.md`（M9 启动）。

---

## 8. L2-01 · 文档 I/O 编排器 详细定义

### 8.1 职责 + 锚定

**一句话职责**：HarnessFlow 的 "md 文档读写工 "—— 统一封装 md 文档的 Read / Write / Edit 三类动作，读时把 frontmatter + headings + 正文解析为结构化 sections 供上游消费，写时按调用方给的内容落盘到白名单路径（由 L2-04 守门）并作写后复检，对 > 2000 行大文档执行分页读循环。

**上游锚定**：
- Goal §3.2 输出 D · "可审计的决策链 + 知识沉淀"（所有 md 产出物走统一 I/O 保证审计可追溯）
- scope §5.8.1 职责 "读写 md 文档"
- scope §5.8.3 In-scope "md 文件 Read / Write / Edit（走 L1-05 工具柜）的封装" + "大文件（> 2000 行）分页处理"
- scope §5.8.4 硬约束 1 "md 文件 > 2000 行必分页读（一次不得全量读）"
- businessFlow BF-L3-06（文档处理流）

**下游服务**：
- L2-04（接收从守门路由来的 md 请求）
- L1-02 L2-02 ~ L2-06（PMP + TOGAF 产出物 md 落盘的最终写入通道）
- L1-04（TDD 蓝图 md / 验证报告 md 读取）

---

### 8.2 输入 / 输出

**输入**：
- 从 L2-04 经 IC-L2-01 路由来的 md 请求（带 `type=md` + path + action + 可选 paged 标志）
- action 有三种：read / write / edit
- 读请求可选 `offset / limit`（调用方主动分页读某段时）
- 写请求带 content（由调用方拼接好的完整内容或 diff）
- 在 > 2000 行场景下还带 L2-04 标记的 `paged=true` 暗示

**输出**：
- read 产出：**结构化 sections**（frontmatter 字段字典 + headings 层次列表 + 按 heading 划分的正文段落）
- write / edit 产出：**写入确认**（path + size + hash + 写后复检通过 flag）
- 错误情况：**结构化 err**（由 L2-04 统一封装走 IC-L2-06）

**不做的输出**：
- ❌ 不产出渲染后的 HTML / PDF（只处理源 md）
- ❌ 不产出 md → 代码转换
- ❌ 不产出图片（md 中的图片引用保留为文本链接，图片本身交 L2-03）

---

### 8.3 边界

**In-scope**：
1. md Read（整份 ≤ 2000 行直读 · > 2000 行必分页循环）
2. md Write（新增或覆写整份到白名单路径）
3. md Edit（局部编辑 · 调用方给出 old_string / new_string 精确匹配）
4. frontmatter 解析（YAML frontmatter 识别 + 字段提取 · **不做 schema 校验**，schema 校验是 L1-02 产出物模板引擎的职责）
5. headings 层次结构化（# / ## / ### 识别 + 按层收进 sections 树）
6. 正文段落按 heading 划分
7. 写后复检（Write 成功后再 Read 一次对齐 hash · 防止 disk 异常）
8. 分页读循环编排（按 2000 行一页循环 · 逐页结构化 · 最后合并）

**Out-of-scope**：
- ❌ 不做路径白名单校验（→ L2-04）
- ❌ 不做 > 2000 行判定（→ L2-04 探测 + 标记；本 L2 只接收 `paged=true` 并执行分页循环）
- ❌ 不做不可读告警（→ L2-04）
- ❌ 不做 md 内容的**语义理解**（如"这份 md 写的对不对"）→ 调用方的业务判断
- ❌ 不做 md 模板驱动生成（那是 L1-02 L2-07 产出物模板引擎的事；本 L2 只落盘已生成好的内容）
- ❌ 不做 md → 其他格式转换（HTML / PDF / docx 等均不做）
- ❌ 不做 md 中引用的图片加载（→ L2-03）
- ❌ 不做 diff 合并（两份 md 合并是调用方先拼好内容再给本 L2 写）

**边界规则**：
- 本 L2 只做"**md 内容的搬运 + 结构化**"，不碰"**md 写什么（业务）**"也不碰"**md 能不能写（安全）**"
- 结构化的深浅度：frontmatter 字段 + headings 层次 + 按 heading 划分的段落文本——**够用即可**，不做语义 parsing（不识别 "表格"、"代码块类型"、"任务列表"等语义元素）
- Edit 要求调用方给的 old_string **精确匹配**——本 L2 不做模糊匹配 / 启发式替换

---

### 8.4 约束

**业务模式引用**：
- **PM-08 可审计全链追溯**：所有 md I/O 必走 IC-09 审计
- **PM-09 能力抽象层**：本 L2 是 Read / Write / Edit 工具柜的"场景封装层"，不直接暴露底层工具

**硬约束清单**：
1. **硬拦 > 2000 行单次读**：凡 L2-04 传 `paged=true` 就**必须**走分页循环，禁一次性全量读（scope §5.8.4 硬约束 1）
2. **写后必复检**：Write 成功必 Read 一次比对（防 disk 异常 / 并发覆盖）
3. **frontmatter 解析失败不致命**：frontmatter 损坏只告警不拒绝读（正文还可用）；但 write 时若 frontmatter 解析失败则拒绝（避免写出损坏的产出物）
4. **Edit 精确匹配失败即 err**：old_string 在文件中不唯一或不存在时直接返回结构化 err（不做启发式 fallback）
5. **分页读必须顺序不跳过**：每页一条审计事件，page 间不允许乱序（否则 sections 合并错乱）

**性能约束**（文字描述）：
- 单份 md（≤ 2000 行）读整份 + 结构化 ≤ 1s
- 单份 md（2000-10000 行）分页读 + 结构化累积 ≤ 10s
- 单份 md Write 落盘 + 写后复检 ≤ 500ms
- Edit 单次 old_string / new_string 替换 + 落盘 + 复检 ≤ 500ms
- 支持并发：同一 path 禁并发写（L2-04 加锁）；不同 path 可并行

---

### 8.5 🚫 禁止行为（明确清单）

- 🚫 **禁止一次性全量读 > 2000 行 md**（必须按 L2-04 标记的 paged 分页循环）
- 🚫 **禁止对 md 内容做语义理解 / 评估 / 打分**（那是调用方的业务 · 本 L2 只是搬运工）
- 🚫 **禁止 Write 未经写后复检就返回成功**（必须 Read 一次对齐 hash）
- 🚫 **禁止 Edit 时做启发式 / 模糊匹配**（old_string 不唯一或不存在 = err）
- 🚫 **禁止跳过 frontmatter 解析直接写**（frontmatter 损坏不能 write · 避免产出坏产出物）
- 🚫 **禁止返回原始 md 字节流 / 二进制**（必须是 sections 结构化字典）
- 🚫 **禁止把业务模板填充逻辑内嵌进本 L2**（模板驱动是 L1-02 L2-07 的事）

---

### 8.6 ✅ 必须职责（明确清单）

- ✅ **必须**对 L2-04 标记 `paged=true` 的请求走分页循环（每页 ≤ 2000 行）
- ✅ **必须**每次 Write / Edit 成功后复检（Read 对齐 hash）
- ✅ **必须**把 frontmatter + headings + 段落三层结构化给调用方
- ✅ **必须**对 Edit 的 old_string 做精确匹配（不唯一即 err）
- ✅ **必须**每次 I/O 经由 L2-04 走 IC-L2-05 审计（不得绕过）
- ✅ **必须**分页读时保证 page 顺序（sections 顺序合并正确）
- ✅ **必须**对 YAML frontmatter 解析失败的写入请求返回 err 而非强写

---

### 8.7 🔧 可选功能职责

- 🔧 **md 差分优化**：Edit 成功后产出 diff hunk 供 UI 展示"本次改了什么"
- 🔧 **headings 锚点生成**：对长 md 产出 heading → 锚点链接的映射（方便 L1-10 UI 跳转）
- 🔧 **分页读并发**：同一大 md 的多页可并发读（实现细节留到 tech-design）
- 🔧 **写入原子性**：write 时先写临时文件再 rename（防写一半崩溃 · 细节留到 tech-design）

---

### 8.8 与其他 L2 / L1 交互（IC-L2 一句话 + 方向）

**作为被调方**：
- 来自 **L2-04** · IC-L2-01 · 方向 L2-04 → L2-01 · 接收：守门后路由的 md read / write / edit 请求
- 来自 **L1-02 L2-03 / L2-06 等**（最终经由 L2-04 + IC-11 → 路由到本 L2）· 方向 调用方 → L2-04 → L2-01

**作为调用方**：
- 调 **L2-04** · IC-L2-05 · 方向 L2-01 → L2-04 · 意义：每次 I/O 完成报审计（由 L2-04 统一经 IC-09 落事件总线）
- 调 **L2-04** · IC-L2-06 · 方向 L2-01 → L2-04 · 意义：错误由 L2-04 统一结构化后返回给调用方（本 L2 不直接面向调用方）

**不交互**：
- ❌ 不调 L2-02（代码）/ L2-03（图片）
- ❌ 不直接调 L1-05（工具柜调用由本 L2 内部完成 · 不发 IC）
- ❌ 不直接调 L1-06（md 不入 KB）

---

### 8.9 🎯 交付验证大纲（Given-When-Then）

#### 正向场景

- **Given** 调用方 IC-11 请求读 `docs/planning/requirements.md`（320 行） · L2-04 判定 paged=false · 路由到本 L2
  - **When** 本 L2 执行 Read → 解析 frontmatter + headings + 段落
  - **Then** 返回 sections 字典（frontmatter 字段齐全 · headings 层次正确 · 段落按 heading 划分）+ 审计事件落盘

- **Given** 调用方请求读 `docs/big-adr-collection.md`（3200 行） · L2-04 判定 paged=true · 路由到本 L2
  - **When** 本 L2 分页循环（Page 1: 0-2000 行 · Page 2: 2000-3200 行）
  - **Then** 两页顺序读完 · sections 按顺序合并 · 每页一条审计事件 · 最终 sections 正确反映全文 headings 层次

- **Given** 调用方请求写 `docs/planning/goals.md`（content 已备好 · path 在白名单）· L2-04 路由到本 L2
  - **When** 本 L2 Write + 写后复检（Read 对齐 hash）
  - **Then** 返回写入确认（path + size + hash）+ 审计事件

- **Given** 调用方请求 Edit `docs/adr/ADR-007.md`（old_string 精确匹配一次 · new_string 替换）
  - **When** 本 L2 Edit + 写后复检
  - **Then** 返回编辑确认 + 审计事件

#### 负向场景

- **Given** 调用方请求读 5000 行 md 但请求体标了 paged=false
  - **When** 本 L2 收到（L2-04 应已标 paged=true · 若未标则违反守门职责）
  - **Then** 本 L2 自身二次校验（行数探测）· 若 > 2000 行则强制走分页 + 审计"守门失败 L2-01 兜底分页"

- **Given** 调用方请求 Edit 但 old_string 在文件中出现 3 次
  - **When** 本 L2 精确匹配校验 → 3 次不唯一
  - **Then** 返回结构化 err（由 L2-04 统一封装）+ 审计"Edit 匹配不唯一"

- **Given** 调用方请求 Write · content 中 frontmatter YAML 缺闭合 ---
  - **When** 本 L2 frontmatter 解析失败
  - **Then** 拒绝写入 + 结构化 err + 审计"frontmatter 损坏拒写"

- **Given** 写后复检 Read 到的 hash 与写入 hash 不一致
  - **When** 本 L2 发现哈希偏差
  - **Then** 标记 write 失败 + 结构化 err + 审计"写后复检偏差" + 建议调用方重试

#### 集成场景（跨 L2 / 跨 L1）

- **I1** · L1-02 L2-03 生成 requirements.md → IC-11 → L2-04 → L2-01 写 → L1-09 审计 → L1-10 UI 展示新产出物链接
- **I2** · L1-04 调 verifier 子 Agent 回传 verifier_report.md → L2-01 写到 `tests/verifier/` → L1-04 S5 判定消费
- **I3** · 跨 session 恢复 · 未完成的分页读被中断 · bootstrap 后重新发起 IC-11 · L2-04 重路由 · L2-01 从头分页（不做 page 级断点续读 · 简化）

#### 性能阈值（P99）

- 单份 md（≤ 2000 行）读 + 结构化 ≤ 1s
- 单份 md 2000-10000 行分页读 + 累积 ≤ 10s
- 单份 md Write + 复检 ≤ 500ms
- Edit + 复检 ≤ 500ms

---

## 9. L2-02 · 代码结构理解编排器 详细定义

### 9.1 职责 + 锚定

**一句话职责**：HarnessFlow 的 "代码仓库阅读器 "—— 对给定代码仓库路径执行 Glob 扫目录 + Read 入口文件 + Grep 关键模式 的组合探测，产出"语言 + 框架 + 入口 + 依赖图 + 关键模式"的结构摘要，在代码量超过阈值（> 10 万行）时降级委托 `codebase-onboarding` 子 Agent（经 L1-05），所有摘要结果写入 L1-06 Project KB 供后续 L1-01 决策 / L1-02 规划复用。

**上游锚定**：
- Goal §3.1 输入 · Brownfield 模式（接入现有代码库要能"看懂"）
- scope §5.8.1 职责 "读代码结构（AST + Grep）"
- scope §5.8.3 In-scope "代码结构扫描（Glob + Grep + Read 入口）" + "代码仓库 > 10 万行时委托 codebase-onboarding 子 Agent"
- scope §5.8.4 硬约束 2 "代码仓库 > 10 万行必委托 codebase-onboarding 子 Agent，不得单体 Agent 硬读"
- scope §5.8.6 必须义务 4 "必须在代码分析后写入 session KB（供 L1-01 后续决策复用）"
- businessFlow BF-L3-07（代码读取与分析流）

**下游服务**：
- L2-04（路径守门 + 行数探测入口）
- L1-01（Brownfield 首轮决策读代码结构摘要）
- L1-02 L2-05（TOGAF C/D 架构生成时引用现有代码结构）
- L1-06（Project KB 写入方）

---

### 9.2 输入 / 输出

**输入**：
- 从 L2-04 经 IC-L2-01 路由来的代码分析请求（带 `type=code` + repo_path + action=analyze + 可选 delegate 标志）
- 可选参数：`focus_hint`（聚焦某子目录 · 如只分析 `backend/` 而非整仓）
- 可选参数：`include_patterns / exclude_patterns`（调用方若想限定分析范围 · 如排除 `node_modules` · 本 L2 默认也做合理忽略）

**输出**：
- **结构摘要**（概念级字段：语言列表 / 主框架 / 入口文件清单 / 核心模块 / 依赖清单 / 关键模式归纳 / git_head 快照）
- **KB 条目引用**（写入 L1-06 后返回的 entry id 列表）
- **委托报告**（若触发 delegate）：含委托 session id + 子 Agent 耗时 + 子 Agent 质量评级（由 L1-05 附加）

---

### 9.3 边界

**In-scope**：
1. Glob 扫目录结构（识别深度 + 文件数量 + 顶层目录分布）
2. 语言识别（基于文件扩展名 + 关键配置文件如 `package.json` / `pom.xml` / `Cargo.toml` / `go.mod` / `requirements.txt` / `pyproject.toml`）
3. 框架识别（基于依赖声明 + 入口模式 · 如 `FastAPI()` / `express()` / `@SpringBootApplication`）
4. 入口文件探测（main.py / index.ts / App.tsx / pom.xml 主模块等）
5. Grep 关键模式扫描（类定义 / 函数签名 / API 端点 / DB 访问模式 / env 读取点）
6. 依赖图构建（模块间 import / require 关系 · 顶层依赖粒度 · 不做全量符号级依赖）
7. 代码行数探测（粗略 · 用于判定是否 > 10 万行）
8. > 10 万行自动降级委托 `codebase-onboarding`（IC-L2-02 → L1-05 IC-12）
9. 结果写 Project KB（缓存 key = repo_path + git_head）
10. 命中缓存直接返回（同 repo + 同 head 不重复分析）

**Out-of-scope**：
- ❌ 不做 AST 深度分析（符号表 / 调用图 / 类型推导等）→ 委托 `codebase-onboarding`（但 onboarding 内部也可能不做得那么深 · 依赖 L1-05 子 Agent 实现）
- ❌ 不做代码重构 / 代码生成（那是 L1-05 调 `tdd` / `prp-implement` skill）
- ❌ 不做代码质量打分 / lint / 类型检查（那是专业工具 · 不归本 L2）
- ❌ 不做跨仓库的依赖分析（单仓库 scope）
- ❌ 不做 Git 历史挖掘（不看 commit log · 不做贡献者分析）
- ❌ 不执行任何代码（scope §5.8.5 禁止 4）
- ❌ 不做 SQL 优化建议（scope §5.8 任务表：专业 DB 技能走 `database-reviewer` 子 Agent）

**边界规则**：
- 本 L2 做"**广度优先概览**" · 不做"**深度钻研**"——后者委托 onboarding 子 Agent
- 10 万行是"**单体 Agent 硬读 vs 委托**"的硬分界（scope §5.8.4 硬约束 2）
- 结果入 KB 是"**硬约束**"（scope §5.8.6 必须义务 4）· 禁短寿命消耗即弃

---

### 9.4 约束

**业务模式引用**：
- **PM-08 可审计全链追溯**：每次 analyze 必审计
- **PM-04 WP 拓扑 / mini-PMP**：代码结构摘要是 WP 拆解的输入
- **PM-09 能力抽象层**：Glob / Grep / Read 是工具柜底层，本 L2 是场景封装

**硬约束清单**：
1. **> 10 万行必委托**：本 L2 估算行数超过阈值必发 IC-L2-02 委托 · 禁止单体硬读（scope §5.8.4 硬约束 2）
2. **结果必入 KB**：analyze 完成必写 L1-06 · 禁止"分析完就丢"（scope §5.8.6 必须义务 4）
3. **缓存命中先于分析**：IC-11 请求到达后先查 KB 缓存（repo_path + git_head）· 命中即直接返回
4. **路径只读不执行**：禁止 `shell` / `exec` / 任何代码运行（scope §5.8.5 禁止 4）
5. **不修改代码文件**：本 L2 是纯只读（scope §5.8.5 禁止 1）
6. **Grep 扫描的目标模式清单有限**：不做"全量枚举所有模式" · 必须是有目的的扫描（避免 token 爆炸）

**性能约束**（文字描述）：
- 小仓库（< 1 万行）分析 + 入 KB ≤ 30s
- 中等仓库（1-10 万行）分析 + 入 KB ≤ 3min
- 大仓库（> 10 万行）委托决策 ≤ 5s · 子 Agent 报告返回时间视 onboarding 而定（本 L2 不承诺）
- 缓存命中返回 ≤ 1s
- 并发：同一 repo_path 禁并发分析（L2-04 加锁）· 不同 repo 可并行

---

### 9.5 🚫 禁止行为（明确清单）

- 🚫 **禁止对 > 10 万行代码仓库硬扛单体分析**（必须委托 · scope §5.8.4 硬约束 2）
- 🚫 **禁止分析完不入 KB**（scope §5.8.6 必须义务 4）
- 🚫 **禁止执行代码（shell / exec / subprocess）**（scope §5.8.5 禁止 4）
- 🚫 **禁止修改代码文件**（scope §5.8.5 禁止 1）
- 🚫 **禁止跨仓库分析**（scope §5.8.5 禁止 6）
- 🚫 **禁止无目的 Grep 全量模式**（token 预算爆炸风险）
- 🚫 **禁止静默跳过 .gitignore / 大二进制文件**（必须显式忽略规则 · 可追溯）

---

### 9.6 ✅ 必须职责（明确清单）

- ✅ **必须**先查 KB 缓存再决定是否重新分析（缓存 key = repo_path + git_head）
- ✅ **必须**对 > 10 万行触发委托（IC-L2-02 → L1-05 IC-12）
- ✅ **必须**产出"语言 + 框架 + 入口 + 依赖图 + 关键模式"五要素（少一要素即分析不完整）
- ✅ **必须**把结果写 Project KB（持久化到下次复用）
- ✅ **必须**对分析过程中失败（Glob 无结果 / Read 失败 / Grep 超时）走 L2-04 IC-L2-06 结构化 err
- ✅ **必须**对每次 analyze 经 L2-04 走 IC-L2-05 审计
- ✅ **必须**记录"本次分析是命中缓存还是重新跑"（审计字段）

---

### 9.7 🔧 可选功能职责

- 🔧 **依赖图可视化建议**：产出给 L1-10 UI 的依赖图渲染建议（节点 / 边 · UI 自己画）
- 🔧 **变化热点识别**：若有 git log 权限，可识别最近高变动的模块（V1 可选 · 默认关闭）
- 🔧 **framework 版本推断**：从依赖声明中提取主框架版本号（辅助 L1-02 L2-05 TOGAF D 技术架构生成）
- 🔧 **partial 分析模式**：focus_hint 子目录时只分析该目录，整体摘要标记"partial"（避免不必要全仓扫）

---

### 9.8 与其他 L2 / L1 交互（IC-L2 一句话 + 方向）

**作为被调方**：
- 来自 **L2-04** · IC-L2-01 · 方向 L2-04 → L2-02 · 接收：守门后路由的代码 analyze 请求

**作为调用方**：
- 调 **L1-05** · IC-L2-02（对外经 IC-12）· 方向 L2-02 → L1-05 · 意义：> 10 万行委托 codebase-onboarding 子 Agent
- 调 **L1-06** · IC-L2-04（对外经 IC-06/07）· 方向 L2-02 → L1-06 · 意义：写入代码结构摘要到 Project KB
- 调 **L1-06** · IC-L2-04（读缓存）· 方向 L2-02 → L1-06 · 意义：查询同 repo_path + git_head 的历史摘要（命中即跳过重分析）
- 调 **L2-04** · IC-L2-05 · 方向 L2-02 → L2-04 · 意义：审计每次分析动作（含"命中缓存 vs 重新跑"字段）
- 调 **L2-04** · IC-L2-06 · 方向 L2-02 → L2-04 · 意义：分析失败的结构化 err 统一封装

---

### 9.9 🎯 交付验证大纲（Given-When-Then）

#### 正向场景

- **Given** 调用方请求分析 `./backend`（FastAPI + Python · 约 3 万行 · 首次分析）· L2-04 判定 delegate=false · 路由到本 L2
  - **When** 本 L2 先查 KB 缓存（未命中）→ Glob 扫目录 → Read 入口（main.py / pyproject.toml）→ Grep 模式（FastAPI 路由 / SQLAlchemy 模型）→ 组装摘要 → 写 KB
  - **Then** 返回五要素摘要（language=Python · framework=FastAPI · entries=['app/main.py'] · deps=[sqlalchemy, pydantic, ...] · patterns=[...]) + kb_entry_id + 审计事件

- **Given** 调用方请求再次分析同一 `./backend` · git_head 未变
  - **When** 本 L2 查 KB 缓存 → 命中（key = repo_path + git_head）
  - **Then** 直接返回缓存摘要 + 审计标记"cache_hit" · 不重新跑 Glob / Grep

- **Given** 调用方请求分析 `./monorepo`（约 30 万行 · 多语言）· L2-04 估算行数 → 触发 delegate=true
  - **When** 本 L2 经 IC-L2-02 委托 L1-05 → L1-05 跑 codebase-onboarding 子 Agent → 返回 structure_summary + kb_entries
  - **Then** 本 L2 把 kb_entries 写 L1-06 · 返回 structure_summary 给调用方 · 审计含"delegated=true + subagent_session_id"

#### 负向场景

- **Given** 调用方请求分析 `/etc/passwd`（跨项目 · 不在本项目 scope）
  - **When** L2-04 路径校验不通过（跨项目）
  - **Then** 本 L2 不被调用 · L2-04 直接拒绝 + err

- **Given** 调用方请求分析 `./binary_blobs`（只有 .so / .bin 文件 · Glob 结果全为二进制）
  - **When** 本 L2 Glob 后发现无可读文本代码
  - **Then** 返回结构化 err（type=no_text_code）+ 不写 KB + 审计

- **Given** 调用方请求 analyze 但子 Agent（codebase-onboarding）超时 / 崩溃（经 L1-05 降级）
  - **When** L1-05 返回 err
  - **Then** 本 L2 透传 err（不兜底硬读 · 否则违反硬约束）+ 建议调用方缩小 focus_hint 或人工介入

- **Given** Grep 模式扫描超过 token 预算
  - **When** 本 L2 检测到模式输出过大
  - **Then** 截断 + 标记 partial=true + 审计"grep_truncated" + 不失败（保返回 best-effort 摘要）

#### 集成场景

- **I1** · L1-01 Brownfield 启动 → IC-11 analyze → L2-04 → L2-02 → 小仓直分析 → 摘要回 L1-01 → L1-01 决策"接入哪个阶段" + L1-02 L2-05 读 KB 缓存用于 TOGAF D 生成
- **I2** · L1-02 L2-05 生成 TOGAF C 时需要现有系统数据架构 → IC-11 analyze → L2-04 → L2-02 → KB 缓存命中 → 即时返回
- **I3** · 大仓（50 万行）分析 → 委托 onboarding 子 Agent → L1-07 supervisor 观察到长耗时 → 推 INFO 告知用户"正在委托分析"
- **I4** · 跨 session · 首轮分析 completed 但 KB 写入失败 → 重启后重新发起 IC-11 · L2-02 发现 KB 无缓存 · 再分析一次（幂等）

#### 性能阈值（P99）

- 小仓（< 1 万行）分析 + 入 KB ≤ 30s
- 中仓（1-10 万行）分析 + 入 KB ≤ 3min
- 大仓（> 10 万行）委托决策 ≤ 5s
- 缓存命中返回 ≤ 1s

---

## 10. L2-03 · 图片视觉理解编排器 详细定义

### 10.1 职责 + 锚定

**一句话职责**：HarnessFlow 的 "看图说话师 "—— 对给定本地图片路径执行 Read 加载（Claude 多模态原生）+ 主 Agent 视觉理解，根据 image_hint（架构图 / UI mock / 截图）按对应模板产出结构化描述（节点 / 关系 / 组件 / 状态 等），严格禁止原始二进制外抛与外部服务上传。

**上游锚定**：
- Goal §3.1 输入 · 用户提供的架构图 / UI mock
- scope §5.8.1 职责 "读图片（架构图 / 截图 / UI mock）"
- scope §5.8.3 In-scope "图片视觉理解（Claude 多模态原生能力）"
- scope §5.8.5 禁止 3 "禁止图片上传到外部服务（隐私保护；只本地 Read）"
- scope §5.8.5 禁止 5 "禁止返回未经结构化的原始图片二进制给其他 L1"
- scope §5.8.6 必须义务 3 "必须为图片产出结构化描述（不只是'我看到了一张图'；必须列节点 / 组件 / 状态）"
- businessFlow BF-L3-08（图片/截图分析流）

**下游服务**：
- L2-04（路径守门 · 图片格式校验入口）
- L1-01（用户上传架构图作为项目目标输入的补充理解）
- L1-02 L2-05（TOGAF 架构生成时参考用户给的现有架构图）
- L1-04（Playwright 截图作为验证证据 · S5 阶段）
- L1-10（架构图展厅 / 截图预览的结构化数据源 · P1 新增 UI）

---

### 10.2 输入 / 输出

**输入**：
- 从 L2-04 经 IC-L2-01 路由来的图片分析请求（带 `type=image` + path + action=analyze + 可选 `image_hint`）
- image_hint 枚举三类：`architecture` / `ui_mock` / `screenshot`（若调用方未提供 · 本 L2 用启发式推断 · 推断失败默认走 `screenshot`）
- 支持格式：png / jpg / webp / gif（静态帧）· V1 范围

**输出**：
- **结构化描述**（按 image_hint 对应模板）：
  - architecture → 节点列表 + 节点间关系 + 推断的技术栈 + 分层标注
  - ui_mock → 布局骨架 + 组件清单（按位置）+ 交互点（按钮 / 输入框 / 链接）+ 色彩风格摘要
  - screenshot → 当前页面状态 + 可见文本摘录 + 是否有错误迹象（红色告警 / 异常弹窗）+ 时间戳（若可见）
- **元数据**：image_hint（确认或本 L2 推断出的）+ path + 图片分辨率 + 文件大小

**不做的输出**：
- ❌ 绝不返回原始二进制 / base64 / 像素矩阵（scope §5.8.5 禁止 5）
- ❌ 不产出 OCR 精确文本（模糊识别可 · 精确 OCR 是 out-of-scope · scope §5.8.3）
- ❌ 不产出图片生成（只读不生成 · scope §5.8.3）

---

### 10.3 边界

**In-scope**：
1. Read 本地图片（Claude 多模态原生加载）
2. 主 Agent 视觉理解（走当前会话 · 不跨出模型边界）
3. 按 image_hint 选结构化模板：
   - architecture（节点 + 关系 + 技术栈）
   - ui_mock（布局 + 组件 + 交互点 + 配色）
   - screenshot（状态 + 文本 + 错误迹象）
4. 若 image_hint 未提供则启发式推断（基于视觉特征 · 如"有矩形框 + 箭头"→ architecture；"有按钮 / 输入框"→ ui_mock；否则 → screenshot）
5. 结构化 + 审计 + 返回
6. 多图批量（调用方一次给多个 path · 本 L2 串行处理）

**Out-of-scope**：
- ❌ 不做精确 OCR（scope §5.8.3 · 未来）
- ❌ 不做图片生成 / 编辑 / 标注（只读）
- ❌ 不做外部视觉服务调用（禁隐私泄露 · scope §5.8.5 禁止 3）
- ❌ 不做 PDF / docx 等文档里的图片抽取（PDF 不支持 · V1 · scope §5.8.3）
- ❌ 不做视频帧提取（视频完全 out-of-scope · V1）
- ❌ 不做图片语义对比 / diff（两张图差异分析 out-of-scope · V2 再议）
- ❌ 不上传到任何外部 hosting / CDN / OCR API（隐私硬约束）

**边界规则**：
- 本 L2 只做"**结构化看图**" · 不做"**精确读字**"
- 图片处理**全程本地**（Read 本地文件 + Claude 视觉模型走主 session · 不出模型边界）
- 图片 hint 的三类**穷举 V1 范围**· 新增类型需走 scope 变更流程

---

### 10.4 约束

**业务模式引用**：
- **PM-08 可审计全链追溯**：图片分析必审计（但不记原始像素 · 只记路径 + 摘要）
- **PM-09 能力抽象层**：Read 是工具柜 · 本 L2 是视觉场景封装

**硬约束清单**：
1. **禁外部服务**：任何网络调用、任何外部 API 上传图片 = 硬拒绝 · 本 L2 启动时即校验无外部 endpoint 配置
2. **禁原始二进制外抛**：IC 返回值绝不含 bytes / base64 / 像素阵列（scope §5.8.5 禁止 5）
3. **结构化非空**：返回描述必含至少 1 个节点 / 组件 / 状态（"我看到了一张图"不算合格输出 · scope §5.8.6 必须义务 3）
4. **格式白名单**：png / jpg / webp / gif（静态）· 其他格式拒绝并走 L2-04 IC-L2-06 err
5. **文件大小上限**：单图 ≤ 20MB（V1 保守；超则拒绝 · 避免 token 爆炸）
6. **审计不记像素**：审计事件只含 path + 图片类型 + 描述摘要（前 200 字）· 不记完整描述、不记原始数据

**性能约束**（文字描述）：
- 单图视觉理解 + 结构化 ≤ 15s（受 Claude 视觉模型延迟约束）
- 批量（10 图）串行 ≤ 3min
- image_hint 未提供时的启发式推断 ≤ 2s（推断失败则默认 screenshot · 不阻塞主流程）
- 并发：同一 path 禁并发（L2-04 加锁）· 不同 path 可并行（视觉模型自身可能串行化）

---

### 10.5 🚫 禁止行为（明确清单）

- 🚫 **禁止返回原始图片二进制 / base64 / 像素矩阵**（scope §5.8.5 禁止 5）
- 🚫 **禁止上传图片到任何外部服务**（scope §5.8.5 禁止 3 · 本 L2 启动时硬校验无外部 endpoint）
- 🚫 **禁止产出"我看到了一张图"之类非结构化描述**（scope §5.8.6 必须义务 3 · 必须有节点 / 组件 / 状态）
- 🚫 **禁止处理 PDF / docx 嵌入图片**（V1 out-of-scope · scope §5.8.3）
- 🚫 **禁止处理视频 / 视频帧**（V1 完全 out-of-scope）
- 🚫 **禁止精确 OCR 模式**（模糊识别可 · 精确 OCR 属未来 scope）
- 🚫 **禁止在审计事件中记录图片的完整描述 / 像素 / 原始数据**（只记路径 + 摘要）

---

### 10.6 ✅ 必须职责（明确清单）

- ✅ **必须**本地 Read 图片（不经任何外部路径）
- ✅ **必须**按 image_hint 产出对应模板的结构化字段（节点 / 组件 / 状态 至少一类）
- ✅ **必须**在 hint 未提供时走启发式推断（并在输出元数据中标明"推断出的"）
- ✅ **必须**对超大图 / 非支持格式通过 L2-04 IC-L2-06 结构化 err
- ✅ **必须**每次分析经 L2-04 走 IC-L2-05 审计（不记像素）
- ✅ **必须**启动时硬校验无外部 endpoint 配置（防运维误配）
- ✅ **必须**对无法理解的图（过于抽象 / 内容混乱）明确返回"low_confidence" 标记而非瞎编

---

### 10.7 🔧 可选功能职责

- 🔧 **多图批量 + 主题合并**：调用方一次给多张相关图（如一个项目的 N 张 UI mock）· 本 L2 串行处理后产"跨图主题摘要"
- 🔧 **图片 hint 主动确认**：推断出 hint 后先问用户"我猜这是 ui_mock · 对吗？"（V1 可选 · 默认跳过直接推断）
- 🔧 **结构化描述的 UI 坐标**：为 ui_mock 产组件的相对坐标（左上右下百分比）· 供 L1-10 UI 做"可点击热区"渲染（P1）
- 🔧 **错误迹象专项模式**：screenshot 若检出"红色告警 / 异常弹窗"可触发 L1-07 supervisor 的 WARN（P1）

---

### 10.8 与其他 L2 / L1 交互（IC-L2 一句话 + 方向）

**作为被调方**：
- 来自 **L2-04** · IC-L2-01 · 方向 L2-04 → L2-03 · 接收：守门后路由的图片 analyze 请求（含 image_hint 或无）

**作为调用方**：
- 调 **L2-04** · IC-L2-05 · 方向 L2-03 → L2-04 · 意义：审计每次视觉分析（path + hint + 摘要 · 不含像素）
- 调 **L2-04** · IC-L2-06 · 方向 L2-03 → L2-04 · 意义：结构化 err（格式不支持 / 大小超限 / 低置信度）

**不交互**：
- ❌ 不调 L1-05（不委托子 Agent · V1 所有图都主 Agent 直看）
- ❌ 不调 L1-06（图不入 KB · 短寿命消耗）
- ❌ 不调 L2-01 / L2-02（跨模态不混用）
- ❌ 不调任何外部服务（硬约束）

---

### 10.9 🎯 交付验证大纲（Given-When-Then）

#### 正向场景

- **Given** 调用方 IC-11 analyze 请求 `uploads/architecture.png` + image_hint=architecture · L2-04 守门通过 · 路由到本 L2
  - **When** 本 L2 Read 图 + 主 Agent 视觉 + 按 architecture 模板结构化
  - **Then** 返回 {nodes: [...], relations: [...], inferred_stack: [...], layers: [...]} + 审计事件（不含像素）

- **Given** 调用方 IC-11 analyze 请求 `mocks/login.png` + image_hint=ui_mock
  - **When** 本 L2 按 ui_mock 模板结构化
  - **Then** 返回 {layout, components, interaction_points, color_palette_summary} + 审计

- **Given** 调用方 IC-11 analyze 请求 `screenshots/error.png` + 无 hint
  - **When** 本 L2 启发式推断 → screenshot · 按 screenshot 模板结构化
  - **Then** 返回 {page_state, visible_text_excerpt, error_signals} + 元数据标 hint_inferred=true + 审计

- **Given** 调用方 IC-11 analyze 请求批量 `[mock_01.png, mock_02.png, mock_03.png]` + image_hint=ui_mock
  - **When** 本 L2 串行处理三图
  - **Then** 依次返回三份结构化描述（可选：附跨图主题摘要）

#### 负向场景

- **Given** 调用方请求分析 `secret.pdf`（PDF 不支持）
  - **When** L2-04 格式校验失败
  - **Then** 结构化 err（type=format_unsupported · V1）+ 审计"unsupported_format"

- **Given** 调用方请求分析 `huge.png`（50MB · 超过 20MB 上限）
  - **When** L2-04 大小校验失败
  - **Then** 结构化 err（type=size_exceeded）+ 审计

- **Given** 调用方请求分析 `noise.png`（视觉抽象 · 无法识别节点 / 组件）
  - **When** 本 L2 视觉理解返回低置信度
  - **Then** 结构化输出 {low_confidence: true, best_effort_summary: "..."} + 审计"low_confidence_image" + 不硬编

- **Given** 启动时发现配置里有外部 image API endpoint（如 OCR 云服务）
  - **When** 本 L2 启动时硬校验
  - **Then** 拒绝启动 + 审计"external_endpoint_blocked" + 告警运维

#### 集成场景

- **I1** · 用户在 L1-10 UI 上传 `architecture-as-is.png` → L1-01 收到 → IC-11 → L2-04 → L2-03 → 返回节点 / 关系 → L1-02 L2-05 生成 TOGAF B 现状架构文档时引用
- **I2** · L1-04 S5 Playwright 抓 screenshot → IC-11 → L2-04 → L2-03 → 识别"错误迹象"→ 作为验证证据链的三段之一
- **I3** · L1-10 "架构图展厅"（P1 新增 UI）调 IC-18 query_audit_trail 反查某结构化描述 → 能溯回原图路径 + 审计事件（不暴露像素）
- **I4** · 跨 session · 分析中被中断 → 重启后调用方重新发 IC-11 · 本 L2 再次分析（图不入 KB · 幂等简单）

#### 性能阈值（P99）

- 单图 analyze ≤ 15s（受 Claude 视觉模型延迟限）
- 批量 10 图串行 ≤ 3min
- 启发式 hint 推断 ≤ 2s
- 格式 / 大小校验 ≤ 100ms

---

## 11. L2-04 · 路径安全与降级编排器（横切） 详细定义

### 11.1 职责 + 锚定

**一句话职责**：HarnessFlow 的 "多模态守门人 "—— 所有 IC-11 请求的统一入口，负责路径白名单校验（写路径限 `docs/` / `tests/` / `harnessFlow/`；读路径限项目 scope 内）+ 文件大小 / 行数阈值判定（触发分页或委托）+ 不可读告警（权限 / 不存在 / 二进制）+ 降级路由（直接 / 分页 / 委托 / 拒绝）+ 每次 I/O 走 IC-09 审计 · 是本 L1 的"脊柱 + 安全门卫"。

**上游锚定**：
- Goal §3.2 输出 D · "可审计的决策链"
- scope §5.8.4 硬约束 3 "所有读写路径必须是项目内相对路径或显式允许的外部路径（安全约束）"
- scope §5.8.4 硬约束 1 "md > 2000 行必分页" + 硬约束 2 "> 10 万行必委托"
- scope §5.8.5 禁止 2 "禁止写入非 docs/ / tests/ / harnessFlow/ 路径"
- scope §5.8.5 禁止 6 "禁止跨项目读写"
- scope §5.8.6 必须义务 1 "必须为每次读写产生 L1-09 事件"
- scope §5.8.6 必须义务 5 "必须对不可读文件明确告警 · 禁静默失败"
- businessFlow BF-X-03（事件总线落盘流）+ BF-L3-06/07/08 横切

**下游服务**：
- 全部 IC-11 调用方（L1-01 / L1-02 / L1-04 · 对外唯一 L1-08 入口）
- L2-01 / L2-02 / L2-03（守门通过后分派）
- L1-09（审计事件总线）
- L1-07（硬约束违规时通知监督）

---

### 11.2 输入 / 输出

**输入**：
- **IC-11 请求**（由 L1-01 / L1-02 / L1-04 发起 · 经 scope §8.2）：`{type: md/code/image, path, action: read/write/update/analyze, 可选参数如 content / image_hint / focus_hint}`
- **配置**：允许写入的白名单路径清单（启动时从 `HarnessFlowGoal.md` 或 `scope` 派生 · 默认 `docs/` / `tests/` / `harnessFlow/`）
- **阈值配置**：md 分页阈值（默认 2000 行）/ 代码委托阈值（默认 10 万行）/ 图片大小上限（默认 20MB）
- **项目 scope 根**（启动时确定的项目根目录 · 禁止跨此根）

**输出**：
- **IC-L2-01 分派**：按 `type` 路由到对应模态 L2（带降级标记 paged / delegate）
- **结构化响应**（透传给调用方）：读结果 / 写确认 / 分析摘要
- **结构化 err**（统一封装）：type + reason + suggested_action
- **审计事件**（IC-L2-05 → L1-09 IC-09）：每次 I/O 含 path + size + hash + 模态 + 结果 + 耗时
- **硬约束违规通知**（IC-L2-07 → L1-07 supervisor）：路径越权 / 强制不分页 等被拒绝的请求信息

---

### 11.3 边界

**In-scope**：
1. 路径白名单校验：
   - **写路径**：必须在 `docs/` / `tests/` / `harnessFlow/` 内（或配置追加的显式路径）
   - **读路径**：必须在项目 scope 根内（禁跨项目 / 禁 /etc / 禁 /home 等系统路径）
   - **特殊**：图片路径可接受项目根内的 `uploads/` / 显式允许的"外部上传目录"（有限白名单）
2. 文件大小 / 行数阈值判定：
   - md：快速行数探测 · > 2000 行标 paged=true
   - code：Glob + 粗估行数 · > 10 万行标 delegate=true
   - image：文件大小 · > 20MB 拒绝
3. 不可读告警：
   - 文件不存在 → 结构化 err（type=not_found）
   - 权限拒绝 → 结构化 err（type=permission_denied）
   - 二进制未支持（md 模式读到非文本）→ 结构化 err（type=binary_unsupported）
4. 降级路由：
   - 小文件 / 小仓 / 小图 → 直接 IC-L2-01 分派到对应模态 L2
   - 大文件 → IC-L2-01 带 paged=true
   - 大仓 → IC-L2-01 带 delegate=true（由 L2-02 具体执行委托）
   - 不可读 → 直接 IC-L2-06 err 返回（不分派）
5. 审计事件：每次 I/O 无论成败都 IC-L2-05 走 IC-09 落盘（成功含 result summary · 失败含 err）
6. 硬约束违规监督推送：写非白名单 / 尝试绕过分页 / 外部 endpoint 配置等 · 通知 L1-07
7. 并发控制：同一 path 的写 / 分析禁并发（加锁）· 不同 path 可并行

**Out-of-scope**：
- ❌ 不做具体读写 I/O（→ L2-01 / L2-02 / L2-03）
- ❌ 不做内容解析 / 视觉理解（→ 对应模态 L2）
- ❌ 不做 KB 读写（→ L2-02 自己写 L1-06）
- ❌ 不决定"该不该分析"业务逻辑（→ 调用方业务判断）
- ❌ 不做复杂权限系统（只简单路径白名单 · 无 RBAC）
- ❌ 不做加密 / 脱敏（若图片 / 代码含敏感信息 · 由用户 / 上游保证）

**边界规则**：
- 本 L2 是"**纯守门层**"· 一律不碰内容
- "守门"三板斧：**路径校验 → 阈值判定 → 降级路由**（缺一不可）
- 所有 IC-11 **必经本 L2**· 模态 L2 禁止对外直接接收请求

---

### 11.4 约束

**业务模式引用**：
- **PM-08 可审计全链追溯**：每次 I/O 必审计
- **PM-10 事件总线单一事实源**：审计通过 IC-09 落 L1-09
- **PM-07 user-intervene-always-wins**：用户若要扩展白名单 · 需显式走 scope 变更（本 L2 启动时读一次配置 · 不运行时热改）

**硬约束清单**：
1. **路径白名单硬锁**：写 `docs/` / `tests/` / `harnessFlow/` 之外一律拒绝 · 禁任何运行时 bypass（scope §5.8.5 禁止 2）
2. **跨项目读禁**：超出项目 scope 根的读请求一律拒绝（scope §5.8.5 禁止 6）
3. **每次 I/O 必审计**：无论成败 / 是否命中缓存 / 是否降级 · 审计不可省略（scope §5.8.6 必须义务 1）
4. **不可读必告警**：禁止静默失败（scope §5.8.6 必须义务 5）· 返回结构化 err
5. **阈值判定不可跳**：md 分页 / code 委托 / image 大小 · 三个阈值是硬检（scope §5.8.4 硬约束 1/2/3）
6. **同一 path 并发写锁**：禁止同时多个 IC-11 对同一 path 写 · 必须串行化
7. **审计事件不记敏感**：图片不记像素 · 代码不记全文 · md 不记完整内容（只记 path + hash + 摘要）

**性能约束**（文字描述）：
- 路径校验 + 阈值探测 ≤ 200ms（除代码大仓粗估行数可能 ≤ 5s）
- IC-L2-01 分派 ≤ 50ms（不阻塞模态 L2）
- 审计事件落盘 ≤ 100ms（IC-09 同步写 · 符合 L1-09 性能指标）
- 守门总开销（校验 + 分派 + 审计）≤ 500ms（小文件场景 P99）
- 并发：同一 project 内 ≤ 100 个 IC-11 并发（超则排队）· 不同 path 不排队

---

### 11.5 🚫 禁止行为（明确清单）

- 🚫 **禁止允许运行时热改白名单**（必须启动时固定 · 防误操作 · 改动必走 scope 变更）
- 🚫 **禁止跳过审计**（任何 I/O 都必须 IC-09 · 包括失败 · scope §5.8.6 必须义务 1）
- 🚫 **禁止静默失败**（不可读必结构化 err · scope §5.8.6 必须义务 5）
- 🚫 **禁止分派模态 L2 前未判定阈值**（分页 / 委托 / 大小都是守门职责）
- 🚫 **禁止审计事件中包含完整内容 / 像素 / 原始二进制**（只记 hash + 摘要）
- 🚫 **禁止路径拼接时使用用户原始字符串**（必须规范化 · 防 `../../../etc/...` 逃逸）
- 🚫 **禁止对硬约束违规静默放行**（必须通知 L1-07 supervisor）

---

### 11.6 ✅ 必须职责（明确清单）

- ✅ **必须**路径规范化（resolve symlink + 解析 `..` + 绝对路径比对白名单）
- ✅ **必须**三阈值判定（md 行数 / code 行数 / image 大小）· 一个不漏
- ✅ **必须**每次 I/O 走 IC-09 审计（成 / 败 / 缓存命中都记）
- ✅ **必须**不可读时返回结构化 err（含 type + reason + suggested_action）
- ✅ **必须**硬约束违规时通知 L1-07 supervisor（IC-L2-07）
- ✅ **必须**同一 path 的写请求串行化（加锁）
- ✅ **必须**对 image 外部 endpoint 配置启动时硬校验
- ✅ **必须**启动时加载白名单配置 + 阈值配置（不可运行时改）

---

### 11.7 🔧 可选功能职责

- 🔧 **审计事件压缩**：高频 I/O 场景下审计事件聚合（1 分钟内同 path 同 action 合并 · 避免审计日志爆炸 · V2 再考虑）
- 🔧 **降级决策缓存**：对同一 repo_path 的阈值探测结果缓存（避免每次都 Glob 粗估）
- 🔧 **请求去重**：调用方在极短时间内发重复 IC-11（同 path 同 action）→ 合并处理（V1 可选 · 默认关闭）
- 🔧 **白名单动态扩展提案**：用户在 UI 点"我想写 `scripts/`" → 产 scope 变更提案给用户 → 批准后下次启动生效（V2 UX 增强）

---

### 11.8 与其他 L2 / L1 交互（IC-L2 一句话 + 方向）

**作为被调方**：
- 来自 **全部 IC-11 调用方**（L1-01 / L1-02 / L1-04 · 经 scope §8.2 IC-11）· 方向 调用方 → L2-04 · 接收：所有多模态内容处理请求

**作为调用方**：
- 调 **L2-01** · IC-L2-01 · 方向 L2-04 → L2-01 · 意义：守门通过后路由 md 请求（可带 paged 标记）
- 调 **L2-02** · IC-L2-01 · 方向 L2-04 → L2-02 · 意义：守门通过后路由代码请求（可带 delegate 标记）
- 调 **L2-03** · IC-L2-01 · 方向 L2-04 → L2-03 · 意义：守门通过后路由图片请求（可带 image_hint）
- 调 **L1-09** · IC-L2-05（对外经 IC-09）· 方向 L2-04 → L1-09 · 意义：审计事件落盘
- 调 **L1-07** · IC-L2-07（经 BF-X-02 监督广播）· 方向 L2-04 → L1-07 · 意义：硬约束违规通知
- 调 **调用方**· IC-L2-06 · 方向 L2-04 → 调用方 · 意义：结构化 err 返回（统一封装模态 L2 抛出的 err + 自身守门失败）

---

### 11.9 🎯 交付验证大纲（Given-When-Then）

#### 正向场景

- **Given** 调用方 IC-11 写 `docs/planning/goals.md`（path 在白名单）· content 正常
  - **When** 本 L2 路径规范化 + 白名单校验通过 + 阈值探测 paged=false + 加锁 → 分派 L2-01 → L2-01 写成功 → 审计
  - **Then** 调用方收到写确认 + 审计事件（含 path + hash + 耗时）落 L1-09

- **Given** 调用方 IC-11 读 `big.md`（3500 行）
  - **When** 本 L2 路径校验通过 + 行数探测 → paged=true · 分派 L2-01（含 paged 标记）→ L2-01 分页读完
  - **Then** 返回合并 sections + 多条审计事件（每页一条）

- **Given** 调用方 IC-11 分析 `./bigRepo`（估算 30 万行）
  - **When** 本 L2 路径校验通过 + 行数探测 > 10 万 → delegate=true · 分派 L2-02（含 delegate 标记）→ L2-02 经 L1-05 委托 → 返回 summary
  - **Then** 调用方收到 structure_summary + 审计（含 delegated=true）

- **Given** 调用方 IC-11 分析 `uploads/arch.png`（12MB · png）
  - **When** 本 L2 格式 + 大小校验通过 + 路径白名单通过 → 分派 L2-03 → 返回结构化描述
  - **Then** 调用方收到描述 + 审计（不含像素 · 只含 path + hint + 描述摘要）

#### 负向场景

- **Given** 调用方 IC-11 写 `/etc/hosts`（跨系统路径）
  - **When** 本 L2 路径规范化 → 不在白名单
  - **Then** 直接拒绝 + 结构化 err（type=path_forbidden）+ 审计"path_forbidden"事件 + IC-L2-07 通知 L1-07 supervisor

- **Given** 调用方 IC-11 读 `../../../secret.md`（路径逃逸尝试）
  - **When** 本 L2 路径规范化 resolve `..` → 超出项目 scope 根
  - **Then** 拒绝 + 结构化 err + 审计"path_escape_blocked" + 通知 L1-07

- **Given** 调用方 IC-11 读 `missing.md`（文件不存在）
  - **When** 本 L2 路径校验通过（白名单内）+ 存在性检查失败
  - **Then** 结构化 err（type=not_found）+ 审计"not_found"事件（禁静默失败）

- **Given** 调用方 IC-11 读某 `photo.jpg` 但写的是 `type=md`（类型不匹配）
  - **When** 本 L2 识别文件扩展名 vs 请求 type 不匹配
  - **Then** 结构化 err（type=type_mismatch）+ 审计 · 不分派任何模态 L2

- **Given** 调用方 IC-11 写 20MB 的 md 文件（md 通常不应这么大）
  - **When** 本 L2 行数探测触发（假设 > 2000 行）→ 走 paged · 不阻塞（md 写大文件合法）
  - **Then** 正常走分页 · 审计标 `large_md_write`（供 supervisor 观察模式异常）

- **Given** 启动时配置含 image 外部 endpoint（如 `OCR_URL=https://ocr.xxx`）
  - **When** 本 L2 启动时硬校验
  - **Then** 拒绝启动 + 审计 + 硬告警（scope §5.8.5 禁止 3）

#### 集成场景（横切 / 跨 L1）

- **I1** · 全 IC-11 端到端 · 调用方 → L2-04 → 模态 L2 → 返回 + 审计落 L1-09 · 路径全程可追溯
- **I2** · 并发 · 多个 IC-11 对同一 `docs/planning/requirements.md` 写 · L2-04 加锁 · 串行化通过
- **I3** · Supervisor 观察 · L1-07 通过 L1-09 事件总线观察到连续 5 次"path_forbidden"违规 → 触发 WARN 推给用户
- **I4** · 跨 session · 恢复时 L2-04 启动 · 重新加载白名单 + 阈值 · 审计落"L2-04_started"事件
- **I5** · L1-07 硬红线场景 · state=HALTED · L2-04 接收 IC-11 → 拒绝（审计 "halted_denied"）直到用户授权恢复

#### 性能阈值（P99）

- 路径校验 + 阈值探测 ≤ 200ms（除代码仓库粗估行数 ≤ 5s）
- IC-L2-01 分派 ≤ 50ms
- 审计事件落盘 ≤ 100ms
- 守门总开销 ≤ 500ms（小文件）
- 同 project 并发：≤ 100 IC-11 排队上限

---

## 12. L1-08 对外 scope §8 IC 契约映射（本 L1 实际承担）

本表列出 L1-08 对 scope §8 中 20 条 IC 契约的实际承担（发起方 or 接收方）+ 内部 L2 承担者。

### 12.1 L1-08 作为接收方的 IC

| scope §8 IC | 内部 L2 承接者 | 触发时机 | 来源 L1 |
|---|---|---|---|
| **IC-11** process_content | **L2-04**（唯一入口）→ 按 type 路由到 L2-01 / L2-02 / L2-03 | 调用方需要读 / 写 / 分析 md / code / image | L1-01 主要、L1-02 次要、L1-04 偶发 |

### 12.2 L1-08 作为发起方的 IC

| scope §8 IC | 内部 L2 承担者 | 触发时机 | 目标 L1 |
|---|---|---|---|
| **IC-12** delegate_codebase_onboarding | **L2-02**（> 10 万行阈值命中时） | L2-04 触发 delegate=true 后 L2-02 委托 | L1-05 |
| **IC-06** kb_read | **L2-02**（查 KB 缓存同 repo_path + git_head） | L2-02 分析前必查缓存 | L1-06 |
| **IC-07** kb_write_session | **L2-02**（默认写 Project KB · 非 session · 但走同 L1-06 接口） | 代码结构摘要产出后持久化 | L1-06 |
| **IC-09** append_event | **L2-04**（统一走 · 全 L2 审计经由 L2-04 IC-L2-05 转发） | 每次 I/O · 每次守门失败 · 每次降级决策 | L1-09 |

### 12.3 L1-08 IC 承担总览图

```
                    ┌──────────────────────────────────┐
    L1-01 / L1-02 / L1-04 ──IC-11──→  L2-04（守门唯一入口）    │
                    │                  │                       │
                    │                  │ IC-L2-01 (按 type 分派)│
                    │                  │                       │
                    │           ┌──────┼──────┐                 │
                    │           ▼      ▼      ▼                 │
                    │        L2-01  L2-02  L2-03                │
                    │        (md)  (code)  (image)              │
                    │                  │                       │
                    │                  │ L2-02 → IC-12 ─────→ L1-05
                    │                  │       → IC-06/07 ──→ L1-06
                    │                  │                       │
                    │                  └── IC-09 ──────────→ L1-09 (审计)
                    │                                          │
                    │  L2-04 → IC-L2-07 ───────────────────→ L1-07 (违规通知)
                    └──────────────────────────────────────────┘
```

### 12.4 未承担的 IC

scope §8 中 L1-08 明确**不承担**的契约：

| scope §8 IC | 所属 L1 | 说明 |
|---|---|---|
| IC-01 request_state_transition | L1-01 / L1-02 | 本 L1 不做状态转换 |
| IC-02 tick | L1-01 | 本 L1 无 tick |
| IC-03 dispatch_wbs | L1-03 | 本 L1 不做 WBS |
| IC-04 request_tdd | L1-04 | 本 L1 不做 TDD |
| IC-05 delegate_subagent（通用） | L1-05 | 本 L1 只用 IC-12（专项大仓委托）· 不用通用 IC-05 |
| IC-08 kb_promote | L1-06 | 本 L1 只 read/write session 级 · 不做晋升 |
| IC-10 forward_supervisor_event | L1-09 | 本 L1 不转发 supervisor |
| IC-13 push_suggestion | L1-07 | 本 L1 不发监督建议 |
| IC-14 push_rollback_route | L1-07 | 本 L1 不发回退路由 |
| IC-15 request_hard_halt | L1-07 | 本 L1 不发硬 halt |
| IC-16 push_stage_gate_card | L1-02 | 本 L1 不做 Gate |
| IC-17 user_intervene | L1-10 → L1-01 | 本 L1 不直接接 UI |
| IC-18 query_audit_trail | L1-10 → L1-09 | 本 L1 不做审计查询 |
| IC-19 request_wbs_decomposition | L1-02 | 本 L1 不做 WBS |
| IC-20 delegate_verifier | L1-04 | 本 L1 不做 verifier |

---

## 13. 本 L1 retro 位点

**占位说明**：
L1-08 实现完成 + 集成测试通过后，按 11 项 retro 模板撰写本 L1 的 retro（存入 `retros/L1-08.md`）。

**11 项模板锚定**（同 L1-01 §15.1）：

1. **本 L1 目标达成度**：md / code / image 三模态读写 + 守门 + 降级是否全实现 · 硬约束是否全顶住
2. **与 scope §5.8 的契合度**：禁止行为清单 / 必须义务清单 / 边界是否严守（尤其"不上传外部" / "不入 KB（md/image）" / "> 10 万行必委托"）
3. **关键决策复盘**：4 L2 切分决定（三模态 + 一横切）/ L2-04 作为唯一入口的决策 / 缓存 key（repo_path + git_head）设计 / 图片 hint 启发式规则
4. **困难与突破**：大仓估算行数的开销控制 / 图片视觉理解的置信度标注 / 路径规范化的边界 case（symlink / `..` 逃逸 / Windows 路径）
5. **成本回顾**：L1-08 开发总耗时 / Claude 视觉调用成本 / codebase-onboarding 子 Agent 的委托频次成本
6. **进度回顾**：4 个 L2 实际工作量 vs 估算（L2-04 横切最重 · L2-01 最轻）
7. **质量指标汇总**：单测覆盖率 / 集成测试通过率 / 性能指标达标情况（守门开销 / 分页效率 / 视觉延迟）
8. **沟通 & 干系人**：本 L1 对 L1-05（委托通道）/ L1-06（KB）/ L1-07（违规通知）/ L1-09（审计）的依赖协同情况
9. **风险事件**：是否发生"路径逃逸"/ "不可读静默失败"/ "外部 endpoint 误配"等违规尝试及其拦截效果
10. **知识沉淀**：ADR-L1-08-* 累积条目（白名单路径策略 / 阈值选择理由 / 降级策略）
11. **后续行动项**：L1-08 后续 v1.1 / v2.0 的增强方向（如 PDF 支持 / OCR / 视频帧 / 多图主题合并 / UI 坐标映射）

---

## 附录 A · 术语（L1-08 本地）

| 术语 | 含义 |
|---|---|
| **多模态内容** | md 文档 / 代码仓库 / 图片 三类非纯文本请求的统称（V1 范围 · 不含 PDF / 视频 / 音频） |
| **守门人（Gatekeeper）** | L2-04 的别称 · 所有 IC-11 请求的唯一统一入口 · 负责路径校验 + 阈值判定 + 降级路由 + 审计 |
| **分页读（paged read）** | md > 2000 行时按页循环 Read 的机制（scope §5.8.4 硬约束 1） |
| **委托（delegate）** | 代码仓库 > 10 万行时交给 `codebase-onboarding` 独立 session 子 Agent 处理的降级机制（scope §5.8.4 硬约束 2） |
| **路径白名单** | 允许写入的路径集合（默认 `docs/` / `tests/` / `harnessFlow/`）· 读路径更宽（项目 scope 根内） |
| **image_hint** | 图片类型提示 · 枚举：`architecture` / `ui_mock` / `screenshot` · 决定结构化描述模板 |
| **结构化描述** | 图片视觉理解的产出 · 含节点 / 组件 / 状态 等字段 · 禁原始二进制 |
| **sections** | md 读产出的结构 · 含 frontmatter + headings 层次 + 按 heading 划分的段落 |
| **结构摘要（structure_summary）** | 代码分析产出 · 含语言 / 框架 / 入口 / 依赖 / 关键模式五要素 |
| **KB 缓存** | L2-02 对同 repo_path + 同 git_head 的分析结果的 Project KB 级缓存（命中即跳过重分析） |
| **不可读告警** | 文件不存在 / 权限拒绝 / 二进制未支持 时的结构化 err（禁静默 · scope §5.8.6 必须义务 5） |
| **路径规范化** | 对用户原始路径做 resolve symlink + 解析 `..` + 转绝对路径 · 防路径逃逸 |
| **外部 endpoint 硬校验** | 启动时扫描配置 · 发现图片 / 代码任何外部 API 即拒绝启动（隐私硬约束） |

---

## 附录 B · businessFlow BF 映射

| L2 | 聚合的 BF |
|---|---|
| L2-01 文档 I/O 编排器 | BF-L3-06（文档处理流） |
| L2-02 代码结构理解编排器 | BF-L3-07（代码读取与分析流） |
| L2-03 图片视觉理解编排器 | BF-L3-08（图片/截图分析流） |
| L2-04 路径安全与降级编排器（横切） | 横切 BF-L3-06 / 07 / 08 + BF-X-03（事件总线落盘流）+ BF-X-05（KB 注入策略 · 仅 L2-02 代码摘要入 KB 路径参与） |

**BF-L3-06 / 07 / 08 的路径锚点**（文字描述 · 不放算法图）：
- BF-L3-06 · 文档处理流：L2-04 守门 → L2-01 Read/Write/Edit → 结构化 sections / 写确认 · 大文件经 L2-01 分页循环
- BF-L3-07 · 代码读取与分析流：L2-04 守门 + 行数估算 → L2-02 Glob → Read 入口 → Grep 模式 → 组装摘要 → 写 KB · > 10 万行经 L2-02 → IC-12 → L1-05 子 Agent
- BF-L3-08 · 图片/截图分析流：L2-04 守门 + 格式 / 大小校验 → L2-03 Read 图 → Claude 视觉 → 按 hint 结构化 · 全程本地

**BF-X-03 横切**（事件总线落盘）：
- 全部 L2（尤其 L2-04 统一入口）每次 I/O 都落 IC-09 审计事件

---

*— L1-08 PRD v0.1（骨架 + 4 L2 产品级详细合一 · 无 L3 / 无 schema / 无 config）· 待 review + 进入 M5.5 清洗若发现越界即迁技术方案 —*
