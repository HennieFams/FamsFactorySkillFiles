#!/usr/bin/env python3
"""Offline test for notion_sync.py with a fake Notion API.  Run from tests/smoke_test.sh."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
os.environ.update(NOTION_API_KEY="test", NOTION_KB_DATABASE_ID="kbdb",
                  NOTION_FIXES_DATABASE_ID="fixdb", NOTION_SUPPORT_PAGE_ID="page")
import notion_sync as ns  # noqa: E402


def rt(s):
    return [{"plain_text": s}]


def kb(n, summary, question, answer, customer="", status="Approved", keywords=""):
    return {"id": f"id{n}", "url": f"https://notion.so/kb{n}", "properties": {
        "Problem summary": {"type": "title", "title": rt(summary)},
        "Entry": {"type": "unique_id", "unique_id": {"prefix": "KB", "number": n}},
        "Status": {"type": "select", "select": {"name": status}},
        "Category": {"type": "select", "select": {"name": "Tags & DWN"}},
        "Customer": {"type": "rich_text", "rich_text": rt(customer)},
        "Customer question": {"type": "rich_text", "rich_text": rt(question)},
        "Resolution / response": {"type": "rich_text", "rich_text": rt(answer)},
        "Internal notes": {"type": "rich_text", "rich_text": rt("password: Secret123 reset in admin")},
        "Keywords": {"type": "rich_text", "rich_text": rt(keywords)},
        "Freshdesk ticket #": {"type": "number", "number": 1545},
        "Last edited": {"type": "last_edited_time", "last_edited_time": "2026-10-05T10:00:00Z"},
    }}


class Resp:
    def __init__(self, d, code=200):
        self.d, self.status_code, self.text = d, code, json.dumps(d)

    def json(self):
        return self.d


class FakeSession:
    def __init__(self, kb_rows):
        self.kb_rows, self.calls = kb_rows, []

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append((method, url))
        assert method in ("GET", "POST") and "/pages" not in url, "sync must be read-only"
        if url.endswith("/databases/kbdb/query"):
            return Resp({"results": [r for r in self.kb_rows if r["properties"]["Status"]["select"]["name"] == "Approved"], "has_more": False})
        if url.endswith("/databases/fixdb/query"):
            return Resp({"results": [{"id": "f1", "url": "https://notion.so/k2", "properties": {
                "Fix": {"type": "title", "title": rt("Tag invalid after change (DWN)")},
                "Code": {"type": "rich_text", "rich_text": rt("K2")},
                "Recognise it by": {"type": "rich_text", "rich_text": rt("invalid tag")},
                "Reply should say": {"type": "rich_text", "rich_text": rt("set DWN and wait for sync")}}}], "has_more": False})
        if "/blocks/page/children" in url:
            def b(t, s):
                return {"type": t, t: {"rich_text": rt(s)}}
            return Resp({"results": [b("heading_2", "How to add a solved case"), b("bulleted_list_item", "not guidance"),
                                     b("heading_2", "Support guidance (the agent reads this section)"),
                                     b("paragraph", "General rules"), b("bulleted_list_item", "Reply in the customer's language."),
                                     b("bulleted_list_item", "(Add more: support hours…)"),
                                     b("heading_2", "How the agent uses this page"), b("bulleted_list_item", "after")],
                         "has_more": False})
        raise AssertionError(url)


rows = [kb(1, "Tag invalid after registration change", "Truck tag shows invalid after we changed the registration",
           "Set the vehicle to DWN, wait for the unit to sync (orange to grey), then scan vehicle tag first.",
           "Acme Haulage", keywords="tag werk nie, invalid tag"),
        kb(2, "EXAMPLE – sample", "q", "a"),
        kb(3, "Draft entry", "q", "a", status="Draft")]
assert ns.main(["--no-index"], FakeSession(rows)) == 0
files = sorted(p.name for p in ns.NOTION_RAW.glob("ticket_*.json"))
assert files == ["ticket_KB-1.json"], files
doc = json.loads((ns.NOTION_RAW / "ticket_KB-1.json").read_text())
assert doc["original"]["company_id"] == "kb:acme-haulage"
assert "Secret123" not in json.dumps(doc), "credentials must be redacted"
assert "tag werk nie" in doc["original"]["tags"]
fixes = (ns.OUT / "known_fixes_notion.md").read_text()
assert "## K2" in fixes and "set DWN" in fixes
g = (ns.OUT / "guidance.md").read_text()
assert "Reply in the customer's language." in g and "not guidance" not in g and "Add more" not in g and "after" not in g

# retiring the entry removes its file on the next sync
rows[0]["properties"]["Status"]["select"]["name"] = "Retired"
assert ns.main(["--no-index"], FakeSession(rows)) == 0
assert not list(ns.NOTION_RAW.glob("ticket_*.json")), "retired entry must be removed"
rows[0]["properties"]["Status"]["select"]["name"] = "Approved"
ns.main(["--no-index"], FakeSession(rows))
# --max-age: second call within the hour does not hit Notion
s = FakeSession(rows)
ns.main(["--max-age", "60"], s)
assert s.calls == [], "fresh sync should be skipped"
print("notion_sync test OK")
