"""CLI: python -m opspilot "question"."""
import argparse
import asyncio
import sys

from mcp import MCPError

from opspilot import agent, policies, tickets
from opspilot.memory import Memory
from opspilot.mcp_client import open_toolbox
from opspilot.router import Route, route

REFUSAL = ("I can only answer questions about Northwind Pay policies (disputes, refunds, fees, fraud) "
           "and look up tickets by ID (e.g. T-1001) or customer (e.g. C-17).")

AGENT_FAILED = "Sorry, I couldn't reach the OpsPilot tool server ({reason}). Is the mock API running?"


def _ask_agent(question: str) -> str:
    async def go() -> str:
        async with open_toolbox() as toolbox:
            return await agent.run(question, toolbox)

    try:
        return asyncio.run(go())
    except (OSError, MCPError, ExceptionGroup) as e:
        return AGENT_FAILED.format(reason=type(e).__name__)


def dispatch(question: str, r: Route | None = None) -> str:
    r = r or route(question)
    if r.kind == "ticket_lookup":
        return tickets.lookup(r.ticket_id).model_dump_json(indent=2)
    if r.kind == "customer_tickets":
        return tickets.tickets_for_customer(r.customer_id).model_dump_json(indent=2)
    if r.kind in ("ticket_question", "customer_question"):
        return _ask_agent(question)
    if r.kind == "policy":
        return policies.answer(question)
    if r.kind == "error":
        return f"Sorry, I couldn't work out what you asked right now ({r.error})."
    return REFUSAL


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opspilot", description="OpsPilot assistant")
    parser.add_argument("question", nargs="?", help="e.g. 'show ticket T-1001' or 'how long to file a dispute?'")
    parser.add_argument("--forget", metavar="CUSTOMER_ID", help="delete everything remembered about a customer, then exit")
    parser.add_argument("--show-memory", metavar="CUSTOMER_ID", help="print what is remembered about a customer, then exit")
    args = parser.parse_args(argv)
    if args.forget:
        print(f"Forgot {Memory().forget(args.forget)} entries for {args.forget.upper()}.")
        return 0
    if args.show_memory:
        print(Memory().block_for([args.show_memory.upper()]) or f"Nothing remembered about {args.show_memory.upper()}.")
        return 0
    if not args.question:
        parser.error("a question is required (or use --forget / --show-memory)")
    try:
        print(dispatch(args.question))
    except ValueError as e:  # bad configuration, e.g. unknown LLM_PROVIDER
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2
    return 0
