#!/usr/bin/env bash
set -euo pipefail

# 用法：
#   bash restart.sh        # 默认 dev
#   bash restart.sh dev
#   bash restart.sh prod

MODE="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[INFO] 正在重启服务，模式: $MODE"
bash "$ROOT_DIR/stop.sh" || true
sleep 1
exec bash "$ROOT_DIR/start.sh" "$MODE"
