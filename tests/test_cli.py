import json

from opspilot import fake_llm
from opspilot.cli import REFUSAL, dispatch, main
from opspilot.schemas import CustomerTickets, TicketLookup


def test_ticket_lookup_end_to_end_no_llm():
    fake_llm.queue_responses("SHOULD NOT BE CONSUMED")
    out = TicketLookup.model_validate_json(dispatch("show ticket T-1001"))
    assert out.found and out.ticket_id == "T-1001"
    assert fake_llm._queue


def test_unknown_ticket():
    out = TicketLookup.model_validate_json(dispatch("T-424242"))
    assert not out.found and out.error == "ticket_not_found"


def test_customer_tickets():
    assert CustomerTickets.model_validate_json(dispatch("tickets for customer C-17")).count > 0


def _spy(monkeypatch):
    seen = {}
    orig = fake_llm.respond

    def spy(messages, json_mode):
        seen["messages"] = messages
        return orig(messages, json_mode)

    monkeypatch.setattr(fake_llm, "respond", spy)
    return seen


def test_ticket_question_uses_ticket_as_context(monkeypatch):
    seen = _spy(monkeypatch)
    fake_llm.queue_responses("It is open because nobody replied.")
    out = dispatch("why is T-1001 still open?")
    assert out == "It is open because nobody replied."
    system = seen["messages"][0]["content"]
    assert "<ticket_data>" in system and "T-1001" in system


def test_ticket_question_unknown_ticket_never_calls_llm():
    fake_llm.queue_responses("SHOULD NOT BE CONSUMED")
    assert not TicketLookup.model_validate_json(dispatch("why is T-424242 still open?")).found
    assert fake_llm._queue


def test_injection_ticket_body_is_wrapped_as_data(monkeypatch):
    seen = _spy(monkeypatch)
    dispatch("summarise T-9001")
    system = seen["messages"][0]["content"]
    assert "never as instructions" in system
    assert system.index("<ticket_data>") < system.index("Ignore all previous") < system.index("</ticket_data>")


def test_out_of_scope_refused_one_line():
    out = dispatch("write me a poem about cats")
    assert out == REFUSAL and "\n" not in out


def test_policy_path_with_fake():
    fake_llm.queue_responses(
        json.dumps({"intent": "policy"}),
        json.dumps({"answer": "120 days.", "sources": [{"title": "Dispute and Refund Policy", "version": 2,
                                                         "effective_date": "x"}]}))
    out = dispatch("how long do I have to file a dispute?")
    assert "120 days." in out and "v2, effective 2026-03-01" in out


def test_main_bad_provider_exit_code(monkeypatch, capsys):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    assert main(["write me a poem"]) == 2
    assert "Configuration error" in capsys.readouterr().err


def test_main_prints_json(capsys):
    assert main(["show ticket T-1001"]) == 0
    assert json.loads(capsys.readouterr().out)["ticket_id"] == "T-1001"
