#!/usr/bin/env python3
"""Pull the support team's Notion knowledge base into the agent's local data (READ-ONLY on Notion).

Notion page "FAMS Workspace Portal / FAMS Support" holds:
  * Support Knowledge Base  (database) - solved cases written by the support team
  * Known Fixes Playbook     (database) - recurring problems with one proven fix
  * "Support guidance" section on the page itself - general rules for every answer

Only entries with Status = Approved are used. This script writes:
  data/raw/notion/ticket_KB-<n>.json   one file per Approved KB entry, in the same shape as the
                                       Freshdesk exports, so build_index.py indexes it with the
                                       ticket history (ticket_id "KB-<n>", source "notion")
  data/notion/known_fixes_notion.md    Approved playbook entries (same layout as known_fixes.md)
  data/notion/guidance.md              the page's "Support guidance" bullets
  data/notion/last_sync.json           summary + timestamp
and rebuilds the history index when the set of KB entries changed.

Settings (config/agent.env):  NOTION_API_KEY (secret, read-only internal integration),
  NOTION_KB_DATABASE_ID, NOTION_FIXES_DATABASE_ID, NOTION_SUPPORT_PAGE_ID

Usage:  python3 notion_sync.py [--max-age MINUTES] [--no-index]
  --max-age 60   skip if the last successful sync is younger than 60 minutes (used at the start
                 of every triage run, so approvals reach the agent within the hour)
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import HOME, RAW_DIR, redact

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
NOTION_RAW = RAW_DIR / "notion"
OUT = HOME / "data" / "notion"
STATE = OUT / "last_sync.json"
GUIDANCE_HEADING = "support guidance"
# FAMS Workspace Portal / FAMS Support (ids are not secret; override in config/agent.env)
DEFAULT_IDS = {"NOTION_SUPPORT_PAGE_ID": "3f075654d68a81f0a67dfe6cb61584f6",
               "NOTION_KB_DATABASE_ID": "3001ca67cb0d47a8ba97f2fa27f674e9",
               "NOTION_FIXES_DATABASE_ID": "9a71c3749f8041d785b78ab17a464870"}


# ---------------------------------------------------------------- Notion HTTP (GET/query only)
class Notion:
    def __init__(self, token, session=None):
        import requests  # imported here so the offline tests can inject a fake session
        self.s = session or requests.Session()
        self.h = {"Authorization": f"Bearer {token}", "Notion-Version": VERSION,
                  "Content-Type": "application/json"}

    def _call(self, method, path, body=None, version=None):
        h = dict(self.h, **({"Notion-Version": version} if version else {}))
        r = self.s.request(method, f"{API}{path}", headers=h, json=body, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"Notion {method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()

    def query(self, database_id, flt):
        """All rows of a database matching flt (handles paging and multi-source databases)."""
        path, version = f"/databases/{database_id}/query", None
        rows, cursor = [], None
        while True:
            body = {"filter": flt, "page_size": 100, **({"start_cursor": cursor} if cursor else {})}
            try:
                d = self._call("POST", path, body, version)
            except RuntimeError as e:
                if version or "data source" not in str(e).lower():
                    raise
                # newer workspaces: query the database's first data source instead
                ds = self._call("GET", f"/databases/{database_id}", version="2025-09-03")["data_sources"][0]["id"]
                path, version = f"/data_sources/{ds}/query", "2025-09-03"
                continue
            rows += d.get("results", [])
            if not d.get("has_more"):
                return rows
            cursor = d["next_cursor"]

    def blocks(self, block_id):
        out, cursor = [], None
        while True:
            q = f"?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            d = self._call("GET", f"/blocks/{block_id}/children{q}")
            out += d.get("results", [])
            if not d.get("has_more"):
                return out
            cursor = d["next_cursor"]


# ---------------------------------------------------------------- property helpers
def text(prop):
    if not prop:
        return ""
    t = prop.get("type")
    v = prop.get(t)
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in v or []).strip()
    if t == "select":
        return (v or {}).get("name", "")
    if t == "number":
        return "" if v is None else str(int(v) if float(v).is_integer() else v)
    if t == "unique_id":
        return f"{v.get('prefix') or ''}-{v.get('number')}".lstrip("-") if v else ""
    if t in ("created_time", "last_edited_time"):
        return v or ""
    return ""


def props(page):
    return {k: text(v) for k, v in (page.get("properties") or {}).items()}


def clean(s, limit=4000):
    return redact(re.sub(r"[ \t]+", " ", s or "")).strip()[:limit]


APPROVED = {"property": "Status", "select": {"equals": "Approved"}}


# ---------------------------------------------------------------- 1. knowledge base -> raw files
def kb_to_ticket(page):
    p = props(page)
    entry = p.get("Entry") or f"KB-{page['id'][:8]}"
    fd = p.get("Freshdesk ticket #", "")
    customer = p.get("Customer", "")
    slug = re.sub(r"[^a-z0-9]+", "-", customer.lower()).strip("-")
    keywords = [k.strip() for k in p.get("Keywords", "").split(",") if k.strip()]
    ref = f"Notion KB entry {entry}" + (f" (Freshdesk ticket #{fd})" if fd else "") + f" {page.get('url', '')}"
    convs = [{"body_text": clean(p.get("Resolution / response")), "incoming": False, "private": False,
              "created_at": p.get("Last edited", "")}]
    convs.append({"body_text": clean(ref + ". " + p.get("Internal notes", ""), 2000), "incoming": False,
                  "private": True, "created_at": p.get("Last edited", "")})
    return entry, {
        "status": "success",
        "source": "notion_kb",
        "notion_url": page.get("url", ""),
        "original": {
            "id": entry,
            "subject": clean(p.get("Problem summary"), 300),
            "description_text": clean(p.get("Customer question")),
            "status": "5",  # treated as closed/resolved by build_index.py
            "source": "notion",
            "type": p.get("Category", ""),
            "created_at": p.get("Created", ""),
            "updated_at": p.get("Last edited", ""),
            "requester_id": "",
            # one "customer" per company named in the entry; unnamed entries count as their own
            "company_id": f"kb:{slug}" if slug else f"kb:{entry}",
            "tags": [t for t in [p.get("Category", ""), p.get("Language", "")] if t] + keywords,
            "freshdesk_ticket": fd,
        },
        "conversations": convs,
    }


def sync_kb(n, db_id):
    pages = [pg for pg in n.query(db_id, APPROVED) if not pg.get("archived") and not pg.get("in_trash")]
    files = {}
    for pg in pages:
        entry, doc = kb_to_ticket(pg)
        if not doc["original"]["subject"] or not doc["conversations"][0]["body_text"]:
            continue  # an Approved entry without summary or resolution is useless - skip it
        if doc["original"]["subject"].upper().startswith("EXAMPLE"):
            continue  # the guide's example entry
        files[f"ticket_{entry}.json"] = json.dumps(doc, ensure_ascii=False, indent=2)
    NOTION_RAW.mkdir(parents=True, exist_ok=True)
    before = {f.name: f.read_text(encoding="utf-8") for f in NOTION_RAW.glob("ticket_*.json")}
    for name in set(before) - set(files):  # retired / un-approved / deleted
        (NOTION_RAW / name).unlink()
    for name, body in files.items():
        if before.get(name) != body:
            (NOTION_RAW / name).write_text(body, encoding="utf-8")
    return len(files), before != files


# ---------------------------------------------------------------- 2. playbook -> markdown
FIX_FIELDS = [("Recognise it by", "Recognise it by"), ("Not this fix if", "Not this entry if"),
              ("Fix (internal)", "Fix (internal)"), ("Reply should say", "Reply should say"),
              ("Special rule", "Special rule"), ("Evidence tickets", "Evidence")]


def sync_fixes(n, db_id):
    pages = [pg for pg in n.query(db_id, APPROVED) if not pg.get("archived") and not pg.get("in_trash")]
    entries = sorted((props(pg) | {"_url": pg.get("url", "")} for pg in pages),
                     key=lambda p: (p.get("Code") or "ZZ", p.get("Fix", "")))
    lines = ["# Known fixes approved in Notion (generated by notion_sync.py - do not edit)",
             "", "Same rules as known_fixes.md. For the same code, THIS file wins (it is newer).", ""]
    for p in entries:
        lines += ["---", "", f"## {p.get('Code') or 'N?'} — {clean(p.get('Fix'), 300)}"]
        for key, label in FIX_FIELDS:
            if p.get(key):
                lines.append(f"**{label}:** {clean(p[key], 2000)}")
        lines += [f"Source: {p['_url']}", ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "known_fixes_notion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(entries)


# ---------------------------------------------------------------- 3. guidance section
def block_text(b):
    v = b.get(b.get("type"), {}) or {}
    return "".join(x.get("plain_text", "") for x in v.get("rich_text", []) or []).strip()


def sync_guidance(n, page_id):
    out, inside = [], False
    for b in n.blocks(page_id):
        t = b.get("type", "")
        if t.startswith("heading_"):
            if inside:
                break
            inside = GUIDANCE_HEADING in block_text(b).lower()
            continue
        if inside:
            s = block_text(b)
            if s and not s.startswith("(Add more"):
                out.append(("- " if t in ("bulleted_list_item", "numbered_list_item", "to_do") else "") + clean(s, 1000))
    OUT.mkdir(parents=True, exist_ok=True)
    body = "# Support guidance from the FAMS Support Notion page (generated - do not edit)\n\n" + "\n".join(out) + "\n"
    (OUT / "guidance.md").write_text(body, encoding="utf-8")
    return len(out)


# ---------------------------------------------------------------- main
def main(argv=None, session=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age", type=int, default=0, help="minutes; skip if the last sync is younger")
    ap.add_argument("--no-index", action="store_true")
    a = ap.parse_args(argv)

    token = os.environ.get("NOTION_API_KEY", "")
    if not token:
        print(json.dumps({"notion": "skipped", "reason": "NOTION_API_KEY not set"}))
        return 0
    if a.max_age and STATE.exists():
        last = json.loads(STATE.read_text()).get("synced_at", "")
        if last and (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() < a.max_age * 60:
            print(json.dumps({"notion": "fresh", "synced_at": last}))
            return 0

    ids = {k: os.environ.get(k) or v for k, v in DEFAULT_IDS.items()}
    n = Notion(token, session)
    summary, changed = {"notion": "ok"}, False
    try:
        if ids["NOTION_KB_DATABASE_ID"]:
            summary["kb_entries"], changed = sync_kb(n, ids["NOTION_KB_DATABASE_ID"])
        if ids["NOTION_FIXES_DATABASE_ID"]:
            summary["known_fixes"] = sync_fixes(n, ids["NOTION_FIXES_DATABASE_ID"])
        if ids["NOTION_SUPPORT_PAGE_ID"]:
            summary["guidance_points"] = sync_guidance(n, ids["NOTION_SUPPORT_PAGE_ID"])
    except Exception as e:  # keep the last good copy; the agent carries on without fresh Notion data
        print(json.dumps({"notion": "error", "error": str(e)[:400]}))
        return 1

    summary["synced_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["index_rebuilt"] = bool(changed and not a.no_index)
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(summary, indent=2))
    if summary["index_rebuilt"]:
        subprocess.run([sys.executable, str(Path(__file__).with_name("build_index.py"))], check=True,
                       stdout=subprocess.DEVNULL)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
