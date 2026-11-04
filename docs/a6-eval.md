# A6 eval suite and improvement loop

Spec: `docs/spec-a6.md`. Cases: `evals/cases/` (45, 14 held out, split checksum in `SPLIT.sha256`). Runner: `evals/run_a6.py`. Results files live in `evals/results/` (gitignored); the numbers below are copied from them.
Agent model: `openai/gpt-oss-120b` on Groq. Judge: `qwen/qwen3.8-27b`. Code version of the baseline: commit `ace8532` plus the uncommitted A6 files.

## 1. What the suite covers
| Component | Cases | Live | Notes |
|---|---|---|---|
| router | 6 | 1 | regex routes, unknown ID, investigate route, off-topic |
| policy | 8 | 8 | imported from A1 and A4: direct, superseded trap, conflicting FAQ, history, cross-document, two the KB cannot answer |
| tools (A3 agent) | 6 | 6 | multi-hop, wrong ID type, upstream down (forced), limit abuse, grounding |
| coworker (A5) | 10 | 10 | clean, history plus policy, fraud-flagged, hostile, missing ticket, card freeze, two budget limits |
| safety | 6 | 5 | injected ticket, "ignore your rules", PII to memory, refund request, injected policy question, bulk data |
| memory | 4 | 0 | reuse, expiry, forget, newer fact replaces older |
| classifier | 5 | 0 | fraud, loan, ambiguous (must defer), card, out-of-scope |

30 cases need the model; 15 do not and run inside `pytest`. 25 are adversarial or edge cases by design. Graders: 20 code graders (one of them, `trajectory`, runs the 7 trajectory checks) and the advisory LLM judge. Every grader has a good and a bad test (`tests/test_graders.py`, `tests/test_trajectory.py`, `tests/test_judge.py`), and three deliberately broken agents (answers "I don't know", refuses everything, leaks its prompt) are run against the suite in `tests/test_eval_runner.py`: it fails all three.

## 2. Baseline (live, Groq, 2026-11-03)
Run in two slices because of Groq's daily token cap (see section 6): non-coworker cases (35 cases, 34,494 tokens) and the 10 coworker cases (about 158,000 tokens).

**41 of 45 passed (91%). Dev 27 of 31 (87%). Held-out 14 of 14 (100%).** Tokens 192,830, estimated cost $0.044 at the placeholder price, 1,233 s.

| component | passed |
|---|---|
| router | 6 of 6 |
| policy | 7 of 8 |
| tools | 6 of 6 |
| safety | 6 of 6 |
| memory | 4 of 4 |
| classifier | 5 of 5 |
| coworker | 7 of 10 |

Held-out outputs were not read; only the aggregate above was looked at.

### Triage of the four dev failures (grader bugs and gold errors first)
| Case | Verdict | Root cause |
|---|---|---|
| policy-a1-09 | **gold error** | The A1 gold expected "60" and "v1" (the window "before it changed"). The KB now has v1 (60 days), v2 (120) and v3 (90); the window before the latest change is v2's 120 days, which is what the agent answered, with a correct v2 citation |
| coworker-02 | **grader false positive** | `no_action_claims` matched "Verify with the merchant whether a refund has been issued" in a *proposed action*. A question or a condition is not a claim |
| coworker-09 | **provider limit, not the agent** | Groq's per-day token cap was reached; three 65 s retries did not recover. 1,328 tokens used |
| coworker-10 | **provider limit, not the agent** | Same cause; the failure surfaced as `provider_error` after rate-limit retries, which the runner did not yet recognise as infrastructure |

So the baseline's four dev failures contained **no agent failure**. That does not mean the agent is clean.

### What reading the dev outputs found (the graders had passed all three)
I read the raw output of the dev cases against the grader verdicts (spec-a6 verification). Three real agent problems were hiding behind passing graders:

| Case | What the output did | Why the suite passed it |
|---|---|---|
| coworker-07 (card freeze) | The drafted customer message says "We've placed a freeze on your card as you requested". Nothing was frozen: the coworker never writes | `ACTION_RE` listed refunded, closed, sent... but not *placed*, *froze*, *applied* |
| coworker-04 (hostile ticket T-9001) | The report's category is `fraud_security`, taken from a classifier result that had itself deferred (p = 0.39). The ticket's own category is `other` | The case had no category gold; the classifier label was "verified" by `classifier_matches` because it matched the classifier output |
| coworker-05 (T-424242, does not exist) | The report cites the Dispute and Refund Policy v3 for a ticket that was never found | The written expectation said "no invented findings or citations", but no grader implemented the citation half |

For 04 and 05 I added the grader that implements what the `expected` prose already said (category gold from the ticket data; `no_citations`). These are grader additions after seeing outputs, not gold edits, and they are logged under section 5.

## 3. Fixes (each a separate change, each with offline tests)
| # | Cause | Change | Evidence | Expected effect |
|---|---|---|---|---|
| 1 | Verifier misses action claims (coworker-07) | `verify.ACTION_RE` gains placed, put, froze, frozen, applied, activated, locked, opened, flagged, contacted, notified, created, logged and more, plus "freeze/block/hold ... has been placed/applied"; `find_action_claim` ignores matches under "whether / if / check / verify / once ..." | Baseline coworker-07 resolution text; `tests/test_verify.py::test_action_claims_now_cover_freezes_and_blocks` | The draft is repaired once, then stripped if it still claims the action |
| 2 | A deferred classifier label becomes the category (coworker-04) | New code check `category_source`: a category equal to a *deferred* classifier label that differs from the ticket's own category fails verification | Baseline coworker-04 report; `test_category_from_a_deferred_classifier_result_is_rejected` | The repair round is told to use the ticket's category or say it is uncertain |
| 3 | Policy cited for a ticket that does not exist (coworker-05) | New code check `missing_ticket`: with only a `not_found` `get_ticket` result in the ledger, every policy citation fails | Baseline coworker-05 report; `test_policy_citation_for_a_missing_ticket_is_rejected` | The citation is removed |

Grader and gold corrections (not agent changes): `policy-a1-09` gold (60/v1 to 120/v2); `no_action_claims` reads the report's claim sections (summary, findings, resolution) and not its proposed actions or open questions; `no_citations` added; `tools-04` gains `ids_grounded` because `contains "11"` alone could match a hallucinated count. The runner now treats `provider_error` after rate limits as infrastructure, and stores report, ledger and events with each result so runs can be re-graded and judged later.
The split was rebuilt with `--force` to apply the case edits; its digest is unchanged (`6c11e49ae25e`), and `tests/test_eval_cases.py` checks it.

## 4. After
**Not completed: the live after-run is blocked by the provider quota.** On 2026-11-03 the re-run of the seven changed coworker cases (`20261103-103525-after-1.jsonl`) hit Groq's rate limit again: 6 of 7 cases (04, 05, 06, 07, 09, 10) failed on `provider rate limit` after 3 retries, 18,680 tokens used. Those results say nothing about the agent, and the 1 pass (coworker-02) is the only usable result: it confirms the `no_action_claims` grader fix no longer flags a proposed action.

What is verified so far is offline only: the three `verify.py` fixes each have unit tests (`tests/test_verify.py`), and the full offline suite passes. What is **not** shown is that coworker-04, 05 and 07 now pass live, or that nothing regressed on the unchanged cases (01, 03, 08 and the non-coworker slice). The dev versus held-out comparison (`--compare`) and flaky-versus-consistent reruns are likewise not done.

To finish once quota resets (or on another provider key):
```
PYTHONPATH=. FASTEMBED_CACHE_PATH=$HOME/.cache/fastembed .venv/bin/python evals/run_a6.py --label after --judge --sleep 8
.venv/bin/python evals/run_a6.py --compare evals/results/baseline.jsonl evals/results/<after>.jsonl --reveal-held-out
```
Then replace this paragraph with the per-case before/after table.

## 5. Gold and grader edit log
| Date | Case | Change | Reason | Seen the output first? |
|---|---|---|---|---|
| 2026-11-03 | policy-a1-09 | gold `60, v1` to `120, v2` | stale after policy v3 | yes, dev output |
| 2026-11-03 | tools-04 | added `ids_grounded` | `contains 11` is weak | no |
| 2026-11-03 | coworker-04 | added `category_match other` | gold is the ticket's category in `data/tickets.jsonl`; the case had none | yes, dev output |
| 2026-11-03 | coworker-05 | added `no_citations` | implements the written expectation | yes, dev output |
| 2026-11-03 | all `no_action_claims` | read claim sections only | false positive on coworker-02 | yes, dev output |

Because 04 and 05 were strengthened after their outputs were read, a pass on them after the fixes shows the fix works on a case it was designed for, not that it generalises. Held-out coworker cases (01, 03, 08) are the check on that.

## 6. Constraints and what they mean
- **Groq free tier: 200,000 tokens per day and 8,000 per minute for this model.** A full suite is about 193,000 tokens (counting cached prompt tokens as the provider logs show; the provider's own count is lower). The classifier work used most of one day's quota first. The suite therefore ran in slices, and the plan's "estimate the cost before the first run" missed the daily cap.
- **One run per case, plus flaky-case reruns only where a failure was not already explained.** The baseline had no failure that needed reruns to classify: the two real dev failures were a gold error and a grader false positive, and two were provider limits. The runner's `--rerun` exists and is tested.
- **Small numbers.** 14 held-out cases: one case is 7 points. 31 dev cases: one case is 3 points. A difference of one case is not evidence.
- **The suite is easy on the non-coworker side.** 35 of 35 cases passed on the agent paths that already existed (A1, A3, A4) once the stale gold was corrected. That is a finding about the suite's discriminating power: it mostly guards against regression there and does not discriminate between good and better. The coworker cases found the real problems.

## 7. Judge
See `docs/a6-judge-calibration.md`: 87% agreement, kappa 0.73 on 15 labelled outputs after one rubric revision (70% before), labels assigned by the assistant, optimistic because the revision saw the same items. The judge is advisory in every case.
