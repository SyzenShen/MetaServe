#!/usr/bin/env bash
set -euo pipefail

# 一键启动前端(Vite)与后端(Django)开发服务，常驻后台运行

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 允许通过环境变量覆盖默认端口
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
# 将后端默认端口调整为 8020，与前端代理一致
BACKEND_PORT="${BACKEND_PORT:-8020}"

LOG_DIR="$REPO_ROOT/logs"
PID_DIR="$REPO_ROOT/.pids"
FRONTEND_DIR="$REPO_ROOT/frontend"
BACKEND_DIR="$REPO_ROOT"
NODE_BIN="$REPO_ROOT/.node/bin/node"
if [[ ! -x "$NODE_BIN" ]]; then
  # Fallback to system node
  NODE_BIN="$(command -v node || true)"
fi
VITE_BIN="$REPO_ROOT/frontend/node_modules/vite/bin/vite.js"

mkdir -p "$LOG_DIR" "$PID_DIR"

# 将用户本地可执行目录加入 PATH，便于解析 ~/.local/bin/cellxgene
export PATH="$HOME/Library/Python/3.10/bin:$HOME/.local/bin:$PATH"
export LND_PATH="${LND_PATH:-/home/mosserver/software/linuxnd}"

# 解析并导出 Cellxgene 路径与用于布局生成的 Python 解释器
# 允许外部覆盖：若环境已设置则保持不变
CELLXGENE_CMD="${CELLXGENE_CMD:-$(command -v cellxgene || true)}"
CELLXGENE_PYTHON="${CELLXGENE_PYTHON:-$(command -v python3 || command -v python || true)}"
export CELLXGENE_CMD CELLXGENE_PYTHON
CELLXGENE_PORT="${CELLXGENE_PORT:-5005}"
# 若未设置，令前端默认指向代理路径 /cellxgene/，以便利用 Vite 代理转发到 CELLXGENE_PORT
export VITE_CELLXGENE_URL="${VITE_CELLXGENE_URL:-/cellxgene/}"

echo "CELLXGENE_CMD=${CELLXGENE_CMD:-<not found>}"
echo "CELLXGENE_PYTHON=${CELLXGENE_PYTHON:-<not found>}"

is_port_up() {
  local port="$1"
  curl -sSfI "http://localhost:${port}" --max-time 1 >/dev/null 2>&1
}

wait_for_port() {
  local name="$1"; local port="$2"; local timeout="${3:-20}"
  echo "等待 ${name} 在端口 ${port} 上线..."
  for ((i=0; i<timeout; i++)); do
    if is_port_up "$port"; then
      echo "${name} 已在 http://localhost:${port}/ 就绪"
      return 0
    fi
    sleep 1
  done
  echo "警告: ${name} 在 ${timeout}s 内未就绪，请检查日志。"
  return 1
}

start_frontend() {
  echo "启动前端服务 (Vite) ..."
  # 若端口已被占用，认为已有服务在运行，直接跳过启动
  if is_port_up "$FRONTEND_PORT"; then
    echo "前端端口 ${FRONTEND_PORT} 已有服务，就绪，跳过启动。"
    return 0
  fi
  if [[ ! -x "$NODE_BIN" ]]; then
    echo "错误: Node 未找到：$NODE_BIN"
    exit 1
  fi
  if [[ ! -f "$VITE_BIN" ]]; then
    echo "错误: Vite 未安装：$VITE_BIN 不存在。"
    echo "请先执行: cd frontend && npm install"
    exit 1
  fi
  # 若 PID 文件存在且进程仍在运行，也跳过
  if [[ -f "$PID_DIR/frontend.pid" ]]; then
    local pid
    pid="$(cat "$PID_DIR/frontend.pid" || true)"
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "前端已在运行 (PID ${pid})，跳过启动。"
      return 0
    fi
  fi
  (
    cd "$FRONTEND_DIR"
    nohup "$NODE_BIN" "$VITE_BIN" --host --port "$FRONTEND_PORT" --strictPort \
      > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
  )
  wait_for_port "前端" "$FRONTEND_PORT" 20
}

start_cellxgene() {
  # 仅在命令存在时尝试启动
  if [[ -z "${CELLXGENE_CMD}" ]]; then
    return 0
  fi
  # 若未指定数据集，尝试查找 cellxgene_data 下的第一个 h5ad 文件
  if [[ -z "${CELLXGENE_DATASET:-}" ]]; then
    local default_h5ad
    default_h5ad="$(find "$REPO_ROOT/cellxgene_data" -name "*.h5ad" -print -quit 2>/dev/null || true)"
    if [[ -n "$default_h5ad" ]]; then
      echo "发现默认数据集: $default_h5ad"
      CELLXGENE_DATASET="$default_h5ad"
    else
      echo "提示: 未设置 CELLXGENE_DATASET 且未在 cellxgene_data 下找到 h5ad 文件，跳过 Cellxgene 启动。"
      return 0
    fi
  fi
  if is_port_up "$CELLXGENE_PORT"; then
    echo "Cellxgene 端口 ${CELLXGENE_PORT} 已有服务，就绪，跳过启动。"
    return 0
  fi
  (
    cd "$REPO_ROOT"
    nohup "$CELLXGENE_CMD" launch "${CELLXGENE_DATASET}" --port "${CELLXGENE_PORT}" --host 0.0.0.0 \
      > "$LOG_DIR/cellxgene.log" 2>&1 &
    echo $! > "$PID_DIR/cellxgene.pid"
  )
  wait_for_port "Cellxgene" "$CELLXGENE_PORT" 25 || true
}

start_backend() {
  echo "启动后端服务 (Django) ..."
  # 若端口已被占用，认为已有服务在运行，直接跳过启动
  if is_port_up "$BACKEND_PORT"; then
    echo "后端端口 ${BACKEND_PORT} 已有服务，就绪，跳过启动。"
    return 0
  fi
  if [[ -f "$PID_DIR/backend.pid" ]]; then
    local pid
    pid="$(cat "$PID_DIR/backend.pid" || true)"
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "后端已在运行 (PID ${pid})，跳过启动。"
      return 0
    fi
  fi
  (
    cd "$BACKEND_DIR"
    nohup python3 manage.py runserver 0.0.0.0:"$BACKEND_PORT" \
      > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
  )
  wait_for_port "后端" "$BACKEND_PORT" 20
}

start_frontend
start_cellxgene
start_backend

echo "已尝试启动：前端 http://localhost:${FRONTEND_PORT}/，后端 http://localhost:${BACKEND_PORT}/"
echo "日志: $LOG_DIR/frontend.log, $LOG_DIR/backend.log"
echo "PID 文件: $PID_DIR/frontend.pid, $PID_DIR/backend.pid"
