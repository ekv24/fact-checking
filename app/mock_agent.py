"""ЗАГЛУШКА агента: имитирует поток событий, чтобы делать интерфейс
независимо от пайплайна. Вердикты случайные и ничего не проверяют."""
from __future__ import annotations

import hashlib
import time
from typing import Iterator

from schemas import (Evidence, Event, GapEvent, GapItem, Record, RecordResult,
                     ResultEvent, Stance, StatusEvent, Verdict)

DELAY = 0.4  # секунд на шаг; в тестах ставится в 0


def _ev(n: int, stance: Stance, reliability: float, record: Record) -> Evidence:
    return Evidence(
        url=f"https://example.org/doc-{n}",
        title=f"Документ {n} (заглушка)",
        stance=stance,
        reliability=reliability,
        quote=f"Фрагмент документа о событии «{record.event_type}» ({record.person}).",
    )


def check_records(records: list[Record]) -> Iterator[Event]:
    verdicts = [Verdict.SUPPORTED, Verdict.REFUTED, Verdict.NOT_ENOUGH_INFO, Verdict.CONFLICT]
    for rec in records:
        yield StatusEvent(f"Запись {rec.id} из {len(records)}: ищу свидетельства…")
        time.sleep(DELAY)
        h = int(hashlib.md5(f"{rec.person}{rec.event_type}{rec.date}".encode()).hexdigest(), 16)
        if h % 9 == 0:  # имитация сбоя на одной записи
            yield ResultEvent(RecordResult(record=rec, error="Поиск не ответил вовремя."))
            continue
        verdict = verdicts[h % 4]
        evidence: list[Evidence] = []
        if verdict in (Verdict.SUPPORTED, Verdict.CONFLICT):
            evidence.append(_ev(1, Stance.SUPPORTS, 0.9, rec))
        if verdict in (Verdict.REFUTED, Verdict.CONFLICT):
            evidence.append(_ev(2, Stance.REFUTES, 0.7, rec))
        yield ResultEvent(RecordResult(
            record=rec, verdict=verdict, confidence=0.5 + (h % 45) / 100, evidence=evidence,
            steps=[f"Извлечены события человека «{rec.person}» из документов",
                   "Найдено 4 фрагмента, оставлено 2 по надёжности источника",
                   "Сопоставлены дата и участники события с записью",
                   f"Вердикт: {verdict.value}"],
        ))
    yield StatusEvent("Ищу возможные пропуски в таблице…")
    time.sleep(DELAY)
    persons = list(dict.fromkeys(r.person for r in records))[:2]
    yield GapEvent([
        GapItem(person=p, event_type="рождение ребёнка", date="1958",
                source_url="https://example.org/doc-3",
                quote="Фрагмент документа, где событие есть, а в таблице его нет (заглушка).")
        for p in persons
    ])
