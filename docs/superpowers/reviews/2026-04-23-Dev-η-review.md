---
review_target: Dev-η · L1-08 多模态内容处理
branch: feat/dev-eta-l1-08 @ 48454b0c
reviewer: 主会话（轻量 review · 前置 agent 遇 rate limit）
reviewed_at: 2026-04-23
files: 52 · 4321 insertions · 31 src + 15 tests
---

# Dev-η L1-08 Code Review · 2026-04-23（主会话轻量版）

## Verdict

**REQUEST_CHANGES** · 1 P1 真 bug 必修 · 1 P1 SLO 待验证 · 其余 P2/P3 建议改 · 包结构与安全边界整体过关。

---

## 前提声明

前置派出的 python-reviewer agent 遇 Claude rate limit 未产出完整报告。本报告由主会话亲读 5 个关键文件（ic_12_delegator / pid_guard / path_safety/facade / symlink_detector / event_bus_stub）+ git diff --stat 得出 · **未遍历全 31 src + 15 test**。Dev-η 下轮可在 rate limit 恢复后请求完整深度 review。

---

## 亮点（值得保留）

1. **IC-12 delegator 用 Protocol**（`L1_05_Client` Protocol）· dependency inversion 干净 · 比 Dev-ζ 的具体 Stub 类型标注更优
2. **PM-14 `pid_guard.py`** 只 14 行 · 清晰：empty raise + 跨 pid raise · 无歧义
3. **PathSafetyFacade 主入口**：HALTED guard → whitelist → symlink → os.stat (FileNotFound/Permission/NotAFile) → binary sniff → route → dispatch → audit · 层次清晰 · 错误映射 L2-04 → IC-11 (`_L2_04_TO_IC_11` 表) 与 ic-contracts §3.11.4 对齐
4. **SymlinkCycleDetector** MAX_DEPTH=8 + visited set · 手动 walk 避免 `resolve()` 一次性爆炸风险
5. **`EventBusStub.append_event(event: dict)` 泛型签名** · 不像 Dev-ε 绑死 event_type/content 参数 · 未来 swap 真实 IC-09 时零调用点改动 ✅

---

## 问题清单

### P1-01 · IC-12 `ts` 硬编码 timestamp（真 bug · 必修）

**位置**：`app/multimodal/ic_12_delegator.py` line ~46

```python
cmd: dict[str, Any] = {
    "delegation_id": delegation_id,
    "project_id": project_id,
    ...
    "ts": "2026-04-23T00:00:00Z",   # ❌ 硬编码 · 永远是 2026-04-23
}
```

**影响**：
- 审计链所有 IC-12 事件 ts 都相同 · 无法排序 · 违反 L1-09 事件可追溯原则
- 跨 day 调用时 · ts 不反映实际时间 · 问题排查时误导

**修复**：
```python
from datetime import datetime, timezone
...
"ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
```

### P1-02 · IC-12 dispatch 超时 2.0s · 未验证 ≤200ms SLO（待验证）

**位置**：`app/multimodal/ic_12_delegator.py`

```python
dispatch = await asyncio.wait_for(
    client.dispatch_codebase_onboarding(cmd), timeout=2.0
)
```

**问题**：
- Dev-η 自报 "dispatch ≤ 200ms 验证过" · 但代码 timeout 是 **2.0 秒**（宽松 10×）
- 没有 pytest-benchmark 验证 P99 ≤ 200ms 的迹象（`tests/multimodal/perf/` 目录存在但内容未核实）

**要求**：
- 确认 `tests/multimodal/integration/test_ic_12_delegator.py` 或 `tests/multimodal/perf/` 有 SLO benchmark
- 若无 · 下轮补 · 参考 ic-contracts §3.12 SLA 字段

### P2-01 · `_estimate_loc` 目录返回 0（已知 WP-03 债）

**位置**：`app/multimodal/path_safety/facade.py`

```python
def _estimate_loc(path: Path) -> int:
    if path.is_dir():
        return 0  # WP-01: we don't walk. Return 0 so small repos go DIRECT. WP-03 will replace.
```

**状态**：代码注释已标 · 但 WP-03 已关闭 · 这段是否已在 code_structure/ 接管？需核实。若未 · 下轮处理。

### P2-02 · binary sniff 只查 NUL 字节

`_looks_binary` 读 512 字节查 `\x00` · 会漏掉一些特殊编码（UTF-16 BOM · 某些 binary format 开头无 NUL）· 当前为 md 路径的兜底 · 风险可接受但可改进（magic byte table）。

### P2-03 · 错误处理 `raise X` 未用 `raise X from e`（B904 · 已知）

Dev-η 自报 50 ruff warnings 含 B904 × 16 · 不改异常链会让 traceback 丢失原因。**建议下轮批量 `from e` 修**。

### P3-01 · `import stat as _stat` 函数内 import

`path_safety/facade.py` 在 `handle_process_content` 内部 `import stat as _stat` · 惯例是文件顶部 · 除非为解循环依赖。可挪顶部。

### P3-02 · `_BINARY_SNIFF_BYTES = 512` 常量作用域

放模块级 · 调用时若改成 class 常量或 dataclass field 更明确（非必改）。

---

## 安全性（L1-08 高风险面）· 速评

| 维度 | 评估 | 备注 |
|:---:|:---:|:---|
| 路径逃逸 (`../`) | ✅ 通过 whitelist validator | facade 第一道门 |
| symlink loop | ✅ MAX_DEPTH=8 + visited set | 手动 walk · 不一次性 resolve |
| 绝对路径 | 需核实 whitelist.validate 逻辑 | 未读 · 本轮未覆盖 |
| 设备文件 /dev/null | 需核实 | 未读 os.stat 对 S_ISCHR 等的判定 |
| tree-sitter CVE | 未核实 | 5 种 language binding · 版本 pin 见 pyproject 合并时验证 |
| VLM 降级链 | 未核实 | VLMInvoker → OCR → 规则 · 各级失败隔离度需 agent 深度审 |

**建议**：下轮 rate limit 恢复 · 补安全专项 review（symlink 全集 · device file · tree-sitter CVE 查 pypi）。

---

## 契约对齐（抽检）

| IC | 抽检结果 |
|:---:|:---|
| IC-11 `process_content` | `ProcessContentCommand/Result` schemas 存在 · 字段逐字段对齐未核实（未读 schemas.py） |
| IC-12 `delegate_codebase_onboarding` | cmd 结构含 `delegation_id` + `project_id` + `repo_path` + `kb_write_back` + `timeout_s` + `ts` + `focus.interfaces` · 与 §3.12 大致对齐 · 但 P1-01 ts bug |

---

## 合并依赖清单（交主会话 pyproject.toml 合并）

```toml
[project.dependencies]
tree-sitter = ">=0.25,<1.0"
tree-sitter-python = "*"       # 请 pin 具体 version（主会话合并时查最新稳定版）
tree-sitter-typescript = "*"
tree-sitter-go = "*"
tree-sitter-rust = "*"
tree-sitter-java = "*"
python-frontmatter = "*"
Pillow = "*"                   # CVE surface · pin ≥ 最近 LTS
pytesseract = "*"              # 需 tesseract binary · 文档提示
```

**主会话合并时**：
1. 每 dep 查 pypi 最新稳定 · pin minor（`^10.2`）
2. `pip-audit` 扫 CVE · 有 HIGH 换版本
3. Pillow 尤其注意 · 有频繁 CVE 历史

---

## Merge 建议

1. **Dev-η 下轮改 P1-01**（ts 硬编码 · 10 min 就能修）
2. 确认 P1-02 SLO bench 存在 · 否则补
3. P2-03（B904）批量修（ruff `--fix` 或半自动）
4. 其他 P2/P3 按优先级下轮处理
5. 改完再 `git push origin feat/dev-eta-l1-08` · 主会话开 PR 到 main

---

## 给 Dev-η 下轮的消息

```
主会话轻量 review 完（agent rate limit · 下轮可深度 review）
报告：docs/superpowers/reviews/2026-04-23-Dev-η-review.md

必修：
- P1-01 · ic_12_delegator.py ts 硬编码 · 改 datetime.now(timezone.utc).isoformat()
- P1-02 · 核实 IC-12 dispatch P99 ≤200ms 有 pytest-benchmark · 没有就补

建议批量改：
- P2-03 · 16 个 B904 raise-from · ruff --fix / 手动

改完 push feat/dev-eta-l1-08 · 主会话 PR 合 main。
深度 review 下一会话 rate limit 恢复后补。
```

---

*— Dev-η review · 2026-04-23 · 主会话轻量版（agent rate limit fallback）—*
