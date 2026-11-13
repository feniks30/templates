"""Лимиты и доступ: бот отвечает только тем, кому надо, и не чаще, чем надо.

Нужны две вещи:
  * на время показа — «белый список» из нескольких id, чтобы демо не стало публичным ботом;
  * частота — чтобы один человек не мог засыпать бота и заодно не упереться в лимиты Telegram.
"""
from __future__ import annotations

import time
from collections import deque


class RateLimiter:
    """Не больше `per_minute` сообщений в минуту на пользователя (по умолчанию 8)."""

    def __init__(self, per_minute: int = 8, window: float = 60.0):
        self.per_minute = max(1, per_minute)
        self.window = window
        self._hits: dict[int, deque] = {}

    def allow(self, user_id: int, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        q = self._hits.setdefault(user_id, deque())
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True

    def reset(self, user_id: int | None = None) -> None:
        if user_id is None:
            self._hits.clear()
        else:
            self._hits.pop(user_id, None)


class Access:
    """Белый список на время показа. Пустой список = демо открыто всем."""

    def __init__(self, allowed: set[int] | list[int] | None = None, open_demo: bool = True):
        self.allowed = set(allowed or [])
        self.open_demo = open_demo or not self.allowed

    def check(self, user_id: int) -> tuple[bool, str]:
        if self.open_demo and not self.allowed:
            return True, ""
        if user_id in self.allowed:
            return True, ""
        return False, ("Это демонстрационный бот и сейчас он показывает пример одному человеку. "
                       "Напишите исполнителю — включим показ для вас.")


def read_ids(raw: str) -> set[int]:
    """«123, 456 789» → {123, 456, 789}; мусор не ломает разбор."""
    out = set()
    for chunk in str(raw or "").replace(";", ",").replace(" ", ",").split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            out.add(int(chunk))
    return out
