import mock_agent
from streamlit.testing.v1 import AppTest
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py"


def make_app() -> AppTest:
    mock_agent.DELAY = 0
    return AppTest.from_file(str(APP), default_timeout=30).run()


def test_start_screen_has_hint():
    at = make_app()
    assert not at.exception
    assert any("Загрузите CSV" in i.value for i in at.info)


def test_sample_full_flow():
    at = make_app()
    at.button(key="load_sample").click().run()
    at.button(key="check_btn").click().run()
    assert not at.exception
    assert len(at.metric) == 4
    assert at.get("download_button")


def test_single_record_validation_error():
    at = make_app()
    # отправка пустой формы
    form_submit = [b for b in at.button if b.label == "Добавить запись"][0]
    form_submit.click().run()
    assert any("обязательные" in e.value for e in at.error)


def test_pipeline_crash_is_handled(monkeypatch):
    import agent_api

    def broken(_records):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    monkeypatch.setattr(agent_api, "check_records", broken)
    at = make_app()
    at.button(key="load_sample").click().run()
    at.button(key="check_btn").click().run()
    assert not at.exception
    assert any("ошибка" in e.value for e in at.error)
