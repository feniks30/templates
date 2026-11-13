"""{{NAME}} — точка входа.

Правило: сюда попадает только то, что можно проверить тестом.
Всё, что требует сети, ключей или телефона, живёт за отдельной функцией с явными аргументами.
"""
from __future__ import annotations

import argparse


def run(text: str) -> str:
    """Заменить на первую настоящую операцию проекта."""
    return (text or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(prog="{{SLUG}}")
    ap.add_argument("text", nargs="?", default="", help="что обработать")
    a = ap.parse_args()
    print(run(a.text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
