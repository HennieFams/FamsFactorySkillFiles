#!/usr/bin/env python3
"""Read-only Freshdesk MCP server for the FAMS Support Agent.

Only GET requests exist in this file, so the agent physically cannot reply to,
note on, edit or delete anything in Freshdesk - no reliance on tool deny-lists.
The API key is read from config/agent.env and never appears in any MCP config.

Tools: list_recent_tickets, get_ticket, get_ticket_conversation, get_contact, search_tickets
Run (stdio): .venv/bin/python scripts/freshdesk_readonly_mcp.py
"""
import os

import requests
from mcp.server.fastmcp import FastMCP

import common  # noqa: F401  (loads config/agent.env into the environment)
from common import clean_text, redact

DOMAIN = os.environ.get("FRESHDESK_DOMAIN", "tecmo.freshdesk.com")
KEY = os.environ.get("FRESHDESK_API_KEY", "")
BASE = f"https://{DOMAIN}/api/v2"
STATUS = {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed"}
SOURCE = {1: "Email", 2: "Portal", 3: "Phone", 7: "Chat", 9: "Feedback widget", 10: "Outbound email"}

mcp = FastMCP("freshdesk")


def _get(path, params=None):
    if not KEY:
        raise RuntimeError("FRESHDESK_API_KEY missing in config/agent.env")
    r = requests.get(BASE + path, params=params, auth=(KEY, "X"), timeout=30)
    if r.status_code == 429:
        raise RuntimeError("Freshdesk rate limit hit - try again in a minute")
    r.raise_for_status()
    return r.json()


def _ticket_summary(t):
    return {
        "id": t.get("id"),
        "subject": t.get("subject"),
        "status": STATUS.get(t.get("status"), t.get("status")),
        "source": SOURCE.get(t.get("source"), t.get("source")),
        "source_code": t.get("source"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
        "requester_id": t.get("requester_id"),
        "company_id": t.get("company_id"),
        "responder_id": t.get("responder_id"),
        "type": t.get("type"),
        "tags": t.get("tags"),
    }


@mcp.tool()
def list_recent_tickets(per_page: int = 30, page: int = 1) -> list:
    """Newest Freshdesk tickets first (created in the last 30 days). Summary fields only;
    call get_ticket for the description."""
    per_page = max(1, min(int(per_page), 100))
    data = _get("/tickets", {"order_by": "created_at", "order_type": "desc",
                             "per_page": per_page, "page": page})
    return [_ticket_summary(t) for t in data]


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """One ticket with its description and the requester's name/email."""
    t = _get(f"/tickets/{int(ticket_id)}", {"include": "requester"})
    out = _ticket_summary(t)
    req = t.get("requester") or {}
    out.update({
        "description_text": redact(clean_text(t.get("description_text") or t.get("description"), cut_quoted=True))[:6000],
        "requester_name": req.get("name"),
        "requester_email": req.get("email"),
    })
    return out


@mcp.tool()
def get_ticket_conversation(ticket_id: int) -> list:
    """All replies and notes on a ticket, oldest first. incoming=true means from the customer;
    private=true means an internal note."""
    convs = _get(f"/tickets/{int(ticket_id)}/conversations", {"per_page": 100})
    return [{
        "created_at": c.get("created_at"),
        "incoming": bool(c.get("incoming")),
        "private": bool(c.get("private")),
        "from_email": c.get("from_email"),
        "body_text": redact(clean_text(c.get("body_text") or c.get("body"), cut_quoted=True))[:4000],
    } for c in sorted(convs, key=lambda c: c.get("created_at") or "")]


@mcp.tool()
def get_contact(contact_id: int) -> dict:
    """Name, email and company of a requester (contact)."""
    c = _get(f"/contacts/{int(contact_id)}")
    return {"id": c.get("id"), "name": c.get("name"), "email": c.get("email"),
            "company_id": c.get("company_id")}


@mcp.tool()
def search_tickets(query: str) -> list:
    """Freshdesk filter query, e.g. "status:2" or "created_at:>'2026-10-01'" (Freshdesk filter syntax)."""
    q = query if query.startswith('"') else f'"{query}"'
    data = _get("/search/tickets", {"query": q})
    return [_ticket_summary(t) for t in data.get("results", [])][:30]


if __name__ == "__main__":
    mcp.run()
