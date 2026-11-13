"""Тесты логики демо-бота: без Telegram, без сети, за доли секунды."""
from __future__ import annotations

from datetime import datetime

import pytest

from bot.core import (BTN_CANCEL, BTN_LATER, BTN_MY, BTN_NEW, BTN_SEND, STATUS_DONE,
                      STATUS_NEW, STATUS_WORK, Dialog, Store, parse_deadline, valid_name,
                      valid_task)

NOW = datetime(2026, 11, 11, 10, 0)


# ---------------------------------------------------------------- проверки полей
@pytest.mark.parametrize("value", ["Иван", "Оля", "Jean-Luc", "Анна Мария"])
def test_names_accepted(value):
    assert valid_name(value)


@pytest.mark.parametrize("value", ["", "А", "12", "!!!", "-"])
def test_names_rejected(value):
    assert not valid_name(value)


@pytest.mark.parametrize("value", [
    "нужен парсер цен конкурента",
    "сделать бота для заявок",
    "починить выгрузку в Excel",
])
def test_tasks_accepted(value):
    assert valid_task(value)


@pytest.mark.parametrize("value", ["нужно", "1234567890", "парсер", ""])
def test_tasks_rejected(value):
    assert not valid_task(value)


# ---------------------------------------------------------------- сроки
def test_deadline_days_word():
    assert parse_deadline("три дня", NOW) == "2026-11-14"


def test_deadline_digits():
    assert parse_deadline("за 5 дней", NOW) == "2026-11-16"


def test_deadline_week():
    assert parse_deadline("неделя", NOW) == "2026-11-18"


def test_deadline_friday():
    # 11.11.2026 — среда, ближайшая пятница = 13.11
    assert parse_deadline("до пятницы", NOW) == "2026-11-13"


@pytest.mark.parametrize("value", ["уточню позже", "не знаю", "", "потом"])
def test_deadline_later(value):
    assert parse_deadline(value, NOW) == "уточним позже"


def test_deadline_limits_absurd_numbers():
    assert parse_deadline("365 дней", NOW) == "2027-02-09"      # 11.11.2026 + 90 дней — предел


# ---------------------------------------------------------------- база
def test_store_add_and_get():
    store = Store(":memory:")
    rid = store.add(1, "Иван", "нужен парсер цен конкурента", "2026-11-14", now=NOW)
    row = store.get(rid)
    assert row and row.status == STATUS_NEW and row.name == "Иван"
    assert store.count() == 1


def test_store_statuses():
    store = Store(":memory:")
    rid = store.add(1, "Иван", "нужен парсер цен конкурента", "2026-11-14", now=NOW)
    assert store.set_status(rid, STATUS_WORK) is True
    assert store.get(rid).status == STATUS_WORK
    assert store.set_status(rid, STATUS_DONE) is True
    assert store.set_status(999, STATUS_DONE) is False
    with pytest.raises(ValueError):
        store.set_status(rid, "что-то")


def test_second_click_does_not_create_duplicate():
    store = Store(":memory:")
    store.add(1, "Иван", "нужен парсер цен конкурента", "2026-11-14", now=NOW)
    same = store.find_recent_same(1, "Иван", "нужен парсер цен конкурента", "2026-11-14", now=NOW)
    assert same is not None and same.id == 1


def test_old_request_does_not_block_new_one():
    store = Store(":memory:")
    store.add(1, "Иван", "нужен парсер цен конкурента", "2026-11-14",
              now=datetime(2026, 11, 11, 8, 0))
    same = store.find_recent_same(1, "Иван", "нужен парсер цен конкурента", "2026-11-14",
                                  now=NOW, seconds=120)
    assert same is None


def test_store_persists_to_file(tmp_path):
    path = tmp_path / "db" / "requests.db"
    s1 = Store(path)
    rid = s1.add(7, "Оля", "сделать бота для заявок", "2026-11-18", now=NOW)
    s1.close()
    s2 = Store(path)
    assert s2.get(rid).name == "Оля"


# ---------------------------------------------------------------- диалог
def drive(dialog: Dialog, *lines: str):
    replies = [dialog.handle(line) for line in lines]
    return replies


def test_full_dialog_creates_request():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    r1 = d.handle("/start")
    assert "как вас зовут" in r1.text.lower()
    r2 = d.handle("Иван")
    assert "что нужно сделать" in r2.text.lower()
    r3 = d.handle("нужен парсер цен конкурента")
    assert "когда" in r3.text.lower()
    r4 = d.handle("3 дня")
    assert "Проверьте заявку" in r4.text and BTN_SEND in r4.buttons
    r5 = d.handle(BTN_SEND)
    assert "принята" in r5.text and r5.request_id == 1
    assert store.count() == 1
    assert store.get(1).deadline == "2026-11-14"


def test_bad_name_is_reasked_without_moving_on():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    d.handle("/start")
    r = d.handle("1")
    assert "две буквы" in r.text.lower()
    assert d.state == "name"
    assert store.count() == 0


def test_short_task_is_reasked():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    drive(d, "/start", "Иван")
    r = d.handle("парсер")
    assert "подробнее" in r.text.lower()
    assert d.state == "task"


def test_cancel_resets_dialog():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    drive(d, "/start", "Иван", "нужен парсер цен конкурента", "3 дня")
    r = d.handle(BTN_CANCEL)
    assert "отменил" in r.text.lower()
    assert d.state == "start"
    assert store.count() == 0


def test_later_button_sets_placeholder_deadline():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    drive(d, "/start", "Иван", "нужен парсер цен конкурента")
    r = d.handle(BTN_LATER)
    assert "уточним позже" in r.text


def test_double_send_is_idempotent():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    drive(d, "/start", "Иван", "нужен парсер цен конкурента", "3 дня", BTN_SEND)
    again = d.handle(BTN_SEND)
    assert "уже принята" in again.text.lower()
    assert store.count() == 1


def test_my_requests_lists_only_mine():
    store = Store(":memory:")
    d1 = Dialog(store, 1, now=NOW)
    drive(d1, "/start", "Иван", "нужен парсер цен конкурента", "3 дня", BTN_SEND)
    d2 = Dialog(store, 2, now=NOW)
    drive(d2, "/start", "Оля", "сделать бота для заявок", "неделя", BTN_SEND)
    reply = d1.handle(BTN_MY)
    assert "№1" in reply.text and "бот" not in reply.text.split("№1")[1][:40]
    assert store.count() == 2


def test_text_without_start_is_taken_as_name():
    """Написал имя сразу, без /start — бот принимает его, а не просит повторить."""
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    r = d.handle("Иван")
    assert "что нужно сделать" in r.text.lower()
    assert d.state == "task"


def test_my_requests_when_empty():
    store = Store(":memory:")
    d = Dialog(store, 5, now=NOW)
    r = d.handle(BTN_MY)
    assert "пока нет" in r.text.lower()
    assert BTN_NEW in r.buttons


def test_new_button_starts_over():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    drive(d, "/start", "Иван", "нужен парсер цен конкурента", "3 дня", BTN_SEND)
    r = d.handle(BTN_NEW)
    assert r.state == "name" and "как вас зовут" in r.text.lower()


def test_message_after_done_does_not_create_garbage():
    store = Store(":memory:")
    d = Dialog(store, 1, now=NOW)
    drive(d, "/start", "Иван", "нужен парсер цен конкурента", "3 дня", BTN_SEND)
    r = d.handle("спасибо")
    assert "уже принята" in r.text.lower()
    assert store.count() == 1
