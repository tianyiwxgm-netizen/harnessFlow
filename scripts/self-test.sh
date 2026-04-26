#!/usr/bin/env bash
#
# harnessFlow self-test — 验证安装完整性 + 回归测试。
#
# 用途（Phase 8.1 产出）：
#   - setup.sh 跑完后一键确认 skill / agents / hooks / Python 依赖 / pytest 全部到位
#   - CI 场景可作 smoke test（exit 0 即健康）
#
# 使用：
#   bash "harnessFlow /scripts/self-test.sh"
#
# 退出码：
#   0  全部 PASS
#   N  有 N 项 FAIL
#
# 6 个检查模块（与 plan Task 8.1.2 对齐）：
#   1. setup.sh 跑过（skill symlink）
#   2. 4 个 subagent 软链 + name 字段匹配
#   3. hooks 在 settings.local.json 注册 + 命令路径存在
#   4. python3 + jsonschema
#   5. pytest 全绿（85 个）
#   6. auditor 不改 routing-matrix（进化边界硬线抽查）

set -u
# 不 set -e：我们要继续跑完所有模块再退出
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$HARNESS_DIR/.." && pwd)"
# standalone repo: .claude/ is inside the repo; parent-repo: .claude/ is one level up
if [ -d "$HARNESS_DIR/.claude" ]; then
  CLAUDE_DIR="$HARNESS_DIR/.claude"
else
  CLAUDE_DIR="$PROJECT_ROOT/.claude"
fi

pass=0
fail=0

_pass() { printf "  \033[32m[PASS]\033[0m %s\n" "$1"; pass=$((pass + 1)); }
_fail() { printf "  \033[31m[FAIL]\033[0m %s\n" "$1"; fail=$((fail + 1)); }

echo "[self-test] harnessFlow: $HARNESS_DIR"
echo "[self-test] project:     $PROJECT_ROOT"
echo ""

# === 模块 1: setup.sh 已跑（skill + command symlinks）===
echo "[1/6] setup.sh 已跑（skill + slash-command symlinks）"
if [ -L "$CLAUDE_DIR/skills/harnessFlow.md" ]; then
  target="$(readlink "$CLAUDE_DIR/skills/harnessFlow.md")"
  if [ -f "$target" ]; then
    _pass "skill symlink -> $target"
  else
    _fail "skill symlink target missing: $target"
  fi
else
  _fail ".claude/skills/harnessFlow.md not a symlink (run setup.sh?)"
fi

if [ -L "$CLAUDE_DIR/commands/harnessFlow.md" ]; then
  target="$(readlink "$CLAUDE_DIR/commands/harnessFlow.md")"
  if [ -f "$target" ]; then
    _pass "slash-command symlink -> $target (用户打 /harnessFlow 触发入口)"
  else
    _fail "command symlink target missing: $target"
  fi
elif [ -f "$CLAUDE_DIR/commands/harnessFlow.md" ]; then
  _pass ".claude/commands/harnessFlow.md (standalone repo real file · /harnessFlow 已注册)"
else
  _fail ".claude/commands/harnessFlow.md missing — /harnessFlow 将被 Claude Code 报 Unknown command"
fi

# === 模块 2: 4 个 subagent 软链 + name 字段 ===
echo ""
echo "[2/6] subagent 软链 + name 字段"
for name in supervisor verifier retro-generator failure-archive-writer; do
  link="$CLAUDE_DIR/agents/harnessFlow-$name.md"
  if [ ! -L "$link" ]; then
    _fail "agent symlink missing: $link"
    continue
  fi
  target="$(readlink "$link")"
  if [ ! -f "$target" ]; then
    _fail "agent target missing: $target"
    continue
  fi
  expected_name="harnessFlow:$name"
  # 读 frontmatter name 字段（前 20 行内）
  actual_name="$(head -20 "$target" | grep -E '^name:' | head -1 | awk -F': ' '{print $2}' | tr -d '[:space:]')"
  if [ "$actual_name" = "$expected_name" ]; then
    _pass "agent: $name (name=$actual_name)"
  else
    _fail "agent $name name mismatch: got '$actual_name', want '$expected_name'"
  fi
done

# === 模块 3: hooks 注册 + 命令路径存在 ===
echo ""
echo "[3/6] hooks 注册 + 命令路径"
SETTINGS="$CLAUDE_DIR/settings.local.json"
if [ ! -f "$SETTINGS" ]; then
  _fail "settings.local.json missing"
else
  post_cmd="$(jq -r '.hooks.PostToolUse[0].hooks[0].command // empty' "$SETTINGS" 2>/dev/null)"
  stop_cmd="$(jq -r '.hooks.Stop[0].hooks[0].command // empty' "$SETTINGS" 2>/dev/null)"

  if [ -n "$post_cmd" ]; then
    # 从 command 里提取脚本路径（双引号包裹的部分）
    post_path="$(echo "$post_cmd" | sed -nE 's/.*"([^"]+PostToolUse[^"]+\.sh)".*/\1/p')"
    if [ -n "$post_path" ] && [ -x "$post_path" ]; then
      _pass "PostToolUse hook: $post_path"
    else
      _fail "PostToolUse hook script missing or not executable: '$post_path'"
    fi
  else
    _fail "PostToolUse hook not registered"
  fi

  if [ -n "$stop_cmd" ]; then
    stop_path="$(echo "$stop_cmd" | sed -nE 's/.*"([^"]+Stop[^"]+\.sh)".*/\1/p')"
    if [ -n "$stop_path" ] && [ -x "$stop_path" ]; then
      _pass "Stop hook: $stop_path"
    else
      _fail "Stop hook script missing or not executable: '$stop_path'"
    fi
  else
    _fail "Stop hook not registered"
  fi
fi

# === 模块 4: python3 + jsonschema ===
echo ""
echo "[4/6] python3 + jsonschema"
if command -v python3 >/dev/null 2>&1; then
  py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  major="$(echo "$py_ver" | cut -d. -f1)"
  minor="$(echo "$py_ver" | cut -d. -f2)"
  if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
    _pass "python3 $py_ver (>= 3.10)"
  else
    _fail "python3 $py_ver too old (want >= 3.10)"
  fi

  if python3 -c 'import jsonschema' 2>/dev/null; then
    # v1.1 P9-P2 修：用 importlib.metadata 代替 deprecated jsonschema.__version__
    js_ver="$(python3 -c 'from importlib.metadata import version; print(version("jsonschema"))' 2>/dev/null \
              || python3 -c 'import jsonschema; print(getattr(jsonschema, "__version__", "unknown"))')"
    _pass "jsonschema $js_ver importable"
  else
    _fail "jsonschema not importable (pip install jsonschema?)"
  fi
else
  _fail "python3 not on PATH"
fi

# === 模块 5: pytest 全绿（753 官方 TC：shared + integration + acceptance + performance）===
# v1.2 修：只跑 4 个官方 suite，排除 bff/multimodal（依赖未安装不影响交付）
echo ""
echo "[5/6] pytest 全绿（753 官方 TC）"
if command -v python3 >/dev/null 2>&1; then
  pytest_log="$(mktemp)"
  ( cd "$HARNESS_DIR" && python3 -m pytest tests/shared tests/integration tests/acceptance tests/performance -q --no-header > "$pytest_log" 2>&1 )
  pytest_exit=$?
  # 从 pytest 输出里找 "... passed|failed|error in T.Ts" 行；宽松匹配多种 pytest 版本
  summary="$(grep -E '(passed|failed|error).*in [0-9.]+s' "$pytest_log" | tail -1 | tr -s ' =')"
  [ -z "$summary" ] && summary="$(tail -1 "$pytest_log")"
  if [ "$pytest_exit" -eq 0 ]; then
    _pass "pytest: exit=0 | $summary"
  else
    _fail "pytest: exit=$pytest_exit | $summary (full log: $pytest_log)"
    cat "$pytest_log" | tail -15 >&2
  fi
  rm -f "$pytest_log"
fi

# === 模块 6: auditor 不改 routing-matrix（进化边界硬线）===
echo ""
echo "[6/6] auditor 进化边界硬线（不 open-write routing-matrix.json）"
if grep -nE "open\s*\(.*routing-matrix.*['\"]?[wa]['\"]?|\.write_text\s*\(.*routing-matrix|matrix_path.*open.*w" \
    "$HARNESS_DIR/archive/auditor.py" >/dev/null 2>&1; then
  _fail "auditor.py contains write-to-matrix pattern (violates method3 § 7.3)"
else
  _pass "auditor.py does not open/write routing-matrix.json"
fi

# === Summary ===
echo ""
echo "============================================================"
printf "[self-test] Result: "
if [ "$fail" -eq 0 ]; then
  printf "\033[32mPASS\033[0m (%d checks)\n" "$pass"
  exit 0
else
  printf "\033[31mFAIL\033[0m (%d passed, %d failed)\n" "$pass" "$fail"
  exit "$fail"
fi
