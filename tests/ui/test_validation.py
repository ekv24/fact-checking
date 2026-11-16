import pytest

from validation import InputError, make_single_record, parse_records_csv

GOOD = "person,event_type,date,source_url,quote\nМария,брак,1952,http://x,цит\n".encode("utf-8")


def test_parse_ok():
    res = parse_records_csv(GOOD)
    assert len(res.records) == 1
    assert res.records[0].person == "Мария" and res.records[0].id == 1


def test_semicolon_and_cp1251_and_russian_headers():
    data = "человек;тип_события;дата\nИван;брак;1948\n".encode("cp1251")
    res = parse_records_csv(data)
    assert res.records[0].event_type == "брак"


def test_missing_column():
    with pytest.raises(InputError, match="date"):
        parse_records_csv("person,event_type\nа,б\n".encode())


def test_skips_incomplete_rows_and_reports_line():
    data = "person,event_type,date\nМария,брак,1952\n,брак,1950\n".encode()
    res = parse_records_csv(data)
    assert len(res.records) == 1
    assert res.skipped and res.skipped[0][0] == 3


def test_all_rows_bad():
    with pytest.raises(InputError):
        parse_records_csv("person,event_type,date\n,,\n,брак,\n".encode())


def test_empty_file():
    with pytest.raises(InputError):
        parse_records_csv(b"  ")


def test_too_many_rows():
    rows = "\n".join(f"П{i},брак,19{i % 90:02d}" for i in range(60))
    with pytest.raises(InputError, match="Слишком много"):
        parse_records_csv(("person,event_type,date\n" + rows).encode())


def test_single_record_validation():
    with pytest.raises(InputError):
        make_single_record("", "брак", "1952")
    assert make_single_record(" Мария ", "брак", "1952").person == "Мария"
