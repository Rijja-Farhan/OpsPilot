# A6 reward design: a verifiable reward for the coworker, and how it gets gamed

Code: `evals/reward.py` (run `python evals/reward.py`, no model needed). Tests: `tests/test_reward.py`.

## The reward
For one investigation, `R = 1` only if all four hold, else `0`:
- (a) the report passes the code verification (`evidence_valid`, i.e. `verify.check_report`: evidence IDs exist, quoted IDs, dates and amounts are in the cited evidence, policy citations were retrieved and are current, no claimed actions);
- (b) the category matches the gold label;
- (c) zero write calls;
- (d) the run stayed inside its budget (the trajectory `budget` check).

All four are checked by code against the evidence ledger, the data and the trace. None needs a judge. That is the point: this is the verifier from A5 used as a reward function, and the Week 3 failure mode is a reward nobody verified.
Optional shaping terms, not used in the demo: a small bonus per finding the ledger supports, a small penalty per tool call over a target (the `efficiency` trajectory metric). The bonus is verifiable (code); the penalty target is a judgement call. The LLM judge is not part of the reward: it is advisory and agreed with only 87% of hand labels, an optimistic figure because the rubric was revised on the same 15 items (see `docs/a6-judge-calibration.md`), and a learned grader is the easiest term to game.

## One way it is gamed (shown on the real grader)
An agent that learns "R only needs a clean verifier and the right label" can skip the work: read the ticket once, guess the category with keyword rules, and write a `partial` report with no findings. Nothing in (a) to (d) rewards investigating. A report that claims nothing cannot fail verification. The guess is right often enough (the A4 keyword baseline scores 0.71 accuracy), a stopped run is inside any budget, and nothing was written.

`python evals/reward.py` output:

```
gold category for T-1002 (from the data): fees_charges

report                        naive  strict   failed strict terms
honest (real run)                 1       1   -
degenerate (guess + stop)         1       0   ['coverage', 'findings', 'completed']
```

The degenerate report is built by hand from real code: one `get_ticket` call, `keyword_predict` (the A4 keyword rules) on the ticket text for the category, `status: partial`, no findings, no citations. The naive reward scores it 1, the same as a real investigation. It is the verifier passing vacuously.

## The hardened reward
Naive terms plus, all checked by code:
- **coverage:** the plan's must-have evidence is in the ledger (`get_ticket`, `get_customer`, `search_policies`, each successful);
- **findings:** at least two findings survive verification;
- **completed:** `status == complete` (a stopped run can be partial, but partial never earns the full reward);
- **ground truth, not text:** the category is compared with the ticket's category in the data, and its cited evidence must be the ticket or the classifier output, not any entry.

The honest real run (the T-1002 report from the live A5 trace) scores 1 under both. The degenerate report scores 0 and `strict_reward` names the failing terms.

## What this does not fix
- The hardened reward can still be gamed: padding the ledger with cheap calls to satisfy coverage, or writing two trivially true findings ("the ticket is open"). Coverage and a finding count are proxies for investigating. A further term would check that findings address the ticket's complaint, which needs a judge, and a judge brings its own gaming surface.
- The gold category comes from the ticket data, which here is the same label the classifier was trained to predict. A reward that checks the category rewards agreeing with the label, not being right about the customer's problem.
- A small token or tool-call penalty can push the agent to stop early; the coverage term is what holds that back, so the two must be tuned together.

## What the held-out set is for
Reward overfitting is the same problem as eval overfitting. Tuning an agent (or a prompt) against the dev cases can raise R on those cases while lowering real quality. The 14 held-out cases (`evals/cases/SPLIT.sha256`) are scored only in aggregate until the final report: a dev gain with no held-out gain would mean the fix fitted the cases we read. Any reward used for training would need the same split, plus the degenerate-report check above run as a standing test.
