import pytest

from opspilot import fake_llm


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """Every test runs against the fake provider with an isolated trace file."""
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("OPSPILOT_TRACE_PATH", str(tmp_path / "trace.jsonl"))
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "hash")
    monkeypatch.setenv("OPSPILOT_MEMORY_PATH", str(tmp_path / "memory.jsonl"))
    monkeypatch.setenv("OPSPILOT_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("OPSPILOT_RUN_TRACE_DIR", str(tmp_path / "run-traces"))
    # No built index: policies fall back to A1 BM25 over data/kb/ unless a test builds its own index.
    monkeypatch.setenv("OPSPILOT_INDEX_DIR", str(tmp_path / "no-index"))
    fake_llm.queue_responses()
    yield
    fake_llm.queue_responses()
