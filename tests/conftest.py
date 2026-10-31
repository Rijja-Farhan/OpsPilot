import pytest

from opspilot import fake_llm


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """Every test runs against the fake provider with an isolated trace file."""
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("OPSPILOT_TRACE_PATH", str(tmp_path / "trace.jsonl"))
    fake_llm.queue_responses()
    yield
    fake_llm.queue_responses()
