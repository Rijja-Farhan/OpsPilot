"""Labelled pool and the fixed splits for the ticket classifier (spec-a4 'Classifier').

Sources: Banking77 train/test mapped to our 8 categories (mapping lives in tools/gen/make_tickets.py), plus the
synthetic `loans_credit` and `fees_charges` control messages in data/synth/. Splits are stored as ID lists in
data/splits/ and never regenerated (see tools/gen/make_splits.py).
"""
import csv
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B77 = ROOT / "data" / "raw" / "banking77"
SYNTH = ROOT / "data" / "synth"
SPLITS = ROOT / "data" / "splits"
CATEGORIES = ["card_issues", "transfers_payments", "account_access", "fees_charges",
              "fraud_security", "loans_credit", "disputes_refunds", "other"]


def _intent_map() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location("make_tickets", ROOT / "tools" / "gen" / "make_tickets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.INTENT_TO_CATEGORY


def norm_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _banking77(split: str, intent_to_cat: dict[str, str]) -> list[dict]:
    with (B77 / f"{split}.csv").open(newline="") as f:
        return [{"id": f"b77-{split}-{i}", "text": r["text"], "category": intent_to_cat[r["category"]],
                 "source": f"banking77_{split}", "topic": ""} for i, r in enumerate(csv.DictReader(f))]


def _synth() -> list[dict]:
    rows = []
    for name in ("loans_credit", "fees_control"):
        with (SYNTH / f"{name}.jsonl").open() as f:
            rows += [{"id": r["id"], "text": r["text"], "category": r["category"], "source": f"synth_{name}",
                      "topic": r["topic"]} for r in map(json.loads, f)]
    return rows


def build_pool() -> tuple[list[dict], dict[str, int]]:
    """All labelled rows, deduplicated by normalised text so one text can never sit on both sides of a split.
    Test-file texts win: a train row whose text also appears in Banking77 test.csv is dropped. Returns (rows, drops)."""
    intent_to_cat = _intent_map()
    train, test, synth = _banking77("train", intent_to_cat), _banking77("test", intent_to_cat), _synth()
    drops = {"train_text_in_test": 0, "duplicate_text": 0}
    seen: set[str] = set()
    out: list[dict] = []
    for row in test:  # test first: it is fixed by the dataset, everything else yields to it
        key = norm_text(row["text"])
        if key in seen:
            drops["duplicate_text"] += 1
            continue
        seen.add(key)
        out.append(row)
    test_texts = set(seen)
    for row in train + synth:
        key = norm_text(row["text"])
        if key in test_texts:
            drops["train_text_in_test"] += 1
        elif key in seen:
            drops["duplicate_text"] += 1
        else:
            seen.add(key)
            out.append(row)
    return out, drops


def load_split_ids(name: str) -> list[str]:
    return json.loads((SPLITS / f"{name}_ids.json").read_text())


def load_split(name: str, pool: list[dict] | None = None) -> list[dict]:
    pool = pool if pool is not None else build_pool()[0]
    by_id = {r["id"]: r for r in pool}
    return [by_id[i] for i in load_split_ids(name)]
