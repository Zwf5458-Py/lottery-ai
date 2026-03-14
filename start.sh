#!/usr/bin/env bash
set -euo pipefail

# 稳定启动脚本：自动准备虚拟环境、安装依赖，并按模式启动服务。
# 用法：
#   bash start.sh            # 默认 dev 模式
#   bash start.sh dev        # Flask 开发模式
#   bash start.sh prod       # Gunicorn 生产模式

MODE="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
RUN_DIR="$ROOT_DIR/.run"
PID_FILE="$RUN_DIR/app.pid"
MODE_FILE="$RUN_DIR/app.mode"
PY_BIN="python3"
USE_VENV=1
RUN_PY="$PY_BIN"

if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  echo "[ERROR] 未找到 python3，请先安装 Python 3。"
  exit 1
fi

if [ -d "$VENV_DIR" ] && [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "[WARN] 检测到损坏的虚拟环境，正在重建: $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] 创建虚拟环境: $VENV_DIR"
  if ! "$PY_BIN" -m venv "$VENV_DIR"; then
    echo "[WARN] 创建虚拟环境失败，降级为系统 Python 模式。"
    USE_VENV=0
  fi
fi

if [ "$USE_VENV" -eq 1 ] && [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  RUN_PY="python"
else
  USE_VENV=0
  RUN_PY="$PY_BIN"
fi

if [ -f "$ROOT_DIR/.env" ]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

echo "[INFO] 安装/校验依赖..."
if [ "$USE_VENV" -eq 1 ]; then
  "$RUN_PY" -m pip install --upgrade pip >/dev/null
else
  "$RUN_PY" -m pip install --user --break-system-packages --upgrade pip >/dev/null
fi
if [ "$USE_VENV" -eq 1 ]; then
  "$RUN_PY" -m pip install -r "$ROOT_DIR/requirements.txt"
else
  "$RUN_PY" -m pip install --user --break-system-packages -r "$ROOT_DIR/requirements.txt"
fi

mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/data/user_dbs"
mkdir -p "$RUN_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" >/dev/null 2>&1; then
    echo "[ERROR] 服务已在运行 (PID: $OLD_PID)。请先执行: bash stop.sh"
    exit 1
  fi
  rm -f "$PID_FILE"
fi

# 默认安全配置（可被外部环境变量覆盖）
export FLASK_HOST="${FLASK_HOST:-127.0.0.1}"
export FLASK_PORT="${FLASK_PORT:-5000}"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"
export SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-0}"

if [ -z "${FLASK_SECRET_KEY:-}" ]; then
  echo "[WARN] 未设置 FLASK_SECRET_KEY。建议在 .env 中配置一个强随机密钥。"
fi

case "$MODE" in
  dev)
    export FLASK_DEBUG="${FLASK_DEBUG:-1}"
    echo "$MODE" > "$MODE_FILE"
    echo "$$" > "$PID_FILE"
    echo "[INFO] 启动开发服务: http://$FLASK_HOST:$FLASK_PORT"
    exec "$RUN_PY" "$ROOT_DIR/app.py"
    ;;
  prod)
    echo "$MODE" > "$MODE_FILE"
    echo "$$" > "$PID_FILE"
    echo "[INFO] 启动生产服务(Gunicorn): http://$FLASK_HOST:$FLASK_PORT"
    exec "$RUN_PY" -m gunicorn -c "$ROOT_DIR/gunicorn.conf.py" app:app
    ;;
  *)
    echo "[ERROR] 不支持的模式: $MODE (可选: dev | prod)"
    exit 1
    ;;
esac
