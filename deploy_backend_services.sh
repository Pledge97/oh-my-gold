#!/usr/bin/env bash
set -euo pipefail

# 项目根目录：默认取当前脚本所在目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python 虚拟环境目录
VENV_DIR="${PROJECT_DIR}/.venv"

# systemd 服务名称
BACKEND_SERVICE_NAME="oh-my-gold-backend"
DATA_SERVICE_NAME="oh-my-gold-data"

# 后端和数据服务端口
BACKEND_PORT="8000"
DATA_SERVICE_PORT="8001"

# 当前运行用户，用于 systemd User 字段
RUN_USER="${SUDO_USER:-$(id -un)}"

# sudo 命令封装：root 用户执行时不需要 sudo
if [[ "$(id -u)" -eq 0 ]]; then
  SUDO_CMD=""
else
  SUDO_CMD="sudo"
fi

echo "[deploy] 项目目录：${PROJECT_DIR}"
echo "[deploy] 运行用户：${RUN_USER}"

# 检查基础命令
command -v python3 >/dev/null 2>&1 || {
  echo "[deploy] 未找到 python3，请先安装 python3 和 python3-venv"
  exit 1
}

# 创建数据目录，确保 SQLite 文件有持久化位置
mkdir -p "${PROJECT_DIR}/data"

# 创建或复用 Python 虚拟环境
if [[ ! -d "${VENV_DIR}" ]]; then
  echo "[deploy] 创建 Python 虚拟环境"
  python3 -m venv "${VENV_DIR}"
fi

# 安装依赖
echo "[deploy] 安装 Python 依赖"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/data_service/requirements.txt"

# 写入后端 systemd 服务
echo "[deploy] 写入 ${BACKEND_SERVICE_NAME}.service"
${SUDO_CMD} tee "/etc/systemd/system/${BACKEND_SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=Oh My Gold Backend API
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${VENV_DIR}/bin/uvicorn backend.main:app --host 127.0.0.1 --port ${BACKEND_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 写入数据采集 systemd 服务
echo "[deploy] 写入 ${DATA_SERVICE_NAME}.service"
${SUDO_CMD} tee "/etc/systemd/system/${DATA_SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=Oh My Gold Data Service
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}/data_service
Environment=PYTHONUNBUFFERED=1
ExecStart=${VENV_DIR}/bin/uvicorn main:app --host 127.0.0.1 --port ${DATA_SERVICE_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 重新加载并启动服务
echo "[deploy] 启动 systemd 服务"
${SUDO_CMD} systemctl daemon-reload
${SUDO_CMD} systemctl enable "${BACKEND_SERVICE_NAME}"
${SUDO_CMD} systemctl enable "${DATA_SERVICE_NAME}"
${SUDO_CMD} systemctl restart "${BACKEND_SERVICE_NAME}"
${SUDO_CMD} systemctl restart "${DATA_SERVICE_NAME}"

echo "[deploy] 部署完成"
echo "[deploy] 后端文档：http://127.0.0.1:${BACKEND_PORT}/docs"
echo "[deploy] 数据服务健康检查：http://127.0.0.1:${DATA_SERVICE_PORT}/health"
echo "[deploy] 查看日志：sudo journalctl -u ${BACKEND_SERVICE_NAME} -f"
echo "[deploy] 查看日志：sudo journalctl -u ${DATA_SERVICE_NAME} -f"
