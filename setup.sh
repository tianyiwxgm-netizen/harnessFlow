#!/usr/bin/env bash
#
# harnessFlow 一键安装脚本（Phase 8 产出；Phase 9 增强依赖自检）
#
# 功能：
#   1. 注册 harnessFlow skill 到 .claude/skills/harnessFlow.md（符号链接）
#   2. 注册 4 个 subagent 到 .claude/agents/harnessFlow-*.md（符号链接）
#   3. 合并 2 个 hooks 到 .claude/settings.local.json（PostToolUse + Stop）
#   4. 安装 Python 依赖（jsonschema 等）
#   5. 【新】自检 3 个依赖 skill 生态（Superpowers / everything-claude-code / gstack），
#      缺失 → 主动安装（能通过 `claude plugin install` 的）或打印手工安装指令
#
# 使用：
#   cd <project-root-where-harnessFlow-dir-lives>
#   bash "harnessFlow /setup.sh"
#
# 幂等：重复运行只会更新符号链接；不会重复合并 hook 数组；依赖已装则跳过。
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

# --- 2.5 依赖 skill 生态自检（Superpowers / everything-claude-code / gstack） ---
#
# harnessFlow 是**纯编排器**，自身只 orchestrate、不造轮。下游调度依赖 3 大 skill 生态：
#   - Superpowers (SP)                 —— brainstorming / executing-plans / verification-before-completion ...
#   - everything-claude-code (ECC)     —— prp-prd / prp-plan / prp-implement / code-reviewer / retro / save-session ...
#   - gstack                           —— autoplan / browse / canary / careful / ship / ...
#
# 任一缺失 → harnessFlow 路线 A-F 会 degrade 或直接 fail。
# 本段做 best-effort 自检 + 自动安装（能通过 `claude plugin install` 的 2 个）+
# 对 gstack 打印手工安装指令（gstack 未走 plugin marketplace 协议，因地制宜）。

echo ""
echo "[setup] 依赖 skill 自检 (SP / ECC / gstack) ..."

HAS_CLAUDE_CLI=0
if command -v claude >/dev/null 2>&1; then
  HAS_CLAUDE_CLI=1
fi

# 辅助：检测 claude plugin 是否已装
_plugin_installed() {
  local full_id="$1"  # e.g. superpowers@claude-plugins-official
  [ "$HAS_CLAUDE_CLI" = "1" ] || return 1
  claude plugin list 2>/dev/null | grep -qE "^[[:space:]]*[^[:space:]]+[[:space:]]+${full_id//./\\.}([[:space:]]|$)" \
    || claude plugin list 2>/dev/null | grep -qE "${full_id//./\\.}"
}

# 辅助：装 claude plugin（失败不阻断整个 setup）
_plugin_install() {
  local full_id="$1"
  if [ "$HAS_CLAUDE_CLI" != "1" ]; then
    echo "[setup]   WARN: claude CLI 不存在，跳过 $full_id 的自动安装"
    echo "[setup]         请先装 Claude Code CLI，再跑:  claude plugin install $full_id"
    return 1
  fi
  echo "[setup]   attempting: claude plugin install $full_id"
  if claude plugin install "$full_id" 2>&1 | tail -3; then
    echo "[setup]   installed: $full_id"
    return 0
  else
    echo "[setup]   WARN: 自动装 $full_id 失败，请手工跑: claude plugin install $full_id"
    return 1
  fi
}

# 2.5a) Superpowers
SP_ID="superpowers@claude-plugins-official"
if _plugin_installed "$SP_ID"; then
  echo "[setup]   ✓ Superpowers 已装"
else
  echo "[setup]   ✗ Superpowers 缺失 — harnessFlow B/C/D/E/F 路线的 CLARIFY / VERIFY / retro 步依赖 SP:brainstorming 等"
  _plugin_install "$SP_ID" || true
fi

# 2.5b) everything-claude-code
ECC_ID="everything-claude-code@everything-claude-code"
if _plugin_installed "$ECC_ID"; then
  echo "[setup]   ✓ everything-claude-code 已装"
else
  echo "[setup]   ✗ everything-claude-code 缺失 — harnessFlow 所有路线的 prp-plan / prp-implement / code-reviewer / retro / save-session 步依赖 ECC"
  _plugin_install "$ECC_ID" || true
fi

# 2.5c) gstack（不走 plugin marketplace；以 ~/.claude/skills/autoplan 作为签名 skill 检测）
if [ -f "$HOME/.claude/skills/autoplan/SKILL.md" ] || [ -f "$HOME/.claude/skills/ship/SKILL.md" ]; then
  echo "[setup]   ✓ gstack 已装（检测到 ~/.claude/skills/autoplan 或 /ship）"
else
  echo "[setup]   ✗ gstack 缺失 — harnessFlow 的 ship / qa / review / careful / browse 等路线步依赖 gstack"
  echo "[setup]     gstack 未走 claude plugin marketplace 协议，请按以下之一手动安装："
  echo "[setup]       • curl -fsSL https://gstack.dev/install.sh | bash"
  echo "[setup]       • 或 git clone https://github.com/gstack/skills ~/.claude/skills-gstack && cp -r ~/.claude/skills-gstack/* ~/.claude/skills/"
  echo "[setup]     （具体命令以 gstack 官方 README 为准，装完重跑本脚本确认）"
fi

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
