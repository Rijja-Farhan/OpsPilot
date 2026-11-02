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

## A4 build (2026-11-01)
| Where | What went wrong | How it was caught | Fix |
|---|---|---|---|
| `ingest/chunk.py` | A heading with no text under it (the `# Title (vN)` line) became its own chunk holding only the header and the title. These chunks ranked high for on-topic queries and crowded out the answer. My first retrieval grid was computed with this bug and pointed to dense retrieval | Rerunning the A1 live eval: the history question that A1 answered now returned "couldn't ground that answer"; I then looked at the retrieved text | Skip empty sections; regression tests (no chunk is only a heading, every real-corpus chunk has body text, history query retrieves the old value). Regrid: the winner changed to hybrid |
| `ingest/dedupe.py` | Set `THRESHOLD = 0.6` before measuring, i.e. by feel, which the plan forbids; also 0.6 was above two labelled versions only by luck | Re-read the plan after computing pair scores | Threshold derived from labelled pairs (0.68) with a test that it sits in the gap |
| `memory.py` | The "safe token" regex allowed only letters, so `p2` and `p3` were silently dropped and priority never reached memory | My own unit test for the run summary | Regex allows digits |
| `evals/run_a4_stale.py` | Checker counted a correct answer as missing the current value because of formatting (`£750`, `1 %`) | Read the actual answers instead of trusting the flags | Normalise formats; three-way verdict (wrong, mixed, ok) |
| Plan assumption | The plan assumed CFPB narratives are available. They are not (0 of 9,680 records, and the CSV has no narrative column) | Counted narratives before building on them | Documented deviation: LLM-written `loans_credit` data plus a control set; results carry a confound warning |
| `tools/gen/make_messy_kb.py` | Claimed the generator is deterministic; the scanned PDF carried Pillow's current timestamp. My first fix crashed after the script had already deleted `data/kb_raw` | Hashing the output before and after regeneration; the crash was immediate | Fixed timestamp passed as `time.struct_time`; two regenerations give the same hash |
| Threshold cost | Assumed a deferred ticket is resolved correctly by the LLM | Measured on the 200-ticket sample: LLM 50% vs classifier 65% on deferred tickets | Recommendation changed to human review; assumption stated in the metrics file |
| `tests/test_classifier.py` | Two demo tickets (T-1198, T-1234) share text with Banking77 `test.csv` although the plan says demo tickets never appear in test | The leak test I wrote failed on the real data | Overlap pinned explicitly in the test; training side already excludes those texts |
| `tests/test_memory.py` | A spy lambda used the wrong keyword name; one test had a dead `if False` branch and a meaningless assertion | Test failure; re-reading the file | Fixed and removed |

Verified only on Groq (`openai/gpt-oss-120b`); the Gemini entry from A1 was not exercised.

## A5 build (2026-11-01)
| Where | What went wrong | How it was caught | Fix |
|---|---|---|---|
| `docs/spec-a5.md` | Wrote that Dispute and Refund Policy v2 is current; the A4 index has a v3 | Live run 2 cited v3, which verification accepted as current | Spec note and trace reading corrected; the check was right, my expectation was stale |
| `coworker.py` live run | A Groq 429 in the 2nd ACT call ended the run as `model_error` with no detail and no list of unrun steps | Live run `12ed`, read the trace | `StopRun` detail, "Not completed" notes by code |
| `coworker.py` re-run | The REPORT call hit a 429 and the run produced an empty fallback report. My `report_phase` edit had not applied (a dead `if draft is None` branch still referenced an undefined name), so the failure detail was blank | Live run `4036`; I read the code instead of trusting the green tests | Rewrote the branch; test for the persistent-rate-limit case |
| `coworker.py` | 429 handling relied on `llm.complete`'s ~15 s backoff, shorter than the provider's window | Same runs | Harness-level model retry (2 x 20 s), 240 s time budget |
| `trace.py` call | `event("start", phase=...)` collided with the positional `phase` argument | 16 of 17 new tests failed with `TypeError` | Renamed the field to `resume_phase` |
| `tests/test_budget.py` | The time-budget test advanced the fake clock before the run began, so no time passed during it; the per-tool test used a summary naming IDs absent from its evidence, so verification (correctly) made it partial | Two failing tests, read each | Clock advanced inside the model call; summary text fixed |
| `cli.py` | `--resume nope` started the tool server first and surfaced an `ExceptionGroup` instead of "No saved run" | `tests/test_cli.py` | State is loaded before the server starts |
| Shell | `pkill -f "uvicorn mockapi"` matched my own command line and killed the shell | Exit code 144 | `pgrep -f "[u]vicorn ..."` |
| Live runs | Groq rate-limited so heavily that the API-down case could not be run cleanly twice | Traces `0784` and `286b` | Reported as not fully verified live; offline tests cover retries |
