"""Telegram-слой: aiogram 3. Здесь только «как сказать», вся логика — в core.py.

Два режима запуска:
    python -m bot.app                 # polling — для проверки на своей машине
    python -m bot.app --webhook       # webhook + aiohttp — так работает на сервере

Переменные окружения (или файл .env, см. .env.example):
    BOT_TOKEN         токен из @BotFather
    DB_PATH           путь к SQLite (по умолчанию ./data/requests.db)
    ALLOWED_IDS       «белый список» id через запятую (пусто = открыто всем)
    LIMIT_PER_MINUTE  сообщений в минуту на пользователя (по умолчанию 8)
    WEBHOOK_BASE      https://домен/префикс, например https://fh.example.com/bots/orders
    WEBHOOK_SECRET    секрет заголовка X-Telegram-Bot-Api-Secret-Token
    WEBHOOK_PORT      локальный порт aiohttp (по умолчанию 8081)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

if __package__ in (None, ""):                    # запуск как `python bot/app.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bot.core import (BTN_CANCEL, BTN_LATER, BTN_MY, BTN_NEW, BTN_SEND, Dialog, Store)
    from bot.limits import Access, RateLimiter, read_ids
else:
    from .core import (BTN_CANCEL, BTN_LATER, BTN_MY, BTN_NEW, BTN_SEND, Dialog, Store)
    from .limits import Access, RateLimiter, read_ids

router = Router()

# Диалоги держим в памяти: демо-бот, переживать рестарт ему не нужно.
# На рабочей версии это место занимает FSM в Redis.
DIALOGS: dict[int, Dialog] = {}
LIMITER = RateLimiter(per_minute=int(os.getenv("LIMIT_PER_MINUTE", "8")))
ACCESS = Access(read_ids(os.getenv("ALLOWED_IDS", "")), open_demo=True)
STORE: Store | None = None


def store() -> Store:
    global STORE
    if STORE is None:
        STORE = Store(os.getenv("DB_PATH", "data/requests.db"))
    return STORE


def keyboard(buttons: list) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if not buttons:
        return ReplyKeyboardRemove()
    rows = [[KeyboardButton(text=b)] for b in buttons]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


async def send(message: Message, reply) -> None:
    await message.answer(reply.text, reply_markup=keyboard(reply.buttons))


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    user_id = message.from_user.id
    ok, why = ACCESS.check(user_id)
    if not ok:
        await message.answer(why)
        return
    DIALOGS[user_id] = Dialog(store(), user_id)
    await send(message, DIALOGS[user_id].handle("/start"))


@router.message(F.text == BTN_NEW)
async def on_new(message: Message) -> None:
    DIALOGS[message.from_user.id] = Dialog(store(), message.from_user.id)
    await send(message, DIALOGS[message.from_user.id].handle(BTN_NEW))


@router.message(F.text == BTN_MY)
async def on_my(message: Message) -> None:
    ok, why = ACCESS.check(message.from_user.id)
    if not ok:
        await message.answer(why)
        return
    dialog = DIALOGS.get(message.from_user.id) or Dialog(store(), message.from_user.id)
    DIALOGS[message.from_user.id] = dialog
    await send(message, dialog.handle(BTN_MY))


@router.message(F.text)
async def on_text(message: Message) -> None:
    user_id = message.from_user.id
    ok, why = ACCESS.check(user_id)
    if not ok:
        await message.answer(why)
        return
    if not LIMITER.allow(user_id):
        await message.answer("Слишком часто. Подождите минуту — и продолжим.")
        return
    dialog = DIALOGS.get(user_id)
    if dialog is None:
        dialog = Dialog(store(), user_id)
        DIALOGS[user_id] = dialog
    await send(message, dialog.handle(message.text or ""))


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp


async def run_polling(token: str) -> None:
    bot = Bot(token=token)
    await build_dispatcher().start_polling(bot)


async def run_webhook(token: str, base: str, secret: str, port: int) -> None:
    from aiohttp import web

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = Bot(token=token)
    dp = build_dispatcher()
    path = "/webhook"
    await bot.set_webhook(f"{base.rstrip('/')}{path}", secret_token=secret or None,
                          drop_pending_updates=True)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret or None).register(app, path=path)
    setup_application(app, dp, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="127.0.0.1", port=port)
    await site.start()
    print(f"webhook: {base.rstrip('/')}{path} → 127.0.0.1:{port}{path}")
    await asyncio.Event().wait()


def main() -> int:
    ap = argparse.ArgumentParser(prog="bot.app")
    ap.add_argument("--webhook", action="store_true", help="работать через webhook (сервер)")
    a = ap.parse_args()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        print("❌ Нет BOT_TOKEN. Положите токен в .env (см. .env.example), в чат его не присылайте.")
        return 2
    if a.webhook:
        base = os.getenv("WEBHOOK_BASE", "").strip()
        if not base.startswith("https://"):
            print("❌ WEBHOOK_BASE должен быть https://... — Telegram не принимает http")
            return 2
        asyncio.run(run_webhook(token, base, os.getenv("WEBHOOK_SECRET", ""),
                                int(os.getenv("WEBHOOK_PORT", "8081"))))
    else:
        asyncio.run(run_polling(token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
