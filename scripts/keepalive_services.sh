#!/usr/bin/env bash
set -euo pipefail

# 简易守护脚本：定期检测前端(Vite)与后端(Django)进程是否存活，不存活则拉起。
# 使用方式：
#  - 手动启动：nohup bash scripts/keepalive_services.sh >/dev/null 2>&1 &
#  - 开机自启：将上述命令写入 crontab 的 @reboot；或在 systemd 中创建服务。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$REPO_ROOT/logs"
PID_DIR="$REPO_ROOT/.pids"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

STARTER="$REPO_ROOT/scripts/start_services.sh"

mkdir -p "$LOG_DIR" "$PID_DIR"

is_port_up() {
  local port="$1"
  curl -sSfI "http://localhost:${port}" --max-time 1 >/dev/null 2>&1
}

ensure_services() {
  local need_start=false

  if ! is_port_up "$FRONTEND_PORT"; then
    echo "[keepalive] 前端端口 ${FRONTEND_PORT} 未就绪，准备拉起。"
    need_start=true
  fi
  if ! is_port_up "$BACKEND_PORT"; then
    echo "[keepalive] 后端端口 ${BACKEND_PORT} 未就绪，准备拉起。"
    need_start=true
  fi

  if [[ "$need_start" == true ]]; then
    echo "[keepalive] 调用 start_services.sh 进行拉起。"
    bash "$STARTER" || echo "[keepalive] 启动脚本执行失败，请检查。"
  fi
}

echo "[keepalive] 守护进程启动，监控端口 前端:${FRONTEND_PORT} 后端:${BACKEND_PORT}"
while true; do
  ensure_services
  sleep 30
done