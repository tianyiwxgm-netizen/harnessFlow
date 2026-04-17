#!/usr/bin/env bash
#
# harnessFlow 一键安装脚本（Phase 8 产出）
#
# 功能：
#   1. 注册 harnessFlow skill 到 .claude/skills/harnessFlow.md（符号链接）
#   2. 注册 4 个 subagent 到 .claude/agents/harnessFlow-*.md（符号链接）
#   3. 合并 2 个 hooks 到 .claude/settings.local.json（PostToolUse + Stop）
#   4. 安装 Python 依赖（jsonschema 等）
#
# 使用：
#   cd <project-root-where-harnessFlow-dir-lives>
#   bash "harnessFlow /setup.sh"
#
# 幂等：重复运行只会更新符号链接；不会重复合并 hook 数组。
#
# 退出码：
#   0 成功
#   1 前置条件缺失（harnessFlow/ 目录不存在等）
#   2 jq/python3 缺失
#   3 合并 settings.local.json 失败

set -eu

# --- 0. 定位 harnessFlow 目录（脚本所在目录） ---
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$HARNESS_DIR/.." && pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"

echo "[setup] harnessFlow dir: $HARNESS_DIR"
echo "[setup] project root:   $PROJECT_ROOT"

# --- 1. 前置检查 ---
for f in \
    "$HARNESS_DIR/harnessFlow-skill.md" \
    "$HARNESS_DIR/commands/harnessFlow.md" \
    "$HARNESS_DIR/subagents/supervisor.md" \
    "$HARNESS_DIR/subagents/verifier.md" \
    "$HARNESS_DIR/subagents/retro-generator.md" \
    "$HARNESS_DIR/subagents/failure-archive-writer.md" \
    "$HARNESS_DIR/hooks/PostToolUse-goal-drift-check.sh" \
    "$HARNESS_DIR/hooks/Stop-final-gate.sh"; do
  if [ ! -f "$f" ]; then
    echo "[setup] FATAL: missing $f" >&2
    exit 1
  fi
done

for cmd in jq python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[setup] FATAL: $cmd not installed" >&2
    exit 2
  fi
done

# --- 2. Python 依赖 ---
echo "[setup] installing python deps (jsonschema)..."
python3 -m pip install --quiet --user jsonschema 2>/dev/null || \
    python3 -m pip install --quiet --break-system-packages jsonschema 2>/dev/null || \
    echo "[setup] WARN: jsonschema install skipped (already installed or pip restricted)"

# --- 3. 创建 .claude/{skills,agents,commands}/ ---
mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/agents" "$CLAUDE_DIR/commands"

# --- 4a. 符号链接 skill（Assistant 用 Skill 工具调用）---
ln -sf "$HARNESS_DIR/harnessFlow-skill.md" "$CLAUDE_DIR/skills/harnessFlow.md"
echo "[setup] registered skill:   .claude/skills/harnessFlow.md -> harnessFlow-skill.md"

# --- 4b. 符号链接 slash command（用户打 /harnessFlow 触发）---
ln -sf "$HARNESS_DIR/commands/harnessFlow.md" "$CLAUDE_DIR/commands/harnessFlow.md"
echo "[setup] registered command: .claude/commands/harnessFlow.md -> commands/harnessFlow.md"

# --- 5. 符号链接 4 个 subagent ---
for name in supervisor verifier retro-generator failure-archive-writer; do
  ln -sf "$HARNESS_DIR/subagents/$name.md" "$CLAUDE_DIR/agents/harnessFlow-$name.md"
  echo "[setup] registered agent: .claude/agents/harnessFlow-$name.md"
done

# --- 6. 确保 hook 脚本可执行 ---
chmod +x "$HARNESS_DIR/hooks/PostToolUse-goal-drift-check.sh"
chmod +x "$HARNESS_DIR/hooks/Stop-final-gate.sh"

# --- 7. 合并 hooks 到 settings.local.json（幂等 jq 合并）---
SETTINGS="$CLAUDE_DIR/settings.local.json"
POST_HOOK_CMD="bash \"$HARNESS_DIR/hooks/PostToolUse-goal-drift-check.sh\""
STOP_HOOK_CMD="bash \"$HARNESS_DIR/hooks/Stop-final-gate.sh\""

if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

# 构造新 hooks 结构（幂等：存在则替换，不存在则加）
TMP_SETTINGS="$(mktemp)"
jq \
  --arg post_cmd "$POST_HOOK_CMD" \
  --arg stop_cmd "$STOP_HOOK_CMD" \
  '
  .hooks = (.hooks // {})
  | .hooks.PostToolUse = [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": $post_cmd,
        "timeout": 15
      }]
    }]
  | .hooks.Stop = [{
      "hooks": [{
        "type": "command",
        "command": $stop_cmd,
        "timeout": 30
      }]
    }]
  ' "$SETTINGS" > "$TMP_SETTINGS" || { echo "[setup] FATAL: jq merge failed" >&2; exit 3; }

mv "$TMP_SETTINGS" "$SETTINGS"
echo "[setup] hooks merged into $SETTINGS"

# --- 8. 自测：Stop hook 空 board 场景 ---
if bash "$HARNESS_DIR/hooks/Stop-final-gate.sh" < /dev/null >/dev/null 2>&1; then
  echo "[setup] Stop hook self-test: PASS"
else
  echo "[setup] WARN: Stop hook self-test failed (check harnessFlow/task-boards/ state)"
fi

# --- 9. 最终 summary ---
cat <<EOF

[setup] harnessFlow 安装完成 ✓

  Command: .claude/commands/harnessFlow.md  (用户打 /harnessFlow <args>)
  Skill:   .claude/skills/harnessFlow.md    (Assistant 用 Skill 工具调)
  Agents:  .claude/agents/harnessFlow-{supervisor,verifier,retro-generator,failure-archive-writer}.md
  Hooks:   .claude/settings.local.json#.hooks.{PostToolUse,Stop}

下一步：
  1. 重启 Claude Code（或运行 /hooks 命令让配置生效）
  2. 输入 /harnessFlow <任务描述> 激活主 skill
  3. 详细用法见 $HARNESS_DIR/README.md 和 $HARNESS_DIR/QUICKSTART.md

EOF
