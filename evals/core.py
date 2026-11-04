"""Shared types for the A6 eval suite: Case (the file format), Outcome (what one run produced), Grade (one verdict)."""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "evals" / "cases"
SPLIT_FILE = CASES_DIR / "SPLIT.sha256"
COMPONENTS = ("router", "policy", "tools", "coworker", "safety", "memory", "classifier")


class Case(BaseModel):
    id: str
    split: Literal["dev", "held_out"]
    component: Literal["router", "policy", "tools", "coworker", "safety", "memory", "classifier"]
    input: str
    setup: dict = Field(default_factory=dict)
    expected: str
    graders: list[dict]
    severity: Literal["high", "medium", "low"]
    source: Literal["new", "a1", "a4", "a5"] = "new"
    live: bool = True
    adversarial: bool = False


def load_cases(directory: Path = CASES_DIR) -> list[Case]:
    cases = []
    for path in sorted(directory.glob("*.jsonl")):
        cases += [Case.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]
    return cases


def split_digest(cases: list[Case]) -> str:
    """Checksum of the id-to-split assignment, so the dev/held-out split cannot drift silently."""
    return hashlib.sha256("\n".join(f"{c.id}:{c.split}" for c in sorted(cases, key=lambda c: c.id)).encode()).hexdigest()


@dataclass
class Grade:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Outcome:
    """Everything a grader may look at. `tool_calls` are the calls that actually executed."""
    text: str = ""
    route: str = ""
    report: dict | None = None
    ledger: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)   # {tool, args, ok, error, result}
    events: list[dict] = field(default_factory=list)       # coworker trace (RunTrace.read())
    budget: dict = field(default_factory=dict)             # declared limits for the run
    run_id: str | None = None
    label: str | None = None
    probability: float | None = None
    deferred: bool | None = None
    extra: dict = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_calls: int = 0
    latency_s: float = 0.0
    error: str | None = None


def report_text(report: dict) -> str:
    """The prose of a coworker report (no verification lines), for text graders and the judge."""
    parts = [report.get("summary", "")]
    if c := report.get("category"):
        parts.append(f"Category: {c.get('label')}")
    parts += [f"Finding: {f['claim']}" for f in report.get("findings", [])]
    parts += [f"Policy: {c['title']}, v{c['version']}, effective {c['effective_date']}" for c in report.get("policy_citations", [])]
    parts.append("Proposed resolution: " + report.get("proposed_resolution", ""))
    parts += [f"Proposed action: {a}" for a in report.get("proposed_actions", [])]
    parts += [f"Open question: {q}" for q in report.get("open_questions", [])]
    return "\n".join(parts)


def dump(obj) -> str:
    return json.dumps(obj, default=str)
