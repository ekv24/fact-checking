"""Единственная точка, через которую интерфейс вызывает агента.

Чтобы подключить настоящий пайплайн, замените тело `check_records`:
функция принимает список `Record` и возвращает итератор событий из schemas.py
(`StatusEvent`, `ResultEvent` по одному на запись, в конце `GapEvent`).
"""
from __future__ import annotations

from typing import Iterator

from mock_agent import check_records as _mock_check_records
from schemas import Event, Record


def check_records(records: list[Record]) -> Iterator[Event]:
    return _mock_check_records(records)  # TODO: заменить на реальный пайплайн
