"""Контракт между интерфейсом и пайплайном агента.

Агент принимает список записей (строк таблицы) и отдаёт поток событий.
Интерфейс умеет показывать только эти типы, поэтому реальный пайплайн
подключается через `agent_api.check_records`, а интерфейс менять не нужно.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    SUPPORTED = "supported"              # подтверждается
    REFUTED = "refuted"                  # опровергается
    NOT_ENOUGH_INFO = "not_enough_info"  # недостаточно данных
    CONFLICT = "conflict"                # источники противоречат друг другу


class Stance(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"


@dataclass
class Record:
    """Одна запись-событие из проверяемой таблицы."""
    id: int
    person: str
    event_type: str
    date: str
    source_url: str = ""
    quote: str = ""


@dataclass
class Evidence:
    """Свидетельство: фрагмент источника за или против записи."""
    url: str
    title: str
    stance: Stance
    reliability: float  # 0..1, оценка надёжности источника
    quote: str = ""


@dataclass
class RecordResult:
    record: Record
    verdict: Verdict | None = None
    confidence: float = 0.0  # 0..1
    evidence: list[Evidence] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)  # «как агент пришёл к выводу»
    error: str | None = None  # если запись проверить не удалось


@dataclass
class GapItem:
    """Событие, найденное в документах, но отсутствующее в таблице (трек A)."""
    person: str
    event_type: str
    date: str
    source_url: str = ""
    quote: str = ""


# --- события потока ---
@dataclass
class StatusEvent:
    message: str


@dataclass
class ResultEvent:
    result: RecordResult


@dataclass
class GapEvent:
    gaps: list[GapItem]


Event = StatusEvent | ResultEvent | GapEvent
