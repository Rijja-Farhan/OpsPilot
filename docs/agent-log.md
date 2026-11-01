# Agent log

Where the coding agent helped, where it was wrong, how it was verified.


## A1 build (2026-11-01)
| Where | What went wrong | How it was caught | Fix |
|---|---|---|---|
| `tests/test_llm.py` | Imported `httpx`, but the installed `openai` 3.x depends on `httpx2`, so the test module did not import | pytest collection error | Switched to `httpx2` |
| `tests/test_cli.py` | First version of the "ticket body is data" test replaced `fake_llm.respond` with a lambda missing the `json_mode` keyword and restored it by hand | Test failed with TypeError; also hacky | Shared `_spy` helper using `monkeypatch` |
| `config.py` | Model IDs are from memory, not from the providers' current lists; the plan asks to verify Groq JSON-mode support | No API key or network check in this session | Marked as placeholders in code and decisions; verify before the live eval |
| `tools/gen/make_tickets.py` | Banking77 has no loan intents, so `loans_credit` has 0 tickets in the sample | Counted categories after generating | Documented in decisions; not hidden |
| `fake_llm.py` | The default fake cannot answer policy questions (returns the intent JSON, so validation fails) | Ran the CLI by hand with `LLM_PROVIDER=fake` | Left as is: policy tests queue exact responses; real policy answers need the live eval |

| `config.py` Groq model | `llama-3.3-70b-versatile` returned 404 for the user's key | First live call; listed the key's models via the API | Default is now `openai/gpt-oss-120b` |
| `evals/` checks | Substring checks were too brittle (no-break space) and one injection check flagged a harmless quote | Read the failing answers instead of trusting the FAIL line | Normalised Unicode; changed the check, and said so in `docs/a1-eval.md` |
| Policy answer #15 | Model answered an SLA question from the Fraud Policy (P1/P2 priority confused with incident SLA) | Live eval, reading the answer | Open: needs a stricter prompt or retrieval threshold |

Live Groq run done on 2026-11-01 (14/15, see `docs/a1-eval.md`). Only Groq was tried, so criterion 5 is proven on `fake` and Groq, not a second real provider.

## A1 review follow-up (2026-11-01)
| Where | What went wrong | How it was caught | Fix |
|---|---|---|---|
| `policies.wants_history` | Substring matching: "before", "past", `"old "` and `"change "` (inside "exchange ") flagged ordinary questions as history, pulling superseded v1 docs into answers and breaking criterion 3. My 15-question eval had no question containing those words, so it missed it | External review, then reproduced by running it | Whole-word regex, tighter word list, regression tests |
| Dependencies | Packages were only in a README pip line | External review | `requirements.txt` |

## A3 build (2026-11-01)
| Where | What went wrong | How it was caught | Fix |
|---|---|---|---|
| `mcp_server` | I wrote against the MCP v1 API (`FastMCP`), but the installed SDK is 2.x where it was renamed `MCPServer` and the client changed | Read the installed package first; `mcp/server/fastmcp.py` only raises a migration error | Probed the 2.x API in a scratch script before writing the server |
| `llm.py` tool support | Adding a `tools` kwarg to the fake client call broke two A1 CLI tests, whose spy replaced `fake_llm.respond` with a fixed signature | pytest (2 failures, `TypeError`) | Pass `tools` only when set, so the old call shape is unchanged |
| `tests/test_mcp_server.py` | My error-shape helper asserted "http" never appears in an error message, but "upstream returned HTTP 500" is a legitimate message; the check was wrong, not the server | Two failing tests, read the message | Assert on `://`, `<` and `Traceback` (raw bodies and traces) instead |
| `tests/test_cli.py` | First draft of the agent-failure test patched `asyncio.run` with a lambda that closes the coroutine; hard to explain | Re-read it before committing | Patch `open_toolbox` with a small async context manager that raises |
| `search_tickets` misuse | Model sent `category: "fraud"` in 3 of 3 live runs. A description fix did nothing; a JSON-schema enum made Groq reject the call with HTTP 400 (provider-side validation), so I reverted it | Live run, read the tool-call log, then re-ran each variant 3 times | Server accepts an unambiguous fragment and reports `filters_normalized` (see decisions) |
| Live answer quality | "why is T-1002 still open?" claimed "no action has been taken" from a null assignee; the data does not say that | Read the answer against the ticket | Open: not a tool problem; the prompt could say "state only what the tool results show" |
| Live latency | Triage question took 22 to 44 s on Groq (`gpt-oss-120b` reasons before each tool call) | Timings in `evals/run_a3.py` output | Open: consider a smaller model for tool turns |
| Test data | Live runs wrote a note to `data/notes.jsonl` (the real write path) | `ls data/` after the run | File is gitignored and deleted after runs; tests use a temp path |
