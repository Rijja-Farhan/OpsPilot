"""Fetch a sample of CFPB consumer complaints (with narratives) via the public search API.

The full export is ~360 MB, so we pull a capped sample per product instead.
Output: data/raw/cfpb/complaints_sample.jsonl (one complaint per line).
Public-domain US government data; narratives are consumer-consented and redacted by the CFPB.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
OUT = Path(__file__).resolve().parents[2] / "data" / "raw" / "cfpb" / "complaints_sample.jsonl"
PRODUCTS = [
    "Checking or savings account",
    "Credit card or prepaid card",
    "Money transfer, virtual currency, or money service",
    "Payday loan, title loan, personal loan, or advance loan",
    "Vehicle loan or lease",
    "Mortgage",
    "Student loan",
]
PER_WINDOW = 80
# The API ignores a paging offset, so we slice by quarterly date windows instead.
WINDOWS = [(f"{y}-{m:02d}-01", f"{y + (m + 2) // 12}-{(m + 2) % 12 + 1:02d}-01") for y in range(2022, 2027) for m in (1, 4, 7, 10)]
FIELDS = ["complaint_id", "date_received", "product", "sub_product", "issue", "sub_issue", "complaint_what_happened"]


def fetch(product, start, end):
    params = [
        ("size", PER_WINDOW), ("has_narrative", "true"), ("no_aggs", "true"),
        ("sort", "created_date_desc"), ("product", product),
        ("date_received_min", start), ("date_received_max", end),
    ]
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)["hits"]["hits"]
        except Exception as e:
            print(f"  retry {attempt + 1} after {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed: {product} {start}")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    with OUT.open("w") as f:
        for product in PRODUCTS:
            n = 0
            for start, end in WINDOWS:
                hits = fetch(product, start, end)
                for h in hits:
                    s = h["_source"]
                    if s["complaint_id"] in seen:
                        continue
                    seen.add(s["complaint_id"])
                    f.write(json.dumps({k: s.get(k) for k in FIELDS}) + "\n")
                    n += 1
            print(f"{product}: {n}")


if __name__ == "__main__":
    main()
