# Decisions log

## 2026-11-01: Rebrand domain from SaaS to fintech
Chose a fictional fintech (Northwind Pay) so public banking-support datasets (Banking77, Bitext, CFPB, NAB) map onto our ticket categories with minimal remapping. Trade-off: we still need to write the glue (customer/ticket links, incident clusters) and the policy KB ourselves.

## 2026-11-01: A1 uses LLM only where language is needed (docs/spec-a1.md)
Ticket-by-ID and by-customer lookups are plain code: exact, deterministic, free, and an LLM there only adds error. The LLM handles free-text ticket questions (given the looked-up ticket as context), policy questions (given retrieved docs, must cite) and the fallback intent call. Router is regex first, LLM intent only if no regex matches. A lookup is "pure" if the text left after removing the ID contains only lookup words ("show", "ticket", "details"); anything else with an ID is a free-text ticket question.

## 2026-11-01: One SDK, provider table in config (plan-a1 section 3)
Groq, OpenAI and Ollama expose OpenAI-compatible endpoints, so `llm.py` uses the `openai` SDK and `config.PROVIDERS` holds base URL, key env var and model. Switching provider is one `.env` line. JSON mode is requested but output is always Pydantic-validated, with one retry that feeds the validation error back, then a typed `LLMError` (never an exception). A `fake` provider runs through the same code path via a duck-typed client (`fake_llm.py`) so tests are offline. Model IDs in the table are unverified placeholders until checked against each provider's model list.

## 2026-11-01: Citations are built in code, not by the model
The model lists sources it used, but `policies.answer` keeps only sources that were actually retrieved and fills `effective_date` from the doc's front matter. A fabricated or superseded source (in default mode) is dropped; if none survive, no answer is given. Retrieval is BM25 over whole current docs (A4 replaces it with embeddings and chunking). History questions (keyword check) include superseded docs.

## 2026-11-01: Banking77 intent -> category mapping (tools/gen/make_tickets.py)
The 77 intents map to the 8 labels in `CATEGORY_INTENTS` (the generator asserts every intent is mapped). Judgement calls: unrecognised card/cash/direct-debit payments and compromised card or lost phone -> `fraud_security`; top-ups and pending/reverted payments -> `transfers_payments`; refund requests, double charges and wrong cash amounts -> `disputes_refunds`; country/currency/age/exchange-via-app questions -> `other`. Banking77 has no loan intents, so the A1 sample has zero `loans_credit` tickets (CFPB would supply those later). `T-9001` is a hand-written prompt-injection fixture appended to the 300 sampled tickets.
