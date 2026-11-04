from evals import reward


def test_naive_reward_is_gamed_by_a_guess_and_a_stop():
    rep, led = reward.degenerate()
    task = "investigate T-1002 and draft a resolution with evidence"
    r, parts = reward.naive_reward(rep, led, task, "fees_charges")
    assert r == 1.0 and all(parts.values()), parts   # the exploit works on the naive reward


def test_strict_reward_rejects_it_and_names_why():
    rep, led = reward.degenerate()
    r, parts = reward.strict_reward(rep, led, "investigate T-1002 and draft a resolution with evidence", "T-1002")
    assert r == 0.0
    assert not parts["coverage"] and not parts["findings"] and not parts["completed"]


def test_both_rewards_accept_an_honest_report():
    rep, led = reward.honest()
    task = "investigate T-1002 and draft a resolution with evidence"
    assert reward.naive_reward(rep, led, task, "fees_charges")[0] == 1.0
    r, parts = reward.strict_reward(rep, led, task, "T-1002")
    assert r == 1.0, parts


def test_wrong_category_and_a_write_both_zero_the_reward():
    rep, led = reward.honest()
    task = "investigate T-1002"
    assert reward.naive_reward({**rep, "category": {"label": "other", "evidence_ids": ["E1"]}}, led, task, "fees_charges")[0] == 0.0
    wrote = led + [{"id": "E9", "tool": "add_ticket_note", "arguments": {}, "ok": True, "result": {}, "timestamp": "t"}]
    assert reward.naive_reward(rep, wrote, task, "fees_charges")[1]["no_writes"] is False
