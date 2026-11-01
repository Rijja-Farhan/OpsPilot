import json

import pytest
from fastapi.testclient import TestClient

from mockapi.main import app


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCKAPI_NOTES_PATH", str(tmp_path / "notes.jsonl"))
    monkeypatch.setenv("MOCKAPI_FAIL_RATE", "0")
    return TestClient(app)


def test_get_ticket(api):
    r = api.get("/tickets/T-1002")
    assert r.status_code == 200 and r.json()["ticket_id"] == "T-1002" and "body" in r.json()


def test_unknown_ticket_404_shape(api):
    r = api.get("/tickets/T-424242")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_found"


def test_search_tickets_filters_and_orders(api):
    body = api.get("/tickets", params={"customer_id": "c-17", "limit": 3}).json()
    assert 0 < len(body["tickets"]) <= 3 and body["total"] >= len(body["tickets"])
    assert all(t["customer_id"] == "C-17" for t in body["tickets"])
    dates = [t["created_at"] for t in body["tickets"]]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 51}, {"status": "bogus"}, {"category": "bogus"}])
def test_search_tickets_rejects_bad_params(api, params):
    r = api.get("/tickets", params=params)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_argument"


def test_customer_and_transactions(api):
    assert api.get("/customers/C-1").json()["customer_id"] == "C-1"
    body = api.get("/customers/C-1/transactions", params={"limit": 2}).json()
    assert len(body["transactions"]) <= 2
    dates = [t["date"] for t in body["transactions"]]
    assert dates == sorted(dates, reverse=True)


def test_transactions_since_filter(api):
    rows = api.get("/customers/C-1/transactions", params={"since": "2999-01-01"}).json()
    assert rows["transactions"] == []


def test_unknown_customer_404(api):
    assert api.get("/customers/C-999999").status_code == 404
    assert api.get("/customers/C-999999/transactions").status_code == 404


def test_add_note_appends(api, tmp_path):
    r = api.post("/tickets/T-1002/notes", json={"note": "called the customer"})
    assert r.status_code == 201
    api.post("/tickets/T-1002/notes", json={"note": "second"})
    lines = (tmp_path / "notes.jsonl").read_text().splitlines()
    assert [json.loads(x)["note"] for x in lines] == ["called the customer", "second"]


@pytest.mark.parametrize("body", [{"note": ""}, {"note": "x" * 501}, {}])
def test_add_note_validation(api, body):
    assert api.post("/tickets/T-1002/notes", json=body).status_code == 422


def test_add_note_unknown_ticket(api):
    assert api.post("/tickets/T-424242/notes", json={"note": "hi"}).status_code == 404


def test_policies_search_current_only_by_default(api):
    docs = api.get("/policies", params={"query": "dispute window"}).json()["policies"]
    assert docs and all(d["status"] == "current" for d in docs)
    with_old = api.get("/policies", params={"query": "dispute window", "include_superseded": True}).json()["policies"]
    assert any(d["status"] == "superseded" for d in with_old)


def test_get_policy_by_slug(api):
    assert api.get("/policies/fees-schedule-v2").json()["version"] == 2
    assert api.get("/policies/nope").status_code == 404


def test_simulated_outage(api, monkeypatch):
    monkeypatch.setenv("MOCKAPI_FAIL_RATE", "1")
    r = api.get("/tickets/T-1002")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "upstream_unavailable"
