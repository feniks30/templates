"""Тренажёр диалога: поговорить с ботом в терминале, без Telegram и токена.

    python -m bot.simulate                  # интерактивно
    python -m bot.simulate --script "Иван|нужен парсер цен|3 дня|Отправить|Мои заявки"

Нужен для двух вещей: показать логику до выкладки на сервер и записать сценарий для теста.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bot.core import Dialog, Store
else:
    from .core import Dialog, Store


def run(lines: list, store: Store | None = None, user_id: int = 1,
        now: datetime | None = None) -> list:
    store = store or Store(":memory:")
    dialog = Dialog(store, user_id, now=now)
    shown = []
    for line in lines:
        reply = dialog.handle(line)
        shown.append((line, reply))
    return shown


def main() -> int:
    ap = argparse.ArgumentParser(prog="bot.simulate")
    ap.add_argument("--script", default="", help="шаги через | (пусто — интерактивно)")
    a = ap.parse_args()
    store = Store(":memory:")
    dialog = Dialog(store, 1)

    # сценарий считаем с момента «нажал Start» — как в настоящем Telegram
    steps = ["/start"] + ([s.strip() for s in a.script.split("|")] if a.script else [])
    print("Демо-бот заявок. Пишите как клиент. Выход: пустая строка.\n")
    if steps:
        for line in steps:
            reply = dialog.handle(line)
            print(f"вы: {line}")
            print(f"бот: {reply.text}\n")
        return 0
    while True:
        try:
            line = input("вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        reply = dialog.handle(line)
        print(f"бот: {reply.text}")
        if reply.buttons:
            print(f"     кнопки: {' | '.join(reply.buttons)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
