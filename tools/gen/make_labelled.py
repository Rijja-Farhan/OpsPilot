"""Assemble the labelled pool and print class counts per source (no model, no text inspection).
Writes data/processed/labelled.jsonl (gitignored; rebuilt from data/raw and data/synth).
Usage: python tools/gen/make_labelled.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.data import CATEGORIES, build_pool  # noqa: E402


def main() -> None:
    pool, drops = build_pool()
    out = ROOT / "data" / "processed" / "labelled.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in pool))
    print(f"{len(pool)} rows -> {out}; dropped {drops}")
    by_source = Counter((r["source"], r["category"]) for r in pool)
    for src in sorted({s for s, _ in by_source}):
        print(f"  {src}: " + ", ".join(f"{c}={by_source[(src, c)]}" for c in CATEGORIES if by_source[(src, c)]))


if __name__ == "__main__":
    main()
