#!/usr/bin/env bash
#
# /harnessFlow-ui launcher
#
# Starts FastAPI backend on port 8765 and opens the browser.
# Zero npm install — frontend is CDN-based Vue 3 + Element Plus.

set -u

UI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$(cd "$UI_DIR/.." && pwd)"
PORT="${HARNESSFLOW_UI_PORT:-8765}"
PID_FILE="$UI_DIR/.ui.pid"

# --- prereqs ---
for cmd in python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ui] FATAL: $cmd not installed" >&2
    exit 2
  fi
done

# --- ensure deps ---
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "[ui] installing fastapi + uvicorn..."
  python3 -m pip install --quiet --user fastapi uvicorn 2>/dev/null || \
  python3 -m pip install --quiet --break-system-packages fastapi uvicorn 2>/dev/null || {
    echo "[ui] FATAL: failed to install fastapi + uvicorn" >&2
    exit 3
  }
fi

# --- detect already-running ---
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || echo "")"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[ui] already running (pid=$OLD_PID) — opening browser"
    open "http://localhost:$PORT" 2>/dev/null || echo "  → http://localhost:$PORT"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

# --- start uvicorn ---
cd "$UI_DIR/backend"
echo "[ui] starting uvicorn on port $PORT"
echo "[ui] harness_root=$HARNESS_DIR"
echo "[ui] press Ctrl-C to stop"
echo ""

# Launch in foreground (Ctrl-C stops); background mode via & at caller
if [ "${1:-}" = "--daemon" ]; then
  nohup python3 -m uvicorn server:app --host 127.0.0.1 --port "$PORT" \
        > "$UI_DIR/ui.log" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 1.5
  if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "[ui] daemon pid=$(cat "$PID_FILE") log=$UI_DIR/ui.log"
    open "http://localhost:$PORT" 2>/dev/null || echo "  → http://localhost:$PORT"
  else
    echo "[ui] FATAL: daemon failed to start; see $UI_DIR/ui.log"
    exit 4
  fi
else
  (sleep 1.2 && open "http://localhost:$PORT" 2>/dev/null) &
  exec python3 -m uvicorn server:app --host 127.0.0.1 --port "$PORT"
fi
