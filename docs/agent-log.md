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
