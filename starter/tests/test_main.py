"""Тесты {{NAME}}: запускаются без сети и без ключей — `python -m pytest -q`."""
from src.main import run


def test_run_strips_spaces():
    assert run("  привет  ") == "привет"


def test_run_accepts_empty():
    assert run("") == ""
