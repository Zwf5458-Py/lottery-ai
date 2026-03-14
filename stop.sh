#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
PID_FILE="$RUN_DIR/app.pid"
MODE_FILE="$RUN_DIR/app.mode"

if [ ! -f "$PID_FILE" ]; then
  echo "[INFO] 未发现运行中的服务（PID 文件不存在）。"
  exit 0
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -z "$PID" ]; then
  echo "[WARN] PID 文件为空，清理状态文件。"
  rm -f "$PID_FILE" "$MODE_FILE"
  exit 0
fi

if ! kill -0 "$PID" >/dev/null 2>&1; then
  echo "[INFO] 服务进程不存在（PID: $PID），清理状态文件。"
  rm -f "$PID_FILE" "$MODE_FILE"
  exit 0
fi

echo "[INFO] 正在停止服务 (PID: $PID)..."
kill "$PID" >/dev/null 2>&1 || true

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if ! kill -0 "$PID" >/dev/null 2>&1; then
    rm -f "$PID_FILE" "$MODE_FILE"
    echo "[OK] 服务已停止。"
    exit 0
  fi
  sleep 1
done

echo "[WARN] 优雅停止超时，尝试强制终止 (SIGKILL)..."
kill -9 "$PID" >/dev/null 2>&1 || true
rm -f "$PID_FILE" "$MODE_FILE"
echo "[OK] 服务已强制停止。"
