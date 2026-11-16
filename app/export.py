"""Выгрузка результатов проверки в CSV (открывается в Excel)."""
from __future__ import annotations

import csv
import io

from schemas import RecordResult, Stance

HEADER = ["person", "event_type", "date", "verdict", "confidence",
          "supporting_sources", "refuting_sources", "error"]


def results_to_csv(results: list[RecordResult]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(HEADER)
    for r in results:
        sup = sum(e.stance is Stance.SUPPORTS for e in r.evidence)
        ref = sum(e.stance is Stance.REFUTES for e in r.evidence)
        writer.writerow([
            r.record.person, r.record.event_type, r.record.date,
            r.verdict.value if r.verdict else "", f"{r.confidence:.2f}" if r.verdict else "",
            sup, ref, r.error or "",
        ])
    return buf.getvalue().encode("utf-8-sig")
