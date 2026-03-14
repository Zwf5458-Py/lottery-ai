#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
PID_FILE="$RUN_DIR/app.pid"
MODE_FILE="$RUN_DIR/app.mode"

if [ ! -f "$PID_FILE" ]; then
  echo "[INFO] 服务状态: 未运行"
  exit 1
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
MODE="unknown"
if [ -f "$MODE_FILE" ]; then
  MODE="$(cat "$MODE_FILE" 2>/dev/null || echo unknown)"
fi

if [ -z "$PID" ]; then
  echo "[WARN] 服务状态异常: PID 文件为空"
  exit 1
fi

if kill -0 "$PID" >/dev/null 2>&1; then
  echo "[OK] 服务状态: 运行中"
  echo "[OK] 模式: $MODE"
  echo "[OK] PID: $PID"
  exit 0
fi

echo "[WARN] 服务状态: 未运行（检测到陈旧 PID 文件，PID: $PID）"
exit 1
