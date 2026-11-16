"""Разбор и проверка пользовательского ввода (CSV или одна запись)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from schemas import Record

MAX_ROWS = 50
MAX_BYTES = 1_000_000
MAX_FIELD = 1000
REQUIRED = ("person", "event_type", "date")

# допустимые названия столбцов -> внутренние имена
ALIASES = {
    "person": "person", "человек": "person", "персона": "person", "имя": "person",
    "event_type": "event_type", "event": "event_type", "тип_события": "event_type", "событие": "event_type",
    "date": "date", "дата": "date",
    "source_url": "source_url", "source": "source_url", "источник": "source_url", "ссылка": "source_url",
    "quote": "quote", "цитата": "quote",
}


class InputError(ValueError):
    """Ошибка ввода: текст можно безопасно показать пользователю."""


@dataclass
class ParseResult:
    records: list[Record] = field(default_factory=list)
    skipped: list[tuple[int, str]] = field(default_factory=list)  # (номер строки, причина)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise InputError("Не удалось прочитать файл. Сохраните таблицу как CSV в кодировке UTF-8.")


def _norm_header(name: str) -> str:
    return ALIASES.get(name.strip().lower().replace(" ", "_"), "")


def parse_records_csv(data: bytes) -> ParseResult:
    if not data.strip():
        raise InputError("Файл пустой.")
    if len(data) > MAX_BYTES:
        raise InputError("Файл слишком большой: максимум 1 МБ.")
    text = _decode(data)
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = list(reader)
    if not rows:
        raise InputError("Файл пустой.")

    header = [_norm_header(h) for h in rows[0]]
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        raise InputError(
            "В таблице нет обязательных столбцов: " + ", ".join(missing)
            + ". Нужны: person (человек), event_type (тип события), date (дата); "
              "необязательные: source_url (источник), quote (цитата)."
        )

    result = ParseResult()
    for line_no, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue  # пустая строка
        values = {name: row[i].strip() for i, name in enumerate(header) if name and i < len(row)}
        absent = [c for c in REQUIRED if not values.get(c)]
        if absent:
            result.skipped.append((line_no, "пусто: " + ", ".join(absent)))
            continue
        if any(len(v) > MAX_FIELD for v in values.values()):
            result.skipped.append((line_no, "слишком длинное значение"))
            continue
        result.records.append(Record(
            id=len(result.records) + 1,
            person=values["person"], event_type=values["event_type"], date=values["date"],
            source_url=values.get("source_url", ""), quote=values.get("quote", ""),
        ))
    if not result.records:
        raise InputError("В таблице нет ни одной корректной записи.")
    if len(result.records) > MAX_ROWS:
        raise InputError(
            f"Слишком много записей ({len(result.records)}). За один запуск можно проверить не больше {MAX_ROWS}."
        )
    return result


def make_single_record(person: str, event_type: str, date: str, source_url: str = "", quote: str = "") -> Record:
    values = {"person": person, "event_type": event_type, "date": date}
    labels = {"person": "человек", "event_type": "тип события", "date": "дата"}
    empty = [labels[k] for k, v in values.items() if not v.strip()]
    if empty:
        raise InputError("Заполните обязательные поля: " + ", ".join(empty) + ".")
    if any(len(v) > MAX_FIELD for v in (person, event_type, date, source_url, quote)):
        raise InputError("Одно из полей слишком длинное.")
    return Record(1, person.strip(), event_type.strip(), date.strip(), source_url.strip(), quote.strip())
