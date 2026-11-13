"""Логика демо-бота «Заявки» — без Telegram, чтобы её можно было проверить тестами.

Разделение простое и осознанное:
  core.py  — что бот делает (состояния, проверки, база);
  app.py   — как он это говорит (aiogram, кнопки, webhook).

Благодаря этому весь диалог проверяется обычным pytest за доли секунды, без токена и сети.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

STATUS_NEW = "new"
STATUS_WORK = "in_progress"
STATUS_DONE = "done"

STATUS_LABEL = {
    STATUS_NEW: "новая",
    STATUS_WORK: "в работе",
    STATUS_DONE: "сделано",
}

# Кнопки, которые бот показывает на каждом шаге (app.py превращает их в reply-клавиатуру).
BTN_SEND = "Отправить"
BTN_CANCEL = "Отменить"
BTN_MY = "Мои заявки"
BTN_NEW = "Новая заявка"
BTN_LATER = "Уточню позже"


@dataclass
class Request:
    id: int
    user_id: int
    name: str
    task: str
    deadline: str
    status: str
    created_at: str

    def as_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "task": self.task,
                "deadline": self.deadline, "status": self.status,
                "status_label": STATUS_LABEL.get(self.status, self.status),
                "created_at": self.created_at}


# ---------------------------------------------------------------- проверки
def valid_name(text: str) -> bool:
    """Имя: хотя бы две буквы, не набор символов, не цифры вместо имени."""
    t = (text or "").strip()
    if len(t) < 2 or len(t) > 60:
        return False
    letters = sum(1 for ch in t if ch.isalpha())
    return letters >= 2


def valid_task(text: str) -> bool:
    """Задача: содержит смысл — 10+ символов и хотя бы три слова."""
    t = (text or "").strip()
    if len(t) < 10 or len(t) > 600:
        return False
    return len(t.split()) >= 3


def parse_deadline(text: str, today: datetime | None = None) -> str:
    """Срок из свободного текста: «3 дня», «неделя», «до пятницы», «уточню позже»."""
    today = today or datetime.now()
    t = (text or "").strip().lower()
    if not t:
        return "уточним позже"
    if "позже" in t or "не знаю" in t or "потом" in t:
        return "уточним позже"
    if "недел" in t:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    days = {"один": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5,
            "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10}
    for word, num in days.items():
        if word in t:
            return (today + timedelta(days=num)).strftime("%Y-%m-%d")
    digits = "".join(ch for ch in t if ch.isdigit())
    if digits:
        n = max(1, min(90, int(digits)))
        return (today + timedelta(days=n)).strftime("%Y-%m-%d")
    if "пятниц" in t:
        shift = (4 - today.weekday()) % 7 or 7
        return (today + timedelta(days=shift)).strftime("%Y-%m-%d")
    return t[:40]


# ---------------------------------------------------------------- база
class Store:
    """SQLite: заявки. Одна таблица, никакой магии — демо должно быть понятным."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                task TEXT NOT NULL,
                deadline TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            )""")
        self.conn.commit()

    def add(self, user_id: int, name: str, task: str, deadline: str,
            now: datetime | None = None) -> int:
        now = now or datetime.now()
        cur = self.conn.execute(
            "INSERT INTO requests (user_id, name, task, deadline, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name.strip(), task.strip(), deadline.strip(),
             STATUS_NEW, now.strftime("%Y-%m-%d %H:%M")))
        self.conn.commit()
        return int(cur.lastrowid)

    def get(self, request_id: int) -> Request | None:
        row = self.conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        return Request(**dict(row)) if row else None

    def last_for_user(self, user_id: int) -> Request | None:
        row = self.conn.execute(
            "SELECT * FROM requests WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)).fetchone()
        return Request(**dict(row)) if row else None

    def find_recent_same(self, user_id: int, name: str, task: str, deadline: str,
                         seconds: int = 120, now: datetime | None = None) -> Request | None:
        """Двойной клик не должен создавать вторую заявку."""
        now = now or datetime.now()
        row = self.conn.execute(
            "SELECT * FROM requests WHERE user_id = ? AND name = ? AND task = ? AND deadline = ?"
            " ORDER BY id DESC LIMIT 1",
            (user_id, name.strip(), task.strip(), deadline.strip())).fetchone()
        if not row:
            return None
        created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M")
        if now - created <= timedelta(seconds=seconds):
            return Request(**dict(row))
        return None

    def list_for_user(self, user_id: int) -> list:
        rows = self.conn.execute(
            "SELECT * FROM requests WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        return [Request(**dict(r)) for r in rows]

    def set_status(self, request_id: int, status: str) -> bool:
        if status not in STATUS_LABEL:
            raise ValueError(f"неизвестный статус: {status}")
        cur = self.conn.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
        self.conn.commit()
        return cur.rowcount > 0

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0])

    def close(self) -> None:
        self.conn.close()


# ---------------------------------------------------------------- диалог
@dataclass
class Reply:
    """Ответ бота: текст, кнопки и новое состояние — app.py только отправляет."""
    text: str
    buttons: list
    state: str
    request_id: int | None = None


class Dialog:
    """Состояния диалога: start → name → task → deadline → confirm → done."""

    STEPS = ("start", "name", "task", "deadline", "confirm", "done")

    def __init__(self, store: Store, user_id: int, now: datetime | None = None):
        self.store = store
        self.user_id = user_id
        self.state = "start"
        self.data = {"name": "", "task": "", "deadline": ""}
        self.now = now

    # --- вспомогательное
    def _reset(self) -> None:
        self.state = "start"
        self.data = {"name": "", "task": "", "deadline": ""}

    def summary(self) -> str:
        d = self.data
        return (f"Проверьте заявку:\n\n"
                f"Имя: {d['name']}\n"
                f"Задача: {d['task']}\n"
                f"Срок: {d['deadline']}")

    # --- основной вход
    def handle(self, text: str) -> Reply:
        t = (text or "").strip()
        low = t.lower()

        if low.startswith("/start") or low in ("начать", "заново"):
            self._reset()
            self.state = "name"
            return Reply("Здравствуйте! Это демо-бот заявок.\nКак вас зовут?",
                         [], "name")

        if low == BTN_MY.lower() or low == "мои заявки":
            return self._my_requests()

        if low == BTN_NEW.lower() or low == "новая заявка":
            self._reset()
            self.state = "name"
            return Reply("Хорошо, новая заявка. Как вас зовут?", [], "name")

        if self.state == "done":
            last = self.store.last_for_user(self.user_id)
            return Reply("Заявка уже принята. Хотите новую? Нажмите «Новая заявка».",
                         [BTN_NEW, BTN_MY], "done",
                         request_id=last.id if last else None)

        if self.state == "name":
            if not valid_name(t):
                return Reply("Имя нужно настоящее — хотя бы две буквы. Как вас зовут?", [], "name")
            self.data["name"] = t
            self.state = "task"
            return Reply(f"{t}, что нужно сделать? Опишите задачу в двух-трёх словах.",
                         [], "task")

        if self.state == "task":
            if not valid_task(t):
                return Reply("Опишите чуть подробнее: что сделать и зачем — хотя бы три слова.",
                             [], "task")
            self.data["task"] = t
            self.state = "deadline"
            return Reply("Когда нужно? Можно написать «3 дня», «неделя» или «уточню позже».",
                         [BTN_LATER], "deadline")

        if self.state == "deadline":
            self.data["deadline"] = parse_deadline(t, self.now)
            self.state = "confirm"
            return Reply(self.summary(), [BTN_SEND, BTN_CANCEL], "confirm")

        if self.state == "confirm":
            if low in (BTN_CANCEL.lower(), "нет", "отмена"):
                self._reset()
                return Reply("Отменил. Если что-то нужно — нажмите «Новая заявка».",
                             [BTN_NEW], "start")
            if low in (BTN_SEND.lower(), "да", "отправить", "готово"):
                return self._save()
            return Reply("Отправить заявку? Нажмите «Отправить» или «Отменить».",
                         [BTN_SEND, BTN_CANCEL], "confirm")

        # бот не ждал ответа: начинаем сначала, но написанное не выбрасываем —
        # человек, который сразу написал имя вместо /start, не должен повторять дважды
        self._reset()
        self.state = "name"
        return self.handle(t)

    # --- сохранение
    def _save(self) -> Reply:
        d = self.data
        same = self.store.find_recent_same(self.user_id, d["name"], d["task"], d["deadline"],
                                           now=self.now)
        if same:
            self.state = "done"
            return Reply(f"Эта заявка уже принята — номер {same.id}, статус «"
                         f"{STATUS_LABEL.get(same.status, same.status)}».", [BTN_NEW, BTN_MY],
                         "done", request_id=same.id)
        rid = self.store.add(self.user_id, d["name"], d["task"], d["deadline"], now=self.now)
        self.state = "done"
        return Reply(f"Заявка №{rid} принята. Статус — «{STATUS_LABEL[STATUS_NEW]}».\n"
                     f"Ответ придёт в этот чат.", [BTN_NEW, BTN_MY], "done", request_id=rid)

    # --- список
    def _my_requests(self) -> Reply:
        rows = self.store.list_for_user(self.user_id)
        if not rows:
            return Reply("Заявок пока нет. Нажмите «Новая заявка» — приму за минуту.",
                         [BTN_NEW], "start")
        lines = ["Ваши заявки:", ""]
        for r in rows[:10]:
            lines.append(f"№{r.id} · {STATUS_LABEL.get(r.status, r.status)} · "
                         f"{r.deadline}\n   {r.task[:60]}")
        return Reply("\n".join(lines), [BTN_NEW], "start")
