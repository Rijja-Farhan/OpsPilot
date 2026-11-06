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

## A6 (2026-11-02 to 11-03)
| Where | Mistake | How found | Fix |
|---|---|---|---|
| `evals/graders.py` | NFKC normalisation was assumed to turn a non-breaking hyphen into `-`; it gives U+2010 | The grader's own unit test (`v2-final`) | Added an explicit dash fold |
| `evals/graders.py` | Policy catalog read the live index path instead of the environment's, so tests saw v2 as superseded | Failing `citation_valid` test | Catalog keyed on `policies._index_dir()` |
| `ml/a6_classifier.py` | The first write-up said the LLM was "better" on deferred tickets from a 1.7-point gap on 118 tickets (interval -10 to +13), and compared "perfect LLM" at the wrong threshold | Reading the generated table against the cost numbers | Paired bootstrap interval; the perfect-LLM column uses its own best threshold |
| Plan | Cost estimate ignored Groq's 200,000 tokens/day cap on the agent model; the classifier labelling (325 calls) used most of a day's quota before the suite ran | 429s with "tokens per day" in the error body | Ran the suite in slices; runner now retries provider rate limits and flags cases that never recover |
| Runner | First live baseline scored provider 429s as agent failures | Coworker case took 179 s and 1,226 tokens | `infra_failure` detection, 65 s waits, 3 retries, separate flag in the summary |
| Environment | The fastembed model cache lived in `/tmp` and was wiped, so every policy case silently returned "not found" with 0 tokens | `[FAIL]` rows with 0 tokens in the first slice | Persistent `FASTEMBED_CACHE_PATH`; a zero-token live failure is now treated as a signal to look at |
| Judge | Rubric v1 was too lenient (70% agreement on the 10 items that did not error); I revised it after seeing the disagreements, so the 87% on the same 15 items is optimistic | Calibration table | Disclosed in `docs/a6-judge-calibration.md` |
| `build_cases.py` | Imported A1 gold ("60", "v1") predates policy v3; the agent's "120 days, v2" is the right answer today | Reading the raw dev output of the one failing policy case | Gold corrected and logged in `docs/a6-eval.md` |
| Shell | `pkill`/`xargs kill` matched my own shell twice | Exit 143/144 | Started servers with `setsid`, avoided pattern kills |

## A7 (2026-11-04)
| Where | Mistake | How found | Fix |
|---|---|---|---|
| `tools/gen/make_stream.py` | The burst templates let two burst tickets come from one customer inside the dedupe window, so two real burst tickets were linked as duplicates | First stream replay: two "false links" with role `burst` | Not regenerated (the stream is fixed once); reported as a measured false-link count |
| Detector | My first calibration rule (smallest k that works) picked k = 2.0, below the usual range, because the calibration stream has only one burst | Reading the calibration table | Changed the rule, before reading eval results, to the middle of the working range (k = 3.0). I had already run the eval stream once at k = 2.5 and 3.0 in a smoke test and seen the decoy alert; I did not change any parameter after that |
| `Store` | SQLite refused calls from the webhook test client's thread | `test_webhook_...` | `check_same_thread=False`; one writer, each statement autocommitted |
| `redteam_a7.py` | The verdict labelled a real model's harmless draft "caught by policy" because it counted every refused action name, including unknown but harmless ones | Live red team: 11 of 11 "caught by policy" with no obeying reply | Only names in the denied set, or a rejected draft, count as policy catches; the live run now reports 11 `reached_human` |
| Draft prompt | The real model proposed made-up action names, all refused by default deny and recorded as "denied" | Live injection run | Prompt lists the two names allowed |
| Replay design | `drain` used `asyncio.run` per event, which cannot share one MCP client session | Reading the toolbox lifetime before running | `drain` is async and runs inside the caller's loop |
| Shell | `pgrep -f "run_a7.py --live"` matched my own wait loop and reported "running" forever | Wait loop never ended | Check the output file instead |
