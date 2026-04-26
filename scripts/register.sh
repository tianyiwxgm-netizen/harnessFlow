#!/usr/bin/env bash
#
# register.sh — 把 harnessFlow 的 slash commands + skill + subagents
#               注册到用户全局 ~/.claude/，使其在任何项目里都可用。
#
# 用法：
#   bash scripts/register.sh
#
# 注册后可在任意 Claude Code 项目里使用：
#   /harnessFlow <任务描述>
#   /harnessFlow-ui

set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_USER="$HOME/.claude"

echo "[register] harnessFlow: $HARNESS_DIR"
echo "[register] user .claude: $CLAUDE_USER"
echo ""

# ── 1. 全局 slash commands ──────────────────────────────────────────────────
mkdir -p "$CLAUDE_USER/commands"
ln -sf "$HARNESS_DIR/.claude/commands/harnessFlow.md"    "$CLAUDE_USER/commands/harnessFlow.md"
ln -sf "$HARNESS_DIR/.claude/commands/harnessFlow-ui.md" "$CLAUDE_USER/commands/harnessFlow-ui.md"
echo "  [OK] commands: /harnessFlow · /harnessFlow-ui → ~/.claude/commands/"

# ── 2. 全局 skill（Skill tool 可通过 skill="harnessFlow" 调用）──────────────
mkdir -p "$CLAUDE_USER/skills/harnessFlow"
ln -sf "$HARNESS_DIR/harnessFlow-skill.md" "$CLAUDE_USER/skills/harnessFlow/SKILL.md"
echo "  [OK] skill: harnessFlow → ~/.claude/skills/harnessFlow/SKILL.md"

# ── 3. 项目级 subagents（Agent(subagent_type="harnessFlow:*") 需要）─────────
mkdir -p "$HARNESS_DIR/.claude/agents"
for name in supervisor verifier retro-generator failure-archive-writer; do
  ln -sf "../../subagents/$name.md" "$HARNESS_DIR/.claude/agents/harnessFlow-$name.md"
done
echo "  [OK] agents: supervisor · verifier · retro-generator · failure-archive-writer"

# ── 4. 项目级 skill symlink（self-test 检查用）──────────────────────────────
mkdir -p "$HARNESS_DIR/.claude/skills"
ln -sf "../../harnessFlow-skill.md" "$HARNESS_DIR/.claude/skills/harnessFlow.md"
echo "  [OK] project skill symlink: .claude/skills/harnessFlow.md"

echo ""
echo "[register] Done. 验证："
echo "  bash scripts/self-test.sh"
echo ""
echo "  注意：hooks (PostToolUse / Stop) 需要在 .claude/settings.local.json"
echo "  自行添加，或参考 hooks/README.md。"
