"""Build data/kb_raw/: a deliberately messy policy corpus (all synthetic) for the A4 ingestion pipeline.

Starts from the five clean docs in data/kb/ and adds what real knowledge bases contain: a newer policy
version whose predecessor still claims to be current, a draft that never took effect, a stale FAQ,
exact and near duplicates (one with a changed number), text PDFs and an image-only "scanned" PDF.
The content is fixed text, so the output is identical on every run.
Usage: python tools/gen/make_messy_kb.py
"""
import shutil
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "kb"
OUT = ROOT / "data" / "kb_raw"


def front(**meta) -> str:
    return "---\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n---\n"


DISPUTE_V3_BODY = """# Dispute and Refund Policy (v3)

## Filing window
A customer must file a card or payment dispute within **90 days** of the transaction date. Disputes about unauthorised transactions follow the Fraud Policy instead and have no filing window.

## Process
1. Support records the dispute and the disputed amount.
2. Provisional credit of up to 750 GBP is given within 3 business days of filing for eligible card disputes. Any provisional credit or refund decision requires human approval.
3. Northwind Pay contacts the merchant; the merchant has 15 days to respond.
4. Disputes over 2,000 GBP go to the Disputes Team lead.

## Refunds
Merchant refunds appear within 5 business days. After that, the customer may open a refund dispute.

## Chargebacks
A chargeback must be raised within 45 days of the merchant's final response. Chargebacks are raised by the Disputes Team, never by the first-line agent.
"""

# Same facts, different layout and a few reworded sentences: a near duplicate that is not byte-identical.
DISPUTE_V3_REFORMATTED = """# Dispute and Refund Policy (v3)


## FILING WINDOW

- A customer must file a card or payment dispute within **90 days** of the transaction date.
- Disputes about unauthorised transactions follow the Fraud Policy and have no filing window.


## PROCESS

- Support records the dispute and the disputed amount.
- Provisional credit of up to 750 GBP is given within 3 business days of filing for eligible card disputes. Any provisional credit or refund decision requires human approval.
- Northwind Pay contacts the merchant; the merchant has 15 days to respond.
- Disputes over 2,000 GBP go to the Disputes Team lead.


## REFUNDS

Merchant refunds appear within 5 business days. After that, the customer may open a refund dispute.


## CHARGEBACKS

A chargeback must be raised within 45 days of the merchant's final response. Chargebacks are raised by the Disputes Team, never by the first-line agent.
"""

# A wiki export with no metadata and one changed number (100 instead of 90): wrong, and easy to mistake for current.
DISPUTE_WIKI = """Dispute & Refund Policy - wiki export

Filing window
A customer must file a card or payment dispute within 100 days of the transaction date. Disputes about unauthorised transactions follow the Fraud Policy instead and have no filing window.

Process
1. Support records the dispute and the disputed amount.
2. Provisional credit of up to 750 GBP is given within 3 business days of filing for eligible card disputes. Any provisional credit or refund decision requires human approval.
3. Northwind Pay contacts the merchant; the merchant has 15 days to respond.
4. Disputes over 2,000 GBP go to the Disputes Team lead.

Refunds
Merchant refunds appear within 5 business days. After that, the customer may open a refund dispute.

Chargebacks
A chargeback must be raised within 45 days of the merchant's final response.
"""

DISPUTE_V4_DRAFT = """# Dispute and Refund Policy (v4, DRAFT)

## Filing window
Proposal: a customer must file a card or payment dispute within **45 days** of the transaction date. Not approved.

## Process
Proposal: provisional credit of up to 250 GBP within 10 business days.
"""

FAQ = """# Disputes FAQ

**How long do I have to dispute a payment?** You have 60 days to dispute a payment from the transaction date.

**Do I get my money back straight away?** No. Provisional credit is not given while a dispute is open.

**How long do merchant refunds take?** Merchant refunds appear within 10 business days.
"""

FEES_V3_DRAFT = """# Fees Schedule (v3, DRAFT)

| Item | Fee |
|---|---|
| International transfer | 4.00 GBP |
| ATM withdrawal abroad | 3% of amount |

Proposal under review. Not approved.
"""

ESCALATION_TXT = """Title: Escalation Policy
Version: 1
Effective: 2026-01-15

P1 (platform outage): page the on-call engineer immediately. If it is unresolved after 30 minutes, page the Head of Operations.
P2 (degraded service): page the on-call engineer within 1 hour during business hours.
P3 (normal): no paging; handle in the queue.
Fraud cases: escalate to the Fraud Team lead within 1 hour of a confirmed account takeover.
"""

SLA_LINES = """Support SLA
Version 1
Effective: 2026-01-15

Response and resolution targets by priority.
P1 (platform outage): first response within 15 minutes, resolution target 4 hours.
P2 (degraded service): first response within 1 hour, resolution target 1 business day.
P3 (normal): first response within 1 business day, resolution target 5 business days.
Targets are measured from ticket creation in business hours unless the priority is P1.
Breaches are reviewed weekly by the Head of Operations.
""".splitlines()

PRIVACY_LINES = """Data and Privacy Policy
Version 1
Effective: 2025-09-01

What an agent may see: the last 4 digits of a card or account number, the customer ID and ticket history.
Customer-facing drafts must not include full card or account numbers, home addresses or dates of birth.
Agents must not copy customer names or ticket text into notes, memory or external tools.
Customer history kept for assistance expires after 90 days.
Any request to export customer data goes to the Data Protection Officer.
""".splitlines()

CARD_GUIDE = """# How to order a replacement card

Open the app, choose Cards, then Replace card. The new card arrives in 5 business days.
The fee for a replacement is set by the Fees Schedule. Lost or stolen cards are frozen first by a human agent.
"""

SCAN_LINES = ["CHARGEBACK MEMO", "Chargebacks must be raised within 30 days.", "Signed: Disputes Team"]


def write_text_pdf(path: Path, lines: list[str], per_page: int = 12) -> None:
    """Minimal text PDF (Helvetica) with a running header and 'Page n of m' footer, like a corporate document."""
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objs: list[bytes] = []
    n = len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    for i, page in enumerate(pages):
        ops = ["BT /F1 9 Tf 50 800 Td (Northwind Pay - Internal - Confidential) Tj ET"]
        for j, line in enumerate(page):
            ops.append(f"BT /F1 11 Tf 50 {760 - 22 * j} Td ({esc(line)}) Tj ET")
        ops.append(f"BT /F1 9 Tf 270 40 Td (Page {i + 1} of {n}) Tj ET")
        stream = "\n".join(ops).encode()
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {4 + 2 * i} 0 R "
                    f"/Resources << /Font << /F1 {3 + 2 * n} 0 R >> >> >>".encode())
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for k, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{k} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def write_scanned_pdf(path: Path, lines: list[str]) -> None:
    """Image-only PDF: the text exists only as pixels, so pdftotext finds nothing and OCR would be needed."""
    img = Image.new("L", (800, 400), 245)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((40, 60 + 50 * i), line, fill=20)
    stamp = time.gmtime(1768435200)  # fixed (2026-01-15): Pillow otherwise writes the current time and the file differs per run
    img.save(path, "PDF", resolution=100, creationDate=stamp, modDate=stamp)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for p in sorted(CLEAN.glob("*.md")):
        shutil.copy(p, OUT / p.name)
    shutil.copy(CLEAN / "fraud-policy-v1.md", OUT / "fraud-policy-v1-copy.md")  # exact duplicate

    d3 = dict(title="Dispute and Refund Policy", version=3, effective_date="2026-09-01", status="current")
    (OUT / "dispute-refund-policy-v3.md").write_text(front(**d3) + DISPUTE_V3_BODY)
    (OUT / "dispute-refund-policy-v3-copy.md").write_text(front(**d3) + DISPUTE_V3_BODY)  # exact duplicate
    (OUT / "dispute-refund-policy-v3-reformatted.md").write_text(front(**d3) + DISPUTE_V3_REFORMATTED)
    (OUT / "dispute-refund-policy-v3-wiki-export.txt").write_text(DISPUTE_WIKI)
    (OUT / "dispute-refund-policy-v4-DRAFT.md").write_text(front(
        title="Dispute and Refund Policy", version=4, effective_date="2026-12-01", status="draft") + DISPUTE_V4_DRAFT)
    (OUT / "disputes-faq.md").write_text(front(
        title="Disputes FAQ", version=1, effective_date="2025-03-10", status="current",
        applies_to="Dispute and Refund Policy") + FAQ)

    fees_v2 = (CLEAN / "fees-schedule-v2.md").read_text()
    meta, body = fees_v2.split("---\n", 2)[1:]
    rows = [r.strip("|").split("|") for r in body.splitlines() if r.startswith("|") and "---" not in r][1:]
    bullets = "\n".join(f"- {a.strip()}: {b.strip()}" for a, b in rows)
    (OUT / "fees-schedule-v2-reformatted.md").write_text(
        f"---\n{meta}---\n# Fees Schedule (v2)\n\n{bullets}\n\nAny fee waiver or refund of a fee requires human approval.\n")
    (OUT / "fees-schedule-v3-DRAFT.md").write_text(front(
        title="Fees Schedule", version=3, effective_date="2026-12-01", status="draft") + FEES_V3_DRAFT)

    (OUT / "escalation-policy-v1.txt").write_text(ESCALATION_TXT)
    (OUT / "card-replacement-guide.md").write_text(CARD_GUIDE)
    write_text_pdf(OUT / "support-sla-v1.pdf", SLA_LINES, per_page=6)
    write_text_pdf(OUT / "data-privacy-policy-v1.pdf", PRIVACY_LINES, per_page=3)
    write_scanned_pdf(OUT / "scanned-chargeback-memo.pdf", SCAN_LINES)
    print(f"wrote {len(list(OUT.iterdir()))} files to {OUT}")


if __name__ == "__main__":
    main()
