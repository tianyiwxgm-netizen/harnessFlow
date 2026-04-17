# harnessFlow QUICKSTART — 5 分钟跑通

## 前置

- macOS / Linux shell
- Python 3.10+
- `jq`（`brew install jq` 或 `apt install jq`）
- Claude Code（CLI 或 VSCode 扩展）

## 1 分钟安装

```bash
cd <含 harnessFlow/ 目录的项目根>
bash "harnessFlow /setup.sh"
```

看到 `[setup] harnessFlow 安装完成 ✓` 即成功。重启 Claude Code（或在 Claude Code 里执行 `/hooks` 命令重载配置）。

**自动完成的事**：
- `.claude/skills/harnessFlow.md` ← 软链到 `harnessFlow /harnessFlow-skill.md`
- `.claude/agents/harnessFlow-{supervisor,verifier,retro-generator,failure-archive-writer}.md` ← 4 个软链
- `.claude/settings.local.json#.hooks` ← 合并 PostToolUse（goal-drift 检测）+ Stop（终态门卫）两个 hook
- `pip install jsonschema`（已装则跳过）

## 2 分钟跑第一个任务

在 Claude Code 里输入：

```
/harnessFlow 给 aigc/frontend/src/views/Dashboard.vue 加一个"Phase 8 验证入口"按钮，点击跳转到 /phase8-status 新页面
```

主 skill 会做：

1. **2-3 轮澄清**：问你目标 / 验收标准 / 风险边界
2. **识别三维**：`(size=M, task_type=UI页面, risk=可逆)`
3. **查 matrix 推荐 Top-2 路线**：例如 "推荐 D（UI 视觉专线）或 B（轻 PRP）"
4. **等你选**
5. **Spawn Supervisor** 开始侧挂监听
6. **按所选路线调度既有 skill** 做实际工作
7. **Spawn Verifier** 跑 DoD 布尔表达式（`dev_server_up` + `playwright_exit_code==0` + `screenshot_has_content` + `browser_console_errors_count==0`）
8. **PASS 后走 RETRO_CLOSE**：自动产 11 段 retro + 追加 failure-archive.jsonl
9. **Stop hook 校验** → `CLOSED`

## 3 分钟读产物

任务收口后，下列目录有产物：

| 产物 | 位置 | 看什么 |
|---|---|---|
| task-board | `harnessFlow /task-boards/<task_id>.json` | `.current_state` / `.final_outcome` / `.verifier_report.verdict` / `.retro_link` / `.archive_entry_link` |
| verifier 独立报告 | `harnessFlow /verifier_reports/<task_id>.json` | `.verdict` / `.failed_conditions` / `.evidence_chain.{existence,behavior,quality}` |
| 11 段 retro | `harnessFlow /retros/<task_id>.md` | `grep "^## " <file>` 应 ≥ 11 段 |
| 结构化归档 | `harnessFlow /failure-archive.jsonl`（最后一行） | `tail -1 <file> \| jq` 看 error_type / missing_subcontract / frequency / root_cause |

## 常见问题

### Q1: `/harnessFlow` 没反应

- 原因：Claude Code 未识别新 skill 或 symlink 坏了
- 验证：`ls -la .claude/skills/harnessFlow.md` 应显示 symlink 到 `harnessFlow-skill.md`
- 修法：在 Claude Code 里运行 `/hooks` 重载；或重启 Claude Code

### Q2: Stop hook 报 `task <id>: retro missing`

- 原因：非 A 路线收口但未产 retro
- 验证：`cat harnessFlow\ /task-boards/<id>.json | jq '.route_id'`，不是 A
- 修法：主 skill 流程有 bug → 查 harnessFlow-skill.md § 8.6；或改 task-board `route_id=A`（仅 XS + 可逆适用）

### Q3: Verifier 一直返 `INSUFFICIENT_EVIDENCE`

- 原因：DoD 表达式里的 primitive 没返回明确布尔值（如 `oss_head()` 网络问题）
- 验证：看 `verifier_reports/<id>.json .evidence_chain.{existence,behavior,quality}` 里哪些条目 `result: null`
- 修法：补 evidence / 改 DoD 表达式 / 升级 primitive 错误处理（`insufficient_evidence_count` cap=2 → IMPL↔VERIFY 死循环自动打破进 PAUSED）

### Q4: 想跳过 retro 怎么办

- 唯一豁免：`route=A` 且 `size=XS`（delivery-checklist § 7.2 carve-out）
- 其他情况不可绕开——这是 harnessFlow 防"假完成"的核心机制

### Q5: auditor 会自动改 routing-matrix 吗

- **不会**。`archive/auditor.py::audit()` 只写 `audit-reports/audit-*.json` 建议文件，**永不写** `routing-matrix.json`（method3 § 7.3 进化边界硬线）
- 路线权重变更须人审批后手动改 matrix（推荐走 PR）

## 卸载

```bash
rm .claude/skills/harnessFlow.md
rm .claude/agents/harnessFlow-*.md
# 手动从 .claude/settings.local.json 的 .hooks.{PostToolUse,Stop} 里移除 harnessFlow 相关条目
```

## 下一步

- 看 [README.md](README.md) 了解架构和设计 bet
- 看 [harnessFlow-skill.md](harnessFlow-skill.md) 了解主 skill prompt 完整逻辑
- 看 [flow-catalog.md](flow-catalog.md) 了解 6 路线各自的调度顺序
- 看 [method3.md § 8](method3.md) 了解 10 条反模式（避免触发）
