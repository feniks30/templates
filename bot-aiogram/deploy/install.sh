#!/usr/bin/env bash
# Установка демо-бота на сервер. Идемпотентно: можно запускать повторно.
#
#   sudo ./deploy/install.sh                 # бот «заявки», порт 8081, имя orders
#   sudo NAME=parser PORT=8082 ./deploy/install.sh
#
# Что делает: пользователь → папка → venv → пакеты → systemd → запуск.
# Токен НЕ спрашивает и НЕ пишет: его кладёт человек в /etc/fh-bots/<имя>.env (права 600).
set -euo pipefail

NAME="${NAME:-orders}"
PORT="${PORT:-8081}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="/opt/fh-bots/${NAME}"
ENV_FILE="/etc/fh-bots/${NAME}.env"
UNIT="/etc/systemd/system/fh-bot-${NAME}.service"

say() { printf '\n== %s\n' "$1"; }

[ "$(id -u)" = "0" ] || { echo "нужен root: sudo $0"; exit 1; }

say "пользователь fhbot"
id -u fhbot >/dev/null 2>&1 || useradd --system --home /opt/fh-bots --shell /usr/sbin/nologin fhbot

say "папки"
mkdir -p "$DEST" /etc/fh-bots /var/log/fh-bots
chown -R fhbot:fhbot /opt/fh-bots /var/log/fh-bots
chmod 750 /etc/fh-bots

say "файлы бота"
cp -a "$SRC/bot" "$DEST/"
cp -a "$SRC/requirements.txt" "$DEST/"
chown -R fhbot:fhbot "$DEST"

say "виртуальное окружение"
if [ ! -x "$DEST/.venv/bin/python" ]; then
  python3 -m venv "$DEST/.venv"
fi
"$DEST/.venv/bin/pip" install --disable-pip-version-check -q --upgrade pip
"$DEST/.venv/bin/pip" install --disable-pip-version-check -q -r "$DEST/requirements.txt"
chown -R fhbot:fhbot "$DEST/.venv"

say "переменные окружения"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<EOF
# заполнить и сохранить права 600: chmod 600 $ENV_FILE
BOT_TOKEN=
DB_PATH=$DEST/data/requests.db
ALLOWED_IDS=
LIMIT_PER_MINUTE=8
WEBHOOK_BASE=https://ВАШ-ДОМЕН/bots/${NAME}
WEBHOOK_SECRET=замените-на-случайную-строку
WEBHOOK_PORT=${PORT}
EOF
  chmod 600 "$ENV_FILE"
  echo "создан $ENV_FILE — впишите BOT_TOKEN, WEBHOOK_BASE и WEBHOOK_SECRET, потом запустите скрипт снова"
  exit 1
fi
chmod 600 "$ENV_FILE"
if ! grep -q '^BOT_TOKEN=..*' "$ENV_FILE"; then
  echo "в $ENV_FILE пустой BOT_TOKEN — заполните и запустите снова"; exit 1
fi

say "systemd"
sed "s#/etc/systemd/system/fh-bot-orders.service#$UNIT#" "$SRC/deploy/fh-bot-${NAME}.service" \
  | sed "s#/opt/fh-bots/orders#$DEST#g" \
  | sed "s#/etc/fh-bots/orders.env#$ENV_FILE#g" > "$UNIT"
systemctl daemon-reload
systemctl enable --now "fh-bot-${NAME}"
sleep 2

say "состояние"
systemctl --no-pager --lines=5 status "fh-bot-${NAME}" || true
echo
echo "логи: journalctl -u fh-bot-${NAME} -f   ·   tail -f /var/log/fh-bots/${NAME}.log"
echo "дальше: nginx (deploy/nginx.conf) и сертификат: certbot --nginx -d ВАШ-ДОМЕН"
echo "выключить показ: systemctl stop fh-bot-${NAME}"
