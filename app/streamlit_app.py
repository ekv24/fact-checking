"""Интерфейс Fact-checking: проверка таблицы записей-событий.

Запуск из корня репозитория: streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import streamlit as st  # noqa: E402

from agent_api import check_records  # noqa: E402
from export import results_to_csv  # noqa: E402
from schemas import (Evidence, GapEvent, GapItem, Record, RecordResult,  # noqa: E402
                     ResultEvent, Stance, StatusEvent, Verdict)
from validation import InputError, make_single_record, parse_records_csv  # noqa: E402

SAMPLE_PATH = APP_DIR / "sample_data" / "sample_events.csv"

VERDICT_VIEW = {
    Verdict.SUPPORTED: ("Подтверждается", "green", "✅"),
    Verdict.REFUTED: ("Опровергается", "red", "❌"),
    Verdict.NOT_ENOUGH_INFO: ("Недостаточно данных", "orange", "❔"),
    Verdict.CONFLICT: ("Источники противоречат", "violet", "⚠️"),
}


def setup_logging() -> logging.Logger:
    log = logging.getLogger("factcheck.ui")
    if not log.handlers:  # Streamlit перезапускает скрипт, не дублируем обработчики
        log_dir = APP_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        for handler in (logging.FileHandler(log_dir / "app.log", encoding="utf-8"), logging.StreamHandler()):
            handler.setFormatter(fmt)
            log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log


log = setup_logging()


def reliability_label(value: float) -> str:
    return "высокая" if value >= 0.8 else "средняя" if value >= 0.5 else "низкая"


def render_evidence(title: str, items: list[Evidence]) -> None:
    st.markdown(f"**{title}**")
    if not items:
        st.caption("Нет.")
    for e in items:
        st.markdown(f"- [{e.title}]({e.url}) · надёжность: {reliability_label(e.reliability)}")
        if e.quote:
            st.caption(f"«{e.quote}»")


def render_card(r: RecordResult) -> None:
    rec = r.record
    with st.container(border=True):
        st.markdown(f"**{rec.person}** · {rec.event_type} · {rec.date}")
        if rec.quote:
            st.caption(f"В таблице: «{rec.quote}»")
        if r.error:
            st.warning(f"Не удалось проверить запись: {r.error}")
            return
        if r.verdict is None:
            st.info("Вердикт не вынесен.")
            return
        label, color, icon = VERDICT_VIEW[r.verdict]
        st.markdown(f"### {icon} :{color}[{label}]")
        st.progress(min(max(r.confidence, 0.0), 1.0), text=f"Уверенность: {r.confidence:.0%}")
        col_pro, col_con = st.columns(2)
        with col_pro:
            render_evidence("Подтверждают", [e for e in r.evidence if e.stance is Stance.SUPPORTS])
        with col_con:
            render_evidence("Опровергают", [e for e in r.evidence if e.stance is Stance.REFUTES])
        with st.expander("Как агент пришёл к выводу"):
            for i, step in enumerate(r.steps, 1):
                st.markdown(f"{i}. {step}")


def run_check(records: list[Record]) -> tuple[list[RecordResult], list[GapItem]]:
    """Запускает агента с живым прогрессом. Сбой одной записи не роняет остальные."""
    results: dict[int, RecordResult] = {}
    gaps: list[GapItem] = []
    with st.status("Проверяю записи…", expanded=True) as status:
        try:
            for event in check_records(records):
                if isinstance(event, StatusEvent):
                    st.write(event.message)
                elif isinstance(event, ResultEvent):
                    results[event.result.record.id] = event.result
                elif isinstance(event, GapEvent):
                    gaps = event.gaps
            status.update(label="Проверка завершена", state="complete", expanded=False)
        except Exception:
            log.exception("Сбой пайплайна")
            status.update(label="Проверка прервана", state="error")
            st.error("В работе агента произошла ошибка. Показаны уже готовые результаты, попробуйте ещё раз.")
    return sorted(results.values(), key=lambda r: r.record.id), gaps


def input_section() -> None:
    st.subheader("1. Загрузите записи")
    tab_file, tab_one = st.tabs(["Таблица CSV", "Одна запись"])

    with tab_file:
        st.caption("Столбцы: person (человек), event_type (тип события), date (дата) — обязательные; "
                   "source_url (источник), quote (цитата) — по желанию.")
        uploaded = st.file_uploader("CSV-файл", type=["csv"], key="csv_file")
        if uploaded is not None and st.session_state.get("loaded_name") != uploaded.file_id:
            try:
                parsed = parse_records_csv(uploaded.getvalue())
            except InputError as exc:
                st.error(str(exc))
            else:
                st.session_state.update(records=parsed.records, skipped=parsed.skipped,
                                        loaded_name=uploaded.file_id, results=None, gaps=None)
                log.info("Загружен файл: %d записей, пропущено %d", len(parsed.records), len(parsed.skipped))
        if st.button("Загрузить пример", key="load_sample"):
            parsed = parse_records_csv(SAMPLE_PATH.read_bytes())
            st.session_state.update(records=parsed.records, skipped=parsed.skipped,
                                    loaded_name=None, results=None, gaps=None)

    with tab_one:
        with st.form("single_form"):
            person = st.text_input("Человек", placeholder="Мария Иванова")
            event_type = st.text_input("Тип события", placeholder="брак")
            date = st.text_input("Дата", placeholder="1952 или 1952-06-14")
            source_url = st.text_input("Источник (по желанию)")
            quote = st.text_area("Цитата (по желанию)", height=80)
            if st.form_submit_button("Добавить запись"):
                try:
                    rec = make_single_record(person, event_type, date, source_url, quote)
                except InputError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.update(records=[rec], skipped=[], loaded_name=None, results=None, gaps=None)


def preview_section() -> None:
    records: list[Record] = st.session_state.get("records") or []
    if not records:
        st.info("Загрузите CSV, добавьте запись вручную или нажмите «Загрузить пример».")
        return
    st.subheader("2. Проверьте и запустите")
    st.dataframe(
        [{"Человек": r.person, "Событие": r.event_type, "Дата": r.date, "Источник": r.source_url} for r in records],
        hide_index=True, use_container_width=True,
    )
    skipped = st.session_state.get("skipped") or []
    if skipped:
        lines = ", ".join(f"строка {n} ({why})" for n, why in skipped[:10])
        st.warning(f"Пропущено строк: {len(skipped)} — {lines}")
    if st.button("Проверить", type="primary", key="check_btn"):
        log.info("Запуск проверки: %d записей", len(records))
        results, gaps = run_check(records)
        st.session_state.update(results=results, gaps=gaps)


def results_section() -> None:
    results: list[RecordResult] | None = st.session_state.get("results")
    if not results:
        return
    st.subheader("3. Результаты")
    tab_records, tab_gaps = st.tabs(["Записи", "Возможные пропуски"])

    with tab_records:
        checked = [r for r in results if r.verdict is not None]
        cols = st.columns(4)
        for col, verdict in zip(cols, Verdict):
            label = VERDICT_VIEW[verdict][0]
            col.metric(label, sum(r.verdict is verdict for r in checked))
        failed = sum(r.error is not None for r in results)
        if failed:
            st.caption(f"Не удалось проверить записей: {failed}")
        chosen = st.multiselect("Показать вердикты", [VERDICT_VIEW[v][0] for v in Verdict],
                                default=[VERDICT_VIEW[v][0] for v in Verdict], key="verdict_filter")
        for r in results:
            if r.verdict is None or VERDICT_VIEW[r.verdict][0] in chosen:
                render_card(r)
        st.download_button("Скачать результаты (CSV)", data=results_to_csv(results),
                           file_name="factcheck_results.csv", mime="text/csv")

    with tab_gaps:
        gaps: list[GapItem] = st.session_state.get("gaps") or []
        st.caption("События, которые нашлись в документах, но отсутствуют в вашей таблице. "
                   "Это кандидаты для ручной проверки, а не готовые факты.")
        if not gaps:
            st.info("Возможных пропусков не найдено.")
        else:
            st.dataframe(
                [{"Человек": g.person, "Событие": g.event_type, "Дата": g.date,
                  "Источник": g.source_url, "Цитата": g.quote} for g in gaps],
                hide_index=True, use_container_width=True,
            )


def main() -> None:
    st.set_page_config(page_title="Fact-checking", page_icon="🔎", layout="wide")
    st.title("🔎 Fact-checking: проверка таблицы событий")
    st.write("Загрузите таблицу записей (например, события из биографий). Для каждой записи агент ищет "
             "подтверждения и опровержения в независимых источниках, выносит вердикт с цитатами "
             "и подсказывает, каких записей может не хватать.")
    st.caption("Сейчас работает демонстрационная заглушка: вердикты случайные.")
    input_section()
    preview_section()
    results_section()


main()
