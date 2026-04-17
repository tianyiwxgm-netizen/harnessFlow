# harnessFlow Claude Code Hooks

两个 hook 脚本，**默认 off**。启用前请确认你理解 Claude Code hooks 机制（见 [Claude Code 文档](https://docs.claude.com/claude-code/hooks)）。

## 脚本清单

| 脚本 | 触发时机 | 对应规则 | 失败行为 |
|---|---|---|---|
| `PostToolUse-goal-drift-check.sh` | Edit/Write CLAUDE.md 后 | state-machine § 5.4 运行时 goal drift 监控 | 非 0 exit → Claude Code 把 drift 事件呈现给主 skill |
| `Stop-final-gate.sh` | Claude Code session 结束前 | delivery-checklist § 7.2 Stop 门卫 | 非 0 exit → 提醒用户有未收口任务 |

## 启用方式

编辑 `~/.claude/settings.json`（或项目级 `.claude/settings.json`），加入：

```jsonc
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "path_matcher": ".*CLAUDE\\.md$",
        "command": "bash '/Users/zhongtianyi/work/code/harnessFlow /hooks/PostToolUse-goal-drift-check.sh'"
      }
    ],
    "Stop": [
      {
        "command": "bash '/Users/zhongtianyi/work/code/harnessFlow /hooks/Stop-final-gate.sh'"
      }
    ]
  }
}
```

> 注意路径里的空格 —— 目录名含尾部空格（`harnessFlow /`），必须加引号。

## 禁用方式

从 `settings.json` 删掉对应的 hook entry；脚本本身留着无副作用。

## 依赖

- `bash` 4+
- `python3`
- `shasum` (macOS) / `sha256sum` (Linux，需改脚本)
- 只读 `harnessFlow /task-boards/` / `supervisor-events/` / `retros/` 三个目录

## 故障排查

- **hook 一直 exit 2 但看不到 evidence**：检查 `supervisor-events/<task_id>.jsonl` 最后一行，里面有详细字段
- **有多个 active task-board 时 PostToolUse hook 跳过**：这是 v1 MVP 的限制（见脚本注释）；Phase 7+ 会扩展
- **Stop hook 阻止了正常关闭**：先检查 `task-boards/*.json` 的 `current_state`；把未收口任务显式推到 PAUSED_ESCALATED 或 ABORTED 再停

## v1 已知限制

1. 同一项目同时只支持 1 个 active task（多任务识别由 Phase 7 支持）
2. hook 里不自动写 task-board（避免和主 skill/Supervisor 竞争锁）；只 append supervisor-events
3. Stop hook 不自动拉起 failure-archive-writer（用户自行决定是否归档）
