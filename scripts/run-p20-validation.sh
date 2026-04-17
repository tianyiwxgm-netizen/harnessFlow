#!/usr/bin/env bash
#
# P20 真出片验证触发脚本（Phase 8.3 handoff）。
#
# ⚠️ 本脚本会真实消耗你的 aigc 后端资源：
#   - uvicorn 进程
#   - DeepSeek / 火山方舟 / Seedance API 配额（~¥5-20）
#   - 阿里 OSS 上传带宽
#   - LangGraph pipeline 30-60 分钟
#
# **仅在你确认要验证 P20 假完成修复时运行**。
#
# 用法：
#   bash "harnessFlow /scripts/run-p20-validation.sh" [query] [duration_sec] [round]
#
# 示例：
#   bash "harnessFlow /scripts/run-p20-validation.sh" "开飞船炸月球" 30 8
#
# 步骤（全自动）：
#   1. 前置检查：.env 存在 / uvicorn 可启 / aigc/backend 目录结构 OK
#   2. 启动 uvicorn (port 8000)，等 server up
#   3. 调 e2e_runner.py 触发 POST /api/pipelines
#   4. 轮询 pipeline 状态到终态
#   5. 下载 mp4 + 记录 OSS key
#   6. 调 scripts/verify-p20-artifacts.py 跑 DoD_P20 全套 8 子契约
#   7. 产出 task-boards/p8-3-p20.json + verifier_reports/p8-3-p20.json + retros/p8-3-p20.md
#   8. 调 archive writer 写 jsonl entry
#   9. kill uvicorn
#
# 退出码：
#   0  DoD_P20 全 PASS（真完成率 100%）
#   N  N 个子契约 FAIL（见 verifier_report.failed_conditions）

set -u
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$HARNESS_DIR/.." && pwd)"
AIGC_BACKEND="$PROJECT_ROOT/aigc/backend"

QUERY="${1:-开飞船炸月球}"
DURATION="${2:-30}"
ROUND="${3:-8}"
TASK_ID="p8-3-p20"

echo "=========================================="
echo "[p20] harnessFlow Phase 8.3 P20 真出片验证"
echo "=========================================="
echo "  query:    $QUERY"
echo "  duration: ${DURATION}s"
echo "  round:    $ROUND"
echo "  task_id:  $TASK_ID"
echo ""
echo "⚠️  此操作会消耗真实 API 配额 + 30-60 分钟"
read -p "继续？(y/N) " -n 1 -r REPLY
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "[p20] aborted by user"
  exit 2
fi

# === 1. 前置检查 ===
echo ""
echo "[1/9] 前置检查"
if [ ! -d "$AIGC_BACKEND" ]; then
  echo "  ERROR: aigc/backend 目录不存在: $AIGC_BACKEND" >&2
  exit 1
fi
if [ ! -f "$AIGC_BACKEND/.env" ]; then
  echo "  WARN: $AIGC_BACKEND/.env 不存在，uvicorn 可能因缺 API key 启动失败"
fi
if [ ! -f "$AIGC_BACKEND/scripts/e2e_runner.py" ]; then
  echo "  ERROR: e2e_runner.py 缺失" >&2
  exit 1
fi
if ! lsof -i :8000 >/dev/null 2>&1; then
  echo "  port 8000 free ✓"
else
  echo "  ERROR: port 8000 占用，请先释放" >&2
  exit 1
fi

# === 2. 创建 task-board INIT 态 ===
echo ""
echo "[2/9] 创建 task-board INIT"
TB="$HARNESS_DIR/task-boards/$TASK_ID.json"
mkdir -p "$HARNESS_DIR/task-boards" "$HARNESS_DIR/verifier_reports" "$HARNESS_DIR/retros" "$HARNESS_DIR/sessions"
python3 - "$TB" "$TASK_ID" "$QUERY" "$DURATION" <<'PY'
import json, sys
from datetime import datetime, timezone
tb_path, task_id, query, duration = sys.argv[1:5]
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
tb = {
    "task_id": task_id,
    "project": "aigcv2",
    "task_type": "视频出片",
    "size": "XL",
    "risk": "不可逆",
    "route_id": "C",
    "route": "C",
    "initial_route_recommendation": "C",
    "current_state": "IMPL",
    "dod_expression": "file_exists('final.mp4') AND ffprobe_duration > 0 AND oss_head OK AND uvicorn_started AND curl_status == 200",
    "input_query": query,
    "input_duration_sec": int(duration),
    "red_lines": [],
    "retries": [],
    "supervisor_interventions": [],
    "artifacts": [],
    "state_history": [{"from": "INIT", "to": "IMPL", "at": now, "reason": "P20 真出片自动脚本启动"}],
    "time_budget": {"cap_sec": 3600, "elapsed_sec": 0},
    "cost_budget": {"token_cap": 200000, "token_used": 0, "cost_usd": 0},
}
with open(tb_path, "w", encoding="utf-8") as fh:
    json.dump(tb, fh, ensure_ascii=False, indent=2)
print(f"  task-board: {tb_path}")
PY

# === 3. 启动 uvicorn ===
echo ""
echo "[3/9] 启动 uvicorn (port 8000)"
cd "$AIGC_BACKEND" || exit 1
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
UVICORN_LOG="/tmp/p8-3-uvicorn.log"
nohup python3 -m uvicorn app.main:app --port 8000 > "$UVICORN_LOG" 2>&1 &
UVICORN_PID=$!
echo "  uvicorn PID=$UVICORN_PID, log=$UVICORN_LOG"

echo "  waiting for uvicorn ready..."
for i in {1..30}; do
  if curl -sf http://localhost:8000/docs >/dev/null 2>&1; then
    echo "  uvicorn up ✓ (took ${i}s)"
    break
  fi
  sleep 2
done
if ! curl -sf http://localhost:8000/docs >/dev/null 2>&1; then
  echo "  ERROR: uvicorn did not start in 60s" >&2
  kill "$UVICORN_PID" 2>/dev/null || true
  echo "  --- uvicorn log tail ---"
  tail -30 "$UVICORN_LOG"
  exit 1
fi

# === 4. 触发 e2e_runner ===
echo ""
echo "[4/9] 触发出片 pipeline"
E2E_OUT="/tmp/p8-3-e2e.log"
(
  cd "$AIGC_BACKEND" || exit 1
  python3 scripts/e2e_runner.py --round "$ROUND" --query "$QUERY" 2>&1 | tee "$E2E_OUT"
)
E2E_EXIT=$?
echo "  e2e_runner exit=$E2E_EXIT"

# === 5-9 由 python 一起做 ===
echo ""
echo "[5-9/9] 收集产物 + 跑 DoD_P20 + 产出四件套"
kill "$UVICORN_PID" 2>/dev/null || true
wait "$UVICORN_PID" 2>/dev/null

python3 "$HARNESS_DIR/scripts/verify-p20-artifacts.py" \
  --task-id "$TASK_ID" \
  --e2e-log "$E2E_OUT" \
  --uvicorn-log "$UVICORN_LOG" \
  --round "$ROUND" \
  --query "$QUERY"
VERIFY_EXIT=$?

echo ""
echo "=========================================="
if [ "$VERIFY_EXIT" -eq 0 ]; then
  echo "[p20] ✅ DoD_P20 全 PASS — 真完成"
else
  echo "[p20] ❌ DoD_P20 FAIL ($VERIFY_EXIT 子契约未过)"
  echo "  详见: $HARNESS_DIR/verifier_reports/$TASK_ID.json"
fi
echo "=========================================="
exit "$VERIFY_EXIT"
