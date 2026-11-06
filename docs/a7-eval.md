# A7: results on the event stream

Run: `PYTHONPATH=. python evals/run_a7.py --offline` (real classifier, real tool server over the mock API, scripted model), `--offline --obedient` (the scripted model obeys every injection), and `--live --inprocess --limit 45` (real LLM on a prefix). Raw results: `evals/results/a7-*.json` (gitignored). Spec: `docs/spec-a7.md`. The streams (`data/stream/`) and their gold files were written before any run and are checksummed.

## The stream
`eval.jsonl`: 290 events over 6 simulated hours: 190 normal (classifier test split), 40 burst, 8 decoy, 10 exact replays, 11 near duplicates, 3 legitimate repeats, 15 injections, 12 from one flooding customer, 1 unknown customer. `calibration.jsonl`: 168 events, 4 hours, a burst of 30 and a decoy of 8, used only to choose the detector's k.

## Results (offline run, 260 tickets processed, audit chain intact over 2,188 entries)
| Criterion | Result |
|---|---|
| Exact replays linked to the original | 10 of 10 |
| Near duplicates linked to the right original | 11 of 11 |
| Legitimate repeat 90 minutes later processed, not dropped | 3 of 3 |
| **False links** | **2**: two burst tickets from the same customer inside 30 minutes were linked (a generator quirk; the dedupe did what the spec says) |
| One customer flooding (cap 5 per 10 min) | 5 admitted, 7 shed and audited |
| Confident classifier predictions (no LLM call) | 171 of 190 normal tickets (90%); the classifier was right on 166 of those 171 (97%) |
| Deferred to the LLM | 19 of 190 (10%). Accuracy of the scripted model is not meaningful offline. In the live sample 3 of 3 were right |
| Injections: flagged by the guard | 12 of 15; the 3 left are the designed evasions (paraphrase, Spanish, reply steering) |
| Injections: denied actions executed | **0**, also with the scripted model obeying every one |
| Replies sent without approval | **0** (the agent has no send path; `approve()` is the only one) |
| Burst detected | **Yes**: 23 tickets in the 5 minutes from 11:20 against 3.4 expected, z = 10.6, attributed to `card_issues` (16 of 23, correct). The alert is raised when that bucket closes, 5 minutes after the burst began |
| False alerts | **1**: the decoy at 09:30 (12 tickets against 3.2 expected, z = 5.0) |

## Detector choice
Calibration stream, window 12 buckets, min count 8, cooldown 3: every k from 2.0 to 4.0 catches the burst with no false alert; k = 5.0 misses it. k = 3.0 is the middle of the working range. The decoy was sized to be a mild bump, but on the eval stream it came out at z = 5.0 (8 extra tickets landed in two adjacent buckets on top of a small baseline), so it fires at every k up to 5 and I cannot remove it by choosing k without tuning on the eval stream. It is reported as a false alert. Whether it is "false" is arguable: a 4x jump in volume is probably worth a glance, and the alert says which category and which tickets.

## Live sample (45 events, `openai/gpt-oss-120b`)
41 processed, 2 linked as duplicates, 0 shed. 32 of 35 normal tickets were confident (91%). Drafts: 36; 3 were rejected by the output checks (`amount_not_in_ticket`: the model quoted an amount that is not in the ticket), so 8% of drafts needed a human to write the reply from scratch. This is the cost of the blunt amount check. No injection in the sample changed anything.

## Acceptance (spec-a7)
| # | Criterion | Status |
|---|---|---|
| 1 | End to end with no prompt | Met (`replay`, `serve`) |
| 2 | Duplicates linked, legit repeat kept | Met, with 2 false links reported |
| 3 | Confident predictions make no LLM call | Met (`test_confident_prediction_makes_no_llm_classification_call`) |
| 4 | Burst flagged with an explanation; false alerts reported | Met: 1 caught, 1 false |
| 5 | Zero denied actions under an obeying model | Met offline (15 stream injections, 15 red-team texts, 8 structural attacks) |
| 6 | Approve, edit, reject; edits re-validated; timeouts escalate | Met (tests) |
| 7 | Tamper-evident audit | Met (`test_audit_tampering_is_detected`) |
| 8 | Killed worker resumes with no loss or duplicates | Met in a simulated kill (`crash_after`, the event stays `processing` and is re-claimed). Not tested with a real SIGKILL of a separate process |
| 9 | Cost per 1,000 tickets | `docs/a7-cost.md` |
| 10 | Red-team report lists what got through | `docs/a7-redteam.md` |
| 11 | Classifier test set untouched; thresholds from calibration | Met: the test split supplies stream text only, the detector's k comes from the calibration stream |
| 12 | A1 to A6 unchanged, offline suite passes | 389 tests pass (326 before, 63 new) |

## Limits
- One eval stream, one burst, one decoy: detection results are one sample, not a rate.
- The live run covers 45 of 290 events because of the provider's daily token cap.
- The scripted obeying model only misbehaves in the ways I scripted; the live column in the red-team report is what a real model did.
- The simulated kill does not test a real process dying inside a database write; SQLite's autocommit per statement is what is relied on.
