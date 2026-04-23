---
doc_id: code-ownership-matrix-v1.0
doc_type: code-ownership-matrix
parent_doc:
  - docs/MASTER-SESSION-DISPATCH.md
  - docs/4-exe-plan/4-0-master-execution-plan.md
version: v1.0
status: active
maintainer: 主会话
updated_at: 2026-04-23
---

# CODE-OWNERSHIP-MATRIX · 代码所有权矩阵（8 Dev 并发防冲突）

> **目的**：各 Dev 会话并发开发时 · 明确**能动哪些目录** / **不能碰哪些**。
>
> **铁律**：
> 1. 各 Dev **只写自己 L1 的目录**（下表绿色列）
> 2. 跨 L1 发现 bug → **只读 · 不改** · 走 `4-0 §6` 情形 D 仲裁
> 3. 共享文件（pyproject / conftest / scripts · 下表黄色）→ **冻结 · 找主会话**
> 4. 文档目录（docs / · 下表灰色）→ **只主会话改** · 各 Dev 不写 docs

---

## §1 每 Dev 会话的专属代码包

| Dev | L1 | **专属目录（可写）** | 冲突风险 |
|:---:|:---:|:---|:---:|
| Dev-α | L1-09 | `app/l1_09/**` · `tests/l1_09/**` · `tests/unit/l1_09/**` | 🟢 低 |
| Dev-β | L1-06 | `app/l1_06/**` · `tests/l1_06/**` · `tests/unit/l1_06/**` | 🟢 低 |
| Dev-γ | L1-05 | `app/l1_05/**` · `tests/l1_05/**` · `tests/unit/l1_05/**` | 🟢 低 |
| Dev-δ | L1-02 | `app/l1_02/**` · `tests/l1_02/**` · `tests/unit/l1_02/**` | 🟢 低（已存在基础骨架）|
| Dev-ε | L1-03 | `app/l1_03/**` · `tests/l1_03/**` · `tests/unit/l1_03/**` | 🟢 低 |
| Dev-ζ | L1-07 | `app/l1_07/**` · `tests/l1_07/**` · `tests/unit/l1_07/**` | 🟢 低 |
| Dev-η | L1-08 | `app/l1_08/**` · `tests/l1_08/**` · `tests/unit/l1_08/**` | 🟢 低 |
| Dev-θ | L1-10 | `app/l1_10/**` · `tests/l1_10/**` · `tests/unit/l1_10/**` · `frontend/**`（Vue）· `bff/**`（FastAPI BFF）| 🟡 中（frontend 独立子树）|

**创建目录自由**：若自己 L1 目录不存在 · Dev 自己 `mkdir` · 不需要主会话。

---

## §2 共享区（🟡 · 冻结 · 需协调）

### 2.1 依赖文件 · 所有会话都要加依赖

| 文件 | 风险 | 协调方式 |
|:---:|:---:|:---|
| `pyproject.toml` | 🔴 高（8 会话同时改 → 必冲突）| **只通过 PR 到主会话 · 主会话合并**。各 Dev 在会话内**先通过 pip 装** · 末期才提交 pyproject 变更 |
| `requirements.txt`（如有）| 🔴 高 | 同上 |
| `.env.example` | 🟡 中 | 各 Dev 在自己 L1 小节追加（例如 `# L1-09 ===` block）· 主会话合并 |
| `package.json`（frontend）| 🟢 低 | 仅 Dev-θ 动 |

**操作方式**：
- 各 Dev 会话在 venv 内 `pip install <pkg>` · 不急着改 pyproject
- 每晚主会话收集各 Dev 报的依赖清单 · 统一 commit pyproject

### 2.2 共享测试基础设施

| 文件 | 谁能改 |
|:---:|:---|
| `tests/__init__.py` | 不动（空）|
| `tests/conftest.py`（根 conftest）| **主会话独占** · Dev 需要共享 fixture → 报主会话 |
| `tests/shared/**`（如 project_factory / e2e_harness）| **main-3 独占**（波 6） · 现在各 Dev **不改**|
| `tests/l1_XX/conftest.py`（L1 本地 conftest）| 对应 Dev 可自由改 |

### 2.3 共享脚本 · `scripts/`

| 文件 | 谁能改 |
|:---:|:---|
| `scripts/quality_gate.sh` | **主会话独占** |
| 其他现有 scripts | **冻结 · 只读** |
| 新脚本（Dev 自用）| 自己 L1 的 `app/l1_XX/scripts/` 下 · 不放到根 `scripts/` |

### 2.4 根级 Python 包

| 文件 | 谁能改 |
|:---:|:---|
| `app/__init__.py` | **主会话独占** · 用于 L1 注册 |
| `app/registry.py`（如有）| **主会话独占** |
| 各 L1 内部 `app/l1_XX/__init__.py` | 对应 Dev 自由 |

---

## §3 只读区（🔴 · 绝对不改）

| 路径 | 理由 |
|:---:|:---|
| `docs/**` | 源文档 · 只主会话改（走 §6 自修正） |
| 其他 L1 的 `app/l1_YY/**` | 不许越界 · 有 bug → 报主会话（情形 D） |
| `archive/**` | 历史版本 · 冻结 |
| `.claude/**` | 平台配置 · 不动 |
| `.git/**` | git 内部 |
| `.venv/**` | 虚拟环境 |

---

## §4 跨 L1 消费（只读 · 通过 IC 契约）

每个 L1 必定**消费**其他 L1 的输出 · 但**不读源码** · 只通过 IC 契约接口（mock 或真实 stub）：

| 消费方 | 被消费的 L1 | 通过 IC | 做法 |
|:---:|:---|:---|:---|
| 所有 L1 | L1-09 events_append | IC-09 | 波 1 前用 mock · 波 1 后可真实 |
| L1-01~03 | L1-06 kb_read | IC-06 | mock / 真实 stub |
| L1-01 | L1-02 state_transition | IC-01 | mock / 真实 |
| L1-01 | L1-05 invoke_skill | IC-04 | mock / 真实 |
| L1-07 | L1-01 halt | IC-15 | mock · 主-2 真实 |
| ... | ... | ... | 见 ic-contracts.md §3.1-§3.20 |

**铁律**：消费其他 L1 时 · **只 import 该 L1 暴露的公开 IC 接口** · **不碰内部实现**。

---

## §5 冲突处理 SOP

### 5.1 发现冲突时怎么办

**情形 A · 自己写的文件其他会话也改了**：
- `git pull` 前冻结 · 本地 commit 先打标
- `git pull` · 遇 conflict → **不自动解** · 报主会话仲裁
- 主会话用 PR 方式逐一合并

**情形 B · 你需要改共享文件（pyproject / conftest）**：
- 冻结 · 不自己动
- 在 standup log 里报："需加依赖 X" / "需共享 fixture Y"
- 主会话每日收集 · 统一改

**情形 C · 你发现其他 L1 有 bug**：
- 不改对方代码
- 报主会话 · 走情形 D 仲裁
- 主会话开 main-X 会话（或让原 Dev 修）

### 5.2 commit 策略

- 各 Dev **在自己分支**工作（推荐）: `git checkout -b dev-α-l1-09`
- 频繁提交 · 但**不 push 到 main**
- 每日 standup 后 · push 到自己分支 · **主会话 merge 到 main**

**如果坚持直接 push main**（不推荐）：
- 每次 push 前：`git pull --rebase` · 解本地冲突
- 只 commit 自己 L1 目录 · 不 `git add -A`

---

## §6 目录初始化模板（各 Dev 第一步做）

每个 Dev 会话开第一步:

```bash
# 1. 新分支（强烈推荐）
git checkout -b dev-<你的名>-l1-<数字>   # 例如 dev-α-l1-09

# 2. 建自己的目录
mkdir -p app/l1_XX/{__init__.py,...}    # 按 md §3 WP 拆解的子模块
mkdir -p tests/l1_XX/unit
mkdir -p tests/l1_XX/integration
touch app/l1_XX/__init__.py
touch tests/l1_XX/__init__.py
touch tests/l1_XX/conftest.py

# 3. 标记工作空间
echo "Dev-<你的名> · L1-XX · 2026-04-23" > app/l1_XX/OWNERSHIP.md

# 4. 确认专属目录
ls app/l1_XX
```

---

## §7 文件锁定状态（主会话维护 · 每日更新）

> 表示当前**哪些文件正在被哪个 Dev 改**。若你想改 · 查此表。

| 路径 | 占用者 | 占用时间 | 预计释放 |
|:---|:---:|:---:|:---:|
| `app/l1_09/**` | Dev-α | 2026-04-23 | 2026-04-30 |
| `app/l1_06/**` | Dev-β | 2026-04-23 | 2026-04-30 |
| `app/l1_05/**` | Dev-γ | 2026-04-23 | 2026-04-28 |
| `app/l1_02/**` | Dev-δ | 2026-04-23 | 2026-04-30 |
| `app/l1_03/**` | Dev-ε | 2026-04-23 | 2026-04-28 |
| `app/l1_07/**` | Dev-ζ | 2026-04-23 | 2026-05-01 |
| `app/l1_08/**` | Dev-η | 2026-04-23 | 2026-04-29 |
| `app/l1_10/**` + `frontend/**` + `bff/**` | Dev-θ | 2026-04-23 | 2026-05-02 |
| `pyproject.toml` | **主会话合并期** | 夜晚 | 每日 |
| `tests/shared/**` | **冻结（main-3 波 6）** | - | 2026-06-10 |
| `docs/**` | **主会话独占** | 持续 | - |

---

## §8 快速查阅 · 一图流

```
harnessFlow/
├── app/
│   ├── __init__.py           🔴 主会话独占
│   ├── l1_01/                 ⏸️  波 5 main-2 才写
│   ├── l1_02/                 🟢 Dev-δ 专属
│   ├── l1_03/                 🟢 Dev-ε 专属
│   ├── l1_04/                 ⏸️  波 4 main-1 才写
│   ├── l1_05/                 🟢 Dev-γ 专属
│   ├── l1_06/                 🟢 Dev-β 专属
│   ├── l1_07/                 🟢 Dev-ζ 专属
│   ├── l1_08/                 🟢 Dev-η 专属
│   ├── l1_09/                 🟢 Dev-α 专属
│   └── l1_10/                 🟢 Dev-θ 专属
├── frontend/                  🟢 Dev-θ 专属
├── bff/                       🟢 Dev-θ 专属
├── tests/
│   ├── conftest.py            🔴 主会话独占
│   ├── shared/                ⏸️  冻结（main-3）
│   ├── l1_02/~l1_10/          🟢 对应 Dev 专属
│   ├── integration/           ⏸️  冻结（main-3）
│   └── acceptance/            ⏸️  冻结（main-3）
├── scripts/
│   ├── quality_gate.sh        🔴 主会话独占
│   └── (其他)                 ⚪ 冻结只读
├── docs/                      🔴 主会话独占
├── pyproject.toml             🔴 每晚主会话合并
├── .env.example               🟡 Dev 追加小节 · 主合并
└── archive/                   ⚪ 冻结只读
```

图例：🟢 可写 · 🟡 协调 · 🔴 主会话独占 · ⏸️ 延后 · ⚪ 只读

---

*— CODE-OWNERSHIP-MATRIX · v1.0 · 主会话维护 · 冲突第一锚 —*
