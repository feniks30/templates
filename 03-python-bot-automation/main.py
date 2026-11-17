#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03-python-bot-automation — каркас Telegram-бота / парсера на чистом Python 3.9+.

Нет обязательных внешних зависимостей: HTTP через urllib.request,
long polling к Telegram Bot API, логирование, экспорт в CSV/JSON,
чтение настроек из .env (без python-dotenv).

Запуск:  python main.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger("fh-bot")

# ---------------------------------------------------------------------------
# Чтение .env вручную (без внешней библиотеки python-dotenv)
# ---------------------------------------------------------------------------
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load_env(path: str = ENV_PATH) -> None:
    """Подгружает переменные из .env в os.environ, если файл существует."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env()

# ---------------------------------------------------------------------------
# Конфигурация из окружения
# ---------------------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
TARGET_URL: str = os.getenv("TARGET_URL", "")
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "60"))
EXPORT_FILE: str = os.getenv("EXPORT_FILE", "export.json")
EXPORT_FORMAT: str = os.getenv("EXPORT_FORMAT", "json").lower()
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# Хранилище данных (в памяти, сброс на диск при остановке)
# ---------------------------------------------------------------------------
records: List[Dict[str, Any]] = []
_running = True


# ---------------------------------------------------------------------------
# Экспорт в CSV / JSON
# ---------------------------------------------------------------------------
def export_data() -> None:
    """Сохраняет накопленные записи в файл EXPORT_FILE."""
    if not records:
        LOGGER.info("Нет записей для экспорта — пропускаем.")
        return
    try:
        if EXPORT_FORMAT == "csv":
            fieldnames = sorted({k for r in records for k in r.keys()})
            with open(EXPORT_FILE, "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for row in records:
                    writer.writerow(row)
        else:
            with open(EXPORT_FILE, "w", encoding="utf-8") as fh:
                json.dump(records, fh, ensure_ascii=False, indent=2)
        LOGGER.info("Экспорт %d записей -> %s (формат %s)", len(records), EXPORT_FILE, EXPORT_FORMAT)
    except OSError as exc:
        LOGGER.exception("Не удалось экспортировать данные: %s", exc)


def add_record(title: str, source: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """Добавляет запись в хранилище."""
    record: Dict[str, Any] = {
        "id": int(time.time() * 1000),
        "ts": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "source": source,
    }
    if payload:
        record["payload"] = payload
    records.append(record)
    LOGGER.debug("Добавлена запись: %s (источник %s)", title, source)


# ---------------------------------------------------------------------------
# Telegram Bot API через urllib.request (long polling)
# ---------------------------------------------------------------------------
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def tg_request(method: str, data: Optional[Dict[str, Any]] = None,
               timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Выполняет запрос к Telegram Bot API. Возвращает JSON или None при ошибке."""
    if not BOT_TOKEN:
        LOGGER.debug("BOT_TOKEN не задан — пропускаем Telegram-запрос %s", method)
        return None
    url = TELEGRAM_API.format(token=BOT_TOKEN, method=method)
    body = None
    headers = {"Content-Type": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        LOGGER.error("Telegram HTTP %s для %s: %s", exc.code, method, exc.read().decode("utf-8", "replace"))
    except urllib.error.URLError as exc:
        LOGGER.error("Telegram сетевая ошибка для %s: %s", method, exc)
    except json.JSONDecodeError as exc:
        LOGGER.error("Ошибка разбора JSON от Telegram %s: %s", method, exc)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("Непредвиденная ошибка при запросе к Telegram %s: %s", method, exc)
    return None


def tg_send_message(chat_id: int, text: str) -> bool:
    """Отправляет сообщение в чат. Возвращает True при успехе."""
    result = tg_request("sendMessage", {"chat_id": chat_id, "text": text})
    return bool(result and result.get("ok"))


def tg_get_updates(offset: int, timeout: int = 30) -> List[Dict[str, Any]]:
    """Long polling getUpdates. Возвращает список обновлений."""
    result = tg_request("getUpdates", {"offset": offset, "timeout": timeout, "allowed_updates": ["message"]})
    if not result or not result.get("ok"):
        return []
    return result.get("result", [])


# ---------------------------------------------------------------------------
# Парсер цели (TARGET_URL) — пример на urllib.request
# ---------------------------------------------------------------------------
def fetch_target() -> Optional[str]:
    """Забирает содержимое TARGET_URL (пример для парсера)."""
    if not TARGET_URL:
        return None
    try:
        req = urllib.request.Request(TARGET_URL, headers={"User-Agent": "FH-Bot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("Не удалось получить %s: %s", TARGET_URL, exc)
        return None


# ---------------------------------------------------------------------------
# Обработка обновлений Telegram
# ---------------------------------------------------------------------------
def handle_update(update: Dict[str, Any]) -> None:
    """Обрабатывает одно обновление от Telegram."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return

    LOGGER.info("Сообщение от чата %s: %s", chat_id, text)

    if text == "/start":
        tg_send_message(chat_id, "Бот запущен. Каркас 03-python-bot-automation.")
    elif text == "/help":
        tg_send_message(chat_id, "Команды: /start, /help, /export")
    elif text == "/export":
        export_data()
        tg_send_message(chat_id, f"Экспорт {len(records)} записей в {EXPORT_FILE}")
    else:
        # Эхо + сохранение в записи (пример)
        add_record(title=text, source="telegram", payload={"chat_id": chat_id})
        tg_send_message(chat_id, f"Принято: {text}")


# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------
def poll_telegram() -> None:
    """Цикл long polling для Telegram Bot API."""
    offset = 0
    LOGGER.info("Запуск long polling (token=%s…)", BOT_TOKEN[:8] if BOT_TOKEN else "пусто")
    while _running:
        try:
            updates = tg_get_updates(offset)
            for upd in updates:
                offset = max(offset, int(upd.get("update_id", 0)) + 1)
                handle_update(upd)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception("Ошибка в цикле polling: %s", exc)
            time.sleep(min(CHECK_INTERVAL, 10))


def poll_target() -> None:
    """Цикл опроса TARGET_URL (пример для парсера)."""
    if not TARGET_URL:
        return
    LOGGER.info("Запуск опроса цели %s (интервал %sс)", TARGET_URL, CHECK_INTERVAL)
    while _running:
        try:
            content = fetch_target()
            if content:
                add_record(title="Проверка " + TARGET_URL, source="parser",
                           payload={"length": len(content)})
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception("Ошибка опроса цели: %s", exc)
        time.sleep(CHECK_INTERVAL)


def main() -> None:
    """Точка входа."""
    global _running

    LOGGER.info("Старт 03-python-bot-automation (Python %s)", sys.version.split()[0])

    def stop(_signum=None, _frame=None) -> None:
        global _running
        _running = False
        LOGGER.info("Получен сигнал остановки — экспорт данных…")
        export_data()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    # Запуск парсера в фоновом потоке, если задан TARGET_URL
    if TARGET_URL:
        import threading
        t = threading.Thread(target=poll_target, daemon=True, name="target-poller")
        t.start()

    if BOT_TOKEN:
        poll_telegram()
    else:
        LOGGER.warning("BOT_TOKEN не задан — режим только-парсер. "
                       "Запишите токен в .env для работы с Telegram.")
        # Держим процесс живым, если есть только парсер
        if TARGET_URL:
            while _running:
                time.sleep(1)

    export_data()
    LOGGER.info("Остановлен.")


if __name__ == "__main__":
    main()