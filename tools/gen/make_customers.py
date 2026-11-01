"""Build data/customers.jsonl and data/transactions.jsonl for the mock API (fixed seed, fully synthetic).

Customer IDs are taken from data/tickets.jsonl so every ticket has a matching customer.
Names, amounts, merchants and dates are invented; no real customer data.
Usage: python tools/gen/make_customers.py
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TICKETS = ROOT / "data" / "tickets.jsonl"
CUSTOMERS_OUT = ROOT / "data" / "customers.jsonl"
TRANSACTIONS_OUT = ROOT / "data" / "transactions.jsonl"
SEED = 42
TODAY = date(2026, 10, 31)
TXNS_PER_CUSTOMER = (4, 14)

FIRST = "Amira Ben Chloe Dev Elena Farid Grace Hiro Isla Jonas Kira Liam Maya Nolan Omar Priya Quinn Rosa Sven Tara".split()
LAST = "Adler Brandt Castillo Dube Evans Fischer Gupta Haddad Ito Jensen Khan Lopez Meyer Novak Okafor Patel".split()
TIERS = ["standard", "standard", "standard", "plus", "premium"]
MERCHANTS = ["Corner Cafe", "City Transit", "GreenGrocer", "StreamBox", "PetWorld", "BookNook", "FuelStop", "TechMart",
             "Sunrise Pharmacy", "Cinema Max", "AirNorth", "HomeFix", "Pizza Planet", "Gym Central"]
STATUSES = ["settled"] * 8 + ["pending", "declined", "reversed"]


def customer_ids() -> list[str]:
    with TICKETS.open() as f:
        ids = {json.loads(line)["customer_id"] for line in f if line.strip()}
    return sorted(ids, key=lambda s: int(s.split("-")[1]))


def main() -> None:
    rng = random.Random(SEED)
    customers, transactions = [], []
    for cid in customer_ids():
        opened = TODAY - timedelta(days=rng.randint(60, 1500))
        customers.append({
            "customer_id": cid, "name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            "tier": rng.choice(TIERS), "opened_at": opened.isoformat(),
            "status": rng.choice(["active"] * 9 + ["restricted"]),
        })
        for _ in range(rng.randint(*TXNS_PER_CUSTOMER)):
            transactions.append({
                "txn_id": f"X-{len(transactions) + 1:05d}", "customer_id": cid,
                "amount": round(rng.uniform(2, 450), 2), "currency": "USD",
                "merchant": rng.choice(MERCHANTS), "date": (TODAY - timedelta(days=rng.randint(0, 120))).isoformat(),
                "status": rng.choice(STATUSES),
            })
    transactions.sort(key=lambda t: (t["customer_id"], t["date"]), reverse=False)
    CUSTOMERS_OUT.write_text("".join(json.dumps(c) + "\n" for c in customers))
    TRANSACTIONS_OUT.write_text("".join(json.dumps(t) + "\n" for t in transactions))
    print(f"wrote {len(customers)} customers, {len(transactions)} transactions")


if __name__ == "__main__":
    main()
