# OpsPilot

An operations agent for Northwind Pay, a fictional digital bank (see `docs/domain.md`): assistant (v1) -> tools/MCP/retrieval/memory + classifier (v2) -> coworker (v3) -> ambient (v4).

## Layout

| Path | Purpose |
|---|---|
| `docs/` | Domain bible, specs (`spec-a1.md`), decisions log, agent log |
| `data/` | `tickets.jsonl` (generated), `kb/` policy docs; raw data is gitignored |
| `tools/gen/` | Seeded scripts that build or ingest the data |
| `mockapi/` | Mock REST API (customers, accounts, transactions, incidents, tickets) |
| `mcp_server/` | MCP server wrapping the mock API |
| `opspilot/` | The agent (see below) |
| `ml/` | Ticket classifier and anomaly detector |
| `evals/` | Eval datasets and graders |
| `tests/` | Unit and integration tests |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set LLM_PROVIDER and the matching key
```

## Run (A1)

```bash
python -m opspilot "show ticket T-1001"              # JSON, no LLM
python -m opspilot "tickets for customer C-17"       # JSON, no LLM
python -m opspilot "why is T-1001 still open?"       # LLM, ticket as context
python -m opspilot "how long do I have to file a dispute?"   # LLM + cited policy
```

Switch provider by changing `LLM_PROVIDER` in `.env` (`groq`, `openai`, `ollama`, `fake`). Only `opspilot/llm.py` and `opspilot/config.py` know about providers.

## Test and eval

```bash
LLM_PROVIDER=fake python -m pytest -q       # offline, free
LLM_PROVIDER=groq python evals/run_a1.py    # live eval, record in docs/a1-eval.md
python tools/gen/make_tickets.py            # regenerate data/tickets.jsonl (needs data/raw/banking77)
```

## A1 modules
`router.py` (regex, then LLM intent), `tickets.py` (plain-code lookups), `policies.py` (BM25 + cited answers), `schemas.py` (Pydantic source of truth), `llm.py` (`complete()`, retry, backoff, trace), `fake_llm.py` (offline provider), `config.py`, `cli.py`.

## What I would change
- Verify model IDs and run the live eval before trusting any answer quality claim.
- Policy retrieval loads whole docs with keyword search; A4 should chunk and embed, and handle staleness properly.
- The history-question check is a keyword list; an LLM or better parse would be sturdier.
- The ticket-vs-question split relies on a lookup-word list and will misroute unusual phrasings to the LLM path.
- Traces go to `traces/llm_calls.jsonl` as plain JSONL; A5/A6 will want structure and IDs.
