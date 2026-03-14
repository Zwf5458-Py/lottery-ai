#!/usr/bin/env bash
set -euo pipefail

# 用法：
#   bash logs.sh           # 默认查看 error.log 尾部
#   bash logs.sh error
#   bash logs.sh access
#   bash logs.sh ai
#   bash logs.sh all       # 同时跟踪 error / access / ai

MODE="${1:-error}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
ERR_LOG="$LOG_DIR/error.log"
ACC_LOG="$LOG_DIR/access.log"
AI_LOG="$LOG_DIR/ai_errors.log"

mkdir -p "$LOG_DIR"
touch "$ERR_LOG" "$ACC_LOG" "$AI_LOG"

case "$MODE" in
  error)
    echo "[INFO] 跟踪错误日志: $ERR_LOG"
    exec tail -n 200 -f "$ERR_LOG"
    ;;
  access)
    echo "[INFO] 跟踪访问日志: $ACC_LOG"
    exec tail -n 200 -f "$ACC_LOG"
    ;;
  ai)
    echo "[INFO] 跟踪 AI 故障日志: $AI_LOG"
    exec tail -n 200 -f "$AI_LOG"
    ;;
  all)
    echo "[INFO] 同时跟踪日志: $ERR_LOG + $ACC_LOG + $AI_LOG"
    exec tail -n 200 -f "$ERR_LOG" "$ACC_LOG" "$AI_LOG"
    ;;
  *)
    echo "[ERROR] 不支持的参数: $MODE (可选: error | access | ai | all)"
    exit 1
    ;;
esac
