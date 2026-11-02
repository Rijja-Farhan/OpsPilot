"""MCP server tests: every tool, every failure path of the error contract. Runs in-process, offline."""
import asyncio
import json

import httpx
import pytest
from mcp import Client

from mcp_server.server import MAX_NOTE, build_server
from mockapi.main import app

TOOLS = {"get_ticket", "search_tickets", "get_customer", "list_transactions", "search_policies", "add_ticket_note",
         "classify_ticket"}


@pytest.fixture(autouse=True)
def api_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCKAPI_NOTES_PATH", str(tmp_path / "notes.jsonl"))
    monkeypatch.setenv("MOCKAPI_FAIL_RATE", "0")


def asgi() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api")


def run(coro_fn, http: httpx.AsyncClient | None = None):
    async def go():
        async with Client(build_server(http or asgi())) as c:
            return await coro_fn(c)
    return asyncio.run(go())


def call(tool: str, args: dict, http=None):
    async def one(c):
        res = await c.call_tool(tool, args)
        return res.is_error, json.loads(res.content[0].text) if res.content[0].text.startswith("{") else res.content[0].text
    return run(one, http)[1]


def assert_error(out, code: str, retryable: bool = False):
    assert set(out) == {"error"} and out["error"]["code"] == code and out["error"]["retryable"] is retryable
    message = out["error"]["message"]
    assert "Traceback" not in message and "://" not in message and "<" not in message


def test_tools_resource_and_schemas():
    async def go(c):
        tools = (await c.list_tools()).tools
        templates = (await c.list_resource_templates()).resource_templates
        return tools, templates
    tools, templates = run(go)
    assert {t.name for t in tools} == TOOLS and len(tools) >= 5
    assert all(t.description and t.input_schema["type"] == "object" for t in tools)
    assert [t.uri_template for t in templates] == ["policy://{slug}"]


def test_get_ticket_ok():
    out = call("get_ticket", {"ticket_id": "t-1002"})
    assert out["ticket_id"] == "T-1002" and out["status"] in {"open", "pending", "resolved", "closed"}


@pytest.mark.parametrize("bad", ["C-17", "1002", "T-", "T-12; drop", ""])
def test_get_ticket_rejects_bad_ids(bad):
    assert_error(call("get_ticket", {"ticket_id": bad}), "invalid_argument")


def test_get_ticket_customer_id_hint_points_to_search():
    assert "search_tickets" in call("get_ticket", {"ticket_id": "C-17"})["error"]["message"]


def test_get_ticket_unknown():
    assert_error(call("get_ticket", {"ticket_id": "T-424242"}), "not_found")


def test_search_tickets_ok_and_limit_default():
    out = call("search_tickets", {"customer_id": "C-17"})
    assert out["total"] >= 1 and len(out["tickets"]) <= 10


@pytest.mark.parametrize("args", [{"limit": 0}, {"limit": 51}, {"status": "bogus"}, {"category": "bogus"},
                                  {"category": "s"}, {"customer_id": "T-1002"}])
def test_search_tickets_validation(args):
    assert_error(call("search_tickets", args), "invalid_argument")


def test_search_tickets_accepts_an_unambiguous_fragment_and_says_so():
    out = call("search_tickets", {"category": "fraud", "limit": 5})
    assert out["filters_normalized"] == {"category": "fraud_security"}
    assert all(t["category"] == "fraud_security" for t in out["tickets"])
    exact = call("search_tickets", {"category": "fraud_security", "limit": 5})
    assert "filters_normalized" not in exact


def test_search_tickets_non_integer_limit_is_rejected_by_sdk():
    async def one(c):
        return await c.call_tool("search_tickets", {"limit": "abc"})
    assert run(one).is_error  # schema validation in the SDK; ToolBox maps this to the contract


def test_get_customer():
    assert call("get_customer", {"customer_id": "C-1"})["customer_id"] == "C-1"
    assert_error(call("get_customer", {"customer_id": "C-999999"}), "not_found")
    assert_error(call("get_customer", {"customer_id": "T-1002"}), "invalid_argument")


def test_list_transactions():
    out = call("list_transactions", {"customer_id": "C-1", "limit": 3})
    assert len(out["transactions"]) <= 3
    assert_error(call("list_transactions", {"customer_id": "C-1", "since": "yesterday"}), "invalid_argument")
    assert_error(call("list_transactions", {"customer_id": "C-1", "limit": 99}), "invalid_argument")
    assert_error(call("list_transactions", {"customer_id": "C-999999"}), "not_found")


def test_search_policies_current_by_default():
    out = call("search_policies", {"query": "dispute filing window"})
    assert out["policies"] and all(p["status"] == "current" for p in out["policies"])
    old = call("search_policies", {"query": "dispute filing window", "include_superseded": True})
    assert any(p["status"] == "superseded" for p in old["policies"])
    assert_error(call("search_policies", {"query": "  "}), "invalid_argument")


def test_add_note_writes_once_and_validates(tmp_path):
    out = call("add_ticket_note", {"ticket_id": "T-1002", "note": "customer called back"})
    assert out["ticket_id"] == "T-1002"
    assert len((tmp_path / "notes.jsonl").read_text().splitlines()) == 1
    assert_error(call("add_ticket_note", {"ticket_id": "T-1002", "note": "x" * (MAX_NOTE + 1)}), "invalid_argument")
    assert_error(call("add_ticket_note", {"ticket_id": "T-1002", "note": "   "}), "invalid_argument")
    assert_error(call("add_ticket_note", {"ticket_id": "T-424242", "note": "hi"}), "not_found")
    assert len((tmp_path / "notes.jsonl").read_text().splitlines()) == 1  # failures wrote nothing


def test_upstream_outage_is_retryable(monkeypatch):
    monkeypatch.setenv("MOCKAPI_FAIL_RATE", "1")
    assert_error(call("get_ticket", {"ticket_id": "T-1002"}), "upstream_unavailable", retryable=True)


def test_upstream_unreachable_is_retryable():
    def refuse(request):
        raise httpx.ConnectError("refused")
    http = httpx.AsyncClient(transport=httpx.MockTransport(refuse), base_url="http://api")
    assert_error(call("get_customer", {"customer_id": "C-1"}, http), "upstream_unavailable", retryable=True)


def test_upstream_timeout_is_retryable():
    def slow(request):
        raise httpx.ReadTimeout("slow")
    http = httpx.AsyncClient(transport=httpx.MockTransport(slow), base_url="http://api")
    assert_error(call("get_ticket", {"ticket_id": "T-1002"}, http), "upstream_unavailable", retryable=True)


def test_rate_limited_is_retryable():
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(429, json={"detail": "slow down"})),
                             base_url="http://api")
    assert_error(call("get_ticket", {"ticket_id": "T-1002"}, http), "rate_limited", retryable=True)


def test_upstream_garbage_body_does_not_leak():
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500, text="<html>stack trace</html>")),
                             base_url="http://api")
    out = call("get_ticket", {"ticket_id": "T-1002"}, http)
    assert_error(out, "upstream_unavailable", retryable=True)
    assert "stack trace" not in out["error"]["message"]


def test_long_text_is_capped():
    body = {"ticket_id": "T-1", "body": "y" * 10_000}
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)), base_url="http://api")
    assert len(call("get_ticket", {"ticket_id": "T-1"}, http)["body"]) < 2100


def test_resource_read_and_unknown():
    async def read(c, uri):
        return (await c.read_resource(uri)).contents[0].text
    text = run(lambda c: read(c, "policy://fees-schedule-v2"))
    assert text.startswith("---\ntitle: Fees Schedule\nversion: 2\n") and "status: current" in text
    with pytest.raises(Exception):
        run(lambda c: read(c, "policy://does-not-exist"))
