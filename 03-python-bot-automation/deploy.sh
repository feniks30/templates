#!/usr/bin/env bash
# Пример установки systemd-сервиса для 03-python-bot-automation на Linux VPS.
# Запуск: sudo bash deploy.sh install   (или remove)

set -euo pipefail

APP_DIR="/opt/fh-bots/03-python-bot-automation"
SERVICE_NAME="fh-bot-parser"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

case "${1:-}" in
  install)
    echo "==> Установка сервиса ${SERVICE_NAME}"
    sudo mkdir -p "${APP_DIR}"
    sudo cp -r . "${APP_DIR}/"
    sudo cp "${APP_DIR}/.env.example" "${APP_DIR}/.env" 2>/dev/null || true
    echo "==> Заполните ${APP_DIR}/.env перед запуском"
    cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=FH Bot Parser (03-python-bot-automation)
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=/usr/bin/python3 ${APP_DIR}/main.py
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    echo "==> Готово. Теперь:"
    echo "    sudo nano ${APP_DIR}/.env     # впишите BOT_TOKEN и остальные параметры"
    echo "    sudo systemctl enable --now ${SERVICE_NAME}"
    echo "    sudo systemctl status ${SERVICE_NAME}"
    ;;
  remove)
    echo "==> Удаление сервиса ${SERVICE_NAME}"
    sudo systemctl disable --now "${SERVICE_NAME}" 2>/dev/null || true
    sudo rm -f "${SERVICE_FILE}"
    sudo systemctl daemon-reload
    echo "==> Удалено."
    ;;
  *)
    echo "Использование: $0 {install|remove}"
    exit 1
    ;;
esac