"""Проверки Telegram-слоя без запуска Telegram.

Здесь важно не «бот отвечает» (это проверено на логике в test_core.py), а то, что слой aiogram
собран правильно: роутеры на месте, обработчики зарегистрированы, без токена бот честно
отказывается стартовать, а локальная база создаётся в нужном месте.
"""
from __future__ import annotations

import sys

import pytest

pytest.importorskip("aiogram", reason="Telegram-слой проверяется только там, где стоит aiogram")

from bot import app as bot_app  # noqa: E402


def test_dispatcher_has_router_connected():
    dp = bot_app.build_dispatcher()
    assert dp.sub_routers, "роутер не подключён к диспетчеру"
    assert dp.sub_routers[0] is bot_app.router


def test_handlers_registered():
    # /start, кнопки «Новая заявка», «Мои заявки» и общий приём текста
    assert len(bot_app.router.message.handlers) >= 4
    names = {h.callback.__name__ for h in bot_app.router.message.handlers}
    assert {"on_start", "on_new", "on_my", "on_text"} <= names


def test_keyboard_builds_buttons():
    kb = bot_app.keyboard(["Отправить", "Отменить"])
    assert kb.keyboard[0][0].text == "Отправить"


def test_keyboard_removed_when_no_buttons():
    from aiogram.types import ReplyKeyboardRemove
    assert isinstance(bot_app.keyboard([]), ReplyKeyboardRemove)


def test_no_token_means_clear_refusal(monkeypatch, capsys):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["bot.app"])
    rc = bot_app.main()
    out = capsys.readouterr().out
    assert rc == 2
    assert "BOT_TOKEN" in out
    assert "не присылайте" in out          # напоминание не светить токеном


def test_webhook_requires_https(monkeypatch, capsys):
    monkeypatch.setenv("BOT_TOKEN", "123:TEST")
    monkeypatch.setenv("WEBHOOK_BASE", "http://example.com/bot")
    monkeypatch.setattr(sys, "argv", ["bot.app", "--webhook"])
    rc = bot_app.main()
    assert rc == 2
    assert "https" in capsys.readouterr().out


def test_store_uses_env_path(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "requests.db"))
    monkeypatch.setattr(bot_app, "STORE", None)
    st = bot_app.store()
    rid = st.add(1, "Иван", "нужен парсер цен конкурента", "2026-11-14")
    assert rid == 1
    assert (tmp_path / "data" / "requests.db").exists()
    st.close()
    monkeypatch.setattr(bot_app, "STORE", None)


def test_module_importable_by_path():
    """`python bot/app.py` тоже должен работать — путь к пакету подставляется вручную."""
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, "-c",
                        "import runpy, sys; sys.argv=['bot/app.py']; "
                        "runpy.run_path('bot/app.py', run_name='__main__')"],
                       cwd=root, capture_output=True, text=True)
    # без токена модуль должен отработать и вернуть понятную ошибку, а не упасть импортом
    assert "BOT_TOKEN" in (r.stdout + r.stderr)
