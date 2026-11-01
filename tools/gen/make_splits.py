"""Fix the train/val/test split ONCE (AGENTS.md: split before inspecting data; never train on the test set).

Test  = Banking77 test.csv + whole held-out topics of the synthetic messages (paraphrases of one topic never straddle
        the train/test line).
Val   = ~15% of what is left per category (whole topics for synthetic rows), used for tuning and the threshold.
Train = the rest.
Writes data/splits/{train,val,test}_ids.json and CHECKSUMS.txt. Refuses to overwrite: the split must not drift.
Usage: python tools/gen/make_splits.py
"""
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.data import CATEGORIES, SPLITS, build_pool  # noqa: E402

SEED = 42
TEST_TOPIC_SHARE = 0.2
VAL_SHARE = 0.15


def pick_groups(groups: list[list[dict]], share: float, rng: random.Random) -> list[list[dict]]:
    """Take whole groups until at least `share` of the rows are covered (at least one group)."""
    groups = sorted(groups, key=lambda g: g[0]["id"])
    rng.shuffle(groups)
    total, taken, n = sum(map(len, groups)), [], 0
    for g in groups:
        if taken and n >= share * total:
            break
        taken.append(g)
        n += len(g)
    return taken


def main() -> None:
    if (SPLITS / "test_ids.json").exists():
        raise SystemExit("data/splits/ already exists. The split is fixed once; do not regenerate it.")
    pool, _ = build_pool()
    rng = random.Random(SEED)
    test = [r for r in pool if r["source"] == "banking77_test"]
    rest = [r for r in pool if r["source"] != "banking77_test"]

    synth_by_topic: dict[str, list[dict]] = defaultdict(list)
    for r in rest:
        if r["topic"]:
            synth_by_topic[r["topic"]].append(r)
    by_cat_topics: dict[str, list[list[dict]]] = defaultdict(list)
    for rows in synth_by_topic.values():
        by_cat_topics[rows[0]["category"]].append(rows)
    for cat in sorted(by_cat_topics):
        for g in pick_groups(by_cat_topics[cat], TEST_TOPIC_SHARE, rng):
            test += g
    test_ids = {r["id"] for r in test}

    remaining = [r for r in rest if r["id"] not in test_ids]
    val: list[dict] = []
    for cat in CATEGORIES:
        rows = [r for r in remaining if r["category"] == cat]
        groups = [[r] for r in rows if not r["topic"]]
        topics = defaultdict(list)
        for r in rows:
            if r["topic"]:
                topics[r["topic"]].append(r)
        groups += list(topics.values())
        for g in pick_groups(groups, VAL_SHARE, rng) if groups else []:
            val += g
    val_ids = {r["id"] for r in val}
    train = [r for r in remaining if r["id"] not in val_ids]

    SPLITS.mkdir(parents=True, exist_ok=True)
    sums = []
    for name, rows in (("train", train), ("val", val), ("test", test)):
        path = SPLITS / f"{name}_ids.json"
        path.write_text(json.dumps(sorted(r["id"] for r in rows)) + "\n")
        sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
        c = Counter(r["category"] for r in rows)
        print(f"{name}: {len(rows)} rows; " + ", ".join(f"{k}={c[k]}" for k in CATEGORIES if c[k]))
    (SPLITS / "CHECKSUMS.txt").write_text("\n".join(sums) + "\n")


if __name__ == "__main__":
    main()
