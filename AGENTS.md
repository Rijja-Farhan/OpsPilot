# AGENTS.md

Project conventions for coding agents. Keep this file current; conventions live here, not in chat history.

## Project
OpsPilot: an operations agent. See `docs/domain.md` for the business context and `README.md` for layout.

## Rules
- Search the repo before creating a helper; do not duplicate existing utilities.
- One feature per branch; keep PRs under ~400 changed lines.
- Cite the relevant spec in `docs/` in commit messages.
- Never paste credentials or real customer data. Use only the provided/generated data.
- Fix train/test splits once, before inspecting data; never train on the test set.
- Record design decisions in `docs/decisions.md`; record agent mistakes in `docs/agent-log.md`.

## Commands
- Test: `LLM_PROVIDER=fake .venv/bin/python -m pytest -q`
- Run: `.venv/bin/python -m opspilot "question"`
- Generate tickets: `.venv/bin/python tools/gen/make_tickets.py`
- Live eval: `.venv/bin/python evals/run_a1.py`
- Mock API: `.venv/bin/python -m uvicorn mockapi.main:app --port 8000`
- MCP server (stdio, normally launched by the agent): `.venv/bin/python -m mcp_server`
- Generate customers and transactions: `.venv/bin/python tools/gen/make_customers.py`
- Live tool run: `PYTHONPATH=. .venv/bin/python evals/run_a3.py`
- Build the messy KB, then ingest and index it: `.venv/bin/python tools/gen/make_messy_kb.py && .venv/bin/python -m opspilot.ingest`
- Retrieval eval, stale example (live): `.venv/bin/python evals/run_a4_retrieval.py`, `.venv/bin/python evals/run_a4_stale.py`
- Classifier: `.venv/bin/python ml/train.py`, then `.venv/bin/python ml/compare_llm.py` (live)
- Memory: `.venv/bin/python -m opspilot --show-memory C-17`, `--forget C-17`
- Coworker: `.venv/bin/python -m opspilot "investigate T-1002"`, `--runs`, `--resume RUN_ID`; live tasks: `PYTHONPATH=. .venv/bin/python evals/run_a5.py`
- Plain `openai` SDK only; no LangChain-style frameworks.
- The train/val/test split in `data/splits/` is fixed; never regenerate it, never tune on the test set.
- Tools return data or the error contract `{error: {code, message, retryable}}`; never raise from a tool. Writes are gated in `opspilot/agent.py` (assistant) and denied in `opspilot/coworker.py` (coworker), not only in prompts.

## Do not
- Commit `.venv/`, `.env`, or generated raw data.
- Commit code you cannot explain.
