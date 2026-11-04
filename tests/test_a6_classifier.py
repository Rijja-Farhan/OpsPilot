"""The cost model and the interval code behind docs/a6-classifier.md, on tiny hand-made inputs."""
import numpy as np
import pytest

from ml import a6_classifier as m
from ml.data import CATEGORIES

CLASSES = sorted(CATEGORIES)
F = CLASSES.index("fraud_security")
CARD = CLASSES.index("card_issues")


def proba(rows):
    out = np.full((len(rows), len(CLASSES)), 0.0)
    for i, row in enumerate(rows):
        out[i] = row
    return out


def row(**p):
    r = np.zeros(len(CLASSES))
    for k, v in p.items():
        r[CLASSES.index(k)] = v
    return r


def test_error_costs_follow_the_table():
    assert m.err_cost("card_issues", "card_issues", 5) == 0
    assert m.err_cost("other", "fraud_security", 5) == 5          # missed fraud
    assert m.err_cost("fraud_security", "other", 5) == m.COST_FRAUD_FP
    assert m.err_cost("other", "card_issues", 5) == m.COST_MISROUTE
    assert m.err_cost("other", "fraud_security", 20) == 20


def test_decisions_defer_below_threshold_and_on_a_fraud_alert():
    p = proba([row(card_issues=0.9, fraud_security=0.05, other=0.05),
               row(card_issues=0.6, fraud_security=0.3, other=0.1),
               row(card_issues=0.5, other=0.5)])
    _, d = m.decisions(p, CLASSES, 0.7, None)
    assert d.tolist() == [False, True, True]
    _, d = m.decisions(p, CLASSES, 0.55, None)
    assert d.tolist() == [False, False, True]                      # only the 0.5 row is below 0.55
    _, d = m.decisions(p, CLASSES, 0.0, 0.25)
    assert d.tolist() == [False, True, False]                      # P(fraud) 0.3 >= 0.25 although card_issues won


def test_fraud_alert_does_not_defer_when_fraud_already_wins():
    p = proba([row(fraud_security=0.8, other=0.2)])
    _, d = m.decisions(p, CLASSES, 0.0, 0.1)
    assert not d[0]


def test_expected_cost_counts_deferral_and_the_llms_own_errors():
    p = proba([row(card_issues=0.9, other=0.1), row(card_issues=0.55, fraud_security=0.45)])
    y = ["card_issues", "fraud_security"]
    never = m.expected_cost(p, CLASSES, y, {}, 0.0, None, 5.0)
    assert never["cost"] == pytest.approx(5.0 / 2)                  # the second ticket is a missed fraud
    right = m.expected_cost(p, CLASSES, y, {1: "fraud_security"}, 0.6, None, 5.0)
    assert right["cost"] == pytest.approx(m.COST_DEFER / 2)         # deferred and the LLM is right
    wrong = m.expected_cost(p, CLASSES, y, {1: "card_issues"}, 0.6, None, 5.0)
    assert wrong["cost"] == pytest.approx((m.COST_DEFER + 5.0) / 2)  # deferred and the LLM misses the fraud too
    perfect = m.expected_cost(p, CLASSES, y, {1: "card_issues"}, 0.6, None, 5.0, assume_perfect_llm=True)
    assert perfect["cost"] == right["cost"]
    assert wrong["deferred_share"] == 0.5 and wrong["accuracy"] == 0.5


def test_a_failed_llm_call_falls_back_to_the_classifier():
    p = proba([row(card_issues=0.55, fraud_security=0.45)])
    r = m.expected_cost(p, CLASSES, ["fraud_security"], {0: None}, 0.6, None, 5.0)
    assert r["cost"] == pytest.approx(m.COST_DEFER + 5.0)


def test_higher_miss_cost_never_lowers_the_cost():
    p = proba([row(card_issues=0.6, fraud_security=0.4)] * 4)
    y = ["fraud_security"] * 4
    costs = [m.expected_cost(p, CLASSES, y, {}, 0.0, None, r)["cost"] for r in m.RATIOS]
    assert costs == sorted(costs)


def test_bootstrap_interval_is_wider_for_small_classes():
    y = ["card_issues"] * 300 + ["loans_credit"] * 10
    pred = ["card_issues"] * 300 + ["loans_credit"] * 8 + ["card_issues"] * 2
    ci = m.bootstrap_ci(y, pred)
    width = lambda c: ci[c]["recall_ci"][1] - ci[c]["recall_ci"][0]  # noqa: E731
    assert width("loans_credit") > 5 * width("card_issues")
    lo, hi = ci["loans_credit"]["recall_ci"]
    assert lo <= 0.8 <= hi
