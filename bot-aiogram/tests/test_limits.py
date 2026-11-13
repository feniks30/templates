"""Лимиты и доступ: демо не должно стать публичным ботом и не должно упираться в лимиты Telegram."""
from __future__ import annotations

from bot.limits import Access, RateLimiter, read_ids


# ---------------------------------------------------------------- частота
def test_rate_limit_allows_within_limit():
    rl = RateLimiter(per_minute=3)
    assert [rl.allow(1, now=t) for t in (0, 1, 2)] == [True, True, True]


def test_rate_limit_blocks_after_limit():
    rl = RateLimiter(per_minute=3)
    for t in (0, 1, 2):
        rl.allow(1, now=t)
    assert rl.allow(1, now=3) is False


def test_rate_limit_window_slides():
    rl = RateLimiter(per_minute=2, window=60)
    assert rl.allow(1, now=0)
    assert rl.allow(1, now=1)
    assert rl.allow(1, now=2) is False
    assert rl.allow(1, now=61) is True          # старое сообщение вышло из окна


def test_rate_limit_is_per_user():
    rl = RateLimiter(per_minute=1)
    assert rl.allow(1, now=0)
    assert rl.allow(2, now=0) is True
    assert rl.allow(1, now=1) is False


def test_rate_limit_reset():
    rl = RateLimiter(per_minute=1)
    rl.allow(1, now=0)
    rl.reset(1)
    assert rl.allow(1, now=1)


# ---------------------------------------------------------------- доступ
def test_open_demo_allows_everyone():
    acc = Access(set(), open_demo=True)
    ok, why = acc.check(999)
    assert ok and why == ""


def test_whitelist_blocks_strangers():
    acc = Access({1, 2})
    assert acc.check(1)[0] is True
    assert acc.check(7)[0] is False
    assert "демонстрационный" in acc.check(7)[1]


def test_empty_whitelist_opens_demo():
    acc = Access([])                     # пустой список = показ открыт
    assert acc.check(42)[0] is True


def test_read_ids_parses_dirty_input():
    assert read_ids("123, 456;789 1011") == {123, 456, 789, 1011}
    assert read_ids("abc, 5, -3, ") == {5}
    assert read_ids("") == set()
