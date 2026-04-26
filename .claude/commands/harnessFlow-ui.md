---
description: 启动或停止 harnessFlow Dashboard UI（port 8765，零 npm，CDN Vue3）并自动打开浏览器
argument-hint: [stop]
allowed-tools: Bash
---

# /harnessFlow-ui

启动或停止 harnessFlow 任务看板 Web UI。

## 用法

- `/harnessFlow-ui` — 后台 daemon 启动，浏览器自动打开 `http://localhost:8765`
- `/harnessFlow-ui stop` — 停止 daemon

## UI 包含什么

- **任务看板**：所有历史 task-boards 的时间轴、路由、状态、产出物
- **知识库视图**：跨任务聚合 anti-patterns / effective-combos / external-refs
- **项目视图**：按 project 分组的任务统计
- **Admin 页**：引擎配置、subagent 注册表、技能列表

## 执行步骤

### 启动（$ARGUMENTS 为空或 daemon）

用 Bash 工具运行以下命令（不要修改路径检测逻辑）：

```bash
HARNESS_DIR="$(python3 -c "
import os, sys
# 优先通过 symlink 解析真实路径
cmd_sym = os.path.expanduser('~/.claude/commands/harnessFlow-ui.md')
if os.path.islink(cmd_sym):
    real = os.path.realpath(cmd_sym)
    # real = HARNESS/.claude/commands/harnessFlow-ui.md → 上推 3 层
    print(os.path.dirname(os.path.dirname(os.path.dirname(real))))
    sys.exit(0)
# fallback: 找当前 git repo root 下有 ui/start.sh 的目录
cwd = os.getcwd()
for d in [cwd] + [os.path.join(cwd, p) for p in ['harnessFlow', '../harnessFlow']]:
    if os.path.isfile(os.path.join(d, 'ui', 'start.sh')):
        print(d)
        sys.exit(0)
print(cwd)
" 2>/dev/null)"

if [ ! -f "${HARNESS_DIR}/ui/start.sh" ]; then
  echo "[harnessFlow-ui] ERROR: ui/start.sh not found in ${HARNESS_DIR}"
  echo "  请确认 harnessFlow 已安装并通过 setup.sh 或 symlink 注册"
  exit 1
fi

bash "${HARNESS_DIR}/ui/start.sh" --daemon
```

成功后告知用户：**UI 已就绪，请访问 http://localhost:8765**

如果失败，打印 `${HARNESS_DIR}/ui/ui.log` 最后 15 行。

### 停止（$ARGUMENTS = stop）

```bash
HARNESS_DIR="$(python3 -c "
import os, sys
cmd_sym = os.path.expanduser('~/.claude/commands/harnessFlow-ui.md')
if os.path.islink(cmd_sym):
    real = os.path.realpath(cmd_sym)
    print(os.path.dirname(os.path.dirname(os.path.dirname(real))))
    sys.exit(0)
print(os.getcwd())
" 2>/dev/null)"

PID_FILE="${HARNESS_DIR}/ui/.ui.pid"
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE")"
  kill "$OLD_PID" 2>/dev/null && echo "[harnessFlow-ui] stopped (pid=$OLD_PID)" || echo "[harnessFlow-ui] pid=$OLD_PID already gone"
  rm -f "$PID_FILE"
else
  echo "[harnessFlow-ui] not running (no pid file)"
fi
```
