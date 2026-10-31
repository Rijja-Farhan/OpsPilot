"""Offline fake provider: canned, deterministic responses so tests run free and without a network.

Tests can queue exact responses with queue_responses(); otherwise a simple keyword heuristic is used.
"""
import json
from types import SimpleNamespace

_queue: list[str] = []

POLICY_WORDS = ("dispute", "refund", "fee", "fraud", "policy", "sla", "escalat", "privacy", "chargeback", "liability")


def queue_responses(*responses: str) -> None:
    _queue.clear()
    _queue.extend(responses)


def _default(messages: list[dict], json_mode: bool) -> str:
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "").lower()
    if json_mode:
        return json.dumps({"intent": "policy" if any(w in user for w in POLICY_WORDS) else "out_of_scope"})
    return "FAKE ANSWER"


def respond(messages: list[dict], json_mode: bool):
    text = _queue.pop(0) if _queue else _default(messages, json_mode)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=sum(len(m["content"]) for m in messages) // 4, completion_tokens=len(text) // 4),
    )
